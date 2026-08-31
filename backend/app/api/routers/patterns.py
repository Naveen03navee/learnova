import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_, func
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone

from app.services.storage import upload_file_to_storage, sanitize_filename, download_file_from_storage
from app.core.supabase import get_supabase_service_client

from app.core.database import get_db, AsyncSessionLocal
from app.models.pattern import ExamPattern, PatternStatus
from app.models.pattern_chunk import PatternChunk
from app.models.workspace import Exam, Subject
from app.models.sharing import SharePermission
from app.schemas.pattern import ExamPatternResponse
from app.api.deps import get_current_user
from app.core.authorization import require_view_access, require_edit_access, require_owner_access, get_entity_access
from app.services.pattern_analysis import analyze_pattern, extract_pattern_questions
from app.services.document_processor.orchestrator import _embed_sync, _extract_sync
from app.services.generation.events import event_bus, GenerationEvent
import asyncio
import logging
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["patterns"])

async def process_pattern_background(pattern_id: UUID):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ExamPattern).where(ExamPattern.id == pattern_id))
        pattern = result.scalar_one_or_none()
        if not pattern:
            return
            
        pattern.status = PatternStatus.ANALYZING
        await db.commit()
        
        sid = str(pattern_id)
        try:
            await event_bus.publish(GenerationEvent(
                resource_id=pattern_id,
                status="ANALYZING",
                event_type="INITIALIZING",
                message="Initializing pattern analysis...",
                progress=0.1
            ))
            
            supabase = get_supabase_service_client()
            
            await event_bus.publish(GenerationEvent(
                resource_id=pattern_id,
                status="ANALYZING",
                event_type="EXTRACTING",
                message="Downloading and extracting document...",
                progress=0.2
            ))
            file_bytes = await asyncio.to_thread(download_file_from_storage, supabase, pattern.file_path)
                
            file_ext = pattern.file_name.split('.')[-1].lower() if '.' in pattern.file_name else ''
            file_type = "application/pdf"
            if file_ext == "docx":
                file_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif file_ext == "txt":
                file_type = "text/plain"
                
            text_content, _ = await asyncio.to_thread(_extract_sync, file_bytes, file_type)
            
            if not text_content or not text_content.strip():
                logger.error(f"Failed to extract text from pattern {pattern.id}")
                pattern.status = PatternStatus.FAILED
                await db.commit()
                await event_bus.publish(GenerationEvent(
                    resource_id=pattern_id,
                    status="FAILED",
                    event_type="EXTRACTION_FAILED",
                    message="Failed to extract text from the document.",
                    progress=1.0
                ))
                return

            await event_bus.publish(GenerationEvent(
                resource_id=pattern_id,
                status="ANALYZING",
                event_type="ANALYZING",
                message="Analyzing exam pattern and structure using AI...",
                progress=0.4
            ))
            analysis_data = await analyze_pattern(pattern, text_content)
            
            if analysis_data and (analysis_data.question_count > 0 or analysis_data.total_marks > 0 or len(analysis_data.sections) > 0):
                pattern.analysis_data = analysis_data.model_dump()
                
                await event_bus.publish(GenerationEvent(
                    resource_id=pattern_id,
                    status="ANALYZING",
                    event_type="EXTRACTING",
                    message="Extracting representative sample questions...",
                    progress=0.6
                ))
                # Output B - Extract and embed representative questions
                questions = await extract_pattern_questions(pattern, text_content)
                if questions:
                    await event_bus.publish(GenerationEvent(
                        resource_id=pattern_id,
                        status="ANALYZING",
                        event_type="EMBEDDING",
                        message=f"Generating embeddings for {len(questions)} sample questions...",
                        progress=0.8
                    ))
                    contents = [q.content for q in questions]
                    embeddings = await asyncio.to_thread(_embed_sync, contents)
                    
                    chunks_to_add = []
                    for q, emb in zip(questions, embeddings):
                        chunk = PatternChunk(
                            pattern_id=pattern.id,
                            content=q.content,
                            question_type=q.question_type,
                            section=q.section,
                            topic=q.topic,
                            difficulty=q.difficulty,
                            marks=q.marks,
                            question_number=q.question_number,
                            metadata_=q.metadata_info,
                            embedding=emb
                        )
                        chunks_to_add.append(chunk)
                    
                    if chunks_to_add:
                        db.add_all(chunks_to_add)

                pattern.status = PatternStatus.ACTIVE
                await event_bus.publish(GenerationEvent(
                    resource_id=pattern_id,
                    status="READY",
                    event_type="ANALYSIS_COMPLETED",
                    message="Pattern analysis completed successfully.",
                    progress=1.0
                ))
            else:
                pattern.status = PatternStatus.FAILED
                if analysis_data:
                    pattern.analysis_data = analysis_data.model_dump()
                await event_bus.publish(GenerationEvent(
                    resource_id=pattern_id,
                    status="FAILED",
                    event_type="ANALYSIS_FAILED",
                    message="Failed to identify exam structure. Please upload a valid sample paper.",
                    progress=1.0
                ))
                
        except Exception as e:
            logger.error(f"Pattern background processing failed: {e}")
            pattern.status = PatternStatus.FAILED
            await event_bus.publish(GenerationEvent(
                resource_id=pattern_id,
                status="FAILED",
                event_type="ERROR",
                message=f"An unexpected error occurred: {str(e)}",
                progress=1.0
            ))
            
        await db.commit()

@router.post("/patterns/upload", response_model=ExamPatternResponse, status_code=status.HTTP_201_CREATED)
async def upload_pattern(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    exam_id: UUID = Form(...),
    subject_id: UUID = Form(...),
    year: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    user_uuid = UUID(user_id)
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
        
    file.file.seek(0, 2)
    size = file.file.tell()
    if size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    file.file.seek(0)
    
    # Validate Exam Ownership
    exam = await db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    subject = await db.get(Subject, subject_id)
    if not subject or subject.exam_id != exam_id:
        raise HTTPException(status_code=403, detail="Invalid exam/subject scope")
        
    await require_edit_access(db, "subject", subject_id, user_uuid)

    file_bytes = await file.read()
    sanitized = sanitize_filename(file.filename)
    new_pattern_id = uuid4()
    storage_path = f"patterns/{exam_id}/{subject_id}/{new_pattern_id}_{sanitized}"
    
    supabase = get_supabase_service_client()
    try:
        upload_file_to_storage(supabase, storage_path, file_bytes, file.content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file to storage: {str(e)}")

    pattern = ExamPattern(
        id=new_pattern_id,
        exam_id=exam_id,
        subject_id=subject_id,
        file_name=file.filename,
        file_path=storage_path,
        year=year,
        status=PatternStatus.UPLOADED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(pattern)
    await db.commit()
    await db.refresh(pattern)
    
    background_tasks.add_task(process_pattern_background, pattern.id)
    
    return pattern

@router.get("/patterns", response_model=list[dict])
async def list_patterns(
    exam_id: Optional[UUID] = None,
    subject_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    user_uuid = UUID(user_id)
    
    chunk_count_sq = select(
        PatternChunk.pattern_id,
        func.count(PatternChunk.id).label('extracted_example_count')
    ).group_by(PatternChunk.pattern_id).subquery()
    
    query = select(ExamPattern, chunk_count_sq.c.extracted_example_count).outerjoin(
        chunk_count_sq, ExamPattern.id == chunk_count_sq.c.pattern_id
    ).join(Exam, ExamPattern.exam_id == Exam.id).join(Subject, ExamPattern.subject_id == Subject.id).outerjoin(
        SharePermission, and_(
            SharePermission.entity_id == ExamPattern.id,
            SharePermission.entity_type == "pattern",
            SharePermission.shared_with_id == user_uuid
        )
    ).where(
        or_(
            Subject.created_by == user_uuid,
            SharePermission.id != None
        )
    )
    
    if exam_id:
        query = query.where(ExamPattern.exam_id == exam_id)
    if subject_id:
        query = query.where(ExamPattern.subject_id == subject_id)
        
    query = query.order_by(ExamPattern.created_at.desc())
    
    result = await db.execute(query)
    rows = result.all()
    
    patterns = []
    for pattern, count in rows:
        access = await get_entity_access(db, "pattern", pattern.id, user_uuid)
        
        pattern_dict = {
            "id": pattern.id,
            "exam_id": pattern.exam_id,
            "subject_id": pattern.subject_id,
            "file_name": pattern.file_name,
            "file_path": pattern.file_path,
            "year": pattern.year,
            "status": pattern.status,
            "analysis_data": pattern.analysis_data,
            "extracted_example_count": count or 0,
            "created_at": pattern.created_at,
            "updated_at": pattern.updated_at,
            "access": access
        }
        patterns.append(pattern_dict)
        
    return patterns

@router.get("/patterns/{pattern_id}/chunks")
async def get_pattern_chunks(
    pattern_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await require_view_access(db, "pattern", pattern_id, UUID(user_id))
    
    query = select(PatternChunk).where(PatternChunk.pattern_id == pattern_id).order_by(PatternChunk.created_at.desc())
    result = await db.execute(query)
    chunks = result.scalars().all()
    
    return [
        {
            "id": str(c.id),
            "content": c.content,
            "question_type": c.question_type,
            "difficulty": c.difficulty,
            "marks": c.marks
        } for c in chunks
    ]

@router.delete("/patterns/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pattern(
    pattern_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await require_edit_access(db, "pattern", pattern_id, UUID(user_id))
    
    result = await db.execute(select(ExamPattern).where(ExamPattern.id == pattern_id))
    pattern = result.scalar_one_or_none()
    
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
        
    try:
        from app.services.storage import delete_file_from_storage
        delete_file_from_storage(get_supabase_service_client(), pattern.file_path)
    except Exception as e:
        import logging
        logging.error(f"Failed to delete pattern file from storage: {e}")
        
    await db.delete(pattern)
    await db.commit()
    
    return None

@router.get("/patterns/{pattern_id}/events")
async def stream_pattern_events(
    pattern_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await require_view_access(db, "pattern", pattern_id, UUID(user_id))
    
    from app.services.generation.events import event_stream
    return StreamingResponse(
        event_stream(pattern_id), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
