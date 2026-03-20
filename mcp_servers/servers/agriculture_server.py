"""Agriculture MCP Server — 4 tools. NEXUS(voyager) 전담."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.phase3_adapters import AgricultureAdapter
logger = logging.getLogger(__name__)

class AgricultureServer:
    def __init__(self):
        self._a = AgricultureAdapter()
        self.mcp = FastMCP("agriculture")
        self._register()
        logger.info("Agriculture MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def agri_kamis_prices(product_code: str = "100") -> dict:
            """KAMIS 농산물 가격 (100=채소, 200=과일, 300=수산, 400=축산)."""
            return self._a.get_kamis_prices(product_code)
        @self.mcp.tool()
        def agri_fao_info() -> dict:
            """FAO Food Price Index 정보."""
            return self._a.get_fao_food_price_index()
        @self.mcp.tool()
        def agri_product_codes() -> dict:
            """KAMIS 품목 분류 코드."""
            return {"success": True, "codes": {"100": "채소류", "200": "과일류", "300": "수산물", "400": "축산물", "500": "식량작물"}}
        @self.mcp.tool()
        def agri_snapshot() -> dict:
            """농산물 가격 종합 (채소+과일+축산)."""
            return {"vegetables": self._a.get_kamis_prices("100"), "fruits": self._a.get_kamis_prices("200"), "livestock": self._a.get_kamis_prices("400")}
