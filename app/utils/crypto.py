"""
Cryptographic utilities for hashing, token generation, and HMAC verification.
"""

import hashlib
import hmac
import secrets
from base64 import b64decode, b64encode

# =============================================================================
# Secure Token Generation
# =============================================================================


def generate_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.

    Args:
        length: Number of random bytes (output will be 2x length in hex)

    Returns:
        Hex-encoded random string
    """
    return secrets.token_hex(length)


def generate_urlsafe_token(length: int = 32) -> str:
    """
    Generate a URL-safe random token.

    Args:
        length: Number of random bytes

    Returns:
        URL-safe base64 encoded string
    """
    return secrets.token_urlsafe(length)


def generate_api_key(prefix: str = "sk") -> str:
    """
    Generate an API key with prefix.

    Args:
        prefix: Key prefix (e.g., 'sk' for secret key, 'pk' for public key)

    Returns:
        Formatted API key like 'sk_live_abc123...'
    """
    token = secrets.token_urlsafe(24)
    return f"{prefix}_live_{token}"


# =============================================================================
# HMAC Signature Verification
# =============================================================================


def compute_hmac(
    payload: str | bytes,
    secret: str | bytes,
    algorithm: str = "sha256",
) -> str:
    """
    Compute HMAC signature for payload.

    Args:
        payload: Data to sign
        secret: Secret key
        algorithm: Hash algorithm (sha256, sha512, etc.)

    Returns:
        Hex-encoded HMAC signature
    """
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    if isinstance(secret, str):
        secret = secret.encode("utf-8")

    return hmac.new(secret, payload, algorithm).hexdigest()


def verify_hmac(
    payload: str | bytes,
    signature: str,
    secret: str | bytes,
    algorithm: str = "sha256",
) -> bool:
    """
    Verify HMAC signature using constant-time comparison.

    Args:
        payload: Original data
        signature: Signature to verify (hex-encoded)
        secret: Secret key
        algorithm: Hash algorithm

    Returns:
        True if signature is valid
    """
    expected = compute_hmac(payload, secret, algorithm)
    return hmac.compare_digest(expected, signature)


def verify_webhook_signature(
    payload: bytes,
    signature_header: str,
    secret: str,
    prefix: str = "sha256=",
) -> bool:
    """
    Verify webhook signature (commonly used by GitHub, Stripe, etc.).

    Args:
        payload: Raw request body
        signature_header: Value from signature header
        secret: Webhook secret
        prefix: Signature prefix (e.g., 'sha256=')

    Returns:
        True if signature is valid
    """
    if not signature_header.startswith(prefix):
        return False

    provided_signature = signature_header[len(prefix) :]
    return verify_hmac(payload, provided_signature, secret)


# =============================================================================
# Hashing Utilities
# =============================================================================


def hash_sha256(data: str | bytes) -> str:
    """
    Compute SHA-256 hash.

    Args:
        data: Data to hash

    Returns:
        Hex-encoded hash
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def hash_sha512(data: str | bytes) -> str:
    """
    Compute SHA-512 hash.

    Args:
        data: Data to hash

    Returns:
        Hex-encoded hash
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha512(data).hexdigest()


def hash_md5(data: str | bytes) -> str:
    """
    Compute MD5 hash (NOT for security, only checksums).

    Args:
        data: Data to hash

    Returns:
        Hex-encoded hash
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.md5(data).hexdigest()


# =============================================================================
# Password Hashing (if not using external auth)
# =============================================================================

# Note: For production password hashing, use argon2-cffi or bcrypt.
# This is a simple implementation using PBKDF2 (built into Python).

HASH_ALGORITHM = "sha256"
HASH_ITERATIONS = 600_000  # OWASP 2023 recommendation
SALT_LENGTH = 32


def hash_password(password: str) -> str:
    """
    Hash password using PBKDF2-SHA256.
    Returns a string containing salt and hash for storage.

    Args:
        password: Plain text password

    Returns:
        Formatted string: 'algorithm$iterations$salt$hash'
    """
    salt = secrets.token_bytes(SALT_LENGTH)
    hash_bytes = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode("utf-8"),
        salt,
        HASH_ITERATIONS,
    )

    salt_b64 = b64encode(salt).decode("ascii")
    hash_b64 = b64encode(hash_bytes).decode("ascii")

    return f"pbkdf2_{HASH_ALGORITHM}${HASH_ITERATIONS}${salt_b64}${hash_b64}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verify password against stored hash using constant-time comparison.

    Args:
        password: Plain text password to verify
        stored_hash: Hash from hash_password()

    Returns:
        True if password matches
    """
    try:
        parts = stored_hash.split("$")
        if len(parts) != 4:
            return False

        algorithm_part, iterations_str, salt_b64, hash_b64 = parts

        # Extract algorithm
        if not algorithm_part.startswith("pbkdf2_"):
            return False
        algorithm = algorithm_part[7:]  # Remove 'pbkdf2_' prefix

        iterations = int(iterations_str)
        salt = b64decode(salt_b64)
        stored_hash_bytes = b64decode(hash_b64)

        # Compute hash with same parameters
        computed_hash = hashlib.pbkdf2_hmac(
            algorithm,
            password.encode("utf-8"),
            salt,
            iterations,
        )

        # Constant-time comparison
        return hmac.compare_digest(computed_hash, stored_hash_bytes)

    except Exception:
        return False


# =============================================================================
# Encoding Utilities
# =============================================================================


def base64_encode(data: str | bytes) -> str:
    """Encode data to base64 string."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return b64encode(data).decode("ascii")


def base64_decode(data: str) -> bytes:
    """Decode base64 string to bytes."""
    return b64decode(data)
