"""
Base model with common fields for all database tables.
"""

import uuid
from datetime import datetime

from sqlalchemy import text
from sqlmodel import Field, SQLModel


class BaseModel(SQLModel):
    """Base model with common fields for all database tables."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        description="Unique identifier (UUID)",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
        description="Record creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": datetime.utcnow,
        },
        description="Last update timestamp",
    )


class SoftDeleteMixin(SQLModel):
    """Mixin for soft delete support."""

    deleted_at: datetime | None = Field(
        default=None,
        description="Soft delete timestamp (null = active)",
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
