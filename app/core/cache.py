"""
Redis cache client and utilities.
Supports both standard Redis and Upstash REST API.
"""

import logging
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis client instance
redis_client: redis.Redis | None = None


async def init_redis() -> redis.Redis | None:
    """Initialize Redis connection."""
    global redis_client

    if not settings.REDIS_URL:
        logger.warning("REDIS_URL not configured, cache disabled")
        return None

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
        logger.error(f"Failed to connect to Redis: {e}")
        redis_client = None
        return None


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
        logger.info("Redis connection closed")


def get_redis() -> redis.Redis | None:
    """Get Redis client instance."""
    return redis_client


async def cache_get(key: str) -> str | None:
    """Get value from cache."""
    if not redis_client:
        return None
    try:
        return await redis_client.get(key)
    except Exception as e:
        logger.error(f"Cache get error: {e}")
        return None


async def cache_set(
    key: str,
    value: str,
    expire: int | None = None,
) -> bool:
    """Set value in cache with optional expiration (seconds)."""
    if not redis_client:
        return False
    try:
        await redis_client.set(key, value, ex=expire)
        return True
    except Exception as e:
        logger.error(f"Cache set error: {e}")
        return False


async def cache_delete(key: str) -> bool:
    """Delete key from cache."""
    if not redis_client:
        return False
    try:
        await redis_client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Cache delete error: {e}")
        return False


async def cache_exists(key: str) -> bool:
    """Check if key exists in cache."""
    if not redis_client:
        return False
    try:
        return bool(await redis_client.exists(key))
    except Exception as e:
        logger.error(f"Cache exists error: {e}")
        return False


async def cache_get_json(key: str) -> Any | None:
    """Get JSON value from cache."""
    import json

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
    import json

    try:
        json_str = json.dumps(value)
        return await cache_set(key, json_str, expire)
    except (TypeError, ValueError) as e:
        logger.error(f"JSON serialization error: {e}")
        return False
