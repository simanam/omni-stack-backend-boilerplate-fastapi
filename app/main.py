"""
FastAPI application factory and entry point.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.api.v2.router import api_v2_router
from app.core.cache import close_redis, init_redis
from app.core.config import settings
from app.core.exceptions import AppException, app_exception_handler
from app.core.logging import get_logger, setup_logging
from app.core.middleware import register_middleware
from app.core.sentry import init_sentry
from app.core.tracing import (
    init_tracing,
    instrument_app,
    instrument_httpx,
    instrument_redis,
    shutdown_tracing,
)
from app.core.versioning import VersionMiddleware
from app.services.websocket import connection_manager

# Configure structured logging
setup_logging()
logger = get_logger(__name__)

# Initialize Sentry (if configured)
init_sentry()

# Initialize OpenTelemetry tracing (if configured)
init_tracing()

# Instrument httpx and redis globally (before app creation)
instrument_httpx()
instrument_redis()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.
    Manages startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.PROJECT_NAME} ({settings.ENVIRONMENT})")

    # Initialize Redis (optional)
    await init_redis()

    # Start WebSocket connection manager
    await connection_manager.start()

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.PROJECT_NAME}")

    # Stop WebSocket connection manager
    await connection_manager.stop()

    await close_redis()

    # Shutdown OpenTelemetry (flush pending spans)
    shutdown_tracing()


def create_app() -> FastAPI:
    """
    Application factory.
    Creates and configures the FastAPI application.
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Production-ready FastAPI backend boilerplate for SaaS applications",
        version="0.1.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
        if settings.ENVIRONMENT != "production"
        else None,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # Add CORS middleware (must be added before other middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
    )

    # Register custom middleware (rate limiting, security headers, request ID, logging)
    register_middleware(app)

    # Add version middleware for deprecation headers
    app.add_middleware(VersionMiddleware)

    # Register exception handlers
    app.add_exception_handler(AppException, app_exception_handler)

    # Include API routers (v1 and v2)
    app.include_router(api_router)
    app.include_router(api_v2_router)

    # Instrument FastAPI with OpenTelemetry (after adding routes)
    instrument_app(app)

    return app


# Create the application instance
app = create_app()
