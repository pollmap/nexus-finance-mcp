"""
Visualization MCP Server - thin re-export module.

The actual implementation lives in mcp_servers/servers/viz/ package.
This file exists for backward compatibility with existing imports.
"""
from mcp_servers.servers.viz import VizServer

__all__ = ["VizServer"]


def main():
    """Main entry point for standalone server."""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    server = VizServer()
    server.run()


if __name__ == "__main__":
    main()
