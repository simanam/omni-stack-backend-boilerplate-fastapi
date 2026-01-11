"""
Tests for Apple App Store In-App Purchase service.
"""

import base64
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.business.iap_service import IAPService
from app.models.user import User
from app.services.payments.apple_iap_service import (
    AppleIAPService,
    AppleNotification,
    AppleNotificationType,
    AppleRenewalInfo,
    AppleSubtype,
    AppleTransactionInfo,
    get_apple_iap_service,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def apple_service() -> AppleIAPService:
    """Create Apple IAP service instance."""
    return AppleIAPService()


@pytest.fixture
def mock_transaction_info() -> AppleTransactionInfo:
    """Create mock transaction info."""
    return AppleTransactionInfo(
        transaction_id="txn_123",
        original_transaction_id="orig_txn_123",
        product_id="com.example.pro_monthly",
        bundle_id="com.example.myapp",
        purchase_date=1704067200000,
        expires_date=1706745600000,
        quantity=1,
        type="Auto-Renewable Subscription",
        in_app_ownership_type="PURCHASED",
        signed_date=1704067200000,
        environment="Sandbox",
        storefront="USA",
        storefront_id="143441",
        revocation_date=None,
        revocation_reason=None,
        is_upgraded=None,
        offer_type=None,
        offer_identifier=None,
    )


@pytest.fixture
def mock_renewal_info() -> AppleRenewalInfo:
    """Create mock renewal info."""
    return AppleRenewalInfo(
        auto_renew_product_id="com.example.pro_monthly",
        auto_renew_status=1,
        expiration_intent=None,
        grace_period_expires_date=None,
        is_in_billing_retry_period=False,
        offer_identifier=None,
        offer_type=None,
        original_transaction_id="orig_txn_123",
        price_increase_status=None,
        product_id="com.example.pro_monthly",
        signed_date=1704067200000,
        environment="Sandbox",
    )


@pytest.fixture
def mock_notification(mock_transaction_info, mock_renewal_info) -> AppleNotification:
    """Create mock Apple notification."""
    return AppleNotification(
        notification_type=AppleNotificationType.DID_RENEW,
        subtype=None,
        notification_uuid="notif_uuid_123",
        version="2.0",
        signed_date=1704067200000,
        environment="Sandbox",
        bundle_id="com.example.myapp",
        app_apple_id=12345,
        transaction_info=mock_transaction_info,
        renewal_info=mock_renewal_info,
        raw_payload={"notificationType": "DID_RENEW"},
    )


@pytest.fixture
def mock_user() -> User:
    """Create mock user with Apple subscription."""
    return User(
        id="user_123",
        email="test@example.com",
        full_name="Test User",
        apple_original_transaction_id="orig_txn_123",
        subscription_status="active",
        subscription_plan="pro",
    )


# =============================================================================
# AppleIAPService Tests
# =============================================================================


class TestAppleIAPService:
    """Tests for AppleIAPService class."""

    def test_decode_jws_payload_without_verification(self, apple_service):
        """decode_jws_payload should decode JWS without verification."""
        # Create a simple JWS-like structure (header.payload.signature)
        header = base64.urlsafe_b64encode(b'{"alg":"ES256"}').decode().rstrip("=")
        payload_data = {"notificationType": "DID_RENEW", "notificationUUID": "test123"}
        payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip("=")
        signature = base64.urlsafe_b64encode(b"fake_signature").decode().rstrip("=")

        jws = f"{header}.{payload}.{signature}"

        result = apple_service._decode_jws_payload(jws, verify=False)

        assert result["notificationType"] == "DID_RENEW"
        assert result["notificationUUID"] == "test123"

    def test_decode_jws_payload_invalid_format(self, apple_service):
        """decode_jws_payload should raise error for invalid format."""
        with pytest.raises(ValueError, match="Invalid JWS token format"):
            apple_service._decode_jws_payload("not.a.valid.jws.token", verify=False)

    def test_verify_bundle_id_matches(self, apple_service, mock_notification):
        """verify_bundle_id should return True when bundle ID matches."""
        with patch("app.services.payments.apple_iap_service.settings") as mock_settings:
            mock_settings.APPLE_BUNDLE_ID = "com.example.myapp"

            result = apple_service.verify_bundle_id(mock_notification)

            assert result is True

    def test_verify_bundle_id_mismatch(self, apple_service, mock_notification):
        """verify_bundle_id should return False when bundle ID doesn't match."""
        with patch("app.services.payments.apple_iap_service.settings") as mock_settings:
            mock_settings.APPLE_BUNDLE_ID = "com.other.app"

            result = apple_service.verify_bundle_id(mock_notification)

            assert result is False

    def test_verify_bundle_id_not_configured(self, apple_service, mock_notification):
        """verify_bundle_id should return True when not configured."""
        with patch("app.services.payments.apple_iap_service.settings") as mock_settings:
            mock_settings.APPLE_BUNDLE_ID = None

            result = apple_service.verify_bundle_id(mock_notification)

            assert result is True

    def test_is_subscription_active_subscribed(self, apple_service, mock_notification):
        """is_subscription_active should return True for SUBSCRIBED."""
        mock_notification.notification_type = AppleNotificationType.SUBSCRIBED

        result = apple_service.is_subscription_active(mock_notification)

        assert result is True

    def test_is_subscription_active_did_renew(self, apple_service, mock_notification):
        """is_subscription_active should return True for DID_RENEW."""
        mock_notification.notification_type = AppleNotificationType.DID_RENEW

        result = apple_service.is_subscription_active(mock_notification)

        assert result is True

    def test_is_subscription_active_expired(self, apple_service, mock_notification):
        """is_subscription_active should return False for EXPIRED."""
        mock_notification.notification_type = AppleNotificationType.EXPIRED

        result = apple_service.is_subscription_active(mock_notification)

        assert result is False

    def test_is_subscription_active_grace_period(self, apple_service, mock_notification, mock_renewal_info):
        """is_subscription_active should return True in billing retry period."""
        mock_notification.notification_type = AppleNotificationType.DID_FAIL_TO_RENEW
        mock_renewal_info.is_in_billing_retry_period = True
        mock_notification.renewal_info = mock_renewal_info

        result = apple_service.is_subscription_active(mock_notification)

        assert result is True

    def test_should_cancel_subscription_expired(self, apple_service, mock_notification):
        """should_cancel_subscription should return True for EXPIRED."""
        mock_notification.notification_type = AppleNotificationType.EXPIRED

        result = apple_service.should_cancel_subscription(mock_notification)

        assert result is True

    def test_should_cancel_subscription_refund(self, apple_service, mock_notification):
        """should_cancel_subscription should return True for REFUND."""
        mock_notification.notification_type = AppleNotificationType.REFUND

        result = apple_service.should_cancel_subscription(mock_notification)

        assert result is True

    def test_should_cancel_subscription_revoke(self, apple_service, mock_notification):
        """should_cancel_subscription should return True for REVOKE."""
        mock_notification.notification_type = AppleNotificationType.REVOKE

        result = apple_service.should_cancel_subscription(mock_notification)

        assert result is True

    def test_should_cancel_subscription_active(self, apple_service, mock_notification):
        """should_cancel_subscription should return False for active subscription."""
        mock_notification.notification_type = AppleNotificationType.DID_RENEW

        result = apple_service.should_cancel_subscription(mock_notification)

        assert result is False

    def test_get_auto_renew_status_enabled(self, apple_service, mock_notification, mock_renewal_info):
        """get_auto_renew_status should return True when auto-renew is on."""
        mock_renewal_info.auto_renew_status = 1
        mock_notification.renewal_info = mock_renewal_info

        result = apple_service.get_auto_renew_status(mock_notification)

        assert result is True

    def test_get_auto_renew_status_disabled(self, apple_service, mock_notification, mock_renewal_info):
        """get_auto_renew_status should return False when auto-renew is off."""
        mock_renewal_info.auto_renew_status = 0
        mock_notification.renewal_info = mock_renewal_info

        result = apple_service.get_auto_renew_status(mock_notification)

        assert result is False

    def test_get_auto_renew_status_no_renewal_info(self, apple_service, mock_notification):
        """get_auto_renew_status should return None when no renewal info."""
        mock_notification.renewal_info = None

        result = apple_service.get_auto_renew_status(mock_notification)

        assert result is None


class TestAppleIAPServiceSingleton:
    """Tests for Apple IAP service singleton."""

    def test_get_apple_iap_service_returns_instance(self):
        """get_apple_iap_service should return an AppleIAPService instance."""
        service = get_apple_iap_service()

        assert isinstance(service, AppleIAPService)

    def test_get_apple_iap_service_returns_same_instance(self):
        """get_apple_iap_service should return the same instance."""
        service1 = get_apple_iap_service()
        service2 = get_apple_iap_service()

        assert service1 is service2


# =============================================================================
# IAPService Apple Integration Tests
# =============================================================================


class TestIAPServiceApple:
    """Tests for IAPService Apple-related methods."""

    @pytest.mark.asyncio
    async def test_handle_apple_notification_success(self, mock_notification, mock_user):
        """handle_apple_notification should update user subscription."""
        from unittest.mock import MagicMock

        iap_service = IAPService()
        mock_session = AsyncMock()

        # Mock database query to return user - use MagicMock for sync method
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        with patch("app.business.iap_service.get_apple_iap_service") as mock_get_service:
            mock_apple_service = MagicMock()
            mock_apple_service.verify_bundle_id.return_value = True
            mock_apple_service.is_subscription_active.return_value = True
            mock_apple_service.should_cancel_subscription.return_value = False
            mock_get_service.return_value = mock_apple_service

            result = await iap_service.handle_apple_notification(mock_session, mock_notification)

            assert result is not None
            assert result.id == "user_123"
            mock_session.add.assert_called()
            mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_handle_apple_notification_user_not_found(self, mock_notification):
        """handle_apple_notification should return None when user not found."""
        from unittest.mock import MagicMock

        iap_service = IAPService()
        mock_session = AsyncMock()

        # Mock database query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch("app.business.iap_service.get_apple_iap_service") as mock_get_service:
            mock_apple_service = MagicMock()
            mock_apple_service.verify_bundle_id.return_value = True
            mock_get_service.return_value = mock_apple_service

            result = await iap_service.handle_apple_notification(mock_session, mock_notification)

            assert result is None

    @pytest.mark.asyncio
    async def test_handle_apple_notification_bundle_id_mismatch(self, mock_notification):
        """handle_apple_notification should return None for bundle ID mismatch."""
        from unittest.mock import MagicMock

        iap_service = IAPService()
        mock_session = AsyncMock()

        with patch("app.business.iap_service.get_apple_iap_service") as mock_get_service:
            mock_apple_service = MagicMock()
            mock_apple_service.verify_bundle_id.return_value = False
            mock_get_service.return_value = mock_apple_service

            result = await iap_service.handle_apple_notification(mock_session, mock_notification)

            assert result is None

    @pytest.mark.asyncio
    async def test_link_apple_subscription(self, mock_user):
        """link_apple_subscription should set Apple transaction ID."""
        iap_service = IAPService()
        mock_session = AsyncMock()

        mock_user.apple_original_transaction_id = None

        result = await iap_service.link_apple_subscription(
            session=mock_session,
            user=mock_user,
            original_transaction_id="new_txn_456",
            product_id="com.example.pro_monthly",
        )

        assert result.apple_original_transaction_id == "new_txn_456"
        assert result.subscription_status == "active"
        assert result.subscription_plan == "pro"
        mock_session.add.assert_called()
        mock_session.flush.assert_called()

    def test_get_plan_from_apple_product_pro(self):
        """_get_plan_from_apple_product should return 'pro' for pro products."""
        iap_service = IAPService()

        result = iap_service._get_plan_from_apple_product("com.example.pro_monthly")

        assert result == "pro"

    def test_get_plan_from_apple_product_premium(self):
        """_get_plan_from_apple_product should return 'pro' for premium products."""
        iap_service = IAPService()

        result = iap_service._get_plan_from_apple_product("com.example.premium_yearly")

        assert result == "pro"

    def test_get_plan_from_apple_product_enterprise(self):
        """_get_plan_from_apple_product should return 'enterprise' for enterprise products."""
        iap_service = IAPService()

        result = iap_service._get_plan_from_apple_product("com.example.enterprise_monthly")

        assert result == "enterprise"


class TestAppleNotificationTypes:
    """Tests for Apple notification type enums."""

    def test_notification_type_values(self):
        """AppleNotificationType should have correct values."""
        assert AppleNotificationType.SUBSCRIBED.value == "SUBSCRIBED"
        assert AppleNotificationType.DID_RENEW.value == "DID_RENEW"
        assert AppleNotificationType.EXPIRED.value == "EXPIRED"
        assert AppleNotificationType.REFUND.value == "REFUND"

    def test_subtype_values(self):
        """AppleSubtype should have correct values."""
        assert AppleSubtype.INITIAL_BUY.value == "INITIAL_BUY"
        assert AppleSubtype.RESUBSCRIBE.value == "RESUBSCRIBE"
        assert AppleSubtype.AUTO_RENEW_ENABLED.value == "AUTO_RENEW_ENABLED"
