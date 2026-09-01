from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy import func, or_, and_
from typing import Optional, List
from uuid import UUID

from app.core.database import get_db
from app.core.config import settings
from app.core.supabase import get_supabase_service_client
from app.models.knowledge import Resource, Folder, ResourceStatus
from app.models.workspace import Subject, Exam
from app.models.sharing import SharePermission
from app.schemas.knowledge import ResourceResponse, ResourceListResponse
from app.api.deps import get_current_user
from fastapi.responses import StreamingResponse
from app.services.generation.events import event_stream
from app.services.storage import upload_file_to_storage, delete_file_from_storage, generate_storage_path, generate_signed_url
from app.services.document_processor import process_resource_task
from app.core.database import engine
from app.core.authorization import require_view_access, require_edit_access, require_owner_access, get_entity_access

router = APIRouter(prefix="/api/v1/resources", tags=["Resources"])
async_session = async_sessionmaker(engine, expire_on_commit=False)

ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
    "application/msword": ".doc"
}

@router.get("", response_model=dict)
async def get_resources(
    exam_id: UUID,
    subject_id: UUID,
    folder_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    user_uuid = UUID(user_id)
    offset = (page - 1) * page_size
    
    if folder_id:
        folder = await db.get(Folder, folder_id)
        if not folder or folder.exam_id != exam_id or folder.subject_id != subject_id:
            raise HTTPException(status_code=403, detail="Invalid exam/subject/folder scope")
            
    base_query = select(Resource).join(Exam, Resource.exam_id == Exam.id).join(Subject, Resource.subject_id == Subject.id).outerjoin(
        SharePermission, and_(
            SharePermission.shared_with_id == user_uuid,
            or_(
                and_(SharePermission.entity_type == "resource", SharePermission.entity_id == Resource.id),
                and_(SharePermission.entity_type == "exam", SharePermission.entity_id == exam_id)
            )
        )
    ).where(
        Resource.exam_id == exam_id,
        Resource.subject_id == subject_id,
        or_(
            Subject.created_by == user_uuid,
            Resource.uploaded_by == user_uuid,
            SharePermission.id != None
        )
    )
    
    if folder_id:
        base_query = base_query.where(Resource.folder_id == folder_id)
    
    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated items
    items_query = base_query.order_by(Resource.created_at.desc()).offset(offset).limit(page_size)
    items_result = await db.execute(items_query)
    items = items_result.scalars().all()
    
    # Enhance with access info
    items_with_access = []
    for item in items:
        access = await get_entity_access(db, "resource", item.id, user_uuid)
        item_dict = {
            "id": item.id,
            "name": item.name,
            "file_type": item.file_type,
            "file_size": item.file_size,
            "exam_id": item.exam_id,
            "subject_id": item.subject_id,
            "folder_id": item.folder_id,
            "status": item.status,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "access": access
        }
        items_with_access.append(item_dict)
    
    return {
        "items": items_with_access,
        "total": total,
        "page": page,
        "page_size": page_size
    }

@router.post("", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
async def upload_resource(
    background_tasks: BackgroundTasks,
    exam_id: UUID = Form(...),
    subject_id: UUID = Form(...),
    folder_id: Optional[UUID] = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    user_uuid = UUID(user_id)
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty filename")
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")
        
    file_bytes = await file.read()
    file_size = len(file_bytes)
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    max_size_bytes = settings.MAX_RESOURCE_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_size_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds maximum size of {settings.MAX_RESOURCE_FILE_SIZE_MB}MB")

    exam = await db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    subject = await db.get(Subject, subject_id)
    if not subject or subject.exam_id != exam_id:
        raise HTTPException(status_code=403, detail="Invalid exam/subject scope")
        
    await require_edit_access(db, "subject", subject_id, user_uuid)
        
    if folder_id:
        folder = await db.get(Folder, folder_id)
        if not folder or folder.exam_id != exam_id or folder.subject_id != subject_id:
            raise HTTPException(status_code=403, detail="Invalid folder scope")
            
    new_resource = Resource(
        name=file.filename,
        file_path="pending",
        file_type=file.content_type,
        file_size=file_size,
        exam_id=exam_id,
        subject_id=subject_id,
        folder_id=folder_id,
        uploaded_by=user_uuid,
        status=ResourceStatus.UPLOADED
    )
    
    db.add(new_resource)
    await db.flush() 
    
    storage_path = generate_storage_path(
        str(exam_id), str(subject_id), str(folder_id) if folder_id else None, str(new_resource.id), file.filename
    )
    new_resource.file_path = storage_path
    
    try:
        supabase = get_supabase_service_client()
        upload_file_to_storage(supabase, storage_path, file_bytes, file.content_type)
        
        await db.commit()
        await db.refresh(new_resource)
        background_tasks.add_task(process_resource_task, new_resource.id, async_session)
        return new_resource
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/{resource_id}/process", response_model=dict)
async def reprocess_resource(
    resource_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await require_edit_access(db, "resource", resource_id, UUID(user_id))
    resource = await db.get(Resource, resource_id)
    
    if resource.status in [ResourceStatus.PROCESSING, ResourceStatus.EXTRACTING, ResourceStatus.OCR, ResourceStatus.CHUNKING, ResourceStatus.EMBEDDING]:
        raise HTTPException(status_code=400, detail="Resource is currently being processed")
        
    background_tasks.add_task(process_resource_task, resource.id, async_session)
    return {"detail": "Processing started in background"}

@router.get("/{resource_id}/events")
async def stream_resource_events(
    resource_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await require_view_access(db, "resource", resource_id, UUID(user_id))
    
    return StreamingResponse(
        event_stream(resource_id), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await require_owner_access(db, "resource", resource_id, UUID(user_id))
    resource = await db.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
        
    try:
        supabase = get_supabase_service_client()
        delete_file_from_storage(supabase, resource.file_path)
    except Exception:
        pass
        
    await db.delete(resource)
    await db.commit()
    return None

@router.get("/{resource_id}/download")
async def download_resource(
    resource_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await require_view_access(db, "resource", resource_id, UUID(user_id))
    resource = await db.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
        
    try:
        supabase = get_supabase_service_client()
        url = generate_signed_url(supabase, resource.file_path, expires_in_seconds=3600)
        return {"download_url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate download link: {str(e)}")
