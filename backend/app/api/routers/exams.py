from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from typing import List

from app.core.database import get_db
from app.models.workspace import Exam
from app.schemas.exam import ExamResponse, ExamCreate
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/v1/exams", tags=["Exams"])

@router.get("", response_model=List[ExamResponse])
async def get_exams(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    import uuid
    user_uuid = uuid.UUID(user_id)
    result = await db.execute(
        select(Exam).where(
            or_(Exam.created_by == None, Exam.created_by == user_uuid)
        ).order_by(Exam.created_at)
    )
    return result.scalars().all()

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
