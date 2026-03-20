"""Trade MCP Server — 3 tools. NEXUS(voyager) 전담."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.phase3_adapters import TradeAdapter
logger = logging.getLogger(__name__)

class TradeServer:
    def __init__(self):
        self._a = TradeAdapter()
        self.mcp = FastMCP("trade")
        self._register()
        logger.info("Trade MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def trade_korea_exports(partner: str = "0", hs_code: str = "TOTAL", year: str = "2024") -> dict:
            """한국 수출 데이터 (UN Comtrade). partner 0=세계, 842=미국, 156=중국."""
            return self._a.get_trade_data("410", partner, "X", hs_code, year)
        @self.mcp.tool()
        def trade_korea_imports(partner: str = "0", hs_code: str = "TOTAL", year: str = "2024") -> dict:
            """한국 수입 데이터."""
            return self._a.get_trade_data("410", partner, "M", hs_code, year)
        @self.mcp.tool()
        def trade_country_codes() -> dict:
            """주요 국가 코드 (UN Comtrade)."""
            return {"success": True, "codes": {"0": "World", "410": "Korea", "842": "USA", "156": "China", "392": "Japan", "276": "Germany", "704": "Vietnam", "158": "Taiwan"}}
