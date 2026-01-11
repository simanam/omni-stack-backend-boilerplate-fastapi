"""
Cloudinary storage service implementation.
https://cloudinary.com/documentation/django_integration
"""

import hashlib
import logging
import time
from io import BytesIO
from typing import Any, BinaryIO

import cloudinary
import cloudinary.api
import cloudinary.uploader

from app.core.config import settings
from app.services.storage.base import BaseStorageService, PresignedUrl, StorageFile

logger = logging.getLogger(__name__)


class CloudinaryStorageService(BaseStorageService):
    """Cloudinary storage service implementation."""

    def __init__(self) -> None:
        if not settings.CLOUDINARY_CLOUD_NAME:
            raise ValueError("CLOUDINARY_CLOUD_NAME is required")
        if not settings.CLOUDINARY_API_KEY:
            raise ValueError("CLOUDINARY_API_KEY is required")
        if not settings.CLOUDINARY_API_SECRET:
            raise ValueError("CLOUDINARY_API_SECRET is required")

        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )

    def _key_to_public_id(self, key: str) -> str:
        """Convert storage key to Cloudinary public_id."""
        public_id = key.rsplit(".", 1)[0]
        return public_id

    def _get_resource_type(self, content_type: str | None) -> str:
        """Determine Cloudinary resource type from content type."""
        if not content_type:
            return "auto"
        if content_type.startswith("image/"):
            return "image"
        if content_type.startswith("video/"):
            return "video"
        return "raw"

    async def upload(
        self,
        file: BinaryIO,
        key: str,
        content_type: str | None = None,
    ) -> StorageFile:
        """Upload a file to Cloudinary."""
        file.seek(0)
        data = file.read()
        file.seek(0)

        public_id = self._key_to_public_id(key)
        resource_type = self._get_resource_type(content_type)

        result = cloudinary.uploader.upload(
            file,
            public_id=public_id,
            resource_type=resource_type,
            overwrite=True,
        )

        logger.info("Uploaded file to Cloudinary: %s (%d bytes)", key, len(data))

        return StorageFile(
            key=key,
            size=result.get("bytes", len(data)),
            content_type=content_type,
            etag=result.get("etag", ""),
            last_modified=result.get("created_at", ""),
        )

    async def upload_bytes(
        self,
        data: bytes,
        key: str,
        content_type: str | None = None,
    ) -> StorageFile:
        """Upload bytes to Cloudinary."""
        return await self.upload(BytesIO(data), key, content_type)

    async def download(self, key: str) -> bytes:
        """Download a file from Cloudinary."""
        import httpx

        public_id = self._key_to_public_id(key)

        try:
            resource = cloudinary.api.resource(public_id)
            url = resource.get("secure_url") or resource.get("url")

            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.content

            logger.info("Downloaded file from Cloudinary: %s (%d bytes)", key, len(data))
            return data

        except Exception as e:
            logger.exception("Failed to download from Cloudinary: %s", key)
            raise FileNotFoundError(f"File not found: {key}") from e

    async def delete(self, key: str) -> bool:
        """Delete a file from Cloudinary."""
        public_id = self._key_to_public_id(key)

        try:
            result = cloudinary.uploader.destroy(public_id)
            success = result.get("result") == "ok"

            if success:
                logger.info("Deleted file from Cloudinary: %s", key)
            else:
                logger.warning("File not found in Cloudinary: %s", key)

            return success

        except Exception:
            logger.exception("Failed to delete from Cloudinary: %s", key)
            return False

    async def exists(self, key: str) -> bool:
        """Check if a file exists in Cloudinary."""
        public_id = self._key_to_public_id(key)

        try:
            cloudinary.api.resource(public_id)
            return True
        except cloudinary.api.NotFound:
            return False
        except Exception:
            return False

    def _generate_signature(self, params: dict[str, Any]) -> str:
        """Generate upload signature for Cloudinary."""
        sorted_params = sorted(params.items())
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params if v)
        to_sign = param_str + settings.CLOUDINARY_API_SECRET
        return hashlib.sha1(to_sign.encode()).hexdigest()

    async def get_presigned_upload_url(
        self,
        key: str,
        content_type: str | None = None,  # noqa: ARG002
        expires_in: int = 3600,
    ) -> PresignedUrl:
        """Generate a signed upload URL for Cloudinary."""
        public_id = self._key_to_public_id(key)
        timestamp = int(time.time())

        params = {
            "public_id": public_id,
            "timestamp": timestamp,
        }

        signature = self._generate_signature(params)

        upload_url = (
            f"https://api.cloudinary.com/v1_1/"
            f"{settings.CLOUDINARY_CLOUD_NAME}/auto/upload"
        )

        return PresignedUrl(
            url=upload_url,
            expires_in=expires_in,
            fields={
                "api_key": settings.CLOUDINARY_API_KEY,
                "timestamp": str(timestamp),
                "signature": signature,
                "public_id": public_id,
            },
        )

    async def get_presigned_download_url(
        self,
        key: str,
        expires_in: int = 3600,
        filename: str | None = None,
    ) -> PresignedUrl:
        """Generate a signed download URL for Cloudinary."""
        public_id = self._key_to_public_id(key)

        try:
            resource = cloudinary.api.resource(public_id)
            url = resource.get("secure_url") or resource.get("url")

            if filename:
                url = cloudinary.utils.cloudinary_url(
                    public_id,
                    flags="attachment:" + filename,
                )[0]

            return PresignedUrl(
                url=url,
                expires_in=expires_in,
            )

        except Exception as e:
            logger.exception("Failed to get download URL from Cloudinary: %s", key)
            raise FileNotFoundError(f"File not found: {key}") from e

    async def list_files(
        self,
        prefix: str = "",
        max_keys: int = 1000,
    ) -> list[StorageFile]:
        """List files in Cloudinary with optional prefix filter."""
        files: list[StorageFile] = []

        try:
            result = cloudinary.api.resources(
                type="upload",
                prefix=prefix if prefix else None,
                max_results=min(max_keys, 500),
            )

            for resource in result.get("resources", []):
                files.append(
                    StorageFile(
                        key=resource.get("public_id", ""),
                        size=resource.get("bytes", 0),
                        content_type=resource.get("format", ""),
                        etag=resource.get("etag", ""),
                        last_modified=resource.get("created_at", ""),
                    )
                )

        except Exception:
            logger.exception("Failed to list files from Cloudinary")

        return files[:max_keys]
