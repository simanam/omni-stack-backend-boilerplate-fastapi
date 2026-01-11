"""
FastAPI dependency injection - shared dependencies for routes.
"""

from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import get_current_user_id, verify_token
from app.models.user import User

# Database session dependency
DBSession = Annotated[AsyncSession, Depends(get_session)]

# Auth dependencies
TokenPayload = Annotated[dict[str, Any], Depends(verify_token)]
CurrentUserId = Annotated[str, Depends(get_current_user_id)]


async def get_current_user(
    session: DBSession,
    user_id: CurrentUserId,
    payload: TokenPayload,
) -> User:
    """
    Get full user object from database.
    Auto-creates user on first request (synced from auth provider).
    """
    from app.business.user_service import sync_user_from_token

    user = await sync_user_from_token(session, user_id, payload)

    if not user.is_active:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
