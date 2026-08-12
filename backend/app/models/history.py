from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # In a single-user system this is optional, but good practice
    user_id = Column(UUID(as_uuid=True), nullable=True) 
    
    action = Column(String, nullable=False) # e.g. UPLOAD_KNOWLEDGE, PROCESS_PATTERN, GENERATE, APPROVE
    
    resource_type = Column(String, nullable=False) # e.g. Document, ExamPattern, QuestionPaper
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    
    metadata_ = Column("metadata", JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
