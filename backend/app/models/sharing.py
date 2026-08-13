import enum
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base

class SharePermissionLevel(str, enum.Enum):
    VIEW = "VIEW"
    EDIT = "EDIT"
    OWNER = "OWNER"

class SharePermission(Base):
    __tablename__ = "share_permissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Entity reference (e.g., "resource", "pattern", "question", "paper")
    entity_type = Column(String, nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Ownership and Recipient
    shared_by_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    shared_with_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    
    # Permission granted
    permission = Column(Enum(SharePermissionLevel), default=SharePermissionLevel.VIEW, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('entity_type', 'entity_id', 'shared_with_id', name='uix_share_permission_unique'),
    )
