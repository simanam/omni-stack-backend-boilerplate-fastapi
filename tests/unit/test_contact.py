"""
Tests for contact form endpoint.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.public.contact import (
    ContactFormRequest,
    ContactFormResponse,
    ContactMessage,
    _check_timing_spam,
    _generate_reference_id,
)


class TestContactFormSchemas:
    """Tests for contact form schemas."""

    def test_contact_form_request_valid(self):
        """Valid contact form should be accepted."""
        form = ContactFormRequest(
            name="John Doe",
            email="john@example.com",
            subject="Test inquiry",
            message="This is a test message that is long enough.",
        )
        assert form.name == "John Doe"
        assert form.email == "john@example.com"
        assert form.subject == "Test inquiry"
        assert form.website is None

    def test_contact_form_request_with_honeypot_fails(self):
        """Form with honeypot field filled should be rejected."""
        with pytest.raises(ValueError, match="Invalid form submission"):
            ContactFormRequest(
                name="Bot",
                email="bot@spam.com",
                subject="Buy now!!!",
                message="Click this link for amazing deals!",
                website="http://spam-site.com",  # Honeypot filled
            )

    def test_contact_form_request_name_too_short(self):
        """Name that is too short should be rejected."""
        with pytest.raises(ValueError):
            ContactFormRequest(
                name="J",  # Too short (min 2)
                email="john@example.com",
                subject="Test inquiry",
                message="This is a test message.",
            )

    def test_contact_form_request_subject_too_short(self):
        """Subject that is too short should be rejected."""
        with pytest.raises(ValueError):
            ContactFormRequest(
                name="John",
                email="john@example.com",
                subject="Hi",  # Too short (min 5)
                message="This is a test message.",
            )

    def test_contact_form_request_message_too_short(self):
        """Message that is too short should be rejected."""
        with pytest.raises(ValueError):
            ContactFormRequest(
                name="John",
                email="john@example.com",
                subject="Valid subject",
                message="Short",  # Too short (min 10)
            )

    def test_contact_form_request_invalid_email(self):
        """Invalid email should be rejected."""
        with pytest.raises(ValueError):
            ContactFormRequest(
                name="John",
                email="not-an-email",
                subject="Valid subject",
                message="This is a test message.",
            )

    def test_contact_form_response(self):
        """Contact form response should have correct fields."""
        response = ContactFormResponse(
            success=True,
            message="Thank you!",
            reference_id="CNT-12345678",
        )
        assert response.success is True
        assert response.reference_id == "CNT-12345678"

    def test_contact_message(self):
        """ContactMessage should store all fields correctly."""
        message = ContactMessage(
            id="CNT-12345678",
            name="John Doe",
            email="john@example.com",
            subject="Test",
            message="Test message content",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0",
            submitted_at=datetime.utcnow(),
            metadata={"source": "website"},
        )
        assert message.id == "CNT-12345678"
        assert message.ip_address == "127.0.0.1"
        assert message.metadata["source"] == "website"


class TestReferenceIdGeneration:
    """Tests for reference ID generation."""

    def test_generate_reference_id_format(self):
        """Reference ID should follow CNT-XXXXXXXX format."""
        ref_id = _generate_reference_id()
        assert ref_id.startswith("CNT-")
        assert len(ref_id) == 12  # CNT- + 8 chars

    def test_generate_reference_id_unique(self):
        """Reference IDs should be unique."""
        ids = [_generate_reference_id() for _ in range(100)]
        assert len(set(ids)) == 100


class TestTimingSpamDetection:
    """Tests for timing-based spam detection."""

    def test_no_timestamp_not_spam(self):
        """Missing timestamp should not be flagged as spam."""
        assert _check_timing_spam(None) is False

    def test_old_timestamp_not_spam(self):
        """Timestamp from more than 3 seconds ago should not be spam."""
        old_time = str(datetime.utcnow().timestamp() - 10)
        assert _check_timing_spam(old_time) is False

    def test_recent_timestamp_is_spam(self):
        """Timestamp from less than 3 seconds ago should be spam."""
        recent_time = str(datetime.utcnow().timestamp() - 1)
        assert _check_timing_spam(recent_time) is True

    def test_invalid_timestamp_not_spam(self):
        """Invalid timestamp format should not be flagged."""
        assert _check_timing_spam("invalid") is False
        assert _check_timing_spam("abc123") is False


class TestContactFormRateLimiting:
    """Tests for contact form rate limiting."""

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_initial_requests(self):
        """Rate limiter should allow initial requests."""
        from app.api.v1.public.contact import CONTACT_RATE_LIMIT, contact_rate_limiter

        # Use a unique key for this test
        test_key = f"test_contact_rate_{datetime.utcnow().timestamp()}"

        allowed, remaining, _ = await contact_rate_limiter.is_allowed(
            test_key,
            CONTACT_RATE_LIMIT,
        )

        assert allowed is True
        assert remaining >= 0


class TestContactFormEndpoint:
    """Tests for contact form endpoint behavior."""

    @pytest.mark.asyncio
    async def test_submit_contact_form_success(self):
        """Successful contact form submission."""
        from unittest.mock import MagicMock

        from app.api.v1.public.contact import submit_contact_form

        # Mock request
        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "Mozilla/5.0"

        # Valid form
        form = ContactFormRequest(
            name="John Doe",
            email="john@example.com",
            subject="Test inquiry",
            message="This is a test message that is long enough.",
            form_timestamp=str(datetime.utcnow().timestamp() - 10),  # 10 seconds ago
        )

        with patch("app.api.v1.public.contact.contact_rate_limiter") as mock_limiter:
            mock_limiter.is_allowed = AsyncMock(return_value=(True, 4, 3600))

            with patch("app.api.v1.public.contact._store_contact_message") as mock_store:
                mock_store.return_value = None

                with patch("app.api.v1.public.contact.enqueue") as mock_enqueue:
                    mock_enqueue.return_value = None

                    response = await submit_contact_form(mock_request, form)

                    assert response.success is True
                    assert response.reference_id is not None
                    assert response.reference_id.startswith("CNT-")

    @pytest.mark.asyncio
    async def test_submit_contact_form_rate_limited(self):
        """Rate limited contact form submission should return 429."""
        from unittest.mock import MagicMock

        from fastapi import HTTPException

        from app.api.v1.public.contact import submit_contact_form

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"

        form = ContactFormRequest(
            name="John Doe",
            email="john@example.com",
            subject="Test inquiry",
            message="This is a test message that is long enough.",
        )

        with patch("app.api.v1.public.contact.contact_rate_limiter") as mock_limiter:
            mock_limiter.is_allowed = AsyncMock(return_value=(False, 0, 3600))

            with pytest.raises(HTTPException) as exc_info:
                await submit_contact_form(mock_request, form)

            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_submit_contact_form_timing_spam(self):
        """Spam detected by timing should return fake success."""
        from unittest.mock import MagicMock

        from app.api.v1.public.contact import submit_contact_form

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"

        # Form submitted too quickly (1 second ago)
        form = ContactFormRequest(
            name="Bot",
            email="bot@example.com",
            subject="Spam message",
            message="This is spam content that was submitted too quickly.",
            form_timestamp=str(datetime.utcnow().timestamp() - 1),
        )

        with patch("app.api.v1.public.contact.contact_rate_limiter") as mock_limiter:
            mock_limiter.is_allowed = AsyncMock(return_value=(True, 4, 3600))

            response = await submit_contact_form(mock_request, form)

            # Should return success to not tip off bots
            assert response.success is True
            assert response.reference_id is not None

    @pytest.mark.asyncio
    async def test_get_contact_status(self):
        """Contact status endpoint should return rate limit info."""
        from unittest.mock import MagicMock

        from app.api.v1.public.contact import get_contact_status

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"

        with patch("app.api.v1.public.contact.contact_rate_limiter") as mock_limiter:
            mock_limiter.is_allowed = AsyncMock(return_value=(True, 3, 3600))

            status = await get_contact_status(mock_request)

            assert status["available"] is True
            assert status["rate_limit"]["limit"] == 5
            assert status["rate_limit"]["remaining"] == 3


class TestEmailNotification:
    """Tests for email notification functionality."""

    @pytest.mark.asyncio
    async def test_send_notification_with_admin_email(self):
        """Should send notification when ADMIN_EMAIL is configured."""
        from app.api.v1.public.contact import _send_notification_email

        message = ContactMessage(
            id="CNT-12345678",
            name="John Doe",
            email="john@example.com",
            subject="Test",
            message="Test message",
            submitted_at=datetime.utcnow(),
        )

        with patch("app.api.v1.public.contact.settings") as mock_settings:
            mock_settings.ADMIN_EMAIL = "admin@example.com"

            with patch("app.api.v1.public.contact.get_email_service") as mock_email:
                mock_service = MagicMock()
                mock_service.send_raw = AsyncMock(return_value=True)
                mock_email.return_value = mock_service

                await _send_notification_email(message)

                mock_service.send_raw.assert_called_once()
                call_kwargs = mock_service.send_raw.call_args.kwargs
                assert call_kwargs["to"] == "admin@example.com"
                assert "[Contact Form]" in call_kwargs["subject"]

    @pytest.mark.asyncio
    async def test_send_notification_without_admin_email(self):
        """Should skip notification when ADMIN_EMAIL is not configured."""
        from app.api.v1.public.contact import _send_notification_email

        message = ContactMessage(
            id="CNT-12345678",
            name="John Doe",
            email="john@example.com",
            subject="Test",
            message="Test message",
            submitted_at=datetime.utcnow(),
        )

        with patch("app.api.v1.public.contact.settings") as mock_settings:
            # Simulate ADMIN_EMAIL not being set
            del mock_settings.ADMIN_EMAIL

            with patch("app.api.v1.public.contact.get_email_service") as mock_email:
                mock_service = MagicMock()
                mock_email.return_value = mock_service

                await _send_notification_email(message)

                # Should not attempt to send
                mock_service.send_raw.assert_not_called()


class TestContactMessageStorage:
    """Tests for contact message storage."""

    @pytest.mark.asyncio
    async def test_store_contact_message_with_redis(self):
        """Should store message in Redis when available."""
        from app.api.v1.public.contact import _store_contact_message

        message = ContactMessage(
            id="CNT-12345678",
            name="John Doe",
            email="john@example.com",
            subject="Test",
            message="Test message",
            submitted_at=datetime.utcnow(),
        )

        with patch("app.api.v1.public.contact.get_redis") as mock_get_redis:
            mock_redis = MagicMock()
            mock_redis.setex = AsyncMock()
            mock_redis.lpush = AsyncMock()
            mock_get_redis.return_value = mock_redis

            await _store_contact_message(message)

            mock_redis.setex.assert_called_once()
            mock_redis.lpush.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_contact_message_without_redis(self):
        """Should handle missing Redis gracefully."""
        from app.api.v1.public.contact import _store_contact_message

        message = ContactMessage(
            id="CNT-12345678",
            name="John Doe",
            email="john@example.com",
            subject="Test",
            message="Test message",
            submitted_at=datetime.utcnow(),
        )

        with patch("app.api.v1.public.contact.get_redis") as mock_get_redis:
            mock_get_redis.return_value = None

            # Should not raise
            await _store_contact_message(message)
