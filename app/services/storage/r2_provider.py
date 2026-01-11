"""
Cloudflare R2 storage service implementation.
R2 uses S3-compatible API with a different endpoint.
"""

import logging
import mimetypes
from io import BytesIO
from typing import BinaryIO

import aioboto3
from botocore.config import Config

from app.core.config import settings
from app.services.storage.base import BaseStorageService, PresignedUrl, StorageFile

logger = logging.getLogger(__name__)


class R2StorageService(BaseStorageService):
    """Cloudflare R2 storage service implementation."""

    def __init__(self) -> None:
        if not settings.R2_BUCKET:
            raise ValueError("R2_BUCKET is required for R2 storage service")
        if not settings.R2_ACCOUNT_ID:
            raise ValueError("R2_ACCOUNT_ID is required for R2 storage service")

        self._session = aioboto3.Session(
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        )
        self._bucket = settings.R2_BUCKET
        self._endpoint_url = (
            f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        )
        self._config = Config(signature_version="s3v4")

    def _get_content_type(self, key: str, content_type: str | None) -> str:
        """Determine content type from key or provided value."""
        if content_type:
            return content_type
        guessed, _ = mimetypes.guess_type(key)
        return guessed or "application/octet-stream"

    async def upload(
        self,
        file: BinaryIO,
        key: str,
        content_type: str | None = None,
    ) -> StorageFile:
        """Upload a file to R2."""
        ct = self._get_content_type(key, content_type)

        async with self._session.client(
            "s3",
            endpoint_url=self._endpoint_url,
            config=self._config,
        ) as s3:
            file.seek(0)
            data = file.read()
            file.seek(0)

            await s3.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=ct,
            )

            head = await s3.head_object(Bucket=self._bucket, Key=key)

            logger.info("Uploaded file to R2: %s (%d bytes)", key, len(data))

            return StorageFile(
                key=key,
                size=head.get("ContentLength", len(data)),
                content_type=ct,
                etag=head.get("ETag", "").strip('"'),
                last_modified=str(head.get("LastModified", "")),
            )

    async def upload_bytes(
        self,
        data: bytes,
        key: str,
        content_type: str | None = None,
    ) -> StorageFile:
        """Upload bytes to R2."""
        return await self.upload(BytesIO(data), key, content_type)

    async def download(self, key: str) -> bytes:
        """Download a file from R2."""
        async with self._session.client(
            "s3",
            endpoint_url=self._endpoint_url,
            config=self._config,
        ) as s3:
            response = await s3.get_object(Bucket=self._bucket, Key=key)
            data = await response["Body"].read()
            logger.info("Downloaded file from R2: %s (%d bytes)", key, len(data))
            return data

    async def delete(self, key: str) -> bool:
        """Delete a file from R2."""
        async with self._session.client(
            "s3",
            endpoint_url=self._endpoint_url,
            config=self._config,
        ) as s3:
            try:
                await s3.delete_object(Bucket=self._bucket, Key=key)
                logger.info("Deleted file from R2: %s", key)
                return True
            except Exception:
                logger.exception("Failed to delete file from R2: %s", key)
                return False

    async def exists(self, key: str) -> bool:
        """Check if a file exists in R2."""
        async with self._session.client(
            "s3",
            endpoint_url=self._endpoint_url,
            config=self._config,
        ) as s3:
            try:
                await s3.head_object(Bucket=self._bucket, Key=key)
                return True
            except Exception:
                return False

    async def get_presigned_upload_url(
        self,
        key: str,
        content_type: str | None = None,
        expires_in: int = 3600,
    ) -> PresignedUrl:
        """Generate a presigned URL for client-side upload to R2."""
        ct = self._get_content_type(key, content_type)

        async with self._session.client(
            "s3",
            endpoint_url=self._endpoint_url,
            config=self._config,
        ) as s3:
            response = await s3.generate_presigned_post(
                Bucket=self._bucket,
                Key=key,
                Fields={"Content-Type": ct},
                Conditions=[
                    {"Content-Type": ct},
                    ["content-length-range", 1, 100 * 1024 * 1024],
                ],
                ExpiresIn=expires_in,
            )

            return PresignedUrl(
                url=response["url"],
                expires_in=expires_in,
                fields=response["fields"],
            )

    async def get_presigned_download_url(
        self,
        key: str,
        expires_in: int = 3600,
        filename: str | None = None,
    ) -> PresignedUrl:
        """Generate a presigned URL for downloading from R2."""
        params = {"Bucket": self._bucket, "Key": key}

        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'

        async with self._session.client(
            "s3",
            endpoint_url=self._endpoint_url,
            config=self._config,
        ) as s3:
            url = await s3.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expires_in,
            )

            return PresignedUrl(url=url, expires_in=expires_in)

    async def list_files(
        self,
        prefix: str = "",
        max_keys: int = 1000,
    ) -> list[StorageFile]:
        """List files in R2 with optional prefix filter."""
        files: list[StorageFile] = []

        async with self._session.client(
            "s3",
            endpoint_url=self._endpoint_url,
            config=self._config,
        ) as s3:
            paginator = s3.get_paginator("list_objects_v2")

            async for page in paginator.paginate(
                Bucket=self._bucket,
                Prefix=prefix,
                MaxKeys=max_keys,
            ):
                for obj in page.get("Contents", []):
                    files.append(
                        StorageFile(
                            key=obj["Key"],
                            size=obj["Size"],
                            etag=obj.get("ETag", "").strip('"'),
                            last_modified=str(obj.get("LastModified", "")),
                        )
                    )

                if len(files) >= max_keys:
                    break

        return files[:max_keys]
