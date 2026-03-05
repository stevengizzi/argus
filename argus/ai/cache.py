"""Response caching for the ARGUS AI Copilot.

Provides TTL-based caching for AI responses, primarily used for
Dashboard insight caching to avoid redundant API calls.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    """A cached response with expiration time.

    Attributes:
        value: The cached response data.
        expires_at: Unix timestamp when this entry expires.
    """

    value: dict[str, Any]
    expires_at: float


class ResponseCache:
    """Simple TTL-based cache for AI responses.

    Uses an in-memory dict keyed by (endpoint, params_hash).
    Thread-safe via asyncio lock.
    """

    def __init__(self, default_ttl: int = 300) -> None:
        """Initialize the cache.

        Args:
            default_ttl: Default TTL in seconds (5 minutes).
        """
        self._cache: dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

    @staticmethod
    def _hash_params(params: dict[str, Any]) -> str:
        """Create a hash of parameters for cache key.

        Args:
            params: Parameters dict to hash.

        Returns:
            MD5 hex digest of the sorted params.
        """
        # Sort keys for consistent hashing
        sorted_str = str(sorted(params.items()))
        return hashlib.md5(sorted_str.encode()).hexdigest()

    def _make_key(self, endpoint: str, params: dict[str, Any] | None = None) -> str:
        """Create a cache key from endpoint and params.

        Args:
            endpoint: The API endpoint or cache namespace.
            params: Optional parameters to include in the key.

        Returns:
            Cache key string.
        """
        if params:
            params_hash = self._hash_params(params)
            return f"{endpoint}:{params_hash}"
        return endpoint

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if a cache entry has expired.

        Args:
            entry: The cache entry to check.

        Returns:
            True if expired, False otherwise.
        """
        return time.time() >= entry.expires_at

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get a cached value by key.

        Args:
            key: The cache key.

        Returns:
            The cached value, or None if not found or expired.
        """
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if self._is_expired(entry):
                del self._cache[key]
                return None
            return entry.value

    async def get_by_endpoint(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Get a cached value by endpoint and params.

        Args:
            endpoint: The API endpoint or namespace.
            params: Optional parameters.

        Returns:
            The cached value, or None if not found or expired.
        """
        key = self._make_key(endpoint, params)
        return await self.get(key)

    async def set(
        self,
        key: str,
        value: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        """Set a cached value.

        Args:
            key: The cache key.
            value: The value to cache.
            ttl: Optional TTL in seconds (uses default if not specified).
        """
        actual_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.time() + actual_ttl

        async with self._lock:
            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)

    async def set_by_endpoint(
        self,
        endpoint: str,
        value: dict[str, Any],
        params: dict[str, Any] | None = None,
        ttl: int | None = None,
    ) -> None:
        """Set a cached value by endpoint and params.

        Args:
            endpoint: The API endpoint or namespace.
            value: The value to cache.
            params: Optional parameters for key generation.
            ttl: Optional TTL in seconds.
        """
        key = self._make_key(endpoint, params)
        await self.set(key, value, ttl)

    async def invalidate(self, key: str) -> bool:
        """Invalidate (remove) a cached entry.

        Args:
            key: The cache key to invalidate.

        Returns:
            True if the key was found and removed, False otherwise.
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def invalidate_by_endpoint(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> bool:
        """Invalidate a cached entry by endpoint and params.

        Args:
            endpoint: The API endpoint or namespace.
            params: Optional parameters.

        Returns:
            True if found and removed, False otherwise.
        """
        key = self._make_key(endpoint, params)
        return await self.invalidate(key)

    async def invalidate_prefix(self, prefix: str) -> int:
        """Invalidate all entries with keys starting with prefix.

        Args:
            prefix: The key prefix to match.

        Returns:
            Number of entries removed.
        """
        async with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_remove:
                del self._cache[key]
            return len(keys_to_remove)

    async def clear(self) -> int:
        """Clear all cached entries.

        Returns:
            Number of entries cleared.
        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    async def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of expired entries removed.
        """
        async with self._lock:
            now = time.time()
            expired_keys = [
                key for key, entry in self._cache.items() if now >= entry.expires_at
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    @property
    def size(self) -> int:
        """Get the current number of cached entries."""
        return len(self._cache)
