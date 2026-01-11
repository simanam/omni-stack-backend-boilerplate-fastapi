"""
Contact submission model for database persistence.
Stores contact form submissions permanently for tracking and follow-up.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.base import BaseModel


class ContactSubmission(BaseModel, table=True):
    """
    Contact form submission stored in database.

    Provides permanent storage for contact inquiries,
    unlike Redis which has TTL-based expiration.
    """

    __tablename__ = "contact_submissions"

    # Core fields (always required)
    name: str = Field(max_length=100, description="Sender's name")
    email: str = Field(max_length=255, index=True, description="Sender's email")
    message: str = Field(sa_column=Column(Text), description="Message content")

    # Optional standard fields
    subject: str | None = Field(
        default=None,
        max_length=200,
        description="Message subject",
    )
    phone: str | None = Field(
        default=None,
        max_length=50,
        description="Phone number",
    )
    company: str | None = Field(
        default=None,
        max_length=200,
        description="Company name",
    )

    # Flexible custom fields (any additional data)
    extra_fields: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, default={}),
        description="Custom fields submitted with the form",
    )

    # Tracking
    reference_id: str = Field(
        unique=True,
        index=True,
        max_length=20,
        description="Public reference ID (CNT-XXXXXXXX)",
    )
    ip_address: str | None = Field(default=None, max_length=45)
    user_agent: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    source: str | None = Field(
        default=None,
        max_length=100,
        description="Form source (e.g., 'website', 'landing-page')",
    )

    # Status tracking
    status: str = Field(
        default="new",
        max_length=20,
        index=True,
        description="Status: new, read, replied, archived",
    )
    replied_at: datetime | None = Field(default=None)
    replied_by: str | None = Field(default=None)

    # Webhook tracking
    webhook_sent: bool = Field(default=False)
    webhook_sent_at: datetime | None = Field(default=None)


class ContactSubmissionCreate(SQLModel):
    """Schema for creating a contact submission."""

    name: str = Field(min_length=2, max_length=100)
    email: str = Field(max_length=255)
    message: str = Field(min_length=10, max_length=5000)
    subject: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    company: str | None = Field(default=None, max_length=200)
    extra_fields: dict[str, Any] = Field(default_factory=dict)
    source: str | None = None


class ContactSubmissionRead(SQLModel):
    """Schema for reading a contact submission."""

    id: str
    reference_id: str
    name: str
    email: str
    message: str
    subject: str | None
    phone: str | None
    company: str | None
    extra_fields: dict[str, Any]
    source: str | None
    status: str
    ip_address: str | None
    created_at: datetime
    replied_at: datetime | None
    replied_by: str | None


class ContactSubmissionUpdate(SQLModel):
    """Schema for updating a contact submission (admin use)."""

    status: str | None = Field(
        default=None,
        description="Status: new, read, replied, archived",
    )
    replied_by: str | None = None
