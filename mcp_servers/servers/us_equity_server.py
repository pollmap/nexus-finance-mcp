"""
US Equity MCP Server — Finnhub (4 tools).
"""
import logging, sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from fastmcp import FastMCP
from mcp_servers.adapters.phase2_adapters import FinnhubAdapter

logger = logging.getLogger(__name__)

class USEquityServer:
    def __init__(self):
        self._fh = FinnhubAdapter()
        self.mcp = FastMCP("us-equity")
        self._register_tools()
        logger.info("US Equity MCP Server initialized")

    def _register_tools(self):
        @self.mcp.tool()
        def us_stock_quote(symbol: str = "AAPL") -> dict:
            """미국 주식 실시간 시세 (Finnhub). symbol: AAPL, MSFT, NVDA 등."""
            return self._fh.get_quote(symbol)

        @self.mcp.tool()
        def us_company_profile(symbol: str = "AAPL") -> dict:
            """미국 기업 프로필 (시총, 섹터, IPO일, 웹사이트)."""
            return self._fh.get_company_profile(symbol)

        @self.mcp.tool()
        def us_economic_calendar() -> dict:
            """미국 경제 캘린더 — FOMC, 고용, CPI 등 주요 이벤트."""
            return self._fh.get_economic_calendar()

        @self.mcp.tool()
        def us_market_news(category: str = "general") -> dict:
            """미국 시장 뉴스 (Finnhub). category: general, forex, crypto, merger."""
            return self._fh.get_market_news(category)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    USEquityServer().mcp.run(transport="stdio")
