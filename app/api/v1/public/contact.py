"""
Contact form endpoint for public submissions.
Includes rate limiting, spam protection, confirmation emails, and webhook integration.

Features:
- Modular fields: name, email, message (required) + phone, company, subject (optional)
- Custom fields via extra_fields dict for any additional data
- Confirmation email to sender (configurable)
- Webhook for CRM/integration (Zapier, Make, n8n compatible)
- Database persistence + Redis cache
- Spam protection: honeypot + timing-based detection
"""

import hashlib
import logging
from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, model_validator

from app.api.deps import DBSession
from app.core.cache import get_redis
from app.core.config import settings
from app.core.middleware import RateLimitConfig, RateLimiter
from app.jobs import enqueue
from app.models.contact_submission import ContactSubmission, ContactSubmissionRead
from app.services.email import get_email_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contact", tags=["contact"])

# Rate limiter for contact form
contact_rate_limiter = RateLimiter()


def _get_rate_limit_config() -> RateLimitConfig:
    """Parse rate limit from settings."""
    return RateLimitConfig.from_string(settings.CONTACT_RATE_LIMIT)


# =============================================================================
# Schemas
# =============================================================================


class ContactFormRequest(BaseModel):
    """
    Contact form submission request.

    Required fields: name, email, message
    Optional fields: subject, phone, company
    Custom fields: extra_fields (dict for any additional data)
    """

    # Required fields
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
    message: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Message content",
    )

    # Optional standard fields
    subject: str | None = Field(
        default=None,
        max_length=200,
        description="Message subject (required if CONTACT_REQUIRE_SUBJECT=true)",
    )
    phone: str | None = Field(
        default=None,
        max_length=50,
        description="Phone number (required if CONTACT_REQUIRE_PHONE=true)",
    )
    company: str | None = Field(
        default=None,
        max_length=200,
        description="Company name",
    )

    # Flexible custom fields - users can add any additional data
    extra_fields: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom fields (e.g., budget, project_type, referral_source)",
    )

    # Form source tracking
    source: str | None = Field(
        default=None,
        max_length=100,
        description="Form source identifier (e.g., 'homepage', 'pricing-page')",
    )

    # Spam protection fields (hidden from users)
    website: str | None = Field(
        default=None,
        max_length=200,
        description="Honeypot field - leave empty",
    )
    form_timestamp: str | None = Field(
        default=None,
        description="Form load timestamp for bot detection",
    )

    @model_validator(mode="after")
    def validate_form(self) -> "ContactFormRequest":
        """Validate honeypot and required fields based on config."""
        # Honeypot check
        if self.website:
            raise ValueError("Invalid form submission")

        # Check configurable required fields
        if settings.CONTACT_REQUIRE_SUBJECT and not self.subject:
            raise ValueError("Subject is required")

        if settings.CONTACT_REQUIRE_PHONE and not self.phone:
            raise ValueError("Phone number is required")

        return self


class ContactFormResponse(BaseModel):
    """Contact form submission response."""

    success: bool = True
    message: str = "Thank you for your message. We'll get back to you soon!"
    reference_id: str | None = None


# Keep for backwards compatibility with tests
class ContactMessage(BaseModel):
    """Internal representation of a contact message (legacy)."""

    id: str
    name: str
    email: str
    subject: str | None = None
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
        return False

    try:
        load_time = float(form_timestamp)
        submit_time = datetime.utcnow().timestamp()
        elapsed = submit_time - load_time

        if elapsed < 3:
            logger.warning(f"Contact form submitted too quickly: {elapsed:.2f}s")
            return True
    except (ValueError, TypeError):
        pass

    return False


async def _send_admin_notification(submission: ContactSubmission) -> None:
    """Send notification email to admin about new contact submission."""
    if not settings.ADMIN_EMAIL:
        logger.warning("No ADMIN_EMAIL configured, skipping admin notification")
        return

    email_service = get_email_service()

    # Build extra fields display
    extra_display = ""
    if submission.extra_fields:
        extra_lines = [
            f"<li><strong>{k}:</strong> {v}</li>"
            for k, v in submission.extra_fields.items()
        ]
        extra_display = (
            f"<p><strong>Additional Info:</strong></p><ul>{''.join(extra_lines)}</ul>"
        )

    subject_line = submission.subject or "New Message"

    try:
        await email_service.send_raw(
            to=settings.ADMIN_EMAIL,
            subject=f"[Contact Form] {subject_line} - {submission.name}",
            html_content=f"""
            <h2>New Contact Form Submission</h2>
            <p><strong>Reference:</strong> {submission.reference_id}</p>
            <p><strong>From:</strong> {submission.name} ({submission.email})</p>
            {f'<p><strong>Phone:</strong> {submission.phone}</p>' if submission.phone else ''}
            {f'<p><strong>Company:</strong> {submission.company}</p>' if submission.company else ''}
            {f'<p><strong>Subject:</strong> {submission.subject}</p>' if submission.subject else ''}
            {f'<p><strong>Source:</strong> {submission.source}</p>' if submission.source else ''}
            <hr>
            <p><strong>Message:</strong></p>
            <p>{submission.message}</p>
            {extra_display}
            <hr>
            <p><small>
                Submitted at: {submission.created_at.isoformat()}<br>
                IP: {submission.ip_address or 'Unknown'}
            </small></p>
            """,
            text_content=f"""
New Contact Form Submission

Reference: {submission.reference_id}
From: {submission.name} ({submission.email})
{f'Phone: {submission.phone}' if submission.phone else ''}
{f'Company: {submission.company}' if submission.company else ''}
{f'Subject: {submission.subject}' if submission.subject else ''}

Message:
{submission.message}

---
Submitted at: {submission.created_at.isoformat()}
            """,
        )
        logger.info(f"Sent admin notification for {submission.reference_id}")
    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")


async def _send_confirmation_email(submission: ContactSubmission) -> None:
    """Send confirmation email to the person who submitted the form."""
    if not settings.CONTACT_SEND_CONFIRMATION:
        return

    email_service = get_email_service()

    try:
        await email_service.send_raw(
            to=submission.email,
            subject=f"We received your message - {settings.PROJECT_NAME}",
            html_content=f"""
            <h2>Thank you for contacting us!</h2>
            <p>Hi {submission.name},</p>
            <p>We've received your message and will get back to you as soon as possible.</p>
            <p><strong>Your reference number:</strong> {submission.reference_id}</p>
            <hr>
            <p><strong>Your message:</strong></p>
            <p>{submission.message[:500]}{'...' if len(submission.message) > 500 else ''}</p>
            <hr>
            <p>Best regards,<br>The {settings.PROJECT_NAME} Team</p>
            """,
            text_content=f"""
Thank you for contacting us!

Hi {submission.name},

We've received your message and will get back to you as soon as possible.

Your reference number: {submission.reference_id}

---
Your message:
{submission.message[:500]}{'...' if len(submission.message) > 500 else ''}

---
Best regards,
The {settings.PROJECT_NAME} Team
            """,
        )
        logger.info(f"Sent confirmation email to {submission.email}")
    except Exception as e:
        logger.error(f"Failed to send confirmation email: {e}")


async def _send_webhook(submission: ContactSubmission) -> bool:
    """
    Send submission data to configured webhook URL.

    Compatible with Zapier, Make, n8n, and custom integrations.
    Includes signature header for verification.
    """
    if not settings.CONTACT_WEBHOOK_URL:
        return False

    payload = {
        "event": "contact.submitted",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "reference_id": submission.reference_id,
            "name": submission.name,
            "email": submission.email,
            "phone": submission.phone,
            "company": submission.company,
            "subject": submission.subject,
            "message": submission.message,
            "extra_fields": submission.extra_fields,
            "source": submission.source,
            "submitted_at": submission.created_at.isoformat(),
        },
    }

    # Generate signature for webhook verification
    signature = hashlib.sha256(
        f"{submission.reference_id}{settings.SECRET_KEY}".encode()
    ).hexdigest()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                settings.CONTACT_WEBHOOK_URL,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,
                    "X-Reference-Id": submission.reference_id,
                },
            )
            response.raise_for_status()
            logger.info(f"Webhook sent for {submission.reference_id}")
            return True
    except Exception as e:
        logger.error(f"Webhook failed for {submission.reference_id}: {e}")
        return False


async def _cache_submission(submission: ContactSubmission) -> None:
    """Cache submission in Redis for quick access."""
    redis = get_redis()
    if redis:
        try:
            key = f"contact:{submission.reference_id}"
            await redis.setex(
                key,
                86400 * 7,  # 7 days
                ContactSubmissionRead.model_validate(submission).model_dump_json(),
            )
        except Exception as e:
            logger.error(f"Failed to cache submission: {e}")


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
    session: DBSession,
) -> ContactFormResponse:
    """
    Submit a contact form message.

    Features:
    - Rate limiting (configurable via CONTACT_RATE_LIMIT)
    - Honeypot spam protection
    - Timing-based bot detection
    - Database persistence
    - Admin email notification
    - Confirmation email to sender (if CONTACT_SEND_CONFIRMATION=true)
    - Webhook for CRM/integrations (if CONTACT_WEBHOOK_URL set)
    """
    # Get client IP for rate limiting
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"contact_rate:{client_ip}"

    # Check rate limit
    rate_config = _get_rate_limit_config()
    allowed, remaining, reset_time = await contact_rate_limiter.is_allowed(
        rate_key,
        rate_config,
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
        logger.warning(f"Timing-based spam detection triggered for IP: {client_ip}")
        return ContactFormResponse(
            success=True,
            message="Thank you for your message. We'll get back to you soon!",
            reference_id=_generate_reference_id(),
        )

    # Create submission record
    reference_id = _generate_reference_id()
    user_agent = request.headers.get("user-agent")

    submission = ContactSubmission(
        reference_id=reference_id,
        name=form.name,
        email=form.email,
        message=form.message,
        subject=form.subject,
        phone=form.phone,
        company=form.company,
        extra_fields=form.extra_fields,
        source=form.source,
        ip_address=client_ip,
        user_agent=user_agent,
        status="new",
    )

    # Save to database
    session.add(submission)
    await session.commit()
    await session.refresh(submission)

    # Cache in Redis
    await _cache_submission(submission)

    # Send notifications via background jobs when possible
    try:
        # Admin notification
        if settings.ADMIN_EMAIL:
            await enqueue(
                "app.jobs.email_jobs.send_notification_email",
                settings.ADMIN_EMAIL,
                f"[Contact Form] {form.subject or 'New Message'} - {form.name}",
                f"From: {form.name} ({form.email})\n\n{form.message}",
            )

        # Confirmation email to sender
        if settings.CONTACT_SEND_CONFIRMATION:
            await enqueue(
                "app.jobs.email_jobs.send_notification_email",
                form.email,
                f"We received your message - {settings.PROJECT_NAME}",
                f"Hi {form.name},\n\nThank you for contacting us. "
                f"Your reference number is {reference_id}.\n\nWe'll get back to you soon!",
            )
    except Exception:
        # Fall back to direct send if job queue unavailable
        await _send_admin_notification(submission)
        await _send_confirmation_email(submission)

    # Send webhook (async, don't block response)
    if settings.CONTACT_WEBHOOK_URL:
        try:
            webhook_sent = await _send_webhook(submission)
            if webhook_sent:
                submission.webhook_sent = True
                submission.webhook_sent_at = datetime.utcnow()
                session.add(submission)
                await session.commit()
        except Exception as e:
            logger.error(f"Webhook error: {e}")

    logger.info(f"Contact form submitted: {reference_id} from {client_ip}")

    return ContactFormResponse(
        success=True,
        message="Thank you for your message. We'll get back to you soon!",
        reference_id=reference_id,
    )


@router.get(
    "/status",
    summary="Check contact form status",
    description="Check if contact form is available and get configuration info.",
)
async def get_contact_status(request: Request) -> dict:
    """Get contact form availability and configuration."""
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"contact_rate:{client_ip}"

    rate_config = _get_rate_limit_config()
    allowed, remaining, reset_time = await contact_rate_limiter.is_allowed(
        rate_key,
        rate_config,
    )

    return {
        "available": allowed,
        "rate_limit": {
            "limit": rate_config.requests,
            "remaining": remaining,
            "reset": reset_time,
            "window": settings.CONTACT_RATE_LIMIT,
        },
        "config": {
            "require_subject": settings.CONTACT_REQUIRE_SUBJECT,
            "require_phone": settings.CONTACT_REQUIRE_PHONE,
            "sends_confirmation": settings.CONTACT_SEND_CONFIRMATION,
        },
    }
