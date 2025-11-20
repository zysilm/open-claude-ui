"""API key database model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, LargeBinary
from app.core.storage.database import Base


class ApiKey(Base):
    """API key model for encrypted storage of LLM provider API keys."""

    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String(50), nullable=False, unique=True)  # openai, anthropic, azure, etc.
    encrypted_key = Column(LargeBinary, nullable=False)  # Fernet-encrypted API key
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    # FUTURE: Add for multi-user support
    # user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    # Then change unique constraint to: UniqueConstraint('user_id', 'provider')
