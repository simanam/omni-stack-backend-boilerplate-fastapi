"""
API versioning utilities.

Provides version detection, deprecation headers, and sunset date support.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated

from fastapi import Header, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class APIVersion(str, Enum):
    """Supported API versions."""

    V1 = "v1"
    V2 = "v2"

    @classmethod
    def from_string(cls, version: str) -> "APIVersion":
        """Parse version string to enum."""
        version = version.lower().strip()
        if version in ("v1", "1", "1.0"):
            return cls.V1
        if version in ("v2", "2", "2.0"):
            return cls.V2
        raise ValueError(f"Unknown API version: {version}")

    @property
    def is_deprecated(self) -> bool:
        """Check if this version is deprecated."""
        return self in DEPRECATED_VERSIONS

    @property
    def sunset_date(self) -> datetime | None:
        """Get sunset date for this version if deprecated."""
        return SUNSET_DATES.get(self)


# Configuration for deprecated versions
DEPRECATED_VERSIONS: set[APIVersion] = set()  # Add versions here when deprecated

# Sunset dates for deprecated versions (when they will be removed)
SUNSET_DATES: dict[APIVersion, datetime] = {
    # Example: APIVersion.V1: datetime(2025, 12, 31),
}

# Current/latest API version
CURRENT_VERSION = APIVersion.V2
DEFAULT_VERSION = APIVersion.V1  # For clients that don't specify


def get_version_from_path(path: str) -> APIVersion | None:
    """
    Extract API version from URL path.

    Examples:
        /api/v1/users -> APIVersion.V1
        /api/v2/users -> APIVersion.V2
        /health -> None
    """
    parts = path.lower().split("/")
    for part in parts:
        if part.startswith("v") and part[1:].isdigit():
            try:
                return APIVersion.from_string(part)
            except ValueError:
                continue
    return None


def get_version_from_header(
    accept_version: Annotated[str | None, Header(alias="Accept-Version")] = None,
    api_version: Annotated[str | None, Header(alias="X-API-Version")] = None,
) -> APIVersion | None:
    """
    Get API version from request headers.

    Supports:
        - Accept-Version: v1
        - X-API-Version: v2
    """
    version_str = accept_version or api_version
    if version_str:
        try:
            return APIVersion.from_string(version_str)
        except ValueError:
            return None
    return None


class VersionInfo:
    """Version information for a request."""

    def __init__(
        self,
        version: APIVersion,
        is_deprecated: bool = False,
        sunset_date: datetime | None = None,
        latest_version: APIVersion = CURRENT_VERSION,
    ):
        self.version = version
        self.is_deprecated = is_deprecated
        self.sunset_date = sunset_date
        self.latest_version = latest_version

    @property
    def deprecation_message(self) -> str | None:
        """Get deprecation warning message."""
        if not self.is_deprecated:
            return None
        msg = f"API {self.version.value} is deprecated."
        if self.sunset_date:
            msg += f" It will be removed on {self.sunset_date.strftime('%Y-%m-%d')}."
        msg += f" Please migrate to {self.latest_version.value}."
        return msg


def add_version_headers(response: Response, version_info: VersionInfo) -> None:
    """
    Add version-related headers to response.

    Headers added:
        - X-API-Version: Current API version used
        - X-API-Latest-Version: Latest available version
        - Deprecation: true (if deprecated, RFC 8594)
        - Sunset: date (if sunset date set, RFC 8594)
        - X-Deprecation-Notice: Human-readable message
        - Link: <url>; rel="successor-version" (if deprecated)
    """
    response.headers["X-API-Version"] = version_info.version.value
    response.headers["X-API-Latest-Version"] = version_info.latest_version.value

    if version_info.is_deprecated:
        # RFC 8594 deprecation header
        response.headers["Deprecation"] = "true"

        if version_info.sunset_date:
            # RFC 8594 sunset header (HTTP-date format)
            response.headers["Sunset"] = version_info.sunset_date.strftime(
                "%a, %d %b %Y %H:%M:%S GMT"
            )

        if version_info.deprecation_message:
            response.headers["X-Deprecation-Notice"] = version_info.deprecation_message

        # Link to successor version
        response.headers["Link"] = f'</api/{version_info.latest_version.value}/>; rel="successor-version"'


class VersionMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds version headers to all API responses.

    Detects version from URL path and adds appropriate headers
    including deprecation warnings when applicable.
    """

    # Paths that don't need version headers
    SKIP_PATHS: set[str] = {
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
    }

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Skip non-API paths
        path = request.url.path
        if path in self.SKIP_PATHS or not path.startswith("/api/"):
            return response

        # Detect version from path
        version = get_version_from_path(path)
        if version is None:
            return response

        # Build version info
        version_info = VersionInfo(
            version=version,
            is_deprecated=version.is_deprecated,
            sunset_date=version.sunset_date,
            latest_version=CURRENT_VERSION,
        )

        # Add headers
        add_version_headers(response, version_info)

        return response


# Helper dependency for getting version in endpoints
async def get_api_version(request: Request) -> APIVersion:
    """
    FastAPI dependency to get current API version.

    Priority:
        1. URL path (/api/v1/... or /api/v2/...)
        2. Accept-Version header
        3. X-API-Version header
        4. Default version
    """
    # First try URL path
    path_version = get_version_from_path(request.url.path)
    if path_version:
        return path_version

    # Then try headers
    accept_version = request.headers.get("Accept-Version")
    api_version = request.headers.get("X-API-Version")
    header_version = get_version_from_header(accept_version, api_version)
    if header_version:
        return header_version

    return DEFAULT_VERSION


# Type alias for dependency injection
CurrentAPIVersion = Annotated[APIVersion, get_api_version]
