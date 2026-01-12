"""User usage endpoints for viewing own usage data."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser
from app.services.payments.usage import (
    UsageMetric,
    get_usage_tracker,
)

router = APIRouter(prefix="/usage", tags=["Usage"])


@router.get("/summary")
async def get_my_usage_summary(
    user: CurrentUser,
    days: int = Query(default=30, ge=1, le=365),
) -> dict:
    """
    Get your usage summary for all metrics.

    Args:
        days: Number of days to look back

    Returns:
        Usage summary for all tracked metrics
    """
    tracker = get_usage_tracker()
    now = datetime.now(UTC)
    period_start = now - timedelta(days=days)

    summaries = await tracker.get_all_metrics(user.id, period_start, now)

    return {
        "user_id": user.id,
        "period_start": period_start.isoformat(),
        "period_end": now.isoformat(),
        "days": days,
        "metrics": {
            name: {
                "total": summary.total,
                "breakdown": summary.breakdown,
            }
            for name, summary in summaries.items()
        },
    }


@router.get("/current-period")
async def get_current_period_usage(
    user: CurrentUser,
) -> dict:
    """
    Get usage for the current billing period (current month).

    Returns:
        Usage counts for all metrics this month
    """
    tracker = get_usage_tracker()
    now = datetime.now(UTC)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    summaries = await tracker.get_all_metrics(user.id, period_start, now)

    # Calculate days remaining in period
    if period_start.month == 12:
        next_month = period_start.replace(year=period_start.year + 1, month=1)
    else:
        next_month = period_start.replace(month=period_start.month + 1)
    days_remaining = (next_month - now).days

    return {
        "user_id": user.id,
        "period_start": period_start.isoformat(),
        "period_end": next_month.isoformat(),
        "days_remaining": days_remaining,
        "usage": {name: summary.total for name, summary in summaries.items()},
    }


@router.get("/trends")
async def get_my_usage_trends(
    user: CurrentUser,
    metric: str = Query(default="api_requests"),
) -> dict:
    """
    Get your usage trends comparing this period to last period.

    Args:
        metric: Metric to analyze (api_requests, ai_tokens, etc.)

    Returns:
        Trend data with growth rate and averages
    """
    tracker = get_usage_tracker()

    try:
        metric_enum = UsageMetric(metric)
    except ValueError:
        return {"error": f"Invalid metric: {metric}"}

    trend = await tracker.get_trends(user.id, metric_enum)

    return {
        "metric": trend.metric.value,
        "current_period_total": trend.current_period,
        "previous_period_total": trend.previous_period,
        "growth_rate_percent": trend.growth_rate,
        "daily_average": trend.daily_average,
        "peak_day": trend.peak_day,
        "peak_value": trend.peak_value,
    }


@router.get("/daily")
async def get_my_daily_usage(
    user: CurrentUser,
    metric: str = Query(default="api_requests"),
    days: int = Query(default=30, ge=1, le=90),
) -> dict:
    """
    Get your daily usage for a specific metric.

    Args:
        metric: Metric to retrieve
        days: Number of days to look back

    Returns:
        Daily usage breakdown
    """
    tracker = get_usage_tracker()

    try:
        metric_enum = UsageMetric(metric)
    except ValueError:
        return {"error": f"Invalid metric: {metric}"}

    daily = await tracker.get_daily_usage(user.id, metric_enum, days)

    # Sort by date
    sorted_daily = dict(sorted(daily.items()))

    return {
        "metric": metric,
        "days": days,
        "daily_usage": sorted_daily,
        "total": sum(daily.values()),
        "average": round(sum(daily.values()) / max(len(daily), 1), 2),
    }


@router.get("/breakdown")
async def get_my_usage_breakdown(
    user: CurrentUser,
    metric: str = Query(default="api_requests"),
    days: int = Query(default=30, ge=1, le=365),
) -> dict:
    """
    Get detailed breakdown of your usage.

    For API requests: which endpoints you're calling most
    For AI tokens: which models you're using
    For storage: what file types you're uploading

    Args:
        metric: Metric to break down
        days: Number of days

    Returns:
        Usage breakdown by category
    """
    tracker = get_usage_tracker()
    now = datetime.now(UTC)
    period_start = now - timedelta(days=days)

    try:
        metric_enum = UsageMetric(metric)
    except ValueError:
        return {"error": f"Invalid metric: {metric}"}

    summary = await tracker.get_usage(user.id, metric_enum, period_start, now)

    # Sort breakdown by value descending
    sorted_breakdown = dict(sorted(summary.breakdown.items(), key=lambda x: x[1], reverse=True))

    # Limit to top 20 for readability
    top_breakdown = dict(list(sorted_breakdown.items())[:20])

    return {
        "metric": metric,
        "total": summary.total,
        "period_start": period_start.isoformat(),
        "period_end": now.isoformat(),
        "breakdown": top_breakdown,
        "other": sum(v for k, v in list(sorted_breakdown.items())[20:]),
    }


@router.get("/metrics")
async def list_available_metrics(
    user: CurrentUser,
) -> dict:
    """
    List all available usage metrics.

    Returns:
        List of trackable metrics
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
