"""
Storage service factory.
Returns the appropriate storage provider based on configuration.
"""

from functools import lru_cache

from app.core.config import settings
from app.services.storage.base import BaseStorageService


@lru_cache(maxsize=1)
def get_storage_service() -> BaseStorageService:
    """
    Factory that returns configured storage service.

    Provider is selected based on STORAGE_PROVIDER setting:
    - "s3": AWS S3 (requires AWS_S3_BUCKET and credentials)
    - "r2": Cloudflare R2 (requires R2_BUCKET and credentials)
    - "cloudinary": Cloudinary (requires CLOUDINARY_* credentials)
    - "local": Local filesystem (default for development)
    """
    if settings.STORAGE_PROVIDER == "s3":
        from app.services.storage.s3_provider import S3StorageService

        return S3StorageService()

    elif settings.STORAGE_PROVIDER == "r2":
        from app.services.storage.r2_provider import R2StorageService

        return R2StorageService()

    elif settings.STORAGE_PROVIDER == "cloudinary":
        from app.services.storage.cloudinary_provider import CloudinaryStorageService

        return CloudinaryStorageService()

    else:
        from app.services.storage.local_provider import LocalStorageService

        return LocalStorageService()


def clear_storage_service_cache() -> None:
    """Clear the cached storage service instance (useful for testing)."""
    get_storage_service.cache_clear()
