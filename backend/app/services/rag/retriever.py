import asyncio
import logging
from typing import Optional, List
from uuid import UUID
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, func

from app.models.knowledge import DocumentChunk, Resource, ResourceStatus, Folder
from app.models.workspace import Subject, Exam
from app.schemas.rag import RetrievalRequest, RetrievalResult, RetrievalResponse
from app.core.config import settings
from app.services.document_processor.embedder import embedder

logger = logging.getLogger(__name__)

def _get_embedding_sync(query: str) -> List[float]:
    # embedder.encode returns a list of embeddings. We pass a list of 1 string.
    embeddings = embedder.encode([query])
    return embeddings[0]

async def validate_hierarchy(db: AsyncSession, exam_id: UUID, subject_id: UUID, folder_id: Optional[UUID]):
    """
    Validates that the provided Exam, Subject, and Folder exist and belong to the correct hierarchy.
    Raises ValueError if invalid.
    """
    # 1. Validate Exam
    exam_query = select(Exam).where(Exam.id == exam_id)
    exam = (await db.execute(exam_query)).scalar_one_or_none()
    if not exam:
        raise ValueError(f"Exam {exam_id} not found.")

    # 2. Validate Subject
    subject_query = select(Subject).where(
        and_(Subject.id == subject_id, Subject.exam_id == exam_id)
    )
    subject = (await db.execute(subject_query)).scalar_one_or_none()
    if not subject:
        raise ValueError(f"Subject {subject_id} does not belong to Exam {exam_id} or does not exist.")

    # 3. Validate Folder
    if folder_id:
        folder_query = select(Folder).where(
            and_(
                Folder.id == folder_id,
                Folder.subject_id == subject_id,
                Folder.exam_id == exam_id
            )
        )
        folder = (await db.execute(folder_query)).scalar_one_or_none()
        if not folder:
            raise ValueError(f"Folder {folder_id} does not belong to the given Exam/Subject or does not exist.")

async def retrieve_chunks(db: AsyncSession, request: RetrievalRequest) -> RetrievalResponse:
    # 1. Scope Validation
    try:
        await validate_hierarchy(db, request.exam_id, request.subject_id, request.folder_id)
    except ValueError as e:
        # We raise a standard ValueError here, which the router will catch and turn into HTTP 400 or 404
        raise e

    # 2. Embedding Generation (Non-blocking)
    query_embedding = await asyncio.to_thread(_get_embedding_sync, request.query)

    # 3. Build Strict Scope (Folder and Descendants CTE if folder_id is provided)
    folder_filter = None
    if request.folder_id:
        # Recursive CTE to get the folder and all its descendants
        # Base case
        top_folder = select(Folder.id).where(Folder.id == request.folder_id).cte(name="folder_tree", recursive=True)
        # Recursive case
        folder_alias = top_folder.alias("parent_folder")
        child_folder = select(Folder.id).join(folder_alias, Folder.parent_id == folder_alias.c.id)
        # Union
        recursive_q = top_folder.union_all(child_folder)
        # The filter condition for resources
        folder_filter = Resource.folder_id.in_(select(recursive_q.c.id))
    
    # Cosine distance limit (distance = 1 - similarity)
    max_distance = 1.0 - settings.RAG_MIN_COSINE_SIMILARITY
    
    # 4. Vector Search and Resource Diversity
    # We can use a CTE to rank chunks per resource before applying the final top_k limit.
    # This prevents one resource from dominating the results.
    
    distance_expr = DocumentChunk.embedding.cosine_distance(query_embedding)
    
    # Select chunk + resource metadata + distance + row number per resource
    ranked_chunks_cte = select(
        DocumentChunk.id.label("chunk_id"),
        DocumentChunk.content,
        DocumentChunk.chunk_index,
        DocumentChunk.page_number,
        Resource.id.label("resource_id"),
        Resource.name.label("resource_name"),
        Resource.folder_id,
        distance_expr.label("distance"),
        func.row_number().over(
            partition_by=Resource.id,
            order_by=distance_expr
        ).label("rank_in_resource")
    ).select_from(DocumentChunk).join(
        Resource, Resource.id == DocumentChunk.resource_id
    ).where(
        and_(
            Resource.exam_id == request.exam_id,
            Resource.subject_id == request.subject_id,
            Resource.status == ResourceStatus.READY,
            distance_expr <= max_distance
        )
    )

    if folder_filter is not None:
        ranked_chunks_cte = ranked_chunks_cte.where(folder_filter)

    ranked_chunks_cte = ranked_chunks_cte.cte("ranked_chunks")

    # Now select from the CTE, applying the diversity limit and final global top_k limit
    final_query = select(
        ranked_chunks_cte.c.chunk_id,
        ranked_chunks_cte.c.content,
        ranked_chunks_cte.c.chunk_index,
        ranked_chunks_cte.c.page_number,
        ranked_chunks_cte.c.resource_id,
        ranked_chunks_cte.c.resource_name,
        ranked_chunks_cte.c.folder_id,
        ranked_chunks_cte.c.distance
    ).where(
        ranked_chunks_cte.c.rank_in_resource <= settings.RAG_MAX_CHUNKS_PER_RESOURCE
    ).order_by(
        ranked_chunks_cte.c.distance.asc()
    ).limit(request.top_k)

    result = await db.execute(final_query)
    rows = result.all()

    # 5. Format Response
    retrieval_results = []
    for row in rows:
        similarity = 1.0 - float(row.distance)
        retrieval_results.append(
            RetrievalResult(
                chunk_id=row.chunk_id,
                resource_id=row.resource_id,
                resource_name=row.resource_name,
                folder_id=row.folder_id,
                page_number=row.page_number,
                chunk_index=row.chunk_index,
                content=row.content,
                similarity=round(similarity, 4)
            )
        )

    return RetrievalResponse(
        query=request.query,
        exam_id=request.exam_id,
        subject_id=request.subject_id,
        folder_id=request.folder_id,
        results=retrieval_results,
        total_results=len(retrieval_results)
    )
