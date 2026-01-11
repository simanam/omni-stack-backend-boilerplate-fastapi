"""
Prometheus metrics for application monitoring.
Provides request, database, and business metrics.
"""

import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from functools import wraps
from typing import Any

from app.core.config import settings

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
