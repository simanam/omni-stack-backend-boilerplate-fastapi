"""
Admin feature flags management endpoints.
Requires admin role for access.
"""

import hashlib
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DBSession
from app.core.exceptions import NotFoundError, ValidationError
from app.core.security import require_admin
from app.models.feature_flag import (
    FeatureFlag,
    FeatureFlagCheck,
    FeatureFlagCreate,
    FeatureFlagRead,
    FeatureFlagUpdate,
)
from app.models.user import User

router = APIRouter(dependencies=[Depends(require_admin)])


class FeatureFlagListResponse(BaseModel):
    """Response for feature flag listing."""

    items: list[FeatureFlagRead]
    total: int
    skip: int
    limit: int


@router.get("", response_model=FeatureFlagListResponse)
async def list_feature_flags(
    session: DBSession,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    enabled: bool | None = Query(None, description="Filter by enabled status"),
    flag_type: str | None = Query(None, description="Filter by flag type"),
) -> FeatureFlagListResponse:
    """
    List all feature flags with pagination.

    Requires admin role.
    """
    # Build query
    query = select(FeatureFlag)

    if enabled is not None:
        query = query.where(FeatureFlag.enabled == enabled)
    if flag_type:
        query = query.where(FeatureFlag.flag_type == flag_type)

    # Get total count
    count_query = select(func.count()).select_from(FeatureFlag)
    if enabled is not None:
        count_query = count_query.where(FeatureFlag.enabled == enabled)
    if flag_type:
        count_query = count_query.where(FeatureFlag.flag_type == flag_type)

    total = await session.scalar(count_query)

    # Get paginated results
    query = query.order_by(FeatureFlag.key).offset(skip).limit(limit)
    result = await session.execute(query)
    flags = result.scalars().all()

    return FeatureFlagListResponse(
        items=[FeatureFlagRead.model_validate(flag) for flag in flags],
        total=total or 0,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=FeatureFlagRead)
async def create_feature_flag(
    session: DBSession,
    current_user: CurrentUser,
    flag_data: FeatureFlagCreate,
) -> FeatureFlagRead:
    """
    Create a new feature flag.

    Requires admin role.
    """
    # Check if flag with same key exists
    existing = await session.scalar(
        select(FeatureFlag).where(FeatureFlag.key == flag_data.key)
    )
    if existing:
        raise ValidationError(f"Feature flag with key '{flag_data.key}' already exists")

    # Validate flag type specific fields
    if flag_data.flag_type == "percentage" and (
        flag_data.percentage < 0 or flag_data.percentage > 100
    ):
        raise ValidationError("Percentage must be between 0 and 100")

    if flag_data.flag_type == "plan_based" and not flag_data.plans:
        raise ValidationError("Plans must be specified for plan_based flag type")

    # Create flag
    flag = FeatureFlag(
        **flag_data.model_dump(),
        created_by=current_user.id,
        updated_by=current_user.id,
    )

    session.add(flag)
    await session.flush()
    await session.refresh(flag)

    return FeatureFlagRead.model_validate(flag)


@router.get("/{flag_id}", response_model=FeatureFlagRead)
async def get_feature_flag(
    session: DBSession,
    flag_id: str,
) -> FeatureFlagRead:
    """
    Get a specific feature flag by ID.

    Requires admin role.
    """
    result = await session.execute(
        select(FeatureFlag).where(FeatureFlag.id == flag_id)
    )
    flag = result.scalar_one_or_none()

    if not flag:
        raise NotFoundError("FeatureFlag", flag_id)

    return FeatureFlagRead.model_validate(flag)


@router.get("/key/{flag_key}", response_model=FeatureFlagRead)
async def get_feature_flag_by_key(
    session: DBSession,
    flag_key: str,
) -> FeatureFlagRead:
    """
    Get a specific feature flag by key.

    Requires admin role.
    """
    result = await session.execute(
        select(FeatureFlag).where(FeatureFlag.key == flag_key)
    )
    flag = result.scalar_one_or_none()

    if not flag:
        raise NotFoundError("FeatureFlag", flag_key)

    return FeatureFlagRead.model_validate(flag)


@router.patch("/{flag_id}", response_model=FeatureFlagRead)
async def update_feature_flag(
    session: DBSession,
    current_user: CurrentUser,
    flag_id: str,
    flag_update: FeatureFlagUpdate,
) -> FeatureFlagRead:
    """
    Update a feature flag.

    Requires admin role.
    """
    result = await session.execute(
        select(FeatureFlag).where(FeatureFlag.id == flag_id)
    )
    flag = result.scalar_one_or_none()

    if not flag:
        raise NotFoundError("FeatureFlag", flag_id)

    # Apply updates
    update_dict = flag_update.model_dump(exclude_unset=True)

    # Validate percentage if updating
    if "percentage" in update_dict and (
        update_dict["percentage"] < 0 or update_dict["percentage"] > 100
    ):
        raise ValidationError("Percentage must be between 0 and 100")

    for field, value in update_dict.items():
        setattr(flag, field, value)

    flag.updated_by = current_user.id

    session.add(flag)
    await session.flush()
    await session.refresh(flag)

    return FeatureFlagRead.model_validate(flag)


@router.delete("/{flag_id}")
async def delete_feature_flag(
    session: DBSession,
    flag_id: str,
) -> dict[str, str]:
    """
    Delete a feature flag.

    Requires admin role.
    """
    result = await session.execute(
        select(FeatureFlag).where(FeatureFlag.id == flag_id)
    )
    flag = result.scalar_one_or_none()

    if not flag:
        raise NotFoundError("FeatureFlag", flag_id)

    await session.delete(flag)
    await session.flush()

    return {"message": f"Feature flag '{flag.key}' deleted"}


@router.post("/{flag_id}/enable", response_model=FeatureFlagRead)
async def enable_feature_flag(
    session: DBSession,
    current_user: CurrentUser,
    flag_id: str,
) -> FeatureFlagRead:
    """
    Enable a feature flag.

    Requires admin role.
    """
    result = await session.execute(
        select(FeatureFlag).where(FeatureFlag.id == flag_id)
    )
    flag = result.scalar_one_or_none()

    if not flag:
        raise NotFoundError("FeatureFlag", flag_id)

    flag.enabled = True
    flag.updated_by = current_user.id

    session.add(flag)
    await session.flush()
    await session.refresh(flag)

    return FeatureFlagRead.model_validate(flag)


@router.post("/{flag_id}/disable", response_model=FeatureFlagRead)
async def disable_feature_flag(
    session: DBSession,
    current_user: CurrentUser,
    flag_id: str,
) -> FeatureFlagRead:
    """
    Disable a feature flag.

    Requires admin role.
    """
    result = await session.execute(
        select(FeatureFlag).where(FeatureFlag.id == flag_id)
    )
    flag = result.scalar_one_or_none()

    if not flag:
        raise NotFoundError("FeatureFlag", flag_id)

    flag.enabled = False
    flag.updated_by = current_user.id

    session.add(flag)
    await session.flush()
    await session.refresh(flag)

    return FeatureFlagRead.model_validate(flag)


@router.post("/{flag_id}/add-user")
async def add_user_to_flag(
    session: DBSession,
    current_user: CurrentUser,
    flag_id: str,
    user_id: str = Query(..., description="User ID to add"),
) -> FeatureFlagRead:
    """
    Add a user to a feature flag's user list.

    Requires admin role.
    """
    result = await session.execute(
        select(FeatureFlag).where(FeatureFlag.id == flag_id)
    )
    flag = result.scalar_one_or_none()

    if not flag:
        raise NotFoundError("FeatureFlag", flag_id)

    if user_id not in flag.user_ids:
        flag.user_ids = [*flag.user_ids, user_id]
        flag.updated_by = current_user.id

        session.add(flag)
        await session.flush()
        await session.refresh(flag)

    return FeatureFlagRead.model_validate(flag)


@router.post("/{flag_id}/remove-user")
async def remove_user_from_flag(
    session: DBSession,
    current_user: CurrentUser,
    flag_id: str,
    user_id: str = Query(..., description="User ID to remove"),
) -> FeatureFlagRead:
    """
    Remove a user from a feature flag's user list.

    Requires admin role.
    """
    result = await session.execute(
        select(FeatureFlag).where(FeatureFlag.id == flag_id)
    )
    flag = result.scalar_one_or_none()

    if not flag:
        raise NotFoundError("FeatureFlag", flag_id)

    if user_id in flag.user_ids:
        flag.user_ids = [uid for uid in flag.user_ids if uid != user_id]
        flag.updated_by = current_user.id

        session.add(flag)
        await session.flush()
        await session.refresh(flag)

    return FeatureFlagRead.model_validate(flag)


@router.get("/check/{flag_key}", response_model=FeatureFlagCheck)
async def check_flag_for_user(
    session: DBSession,
    flag_key: str,
    user_id: str = Query(..., description="User ID to check"),
) -> FeatureFlagCheck:
    """
    Check if a feature flag is enabled for a specific user.

    Requires admin role.
    """
    result = await session.execute(
        select(FeatureFlag).where(FeatureFlag.key == flag_key)
    )
    flag = result.scalar_one_or_none()

    if not flag:
        return FeatureFlagCheck(
            key=flag_key,
            enabled=False,
            reason="Flag not found",
        )

    # Check if flag is globally disabled
    if not flag.enabled:
        return FeatureFlagCheck(
            key=flag_key,
            enabled=False,
            reason="Flag is disabled",
        )

    # Check if flag has expired
    if flag.expires_at and flag.expires_at < datetime.utcnow():
        return FeatureFlagCheck(
            key=flag_key,
            enabled=False,
            reason="Flag has expired",
        )

    # Check based on flag type
    if flag.flag_type == "boolean":
        return FeatureFlagCheck(
            key=flag_key,
            enabled=True,
            reason="Flag is enabled globally",
        )

    if flag.flag_type == "user_list":
        if user_id in flag.user_ids:
            return FeatureFlagCheck(
                key=flag_key,
                enabled=True,
                reason="User is in the flag's user list",
            )
        return FeatureFlagCheck(
            key=flag_key,
            enabled=False,
            reason="User is not in the flag's user list",
        )

    if flag.flag_type == "percentage":
        # Use consistent hashing for percentage rollout
        hash_value = int(hashlib.md5(f"{flag_key}:{user_id}".encode()).hexdigest(), 16)
        bucket = hash_value % 100

        if bucket < flag.percentage:
            return FeatureFlagCheck(
                key=flag_key,
                enabled=True,
                reason=f"User is in the {flag.percentage}% rollout",
            )
        return FeatureFlagCheck(
            key=flag_key,
            enabled=False,
            reason=f"User is not in the {flag.percentage}% rollout",
        )

    if flag.flag_type == "plan_based":
        # Get user's plan
        user_result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            return FeatureFlagCheck(
                key=flag_key,
                enabled=False,
                reason="User not found",
            )

        user_plan = user.subscription_plan or "free"
        if user_plan in flag.plans:
            return FeatureFlagCheck(
                key=flag_key,
                enabled=True,
                reason=f"User's plan ({user_plan}) is in the allowed plans",
            )
        return FeatureFlagCheck(
            key=flag_key,
            enabled=False,
            reason=f"User's plan ({user_plan}) is not in the allowed plans",
        )

    return FeatureFlagCheck(
        key=flag_key,
        enabled=False,
        reason=f"Unknown flag type: {flag.flag_type}",
    )
