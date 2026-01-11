"""
Feature flag model for dynamic feature toggling.
Supports per-user, percentage-based, and global toggles.
"""

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field, SQLModel, String

from app.models.base import BaseModel

# Type aliases
FlagType = Literal["boolean", "percentage", "user_list", "plan_based"]


class FeatureFlag(BaseModel, table=True):
    """
    Feature flag for dynamic feature toggling.

    Supports:
    - Boolean: Simple on/off toggle
    - Percentage: Enable for X% of users
    - User list: Enable for specific user IDs
    - Plan based: Enable for specific subscription plans
    """

    __tablename__ = "feature_flags"

    # Flag identification
    key: str = Field(
        unique=True,
        index=True,
        max_length=100,
        description="Unique flag key (e.g., 'new_dashboard', 'beta_ai_features')",
    )
    name: str = Field(
        max_length=255,
        description="Human-readable name",
    )
    description: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Description of what this flag controls",
    )

    # Flag configuration
    flag_type: str = Field(
        default="boolean",
        description="Flag type: boolean, percentage, user_list, plan_based",
    )
    enabled: bool = Field(
        default=False,
        index=True,
        description="Whether the flag is globally enabled",
    )

    # Type-specific configuration
    percentage: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Rollout percentage (0-100) for percentage type",
    )
    user_ids: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String), nullable=False, default=[]),
        description="List of user IDs for user_list type",
    )
    plans: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String), nullable=False, default=[]),
        description="List of plans (free, pro, enterprise) for plan_based type",
    )

    # Extra data (using extra_data instead of metadata which is reserved)
    extra_data: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, default={}),
        description="Additional data for the flag",
    )

    # Lifecycle
    expires_at: datetime | None = Field(
        default=None,
        description="Optional expiration date for the flag",
    )
    created_by: str | None = Field(
        default=None,
        description="User ID of who created the flag",
    )
    updated_by: str | None = Field(
        default=None,
        description="User ID of who last updated the flag",
    )


class FeatureFlagCreate(SQLModel):
    """Schema for creating a feature flag."""

    key: str = Field(max_length=100)
    name: str = Field(max_length=255)
    description: str | None = None
    flag_type: str = "boolean"
    enabled: bool = False
    percentage: int = Field(default=0, ge=0, le=100)
    user_ids: list[str] = Field(default_factory=list)
    plans: list[str] = Field(default_factory=list)
    extra_data: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None


class FeatureFlagUpdate(SQLModel):
    """Schema for updating a feature flag."""

    name: str | None = None
    description: str | None = None
    flag_type: str | None = None
    enabled: bool | None = None
    percentage: int | None = Field(default=None, ge=0, le=100)
    user_ids: list[str] | None = None
    plans: list[str] | None = None
    extra_data: dict[str, Any] | None = None
    expires_at: datetime | None = None


class FeatureFlagRead(SQLModel):
    """Schema for reading a feature flag."""

    id: str
    key: str
    name: str
    description: str | None
    flag_type: str
    enabled: bool
    percentage: int
    user_ids: list[str]
    plans: list[str]
    extra_data: dict[str, Any]
    expires_at: datetime | None
    created_by: str | None
    updated_by: str | None
    created_at: datetime
    updated_at: datetime


class FeatureFlagCheck(SQLModel):
    """Schema for checking if a flag is enabled for a user."""

    key: str
    enabled: bool
    reason: str  # Why the flag is enabled/disabled
