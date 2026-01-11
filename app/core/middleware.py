"""
Middleware for rate limiting, security headers, request ID tracking, and logging.
"""

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.cache import get_redis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Context variable for request ID (accessible throughout the request lifecycle)
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """Get the current request ID from context."""
    return request_id_ctx.get()


# =============================================================================
# Rate Limiting
# =============================================================================


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""

    requests: int
    window_seconds: int

    @classmethod
    def from_string(cls, s: str) -> "RateLimitConfig":
        """
        Parse rate limit string format.
        Examples: '60/minute', '10/second', '1000/hour', '10000/day'
        """
        parts = s.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid rate limit format: {s}")

        requests = int(parts[0])

        window_map = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
        }
        window = window_map.get(parts[1])
        if window is None:
            raise ValueError(f"Invalid time unit: {parts[1]}")

        return cls(requests=requests, window_seconds=window)


class RateLimiter:
    """
    Sliding window rate limiter using Redis.
    Falls back to in-memory if Redis unavailable.
    """

    def __init__(self) -> None:
        self._memory_store: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(
        self,
        key: str,
        config: RateLimitConfig,
    ) -> tuple[bool, int, int]:
        """
        Check if request is allowed.
        Returns: (allowed, remaining, reset_time)
        """
        redis_client = get_redis()
        if redis_client:
            try:
                return await self._check_redis(key, config, redis_client)
            except Exception as e:
                logger.warning(f"Redis rate limit check failed, falling back to memory: {e}")
                return await self._check_memory(key, config)
        return await self._check_memory(key, config)

    async def _check_redis(
        self,
        key: str,
        config: RateLimitConfig,
        redis_client,
    ) -> tuple[bool, int, int]:
        """Redis-backed rate limiting using sliding window."""
        now = int(time.time())
        window_start = now - config.window_seconds
        redis_key = f"ratelimit:{key}"

        pipe = redis_client.pipeline()

        # Remove old entries outside the window
        pipe.zremrangebyscore(redis_key, 0, window_start)
        # Add current request with timestamp as score
        pipe.zadd(redis_key, {f"{now}:{uuid.uuid4().hex[:8]}": now})
        # Count requests in current window
        pipe.zcard(redis_key)
        # Set key expiry to window size
        pipe.expire(redis_key, config.window_seconds)

        results = await pipe.execute()
        request_count = results[2]

        allowed = request_count <= config.requests
        remaining = max(0, config.requests - request_count)
        reset_time = now + config.window_seconds

        return allowed, remaining, reset_time

    async def _check_memory(
        self,
        key: str,
        config: RateLimitConfig,
    ) -> tuple[bool, int, int]:
        """In-memory fallback (not suitable for multi-process deployments)."""
        async with self._lock:
            now = time.time()
            window_start = now - config.window_seconds

            # Clean old entries
            if key in self._memory_store:
                self._memory_store[key] = [
                    t for t in self._memory_store[key] if t > window_start
                ]
            else:
                self._memory_store[key] = []

            # Add current request
            self._memory_store[key].append(now)
            request_count = len(self._memory_store[key])

            allowed = request_count <= config.requests
            remaining = max(0, config.requests - request_count)
            reset_time = int(now + config.window_seconds)

            return allowed, remaining, reset_time


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that applies rate limiting to all routes."""

    # Route-specific limits (path prefix -> config string)
    ROUTE_LIMITS: dict[str, str] = {
        "/api/v1/app/ai": settings.RATE_LIMIT_AI,
        "/api/v1/public/auth": settings.RATE_LIMIT_AUTH,
    }

    # Paths to skip rate limiting
    SKIP_PATHS: set[str] = {
        "/health",
        "/api/v1/public/health",
        "/api/v1/public/health/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and docs
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        # Determine rate limit config based on route
        config_str = settings.RATE_LIMIT_DEFAULT
        for prefix, limit in self.ROUTE_LIMITS.items():
            if request.url.path.startswith(prefix):
                config_str = limit
                break

        config = RateLimitConfig.from_string(config_str)

        # Build rate limit key
        # Use IP address for unauthenticated requests
        # Could be extended to use user_id for authenticated requests
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{request.url.path}"

        # Check rate limit
        allowed, remaining, reset_time = await rate_limiter.is_allowed(key, config)

        if not allowed:
            return Response(
                content='{"error":{"code":"RATE_LIMITED","message":"Rate limit exceeded. Please try again later."}}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
                headers={
                    "X-RateLimit-Limit": str(config.requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(config.window_seconds),
                },
            )

        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(config.requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response


# =============================================================================
# Security Headers
# =============================================================================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # XSS protection (legacy, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy (restrictive default for API)
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

        # Permissions Policy (disable unused browser features)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )

        # HSTS - only in production (requires HTTPS)
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response


# =============================================================================
# Request ID Tracking
# =============================================================================


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Add unique request ID to each request for tracing.
    Accepts X-Request-ID header if provided, otherwise generates one.
    """

    HEADER_NAME = "X-Request-ID"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Use provided request ID or generate a new one
        request_id = request.headers.get(self.HEADER_NAME)
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in context for access throughout request lifecycle
        token = request_id_ctx.set(request_id)

        try:
            response = await call_next(request)
            # Add request ID to response headers
            response.headers[self.HEADER_NAME] = request_id
            return response
        finally:
            request_id_ctx.reset(token)


# =============================================================================
# Request Logging
# =============================================================================


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request/response details for observability."""

    # Paths to skip logging (avoid spam from health checks)
    SKIP_PATHS: set[str] = {
        "/health",
        "/api/v1/public/health",
        "/api/v1/public/health/ready",
    }

    # Headers to redact from logs
    REDACT_HEADERS: set[str] = {
        "authorization",
        "cookie",
        "x-api-key",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for health checks
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        start_time = time.perf_counter()
        request_id = get_request_id() or "unknown"

        # Log request
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params) if request.query_params else None,
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent"),
            },
        )

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log response
            log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
            logger.log(
                log_level,
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            return response
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                },
            )
            raise


# =============================================================================
# Middleware Registration Helper
# =============================================================================


def register_middleware(app: ASGIApp) -> None:
    """
    Register all middleware in the correct order.
    Order matters: middleware added last is executed first.

    Execution order (outside-in):
    1. RequestIDMiddleware - Generate/capture request ID first
    2. RequestLoggingMiddleware - Log with request ID
    3. SecurityHeadersMiddleware - Add security headers
    4. RateLimitMiddleware - Check rate limits
    5. (CORS is handled separately by FastAPI)
    """
    # Add in reverse order (last added = first executed)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
