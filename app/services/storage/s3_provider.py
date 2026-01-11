"""
AWS S3 storage service implementation.
Uses aioboto3 for async S3 operations.
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


class S3StorageService(BaseStorageService):
    """AWS S3 storage service implementation."""

    def __init__(self) -> None:
        if not settings.AWS_S3_BUCKET:
            raise ValueError("AWS_S3_BUCKET is required for S3 storage service")

        self._session = aioboto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        self._bucket = settings.AWS_S3_BUCKET
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
        """Upload a file to S3."""
        ct = self._get_content_type(key, content_type)

        async with self._session.client("s3", config=self._config) as s3:
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

            logger.info("Uploaded file to S3: %s (%d bytes)", key, len(data))

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
        """Upload bytes to S3."""
        return await self.upload(BytesIO(data), key, content_type)

    async def download(self, key: str) -> bytes:
        """Download a file from S3."""
        async with self._session.client("s3", config=self._config) as s3:
            response = await s3.get_object(Bucket=self._bucket, Key=key)
            data = await response["Body"].read()
            logger.info("Downloaded file from S3: %s (%d bytes)", key, len(data))
            return data

    async def delete(self, key: str) -> bool:
        """Delete a file from S3."""
        async with self._session.client("s3", config=self._config) as s3:
            try:
                await s3.delete_object(Bucket=self._bucket, Key=key)
                logger.info("Deleted file from S3: %s", key)
                return True
            except Exception:
                logger.exception("Failed to delete file from S3: %s", key)
                return False

    async def exists(self, key: str) -> bool:
        """Check if a file exists in S3."""
        async with self._session.client("s3", config=self._config) as s3:
            try:
                await s3.head_object(Bucket=self._bucket, Key=key)
                return True
            except s3.exceptions.ClientError as e:
                if e.response.get("Error", {}).get("Code") == "404":
                    return False
                raise
            except Exception:
                return False

    async def get_presigned_upload_url(
        self,
        key: str,
        content_type: str | None = None,
        expires_in: int = 3600,
    ) -> PresignedUrl:
        """Generate a presigned URL for client-side upload to S3."""
        ct = self._get_content_type(key, content_type)

        async with self._session.client("s3", config=self._config) as s3:
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
        """Generate a presigned URL for downloading from S3."""
        params = {"Bucket": self._bucket, "Key": key}

        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'

        async with self._session.client("s3", config=self._config) as s3:
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
        """List files in S3 with optional prefix filter."""
        files: list[StorageFile] = []

        async with self._session.client("s3", config=self._config) as s3:
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
