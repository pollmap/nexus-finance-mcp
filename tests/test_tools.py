"""
Nexus Finance MCP — Live Tool Integration Tests.

Tests the running MCP server at http://127.0.0.1:8100/mcp via
JSON-RPC over Streamable HTTP (SSE responses).

Prerequisites:
    - Server running: python server.py --transport streamable-http --port 8100
    - pip install pytest httpx

Run:
    pytest tests/test_tools.py -v
    pytest tests/test_tools.py -v -k "gateway"   # single test
"""
import json
import pytest
import httpx

MCP_URL = "http://127.0.0.1:8100/mcp"
PROTOCOL_VERSION = "2024-11-05"
EXPECTED_TOOL_COUNT = 396


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_sse_data(text: str) -> list[dict]:
    """Parse SSE response text into list of JSON objects from 'data:' lines."""
    results = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            try:
                results.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return results


def extract_result(response: httpx.Response) -> dict:
    """Extract the JSON-RPC result from an SSE response."""
    msgs = parse_sse_data(response.text)
    for msg in msgs:
        if "result" in msg:
            return msg["result"]
        if "error" in msg:
            raise RuntimeError(f"JSON-RPC error: {msg['error']}")
    raise RuntimeError(f"No result in SSE response: {response.text[:500]}")


def extract_tool_result(response: httpx.Response) -> dict:
    """Extract tools/call result and parse the text content as JSON if possible."""
    result = extract_result(response)
    # structuredContent is preferred when available
    if "structuredContent" in result and result["structuredContent"]:
        return {
            "structured": result["structuredContent"],
            "is_error": result.get("isError", False),
            "raw": result,
        }
    # Fall back to text content
    content = result.get("content", [])
    text_parts = [c["text"] for c in content if c.get("type") == "text"]
    combined = "\n".join(text_parts)
    try:
        parsed = json.loads(combined)
    except (json.JSONDecodeError, TypeError):
        parsed = combined
    return {
        "structured": parsed,
        "is_error": result.get("isError", False),
        "raw": result,
    }


# ---------------------------------------------------------------------------
# Session fixture — one MCP session per test module
# ---------------------------------------------------------------------------

class MCPSession:
    """Lightweight MCP session wrapper over httpx."""

    def __init__(self):
        self.client = httpx.Client(timeout=60.0)
        self.session_id: str | None = None
        self._req_id = 0

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _headers(self) -> dict:
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            h["Mcp-Session-Id"] = self.session_id
        return h

    def send(self, method: str, params: dict | None = None) -> httpx.Response:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params is not None:
            payload["params"] = params
        resp = self.client.post(MCP_URL, json=payload, headers=self._headers())
        resp.raise_for_status()
        # Capture session ID from first response
        if not self.session_id and "mcp-session-id" in resp.headers:
            self.session_id = resp.headers["mcp-session-id"]
        return resp

    def initialize(self) -> dict:
        resp = self.send("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "pytest-nexus", "version": "1.0.0"},
        })
        result = extract_result(resp)
        # Send initialized notification (fire-and-forget)
        self.send("notifications/initialized", {})
        return result

    def list_tools(self) -> list[dict]:
        resp = self.send("tools/list", {})
        result = extract_result(resp)
        return result.get("tools", [])

    def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        resp = self.send("tools/call", {
            "name": name,
            "arguments": arguments or {},
        })
        return extract_tool_result(resp)

    def close(self):
        self.client.close()


@pytest.fixture(scope="module")
def mcp():
    """Shared MCP session for all tests in this module."""
    session = MCPSession()
    try:
        session.initialize()
    except Exception as e:
        pytest.skip(f"MCP server not reachable at {MCP_URL}: {e}")
    yield session
    session.close()


# ---------------------------------------------------------------------------
# 1. Protocol / Infrastructure Tests
# ---------------------------------------------------------------------------

class TestMCPProtocol:
    """Tests for MCP protocol handshake and tool discovery."""

    def test_initialize_handshake(self, mcp: MCPSession):
        """Server should complete initialize handshake and return server info."""
        # Re-initialize to verify (session already initialized in fixture)
        resp = mcp.send("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "pytest-verify", "version": "1.0.0"},
        })
        result = extract_result(resp)
        assert result["protocolVersion"] == PROTOCOL_VERSION
        assert "serverInfo" in result
        assert result["serverInfo"]["name"] == "nexus-finance-mcp"
        assert "capabilities" in result
        assert "tools" in result["capabilities"]

    def test_tools_list_count(self, mcp: MCPSession):
        """tools/list should return exactly EXPECTED_TOOL_COUNT tools."""
        tools = mcp.list_tools()
        assert len(tools) == EXPECTED_TOOL_COUNT, (
            f"Expected {EXPECTED_TOOL_COUNT} tools, got {len(tools)}"
        )

    def test_tools_have_required_fields(self, mcp: MCPSession):
        """Every tool should have name, description, and inputSchema."""
        tools = mcp.list_tools()
        for tool in tools[:20]:  # spot-check first 20
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert "description" in tool, f"Tool {tool['name']} missing 'description'"
            assert "inputSchema" in tool, f"Tool {tool['name']} missing 'inputSchema'"

    def test_gateway_status(self, mcp: MCPSession):
        """gateway_status should return online with 64 servers loaded."""
        result = mcp.call_tool("gateway_status")
        assert not result["is_error"]
        data = result["structured"]
        assert data["status"] == "online"
        assert data["loaded"] == 64
        assert data["failed"] == 0


# ---------------------------------------------------------------------------
# 2. Domain Tool Tests (no API key required)
# ---------------------------------------------------------------------------

class TestCrypto:
    """Crypto domain — CCXT, no API key needed."""

    def test_crypto_ticker(self, mcp: MCPSession):
        """crypto_ticker should return BTC/USDT price data."""
        result = mcp.call_tool("crypto_ticker", {"symbol": "BTC/USDT"})
        assert not result["is_error"], f"Error: {result['raw']}"
        data = result["structured"]
        # Should have price-related fields
        assert data is not None
        content_str = str(data)
        assert len(content_str) > 10, "Response too short, likely empty"


class TestDeFi:
    """DeFi domain — public endpoints."""

    def test_defi_feargreed(self, mcp: MCPSession):
        """defi_feargreed should return fear & greed index."""
        result = mcp.call_tool("defi_feargreed")
        assert not result["is_error"], f"Error: {result['raw']}"
        data = result["structured"]
        assert data is not None
        content_str = str(data)
        assert len(content_str) > 5, "Response too short"


class TestAlternativeData:
    """Alternative data domain — space weather (no key)."""

    def test_space_sunspot_data(self, mcp: MCPSession):
        """space_sunspot_data should return sunspot observations."""
        result = mcp.call_tool("space_sunspot_data")
        assert not result["is_error"], f"Error: {result['raw']}"
        data = result["structured"]
        assert data is not None
        content_str = str(data)
        assert len(content_str) > 10, "Response too short"


class TestAcademic:
    """Academic domain — arXiv (no key)."""

    def test_academic_arxiv(self, mcp: MCPSession):
        """academic_arxiv should return papers for a search query."""
        result = mcp.call_tool("academic_arxiv", {
            "query": "quantitative finance",
            "limit": 3,
        })
        assert not result["is_error"], f"Error: {result['raw']}"
        data = result["structured"]
        assert data is not None
        content_str = str(data)
        assert len(content_str) > 20, "Response too short — no papers returned?"


class TestQuant:
    """Quant domain — computational tools (no external API)."""

    def test_vol_garch(self, mcp: MCPSession):
        """vol_garch should compute GARCH volatility from sample returns."""
        # Sample daily log-returns (synthetic but realistic)
        sample_returns = [
            0.01, -0.005, 0.008, -0.012, 0.003,
            -0.007, 0.015, -0.002, 0.006, -0.009,
            0.011, -0.004, 0.007, -0.008, 0.002,
            0.013, -0.006, 0.009, -0.011, 0.004,
            -0.003, 0.01, -0.007, 0.005, -0.001,
            0.008, -0.005, 0.012, -0.009, 0.006,
        ]
        result = mcp.call_tool("vol_garch", {"returns_series": sample_returns})
        assert not result["is_error"], f"Error: {result['raw']}"
        data = result["structured"]
        assert data is not None
        content_str = str(data)
        assert len(content_str) > 5, "Response too short"


class TestKoreanEquity:
    """Korean equity domain — may require API key, soft-fail."""

    def test_stocks_search(self, mcp: MCPSession):
        """stocks_search for Samsung — skip if API key missing."""
        result = mcp.call_tool("stocks_search", {"query": "삼성전자"})
        if result["is_error"]:
            error_text = str(result["raw"])
            if "api" in error_text.lower() or "key" in error_text.lower() or "auth" in error_text.lower():
                pytest.skip("stocks_search requires API key")
            pytest.fail(f"Unexpected error: {error_text}")
        data = result["structured"]
        assert data is not None


# ---------------------------------------------------------------------------
# 3. Error Handling Tests
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Verify the server handles bad input gracefully."""

    def test_unknown_tool(self, mcp: MCPSession):
        """Calling a non-existent tool should return an error, not crash."""
        resp = mcp.send("tools/call", {
            "name": "this_tool_does_not_exist_xyz",
            "arguments": {},
        })
        msgs = parse_sse_data(resp.text)
        # Should get either an error in result or a JSON-RPC error
        got_error = False
        for msg in msgs:
            if "error" in msg:
                got_error = True
            elif "result" in msg and msg["result"].get("isError"):
                got_error = True
        assert got_error, "Expected error for unknown tool"

    def test_missing_required_argument(self, mcp: MCPSession):
        """Calling a tool without required args should return an error."""
        # academic_arxiv requires 'query'
        resp = mcp.send("tools/call", {
            "name": "academic_arxiv",
            "arguments": {},
        })
        msgs = parse_sse_data(resp.text)
        got_error = False
        for msg in msgs:
            if "error" in msg:
                got_error = True
            elif "result" in msg and msg["result"].get("isError"):
                got_error = True
        assert got_error, "Expected error for missing required argument"
