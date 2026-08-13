from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.sharing import SharePermission, SharePermissionLevel
from app.models.workspace import Exam
from app.models.knowledge import Resource
from app.models.pattern import ExamPattern
from app.models.question import Question
from app.models.paper import QuestionPaper

async def get_entity_exam_id(db: AsyncSession, entity_type: str, entity_id: UUID) -> UUID | None:
    if entity_type == "resource":
        result = await db.execute(select(Resource.exam_id).where(Resource.id == entity_id))
    elif entity_type == "pattern":
        result = await db.execute(select(ExamPattern.exam_id).where(ExamPattern.id == entity_id))
    elif entity_type == "question":
        result = await db.execute(select(Question.exam_id).where(Question.id == entity_id))
    elif entity_type == "paper":
        result = await db.execute(select(QuestionPaper.exam_id).where(QuestionPaper.id == entity_id))
    elif entity_type == "subject":
        from app.models.workspace import Subject
        result = await db.execute(select(Subject.exam_id).where(Subject.id == entity_id))
    elif entity_type == "exam":
        return entity_id
    else:
        return None
    
    return result.scalar_one_or_none()

async def get_entity_owner_id(db: AsyncSession, entity_type: str, entity_id: UUID) -> UUID | None:
    from app.models.workspace import Subject
    if entity_type == "exam":
        result = await db.execute(select(Exam.created_by).where(Exam.id == entity_id))
    elif entity_type == "subject":
        result = await db.execute(select(Subject.created_by).where(Subject.id == entity_id))
    elif entity_type == "resource":
        result = await db.execute(
            select(Subject.created_by)
            .join(Resource, Resource.subject_id == Subject.id)
            .where(Resource.id == entity_id)
        )
    elif entity_type == "pattern":
        result = await db.execute(
            select(Subject.created_by)
            .join(ExamPattern, ExamPattern.subject_id == Subject.id)
            .where(ExamPattern.id == entity_id)
        )
    elif entity_type == "question":
        result = await db.execute(
            select(Subject.created_by)
            .join(Question, Question.subject_id == Subject.id)
            .where(Question.id == entity_id)
        )
    elif entity_type == "paper":
        result = await db.execute(
            select(Subject.created_by)
            .join(QuestionPaper, QuestionPaper.subject_id == Subject.id)
            .where(QuestionPaper.id == entity_id)
        )
    else:
        return None
    return result.scalar_one_or_none()

async def get_entity_access(db: AsyncSession, entity_type: str, entity_id: UUID, user_id: UUID) -> dict:
    """
    Returns a dictionary detailing access:
    {
        "is_owner": bool,
        "is_global": bool,
        "has_view": bool,
        "has_edit": bool
    }
    """
    exam_id = await get_entity_exam_id(db, entity_type, entity_id)
    if not exam_id:
        raise HTTPException(status_code=404, detail="Entity not found")
        
    exam = await db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Associated exam not found")
        
    is_global_exam = (exam.created_by is None)
    
    owner_id = await get_entity_owner_id(db, entity_type, entity_id)
    is_owner = (owner_id == user_id)
    
    # Global only applies to Exam visibility. Teacher data is private to the owner.
    has_view = is_owner
    if entity_type == "exam" and is_global_exam:
        has_view = True
        
    level = "NONE"
    is_shared = False
    
    if is_owner:
        level = "OWNER"

    access = {
        "is_owner": is_owner,
        "is_global": (entity_type == "exam" and is_global_exam),
        "has_view": has_view,
        "has_edit": is_owner,
        "level": level,
        "is_shared": is_shared
    }
    
    if is_owner:
        return access
        
    # Check if they have an active share
    share_result = await db.execute(
        select(SharePermission).where(
            SharePermission.entity_type == entity_type,
            SharePermission.entity_id == entity_id,
            SharePermission.shared_with_id == user_id
        )
    )
    share = share_result.scalar_one_or_none()
    
    if share:
        access["is_shared"] = True
        access["has_view"] = True
        if share.permission == SharePermissionLevel.EDIT:
            access["has_edit"] = True
            access["level"] = "EDIT"
        else:
            access["level"] = "VIEW"
            
    return access

async def require_view_access(db: AsyncSession, entity_type: str, entity_id: UUID, user_id: UUID) -> dict:
    access = await get_entity_access(db, entity_type, entity_id, user_id)
    if not access["has_view"]:
        raise HTTPException(status_code=403, detail="You do not have permission to view this content.")
    return access

async def require_edit_access(db: AsyncSession, entity_type: str, entity_id: UUID, user_id: UUID) -> dict:
    access = await get_entity_access(db, entity_type, entity_id, user_id)
    if not access["has_edit"]:
        raise HTTPException(status_code=403, detail="You do not have permission to modify this content.")
    return access

async def require_owner_access(db: AsyncSession, entity_type: str, entity_id: UUID, user_id: UUID) -> dict:
    access = await get_entity_access(db, entity_type, entity_id, user_id)
    if not access["is_owner"]:
        raise HTTPException(status_code=403, detail="Only the owner can perform this action.")
    return access
