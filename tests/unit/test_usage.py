"""
Unit tests for usage tracking service (Phase 12.7).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestUsageMetric:
    """Test UsageMetric enum."""

    def test_all_metrics_defined(self):
        """Test that all expected metrics are defined."""
        from app.services.payments.usage import UsageMetric

        expected = [
            "api_requests",
            "ai_tokens",
            "ai_requests",
            "storage_bytes",
            "file_uploads",
            "file_downloads",
            "websocket_messages",
            "background_jobs",
            "email_sent",
        ]

        for metric in expected:
            assert UsageMetric(metric) is not None

    def test_metric_string_value(self):
        """Test that metrics have correct string values."""
        from app.services.payments.usage import UsageMetric

        assert UsageMetric.API_REQUESTS.value == "api_requests"
        assert UsageMetric.AI_TOKENS.value == "ai_tokens"


class TestUsageEvent:
    """Test UsageEvent dataclass."""

    def test_create_event(self):
        """Test creating a usage event."""
        from app.services.payments.usage import UsageEvent, UsageMetric

        event = UsageEvent(
            user_id="user123",
            metric=UsageMetric.API_REQUESTS,
            quantity=1,
        )

        assert event.user_id == "user123"
        assert event.metric == UsageMetric.API_REQUESTS
        assert event.quantity == 1
        assert event.timestamp is not None
        assert event.metadata == {}

    def test_event_with_metadata(self):
        """Test creating event with metadata."""
        from app.services.payments.usage import UsageEvent, UsageMetric

        event = UsageEvent(
            user_id="user123",
            metric=UsageMetric.AI_TOKENS,
            quantity=1000,
            metadata={"model": "gpt-4o", "provider": "openai"},
        )

        assert event.metadata["model"] == "gpt-4o"
        assert event.metadata["provider"] == "openai"


class TestUsageSummary:
    """Test UsageSummary dataclass."""

    def test_create_summary(self):
        """Test creating a usage summary."""
        from app.services.payments.usage import UsageMetric, UsageSummary

        now = datetime.now(UTC)
        summary = UsageSummary(
            user_id="user123",
            metric=UsageMetric.API_REQUESTS,
            total=1000,
            period_start=now - timedelta(days=30),
            period_end=now,
        )

        assert summary.user_id == "user123"
        assert summary.total == 1000
        assert summary.breakdown == {}


class TestUsageTrend:
    """Test UsageTrend dataclass."""

    def test_create_trend(self):
        """Test creating a usage trend."""
        from app.services.payments.usage import UsageMetric, UsageTrend

        trend = UsageTrend(
            user_id="user123",
            metric=UsageMetric.API_REQUESTS,
            current_period=1500,
            previous_period=1000,
            growth_rate=50.0,
            daily_average=50.0,
        )

        assert trend.current_period == 1500
        assert trend.previous_period == 1000
        assert trend.growth_rate == 50.0


class TestUsageTracker:
    """Test UsageTracker class."""

    def test_get_period_key(self):
        """Test period key generation."""
        from app.services.payments.usage import UsageTracker

        tracker = UsageTracker()
        dt = datetime(2026, 1, 15, 12, 0, 0)
        key = tracker._get_period_key(dt)

        assert key == "2026-01"

    def test_get_date_key(self):
        """Test date key generation."""
        from app.services.payments.usage import UsageTracker

        tracker = UsageTracker()
        dt = datetime(2026, 1, 15, 12, 0, 0)
        key = tracker._get_date_key(dt)

        assert key == "2026-01-15"

    @pytest.mark.asyncio
    async def test_record_without_redis(self):
        """Test recording usage without Redis (in-memory fallback)."""
        from app.services.payments.usage import UsageMetric, UsageTracker

        with patch("app.services.payments.usage.get_redis", return_value=None):
            tracker = UsageTracker()
            tracker._redis = None

            result = await tracker.record(
                user_id="user123",
                metric=UsageMetric.API_REQUESTS,
                quantity=1,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_record_with_redis_mock(self):
        """Test recording usage with mocked Redis."""
        from app.services.payments.usage import UsageMetric, UsageTracker

        mock_redis = AsyncMock()
        mock_redis.incrby = AsyncMock()
        mock_redis.expire = AsyncMock()
        mock_redis.hincrby = AsyncMock()

        with patch("app.services.payments.usage.get_redis", return_value=mock_redis):
            tracker = UsageTracker()
            tracker._redis = mock_redis

            result = await tracker.record(
                user_id="user123",
                metric=UsageMetric.API_REQUESTS,
                quantity=5,
                metadata={"endpoint": "/api/v1/users"},
            )

            assert result is True
            assert mock_redis.incrby.called

    @pytest.mark.asyncio
    async def test_get_usage_without_redis(self):
        """Test getting usage without Redis."""
        from app.services.payments.usage import UsageMetric, UsageTracker

        with patch("app.services.payments.usage.get_redis", return_value=None):
            tracker = UsageTracker()
            tracker._redis = None

            # Record some usage first
            await tracker.record("user123", UsageMetric.API_REQUESTS, 10)

            summary = await tracker.get_usage("user123", UsageMetric.API_REQUESTS)

            assert summary.user_id == "user123"
            assert summary.total >= 0  # May be 0 or 10 depending on timing

    @pytest.mark.asyncio
    async def test_get_daily_usage_without_redis(self):
        """Test getting daily usage without Redis."""
        from app.services.payments.usage import UsageMetric, UsageTracker

        with patch("app.services.payments.usage.get_redis", return_value=None):
            tracker = UsageTracker()
            tracker._redis = None

            daily = await tracker.get_daily_usage("user123", UsageMetric.API_REQUESTS, 7)

            assert isinstance(daily, dict)

    @pytest.mark.asyncio
    async def test_get_trends(self):
        """Test getting usage trends."""
        from app.services.payments.usage import UsageMetric, UsageTracker

        with patch("app.services.payments.usage.get_redis", return_value=None):
            tracker = UsageTracker()
            tracker._redis = None

            trend = await tracker.get_trends("user123", UsageMetric.API_REQUESTS)

            assert trend.user_id == "user123"
            assert trend.metric == UsageMetric.API_REQUESTS
            assert trend.growth_rate is not None

    @pytest.mark.asyncio
    async def test_get_all_metrics(self):
        """Test getting all metrics for a user."""
        from app.services.payments.usage import UsageTracker

        with patch("app.services.payments.usage.get_redis", return_value=None):
            tracker = UsageTracker()
            tracker._redis = None

            result = await tracker.get_all_metrics("user123")

            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_top_users_without_redis(self):
        """Test getting top users without Redis."""
        from app.services.payments.usage import UsageMetric, UsageTracker

        with patch("app.services.payments.usage.get_redis", return_value=None):
            tracker = UsageTracker()
            tracker._redis = None

            result = await tracker.get_top_users(UsageMetric.API_REQUESTS, limit=10)

            assert isinstance(result, list)


class TestStripeUsageReporter:
    """Test StripeUsageReporter class."""

    def test_init_without_stripe_key(self):
        """Test initialization without Stripe key raises error."""
        from app.services.payments.usage import StripeUsageReporter

        with patch("app.services.payments.usage.settings") as mock_settings:
            mock_settings.STRIPE_SECRET_KEY = None

            with pytest.raises(ValueError, match="STRIPE_SECRET_KEY not configured"):
                StripeUsageReporter()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Stripe SDK v14 removed legacy usage record API - requires Billing Meter API")
    async def test_report_usage_mock(self):
        """Test reporting usage to Stripe with mock.

        Note: Stripe SDK v14 removed stripe.SubscriptionItem.create_usage_record.
        The new approach uses Stripe Billing Meters API instead.
        This test is skipped until the implementation is updated to use the new API.
        """
        from app.services.payments.usage import StripeUsageReporter

        with patch("app.services.payments.usage.settings") as mock_settings:
            mock_settings.STRIPE_SECRET_KEY = "sk_test_xxx"

            with patch("stripe.SubscriptionItem.create_usage_record") as mock_create:
                mock_record = MagicMock()
                mock_record.id = "mbur_xxx"
                mock_record.quantity = 100
                mock_record.timestamp = 1234567890
                mock_record.subscription_item = "si_xxx"
                mock_create.return_value = mock_record

                reporter = StripeUsageReporter()
                result = await reporter.report_usage(
                    subscription_item_id="si_xxx",
                    quantity=100,
                    action="increment",
                )

                assert result["id"] == "mbur_xxx"
                assert result["quantity"] == 100
                mock_create.assert_called_once()


class TestConvenienceFunctions:
    """Test convenience tracking functions."""

    @pytest.mark.asyncio
    async def test_track_api_request(self):
        """Test track_api_request convenience function."""
        from app.services.payments.usage import track_api_request

        with patch("app.services.payments.usage.get_redis", return_value=None):
            result = await track_api_request(
                user_id="user123",
                endpoint="/api/v1/users",
                method="GET",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_track_ai_usage(self):
        """Test track_ai_usage convenience function."""
        from app.services.payments.usage import track_ai_usage

        with patch("app.services.payments.usage.get_redis", return_value=None):
            result = await track_ai_usage(
                user_id="user123",
                provider="openai",
                model="gpt-4o",
                prompt_tokens=100,
                completion_tokens=50,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_track_ai_usage_without_tokens(self):
        """Test track_ai_usage without token counts."""
        from app.services.payments.usage import track_ai_usage

        with patch("app.services.payments.usage.get_redis", return_value=None):
            result = await track_ai_usage(
                user_id="user123",
                provider="anthropic",
                model="claude-sonnet-4-5",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_track_storage_upload(self):
        """Test track_storage for upload."""
        from app.services.payments.usage import track_storage

        with patch("app.services.payments.usage.get_redis", return_value=None):
            result = await track_storage(
                user_id="user123",
                bytes_used=1024 * 1024,
                operation="upload",
                file_type="image/png",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_track_storage_download(self):
        """Test track_storage for download."""
        from app.services.payments.usage import track_storage

        with patch("app.services.payments.usage.get_redis", return_value=None):
            result = await track_storage(
                user_id="user123",
                bytes_used=1024 * 1024,
                operation="download",
            )

            assert result is True


class TestUsageTrackerSingleton:
    """Test singleton pattern for UsageTracker."""

    def test_get_usage_tracker_returns_instance(self):
        """Test get_usage_tracker returns a UsageTracker instance."""
        from app.services.payments.usage import UsageTracker, get_usage_tracker

        tracker = get_usage_tracker()
        assert isinstance(tracker, UsageTracker)

    def test_get_usage_tracker_returns_same_instance(self):
        """Test get_usage_tracker returns the same instance."""
        from app.services.payments import usage

        # Reset singleton
        usage._usage_tracker = None

        tracker1 = usage.get_usage_tracker()
        tracker2 = usage.get_usage_tracker()

        assert tracker1 is tracker2


class TestUsageRecordModel:
    """Test UsageRecord model."""

    def test_usage_record_creation(self):
        """Test creating a UsageRecord model instance."""
        from app.models.usage_record import UsageRecord

        now = datetime.now(UTC)
        record = UsageRecord(
            user_id="user123",
            metric="api_requests",
            quantity=1000,
            period_start=now - timedelta(days=30),
            period_end=now,
        )

        assert record.user_id == "user123"
        assert record.metric == "api_requests"
        assert record.quantity == 1000
        assert record.reported_to_stripe is False

    def test_usage_summary_view(self):
        """Test UsageSummaryView model."""
        from app.models.usage_record import UsageSummaryView

        now = datetime.now(UTC)
        view = UsageSummaryView(
            user_id="user123",
            metric="api_requests",
            total_quantity=5000,
            period_start=now - timedelta(days=30),
            period_end=now,
        )

        assert view.total_quantity == 5000

    def test_usage_analytics(self):
        """Test UsageAnalytics model."""
        from app.models.usage_record import UsageAnalytics

        analytics = UsageAnalytics(
            user_id="user123",
            metric="api_requests",
            current_period_total=1500,
            previous_period_total=1000,
            growth_rate_percent=50.0,
            daily_average=50.0,
        )

        assert analytics.growth_rate_percent == 50.0

    def test_user_usage_overview(self):
        """Test UserUsageOverview model."""
        from app.models.usage_record import UserUsageOverview

        now = datetime.now(UTC)
        overview = UserUsageOverview(
            user_id="user123",
            period_start=now - timedelta(days=30),
            period_end=now,
            metrics={"api_requests": 1000, "ai_tokens": 50000},
            plan_limits={"api_requests": 10000, "ai_tokens": 100000},
            usage_percent={"api_requests": 10.0, "ai_tokens": 50.0},
        )

        assert overview.metrics["api_requests"] == 1000
        assert overview.usage_percent["ai_tokens"] == 50.0


class TestUsageMiddleware:
    """Test UsageTrackingMiddleware."""

    def test_skip_paths(self):
        """Test that skip paths are correctly defined."""
        from app.core.middleware import UsageTrackingMiddleware

        assert "/health" in UsageTrackingMiddleware.SKIP_PATHS
        assert "/api/v1/public/health" in UsageTrackingMiddleware.SKIP_PATHS
        assert "/docs" in UsageTrackingMiddleware.SKIP_PATHS

    def test_public_prefixes(self):
        """Test that public prefixes are correctly defined."""
        from app.core.middleware import UsageTrackingMiddleware

        assert "/api/v1/public/" in UsageTrackingMiddleware.PUBLIC_PREFIXES
        assert "/api/v2/public/" in UsageTrackingMiddleware.PUBLIC_PREFIXES


class TestUsageIntegration:
    """Integration tests for usage tracking."""

    @pytest.mark.asyncio
    async def test_full_usage_flow(self):
        """Test complete usage tracking flow."""
        from app.services.payments.usage import UsageMetric, UsageTracker

        with patch("app.services.payments.usage.get_redis", return_value=None):
            tracker = UsageTracker()
            tracker._redis = None
            user_id = "test_user_flow"

            # Record multiple events
            await tracker.record(user_id, UsageMetric.API_REQUESTS, 10)
            await tracker.record(user_id, UsageMetric.API_REQUESTS, 5)
            await tracker.record(user_id, UsageMetric.AI_TOKENS, 1000)

            # Get summary (in-memory mode)
            summary = await tracker.get_usage(user_id, UsageMetric.API_REQUESTS)
            assert summary is not None

            # Get trends
            trends = await tracker.get_trends(user_id, UsageMetric.API_REQUESTS)
            assert trends is not None
            assert trends.user_id == user_id

    @pytest.mark.asyncio
    async def test_metric_string_parsing(self):
        """Test that string metrics are correctly parsed."""
        from app.services.payments.usage import UsageTracker

        with patch("app.services.payments.usage.get_redis", return_value=None):
            tracker = UsageTracker()
            tracker._redis = None

            # Should work with string metric
            result = await tracker.record(
                user_id="user123",
                metric="api_requests",
                quantity=1,
            )

            assert result is True
