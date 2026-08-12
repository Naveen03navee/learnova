from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from app.core.database import get_db
from app.models.generation import GenerationSession
from app.schemas.generation import GenerationStartRequest, GenerationSessionResponse
from app.services.generation.orchestrator import process_generation_session
from app.services.generation.events import event_stream
from fastapi import Query
from sqlalchemy import desc
from sqlalchemy.orm import joinedload
from typing import Optional
from app.models.generation import GeneratedQuestion, ApprovalStatus
from app.models.question import Question
from app.schemas.question import GeneratedQuestionUpdateRequest

router = APIRouter(prefix="/api/v1/generation", tags=["generation"])

@router.post("/start", response_model=GenerationSessionResponse)
async def start_generation(
    request: GenerationStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Initializes a new GenerationSession and queues the background orchestrator.
    Returns the session details immediately so the client can subscribe to SSE.
    """
    if request.pattern_id:
        from app.models.pattern import ExamPattern, PatternStatus
        pattern_result = await db.execute(select(ExamPattern).where(ExamPattern.id == request.pattern_id))
        pattern = pattern_result.scalar_one_or_none()
        if not pattern:
            raise HTTPException(status_code=404, detail="Exam pattern not found")
        if pattern.status != PatternStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Exam pattern must be ACTIVE")
        if pattern.exam_id != request.exam_id or pattern.subject_id != request.subject_id:
            raise HTTPException(status_code=400, detail="Exam pattern does not match the active context")
            
    session = GenerationSession(
        exam_id=request.exam_id,
        subject_id=request.subject_id,
        folder_id=request.folder_id,
        pattern_id=request.pattern_id,
        topic=request.topic,
        question_type=request.question_type,
        difficulty=request.difficulty,
        marks=request.marks,
        requested_count=request.count
    )
    
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    # Set context and log
    from app.core.request_context import set_session_id
    from app.core.logging import get_logger
    set_session_id(str(session.id))
    logger = get_logger(__name__)
    logger.info("generation_started", requested_count=request.count, exam_id=str(request.exam_id))
    
    # Enqueue background processing
    background_tasks.add_task(process_generation_session, session.id)
    
    return session

@router.get("/questions", tags=["review"])
async def list_generated_questions(
    exam_id: Optional[UUID] = None,
    subject_id: Optional[UUID] = None,
    session_id: Optional[UUID] = None,
    status: ApprovalStatus = ApprovalStatus.PENDING,
    skip: int = 0,
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(GeneratedQuestion)
        .options(joinedload(GeneratedQuestion.session))
        .join(GenerationSession)
        .where(GeneratedQuestion.approval_status == status)
    )
    if exam_id:
        query = query.where(GenerationSession.exam_id == exam_id)
    if subject_id:
        query = query.where(GenerationSession.subject_id == subject_id)
    if session_id:
        query = query.where(GeneratedQuestion.session_id == session_id)
        
    query = query.order_by(desc(GeneratedQuestion.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{session_id}/stream")
async def stream_generation_progress(session_id: UUID):
    """
    Server-Sent Events (SSE) endpoint for tracking generation progress.
    """
    return StreamingResponse(event_stream(session_id), media_type="text/event-stream")

@router.get("/{session_id}", response_model=GenerationSessionResponse)
async def get_generation_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Fetches the current status of a generation session.
    """
    result = await db.execute(select(GenerationSession).where(GenerationSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.get("/questions/{question_id}", tags=["review"])
async def get_generated_question(question_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GeneratedQuestion).where(GeneratedQuestion.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question

@router.put("/questions/{question_id}", tags=["review"])
async def update_generated_question(
    question_id: UUID,
    update_data: GeneratedQuestionUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(GeneratedQuestion).where(GeneratedQuestion.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
        
    if update_data.question_text is not None:
        question.question_text = update_data.question_text
    if update_data.content is not None:
        question.content = update_data.content
        
    await db.commit()
    await db.refresh(question)
    return question

@router.post("/questions/{question_id}/approve", tags=["review"])
async def approve_generated_question(question_id: UUID, db: AsyncSession = Depends(get_db)):
    # 1. Fetch generated question and session
    result = await db.execute(
        select(GeneratedQuestion, GenerationSession)
        .join(GenerationSession, GeneratedQuestion.session_id == GenerationSession.id)
        .where(GeneratedQuestion.id == question_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Question not found")
        
    gen_question, session = row
    
    if gen_question.approval_status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Question is already {gen_question.approval_status}")
        
    # 2. Transactional Approval
    try:
        new_question = Question(
            generated_question_id=gen_question.id,
            exam_id=session.exam_id,
            subject_id=session.subject_id,
            folder_id=session.folder_id,
            question_type=session.question_type,
            difficulty=session.difficulty,
            marks=session.marks,
            question_text=gen_question.question_text,
            content=gen_question.content,
            source_citation=gen_question.content.get("source_citation"),
            source_resource_ids=gen_question.source_resource_ids,
            source_chunk_ids=gen_question.source_chunk_ids,
            embedding=gen_question.embedding
        )
        
        db.add(new_question)
        
        from datetime import datetime
        gen_question.approval_status = ApprovalStatus.APPROVED
        gen_question.approved_at = datetime.utcnow()
        
        await db.commit()
        return {"status": "success", "question_id": new_question.id}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to approve question: {str(e)}")

@router.post("/questions/{question_id}/reject", tags=["review"])
async def reject_generated_question(question_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GeneratedQuestion).where(GeneratedQuestion.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
        
    if question.approval_status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Question is already {question.approval_status}")
        
    from datetime import datetime
    question.approval_status = ApprovalStatus.REJECTED
    question.rejection_reason = "Manually rejected by teacher"
    
    await db.commit()
    return {"status": "success"}

from app.schemas.question import BulkActionRequest

@router.post("/questions/bulk-approve", tags=["review"])
async def bulk_approve_generated_questions(request: BulkActionRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(GeneratedQuestion, GenerationSession)
        .join(GenerationSession, GeneratedQuestion.session_id == GenerationSession.id)
        .where(GeneratedQuestion.id.in_(request.question_ids))
        .where(GeneratedQuestion.approval_status == ApprovalStatus.PENDING)
    )
    rows = result.all()
    
    if not rows:
        return {"status": "success", "count": 0}
        
    new_questions = []
    from datetime import datetime
    now = datetime.utcnow()
    
    try:
        for gen_question, session in rows:
            new_question = Question(
                generated_question_id=gen_question.id,
                exam_id=session.exam_id,
                subject_id=session.subject_id,
                folder_id=session.folder_id,
                question_type=session.question_type,
                difficulty=session.difficulty,
                marks=session.marks,
                question_text=gen_question.question_text,
                content=gen_question.content,
                source_citation=gen_question.content.get("source_citation"),
                source_resource_ids=gen_question.source_resource_ids,
                source_chunk_ids=gen_question.source_chunk_ids,
                embedding=gen_question.embedding
            )
            new_questions.append(new_question)
            
            gen_question.approval_status = ApprovalStatus.APPROVED
            gen_question.approved_at = now
            
        db.add_all(new_questions)
        await db.commit()
        return {"status": "success", "count": len(new_questions)}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to bulk approve questions: {str(e)}")

@router.post("/questions/bulk-reject", tags=["review"])
async def bulk_reject_generated_questions(request: BulkActionRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(GeneratedQuestion)
        .where(GeneratedQuestion.id.in_(request.question_ids))
        .where(GeneratedQuestion.approval_status == ApprovalStatus.PENDING)
    )
    questions = result.scalars().all()
    
    if not questions:
        return {"status": "success", "count": 0}
        
    try:
        for question in questions:
            question.approval_status = ApprovalStatus.REJECTED
            question.rejection_reason = "Manually rejected in bulk"
        
        await db.commit()
        return {"status": "success", "count": len(questions)}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to bulk reject questions: {str(e)}")
