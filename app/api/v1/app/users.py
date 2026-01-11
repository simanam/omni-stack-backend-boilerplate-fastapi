"""
User profile endpoints for authenticated users.
"""

from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.business import user_service
from app.schemas.user import UserRead, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(
    user: CurrentUser,
) -> UserRead:
    """
    Get current authenticated user's profile.

    This endpoint automatically creates a user record on first access
    by syncing data from the JWT token.
    """
    return UserRead.model_validate(user)


@router.patch("/me", response_model=UserRead)
async def update_current_user_profile(
    session: DBSession,
    user: CurrentUser,
    user_update: UserUpdate,
) -> UserRead:
    """
    Update current authenticated user's profile.

    Only allows updating non-sensitive fields like name and avatar.
    Role and subscription changes require admin access.
    """
    updated_user = await user_service.update_user(session, user, user_update)
    return UserRead.model_validate(updated_user)
