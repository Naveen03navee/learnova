from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional

class ExamCreate(BaseModel):
    name: str
    exam_type: str = "Competitive"
    description: Optional[str] = None
    is_college: bool = False

class ExamResponse(BaseModel):
    id: UUID
    name: str
    is_college: bool
    exam_type: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    access: Optional[dict] = None
    created_by: Optional[UUID] = None
    
    model_config = ConfigDict(from_attributes=True)
