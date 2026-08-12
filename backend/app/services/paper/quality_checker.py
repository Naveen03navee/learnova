from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.models.paper import QuestionPaper, PaperStatus
from app.services.ai.manager import ai_manager
from app.services.ai.router import get_primary_provider_name
from app.services.ai.schemas import GenerationRequest

class QualityReportSchema(BaseModel):
    status: str = Field(..., description="Must be exactly PASS, WARNING, or FAIL")
    repetition_analysis: str = Field(..., description="Analysis of thematic repetition or overlapping concepts")
    difficulty_consistency: str = Field(..., description="Analysis of whether the difficulty is consistent and appropriate")
    overall_feedback: str = Field(..., description="Overall summary of the paper's quality")
    problematic_question_numbers: List[int] = Field(default_factory=list, description="List of question numbers (1-indexed) that have issues")

PAPER_QUALITY_SYSTEM_PROMPT = """You are an expert academic reviewer. Your job is to review a draft examination paper and provide a strict quality assessment.
You must evaluate the paper holistically, looking for:
1. Concept overlap: Do multiple questions test the exact same concept?
2. Thematic repetition: Are there too many questions about the same narrow topic?
3. Difficulty consistency: Does the difficulty seem appropriate and varied, or is it heavily skewed?

You must output a structured assessment.
If the paper is excellent, status must be PASS.
If there are minor issues or moderate repetition, status must be WARNING.
If the paper is structurally flawed, highly repetitive, or has severe concept overlap, status must be FAIL.
"""

async def run_paper_quality_check(db: AsyncSession, paper_id: UUID) -> QuestionPaper:
    result = await db.execute(
        select(QuestionPaper)
        .options(selectinload(QuestionPaper.items))
        .where(QuestionPaper.id == paper_id)
    )
    paper = result.scalar_one_or_none()
    
    if not paper:
        raise ValueError("Paper not found")
        
    if paper.status != PaperStatus.DRAFT:
        raise ValueError(f"Quality check can only be run on DRAFT papers. Current status: {paper.status}")
        
    # Format the paper for the AI
    paper_content = f"PAPER TITLE: {paper.title}\n\n"
    
    items = sorted(paper.items, key=lambda x: x.order_index)
    for idx, item in enumerate(items):
        q_num = idx + 1
        marks = item.marks_override if item.marks_override is not None else item.marks_snapshot
        paper_content += f"Question {q_num} [{item.section_name} - {marks} Marks]:\n{item.question_text_snapshot}\n"
        
        options = item.content_snapshot.get("options")
        if options:
            for opt in options:
                paper_content += f"  {opt['id']}. {opt['text']}\n"
        
        paper_content += f"Correct Answer: {item.content_snapshot.get('correct_answer')}\n\n"
        
    user_prompt = f"Please review the following paper:\n\n{paper_content}"
    
    # We can use the medium/hard provider for holistic review
    provider = get_primary_provider_name("hard")
    
    req = GenerationRequest(
        system_prompt=PAPER_QUALITY_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=QualityReportSchema,
        temperature=0.3
    )
    
    res = await ai_manager.generate(provider, req)
    report: QualityReportSchema = res.parsed_output
    
    # Enforce status string
    valid_statuses = ["PASS", "WARNING", "FAIL"]
    status = report.status.upper()
    if status not in valid_statuses:
        status = "WARNING"
        
    paper.quality_status = status
    paper.quality_report = report.model_dump()
    paper.quality_checked_at = datetime.utcnow()
    paper.quality_report_stale = False
    
    await db.commit()
    return paper
