"""
Local filesystem storage service for development.
Stores files in a local directory and simulates presigned URLs.
"""

import hashlib
import logging
import mimetypes
import os
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from app.services.storage.base import BaseStorageService, PresignedUrl, StorageFile

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_DIR = Path("./storage")


class LocalStorageService(BaseStorageService):
    """Local filesystem storage service for development."""

    def __init__(self, storage_dir: Path | str | None = None) -> None:
        self._storage_dir = Path(storage_dir) if storage_dir else DEFAULT_STORAGE_DIR
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Local storage initialized at: %s", self._storage_dir.absolute())

    def _get_file_path(self, key: str) -> Path:
        """Get full path for a storage key."""
        safe_key = key.lstrip("/")
        return self._storage_dir / safe_key

    def _get_content_type(self, key: str, content_type: str | None) -> str:
        """Determine content type from key or provided value."""
        if content_type:
            return content_type
        guessed, _ = mimetypes.guess_type(key)
        return guessed or "application/octet-stream"

    def _calculate_etag(self, data: bytes) -> str:
        """Calculate MD5 etag for data."""
        return hashlib.md5(data).hexdigest()

    async def upload(
        self,
        file: BinaryIO,
        key: str,
        content_type: str | None = None,
    ) -> StorageFile:
        """Upload a file to local storage."""
        file_path = self._get_file_path(key)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file.seek(0)
        data = file.read()
        file.seek(0)

        file_path.write_bytes(data)

        logger.info("Uploaded file to local storage: %s (%d bytes)", key, len(data))

        return StorageFile(
            key=key,
            size=len(data),
            content_type=self._get_content_type(key, content_type),
            etag=self._calculate_etag(data),
            last_modified=datetime.now().isoformat(),
        )

    async def upload_bytes(
        self,
        data: bytes,
        key: str,
        content_type: str | None = None,
    ) -> StorageFile:
        """Upload bytes to local storage."""
        return await self.upload(BytesIO(data), key, content_type)

    async def download(self, key: str) -> bytes:
        """Download a file from local storage."""
        file_path = self._get_file_path(key)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {key}")

        data = file_path.read_bytes()
        logger.info("Downloaded file from local storage: %s (%d bytes)", key, len(data))
        return data

    async def delete(self, key: str) -> bool:
        """Delete a file from local storage."""
        file_path = self._get_file_path(key)

        if not file_path.exists():
            return False

        try:
            file_path.unlink()
            logger.info("Deleted file from local storage: %s", key)

            parent = file_path.parent
            while parent != self._storage_dir and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent

            return True
        except Exception:
            logger.exception("Failed to delete file from local storage: %s", key)
            return False

    async def exists(self, key: str) -> bool:
        """Check if a file exists in local storage."""
        return self._get_file_path(key).exists()

    async def get_presigned_upload_url(
        self,
        key: str,
        content_type: str | None = None,
        expires_in: int = 3600,
    ) -> PresignedUrl:
        """
        Generate a simulated presigned URL for local development.
        In local mode, this returns a placeholder URL.
        """
        token = uuid.uuid4().hex

        url = f"http://localhost:8000/api/v1/public/storage/upload/{token}"

        return PresignedUrl(
            url=url,
            expires_in=expires_in,
            fields={
                "key": key,
                "Content-Type": self._get_content_type(key, content_type),
                "token": token,
            },
        )

    async def get_presigned_download_url(
        self,
        key: str,
        expires_in: int = 3600,
        filename: str | None = None,
    ) -> PresignedUrl:
        """
        Generate a simulated presigned URL for local development.
        In local mode, this returns a placeholder URL.
        """
        token = uuid.uuid4().hex

        url = f"http://localhost:8000/api/v1/public/storage/download/{token}"

        return PresignedUrl(
            url=url,
            expires_in=expires_in,
            fields={
                "key": key,
                "token": token,
                "filename": filename or key.split("/")[-1],
            },
        )

    async def list_files(
        self,
        prefix: str = "",
        max_keys: int = 1000,
    ) -> list[StorageFile]:
        """List files in local storage with optional prefix filter."""
        files: list[StorageFile] = []
        search_dir = self._storage_dir / prefix.lstrip("/")

        if not search_dir.exists():
            return files

        for root, _, filenames in os.walk(search_dir):
            for filename in filenames:
                if len(files) >= max_keys:
                    return files

                file_path = Path(root) / filename
                relative_path = file_path.relative_to(self._storage_dir)
                key = str(relative_path)

                stat = file_path.stat()
                data = file_path.read_bytes()

                files.append(
                    StorageFile(
                        key=key,
                        size=stat.st_size,
                        content_type=self._get_content_type(key, None),
                        etag=self._calculate_etag(data),
                        last_modified=datetime.fromtimestamp(
                            stat.st_mtime
                        ).isoformat(),
                    )
                )

        return files
