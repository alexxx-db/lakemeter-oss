"""Durable AI assistant conversation state."""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class AIConversation(Base):
    """Owner-scoped AI chat session persisted in Lakebase."""

    __tablename__ = "ai_conversations"
    __table_args__ = {"schema": "lakemeter"}

    conversation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("lakemeter.users.user_id"),
        nullable=False,
        index=True,
    )
    mode = Column(String(20), default="estimate")
    state = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", foreign_keys=[owner_user_id])
