"""
Stripe payment service for subscription management.
Handles customer creation, checkout sessions, subscriptions, and billing portal.
"""

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import stripe
from stripe import Customer, Subscription

from app.core.config import settings

logger = logging.getLogger(__name__)

# Type aliases
PlanInterval = Literal["month", "year"]


@dataclass
class CheckoutResult:
    """Result of creating a checkout session."""

    session_id: str
    url: str


@dataclass
class PortalResult:
    """Result of creating a billing portal session."""

    url: str


@dataclass
class SubscriptionInfo:
    """Subscription information."""

    id: str
    status: str
    plan: str | None
    current_period_start: int
    current_period_end: int
    cancel_at_period_end: bool
    price_id: str | None


class StripeService:
    """
    Stripe API wrapper for subscription management.

    Usage:
        stripe_svc = get_stripe_service()
        customer = await stripe_svc.create_customer(email, name, user_id)
        checkout = await stripe_svc.create_checkout_session(customer.id, "monthly")
    """

    def __init__(self) -> None:
        if not settings.STRIPE_SECRET_KEY:
            raise ValueError("STRIPE_SECRET_KEY not configured")
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self._price_ids = {
            "monthly": settings.STRIPE_PRICE_ID_MONTHLY,
            "yearly": settings.STRIPE_PRICE_ID_YEARLY,
        }

    def _get_price_id(self, plan: str) -> str:
        """Get price ID for plan."""
        price_id = self._price_ids.get(plan)
        if not price_id:
            raise ValueError(f"No price ID configured for plan: {plan}")
        return price_id

    async def create_customer(
        self,
        email: str,
        name: str | None = None,
        user_id: str | None = None,
    ) -> Customer:
        """
        Create a new Stripe customer.

        Args:
            email: Customer email
            name: Customer name
            user_id: Internal user ID for metadata

        Returns:
            Stripe Customer object
        """
        try:
            metadata = {}
            if user_id:
                metadata["user_id"] = user_id

            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata,
            )
            logger.info(f"Created Stripe customer: {customer.id} for user: {user_id}")
            return customer
        except stripe.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise

    async def get_customer(self, customer_id: str) -> Customer | None:
        """
        Retrieve a Stripe customer by ID.

        Args:
            customer_id: Stripe customer ID

        Returns:
            Stripe Customer object or None if not found
        """
        try:
            return stripe.Customer.retrieve(customer_id)
        except stripe.InvalidRequestError:
            return None
        except stripe.StripeError as e:
            logger.error(f"Failed to retrieve customer {customer_id}: {e}")
            raise

    async def update_customer(
        self,
        customer_id: str,
        email: str | None = None,
        name: str | None = None,
    ) -> Customer:
        """
        Update a Stripe customer.

        Args:
            customer_id: Stripe customer ID
            email: New email (optional)
            name: New name (optional)

        Returns:
            Updated Stripe Customer object
        """
        try:
            update_data = {}
            if email:
                update_data["email"] = email
            if name:
                update_data["name"] = name

            return stripe.Customer.modify(customer_id, **update_data)
        except stripe.StripeError as e:
            logger.error(f"Failed to update customer {customer_id}: {e}")
            raise

    async def create_checkout_session(
        self,
        customer_id: str,
        plan: str,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutResult:
        """
        Create a Stripe Checkout session for subscription.

        Args:
            customer_id: Stripe customer ID
            plan: Plan type ("monthly" or "yearly")
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancel

        Returns:
            CheckoutResult with session ID and URL
        """
        try:
            price_id = self._get_price_id(plan)

            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode="subscription",
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                success_url=success_url,
                cancel_url=cancel_url,
                allow_promotion_codes=True,
            )

            logger.info(f"Created checkout session: {session.id} for customer: {customer_id}")
            return CheckoutResult(session_id=session.id, url=session.url or "")
        except stripe.StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise

    async def create_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> PortalResult:
        """
        Create a Stripe Billing Portal session.

        Args:
            customer_id: Stripe customer ID
            return_url: URL to return to after portal

        Returns:
            PortalResult with portal URL
        """
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )

            logger.info(f"Created portal session for customer: {customer_id}")
            return PortalResult(url=session.url)
        except stripe.StripeError as e:
            logger.error(f"Failed to create portal session: {e}")
            raise

    async def get_subscription(self, subscription_id: str) -> SubscriptionInfo | None:
        """
        Get subscription details.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            SubscriptionInfo or None if not found
        """
        try:
            sub = stripe.Subscription.retrieve(subscription_id)
            return self._subscription_to_info(sub)
        except stripe.InvalidRequestError:
            return None
        except stripe.StripeError as e:
            logger.error(f"Failed to get subscription {subscription_id}: {e}")
            raise

    async def get_customer_subscriptions(
        self,
        customer_id: str,
    ) -> list[SubscriptionInfo]:
        """
        Get all subscriptions for a customer.

        Args:
            customer_id: Stripe customer ID

        Returns:
            List of SubscriptionInfo
        """
        try:
            subs = stripe.Subscription.list(customer=customer_id, limit=10)
            return [self._subscription_to_info(sub) for sub in subs.data]
        except stripe.StripeError as e:
            logger.error(f"Failed to list subscriptions for {customer_id}: {e}")
            raise

    async def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True,
    ) -> SubscriptionInfo:
        """
        Cancel a subscription.

        Args:
            subscription_id: Stripe subscription ID
            at_period_end: If True, cancel at end of billing period

        Returns:
            Updated SubscriptionInfo
        """
        try:
            if at_period_end:
                sub = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True,
                )
            else:
                sub = stripe.Subscription.cancel(subscription_id)

            logger.info(f"Cancelled subscription: {subscription_id}")
            return self._subscription_to_info(sub)
        except stripe.StripeError as e:
            logger.error(f"Failed to cancel subscription {subscription_id}: {e}")
            raise

    async def resume_subscription(self, subscription_id: str) -> SubscriptionInfo:
        """
        Resume a subscription that was cancelled but not yet ended.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            Updated SubscriptionInfo
        """
        try:
            sub = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=False,
            )
            logger.info(f"Resumed subscription: {subscription_id}")
            return self._subscription_to_info(sub)
        except stripe.StripeError as e:
            logger.error(f"Failed to resume subscription {subscription_id}: {e}")
            raise

    async def update_subscription(
        self,
        subscription_id: str,
        new_plan: str,
    ) -> SubscriptionInfo:
        """
        Update subscription to a different plan.

        Args:
            subscription_id: Stripe subscription ID
            new_plan: New plan ("monthly" or "yearly")

        Returns:
            Updated SubscriptionInfo
        """
        try:
            price_id = self._get_price_id(new_plan)

            # Get current subscription to find item ID
            sub = stripe.Subscription.retrieve(subscription_id)
            if not sub.items.data:
                raise ValueError("Subscription has no items")

            item_id = sub.items.data[0].id

            updated_sub = stripe.Subscription.modify(
                subscription_id,
                items=[
                    {
                        "id": item_id,
                        "price": price_id,
                    }
                ],
                proration_behavior="always_invoice",
            )

            logger.info(f"Updated subscription {subscription_id} to {new_plan}")
            return self._subscription_to_info(updated_sub)
        except stripe.StripeError as e:
            logger.error(f"Failed to update subscription {subscription_id}: {e}")
            raise

    async def get_invoices(
        self,
        customer_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """
        Get customer invoices.

        Args:
            customer_id: Stripe customer ID
            limit: Max number of invoices

        Returns:
            List of invoice dictionaries
        """
        try:
            invoices = stripe.Invoice.list(customer=customer_id, limit=limit)
            return [
                {
                    "id": inv.id,
                    "number": inv.number,
                    "status": inv.status,
                    "amount_due": inv.amount_due,
                    "amount_paid": inv.amount_paid,
                    "currency": inv.currency,
                    "created": inv.created,
                    "hosted_invoice_url": inv.hosted_invoice_url,
                    "invoice_pdf": inv.invoice_pdf,
                }
                for inv in invoices.data
            ]
        except stripe.StripeError as e:
            logger.error(f"Failed to get invoices for {customer_id}: {e}")
            raise

    def _subscription_to_info(self, sub: Subscription) -> SubscriptionInfo:
        """Convert Stripe Subscription to SubscriptionInfo."""
        price_id = None
        plan = None

        if sub.items.data:
            price_id = sub.items.data[0].price.id
            # Determine plan from price ID
            if price_id == settings.STRIPE_PRICE_ID_MONTHLY:
                plan = "pro"
            elif price_id == settings.STRIPE_PRICE_ID_YEARLY:
                plan = "pro"  # Both monthly and yearly are "pro" plan

        return SubscriptionInfo(
            id=sub.id,
            status=sub.status,
            plan=plan,
            current_period_start=sub.current_period_start,
            current_period_end=sub.current_period_end,
            cancel_at_period_end=sub.cancel_at_period_end,
            price_id=price_id,
        )

    def construct_webhook_event(
        self,
        payload: bytes,
        signature: str,
    ) -> stripe.Event:
        """
        Construct and verify a Stripe webhook event.

        Args:
            payload: Raw request body
            signature: Stripe-Signature header value

        Returns:
            Verified Stripe Event

        Raises:
            ValueError: If signature is invalid
        """
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise ValueError("STRIPE_WEBHOOK_SECRET not configured")

        try:
            return stripe.Webhook.construct_event(
                payload,
                signature,
                settings.STRIPE_WEBHOOK_SECRET,
            )
        except stripe.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise ValueError("Invalid webhook signature") from e


@lru_cache(maxsize=1)
def get_stripe_service() -> StripeService:
    """Get or create the Stripe service singleton."""
    if not settings.stripe_available:
        raise ValueError("Stripe is not configured. Set STRIPE_SECRET_KEY.")
    return StripeService()
