"""Message database model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text, JSON
from sqlalchemy.orm import relationship
import enum

from app.core.storage.database import Base


class MessageRole(str, enum.Enum):
    """Message role enum."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(Base):
    """Message model."""

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_session_id = Column(
        String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    message_metadata = Column(JSON, default=dict, nullable=False)  # attachments, etc.

    # Relationships
    chat_session = relationship("ChatSession", back_populates="messages")
    agent_actions = relationship(
        "AgentAction", back_populates="message", cascade="all, delete-orphan"
    )
