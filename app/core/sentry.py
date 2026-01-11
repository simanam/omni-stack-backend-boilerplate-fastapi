"""
Sentry integration for error tracking and performance monitoring.
"""

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """
    Initialize Sentry SDK for error tracking and performance monitoring.
    Only initializes if SENTRY_DSN is configured.
    """
    if not settings.SENTRY_DSN:
        logger.debug("Sentry DSN not configured, skipping initialization")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.asyncio import AsyncioIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            profiles_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            send_default_pii=False,  # Don't send PII by default
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                RedisIntegration(),
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR,
                ),
                AsyncioIntegration(),
            ],
            # Filter out health check endpoints from traces
            traces_sampler=_traces_sampler,
            # Custom before_send hook
            before_send=_before_send,
            before_send_transaction=_before_send_transaction,
        )

        logger.info(
            f"Sentry initialized for environment: {settings.ENVIRONMENT}"
        )
    except ImportError:
        logger.warning(
            "sentry-sdk not installed. Run: pip install sentry-sdk[fastapi]"
        )
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def _traces_sampler(sampling_context: dict[str, Any]) -> float:
    """
    Custom traces sampler to filter out noisy endpoints.
    """
    # Get transaction name
    transaction_context = sampling_context.get("transaction_context", {})
    name = transaction_context.get("name", "")

    # Don't trace health check endpoints
    if "/health" in name or "/metrics" in name:
        return 0.0

    # Use configured sample rate for everything else
    return settings.SENTRY_TRACES_SAMPLE_RATE


def _before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """
    Filter and modify events before sending to Sentry.
    """
    # Filter out specific exceptions if needed
    if "exc_info" in hint:
        exc_type, exc_value, _ = hint["exc_info"]
        # Example: Don't report 404 errors
        # if isinstance(exc_value, NotFoundError):
        #     return None

    # Scrub sensitive data from headers
    if "request" in event:
        request = event["request"]
        if "headers" in request:
            headers = request["headers"]
            # Remove sensitive headers
            sensitive_headers = ["authorization", "cookie", "x-api-key"]
            for header in sensitive_headers:
                if header in headers:
                    headers[header] = "[Filtered]"

    return event


def _before_send_transaction(
    event: dict[str, Any], hint: dict[str, Any]
) -> dict[str, Any] | None:
    """
    Filter transactions before sending.
    """
    # Get transaction name
    transaction = event.get("transaction", "")

    # Filter out noisy transactions
    if "/health" in transaction or "/metrics" in transaction:
        return None

    return event


def set_user_context(user_id: str, email: str | None = None) -> None:
    """
    Set user context for Sentry error tracking.
    Call this after user authentication.
    """
    if not settings.SENTRY_DSN:
        return

    try:
        import sentry_sdk

        sentry_sdk.set_user(
            {
                "id": user_id,
                "email": email if email else "[redacted]",
            }
        )
    except ImportError:
        pass


def capture_exception(exception: Exception, **kwargs: Any) -> str | None:
    """
    Manually capture an exception to Sentry.
    Returns the event ID if captured.
    """
    if not settings.SENTRY_DSN:
        return None

    try:
        import sentry_sdk

        return sentry_sdk.capture_exception(exception, **kwargs)
    except ImportError:
        return None


def capture_message(message: str, level: str = "info", **kwargs: Any) -> str | None:
    """
    Capture a message to Sentry.
    Returns the event ID if captured.
    """
    if not settings.SENTRY_DSN:
        return None

    try:
        import sentry_sdk

        return sentry_sdk.capture_message(message, level=level, **kwargs)
    except ImportError:
        return None


def add_breadcrumb(
    message: str,
    category: str = "custom",
    level: str = "info",
    data: dict[str, Any] | None = None,
) -> None:
    """
    Add a breadcrumb for debugging context.
    """
    if not settings.SENTRY_DSN:
        return

    try:
        import sentry_sdk

        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {},
        )
    except ImportError:
        pass


def set_tag(key: str, value: str) -> None:
    """
    Set a custom tag on the current scope.
    """
    if not settings.SENTRY_DSN:
        return

    try:
        import sentry_sdk

        sentry_sdk.set_tag(key, value)
    except ImportError:
        pass


def set_context(name: str, data: dict[str, Any]) -> None:
    """
    Set custom context data on the current scope.
    """
    if not settings.SENTRY_DSN:
        return

    try:
        import sentry_sdk

        sentry_sdk.set_context(name, data)
    except ImportError:
        pass
