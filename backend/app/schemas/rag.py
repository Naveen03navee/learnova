from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID

class RetrievalRequest(BaseModel):
    query: str = Field(..., max_length=1000, description="The search query.")
    exam_id: UUID = Field(..., description="The ID of the exam to scope the search to.")
    subject_id: UUID = Field(..., description="The ID of the subject to scope the search to.")
    folder_id: Optional[UUID] = Field(None, description="Optional folder ID to limit search to a specific folder and its descendants.")
    top_k: int = Field(8, ge=1, le=50, description="Maximum number of results to return.")

class RetrievalResult(BaseModel):
    chunk_id: UUID
    resource_id: UUID
    resource_name: str
    folder_id: Optional[UUID]
    page_number: Optional[int]
    chunk_index: int
    content: str
    similarity: float

class RetrievalResponse(BaseModel):
    query: str
    exam_id: UUID
    subject_id: UUID
    folder_id: Optional[UUID]
    results: List[RetrievalResult]
    total_results: int
