"""
In-App Purchase business logic service.
Handles subscription sync for Apple App Store and Google Play Store.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.user import User
from app.services.payments.apple_iap_service import (
    AppleNotification,
    AppleNotificationType,
    get_apple_iap_service,
)
from app.services.payments.google_iap_service import (
    GoogleNotificationType,
    GoogleSubscriptionNotification,
    get_google_iap_service,
)

logger = logging.getLogger(__name__)


class IAPService:
    """
    Business logic for mobile In-App Purchase subscription management.

    Handles subscription lifecycle events from Apple App Store and Google Play Store.
    """

    # =========================================================================
    # Apple App Store
    # =========================================================================

    async def handle_apple_notification(
        self,
        session: AsyncSession,
        notification: AppleNotification,
    ) -> User | None:
        """
        Handle an Apple App Store Server Notification.

        Finds the user by original_transaction_id and updates subscription status.

        Args:
            session: Database session
            notification: Parsed Apple notification

        Returns:
            Updated User, or None if user not found
        """
        apple_service = get_apple_iap_service()

        # Verify bundle ID
        if not apple_service.verify_bundle_id(notification):
            logger.warning(
                f"Bundle ID mismatch: got {notification.bundle_id}"
            )
            return None

        # Get the original transaction ID
        if not notification.transaction_info:
            logger.warning("No transaction info in Apple notification")
            return None

        original_transaction_id = notification.transaction_info.original_transaction_id

        # Find user by original transaction ID
        result = await session.execute(
            select(User).where(User.apple_original_transaction_id == original_transaction_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(
                f"No user found for Apple original_transaction_id: {original_transaction_id}"
            )
            return None

        # Update subscription based on notification type
        await self._sync_apple_subscription(session, user, notification)

        return user

    async def _sync_apple_subscription(
        self,
        session: AsyncSession,
        user: User,
        notification: AppleNotification,
    ) -> None:
        """
        Sync user subscription status from Apple notification.
        """
        apple_service = get_apple_iap_service()

        notification_type = notification.notification_type
        logger.info(
            f"Processing Apple notification {notification_type.value} "
            f"for user {user.id}"
        )

        # Determine new subscription status
        if apple_service.is_subscription_active(notification):
            user.subscription_status = "active"
            user.subscription_plan = self._get_plan_from_apple_product(
                notification.transaction_info.product_id if notification.transaction_info else ""
            )

        elif apple_service.should_cancel_subscription(notification):
            user.subscription_status = "canceled"
            user.subscription_plan = "free"

        elif notification_type == AppleNotificationType.DID_FAIL_TO_RENEW:
            # Check if in grace period
            if notification.renewal_info and notification.renewal_info.is_in_billing_retry_period:
                user.subscription_status = "past_due"
            else:
                user.subscription_status = "incomplete"

        elif notification_type == AppleNotificationType.DID_CHANGE_RENEWAL_STATUS:
            # Auto-renew was enabled or disabled
            # Keep current status, just log the change
            auto_renew = apple_service.get_auto_renew_status(notification)
            logger.info(f"Apple auto-renew status changed to: {auto_renew}")

        session.add(user)
        await session.flush()

    def _get_plan_from_apple_product(self, product_id: str) -> str:
        """
        Map Apple product ID to subscription plan.

        Override this method to customize plan mapping.
        """
        # Default mapping - customize based on your product IDs
        product_id_lower = product_id.lower()
        if "enterprise" in product_id_lower:
            return "enterprise"
        elif "pro" in product_id_lower or "premium" in product_id_lower:
            return "pro"
        return "pro"  # Default to pro for any paid subscription

    async def link_apple_subscription(
        self,
        session: AsyncSession,
        user: User,
        original_transaction_id: str,
        product_id: str | None = None,
    ) -> User:
        """
        Link an Apple subscription to a user.

        Called when a user first purchases or restores a subscription.

        Args:
            session: Database session
            user: User to link subscription to
            original_transaction_id: Apple's original transaction ID
            product_id: Optional product ID for plan determination

        Returns:
            Updated User
        """
        user.apple_original_transaction_id = original_transaction_id
        user.subscription_status = "active"
        user.subscription_plan = self._get_plan_from_apple_product(product_id or "")

        session.add(user)
        await session.flush()

        logger.info(
            f"Linked Apple subscription {original_transaction_id} to user {user.id}"
        )
        return user

    # =========================================================================
    # Google Play Store
    # =========================================================================

    async def handle_google_notification(
        self,
        session: AsyncSession,
        notification: GoogleSubscriptionNotification,
    ) -> User | None:
        """
        Handle a Google Play subscription notification.

        Finds the user by purchase_token and updates subscription status.

        Args:
            session: Database session
            notification: Parsed Google subscription notification

        Returns:
            Updated User, or None if user not found
        """
        # Find user by purchase token
        result = await session.execute(
            select(User).where(User.google_purchase_token == notification.purchase_token)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(
                f"No user found for Google purchase_token: {notification.purchase_token[:20]}..."
            )
            return None

        # Update subscription based on notification type
        await self._sync_google_subscription(session, user, notification)

        return user

    async def _sync_google_subscription(
        self,
        session: AsyncSession,
        user: User,
        notification: GoogleSubscriptionNotification,
    ) -> None:
        """
        Sync user subscription status from Google notification.
        """
        google_service = get_google_iap_service()

        notification_type = notification.notification_type
        logger.info(
            f"Processing Google notification {google_service.get_notification_type_name(notification_type)} "
            f"for user {user.id}"
        )

        # Determine new subscription status
        if google_service.is_subscription_active(notification):
            user.subscription_status = "active"
            user.subscription_plan = self._get_plan_from_google_product(
                notification.subscription_id
            )

        elif google_service.should_cancel_subscription(notification):
            user.subscription_status = "canceled"
            user.subscription_plan = "free"

        elif google_service.is_subscription_in_grace_period(notification):
            user.subscription_status = "past_due"

        elif google_service.is_subscription_paused(notification):
            # Paused subscriptions - keep plan but mark as paused
            user.subscription_status = "incomplete"

        elif notification_type == GoogleNotificationType.SUBSCRIPTION_CANCELED:
            # Canceled but not expired yet - user will have access until period end
            user.subscription_status = "active"  # or you could track cancel_at_period_end

        session.add(user)
        await session.flush()

    def _get_plan_from_google_product(self, subscription_id: str) -> str:
        """
        Map Google subscription ID to subscription plan.

        Override this method to customize plan mapping.
        """
        # Default mapping - customize based on your subscription IDs
        subscription_id_lower = subscription_id.lower()
        if "enterprise" in subscription_id_lower:
            return "enterprise"
        elif "pro" in subscription_id_lower or "premium" in subscription_id_lower:
            return "pro"
        return "pro"  # Default to pro for any paid subscription

    async def link_google_subscription(
        self,
        session: AsyncSession,
        user: User,
        purchase_token: str,
        subscription_id: str | None = None,
    ) -> User:
        """
        Link a Google Play subscription to a user.

        Called when a user first purchases a subscription.

        Args:
            session: Database session
            user: User to link subscription to
            purchase_token: Google Play purchase token
            subscription_id: Optional subscription ID for plan determination

        Returns:
            Updated User
        """
        user.google_purchase_token = purchase_token
        user.subscription_status = "active"
        user.subscription_plan = self._get_plan_from_google_product(subscription_id or "")

        session.add(user)
        await session.flush()

        logger.info(f"Linked Google subscription to user {user.id}")
        return user

    # =========================================================================
    # Common Utilities
    # =========================================================================

    async def get_user_by_apple_transaction(
        self,
        session: AsyncSession,
        original_transaction_id: str,
    ) -> User | None:
        """Find a user by Apple original transaction ID."""
        result = await session.execute(
            select(User).where(User.apple_original_transaction_id == original_transaction_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_google_token(
        self,
        session: AsyncSession,
        purchase_token: str,
    ) -> User | None:
        """Find a user by Google purchase token."""
        result = await session.execute(
            select(User).where(User.google_purchase_token == purchase_token)
        )
        return result.scalar_one_or_none()


# Singleton instance
iap_service = IAPService()
