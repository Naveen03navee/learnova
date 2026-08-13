from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy import delete
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.workspace import Subject, Exam
from app.models.sharing import SharePermission, SharePermissionLevel
from app.models.knowledge import Resource
from app.core.authorization import require_edit_access, get_entity_access
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
    from sqlalchemy import or_, and_, func
    import uuid
    user_uuid = uuid.UUID(user_id)

    # Verify exam exists
    exam = await db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    # Return subjects owned by the user or explicitly shared with them.
    # Do NOT return other teachers' private subjects even for global exams.
    sp = SharePermission
    query = (
        select(Subject)
        .outerjoin(sp, and_(sp.entity_type == 'subject', sp.entity_id == Subject.id, sp.shared_with_id == user_uuid))
        .where(
            Subject.exam_id == exam_id,
            or_(Subject.created_by == user_uuid, sp.id != None)
        )
        .order_by(Subject.created_at)
    )

    result = await db.execute(query)
    subjects = result.scalars().all()
    
    response = []
    for subject in subjects:
        access = await get_entity_access(db, "subject", subject.id, user_uuid)
        s_dict = subject.__dict__.copy()
        s_dict['access'] = access
        response.append(s_dict)
        
    return response


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

    # Explicitly check for existing subject for this owner to provide clear errors
    existing = await db.execute(
        select(Subject).where(
            Subject.exam_id == data.exam_id,
            Subject.created_by == user_uuid,
            Subject.normalized_name == norm_name
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"{data.name.strip()} already exists in your subjects for this exam.")

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
        
    import uuid
    user_uuid = uuid.UUID(user_id)

    # Check if authorized to modify: owner or explicitly granted EDIT share
    if subject.created_by != user_uuid:
        # check share permission
        share_result = await db.execute(
            select(SharePermission).where(
                SharePermission.entity_type == 'subject',
                SharePermission.entity_id == subject.id,
                SharePermission.shared_with_id == user_uuid
            )
        )
        share = share_result.scalar_one_or_none()
        if not share or share.permission != SharePermissionLevel.EDIT:
            raise HTTPException(status_code=403, detail="Not authorized to modify this subject")
        
    norm_name = normalize_name(data.name)
    # Ensure we don't collide with another of the user's subjects
    existing = await db.execute(
        select(Subject).where(
            Subject.exam_id == subject.exam_id,
            Subject.created_by == subject.created_by,
            Subject.normalized_name == norm_name,
            Subject.id != subject.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"{data.name.strip()} already exists in your subjects for this exam.")

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


@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    subject = await db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    import uuid
    user_uuid = uuid.UUID(user_id)

    # Owner or shared view permission required
    if subject.created_by != user_uuid:
        share_result = await db.execute(
            select(SharePermission).where(
                SharePermission.entity_type == 'subject',
                SharePermission.entity_id == subject.id,
                SharePermission.shared_with_id == user_uuid
            )
        )
        share = share_result.scalar_one_or_none()
        if not share:
            raise HTTPException(status_code=403, detail="Not authorized to view this subject")

    return subject

@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subject(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    subject = await db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    import uuid
    user_uuid = uuid.UUID(user_id)

    # Only owner or EDIT-shared users can delete
    if subject.created_by != user_uuid:
        share_result = await db.execute(
            select(SharePermission).where(
                SharePermission.entity_type == 'subject',
                SharePermission.entity_id == subject.id,
                SharePermission.shared_with_id == user_uuid
            )
        )
        share = share_result.scalar_one_or_none()
        if not share or share.permission != SharePermissionLevel.EDIT:
            raise HTTPException(status_code=403, detail="Not authorized to delete this subject")

    # In future phases, we would check for dependencies here (e.g. resources, questions)
    # and raise a 409 Conflict if they exist.

    await db.delete(subject)
    await db.commit()
    return None


@router.delete("/{subject_id}/resources", response_model=dict)
async def bulk_delete_subject_resources(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Bulk-delete all Resource rows belonging to a specific Subject.

    Authorization: Subject owner or EDIT-shared teacher.
    VIEW-only shared teachers and unrelated teachers receive 403.

    Only Resource rows for this Subject are deleted. Questions, Patterns,
    Papers, GenerationSessions, and other entities are NOT touched unless
    an existing CASCADE relationship causes it (e.g. DocumentChunks cascade
    from Resource via the existing 'all, delete-orphan' relationship).

    Returns: {"deleted": N} where N is the actual deleted row count.
    """
    import uuid as _uuid
    user_uuid = _uuid.UUID(user_id)

    # Verify the subject exists before checking access
    subject = await db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    # Require edit-level access on the subject (owner or EDIT-shared)
    await require_edit_access(db, "subject", subject_id, user_uuid)

    # Efficient bulk delete — SQLAlchemy Core DELETE with RETURNING for count
    stmt = (
        delete(Resource)
        .where(Resource.subject_id == subject_id)
        .execution_options(synchronize_session="fetch")
    )
    result = await db.execute(stmt)
    deleted_count = result.rowcount
    await db.commit()

    return {"deleted": deleted_count}
