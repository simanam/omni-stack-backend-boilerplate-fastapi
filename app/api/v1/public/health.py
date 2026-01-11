"""
Health check endpoints for liveness and readiness probes.
"""

from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import text

from app.core.cache import get_redis
from app.core.db import AsyncSessionLocal
from app.schemas.common import HealthReadyResponse, HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Basic health check to verify the service is running.",
)
async def health() -> HealthResponse:
    """Basic liveness check - returns 200 if service is running."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
    )


@router.get(
    "/health/ready",
    response_model=HealthReadyResponse,
    summary="Readiness probe",
    description="Full readiness check including database and cache connectivity.",
)
async def health_ready() -> HealthReadyResponse:
    """
    Readiness check that verifies all dependencies are available.
    Checks database and Redis connectivity.
    """
    components: dict[str, dict[str, str]] = {}
    overall_status = "healthy"

    # Check database
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            components["database"] = {"status": "healthy"}
    except Exception as e:
        components["database"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "unhealthy"

    # Check Redis (optional)
    redis_client = get_redis()
    if redis_client:
        try:
            await redis_client.ping()
            components["redis"] = {"status": "healthy"}
        except Exception as e:
            components["redis"] = {"status": "unhealthy", "error": str(e)}
            overall_status = "degraded" if overall_status == "healthy" else overall_status
    else:
        components["redis"] = {"status": "not_configured"}

    return HealthReadyResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        components=components,
    )
