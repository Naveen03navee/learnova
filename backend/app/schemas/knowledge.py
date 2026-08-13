from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.models.knowledge import ResourceStatus

# Folder Schemas
class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    exam_id: UUID
    subject_id: UUID
    parent_id: Optional[UUID] = None

class FolderUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

class FolderResponse(BaseModel):
    id: UUID
    name: str
    normalized_name: str
    exam_id: UUID
    subject_id: UUID
    parent_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Resource Schemas
class ResourceResponse(BaseModel):
    id: UUID
    name: str
    file_type: str
    file_size: int
    exam_id: UUID
    subject_id: UUID
    folder_id: Optional[UUID]
    uploaded_by: Optional[UUID]
    status: ResourceStatus
    created_at: datetime
    updated_at: datetime
    access: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)

class ResourceListResponse(BaseModel):
    items: List[ResourceResponse]
    total: int
    page: int
    page_size: int
