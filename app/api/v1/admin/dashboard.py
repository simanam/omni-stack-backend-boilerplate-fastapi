"""
Admin dashboard endpoints for system statistics and monitoring.
Requires admin role for access.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import DBSession
from app.core.cache import get_redis
from app.core.security import require_admin
from app.models.audit_log import AuditLog, AuditLogRead
from app.models.user import User
from app.models.webhook_event import WebhookEvent

router = APIRouter(dependencies=[Depends(require_admin)])


class UserStats(BaseModel):
    """User statistics."""

    total: int
    active: int
    inactive: int
    admins: int
    new_last_7_days: int
    new_last_30_days: int


class SubscriptionStats(BaseModel):
    """Subscription statistics."""

    free: int
    pro: int
    enterprise: int
    active: int
    trialing: int
    canceled: int
    past_due: int


class WebhookStats(BaseModel):
    """Webhook event statistics."""

    total: int
    pending: int
    processed: int
    failed: int
    last_24_hours: int


class JobStats(BaseModel):
    """Background job statistics."""

    queued: int
    active: int
    completed: int
    failed: int


class SystemStats(BaseModel):
    """Overall system statistics."""

    database_connected: bool
    redis_connected: bool
    uptime_seconds: float | None = None


class DashboardStats(BaseModel):
    """Complete dashboard statistics."""

    users: UserStats
    subscriptions: SubscriptionStats
    webhooks: WebhookStats
    jobs: JobStats
    system: SystemStats
    generated_at: datetime


class AuditLogListResponse(BaseModel):
    """Response for audit log listing."""

    items: list[AuditLogRead]
    total: int
    skip: int
    limit: int


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(session: DBSession) -> DashboardStats:
    """
    Get comprehensive dashboard statistics.

    Requires admin role.
    """
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)
    twenty_four_hours_ago = now - timedelta(hours=24)

    # User stats
    total_users = await session.scalar(select(func.count()).select_from(User))
    active_users = await session.scalar(
        select(func.count()).select_from(User).where(User.is_active == True)  # noqa: E712
    )
    admin_users = await session.scalar(
        select(func.count()).select_from(User).where(User.role.in_(["admin", "superadmin"]))
    )
    new_7_days = await session.scalar(
        select(func.count()).select_from(User).where(User.created_at >= seven_days_ago)
    )
    new_30_days = await session.scalar(
        select(func.count()).select_from(User).where(User.created_at >= thirty_days_ago)
    )

    user_stats = UserStats(
        total=total_users or 0,
        active=active_users or 0,
        inactive=(total_users or 0) - (active_users or 0),
        admins=admin_users or 0,
        new_last_7_days=new_7_days or 0,
        new_last_30_days=new_30_days or 0,
    )

    # Subscription stats
    free_users = await session.scalar(
        select(func.count()).select_from(User).where(
            (User.subscription_plan == "free") | (User.subscription_plan == None)  # noqa: E711
        )
    )
    pro_users = await session.scalar(
        select(func.count()).select_from(User).where(User.subscription_plan == "pro")
    )
    enterprise_users = await session.scalar(
        select(func.count()).select_from(User).where(User.subscription_plan == "enterprise")
    )
    active_subs = await session.scalar(
        select(func.count()).select_from(User).where(User.subscription_status == "active")
    )
    trialing_subs = await session.scalar(
        select(func.count()).select_from(User).where(User.subscription_status == "trialing")
    )
    canceled_subs = await session.scalar(
        select(func.count()).select_from(User).where(User.subscription_status == "canceled")
    )
    past_due_subs = await session.scalar(
        select(func.count()).select_from(User).where(User.subscription_status == "past_due")
    )

    subscription_stats = SubscriptionStats(
        free=free_users or 0,
        pro=pro_users or 0,
        enterprise=enterprise_users or 0,
        active=active_subs or 0,
        trialing=trialing_subs or 0,
        canceled=canceled_subs or 0,
        past_due=past_due_subs or 0,
    )

    # Webhook stats
    total_webhooks = await session.scalar(
        select(func.count()).select_from(WebhookEvent)
    )
    pending_webhooks = await session.scalar(
        select(func.count()).select_from(WebhookEvent).where(WebhookEvent.status == "pending")
    )
    processed_webhooks = await session.scalar(
        select(func.count()).select_from(WebhookEvent).where(WebhookEvent.status == "processed")
    )
    failed_webhooks = await session.scalar(
        select(func.count()).select_from(WebhookEvent).where(WebhookEvent.status == "failed")
    )
    recent_webhooks = await session.scalar(
        select(func.count()).select_from(WebhookEvent).where(
            WebhookEvent.created_at >= twenty_four_hours_ago
        )
    )

    webhook_stats = WebhookStats(
        total=total_webhooks or 0,
        pending=pending_webhooks or 0,
        processed=processed_webhooks or 0,
        failed=failed_webhooks or 0,
        last_24_hours=recent_webhooks or 0,
    )

    # Job stats from Redis
    job_stats = JobStats(queued=0, active=0, completed=0, failed=0)
    redis = await get_redis()
    if redis:
        try:
            # ARQ stores job counts in Redis
            queued = await redis.llen("arq:queue")
            job_stats.queued = queued or 0
        except Exception:
            pass

    # System stats
    redis_connected = redis is not None
    system_stats = SystemStats(
        database_connected=True,  # If we got here, DB is connected
        redis_connected=redis_connected,
    )

    return DashboardStats(
        users=user_stats,
        subscriptions=subscription_stats,
        webhooks=webhook_stats,
        jobs=job_stats,
        system=system_stats,
        generated_at=now,
    )


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    session: DBSession,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    actor_id: str | None = Query(None, description="Filter by actor ID"),
    action: str | None = Query(None, description="Filter by action type"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    resource_id: str | None = Query(None, description="Filter by resource ID"),
    start_date: datetime | None = Query(None, description="Filter by start date"),
    end_date: datetime | None = Query(None, description="Filter by end date"),
) -> AuditLogListResponse:
    """
    List audit logs with filtering and pagination.

    Requires admin role.
    """
    # Build query
    query = select(AuditLog)

    if actor_id:
        query = query.where(AuditLog.actor_id == actor_id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if resource_id:
        query = query.where(AuditLog.resource_id == resource_id)
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)

    # Get total count
    count_query = select(func.count()).select_from(AuditLog)
    if actor_id:
        count_query = count_query.where(AuditLog.actor_id == actor_id)
    if action:
        count_query = count_query.where(AuditLog.action == action)
    if resource_type:
        count_query = count_query.where(AuditLog.resource_type == resource_type)
    if resource_id:
        count_query = count_query.where(AuditLog.resource_id == resource_id)
    if start_date:
        count_query = count_query.where(AuditLog.created_at >= start_date)
    if end_date:
        count_query = count_query.where(AuditLog.created_at <= end_date)

    total = await session.scalar(count_query)

    # Get paginated results
    query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    logs = result.scalars().all()

    return AuditLogListResponse(
        items=[AuditLogRead.model_validate(log) for log in logs],
        total=total or 0,
        skip=skip,
        limit=limit,
    )


@router.get("/audit-logs/{log_id}", response_model=AuditLogRead)
async def get_audit_log(
    session: DBSession,
    log_id: str,
) -> AuditLogRead:
    """
    Get a specific audit log entry.

    Requires admin role.
    """
    from app.core.exceptions import NotFoundError

    result = await session.execute(
        select(AuditLog).where(AuditLog.id == log_id)
    )
    log = result.scalar_one_or_none()

    if not log:
        raise NotFoundError("AuditLog", log_id)

    return AuditLogRead.model_validate(log)
