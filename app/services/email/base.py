"""
Abstract email service interface.
All email providers must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class EmailResult:
    """Result of an email send operation."""

    success: bool
    message_id: str | None = None
    error: str | None = None


class BaseEmailService(ABC):
    """Abstract base class for email services."""

    @abstractmethod
    async def send(
        self,
        to: str | list[str],
        subject: str,
        template: str,
        data: dict[str, Any],
        from_email: str | None = None,
        from_name: str | None = None,
    ) -> EmailResult:
        """
        Send a templated email.

        Args:
            to: Recipient email address(es)
            subject: Email subject line
            template: Template name (e.g., "welcome", "password_reset")
            data: Template variables
            from_email: Override default sender email
            from_name: Override default sender name

        Returns:
            EmailResult with success status and message ID or error
        """
        pass

    @abstractmethod
    async def send_raw(
        self,
        to: str | list[str],
        subject: str,
        html_content: str,
        text_content: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
    ) -> EmailResult:
        """
        Send a raw HTML email.

        Args:
            to: Recipient email address(es)
            subject: Email subject line
            html_content: HTML body content
            text_content: Optional plain text fallback
            from_email: Override default sender email
            from_name: Override default sender name

        Returns:
            EmailResult with success status and message ID or error
        """
        pass

    @abstractmethod
    async def send_bulk(
        self,
        recipients: list[dict[str, Any]],
        subject: str,
        template: str,
        common_data: dict[str, Any] | None = None,
    ) -> list[EmailResult]:
        """
        Send bulk templated emails.

        Args:
            recipients: List of dicts with "email" and optional per-recipient data
            subject: Email subject line
            template: Template name
            common_data: Data shared across all recipients

        Returns:
            List of EmailResult for each recipient
        """
        pass

    def _normalize_recipients(self, to: str | list[str]) -> list[str]:
        """Convert single recipient to list."""
        if isinstance(to, str):
            return [to]
        return to
