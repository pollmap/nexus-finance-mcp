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
            codes = {
                # 대분류
                "100": "채소류", "200": "과일류", "300": "수산물", "400": "축산물", "500": "식량작물",
                # 채소 세부
                "111": "배추", "112": "무", "141": "건고추", "142": "풋고추",
                "143": "양파", "144": "대파", "151": "시금치", "152": "상추",
                "153": "깻잎", "154": "호박", "155": "오이", "156": "토마토",
                "157": "당근", "161": "감자", "162": "고구마",
                # 과일 세부
                "211": "사과", "212": "배", "213": "포도", "214": "복숭아",
                "215": "감귤", "216": "참외", "217": "수박", "218": "딸기",
                "221": "바나나", "222": "키위",
                # 축산 세부
                "411": "쇠고기", "412": "돼지고기", "413": "닭고기", "414": "계란",
                "415": "우유",
                # 수산 세부
                "311": "고등어", "312": "갈치", "313": "오징어", "314": "명태",
                "315": "멸치", "316": "새우",
                # 식량작물 세부
                "511": "쌀", "512": "찹쌀", "521": "콩", "522": "팥",
            }
            return {"success": True, "count": len(codes), "codes": codes}
        @self.mcp.tool()
        def agri_snapshot() -> dict:
            """농산물 가격 종합 (채소+과일+축산)."""
            return {"vegetables": self._a.get_kamis_prices("100"), "fruits": self._a.get_kamis_prices("200"), "livestock": self._a.get_kamis_prices("400")}
        @self.mcp.tool()
        def agri_fao_production(item_code: str = "0015", area_code: str = "410", limit: int = 20) -> dict:
            """FAOSTAT 농업 생산량 (item: 0015=밀, 0027=쌀, 0056=옥수수. area: 410=한국)."""
            return self._a.get_fao_production(item_code, area_code, limit)
        @self.mcp.tool()
        def agri_fao_trade(item_code: str = "0015", area_code: str = "410", limit: int = 20) -> dict:
            """FAOSTAT 농산물 무역 데이터."""
            return self._a.get_fao_trade(item_code, area_code, limit)
        @self.mcp.tool()
        def agri_usda_psd(commodity: str = "Rice, Milled", country: str = "Korea, South") -> dict:
            """USDA PSD 생산/공급/배분 데이터."""
            return self._a.get_usda_psd(commodity, country)
