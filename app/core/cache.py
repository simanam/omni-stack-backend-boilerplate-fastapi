"""
Redis cache client and utilities.

Supports:
- Standard Redis (production)
- In-memory fallback (offline development)
- Upstash REST API

Phase 12.8: In-memory cache fallback for offline development
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis client instance
redis_client: redis.Redis | None = None


# =============================================================================
# In-Memory Cache Fallback
# =============================================================================


@dataclass
class CacheEntry:
    """Cache entry with optional expiration."""

    value: str
    expires_at: float | None = None

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class InMemoryCache:
    """
    In-memory cache fallback when Redis is unavailable.

    Features:
    - TTL support with expiration
    - Thread-safe for async operations
    - Automatic cleanup of expired entries
    - Hash and set operations for compatibility
    """

    def __init__(self) -> None:
        self._store: dict[str, CacheEntry] = {}
        self._hashes: dict[str, dict[str, str]] = {}
        self._sets: dict[str, set[str]] = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 60  # seconds

    def _maybe_cleanup(self) -> None:
        """Periodically clean up expired entries."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        # Clean up expired string entries
        expired = [k for k, v in self._store.items() if v.is_expired()]
        for key in expired:
            del self._store[key]

        self._last_cleanup = now

    async def get(self, key: str) -> str | None:
        """Get value from cache."""
        self._maybe_cleanup()
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            del self._store[key]
            return None
        return entry.value

    async def set(
        self,
        key: str,
        value: str,
        ex: int | None = None,
    ) -> bool:
        """Set value with optional expiration (seconds)."""
        expires_at = time.time() + ex if ex else None
        self._store[key] = CacheEntry(value=value, expires_at=expires_at)
        return True

    async def delete(self, key: str) -> int:
        """Delete key from cache. Returns 1 if deleted, 0 if not found."""
        if key in self._store:
            del self._store[key]
            return 1
        if key in self._hashes:
            del self._hashes[key]
            return 1
        if key in self._sets:
            del self._sets[key]
            return 1
        return 0

    async def exists(self, key: str) -> int:
        """Check if key exists. Returns 1 if exists, 0 if not."""
        entry = self._store.get(key)
        if entry and not entry.is_expired():
            return 1
        if key in self._hashes or key in self._sets:
            return 1
        return 0

    async def incr(self, key: str) -> int:
        """Increment integer value."""
        entry = self._store.get(key)
        if entry is None or entry.is_expired():
            self._store[key] = CacheEntry(value="1")
            return 1
        new_value = int(entry.value) + 1
        entry.value = str(new_value)
        return new_value

    async def incrby(self, key: str, amount: int) -> int:
        """Increment integer value by amount."""
        entry = self._store.get(key)
        if entry is None or entry.is_expired():
            self._store[key] = CacheEntry(value=str(amount))
            return amount
        new_value = int(entry.value) + amount
        entry.value = str(new_value)
        return new_value

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key."""
        entry = self._store.get(key)
        if entry:
            entry.expires_at = time.time() + seconds
            return True
        return False

    # Hash operations
    async def hset(self, name: str, key: str, value: str) -> int:
        """Set hash field."""
        if name not in self._hashes:
            self._hashes[name] = {}
        is_new = key not in self._hashes[name]
        self._hashes[name][key] = value
        return 1 if is_new else 0

    async def hget(self, name: str, key: str) -> str | None:
        """Get hash field."""
        hash_data = self._hashes.get(name, {})
        return hash_data.get(key)

    async def hgetall(self, name: str) -> dict[str, str]:
        """Get all hash fields."""
        return self._hashes.get(name, {}).copy()

    async def hincrby(self, name: str, key: str, amount: int = 1) -> int:
        """Increment hash field."""
        if name not in self._hashes:
            self._hashes[name] = {}
        current = int(self._hashes[name].get(key, "0"))
        new_value = current + amount
        self._hashes[name][key] = str(new_value)
        return new_value

    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields."""
        if name not in self._hashes:
            return 0
        deleted = 0
        for key in keys:
            if key in self._hashes[name]:
                del self._hashes[name][key]
                deleted += 1
        return deleted

    # Set operations
    async def sadd(self, name: str, *values: str) -> int:
        """Add members to set."""
        if name not in self._sets:
            self._sets[name] = set()
        before = len(self._sets[name])
        self._sets[name].update(values)
        return len(self._sets[name]) - before

    async def smembers(self, name: str) -> set[str]:
        """Get all members of set."""
        return self._sets.get(name, set()).copy()

    async def srem(self, name: str, *values: str) -> int:
        """Remove members from set."""
        if name not in self._sets:
            return 0
        before = len(self._sets[name])
        self._sets[name] -= set(values)
        return before - len(self._sets[name])

    async def scard(self, name: str) -> int:
        """Get cardinality of set."""
        return len(self._sets.get(name, set()))

    # Key scanning
    async def keys(self, pattern: str = "*") -> list[str]:
        """Get keys matching pattern (simple * wildcard only)."""
        all_keys = list(self._store.keys())
        if pattern == "*":
            return all_keys
        # Simple prefix match
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in all_keys if k.startswith(prefix)]
        return [k for k in all_keys if k == pattern]

    async def ping(self) -> bool:
        """Always returns True for in-memory cache."""
        return True

    def clear(self) -> None:
        """Clear all data."""
        self._store.clear()
        self._hashes.clear()
        self._sets.clear()


# Global in-memory cache instance
_memory_cache: InMemoryCache | None = None


def get_memory_cache() -> InMemoryCache:
    """Get or create in-memory cache instance."""
    global _memory_cache
    if _memory_cache is None:
        _memory_cache = InMemoryCache()
    return _memory_cache


# =============================================================================
# Redis Connection Management
# =============================================================================


async def init_redis() -> redis.Redis | InMemoryCache | None:
    """Initialize Redis connection or fallback to in-memory cache."""
    global redis_client

    if not settings.REDIS_URL:
        logger.warning("REDIS_URL not configured, using in-memory cache fallback")
        return get_memory_cache()

    try:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        # Test connection
        await redis_client.ping()
        logger.info("Redis connection established")
        return redis_client
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}, using in-memory cache fallback")
        redis_client = None
        return get_memory_cache()


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
        logger.info("Redis connection closed")


def get_redis() -> redis.Redis | None:
    """Get Redis client instance (None if using in-memory fallback)."""
    return redis_client


def get_cache() -> redis.Redis | InMemoryCache:
    """
    Get cache client - either Redis or in-memory fallback.

    This is the preferred method for getting a cache client as it
    always returns a usable cache interface.
    """
    if redis_client:
        return redis_client
    return get_memory_cache()


def is_redis_available() -> bool:
    """Check if Redis is connected."""
    return redis_client is not None


# =============================================================================
# Cache Helper Functions
# =============================================================================


async def cache_get(key: str) -> str | None:
    """Get value from cache."""
    cache = get_cache()
    try:
        return await cache.get(key)
    except Exception as e:
        logger.error(f"Cache get error: {e}")
        return None


async def cache_set(
    key: str,
    value: str,
    expire: int | None = None,
) -> bool:
    """Set value in cache with optional expiration (seconds)."""
    cache = get_cache()
    try:
        await cache.set(key, value, ex=expire)
        return True
    except Exception as e:
        logger.error(f"Cache set error: {e}")
        return False


async def cache_delete(key: str) -> bool:
    """Delete key from cache."""
    cache = get_cache()
    try:
        await cache.delete(key)
        return True
    except Exception as e:
        logger.error(f"Cache delete error: {e}")
        return False


async def cache_exists(key: str) -> bool:
    """Check if key exists in cache."""
    cache = get_cache()
    try:
        return bool(await cache.exists(key))
    except Exception as e:
        logger.error(f"Cache exists error: {e}")
        return False


async def cache_get_json(key: str) -> Any | None:
    """Get JSON value from cache."""
    value = await cache_get(key)
    if value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return None


async def cache_set_json(
    key: str,
    value: Any,
    expire: int | None = None,
) -> bool:
    """Set JSON value in cache."""
    try:
        json_str = json.dumps(value)
        return await cache_set(key, json_str, expire)
    except (TypeError, ValueError) as e:
        logger.error(f"JSON serialization error: {e}")
        return False
