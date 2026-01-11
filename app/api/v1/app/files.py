"""
File upload and management endpoints.
Uses presigned URLs for client-side uploads to storage providers.
"""

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func
from sqlmodel import select

from app.api.deps import CurrentUser, DBSession
from app.core.exceptions import NotFoundError
from app.models.file import File
from app.schemas.common import PaginatedResponse
from app.schemas.file import (
    FileConfirmRequest,
    FileDownloadResponse,
    FileRead,
    FileUploadRequest,
    FileUploadResponse,
)
from app.services.storage import get_storage_service

router = APIRouter(tags=["Files"])


def _generate_storage_key(user_id: str, filename: str) -> str:
    """Generate a unique storage key for a file."""
    unique_id = uuid.uuid4().hex[:12]
    safe_filename = filename.replace("/", "_").replace("\\", "_")
    return f"uploads/{user_id}/{unique_id}/{safe_filename}"


@router.post(
    "/upload-url",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def get_upload_url(
    session: DBSession,
    user: CurrentUser,
    request: FileUploadRequest,
) -> FileUploadResponse:
    """
    Get a presigned URL for uploading a file.

    The client should:
    1. Call this endpoint to get an upload URL
    2. Upload the file directly to the storage provider using the URL
    3. Call POST /files/confirm to mark the upload as complete
    """
    storage = get_storage_service()

    key = _generate_storage_key(user.id, request.filename)

    file = File(
        owner_id=user.id,
        key=key,
        filename=request.filename,
        content_type=request.content_type,
        size=request.size,
        status="pending",
    )
    session.add(file)
    await session.flush()
    await session.refresh(file)

    presigned = await storage.get_presigned_upload_url(
        key=key,
        content_type=request.content_type,
        expires_in=3600,
    )

    return FileUploadResponse(
        file_id=file.id,
        upload_url=presigned.url,
        fields=presigned.fields,
        expires_in=presigned.expires_in,
    )


@router.post("/confirm", response_model=FileRead)
async def confirm_upload(
    session: DBSession,
    user: CurrentUser,
    request: FileConfirmRequest,
) -> File:
    """
    Confirm that a file upload has completed.

    Call this after successfully uploading the file to the presigned URL.
    """
    result = await session.execute(
        select(File).where(File.id == request.file_id, File.owner_id == user.id)
    )
    file = result.scalar_one_or_none()

    if not file:
        raise NotFoundError("File", str(request.file_id))

    if file.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not in pending status",
        )

    storage = get_storage_service()
    exists = await storage.exists(file.key)

    if not exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File not found in storage. Upload may have failed.",
        )

    file.status = "uploaded"
    session.add(file)
    await session.flush()
    await session.refresh(file)

    return file


@router.get("", response_model=PaginatedResponse[FileRead])
async def list_files(
    session: DBSession,
    user: CurrentUser,
    skip: int = Query(default=0, ge=0, description="Number of items to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Max items to return"),
    status_filter: str | None = Query(default=None, alias="status"),
):
    """List user's files with optional status filter."""
    query = select(File).where(File.owner_id == user.id)

    if status_filter:
        query = query.where(File.status == status_filter)

    count_result = await session.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    query = query.order_by(File.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    files = result.scalars().all()

    return PaginatedResponse(
        items=files,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{file_id}", response_model=FileRead)
async def get_file(
    session: DBSession,
    user: CurrentUser,
    file_id: uuid.UUID,
) -> File:
    """Get file metadata by ID."""
    result = await session.execute(
        select(File).where(File.id == file_id, File.owner_id == user.id)
    )
    file = result.scalar_one_or_none()

    if not file:
        raise NotFoundError("File", str(file_id))

    return file


@router.get("/{file_id}/download-url", response_model=FileDownloadResponse)
async def get_download_url(
    session: DBSession,
    user: CurrentUser,
    file_id: uuid.UUID,
) -> FileDownloadResponse:
    """Get a presigned URL for downloading a file."""
    result = await session.execute(
        select(File).where(File.id == file_id, File.owner_id == user.id)
    )
    file = result.scalar_one_or_none()

    if not file:
        raise NotFoundError("File", str(file_id))

    if file.status != "uploaded":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not available for download",
        )

    storage = get_storage_service()
    presigned = await storage.get_presigned_download_url(
        key=file.key,
        expires_in=3600,
        filename=file.filename,
    )

    return FileDownloadResponse(
        download_url=presigned.url,
        filename=file.filename,
        expires_in=presigned.expires_in,
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    session: DBSession,
    user: CurrentUser,
    file_id: uuid.UUID,
) -> None:
    """Delete a file from storage and database."""
    result = await session.execute(
        select(File).where(File.id == file_id, File.owner_id == user.id)
    )
    file = result.scalar_one_or_none()

    if not file:
        raise NotFoundError("File", str(file_id))

    storage = get_storage_service()
    await storage.delete(file.key)

    await session.delete(file)
    await session.flush()
