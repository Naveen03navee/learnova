from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models.knowledge import Folder, Resource
from app.models.workspace import Subject
from app.schemas.knowledge import FolderCreate, FolderUpdate, FolderResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/v1/folders", tags=["Folders"])

@router.get("", response_model=List[FolderResponse])
async def get_folders(
    exam_id: UUID,
    subject_id: UUID,
    parent_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    query = select(Folder).where(
        Folder.exam_id == exam_id,
        Folder.subject_id == subject_id,
        Folder.parent_id == parent_id
    ).order_by(Folder.name)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder_in: FolderCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    # 1. Verify the subject belongs to the given exam
    subject = await db.get(Subject, folder_in.subject_id)
    if not subject or subject.exam_id != folder_in.exam_id:
        raise HTTPException(status_code=400, detail="Invalid exam/subject combination")

    # 2. If parent_id is provided, verify it exists and belongs to the same exam/subject
    if folder_in.parent_id:
        parent = await db.get(Folder, folder_in.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent folder not found")
        if parent.exam_id != folder_in.exam_id or parent.subject_id != folder_in.subject_id:
            raise HTTPException(status_code=403, detail="Parent folder belongs to a different exam or subject")

    normalized_name = folder_in.name.strip().lower()
    
    new_folder = Folder(
        name=folder_in.name.strip(),
        normalized_name=normalized_name,
        exam_id=folder_in.exam_id,
        subject_id=folder_in.subject_id,
        parent_id=folder_in.parent_id
    )
    
    db.add(new_folder)
    try:
        await db.commit()
        await db.refresh(new_folder)
        return new_folder
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="A folder with this name already exists in the current location")

@router.get("/{folder_id}/path", response_model=List[FolderResponse])
async def get_folder_path(
    folder_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Returns the breadcrumb path from the root down to the given folder.
    Also validates that all folders belong to the same exam/subject.
    """
    current_folder = await db.get(Folder, folder_id)
    if not current_folder:
        raise HTTPException(status_code=404, detail="Folder not found")
        
    path = []
    # Maximum depth safeguard
    depth = 0
    while current_folder and depth < 20:
        path.insert(0, current_folder)
        if current_folder.parent_id:
            parent = await db.get(Folder, current_folder.parent_id)
            if not parent:
                # Broken hierarchy
                break
            # Validate context hasn't been maliciously altered
            if parent.exam_id != current_folder.exam_id or parent.subject_id != current_folder.subject_id:
                raise HTTPException(status_code=403, detail="Corrupted folder hierarchy context")
            current_folder = parent
        else:
            break
        depth += 1
        
    return path

@router.put("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: UUID,
    folder_in: FolderUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    folder = await db.get(Folder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
        
    normalized_name = folder_in.name.strip().lower()
    folder.name = folder_in.name.strip()
    folder.normalized_name = normalized_name
    
    try:
        await db.commit()
        await db.refresh(folder)
        return folder
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="A folder with this name already exists in the current location")

@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    folder = await db.get(Folder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
        
    # Check if folder contains child folders
    children_result = await db.execute(select(Folder.id).where(Folder.parent_id == folder_id).limit(1))
    if children_result.scalar():
        raise HTTPException(status_code=400, detail="Cannot delete folder: it contains subfolders")
        
    # Check if folder contains resources
    resources_result = await db.execute(select(Resource.id).where(Resource.folder_id == folder_id).limit(1))
    if resources_result.scalar():
        raise HTTPException(status_code=400, detail="Cannot delete folder: it contains resources")
        
    await db.delete(folder)
    await db.commit()
    return None
