"""
Health check endpoints for API v2.

v2 changes from v1:
- Added version info in response
- Added uptime tracking
- Enhanced component metadata (latency, version info)
- ISO 8601 timestamps with timezone
"""

import time
from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.cache import get_redis
from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.versioning import APIVersion

router = APIRouter(tags=["Health"])

# Track service start time for uptime calculation
SERVICE_START_TIME = time.time()


class ComponentStatusV2(BaseModel):
    """Enhanced component status for v2."""

    status: str = Field(description="Component status: healthy, unhealthy, degraded, not_configured")
    latency_ms: float | None = Field(default=None, description="Response latency in milliseconds")
    version: str | None = Field(default=None, description="Component version if available")
    error: str | None = Field(default=None, description="Error message if unhealthy")


class HealthResponseV2(BaseModel):
    """Enhanced health check response for v2."""

    status: str = Field(description="Service status")
    timestamp: datetime = Field(description="Check timestamp (ISO 8601 with timezone)")
    version: str = Field(description="API version")
    service: str = Field(description="Service name")
    uptime_seconds: float = Field(description="Service uptime in seconds")


class HealthReadyResponseV2(BaseModel):
    """Enhanced readiness check response for v2."""

    status: str = Field(description="Overall status")
    timestamp: datetime = Field(description="Check timestamp (ISO 8601 with timezone)")
    version: str = Field(description="API version")
    service: str = Field(description="Service name")
    environment: str = Field(description="Deployment environment")
    uptime_seconds: float = Field(description="Service uptime in seconds")
    components: dict[str, ComponentStatusV2] = Field(description="Component statuses with metadata")


@router.get(
    "/health",
    response_model=HealthResponseV2,
    summary="Liveness probe (v2)",
    description="Enhanced health check with version and uptime info.",
)
async def health() -> HealthResponseV2:
    """Basic liveness check with enhanced metadata."""
    return HealthResponseV2(
        status="healthy",
        timestamp=datetime.now(UTC),
        version=APIVersion.V2.value,
        service=settings.PROJECT_NAME,
        uptime_seconds=round(time.time() - SERVICE_START_TIME, 2),
    )


@router.get(
    "/health/ready",
    response_model=HealthReadyResponseV2,
    summary="Readiness probe (v2)",
    description="Full readiness check with latency metrics and component versions.",
)
async def health_ready() -> HealthReadyResponseV2:
    """
    Enhanced readiness check with latency metrics and component metadata.
    """
    components: dict[str, ComponentStatusV2] = {}
    overall_status = "healthy"

    # Check database with latency
    db_start = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT version()"))
            db_version = result.scalar()
            db_latency = (time.perf_counter() - db_start) * 1000
            components["database"] = ComponentStatusV2(
                status="healthy",
                latency_ms=round(db_latency, 2),
                version=db_version.split()[0] if db_version else None,
            )
    except Exception as e:
        db_latency = (time.perf_counter() - db_start) * 1000
        components["database"] = ComponentStatusV2(
            status="unhealthy",
            latency_ms=round(db_latency, 2),
            error=str(e),
        )
        overall_status = "unhealthy"

    # Check Redis with latency (optional)
    redis_client = get_redis()
    if redis_client:
        redis_start = time.perf_counter()
        try:
            info = await redis_client.info("server")
            redis_latency = (time.perf_counter() - redis_start) * 1000
            components["redis"] = ComponentStatusV2(
                status="healthy",
                latency_ms=round(redis_latency, 2),
                version=info.get("redis_version"),
            )
        except Exception as e:
            redis_latency = (time.perf_counter() - redis_start) * 1000
            components["redis"] = ComponentStatusV2(
                status="unhealthy",
                latency_ms=round(redis_latency, 2),
                error=str(e),
            )
            overall_status = "degraded" if overall_status == "healthy" else overall_status
    else:
        components["redis"] = ComponentStatusV2(
            status="not_configured",
        )

    return HealthReadyResponseV2(
        status=overall_status,
        timestamp=datetime.now(UTC),
        version=APIVersion.V2.value,
        service=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
        uptime_seconds=round(time.time() - SERVICE_START_TIME, 2),
        components=components,
    )
