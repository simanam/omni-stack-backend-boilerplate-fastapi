"""
Webhook event model for tracking and idempotency.
Stores incoming webhook events to prevent duplicate processing.
"""

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.base import BaseModel

# Type aliases
WebhookProvider = Literal["stripe", "clerk", "supabase", "custom"]
WebhookStatus = Literal["pending", "processing", "processed", "failed"]


class WebhookEvent(BaseModel, table=True):
    """
    Webhook event for tracking and idempotency.

    Stores:
    - Event metadata (provider, type)
    - Idempotency key for duplicate detection
    - Full payload for debugging/replay
    - Processing status and error info
    """

    __tablename__ = "webhook_events"

    # Event identification
    provider: str = Field(
        index=True,
        description="Webhook provider (stripe, clerk, supabase, custom)",
    )
    event_type: str = Field(
        index=True,
        description="Event type (e.g., checkout.session.completed)",
    )
    idempotency_key: str = Field(
        unique=True,
        index=True,
        description="Unique event ID for deduplication",
    )

    # Payload storage (using JSONB for Postgres, falls back to JSON for SQLite)
    payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, default={}),
        description="Full event payload",
    )

    # Processing status
    status: str = Field(
        default="pending",
        index=True,
        description="Processing status (pending, processing, processed, failed)",
    )
    error_message: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Error message if processing failed",
    )
    processed_at: datetime | None = Field(
        default=None,
        description="When the event was successfully processed",
    )
    attempts: int = Field(
        default=0,
        description="Number of processing attempts",
    )


class WebhookEventCreate(SQLModel):
    """Schema for creating a webhook event."""

    provider: str
    event_type: str
    idempotency_key: str
    payload: dict[str, Any] = Field(default_factory=dict)


class WebhookEventRead(SQLModel):
    """Schema for reading a webhook event."""

    id: str
    provider: str
    event_type: str
    idempotency_key: str
    status: str
    error_message: str | None
    processed_at: datetime | None
    attempts: int
    created_at: datetime
