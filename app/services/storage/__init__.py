"""
Storage service package.
Provides pluggable storage providers (S3, R2, Local).
"""

from app.services.storage.base import BaseStorageService, PresignedUrl, StorageFile
from app.services.storage.factory import get_storage_service

__all__ = [
    "BaseStorageService",
    "PresignedUrl",
    "StorageFile",
    "get_storage_service",
]
