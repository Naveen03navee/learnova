from enum import Enum
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

class EventType(str, Enum):
    INFO = "INFO"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    GENERATION_STARTED = "GENERATION_STARTED"
    INITIALIZING = "INITIALIZING"
    EXTRACTING = "EXTRACTING"
    ANALYZING = "ANALYZING"
    EMBEDDING = "EMBEDDING"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    ANALYSIS_COMPLETED = "ANALYSIS_COMPLETED"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    LOADING_EMBEDDING_MODEL = "LOADING_EMBEDDING_MODEL"
    EMBEDDING_MODEL_READY = "EMBEDDING_MODEL_READY"
    RETRIEVING_KNOWLEDGE = "RETRIEVING_KNOWLEDGE"
    KNOWLEDGE_RETRIEVED = "KNOWLEDGE_RETRIEVED"
    BUILDING_CONTEXT = "BUILDING_CONTEXT"
    PROVIDER_START = "PROVIDER_START"
    PROVIDER_SUCCESS = "PROVIDER_SUCCESS"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    RATE_LIMIT = "RATE_LIMIT"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    PROVIDER_FALLBACK = "PROVIDER_FALLBACK"
    PROVIDER_RETRY = "PROVIDER_RETRY"
    FALLBACK_SUCCESS = "FALLBACK_SUCCESS"
    GENERATING_BATCH = "GENERATING_BATCH"
    VALIDATING = "VALIDATING"
    DEDUPLICATING = "DEDUPLICATING"
    REPAIRING = "REPAIRING"
    BATCH_COMPLETED = "BATCH_COMPLETED"
    GENERATION_COMPLETED = "GENERATION_COMPLETED"
    GENERATION_FAILED = "GENERATION_FAILED"
    CANCELLED = "CANCELLED"

class GenerationEvent(BaseModel):
    session_id: Optional[UUID] = None
    resource_id: Optional[UUID] = None
    event_type: EventType = EventType.INFO
    operation: str = "generation"
    status: str
    provider: Optional[str] = None
    model: Optional[str] = None
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    progress: float = 0.0
    retry_after_seconds: Optional[int] = None
    retry_at: Optional[datetime] = None
    batch: Optional[int] = None
    total_batches: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
