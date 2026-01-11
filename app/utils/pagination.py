"""
Pagination utilities for API endpoints.

Provides helpers for paginated queries and responses.
"""

from typing import Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from sqlmodel import SQLModel

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination query parameters."""

    skip: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum items to return")

    @property
    def offset(self) -> int:
        """Alias for skip (more SQL-like naming)."""
        return self.skip


class PageParams(BaseModel):
    """Page-based pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def skip(self) -> int:
        """Calculate skip value from page number."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Alias for page_size."""
        return self.page_size


class PaginatedResult(BaseModel, Generic[T]):
    """Paginated result with metadata."""

    items: list[T]
    total: int = Field(description="Total number of items")
    skip: int = Field(description="Number of items skipped")
    limit: int = Field(description="Maximum items per page")

    @property
    def has_more(self) -> bool:
        """Check if there are more items after current page."""
        return self.skip + len(self.items) < self.total

    @property
    def page(self) -> int:
        """Current page number (1-indexed)."""
        return (self.skip // self.limit) + 1 if self.limit > 0 else 1

    @property
    def total_pages(self) -> int:
        """Total number of pages."""
        return (self.total + self.limit - 1) // self.limit if self.limit > 0 else 1


def get_pagination_params(
    skip: int = Query(default=0, ge=0, description="Number of items to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Max items to return"),
) -> PaginationParams:
    """
    FastAPI dependency for pagination parameters.

    Usage:
        @router.get("/items")
        async def list_items(pagination: PaginationParams = Depends(get_pagination_params)):
            ...
    """
    return PaginationParams(skip=skip, limit=limit)


def get_page_params(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> PageParams:
    """
    FastAPI dependency for page-based pagination.

    Usage:
        @router.get("/items")
        async def list_items(pagination: PageParams = Depends(get_page_params)):
            ...
    """
    return PageParams(page=page, page_size=page_size)


async def paginate_query[ModelType: SQLModel](
    session: AsyncSession,
    query: Select[tuple[ModelType]],
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[ModelType], int]:
    """
    Execute a paginated query and return items with total count.

    Args:
        session: Database session.
        query: SQLAlchemy Select statement.
        skip: Number of items to skip.
        limit: Maximum items to return.

    Returns:
        Tuple of (items, total_count).
    """
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # Get paginated items
    paginated_query = query.offset(skip).limit(limit)
    result = await session.execute(paginated_query)
    items = list(result.scalars().all())

    return items, total


async def paginate[ModelType: SQLModel](
    session: AsyncSession,
    query: Select[tuple[ModelType]],
    params: PaginationParams | PageParams,
) -> PaginatedResult[Any]:
    """
    Execute a paginated query and return a PaginatedResult.

    Args:
        session: Database session.
        query: SQLAlchemy Select statement.
        params: Pagination parameters.

    Returns:
        PaginatedResult with items and metadata.
    """
    skip = params.skip
    limit = params.limit if hasattr(params, "limit") else params.page_size

    items, total = await paginate_query(session, query, skip=skip, limit=limit)

    return PaginatedResult(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )
