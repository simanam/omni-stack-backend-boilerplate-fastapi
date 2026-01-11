"""
Tests for webhook handlers.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.public.webhooks import (
    _handle_checkout_completed,
    _handle_clerk_user_created,
    _handle_clerk_user_deleted,
    _handle_clerk_user_updated,
    _handle_invoice_paid,
    _handle_invoice_payment_failed,
    _handle_subscription_deleted,
    _handle_subscription_updated,
    _handle_supabase_user_created,
    _handle_supabase_user_deleted,
    _handle_supabase_user_updated,
    _verify_clerk_signature,
    create_webhook_event,
    mark_event_failed,
    mark_event_processed,
)
from app.models.user import User
from app.models.webhook_event import WebhookEvent

# =============================================================================
# Webhook Event Helper Tests
# =============================================================================


class TestWebhookEventHelpers:
    """Tests for webhook event helper functions."""

    @pytest.mark.asyncio
    async def test_create_webhook_event_new(self):
        """create_webhook_event should create new event."""
        # Mock session that returns no existing event
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        event = await create_webhook_event(
            session=mock_session,
            provider="stripe",
            event_type="test.event",
            idempotency_key="evt_unique123",
            payload={"test": "data"},
        )

        assert event is not None
        assert event.provider == "stripe"
        assert event.event_type == "test.event"
        assert event.idempotency_key == "evt_unique123"
        assert event.status == "processing"
        assert event.attempts == 1
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_webhook_event_duplicate(self, caplog):
        """create_webhook_event should return None for duplicate."""
        # Mock session that returns existing event
        existing_event = WebhookEvent(
            provider="stripe",
            event_type="test.event",
            idempotency_key="evt_duplicate123",
            payload={},
            status="processed",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_event

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await create_webhook_event(
            session=mock_session,
            provider="stripe",
            event_type="test.event",
            idempotency_key="evt_duplicate123",
            payload={},
        )

        assert result is None
        assert "Duplicate webhook event" in caplog.text

    @pytest.mark.asyncio
    async def test_mark_event_processed(self):
        """mark_event_processed should update event status."""
        mock_session = AsyncMock()
        event = WebhookEvent(
            provider="stripe",
            event_type="test.event",
            idempotency_key="evt_process123",
            payload={},
            status="processing",
        )

        await mark_event_processed(mock_session, event)

        assert event.status == "processed"
        assert event.processed_at is not None
        mock_session.add.assert_called_once_with(event)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_event_failed(self):
        """mark_event_failed should update event with error."""
        mock_session = AsyncMock()
        event = WebhookEvent(
            provider="stripe",
            event_type="test.event",
            idempotency_key="evt_fail123",
            payload={},
            status="processing",
        )

        await mark_event_failed(mock_session, event, "Test error message")

        assert event.status == "failed"
        assert event.error_message == "Test error message"
        mock_session.add.assert_called_once_with(event)
        mock_session.flush.assert_called_once()


# =============================================================================
# Stripe Webhook Handler Tests
# =============================================================================


class TestStripeWebhookHandlers:
    """Tests for Stripe webhook event handlers."""

    @pytest.mark.asyncio
    async def test_handle_checkout_completed_missing_data(self):
        """_handle_checkout_completed should skip event without customer/subscription."""
        mock_session = AsyncMock()
        mock_event = MagicMock()
        mock_event.data.object = {}

        await _handle_checkout_completed(mock_session, mock_event)

        # Should not call billing service
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_checkout_completed_success(self):
        """_handle_checkout_completed should call billing service."""
        mock_session = AsyncMock()
        mock_event = MagicMock()
        mock_event.data.object = {
            "customer": "cus_test123",
            "subscription": "sub_test123",
        }

        with patch("app.api.v1.public.webhooks.billing_service") as mock_billing:
            mock_billing.handle_checkout_completed = AsyncMock()

            await _handle_checkout_completed(mock_session, mock_event)

            mock_billing.handle_checkout_completed.assert_called_once_with(
                session=mock_session,
                customer_id="cus_test123",
                subscription_id="sub_test123",
            )

    @pytest.mark.asyncio
    async def test_handle_subscription_updated(self):
        """_handle_subscription_updated should call billing service."""
        mock_session = AsyncMock()
        mock_event = MagicMock()
        mock_event.data.object = {
            "customer": "cus_test123",
            "id": "sub_test123",
        }

        with patch("app.api.v1.public.webhooks.billing_service") as mock_billing:
            mock_billing.handle_subscription_updated = AsyncMock()

            await _handle_subscription_updated(mock_session, mock_event)

            mock_billing.handle_subscription_updated.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_subscription_deleted(self):
        """_handle_subscription_deleted should call billing service."""
        mock_session = AsyncMock()
        mock_event = MagicMock()
        mock_event.data.object = {
            "customer": "cus_test123",
        }

        with patch("app.api.v1.public.webhooks.billing_service") as mock_billing:
            mock_billing.handle_subscription_deleted = AsyncMock()

            await _handle_subscription_deleted(mock_session, mock_event)

            mock_billing.handle_subscription_deleted.assert_called_once_with(
                session=mock_session,
                customer_id="cus_test123",
            )

    @pytest.mark.asyncio
    async def test_handle_invoice_paid(self, caplog):
        """_handle_invoice_paid should log the event."""
        mock_session = AsyncMock()
        mock_event = MagicMock()
        mock_event.data.object = {
            "customer": "cus_test123",
            "subscription": "sub_test123",
        }

        await _handle_invoice_paid(mock_session, mock_event)

        assert "Invoice paid" in caplog.text

    @pytest.mark.asyncio
    async def test_handle_invoice_payment_failed(self, caplog):
        """_handle_invoice_payment_failed should log warning."""
        mock_session = AsyncMock()
        mock_event = MagicMock()
        mock_event.data.object = {
            "customer": "cus_test123",
        }

        await _handle_invoice_payment_failed(mock_session, mock_event)

        assert "Invoice payment failed" in caplog.text


# =============================================================================
# Clerk Webhook Handler Tests
# =============================================================================


class TestClerkWebhookHandlers:
    """Tests for Clerk webhook event handlers."""

    def test_verify_clerk_signature_invalid_format(self):
        """_verify_clerk_signature should return False for invalid format."""
        result = _verify_clerk_signature(b"test", "invalid", "secret")
        assert result is False

    def test_verify_clerk_signature_short_parts(self):
        """_verify_clerk_signature should return False for too few parts."""
        result = _verify_clerk_signature(b"test", "v1,timestamp", "secret")
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_clerk_user_created_missing_fields(self, caplog):
        """_handle_clerk_user_created should skip event with missing fields."""
        mock_session = AsyncMock()
        event = {"data": {"id": None, "email_addresses": []}}

        await _handle_clerk_user_created(mock_session, event)

        assert "missing required fields" in caplog.text

    @pytest.mark.asyncio
    async def test_handle_clerk_user_created_new_user(self, caplog):
        """_handle_clerk_user_created should create new user."""
        # Mock session that returns no existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        event = {
            "data": {
                "id": "clerk_user_new123",
                "email_addresses": [
                    {
                        "id": "email_1",
                        "email_address": "newuser@example.com",
                    }
                ],
                "primary_email_address_id": "email_1",
                "first_name": "New",
                "last_name": "User",
                "image_url": "https://example.com/avatar.jpg",
            }
        }

        await _handle_clerk_user_created(mock_session, event)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        assert "Created user from Clerk" in caplog.text

    @pytest.mark.asyncio
    async def test_handle_clerk_user_created_existing_user(self, caplog):
        """_handle_clerk_user_created should skip existing user."""
        existing_user = User(
            id="clerk_user_existing",
            email="existing@example.com",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        event = {
            "data": {
                "id": "clerk_user_existing",
                "email_addresses": [
                    {
                        "id": "email_1",
                        "email_address": "existing@example.com",
                    }
                ],
                "primary_email_address_id": "email_1",
            }
        }

        await _handle_clerk_user_created(mock_session, event)

        assert "already exists" in caplog.text
        # Should not add user again
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_clerk_user_updated_not_found(self, caplog):
        """_handle_clerk_user_updated should skip nonexistent user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        event = {
            "data": {
                "id": "clerk_user_notfound",
                "email_addresses": [],
            }
        }

        await _handle_clerk_user_updated(mock_session, event)

        assert "not found for update" in caplog.text

    @pytest.mark.asyncio
    async def test_handle_clerk_user_updated_success(self, caplog):
        """_handle_clerk_user_updated should update existing user."""
        user = User(
            id="clerk_user_update",
            email="update@example.com",
            full_name="Old Name",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        event = {
            "data": {
                "id": "clerk_user_update",
                "email_addresses": [
                    {
                        "id": "email_1",
                        "email_address": "newemail@example.com",
                    }
                ],
                "primary_email_address_id": "email_1",
                "first_name": "New",
                "last_name": "Name",
                "image_url": "https://example.com/new-avatar.jpg",
            }
        }

        await _handle_clerk_user_updated(mock_session, event)

        assert user.email == "newemail@example.com"
        assert user.full_name == "New Name"
        assert user.avatar_url == "https://example.com/new-avatar.jpg"
        assert "Updated user from Clerk" in caplog.text

    @pytest.mark.asyncio
    async def test_handle_clerk_user_deleted(self, caplog):
        """_handle_clerk_user_deleted should deactivate user."""
        user = User(
            id="clerk_user_delete",
            email="delete@example.com",
            is_active=True,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        event = {
            "data": {
                "id": "clerk_user_delete",
            }
        }

        await _handle_clerk_user_deleted(mock_session, event)

        assert user.is_active is False
        assert "Deactivated user from Clerk" in caplog.text


# =============================================================================
# Supabase Webhook Handler Tests
# =============================================================================


class TestSupabaseWebhookHandlers:
    """Tests for Supabase webhook event handlers."""

    @pytest.mark.asyncio
    async def test_handle_supabase_user_created_missing_fields(self):
        """_handle_supabase_user_created should skip record with missing fields."""
        mock_session = AsyncMock()
        record = {"id": None, "email": None}

        await _handle_supabase_user_created(mock_session, record)

        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_supabase_user_created_new_user(self, caplog):
        """_handle_supabase_user_created should create new user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        record = {
            "id": "supabase_user_new",
            "email": "supabase@example.com",
            "raw_user_meta_data": {
                "full_name": "Supabase User",
                "avatar_url": "https://example.com/avatar.jpg",
            },
        }

        await _handle_supabase_user_created(mock_session, record)

        mock_session.add.assert_called_once()
        assert "Created user from Supabase" in caplog.text

    @pytest.mark.asyncio
    async def test_handle_supabase_user_created_existing(self):
        """_handle_supabase_user_created should skip existing user."""
        existing_user = User(
            id="supabase_user_existing",
            email="existing_supabase@example.com",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        record = {
            "id": "supabase_user_existing",
            "email": "existing_supabase@example.com",
        }

        await _handle_supabase_user_created(mock_session, record)

        # Should not add again
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_supabase_user_updated(self, caplog):
        """_handle_supabase_user_updated should update existing user."""
        user = User(
            id="supabase_user_update",
            email="old@example.com",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        record = {
            "id": "supabase_user_update",
            "email": "new@example.com",
            "raw_user_meta_data": {
                "full_name": "Updated Name",
                "avatar_url": "https://example.com/new.jpg",
            },
        }

        await _handle_supabase_user_updated(mock_session, record)

        assert user.email == "new@example.com"
        assert user.full_name == "Updated Name"
        assert "Updated user from Supabase" in caplog.text

    @pytest.mark.asyncio
    async def test_handle_supabase_user_updated_not_found(self):
        """_handle_supabase_user_updated should skip nonexistent user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        record = {
            "id": "supabase_nonexistent",
            "email": "test@example.com",
        }

        await _handle_supabase_user_updated(mock_session, record)

        # Should not call add
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_supabase_user_deleted(self, caplog):
        """_handle_supabase_user_deleted should deactivate user."""
        user = User(
            id="supabase_user_delete",
            email="delete@example.com",
            is_active=True,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        record = {"id": "supabase_user_delete"}

        await _handle_supabase_user_deleted(mock_session, record)

        assert user.is_active is False
        assert "Deactivated user from Supabase" in caplog.text


# =============================================================================
# Webhook Endpoint Integration Tests
# =============================================================================


class TestWebhookEndpoints:
    """Integration tests for webhook HTTP endpoints."""

    @pytest.mark.asyncio
    async def test_stripe_webhook_missing_config(self, client: AsyncClient):
        """Stripe webhook should return 503 when not configured."""
        with patch("app.api.v1.public.webhooks.settings") as mock_settings:
            mock_settings.stripe_available = False

            response = await client.post(
                "/api/v1/public/webhooks/stripe",
                content=b"{}",
                headers={"Stripe-Signature": "test"},
            )

            assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_stripe_webhook_invalid_signature(self, client: AsyncClient):
        """Stripe webhook should return 400 for invalid signature."""
        with patch("app.api.v1.public.webhooks.settings") as mock_settings:
            mock_settings.stripe_available = True
            mock_settings.STRIPE_SECRET_KEY = "sk_test_123"

            with patch("app.services.payments.stripe_service.get_stripe_service") as mock_stripe:
                mock_stripe_svc = MagicMock()
                mock_stripe_svc.construct_webhook_event.side_effect = ValueError("Invalid signature")
                mock_stripe.return_value = mock_stripe_svc

                response = await client.post(
                    "/api/v1/public/webhooks/stripe",
                    content=b"{}",
                    headers={"Stripe-Signature": "invalid"},
                )

                assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_clerk_webhook_missing_config(self, client: AsyncClient):
        """Clerk webhook should return 503 when not configured."""
        with patch("app.api.v1.public.webhooks.settings") as mock_settings:
            mock_settings.CLERK_SECRET_KEY = None

            response = await client.post(
                "/api/v1/public/webhooks/clerk",
                content=b"{}",
                headers={
                    "svix-id": "msg_123",
                    "svix-timestamp": "1234567890",
                    "svix-signature": "v1,1234567890,abc123",
                },
            )

            assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_clerk_webhook_invalid_payload(self, client: AsyncClient):
        """Clerk webhook should return 400 for invalid JSON."""
        with patch("app.api.v1.public.webhooks.settings") as mock_settings:
            mock_settings.CLERK_SECRET_KEY = "test_secret"

            response = await client.post(
                "/api/v1/public/webhooks/clerk",
                content=b"not valid json",
                headers={
                    "svix-id": "msg_123",
                    "svix-timestamp": "1234567890",
                    "svix-signature": "v1,1234567890,abc123",
                },
            )

            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_supabase_webhook_invalid_auth(self, client: AsyncClient):
        """Supabase webhook should return 401 for invalid auth."""
        response = await client.post(
            "/api/v1/public/webhooks/supabase",
            json={"type": "INSERT", "table": "auth.users", "record": {}},
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_supabase_webhook_invalid_payload(self, client: AsyncClient):
        """Supabase webhook should return 400 for invalid JSON."""
        with patch("app.api.v1.public.webhooks.settings") as mock_settings:
            mock_settings.SECRET_KEY = "test_secret"

            response = await client.post(
                "/api/v1/public/webhooks/supabase",
                content=b"not json",
                headers={"Authorization": "Bearer test_secret"},
            )

            assert response.status_code == 400
