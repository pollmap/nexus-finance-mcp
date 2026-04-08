"""
Result Classifier for Nexus Finance MCP test framework.

Classifies tool return values into standardized test statuses,
distinguishing between true failures and expected/environmental failures
(missing API keys, rate limits, uninitialized adapters).

Usage:
    from tests.framework.classifier import classify_result, TestStatus
    status = classify_result(tool_output)
"""
from enum import Enum
from typing import Any


class TestStatus(Enum):
    """Standardized test result statuses."""
    PASS = "PASS"                    # Success with meaningful data
    SOFT_PASS = "SOFT_PASS"          # Success but empty/minimal data
    EXPECTED_FAIL = "EXPECTED_FAIL"  # Known failure (missing key, rate limit)
    FAIL = "FAIL"                    # Unexpected failure
    TIMEOUT = "TIMEOUT"              # Execution timed out
    SKIP = "SKIP"                    # Test skipped (e.g. missing dependency)


# Error codes that indicate environmental/expected failures
EXPECTED_ERROR_CODES = frozenset({
    "NOT_INITIALIZED",
    "RATE_LIMITED",
    "API_UNAVAILABLE",
})

# Substrings in error messages that indicate expected failures
EXPECTED_ERROR_PATTERNS = (
    "not initialized",
    "api key",
    "not set",
    "not configured",
    "rate limit",
)


def classify_result(result: Any) -> TestStatus:
    """Classify a tool's return value into a TestStatus.

    Classification logic:
      1. None or non-dict -> FAIL
      2. result["success"] truthy:
         - data is None/empty -> SOFT_PASS
         - data present -> PASS
      3. result["error"] truthy:
         - known error code or message pattern -> EXPECTED_FAIL
         - otherwise -> FAIL
      4. Neither success nor error key:
         - non-empty dict with data -> SOFT_PASS
         - empty dict -> FAIL
    """
    if result is None:
        return TestStatus.FAIL

    if not isinstance(result, dict):
        return TestStatus.FAIL

    # Check success path
    if result.get("success"):
        data = result.get("data")
        if data is None or data == [] or data == {}:
            return TestStatus.SOFT_PASS
        return TestStatus.PASS

    # Check error path
    if result.get("error"):
        code = result.get("code", "")
        if code in EXPECTED_ERROR_CODES:
            return TestStatus.EXPECTED_FAIL

        msg = str(result.get("message", "")).lower()
        if any(pattern in msg for pattern in EXPECTED_ERROR_PATTERNS):
            return TestStatus.EXPECTED_FAIL

        return TestStatus.FAIL

    # Neither success nor error key -- some tools return raw dicts
    if len(result) > 0:
        return TestStatus.SOFT_PASS

    return TestStatus.FAIL
