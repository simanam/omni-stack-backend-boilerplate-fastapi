"""
Usage record model for tracking billable usage.

Stores aggregated usage data for billing and analytics.
Phase 12.7: Usage-Based Billing
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.base import BaseModel

if TYPE_CHECKING:
    pass


class UsageRecord(BaseModel, table=True):
    """
    Aggregated usage record for a user and metric.

    Stores period-based usage summaries for billing and analytics.
    """

    __tablename__ = "usage_records"
    __table_args__ = (
        Index("ix_usage_records_user_metric_period", "user_id", "metric", "period_start"),
        Index("ix_usage_records_period", "period_start", "period_end"),
    )

    user_id: str = Field(
        index=True,
        description="User ID this usage belongs to",
    )
    metric: str = Field(
        index=True,
        description="Usage metric type (api_requests, ai_tokens, etc.)",
    )
    quantity: int = Field(
        default=0,
        description="Total usage quantity for the period",
    )
    period_start: datetime = Field(
        description="Start of the usage period",
    )
    period_end: datetime = Field(
        description="End of the usage period",
    )
    period_type: str = Field(
        default="monthly",
        description="Period type: daily, weekly, monthly",
    )
    breakdown: dict = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, default={}),
        description="Usage breakdown by category (endpoint, model, etc.)",
    )
    metadata_: dict = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSONB, nullable=False, default={}),
        description="Additional metadata",
    )
    reported_to_stripe: bool = Field(
        default=False,
        description="Whether this usage has been reported to Stripe",
    )
    stripe_usage_record_id: str | None = Field(
        default=None,
        description="Stripe usage record ID if reported",
    )


class UsageSummaryView(SQLModel):
    """Read-only view model for usage summaries."""

    user_id: str
    metric: str
    total_quantity: int
    period_start: datetime
    period_end: datetime
    breakdown: dict = Field(default_factory=dict)


class UsageAnalytics(SQLModel):
    """Analytics data for usage trends."""

    user_id: str
    metric: str
    current_period_total: int
    previous_period_total: int
    growth_rate_percent: float
    daily_average: float
    peak_day: str | None = None
    peak_value: int = 0
    top_categories: list[dict] = Field(default_factory=list)


class UserUsageOverview(SQLModel):
    """Overview of all usage metrics for a user."""

    user_id: str
    period_start: datetime
    period_end: datetime
    metrics: dict[str, int] = Field(default_factory=dict)
    total_cost_estimate: float | None = None
    plan_limits: dict[str, int] = Field(default_factory=dict)
    usage_percent: dict[str, float] = Field(default_factory=dict)
