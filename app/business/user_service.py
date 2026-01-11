"""
User business logic service.
Handles user creation, updates, and sync from auth provider tokens.
"""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.user import User, UserUpdate


async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    """Get user by ID."""
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Get user by email."""
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_or_create_user(
    session: AsyncSession,
    user_id: str,
    email: str,
    full_name: str | None = None,
    avatar_url: str | None = None,
) -> tuple[User, bool]:
    """
    Get existing user or create new one.

    Returns:
        Tuple of (user, created) where created is True if user was just created.
    """
    user = await get_user_by_id(session, user_id)

    if user:
        return user, False

    # Create new user
    user = User(
        id=user_id,
        email=email,
        full_name=full_name,
        avatar_url=avatar_url,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user, True


async def create_user_from_token(
    session: AsyncSession,
    user_id: str,
    token_payload: dict[str, Any] | None = None,
) -> User:
    """
    Create user from JWT token payload.
    Extracts email and profile info from common token claim locations.
    """
    if token_payload is None:
        token_payload = {}

    # Extract email from various claim locations
    email = (
        token_payload.get("email")
        or token_payload.get("user_metadata", {}).get("email")
        or token_payload.get("app_metadata", {}).get("email")
        or f"{user_id}@placeholder.local"  # Fallback for tokens without email
    )

    # Extract name from various claim locations
    full_name = (
        token_payload.get("name")
        or token_payload.get("full_name")
        or token_payload.get("user_metadata", {}).get("full_name")
        or token_payload.get("user_metadata", {}).get("name")
    )

    # Extract avatar from various claim locations
    avatar_url = (
        token_payload.get("picture")
        or token_payload.get("avatar_url")
        or token_payload.get("user_metadata", {}).get("avatar_url")
        or token_payload.get("user_metadata", {}).get("picture")
    )

    user = User(
        id=user_id,
        email=email,
        full_name=full_name,
        avatar_url=avatar_url,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def update_user(
    session: AsyncSession,
    user: User,
    update_data: UserUpdate,
) -> User:
    """Update user with new data."""
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(user, field, value)

    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def update_user_login(session: AsyncSession, user: User) -> User:
    """Update user login timestamp and count."""
    user.last_login_at = datetime.utcnow()
    user.login_count += 1
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def sync_user_from_token(
    session: AsyncSession,
    user_id: str,
    token_payload: dict[str, Any],
) -> User:
    """
    Sync user data from token payload.
    Creates user if doesn't exist, updates login stats if exists.
    """
    user = await get_user_by_id(session, user_id)

    if not user:
        user = await create_user_from_token(session, user_id, token_payload)
    else:
        # Update login stats
        user = await update_user_login(session, user)

    return user


async def list_users(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    is_active: bool | None = None,
) -> list[User]:
    """List users with pagination and optional filtering."""
    query = select(User)

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())

    result = await session.execute(query)
    return list(result.scalars().all())


async def count_users(
    session: AsyncSession,
    is_active: bool | None = None,
) -> int:
    """Count total users with optional filtering."""
    from sqlalchemy import func

    query = select(func.count()).select_from(User)

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    result = await session.execute(query)
    return result.scalar_one()


async def update_user_role(
    session: AsyncSession,
    user: User,
    role: str,
) -> User:
    """Update user role (admin operation)."""
    user.role = role
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def deactivate_user(session: AsyncSession, user: User) -> User:
    """Deactivate user (admin operation)."""
    user.is_active = False
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def activate_user(session: AsyncSession, user: User) -> User:
    """Activate user (admin operation)."""
    user.is_active = True
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user
