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
from app.models.contact_submission import (
    ContactSubmission,
    ContactSubmissionCreate,
    ContactSubmissionRead,
)


class TestContactFormSchemas:
    """Tests for contact form schemas."""

    def test_contact_form_request_valid(self):
        """Valid contact form should be accepted."""
        with patch("app.api.v1.public.contact.settings") as mock_settings:
            mock_settings.CONTACT_REQUIRE_SUBJECT = False
            mock_settings.CONTACT_REQUIRE_PHONE = False

            form = ContactFormRequest(
                name="John Doe",
                email="john@example.com",
                message="This is a test message that is long enough.",
            )
            assert form.name == "John Doe"
            assert form.email == "john@example.com"
            assert form.website is None

    def test_contact_form_request_with_optional_fields(self):
        """Form with optional fields should be accepted."""
        with patch("app.api.v1.public.contact.settings") as mock_settings:
            mock_settings.CONTACT_REQUIRE_SUBJECT = False
            mock_settings.CONTACT_REQUIRE_PHONE = False

            form = ContactFormRequest(
                name="John Doe",
                email="john@example.com",
                message="This is a test message that is long enough.",
                subject="Test inquiry",
                phone="+1-555-1234",
                company="Acme Inc",
                extra_fields={"budget": "10k-50k", "project_type": "web"},
                source="pricing-page",
            )
            assert form.subject == "Test inquiry"
            assert form.phone == "+1-555-1234"
            assert form.company == "Acme Inc"
            assert form.extra_fields["budget"] == "10k-50k"
            assert form.source == "pricing-page"

    def test_contact_form_request_with_honeypot_fails(self):
        """Form with honeypot field filled should be rejected."""
        with patch("app.api.v1.public.contact.settings") as mock_settings:
            mock_settings.CONTACT_REQUIRE_SUBJECT = False
            mock_settings.CONTACT_REQUIRE_PHONE = False

            with pytest.raises(ValueError, match="Invalid form submission"):
                ContactFormRequest(
                    name="Bot",
                    email="bot@spam.com",
                    message="Click this link for amazing deals!",
                    website="http://spam-site.com",  # Honeypot filled
                )

    def test_contact_form_request_name_too_short(self):
        """Name that is too short should be rejected."""
        with pytest.raises(ValueError):
            ContactFormRequest(
                name="J",  # Too short (min 2)
                email="john@example.com",
                message="This is a test message.",
            )

    def test_contact_form_request_message_too_short(self):
        """Message that is too short should be rejected."""
        with pytest.raises(ValueError):
            ContactFormRequest(
                name="John",
                email="john@example.com",
                message="Short",  # Too short (min 10)
            )

    def test_contact_form_request_invalid_email(self):
        """Invalid email should be rejected."""
        with pytest.raises(ValueError):
            ContactFormRequest(
                name="John",
                email="not-an-email",
                message="This is a test message.",
            )

    def test_contact_form_request_required_subject(self):
        """Subject should be required when configured."""
        with patch("app.api.v1.public.contact.settings") as mock_settings:
            mock_settings.CONTACT_REQUIRE_SUBJECT = True
            mock_settings.CONTACT_REQUIRE_PHONE = False

            with pytest.raises(ValueError, match="Subject is required"):
                ContactFormRequest(
                    name="John",
                    email="john@example.com",
                    message="This is a test message.",
                )

    def test_contact_form_request_required_phone(self):
        """Phone should be required when configured."""
        with patch("app.api.v1.public.contact.settings") as mock_settings:
            mock_settings.CONTACT_REQUIRE_SUBJECT = False
            mock_settings.CONTACT_REQUIRE_PHONE = True

            with pytest.raises(ValueError, match="Phone number is required"):
                ContactFormRequest(
                    name="John",
                    email="john@example.com",
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

    def test_contact_message_legacy(self):
        """ContactMessage (legacy) should store all fields correctly."""
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


class TestContactSubmissionModel:
    """Tests for ContactSubmission database model."""

    def test_contact_submission_create(self):
        """ContactSubmissionCreate should validate correctly."""
        create_data = ContactSubmissionCreate(
            name="John Doe",
            email="john@example.com",
            message="This is a test message.",
            subject="Test inquiry",
            phone="+1-555-1234",
            company="Acme Inc",
            extra_fields={"budget": "10k-50k"},
            source="homepage",
        )
        assert create_data.name == "John Doe"
        assert create_data.extra_fields["budget"] == "10k-50k"

    def test_contact_submission_read(self):
        """ContactSubmissionRead should serialize correctly."""
        submission = ContactSubmission(
            id="sub_123",
            reference_id="CNT-12345678",
            name="John Doe",
            email="john@example.com",
            message="Test message",
            subject="Test",
            phone="+1-555-1234",
            company="Acme Inc",
            extra_fields={"budget": "10k"},
            source="homepage",
            status="new",
            ip_address="127.0.0.1",
        )
        read_data = ContactSubmissionRead.model_validate(submission)
        assert read_data.reference_id == "CNT-12345678"
        assert read_data.status == "new"

    def test_contact_submission_status_values(self):
        """ContactSubmission should support all status values."""
        for status_val in ["new", "read", "replied", "archived"]:
            submission = ContactSubmission(
                id=f"sub_{status_val}",
                reference_id=f"CNT-{status_val.upper()}",
                name="John",
                email="john@example.com",
                message="Test message",
                status=status_val,
            )
            assert submission.status == status_val


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
        from app.api.v1.public.contact import _get_rate_limit_config, contact_rate_limiter

        # Use a unique key for this test
        test_key = f"test_contact_rate_{datetime.utcnow().timestamp()}"

        with patch("app.api.v1.public.contact.settings") as mock_settings:
            mock_settings.CONTACT_RATE_LIMIT = "5/hour"

            rate_config = _get_rate_limit_config()
            allowed, remaining, _ = await contact_rate_limiter.is_allowed(
                test_key,
                rate_config,
            )

            assert allowed is True
            assert remaining >= 0


class TestContactFormEndpoint:
    """Tests for contact form endpoint behavior."""

    @pytest.mark.asyncio
    async def test_submit_contact_form_success(self):
        """Successful contact form submission with database."""
        from app.api.v1.public.contact import submit_contact_form

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "Mozilla/5.0"

        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("app.api.v1.public.contact.settings") as mock_settings:
            mock_settings.CONTACT_REQUIRE_SUBJECT = False
            mock_settings.CONTACT_REQUIRE_PHONE = False
            mock_settings.CONTACT_RATE_LIMIT = "5/hour"
            mock_settings.ADMIN_EMAIL = None
            mock_settings.CONTACT_SEND_CONFIRMATION = False
            mock_settings.CONTACT_WEBHOOK_URL = None

            form = ContactFormRequest(
                name="John Doe",
                email="john@example.com",
                message="This is a test message that is long enough.",
                form_timestamp=str(datetime.utcnow().timestamp() - 10),
            )

            with patch(
                "app.api.v1.public.contact.contact_rate_limiter"
            ) as mock_limiter:
                mock_limiter.is_allowed = AsyncMock(return_value=(True, 4, 3600))

                with patch(
                    "app.api.v1.public.contact._cache_submission"
                ) as mock_cache:
                    mock_cache.return_value = None

                    with patch("app.api.v1.public.contact.enqueue") as mock_enqueue:
                        mock_enqueue.side_effect = Exception("No queue")

                        response = await submit_contact_form(
                            mock_request, form, mock_session
                        )

                        assert response.success is True
                        assert response.reference_id is not None
                        assert response.reference_id.startswith("CNT-")
                        mock_session.add.assert_called()
                        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_submit_contact_form_rate_limited(self):
        """Rate limited contact form submission should return 429."""
        from fastapi import HTTPException

        from app.api.v1.public.contact import submit_contact_form

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"

        mock_session = MagicMock()

        with patch("app.api.v1.public.contact.settings") as mock_settings:
            mock_settings.CONTACT_REQUIRE_SUBJECT = False
            mock_settings.CONTACT_REQUIRE_PHONE = False
            mock_settings.CONTACT_RATE_LIMIT = "5/hour"

            form = ContactFormRequest(
                name="John Doe",
                email="john@example.com",
                message="This is a test message that is long enough.",
            )

            with patch(
                "app.api.v1.public.contact.contact_rate_limiter"
            ) as mock_limiter:
                mock_limiter.is_allowed = AsyncMock(return_value=(False, 0, 3600))

                with pytest.raises(HTTPException) as exc_info:
                    await submit_contact_form(mock_request, form, mock_session)

                assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_submit_contact_form_timing_spam(self):
        """Spam detected by timing should return fake success."""
        from app.api.v1.public.contact import submit_contact_form

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"

        mock_session = MagicMock()

        with patch("app.api.v1.public.contact.settings") as mock_settings:
            mock_settings.CONTACT_REQUIRE_SUBJECT = False
            mock_settings.CONTACT_REQUIRE_PHONE = False
            mock_settings.CONTACT_RATE_LIMIT = "5/hour"

            form = ContactFormRequest(
                name="Bot",
                email="bot@example.com",
                message="This is spam content that was submitted too quickly.",
                form_timestamp=str(datetime.utcnow().timestamp() - 1),
            )

            with patch(
                "app.api.v1.public.contact.contact_rate_limiter"
            ) as mock_limiter:
                mock_limiter.is_allowed = AsyncMock(return_value=(True, 4, 3600))

                response = await submit_contact_form(mock_request, form, mock_session)

                assert response.success is True
                assert response.reference_id is not None
                # Should NOT save to database for spam
                mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_contact_status(self):
        """Contact status endpoint should return rate limit and config info."""
        from app.api.v1.public.contact import get_contact_status

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"

        with patch("app.api.v1.public.contact.settings") as mock_settings:
            mock_settings.CONTACT_RATE_LIMIT = "5/hour"
            mock_settings.CONTACT_REQUIRE_SUBJECT = True
            mock_settings.CONTACT_REQUIRE_PHONE = False
            mock_settings.CONTACT_SEND_CONFIRMATION = True

            with patch(
                "app.api.v1.public.contact.contact_rate_limiter"
            ) as mock_limiter:
                mock_limiter.is_allowed = AsyncMock(return_value=(True, 3, 3600))

                status = await get_contact_status(mock_request)

                assert status["available"] is True
                assert status["rate_limit"]["limit"] == 5
                assert status["rate_limit"]["remaining"] == 3
                assert status["config"]["require_subject"] is True
                assert status["config"]["require_phone"] is False
                assert status["config"]["sends_confirmation"] is True


class TestConfirmationEmail:
    """Tests for confirmation email functionality."""

    @pytest.mark.asyncio
    async def test_send_confirmation_when_enabled(self):
        """Should send confirmation when CONTACT_SEND_CONFIRMATION=true."""
        from app.api.v1.public.contact import _send_confirmation_email

        submission = ContactSubmission(
            id="sub_123",
            reference_id="CNT-12345678",
            name="John Doe",
            email="john@example.com",
            message="Test message",
        )

        with patch("app.api.v1.public.contact.settings") as mock_settings:
            mock_settings.CONTACT_SEND_CONFIRMATION = True
            mock_settings.PROJECT_NAME = "TestApp"

            with patch(
                "app.api.v1.public.contact.get_email_service"
            ) as mock_email:
                mock_service = MagicMock()
                mock_service.send_raw = AsyncMock(return_value=True)
                mock_email.return_value = mock_service

                await _send_confirmation_email(submission)

                mock_service.send_raw.assert_called_once()
                call_kwargs = mock_service.send_raw.call_args.kwargs
                assert call_kwargs["to"] == "john@example.com"
                assert "TestApp" in call_kwargs["subject"]

    @pytest.mark.asyncio
    async def test_skip_confirmation_when_disabled(self):
        """Should skip confirmation when CONTACT_SEND_CONFIRMATION=false."""
        from app.api.v1.public.contact import _send_confirmation_email

        submission = ContactSubmission(
            id="sub_123",
            reference_id="CNT-12345678",
            name="John Doe",
            email="john@example.com",
            message="Test message",
        )

        with patch("app.api.v1.public.contact.settings") as mock_settings:
            mock_settings.CONTACT_SEND_CONFIRMATION = False

            with patch(
                "app.api.v1.public.contact.get_email_service"
            ) as mock_email:
                mock_service = MagicMock()
                mock_email.return_value = mock_service

                await _send_confirmation_email(submission)

                mock_service.send_raw.assert_not_called()


class TestWebhook:
    """Tests for webhook functionality."""

    @pytest.mark.asyncio
    async def test_send_webhook_when_configured(self):
        """Should send webhook when CONTACT_WEBHOOK_URL is set."""
        from app.api.v1.public.contact import _send_webhook

        submission = ContactSubmission(
            id="sub_123",
            reference_id="CNT-12345678",
            name="John Doe",
            email="john@example.com",
            message="Test message",
            phone="+1-555-1234",
            company="Acme Inc",
            extra_fields={"budget": "10k"},
        )

        with patch("app.api.v1.public.contact.settings") as mock_settings:
            mock_settings.CONTACT_WEBHOOK_URL = "https://example.com/webhook"
            mock_settings.SECRET_KEY = "test-secret-key"

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.raise_for_status = MagicMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                result = await _send_webhook(submission)

                assert result is True
                mock_client.post.assert_called_once()
                call_args = mock_client.post.call_args
                assert call_args[0][0] == "https://example.com/webhook"
                assert "X-Webhook-Signature" in call_args[1]["headers"]

    @pytest.mark.asyncio
    async def test_skip_webhook_when_not_configured(self):
        """Should skip webhook when CONTACT_WEBHOOK_URL is not set."""
        from app.api.v1.public.contact import _send_webhook

        submission = ContactSubmission(
            id="sub_123",
            reference_id="CNT-12345678",
            name="John Doe",
            email="john@example.com",
            message="Test message",
        )

        with patch("app.api.v1.public.contact.settings") as mock_settings:
            mock_settings.CONTACT_WEBHOOK_URL = None

            result = await _send_webhook(submission)

            assert result is False


class TestAdminNotification:
    """Tests for admin notification functionality."""

    @pytest.mark.asyncio
    async def test_send_admin_notification_with_extra_fields(self):
        """Should include extra fields in admin notification."""
        from app.api.v1.public.contact import _send_admin_notification

        submission = ContactSubmission(
            id="sub_123",
            reference_id="CNT-12345678",
            name="John Doe",
            email="john@example.com",
            message="Test message",
            phone="+1-555-1234",
            company="Acme Inc",
            subject="Test inquiry",
            extra_fields={"budget": "10k-50k", "project_type": "web"},
            source="pricing-page",
        )

        with patch("app.api.v1.public.contact.settings") as mock_settings:
            mock_settings.ADMIN_EMAIL = "admin@example.com"

            with patch(
                "app.api.v1.public.contact.get_email_service"
            ) as mock_email:
                mock_service = MagicMock()
                mock_service.send_raw = AsyncMock(return_value=True)
                mock_email.return_value = mock_service

                await _send_admin_notification(submission)

                mock_service.send_raw.assert_called_once()
                call_kwargs = mock_service.send_raw.call_args.kwargs
                assert call_kwargs["to"] == "admin@example.com"
                assert "budget" in call_kwargs["html_content"]
                assert "Acme Inc" in call_kwargs["html_content"]

    @pytest.mark.asyncio
    async def test_skip_admin_notification_without_email(self):
        """Should skip admin notification when ADMIN_EMAIL is not set."""
        from app.api.v1.public.contact import _send_admin_notification

        submission = ContactSubmission(
            id="sub_123",
            reference_id="CNT-12345678",
            name="John Doe",
            email="john@example.com",
            message="Test message",
        )

        with patch("app.api.v1.public.contact.settings") as mock_settings:
            mock_settings.ADMIN_EMAIL = None

            with patch(
                "app.api.v1.public.contact.get_email_service"
            ) as mock_email:
                mock_service = MagicMock()
                mock_email.return_value = mock_service

                await _send_admin_notification(submission)

                mock_service.send_raw.assert_not_called()


class TestCacheSubmission:
    """Tests for Redis cache functionality."""

    @pytest.mark.asyncio
    async def test_cache_submission_with_redis(self):
        """Should cache submission in Redis when available."""
        from app.api.v1.public.contact import _cache_submission

        submission = ContactSubmission(
            id="sub_123",
            reference_id="CNT-12345678",
            name="John Doe",
            email="john@example.com",
            message="Test message",
            status="new",
        )

        with patch("app.api.v1.public.contact.get_redis") as mock_get_redis:
            mock_redis = MagicMock()
            mock_redis.setex = AsyncMock()
            mock_get_redis.return_value = mock_redis

            await _cache_submission(submission)

            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args
            assert "contact:CNT-12345678" in call_args[0]

    @pytest.mark.asyncio
    async def test_cache_submission_without_redis(self):
        """Should handle missing Redis gracefully."""
        from app.api.v1.public.contact import _cache_submission

        submission = ContactSubmission(
            id="sub_123",
            reference_id="CNT-12345678",
            name="John Doe",
            email="john@example.com",
            message="Test message",
        )

        with patch("app.api.v1.public.contact.get_redis") as mock_get_redis:
            mock_get_redis.return_value = None

            # Should not raise
            await _cache_submission(submission)
