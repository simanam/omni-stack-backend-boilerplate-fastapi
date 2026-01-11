"""
FastAPI application factory and entry point.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.cache import close_redis, init_redis
from app.core.config import settings
from app.core.exceptions import AppException, app_exception_handler
from app.core.middleware import register_middleware

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.PROJECT_NAME}")
    await close_redis()


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

    # Register exception handlers
    app.add_exception_handler(AppException, app_exception_handler)

    # Include API router
    app.include_router(api_router)

    return app


# Create the application instance
app = create_app()
