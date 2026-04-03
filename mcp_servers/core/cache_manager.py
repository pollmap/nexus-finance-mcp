"""
4-Tier Cache Manager for MCP servers.

Tiers:
  L1: LRUCache (in-memory, 100 items)
  L2: TTLCache (in-memory, 1000 items, 1hr default TTL)
  L3: DiskCache (SQLite-backed, persistent)

TTL by data type:
  - realtime_price: 60 seconds
  - daily_data: 3600 seconds (1 hour)
  - historical: 86400 seconds (24 hours)
  - static_meta: 604800 seconds (1 week)
"""
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Optional
from functools import wraps
import time

from cachetools import LRUCache, TTLCache
import diskcache

logger = logging.getLogger(__name__)


class CacheManager:
    """Multi-tier cache manager with automatic tier promotion/demotion."""

    # Default TTL values by data type (seconds)
    TTL_CONFIG = {
        "realtime_price": 60,
        "daily_data": 3600,
        "historical": 86400,
        "static_meta": 604800,
        "default": 3600,
    }

    def __init__(
        self,
        cache_dir: Path = None,
        l1_maxsize: int = 100,
        l2_maxsize: int = 1000,
        l2_ttl: int = 3600,
    ):
        """
        Initialize the cache manager.

        Args:
            cache_dir: Directory for disk cache. Defaults to project's .cache/
            l1_maxsize: Maximum items in L1 LRU cache
            l2_maxsize: Maximum items in L2 TTL cache
            l2_ttl: Default TTL for L2 cache in seconds
        """
        # L1: Fast LRU cache (no TTL, just size-limited)
        self._l1: LRUCache = LRUCache(maxsize=l1_maxsize)

        # L2: TTL cache with time-based expiration
        self._l2_ttl: int = l2_ttl
        self._l2: TTLCache = TTLCache(maxsize=l2_maxsize, ttl=l2_ttl)

        # L3: Persistent disk cache
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent.parent / ".cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._l3: diskcache.Cache = diskcache.Cache(str(cache_dir / "diskcache"))

        self._stats = {
            "l1_hits": 0,
            "l2_hits": 0,
            "l3_hits": 0,
            "misses": 0,
        }

    def _make_key(self, namespace: str, key: str) -> str:
        """Create a namespaced cache key."""
        return f"{namespace}:{key}"

    def _hash_key(self, key: Any) -> str:
        """Hash complex keys (dicts, lists) to string."""
        if isinstance(key, str):
            return key
        serialized = json.dumps(key, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def get(self, namespace: str, key: Any) -> Optional[Any]:
        """
        Get value from cache, checking all tiers.

        Args:
            namespace: Cache namespace (e.g., 'ecos', 'dart')
            key: Cache key (can be string, dict, or any serializable object)

        Returns:
            Cached value or None if not found
        """
        cache_key = self._make_key(namespace, self._hash_key(key))

        # L1 check
        if cache_key in self._l1:
            self._stats["l1_hits"] += 1
            logger.debug(f"L1 cache hit: {cache_key}")
            return self._l1[cache_key]

        # L2 check
        if cache_key in self._l2:
            self._stats["l2_hits"] += 1
            # Promote to L1
            value = self._l2[cache_key]
            self._l1[cache_key] = value
            logger.debug(f"L2 cache hit: {cache_key}")
            return value

        # L3 check
        value = self._l3.get(cache_key)
        if value is not None:
            self._stats["l3_hits"] += 1
            # Promote to L1 and L2
            self._l1[cache_key] = value
            self._l2[cache_key] = value
            logger.debug(f"L3 cache hit: {cache_key}")
            return value

        self._stats["misses"] += 1
        logger.debug(f"Cache miss: {cache_key}")
        return None

    def set(
        self,
        namespace: str,
        key: Any,
        value: Any,
        data_type: str = "default",
        ttl: Optional[int] = None,
    ) -> None:
        """
        Set value in all cache tiers.

        Args:
            namespace: Cache namespace
            key: Cache key
            value: Value to cache
            data_type: Type of data for TTL lookup ('realtime_price', 'daily_data', etc.)
            ttl: Override TTL in seconds (optional)
        """
        cache_key = self._make_key(namespace, self._hash_key(key))

        if ttl is None:
            ttl = self.TTL_CONFIG.get(data_type, self.TTL_CONFIG["default"])

        # Set in all tiers
        # L1: LRU (size-based eviction, no TTL — always set)
        self._l1[cache_key] = value
        # L2: TTLCache has fixed TTL from __init__. Skip if data needs
        # shorter TTL to avoid serving stale realtime data.
        if ttl >= self._l2_ttl:
            self._l2[cache_key] = value
        # L3: DiskCache supports per-key TTL
        self._l3.set(cache_key, value, expire=ttl)

        logger.debug(f"Cache set: {cache_key} (TTL={ttl}s)")

    def delete(self, namespace: str, key: Any) -> None:
        """Delete value from all cache tiers."""
        cache_key = self._make_key(namespace, self._hash_key(key))

        self._l1.pop(cache_key, None)
        self._l2.pop(cache_key, None)
        self._l3.delete(cache_key)

        logger.debug(f"Cache delete: {cache_key}")

    def clear_namespace(self, namespace: str) -> int:
        """Clear all entries for a namespace. Returns count of cleared items."""
        prefix = f"{namespace}:"
        count = 0

        # Clear L1
        keys_to_delete = [k for k in self._l1 if k.startswith(prefix)]
        for k in keys_to_delete:
            del self._l1[k]
            count += 1

        # Clear L2
        keys_to_delete = [k for k in self._l2 if k.startswith(prefix)]
        for k in keys_to_delete:
            del self._l2[k]

        # Clear L3 (iterate through disk cache)
        for k in list(self._l3):
            if k.startswith(prefix):
                self._l3.delete(k)

        logger.info(f"Cleared {count} items from namespace '{namespace}'")
        return count

    def clear_all(self) -> None:
        """Clear all caches."""
        self._l1.clear()
        self._l2.clear()
        self._l3.clear()
        logger.info("All caches cleared")

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total_requests = sum(self._stats.values())
        hit_rate = (
            (total_requests - self._stats["misses"]) / total_requests * 100
            if total_requests > 0
            else 0
        )

        return {
            **self._stats,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            "l1_size": len(self._l1),
            "l2_size": len(self._l2),
            "l3_size": len(self._l3),
        }

    def close(self) -> None:
        """Close the disk cache."""
        self._l3.close()


def cached(
    namespace: str,
    data_type: str = "default",
    key_builder: callable = None,
):
    """
    Decorator for caching function results.

    Args:
        namespace: Cache namespace
        data_type: Type of data for TTL
        key_builder: Optional function to build cache key from args/kwargs

    Usage:
        @cached("ecos", "daily_data")
        def fetch_interest_rate(date: str) -> float:
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get cache manager from first arg if it's a class instance with _cache
            cache_mgr = None
            if args and hasattr(args[0], "_cache"):
                cache_mgr = args[0]._cache

            if cache_mgr is None:
                # No cache available, just call function
                return func(*args, **kwargs)

            # Build cache key
            if key_builder:
                key = key_builder(*args, **kwargs)
            else:
                # Default: use function name + all args
                key = {
                    "func": func.__name__,
                    "args": args[1:] if args else (),  # Skip self
                    "kwargs": kwargs,
                }

            # Try to get from cache
            result = cache_mgr.get(namespace, key)
            if result is not None:
                return result

            # Call function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                cache_mgr.set(namespace, key, result, data_type)

            return result

        return wrapper
    return decorator


# Global cache instance (lazy initialization)
_global_cache: Optional[CacheManager] = None
_cache_lock = __import__("threading").Lock()


def get_cache() -> CacheManager:
    """Get or create the global cache instance."""
    global _global_cache
    if _global_cache is None:
        with _cache_lock:
            if _global_cache is None:
                _global_cache = CacheManager()
    return _global_cache
