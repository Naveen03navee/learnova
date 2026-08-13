from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, func
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.models.paper import QuestionPaper, PaperStatus
from app.models.question import Question
from app.services.ai.manager import ai_manager
from app.services.ai.router import get_primary_provider_name
from app.services.ai.schemas import GenerationRequest
from app.services.generation.prompts import PAPER_QUALITY_SYSTEM_PROMPT
from app.core.logging import get_logger

logger = get_logger(__name__)

from app.services.generation.events import event_bus
from app.schemas.generation import GenerationEvent, EventType
import asyncio

async def publish_event(paper_id: UUID, step: str, status: str = "RUNNING", **kwargs):
    logger.info(step, paper_id=str(paper_id), **kwargs)
    try:
        event_type = EventType.INFO
        if "ERROR" in step:
            event_type = EventType.ERROR
            status = "ERROR"
        elif "COMPLETE" in step:
            event_type = EventType.SUCCESS
            status = "SUCCESS"
            
        msg = kwargs.get("reason") or kwargs.get("error") or step.replace("_", " ").title()
        
        event = GenerationEvent(
            resource_id=paper_id,
            event_type=event_type,
            status=status,
            message=str(msg)
        )
        await event_bus.publish(event)
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")


class QualityIssueSchema(BaseModel):
    question_number: int = Field(..., description="1-indexed question number")
    issue_type: str = Field(..., description="DUPLICATE, NEAR_DUPLICATE, STRONG_THEMATIC_REPETITION, MILD_THEMATIC_OVERLAP, etc.")
    severity: str = Field(..., description="LOW, MEDIUM, or HIGH")
    reason: str = Field(..., description="Explanation of the issue")
    related_question_numbers: List[int] = Field(default_factory=list, description="Other questions related to this issue, e.g., duplicates")
    repairable: bool = Field(..., description="Whether this issue can be fixed by replacing the question")
    auto_repair_recommended: bool = Field(False, description="Whether to auto-replace. Only true for DUPLICATE/NEAR_DUPLICATE or excessive STRONG_THEMATIC_REPETITION")
    confidence: float = Field(..., description="Confidence score 0.0-1.0")

class QualityMetricsSchema(BaseModel):
    duplication_score: int = Field(..., description="0-100 score where 100 means no duplication")
    thematic_diversity_score: int = Field(..., description="0-100 score")
    difficulty_balance_score: int = Field(..., description="0-100 score")
    topic_coverage_score: int = Field(..., description="0-100 score")
    question_type_balance_score: int = Field(..., description="0-100 score")
    exam_alignment_score: int = Field(..., description="0-100 score")
    clarity_score: int = Field(..., description="0-100 score")
    overall_balance_score: int = Field(..., description="0-100 score")

class QualityReportSchema(BaseModel):
    overall_status: str = Field(..., description="PASS, WARNING, or FAIL")
    overall_score: int = Field(..., description="0-100 score")
    summary: str = Field(..., description="Overall summary of the paper's quality")
    problematic_question_numbers: List[int] = Field(default_factory=list, description="List of question numbers (1-indexed) that are candidates for replacement")
    issues: List[QualityIssueSchema] = Field(default_factory=list)
    metrics: QualityMetricsSchema
    recommendations: List[str] = Field(default_factory=list)

async def run_paper_quality_check(db: AsyncSession, paper_id: UUID, auto_repair: bool = True) -> QuestionPaper:
    await publish_event(paper_id, "QUALITY_CHECK_STARTED")
    
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
        
    await publish_event(paper_id, "QUALITY_ANALYZING")
    
    # Format the paper for the AI
    paper_content = f"PAPER TITLE: {paper.title}\n"
    paper_content += f"EXAM CONFIG: {paper.config.get('exam_name', 'Unknown')}\n"
    if paper.subject_id:
        paper_content += f"SUBJECT CONFIG: Subject specific paper\n"
    else:
        paper_content += f"SUBJECT CONFIG: Full Exam-level paper\n\n"
    
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
    
    provider = get_primary_provider_name("hard")
    
    req = GenerationRequest(
        system_prompt=PAPER_QUALITY_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=QualityReportSchema,
        temperature=0.2
    )
    
    try:
        res = await ai_manager.generate(provider, req)
    except Exception as e:
        await publish_event(paper_id, "QUALITY_CHECK_ERROR", status="ERROR", error=str(e))
        # Do not modify paper on failure
        raise ValueError(f"AI Quality Check could not be completed. Your paper has not been changed.")
        
    report: QualityReportSchema = res.parsed_output
    
    await publish_event(paper_id, "QUALITY_ANALYSIS_COMPLETE", score=report.overall_score)
    
    # Enforce status string
    valid_statuses = ["PASS", "WARNING", "FAIL"]
    status = report.overall_status.upper()
    if status not in valid_statuses:
        status = "WARNING"
        
    final_report_data = report.model_dump()
    
    # Check if there is an existing repair_summary to preserve initial score
    existing_repair_summary = None
    if paper.quality_report and isinstance(paper.quality_report, dict):
        existing_repair_summary = paper.quality_report.get("repair_summary")
        if existing_repair_summary:
            final_report_data["initial_score"] = paper.quality_report.get("initial_score", report.overall_score)
            final_report_data["final_score"] = report.overall_score
            final_report_data["repair_summary"] = existing_repair_summary
    
    if not existing_repair_summary:
        final_report_data["initial_score"] = report.overall_score
        final_report_data["final_score"] = report.overall_score
        final_report_data["repair_summary"] = {
            "repaired": False,
            "replacement_count": 0,
            "replacements": [],
            "not_repaired": []
        }
        
    paper.quality_status = status
    paper.quality_report = final_report_data
    paper.quality_checked_at = datetime.utcnow()
    paper.quality_report_stale = False
    
    # Auto Repair Phase
    if auto_repair and report.problematic_question_numbers:
        await publish_event(paper_id, "AUTO_REPAIR_STARTED", issues_count=len(report.problematic_question_numbers))
        from app.services.paper.builder import select_single_replacement
        import numpy as np
        
        replaced_count = 0
        replacements = []
        not_repaired = []
        
        existing_question_ids = {i.question_id for i in paper.items if i.question_id is not None}
        existing_embeddings_query = await db.execute(select(Question.embedding).where(Question.id.in_(existing_question_ids)))
        existing_embeddings = [np.array(e) for e in existing_embeddings_query.scalars().all() if e is not None]
        
        for q_num in report.problematic_question_numbers:
            idx = q_num - 1
            if idx < 0 or idx >= len(items):
                continue
                
            item = items[idx]
            
            # Find the issue reason
            issue_reason = "Unknown issue"
            should_repair = False
            for issue in report.issues:
                if issue.question_number == q_num:
                    issue_reason = issue.reason
                    should_repair = issue.auto_repair_recommended
                    break
                    
            if not should_repair:
                # Issue is mild or auto-repair is not recommended
                not_repaired.append({"question_number": q_num, "reason": f"Skipped: AI classified as warning only (Reason: {issue_reason})"})
                await publish_event(paper_id, "REPLACEMENT_SKIPPED", question_number=q_num, reason="Warning only, no repair recommended")
                continue
                    
            await publish_event(paper_id, "REPLACEMENT_ANALYZING", question_number=q_num)
            
            # Get original section constraints
            section_config = None
            for sec in paper.config.get("sections", []):
                if sec["name"] == item.section_name:
                    section_config = sec
                    break
                    
            if not section_config or not item.question_id:
                not_repaired.append({"question_number": q_num, "reason": "Could not identify section constraints or original question."})
                await publish_event(paper_id, "REPLACEMENT_NOT_FOUND", question_number=q_num, reason="No constraints")
                continue
                
            orig_q = await db.get(Question, item.question_id)
            if not orig_q:
                not_repaired.append({"question_number": q_num, "reason": "Original question not found in database."})
                continue
                
            filters = [
                Question.exam_id == paper.exam_id,
                func.lower(Question.question_type) == section_config["question_type"].lower(),
                func.lower(Question.difficulty) == section_config["difficulty"].lower()
            ]
            if paper.subject_id:
                filters.append(Question.subject_id == paper.subject_id)
                
            candidates_query = await db.execute(select(Question).where(and_(*filters)))
            all_candidates = candidates_query.scalars().all()
            
            # Exclude already used questions
            valid_candidates = [c for c in all_candidates if c.id not in existing_question_ids]
            
            if not valid_candidates:
                not_repaired.append({"question_number": q_num, "reason": "No suitable replacement matching the paper requirements was found."})
                await publish_event(paper_id, "REPLACEMENT_NOT_FOUND", question_number=q_num, reason="No suitable replacement was available in your Question Bank.")
                continue
                
            # Pick best replacement
            best_candidate = select_single_replacement(valid_candidates, existing_embeddings)
            
            if best_candidate:
                old_text = item.question_text_snapshot
                
                # Apply replacement
                item.question_id = best_candidate.id
                item.question_text_snapshot = best_candidate.question_text
                item.content_snapshot = best_candidate.content
                item.marks_snapshot = best_candidate.marks
                
                existing_question_ids.add(best_candidate.id)
                if best_candidate.embedding:
                    existing_embeddings.append(np.array(best_candidate.embedding))
                
                replaced_count += 1
                replacements.append({
                    "question_number": q_num,
                    "status": "replaced",
                    "reason": issue_reason,
                    "old_question_id": str(orig_q.id),
                    "new_question_id": str(best_candidate.id),
                    "old_text": old_text,
                    "new_text": best_candidate.question_text
                })
                await publish_event(paper_id, "QUESTION_REPLACED", question_number=q_num)
            else:
                not_repaired.append({"question_number": q_num, "reason": "No suitable replacement matching the paper requirements was found."})
                await publish_event(paper_id, "REPLACEMENT_NOT_FOUND", question_number=q_num, reason="Semantic selection failed")
                
        await publish_event(paper_id, "AUTO_REPAIR_COMPLETE", replaced_count=replaced_count)
        
        if replaced_count > 0:
            final_report_data["repair_summary"] = {
                "repaired": True,
                "replacement_count": replaced_count,
                "replacements": replacements,
                "not_repaired": not_repaired
            }
            paper.quality_report = final_report_data
            await db.commit()
            
            await publish_event(paper_id, "QUALITY_RECHECK_STARTED")
            return await run_paper_quality_check(db, paper_id, auto_repair=False)
        else:
            final_report_data["repair_summary"]["not_repaired"] = not_repaired
            paper.quality_report = final_report_data
            await db.commit()

    else:
        await db.commit()
        
    if not auto_repair:
        await publish_event(paper_id, "QUALITY_RECHECK_COMPLETE", score=paper.quality_report.get("final_score"))
    await publish_event(paper_id, "QUALITY_CHECK_COMPLETE", final_status=paper.quality_status)
    return paper
