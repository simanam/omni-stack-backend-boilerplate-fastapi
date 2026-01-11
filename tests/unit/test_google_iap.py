"""
Tests for Google Play Store In-App Purchase service.
"""

import base64
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.business.iap_service import IAPService
from app.models.user import User
from app.services.payments.google_iap_service import (
    GoogleIAPService,
    GoogleNotification,
    GoogleNotificationType,
    GooglePubSubMessage,
    GoogleSubscriptionNotification,
    get_google_iap_service,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def google_service() -> GoogleIAPService:
    """Create Google IAP service instance."""
    return GoogleIAPService()


@pytest.fixture
def mock_pub_sub_message() -> GooglePubSubMessage:
    """Create mock Pub/Sub message."""
    return GooglePubSubMessage(
        message_id="msg_123",
        publish_time="2024-01-10T12:00:00Z",
        data={
            "version": "1.0",
            "packageName": "com.example.myapp",
            "eventTimeMillis": "1704888000000",
            "subscriptionNotification": {
                "notificationType": 4,
                "purchaseToken": "purchase_token_123",
                "subscriptionId": "premium_monthly",
            },
        },
        subscription="projects/my-project/subscriptions/my-sub",
    )


@pytest.fixture
def mock_subscription_notification() -> GoogleSubscriptionNotification:
    """Create mock subscription notification."""
    return GoogleSubscriptionNotification(
        version="1.0",
        package_name="com.example.myapp",
        event_time_millis=1704888000000,
        notification_type=GoogleNotificationType.SUBSCRIPTION_PURCHASED,
        purchase_token="purchase_token_123",
        subscription_id="premium_monthly",
    )


@pytest.fixture
def mock_notification(mock_subscription_notification) -> GoogleNotification:
    """Create mock Google notification."""
    return GoogleNotification(
        version="1.0",
        package_name="com.example.myapp",
        event_time_millis=1704888000000,
        subscription_notification=mock_subscription_notification,
        one_time_notification=None,
        test_notification=None,
        raw_data={
            "version": "1.0",
            "packageName": "com.example.myapp",
            "subscriptionNotification": {
                "notificationType": 4,
                "purchaseToken": "purchase_token_123",
                "subscriptionId": "premium_monthly",
            },
        },
    )


@pytest.fixture
def mock_user() -> User:
    """Create mock user with Google subscription."""
    return User(
        id="user_123",
        email="test@example.com",
        full_name="Test User",
        google_purchase_token="purchase_token_123",
        subscription_status="active",
        subscription_plan="pro",
    )


# =============================================================================
# GoogleIAPService Tests
# =============================================================================


class TestGoogleIAPService:
    """Tests for GoogleIAPService class."""

    def test_decode_pub_sub_message(self, google_service):
        """decode_pub_sub_message should decode Pub/Sub message correctly."""
        data = {
            "version": "1.0",
            "packageName": "com.example.myapp",
            "subscriptionNotification": {
                "notificationType": 4,
                "purchaseToken": "token123",
                "subscriptionId": "premium",
            },
        }
        encoded_data = base64.b64encode(json.dumps(data).encode()).decode()

        request_body = {
            "message": {
                "data": encoded_data,
                "messageId": "msg_123",
                "publishTime": "2024-01-10T12:00:00Z",
            },
            "subscription": "projects/my-project/subscriptions/my-sub",
        }

        result = google_service.decode_pub_sub_message(request_body)

        assert result.message_id == "msg_123"
        assert result.publish_time == "2024-01-10T12:00:00Z"
        assert result.data["packageName"] == "com.example.myapp"
        assert result.data["subscriptionNotification"]["notificationType"] == 4

    def test_decode_pub_sub_message_empty_data(self, google_service):
        """decode_pub_sub_message should handle empty data."""
        request_body = {
            "message": {
                "data": "",
                "messageId": "msg_123",
            },
        }

        result = google_service.decode_pub_sub_message(request_body)

        assert result.message_id == "msg_123"
        assert result.data == {}

    def test_parse_notification_subscription(self, google_service, mock_pub_sub_message):
        """parse_notification should parse subscription notification."""
        result = google_service.parse_notification(mock_pub_sub_message)

        assert result.package_name == "com.example.myapp"
        assert result.subscription_notification is not None
        assert result.subscription_notification.notification_type == GoogleNotificationType.SUBSCRIPTION_PURCHASED
        assert result.subscription_notification.purchase_token == "purchase_token_123"
        assert result.subscription_notification.subscription_id == "premium_monthly"
        assert result.one_time_notification is None
        assert result.test_notification is None

    def test_parse_notification_test(self, google_service):
        """parse_notification should parse test notification."""
        pub_sub_message = GooglePubSubMessage(
            message_id="msg_123",
            publish_time="2024-01-10T12:00:00Z",
            data={
                "version": "1.0",
                "packageName": "com.example.myapp",
                "testNotification": {"version": "1.0"},
            },
            subscription=None,
        )

        result = google_service.parse_notification(pub_sub_message)

        assert result.test_notification is not None
        assert result.subscription_notification is None

    def test_verify_package_name_matches(self, google_service, mock_notification):
        """verify_package_name should return True when package name matches."""
        with patch("app.services.payments.google_iap_service.settings") as mock_settings:
            mock_settings.GOOGLE_PLAY_PACKAGE_NAME = "com.example.myapp"

            result = google_service.verify_package_name(mock_notification)

            assert result is True

    def test_verify_package_name_mismatch(self, google_service, mock_notification):
        """verify_package_name should return False when package name doesn't match."""
        with patch("app.services.payments.google_iap_service.settings") as mock_settings:
            mock_settings.GOOGLE_PLAY_PACKAGE_NAME = "com.other.app"

            result = google_service.verify_package_name(mock_notification)

            assert result is False

    def test_verify_package_name_not_configured(self, google_service, mock_notification):
        """verify_package_name should return True when not configured."""
        with patch("app.services.payments.google_iap_service.settings") as mock_settings:
            mock_settings.GOOGLE_PLAY_PACKAGE_NAME = None

            result = google_service.verify_package_name(mock_notification)

            assert result is True

    def test_is_subscription_active_purchased(self, google_service, mock_subscription_notification):
        """is_subscription_active should return True for SUBSCRIPTION_PURCHASED."""
        mock_subscription_notification.notification_type = GoogleNotificationType.SUBSCRIPTION_PURCHASED

        result = google_service.is_subscription_active(mock_subscription_notification)

        assert result is True

    def test_is_subscription_active_renewed(self, google_service, mock_subscription_notification):
        """is_subscription_active should return True for SUBSCRIPTION_RENEWED."""
        mock_subscription_notification.notification_type = GoogleNotificationType.SUBSCRIPTION_RENEWED

        result = google_service.is_subscription_active(mock_subscription_notification)

        assert result is True

    def test_is_subscription_active_recovered(self, google_service, mock_subscription_notification):
        """is_subscription_active should return True for SUBSCRIPTION_RECOVERED."""
        mock_subscription_notification.notification_type = GoogleNotificationType.SUBSCRIPTION_RECOVERED

        result = google_service.is_subscription_active(mock_subscription_notification)

        assert result is True

    def test_is_subscription_active_expired(self, google_service, mock_subscription_notification):
        """is_subscription_active should return False for SUBSCRIPTION_EXPIRED."""
        mock_subscription_notification.notification_type = GoogleNotificationType.SUBSCRIPTION_EXPIRED

        result = google_service.is_subscription_active(mock_subscription_notification)

        assert result is False

    def test_is_subscription_in_grace_period(self, google_service, mock_subscription_notification):
        """is_subscription_in_grace_period should return True for grace period."""
        mock_subscription_notification.notification_type = GoogleNotificationType.SUBSCRIPTION_IN_GRACE_PERIOD

        result = google_service.is_subscription_in_grace_period(mock_subscription_notification)

        assert result is True

    def test_is_subscription_in_grace_period_on_hold(self, google_service, mock_subscription_notification):
        """is_subscription_in_grace_period should return True for on hold."""
        mock_subscription_notification.notification_type = GoogleNotificationType.SUBSCRIPTION_ON_HOLD

        result = google_service.is_subscription_in_grace_period(mock_subscription_notification)

        assert result is True

    def test_should_cancel_subscription_expired(self, google_service, mock_subscription_notification):
        """should_cancel_subscription should return True for SUBSCRIPTION_EXPIRED."""
        mock_subscription_notification.notification_type = GoogleNotificationType.SUBSCRIPTION_EXPIRED

        result = google_service.should_cancel_subscription(mock_subscription_notification)

        assert result is True

    def test_should_cancel_subscription_revoked(self, google_service, mock_subscription_notification):
        """should_cancel_subscription should return True for SUBSCRIPTION_REVOKED."""
        mock_subscription_notification.notification_type = GoogleNotificationType.SUBSCRIPTION_REVOKED

        result = google_service.should_cancel_subscription(mock_subscription_notification)

        assert result is True

    def test_should_cancel_subscription_active(self, google_service, mock_subscription_notification):
        """should_cancel_subscription should return False for active subscription."""
        mock_subscription_notification.notification_type = GoogleNotificationType.SUBSCRIPTION_RENEWED

        result = google_service.should_cancel_subscription(mock_subscription_notification)

        assert result is False

    def test_is_subscription_paused(self, google_service, mock_subscription_notification):
        """is_subscription_paused should return True for SUBSCRIPTION_PAUSED."""
        mock_subscription_notification.notification_type = GoogleNotificationType.SUBSCRIPTION_PAUSED

        result = google_service.is_subscription_paused(mock_subscription_notification)

        assert result is True

    def test_get_notification_type_name(self, google_service):
        """get_notification_type_name should return readable name."""
        result = google_service.get_notification_type_name(GoogleNotificationType.SUBSCRIPTION_PURCHASED)

        assert result == "SUBSCRIPTION_PURCHASED"


class TestGoogleIAPServiceSingleton:
    """Tests for Google IAP service singleton."""

    def test_get_google_iap_service_returns_instance(self):
        """get_google_iap_service should return a GoogleIAPService instance."""
        service = get_google_iap_service()

        assert isinstance(service, GoogleIAPService)

    def test_get_google_iap_service_returns_same_instance(self):
        """get_google_iap_service should return the same instance."""
        service1 = get_google_iap_service()
        service2 = get_google_iap_service()

        assert service1 is service2


# =============================================================================
# IAPService Google Integration Tests
# =============================================================================


class TestIAPServiceGoogle:
    """Tests for IAPService Google-related methods."""

    @pytest.mark.asyncio
    async def test_handle_google_notification_success(self, mock_subscription_notification, mock_user):
        """handle_google_notification should update user subscription."""
        from unittest.mock import MagicMock

        iap_service = IAPService()
        mock_session = AsyncMock()

        # Mock database query to return user - use MagicMock for sync method
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        with patch("app.business.iap_service.get_google_iap_service") as mock_get_service:
            mock_google_service = MagicMock()
            mock_google_service.is_subscription_active.return_value = True
            mock_google_service.should_cancel_subscription.return_value = False
            mock_google_service.is_subscription_in_grace_period.return_value = False
            mock_google_service.is_subscription_paused.return_value = False
            mock_google_service.get_notification_type_name.return_value = "SUBSCRIPTION_PURCHASED"
            mock_get_service.return_value = mock_google_service

            result = await iap_service.handle_google_notification(mock_session, mock_subscription_notification)

            assert result is not None
            assert result.id == "user_123"
            mock_session.add.assert_called()
            mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_handle_google_notification_user_not_found(self, mock_subscription_notification):
        """handle_google_notification should return None when user not found."""
        from unittest.mock import MagicMock

        iap_service = IAPService()
        mock_session = AsyncMock()

        # Mock database query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await iap_service.handle_google_notification(mock_session, mock_subscription_notification)

        assert result is None

    @pytest.mark.asyncio
    async def test_link_google_subscription(self, mock_user):
        """link_google_subscription should set Google purchase token."""
        iap_service = IAPService()
        mock_session = AsyncMock()

        mock_user.google_purchase_token = None

        result = await iap_service.link_google_subscription(
            session=mock_session,
            user=mock_user,
            purchase_token="new_token_456",
            subscription_id="premium_monthly",
        )

        assert result.google_purchase_token == "new_token_456"
        assert result.subscription_status == "active"
        assert result.subscription_plan == "pro"
        mock_session.add.assert_called()
        mock_session.flush.assert_called()

    def test_get_plan_from_google_product_pro(self):
        """_get_plan_from_google_product should return 'pro' for pro products."""
        iap_service = IAPService()

        result = iap_service._get_plan_from_google_product("pro_monthly")

        assert result == "pro"

    def test_get_plan_from_google_product_premium(self):
        """_get_plan_from_google_product should return 'pro' for premium products."""
        iap_service = IAPService()

        result = iap_service._get_plan_from_google_product("premium_yearly")

        assert result == "pro"

    def test_get_plan_from_google_product_enterprise(self):
        """_get_plan_from_google_product should return 'enterprise' for enterprise products."""
        iap_service = IAPService()

        result = iap_service._get_plan_from_google_product("enterprise_monthly")

        assert result == "enterprise"

    @pytest.mark.asyncio
    async def test_get_user_by_google_token(self, mock_user):
        """get_user_by_google_token should find user by purchase token."""
        from unittest.mock import MagicMock

        iap_service = IAPService()
        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        result = await iap_service.get_user_by_google_token(mock_session, "purchase_token_123")

        assert result is not None
        assert result.id == "user_123"


class TestGoogleNotificationTypes:
    """Tests for Google notification type enums."""

    def test_notification_type_values(self):
        """GoogleNotificationType should have correct integer values."""
        assert GoogleNotificationType.SUBSCRIPTION_RECOVERED == 1
        assert GoogleNotificationType.SUBSCRIPTION_RENEWED == 2
        assert GoogleNotificationType.SUBSCRIPTION_CANCELED == 3
        assert GoogleNotificationType.SUBSCRIPTION_PURCHASED == 4
        assert GoogleNotificationType.SUBSCRIPTION_EXPIRED == 13
        assert GoogleNotificationType.SUBSCRIPTION_REVOKED == 12

    def test_notification_type_names(self):
        """GoogleNotificationType should have correct names."""
        assert GoogleNotificationType.SUBSCRIPTION_PURCHASED.name == "SUBSCRIPTION_PURCHASED"
        assert GoogleNotificationType.SUBSCRIPTION_EXPIRED.name == "SUBSCRIPTION_EXPIRED"
