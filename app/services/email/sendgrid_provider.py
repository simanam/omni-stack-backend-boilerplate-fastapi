"""
SendGrid email service implementation.
https://docs.sendgrid.com/api-reference
"""

import logging
from typing import Any

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Content, Mail

from app.core.config import settings
from app.services.email.base import BaseEmailService, EmailResult
from app.services.email.renderer import render_template, render_text_fallback

logger = logging.getLogger(__name__)


class SendGridEmailService(BaseEmailService):
    """SendGrid email service implementation."""

    def __init__(self) -> None:
        if not settings.SENDGRID_API_KEY:
            raise ValueError("SENDGRID_API_KEY is required for SendGrid email service")
        self._client = SendGridAPIClient(settings.SENDGRID_API_KEY)

    async def send(
        self,
        to: str | list[str],
        subject: str,
        template: str,
        data: dict[str, Any],
        from_email: str | None = None,
        from_name: str | None = None,
    ) -> EmailResult:
        """Send a templated email via SendGrid."""
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
        html_content: str,
        text_content: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
    ) -> EmailResult:
        """Send a raw HTML email via SendGrid."""
        try:
            sender_email = from_email or settings.EMAIL_FROM_ADDRESS
            sender_name = from_name or settings.EMAIL_FROM_NAME
            from_address = f"{sender_name} <{sender_email}>"

            recipients = self._normalize_recipients(to)

            message = Mail(
                from_email=from_address,
                to_emails=recipients,
                subject=subject,
            )
            message.content = [
                Content("text/plain", text_content or ""),
                Content("text/html", html_content),
            ]

            response = self._client.send(message)

            message_id = response.headers.get("X-Message-Id")
            logger.info(
                "Email sent via SendGrid: %s to %s (status: %s)",
                message_id,
                recipients,
                response.status_code,
            )

            if response.status_code not in (200, 201, 202):
                return EmailResult(
                    success=False,
                    error=f"SendGrid returned status {response.status_code}",
                )

            return EmailResult(success=True, message_id=message_id)

        except Exception as e:
            logger.exception("Failed to send email via SendGrid")
            return EmailResult(success=False, error=str(e))

    async def send_bulk(
        self,
        recipients: list[dict[str, Any]],
        subject: str,
        template: str,
        common_data: dict[str, Any] | None = None,
    ) -> list[EmailResult]:
        """Send bulk templated emails via SendGrid."""
        results: list[EmailResult] = []
        common = common_data or {}

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

        return results
