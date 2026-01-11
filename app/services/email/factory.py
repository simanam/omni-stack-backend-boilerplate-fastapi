"""
Email service factory.
Returns the appropriate email provider based on configuration.
"""

from functools import lru_cache

from app.core.config import settings
from app.services.email.base import BaseEmailService


@lru_cache(maxsize=1)
def get_email_service() -> BaseEmailService:
    """
    Factory that returns configured email service.

    Provider is selected based on EMAIL_PROVIDER setting:
    - "resend": Resend API (requires RESEND_API_KEY)
    - "sendgrid": SendGrid API (requires SENDGRID_API_KEY)
    - "console": Console output (default for development)
    """
    if settings.EMAIL_PROVIDER == "resend":
        from app.services.email.resend_provider import ResendEmailService

        return ResendEmailService()

    elif settings.EMAIL_PROVIDER == "sendgrid":
        from app.services.email.sendgrid_provider import SendGridEmailService

        return SendGridEmailService()

    else:
        from app.services.email.console_provider import ConsoleEmailService

        return ConsoleEmailService()


def clear_email_service_cache() -> None:
    """Clear the cached email service instance (useful for testing)."""
    get_email_service.cache_clear()
