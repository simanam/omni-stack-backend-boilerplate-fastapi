"""
Feature flags and subscription plan limits.
Provides feature gating based on user subscription plan.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.core.cache import get_redis
from app.models.user import User

logger = logging.getLogger(__name__)

# Type aliases
PlanType = Literal["free", "pro", "enterprise"]
FeatureType = Literal["api_calls", "ai_requests", "storage_mb", "projects", "team_members"]


@dataclass
class PlanLimits:
    """Limits for a subscription plan."""

    api_calls: int  # Per month, -1 = unlimited
    ai_requests: int  # Per month, -1 = unlimited
    storage_mb: int  # Total storage, -1 = unlimited
    projects: int  # Max projects, -1 = unlimited
    team_members: int  # Max team members, -1 = unlimited


# Plan configurations
PLAN_LIMITS: dict[PlanType, PlanLimits] = {
    "free": PlanLimits(
        api_calls=1000,
        ai_requests=50,
        storage_mb=100,
        projects=3,
        team_members=1,
    ),
    "pro": PlanLimits(
        api_calls=50000,
        ai_requests=2000,
        storage_mb=10000,  # 10 GB
        projects=50,
        team_members=10,
    ),
    "enterprise": PlanLimits(
        api_calls=-1,  # Unlimited
        ai_requests=-1,
        storage_mb=-1,
        projects=-1,
        team_members=-1,
    ),
}


@dataclass
class FeatureStatus:
    """Status of a feature for a user."""

    allowed: bool
    limit: int  # -1 = unlimited
    used: int
    remaining: int  # -1 = unlimited
    resets_at: datetime | None  # When usage resets (for monthly limits)


class FeatureFlags:
    """
    Feature flags and usage tracking.

    Tracks usage limits per plan and provides feature gating.
    Uses Redis for fast usage counting with monthly reset.

    Usage:
        flags = FeatureFlags()

        # Check if user can use feature
        status = await flags.check_feature(session, user, "ai_requests")
        if not status.allowed:
            raise HTTPException(429, "AI request limit exceeded")

        # Increment usage after successful use
        await flags.increment_usage(session, user, "ai_requests")
    """

    def _get_plan_limits(self, plan: PlanType) -> PlanLimits:
        """Get limits for a plan."""
        return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    def _get_user_plan(self, user: User) -> PlanType:
        """Get user's current plan."""
        if user.subscription_status in ("active", "trialing"):
            return user.subscription_plan or "free"  # type: ignore
        return "free"

    def _get_usage_key(self, user_id: str, feature: FeatureType) -> str:
        """Generate Redis key for usage tracking."""
        # Include month in key for automatic monthly reset
        month = datetime.utcnow().strftime("%Y-%m")
        return f"usage:{user_id}:{feature}:{month}"

    def _get_month_end(self) -> datetime:
        """Get end of current month."""
        now = datetime.utcnow()
        if now.month == 12:
            return datetime(now.year + 1, 1, 1)
        return datetime(now.year, now.month + 1, 1)

    async def get_limit(self, user: User, feature: FeatureType) -> int:
        """
        Get the limit for a feature based on user's plan.

        Args:
            user: User model
            feature: Feature type

        Returns:
            Limit value (-1 = unlimited)
        """
        plan = self._get_user_plan(user)
        limits = self._get_plan_limits(plan)
        return getattr(limits, feature, 0)

    async def get_usage(self, user: User, feature: FeatureType) -> int:
        """
        Get current usage for a feature.

        Args:
            user: User model
            feature: Feature type

        Returns:
            Current usage count
        """
        redis = await get_redis()
        if not redis:
            # Without Redis, we can't track usage
            return 0

        key = self._get_usage_key(user.id, feature)
        value = await redis.get(key)
        return int(value) if value else 0

    async def check_feature(
        self,
        user: User,
        feature: FeatureType,
    ) -> FeatureStatus:
        """
        Check if user can use a feature.

        Args:
            user: User model
            feature: Feature type

        Returns:
            FeatureStatus with allowed status and usage info
        """
        limit = await self.get_limit(user, feature)
        used = await self.get_usage(user, feature)

        # Unlimited
        if limit == -1:
            return FeatureStatus(
                allowed=True,
                limit=-1,
                used=used,
                remaining=-1,
                resets_at=None,
            )

        remaining = max(0, limit - used)
        allowed = remaining > 0

        return FeatureStatus(
            allowed=allowed,
            limit=limit,
            used=used,
            remaining=remaining,
            resets_at=self._get_month_end(),
        )

    async def increment_usage(
        self,
        user: User,
        feature: FeatureType,
        amount: int = 1,
    ) -> int:
        """
        Increment usage for a feature.

        Args:
            user: User model
            feature: Feature type
            amount: Amount to increment

        Returns:
            New usage count
        """
        redis = await get_redis()
        if not redis:
            logger.warning(f"Redis not available, cannot track usage for {feature}")
            return 0

        key = self._get_usage_key(user.id, feature)

        # Increment and set expiry
        new_value = await redis.incr(key, amount)

        # Set expiry to end of month + 1 day buffer
        month_end = self._get_month_end()
        ttl = int((month_end - datetime.utcnow()).total_seconds()) + 86400
        await redis.expire(key, ttl)

        logger.debug(f"Usage for {user.id}/{feature}: {new_value}")
        return new_value

    async def get_remaining(
        self,
        user: User,
        feature: FeatureType,
    ) -> int:
        """
        Get remaining quota for a feature.

        Args:
            user: User model
            feature: Feature type

        Returns:
            Remaining count (-1 = unlimited)
        """
        status = await self.check_feature(user, feature)
        return status.remaining

    async def reset_usage(
        self,
        user: User,
        feature: FeatureType,
    ) -> None:
        """
        Reset usage for a feature (admin function).

        Args:
            user: User model
            feature: Feature type
        """
        redis = await get_redis()
        if not redis:
            return

        key = self._get_usage_key(user.id, feature)
        await redis.delete(key)
        logger.info(f"Reset usage for {user.id}/{feature}")

    async def get_all_usage(self, user: User) -> dict[FeatureType, FeatureStatus]:
        """
        Get usage status for all features.

        Args:
            user: User model

        Returns:
            Dictionary of feature -> FeatureStatus
        """
        features: list[FeatureType] = [
            "api_calls",
            "ai_requests",
            "storage_mb",
            "projects",
            "team_members",
        ]

        result = {}
        for feature in features:
            result[feature] = await self.check_feature(user, feature)

        return result


# Singleton instance
feature_flags = FeatureFlags()


# =============================================================================
# Convenience Functions
# =============================================================================


async def check_feature_limit(
    user: User,
    feature: FeatureType,
) -> FeatureStatus:
    """
    Check if user can use a feature.

    Convenience function for the singleton instance.
    """
    return await feature_flags.check_feature(user, feature)


async def increment_feature_usage(
    user: User,
    feature: FeatureType,
    amount: int = 1,
) -> int:
    """
    Increment usage for a feature.

    Convenience function for the singleton instance.
    """
    return await feature_flags.increment_usage(user, feature, amount)


async def get_feature_remaining(
    user: User,
    feature: FeatureType,
) -> int:
    """
    Get remaining quota for a feature.

    Convenience function for the singleton instance.
    """
    return await feature_flags.get_remaining(user, feature)


def get_plan_limits(plan: PlanType) -> PlanLimits:
    """Get limits for a plan type."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
