from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base

class Question(Base):
    """
    The permanent, authoritative Question Bank table for Learnova.
    Questions here have been reviewed and approved by a teacher.
    """
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Audit/History linking
    generated_question_id = Column(UUID(as_uuid=True), ForeignKey("generated_questions.id", ondelete="SET NULL"), nullable=True)
    
    # Scope
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id", ondelete="SET NULL"), nullable=True)
    
    # Question Meta
    question_type = Column(String, nullable=False) # e.g. 'MCQ', 'SAQ'
    difficulty = Column(String, nullable=False)
    marks = Column(Integer, nullable=False)
    
    # Question Data
    question_text = Column(String, nullable=False)
    content = Column(JSONB, nullable=False) # Store options, correct_answer, explanation etc.
    
    # Provenance
    source_citation = Column(String, nullable=True) # Text representation for UI display
    source_resource_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    source_chunk_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    
    # 384 dimensions for all-MiniLM-L6-v2 deduplication
    embedding = Column(Vector(384), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    generated_question = relationship("GeneratedQuestion")
    exam = relationship("Exam")
    subject = relationship("Subject")
    folder = relationship("Folder")
