from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime

from typing import Optional

class SubjectCreate(BaseModel):
    exam_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    code: Optional[str] = None
    description: Optional[str] = None

class SubjectUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: Optional[str] = None
    description: Optional[str] = None

class SubjectResponse(BaseModel):
    id: UUID
    exam_id: UUID
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    created_by: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)
