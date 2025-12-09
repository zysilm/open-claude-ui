"""Project database model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.orm import relationship

from app.core.storage.database import Base


class Project(Base):
    """Project model."""

    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    agent_config = relationship(
        "AgentConfiguration", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    chat_sessions = relationship(
        "ChatSession", back_populates="project", cascade="all, delete-orphan"
    )
    files = relationship("File", back_populates="project", cascade="all, delete-orphan")
