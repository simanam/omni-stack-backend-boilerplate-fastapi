"""
Billing business logic service.
Handles subscription management, customer sync, and feature gating.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.models.user import User
from app.services.payments.stripe_service import (
    CheckoutResult,
    PortalResult,
    SubscriptionInfo,
    get_stripe_service,
)

logger = logging.getLogger(__name__)

# Type aliases
PlanType = Literal["free", "pro", "enterprise"]
BillingInterval = Literal["monthly", "yearly"]


@dataclass
class BillingStatus:
    """Current billing status for a user."""

    plan: PlanType
    status: str | None
    stripe_customer_id: str | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    subscription_id: str | None


class BillingService:
    """
    Billing service for subscription management.

    Handles:
    - Customer creation/sync with Stripe
    - Subscription checkout flow
    - Billing portal access
    - Subscription status sync
    - Feature gating based on plan

    Usage:
        billing = BillingService()
        status = await billing.get_billing_status(session, user)
        checkout = await billing.start_checkout(session, user, "monthly", success_url, cancel_url)
    """

    async def get_or_create_customer(
        self,
        session: AsyncSession,
        user: User,
    ) -> str:
        """
        Ensure user has a Stripe customer ID, creating one if needed.

        Args:
            session: Database session
            user: User model

        Returns:
            Stripe customer ID
        """
        if user.stripe_customer_id:
            return user.stripe_customer_id

        stripe_svc = get_stripe_service()
        customer = await stripe_svc.create_customer(
            email=user.email,
            name=user.full_name,
            user_id=user.id,
        )

        # Update user with Stripe customer ID
        user.stripe_customer_id = customer.id
        session.add(user)
        await session.flush()

        logger.info(f"Created Stripe customer {customer.id} for user {user.id}")
        return customer.id

    async def get_billing_status(
        self,
        session: AsyncSession,  # noqa: ARG002 - kept for API consistency
        user: User,
    ) -> BillingStatus:
        """
        Get current billing status for a user.

        Args:
            session: Database session
            user: User model

        Returns:
            BillingStatus with current plan and subscription info
        """
        plan: PlanType = "free"
        status = user.subscription_status
        current_period_end = None
        cancel_at_period_end = False
        subscription_id = None

        if user.subscription_plan:
            plan = user.subscription_plan  # type: ignore

        # If user has Stripe customer, get latest subscription info
        if user.stripe_customer_id and settings.stripe_available:
            try:
                stripe_svc = get_stripe_service()
                subs = await stripe_svc.get_customer_subscriptions(user.stripe_customer_id)

                if subs:
                    # Get the most recent active subscription
                    active_sub = next(
                        (s for s in subs if s.status in ("active", "trialing")),
                        subs[0] if subs else None,
                    )
                    if active_sub:
                        status = active_sub.status
                        subscription_id = active_sub.id
                        cancel_at_period_end = active_sub.cancel_at_period_end
                        current_period_end = datetime.fromtimestamp(
                            active_sub.current_period_end
                        )
                        if active_sub.plan:
                            plan = active_sub.plan  # type: ignore
            except Exception as e:
                logger.warning(f"Failed to fetch Stripe subscription: {e}")

        return BillingStatus(
            plan=plan,
            status=status,
            stripe_customer_id=user.stripe_customer_id,
            current_period_end=current_period_end,
            cancel_at_period_end=cancel_at_period_end,
            subscription_id=subscription_id,
        )

    async def start_checkout(
        self,
        session: AsyncSession,
        user: User,
        interval: BillingInterval,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutResult:
        """
        Start a checkout session for subscription.

        Args:
            session: Database session
            user: User model
            interval: Billing interval ("monthly" or "yearly")
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancel

        Returns:
            CheckoutResult with session URL
        """
        customer_id = await self.get_or_create_customer(session, user)

        stripe_svc = get_stripe_service()
        return await stripe_svc.create_checkout_session(
            customer_id=customer_id,
            plan=interval,
            success_url=success_url,
            cancel_url=cancel_url,
        )

    async def get_billing_portal_url(
        self,
        session: AsyncSession,
        user: User,
        return_url: str,
    ) -> PortalResult:
        """
        Get billing portal URL for subscription management.

        Args:
            session: Database session
            user: User model
            return_url: URL to return to after portal

        Returns:
            PortalResult with portal URL
        """
        customer_id = await self.get_or_create_customer(session, user)

        stripe_svc = get_stripe_service()
        return await stripe_svc.create_portal_session(
            customer_id=customer_id,
            return_url=return_url,
        )

    async def sync_subscription_status(
        self,
        session: AsyncSession,
        user: User,
        subscription: SubscriptionInfo,
    ) -> User:
        """
        Sync subscription status from Stripe to user.

        Args:
            session: Database session
            user: User model
            subscription: Subscription info from Stripe

        Returns:
            Updated user
        """
        user.subscription_status = subscription.status

        # Map subscription status to plan
        if subscription.status in ("active", "trialing"):
            user.subscription_plan = subscription.plan or "pro"
        elif subscription.status == "canceled":
            user.subscription_plan = "free"
        # past_due, incomplete keep current plan

        session.add(user)
        await session.flush()

        logger.info(
            f"Synced subscription for user {user.id}: "
            f"plan={user.subscription_plan}, status={user.subscription_status}"
        )
        return user

    async def cancel_subscription(
        self,
        session: AsyncSession,
        user: User,
        at_period_end: bool = True,
    ) -> SubscriptionInfo | None:
        """
        Cancel user's subscription.

        Args:
            session: Database session
            user: User model
            at_period_end: If True, cancel at end of billing period

        Returns:
            Updated SubscriptionInfo or None if no subscription
        """
        if not user.stripe_customer_id:
            return None

        stripe_svc = get_stripe_service()
        subs = await stripe_svc.get_customer_subscriptions(user.stripe_customer_id)

        if not subs:
            return None

        # Cancel the first active subscription
        active_sub = next(
            (s for s in subs if s.status in ("active", "trialing")),
            None,
        )
        if not active_sub:
            return None

        result = await stripe_svc.cancel_subscription(
            active_sub.id,
            at_period_end=at_period_end,
        )

        # Update user status
        await self.sync_subscription_status(session, user, result)
        return result

    async def resume_subscription(
        self,
        session: AsyncSession,
        user: User,
    ) -> SubscriptionInfo | None:
        """
        Resume a cancelled subscription (before period ends).

        Args:
            session: Database session
            user: User model

        Returns:
            Updated SubscriptionInfo or None if no subscription
        """
        if not user.stripe_customer_id:
            return None

        stripe_svc = get_stripe_service()
        subs = await stripe_svc.get_customer_subscriptions(user.stripe_customer_id)

        # Find subscription pending cancellation
        pending_cancel = next(
            (s for s in subs if s.status == "active" and s.cancel_at_period_end),
            None,
        )
        if not pending_cancel:
            return None

        result = await stripe_svc.resume_subscription(pending_cancel.id)
        await self.sync_subscription_status(session, user, result)
        return result

    async def get_invoices(
        self,
        user: User,
        limit: int = 10,
    ) -> list[dict]:
        """
        Get user's invoices.

        Args:
            user: User model
            limit: Max number of invoices

        Returns:
            List of invoice dictionaries
        """
        if not user.stripe_customer_id:
            return []

        stripe_svc = get_stripe_service()
        return await stripe_svc.get_invoices(user.stripe_customer_id, limit)

    def get_current_plan(self, user: User) -> PlanType:
        """
        Get user's current plan.

        Args:
            user: User model

        Returns:
            Plan type (free, pro, or enterprise)
        """
        if user.subscription_status in ("active", "trialing"):
            return user.subscription_plan or "free"  # type: ignore
        return "free"

    async def handle_checkout_completed(
        self,
        session: AsyncSession,
        customer_id: str,
        subscription_id: str,
    ) -> User | None:
        """
        Handle successful checkout completion.

        Args:
            session: Database session
            customer_id: Stripe customer ID
            subscription_id: Stripe subscription ID

        Returns:
            Updated user or None
        """
        # Find user by Stripe customer ID
        result = await session.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"No user found for Stripe customer: {customer_id}")
            return None

        # Get subscription details
        stripe_svc = get_stripe_service()
        sub_info = await stripe_svc.get_subscription(subscription_id)

        if sub_info:
            await self.sync_subscription_status(session, user, sub_info)

        return user

    async def handle_subscription_updated(
        self,
        session: AsyncSession,
        customer_id: str,
        subscription_id: str,
    ) -> User | None:
        """
        Handle subscription update (plan change, renewal, etc.).

        Args:
            session: Database session
            customer_id: Stripe customer ID
            subscription_id: Stripe subscription ID

        Returns:
            Updated user or None
        """
        return await self.handle_checkout_completed(session, customer_id, subscription_id)

    async def handle_subscription_deleted(
        self,
        session: AsyncSession,
        customer_id: str,
    ) -> User | None:
        """
        Handle subscription deletion/cancellation.

        Args:
            session: Database session
            customer_id: Stripe customer ID

        Returns:
            Updated user or None
        """
        result = await session.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"No user found for Stripe customer: {customer_id}")
            return None

        user.subscription_status = "canceled"
        user.subscription_plan = "free"
        session.add(user)
        await session.flush()

        logger.info(f"Subscription deleted for user {user.id}")
        return user


# Singleton instance
billing_service = BillingService()
