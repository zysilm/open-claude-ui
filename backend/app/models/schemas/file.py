"""File schemas for API validation."""

from datetime import datetime
from pydantic import BaseModel, Field

from app.models.database.file import FileType


class FileBase(BaseModel):
    """Base file schema."""

    filename: str = Field(..., min_length=1, max_length=255)
    file_path: str = Field(..., min_length=1, max_length=500)
    file_type: FileType


class FileResponse(FileBase):
    """Schema for file response."""

    id: str
    project_id: str
    size: int
    mime_type: str | None
    uploaded_at: datetime
    hash: str | None

    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    """Schema for file list response."""

    files: list[FileResponse]
    total: int
