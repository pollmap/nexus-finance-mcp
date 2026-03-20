"""
Rate Limiter for MCP servers using Token Bucket algorithm.

Manages API quotas for different data sources to prevent rate limit errors.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""

    capacity: float  # Maximum tokens
    rate: float  # Tokens per second
    tokens: float = field(init=False)
    last_update: float = field(init=False)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def __post_init__(self):
        self.tokens = self.capacity
        self.last_update = time.monotonic()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.

        Returns:
            True if tokens were consumed, False if not enough tokens.
        """
        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def wait_time(self, tokens: int = 1) -> float:
        """
        Calculate wait time until tokens are available.

        Returns:
            Seconds to wait (0 if tokens available now)
        """
        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                return 0.0
            needed = tokens - self.tokens
            return needed / self.rate

    def available(self) -> float:
        """Get current available tokens."""
        with self._lock:
            self._refill()
            return self.tokens


# Default quotas per service (requests per minute)
DEFAULT_QUOTAS: Dict[str, int] = {
    "dart": 100,       # OpenDART: ~100 req/min
    "ecos": 60,        # BOK ECOS: ~60 req/min
    "kosis": 60,       # KOSIS: ~60 req/min
    "fred": 120,       # FRED: 120 req/min
    "krx": 100,        # KRX: ~100 req/min
    "yahoo": 200,      # Yahoo Finance: ~200 req/min
    "coingecko": 50,   # CoinGecko Free: 50 req/min
    "sec": 100,        # SEC EDGAR: ~100 req/min
    "bis": 60,         # BIS: ~60 req/min
    "default": 60,     # Default fallback
}


class RateLimiter:
    """
    Rate limiter managing multiple service quotas.

    Usage:
        limiter = RateLimiter()

        # Sync usage
        if limiter.acquire("dart"):
            response = call_dart_api()

        # Async usage
        await limiter.acquire_async("ecos")
        response = await call_ecos_api()
    """

    def __init__(self, quotas: Dict[str, int] = None):
        """
        Initialize rate limiter.

        Args:
            quotas: Dict mapping service name to requests per minute.
                    Uses DEFAULT_QUOTAS if not provided.
        """
        self._quotas = quotas or DEFAULT_QUOTAS.copy()
        self._buckets: Dict[str, TokenBucket] = {}
        self._stats: Dict[str, Dict[str, int]] = {}

    def _get_bucket(self, service: str) -> TokenBucket:
        """Get or create token bucket for service."""
        if service not in self._buckets:
            rpm = self._quotas.get(service, self._quotas["default"])
            # Convert RPM to tokens per second
            rate = rpm / 60.0
            # Capacity = 1 minute worth of requests (allow burst)
            capacity = rpm
            self._buckets[service] = TokenBucket(capacity=capacity, rate=rate)
            self._stats[service] = {"acquired": 0, "waited": 0, "rejected": 0}
            logger.debug(f"Created rate limiter for '{service}': {rpm} req/min")
        return self._buckets[service]

    def acquire(self, service: str, tokens: int = 1, wait: bool = True) -> bool:
        """
        Acquire tokens for a service (synchronous).

        Args:
            service: Service name (e.g., 'dart', 'ecos')
            tokens: Number of tokens to acquire
            wait: If True, wait until tokens available; if False, return immediately

        Returns:
            True if tokens acquired, False if not (only when wait=False)
        """
        bucket = self._get_bucket(service)

        if bucket.consume(tokens):
            self._stats[service]["acquired"] += tokens
            return True

        if not wait:
            self._stats[service]["rejected"] += tokens
            return False

        # Wait for tokens
        wait_time = bucket.wait_time(tokens)
        if wait_time > 0:
            logger.debug(f"Rate limit: waiting {wait_time:.2f}s for '{service}'")
            self._stats[service]["waited"] += 1
            time.sleep(wait_time)

        # Should succeed after waiting
        bucket.consume(tokens)
        self._stats[service]["acquired"] += tokens
        return True

    async def acquire_async(
        self, service: str, tokens: int = 1, wait: bool = True
    ) -> bool:
        """
        Acquire tokens for a service (asynchronous).

        Args:
            service: Service name
            tokens: Number of tokens to acquire
            wait: If True, wait until tokens available

        Returns:
            True if tokens acquired, False if not
        """
        bucket = self._get_bucket(service)

        if bucket.consume(tokens):
            self._stats[service]["acquired"] += tokens
            return True

        if not wait:
            self._stats[service]["rejected"] += tokens
            return False

        # Wait asynchronously
        wait_time = bucket.wait_time(tokens)
        if wait_time > 0:
            logger.debug(f"Rate limit: waiting {wait_time:.2f}s for '{service}'")
            self._stats[service]["waited"] += 1
            await asyncio.sleep(wait_time)

        bucket.consume(tokens)
        self._stats[service]["acquired"] += tokens
        return True

    def get_available(self, service: str) -> float:
        """Get available tokens for a service."""
        return self._get_bucket(service).available()

    def get_wait_time(self, service: str, tokens: int = 1) -> float:
        """Get wait time until tokens are available."""
        return self._get_bucket(service).wait_time(tokens)

    def update_quota(self, service: str, rpm: int) -> None:
        """
        Update quota for a service.

        Args:
            service: Service name
            rpm: New requests per minute limit
        """
        self._quotas[service] = rpm
        # Reset bucket with new rate
        if service in self._buckets:
            del self._buckets[service]
        logger.info(f"Updated quota for '{service}': {rpm} req/min")

    def get_stats(self) -> Dict[str, Dict[str, int]]:
        """Get rate limiting statistics."""
        return {
            service: {
                **stats,
                "available": round(self._get_bucket(service).available(), 1),
            }
            for service, stats in self._stats.items()
        }

    def reset_stats(self) -> None:
        """Reset all statistics."""
        for service in self._stats:
            self._stats[service] = {"acquired": 0, "waited": 0, "rejected": 0}


class RateLimitContext:
    """
    Context manager for rate-limited operations.

    Usage:
        async with RateLimitContext(limiter, "dart") as acquired:
            if acquired:
                response = await call_dart_api()
    """

    def __init__(
        self,
        limiter: RateLimiter,
        service: str,
        tokens: int = 1,
        wait: bool = True,
    ):
        self.limiter = limiter
        self.service = service
        self.tokens = tokens
        self.wait = wait
        self.acquired = False

    async def __aenter__(self) -> bool:
        self.acquired = await self.limiter.acquire_async(
            self.service, self.tokens, self.wait
        )
        return self.acquired

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pass  # Nothing to clean up

    def __enter__(self) -> bool:
        self.acquired = self.limiter.acquire(
            self.service, self.tokens, self.wait
        )
        return self.acquired

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass


# Global rate limiter instance (lazy initialization)
_global_limiter: Optional[RateLimiter] = None


def get_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance."""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter()
    return _global_limiter
