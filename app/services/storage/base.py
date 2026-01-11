"""
Abstract storage service interface.
All storage providers must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO


@dataclass
class StorageFile:
    """Metadata for a stored file."""

    key: str
    size: int
    content_type: str | None = None
    etag: str | None = None
    last_modified: str | None = None


@dataclass
class PresignedUrl:
    """Presigned URL for upload or download."""

    url: str
    expires_in: int
    fields: dict[str, str] | None = None


class BaseStorageService(ABC):
    """Abstract base class for storage services."""

    @abstractmethod
    async def upload(
        self,
        file: BinaryIO,
        key: str,
        content_type: str | None = None,
    ) -> StorageFile:
        """
        Upload a file to storage.

        Args:
            file: File-like object to upload
            key: Storage path/key for the file
            content_type: MIME type of the file

        Returns:
            StorageFile with file metadata
        """
        pass

    @abstractmethod
    async def upload_bytes(
        self,
        data: bytes,
        key: str,
        content_type: str | None = None,
    ) -> StorageFile:
        """
        Upload bytes to storage.

        Args:
            data: Bytes to upload
            key: Storage path/key for the file
            content_type: MIME type of the file

        Returns:
            StorageFile with file metadata
        """
        pass

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """
        Download a file from storage.

        Args:
            key: Storage path/key of the file

        Returns:
            File contents as bytes
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a file from storage.

        Args:
            key: Storage path/key of the file

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            key: Storage path/key of the file

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    async def get_presigned_upload_url(
        self,
        key: str,
        content_type: str | None = None,
        expires_in: int = 3600,
    ) -> PresignedUrl:
        """
        Generate a presigned URL for client-side upload.

        Args:
            key: Storage path/key for the file
            content_type: Expected MIME type
            expires_in: URL expiration in seconds

        Returns:
            PresignedUrl with upload URL and required fields
        """
        pass

    @abstractmethod
    async def get_presigned_download_url(
        self,
        key: str,
        expires_in: int = 3600,
        filename: str | None = None,
    ) -> PresignedUrl:
        """
        Generate a presigned URL for downloading a file.

        Args:
            key: Storage path/key of the file
            expires_in: URL expiration in seconds
            filename: Suggested download filename

        Returns:
            PresignedUrl with download URL
        """
        pass

    @abstractmethod
    async def list_files(
        self,
        prefix: str = "",
        max_keys: int = 1000,
    ) -> list[StorageFile]:
        """
        List files in storage with optional prefix filter.

        Args:
            prefix: Filter files by prefix (folder path)
            max_keys: Maximum number of files to return

        Returns:
            List of StorageFile objects
        """
        pass
