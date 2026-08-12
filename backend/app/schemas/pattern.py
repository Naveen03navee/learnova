from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.pattern import PatternStatus
from typing import Any

class ExtractedQuestion(BaseModel):
    content: str = Field(..., description="The complete question including options if MCQ, exact formatting.")
    question_type: Optional[str] = Field(None, description="e.g. MCQ, SAQ")
    section: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[str] = Field(None, description="Easy, Medium, Hard")
    marks: Optional[float] = None
    question_number: Optional[str] = None
    metadata_info: Optional[Dict[str, Any]] = None

class PatternExtractionResult(BaseModel):
    questions: List[ExtractedQuestion]

class SectionPattern(BaseModel):
    name: str
    question_count: int
    marks_per_question: int
    total_marks: int
    question_types: Dict[str, int]

class PatternAnalysisData(BaseModel):
    exam: str
    subject: str
    total_marks: int
    question_count: int
    sections: List[SectionPattern] = []
    difficulty_distribution: Dict[str, float]
    topic_weight: Dict[str, float]
    pattern_version: int = 1

class ExamPatternCreate(BaseModel):
    exam_id: UUID
    subject_id: UUID
    year: Optional[str] = None

class ExamPatternResponse(BaseModel):
    id: UUID
    exam_id: UUID
    subject_id: UUID
    file_name: str
    file_path: str
    year: Optional[str]
    status: PatternStatus
    analysis_data: Optional[PatternAnalysisData]
    extracted_example_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
