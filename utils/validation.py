"""
Shared input validation utilities.

Provides parameter validation for MCP tool inputs:
- Stock codes, series IDs, search queries
- Date ranges, numeric bounds

Returns validated value or raises ValueError.

Used by: adapters at their entry points.
"""
import re
from datetime import datetime
from typing import Optional


def validate_stock_code(code: str) -> str:
    """Validate stock code (Korean 6-digit or US alphanumeric).

    Raises ValueError if invalid.
    """
    code = str(code).strip()
    if not code:
        raise ValueError("Stock code cannot be empty")
    if len(code) > 10:
        raise ValueError(f"Stock code too long: {len(code)} chars (max 10)")
    if not re.match(r'^[A-Za-z0-9.]+$', code):
        raise ValueError(f"Invalid stock code characters: {code}")
    return code


def validate_series_id(series_id: str) -> str:
    """Validate FRED/ECOS series ID (alphanumeric + underscore).

    Raises ValueError if invalid.
    """
    series_id = str(series_id).strip()
    if not series_id:
        raise ValueError("Series ID cannot be empty")
    if len(series_id) > 50:
        raise ValueError(f"Series ID too long: {len(series_id)} chars (max 50)")
    if not re.match(r'^[A-Za-z0-9_]+$', series_id):
        raise ValueError(f"Invalid series ID characters: {series_id}")
    return series_id


def validate_search_query(query: str, max_length: int = 200) -> str:
    """Validate and sanitize search query.

    Strips dangerous characters, enforces length limit.
    Raises ValueError if empty after sanitization.
    """
    query = str(query).strip()
    if not query:
        raise ValueError("Search query cannot be empty")
    if len(query) > max_length:
        query = query[:max_length]
    # Remove potential injection characters but keep Korean/CJK
    query = re.sub(r'[<>{}|\\^~\[\]`]', '', query)
    if not query.strip():
        raise ValueError("Search query empty after sanitization")
    return query


def validate_date(date_str: str, param_name: str = "date") -> str:
    """Validate ISO date string (YYYY-MM-DD).

    Raises ValueError if invalid.
    """
    date_str = str(date_str).strip()
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid {param_name} format: {date_str} (expected YYYY-MM-DD)")
    return date_str


def validate_date_range(
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> tuple:
    """Validate a date range. end must be >= start if both provided.

    Returns (start, end) tuple.
    """
    if start:
        start = validate_date(start, "start_date")
    if end:
        end = validate_date(end, "end_date")
    if start and end and start > end:
        raise ValueError(f"start_date ({start}) must be before end_date ({end})")
    return start, end


def validate_positive_int(value: int, param_name: str = "value", max_val: int = 10000) -> int:
    """Validate positive integer within bounds."""
    value = int(value)
    if value < 1:
        raise ValueError(f"{param_name} must be positive, got {value}")
    if value > max_val:
        raise ValueError(f"{param_name} too large: {value} (max {max_val})")
    return value
