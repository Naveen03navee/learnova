import enum
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base

class GenerationStatus(str, enum.Enum):
    PENDING = "PENDING"
    RETRIEVING = "RETRIEVING"
    GENERATING = "GENERATING"
    VALIDATING = "VALIDATING"
    DEDUPLICATING = "DEDUPLICATING"
    SAVING = "SAVING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"

class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class GenerationSession(Base):
    __tablename__ = "generation_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Scope
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id", ondelete="SET NULL"), nullable=True)
    pattern_id = Column(UUID(as_uuid=True), ForeignKey("exam_patterns.id", ondelete="SET NULL"), nullable=True)
    
    # Generation parameters
    topic = Column(String, nullable=False)
    question_type = Column(String, nullable=False) # e.g. 'MCQ', 'SAQ'
    difficulty = Column(String, nullable=False)
    marks = Column(Integer, nullable=False)
    
    # Counters
    requested_count = Column(Integer, nullable=False, default=1)
    valid_count = Column(Integer, nullable=False, default=0)
    duplicate_count = Column(Integer, nullable=False, default=0)
    invalid_count = Column(Integer, nullable=False, default=0)
    
    # Phase 7 Batch Tracking
    batch_size = Column(Integer, nullable=False, default=1)
    total_batches = Column(Integer, nullable=False, default=1)
    current_batch = Column(Integer, nullable=False, default=0)
    repair_count = Column(Integer, nullable=False, default=0)
    llm_call_count = Column(Integer, nullable=False, default=0)
    
    # Meta
    provider_used = Column(String, nullable=True)
    status = Column(Enum(GenerationStatus), default=GenerationStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    questions = relationship("GeneratedQuestion", back_populates="session", cascade="all, delete-orphan")
    pattern = relationship("ExamPattern")


class GeneratedQuestion(Base):
    __tablename__ = "generated_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("generation_sessions.id", ondelete="CASCADE"), nullable=False)
    
    # Question Data
    content = Column(JSONB, nullable=False) # Store options, correct_answer, explanation etc.
    question_text = Column(String, nullable=False) # Plain text for embedding generation
    
    # Provenance
    from sqlalchemy.dialects.postgresql import ARRAY
    source_resource_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    source_chunk_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    
    # 384 dimensions for all-MiniLM-L6-v2 deduplication
    embedding = Column(Vector(384), nullable=True)
    
    # Generation Validation State
    is_valid = Column(Boolean, nullable=False, default=True)
    # SQLAlchemy Boolean vs Postgres Boolean: We should use sqlalchemy Boolean
    
    # Meta state
    rejection_reason = Column(String, nullable=True)
    
    # Phase 8 Boundary
    approval_status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    session = relationship("GenerationSession", back_populates="questions")
