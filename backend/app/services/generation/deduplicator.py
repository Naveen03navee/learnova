import asyncio
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from app.core.config import settings
from app.models.generation import GeneratedQuestion, ApprovalStatus
from app.services.document_processor.embedder import embedder

def _get_embedding_sync(text: str) -> list[float]:
    embeddings = embedder.encode([text])
    return embeddings[0]

async def check_duplicate(db: AsyncSession, question_text: str, exam_id: str, subject_id: str) -> bool:
    """
    Returns True if a highly similar question already exists (is a duplicate).
    """
    # 1. Generate embedding for the proposed question text
    query_embedding = await asyncio.to_thread(_get_embedding_sync, question_text)
    
    # 2. Check against existing GeneratedQuestions that are NOT rejected
    # In Phase 8, this might also check a final QuestionBank table, but for now we check
    # GeneratedQuestions that are Approved or Pending (i.e., staged/saved).
    # We restrict the scope to the same exam/subject.
    
    # Distance = 1 - similarity. So a similarity of 0.85 means distance <= 0.15
    max_distance = 1.0 - settings.GENERATION_DUPLICATE_THRESHOLD
    
    # We need to check both the permanent Question table AND the staging GeneratedQuestion table
    from app.models.generation import GenerationSession
    from app.models.question import Question
    
    # Check GeneratedQuestion first
    distance_expr_gen = GeneratedQuestion.embedding.cosine_distance(query_embedding)
    query_gen = select(GeneratedQuestion.id).join(
        GenerationSession, GeneratedQuestion.session_id == GenerationSession.id
    ).where(
        and_(
            GenerationSession.exam_id == exam_id,
            GenerationSession.subject_id == subject_id,
            GeneratedQuestion.approval_status != ApprovalStatus.REJECTED,
            distance_expr_gen <= max_distance
        )
    ).limit(1)
    
    result_gen = await db.execute(query_gen)
    if result_gen.scalar_one_or_none():
        return True
        
    # Check permanent Question
    distance_expr_q = Question.embedding.cosine_distance(query_embedding)
    query_q = select(Question.id).where(
        and_(
            Question.exam_id == exam_id,
            Question.subject_id == subject_id,
            distance_expr_q <= max_distance
        )
    ).limit(1)
    
    result_q = await db.execute(query_q)
    return result_q.scalar_one_or_none() is not None

async def generate_question_embedding(question_text: str) -> list[float]:
    """Helper to just generate the embedding without checking duplicates."""
    return await asyncio.to_thread(_get_embedding_sync, question_text)
