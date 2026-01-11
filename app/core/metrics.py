"""
Prometheus metrics for application monitoring.
Provides request, database, business, system, and authentication metrics.

Phase 12.5: Enhanced metrics with system monitoring, auth tracking, and middleware.
"""

import os
import platform
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from functools import wraps
from typing import Any

from app.core.config import settings

# Track application start time for uptime calculation
APP_START_TIME = datetime.now(UTC)

# Try to import prometheus_client, provide fallbacks if not installed
try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        REGISTRY,
        Counter,
        Gauge,
        Histogram,
        Info,
        generate_latest,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # Provide dummy implementations
    class DummyMetric:
        def labels(self, **_kwargs: Any) -> "DummyMetric":
            return self

        def inc(self, amount: float = 1) -> None:
            pass

        def dec(self, amount: float = 1) -> None:
            pass

        def set(self, value: float) -> None:
            pass

        def observe(self, value: float) -> None:
            pass

        def info(self, info: dict[str, str]) -> None:
            pass

    def Counter(*args: Any, **kwargs: Any) -> DummyMetric:  # noqa: N802
        return DummyMetric()

    def Gauge(*args: Any, **kwargs: Any) -> DummyMetric:  # noqa: N802
        return DummyMetric()

    def Histogram(*args: Any, **kwargs: Any) -> DummyMetric:  # noqa: N802
        return DummyMetric()

    def Info(*args: Any, **kwargs: Any) -> DummyMetric:  # noqa: N802
        return DummyMetric()

    def generate_latest(registry: Any = None) -> bytes:
        return b"# Prometheus client not installed\n"

    CONTENT_TYPE_LATEST = "text/plain; charset=utf-8"
    REGISTRY = None


# =============================================================================
# Application Info
# =============================================================================

APP_INFO = Info(
    "app",
    "Application information",
)

# Initialize app info
if PROMETHEUS_AVAILABLE:
    APP_INFO.info(
        {
            "name": settings.PROJECT_NAME,
            "environment": settings.ENVIRONMENT,
        }
    )


# =============================================================================
# Request Metrics
# =============================================================================

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

REQUEST_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"],
)


# =============================================================================
# Database Metrics
# =============================================================================

DB_QUERY_COUNT = Counter(
    "db_queries_total",
    "Total database queries",
    ["operation", "table"],
)

DB_QUERY_LATENCY = Histogram(
    "db_query_duration_seconds",
    "Database query latency in seconds",
    ["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

DB_POOL_SIZE = Gauge(
    "db_pool_connections",
    "Database connection pool size",
    ["state"],  # idle, active, overflow
)

DB_ERRORS = Counter(
    "db_errors_total",
    "Total database errors",
    ["error_type"],
)


# =============================================================================
# Redis/Cache Metrics
# =============================================================================

CACHE_HITS = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_type"],
)

CACHE_MISSES = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_type"],
)

REDIS_CONNECTIONS = Gauge(
    "redis_connections",
    "Number of Redis connections",
)


# =============================================================================
# Background Job Metrics
# =============================================================================

JOB_COUNT = Counter(
    "background_jobs_total",
    "Total background jobs",
    ["job_name", "status"],  # status: enqueued, started, completed, failed
)

JOB_DURATION = Histogram(
    "background_job_duration_seconds",
    "Background job execution time in seconds",
    ["job_name"],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0),
)

JOB_QUEUE_SIZE = Gauge(
    "background_job_queue_size",
    "Number of jobs in queue",
    ["queue_name"],
)


# =============================================================================
# Business Metrics
# =============================================================================

USERS_TOTAL = Gauge(
    "users_total",
    "Total number of users",
    ["status"],  # active, inactive
)

ACTIVE_SUBSCRIPTIONS = Gauge(
    "active_subscriptions_total",
    "Number of active subscriptions",
    ["plan"],
)

API_KEY_USAGE = Counter(
    "api_key_usage_total",
    "API key usage count",
    ["key_id", "endpoint"],
)


# =============================================================================
# AI/LLM Metrics
# =============================================================================

LLM_REQUESTS = Counter(
    "llm_requests_total",
    "Total LLM API requests",
    ["provider", "model", "status"],
)

LLM_TOKENS = Counter(
    "llm_tokens_total",
    "Total LLM tokens used",
    ["provider", "model", "type"],  # type: prompt, completion
)

LLM_LATENCY = Histogram(
    "llm_request_duration_seconds",
    "LLM API request latency in seconds",
    ["provider", "model"],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)


# =============================================================================
# External Service Metrics
# =============================================================================

EXTERNAL_SERVICE_REQUESTS = Counter(
    "external_service_requests_total",
    "Total external service requests",
    ["service", "operation", "status"],
)

EXTERNAL_SERVICE_LATENCY = Histogram(
    "external_service_duration_seconds",
    "External service request latency in seconds",
    ["service", "operation"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


# =============================================================================
# Helper Functions
# =============================================================================


def get_metrics() -> tuple[bytes, str]:
    """
    Generate Prometheus metrics output.
    Returns tuple of (metrics_bytes, content_type).
    """
    if PROMETHEUS_AVAILABLE:
        return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
    return b"# Prometheus client not installed\n", "text/plain"


@contextmanager
def track_request_metrics(
    method: str, endpoint: str
) -> Generator[None, None, None]:
    """
    Context manager to track request metrics.

    Usage:
        with track_request_metrics("GET", "/api/v1/users"):
            # handle request
    """
    REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
    start_time = time.perf_counter()

    try:
        yield
    finally:
        duration = time.perf_counter() - start_time
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)


def record_request(
    method: str, endpoint: str, status_code: int, duration: float
) -> None:
    """Record HTTP request metrics."""
    REQUEST_COUNT.labels(
        method=method, endpoint=endpoint, status_code=str(status_code)
    ).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)


@contextmanager
def track_db_query(operation: str, table: str) -> Generator[None, None, None]:
    """
    Context manager to track database query metrics.

    Usage:
        with track_db_query("SELECT", "users"):
            # execute query
    """
    start_time = time.perf_counter()
    try:
        yield
        DB_QUERY_COUNT.labels(operation=operation, table=table).inc()
    except Exception as e:
        DB_ERRORS.labels(error_type=type(e).__name__).inc()
        raise
    finally:
        duration = time.perf_counter() - start_time
        DB_QUERY_LATENCY.labels(operation=operation, table=table).observe(duration)


def record_cache_access(cache_type: str, hit: bool) -> None:
    """Record cache hit/miss."""
    if hit:
        CACHE_HITS.labels(cache_type=cache_type).inc()
    else:
        CACHE_MISSES.labels(cache_type=cache_type).inc()


def record_job_metric(job_name: str, status: str, duration: float | None = None) -> None:
    """Record background job metrics."""
    JOB_COUNT.labels(job_name=job_name, status=status).inc()
    if duration is not None and status in ("completed", "failed"):
        JOB_DURATION.labels(job_name=job_name).observe(duration)


def record_llm_usage(
    provider: str,
    model: str,
    status: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    duration: float | None = None,
) -> None:
    """Record LLM API usage metrics."""
    LLM_REQUESTS.labels(provider=provider, model=model, status=status).inc()

    if prompt_tokens:
        LLM_TOKENS.labels(provider=provider, model=model, type="prompt").inc(
            prompt_tokens
        )
    if completion_tokens:
        LLM_TOKENS.labels(provider=provider, model=model, type="completion").inc(
            completion_tokens
        )

    if duration is not None:
        LLM_LATENCY.labels(provider=provider, model=model).observe(duration)


def track_external_service(
    service: str, operation: str
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to track external service metrics.

    Usage:
        @track_external_service("stripe", "create_customer")
        async def create_customer(...):
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                EXTERNAL_SERVICE_REQUESTS.labels(
                    service=service, operation=operation, status="success"
                ).inc()
                return result
            except Exception:
                EXTERNAL_SERVICE_REQUESTS.labels(
                    service=service, operation=operation, status="error"
                ).inc()
                raise
            finally:
                duration = time.perf_counter() - start_time
                EXTERNAL_SERVICE_LATENCY.labels(
                    service=service, operation=operation
                ).observe(duration)

        return wrapper

    return decorator


def update_db_pool_metrics(idle: int, active: int, overflow: int = 0) -> None:
    """Update database connection pool metrics."""
    DB_POOL_SIZE.labels(state="idle").set(idle)
    DB_POOL_SIZE.labels(state="active").set(active)
    DB_POOL_SIZE.labels(state="overflow").set(overflow)


def update_business_metrics(
    active_users: int = 0,
    inactive_users: int = 0,
    subscriptions: dict[str, int] | None = None,
) -> None:
    """Update business metrics."""
    if active_users:
        USERS_TOTAL.labels(status="active").set(active_users)
    if inactive_users:
        USERS_TOTAL.labels(status="inactive").set(inactive_users)

    if subscriptions:
        for plan, count in subscriptions.items():
            ACTIVE_SUBSCRIPTIONS.labels(plan=plan).set(count)


# =============================================================================
# System Metrics (Phase 12.5)
# =============================================================================

PROCESS_MEMORY_BYTES = Gauge(
    "process_memory_bytes",
    "Process memory usage in bytes",
    ["type"],  # rss, vms, shared
)

PROCESS_CPU_SECONDS = Counter(
    "process_cpu_seconds_total",
    "Total CPU time consumed by the process",
    ["mode"],  # user, system
)

PROCESS_OPEN_FDS = Gauge(
    "process_open_fds",
    "Number of open file descriptors",
)

PROCESS_THREADS = Gauge(
    "process_threads",
    "Number of threads in the process",
)

SYSTEM_INFO = Info(
    "system",
    "System information",
)

APP_UPTIME_SECONDS = Gauge(
    "app_uptime_seconds",
    "Application uptime in seconds",
)


def update_system_metrics() -> None:
    """
    Update system and process metrics.
    Should be called periodically (e.g., every 15 seconds).
    """
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        import resource

        # Get resource usage
        usage = resource.getrusage(resource.RUSAGE_SELF)

        # CPU time
        PROCESS_CPU_SECONDS.labels(mode="user")._value.set(usage.ru_utime)
        PROCESS_CPU_SECONDS.labels(mode="system")._value.set(usage.ru_stime)

        # Memory (maxrss is in KB on Linux, bytes on macOS)
        rss_bytes = (
            usage.ru_maxrss
            if platform.system() == "Darwin"
            else usage.ru_maxrss * 1024
        )
        PROCESS_MEMORY_BYTES.labels(type="rss").set(rss_bytes)

    except ImportError:
        pass

    # Try to get more detailed memory info via /proc (Linux)
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    rss_kb = int(line.split()[1])
                    PROCESS_MEMORY_BYTES.labels(type="rss").set(rss_kb * 1024)
                elif line.startswith("VmSize:"):
                    vms_kb = int(line.split()[1])
                    PROCESS_MEMORY_BYTES.labels(type="vms").set(vms_kb * 1024)
                elif line.startswith("RssFile:"):
                    shared_kb = int(line.split()[1])
                    PROCESS_MEMORY_BYTES.labels(type="shared").set(shared_kb * 1024)
                elif line.startswith("Threads:"):
                    threads = int(line.split()[1])
                    PROCESS_THREADS.set(threads)
    except (FileNotFoundError, PermissionError):
        pass

    # File descriptors (Linux/macOS)
    try:
        fd_count = len(os.listdir("/proc/self/fd"))
        PROCESS_OPEN_FDS.set(fd_count)
    except (FileNotFoundError, PermissionError):
        pass

    # Application uptime
    uptime = (datetime.now(UTC) - APP_START_TIME).total_seconds()
    APP_UPTIME_SECONDS.set(uptime)


def init_system_info() -> None:
    """Initialize static system information."""
    if not PROMETHEUS_AVAILABLE:
        return

    SYSTEM_INFO.info(
        {
            "python_version": platform.python_version(),
            "platform": platform.system(),
            "platform_release": platform.release(),
            "processor": platform.processor() or "unknown",
        }
    )


# =============================================================================
# Authentication Metrics (Phase 12.5)
# =============================================================================

AUTH_EVENTS = Counter(
    "auth_events_total",
    "Total authentication events",
    ["event", "provider"],  # event: login, logout, signup, token_refresh, failed
)

AUTH_FAILURES = Counter(
    "auth_failures_total",
    "Total authentication failures",
    ["reason"],  # invalid_token, expired_token, invalid_credentials, rate_limited
)

ACTIVE_SESSIONS = Gauge(
    "active_sessions",
    "Number of active user sessions",
)

TOKEN_OPERATIONS = Counter(
    "token_operations_total",
    "Token operations count",
    ["operation"],  # issued, verified, revoked, expired
)


def record_auth_event(
    event: str,
    provider: str = "jwt",
) -> None:
    """
    Record an authentication event.

    Args:
        event: Event type (login, logout, signup, token_refresh, failed)
        provider: Auth provider (jwt, clerk, supabase, etc.)
    """
    AUTH_EVENTS.labels(event=event, provider=provider).inc()


def record_auth_failure(reason: str) -> None:
    """
    Record an authentication failure.

    Args:
        reason: Failure reason (invalid_token, expired_token, invalid_credentials, rate_limited)
    """
    AUTH_FAILURES.labels(reason=reason).inc()


def record_token_operation(operation: str) -> None:
    """
    Record a token operation.

    Args:
        operation: Operation type (issued, verified, revoked, expired)
    """
    TOKEN_OPERATIONS.labels(operation=operation).inc()


def update_active_sessions(count: int) -> None:
    """Update the active sessions count."""
    ACTIVE_SESSIONS.set(count)


# =============================================================================
# Rate Limiting Metrics (Phase 12.5)
# =============================================================================

RATE_LIMIT_HITS = Counter(
    "rate_limit_hits_total",
    "Total rate limit hits (requests blocked)",
    ["endpoint", "client_type"],  # client_type: ip, user, api_key
)

RATE_LIMIT_REMAINING = Gauge(
    "rate_limit_remaining",
    "Remaining requests in current window",
    ["endpoint"],
)


def record_rate_limit_hit(endpoint: str, client_type: str = "ip") -> None:
    """Record a rate limit hit (blocked request)."""
    RATE_LIMIT_HITS.labels(endpoint=endpoint, client_type=client_type).inc()


# =============================================================================
# WebSocket Metrics (Phase 12.5)
# =============================================================================

WEBSOCKET_CONNECTIONS = Gauge(
    "websocket_connections",
    "Number of active WebSocket connections",
    ["status"],  # connected, authenticated
)

WEBSOCKET_MESSAGES = Counter(
    "websocket_messages_total",
    "Total WebSocket messages",
    ["direction", "type"],  # direction: sent, received; type: message, ping, pong
)


def record_websocket_connect() -> None:
    """Record a new WebSocket connection."""
    WEBSOCKET_CONNECTIONS.labels(status="connected").inc()


def record_websocket_disconnect() -> None:
    """Record a WebSocket disconnection."""
    WEBSOCKET_CONNECTIONS.labels(status="connected").dec()


def record_websocket_auth(authenticated: bool = True) -> None:
    """Record WebSocket authentication status."""
    if authenticated:
        WEBSOCKET_CONNECTIONS.labels(status="authenticated").inc()
    else:
        WEBSOCKET_CONNECTIONS.labels(status="authenticated").dec()


def record_websocket_message(direction: str, msg_type: str = "message") -> None:
    """Record a WebSocket message."""
    WEBSOCKET_MESSAGES.labels(direction=direction, type=msg_type).inc()


# =============================================================================
# Webhook Metrics (Phase 12.5)
# =============================================================================

WEBHOOK_EVENTS = Counter(
    "webhook_events_total",
    "Total webhook events received",
    ["provider", "event_type", "status"],  # status: processed, failed, duplicate
)

WEBHOOK_LATENCY = Histogram(
    "webhook_processing_duration_seconds",
    "Webhook processing latency",
    ["provider"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)


def record_webhook_event(
    provider: str,
    event_type: str,
    status: str,
    duration: float | None = None,
) -> None:
    """Record a webhook event."""
    WEBHOOK_EVENTS.labels(provider=provider, event_type=event_type, status=status).inc()
    if duration is not None:
        WEBHOOK_LATENCY.labels(provider=provider).observe(duration)


# =============================================================================
# Metrics Middleware (Phase 12.5)
# =============================================================================


class MetricsMiddleware:
    """
    ASGI middleware to automatically collect HTTP request metrics.

    Usage:
        from app.core.metrics import MetricsMiddleware
        app.add_middleware(MetricsMiddleware)
    """

    # Paths to skip metrics collection
    SKIP_PATHS: set[str] = {
        "/health",
        "/api/v1/public/health",
        "/api/v1/public/health/ready",
        "/api/v1/public/metrics",
        "/api/v2/public/health",
        "/api/v2/public/health/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    }

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Skip metrics for certain paths
        if path in self.SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "UNKNOWN")

        # Normalize endpoint for metrics (remove UUIDs, IDs)
        endpoint = self._normalize_path(path)

        # Track request
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
        start_time = time.perf_counter()

        status_code = 500  # Default to error if we don't get a response

        async def send_wrapper(message: dict) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - start_time
            REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
            REQUEST_COUNT.labels(
                method=method, endpoint=endpoint, status_code=str(status_code)
            ).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)

    def _normalize_path(self, path: str) -> str:
        """
        Normalize path for metrics by replacing dynamic segments.
        Examples:
            /api/v1/users/123e4567-e89b-12d3-a456-426614174000 -> /api/v1/users/{id}
            /api/v1/projects/42 -> /api/v1/projects/{id}
        """
        import re

        # Replace UUIDs
        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "/{id}",
            path,
            flags=re.IGNORECASE,
        )

        # Replace numeric IDs
        path = re.sub(r"/\d+", "/{id}", path)

        return path


# =============================================================================
# Metrics Collection Helper (Phase 12.5)
# =============================================================================


async def collect_metrics_snapshot() -> dict[str, Any]:
    """
    Collect a snapshot of key metrics for health checks or debugging.

    Returns:
        Dictionary with metric values.
    """
    # Update system metrics first
    update_system_metrics()

    uptime = (datetime.now(UTC) - APP_START_TIME).total_seconds()

    snapshot = {
        "uptime_seconds": uptime,
        "prometheus_available": PROMETHEUS_AVAILABLE,
        "environment": settings.ENVIRONMENT,
    }

    if PROMETHEUS_AVAILABLE:
        # Try to get some metric values
        try:
            from prometheus_client import REGISTRY

            # Count metrics
            metric_count = 0
            for _ in REGISTRY.collect():
                metric_count += 1
            snapshot["metric_families"] = metric_count
        except Exception:
            pass

    return snapshot


# =============================================================================
# Initialization (Phase 12.5)
# =============================================================================


def init_metrics() -> None:
    """
    Initialize all metrics.
    Call this during application startup.
    """
    # Initialize system info
    init_system_info()

    # Initial system metrics collection
    update_system_metrics()


# Initialize on import if prometheus is available
if PROMETHEUS_AVAILABLE:
    init_system_info()
