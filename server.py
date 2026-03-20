"""
Nexus Finance MCP Server - HTTP/SSE Entry Point.

Luxon AI Agent Network의 금융 데이터 인프라.
43개 도구 / 5개 서버 / 5개 어댑터를 HTTP 엔드포인트로 제공.

Usage:
    # Streamable HTTP (권장 - Smithery/에이전트용)
    python server.py --transport streamable-http --port 8100

    # SSE (레거시 클라이언트용)
    python server.py --transport sse --port 8100

    # stdio (로컬 Claude Code용)
    python server.py --transport stdio

Environment:
    BOK_ECOS_API_KEY  - 한국은행 ECOS
    DART_API_KEY      - OpenDART
    KOSIS_API_KEY     - 통계청 KOSIS
    RONE_API_KEY      - 한국부동산원
    FRED_API_KEY      - Federal Reserve FRED
"""
import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("nexus-finance-mcp")


def create_server():
    """Create the unified gateway MCP server."""
    from mcp_servers.gateway.gateway_server import GatewayServer
    gateway = GatewayServer()
    return gateway.mcp


def main():
    parser = argparse.ArgumentParser(description="Nexus Finance MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http", "http"],
        default=os.getenv("MCP_TRANSPORT", "streamable-http"),
        help="Transport protocol (default: streamable-http)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_HOST", "0.0.0.0"),
        help="Host to bind (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", "8100")),
        help="Port to bind (default: 8100)",
    )
    parser.add_argument(
        "--stateless",
        action="store_true",
        default=os.getenv("MCP_STATELESS", "false").lower() == "true",
        help="Run in stateless HTTP mode",
    )
    args = parser.parse_args()

    mcp = create_server()

    logger.info(f"Starting Nexus Finance MCP Server")
    logger.info(f"  Transport: {args.transport}")
    logger.info(f"  Host: {args.host}:{args.port}")
    logger.info(f"  Stateless: {args.stateless}")

    # API key status
    keys = {
        "BOK_ECOS": bool(os.getenv("BOK_ECOS_API_KEY")),
        "DART": bool(os.getenv("DART_API_KEY")),
        "KOSIS": bool(os.getenv("KOSIS_API_KEY")),
        "RONE": bool(os.getenv("RONE_API_KEY")),
        "FRED": bool(os.getenv("FRED_API_KEY")),
    }
    for name, ok in keys.items():
        logger.info(f"  {name}: {'✓' if ok else '✗ (missing)'}")

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(
            transport=args.transport,
            host=args.host,
            port=args.port,
            stateless=args.stateless,
        )


if __name__ == "__main__":
    main()
