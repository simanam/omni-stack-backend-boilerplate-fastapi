"""
Unit tests for enhanced Prometheus metrics (Phase 12.5).
"""

import asyncio
import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestMetricsBasics:
    """Test basic metrics functionality."""

    def test_prometheus_available_check(self):
        """Test that PROMETHEUS_AVAILABLE is correctly set."""
        from app.core.metrics import PROMETHEUS_AVAILABLE

        # Should be True if prometheus_client is installed
        assert isinstance(PROMETHEUS_AVAILABLE, bool)

    def test_app_start_time_initialized(self):
        """Test that APP_START_TIME is set on import."""
        from app.core.metrics import APP_START_TIME

        assert isinstance(APP_START_TIME, datetime)
        assert APP_START_TIME.tzinfo == UTC

    def test_get_metrics_returns_bytes(self):
        """Test that get_metrics returns bytes and content type."""
        from app.core.metrics import get_metrics

        metrics_output, content_type = get_metrics()
        assert isinstance(metrics_output, bytes)
        assert isinstance(content_type, str)


class TestRequestMetrics:
    """Test HTTP request metrics."""

    def test_record_request(self):
        """Test recording HTTP request metrics."""
        from app.core.metrics import record_request

        # Should not raise
        record_request("GET", "/api/v1/users", 200, 0.05)
        record_request("POST", "/api/v1/users", 201, 0.1)
        record_request("GET", "/api/v1/users", 500, 0.5)

    def test_track_request_metrics_context_manager(self):
        """Test request metrics context manager."""
        from app.core.metrics import track_request_metrics

        with track_request_metrics("GET", "/api/v1/test"):
            time.sleep(0.01)  # Simulate work

        # Should complete without error

    def test_track_request_metrics_with_exception(self):
        """Test that request metrics are recorded even on exception."""
        from app.core.metrics import track_request_metrics

        with pytest.raises(ValueError), track_request_metrics("GET", "/api/v1/error"):
            raise ValueError("Test error")


class TestDatabaseMetrics:
    """Test database metrics."""

    def test_track_db_query_success(self):
        """Test tracking successful database queries."""
        from app.core.metrics import track_db_query

        with track_db_query("SELECT", "users"):
            time.sleep(0.001)

    def test_track_db_query_error(self):
        """Test that DB errors are recorded."""
        from app.core.metrics import track_db_query

        with pytest.raises(RuntimeError), track_db_query("INSERT", "users"):
            raise RuntimeError("DB error")

    def test_update_db_pool_metrics(self):
        """Test updating connection pool metrics."""
        from app.core.metrics import update_db_pool_metrics

        update_db_pool_metrics(idle=5, active=10, overflow=2)


class TestCacheMetrics:
    """Test cache/Redis metrics."""

    def test_record_cache_hit(self):
        """Test recording cache hit."""
        from app.core.metrics import record_cache_access

        record_cache_access("redis", hit=True)

    def test_record_cache_miss(self):
        """Test recording cache miss."""
        from app.core.metrics import record_cache_access

        record_cache_access("redis", hit=False)


class TestJobMetrics:
    """Test background job metrics."""

    def test_record_job_enqueued(self):
        """Test recording job enqueue."""
        from app.core.metrics import record_job_metric

        record_job_metric("send_email", "enqueued")

    def test_record_job_completed_with_duration(self):
        """Test recording completed job with duration."""
        from app.core.metrics import record_job_metric

        record_job_metric("send_email", "completed", duration=1.5)

    def test_record_job_failed(self):
        """Test recording failed job."""
        from app.core.metrics import record_job_metric

        record_job_metric("send_email", "failed", duration=0.5)


class TestLLMMetrics:
    """Test AI/LLM metrics."""

    def test_record_llm_usage_success(self):
        """Test recording successful LLM usage."""
        from app.core.metrics import record_llm_usage

        record_llm_usage(
            provider="openai",
            model="gpt-4o",
            status="success",
            prompt_tokens=100,
            completion_tokens=50,
            duration=2.5,
        )

    def test_record_llm_usage_error(self):
        """Test recording LLM error."""
        from app.core.metrics import record_llm_usage

        record_llm_usage(
            provider="anthropic",
            model="claude-sonnet-4-5",
            status="error",
        )

    def test_record_llm_usage_without_tokens(self):
        """Test recording LLM usage without token counts."""
        from app.core.metrics import record_llm_usage

        record_llm_usage(
            provider="openai",
            model="gpt-4o-mini",
            status="success",
        )


class TestExternalServiceMetrics:
    """Test external service metrics."""

    @pytest.mark.asyncio
    async def test_track_external_service_success(self):
        """Test tracking successful external service call."""
        from app.core.metrics import track_external_service

        @track_external_service("stripe", "create_customer")
        async def mock_stripe_call():
            await asyncio.sleep(0.01)
            return {"id": "cus_123"}

        result = await mock_stripe_call()
        assert result["id"] == "cus_123"

    @pytest.mark.asyncio
    async def test_track_external_service_error(self):
        """Test tracking external service error."""
        from app.core.metrics import track_external_service

        @track_external_service("stripe", "create_customer")
        async def mock_stripe_error():
            raise ConnectionError("API unavailable")

        with pytest.raises(ConnectionError):
            await mock_stripe_error()


class TestBusinessMetrics:
    """Test business metrics."""

    def test_update_business_metrics(self):
        """Test updating business metrics."""
        from app.core.metrics import update_business_metrics

        update_business_metrics(
            active_users=100,
            inactive_users=20,
            subscriptions={"free": 80, "pro": 30, "enterprise": 10},
        )

    def test_update_business_metrics_partial(self):
        """Test updating only some business metrics."""
        from app.core.metrics import update_business_metrics

        update_business_metrics(active_users=50)
        update_business_metrics(subscriptions={"pro": 25})


class TestSystemMetrics:
    """Test system metrics (Phase 12.5)."""

    def test_update_system_metrics(self):
        """Test updating system metrics."""
        from app.core.metrics import update_system_metrics

        # Should not raise
        update_system_metrics()

    def test_init_system_info(self):
        """Test initializing system info."""
        from app.core.metrics import init_system_info

        # Should not raise
        init_system_info()

    def test_app_uptime_increases(self):
        """Test that uptime increases over time."""
        from app.core.metrics import APP_START_TIME

        uptime1 = (datetime.now(UTC) - APP_START_TIME).total_seconds()
        time.sleep(0.01)
        uptime2 = (datetime.now(UTC) - APP_START_TIME).total_seconds()

        assert uptime2 > uptime1


class TestAuthMetrics:
    """Test authentication metrics (Phase 12.5)."""

    def test_record_auth_event_login(self):
        """Test recording login event."""
        from app.core.metrics import record_auth_event

        record_auth_event("login", provider="jwt")

    def test_record_auth_event_signup(self):
        """Test recording signup event."""
        from app.core.metrics import record_auth_event

        record_auth_event("signup", provider="clerk")

    def test_record_auth_event_logout(self):
        """Test recording logout event."""
        from app.core.metrics import record_auth_event

        record_auth_event("logout")

    def test_record_auth_failure_invalid_token(self):
        """Test recording auth failure."""
        from app.core.metrics import record_auth_failure

        record_auth_failure("invalid_token")

    def test_record_auth_failure_expired(self):
        """Test recording expired token failure."""
        from app.core.metrics import record_auth_failure

        record_auth_failure("expired_token")

    def test_record_token_operations(self):
        """Test recording token operations."""
        from app.core.metrics import record_token_operation

        record_token_operation("issued")
        record_token_operation("verified")
        record_token_operation("revoked")

    def test_update_active_sessions(self):
        """Test updating active sessions count."""
        from app.core.metrics import update_active_sessions

        update_active_sessions(42)


class TestRateLimitMetrics:
    """Test rate limiting metrics (Phase 12.5)."""

    def test_record_rate_limit_hit(self):
        """Test recording rate limit hit."""
        from app.core.metrics import record_rate_limit_hit

        record_rate_limit_hit("/api/v1/users", "ip")

    def test_record_rate_limit_hit_by_user(self):
        """Test recording rate limit hit by user."""
        from app.core.metrics import record_rate_limit_hit

        record_rate_limit_hit("/api/v1/ai/chat", "user")


class TestWebSocketMetrics:
    """Test WebSocket metrics (Phase 12.5)."""

    def test_record_websocket_connect(self):
        """Test recording WebSocket connection."""
        from app.core.metrics import record_websocket_connect

        record_websocket_connect()

    def test_record_websocket_disconnect(self):
        """Test recording WebSocket disconnection."""
        from app.core.metrics import record_websocket_disconnect

        record_websocket_disconnect()

    def test_record_websocket_auth(self):
        """Test recording WebSocket authentication."""
        from app.core.metrics import record_websocket_auth

        record_websocket_auth(authenticated=True)
        record_websocket_auth(authenticated=False)

    def test_record_websocket_message(self):
        """Test recording WebSocket messages."""
        from app.core.metrics import record_websocket_message

        record_websocket_message("sent", "message")
        record_websocket_message("received", "message")
        record_websocket_message("sent", "ping")
        record_websocket_message("received", "pong")


class TestWebhookMetrics:
    """Test webhook metrics (Phase 12.5)."""

    def test_record_webhook_event_processed(self):
        """Test recording processed webhook event."""
        from app.core.metrics import record_webhook_event

        record_webhook_event(
            provider="stripe",
            event_type="invoice.paid",
            status="processed",
            duration=0.05,
        )

    def test_record_webhook_event_failed(self):
        """Test recording failed webhook event."""
        from app.core.metrics import record_webhook_event

        record_webhook_event(
            provider="clerk",
            event_type="user.created",
            status="failed",
        )

    def test_record_webhook_event_duplicate(self):
        """Test recording duplicate webhook event."""
        from app.core.metrics import record_webhook_event

        record_webhook_event(
            provider="stripe",
            event_type="checkout.completed",
            status="duplicate",
        )


class TestMetricsMiddleware:
    """Test MetricsMiddleware (Phase 12.5)."""

    def test_middleware_init(self):
        """Test middleware initialization."""
        from app.core.metrics import MetricsMiddleware

        mock_app = MagicMock()
        middleware = MetricsMiddleware(mock_app)
        assert middleware.app == mock_app

    def test_normalize_path_uuid(self):
        """Test path normalization with UUID."""
        from app.core.metrics import MetricsMiddleware

        middleware = MetricsMiddleware(MagicMock())
        normalized = middleware._normalize_path(
            "/api/v1/users/123e4567-e89b-12d3-a456-426614174000"
        )
        assert normalized == "/api/v1/users/{id}"

    def test_normalize_path_numeric_id(self):
        """Test path normalization with numeric ID."""
        from app.core.metrics import MetricsMiddleware

        middleware = MetricsMiddleware(MagicMock())
        normalized = middleware._normalize_path("/api/v1/projects/42")
        assert normalized == "/api/v1/projects/{id}"

    def test_normalize_path_multiple_ids(self):
        """Test path normalization with multiple IDs."""
        from app.core.metrics import MetricsMiddleware

        middleware = MetricsMiddleware(MagicMock())
        normalized = middleware._normalize_path(
            "/api/v1/users/123e4567-e89b-12d3-a456-426614174000/projects/99"
        )
        assert normalized == "/api/v1/users/{id}/projects/{id}"

    def test_normalize_path_no_ids(self):
        """Test path normalization without IDs."""
        from app.core.metrics import MetricsMiddleware

        middleware = MetricsMiddleware(MagicMock())
        normalized = middleware._normalize_path("/api/v1/public/health")
        assert normalized == "/api/v1/public/health"

    @pytest.mark.asyncio
    async def test_middleware_skips_health_endpoint(self):
        """Test that middleware skips health endpoints."""
        from app.core.metrics import MetricsMiddleware

        call_count = 0

        async def mock_app(scope, receive, send):
            nonlocal call_count
            call_count += 1

        middleware = MetricsMiddleware(mock_app)

        scope = {"type": "http", "path": "/api/v1/public/health", "method": "GET"}
        await middleware(scope, AsyncMock(), AsyncMock())

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_middleware_skips_non_http(self):
        """Test that middleware passes through non-HTTP requests."""
        from app.core.metrics import MetricsMiddleware

        call_count = 0

        async def mock_app(scope, receive, send):
            nonlocal call_count
            call_count += 1

        middleware = MetricsMiddleware(mock_app)

        scope = {"type": "websocket", "path": "/ws"}
        await middleware(scope, AsyncMock(), AsyncMock())

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_middleware_tracks_request(self):
        """Test that middleware tracks HTTP requests."""
        from app.core.metrics import MetricsMiddleware

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200})
            await send({"type": "http.response.body", "body": b""})

        middleware = MetricsMiddleware(mock_app)

        scope = {"type": "http", "path": "/api/v1/test", "method": "GET"}
        await middleware(scope, AsyncMock(), AsyncMock())

    @pytest.mark.asyncio
    async def test_middleware_tracks_error_response(self):
        """Test that middleware tracks error responses."""
        from app.core.metrics import MetricsMiddleware

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 500})
            await send({"type": "http.response.body", "body": b"Error"})

        middleware = MetricsMiddleware(mock_app)

        scope = {"type": "http", "path": "/api/v1/error", "method": "GET"}
        await middleware(scope, AsyncMock(), AsyncMock())


class TestMetricsSnapshot:
    """Test metrics snapshot collection (Phase 12.5)."""

    @pytest.mark.asyncio
    async def test_collect_metrics_snapshot(self):
        """Test collecting metrics snapshot."""
        from app.core.metrics import collect_metrics_snapshot

        snapshot = await collect_metrics_snapshot()

        assert "uptime_seconds" in snapshot
        assert snapshot["uptime_seconds"] >= 0
        assert "prometheus_available" in snapshot
        assert "environment" in snapshot


class TestMetricsInitialization:
    """Test metrics initialization (Phase 12.5)."""

    def test_init_metrics(self):
        """Test metrics initialization function."""
        from app.core.metrics import init_metrics

        # Should not raise
        init_metrics()

    def test_init_metrics_idempotent(self):
        """Test that init_metrics can be called multiple times."""
        from app.core.metrics import init_metrics

        init_metrics()
        init_metrics()  # Should not raise


class TestDummyMetrics:
    """Test dummy metrics when prometheus_client is not installed."""

    def test_dummy_metric_labels(self):
        """Test that DummyMetric.labels returns self."""
        # This tests the fallback behavior
        from app.core.metrics import PROMETHEUS_AVAILABLE

        if not PROMETHEUS_AVAILABLE:
            from app.core.metrics import DummyMetric

            metric = DummyMetric()
            result = metric.labels(foo="bar")
            assert result is metric

    def test_dummy_metric_operations(self):
        """Test DummyMetric operations don't raise."""
        from app.core.metrics import PROMETHEUS_AVAILABLE

        if not PROMETHEUS_AVAILABLE:
            from app.core.metrics import DummyMetric

            metric = DummyMetric()
            metric.inc()
            metric.dec()
            metric.set(42)
            metric.observe(1.5)
            metric.info({"key": "value"})
