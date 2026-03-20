"""
OnChain MCP Server — Etherscan V2 on-chain data.

Tools (3):
- onchain_balance: ETH 잔고 조회
- onchain_transactions: 최근 트랜잭션
- onchain_gas: 현재 가스비
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP
from mcp_servers.adapters.etherscan_adapter import EtherscanAdapter

logger = logging.getLogger(__name__)


class OnChainServer:
    def __init__(self):
        self._eth = EtherscanAdapter()
        self.mcp = FastMCP("onchain")
        self._register_tools()
        logger.info("OnChain MCP Server initialized")

    def _register_tools(self):

        @self.mcp.tool()
        def onchain_balance(address: str) -> dict:
            """ETH 잔고 조회. Args: address — 이더리움 주소 (0x...)."""
            return self._eth.get_balance(address)

        @self.mcp.tool()
        def onchain_transactions(address: str, limit: int = 10) -> dict:
            """최근 트랜잭션 조회. Args: address — 주소, limit — 건수."""
            return self._eth.get_transactions(address, limit)

        @self.mcp.tool()
        def onchain_gas() -> dict:
            """현재 이더리움 가스비 (Safe/Propose/Fast gwei)."""
            return self._eth.get_gas_price()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = OnChainServer()
    server.mcp.run(transport="stdio")
