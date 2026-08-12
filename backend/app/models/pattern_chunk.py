from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base

class PatternChunk(Base):
    __tablename__ = "pattern_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    pattern_id = Column(UUID(as_uuid=True), ForeignKey("exam_patterns.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Core content
    content = Column(String, nullable=False)
    
    # Detailed metadata preserving structural info
    question_type = Column(String, nullable=True)
    section = Column(String, nullable=True)
    topic = Column(String, nullable=True)
    difficulty = Column(String, nullable=True)
    marks = Column(Float, nullable=True)
    question_number = Column(String, nullable=True)
    
    # Catch-all for extra structure (e.g., options, nested parts)
    metadata_ = Column("metadata", JSONB, nullable=True)
    
    # 384 dimensions for all-MiniLM-L6-v2
    embedding = Column(Vector(384), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    pattern = relationship("ExamPattern", back_populates="chunks")
