"""
Payments service package.
Provides Stripe integration for subscriptions and billing,
plus Apple App Store and Google Play Store for mobile in-app purchases.
"""

from app.services.payments.apple_iap_service import (
    AppleIAPService,
    AppleNotification,
    AppleNotificationType,
    get_apple_iap_service,
)
from app.services.payments.google_iap_service import (
    GoogleIAPService,
    GoogleNotification,
    GoogleNotificationType,
    GoogleSubscriptionNotification,
    get_google_iap_service,
)
from app.services.payments.stripe_service import (
    StripeService,
    get_stripe_service,
)

__all__ = [
    # Stripe
    "StripeService",
    "get_stripe_service",
    # Apple
    "AppleIAPService",
    "AppleNotification",
    "AppleNotificationType",
    "get_apple_iap_service",
    # Google
    "GoogleIAPService",
    "GoogleNotification",
    "GoogleNotificationType",
    "GoogleSubscriptionNotification",
    "get_google_iap_service",
]
