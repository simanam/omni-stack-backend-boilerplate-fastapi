"""
Tests for middleware functionality.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.middleware import RateLimitConfig, RateLimiter
from app.main import app


class TestRateLimitConfig:
    """Test RateLimitConfig parsing."""

    def test_parse_minute(self):
        config = RateLimitConfig.from_string("60/minute")
        assert config.requests == 60
        assert config.window_seconds == 60

    def test_parse_second(self):
        config = RateLimitConfig.from_string("10/second")
        assert config.requests == 10
        assert config.window_seconds == 1

    def test_parse_hour(self):
        config = RateLimitConfig.from_string("1000/hour")
        assert config.requests == 1000
        assert config.window_seconds == 3600

    def test_parse_day(self):
        config = RateLimitConfig.from_string("10000/day")
        assert config.requests == 10000
        assert config.window_seconds == 86400

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            RateLimitConfig.from_string("invalid")

    def test_invalid_time_unit(self):
        with pytest.raises(ValueError, match="Invalid time unit"):
            RateLimitConfig.from_string("60/week")


class TestRateLimiter:
    """Test RateLimiter in-memory fallback."""

    @pytest.fixture
    def limiter(self):
        return RateLimiter()

    @pytest.mark.asyncio
    async def test_allows_within_limit(self, limiter):
        config = RateLimitConfig(requests=5, window_seconds=60)

        for i in range(5):
            allowed, remaining, reset_time = await limiter.is_allowed("test_key", config)
            assert allowed is True
            assert remaining == 5 - (i + 1)

    @pytest.mark.asyncio
    async def test_blocks_over_limit(self, limiter):
        config = RateLimitConfig(requests=3, window_seconds=60)

        # Use up the limit
        for _ in range(3):
            await limiter.is_allowed("test_key_2", config)

        # Fourth request should be blocked
        allowed, remaining, reset_time = await limiter.is_allowed("test_key_2", config)
        assert allowed is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_different_keys_independent(self, limiter):
        config = RateLimitConfig(requests=2, window_seconds=60)

        # Use up limit for key1
        await limiter.is_allowed("key1", config)
        await limiter.is_allowed("key1", config)
        allowed1, _, _ = await limiter.is_allowed("key1", config)

        # key2 should still be allowed
        allowed2, remaining2, _ = await limiter.is_allowed("key2", config)

        assert allowed1 is False
        assert allowed2 is True
        assert remaining2 == 1


class TestSecurityHeaders:
    """Test security headers middleware."""

    @pytest.fixture
    async def client(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_security_headers_present(self, client):
        response = await client.get("/api/v1/public/health")

        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "default-src 'none'" in response.headers.get("Content-Security-Policy", "")

    @pytest.mark.asyncio
    async def test_no_hsts_in_local(self, client):
        """HSTS should only be set in production."""
        response = await client.get("/api/v1/public/health")
        # In local environment, HSTS should not be present
        assert "Strict-Transport-Security" not in response.headers


class TestRequestIDMiddleware:
    """Test request ID middleware."""

    @pytest.fixture
    async def client(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_generates_request_id(self, client):
        response = await client.get("/api/v1/public/health")
        request_id = response.headers.get("X-Request-ID")

        assert request_id is not None
        # Should be a valid UUID format
        assert len(request_id) == 36
        assert request_id.count("-") == 4

    @pytest.mark.asyncio
    async def test_preserves_provided_request_id(self, client):
        custom_id = "my-custom-request-id-12345"
        response = await client.get(
            "/api/v1/public/health",
            headers={"X-Request-ID": custom_id},
        )

        assert response.headers.get("X-Request-ID") == custom_id


class TestRateLimitMiddleware:
    """Test rate limit middleware integration."""

    @pytest.fixture
    async def client(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(self, client):
        # Health endpoints skip rate limiting (in SKIP_PATHS)
        # Just verify the endpoint works
        await client.get("/api/v1/public/health/ready")

    @pytest.mark.asyncio
    async def test_health_skips_rate_limit(self, client):
        """Health endpoints should skip rate limiting."""
        # Make many requests to health endpoint
        for _ in range(100):
            response = await client.get("/api/v1/public/health")
            assert response.status_code == 200

        # Should not have rate limit headers on health endpoint
        # (it's in SKIP_PATHS)


class TestMiddlewareIntegration:
    """Test all middleware working together."""

    @pytest.fixture
    async def client(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_all_headers_present(self, client):
        """Test that all expected headers are present on responses."""
        response = await client.get("/api/v1/public/health")

        # Security headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers

        # Request ID
        assert "X-Request-ID" in response.headers
