import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone

from app.services.storage import upload_file_to_storage, sanitize_filename
from app.core.supabase import get_supabase_service_client

from app.core.database import get_db
from app.models.pattern import ExamPattern, PatternStatus
from app.models.pattern_chunk import PatternChunk
from app.models.workspace import Exam, Subject
from app.schemas.pattern import ExamPatternResponse
from app.services.pattern_analysis import analyze_pattern, extract_pattern_questions
from app.services.document_processor.orchestrator import _embed_sync
import asyncio

router = APIRouter(prefix="/api/v1", tags=["patterns"])

async def process_pattern_background(pattern_id: UUID, db: AsyncSession):
    # Re-fetch the pattern in the background context
    result = await db.execute(select(ExamPattern).where(ExamPattern.id == pattern_id))
    pattern = result.scalar_one_or_none()
    if not pattern:
        return
        
    pattern.status = PatternStatus.ANALYZING
    await db.commit()
    
    analysis_data = await analyze_pattern(pattern)
    
    if analysis_data:
        pattern.analysis_data = analysis_data.model_dump()
        
        # Output B - Extract and embed representative questions
        questions = await extract_pattern_questions(pattern)
        if questions:
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
    else:
        pattern.status = PatternStatus.FAILED
        
    await db.commit()

@router.post("/patterns/upload", response_model=ExamPatternResponse, status_code=status.HTTP_201_CREATED)
async def upload_pattern(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    exam_id: UUID = Form(...),
    subject_id: UUID = Form(...),
    year: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    # 1. Validate file exists and is not empty
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
        
    file.file.seek(0, 2)
    size = file.file.tell()
    if size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    file.file.seek(0)
    
    # 2. Validate Exam and Subject
    exam_result = await db.execute(select(Exam).where(Exam.id == exam_id))
    if not exam_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Exam not found")
        
    subject_result = await db.execute(select(Subject).where(Subject.id == subject_id, Subject.exam_id == exam_id))
    if not subject_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Subject not found or does not belong to Exam")

    # 3. Save File to Supabase Storage
    file_bytes = await file.read()
    sanitized = sanitize_filename(file.filename)
    # Using uuid4() for the pattern ID here so we can include it in the path
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
    
    # 5. Queue Background Analysis
    background_tasks.add_task(process_pattern_background, pattern.id, db)
    
    return pattern

@router.get("/patterns", response_model=List[ExamPatternResponse])
async def list_patterns(
    exam_id: Optional[UUID] = None,
    subject_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import func
    from app.models.pattern_chunk import PatternChunk
    
    chunk_count_sq = select(
        PatternChunk.pattern_id,
        func.count(PatternChunk.id).label('extracted_example_count')
    ).group_by(PatternChunk.pattern_id).subquery()
    
    query = select(ExamPattern, chunk_count_sq.c.extracted_example_count).outerjoin(
        chunk_count_sq, ExamPattern.id == chunk_count_sq.c.pattern_id
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
        pattern.extracted_example_count = count or 0
        patterns.append(pattern)
        
    return patterns

@router.get("/patterns/{pattern_id}/chunks")
async def get_pattern_chunks(
    pattern_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    from app.models.pattern_chunk import PatternChunk
    
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
    db: AsyncSession = Depends(get_db)
):
    from app.services.storage import delete_file_from_storage
    from app.core.supabase import get_supabase_service_client
    
    query = select(ExamPattern).where(ExamPattern.id == pattern_id)
    result = await db.execute(query)
    pattern = result.scalar_one_or_none()
    
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
        
    # Delete from storage
    try:
        delete_file_from_storage(get_supabase_service_client(), pattern.file_path)
    except Exception as e:
        import logging
        logging.error(f"Failed to delete pattern file from storage: {e}")
        
    await db.delete(pattern)
    await db.commit()
    
    return None

