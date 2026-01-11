"""
File schemas for API requests and responses.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FileUploadRequest(BaseModel):
    """Request to get a presigned upload URL."""

    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., min_length=1, max_length=100)
    size: int = Field(..., gt=0, le=100 * 1024 * 1024)  # Max 100MB


class FileUploadResponse(BaseModel):
    """Response with presigned upload URL and file ID."""

    file_id: UUID
    upload_url: str
    fields: dict[str, str] | None = None
    expires_in: int


class FileConfirmRequest(BaseModel):
    """Request to confirm upload completed."""

    file_id: UUID


class FileRead(BaseModel):
    """File metadata response."""

    id: UUID
    filename: str
    content_type: str | None
    size: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FileDownloadResponse(BaseModel):
    """Response with presigned download URL."""

    download_url: str
    filename: str
    expires_in: int
