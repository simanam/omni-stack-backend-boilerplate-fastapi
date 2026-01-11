"""
Email service package.
Provides pluggable email providers (Resend, SendGrid, Console).
"""

from app.services.email.base import BaseEmailService, EmailResult
from app.services.email.factory import get_email_service

__all__ = [
    "BaseEmailService",
    "EmailResult",
    "get_email_service",
]
