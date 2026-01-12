"""
Database connection and session management.

Supports:
- PostgreSQL with asyncpg (production)
- SQLite with aiosqlite (offline development)
- Traditional connection pooling and serverless (NullPool)

Phase 12.8: SQLite Fallback for offline development
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool, StaticPool
from sqlmodel import SQLModel

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_engine_options() -> dict[str, Any]:
    """
    Get engine options based on database type.

    SQLite requires special handling:
    - StaticPool for connection sharing (required for aiosqlite)
    - check_same_thread=False for multi-threaded access
    """
    if settings.is_sqlite:
        logger.info("Using SQLite database (offline development mode)")
        return {
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
            "echo": settings.DEBUG,
        }

    # PostgreSQL options
    pool_class = NullPool if settings.DB_USE_NULL_POOL else AsyncAdaptedQueuePool
    options: dict[str, Any] = {
        "poolclass": pool_class,
        "echo": settings.DEBUG,
    }

    # Only add pool settings for non-NullPool
    if not settings.DB_USE_NULL_POOL:
        options["pool_size"] = settings.DB_POOL_SIZE
        options["pool_recycle"] = settings.DB_POOL_RECYCLE

    return options


# Create async engine with appropriate settings
engine = create_async_engine(
    settings.async_database_url,
    **get_engine_options(),
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db() -> None:
    """
    Create all tables.

    Use migrations in production with PostgreSQL.
    For SQLite (offline dev), this creates the schema directly.
    """
    if settings.is_sqlite:
        logger.info("Initializing SQLite database schema")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for use outside of FastAPI dependencies."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def is_sqlite() -> bool:
    """Check if using SQLite database."""
    return settings.is_sqlite
