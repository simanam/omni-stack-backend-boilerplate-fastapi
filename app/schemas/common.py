"""
Common schemas shared across the application.
"""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(description="Service status")
    timestamp: datetime = Field(description="Check timestamp")


class HealthReadyResponse(BaseModel):
    """Readiness check response with component status."""

    status: str = Field(description="Overall status")
    timestamp: datetime = Field(description="Check timestamp")
    components: dict[str, dict[str, str]] = Field(description="Component statuses")


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: list[T]
    total: int = Field(description="Total number of items")
    skip: int = Field(description="Number of items skipped")
    limit: int = Field(description="Maximum items per page")

    @property
    def has_more(self) -> bool:
        return self.skip + len(self.items) < self.total


class PaginationParams(BaseModel):
    """Pagination query parameters."""

    skip: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum items to return")


class ErrorDetail(BaseModel):
    """Error detail schema."""

    code: str = Field(description="Error code")
    message: str = Field(description="Error message")
    details: dict = Field(default_factory=dict, description="Additional error details")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: ErrorDetail
