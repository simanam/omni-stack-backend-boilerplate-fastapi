"""
Database connection and session management.
Supports both traditional connection pooling and serverless (NullPool).
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool
from sqlmodel import SQLModel

from app.core.config import settings


def get_pool_class() -> type[NullPool] | type[AsyncAdaptedQueuePool]:
    """Use NullPool for serverless, QueuePool for traditional."""
    if settings.DB_USE_NULL_POOL:
        return NullPool
    return AsyncAdaptedQueuePool


# Create async engine with appropriate pooling strategy
engine = create_async_engine(
    settings.async_database_url,
    poolclass=get_pool_class(),
    pool_size=settings.DB_POOL_SIZE if not settings.DB_USE_NULL_POOL else 0,
    pool_recycle=settings.DB_POOL_RECYCLE if not settings.DB_USE_NULL_POOL else -1,
    echo=settings.DEBUG,
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
    """Create all tables. Use migrations in production."""
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
