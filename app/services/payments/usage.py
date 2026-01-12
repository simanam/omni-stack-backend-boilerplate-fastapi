"""
Usage tracking service for metered billing and analytics.

Tracks API requests, AI tokens, storage, and other billable resources.
Reports usage to Stripe for usage-based billing.

Phase 12.7: Usage-Based Billing
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import stripe

from app.core.cache import get_redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class UsageMetric(str, Enum):
    """Available usage metrics for tracking."""

    API_REQUESTS = "api_requests"
    AI_TOKENS = "ai_tokens"
    AI_REQUESTS = "ai_requests"
    STORAGE_BYTES = "storage_bytes"
    FILE_UPLOADS = "file_uploads"
    FILE_DOWNLOADS = "file_downloads"
    WEBSOCKET_MESSAGES = "websocket_messages"
    BACKGROUND_JOBS = "background_jobs"
    EMAIL_SENT = "email_sent"


@dataclass
class UsageEvent:
    """Single usage event."""

    user_id: str
    metric: UsageMetric
    quantity: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class UsageSummary:
    """Aggregated usage for a period."""

    user_id: str
    metric: UsageMetric
    total: int
    period_start: datetime
    period_end: datetime
    breakdown: dict[str, int] = field(default_factory=dict)


@dataclass
class UsageTrend:
    """Usage trend data for analytics."""

    user_id: str
    metric: UsageMetric
    current_period: int
    previous_period: int
    growth_rate: float  # Percentage
    daily_average: float
    peak_day: str | None = None
    peak_value: int = 0


class UsageTracker:
    """
    Track and aggregate usage metrics for billing and analytics.

    Usage:
        tracker = get_usage_tracker()

        # Record usage event
        await tracker.record(
            user_id="user123",
            metric=UsageMetric.API_REQUESTS,
            quantity=1,
            metadata={"endpoint": "/api/v1/users"}
        )

        # Get usage summary
        summary = await tracker.get_usage(
            user_id="user123",
            metric=UsageMetric.API_REQUESTS,
            period_start=start_of_month,
            period_end=now
        )
    """

    # Redis key patterns
    KEY_PREFIX = "usage"
    KEY_COUNTER = "{prefix}:{user_id}:{metric}:{period}"
    KEY_DAILY = "{prefix}:{user_id}:{metric}:daily:{date}"
    KEY_BREAKDOWN = "{prefix}:{user_id}:{metric}:breakdown:{period}"
    KEY_EVENTS = "{prefix}:{user_id}:events"

    # TTL for usage data (90 days)
    TTL_SECONDS = 90 * 24 * 60 * 60

    def __init__(self) -> None:
        self._redis = get_redis()
        self._in_memory_fallback: dict[str, int] = {}

    def _get_period_key(self, dt: datetime) -> str:
        """Get period key (YYYY-MM format)."""
        return dt.strftime("%Y-%m")

    def _get_date_key(self, dt: datetime) -> str:
        """Get date key (YYYY-MM-DD format)."""
        return dt.strftime("%Y-%m-%d")

    async def record(
        self,
        user_id: str,
        metric: UsageMetric | str,
        quantity: int = 1,
        metadata: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> bool:
        """
        Record a usage event.

        Args:
            user_id: User ID to track usage for
            metric: Usage metric type
            quantity: Amount to record (default 1)
            metadata: Optional metadata (endpoint, model, etc.)
            timestamp: Event timestamp (default now)

        Returns:
            True if recorded successfully
        """
        if isinstance(metric, str):
            metric = UsageMetric(metric)

        ts = timestamp or datetime.now(UTC)
        period = self._get_period_key(ts)
        date = self._get_date_key(ts)

        try:
            if self._redis:
                # Increment period counter
                counter_key = self.KEY_COUNTER.format(
                    prefix=self.KEY_PREFIX,
                    user_id=user_id,
                    metric=metric.value,
                    period=period,
                )
                await self._redis.incrby(counter_key, quantity)
                await self._redis.expire(counter_key, self.TTL_SECONDS)

                # Increment daily counter
                daily_key = self.KEY_DAILY.format(
                    prefix=self.KEY_PREFIX,
                    user_id=user_id,
                    metric=metric.value,
                    date=date,
                )
                await self._redis.incrby(daily_key, quantity)
                await self._redis.expire(daily_key, self.TTL_SECONDS)

                # Track breakdown if metadata provided
                if metadata:
                    await self._record_breakdown(user_id, metric, period, quantity, metadata)

                logger.debug(
                    f"Recorded usage: user={user_id}, metric={metric.value}, "
                    f"quantity={quantity}, period={period}"
                )
                return True
            else:
                # In-memory fallback
                key = f"{user_id}:{metric.value}:{period}"
                self._in_memory_fallback[key] = self._in_memory_fallback.get(key, 0) + quantity
                return True

        except Exception as e:
            logger.error(f"Failed to record usage: {e}")
            return False

    async def _record_breakdown(
        self,
        user_id: str,
        metric: UsageMetric,
        period: str,
        quantity: int,
        metadata: dict[str, Any],
    ) -> None:
        """Record usage breakdown by metadata fields."""
        if not self._redis:
            return

        breakdown_key = self.KEY_BREAKDOWN.format(
            prefix=self.KEY_PREFIX,
            user_id=user_id,
            metric=metric.value,
            period=period,
        )

        # Create breakdown keys from metadata
        # e.g., "endpoint:/api/v1/users" or "model:gpt-4o"
        for key, value in metadata.items():
            if isinstance(value, str):
                field_key = f"{key}:{value}"
                await self._redis.hincrby(breakdown_key, field_key, quantity)

        await self._redis.expire(breakdown_key, self.TTL_SECONDS)

    async def get_usage(
        self,
        user_id: str,
        metric: UsageMetric | str,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> UsageSummary:
        """
        Get aggregated usage for a user and metric.

        Args:
            user_id: User ID
            metric: Usage metric
            period_start: Start of period (default: start of current month)
            period_end: End of period (default: now)

        Returns:
            UsageSummary with totals and breakdown
        """
        if isinstance(metric, str):
            metric = UsageMetric(metric)

        now = datetime.now(UTC)
        period_start = period_start or now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = period_end or now

        total = 0
        breakdown: dict[str, int] = {}

        try:
            if self._redis:
                # Get all periods in range
                current = period_start
                while current <= period_end:
                    period = self._get_period_key(current)
                    counter_key = self.KEY_COUNTER.format(
                        prefix=self.KEY_PREFIX,
                        user_id=user_id,
                        metric=metric.value,
                        period=period,
                    )
                    value = await self._redis.get(counter_key)
                    if value:
                        total += int(value)

                    # Get breakdown for this period
                    breakdown_key = self.KEY_BREAKDOWN.format(
                        prefix=self.KEY_PREFIX,
                        user_id=user_id,
                        metric=metric.value,
                        period=period,
                    )
                    period_breakdown = await self._redis.hgetall(breakdown_key)
                    for k, v in period_breakdown.items():
                        breakdown[k] = breakdown.get(k, 0) + int(v)

                    # Move to next month
                    if current.month == 12:
                        current = current.replace(year=current.year + 1, month=1)
                    else:
                        current = current.replace(month=current.month + 1)
            else:
                # In-memory fallback
                period = self._get_period_key(period_start)
                key = f"{user_id}:{metric.value}:{period}"
                total = self._in_memory_fallback.get(key, 0)

        except Exception as e:
            logger.error(f"Failed to get usage: {e}")

        return UsageSummary(
            user_id=user_id,
            metric=metric,
            total=total,
            period_start=period_start,
            period_end=period_end,
            breakdown=breakdown,
        )

    async def get_daily_usage(
        self,
        user_id: str,
        metric: UsageMetric | str,
        days: int = 30,
    ) -> dict[str, int]:
        """
        Get daily usage for the last N days.

        Args:
            user_id: User ID
            metric: Usage metric
            days: Number of days to retrieve

        Returns:
            Dict mapping date strings to usage counts
        """
        if isinstance(metric, str):
            metric = UsageMetric(metric)

        result: dict[str, int] = {}
        now = datetime.now(UTC)

        try:
            if self._redis:
                for i in range(days):
                    date = now - timedelta(days=i)
                    date_str = self._get_date_key(date)
                    daily_key = self.KEY_DAILY.format(
                        prefix=self.KEY_PREFIX,
                        user_id=user_id,
                        metric=metric.value,
                        date=date_str,
                    )
                    value = await self._redis.get(daily_key)
                    result[date_str] = int(value) if value else 0

        except Exception as e:
            logger.error(f"Failed to get daily usage: {e}")

        return result

    async def get_trends(
        self,
        user_id: str,
        metric: UsageMetric | str,
    ) -> UsageTrend:
        """
        Get usage trends comparing current vs previous period.

        Args:
            user_id: User ID
            metric: Usage metric

        Returns:
            UsageTrend with growth analysis
        """
        if isinstance(metric, str):
            metric = UsageMetric(metric)

        now = datetime.now(UTC)

        # Current month
        current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_summary = await self.get_usage(user_id, metric, current_start, now)

        # Previous month
        if current_start.month == 1:
            prev_start = current_start.replace(year=current_start.year - 1, month=12)
        else:
            prev_start = current_start.replace(month=current_start.month - 1)
        prev_end = current_start - timedelta(seconds=1)
        prev_summary = await self.get_usage(user_id, metric, prev_start, prev_end)

        # Calculate growth rate
        if prev_summary.total > 0:
            growth_rate = ((current_summary.total - prev_summary.total) / prev_summary.total) * 100
        else:
            growth_rate = 100.0 if current_summary.total > 0 else 0.0

        # Get daily usage for peak detection
        daily = await self.get_daily_usage(user_id, metric, 30)
        days_in_period = (now - current_start).days + 1
        daily_average = current_summary.total / max(days_in_period, 1)

        # Find peak day
        peak_day = None
        peak_value = 0
        for date_str, value in daily.items():
            if value > peak_value:
                peak_value = value
                peak_day = date_str

        return UsageTrend(
            user_id=user_id,
            metric=metric,
            current_period=current_summary.total,
            previous_period=prev_summary.total,
            growth_rate=round(growth_rate, 2),
            daily_average=round(daily_average, 2),
            peak_day=peak_day,
            peak_value=peak_value,
        )

    async def get_all_metrics(
        self,
        user_id: str,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> dict[str, UsageSummary]:
        """
        Get usage for all metrics for a user.

        Returns:
            Dict mapping metric names to UsageSummary
        """
        result = {}
        for metric in UsageMetric:
            summary = await self.get_usage(user_id, metric, period_start, period_end)
            if summary.total > 0:
                result[metric.value] = summary
        return result

    async def get_top_users(
        self,
        metric: UsageMetric | str,
        limit: int = 10,
        period: str | None = None,
    ) -> list[tuple[str, int]]:
        """
        Get top users by usage for a metric.

        Note: This requires scanning keys which is expensive.
        Consider using a sorted set for production.

        Args:
            metric: Usage metric
            limit: Max users to return
            period: Period key (default: current month)

        Returns:
            List of (user_id, usage) tuples sorted by usage
        """
        if isinstance(metric, str):
            metric = UsageMetric(metric)

        period = period or self._get_period_key(datetime.now(UTC))
        users: dict[str, int] = {}

        try:
            if self._redis:
                # Scan for matching keys (expensive, use sorted sets in production)
                pattern = f"{self.KEY_PREFIX}:*:{metric.value}:{period}"
                async for key in self._redis.scan_iter(match=pattern):
                    # Extract user_id from key
                    parts = key.split(":")
                    if len(parts) >= 4:
                        user_id = parts[1]
                        value = await self._redis.get(key)
                        if value:
                            users[user_id] = int(value)

        except Exception as e:
            logger.error(f"Failed to get top users: {e}")

        # Sort by usage descending
        sorted_users = sorted(users.items(), key=lambda x: x[1], reverse=True)
        return sorted_users[:limit]


class StripeUsageReporter:
    """
    Report usage to Stripe for metered billing.

    Usage:
        reporter = get_stripe_usage_reporter()
        await reporter.report_usage(
            subscription_item_id="si_xxx",
            quantity=1000,
            action="increment"
        )
    """

    def __init__(self) -> None:
        if not settings.STRIPE_SECRET_KEY:
            raise ValueError("STRIPE_SECRET_KEY not configured")
        stripe.api_key = settings.STRIPE_SECRET_KEY

    async def report_usage(
        self,
        subscription_item_id: str,
        quantity: int,
        action: str = "increment",
        timestamp: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """
        Report usage to Stripe.

        Args:
            subscription_item_id: Stripe subscription item ID
            quantity: Usage quantity
            action: "increment" or "set"
            timestamp: Unix timestamp (default: now)
            idempotency_key: Idempotency key for deduplication

        Returns:
            Stripe UsageRecord object as dict
        """
        try:
            kwargs: dict[str, Any] = {
                "quantity": quantity,
                "action": action,
            }

            if timestamp:
                kwargs["timestamp"] = timestamp
            else:
                kwargs["timestamp"] = int(time.time())

            if idempotency_key:
                kwargs["idempotency_key"] = idempotency_key

            # Note: Stripe SDK v14 removed the legacy usage record API.
            # The new approach uses Stripe Billing Meters for usage-based billing.
            # For legacy metered billing, use the raw API call.
            # See: https://docs.stripe.com/billing/subscriptions/usage-based-legacy/recording-usage
            if hasattr(stripe.SubscriptionItem, "create_usage_record"):
                # Legacy Stripe SDK (< v14)
                usage_record = stripe.SubscriptionItem.create_usage_record(
                    subscription_item_id,
                    **kwargs,
                )
            else:
                # Stripe SDK v14+ - use raw API request
                # This is a temporary workaround until Billing Meters API is implemented
                usage_record = stripe.raw_request(
                    "POST",
                    f"/v1/subscription_items/{subscription_item_id}/usage_records",
                    params=kwargs,
                )

            logger.info(
                f"Reported usage to Stripe: item={subscription_item_id}, "
                f"quantity={quantity}, action={action}"
            )

            # Handle both dict (raw API) and object responses
            if isinstance(usage_record, dict):
                return {
                    "id": usage_record.get("id"),
                    "quantity": usage_record.get("quantity"),
                    "timestamp": usage_record.get("timestamp"),
                    "subscription_item": usage_record.get("subscription_item"),
                }

            return {
                "id": usage_record.id,
                "quantity": usage_record.quantity,
                "timestamp": usage_record.timestamp,
                "subscription_item": usage_record.subscription_item,
            }

        except stripe.StripeError as e:
            logger.error(f"Failed to report usage to Stripe: {e}")
            raise

    async def get_usage_summary(
        self,
        subscription_item_id: str,
    ) -> dict[str, Any]:
        """
        Get usage summary from Stripe for a subscription item.

        Args:
            subscription_item_id: Stripe subscription item ID

        Returns:
            Usage summary with total_usage and period info
        """
        try:
            # Get subscription item to find the usage summary
            item = stripe.SubscriptionItem.retrieve(
                subscription_item_id,
                expand=["price"],
            )

            # Get usage record summaries
            summaries = stripe.SubscriptionItem.list_usage_record_summaries(
                subscription_item_id,
                limit=1,
            )

            result = {
                "subscription_item_id": subscription_item_id,
                "price_id": item.price.id if item.price else None,
            }

            if summaries.data:
                summary = summaries.data[0]
                result.update(
                    {
                        "total_usage": summary.total_usage,
                        "period_start": summary.period.start,
                        "period_end": summary.period.end,
                    }
                )

            return result

        except stripe.StripeError as e:
            logger.error(f"Failed to get usage summary from Stripe: {e}")
            raise

    async def sync_usage_to_stripe(
        self,
        user_id: str,
        subscription_item_id: str,
        metric: UsageMetric,
        tracker: UsageTracker,
    ) -> dict[str, Any] | None:
        """
        Sync usage from tracker to Stripe.

        Args:
            user_id: User ID
            subscription_item_id: Stripe subscription item ID
            metric: Usage metric to sync
            tracker: UsageTracker instance

        Returns:
            Stripe usage record or None if no usage
        """
        # Get current month usage
        now = datetime.now(UTC)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        summary = await tracker.get_usage(user_id, metric, start, now)

        if summary.total == 0:
            logger.debug(f"No usage to sync for user={user_id}, metric={metric.value}")
            return None

        # Report to Stripe with "set" action to replace previous value
        idempotency_key = f"{user_id}:{metric.value}:{self._get_period_key(now)}"

        return await self.report_usage(
            subscription_item_id=subscription_item_id,
            quantity=summary.total,
            action="set",
            idempotency_key=idempotency_key,
        )

    def _get_period_key(self, dt: datetime) -> str:
        """Get period key for idempotency."""
        return dt.strftime("%Y-%m")


# Singleton instances
_usage_tracker: UsageTracker | None = None
_stripe_reporter: StripeUsageReporter | None = None


def get_usage_tracker() -> UsageTracker:
    """Get or create UsageTracker singleton."""
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = UsageTracker()
    return _usage_tracker


def get_stripe_usage_reporter() -> StripeUsageReporter:
    """Get or create StripeUsageReporter singleton."""
    global _stripe_reporter
    if _stripe_reporter is None:
        if not settings.stripe_available:
            raise ValueError("Stripe is not configured")
        _stripe_reporter = StripeUsageReporter()
    return _stripe_reporter


# Convenience functions for common usage patterns
async def track_api_request(
    user_id: str,
    endpoint: str,
    method: str = "GET",
) -> bool:
    """Track an API request."""
    tracker = get_usage_tracker()
    return await tracker.record(
        user_id=user_id,
        metric=UsageMetric.API_REQUESTS,
        quantity=1,
        metadata={"endpoint": endpoint, "method": method},
    )


async def track_ai_usage(
    user_id: str,
    provider: str,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> bool:
    """Track AI/LLM usage."""
    tracker = get_usage_tracker()
    total_tokens = prompt_tokens + completion_tokens

    # Track request count
    await tracker.record(
        user_id=user_id,
        metric=UsageMetric.AI_REQUESTS,
        quantity=1,
        metadata={"provider": provider, "model": model},
    )

    # Track tokens
    if total_tokens > 0:
        return await tracker.record(
            user_id=user_id,
            metric=UsageMetric.AI_TOKENS,
            quantity=total_tokens,
            metadata={
                "provider": provider,
                "model": model,
                "prompt_tokens": str(prompt_tokens),
                "completion_tokens": str(completion_tokens),
            },
        )

    return True


async def track_storage(
    user_id: str,
    bytes_used: int,
    operation: str = "upload",
    file_type: str | None = None,
) -> bool:
    """Track storage usage."""
    tracker = get_usage_tracker()
    metadata = {"operation": operation}
    if file_type:
        metadata["file_type"] = file_type

    # Track bytes
    await tracker.record(
        user_id=user_id,
        metric=UsageMetric.STORAGE_BYTES,
        quantity=bytes_used,
        metadata=metadata,
    )

    # Track file operation count
    if operation == "upload":
        return await tracker.record(
            user_id=user_id,
            metric=UsageMetric.FILE_UPLOADS,
            quantity=1,
            metadata=metadata,
        )
    elif operation == "download":
        return await tracker.record(
            user_id=user_id,
            metric=UsageMetric.FILE_DOWNLOADS,
            quantity=1,
            metadata=metadata,
        )

    return True
