"""Settings API schemas."""

from pydantic import BaseModel, Field
from typing import Optional


class ApiKeyCreate(BaseModel):
    """Schema for creating/updating an API key."""

    provider: str = Field(..., description="Provider name (openai, anthropic, azure, etc.)")
    api_key: str = Field(..., description="The API key to store (will be encrypted)")


class ApiKeyTest(BaseModel):
    """Schema for testing an API key before saving."""

    provider: str = Field(..., description="Provider name")
    api_key: str = Field(..., description="The API key to test")


class ApiKeyStatus(BaseModel):
    """Schema for API key status response (without exposing actual key)."""

    provider: str = Field(..., description="Provider name")
    is_configured: bool = Field(..., description="Whether a key is configured for this provider")
    last_used_at: Optional[str] = Field(
        None, description="Last time this key was used (ISO format)"
    )
    created_at: str = Field(..., description="When the key was added (ISO format)")


class ApiKeyListResponse(BaseModel):
    """Schema for listing all API key statuses."""

    api_keys: list[ApiKeyStatus]
