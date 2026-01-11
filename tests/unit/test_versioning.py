"""
Unit tests for API versioning utilities.

Tests cover:
- Version enum parsing
- Path-based version detection
- Header-based version detection
- Deprecation headers
- Version middleware
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request, Response
from starlette.testclient import TestClient

from app.core.versioning import (
    CURRENT_VERSION,
    DEFAULT_VERSION,
    DEPRECATED_VERSIONS,
    SUNSET_DATES,
    APIVersion,
    VersionInfo,
    VersionMiddleware,
    add_version_headers,
    get_api_version,
    get_version_from_header,
    get_version_from_path,
)


class TestAPIVersionEnum:
    """Tests for APIVersion enum."""

    def test_v1_value(self):
        """v1 has correct string value."""
        assert APIVersion.V1.value == "v1"

    def test_v2_value(self):
        """v2 has correct string value."""
        assert APIVersion.V2.value == "v2"

    def test_from_string_v1(self):
        """Parse v1 from various formats."""
        assert APIVersion.from_string("v1") == APIVersion.V1
        assert APIVersion.from_string("V1") == APIVersion.V1
        assert APIVersion.from_string("1") == APIVersion.V1
        assert APIVersion.from_string("1.0") == APIVersion.V1

    def test_from_string_v2(self):
        """Parse v2 from various formats."""
        assert APIVersion.from_string("v2") == APIVersion.V2
        assert APIVersion.from_string("V2") == APIVersion.V2
        assert APIVersion.from_string("2") == APIVersion.V2
        assert APIVersion.from_string("2.0") == APIVersion.V2

    def test_from_string_invalid(self):
        """Invalid version strings raise ValueError."""
        with pytest.raises(ValueError, match="Unknown API version"):
            APIVersion.from_string("v3")
        with pytest.raises(ValueError, match="Unknown API version"):
            APIVersion.from_string("invalid")

    def test_from_string_with_whitespace(self):
        """Version strings with whitespace are handled."""
        assert APIVersion.from_string("  v1  ") == APIVersion.V1
        assert APIVersion.from_string("\nv2\t") == APIVersion.V2

    def test_is_deprecated_v1_not_deprecated(self):
        """v1 is not deprecated by default."""
        # Clear any test modifications
        DEPRECATED_VERSIONS.discard(APIVersion.V1)
        assert APIVersion.V1.is_deprecated is False

    def test_is_deprecated_when_in_set(self):
        """Version is deprecated when in DEPRECATED_VERSIONS set."""
        DEPRECATED_VERSIONS.add(APIVersion.V1)
        try:
            assert APIVersion.V1.is_deprecated is True
        finally:
            DEPRECATED_VERSIONS.discard(APIVersion.V1)

    def test_sunset_date_none_by_default(self):
        """Sunset date is None when not configured."""
        # Clear any test modifications
        SUNSET_DATES.pop(APIVersion.V1, None)
        assert APIVersion.V1.sunset_date is None

    def test_sunset_date_when_configured(self):
        """Sunset date is returned when configured."""
        sunset = datetime(2025, 12, 31)
        SUNSET_DATES[APIVersion.V1] = sunset
        try:
            assert APIVersion.V1.sunset_date == sunset
        finally:
            SUNSET_DATES.pop(APIVersion.V1, None)


class TestGetVersionFromPath:
    """Tests for get_version_from_path function."""

    def test_v1_path(self):
        """Extract v1 from path."""
        assert get_version_from_path("/api/v1/users") == APIVersion.V1
        assert get_version_from_path("/api/v1/public/health") == APIVersion.V1

    def test_v2_path(self):
        """Extract v2 from path."""
        assert get_version_from_path("/api/v2/users") == APIVersion.V2
        assert get_version_from_path("/api/v2/public/health") == APIVersion.V2

    def test_no_version_in_path(self):
        """Return None when no version in path."""
        assert get_version_from_path("/health") is None
        assert get_version_from_path("/docs") is None
        assert get_version_from_path("/") is None

    def test_case_insensitive(self):
        """Path detection is case insensitive."""
        assert get_version_from_path("/API/V1/users") == APIVersion.V1
        assert get_version_from_path("/Api/V2/Users") == APIVersion.V2

    def test_version_anywhere_in_path(self):
        """Version can be anywhere in path."""
        assert get_version_from_path("/v1/api/users") == APIVersion.V1
        assert get_version_from_path("/prefix/api/v2/suffix") == APIVersion.V2


class TestGetVersionFromHeader:
    """Tests for get_version_from_header function."""

    def test_accept_version_header(self):
        """Parse Accept-Version header."""
        assert get_version_from_header(accept_version="v1") == APIVersion.V1
        assert get_version_from_header(accept_version="v2") == APIVersion.V2

    def test_x_api_version_header(self):
        """Parse X-API-Version header."""
        assert get_version_from_header(api_version="v1") == APIVersion.V1
        assert get_version_from_header(api_version="v2") == APIVersion.V2

    def test_accept_version_takes_precedence(self):
        """Accept-Version takes precedence over X-API-Version."""
        result = get_version_from_header(accept_version="v1", api_version="v2")
        assert result == APIVersion.V1

    def test_no_headers(self):
        """Return None when no headers provided."""
        assert get_version_from_header() is None

    def test_invalid_header_value(self):
        """Return None for invalid header values."""
        assert get_version_from_header(accept_version="invalid") is None
        assert get_version_from_header(api_version="v99") is None


class TestVersionInfo:
    """Tests for VersionInfo class."""

    def test_deprecation_message_not_deprecated(self):
        """No deprecation message when not deprecated."""
        info = VersionInfo(version=APIVersion.V1, is_deprecated=False)
        assert info.deprecation_message is None

    def test_deprecation_message_deprecated(self):
        """Deprecation message when deprecated."""
        info = VersionInfo(
            version=APIVersion.V1,
            is_deprecated=True,
            latest_version=APIVersion.V2,
        )
        assert info.deprecation_message is not None
        assert "v1 is deprecated" in info.deprecation_message
        assert "v2" in info.deprecation_message

    def test_deprecation_message_with_sunset(self):
        """Deprecation message includes sunset date."""
        sunset = datetime(2025, 12, 31)
        info = VersionInfo(
            version=APIVersion.V1,
            is_deprecated=True,
            sunset_date=sunset,
            latest_version=APIVersion.V2,
        )
        assert "2025-12-31" in info.deprecation_message


class TestAddVersionHeaders:
    """Tests for add_version_headers function."""

    def test_adds_version_headers(self):
        """Adds X-API-Version and X-API-Latest-Version."""
        response = Response()
        info = VersionInfo(version=APIVersion.V1, latest_version=APIVersion.V2)

        add_version_headers(response, info)

        assert response.headers["X-API-Version"] == "v1"
        assert response.headers["X-API-Latest-Version"] == "v2"

    def test_no_deprecation_headers_when_not_deprecated(self):
        """No deprecation headers when not deprecated."""
        response = Response()
        info = VersionInfo(version=APIVersion.V1, is_deprecated=False)

        add_version_headers(response, info)

        assert "Deprecation" not in response.headers
        assert "Sunset" not in response.headers

    def test_adds_deprecation_header(self):
        """Adds Deprecation header when deprecated."""
        response = Response()
        info = VersionInfo(
            version=APIVersion.V1,
            is_deprecated=True,
            latest_version=APIVersion.V2,
        )

        add_version_headers(response, info)

        assert response.headers["Deprecation"] == "true"
        assert "X-Deprecation-Notice" in response.headers
        assert "Link" in response.headers
        assert 'rel="successor-version"' in response.headers["Link"]

    def test_adds_sunset_header(self):
        """Adds Sunset header with date."""
        response = Response()
        sunset = datetime(2025, 12, 31, 12, 0, 0)
        info = VersionInfo(
            version=APIVersion.V1,
            is_deprecated=True,
            sunset_date=sunset,
            latest_version=APIVersion.V2,
        )

        add_version_headers(response, info)

        assert "Sunset" in response.headers
        assert "31 Dec 2025" in response.headers["Sunset"]


class TestVersionMiddleware:
    """Tests for VersionMiddleware."""

    @pytest.fixture
    def app_with_middleware(self):
        """Create test app with version middleware."""
        app = FastAPI()
        app.add_middleware(VersionMiddleware)

        @app.get("/api/v1/test")
        async def v1_test():
            return {"version": "v1"}

        @app.get("/api/v2/test")
        async def v2_test():
            return {"version": "v2"}

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        return app

    def test_adds_version_headers_v1(self, app_with_middleware):
        """Adds version headers for v1 requests."""
        client = TestClient(app_with_middleware)
        response = client.get("/api/v1/test")

        assert response.status_code == 200
        assert response.headers["X-API-Version"] == "v1"
        assert response.headers["X-API-Latest-Version"] == "v2"

    def test_adds_version_headers_v2(self, app_with_middleware):
        """Adds version headers for v2 requests."""
        client = TestClient(app_with_middleware)
        response = client.get("/api/v2/test")

        assert response.status_code == 200
        assert response.headers["X-API-Version"] == "v2"
        assert response.headers["X-API-Latest-Version"] == "v2"

    def test_skips_non_api_paths(self, app_with_middleware):
        """Skips version headers for non-API paths."""
        client = TestClient(app_with_middleware)
        response = client.get("/health")

        assert response.status_code == 200
        assert "X-API-Version" not in response.headers

    def test_deprecation_headers_when_deprecated(self, app_with_middleware):
        """Adds deprecation headers when version is deprecated."""
        DEPRECATED_VERSIONS.add(APIVersion.V1)
        try:
            client = TestClient(app_with_middleware)
            response = client.get("/api/v1/test")

            assert response.status_code == 200
            assert response.headers["Deprecation"] == "true"
            assert "X-Deprecation-Notice" in response.headers
        finally:
            DEPRECATED_VERSIONS.discard(APIVersion.V1)


class TestGetApiVersionDependency:
    """Tests for get_api_version dependency."""

    @pytest.mark.asyncio
    async def test_version_from_path(self):
        """Gets version from URL path."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/users"
        request.headers = {}

        version = await get_api_version(request)
        assert version == APIVersion.V1

    @pytest.mark.asyncio
    async def test_version_from_header_when_no_path(self):
        """Falls back to header when no version in path."""
        request = MagicMock(spec=Request)
        request.url.path = "/users"
        # Use MagicMock for headers to allow .get() method
        headers_mock = MagicMock()
        headers_mock.get = MagicMock(side_effect=lambda k: "v2" if k == "Accept-Version" else None)
        request.headers = headers_mock

        version = await get_api_version(request)
        assert version == APIVersion.V2

    @pytest.mark.asyncio
    async def test_default_version(self):
        """Returns default version when not specified."""
        request = MagicMock(spec=Request)
        request.url.path = "/users"
        # Use MagicMock for headers to allow .get() method
        headers_mock = MagicMock()
        headers_mock.get = MagicMock(return_value=None)
        request.headers = headers_mock

        version = await get_api_version(request)
        assert version == DEFAULT_VERSION


class TestConstants:
    """Tests for module constants."""

    def test_current_version_is_v2(self):
        """Current version is v2."""
        assert CURRENT_VERSION == APIVersion.V2

    def test_default_version_is_v1(self):
        """Default version is v1."""
        assert DEFAULT_VERSION == APIVersion.V1

    def test_deprecated_versions_is_set(self):
        """DEPRECATED_VERSIONS is a set."""
        assert isinstance(DEPRECATED_VERSIONS, set)

    def test_sunset_dates_is_dict(self):
        """SUNSET_DATES is a dict."""
        assert isinstance(SUNSET_DATES, dict)
