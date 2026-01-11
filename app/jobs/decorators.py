"""
Job helper decorators for background tasks.
"""

import asyncio
import functools
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class RetryConfig:
    """Configuration for job retry behavior."""

    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0


def retry(config: RetryConfig | None = None) -> Callable[[F], F]:
    """
    Decorator for automatic job retry with exponential backoff.

    Args:
        config: RetryConfig with retry parameters

    Usage:
        @retry(RetryConfig(max_attempts=5))
        async def my_job(ctx, arg1, arg2):
            ...
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < config.max_attempts:
                        delay = min(
                            config.initial_delay * (config.exponential_base ** (attempt - 1)),
                            config.max_delay,
                        )
                        logger.warning(
                            f"Job {func.__name__} failed (attempt {attempt}/{config.max_attempts}), "
                            f"retrying in {delay:.1f}s: {e}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"Job {func.__name__} failed after {config.max_attempts} attempts: {e}"
                        )

            if last_exception:
                raise last_exception

        return wrapper  # type: ignore

    return decorator


def timeout(seconds: float) -> Callable[[F], F]:
    """
    Decorator to set a timeout for job execution.

    Args:
        seconds: Maximum execution time in seconds

    Usage:
        @timeout(60.0)
        async def my_job(ctx, arg1, arg2):
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds,
                )
            except TimeoutError:
                logger.error(f"Job {func.__name__} timed out after {seconds}s")
                raise

        return wrapper  # type: ignore

    return decorator


def background_task(
    *,
    max_attempts: int = 1,
    timeout_seconds: float | None = None,
) -> Callable[[F], F]:
    """
    Combined decorator to mark a function as a background task.

    Args:
        max_attempts: Number of retry attempts (1 = no retry)
        timeout_seconds: Optional timeout in seconds

    Usage:
        @background_task(max_attempts=3, timeout_seconds=300)
        async def my_job(ctx, arg1, arg2):
            ...
    """

    def decorator(func: F) -> F:
        wrapped = func

        # Apply retry if max_attempts > 1
        if max_attempts > 1:
            wrapped = retry(RetryConfig(max_attempts=max_attempts))(wrapped)

        # Apply timeout if specified
        if timeout_seconds is not None:
            wrapped = timeout(timeout_seconds)(wrapped)

        # Mark as background task
        wrapped._is_background_task = True  # type: ignore
        wrapped._max_attempts = max_attempts  # type: ignore
        wrapped._timeout_seconds = timeout_seconds  # type: ignore

        return wrapped  # type: ignore

    return decorator
