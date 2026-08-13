from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr
import uuid

from app.core.database import get_db
from app.models.sharing import SharePermission, SharePermissionLevel
from app.models.workspace import Profile, Exam
from app.models.knowledge import Resource
from app.models.pattern import ExamPattern
from app.models.question import Question
from app.models.paper import QuestionPaper
from app.api.deps import get_current_user
from app.core.authorization import require_owner_access

router = APIRouter(prefix="/api/v1/shares", tags=["shares"])

class ShareRequest(BaseModel):
    entity_type: str
    entity_id: UUID
    shared_with_email: EmailStr
    permission_level: SharePermissionLevel

class ShareResponse(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    shared_with_id: UUID
    shared_with_email: str
    permission_level: SharePermissionLevel

class ShareUpdateRequest(BaseModel):
    permission_level: SharePermissionLevel

@router.post("", response_model=ShareResponse, status_code=status.HTTP_201_CREATED)
async def create_share(
    request: ShareRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    user_uuid = uuid.UUID(user_id)
    
    # Require ownership to share
    await require_owner_access(db, request.entity_type, request.entity_id, user_uuid)
    
    # Find user by email
    profile_result = await db.execute(select(Profile).where(Profile.email == request.shared_with_email))
    target_profile = profile_result.scalar_one_or_none()
    
    if not target_profile:
        raise HTTPException(status_code=404, detail="User with this email not found")
        
    if target_profile.id == user_uuid:
        raise HTTPException(status_code=400, detail="Cannot share with yourself")
        
    # Check if already shared
    existing = await db.execute(
        select(SharePermission).where(
            SharePermission.entity_type == request.entity_type,
            SharePermission.entity_id == request.entity_id,
            SharePermission.shared_with_id == target_profile.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already shared with this user")
        
    new_share = SharePermission(
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        shared_with_id=target_profile.id,
        permission_level=request.permission_level,
        granted_by_id=user_uuid
    )
    
    db.add(new_share)
    await db.commit()
    await db.refresh(new_share)
    
    return ShareResponse(
        id=new_share.id,
        entity_type=new_share.entity_type,
        entity_id=new_share.entity_id,
        shared_with_id=new_share.shared_with_id,
        shared_with_email=target_profile.email,
        permission_level=new_share.permission_level
    )

@router.get("/{entity_type}/{entity_id}", response_model=List[ShareResponse])
async def list_shares(
    entity_type: str,
    entity_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    user_uuid = uuid.UUID(user_id)
    
    # Require ownership to view who has access
    await require_owner_access(db, entity_type, entity_id, user_uuid)
    
    result = await db.execute(
        select(SharePermission, Profile.email)
        .join(Profile, SharePermission.shared_with_id == Profile.id)
        .where(
            SharePermission.entity_type == entity_type,
            SharePermission.entity_id == entity_id
        )
    )
    
    shares = []
    for share, email in result.all():
        shares.append(ShareResponse(
            id=share.id,
            entity_type=share.entity_type,
            entity_id=share.entity_id,
            shared_with_id=share.shared_with_id,
            shared_with_email=email,
            permission_level=share.permission_level
        ))
        
    return shares

@router.put("/{share_id}", response_model=ShareResponse)
async def update_share(
    share_id: UUID,
    request: ShareUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    user_uuid = uuid.UUID(user_id)
    
    result = await db.execute(select(SharePermission).where(SharePermission.id == share_id))
    share = result.scalar_one_or_none()
    
    if not share:
        raise HTTPException(status_code=404, detail="Share record not found")
        
    # Require ownership of the shared entity to modify its shares
    await require_owner_access(db, share.entity_type, share.entity_id, user_uuid)
    
    share.permission_level = request.permission_level
    await db.commit()
    await db.refresh(share)
    
    # get email
    profile_result = await db.execute(select(Profile.email).where(Profile.id == share.shared_with_id))
    email = profile_result.scalar_one()
    
    return ShareResponse(
        id=share.id,
        entity_type=share.entity_type,
        entity_id=share.entity_id,
        shared_with_id=share.shared_with_id,
        shared_with_email=email,
        permission_level=share.permission_level
    )

@router.delete("/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share(
    share_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    user_uuid = uuid.UUID(user_id)
    
    result = await db.execute(select(SharePermission).where(SharePermission.id == share_id))
    share = result.scalar_one_or_none()
    
    if not share:
        raise HTTPException(status_code=404, detail="Share record not found")
        
    # Require ownership of the shared entity to revoke its shares
    await require_owner_access(db, share.entity_type, share.entity_id, user_uuid)
    
    await db.delete(share)
    await db.commit()
    return None
