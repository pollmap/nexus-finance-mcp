"""Standard response helpers for MCP tools."""
import logging

logger = logging.getLogger(__name__)


def error_response(message: str, error: Exception = None, code: str = None) -> dict:
    """Standardized error response for MCP tools.

    Args:
        message: Human-readable error description
        error: Original exception (detail included in response)
        code: Optional error code for programmatic handling
    """
    resp = {"error": True, "message": message}
    if error is not None:
        resp["detail"] = str(error)
    if code:
        resp["code"] = code
    return resp


def success_response(data: dict = None, **meta) -> dict:
    """Standardized success response for MCP tools."""
    resp = {"success": True}
    if data:
        resp.update(data)
    resp.update(meta)
    return resp
