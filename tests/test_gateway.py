"""
Tests for GatewayServer initialization and tool registration.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_gateway_initializes():
    """GatewayServer should initialize and load servers."""
    from mcp_servers.gateway.gateway_server import GatewayServer
    gw = GatewayServer()
    assert len(gw._loaded) > 0
    assert len(gw._failed) == 0


def test_gateway_tool_count():
    """Gateway should have all servers loaded (tool count checked via health endpoint)."""
    from mcp_servers.gateway.gateway_server import GatewayServer
    gw = GatewayServer()
    # With mount() API, tools are distributed across sub-servers
    # Verify via loaded server count instead of direct component inspection
    assert len(gw._loaded) >= 46, f"Expected 46+ servers loaded, got {len(gw._loaded)}"


def test_gateway_status_tool():
    """gateway_status tool should return correct structure."""
    from mcp_servers.gateway.gateway_server import GatewayServer
    gw = GatewayServer()
    comps = gw.mcp._local_provider._components
    assert "tool:gateway_status@latest" in comps or any(
        k.startswith("tool:gateway_status") for k in comps
    )


def test_list_available_tools():
    """list_available_tools tool should be registered."""
    from mcp_servers.gateway.gateway_server import GatewayServer
    gw = GatewayServer()
    comps = gw.mcp._local_provider._components
    assert any(k.startswith("tool:list_available_tools") for k in comps)


def test_all_servers_loaded():
    """All 38 servers should load successfully."""
    from mcp_servers.gateway.gateway_server import GatewayServer
    gw = GatewayServer()
    assert len(gw._loaded) == 46, f"Expected 46 servers, loaded {len(gw._loaded)}: {gw._loaded}"
    assert gw._failed == [], f"Failed servers: {gw._failed}"
