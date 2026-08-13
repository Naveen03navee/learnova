import asyncio
import logging
from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.future import select

from app.models.knowledge import Resource, ResourceStatus, DocumentChunk
from app.services.storage import download_file_from_storage
from app.core.supabase import get_supabase_service_client
from app.services.generation.events import event_bus
from app.schemas.generation import GenerationEvent, EventType

from .pdf import extract_pdf
from .docx import extract_docx
from .txt import extract_txt
from .cleaner import clean_text
from .chunker import chunk_text
from .embedder import embedder

logger = logging.getLogger(__name__)

# Bounded semaphore to prevent concurrent OCR / chunking / embedding from
# saturating CPU or hitting provider limits. This is scoped exclusively to
# document processing; LLM generation has its own concurrency guard via
# GENERATION_MAX_TOTAL_LLM_CALLS.
# Default: 3 concurrent processing tasks per Python worker/process.
# NOTE: On Render, each gunicorn worker has its own semaphore — the limit
# is not shared across processes.
_MAX_CONCURRENT_DOC_PROCESSING = 3
_doc_processing_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_DOC_PROCESSING)

async def transition_status(session_maker: async_sessionmaker[AsyncSession], resource_id: UUID, status: ResourceStatus, error_message: Optional[str] = None):
    """Safely updates the status of a resource in a new transaction."""
    async with session_maker() as session:
        resource = await session.get(Resource, resource_id)
        if resource:
            resource.status = status
            # Log errors if any
            if error_message:
                logger.error(f"Resource {resource_id} FAILED: {error_message}")
            await session.commit()
            
    progress_map = {
        ResourceStatus.UPLOADED: 0.05,
        ResourceStatus.PROCESSING: 0.1,
        ResourceStatus.EXTRACTING: 0.3,
        ResourceStatus.OCR: 0.5,
        ResourceStatus.CHUNKING: 0.7,
        ResourceStatus.EMBEDDING: 0.85,
        ResourceStatus.READY: 1.0,
        ResourceStatus.FAILED: 1.0
    }
    
    progress = progress_map.get(status, 0.0)
    msg = error_message if error_message else f"Document status changed to {status.value}"
    
    await event_bus.publish(GenerationEvent(
        resource_id=resource_id,
        status=status.value,
        message=msg,
        progress=progress,
        event_type=EventType.ERROR if status == ResourceStatus.FAILED else EventType.INFO,
        operation="ocr" if status == ResourceStatus.OCR else "document_processing"
    ))

async def delete_existing_chunks(session_maker: async_sessionmaker[AsyncSession], resource_id: UUID):
    """Deletes any existing chunks for a resource to allow clean reprocessing."""
    async with session_maker() as session:
        chunks_query = select(DocumentChunk).where(DocumentChunk.resource_id == resource_id)
        result = await session.execute(chunks_query)
        chunks = result.scalars().all()
        for chunk in chunks:
            await session.delete(chunk)
        await session.commit()

def _extract_sync(file_bytes: bytes, file_type: str) -> tuple[str, bool]:
    if file_type == "application/pdf":
        return extract_pdf(file_bytes)
    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_docx(file_bytes), False
    elif file_type == "text/plain":
        return extract_txt(file_bytes), False
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

def _chunk_sync(text: str) -> List[str]:
    cleaned = clean_text(text)
    chunks = chunk_text(cleaned)
    if not chunks:
        raise ValueError("Document yielded 0 chunks after cleaning.")
    return chunks

def _embed_sync(chunks: List[str]) -> List[List[float]]:
    return embedder.encode(chunks, batch_size=32)

async def process_resource_task(resource_id: UUID, session_maker: async_sessionmaker[AsyncSession]):
    """
    Main orchestrator task meant to be run in FastAPI BackgroundTasks.

    Concurrency is bounded by _doc_processing_semaphore (default 3 per worker)
    to prevent simultaneous uploads from saturating CPU (OCR/embedding) or
    exhausting storage download connections. The semaphore is acquired after
    the status guard so that a duplicate-processing check is never blocked.
    """
    logger.info(f"Resource {resource_id} processing started")
    
    try:
        # Fetch resource details and check for duplicate processing BEFORE
        # acquiring the semaphore, so we never queue a task that will be
        # immediately discarded.
        async with session_maker() as session:
            resource = await session.get(Resource, resource_id)
            if not resource:
                logger.error(f"Resource {resource_id} not found. Aborting processing.")
                return
                
            # Duplicate processing protection
            if resource.status in [ResourceStatus.PROCESSING, ResourceStatus.EXTRACTING, ResourceStatus.OCR, ResourceStatus.CHUNKING, ResourceStatus.EMBEDDING]:
                logger.warning(f"Resource {resource_id} is already in active processing state ({resource.status}). Aborting.")
                return
                
            file_path = resource.file_path
            file_type = resource.file_type

        # Acquire the bounded semaphore for the heavy CPU/IO work.
        async with _doc_processing_semaphore:
            logger.info(f"Resource {resource_id} acquired processing slot.")
            await _run_processing_pipeline(resource_id, file_path, file_type, session_maker)

    except Exception as e:
        logger.exception(f"Resource {resource_id} processing failed (outer).")
        await transition_status(session_maker, resource_id, ResourceStatus.FAILED, error_message=str(e))


async def _run_processing_pipeline(
    resource_id: UUID,
    file_path: str,
    file_type: str,
    session_maker: async_sessionmaker[AsyncSession]
):
    """Inner pipeline: download → extract → chunk → embed → store."""
    try:
        await transition_status(session_maker, resource_id, ResourceStatus.PROCESSING)
        
        # Download from Supabase
        supabase = get_supabase_service_client()
        try:
            file_bytes = download_file_from_storage(supabase, file_path)
        except Exception as e:
            raise RuntimeError(f"Storage download failed: {str(e)}")
            
        # Delete old chunks if reprocessing
        await delete_existing_chunks(session_maker, resource_id)
        
        # EXTRACT
        await transition_status(session_maker, resource_id, ResourceStatus.EXTRACTING)
        raw_text, used_ocr = await asyncio.to_thread(_extract_sync, file_bytes, file_type)
        
        if used_ocr:
            await transition_status(session_maker, resource_id, ResourceStatus.OCR)
            
        if not raw_text.strip():
            raise ValueError("No extractable text found in document.")
            
        # CHUNK
        await transition_status(session_maker, resource_id, ResourceStatus.CHUNKING)
        chunks = await asyncio.to_thread(_chunk_sync, raw_text)
        
        # EMBED
        await transition_status(session_maker, resource_id, ResourceStatus.EMBEDDING)
        embeddings = await asyncio.to_thread(_embed_sync, chunks)
        
        # STORE
        async with session_maker() as session:
            db_chunks = []
            for i, (content, embedding) in enumerate(zip(chunks, embeddings)):
                db_chunk = DocumentChunk(
                    resource_id=resource_id,
                    content=content,
                    chunk_index=i,
                    embedding=embedding
                )
                db_chunks.append(db_chunk)
            
            session.add_all(db_chunks)
            await session.commit()
            
        await transition_status(session_maker, resource_id, ResourceStatus.READY)
        logger.info(f"Resource {resource_id} marked READY. Created {len(chunks)} chunks.")
        
    except Exception as e:
        logger.exception(f"Resource {resource_id} processing failed.")
        await transition_status(session_maker, resource_id, ResourceStatus.FAILED, error_message=str(e))
