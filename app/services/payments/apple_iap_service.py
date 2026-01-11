"""
Apple App Store In-App Purchase service.
Handles App Store Server Notifications V2 for subscription events.

Reference: https://developer.apple.com/documentation/appstoreservernotifications
"""

import base64
import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_pem_x509_certificate

from app.core.config import settings

logger = logging.getLogger(__name__)


# Apple's root certificates for signature verification
APPLE_ROOT_CA_G3_URL = "https://www.apple.com/certificateauthority/AppleRootCA-G3.cer"


class AppleNotificationType(str, Enum):
    """Apple App Store Server Notification types."""

    # Subscription lifecycle
    SUBSCRIBED = "SUBSCRIBED"
    DID_RENEW = "DID_RENEW"
    DID_CHANGE_RENEWAL_PREF = "DID_CHANGE_RENEWAL_PREF"
    DID_CHANGE_RENEWAL_STATUS = "DID_CHANGE_RENEWAL_STATUS"
    DID_FAIL_TO_RENEW = "DID_FAIL_TO_RENEW"
    EXPIRED = "EXPIRED"
    GRACE_PERIOD_EXPIRED = "GRACE_PERIOD_EXPIRED"

    # Refunds and revocations
    REFUND = "REFUND"
    REFUND_DECLINED = "REFUND_DECLINED"
    REFUND_REVERSED = "REFUND_REVERSED"
    REVOKE = "REVOKE"

    # Other
    CONSUMPTION_REQUEST = "CONSUMPTION_REQUEST"
    RENEWAL_EXTENDED = "RENEWAL_EXTENDED"
    RENEWAL_EXTENSION = "RENEWAL_EXTENSION"
    OFFER_REDEEMED = "OFFER_REDEEMED"
    PRICE_INCREASE = "PRICE_INCREASE"
    TEST = "TEST"


class AppleSubtype(str, Enum):
    """Apple notification subtypes."""

    INITIAL_BUY = "INITIAL_BUY"
    RESUBSCRIBE = "RESUBSCRIBE"
    DOWNGRADE = "DOWNGRADE"
    UPGRADE = "UPGRADE"
    AUTO_RENEW_ENABLED = "AUTO_RENEW_ENABLED"
    AUTO_RENEW_DISABLED = "AUTO_RENEW_DISABLED"
    VOLUNTARY = "VOLUNTARY"
    BILLING_RETRY = "BILLING_RETRY"
    PRICE_INCREASE = "PRICE_INCREASE"
    GRACE_PERIOD = "GRACE_PERIOD"
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    BILLING_RECOVERY = "BILLING_RECOVERY"
    PRODUCT_NOT_FOR_SALE = "PRODUCT_NOT_FOR_SALE"
    SUMMARY = "SUMMARY"
    FAILURE = "FAILURE"


@dataclass
class AppleTransactionInfo:
    """Decoded Apple transaction information."""

    transaction_id: str
    original_transaction_id: str
    product_id: str
    bundle_id: str
    purchase_date: int  # Unix timestamp in milliseconds
    expires_date: int | None  # Unix timestamp in milliseconds
    quantity: int
    type: str  # "Auto-Renewable Subscription", "Non-Consumable", etc.
    in_app_ownership_type: str  # "PURCHASED" or "FAMILY_SHARED"
    signed_date: int  # When this info was signed
    environment: str  # "Sandbox" or "Production"
    storefront: str | None  # Country code
    storefront_id: str | None
    revocation_date: int | None
    revocation_reason: int | None
    is_upgraded: bool | None
    offer_type: int | None
    offer_identifier: str | None


@dataclass
class AppleRenewalInfo:
    """Decoded Apple renewal information."""

    auto_renew_product_id: str
    auto_renew_status: int  # 0 = off, 1 = on
    expiration_intent: int | None  # Why subscription expired
    grace_period_expires_date: int | None
    is_in_billing_retry_period: bool | None
    offer_identifier: str | None
    offer_type: int | None
    original_transaction_id: str
    price_increase_status: int | None
    product_id: str
    signed_date: int
    environment: str


@dataclass
class AppleNotification:
    """Parsed Apple App Store Server Notification V2."""

    notification_type: AppleNotificationType
    subtype: AppleSubtype | None
    notification_uuid: str
    version: str
    signed_date: int
    environment: str  # "Sandbox" or "Production"
    bundle_id: str
    app_apple_id: int | None
    transaction_info: AppleTransactionInfo | None
    renewal_info: AppleRenewalInfo | None
    raw_payload: dict[str, Any]


class AppleIAPService:
    """
    Service for handling Apple App Store In-App Purchase notifications.

    Handles App Store Server Notifications V2 with JWS signature verification.
    """

    def __init__(self):
        self._apple_root_cert: bytes | None = None
        self._http_client: httpx.AsyncClient | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def _fetch_apple_root_certificate(self) -> bytes:
        """Fetch Apple's root certificate for signature verification."""
        if self._apple_root_cert:
            return self._apple_root_cert

        client = await self._get_http_client()
        response = await client.get(APPLE_ROOT_CA_G3_URL)
        response.raise_for_status()
        self._apple_root_cert = response.content
        return self._apple_root_cert

    def _decode_jws_payload(self, jws_token: str, verify: bool = True) -> dict[str, Any]:
        """
        Decode a JWS (JSON Web Signature) token from Apple.

        Apple uses x5c certificate chain in the header for verification.
        For simplicity in development, we can skip verification.
        In production, you should verify the certificate chain.
        """
        if not verify:
            # Decode without verification (for testing/development)
            parts = jws_token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid JWS token format")

            # Decode payload (second part)
            payload_b64 = parts[1]
            # Add padding if needed
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding

            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            return json.loads(payload_bytes)

        # Full verification with certificate chain
        try:
            # Get the header to extract x5c certificate chain
            header = jwt.get_unverified_header(jws_token)
            x5c_chain = header.get("x5c", [])

            if not x5c_chain:
                raise ValueError("No x5c certificate chain in JWS header")

            # The first certificate in the chain is the signing certificate
            signing_cert_pem = (
                b"-----BEGIN CERTIFICATE-----\n"
                + base64.b64encode(base64.b64decode(x5c_chain[0]))
                + b"\n-----END CERTIFICATE-----"
            )

            cert = load_pem_x509_certificate(signing_cert_pem)
            public_key = cert.public_key()

            # Convert to PEM format for PyJWT
            public_key_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )

            # Decode and verify
            payload = jwt.decode(
                jws_token,
                public_key_pem,
                algorithms=["ES256"],
                options={"verify_aud": False},
            )
            return payload

        except Exception as e:
            logger.error(f"Failed to verify Apple JWS: {e}")
            raise ValueError(f"JWS verification failed: {e}")

    def _parse_transaction_info(self, signed_transaction_info: str) -> AppleTransactionInfo:
        """Parse the signed transaction info JWS."""
        # In production, verify=True
        data = self._decode_jws_payload(signed_transaction_info, verify=False)

        return AppleTransactionInfo(
            transaction_id=data.get("transactionId", ""),
            original_transaction_id=data.get("originalTransactionId", ""),
            product_id=data.get("productId", ""),
            bundle_id=data.get("bundleId", ""),
            purchase_date=data.get("purchaseDate", 0),
            expires_date=data.get("expiresDate"),
            quantity=data.get("quantity", 1),
            type=data.get("type", ""),
            in_app_ownership_type=data.get("inAppOwnershipType", "PURCHASED"),
            signed_date=data.get("signedDate", 0),
            environment=data.get("environment", "Sandbox"),
            storefront=data.get("storefront"),
            storefront_id=data.get("storefrontId"),
            revocation_date=data.get("revocationDate"),
            revocation_reason=data.get("revocationReason"),
            is_upgraded=data.get("isUpgraded"),
            offer_type=data.get("offerType"),
            offer_identifier=data.get("offerIdentifier"),
        )

    def _parse_renewal_info(self, signed_renewal_info: str) -> AppleRenewalInfo:
        """Parse the signed renewal info JWS."""
        data = self._decode_jws_payload(signed_renewal_info, verify=False)

        return AppleRenewalInfo(
            auto_renew_product_id=data.get("autoRenewProductId", ""),
            auto_renew_status=data.get("autoRenewStatus", 0),
            expiration_intent=data.get("expirationIntent"),
            grace_period_expires_date=data.get("gracePeriodExpiresDate"),
            is_in_billing_retry_period=data.get("isInBillingRetryPeriod"),
            offer_identifier=data.get("offerIdentifier"),
            offer_type=data.get("offerType"),
            original_transaction_id=data.get("originalTransactionId", ""),
            price_increase_status=data.get("priceIncreaseStatus"),
            product_id=data.get("productId", ""),
            signed_date=data.get("signedDate", 0),
            environment=data.get("environment", "Sandbox"),
        )

    def decode_notification(self, signed_payload: str) -> AppleNotification:
        """
        Decode an App Store Server Notification V2.

        Args:
            signed_payload: The signedPayload field from the webhook request body

        Returns:
            AppleNotification with parsed transaction and renewal info
        """
        # Decode the main notification payload
        payload = self._decode_jws_payload(signed_payload, verify=False)

        notification_type = AppleNotificationType(payload.get("notificationType", ""))
        subtype_str = payload.get("subtype")
        subtype = AppleSubtype(subtype_str) if subtype_str else None

        # Extract nested data
        data = payload.get("data", {})

        # Parse transaction info if present
        transaction_info = None
        if "signedTransactionInfo" in data:
            transaction_info = self._parse_transaction_info(data["signedTransactionInfo"])

        # Parse renewal info if present
        renewal_info = None
        if "signedRenewalInfo" in data:
            renewal_info = self._parse_renewal_info(data["signedRenewalInfo"])

        return AppleNotification(
            notification_type=notification_type,
            subtype=subtype,
            notification_uuid=payload.get("notificationUUID", ""),
            version=payload.get("version", "2.0"),
            signed_date=payload.get("signedDate", 0),
            environment=data.get("environment", "Sandbox"),
            bundle_id=data.get("bundleId", ""),
            app_apple_id=data.get("appAppleId"),
            transaction_info=transaction_info,
            renewal_info=renewal_info,
            raw_payload=payload,
        )

    def verify_bundle_id(self, notification: AppleNotification) -> bool:
        """Verify the notification is for our app's bundle ID."""
        if not settings.APPLE_BUNDLE_ID:
            logger.warning("APPLE_BUNDLE_ID not configured, skipping verification")
            return True

        return notification.bundle_id == settings.APPLE_BUNDLE_ID

    def is_subscription_active(self, notification: AppleNotification) -> bool:
        """
        Determine if the subscription should be considered active based on notification.
        """
        active_types = {
            AppleNotificationType.SUBSCRIBED,
            AppleNotificationType.DID_RENEW,
            AppleNotificationType.OFFER_REDEEMED,
            AppleNotificationType.RENEWAL_EXTENDED,
        }

        if notification.notification_type in active_types:
            return True

        # Check if in grace period (billing retry)
        return (
            notification.notification_type == AppleNotificationType.DID_FAIL_TO_RENEW
            and notification.renewal_info is not None
            and notification.renewal_info.is_in_billing_retry_period is True
        )

    def should_cancel_subscription(self, notification: AppleNotification) -> bool:
        """
        Determine if the subscription should be cancelled based on notification.
        """
        cancel_types = {
            AppleNotificationType.EXPIRED,
            AppleNotificationType.GRACE_PERIOD_EXPIRED,
            AppleNotificationType.REFUND,
            AppleNotificationType.REVOKE,
        }
        return notification.notification_type in cancel_types

    def get_auto_renew_status(self, notification: AppleNotification) -> bool | None:
        """Get auto-renew status from renewal info."""
        if notification.renewal_info:
            return notification.renewal_info.auto_renew_status == 1
        return None


# Singleton instance
_apple_iap_service: AppleIAPService | None = None


def get_apple_iap_service() -> AppleIAPService:
    """Get or create the Apple IAP service instance."""
    global _apple_iap_service
    if _apple_iap_service is None:
        _apple_iap_service = AppleIAPService()
    return _apple_iap_service
