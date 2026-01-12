"""
Payments service package.
Provides Stripe integration for subscriptions and billing,
plus Apple App Store and Google Play Store for mobile in-app purchases,
and usage-based billing tracking (Phase 12.7).
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
from app.services.payments.usage import (
    StripeUsageReporter,
    UsageEvent,
    UsageMetric,
    UsageSummary,
    UsageTracker,
    UsageTrend,
    get_stripe_usage_reporter,
    get_usage_tracker,
    track_ai_usage,
    track_api_request,
    track_storage,
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
    # Usage Tracking (Phase 12.7)
    "UsageTracker",
    "UsageMetric",
    "UsageEvent",
    "UsageSummary",
    "UsageTrend",
    "get_usage_tracker",
    "StripeUsageReporter",
    "get_stripe_usage_reporter",
    "track_api_request",
    "track_ai_usage",
    "track_storage",
]
