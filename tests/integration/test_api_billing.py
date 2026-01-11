"""
Integration tests for billing API endpoints.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.business.billing_service import BillingStatus
from app.main import app
from app.models.user import User
from app.services.payments.stripe_service import CheckoutResult, PortalResult


@pytest.fixture
def mock_user() -> User:
    """Create a mock authenticated user."""
    return User(
        id="billing_test_user",
        email="billing@example.com",
        full_name="Billing User",
        role="user",
        is_active=True,
        subscription_plan="free",
        subscription_status=None,
        stripe_customer_id=None,
    )


@pytest.fixture
def mock_pro_user() -> User:
    """Create a mock user with pro subscription."""
    return User(
        id="pro_test_user",
        email="pro@example.com",
        full_name="Pro User",
        role="user",
        is_active=True,
        subscription_plan="pro",
        subscription_status="active",
        stripe_customer_id="cus_pro123",
    )


@pytest.fixture
async def authenticated_client(client: AsyncClient, mock_user: User, session):
    """Provide client with mocked authentication."""
    session.add(mock_user)
    await session.flush()

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def pro_authenticated_client(client: AsyncClient, mock_pro_user: User, session):
    """Provide client with mocked pro user authentication."""
    session.add(mock_pro_user)
    await session.flush()

    async def override_get_current_user():
        return mock_pro_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


class TestBillingStatusEndpoint:
    """Tests for GET /billing/status endpoint."""

    @pytest.mark.asyncio
    async def test_billing_status_unauthorized(self, client: AsyncClient):
        """GET /billing/status should return 401 without auth."""
        response = await client.get("/api/v1/app/billing/status")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_billing_status_free_user(self, authenticated_client: AsyncClient):
        """GET /billing/status should return free plan for new user."""
        with patch("app.api.v1.app.billing.billing_service") as mock_billing:
            mock_billing.get_billing_status = AsyncMock(
                return_value=BillingStatus(
                    plan="free",
                    status=None,
                    stripe_customer_id=None,
                    current_period_end=None,
                    cancel_at_period_end=False,
                    subscription_id=None,
                )
            )

            response = await authenticated_client.get("/api/v1/app/billing/status")

            assert response.status_code == 200
            data = response.json()
            assert data["plan"] == "free"

    @pytest.mark.asyncio
    async def test_billing_status_pro_user(self, pro_authenticated_client: AsyncClient):
        """GET /billing/status should return pro plan for paying user."""
        with patch("app.api.v1.app.billing.billing_service") as mock_billing:
            mock_billing.get_billing_status = AsyncMock(
                return_value=BillingStatus(
                    plan="pro",
                    status="active",
                    stripe_customer_id="cus_pro123",
                    current_period_end=None,
                    cancel_at_period_end=False,
                    subscription_id="sub_123",
                )
            )

            response = await pro_authenticated_client.get("/api/v1/app/billing/status")

            assert response.status_code == 200
            data = response.json()
            assert data["plan"] == "pro"
            assert data["status"] == "active"


class TestCheckoutEndpoint:
    """Tests for POST /billing/checkout endpoint."""

    @pytest.mark.asyncio
    async def test_checkout_unauthorized(self, client: AsyncClient):
        """POST /billing/checkout should return 401 without auth."""
        response = await client.post(
            "/api/v1/app/billing/checkout",
            json={"interval": "monthly"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_checkout_success(self, authenticated_client: AsyncClient):
        """POST /billing/checkout should create checkout session."""
        with patch("app.api.v1.app.billing.billing_service") as mock_billing:
            mock_billing.start_checkout = AsyncMock(
                return_value=CheckoutResult(
                    session_id="cs_test123",
                    url="https://checkout.stripe.com/test",
                )
            )

            response = await authenticated_client.post(
                "/api/v1/app/billing/checkout",
                json={
                    "interval": "monthly",
                    "success_url": "https://example.com/success",
                    "cancel_url": "https://example.com/cancel",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "cs_test123"
            assert "url" in data

    @pytest.mark.asyncio
    async def test_checkout_yearly(self, authenticated_client: AsyncClient):
        """POST /billing/checkout should support yearly billing."""
        with patch("app.api.v1.app.billing.billing_service") as mock_billing:
            mock_billing.start_checkout = AsyncMock(
                return_value=CheckoutResult(
                    session_id="cs_yearly123",
                    url="https://checkout.stripe.com/yearly",
                )
            )

            response = await authenticated_client.post(
                "/api/v1/app/billing/checkout",
                json={
                    "interval": "yearly",
                    "success_url": "https://example.com/success",
                    "cancel_url": "https://example.com/cancel",
                },
            )

            assert response.status_code == 200


class TestPortalEndpoint:
    """Tests for GET /billing/portal endpoint."""

    @pytest.mark.asyncio
    async def test_portal_unauthorized(self, client: AsyncClient):
        """GET /billing/portal should return 401 without auth."""
        response = await client.get("/api/v1/app/billing/portal")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_portal_success(self, pro_authenticated_client: AsyncClient):
        """GET /billing/portal should return portal URL."""
        with patch("app.api.v1.app.billing.billing_service") as mock_billing:
            mock_billing.get_billing_portal_url = AsyncMock(
                return_value=PortalResult(url="https://billing.stripe.com/portal")
            )

            response = await pro_authenticated_client.get(
                "/api/v1/app/billing/portal",
                params={"return_url": "https://example.com/billing"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "url" in data
            assert "stripe.com" in data["url"]


class TestInvoicesEndpoint:
    """Tests for GET /billing/invoices endpoint."""

    @pytest.mark.asyncio
    async def test_invoices_unauthorized(self, client: AsyncClient):
        """GET /billing/invoices should return 401 without auth."""
        response = await client.get("/api/v1/app/billing/invoices")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invoices_empty(self, authenticated_client: AsyncClient):
        """GET /billing/invoices should return empty list for free user."""
        with patch("app.api.v1.app.billing.billing_service") as mock_billing:
            mock_billing.get_invoices = AsyncMock(return_value=[])

            response = await authenticated_client.get("/api/v1/app/billing/invoices")

            assert response.status_code == 200
            data = response.json()
            assert data == []

    @pytest.mark.asyncio
    async def test_invoices_with_data(self, pro_authenticated_client: AsyncClient):
        """GET /billing/invoices should return invoices for paying user."""
        mock_invoices = [
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

        with patch("app.api.v1.app.billing.billing_service") as mock_billing:
            mock_billing.get_invoices = AsyncMock(return_value=mock_invoices)

            response = await pro_authenticated_client.get("/api/v1/app/billing/invoices")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == "inv_123"


class TestCancelSubscriptionEndpoint:
    """Tests for POST /billing/cancel endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_unauthorized(self, client: AsyncClient):
        """POST /billing/cancel should return 401 without auth."""
        response = await client.post("/api/v1/app/billing/cancel")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_cancel_no_subscription(self, authenticated_client: AsyncClient):
        """POST /billing/cancel should handle user without subscription."""
        with patch("app.api.v1.app.billing.billing_service") as mock_billing:
            mock_billing.cancel_subscription = AsyncMock(return_value=None)

            response = await authenticated_client.post("/api/v1/app/billing/cancel")

            # Should return appropriate response (implementation dependent)
            assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_cancel_success(self, pro_authenticated_client: AsyncClient):
        """POST /billing/cancel should cancel active subscription."""
        from app.services.payments.stripe_service import SubscriptionInfo

        with patch("app.api.v1.app.billing.billing_service") as mock_billing:
            mock_billing.cancel_subscription = AsyncMock(
                return_value=SubscriptionInfo(
                    id="sub_123",
                    status="active",
                    plan="pro",
                    current_period_start=1704067200,
                    current_period_end=1706745600,
                    cancel_at_period_end=True,
                    price_id="price_monthly",
                )
            )

            response = await pro_authenticated_client.post("/api/v1/app/billing/cancel")

            assert response.status_code == 200


class TestResumeSubscriptionEndpoint:
    """Tests for POST /billing/resume endpoint."""

    @pytest.mark.asyncio
    async def test_resume_unauthorized(self, client: AsyncClient):
        """POST /billing/resume should return 401 without auth."""
        response = await client.post("/api/v1/app/billing/resume")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_resume_no_cancelled_subscription(self, authenticated_client: AsyncClient):
        """POST /billing/resume should handle no cancelled subscription."""
        with patch("app.api.v1.app.billing.billing_service") as mock_billing:
            mock_billing.resume_subscription = AsyncMock(return_value=None)

            response = await authenticated_client.post("/api/v1/app/billing/resume")

            # Should return appropriate response (implementation dependent)
            assert response.status_code in [200, 400, 404]
