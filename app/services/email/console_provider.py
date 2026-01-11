"""
Console email service for development.
Prints emails to console instead of sending.
"""

import logging
import uuid
from typing import Any

from app.core.config import settings
from app.services.email.base import BaseEmailService, EmailResult
from app.services.email.renderer import render_template, render_text_fallback

logger = logging.getLogger(__name__)


class ConsoleEmailService(BaseEmailService):
    """Development email service that prints to console."""

    async def send(
        self,
        to: str | list[str],
        subject: str,
        template: str,
        data: dict[str, Any],
        from_email: str | None = None,
        from_name: str | None = None,
    ) -> EmailResult:
        """Send a templated email (prints to console)."""
        try:
            html_content = render_template(template, {"subject": subject, **data})
            text_content = render_text_fallback(html_content)
            return await self.send_raw(
                to=to,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                from_email=from_email,
                from_name=from_name,
            )
        except Exception as e:
            logger.exception("Failed to render email template: %s", template)
            return EmailResult(success=False, error=str(e))

    async def send_raw(
        self,
        to: str | list[str],
        subject: str,
        html_content: str,  # noqa: ARG002
        text_content: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
    ) -> EmailResult:
        """Send a raw HTML email (prints to console)."""
        sender_email = from_email or settings.EMAIL_FROM_ADDRESS
        sender_name = from_name or settings.EMAIL_FROM_NAME
        recipients = self._normalize_recipients(to)
        message_id = f"console-{uuid.uuid4().hex[:12]}"

        separator = "=" * 60
        print(f"\n{separator}")
        print("[CONSOLE EMAIL]")
        print(separator)
        print(f"Message ID: {message_id}")
        print(f"From: {sender_name} <{sender_email}>")
        print(f"To: {', '.join(recipients)}")
        print(f"Subject: {subject}")
        print(separator)
        if text_content:
            print("Content (text):")
            print(text_content[:500])
            if len(text_content) > 500:
                print(f"... ({len(text_content)} chars total)")
        print(separator)
        print()

        logger.info(
            "[CONSOLE EMAIL] To: %s, Subject: %s, Template rendered successfully",
            recipients,
            subject,
        )

        return EmailResult(success=True, message_id=message_id)

    async def send_bulk(
        self,
        recipients: list[dict[str, Any]],
        subject: str,
        template: str,
        common_data: dict[str, Any] | None = None,
    ) -> list[EmailResult]:
        """Send bulk templated emails (prints to console)."""
        results: list[EmailResult] = []
        common = common_data or {}

        print(f"\n[CONSOLE EMAIL BULK] Sending {len(recipients)} emails...")

        for recipient in recipients:
            email = recipient.get("email")
            if not email:
                results.append(EmailResult(success=False, error="Missing email"))
                continue

            data = {**common, **{k: v for k, v in recipient.items() if k != "email"}}
            result = await self.send(
                to=email,
                subject=subject,
                template=template,
                data=data,
            )
            results.append(result)

        successful = sum(1 for r in results if r.success)
        print(f"[CONSOLE EMAIL BULK] Sent {successful}/{len(recipients)} emails\n")

        return results
