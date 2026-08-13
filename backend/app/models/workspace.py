from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True) # Corresponds to Supabase auth.users ID
    email = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    subjects = relationship("Subject", back_populates="created_by_profile")
    exams = relationship("Exam", back_populates="created_by_profile")

class Exam(Base):
    __tablename__ = "exams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False, unique=True)
    is_college = Column(Boolean, default=False, nullable=False)
    exam_type = Column(String, nullable=True) # e.g. 'Competitive', 'College', 'Custom'
    description = Column(String, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    subjects = relationship("Subject", back_populates="exam", cascade="all, delete-orphan")
    created_by_profile = relationship("Profile", back_populates="exams")

class Subject(Base):
    __tablename__ = "subjects"
    # Tenant-aware uniqueness: exam + owner + normalized_name
    __table_args__ = (
        UniqueConstraint('exam_id', 'created_by', 'normalized_name', name='uix_exam_owner_normalized_subject'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)
    description = Column(String, nullable=True)
    normalized_name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    exam = relationship("Exam", back_populates="subjects")
    created_by_profile = relationship("Profile", back_populates="subjects")
