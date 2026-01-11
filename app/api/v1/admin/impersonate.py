"""
Admin impersonation endpoints.
Allows admins to impersonate users for debugging and support.
Requires admin role for access.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import jwt
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.api.deps import CurrentUser, DBSession
from app.business import user_service
from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.core.security import require_admin
from app.models.audit_log import AuditLog
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_admin)])


class ImpersonationToken(BaseModel):
    """Response containing impersonation token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    impersonated_user_id: str
    impersonated_user_email: str
    impersonator_id: str


class ImpersonationRequest(BaseModel):
    """Request to impersonate a user."""

    user_id: str
    reason: str  # Required reason for audit trail
    duration_minutes: int = 30  # Default 30 minutes


def create_impersonation_token(
    impersonated_user: User,
    impersonator: User,
    duration_minutes: int = 30,
) -> str:
    """
    Create a JWT token for impersonation.

    The token includes:
    - sub: The impersonated user's ID
    - impersonator_id: The admin's user ID
    - is_impersonation: True to mark this as an impersonation session

    This token can be used with the standard auth flow, but will be
    tracked as an impersonation session.
    """
    now = datetime.utcnow()
    expires_at = now + timedelta(minutes=duration_minutes)

    payload: dict[str, Any] = {
        # Standard claims
        "sub": impersonated_user.id,
        "email": impersonated_user.email,
        "role": impersonated_user.role,
        "iat": now,
        "exp": expires_at,
        # Impersonation-specific claims
        "is_impersonation": True,
        "impersonator_id": impersonator.id,
        "impersonator_email": impersonator.email,
    }

    # Sign with our secret key (HS256)
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token


@router.post("/start", response_model=ImpersonationToken)
async def start_impersonation(
    session: DBSession,
    current_user: CurrentUser,
    request: Request,
    impersonation_request: ImpersonationRequest,
) -> ImpersonationToken:
    """
    Start an impersonation session.

    Creates a limited-duration token that allows the admin to act as
    the specified user. All actions taken during impersonation are
    logged with the impersonator's ID for audit purposes.

    Requires admin role.
    """
    target_user_id = impersonation_request.user_id
    reason = impersonation_request.reason
    duration = impersonation_request.duration_minutes

    # Validate duration
    if duration < 5:
        raise ValidationError("Impersonation duration must be at least 5 minutes")
    if duration > 480:  # 8 hours max
        raise ValidationError("Impersonation duration cannot exceed 8 hours (480 minutes)")

    # Cannot impersonate yourself
    if target_user_id == current_user.id:
        raise ValidationError("Cannot impersonate yourself")

    # Get target user
    target_user = await user_service.get_user_by_id(session, target_user_id)
    if not target_user:
        raise NotFoundError("User", target_user_id)

    # Cannot impersonate superadmins (unless you are one)
    if target_user.role == "superadmin" and current_user.role != "superadmin":
        raise ForbiddenError("Cannot impersonate superadmin users")

    # Cannot impersonate other admins (unless you are superadmin)
    if target_user.role == "admin" and current_user.role not in ("superadmin",):
        raise ForbiddenError("Cannot impersonate admin users")

    # Create impersonation token
    token = create_impersonation_token(target_user, current_user, duration)

    # Log the impersonation start
    audit_log = AuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        action="user.impersonated",
        description=f"Started impersonation of user {target_user.email}",
        resource_type="user",
        resource_id=target_user.id,
        details={
            "reason": reason,
            "duration_minutes": duration,
            "target_user_email": target_user.email,
            "target_user_role": target_user.role,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=request.headers.get("x-request-id"),
    )
    session.add(audit_log)
    await session.flush()

    logger.warning(
        f"Admin {current_user.email} started impersonating user {target_user.email}. "
        f"Reason: {reason}"
    )

    return ImpersonationToken(
        access_token=token,
        expires_in=duration * 60,  # Convert to seconds
        impersonated_user_id=target_user.id,
        impersonated_user_email=target_user.email,
        impersonator_id=current_user.id,
    )


@router.post("/stop")
async def stop_impersonation(
    session: DBSession,
    current_user: CurrentUser,
    request: Request,
) -> dict[str, str]:
    """
    Stop an impersonation session.

    This is a logging endpoint - the actual token invalidation happens
    client-side by discarding the impersonation token. This endpoint
    creates an audit log entry for when the admin stops impersonating.

    Requires admin role.
    """
    # Log the impersonation stop
    audit_log = AuditLog(
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        action="user.impersonated",
        description="Stopped impersonation session",
        details={"action": "stop"},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=request.headers.get("x-request-id"),
    )
    session.add(audit_log)
    await session.flush()

    return {"message": "Impersonation session logged as stopped"}


@router.get("/active")
async def list_active_impersonations(
    session: DBSession,
) -> dict[str, Any]:
    """
    List recent impersonation sessions from audit logs.

    Note: This shows logged impersonation starts, not actual token validity.
    Tokens expire based on their duration regardless of this log.

    Requires admin role.
    """
    from sqlalchemy import select

    # Get recent impersonation logs (last 24 hours)
    cutoff = datetime.utcnow() - timedelta(hours=24)

    result = await session.execute(
        select(AuditLog)
        .where(AuditLog.action == "user.impersonated")
        .where(AuditLog.created_at >= cutoff)
        .order_by(AuditLog.created_at.desc())
        .limit(50)
    )
    logs = result.scalars().all()

    return {
        "impersonations": [
            {
                "id": log.id,
                "impersonator_id": log.actor_id,
                "impersonator_email": log.actor_email,
                "target_user_id": log.resource_id,
                "target_user_email": log.details.get("target_user_email"),
                "reason": log.details.get("reason"),
                "duration_minutes": log.details.get("duration_minutes"),
                "started_at": log.created_at.isoformat(),
                "is_stop": log.details.get("action") == "stop",
            }
            for log in logs
        ],
        "total": len(logs),
        "since": cutoff.isoformat(),
    }
