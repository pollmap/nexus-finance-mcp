"""
Shared pytest fixtures for Nexus Finance MCP tests.
"""
import os
import sys
import pytest

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture
def mock_env(monkeypatch):
    """Set minimal env vars for testing."""
    monkeypatch.setenv("BOK_ECOS_API_KEY", "test_key")
    monkeypatch.setenv("DART_API_KEY", "test_key")
    monkeypatch.setenv("KOSIS_API_KEY", "test_key")
    monkeypatch.setenv("FRED_API_KEY", "test_key")
    monkeypatch.setenv("ETHERSCAN_API_KEY", "test_key")
    monkeypatch.setenv("NAVER_CLIENT_ID", "test_id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test_secret")
