"""Standard response helpers for MCP tools.

All MCP tool responses MUST use these helpers for consistency.
See docs/PARSING_GUIDE.md for the response format specification.

Success: {"success": true, "data": ..., "count": N, "source": "...", ...extras}
Error:   {"error": true, "message": "...", "code": "..."}
"""
import logging
import math

logger = logging.getLogger(__name__)


def sanitize_records(df) -> list:
    """Convert pandas DataFrame to list of dicts with NaN/Inf → None.

    Ensures valid JSON output compatible with all parsers (Python, JS, etc.).
    Use this instead of raw df.to_dict("records") anywhere DataFrames are returned.

    Args:
        df: pandas DataFrame (or None)

    Returns:
        List of dicts with NaN/Inf replaced by None
    """
    if df is None:
        return []
    if not hasattr(df, 'to_dict'):
        return []
    try:
        import pandas as pd
        import numpy as np
        return df.where(pd.notna(df), None).replace(
            {np.nan: None, np.inf: None, -np.inf: None}
        ).to_dict("records")
    except Exception:
        # Fallback: manual NaN cleaning
        records = df.to_dict("records")
        for r in records:
            for k, v in r.items():
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    r[k] = None
        return records


def error_response(message: str, *, error: Exception = None, code: str = None) -> dict:
    """Standardized error response for MCP tools.

    Args:
        message: Human-readable error description
        error: Original exception (detail included in response)
        code: Optional error code for programmatic handling
              Common codes: INVALID_INPUT, NOT_FOUND, API_UNAVAILABLE,
              RATE_LIMITED, NOT_INITIALIZED, INTERNAL_ERROR
    """
    resp = {"error": True, "message": message}
    if error is not None:
        resp["detail"] = str(error)
    if code:
        resp["code"] = code
    return resp


def success_response(data=None, *, count: int = None, source: str = None, **extras) -> dict:
    """Standardized success response for MCP tools.

    Args:
        data: Primary payload (list, dict, or scalar). Always included.
        count: Number of records (auto-calculated from list length if omitted).
        source: Data source name (e.g., "BOK ECOS", "OpenDART").
        **extras: Domain-specific fields (e.g., stock_code, symbol, indicator).

    Returns:
        {"success": True, "data": ..., "count": N, "source": "...", ...extras}
    """
    resp = {"success": True, "data": data}
    if count is not None:
        resp["count"] = count
    elif isinstance(data, list):
        resp["count"] = len(data)
    if source:
        resp["source"] = source
    resp.update(extras)
    return resp
