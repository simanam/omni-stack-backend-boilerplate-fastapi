"""
Background job utilities and enqueue functions.
"""

import importlib
import logging
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis

from app.jobs.worker import get_redis_settings

logger = logging.getLogger(__name__)

_pool: ArqRedis | None = None


async def get_job_pool() -> ArqRedis | None:
    """Get or create ARQ connection pool."""
    global _pool

    redis_settings = get_redis_settings()
    if not redis_settings:
        logger.warning("Redis not configured, jobs will not be queued")
        return None

    if _pool is None:
        _pool = await create_pool(redis_settings)

    return _pool


async def close_job_pool() -> None:
    """Close the ARQ connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def enqueue(
    function_name: str,
    *args: Any,
    _job_id: str | None = None,
    _defer_by: int | None = None,
    **kwargs: Any,
) -> Any:
    """
    Enqueue a background job.

    Args:
        function_name: Full dotted path to the job function
        *args: Positional arguments for the job
        _job_id: Optional job ID for deduplication
        _defer_by: Optional delay in seconds before job execution
        **kwargs: Keyword arguments for the job

    Returns:
        Job result if Redis available, or direct execution result if not

    Usage:
        await enqueue(
            "app.jobs.email_jobs.send_welcome_email",
            "user@example.com",
            "John"
        )
    """
    pool = await get_job_pool()

    if pool is None:
        # Fallback: execute synchronously (for development without Redis)
        logger.warning(f"Executing {function_name} synchronously (no Redis)")
        module_path, func_name = function_name.rsplit(".", 1)
        module = importlib.import_module(module_path)
        func = getattr(module, func_name)
        return await func({}, *args, **kwargs)

    return await pool.enqueue_job(
        function_name,
        *args,
        _job_id=_job_id,
        _defer_by=_defer_by,
        **kwargs,
    )


async def enqueue_in(
    function_name: str,
    defer_seconds: int,
    *args: Any,
    _job_id: str | None = None,
    **kwargs: Any,
) -> Any:
    """
    Enqueue a job to run after a delay.

    Args:
        function_name: Full dotted path to the job function
        defer_seconds: Seconds to wait before execution
        *args: Positional arguments for the job
        _job_id: Optional job ID for deduplication
        **kwargs: Keyword arguments for the job
    """
    return await enqueue(
        function_name,
        *args,
        _job_id=_job_id,
        _defer_by=defer_seconds,
        **kwargs,
    )
