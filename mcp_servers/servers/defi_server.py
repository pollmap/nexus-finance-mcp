"""
DeFi MCP Server — DefiLlama TVL + Fear & Greed Index.

Tools (4):
- defi_protocols: 프로토콜 TVL 순위
- defi_protocol_detail: 단일 프로토콜 상세
- defi_chains: 체인별 TVL
- defi_feargreed: 공포탐욕지수
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP
from mcp_servers.adapters.defi_adapter import DefiLlamaAdapter, FearGreedAdapter

logger = logging.getLogger(__name__)


class DefiServer:
    def __init__(self):
        self._llama = DefiLlamaAdapter()
        self._fg = FearGreedAdapter()
        self.mcp = FastMCP("defi")
        self._register_tools()
        logger.info("DeFi MCP Server initialized")

    def _register_tools(self):

        @self.mcp.tool()
        def defi_protocols(limit: int = 30) -> dict:
            """DeFi 프로토콜 TVL 순위 (DefiLlama). Args: limit — 상위 N개."""
            return self._llama.get_protocols(limit)

        @self.mcp.tool()
        def defi_protocol_detail(slug: str) -> dict:
            """단일 프로토콜 상세 (체인별 TVL 포함). Args: slug — 프로토콜 ID (aave, uniswap 등)."""
            return self._llama.get_protocol(slug)

        @self.mcp.tool()
        def defi_chains() -> dict:
            """체인별 TVL 합계 (Ethereum, BSC, Solana 등)."""
            return self._llama.get_chains()

        @self.mcp.tool()
        def defi_feargreed(days: int = 1) -> dict:
            """크립토 공포탐욕지수 (0=극도공포, 100=극도탐욕). Args: days — 1이면 현재, 30이면 30일 히스토리."""
            if days <= 1:
                return self._fg.get_current()
            return self._fg.get_history(days)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = DefiServer()
    server.mcp.run(transport="stdio")
