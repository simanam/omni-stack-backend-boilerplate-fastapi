"""
Email-related background jobs.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def send_welcome_email(
    ctx: dict[str, Any],
    user_email: str,
    user_name: str,
) -> None:
    """
    Send welcome email to new user.

    Args:
        ctx: ARQ context dict
        user_email: Recipient email address
        user_name: User's display name
    """
    logger.info(f"Sending welcome email to {user_email} ({user_name})")

    # TODO: Replace with actual email service when Phase 6 is complete
    # from app.services.email.factory import get_email_service
    # email_service = get_email_service()
    # await email_service.send(
    #     to=user_email,
    #     subject="Welcome to OmniStack!",
    #     template="welcome",
    #     data={"name": user_name}
    # )

    logger.info(f"Welcome email sent to {user_email}")


async def send_password_reset_email(
    ctx: dict[str, Any],
    user_email: str,
    reset_link: str,
) -> None:
    """
    Send password reset email.

    Args:
        ctx: ARQ context dict
        user_email: Recipient email address
        reset_link: Password reset URL
    """
    logger.info(f"Sending password reset email to {user_email}")

    # TODO: Replace with actual email service when Phase 6 is complete
    # from app.services.email.factory import get_email_service
    # email_service = get_email_service()
    # await email_service.send(
    #     to=user_email,
    #     subject="Reset Your Password",
    #     template="password_reset",
    #     data={"reset_link": reset_link}
    # )

    logger.info(f"Password reset email sent to {user_email}")


async def send_notification_email(
    ctx: dict[str, Any],
    user_email: str,
    subject: str,
    body: str,
    template: str | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    """
    Send a notification email.

    Args:
        ctx: ARQ context dict
        user_email: Recipient email address
        subject: Email subject
        body: Plain text body (used if no template)
        template: Optional template name
        data: Optional template data
    """
    logger.info(f"Sending notification email to {user_email}: {subject}")

    # TODO: Replace with actual email service when Phase 6 is complete
    # from app.services.email.factory import get_email_service
    # email_service = get_email_service()
    # if template:
    #     await email_service.send(
    #         to=user_email,
    #         subject=subject,
    #         template=template,
    #         data=data or {}
    #     )
    # else:
    #     await email_service.send_plain(
    #         to=user_email,
    #         subject=subject,
    #         body=body
    #     )

    logger.info(f"Notification email sent to {user_email}")
