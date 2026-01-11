"""
JWT verification and authentication utilities.
Supports RS256 (Supabase/Clerk JWKS) and HS256 (legacy Supabase) algorithms.
"""

from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.core.config import settings

# HTTP Bearer security scheme for OpenAPI docs
security_scheme = HTTPBearer(
    scheme_name="Bearer Token",
    description="JWT token from your auth provider (Supabase/Clerk)",
    auto_error=True,
)


class AuthError(Exception):
    """Custom auth exception for internal use."""

    pass


@lru_cache(maxsize=1)
def get_jwks_client() -> PyJWKClient | None:
    """
    Cached JWKS client for RS256 verification.
    Returns None if using HS256 (legacy Supabase).
    """
    if settings.jwt_algorithm == "RS256" and settings.jwks_url:
        return PyJWKClient(
            settings.jwks_url,
            cache_keys=True,
            lifespan=3600,  # Cache keys for 1 hour
        )
    return None


def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security_scheme),
) -> dict[str, Any]:
    """
    Universal JWT verifier for Supabase, Clerk, or custom OAuth.

    Returns the decoded payload containing user info.
    Raises 401 if token is invalid.
    """
    token = credentials.credentials

    try:
        # Determine signing key based on algorithm
        if settings.jwt_algorithm == "RS256":
            jwks_client = get_jwks_client()
            if not jwks_client:
                raise AuthError("JWKS client not configured")
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            key = signing_key.key
        else:
            # HS256 (legacy Supabase)
            if not settings.SUPABASE_JWT_SECRET:
                raise AuthError("JWT secret not configured")
            key = settings.SUPABASE_JWT_SECRET

        # Decode and verify
        payload = jwt.decode(
            token,
            key=key,
            algorithms=[settings.jwt_algorithm],
            options={
                "verify_aud": False,  # Audience varies by provider
                "verify_iss": False,  # We handle issuer manually if needed
            },
        )

        # Basic validation
        if not payload.get("sub"):
            raise AuthError("Token missing 'sub' claim")

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_id(
    payload: dict[str, Any] = Depends(verify_token),
) -> str:
    """Extract user ID from verified token."""
    return payload["sub"]


def get_token_payload(
    payload: dict[str, Any] = Depends(verify_token),
) -> dict[str, Any]:
    """Return full token payload for additional claims access."""
    return payload


def require_role(required_role: str):
    """
    Dependency factory for role-based access control.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role("admin"))])
        def admin_only(): ...
    """

    def role_checker(payload: dict[str, Any] = Depends(verify_token)):
        # Check common role claim locations across providers
        user_role = (
            payload.get("role")
            or payload.get("user_role")
            or payload.get("app_metadata", {}).get("role")
            or payload.get("public_metadata", {}).get("role")
            or payload.get("user_metadata", {}).get("role")
        )

        if user_role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return payload

    return role_checker


# Convenience dependencies for common roles
require_admin = require_role("admin")
require_superadmin = require_role("superadmin")
