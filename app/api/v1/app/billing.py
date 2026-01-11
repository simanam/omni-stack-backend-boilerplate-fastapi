"""
Billing API endpoints for subscription management.
Handles checkout, billing portal, and subscription status.
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DBSession
from app.business.billing_service import billing_service
from app.core.config import settings

router = APIRouter(tags=["Billing"])


# =============================================================================
# Schemas
# =============================================================================


class BillingStatusResponse(BaseModel):
    """Billing status response."""

    plan: str = Field(description="Current plan (free, pro, enterprise)")
    status: str | None = Field(description="Subscription status")
    current_period_end: datetime | None = Field(
        description="Current billing period end date"
    )
    cancel_at_period_end: bool = Field(
        default=False, description="Whether subscription will cancel at period end"
    )
    has_active_subscription: bool = Field(
        description="Whether user has an active subscription"
    )


class CheckoutRequest(BaseModel):
    """Checkout request."""

    plan: Literal["monthly", "yearly"] = Field(description="Billing interval")
    success_url: str = Field(description="URL to redirect on success")
    cancel_url: str = Field(description="URL to redirect on cancel")


class CheckoutResponse(BaseModel):
    """Checkout response."""

    session_id: str = Field(description="Stripe checkout session ID")
    url: str = Field(description="Checkout URL to redirect user")


class PortalResponse(BaseModel):
    """Billing portal response."""

    url: str = Field(description="Billing portal URL")


class InvoiceResponse(BaseModel):
    """Invoice response."""

    id: str
    number: str | None
    status: str
    amount_due: int = Field(description="Amount in cents")
    amount_paid: int = Field(description="Amount in cents")
    currency: str
    created: int = Field(description="Unix timestamp")
    hosted_invoice_url: str | None
    invoice_pdf: str | None


class CancelResponse(BaseModel):
    """Cancel subscription response."""

    message: str
    cancel_at_period_end: bool
    current_period_end: datetime | None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/status", response_model=BillingStatusResponse)
async def get_billing_status(
    session: DBSession,
    user: CurrentUser,
) -> BillingStatusResponse:
    """
    Get current billing/subscription status.

    Returns the user's current plan, subscription status, and billing period info.
    """
    if not settings.stripe_available:
        return BillingStatusResponse(
            plan="free",
            status=None,
            current_period_end=None,
            cancel_at_period_end=False,
            has_active_subscription=False,
        )

    status = await billing_service.get_billing_status(session, user)

    return BillingStatusResponse(
        plan=status.plan,
        status=status.status,
        current_period_end=status.current_period_end,
        cancel_at_period_end=status.cancel_at_period_end,
        has_active_subscription=status.status in ("active", "trialing"),
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    session: DBSession,
    user: CurrentUser,
    request: CheckoutRequest,
) -> CheckoutResponse:
    """
    Create a Stripe checkout session.

    Initiates the subscription checkout flow. Returns a URL to redirect
    the user to Stripe's hosted checkout page.
    """
    if not settings.stripe_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured",
        )

    # Check if user already has an active subscription
    current_status = await billing_service.get_billing_status(session, user)
    if current_status.status in ("active", "trialing"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an active subscription. Use billing portal to change plans.",
        )

    result = await billing_service.start_checkout(
        session=session,
        user=user,
        interval=request.plan,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
    )

    return CheckoutResponse(
        session_id=result.session_id,
        url=result.url,
    )


@router.get("/portal", response_model=PortalResponse)
async def get_billing_portal(
    session: DBSession,
    user: CurrentUser,
    return_url: str = Query(..., description="URL to return to after portal"),
) -> PortalResponse:
    """
    Get Stripe billing portal URL.

    Returns a URL to Stripe's billing portal where users can:
    - Update payment method
    - View invoices
    - Change or cancel subscription
    """
    if not settings.stripe_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured",
        )

    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found. Subscribe first.",
        )

    result = await billing_service.get_billing_portal_url(
        session=session,
        user=user,
        return_url=return_url,
    )

    return PortalResponse(url=result.url)


@router.get("/invoices", response_model=list[InvoiceResponse])
async def get_invoices(
    user: CurrentUser,
    limit: int = Query(default=10, ge=1, le=100),
) -> list[InvoiceResponse]:
    """
    Get user's invoices.

    Returns a list of invoices with download links.
    """
    if not settings.stripe_available:
        return []

    if not user.stripe_customer_id:
        return []

    invoices = await billing_service.get_invoices(user, limit)

    return [
        InvoiceResponse(
            id=inv["id"],
            number=inv["number"],
            status=inv["status"],
            amount_due=inv["amount_due"],
            amount_paid=inv["amount_paid"],
            currency=inv["currency"],
            created=inv["created"],
            hosted_invoice_url=inv["hosted_invoice_url"],
            invoice_pdf=inv["invoice_pdf"],
        )
        for inv in invoices
    ]


@router.post("/cancel", response_model=CancelResponse)
async def cancel_subscription(
    session: DBSession,
    user: CurrentUser,
    immediate: bool = Query(
        default=False,
        description="If true, cancel immediately. Otherwise, cancel at period end.",
    ),
) -> CancelResponse:
    """
    Cancel subscription.

    By default, cancels at the end of the current billing period.
    Set immediate=true to cancel immediately (no refund).
    """
    if not settings.stripe_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured",
        )

    current_status = await billing_service.get_billing_status(session, user)

    if current_status.status not in ("active", "trialing"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription to cancel",
        )

    result = await billing_service.cancel_subscription(
        session=session,
        user=user,
        at_period_end=not immediate,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to cancel subscription",
        )

    period_end = None
    if result.current_period_end:
        period_end = datetime.fromtimestamp(result.current_period_end)

    if immediate:
        message = "Subscription cancelled immediately"
    else:
        message = "Subscription will cancel at the end of the billing period"

    return CancelResponse(
        message=message,
        cancel_at_period_end=result.cancel_at_period_end,
        current_period_end=period_end,
    )


@router.post("/resume")
async def resume_subscription(
    session: DBSession,
    user: CurrentUser,
) -> dict:
    """
    Resume a cancelled subscription (before it ends).

    Only works if the subscription was cancelled with cancel_at_period_end=true
    and the period hasn't ended yet.
    """
    if not settings.stripe_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured",
        )

    result = await billing_service.resume_subscription(session, user)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No cancelled subscription to resume",
        )

    return {
        "message": "Subscription resumed",
        "status": result.status,
        "plan": result.plan,
    }
