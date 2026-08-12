import enum
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base

class PatternStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    ANALYZING = "ANALYZING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"

class ExamPattern(Base):
    __tablename__ = "exam_patterns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    year = Column(String, nullable=True)
    
    status = Column(Enum(PatternStatus), default=PatternStatus.UPLOADED, nullable=False)
    
    # Structural blueprint extracted by AI (schema-validated)
    analysis_data = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    exam = relationship("Exam")
    subject = relationship("Subject")
    chunks = relationship("PatternChunk", back_populates="pattern", cascade="all, delete-orphan")
