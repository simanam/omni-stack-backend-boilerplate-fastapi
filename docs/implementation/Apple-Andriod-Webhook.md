Plan: Add Apple App Store & Google Play Store Webhook Handlers
Overview
Add webhook handlers for Apple App Store Server Notifications (V2) and Google Play Real-time Developer Notifications to support in-app purchases for iOS and Android mobile apps.

Files to Modify/Create

1. Configuration (app/core/config.py)
   Add settings for Apple and Google IAP:

# Apple App Store

APPLE_APP_STORE_SHARED_SECRET: str | None = None # For receipt verification
APPLE_APP_STORE_BUNDLE_ID: str | None = None

# Google Play Store

GOOGLE_PLAY_PACKAGE_NAME: str | None = None
GOOGLE_PLAY_SERVICE_ACCOUNT_JSON: str | None = None # Base64-encoded JSON

# Computed fields for availability checks

apple_iap_available: bool
google_iap_available: bool 2. User Model (app/models/user.py)
Add optional fields for mobile subscribers:

# Apple App Store (for lookup by original_transaction_id)

apple_original_transaction_id: str | None = Field(default=None, index=True)

# Google Play Store (for lookup by purchase token)

google_purchase_token: str | None = Field(default=None, index=True) 3. IAP Services (app/services/payments/)
apple_iap_service.py - Apple Server Notifications V2:

verify_notification(signed_payload) - Verify JWS signature using Apple's public keys
decode_notification(payload) - Extract notification type and transaction info
get_subscription_status(original_transaction_id) - Optional: call App Store Server API
google_iap_service.py - Google Real-time Developer Notifications:

verify_pub_sub_message(message) - Verify Pub/Sub signature
decode_notification(data) - Extract notification type and subscription info
get_subscription_status(purchase_token) - Call Google Play Developer API 4. IAP Business Logic (app/business/iap_service.py)

class IAPService:
async def handle_apple_notification(session, notification) -> User | None
async def handle_google_notification(session, notification) -> User | None
async def sync_subscription_from_apple(session, user, transaction_info)
async def sync_subscription_from_google(session, user, subscription_info) 5. Webhook Endpoints (app/api/v1/public/webhooks.py)
Apple endpoint - POST /api/v1/public/webhooks/apple:

Events: SUBSCRIBED, DID_RENEW, DID_CHANGE_RENEWAL_STATUS, EXPIRED, REFUND, REVOKE, DID_FAIL_TO_RENEW
Verification: Decode JWS signed payload, verify with Apple's public keys
Google endpoint - POST /api/v1/public/webhooks/google:

Events: SUBSCRIPTION_PURCHASED, SUBSCRIPTION_RENEWED, SUBSCRIPTION_CANCELED, SUBSCRIPTION_EXPIRED, SUBSCRIPTION_REVOKED
Verification: Verify Pub/Sub message authenticity 6. Database Migration
New migration for User model fields:

apple_original_transaction_id (indexed)
google_purchase_token (indexed) 7. Tests
tests/unit/test_apple_iap.py - Apple notification verification and handling
tests/unit/test_google_iap.py - Google notification verification and handling
Update tests/unit/test_webhooks.py - Add Apple/Google webhook endpoint tests 8. Documentation Updates
phase-8-payments.md - Add 8.11 Apple IAP, 8.12 Google IAP sections
.env.example - Add Apple/Google credentials
Apple App Store Server Notifications V2 Details
Notification Format: JWS (JSON Web Signature) with payload:

{
"signedPayload": "eyJ...", // JWS containing notification
}
Decoded Payload Structure:

{
"notificationType": "DID_RENEW",
"notificationUUID": "unique-id",
"data": {
"signedTransactionInfo": "eyJ...", // JWS with transaction details
"signedRenewalInfo": "eyJ..." // JWS with renewal details
}
}
Key Events:

Event Description Action
SUBSCRIBED New subscription Set status=active, plan=pro
DID_RENEW Successful renewal Keep status=active
DID_CHANGE_RENEWAL_STATUS Auto-renew toggled Update cancel_at_period_end
EXPIRED Subscription ended Set status=expired, plan=free
REFUND Refund issued Set status=refunded, plan=free
REVOKE Family sharing revoked Set status=revoked, plan=free
Google Play Real-time Developer Notifications
Pub/Sub Message Format:

{
"message": {
"data": "base64-encoded-json",
"messageId": "123",
"publishTime": "2024-01-10T..."
},
"subscription": "projects/.../subscriptions/..."
}
Decoded Data:

{
"version": "1.0",
"packageName": "com.example.app",
"eventTimeMillis": "1234567890",
"subscriptionNotification": {
"notificationType": 4, // SUBSCRIPTION_RENEWED
"purchaseToken": "token...",
"subscriptionId": "premium_monthly"
}
}
Notification Types:

Type Value Description Action
SUBSCRIPTION_RECOVERED 1 Account recovered status=active
SUBSCRIPTION_RENEWED 2 Renewed status=active
SUBSCRIPTION_CANCELED 3 Canceled cancel_at_period_end=true
SUBSCRIPTION_PURCHASED 4 New purchase status=active, plan=pro
SUBSCRIPTION_EXPIRED 13 Expired status=expired, plan=free
SUBSCRIPTION_REVOKED 12 Revoked/refunded status=revoked, plan=free
Implementation Order
Add config settings (config.py)
Add user model fields + migration
Create Apple IAP service
Create Google IAP service
Create IAP business logic service
Add webhook endpoints
Write tests
Update documentation
Dependencies

# Apple JWS verification

PyJWT = "^2.8.0" # Already in project
cryptography = "..." # Already in project (for ES256)

# Google Play API

google-auth = "^2.27.0"
google-api-python-client = "^2.115.0"
Verification
Unit tests: Run pytest tests/unit/test_apple_iap.py tests/unit/test_google_iap.py
Integration tests: Run pytest tests/unit/test_webhooks.py -k "apple or google"
Manual testing:
Apple: Use App Store Connect sandbox notifications
Google: Use Google Play Console test notifications
Linting: Run make lint
User approved the plan
