"""File database model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Integer
from sqlalchemy.orm import relationship
import enum

from app.core.storage.database import Base


class FileType(str, enum.Enum):
    """File type enum."""

    INPUT = "input"
    OUTPUT = "output"


class File(Base):
    """File model."""

    __tablename__ = "files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)  # relative path in project
    file_type = Column(Enum(FileType), nullable=False)
    size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    hash = Column(String(64), nullable=True)  # SHA-256 hash for deduplication

    # Relationships
    project = relationship("Project", back_populates="files")
