"""
Contact form endpoint for public submissions.
Includes rate limiting and honeypot spam protection.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, model_validator

from app.core.cache import get_redis
from app.core.config import settings
from app.core.middleware import RateLimitConfig, RateLimiter
from app.jobs import enqueue
from app.services.email import get_email_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contact", tags=["contact"])

# Rate limiter for contact form (stricter than general API)
contact_rate_limiter = RateLimiter()
CONTACT_RATE_LIMIT = RateLimitConfig(requests=5, window_seconds=3600)  # 5 per hour


# =============================================================================
# Schemas
# =============================================================================


class ContactFormRequest(BaseModel):
    """Contact form submission request."""

    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Sender's name",
    )
    email: EmailStr = Field(
        ...,
        description="Sender's email address",
    )
    subject: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Message subject",
    )
    message: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Message content",
    )
    # Honeypot field - should always be empty
    website: str | None = Field(
        default=None,
        max_length=200,
        description="Honeypot field - leave empty",
    )
    # Hidden timestamp field for timing-based detection
    form_timestamp: str | None = Field(
        default=None,
        description="Form load timestamp for bot detection",
    )

    @model_validator(mode="after")
    def check_honeypot(self) -> "ContactFormRequest":
        """Validate honeypot is empty (spam bots fill it in)."""
        if self.website:
            # Don't tell bots why it failed - just silently reject
            raise ValueError("Invalid form submission")
        return self


class ContactFormResponse(BaseModel):
    """Contact form submission response."""

    success: bool = True
    message: str = "Thank you for your message. We'll get back to you soon!"
    reference_id: str | None = None


class ContactMessage(BaseModel):
    """Internal representation of a contact message."""

    id: str
    name: str
    email: str
    subject: str
    message: str
    ip_address: str | None = None
    user_agent: str | None = None
    submitted_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Helpers
# =============================================================================


def _generate_reference_id() -> str:
    """Generate a unique reference ID for the contact submission."""
    import uuid

    return f"CNT-{uuid.uuid4().hex[:8].upper()}"


def _check_timing_spam(form_timestamp: str | None) -> bool:
    """
    Check if form was submitted too quickly (likely a bot).
    Returns True if submission appears to be spam.
    """
    if not form_timestamp:
        # No timestamp provided - could be legitimate older form
        return False

    try:
        load_time = float(form_timestamp)
        submit_time = datetime.utcnow().timestamp()
        elapsed = submit_time - load_time

        # If form submitted in less than 3 seconds, likely a bot
        if elapsed < 3:
            logger.warning(f"Contact form submitted too quickly: {elapsed:.2f}s")
            return True
    except (ValueError, TypeError):
        # Invalid timestamp format - ignore
        pass

    return False


async def _store_contact_message(message: ContactMessage) -> None:
    """Store contact message in Redis for later processing."""
    redis = get_redis()
    if redis:
        try:
            key = f"contact:{message.id}"
            await redis.setex(
                key,
                86400 * 7,  # Keep for 7 days
                message.model_dump_json(),
            )
            # Add to processing queue
            await redis.lpush("contact_queue", message.id)
        except Exception as e:
            logger.error(f"Failed to store contact message: {e}")


async def _send_notification_email(message: ContactMessage) -> None:
    """Send notification email to admin about new contact submission."""
    email_service = get_email_service()

    admin_email = settings.ADMIN_EMAIL if hasattr(settings, "ADMIN_EMAIL") else None
    if not admin_email:
        logger.warning("No ADMIN_EMAIL configured, skipping contact notification")
        return

    try:
        await email_service.send_raw(
            to=admin_email,
            subject=f"[Contact Form] {message.subject}",
            html_content=f"""
            <h2>New Contact Form Submission</h2>
            <p><strong>Reference:</strong> {message.id}</p>
            <p><strong>From:</strong> {message.name} ({message.email})</p>
            <p><strong>Subject:</strong> {message.subject}</p>
            <hr>
            <p><strong>Message:</strong></p>
            <p>{message.message}</p>
            <hr>
            <p><small>
                Submitted at: {message.submitted_at.isoformat()}<br>
                IP: {message.ip_address or 'Unknown'}<br>
                User Agent: {message.user_agent or 'Unknown'}
            </small></p>
            """,
            text_content=f"""
New Contact Form Submission

Reference: {message.id}
From: {message.name} ({message.email})
Subject: {message.subject}

Message:
{message.message}

---
Submitted at: {message.submitted_at.isoformat()}
IP: {message.ip_address or 'Unknown'}
            """,
        )
        logger.info(f"Sent contact notification for {message.id}")
    except Exception as e:
        logger.error(f"Failed to send contact notification: {e}")


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "",
    response_model=ContactFormResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit contact form",
    description="Submit a contact form message. Rate limited to prevent spam.",
)
async def submit_contact_form(
    request: Request,
    form: ContactFormRequest,
) -> ContactFormResponse:
    """
    Submit a contact form message.

    Includes:
    - Rate limiting (5 submissions per hour per IP)
    - Honeypot spam protection
    - Timing-based bot detection
    - Email notification to admin
    """
    # Get client IP for rate limiting
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"contact_rate:{client_ip}"

    # Check rate limit
    allowed, remaining, reset_time = await contact_rate_limiter.is_allowed(
        rate_key,
        CONTACT_RATE_LIMIT,
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many contact form submissions. Please try again later.",
                    "details": {"retry_after": reset_time},
                }
            },
            headers={"Retry-After": str(reset_time)},
        )

    # Check timing-based spam detection
    if _check_timing_spam(form.form_timestamp):
        # Return success to not tip off bots, but don't process
        logger.warning(f"Timing-based spam detection triggered for IP: {client_ip}")
        return ContactFormResponse(
            success=True,
            message="Thank you for your message. We'll get back to you soon!",
            reference_id=_generate_reference_id(),  # Fake reference
        )

    # Create contact message
    reference_id = _generate_reference_id()
    user_agent = request.headers.get("user-agent")

    message = ContactMessage(
        id=reference_id,
        name=form.name,
        email=form.email,
        subject=form.subject,
        message=form.message,
        ip_address=client_ip,
        user_agent=user_agent,
        submitted_at=datetime.utcnow(),
        metadata={
            "form_timestamp": form.form_timestamp,
        },
    )

    # Store message
    await _store_contact_message(message)

    # Send notification email (async via background job if available)
    try:
        await enqueue(
            "app.jobs.email_jobs.send_notification_email",
            settings.ADMIN_EMAIL if hasattr(settings, "ADMIN_EMAIL") else None,
            f"[Contact Form] {message.subject}",
            f"From: {message.name} ({message.email})\n\n{message.message}",
        )
    except Exception:
        # Fall back to direct send if job queue unavailable
        await _send_notification_email(message)

    logger.info(f"Contact form submitted: {reference_id} from {client_ip}")

    return ContactFormResponse(
        success=True,
        message="Thank you for your message. We'll get back to you soon!",
        reference_id=reference_id,
    )


@router.get(
    "/status",
    summary="Check contact form status",
    description="Check if contact form is available and get rate limit info.",
)
async def get_contact_status(request: Request) -> dict:
    """Get contact form availability status."""
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"contact_rate:{client_ip}"

    # Check current rate limit status
    allowed, remaining, reset_time = await contact_rate_limiter.is_allowed(
        rate_key,
        CONTACT_RATE_LIMIT,
    )

    return {
        "available": allowed,
        "rate_limit": {
            "limit": CONTACT_RATE_LIMIT.requests,
            "remaining": remaining,
            "reset": reset_time,
            "window": "1 hour",
        },
    }
