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
            codes = {
                # 세계/한국
                "0": "World", "410": "Korea",
                # 북미
                "842": "USA", "124": "Canada", "484": "Mexico",
                # 동아시아
                "156": "China", "392": "Japan", "158": "Taiwan", "344": "Hong Kong", "446": "Macao",
                # 동남아시아 (ASEAN)
                "704": "Vietnam", "764": "Thailand", "360": "Indonesia", "458": "Malaysia",
                "608": "Philippines", "702": "Singapore", "104": "Myanmar", "116": "Cambodia",
                # 남아시아
                "356": "India", "050": "Bangladesh", "586": "Pakistan", "144": "Sri Lanka",
                # 유럽
                "276": "Germany", "250": "France", "826": "United Kingdom", "380": "Italy",
                "528": "Netherlands", "724": "Spain", "056": "Belgium", "616": "Poland",
                "203": "Czech Republic", "752": "Sweden", "756": "Switzerland",
                "040": "Austria", "578": "Norway", "208": "Denmark", "246": "Finland",
                "372": "Ireland", "643": "Russia", "792": "Turkey", "804": "Ukraine",
                # 중동
                "682": "Saudi Arabia", "784": "UAE", "634": "Qatar", "414": "Kuwait",
                "368": "Iraq", "364": "Iran", "376": "Israel",
                # 오세아니아
                "036": "Australia", "554": "New Zealand",
                # 남미
                "076": "Brazil", "032": "Argentina", "152": "Chile", "170": "Colombia", "604": "Peru",
                # 아프리카
                "710": "South Africa", "818": "Egypt", "566": "Nigeria",
            }
            return {"success": True, "count": len(codes), "codes": codes}
