"""
Resilience patterns: Circuit breaker, retry with backoff, timeouts.
"""

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Circuit Breaker
# =============================================================================


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes in half-open before closing
    timeout: float = 30.0  # Seconds before trying again (half-open)
    excluded_exceptions: tuple = ()  # Exceptions that don't count as failures


@dataclass
class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by stopping requests to failing services.
    After a timeout, allows a few test requests through (half-open state).
    If those succeed, closes the circuit; if they fail, opens it again.
    """

    name: str
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)

    # Internal state
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _success_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is allowing requests."""
        return self._state == CircuitState.CLOSED

    async def _should_allow_request(self) -> bool:
        """Determine if request should be allowed based on state."""
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            # Check if timeout has passed
            if time.time() - self._last_failure_time >= self.config.timeout:
                async with self._lock:
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                    logger.info(f"Circuit {self.name}: OPEN -> HALF_OPEN")
                return True
            return False

        # HALF_OPEN: allow request for testing
        return True

    async def _record_success(self) -> None:
        """Record successful request."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info(f"Circuit {self.name}: HALF_OPEN -> CLOSED")
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    async def _record_failure(self, exc: Exception) -> None:
        """Record failed request."""
        # Check if exception should be excluded
        if isinstance(exc, self.config.excluded_exceptions):
            return

        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # Failed during test, reopen circuit
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit {self.name}: HALF_OPEN -> OPEN (test failed)")
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(
                        f"Circuit {self.name}: CLOSED -> OPEN "
                        f"(failures: {self._failure_count})"
                    )

    async def call[T](self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """
        Execute function through circuit breaker.

        Raises:
            CircuitOpenError: If circuit is open
        """
        if not await self._should_allow_request():
            raise CircuitOpenError(f"Circuit {self.name} is OPEN")

        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure(e)
            raise


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""

    pass


# Global circuit breaker registry
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    config: CircuitBreakerConfig | None = None,
) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            name=name,
            config=config or CircuitBreakerConfig(),
        )
    return _circuit_breakers[name]


# =============================================================================
# Retry with Exponential Backoff
# =============================================================================


@dataclass
class RetryConfig:
    """Retry configuration."""

    max_attempts: int = 3
    base_delay: float = 1.0  # Initial delay in seconds
    max_delay: float = 60.0  # Maximum delay
    exponential_base: float = 2.0  # Multiplier for each retry
    jitter: bool = True  # Add randomness to prevent thundering herd
    retryable_exceptions: tuple = (Exception,)  # Exceptions to retry


async def retry_async[T](
    func: Callable[..., Awaitable[T]],
    *args,
    config: RetryConfig | None = None,
    **kwargs,
) -> T:
    """
    Execute async function with retry logic.

    Args:
        func: Async function to call
        *args: Positional arguments for func
        config: Retry configuration
        **kwargs: Keyword arguments for func

    Returns:
        Result of func

    Raises:
        Last exception if all retries exhausted
    """
    config = config or RetryConfig()
    last_exception: Exception | None = None

    for attempt in range(1, config.max_attempts + 1):
        try:
            return await func(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e

            if attempt == config.max_attempts:
                logger.warning(
                    f"Retry exhausted after {attempt} attempts: {e}",
                )
                raise

            # Calculate delay with exponential backoff
            delay = min(
                config.base_delay * (config.exponential_base ** (attempt - 1)),
                config.max_delay,
            )

            # Add jitter (0.5 to 1.5 times delay)
            if config.jitter:
                delay = delay * (0.5 + random.random())

            logger.info(
                f"Retry attempt {attempt}/{config.max_attempts} "
                f"after {delay:.2f}s: {e}"
            )
            await asyncio.sleep(delay)

    # Should not reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry failed without exception")


def with_retry[T](config: RetryConfig | None = None):
    """
    Decorator for async functions with retry logic.

    Usage:
        @with_retry(RetryConfig(max_attempts=5))
        async def fetch_data():
            ...
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_async(func, *args, config=config, **kwargs)

        return wrapper

    return decorator


# =============================================================================
# Timeout
# =============================================================================


class TimeoutError(Exception):
    """Raised when operation times out."""

    pass


async def with_timeout[T](
    func: Callable[..., Awaitable[T]],
    *args,
    timeout: float,
    **kwargs,
) -> T:
    """
    Execute async function with timeout.

    Args:
        func: Async function to call
        *args: Positional arguments
        timeout: Timeout in seconds
        **kwargs: Keyword arguments

    Returns:
        Result of func

    Raises:
        TimeoutError: If operation exceeds timeout
    """
    try:
        return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
    except TimeoutError:
        raise TimeoutError(f"Operation timed out after {timeout}s")


def timeout[T](seconds: float):
    """
    Decorator for async functions with timeout.

    Usage:
        @timeout(30.0)
        async def slow_operation():
            ...
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await with_timeout(func, *args, timeout=seconds, **kwargs)

        return wrapper

    return decorator


# =============================================================================
# Fallback
# =============================================================================


async def with_fallback[T](
    func: Callable[..., Awaitable[T]],
    fallback_func: Callable[..., Awaitable[T]] | Callable[..., T],
    *args,
    **kwargs,
) -> T:
    """
    Execute function with fallback on failure.

    Args:
        func: Primary async function
        fallback_func: Fallback function (sync or async)
        *args: Arguments passed to both functions
        **kwargs: Keyword arguments passed to both functions

    Returns:
        Result from primary or fallback function
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Primary function failed, using fallback: {e}")
        result = fallback_func(*args, **kwargs)
        if asyncio.iscoroutine(result):
            return await result
        return result


# =============================================================================
# Combined Patterns
# =============================================================================


async def resilient_call[T](
    func: Callable[..., Awaitable[T]],
    *args,
    circuit_breaker: CircuitBreaker | None = None,
    retry_config: RetryConfig | None = None,
    timeout_seconds: float | None = None,
    fallback: Callable[..., Any] | None = None,
    **kwargs,
) -> T:
    """
    Execute function with all resilience patterns combined.

    Execution order:
    1. Circuit breaker check
    2. Timeout wrapper
    3. Retry logic
    4. Fallback on final failure

    Args:
        func: Async function to call
        circuit_breaker: Optional circuit breaker
        retry_config: Optional retry configuration
        timeout_seconds: Optional timeout
        fallback: Optional fallback function
        *args, **kwargs: Arguments for func

    Returns:
        Result of func or fallback
    """

    async def wrapped_call() -> T:
        call = func

        # Apply timeout if configured
        if timeout_seconds:

            async def timed_call(*a, **kw):
                return await with_timeout(func, *a, timeout=timeout_seconds, **kw)

            call = timed_call

        # Apply retry if configured
        if retry_config:
            return await retry_async(call, *args, config=retry_config, **kwargs)
        return await call(*args, **kwargs)

    try:
        # Apply circuit breaker if configured
        if circuit_breaker:
            return await circuit_breaker.call(wrapped_call)
        return await wrapped_call()

    except Exception as e:
        # Apply fallback if configured
        if fallback:
            logger.warning(f"All attempts failed, using fallback: {e}")
            result = fallback(*args, **kwargs)
            if asyncio.iscoroutine(result):
                return await result
            return result
        raise
