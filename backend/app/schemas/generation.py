from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from app.models.generation import GenerationStatus, ApprovalStatus

class GenerationStartRequest(BaseModel):
    exam_id: UUID
    subject_id: UUID
    folder_id: Optional[UUID] = None
    pattern_id: Optional[UUID] = None
    topic: str = Field("", max_length=255)
    question_type: str = Field(..., description="e.g. MCQ, SAQ")
    difficulty: str = Field(..., description="e.g. easy, medium, hard")
    marks: int = Field(..., ge=1)
    count: int = Field(..., ge=1, le=50, description="Number of questions to generate")

class GenerationSessionResponse(BaseModel):
    id: UUID
    exam_id: UUID
    subject_id: UUID
    folder_id: Optional[UUID]
    pattern_id: Optional[UUID]
    topic: str
    question_type: str
    difficulty: str
    marks: int
    requested_count: int
    valid_count: int
    duplicate_count: int
    invalid_count: int
    batch_size: int
    total_batches: int
    current_batch: int
    repair_count: int
    llm_call_count: int
    provider_used: Optional[str]
    status: GenerationStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class GeneratedQuestionResponse(BaseModel):
    id: UUID
    session_id: UUID
    content: Dict[str, Any]
    question_text: str
    is_valid: bool
    is_duplicate: bool
    rejection_reason: Optional[str]
    approval_status: ApprovalStatus
    approved_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class GenerationEvent(BaseModel):
    session_id: UUID
    status: GenerationStatus
    message: str
    progress: float = 0.0 # 0.0 to 1.0
    batch: Optional[int] = None
    total_batches: Optional[int] = None
