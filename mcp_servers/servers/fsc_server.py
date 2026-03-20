"""
FSC MCP Server — 금융위원회 data.go.kr (2 tools).
"""
import logging, sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from fastmcp import FastMCP
from mcp_servers.adapters.phase2_adapters import FSCAdapter

logger = logging.getLogger(__name__)

class FSCServer:
    def __init__(self):
        self._fsc = FSCAdapter()
        self.mcp = FastMCP("fsc")
        self._register_tools()
        logger.info("FSC MCP Server initialized")

    def _register_tools(self):
        @self.mcp.tool()
        def fsc_stock_price(stock_code: str = "005930", rows: int = 20) -> dict:
            """금융위원회 주식시세 (data.go.kr). 종목코드 입력 → 일별 시세."""
            return self._fsc.get_stock_price(stock_code, rows)

        @self.mcp.tool()
        def fsc_bond_price(rows: int = 20) -> dict:
            """금융위원회 채권시세 (data.go.kr). 최근 채권 가격 정보."""
            return self._fsc.get_bond_price(rows)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    FSCServer().mcp.run(transport="stdio")
