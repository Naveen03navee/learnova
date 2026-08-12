import asyncio
import logging
from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from app.models.pattern_chunk import PatternChunk
from app.models.pattern import ExamPattern, PatternStatus
from app.core.config import settings
from app.services.document_processor.embedder import embedder
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class PatternRetrievalResult(BaseModel):
    chunk_id: UUID
    content: str
    question_type: Optional[str]
    section: Optional[str]
    topic: Optional[str]
    difficulty: Optional[str]
    marks: Optional[float]
    question_number: Optional[str]
    distance: float

def _get_embedding_sync(query: str) -> List[float]:
    embeddings = embedder.encode([query])
    return embeddings[0]

class PatternRetriever:
    """
    Retrieves ONLY from PatternChunk.
    Never queries DocumentChunk.
    """
    
    @staticmethod
    async def retrieve(db: AsyncSession, pattern_id: UUID, query: str, top_k: int = 15) -> List[PatternRetrievalResult]:
        # 1. Verify pattern exists and is ACTIVE
        pattern_query = select(ExamPattern.id).where(
            and_(ExamPattern.id == pattern_id, ExamPattern.status == PatternStatus.ACTIVE)
        )
        pattern = (await db.execute(pattern_query)).scalar_one_or_none()
        if not pattern:
            logger.warning(f"Pattern {pattern_id} not found or not active")
            return []

        # 2. Embedding Generation
        query_embedding = await asyncio.to_thread(_get_embedding_sync, query)
        
        # Cosine distance limit (distance = 1 - similarity)
        max_distance = 1.0 - settings.RAG_MIN_COSINE_SIMILARITY
        
        # 3. Vector Search scoped explicitly to pattern_id
        distance_expr = PatternChunk.embedding.cosine_distance(query_embedding)
        
        chunk_query = select(
            PatternChunk.id,
            PatternChunk.content,
            PatternChunk.question_type,
            PatternChunk.section,
            PatternChunk.topic,
            PatternChunk.difficulty,
            PatternChunk.marks,
            PatternChunk.question_number,
            distance_expr.label("distance")
        ).where(
            and_(
                PatternChunk.pattern_id == pattern_id,
                distance_expr <= max_distance
            )
        ).order_by(
            distance_expr
        ).limit(top_k)
        
        result = await db.execute(chunk_query)
        rows = result.all()
        
        return [
            PatternRetrievalResult(
                chunk_id=row.id,
                content=row.content,
                question_type=row.question_type,
                section=row.section,
                topic=row.topic,
                difficulty=row.difficulty,
                marks=row.marks,
                question_number=row.question_number,
                distance=row.distance
            ) for row in rows
        ]
