import enum
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base

class PaperStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"

class QuestionPaper(Base):
    __tablename__ = "question_papers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Scope
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True)
    
    # Metadata
    title = Column(String, nullable=False)
    status = Column(Enum(PaperStatus), default=PaperStatus.DRAFT, nullable=False)
    
    # Config/Blueprint snapshot
    config = Column(JSONB, nullable=False)
    
    # Phase 11: AI Quality Check
    quality_report = Column(JSONB, nullable=True)
    quality_status = Column(String, nullable=True) # PASS, WARNING, FAIL
    quality_checked_at = Column(DateTime(timezone=True), nullable=True)
    quality_report_stale = Column(Boolean, nullable=False, default=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    exam = relationship("Exam")
    subject = relationship("Subject")
    items = relationship("QuestionPaperItem", back_populates="paper", cascade="all, delete-orphan", order_by="QuestionPaperItem.order_index")


class QuestionPaperItem(Base):
    __tablename__ = "question_paper_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("question_papers.id", ondelete="CASCADE"), nullable=False)
    
    # Provenance linking (The original Question Bank item)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="SET NULL"), nullable=True)
    
    # Immutability Snapshots (Guarantees paper contents don't silently change if Question Bank is edited)
    question_text_snapshot = Column(String, nullable=False)
    content_snapshot = Column(JSONB, nullable=False)
    marks_snapshot = Column(Integer, nullable=False)
    
    # Blueprint placement
    section_name = Column(String, nullable=False)
    order_index = Column(Integer, nullable=False)
    
    # Teacher overrides
    marks_override = Column(Integer, nullable=True)
    
    # Relationships
    paper = relationship("QuestionPaper", back_populates="items")
    original_question = relationship("Question")
