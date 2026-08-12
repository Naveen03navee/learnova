from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models.question import Question
from app.models.workspace import Exam, Subject
from app.schemas.question import QuestionResponse, QuestionUpdateRequest, QuestionCreateRequest
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/v1/questions", tags=["questions"])

@router.get("", response_model=List[QuestionResponse])
async def list_questions(
    q: Optional[str] = None,
    exam_id: Optional[UUID] = None,
    subject_id: Optional[UUID] = None,
    difficulty: Optional[str] = None,
    question_type: Optional[str] = None,
    skip: int = 0,
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db)
):
    if q and q.strip():
        # Hybrid Search: Keyword + Semantic
        from app.services.generation.deduplicator import generate_question_embedding
        q_emb = await generate_question_embedding(q)
        
        query = select(Question)
        
        from sqlalchemy import case, func
        # Cosine distance
        cosine_dist = Question.embedding.cosine_distance(q_emb)
        # Keyword match gives a simple boost
        keyword_boost = case((Question.question_text.ilike(f"%{q}%"), 0.5), else_=0.0)
        
        # Order by combined score (lower distance is better, minus boost if keyword matches)
        query = query.order_by(cosine_dist - keyword_boost)
    else:
        query = select(Question).order_by(desc(Question.created_at))
        
    if exam_id:
        query = query.where(Question.exam_id == exam_id)
    if subject_id:
        query = query.where(Question.subject_id == subject_id)
    if difficulty:
        query = query.where(Question.difficulty == difficulty)
    if question_type:
        query = query.where(Question.question_type == question_type)
        
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    questions = result.scalars().all()
    
    return questions

@router.post("", response_model=QuestionResponse, status_code=201)
async def create_question(
    request: QuestionCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    import uuid
    from sqlalchemy import or_
    
    user_uuid = uuid.UUID(user_id)
    
    # 1. Validate Context Ownership
    exam_result = await db.execute(select(Exam).where(Exam.id == request.exam_id))
    exam = exam_result.scalar_one_or_none()
    
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if exam.created_by is not None and exam.created_by != user_uuid:
        raise HTTPException(status_code=403, detail="Not authorized to modify this context")
        
    subj_result = await db.execute(select(Subject).where(Subject.id == request.subject_id, Subject.exam_id == request.exam_id))
    if not subj_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found in this Exam")
        
    # 2. Generate Embedding
    from app.services.generation.deduplicator import generate_question_embedding
    embedding = await generate_question_embedding(request.question_text)
    
    # 3. Create Question
    question = Question(
        exam_id=request.exam_id,
        subject_id=request.subject_id,
        folder_id=request.folder_id,
        question_type=request.question_type,
        difficulty=request.difficulty,
        marks=request.marks,
        question_text=request.question_text,
        content=request.content,
        embedding=embedding
    )
    
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return question

@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(question_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question

@router.put("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: UUID, 
    update_data: QuestionUpdateRequest, 
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    import uuid
    user_uuid = uuid.UUID(user_id)
    
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
        
    # Validate Context Ownership
    exam_result = await db.execute(select(Exam).where(Exam.id == question.exam_id))
    exam = exam_result.scalar_one_or_none()
    if not exam or (exam.created_by is not None and exam.created_by != user_uuid):
        raise HTTPException(status_code=403, detail="Not authorized to modify this question")
        
    if update_data.question_text is not None and update_data.question_text != question.question_text:
        question.question_text = update_data.question_text
        from app.services.generation.deduplicator import generate_question_embedding
        question.embedding = await generate_question_embedding(question.question_text)
        
    if update_data.question_type is not None:
        question.question_type = update_data.question_type
    if update_data.difficulty is not None:
        question.difficulty = update_data.difficulty
    if update_data.marks is not None:
        question.marks = update_data.marks
    if update_data.content is not None:
        question.content = update_data.content
        
    await db.commit()
    await db.refresh(question)
    return question

@router.delete("/{question_id}", status_code=204)
async def delete_question(
    question_id: UUID, 
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    import uuid
    user_uuid = uuid.UUID(user_id)
    
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
        
    # Validate Context Ownership
    exam_result = await db.execute(select(Exam).where(Exam.id == question.exam_id))
    exam = exam_result.scalar_one_or_none()
    if not exam or (exam.created_by is not None and exam.created_by != user_uuid):
        raise HTTPException(status_code=403, detail="Not authorized to delete this question")
        
    await db.delete(question)
    await db.commit()
    return None
