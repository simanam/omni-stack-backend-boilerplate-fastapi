"""
Webhook handlers for external services.
Handles webhooks from Stripe, Clerk, and Supabase.
"""

import hashlib
import hmac
import logging
from datetime import datetime

from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlmodel import select

from app.api.deps import DBSession
from app.business.billing_service import billing_service
from app.core.config import settings
from app.models.webhook_event import WebhookEvent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Webhooks"])


# =============================================================================
# Webhook Event Helpers
# =============================================================================


async def create_webhook_event(
    session: DBSession,
    provider: str,
    event_type: str,
    idempotency_key: str,
    payload: dict,
) -> WebhookEvent | None:
    """
    Create a webhook event record for idempotency tracking.

    Returns None if event already exists (duplicate).
    """
    # Check for duplicate
    result = await session.execute(
        select(WebhookEvent).where(WebhookEvent.idempotency_key == idempotency_key)
    )
    existing = result.scalar_one_or_none()

    if existing:
        logger.info(f"Duplicate webhook event: {idempotency_key}")
        return None

    # Create new event
    event = WebhookEvent(
        provider=provider,
        event_type=event_type,
        idempotency_key=idempotency_key,
        payload=payload,
        status="processing",
        attempts=1,
    )
    session.add(event)
    await session.flush()
    return event


async def mark_event_processed(
    session: DBSession,
    event: WebhookEvent,
) -> None:
    """Mark webhook event as successfully processed."""
    event.status = "processed"
    event.processed_at = datetime.utcnow()
    session.add(event)
    await session.flush()


async def mark_event_failed(
    session: DBSession,
    event: WebhookEvent,
    error: str,
) -> None:
    """Mark webhook event as failed."""
    event.status = "failed"
    event.error_message = error
    session.add(event)
    await session.flush()


# =============================================================================
# Stripe Webhooks
# =============================================================================


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    session: DBSession,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
) -> dict:
    """
    Handle Stripe webhooks.

    Processes payment and subscription events:
    - checkout.session.completed: New subscription
    - customer.subscription.updated: Plan change, renewal
    - customer.subscription.deleted: Cancellation
    - invoice.paid: Successful payment
    - invoice.payment_failed: Failed payment
    """
    if not settings.stripe_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe not configured",
        )

    # Get raw body for signature verification
    payload = await request.body()

    # Verify and construct event
    from app.services.payments.stripe_service import get_stripe_service

    try:
        stripe_svc = get_stripe_service()
        event = stripe_svc.construct_webhook_event(payload, stripe_signature)
    except ValueError as e:
        logger.error(f"Invalid Stripe webhook signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    # Create idempotency record
    webhook_event = await create_webhook_event(
        session=session,
        provider="stripe",
        event_type=event.type,
        idempotency_key=event.id,
        payload=event.data.object if hasattr(event.data, "object") else {},
    )

    if webhook_event is None:
        # Duplicate event, already processed
        return {"status": "already_processed"}

    try:
        # Handle event types
        if event.type == "checkout.session.completed":
            await _handle_checkout_completed(session, event)

        elif event.type == "customer.subscription.updated":
            await _handle_subscription_updated(session, event)

        elif event.type == "customer.subscription.deleted":
            await _handle_subscription_deleted(session, event)

        elif event.type == "invoice.paid":
            await _handle_invoice_paid(session, event)

        elif event.type == "invoice.payment_failed":
            await _handle_invoice_payment_failed(session, event)

        elif event.type == "customer.created":
            logger.info(f"Customer created: {event.data.object.get('id')}")

        else:
            logger.info(f"Unhandled Stripe event type: {event.type}")

        await mark_event_processed(session, webhook_event)
        return {"status": "processed"}

    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {e}")
        await mark_event_failed(session, webhook_event, str(e))
        # Return 200 to prevent Stripe from retrying
        # We've logged the error and can investigate
        return {"status": "error", "message": str(e)}


async def _handle_checkout_completed(session: DBSession, event) -> None:
    """Handle checkout.session.completed event."""
    checkout_session = event.data.object
    customer_id = checkout_session.get("customer")
    subscription_id = checkout_session.get("subscription")

    if not customer_id or not subscription_id:
        logger.warning("Checkout completed without customer or subscription")
        return

    await billing_service.handle_checkout_completed(
        session=session,
        customer_id=customer_id,
        subscription_id=subscription_id,
    )
    logger.info(f"Checkout completed for customer: {customer_id}")


async def _handle_subscription_updated(session: DBSession, event) -> None:
    """Handle customer.subscription.updated event."""
    subscription = event.data.object
    customer_id = subscription.get("customer")
    subscription_id = subscription.get("id")

    if not customer_id:
        return

    await billing_service.handle_subscription_updated(
        session=session,
        customer_id=customer_id,
        subscription_id=subscription_id,
    )
    logger.info(f"Subscription updated for customer: {customer_id}")


async def _handle_subscription_deleted(session: DBSession, event) -> None:
    """Handle customer.subscription.deleted event."""
    subscription = event.data.object
    customer_id = subscription.get("customer")

    if not customer_id:
        return

    await billing_service.handle_subscription_deleted(
        session=session,
        customer_id=customer_id,
    )
    logger.info(f"Subscription deleted for customer: {customer_id}")


async def _handle_invoice_paid(session: DBSession, event) -> None:
    """Handle invoice.paid event."""
    invoice = event.data.object
    customer_id = invoice.get("customer")
    subscription_id = invoice.get("subscription")

    logger.info(
        f"Invoice paid for customer: {customer_id}, subscription: {subscription_id}"
    )
    # Could send a payment confirmation email here


async def _handle_invoice_payment_failed(session: DBSession, event) -> None:
    """Handle invoice.payment_failed event."""
    invoice = event.data.object
    customer_id = invoice.get("customer")

    logger.warning(f"Invoice payment failed for customer: {customer_id}")
    # Could send a payment failure notification email here


# =============================================================================
# Clerk Webhooks
# =============================================================================


def _verify_clerk_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify Clerk webhook signature (svix).

    Clerk uses Svix for webhooks which has a specific signature format.
    """
    # Clerk signature format: v1,timestamp,signature
    try:
        parts = signature.split(",")
        if len(parts) < 3:
            return False

        timestamp = parts[1]
        provided_signature = parts[2]

        # Create signed payload
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"

        # Compute expected signature
        expected = hmac.new(
            secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, provided_signature)
    except Exception:
        return False


@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    session: DBSession,
    svix_id: str = Header(..., alias="svix-id"),
    svix_timestamp: str = Header(..., alias="svix-timestamp"),
    svix_signature: str = Header(..., alias="svix-signature"),
) -> dict:
    """
    Handle Clerk webhooks.

    Processes user events:
    - user.created: New user signup
    - user.updated: Profile update
    - user.deleted: User deletion
    - session.created: New login
    """
    if not settings.CLERK_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clerk not configured",
        )

    payload = await request.body()

    # Note: For production, use the svix library for proper verification
    # pip install svix
    # from svix.webhooks import Webhook
    # wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
    # payload = wh.verify(payload, headers)

    try:
        import json

        event = json.loads(payload)
    except Exception as e:
        logger.error(f"Invalid Clerk webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        )

    event_type = event.get("type", "")
    event_id = svix_id

    # Create idempotency record
    webhook_event = await create_webhook_event(
        session=session,
        provider="clerk",
        event_type=event_type,
        idempotency_key=event_id,
        payload=event.get("data", {}),
    )

    if webhook_event is None:
        return {"status": "already_processed"}

    try:
        if event_type == "user.created":
            await _handle_clerk_user_created(session, event)

        elif event_type == "user.updated":
            await _handle_clerk_user_updated(session, event)

        elif event_type == "user.deleted":
            await _handle_clerk_user_deleted(session, event)

        elif event_type == "session.created":
            logger.info(f"Clerk session created for user: {event.get('data', {}).get('user_id')}")

        else:
            logger.info(f"Unhandled Clerk event type: {event_type}")

        await mark_event_processed(session, webhook_event)
        return {"status": "processed"}

    except Exception as e:
        logger.error(f"Error processing Clerk webhook: {e}")
        await mark_event_failed(session, webhook_event, str(e))
        return {"status": "error", "message": str(e)}


async def _handle_clerk_user_created(session: DBSession, event: dict) -> None:
    """Handle user.created event from Clerk."""
    from app.models.user import User

    data = event.get("data", {})
    user_id = data.get("id")
    email_addresses = data.get("email_addresses", [])
    primary_email = next(
        (e["email_address"] for e in email_addresses if e.get("id") == data.get("primary_email_address_id")),
        email_addresses[0]["email_address"] if email_addresses else None,
    )

    if not user_id or not primary_email:
        logger.warning("Clerk user.created missing required fields")
        return

    # Check if user already exists
    result = await session.execute(select(User).where(User.id == user_id))
    if result.scalar_one_or_none():
        logger.info(f"User {user_id} already exists")
        return

    # Create user
    user = User(
        id=user_id,
        email=primary_email,
        full_name=f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or None,
        avatar_url=data.get("image_url"),
    )
    session.add(user)
    await session.flush()
    logger.info(f"Created user from Clerk: {user_id}")


async def _handle_clerk_user_updated(session: DBSession, event: dict) -> None:
    """Handle user.updated event from Clerk."""
    from app.models.user import User

    data = event.get("data", {})
    user_id = data.get("id")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"User {user_id} not found for update")
        return

    # Update fields
    email_addresses = data.get("email_addresses", [])
    primary_email = next(
        (e["email_address"] for e in email_addresses if e.get("id") == data.get("primary_email_address_id")),
        None,
    )
    if primary_email:
        user.email = primary_email

    full_name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
    if full_name:
        user.full_name = full_name

    if data.get("image_url"):
        user.avatar_url = data.get("image_url")

    session.add(user)
    await session.flush()
    logger.info(f"Updated user from Clerk: {user_id}")


async def _handle_clerk_user_deleted(session: DBSession, event: dict) -> None:
    """Handle user.deleted event from Clerk."""
    from app.models.user import User

    data = event.get("data", {})
    user_id = data.get("id")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        return

    # Soft delete by deactivating
    user.is_active = False
    session.add(user)
    await session.flush()
    logger.info(f"Deactivated user from Clerk deletion: {user_id}")


# =============================================================================
# Supabase Webhooks
# =============================================================================


@router.post("/supabase")
async def supabase_webhook(
    request: Request,
    session: DBSession,
    authorization: str = Header(None),
) -> dict:
    """
    Handle Supabase webhooks.

    Processes auth events. Note: Supabase webhooks need to be configured
    in the Supabase dashboard with a secret that matches SUPABASE_WEBHOOK_SECRET.
    """
    # Simple token-based auth for Supabase webhooks
    # In production, use a proper webhook secret
    webhook_secret = settings.SECRET_KEY  # Or a dedicated SUPABASE_WEBHOOK_SECRET

    if authorization != f"Bearer {webhook_secret}":
        logger.warning("Invalid Supabase webhook authorization")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization",
        )

    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Invalid Supabase webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        )

    event_type = payload.get("type", "")
    record = payload.get("record", {})
    old_record = payload.get("old_record", {})

    # Generate idempotency key from record ID and timestamp
    record_id = record.get("id") or old_record.get("id", "unknown")
    idempotency_key = f"supabase_{event_type}_{record_id}_{payload.get('timestamp', '')}"

    webhook_event = await create_webhook_event(
        session=session,
        provider="supabase",
        event_type=event_type,
        idempotency_key=idempotency_key,
        payload=payload,
    )

    if webhook_event is None:
        return {"status": "already_processed"}

    try:
        # Handle different event types
        if event_type == "INSERT" and payload.get("table") == "auth.users":
            await _handle_supabase_user_created(session, record)

        elif event_type == "UPDATE" and payload.get("table") == "auth.users":
            await _handle_supabase_user_updated(session, record)

        elif event_type == "DELETE" and payload.get("table") == "auth.users":
            await _handle_supabase_user_deleted(session, old_record)

        else:
            logger.info(f"Unhandled Supabase event: {event_type} on {payload.get('table')}")

        await mark_event_processed(session, webhook_event)
        return {"status": "processed"}

    except Exception as e:
        logger.error(f"Error processing Supabase webhook: {e}")
        await mark_event_failed(session, webhook_event, str(e))
        return {"status": "error", "message": str(e)}


async def _handle_supabase_user_created(session: DBSession, record: dict) -> None:
    """Handle user insert from Supabase."""
    from app.models.user import User

    user_id = record.get("id")
    email = record.get("email")

    if not user_id or not email:
        return

    # Check if exists
    result = await session.execute(select(User).where(User.id == user_id))
    if result.scalar_one_or_none():
        return

    user_metadata = record.get("raw_user_meta_data", {}) or {}

    user = User(
        id=user_id,
        email=email,
        full_name=user_metadata.get("full_name") or user_metadata.get("name"),
        avatar_url=user_metadata.get("avatar_url"),
    )
    session.add(user)
    await session.flush()
    logger.info(f"Created user from Supabase: {user_id}")


async def _handle_supabase_user_updated(session: DBSession, record: dict) -> None:
    """Handle user update from Supabase."""
    from app.models.user import User

    user_id = record.get("id")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        return

    if record.get("email"):
        user.email = record.get("email")

    user_metadata = record.get("raw_user_meta_data", {}) or {}
    if user_metadata.get("full_name"):
        user.full_name = user_metadata.get("full_name")
    if user_metadata.get("avatar_url"):
        user.avatar_url = user_metadata.get("avatar_url")

    session.add(user)
    await session.flush()
    logger.info(f"Updated user from Supabase: {user_id}")


async def _handle_supabase_user_deleted(session: DBSession, record: dict) -> None:
    """Handle user delete from Supabase."""
    from app.models.user import User

    user_id = record.get("id")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        return

    user.is_active = False
    session.add(user)
    await session.flush()
    logger.info(f"Deactivated user from Supabase deletion: {user_id}")


# =============================================================================
# Apple App Store Webhooks (In-App Purchases)
# =============================================================================


@router.post("/apple")
async def apple_webhook(
    request: Request,
    session: DBSession,
) -> dict:
    """
    Handle Apple App Store Server Notifications V2.

    Processes subscription events from iOS apps:
    - SUBSCRIBED: New subscription
    - DID_RENEW: Subscription renewed
    - DID_CHANGE_RENEWAL_STATUS: Auto-renew enabled/disabled
    - EXPIRED: Subscription expired
    - REFUND: Refund issued
    - REVOKE: Family sharing revoked

    Webhook URL to configure in App Store Connect:
    https://your-domain.com/api/v1/public/webhooks/apple
    """
    if not settings.apple_iap_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Apple IAP not configured",
        )

    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Invalid Apple webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        )

    signed_payload = payload.get("signedPayload")
    if not signed_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing signedPayload",
        )

    # Decode and parse the notification
    from app.business.iap_service import iap_service
    from app.services.payments.apple_iap_service import get_apple_iap_service

    apple_service = get_apple_iap_service()

    try:
        notification = apple_service.decode_notification(signed_payload)
    except Exception as e:
        logger.error(f"Failed to decode Apple notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid notification format",
        )

    # Create idempotency record
    webhook_event = await create_webhook_event(
        session=session,
        provider="apple",
        event_type=notification.notification_type.value,
        idempotency_key=notification.notification_uuid,
        payload=notification.raw_payload,
    )

    if webhook_event is None:
        return {"status": "already_processed"}

    try:
        # Handle the notification
        user = await iap_service.handle_apple_notification(session, notification)

        if user:
            logger.info(
                f"Apple notification {notification.notification_type.value} "
                f"processed for user {user.id}"
            )
        else:
            logger.info(
                f"Apple notification {notification.notification_type.value} "
                f"received but no user found"
            )

        await mark_event_processed(session, webhook_event)
        return {"status": "processed"}

    except Exception as e:
        logger.error(f"Error processing Apple webhook: {e}")
        await mark_event_failed(session, webhook_event, str(e))
        return {"status": "error", "message": str(e)}


# =============================================================================
# Google Play Store Webhooks (In-App Purchases)
# =============================================================================


@router.post("/google")
async def google_webhook(
    request: Request,
    session: DBSession,
) -> dict:
    """
    Handle Google Play Real-time Developer Notifications (RTDN).

    Receives Pub/Sub push messages for subscription events:
    - SUBSCRIPTION_PURCHASED: New subscription
    - SUBSCRIPTION_RENEWED: Subscription renewed
    - SUBSCRIPTION_CANCELED: Subscription canceled
    - SUBSCRIPTION_EXPIRED: Subscription expired
    - SUBSCRIPTION_REVOKED: Subscription refunded/revoked

    Webhook URL to configure in Google Cloud Pub/Sub:
    https://your-domain.com/api/v1/public/webhooks/google
    """
    if not settings.google_iap_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google IAP not configured",
        )

    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Invalid Google webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        )

    # Decode Pub/Sub message
    from app.business.iap_service import iap_service
    from app.services.payments.google_iap_service import get_google_iap_service

    google_service = get_google_iap_service()

    try:
        pub_sub_message = google_service.decode_pub_sub_message(payload)
        notification = google_service.parse_notification(pub_sub_message)
    except Exception as e:
        logger.error(f"Failed to decode Google notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid notification format",
        )

    # Verify package name
    if not google_service.verify_package_name(notification):
        logger.warning(f"Package name mismatch: got {notification.package_name}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid package name",
        )

    # Handle test notifications
    if notification.test_notification:
        logger.info(f"Received Google test notification: {notification.test_notification}")
        return {"status": "test_acknowledged"}

    # Only process subscription notifications
    if not notification.subscription_notification:
        logger.info("Ignoring non-subscription Google notification")
        return {"status": "ignored"}

    sub_notification = notification.subscription_notification

    # Create idempotency key from message ID and notification type
    idempotency_key = f"google_{pub_sub_message.message_id}_{sub_notification.notification_type.value}"

    webhook_event = await create_webhook_event(
        session=session,
        provider="google",
        event_type=google_service.get_notification_type_name(sub_notification.notification_type),
        idempotency_key=idempotency_key,
        payload=notification.raw_data,
    )

    if webhook_event is None:
        return {"status": "already_processed"}

    try:
        # Handle the notification
        user = await iap_service.handle_google_notification(session, sub_notification)

        if user:
            logger.info(
                f"Google notification {sub_notification.notification_type.name} "
                f"processed for user {user.id}"
            )
        else:
            logger.info(
                f"Google notification {sub_notification.notification_type.name} "
                f"received but no user found"
            )

        await mark_event_processed(session, webhook_event)
        return {"status": "processed"}

    except Exception as e:
        logger.error(f"Error processing Google webhook: {e}")
        await mark_event_failed(session, webhook_event, str(e))
        return {"status": "error", "message": str(e)}
