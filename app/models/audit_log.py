"""
Audit log model for tracking admin and user actions.
Provides a complete audit trail for compliance and debugging.
"""

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.base import BaseModel

# Type aliases
AuditAction = Literal[
    # User actions
    "user.login",
    "user.logout",
    "user.created",
    "user.updated",
    "user.deleted",
    "user.activated",
    "user.deactivated",
    "user.impersonated",
    # Feature flag actions
    "feature_flag.created",
    "feature_flag.updated",
    "feature_flag.deleted",
    "feature_flag.enabled",
    "feature_flag.disabled",
    # Subscription actions
    "subscription.created",
    "subscription.updated",
    "subscription.canceled",
    # Resource actions
    "resource.created",
    "resource.updated",
    "resource.deleted",
    # Admin actions
    "admin.settings_changed",
    "admin.export_data",
    # Generic
    "custom",
]


class AuditLog(BaseModel, table=True):
    """
    Audit log for tracking all significant actions in the system.

    Captures:
    - Who did what (actor)
    - What was affected (resource)
    - When it happened (created_at)
    - What changed (details)
    - Request context (IP, user agent)
    """

    __tablename__ = "audit_logs"

    # Actor (who performed the action)
    actor_id: str | None = Field(
        default=None,
        index=True,
        description="User ID of the actor (null for system actions)",
    )
    actor_email: str | None = Field(
        default=None,
        description="Email of the actor at time of action",
    )
    actor_role: str | None = Field(
        default=None,
        description="Role of the actor at time of action",
    )

    # Impersonation tracking
    impersonator_id: str | None = Field(
        default=None,
        index=True,
        description="If impersonating, the real admin's user ID",
    )

    # Action details
    action: str = Field(
        index=True,
        description="Action type (e.g., user.updated, feature_flag.created)",
    )
    description: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Human-readable description of the action",
    )

    # Target resource
    resource_type: str | None = Field(
        default=None,
        index=True,
        description="Type of resource affected (e.g., user, project, feature_flag)",
    )
    resource_id: str | None = Field(
        default=None,
        index=True,
        description="ID of the resource affected",
    )

    # Change details (using JSONB for Postgres)
    details: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, default={}),
        description="Additional details about the action (before/after values)",
    )

    # Request context
    ip_address: str | None = Field(
        default=None,
        description="IP address of the request",
    )
    user_agent: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="User agent string",
    )
    request_id: str | None = Field(
        default=None,
        index=True,
        description="Request ID for correlation",
    )


class AuditLogCreate(SQLModel):
    """Schema for creating an audit log entry."""

    actor_id: str | None = None
    actor_email: str | None = None
    actor_role: str | None = None
    impersonator_id: str | None = None
    action: str
    description: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None


class AuditLogRead(SQLModel):
    """Schema for reading an audit log entry."""

    id: str
    actor_id: str | None
    actor_email: str | None
    actor_role: str | None
    impersonator_id: str | None
    action: str
    description: str | None
    resource_type: str | None
    resource_id: str | None
    details: dict[str, Any]
    ip_address: str | None
    request_id: str | None
    created_at: datetime


class AuditLogFilter(SQLModel):
    """Schema for filtering audit logs."""

    actor_id: str | None = None
    action: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
