# Phase 8: Payments & Webhooks ✅

**Duration:** Monetization phase
**Goal:** Implement Stripe integration with subscriptions, mobile IAP (Apple/Google), and webhook handling
**Status:** Complete (12/12 tasks)

**Prerequisites:** Phase 1-7 completed

---

## 8.1 Stripe Service ✅

### Files created:
- [x] `app/services/payments/__init__.py`
- [x] `app/services/payments/stripe_service.py`

### Checklist:
- [x] Initialize Stripe client
- [x] `create_customer(user)` — Create Stripe customer
- [x] `get_customer(stripe_customer_id)` — Retrieve customer
- [x] `create_checkout_session(customer_id, price_id)` — Start checkout
- [x] `create_portal_session(customer_id)` — Billing portal
- [x] `get_subscription(subscription_id)` — Get subscription details
- [x] `cancel_subscription(subscription_id)` — Cancel subscription
- [x] `update_subscription(subscription_id, price_id)` — Change plan
- [x] Error handling and logging

### Validation:
- [x] Can create customers
- [x] Checkout sessions work
- [x] Portal sessions work

---

## 8.2 Subscription Management ✅

### Files created:
- [x] `app/business/billing_service.py`

### Checklist:
- [x] `get_or_create_customer(user)` — Ensure user has Stripe customer
- [x] `start_checkout(user, plan)` — Start subscription flow
- [x] `get_billing_portal_url(user)` — Get portal URL
- [x] `sync_subscription_status(user)` — Sync from Stripe
- [x] `get_current_plan(user)` — Get user's plan
- [x] Feature gating via `app/core/feature_flags.py`

### Plans:
- [x] Free tier (default)
- [x] Pro tier (monthly/yearly)
- [x] Enterprise (unlimited)

### Validation:
- [x] Subscription sync works
- [x] Feature gating works

---

## 8.3 Billing API Endpoints ✅

### Files created:
- [x] `app/api/v1/app/billing.py`

### Checklist:
- [x] `GET /api/v1/app/billing/status` — Current subscription status
- [x] `POST /api/v1/app/billing/checkout` — Start checkout
  - [x] Accept plan selection (monthly/yearly)
  - [x] Return checkout URL
- [x] `GET /api/v1/app/billing/portal` — Get portal URL
- [x] `GET /api/v1/app/billing/invoices` — List invoices
- [x] `POST /api/v1/app/billing/cancel` — Cancel subscription
- [x] `POST /api/v1/app/billing/resume` — Resume cancelled subscription

### Validation:
- [x] All endpoints work
- [x] Requires authentication

---

## 8.4 Webhook Infrastructure ✅

### Files created:
- [x] `app/api/v1/public/webhooks.py` — Webhook handlers

### Checklist:
- [x] Webhook signature verification (Stripe native)
- [x] Idempotency key tracking (prevent duplicate processing)
- [x] Webhook event logging (WebhookEvent model)
- [x] Error handling with proper responses

### Validation:
- [x] Signatures verified
- [x] Duplicate events ignored

---

## 8.5 Stripe Webhook Handler ✅

### Files updated:
- [x] `app/api/v1/public/webhooks.py`

### Events handled:
- [x] `checkout.session.completed` — New subscription
- [x] `customer.subscription.updated` — Plan change
- [x] `customer.subscription.deleted` — Cancellation
- [x] `invoice.paid` — Successful payment
- [x] `invoice.payment_failed` — Failed payment
- [x] `customer.created` — New customer

### Checklist:
- [x] Verify Stripe signature
- [x] Parse event type
- [x] Route to appropriate handler
- [x] Update user subscription status
- [x] Return 200 quickly

### Validation:
- [x] All events processed correctly
- [x] User status updated in database

---

## 8.6 Clerk Webhook Handler ✅

### Files updated:
- [x] `app/api/v1/public/webhooks.py`

### Events handled:
- [x] `user.created` — New user signup
- [x] `user.updated` — Profile update
- [x] `user.deleted` — User deletion
- [x] `session.created` — New login (logged)

### Checklist:
- [x] Verify Clerk signature (svix headers)
- [x] Create/update user in database
- [x] Handle user deletion (soft delete via is_active=False)

### Validation:
- [x] User sync works
- [x] Signatures verified

---

## 8.7 Supabase Webhook Handler ✅

### Files updated:
- [x] `app/api/v1/public/webhooks.py`

### Events handled:
- [x] INSERT on auth.users — User created
- [x] UPDATE on auth.users — User updated
- [x] DELETE on auth.users — User deleted

### Checklist:
- [x] Verify webhook secret (Bearer token)
- [x] Process auth events
- [x] Update local user records

### Validation:
- [x] Events processed correctly

---

## 8.8 Generic Webhook Handler ✅

### Implementation:
- [x] Idempotency tracking via WebhookEvent model
- [x] HMAC signature verification available via `app/utils/crypto.py`
- [x] Event type routing per provider
- [x] Duplicate event detection

### Validation:
- [x] Custom webhooks can be added easily

---

## 8.9 Webhook Event Model ✅

### Files created:
- [x] `app/models/webhook_event.py`
- [x] `migrations/versions/20260110_210000_add_webhook_event_model.py`

### Checklist:
- [x] Store webhook events:
  - [x] `id` (UUID)
  - [x] `provider` (stripe, clerk, supabase, custom)
  - [x] `event_type`
  - [x] `idempotency_key` (unique)
  - [x] `payload` (JSONB)
  - [x] `status` (pending, processing, processed, failed)
  - [x] `error_message`
  - [x] `processed_at`
  - [x] `attempts`
- [x] Index on idempotency_key (unique)

### Validation:
- [x] Events stored correctly
- [x] Duplicate detection works

---

## 8.10 Subscription Feature Gates ✅

### Files created:
- [x] `app/core/feature_flags.py`

### Checklist:
- [x] Define features per plan:
  ```python
  PLAN_LIMITS = {
      "free": PlanLimits(api_calls=1000, ai_requests=50, storage_mb=100, projects=3, team_members=1),
      "pro": PlanLimits(api_calls=50000, ai_requests=2000, storage_mb=10000, projects=50, team_members=10),
      "enterprise": PlanLimits(api_calls=-1, ai_requests=-1, storage_mb=-1, projects=-1, team_members=-1),
  }
  ```
- [x] `check_feature_limit(user, feature)` — Check if user can use feature
- [x] `increment_usage(user, feature)` — Track usage (Redis-backed)
- [x] `get_remaining(user, feature)` — Get remaining quota
- [x] Reset usage monthly (TTL-based in Redis)

### Validation:
- [x] Limits enforced correctly
- [x] Usage tracked
- [x] Resets work (monthly TTL)

---

## 8.11 Apple App Store In-App Purchases ✅

### Files created:
- [x] `app/services/payments/apple_iap_service.py`
- [x] `app/business/iap_service.py`

### Checklist:
- [x] Decode App Store Server Notifications V2 (JWS)
- [x] Parse transaction and renewal info
- [x] Handle notification types:
  - [x] `SUBSCRIBED` — New subscription
  - [x] `DID_RENEW` — Subscription renewed
  - [x] `DID_CHANGE_RENEWAL_STATUS` — Auto-renew toggled
  - [x] `EXPIRED` — Subscription expired
  - [x] `REFUND` — Refund issued
  - [x] `REVOKE` — Family sharing revoked
- [x] Bundle ID verification
- [x] Subscription status sync

### Validation:
- [x] Notifications decoded correctly
- [x] User subscription updated

---

## 8.12 Google Play Store In-App Purchases ✅

### Files created:
- [x] `app/services/payments/google_iap_service.py`
- [x] `app/business/iap_service.py` (shared with Apple)

### Checklist:
- [x] Decode Pub/Sub messages
- [x] Parse subscription notifications
- [x] Handle notification types:
  - [x] `SUBSCRIPTION_PURCHASED` — New subscription
  - [x] `SUBSCRIPTION_RENEWED` — Subscription renewed
  - [x] `SUBSCRIPTION_CANCELED` — Subscription canceled
  - [x] `SUBSCRIPTION_EXPIRED` — Subscription expired
  - [x] `SUBSCRIPTION_REVOKED` — Refund/revoke
- [x] Package name verification
- [x] Subscription status sync

### Validation:
- [x] Notifications decoded correctly
- [x] User subscription updated

---

## Phase 8 Completion Criteria ✅

- [x] Stripe customers created for users
- [x] Checkout flow works
- [x] Billing portal accessible
- [x] Stripe webhooks processed
- [x] User subscription status synced
- [x] Clerk webhooks sync users
- [x] Supabase webhooks sync users
- [x] Feature gates enforce plan limits
- [x] Webhook events logged for debugging
- [x] Apple App Store notifications processed
- [x] Google Play Store notifications processed

---

## Files Created in Phase 8

| File | Purpose |
|------|---------|
| `app/services/payments/__init__.py` | Package exports |
| `app/services/payments/stripe_service.py` | Stripe API wrapper |
| `app/services/payments/apple_iap_service.py` | Apple App Store notifications |
| `app/services/payments/google_iap_service.py` | Google Play Store notifications |
| `app/business/billing_service.py` | Stripe billing business logic |
| `app/business/iap_service.py` | Mobile IAP business logic |
| `app/api/v1/app/billing.py` | Billing endpoints |
| `app/api/v1/public/webhooks.py` | Webhook handlers (Stripe, Clerk, Supabase, Apple, Google) |
| `app/models/webhook_event.py` | Event storage model |
| `app/core/feature_flags.py` | Feature gates |
| `migrations/versions/20260110_210000_add_webhook_event_model.py` | Webhook events table |
| `migrations/versions/20260110_220000_add_mobile_iap_fields.py` | Mobile IAP user fields |

---

## API Endpoints Added

### Billing (requires auth)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/app/billing/status` | Current subscription status |
| POST | `/api/v1/app/billing/checkout` | Start Stripe checkout |
| GET | `/api/v1/app/billing/portal` | Get billing portal URL |
| GET | `/api/v1/app/billing/invoices` | List invoices |
| POST | `/api/v1/app/billing/cancel` | Cancel subscription |
| POST | `/api/v1/app/billing/resume` | Resume subscription |

### Webhooks (public)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/public/webhooks/stripe` | Stripe payment events |
| POST | `/api/v1/public/webhooks/clerk` | Clerk user events |
| POST | `/api/v1/public/webhooks/supabase` | Supabase auth events |

---

## Configuration

```bash
# Required for Stripe
STRIPE_SECRET_KEY=""           # sk_test_... or sk_live_...
STRIPE_WEBHOOK_SECRET=""       # whsec_... from Stripe Dashboard
STRIPE_PRICE_ID_MONTHLY=""     # price_... for monthly subscription
STRIPE_PRICE_ID_YEARLY=""      # price_... for yearly subscription

# Webhook URLs to configure:
# Stripe: https://your-domain.com/api/v1/public/webhooks/stripe
# Clerk:  https://your-domain.com/api/v1/public/webhooks/clerk
```

---

*Completed: 2026-01-10*
