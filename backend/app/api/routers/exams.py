from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, and_
from typing import List

from app.core.database import get_db
from app.models.workspace import Exam
from app.models.sharing import SharePermission
from app.schemas.exam import ExamResponse, ExamCreate
from app.api.deps import get_current_user
from app.core.authorization import get_entity_access

router = APIRouter(prefix="/api/v1/exams", tags=["Exams"])

@router.get("", response_model=list[dict])
async def get_exams(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    import uuid
    user_uuid = uuid.UUID(user_id)
    
    query = select(Exam).outerjoin(
        SharePermission, and_(
            SharePermission.entity_id == Exam.id,
            SharePermission.entity_type == "exam",
            SharePermission.shared_with_id == user_uuid
        )
    ).where(
        or_(
            Exam.created_by == None, 
            Exam.created_by == user_uuid,
            SharePermission.id != None
        )
    ).order_by(Exam.created_at)
    
    result = await db.execute(query)
    exams = result.scalars().all()
    
    response = []
    for exam in exams:
        access = await get_entity_access(db, "exam", exam.id, user_uuid)
        response.append({
            "id": exam.id,
            "name": exam.name,
            "exam_type": exam.exam_type,
            "description": exam.description,
            "is_college": exam.is_college,
            "created_at": exam.created_at,
            "access": access
        })
        
    return response

@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
async def create_exam(
    data: ExamCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    if not data.name or not data.name.strip():
        raise HTTPException(status_code=422, detail="Exam name cannot be empty")
        
    import uuid
    user_uuid = uuid.UUID(user_id)
    exam = Exam(
        name=data.name.strip(),
        exam_type=data.exam_type,
        description=data.description,
        is_college=data.is_college,
        created_by=user_uuid
    )
    db.add(exam)
    try:
        await db.commit()
        await db.refresh(exam)
        return exam
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"Exam '{data.name.strip()}' already exists.")
