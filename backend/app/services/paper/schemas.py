from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from uuid import UUID

class PaperSectionBlueprint(BaseModel):
    name: str = Field(..., description="Name of the section, e.g., 'Section A: Multiple Choice'")
    question_type: str = Field(..., description="e.g., 'MCQ', 'SAQ'")
    difficulty: str = Field(..., description="e.g., 'Easy', 'Medium', 'Hard'")
    count: int = Field(..., ge=1, description="Number of questions in this section")
    marks_per_question: int = Field(..., ge=1, description="Marks per question")

class PaperBlueprint(BaseModel):
    title: str = Field(..., description="Title of the paper")
    exam_id: UUID
    subject_id: Optional[UUID] = None
    sections: List[PaperSectionBlueprint] = Field(..., min_length=1)
