"""
ARQ worker configuration for background job processing.
"""

import logging
from urllib.parse import urlparse

from arq.connections import RedisSettings

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_redis_settings() -> RedisSettings | None:
    """Parse Redis URL into ARQ settings."""
    if not settings.REDIS_URL:
        return None

    parsed = urlparse(settings.REDIS_URL)

    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=parsed.password,
        database=int(parsed.path.lstrip("/") or 0),
    )


async def startup(ctx: dict) -> None:
    """Called when worker starts."""
    logger.info("ARQ Worker starting up...")


async def shutdown(ctx: dict) -> None:
    """Called when worker shuts down."""
    logger.info("ARQ Worker shutting down...")


class WorkerSettings:
    """ARQ worker configuration."""

    redis_settings = get_redis_settings()

    # Import all job functions
    functions = [
        # Email jobs
        "app.jobs.email_jobs.send_welcome_email",
        "app.jobs.email_jobs.send_password_reset_email",
        "app.jobs.email_jobs.send_notification_email",
        # Report jobs
        "app.jobs.report_jobs.generate_daily_report",
        "app.jobs.report_jobs.export_user_data",
        "app.jobs.report_jobs.cleanup_old_data",
    ]

    # Cron jobs (scheduled tasks)
    cron_jobs = [
        # Daily report at 9am UTC
        {
            "coroutine": "app.jobs.report_jobs.generate_daily_report",
            "hour": 9,
            "minute": 0,
        },
        # Weekly cleanup at midnight on Sunday
        {
            "coroutine": "app.jobs.report_jobs.cleanup_old_data",
            "weekday": 6,  # Sunday
            "hour": 0,
            "minute": 0,
        },
    ]

    on_startup = startup
    on_shutdown = shutdown

    # Worker settings
    max_jobs = 10
    job_timeout = 300  # 5 minutes
    keep_result = 3600  # Keep results for 1 hour
    poll_delay = 0.5
