"""
Structured logging configuration for production environments.
Provides JSON-formatted logs with request context and service metadata.
Includes OpenTelemetry trace correlation.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings

# Context variables for request-scoped data
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    Outputs logs in JSON format suitable for log aggregators like
    Datadog, Elasticsearch, CloudWatch, etc.
    """

    def __init__(
        self,
        service_name: str | None = None,
        environment: str | None = None,
        version: str | None = None,
    ):
        super().__init__()
        self.service_name = service_name or settings.PROJECT_NAME
        self.environment = environment or settings.ENVIRONMENT
        self.version = version or "1.0.0"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log structure
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "environment": self.environment,
            "version": self.version,
        }

        # Add location info
        log_data["source"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Add request context if available
        request_id = request_id_ctx.get()
        if request_id:
            log_data["request_id"] = request_id

        user_id = user_id_ctx.get()
        if user_id:
            log_data["user_id"] = user_id

        # Add OpenTelemetry trace context if available
        trace_id, span_id = self._get_trace_context()
        if trace_id:
            log_data["trace_id"] = trace_id
        if span_id:
            log_data["span_id"] = span_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add any extra fields passed to the logger
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        return json.dumps(log_data, default=str)

    def _get_trace_context(self) -> tuple[str | None, str | None]:
        """Get current trace and span IDs from OpenTelemetry context."""
        try:
            from app.core.tracing import get_current_span_id, get_current_trace_id

            return get_current_trace_id(), get_current_span_id()
        except ImportError:
            return None, None


class DevelopmentFormatter(logging.Formatter):
    """
    Human-readable formatter for development environments.
    Includes colors and is easier to read in terminal.
    """

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET

        # Get request context
        request_id = request_id_ctx.get()
        user_id = user_id_ctx.get()

        # Get trace context
        trace_id, span_id = self._get_trace_context()

        # Build prefix with context
        prefix_parts = []
        if request_id:
            prefix_parts.append(f"[{request_id[:8]}]")
        if trace_id:
            prefix_parts.append(f"[trace:{trace_id[:8]}]")
        if user_id:
            prefix_parts.append(f"[user:{user_id[:8]}]")
        prefix = " ".join(prefix_parts)

        # Format timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build message
        message = f"{timestamp} {color}{record.levelname:8}{reset} {prefix} {record.name}: {record.getMessage()}"

        # Add exception if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"

        return message

    def _get_trace_context(self) -> tuple[str | None, str | None]:
        """Get current trace and span IDs from OpenTelemetry context."""
        try:
            from app.core.tracing import get_current_span_id, get_current_trace_id

            return get_current_trace_id(), get_current_span_id()
        except ImportError:
            return None, None


def setup_logging(
    level: str | None = None,
    json_format: bool | None = None,
) -> None:
    """
    Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to settings.LOG_LEVEL.
        json_format: Use JSON format. Defaults to True in production.
    """
    log_level = level or settings.LOG_LEVEL
    use_json = json_format if json_format is not None else (settings.ENVIRONMENT == "production")

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # Set formatter based on environment
    formatter = JSONFormatter() if use_json else DevelopmentFormatter()

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Configure specific loggers
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: level={log_level}, format={'json' if use_json else 'text'}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Usage:
        logger = get_logger(__name__)
        logger.info("Processing request")
    """
    return logging.getLogger(name)


class LogContext:
    """
    Context manager for adding contextual data to logs.

    Usage:
        with LogContext(request_id="abc123", user_id="user456"):
            logger.info("Processing")  # Will include request_id and user_id
    """

    def __init__(
        self,
        request_id: str | None = None,
        user_id: str | None = None,
    ):
        self.request_id = request_id
        self.user_id = user_id
        self._request_id_token = None
        self._user_id_token = None

    def __enter__(self) -> "LogContext":
        if self.request_id:
            self._request_id_token = request_id_ctx.set(self.request_id)
        if self.user_id:
            self._user_id_token = user_id_ctx.set(self.user_id)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._request_id_token is not None:
            request_id_ctx.reset(self._request_id_token)
        if self._user_id_token is not None:
            user_id_ctx.reset(self._user_id_token)


def set_request_context(request_id: str | None = None, user_id: str | None = None) -> None:
    """
    Set request context for logging.
    Call this at the beginning of request handling.
    """
    if request_id:
        request_id_ctx.set(request_id)
    if user_id:
        user_id_ctx.set(user_id)


def clear_request_context() -> None:
    """
    Clear request context.
    Call this at the end of request handling.
    """
    request_id_ctx.set(None)
    user_id_ctx.set(None)


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **extra: Any,
) -> None:
    """
    Log a message with extra context data.

    Usage:
        log_with_context(logger, logging.INFO, "User created", user_email="test@example.com")
    """
    # Create a LogRecord with extra data
    record = logger.makeRecord(
        logger.name,
        level,
        "",
        0,
        message,
        (),
        None,
    )
    record.extra_data = extra
    logger.handle(record)


# Convenience functions for logging with extra context
def info(logger: logging.Logger, message: str, **extra: Any) -> None:
    """Log INFO message with extra context."""
    log_with_context(logger, logging.INFO, message, **extra)


def warning(logger: logging.Logger, message: str, **extra: Any) -> None:
    """Log WARNING message with extra context."""
    log_with_context(logger, logging.WARNING, message, **extra)


def error(logger: logging.Logger, message: str, **extra: Any) -> None:
    """Log ERROR message with extra context."""
    log_with_context(logger, logging.ERROR, message, **extra)


def debug(logger: logging.Logger, message: str, **extra: Any) -> None:
    """Log DEBUG message with extra context."""
    log_with_context(logger, logging.DEBUG, message, **extra)
