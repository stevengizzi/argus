"""Tests for ResponseCache."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

import pytest

from argus.ai.cache import ResponseCache


class TestResponseCacheBasics:
    """Test ResponseCache basic operations."""

    @pytest.mark.asyncio
    async def test_set_and_get(self) -> None:
        """Test setting and getting a cached value."""
        cache = ResponseCache()

        await cache.set("test_key", {"data": "test_value"})
        result = await cache.get("test_key")

        assert result is not None
        assert result["data"] == "test_value"

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self) -> None:
        """Test getting a key that doesn't exist."""
        cache = ResponseCache()

        result = await cache.get("nonexistent_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate(self) -> None:
        """Test invalidating a cached entry."""
        cache = ResponseCache()

        await cache.set("test_key", {"data": "test_value"})
        removed = await cache.invalidate("test_key")
        result = await cache.get("test_key")

        assert removed is True
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_nonexistent(self) -> None:
        """Test invalidating a nonexistent key."""
        cache = ResponseCache()

        removed = await cache.invalidate("nonexistent_key")

        assert removed is False


class TestResponseCacheTTL:
    """Test ResponseCache TTL behavior."""

    @pytest.mark.asyncio
    async def test_entry_expires_after_ttl(self) -> None:
        """Test that entries expire after TTL."""
        cache = ResponseCache(default_ttl=1)  # 1 second TTL

        await cache.set("test_key", {"data": "test_value"})

        # Should exist immediately
        result = await cache.get("test_key")
        assert result is not None

        # Wait for expiry
        await asyncio.sleep(1.1)

        # Should be expired now
        result = await cache.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_custom_ttl_per_entry(self) -> None:
        """Test setting custom TTL for individual entries."""
        cache = ResponseCache(default_ttl=60)

        # Set with short custom TTL
        await cache.set("short_ttl", {"data": "expires_soon"}, ttl=1)
        # Set with default TTL
        await cache.set("default_ttl", {"data": "stays_longer"})

        await asyncio.sleep(1.1)

        # Short TTL entry should be expired
        assert await cache.get("short_ttl") is None
        # Default TTL entry should still exist
        assert await cache.get("default_ttl") is not None


class TestResponseCacheEndpointMethods:
    """Test ResponseCache endpoint-based methods."""

    @pytest.mark.asyncio
    async def test_set_and_get_by_endpoint(self) -> None:
        """Test setting and getting by endpoint with params."""
        cache = ResponseCache()

        await cache.set_by_endpoint(
            "dashboard/insights",
            {"insight": "Portfolio is performing well"},
            params={"page": "Dashboard", "user_id": "123"},
        )

        result = await cache.get_by_endpoint(
            "dashboard/insights",
            params={"page": "Dashboard", "user_id": "123"},
        )

        assert result is not None
        assert result["insight"] == "Portfolio is performing well"

    @pytest.mark.asyncio
    async def test_different_params_different_cache_entries(self) -> None:
        """Test that different params create different cache entries."""
        cache = ResponseCache()

        await cache.set_by_endpoint(
            "dashboard/insights",
            {"data": "for_user_1"},
            params={"user_id": "1"},
        )
        await cache.set_by_endpoint(
            "dashboard/insights",
            {"data": "for_user_2"},
            params={"user_id": "2"},
        )

        result1 = await cache.get_by_endpoint(
            "dashboard/insights", params={"user_id": "1"}
        )
        result2 = await cache.get_by_endpoint(
            "dashboard/insights", params={"user_id": "2"}
        )

        assert result1["data"] == "for_user_1"
        assert result2["data"] == "for_user_2"

    @pytest.mark.asyncio
    async def test_invalidate_by_endpoint(self) -> None:
        """Test invalidating by endpoint."""
        cache = ResponseCache()

        await cache.set_by_endpoint(
            "dashboard/insights",
            {"data": "cached"},
            params={"page": "Dashboard"},
        )

        removed = await cache.invalidate_by_endpoint(
            "dashboard/insights", params={"page": "Dashboard"}
        )
        result = await cache.get_by_endpoint(
            "dashboard/insights", params={"page": "Dashboard"}
        )

        assert removed is True
        assert result is None


class TestResponseCacheBulkOperations:
    """Test ResponseCache bulk operations."""

    @pytest.mark.asyncio
    async def test_clear_all(self) -> None:
        """Test clearing all cache entries."""
        cache = ResponseCache()

        await cache.set("key1", {"data": "1"})
        await cache.set("key2", {"data": "2"})
        await cache.set("key3", {"data": "3"})

        count = await cache.clear()

        assert count == 3
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.get("key3") is None

    @pytest.mark.asyncio
    async def test_invalidate_prefix(self) -> None:
        """Test invalidating entries by prefix."""
        cache = ResponseCache()

        await cache.set("dashboard:user1", {"data": "1"})
        await cache.set("dashboard:user2", {"data": "2"})
        await cache.set("trades:user1", {"data": "3"})

        count = await cache.invalidate_prefix("dashboard:")

        assert count == 2
        assert await cache.get("dashboard:user1") is None
        assert await cache.get("dashboard:user2") is None
        assert await cache.get("trades:user1") is not None

    @pytest.mark.asyncio
    async def test_cleanup_expired(self) -> None:
        """Test cleaning up expired entries."""
        cache = ResponseCache()

        # Set entries with very short TTL
        await cache.set("expires1", {"data": "1"}, ttl=1)
        await cache.set("expires2", {"data": "2"}, ttl=1)
        await cache.set("stays", {"data": "3"}, ttl=60)

        await asyncio.sleep(1.1)

        count = await cache.cleanup_expired()

        assert count == 2
        assert await cache.get("stays") is not None

    @pytest.mark.asyncio
    async def test_size_property(self) -> None:
        """Test the size property."""
        cache = ResponseCache()

        assert cache.size == 0

        await cache.set("key1", {"data": "1"})
        assert cache.size == 1

        await cache.set("key2", {"data": "2"})
        assert cache.size == 2

        await cache.invalidate("key1")
        assert cache.size == 1
