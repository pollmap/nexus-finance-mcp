"""
Asian Markets MCP Server — China/Taiwan/Hong Kong (8 tools).

Covers SSE, SZSE, TWSE, and HKEX via yfinance.
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP
from mcp_servers.adapters.asia_market_adapter import AsiaMarketAdapter

logger = logging.getLogger(__name__)


class AsiaMarketServer:
    def __init__(self):
        self._adapter = AsiaMarketAdapter()
        self.mcp = FastMCP("asia-market")
        self._register_tools()
        logger.info("Asia Market MCP Server initialized (8 tools)")

    def _register_tools(self):

        @self.mcp.tool()
        def asia_china_quote(symbol: str = "600519.SS") -> dict:
            """중국 주식 시세. symbol: 600519.SS=마오타이, 000001.SZ=평안은행, 601398.SS=ICBC."""
            return self._adapter.get_china_stock_quote(symbol)

        @self.mcp.tool()
        def asia_china_index() -> dict:
            """중국 증시 지수 — SSE Composite (上证综指) + SZSE Component (深证成指)."""
            return self._adapter.get_china_index()

        @self.mcp.tool()
        def asia_china_history(symbol: str = "600519.SS", period: str = "1y") -> dict:
            """중국 주식 과거 데이터 (OHLCV). period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, ytd, max."""
            return self._adapter.get_china_stock_history(symbol, period)

        @self.mcp.tool()
        def asia_taiwan_quote(symbol: str = "2330.TW") -> dict:
            """대만 주식 시세. symbol: 2330.TW=TSMC, 2317.TW=혼하이, 2454.TW=미디어텍."""
            return self._adapter.get_taiwan_stock_quote(symbol)

        @self.mcp.tool()
        def asia_taiwan_index() -> dict:
            """대만 가권지수 (TAIEX, 加權指數)."""
            return self._adapter.get_taiwan_index()

        @self.mcp.tool()
        def asia_hk_quote(symbol: str = "0700.HK") -> dict:
            """홍콩 주식 시세. symbol: 0700.HK=텐센트, 9988.HK=알리바바, 1299.HK=AIA."""
            return self._adapter.get_hk_stock_quote(symbol)

        @self.mcp.tool()
        def asia_hk_index() -> dict:
            """홍콩 항셍지수 (Hang Seng Index, 恒生指數)."""
            return self._adapter.get_hk_index()

        @self.mcp.tool()
        def asia_market_overview() -> dict:
            """중국+대만+홍콩 아시아 3대 시장 지수 종합 현황."""
            china = self._adapter.get_china_index()
            taiwan = self._adapter.get_taiwan_index()
            hk = self._adapter.get_hk_index()
            return {
                "success": True,
                "overview": "Greater China Market Overview",
                "china": china,
                "taiwan": taiwan,
                "hong_kong": hk,
            }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    AsiaMarketServer().mcp.run(transport="stdio")
