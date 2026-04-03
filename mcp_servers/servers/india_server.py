"""
India Market MCP Server — NSE/BSE (3 tools).

Covers Nifty 50, Sensex, and individual stock data via yfinance.
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP
from mcp_servers.adapters.india_adapter import IndiaAdapter

logger = logging.getLogger(__name__)


class IndiaServer:
    def __init__(self):
        self._adapter = IndiaAdapter()
        self.mcp = FastMCP("india-market")
        self._register_tools()
        logger.info("India Market MCP Server initialized (3 tools)")

    def _register_tools(self):

        @self.mcp.tool()
        def india_stock_quote(symbol: str = "RELIANCE.NS") -> dict:
            """인도 주식 시세. symbol: RELIANCE.NS=릴라이언스, TCS.NS=TCS, INFY.NS=인포시스, HDFCBANK.NS=HDFC."""
            return self._adapter.get_india_stock_quote(symbol)

        @self.mcp.tool()
        def india_index() -> dict:
            """인도 증시 지수 — Nifty 50 + BSE Sensex."""
            return self._adapter.get_india_index()

        @self.mcp.tool()
        def india_stock_history(symbol: str = "RELIANCE.NS", period: str = "1y") -> dict:
            """인도 주식 과거 데이터 (OHLCV). period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, ytd, max."""
            return self._adapter.get_india_stock_history(symbol, period)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    IndiaServer().mcp.run(transport="stdio")
