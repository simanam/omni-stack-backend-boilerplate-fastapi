"""
Admin user management endpoints.
Requires admin role for access.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DBSession
from app.business import user_service
from app.core.exceptions import NotFoundError
from app.core.security import require_admin
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserAdminUpdate, UserReadAdmin

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("", response_model=PaginatedResponse[UserReadAdmin])
async def list_users(
    session: DBSession,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum records to return"),
    is_active: bool | None = Query(None, description="Filter by active status"),
) -> PaginatedResponse[UserReadAdmin]:
    """
    List all users with pagination.

    Requires admin role.
    """
    users = await user_service.list_users(
        session, skip=skip, limit=limit, is_active=is_active
    )
    total = await user_service.count_users(session, is_active=is_active)

    return PaginatedResponse(
        items=[UserReadAdmin.model_validate(u) for u in users],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{user_id}", response_model=UserReadAdmin)
async def get_user(
    session: DBSession,
    user_id: str,
) -> UserReadAdmin:
    """
    Get a specific user by ID.

    Requires admin role.
    """
    user = await user_service.get_user_by_id(session, user_id)
    if not user:
        raise NotFoundError("User", user_id)
    return UserReadAdmin.model_validate(user)


@router.patch("/{user_id}", response_model=UserReadAdmin)
async def update_user(
    session: DBSession,
    user_id: str,
    user_update: UserAdminUpdate,
) -> UserReadAdmin:
    """
    Update a user (admin can change role, active status).

    Requires admin role.
    """
    user = await user_service.get_user_by_id(session, user_id)
    if not user:
        raise NotFoundError("User", user_id)

    # Apply updates
    update_dict = user_update.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(user, field, value)

    session.add(user)
    await session.flush()
    await session.refresh(user)

    return UserReadAdmin.model_validate(user)


@router.post("/{user_id}/deactivate", response_model=UserReadAdmin)
async def deactivate_user(
    session: DBSession,
    user_id: str,
    current_user: CurrentUser,
) -> UserReadAdmin:
    """
    Deactivate a user account.

    Requires admin role. Cannot deactivate yourself.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    user = await user_service.get_user_by_id(session, user_id)
    if not user:
        raise NotFoundError("User", user_id)

    user = await user_service.deactivate_user(session, user)
    return UserReadAdmin.model_validate(user)


@router.post("/{user_id}/activate", response_model=UserReadAdmin)
async def activate_user(
    session: DBSession,
    user_id: str,
) -> UserReadAdmin:
    """
    Activate a deactivated user account.

    Requires admin role.
    """
    user = await user_service.get_user_by_id(session, user_id)
    if not user:
        raise NotFoundError("User", user_id)

    user = await user_service.activate_user(session, user)
    return UserReadAdmin.model_validate(user)
