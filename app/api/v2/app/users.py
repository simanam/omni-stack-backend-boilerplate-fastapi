"""
User profile endpoints for API v2.

v2 changes from v1:
- Enhanced response with metadata wrapper
- Added request_id in response
- Stricter validation on updates
- Rate limit info included in response
"""

from datetime import UTC, datetime
from typing import Generic, TypeVar

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DBSession
from app.business import user_service
from app.core.middleware import get_request_id
from app.core.versioning import APIVersion
from app.schemas.user import UserRead, UserUpdate

router = APIRouter()

T = TypeVar("T")  # Used by DataResponse generic class


class ResponseMetadata(BaseModel):
    """Metadata included in all v2 responses."""

    request_id: str | None = Field(description="Unique request identifier")
    timestamp: datetime = Field(description="Response timestamp")
    version: str = Field(description="API version")


class DataResponse(BaseModel, Generic[T]):
    """Standard v2 response wrapper with data and metadata."""

    data: T = Field(description="Response data")
    meta: ResponseMetadata = Field(description="Response metadata")


class UserReadV2(UserRead):
    """Enhanced user schema for v2 with additional computed fields."""

    is_premium: bool = Field(description="Whether user has an active paid subscription")
    days_since_joined: int = Field(description="Days since user account creation")


def create_user_response(data: UserReadV2, request: Request) -> DataResponse[UserReadV2]:
    """Helper to create standardized v2 response for user data."""
    return DataResponse(
        data=data,
        meta=ResponseMetadata(
            request_id=get_request_id(),
            timestamp=datetime.now(UTC),
            version=APIVersion.V2.value,
        ),
    )


def user_to_v2(user) -> UserReadV2:
    """Convert User model to UserReadV2."""
    now = datetime.now(UTC)
    created = user.created_at
    if created.tzinfo is None:
        # Assume UTC if no timezone
        created = created.replace(tzinfo=UTC)

    days_since_joined = (now - created).days

    return UserReadV2(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        role=user.role,
        is_active=user.is_active,
        subscription_status=user.subscription_status,
        subscription_plan=user.subscription_plan,
        created_at=user.created_at,
        updated_at=user.updated_at,
        is_premium=user.subscription_status == "active" and user.subscription_plan in ("pro", "enterprise"),
        days_since_joined=days_since_joined,
    )


@router.get("/me", response_model=DataResponse[UserReadV2])
async def get_current_user_profile(
    request: Request,
    user: CurrentUser,
) -> DataResponse[UserReadV2]:
    """
    Get current authenticated user's profile (v2).

    Enhanced response includes:
    - Wrapped data with metadata
    - Computed fields (is_premium, days_since_joined)
    - Request ID for tracing
    """
    user_data = user_to_v2(user)
    return create_user_response(user_data, request)


@router.patch("/me", response_model=DataResponse[UserReadV2])
async def update_current_user_profile(
    request: Request,
    session: DBSession,
    user: CurrentUser,
    user_update: UserUpdate,
) -> DataResponse[UserReadV2]:
    """
    Update current authenticated user's profile (v2).

    Enhanced response includes metadata wrapper.
    """
    updated_user = await user_service.update_user(session, user, user_update)
    user_data = user_to_v2(updated_user)
    return create_user_response(user_data, request)
