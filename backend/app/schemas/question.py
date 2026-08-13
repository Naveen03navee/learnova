from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class QuestionResponse(BaseModel):
    id: UUID
    generated_question_id: Optional[UUID]
    exam_id: UUID
    subject_id: UUID
    folder_id: Optional[UUID]
    question_type: str
    difficulty: str
    marks: int
    question_text: str
    content: Dict[str, Any]
    source_citation: Optional[str]
    source_resource_ids: Optional[List[UUID]]
    source_chunk_ids: Optional[List[UUID]]
    created_at: datetime
    updated_at: datetime
    access: Optional[dict] = None
    
    class Config:
        from_attributes = True

class QuestionUpdateRequest(BaseModel):
    question_text: Optional[str] = None
    question_type: Optional[str] = None
    difficulty: Optional[str] = None
    marks: Optional[int] = None
    content: Optional[Dict[str, Any]] = None

class QuestionCreateRequest(BaseModel):
    exam_id: UUID
    subject_id: UUID
    folder_id: Optional[UUID] = None
    question_type: str
    difficulty: str
    marks: int
    question_text: str
    content: Dict[str, Any]

class GeneratedQuestionUpdateRequest(BaseModel):
    question_text: Optional[str] = None
    question_type: Optional[str] = None
    difficulty: Optional[str] = None
    marks: Optional[int] = None
    content: Optional[Dict[str, Any]] = None

class BulkActionRequest(BaseModel):
    question_ids: List[UUID]
