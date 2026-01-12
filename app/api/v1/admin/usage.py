"""Admin usage analytics endpoints."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query

from app.core.security import require_admin
from app.services.payments.usage import (
    UsageMetric,
    get_usage_tracker,
)

router = APIRouter(
    prefix="/usage",
    tags=["Admin - Usage"],
    dependencies=[Depends(require_admin)],
)


@router.get("/metrics")
async def list_metrics() -> dict:
    """
    List all available usage metrics.

    Returns:
        List of metric names and descriptions
    """
    return {
        "metrics": [
            {
                "name": metric.value,
                "description": _get_metric_description(metric),
            }
            for metric in UsageMetric
        ]
    }


@router.get("/summary/{user_id}")
async def get_user_usage_summary(
    user_id: str,
    days: int = Query(default=30, ge=1, le=365),
) -> dict:
    """
    Get usage summary for a specific user.

    Args:
        user_id: User ID to get usage for
        days: Number of days to look back

    Returns:
        Usage summary for all metrics
    """
    tracker = get_usage_tracker()
    now = datetime.now(UTC)
    period_start = now - timedelta(days=days)

    summaries = await tracker.get_all_metrics(user_id, period_start, now)

    return {
        "user_id": user_id,
        "period_start": period_start.isoformat(),
        "period_end": now.isoformat(),
        "metrics": {
            name: {
                "total": summary.total,
                "breakdown": summary.breakdown,
            }
            for name, summary in summaries.items()
        },
    }


@router.get("/trends/{user_id}")
async def get_user_usage_trends(
    user_id: str,
    metric: str = Query(default="api_requests"),
) -> dict:
    """
    Get usage trends for a user comparing current vs previous period.

    Args:
        user_id: User ID
        metric: Metric to analyze

    Returns:
        Trend data with growth rate and daily average
    """
    tracker = get_usage_tracker()
    trend = await tracker.get_trends(user_id, metric)

    return {
        "user_id": trend.user_id,
        "metric": trend.metric.value,
        "current_period": trend.current_period,
        "previous_period": trend.previous_period,
        "growth_rate_percent": trend.growth_rate,
        "daily_average": trend.daily_average,
        "peak_day": trend.peak_day,
        "peak_value": trend.peak_value,
    }


@router.get("/daily/{user_id}")
async def get_user_daily_usage(
    user_id: str,
    metric: str = Query(default="api_requests"),
    days: int = Query(default=30, ge=1, le=90),
) -> dict:
    """
    Get daily usage breakdown for a user.

    Args:
        user_id: User ID
        metric: Metric to retrieve
        days: Number of days

    Returns:
        Daily usage counts
    """
    tracker = get_usage_tracker()
    daily = await tracker.get_daily_usage(user_id, metric, days)

    # Sort by date
    sorted_daily = dict(sorted(daily.items()))

    return {
        "user_id": user_id,
        "metric": metric,
        "days": days,
        "daily_usage": sorted_daily,
        "total": sum(daily.values()),
    }


@router.get("/top-users")
async def get_top_users_by_usage(
    metric: str = Query(default="api_requests"),
    limit: int = Query(default=10, ge=1, le=100),
) -> dict:
    """
    Get top users by usage for a metric.

    Args:
        metric: Metric to rank by
        limit: Number of users to return

    Returns:
        List of top users with usage counts
    """
    tracker = get_usage_tracker()
    top_users = await tracker.get_top_users(metric, limit)

    return {
        "metric": metric,
        "period": datetime.now(UTC).strftime("%Y-%m"),
        "users": [{"user_id": user_id, "usage": usage} for user_id, usage in top_users],
    }


@router.get("/breakdown/{user_id}")
async def get_usage_breakdown(
    user_id: str,
    metric: str = Query(default="api_requests"),
    days: int = Query(default=30, ge=1, le=365),
) -> dict:
    """
    Get detailed usage breakdown by category.

    For API requests: breakdown by endpoint
    For AI tokens: breakdown by model
    For storage: breakdown by file type

    Args:
        user_id: User ID
        metric: Metric to break down
        days: Number of days

    Returns:
        Usage breakdown by category
    """
    tracker = get_usage_tracker()
    now = datetime.now(UTC)
    period_start = now - timedelta(days=days)

    summary = await tracker.get_usage(user_id, metric, period_start, now)

    # Sort breakdown by value descending
    sorted_breakdown = dict(sorted(summary.breakdown.items(), key=lambda x: x[1], reverse=True))

    return {
        "user_id": user_id,
        "metric": metric,
        "total": summary.total,
        "period_start": period_start.isoformat(),
        "period_end": now.isoformat(),
        "breakdown": sorted_breakdown,
    }


def _get_metric_description(metric: UsageMetric) -> str:
    """Get human-readable description for a metric."""
    descriptions = {
        UsageMetric.API_REQUESTS: "Total API requests made",
        UsageMetric.AI_TOKENS: "Total AI/LLM tokens consumed",
        UsageMetric.AI_REQUESTS: "Number of AI completion requests",
        UsageMetric.STORAGE_BYTES: "Storage space used in bytes",
        UsageMetric.FILE_UPLOADS: "Number of files uploaded",
        UsageMetric.FILE_DOWNLOADS: "Number of files downloaded",
        UsageMetric.WEBSOCKET_MESSAGES: "WebSocket messages sent/received",
        UsageMetric.BACKGROUND_JOBS: "Background jobs executed",
        UsageMetric.EMAIL_SENT: "Emails sent",
    }
    return descriptions.get(metric, metric.value)
