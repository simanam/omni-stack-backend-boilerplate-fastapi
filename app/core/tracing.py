"""
OpenTelemetry distributed tracing integration.

Provides automatic instrumentation for:
- HTTP requests (FastAPI/Starlette)
- Database queries (SQLAlchemy)
- Redis operations
- External HTTP calls (httpx)
- Background jobs (ARQ)

Supports multiple exporters:
- OTLP (OpenTelemetry Protocol) - Jaeger, Tempo, etc.
- Console (for development)
- Zipkin
"""

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# Context variable for trace ID (accessible throughout the request lifecycle)
trace_id_ctx: ContextVar[str | None] = ContextVar("trace_id", default=None)
span_id_ctx: ContextVar[str | None] = ContextVar("span_id", default=None)

# Track if tracing is initialized
_tracer_provider = None
_tracer = None

# Try to import OpenTelemetry, provide fallbacks if not installed
try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.propagators.b3 import B3MultiFormat
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.trace import Status, StatusCode, get_current_span
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None  # type: ignore
    TracerProvider = None  # type: ignore
    Resource = None  # type: ignore
    BatchSpanProcessor = None  # type: ignore
    ConsoleSpanExporter = None  # type: ignore
    OTLPSpanExporter = None  # type: ignore
    FastAPIInstrumentor = None  # type: ignore
    SQLAlchemyInstrumentor = None  # type: ignore
    RedisInstrumentor = None  # type: ignore
    HTTPXClientInstrumentor = None  # type: ignore
    TraceContextTextMapPropagator = None  # type: ignore
    B3MultiFormat = None  # type: ignore
    set_global_textmap = None  # type: ignore
    get_current_span = None  # type: ignore
    Status = None  # type: ignore
    StatusCode = None  # type: ignore


def init_tracing() -> None:
    """
    Initialize OpenTelemetry tracing.

    Configuration via environment variables:
    - OTEL_ENABLED: Enable/disable tracing (default: False)
    - OTEL_SERVICE_NAME: Service name in traces (default: PROJECT_NAME)
    - OTEL_EXPORTER: Exporter type (otlp, console, zipkin)
    - OTEL_EXPORTER_OTLP_ENDPOINT: OTLP collector endpoint
    - OTEL_TRACES_SAMPLER_ARG: Sampling rate (0.0 to 1.0)
    """
    global _tracer_provider, _tracer

    if not OTEL_AVAILABLE:
        logger.debug(
            "OpenTelemetry not installed. Run: pip install opentelemetry-api "
            "opentelemetry-sdk opentelemetry-instrumentation-fastapi "
            "opentelemetry-instrumentation-sqlalchemy opentelemetry-instrumentation-redis "
            "opentelemetry-instrumentation-httpx opentelemetry-exporter-otlp"
        )
        return

    if not settings.OTEL_ENABLED:
        logger.debug("OpenTelemetry disabled (OTEL_ENABLED=False)")
        return

    if _tracer_provider is not None:
        logger.debug("OpenTelemetry already initialized")
        return

    try:
        # Create resource with service information
        resource = Resource.create(
            {
                "service.name": settings.OTEL_SERVICE_NAME or settings.PROJECT_NAME,
                "service.version": "1.0.0",
                "deployment.environment": settings.ENVIRONMENT,
            }
        )

        # Create tracer provider
        _tracer_provider = TracerProvider(resource=resource)

        # Configure exporter based on settings
        exporter = _get_exporter()
        if exporter:
            processor = BatchSpanProcessor(exporter)
            _tracer_provider.add_span_processor(processor)

        # Set as global tracer provider
        trace.set_tracer_provider(_tracer_provider)

        # Set up context propagation (W3C Trace Context is default)
        propagator = TraceContextTextMapPropagator()
        set_global_textmap(propagator)

        # Get tracer instance
        _tracer = trace.get_tracer(
            settings.OTEL_SERVICE_NAME or settings.PROJECT_NAME,
            "1.0.0",
        )

        logger.info(
            f"OpenTelemetry initialized: exporter={settings.OTEL_EXPORTER}, "
            f"endpoint={settings.OTEL_EXPORTER_OTLP_ENDPOINT or 'N/A'}"
        )

    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {e}")
        _tracer_provider = None
        _tracer = None


def _get_exporter():
    """Get the configured span exporter."""
    exporter_type = settings.OTEL_EXPORTER.lower()

    if exporter_type == "otlp":
        if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
            logger.warning("OTLP exporter selected but OTEL_EXPORTER_OTLP_ENDPOINT not set")
            return None
        return OTLPSpanExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=not settings.OTEL_EXPORTER_OTLP_ENDPOINT.startswith("https"),
        )

    elif exporter_type == "console":
        return ConsoleSpanExporter()

    elif exporter_type == "zipkin":
        try:
            from opentelemetry.exporter.zipkin.json import ZipkinExporter

            return ZipkinExporter(
                endpoint=settings.OTEL_EXPORTER_ZIPKIN_ENDPOINT
                or "http://localhost:9411/api/v2/spans"
            )
        except ImportError:
            logger.warning(
                "Zipkin exporter not installed. Run: pip install opentelemetry-exporter-zipkin"
            )
            return None

    elif exporter_type == "none":
        return None

    else:
        logger.warning(f"Unknown exporter type: {exporter_type}, using console")
        return ConsoleSpanExporter()


def instrument_app(app) -> None:
    """
    Instrument a FastAPI application with OpenTelemetry.

    Call this after creating the FastAPI app:
        app = FastAPI()
        instrument_app(app)
    """
    if not OTEL_AVAILABLE or not settings.OTEL_ENABLED:
        return

    try:
        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls=",".join(
                [
                    "/health",
                    "/api/v1/public/health",
                    "/api/v1/public/health/ready",
                    "/api/v2/public/health",
                    "/api/v2/public/health/ready",
                    "/api/v1/public/metrics",
                    "/docs",
                    "/redoc",
                    "/openapi.json",
                ]
            ),
        )
        logger.debug("FastAPI instrumented with OpenTelemetry")
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI: {e}")


def instrument_sqlalchemy(engine) -> None:
    """
    Instrument SQLAlchemy engine with OpenTelemetry.

    Call this after creating the database engine:
        engine = create_async_engine(...)
        instrument_sqlalchemy(engine.sync_engine)
    """
    if not OTEL_AVAILABLE or not settings.OTEL_ENABLED:
        return

    try:
        SQLAlchemyInstrumentor().instrument(
            engine=engine,
            enable_commenter=True,  # Add SQL comments with trace info
        )
        logger.debug("SQLAlchemy instrumented with OpenTelemetry")
    except Exception as e:
        logger.warning(f"Failed to instrument SQLAlchemy: {e}")


def instrument_redis() -> None:
    """
    Instrument Redis client with OpenTelemetry.

    Call this before creating Redis connections.
    """
    if not OTEL_AVAILABLE or not settings.OTEL_ENABLED:
        return

    try:
        RedisInstrumentor().instrument()
        logger.debug("Redis instrumented with OpenTelemetry")
    except Exception as e:
        logger.warning(f"Failed to instrument Redis: {e}")


def instrument_httpx() -> None:
    """
    Instrument httpx client with OpenTelemetry.

    Call this before making HTTP requests.
    """
    if not OTEL_AVAILABLE or not settings.OTEL_ENABLED:
        return

    try:
        HTTPXClientInstrumentor().instrument()
        logger.debug("httpx instrumented with OpenTelemetry")
    except Exception as e:
        logger.warning(f"Failed to instrument httpx: {e}")


def get_tracer(name: str | None = None):
    """
    Get an OpenTelemetry tracer instance.

    Args:
        name: Tracer name (defaults to service name)

    Returns:
        Tracer instance or NoOpTracer if not available
    """
    if not OTEL_AVAILABLE or _tracer is None:
        return _NoOpTracer()

    if name:
        return trace.get_tracer(name)
    return _tracer


def get_current_trace_id() -> str | None:
    """Get the current trace ID from the active span."""
    if not OTEL_AVAILABLE:
        return trace_id_ctx.get()

    span = get_current_span()
    if span and span.is_recording():
        return format(span.get_span_context().trace_id, "032x")
    return trace_id_ctx.get()


def get_current_span_id() -> str | None:
    """Get the current span ID from the active span."""
    if not OTEL_AVAILABLE:
        return span_id_ctx.get()

    span = get_current_span()
    if span and span.is_recording():
        return format(span.get_span_context().span_id, "016x")
    return span_id_ctx.get()


def set_span_attribute(key: str, value: Any) -> None:
    """Set an attribute on the current span."""
    if not OTEL_AVAILABLE:
        return

    span = get_current_span()
    if span and span.is_recording():
        span.set_attribute(key, value)


def set_span_status(status_code: str, description: str | None = None) -> None:
    """
    Set the status of the current span.

    Args:
        status_code: "OK", "ERROR", or "UNSET"
        description: Optional status description
    """
    if not OTEL_AVAILABLE:
        return

    span = get_current_span()
    if span and span.is_recording():
        code_map = {
            "OK": StatusCode.OK,
            "ERROR": StatusCode.ERROR,
            "UNSET": StatusCode.UNSET,
        }
        code = code_map.get(status_code.upper(), StatusCode.UNSET)
        span.set_status(Status(code, description))


def record_exception(exception: Exception) -> None:
    """Record an exception on the current span."""
    if not OTEL_AVAILABLE:
        return

    span = get_current_span()
    if span and span.is_recording():
        span.record_exception(exception)
        span.set_status(Status(StatusCode.ERROR, str(exception)))


@contextmanager
def create_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    kind: str = "internal",
):
    """
    Create a new span as a context manager.

    Args:
        name: Span name
        attributes: Initial span attributes
        kind: Span kind (internal, server, client, producer, consumer)

    Usage:
        with create_span("process_order", {"order_id": "123"}):
            # do work
    """
    if not OTEL_AVAILABLE or _tracer is None:
        yield
        return

    from opentelemetry.trace import SpanKind

    kind_map = {
        "internal": SpanKind.INTERNAL,
        "server": SpanKind.SERVER,
        "client": SpanKind.CLIENT,
        "producer": SpanKind.PRODUCER,
        "consumer": SpanKind.CONSUMER,
    }
    span_kind = kind_map.get(kind.lower(), SpanKind.INTERNAL)

    with _tracer.start_as_current_span(
        name,
        kind=span_kind,
        attributes=attributes or {},
    ) as span:
        # Store trace/span IDs in context for logging
        token_trace = trace_id_ctx.set(format(span.get_span_context().trace_id, "032x"))
        token_span = span_id_ctx.set(format(span.get_span_context().span_id, "016x"))
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
        finally:
            trace_id_ctx.reset(token_trace)
            span_id_ctx.reset(token_span)


def trace_function(
    name: str | None = None,
    attributes: dict[str, Any] | None = None,
    kind: str = "internal",
):
    """
    Decorator to trace a function.

    Args:
        name: Span name (defaults to function name)
        attributes: Initial span attributes
        kind: Span kind

    Usage:
        @trace_function()
        async def process_order(order_id: str):
            ...

        @trace_function("custom_name", {"component": "orders"})
        def sync_function():
            ...
    """
    import asyncio
    from functools import wraps

    def decorator(func):
        span_name = name or func.__name__

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with create_span(span_name, attributes, kind):
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with create_span(span_name, attributes, kind):
                return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class _NoOpTracer:
    """No-op tracer for when OpenTelemetry is not available."""

    def start_span(self, _name: str, **_kwargs):
        return _NoOpSpan()

    def start_as_current_span(self, _name: str, **_kwargs):
        return _NoOpSpanContext()


class _NoOpSpan:
    """No-op span for when OpenTelemetry is not available."""

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_status(self, status: Any) -> None:
        pass

    def record_exception(self, exception: Exception) -> None:
        pass

    def add_event(self, name: str, attributes: dict | None = None) -> None:
        pass

    def end(self) -> None:
        pass

    def is_recording(self) -> bool:
        return False


class _NoOpSpanContext:
    """No-op span context manager for when OpenTelemetry is not available."""

    def __enter__(self):
        return _NoOpSpan()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


def shutdown_tracing() -> None:
    """Shutdown the tracer provider and flush any pending spans."""
    global _tracer_provider, _tracer

    if _tracer_provider is not None:
        try:
            _tracer_provider.shutdown()
            logger.info("OpenTelemetry tracing shutdown complete")
        except Exception as e:
            logger.warning(f"Error during tracing shutdown: {e}")
        finally:
            _tracer_provider = None
            _tracer = None
