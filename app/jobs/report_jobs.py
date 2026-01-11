"""
Report generation and data export background jobs.
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlmodel import select

from app.core.db import get_session_context
from app.models.user import User

logger = logging.getLogger(__name__)


async def generate_daily_report(ctx: dict[str, Any]) -> dict[str, Any]:
    """
    Generate daily usage report.

    This is a scheduled job that runs at 9am UTC.

    Args:
        ctx: ARQ context dict

    Returns:
        Report summary dict
    """
    logger.info("Generating daily report...")

    async with get_session_context() as session:
        # Count total users
        result = await session.execute(select(User))
        users = result.scalars().all()
        total_users = len(users)

        # Count active users (logged in within 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        active_users = sum(
            1 for u in users if u.last_sign_in_at and u.last_sign_in_at > yesterday
        )

        # Count new users today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        new_users_today = sum(1 for u in users if u.created_at >= today_start)

    report = {
        "date": datetime.utcnow().isoformat(),
        "total_users": total_users,
        "active_users_24h": active_users,
        "new_users_today": new_users_today,
    }

    logger.info(f"Daily report generated: {report}")

    # TODO: Send report via email or store in database
    # await enqueue("app.jobs.email_jobs.send_notification_email", ...)

    return report


async def export_user_data(
    ctx: dict[str, Any],
    user_id: str,
) -> dict[str, Any]:
    """
    Export all user data (GDPR data export).

    Args:
        ctx: ARQ context dict
        user_id: UUID of the user requesting export

    Returns:
        Dict containing all user data
    """
    logger.info(f"Exporting data for user {user_id}")

    async with get_session_context() as session:
        result = await session.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"User {user_id} not found for data export")
            return {"error": "User not found"}

        # Collect user data
        user_data = {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "last_sign_in_at": (
                    user.last_sign_in_at.isoformat() if user.last_sign_in_at else None
                ),
            },
            "subscription": {
                "tier": user.subscription_tier,
                "status": user.subscription_status,
            },
            "exported_at": datetime.utcnow().isoformat(),
        }

        # TODO: Add projects, activity logs, etc.

    logger.info(f"Data export complete for user {user_id}")

    # TODO: Store export file and notify user
    # await enqueue("app.jobs.email_jobs.send_notification_email", ...)

    return user_data


async def cleanup_old_data(ctx: dict[str, Any]) -> dict[str, Any]:
    """
    Clean up old data (scheduled maintenance task).

    This job runs weekly on Sunday at midnight.

    Args:
        ctx: ARQ context dict

    Returns:
        Cleanup summary
    """
    logger.info("Running scheduled data cleanup...")

    # Placeholder for cleanup logic
    # Examples:
    # - Delete soft-deleted records older than 30 days
    # - Clean up expired sessions
    # - Archive old audit logs
    # - Remove orphaned files from storage

    cleanup_summary = {
        "executed_at": datetime.utcnow().isoformat(),
        "deleted_records": 0,
        "archived_records": 0,
        "freed_storage_mb": 0,
    }

    logger.info(f"Data cleanup complete: {cleanup_summary}")

    return cleanup_summary
