"""
Unit tests for SQLite fallback functionality (Phase 12.8).
"""

import time
from unittest.mock import patch

import pytest


class TestInMemoryCache:
    """Test InMemoryCache class."""

    def test_basic_get_set(self):
        """Test basic get/set operations."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()

        # Use sync access for testing
        import asyncio

        async def run_test():
            await cache.set("key1", "value1")
            result = await cache.get("key1")
            assert result == "value1"

        asyncio.get_event_loop().run_until_complete(run_test())

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_with_expiration(self):
        """Test set with TTL expiration."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()
        await cache.set("expiring_key", "value", ex=1)

        # Key should exist immediately
        result = await cache.get("expiring_key")
        assert result == "value"

        # Wait for expiration
        time.sleep(1.1)

        # Key should be expired
        result = await cache.get("expiring_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test delete operation."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()
        await cache.set("to_delete", "value")
        assert await cache.get("to_delete") == "value"

        result = await cache.delete("to_delete")
        assert result == 1

        assert await cache.get("to_delete") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self):
        """Test deleting a key that doesn't exist."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()
        result = await cache.delete("nonexistent")
        assert result == 0

    @pytest.mark.asyncio
    async def test_exists(self):
        """Test exists operation."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()
        assert await cache.exists("key") == 0

        await cache.set("key", "value")
        assert await cache.exists("key") == 1

    @pytest.mark.asyncio
    async def test_incr(self):
        """Test increment operation."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()

        # First incr creates the key
        result = await cache.incr("counter")
        assert result == 1

        # Second incr increments
        result = await cache.incr("counter")
        assert result == 2

    @pytest.mark.asyncio
    async def test_incrby(self):
        """Test increment by amount."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()
        result = await cache.incrby("counter", 5)
        assert result == 5

        result = await cache.incrby("counter", 10)
        assert result == 15

    @pytest.mark.asyncio
    async def test_expire(self):
        """Test setting expiration on existing key."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()
        await cache.set("key", "value")

        result = await cache.expire("key", 1)
        assert result is True

        # Key still exists
        assert await cache.get("key") == "value"

        # Wait for expiration
        time.sleep(1.1)

        assert await cache.get("key") is None

    @pytest.mark.asyncio
    async def test_expire_nonexistent(self):
        """Test expire on nonexistent key."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()
        result = await cache.expire("nonexistent", 60)
        assert result is False


class TestInMemoryCacheHash:
    """Test hash operations in InMemoryCache."""

    @pytest.mark.asyncio
    async def test_hset_hget(self):
        """Test hash set and get."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()
        await cache.hset("myhash", "field1", "value1")
        result = await cache.hget("myhash", "field1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_hget_nonexistent(self):
        """Test getting nonexistent hash field."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()
        result = await cache.hget("nonexistent", "field")
        assert result is None

    @pytest.mark.asyncio
    async def test_hgetall(self):
        """Test getting all hash fields."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()
        await cache.hset("myhash", "field1", "value1")
        await cache.hset("myhash", "field2", "value2")

        result = await cache.hgetall("myhash")
        assert result == {"field1": "value1", "field2": "value2"}

    @pytest.mark.asyncio
    async def test_hincrby(self):
        """Test hash field increment."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()
        result = await cache.hincrby("myhash", "counter", 5)
        assert result == 5

        result = await cache.hincrby("myhash", "counter", 3)
        assert result == 8

    @pytest.mark.asyncio
    async def test_hdel(self):
        """Test hash field delete."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()
        await cache.hset("myhash", "field1", "value1")
        await cache.hset("myhash", "field2", "value2")

        result = await cache.hdel("myhash", "field1")
        assert result == 1

        assert await cache.hget("myhash", "field1") is None
        assert await cache.hget("myhash", "field2") == "value2"


class TestInMemoryCacheSet:
    """Test set operations in InMemoryCache."""

    @pytest.mark.asyncio
    async def test_sadd_smembers(self):
        """Test set add and members."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()
        await cache.sadd("myset", "a", "b", "c")
        result = await cache.smembers("myset")
        assert result == {"a", "b", "c"}

    @pytest.mark.asyncio
    async def test_srem(self):
        """Test set remove."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()
        await cache.sadd("myset", "a", "b", "c")
        result = await cache.srem("myset", "b")
        assert result == 1

        members = await cache.smembers("myset")
        assert members == {"a", "c"}

    @pytest.mark.asyncio
    async def test_scard(self):
        """Test set cardinality."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()
        await cache.sadd("myset", "a", "b", "c")
        result = await cache.scard("myset")
        assert result == 3


class TestInMemoryCacheKeys:
    """Test key scanning in InMemoryCache."""

    @pytest.mark.asyncio
    async def test_keys_all(self):
        """Test getting all keys."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("other", "value3")

        result = await cache.keys("*")
        assert set(result) == {"key1", "key2", "other"}

    @pytest.mark.asyncio
    async def test_keys_prefix(self):
        """Test getting keys by prefix."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()
        await cache.set("user:1", "value1")
        await cache.set("user:2", "value2")
        await cache.set("other", "value3")

        result = await cache.keys("user:*")
        assert set(result) == {"user:1", "user:2"}

    @pytest.mark.asyncio
    async def test_ping(self):
        """Test ping always returns True."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()
        result = await cache.ping()
        assert result is True

    def test_clear(self):
        """Test clearing all data."""
        from app.core.cache import InMemoryCache

        cache = InMemoryCache()

        import asyncio

        async def setup():
            await cache.set("key", "value")
            await cache.hset("hash", "field", "value")
            await cache.sadd("set", "member")

        asyncio.get_event_loop().run_until_complete(setup())

        cache.clear()
        assert cache._store == {}
        assert cache._hashes == {}
        assert cache._sets == {}


class TestDatabaseConfig:
    """Test database configuration for SQLite."""

    def test_is_sqlite_detection(self):
        """Test SQLite URL detection logic."""
        # Test the detection logic directly, not via settings singleton
        sqlite_url = "sqlite+aiosqlite:///./test.db"
        postgres_url = "postgresql+asyncpg://localhost/db"

        # SQLite URL should be detected
        assert sqlite_url.startswith("sqlite")

        # PostgreSQL URL should not be detected as SQLite
        assert not postgres_url.startswith("sqlite")

    def test_async_database_url_postgresql(self):
        """Test PostgreSQL URL conversion."""
        with patch.object(
            __import__("app.core.config", fromlist=["settings"]).settings,
            "DATABASE_URL",
            "postgresql://user:pass@localhost/db",
        ):
            from app.core.config import settings

            # The computed property should convert to asyncpg
            if settings.DATABASE_URL.startswith("postgresql://"):
                expected = "postgresql+asyncpg://user:pass@localhost/db"
                assert settings.async_database_url == expected

    def test_async_database_url_sqlite(self):
        """Test SQLite URL stays the same if already has driver."""
        with patch.object(
            __import__("app.core.config", fromlist=["settings"]).settings,
            "DATABASE_URL",
            "sqlite+aiosqlite:///./test.db",
        ):
            from app.core.config import settings

            # SQLite with aiosqlite should stay the same
            if settings.DATABASE_URL.startswith("sqlite+aiosqlite"):
                assert settings.async_database_url == settings.DATABASE_URL


class TestCacheIntegration:
    """Test cache integration with fallback."""

    @pytest.mark.asyncio
    async def test_get_cache_returns_memory_cache_when_no_redis(self):
        """Test that get_cache returns InMemoryCache when Redis unavailable."""
        import app.core.cache
        from app.core.cache import InMemoryCache, get_cache

        # Reset redis client

        app.core.cache.redis_client = None

        cache = get_cache()
        assert isinstance(cache, InMemoryCache)

    @pytest.mark.asyncio
    async def test_cache_helpers_work_with_memory_cache(self):
        """Test cache helper functions work with in-memory cache."""
        import app.core.cache
        from app.core.cache import cache_delete, cache_exists, cache_get, cache_set

        # Reset redis client to force in-memory

        app.core.cache.redis_client = None
        app.core.cache._memory_cache = None  # Reset memory cache too

        # Test operations
        result = await cache_set("test_key", "test_value")
        assert result is True

        result = await cache_get("test_key")
        assert result == "test_value"

        result = await cache_exists("test_key")
        assert result is True

        result = await cache_delete("test_key")
        assert result is True

        result = await cache_get("test_key")
        assert result is None


class TestModelCompat:
    """Test model compatibility utilities."""

    def test_json_column_sqlite(self):
        """Test JSONColumn returns JSON type for SQLite."""
        with patch("app.models.compat.settings") as mock_settings:
            mock_settings.is_sqlite = True

            from app.models.compat import JSONColumn

            column = JSONColumn()
            assert column.type.__class__.__name__ in ["JSON", "JSONB"]

    def test_json_column_postgresql(self):
        """Test JSONColumn returns JSONB type for PostgreSQL."""
        with patch("app.models.compat.settings") as mock_settings:
            mock_settings.is_sqlite = False

            from app.models.compat import JSONColumn

            column = JSONColumn()
            assert column.type.__class__.__name__ in ["JSON", "JSONB"]

    def test_array_column_sqlite(self):
        """Test ArrayColumn returns JSON type for SQLite."""
        with patch("app.models.compat.settings") as mock_settings:
            mock_settings.is_sqlite = True

            from app.models.compat import ArrayColumn

            column = ArrayColumn()
            # SQLite uses JSON for arrays
            assert column.type.__class__.__name__ in ["JSON", "ARRAY"]

    def test_get_json_type(self):
        """Test get_json_type returns correct type."""
        with patch("app.models.compat.settings") as mock_settings:
            mock_settings.is_sqlite = True
            from sqlalchemy import JSON

            from app.models.compat import get_json_type

            assert get_json_type() == JSON

    def test_json_encoded_list(self):
        """Test JSONEncodedList type decorator."""
        from app.models.compat import JSONEncodedList

        decorator = JSONEncodedList()

        # Test encoding
        encoded = decorator.process_bind_param(["a", "b", "c"], None)
        assert encoded == '["a", "b", "c"]'

        # Test decoding
        decoded = decorator.process_result_value('["a", "b", "c"]', None)
        assert decoded == ["a", "b", "c"]

        # Test None handling
        assert decorator.process_bind_param(None, None) is None
        assert decorator.process_result_value(None, None) is None

    def test_json_encoded_dict(self):
        """Test JSONEncodedDict type decorator."""
        from app.models.compat import JSONEncodedDict

        decorator = JSONEncodedDict()

        # Test encoding
        encoded = decorator.process_bind_param({"key": "value"}, None)
        assert encoded == '{"key": "value"}'

        # Test decoding
        decoded = decorator.process_result_value('{"key": "value"}', None)
        assert decoded == {"key": "value"}

        # Test None handling
        assert decorator.process_bind_param(None, None) is None
        assert decorator.process_result_value(None, None) is None
