from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.workspace import Subject, Exam
from app.schemas.subject import SubjectCreate, SubjectUpdate, SubjectResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/v1/subjects", tags=["Subjects"])

def normalize_name(name: str) -> str:
    return name.strip().lower()

@router.get("", response_model=List[SubjectResponse])
async def get_subjects(
    exam_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    from sqlalchemy import or_
    import uuid
    user_uuid = uuid.UUID(user_id)
    result = await db.execute(
        select(Subject).where(
            Subject.exam_id == exam_id,
            or_(
                Subject.created_by == None,   # noqa: E711 — global/seeded subjects
                Subject.created_by == user_uuid
            )
        ).order_by(Subject.created_at)
    )
    return result.scalars().all()


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    data: SubjectCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    # Verify exam exists and is authorized
    exam = await db.get(Exam, data.exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    if exam.created_by is not None and str(exam.created_by) != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to add a subject to this exam")
        
    norm_name = normalize_name(data.name)
    import uuid
    user_uuid = uuid.UUID(user_id)
    subject = Subject(
        exam_id=data.exam_id,
        created_by=user_uuid,
        name=data.name.strip(),
        code=data.code,
        description=data.description,
        normalized_name=norm_name
    )
    
    db.add(subject)
    try:
        await db.commit()
        await db.refresh(subject)
        return subject
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"Subject '{data.name.strip()}' already exists for this exam.")

@router.put("/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: UUID,
    data: SubjectUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    subject = await db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
        
    # Check if authorized to modify
    if str(subject.created_by) != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this subject")
        
    norm_name = normalize_name(data.name)
    subject.name = data.name.strip()
    if data.code is not None:
        subject.code = data.code
    if data.description is not None:
        subject.description = data.description
    subject.normalized_name = norm_name
    
    try:
        await db.commit()
        await db.refresh(subject)
        return subject
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"Subject '{data.name.strip()}' already exists for this exam.")

@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subject(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    subject = await db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
        
    # In future phases, we would check for dependencies here (e.g. resources, questions)
    # and raise a 409 Conflict if they exist.
    
    await db.delete(subject)
    await db.commit()
    return None
