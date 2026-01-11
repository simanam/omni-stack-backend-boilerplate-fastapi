"""
Input validation and sanitization utilities.
"""

import html
import re
from typing import Annotated
from urllib.parse import urlparse
from uuid import UUID

from pydantic import AfterValidator, BeforeValidator

__all__ = [
    "validate_email",
    "ValidatedEmail",
    "validate_url",
    "ValidatedURL",
    "validate_uuid",
    "ValidatedUUID",
    "sanitize_html",
    "strip_html_tags",
    "SanitizedString",
    "PlainTextString",
    "validate_safe_path",
    "SafePath",
    "max_length",
    "min_length",
    "validate_file_type",
    "is_valid_image",
    "is_valid_document",
    "ALLOWED_IMAGE_TYPES",
    "ALLOWED_DOCUMENT_TYPES",
]

# Ensure UUID is used to avoid F401
_uuid_type = UUID


# =============================================================================
# Email Validation
# =============================================================================

# RFC 5322 compliant email regex (simplified but practical)
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)


def validate_email(value: str) -> str:
    """
    Validate email format.
    Raises ValueError if invalid.
    """
    if not value:
        raise ValueError("Email cannot be empty")

    value = value.strip().lower()

    if len(value) > 254:  # RFC 5321 limit
        raise ValueError("Email too long (max 254 characters)")

    if not EMAIL_REGEX.match(value):
        raise ValueError("Invalid email format")

    return value


# Pydantic annotated type for email validation
ValidatedEmail = Annotated[str, AfterValidator(validate_email)]


# =============================================================================
# URL Validation
# =============================================================================

ALLOWED_URL_SCHEMES = {"http", "https"}


def validate_url(value: str) -> str:
    """
    Validate URL format and scheme.
    Raises ValueError if invalid.
    """
    if not value:
        raise ValueError("URL cannot be empty")

    value = value.strip()

    try:
        parsed = urlparse(value)

        if not parsed.scheme:
            raise ValueError("URL must include scheme (http:// or https://)")

        if parsed.scheme not in ALLOWED_URL_SCHEMES:
            raise ValueError(f"URL scheme must be one of: {ALLOWED_URL_SCHEMES}")

        if not parsed.netloc:
            raise ValueError("URL must include domain")

        return value
    except Exception as e:
        raise ValueError(f"Invalid URL: {e}")


ValidatedURL = Annotated[str, AfterValidator(validate_url)]


# =============================================================================
# UUID Validation
# =============================================================================


def validate_uuid(value: str) -> str:
    """
    Validate UUID format.
    Raises ValueError if invalid.
    """
    if not value:
        raise ValueError("UUID cannot be empty")

    try:
        # Attempt to parse as UUID
        uuid_obj = UUID(value)
        # Return normalized lowercase format
        return str(uuid_obj)
    except (ValueError, AttributeError):
        raise ValueError("Invalid UUID format")


ValidatedUUID = Annotated[str, AfterValidator(validate_uuid)]


# =============================================================================
# String Sanitization
# =============================================================================


def sanitize_html(value: str) -> str:
    """
    Escape HTML special characters to prevent XSS.
    Use this for user-provided content that will be displayed.
    """
    if not value:
        return value
    return html.escape(value, quote=True)


def strip_html_tags(value: str) -> str:
    """
    Remove all HTML tags from string.
    Use this when you want plain text only.
    """
    if not value:
        return value
    # Simple regex to strip HTML tags
    clean = re.sub(r"<[^>]+>", "", value)
    # Also decode HTML entities
    return html.unescape(clean)


SanitizedString = Annotated[str, BeforeValidator(sanitize_html)]
PlainTextString = Annotated[str, BeforeValidator(strip_html_tags)]


# =============================================================================
# Path Traversal Prevention
# =============================================================================

PATH_TRAVERSAL_PATTERNS = [
    "..",
    "./",
    ".\\",
    "%2e%2e",
    "%252e%252e",
    "..%c0%af",
    "..%c1%9c",
]


def validate_safe_path(value: str) -> str:
    """
    Validate that path doesn't contain traversal attacks.
    Raises ValueError if suspicious patterns detected.
    """
    if not value:
        raise ValueError("Path cannot be empty")

    value_lower = value.lower()

    for pattern in PATH_TRAVERSAL_PATTERNS:
        if pattern in value_lower:
            raise ValueError("Path contains invalid characters")

    # Check for null bytes
    if "\x00" in value:
        raise ValueError("Path contains invalid characters")

    return value


SafePath = Annotated[str, AfterValidator(validate_safe_path)]


# =============================================================================
# String Length Validators
# =============================================================================


def max_length(max_len: int):
    """
    Create a validator that enforces maximum string length.

    Usage:
        name: Annotated[str, AfterValidator(max_length(100))]
    """

    def validator(value: str) -> str:
        if value and len(value) > max_len:
            raise ValueError(f"String too long (max {max_len} characters)")
        return value

    return validator


def min_length(min_len: int):
    """
    Create a validator that enforces minimum string length.

    Usage:
        password: Annotated[str, AfterValidator(min_length(8))]
    """

    def validator(value: str) -> str:
        if not value or len(value) < min_len:
            raise ValueError(f"String too short (min {min_len} characters)")
        return value

    return validator


# =============================================================================
# File Type Validation
# =============================================================================

# Common MIME types and their allowed extensions
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/gif": [".gif"],
    "image/webp": [".webp"],
}

ALLOWED_DOCUMENT_TYPES = {
    "application/pdf": [".pdf"],
    "application/msword": [".doc"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "text/plain": [".txt"],
    "text/csv": [".csv"],
}


def validate_file_type(
    filename: str,
    content_type: str,
    allowed_types: dict[str, list[str]],
) -> bool:
    """
    Validate file type based on extension and content type.

    Args:
        filename: Original filename
        content_type: MIME type from upload
        allowed_types: Dict mapping MIME types to allowed extensions

    Returns:
        True if valid, raises ValueError otherwise
    """
    if not filename or not content_type:
        raise ValueError("Filename and content type required")

    # Check content type
    if content_type not in allowed_types:
        allowed = ", ".join(allowed_types.keys())
        raise ValueError(f"File type not allowed. Allowed types: {allowed}")

    # Check extension matches content type
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed_extensions = allowed_types[content_type]

    if ext not in allowed_extensions:
        raise ValueError("File extension doesn't match content type")

    return True


def is_valid_image(filename: str, content_type: str) -> bool:
    """Validate that file is an allowed image type."""
    return validate_file_type(filename, content_type, ALLOWED_IMAGE_TYPES)


def is_valid_document(filename: str, content_type: str) -> bool:
    """Validate that file is an allowed document type."""
    return validate_file_type(filename, content_type, ALLOWED_DOCUMENT_TYPES)
