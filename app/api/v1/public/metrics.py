"""
Prometheus metrics endpoint.
Provides /metrics endpoint for Prometheus scraping.
"""

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Response

from app.core.config import settings
from app.core.metrics import PROMETHEUS_AVAILABLE, get_metrics

router = APIRouter(tags=["Metrics"])


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="Returns Prometheus-formatted metrics. Optionally protected with a bearer token.",
    responses={
        200: {
            "description": "Prometheus metrics",
            "content": {"text/plain": {}},
        },
        401: {"description": "Unauthorized - invalid or missing token"},
        503: {"description": "Prometheus client not available"},
    },
)
async def get_prometheus_metrics(
    authorization: Annotated[str | None, Header()] = None,
) -> Response:
    """
    Get Prometheus metrics.

    In production, this endpoint can be protected with a bearer token
    by setting METRICS_TOKEN environment variable.
    """
    # Check if prometheus client is available
    if not PROMETHEUS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Prometheus client not installed. Run: pip install prometheus-client",
        )

    # Optional token-based auth for metrics endpoint
    # This is useful to prevent public access to metrics in production
    metrics_token = getattr(settings, "METRICS_TOKEN", None)
    if metrics_token and settings.ENVIRONMENT == "production":
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail="Authorization header required",
            )
        # Expect "Bearer <token>" format
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header format",
            )
        if parts[1] != metrics_token:
            raise HTTPException(
                status_code=401,
                detail="Invalid metrics token",
            )

    # Generate metrics
    metrics_output, content_type = get_metrics()

    return Response(
        content=metrics_output,
        media_type=content_type,
    )


@router.get(
    "/metrics/health",
    summary="Metrics Health Check",
    description="Check if Prometheus metrics are available.",
    responses={
        200: {"description": "Metrics available"},
        503: {"description": "Metrics not available"},
    },
)
async def metrics_health() -> dict[str, str | bool]:
    """Check if metrics system is healthy."""
    return {
        "status": "healthy" if PROMETHEUS_AVAILABLE else "unavailable",
        "prometheus_available": PROMETHEUS_AVAILABLE,
        "environment": settings.ENVIRONMENT,
    }
