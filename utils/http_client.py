"""
Shared HTTP client with retry, timeout, and rate-limit integration.

Provides a configured requests.Session with:
- Default timeout (30s)
- User-Agent header
- Retry with exponential backoff (3 attempts)
- Optional rate limiter integration

Used by: adapters that call external APIs via requests.get/post.
"""
import logging
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

USER_AGENT = "NexusFinanceMCP/3.0"
DEFAULT_TIMEOUT = 30

_sessions: Dict[str, requests.Session] = {}


def get_session(service: str = "default") -> requests.Session:
    """Get or create a configured requests.Session for a service.

    Args:
        service: Service name for logging and session pooling.
    """
    if service not in _sessions:
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})

        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        _sessions[service] = session
        logger.debug(f"Created HTTP session for service: {service}")

    return _sessions[service]


def safe_get(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    service: str = "default",
    timeout: int = DEFAULT_TIMEOUT,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Perform a GET request with error handling and return parsed JSON.

    Args:
        url: Request URL.
        params: Query parameters.
        service: Service name for session pooling.
        timeout: Request timeout in seconds.
        headers: Additional headers.

    Returns:
        {"success": True, "data": ...} or {"error": True, "message": ...}
    """
    try:
        session = get_session(service)
        resp = session.get(url, params=params, timeout=timeout, headers=headers)
        resp.raise_for_status()
        return {"success": True, "data": resp.json()}
    except requests.exceptions.JSONDecodeError:
        return {"success": True, "data": resp.text}
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout for {service}: {url}")
        return {"error": True, "message": f"Request timed out after {timeout}s"}
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error for {service}: {e}")
        return {"error": True, "message": f"Connection failed: {e}"}
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error for {service}: {e}")
        return {"error": True, "message": f"HTTP {resp.status_code}: {e}"}
    except Exception as e:
        logger.error(f"Request error for {service}: {e}")
        return {"error": True, "message": str(e)}
