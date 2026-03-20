"""
Base MCP Server class using FastMCP.

Provides common infrastructure for all custom MCP servers:
- Caching
- Rate limiting
- Error handling
- Logging
"""
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP

from mcp_servers.core.cache_manager import CacheManager, get_cache
from mcp_servers.core.rate_limiter import RateLimiter, get_limiter

logger = logging.getLogger(__name__)


class BaseMCPServer(ABC):
    """
    Abstract base class for MCP servers.

    Provides:
    - FastMCP server instance
    - Integrated caching (4-tier)
    - Rate limiting
    - Standard error handling

    Subclasses must implement:
    - _register_tools(): Register MCP tools with decorators
    - name: Server name property
    """

    def __init__(
        self,
        cache: CacheManager = None,
        limiter: RateLimiter = None,
        debug: bool = False,
    ):
        """
        Initialize the MCP server.

        Args:
            cache: Cache manager instance (uses global if not provided)
            limiter: Rate limiter instance (uses global if not provided)
            debug: Enable debug logging
        """
        self._cache = cache or get_cache()
        self._limiter = limiter or get_limiter()

        # Configure logging
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        # Create FastMCP server
        self._mcp = FastMCP(self.name)

        # Register tools
        self._register_tools()

        logger.info(f"Initialized MCP server: {self.name}")

    @property
    @abstractmethod
    def name(self) -> str:
        """Server name (used as namespace prefix)."""
        pass

    @abstractmethod
    def _register_tools(self) -> None:
        """Register MCP tools. Override in subclasses."""
        pass

    @property
    def mcp(self) -> FastMCP:
        """Get the FastMCP instance."""
        return self._mcp

    def run(self) -> None:
        """Run the MCP server."""
        logger.info(f"Starting MCP server: {self.name}")
        self._mcp.run()

    # Helper methods for subclasses

    def _cached_request(
        self,
        key: Any,
        fetch_func: callable,
        data_type: str = "default",
        namespace: str = None,
    ) -> Any:
        """
        Execute a cached request.

        Args:
            key: Cache key
            fetch_func: Function to call on cache miss
            data_type: Type of data for TTL
            namespace: Cache namespace (defaults to server name)

        Returns:
            Cached or freshly fetched data
        """
        ns = namespace or self.name

        # Try cache first
        result = self._cache.get(ns, key)
        if result is not None:
            logger.debug(f"Cache hit for {ns}:{key}")
            return result

        # Fetch fresh data
        logger.debug(f"Cache miss, fetching {ns}:{key}")
        result = fetch_func()

        # Cache the result
        if result is not None:
            self._cache.set(ns, key, result, data_type)

        return result

    async def _cached_request_async(
        self,
        key: Any,
        fetch_func: callable,
        data_type: str = "default",
        namespace: str = None,
    ) -> Any:
        """
        Execute a cached async request.

        Args:
            key: Cache key
            fetch_func: Async function to call on cache miss
            data_type: Type of data for TTL
            namespace: Cache namespace

        Returns:
            Cached or freshly fetched data
        """
        ns = namespace or self.name

        result = self._cache.get(ns, key)
        if result is not None:
            return result

        result = await fetch_func()

        if result is not None:
            self._cache.set(ns, key, result, data_type)

        return result

    def _rate_limited(self, service: str = None) -> bool:
        """
        Acquire rate limit token (blocking).

        Args:
            service: Service name (defaults to server name)

        Returns:
            True (always, after waiting if needed)
        """
        svc = service or self.name
        return self._limiter.acquire(svc, wait=True)

    async def _rate_limited_async(self, service: str = None) -> bool:
        """
        Acquire rate limit token asynchronously.

        Args:
            service: Service name

        Returns:
            True (always, after waiting if needed)
        """
        svc = service or self.name
        return await self._limiter.acquire_async(svc, wait=True)

    def _format_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """
        Format error for MCP response.

        Args:
            error: Exception that occurred
            context: Additional context

        Returns:
            Error dict suitable for MCP response
        """
        error_msg = str(error)
        error_type = type(error).__name__

        logger.error(f"{context}: {error_type} - {error_msg}")

        return {
            "error": True,
            "error_type": error_type,
            "message": error_msg,
            "context": context,
        }

    def _format_success(
        self,
        data: Any,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Format successful response.

        Args:
            data: Response data
            metadata: Optional metadata

        Returns:
            Formatted response dict
        """
        response = {
            "success": True,
            "data": data,
        }
        if metadata:
            response["metadata"] = metadata
        return response

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._cache.get_stats()

    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        return self._limiter.get_stats()


class ToolError(Exception):
    """Custom exception for MCP tool errors."""

    def __init__(self, message: str, code: str = "TOOL_ERROR", details: Any = None):
        super().__init__(message)
        self.code = code
        self.details = details


def tool_handler(func):
    """
    Decorator for MCP tool handlers with standard error handling.

    Catches exceptions and formats them consistently.

    Usage:
        @tool_handler
        def my_tool(param: str) -> dict:
            ...
    """
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ToolError as e:
            return {
                "error": True,
                "code": e.code,
                "message": str(e),
                "details": e.details,
            }
        except Exception as e:
            logger.exception(f"Tool error in {func.__name__}")
            return {
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": str(e),
            }

    return wrapper


def async_tool_handler(func):
    """Async version of tool_handler decorator."""
    from functools import wraps

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ToolError as e:
            return {
                "error": True,
                "code": e.code,
                "message": str(e),
                "details": e.details,
            }
        except Exception as e:
            logger.exception(f"Tool error in {func.__name__}")
            return {
                "error": True,
                "code": "INTERNAL_ERROR",
                "message": str(e),
            }

    return wrapper
