from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any, Dict
from uuid import UUID
from datetime import datetime
from app.models.paper import PaperStatus

class QuestionPaperItemSchema(BaseModel):
    id: UUID
    paper_id: UUID
    question_id: Optional[UUID]
    question_text_snapshot: str
    content_snapshot: Dict[str, Any]
    marks_snapshot: int
    section_name: str
    order_index: int
    marks_override: Optional[int]

    model_config = ConfigDict(from_attributes=True)

class QuestionPaperSchema(BaseModel):
    id: UUID
    exam_id: UUID
    subject_id: Optional[UUID] = None
    title: str
    status: PaperStatus
    config: Dict[str, Any]
    quality_report: Optional[Dict[str, Any]] = None
    quality_status: Optional[str] = None
    quality_checked_at: Optional[datetime] = None
    quality_report_stale: bool
    created_at: datetime
    updated_at: datetime
    items: List[QuestionPaperItemSchema] = []

    model_config = ConfigDict(from_attributes=True)
    
class ReorderItemRequest(BaseModel):
    item_id: UUID
    new_index: int
    
class SwapItemRequest(BaseModel):
    new_question_id: UUID

class ApprovePaperRequest(BaseModel):
    override_ai_check: bool = False
