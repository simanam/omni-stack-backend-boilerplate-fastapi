"""
Google Play Store In-App Purchase service.
Handles Real-time Developer Notifications (RTDN) for subscription events.

Reference: https://developer.android.com/google/play/billing/rtdn-reference
"""

import base64
import json
import logging
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleNotificationType(IntEnum):
    """Google Play subscription notification types."""

    # Subscription notifications
    SUBSCRIPTION_RECOVERED = 1  # Subscription recovered from account hold
    SUBSCRIPTION_RENEWED = 2  # Active subscription renewed
    SUBSCRIPTION_CANCELED = 3  # Subscription canceled (voluntary or involuntary)
    SUBSCRIPTION_PURCHASED = 4  # New subscription purchased
    SUBSCRIPTION_ON_HOLD = 5  # Subscription entered account hold
    SUBSCRIPTION_IN_GRACE_PERIOD = 6  # Subscription entered grace period
    SUBSCRIPTION_RESTARTED = 7  # User restarted subscription
    SUBSCRIPTION_PRICE_CHANGE_CONFIRMED = 8  # User confirmed price change
    SUBSCRIPTION_DEFERRED = 9  # Subscription deferred
    SUBSCRIPTION_PAUSED = 10  # Subscription paused
    SUBSCRIPTION_PAUSE_SCHEDULE_CHANGED = 11  # Pause schedule changed
    SUBSCRIPTION_REVOKED = 12  # Subscription revoked before expiration
    SUBSCRIPTION_EXPIRED = 13  # Subscription expired
    SUBSCRIPTION_PENDING_PURCHASE_CANCELED = 20  # Pending purchase canceled


class GoogleOneTimeNotificationType(IntEnum):
    """Google Play one-time product notification types."""

    ONE_TIME_PRODUCT_PURCHASED = 1
    ONE_TIME_PRODUCT_CANCELED = 2


@dataclass
class GooglePubSubMessage:
    """Parsed Google Pub/Sub message."""

    message_id: str
    publish_time: str
    data: dict[str, Any]
    subscription: str | None


@dataclass
class GoogleSubscriptionNotification:
    """Parsed Google Play subscription notification."""

    version: str
    package_name: str
    event_time_millis: int
    notification_type: GoogleNotificationType
    purchase_token: str
    subscription_id: str


@dataclass
class GoogleOneTimeNotification:
    """Parsed Google Play one-time product notification."""

    version: str
    package_name: str
    event_time_millis: int
    notification_type: GoogleOneTimeNotificationType
    purchase_token: str
    sku: str


@dataclass
class GoogleNotification:
    """Unified Google Play notification."""

    version: str
    package_name: str
    event_time_millis: int
    subscription_notification: GoogleSubscriptionNotification | None
    one_time_notification: GoogleOneTimeNotification | None
    test_notification: dict[str, Any] | None
    raw_data: dict[str, Any]


class GoogleIAPService:
    """
    Service for handling Google Play In-App Purchase notifications.

    Handles Real-time Developer Notifications (RTDN) from Pub/Sub.
    """

    def __init__(self):
        self._android_publisher_client = None

    def decode_pub_sub_message(self, request_body: dict[str, Any]) -> GooglePubSubMessage:
        """
        Decode a Pub/Sub push message from Google.

        Args:
            request_body: The raw request body from the Pub/Sub push endpoint

        Returns:
            GooglePubSubMessage with decoded data
        """
        message = request_body.get("message", {})
        data_b64 = message.get("data", "")

        # Decode base64 data
        if data_b64:
            data_bytes = base64.b64decode(data_b64)
            data = json.loads(data_bytes)
        else:
            data = {}

        return GooglePubSubMessage(
            message_id=message.get("messageId", ""),
            publish_time=message.get("publishTime", ""),
            data=data,
            subscription=request_body.get("subscription"),
        )

    def parse_notification(self, pub_sub_message: GooglePubSubMessage) -> GoogleNotification:
        """
        Parse a Google Play Developer Notification from Pub/Sub data.

        Args:
            pub_sub_message: Decoded Pub/Sub message

        Returns:
            GoogleNotification with parsed subscription or one-time notification
        """
        data = pub_sub_message.data

        version = data.get("version", "1.0")
        package_name = data.get("packageName", "")
        event_time_millis = int(data.get("eventTimeMillis", 0))

        subscription_notification = None
        one_time_notification = None
        test_notification = None

        # Parse subscription notification
        if "subscriptionNotification" in data:
            sub_data = data["subscriptionNotification"]
            subscription_notification = GoogleSubscriptionNotification(
                version=version,
                package_name=package_name,
                event_time_millis=event_time_millis,
                notification_type=GoogleNotificationType(sub_data.get("notificationType", 0)),
                purchase_token=sub_data.get("purchaseToken", ""),
                subscription_id=sub_data.get("subscriptionId", ""),
            )

        # Parse one-time product notification
        if "oneTimeProductNotification" in data:
            otp_data = data["oneTimeProductNotification"]
            one_time_notification = GoogleOneTimeNotification(
                version=version,
                package_name=package_name,
                event_time_millis=event_time_millis,
                notification_type=GoogleOneTimeNotificationType(otp_data.get("notificationType", 0)),
                purchase_token=otp_data.get("purchaseToken", ""),
                sku=otp_data.get("sku", ""),
            )

        # Parse test notification
        if "testNotification" in data:
            test_notification = data["testNotification"]

        return GoogleNotification(
            version=version,
            package_name=package_name,
            event_time_millis=event_time_millis,
            subscription_notification=subscription_notification,
            one_time_notification=one_time_notification,
            test_notification=test_notification,
            raw_data=data,
        )

    def verify_package_name(self, notification: GoogleNotification) -> bool:
        """Verify the notification is for our app's package name."""
        if not settings.GOOGLE_PLAY_PACKAGE_NAME:
            logger.warning("GOOGLE_PLAY_PACKAGE_NAME not configured, skipping verification")
            return True

        return notification.package_name == settings.GOOGLE_PLAY_PACKAGE_NAME

    def is_subscription_active(self, notification: GoogleSubscriptionNotification) -> bool:
        """
        Determine if the subscription should be considered active based on notification.
        """
        active_types = {
            GoogleNotificationType.SUBSCRIPTION_PURCHASED,
            GoogleNotificationType.SUBSCRIPTION_RENEWED,
            GoogleNotificationType.SUBSCRIPTION_RECOVERED,
            GoogleNotificationType.SUBSCRIPTION_RESTARTED,
            GoogleNotificationType.SUBSCRIPTION_PRICE_CHANGE_CONFIRMED,
        }
        return notification.notification_type in active_types

    def is_subscription_in_grace_period(self, notification: GoogleSubscriptionNotification) -> bool:
        """Check if subscription is in grace period or on hold."""
        grace_types = {
            GoogleNotificationType.SUBSCRIPTION_IN_GRACE_PERIOD,
            GoogleNotificationType.SUBSCRIPTION_ON_HOLD,
        }
        return notification.notification_type in grace_types

    def should_cancel_subscription(self, notification: GoogleSubscriptionNotification) -> bool:
        """
        Determine if the subscription should be cancelled based on notification.
        """
        cancel_types = {
            GoogleNotificationType.SUBSCRIPTION_EXPIRED,
            GoogleNotificationType.SUBSCRIPTION_REVOKED,
        }
        return notification.notification_type in cancel_types

    def is_subscription_paused(self, notification: GoogleSubscriptionNotification) -> bool:
        """Check if subscription is paused."""
        return notification.notification_type == GoogleNotificationType.SUBSCRIPTION_PAUSED

    def get_notification_type_name(self, notification_type: GoogleNotificationType) -> str:
        """Get human-readable name for notification type."""
        return notification_type.name

    async def verify_purchase(self, package_name: str, subscription_id: str, purchase_token: str) -> dict[str, Any] | None:
        """
        Verify a subscription purchase with Google Play Developer API.

        Note: This requires google-api-python-client and service account credentials.
        In production, you should implement this to verify purchases.

        Args:
            package_name: Android app package name
            subscription_id: Subscription product ID
            purchase_token: Purchase token from the app

        Returns:
            Subscription purchase details from Google, or None if not configured
        """
        if not settings.GOOGLE_PLAY_SERVICE_ACCOUNT_JSON:
            logger.warning("Google Play service account not configured, skipping verification")
            return None

        try:
            # Lazy import to avoid dependency issues if not using Google
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            # Decode service account JSON from base64
            service_account_info = json.loads(
                base64.b64decode(settings.GOOGLE_PLAY_SERVICE_ACCOUNT_JSON)
            )

            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=["https://www.googleapis.com/auth/androidpublisher"],
            )

            # Build the Android Publisher service
            service = build("androidpublisher", "v3", credentials=credentials)

            # Get subscription purchase details
            result = (
                service.purchases()
                .subscriptions()
                .get(
                    packageName=package_name,
                    subscriptionId=subscription_id,
                    token=purchase_token,
                )
                .execute()
            )

            return result

        except ImportError:
            logger.warning(
                "google-api-python-client not installed. "
                "Install with: pip install google-api-python-client google-auth"
            )
            return None
        except Exception as e:
            logger.error(f"Error verifying Google Play purchase: {e}")
            return None


# Singleton instance
_google_iap_service: GoogleIAPService | None = None


def get_google_iap_service() -> GoogleIAPService:
    """Get or create the Google IAP service instance."""
    global _google_iap_service
    if _google_iap_service is None:
        _google_iap_service = GoogleIAPService()
    return _google_iap_service
