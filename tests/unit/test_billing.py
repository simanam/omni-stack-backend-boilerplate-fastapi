"""
Tests for billing service.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.business.billing_service import BillingService, BillingStatus, billing_service
from app.models.user import User
from app.services.payments.stripe_service import (
    CheckoutResult,
    PortalResult,
    SubscriptionInfo,
)


@pytest.fixture
def mock_user() -> User:
    """Create a mock user for testing."""
    return User(
        id="user_123",
        email="test@example.com",
        full_name="Test User",
        stripe_customer_id=None,
        subscription_status=None,
        subscription_plan=None,
    )


@pytest.fixture
def mock_user_with_stripe(mock_user: User) -> User:
    """Create a mock user with Stripe customer ID."""
    mock_user.stripe_customer_id = "cus_test123"
    mock_user.subscription_status = "active"
    mock_user.subscription_plan = "pro"
    return mock_user


@pytest.fixture
def mock_subscription() -> SubscriptionInfo:
    """Create a mock subscription info."""
    return SubscriptionInfo(
        id="sub_test123",
        status="active",
        plan="pro",
        current_period_start=1704067200,
        current_period_end=1706745600,
        cancel_at_period_end=False,
        price_id="price_monthly",
    )


class TestBillingService:
    """Tests for BillingService class."""

    @pytest.mark.asyncio
    async def test_get_or_create_customer_existing(self, mock_user_with_stripe):
        """get_or_create_customer should return existing customer ID."""
        billing = BillingService()
        mock_session = AsyncMock()

        result = await billing.get_or_create_customer(mock_session, mock_user_with_stripe)

        assert result == "cus_test123"
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_customer_creates_new(self, mock_user):
        """get_or_create_customer should create customer when none exists."""
        billing = BillingService()

        mock_customer = MagicMock()
        mock_customer.id = "cus_new123"

        with patch("app.business.billing_service.get_stripe_service") as mock_stripe:
            mock_stripe_svc = AsyncMock()
            mock_stripe_svc.create_customer = AsyncMock(return_value=mock_customer)
            mock_stripe.return_value = mock_stripe_svc

            mock_session = AsyncMock()
            result = await billing.get_or_create_customer(mock_session, mock_user)

            assert result == "cus_new123"
            assert mock_user.stripe_customer_id == "cus_new123"
            mock_stripe_svc.create_customer.assert_called_once_with(
                email="test@example.com",
                name="Test User",
                user_id="user_123",
            )

    @pytest.mark.asyncio
    async def test_get_billing_status_free_user(self, mock_user):
        """get_billing_status should return free plan for new user."""
        billing = BillingService()
        mock_session = AsyncMock()

        result = await billing.get_billing_status(mock_session, mock_user)

        assert isinstance(result, BillingStatus)
        assert result.plan == "free"
        assert result.status is None
        assert result.stripe_customer_id is None

    @pytest.mark.asyncio
    async def test_get_billing_status_with_subscription(self, mock_user_with_stripe, mock_subscription):
        """get_billing_status should return subscription info for paying user."""
        billing = BillingService()
        mock_session = AsyncMock()

        with patch("app.business.billing_service.settings") as mock_settings:
            mock_settings.stripe_available = True

            with patch("app.business.billing_service.get_stripe_service") as mock_stripe:
                mock_stripe_svc = AsyncMock()
                mock_stripe_svc.get_customer_subscriptions = AsyncMock(
                    return_value=[mock_subscription]
                )
                mock_stripe.return_value = mock_stripe_svc

                result = await billing.get_billing_status(mock_session, mock_user_with_stripe)

                assert result.plan == "pro"
                assert result.status == "active"
                assert result.stripe_customer_id == "cus_test123"
                assert result.subscription_id == "sub_test123"
                assert result.cancel_at_period_end is False

    @pytest.mark.asyncio
    async def test_start_checkout(self, mock_user):
        """start_checkout should create checkout session."""
        billing = BillingService()
        mock_session = AsyncMock()

        expected_result = CheckoutResult(
            session_id="cs_test123",
            url="https://checkout.stripe.com/test",
        )

        with patch.object(billing, "get_or_create_customer") as mock_get_customer:
            mock_get_customer.return_value = "cus_test123"

            with patch("app.business.billing_service.get_stripe_service") as mock_stripe:
                mock_stripe_svc = AsyncMock()
                mock_stripe_svc.create_checkout_session = AsyncMock(return_value=expected_result)
                mock_stripe.return_value = mock_stripe_svc

                result = await billing.start_checkout(
                    session=mock_session,
                    user=mock_user,
                    interval="monthly",
                    success_url="https://example.com/success",
                    cancel_url="https://example.com/cancel",
                )

                assert result.session_id == "cs_test123"
                assert result.url == "https://checkout.stripe.com/test"
                mock_stripe_svc.create_checkout_session.assert_called_once_with(
                    customer_id="cus_test123",
                    plan="monthly",
                    success_url="https://example.com/success",
                    cancel_url="https://example.com/cancel",
                )

    @pytest.mark.asyncio
    async def test_get_billing_portal_url(self, mock_user):
        """get_billing_portal_url should create portal session."""
        billing = BillingService()
        mock_session = AsyncMock()

        expected_result = PortalResult(url="https://billing.stripe.com/portal")

        with patch.object(billing, "get_or_create_customer") as mock_get_customer:
            mock_get_customer.return_value = "cus_test123"

            with patch("app.business.billing_service.get_stripe_service") as mock_stripe:
                mock_stripe_svc = AsyncMock()
                mock_stripe_svc.create_portal_session = AsyncMock(return_value=expected_result)
                mock_stripe.return_value = mock_stripe_svc

                result = await billing.get_billing_portal_url(
                    session=mock_session,
                    user=mock_user,
                    return_url="https://example.com/billing",
                )

                assert result.url == "https://billing.stripe.com/portal"

    @pytest.mark.asyncio
    async def test_sync_subscription_status_active(self, mock_user, mock_subscription):
        """sync_subscription_status should update user for active subscription."""
        billing = BillingService()
        mock_session = AsyncMock()

        result = await billing.sync_subscription_status(
            session=mock_session,
            user=mock_user,
            subscription=mock_subscription,
        )

        assert result.subscription_status == "active"
        assert result.subscription_plan == "pro"
        mock_session.add.assert_called()
        mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_sync_subscription_status_canceled(self, mock_user):
        """sync_subscription_status should set free plan for canceled subscription."""
        billing = BillingService()
        mock_session = AsyncMock()

        canceled_sub = SubscriptionInfo(
            id="sub_test123",
            status="canceled",
            plan="pro",
            current_period_start=1704067200,
            current_period_end=1706745600,
            cancel_at_period_end=False,
            price_id="price_monthly",
        )

        result = await billing.sync_subscription_status(
            session=mock_session,
            user=mock_user,
            subscription=canceled_sub,
        )

        assert result.subscription_status == "canceled"
        assert result.subscription_plan == "free"

    @pytest.mark.asyncio
    async def test_cancel_subscription_no_customer(self, mock_user):
        """cancel_subscription should return None for user without Stripe."""
        billing = BillingService()
        mock_session = AsyncMock()

        result = await billing.cancel_subscription(mock_session, mock_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_subscription_with_customer(self, mock_user_with_stripe, mock_subscription):
        """cancel_subscription should cancel active subscription."""
        billing = BillingService()
        mock_session = AsyncMock()

        canceled_sub = SubscriptionInfo(
            id="sub_test123",
            status="active",
            plan="pro",
            current_period_start=1704067200,
            current_period_end=1706745600,
            cancel_at_period_end=True,
            price_id="price_monthly",
        )

        with patch("app.business.billing_service.get_stripe_service") as mock_stripe:
            mock_stripe_svc = AsyncMock()
            mock_stripe_svc.get_customer_subscriptions = AsyncMock(return_value=[mock_subscription])
            mock_stripe_svc.cancel_subscription = AsyncMock(return_value=canceled_sub)
            mock_stripe.return_value = mock_stripe_svc

            result = await billing.cancel_subscription(mock_session, mock_user_with_stripe)

            assert result is not None
            assert result.cancel_at_period_end is True

    @pytest.mark.asyncio
    async def test_resume_subscription_no_customer(self, mock_user):
        """resume_subscription should return None for user without Stripe."""
        billing = BillingService()
        mock_session = AsyncMock()

        result = await billing.resume_subscription(mock_session, mock_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_resume_subscription_with_pending_cancel(self, mock_user_with_stripe):
        """resume_subscription should resume subscription pending cancellation."""
        billing = BillingService()
        mock_session = AsyncMock()

        pending_cancel_sub = SubscriptionInfo(
            id="sub_test123",
            status="active",
            plan="pro",
            current_period_start=1704067200,
            current_period_end=1706745600,
            cancel_at_period_end=True,
            price_id="price_monthly",
        )

        resumed_sub = SubscriptionInfo(
            id="sub_test123",
            status="active",
            plan="pro",
            current_period_start=1704067200,
            current_period_end=1706745600,
            cancel_at_period_end=False,
            price_id="price_monthly",
        )

        with patch("app.business.billing_service.get_stripe_service") as mock_stripe:
            mock_stripe_svc = AsyncMock()
            mock_stripe_svc.get_customer_subscriptions = AsyncMock(return_value=[pending_cancel_sub])
            mock_stripe_svc.resume_subscription = AsyncMock(return_value=resumed_sub)
            mock_stripe.return_value = mock_stripe_svc

            result = await billing.resume_subscription(mock_session, mock_user_with_stripe)

            assert result is not None
            assert result.cancel_at_period_end is False

    @pytest.mark.asyncio
    async def test_get_invoices_no_customer(self, mock_user):
        """get_invoices should return empty list for user without Stripe."""
        billing = BillingService()

        result = await billing.get_invoices(mock_user)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_invoices_with_customer(self, mock_user_with_stripe):
        """get_invoices should return invoices for user with Stripe."""
        billing = BillingService()

        expected_invoices = [
            {
                "id": "inv_123",
                "number": "INV-001",
                "status": "paid",
                "amount_due": 2000,
                "amount_paid": 2000,
                "currency": "usd",
                "created": 1704067200,
                "hosted_invoice_url": "https://invoice.stripe.com/test",
                "invoice_pdf": "https://invoice.stripe.com/test.pdf",
            }
        ]

        with patch("app.business.billing_service.get_stripe_service") as mock_stripe:
            mock_stripe_svc = AsyncMock()
            mock_stripe_svc.get_invoices = AsyncMock(return_value=expected_invoices)
            mock_stripe.return_value = mock_stripe_svc

            result = await billing.get_invoices(mock_user_with_stripe, limit=5)

            assert result == expected_invoices
            mock_stripe_svc.get_invoices.assert_called_once_with("cus_test123", 5)

    def test_get_current_plan_free(self, mock_user):
        """get_current_plan should return free for user without subscription."""
        billing = BillingService()

        result = billing.get_current_plan(mock_user)

        assert result == "free"

    def test_get_current_plan_pro(self, mock_user_with_stripe):
        """get_current_plan should return pro for active subscription."""
        billing = BillingService()

        result = billing.get_current_plan(mock_user_with_stripe)

        assert result == "pro"

    def test_get_current_plan_inactive(self, mock_user_with_stripe):
        """get_current_plan should return free for inactive subscription."""
        billing = BillingService()
        mock_user_with_stripe.subscription_status = "canceled"

        result = billing.get_current_plan(mock_user_with_stripe)

        assert result == "free"


class TestBillingWebhookHandlers:
    """Tests for billing webhook handler methods."""

    @pytest.mark.asyncio
    async def test_handle_checkout_completed_user_not_found(self):
        """handle_checkout_completed should return None when user not found."""
        billing = BillingService()

        # Create mock session that returns no user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await billing.handle_checkout_completed(
            session=mock_session,
            customer_id="cus_unknown",
            subscription_id="sub_test123",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_handle_checkout_completed_success(self, mock_user_with_stripe, mock_subscription):
        """handle_checkout_completed should sync subscription for known user."""
        billing = BillingService()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user_with_stripe

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.business.billing_service.get_stripe_service") as mock_stripe:
            mock_stripe_svc = AsyncMock()
            mock_stripe_svc.get_subscription = AsyncMock(return_value=mock_subscription)
            mock_stripe.return_value = mock_stripe_svc

            result = await billing.handle_checkout_completed(
                session=mock_session,
                customer_id="cus_test123",
                subscription_id="sub_test123",
            )

            assert result is not None
            assert result.subscription_status == "active"

    @pytest.mark.asyncio
    async def test_handle_subscription_deleted(self, mock_user_with_stripe):
        """handle_subscription_deleted should set user to free plan."""
        billing = BillingService()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user_with_stripe

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await billing.handle_subscription_deleted(
            session=mock_session,
            customer_id="cus_test123",
        )

        assert result is not None
        assert result.subscription_status == "canceled"
        assert result.subscription_plan == "free"

    @pytest.mark.asyncio
    async def test_handle_subscription_deleted_user_not_found(self):
        """handle_subscription_deleted should return None for unknown user."""
        billing = BillingService()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await billing.handle_subscription_deleted(
            session=mock_session,
            customer_id="cus_unknown",
        )

        assert result is None


class TestBillingServiceSingleton:
    """Tests for billing service singleton."""

    def test_singleton_instance_exists(self):
        """billing_service should be a BillingService instance."""
        assert isinstance(billing_service, BillingService)
