"""
Real Estate Transaction MCP Server — MOLIT 실거래가 (2 tools).
"""
import logging, sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from fastmcp import FastMCP
from mcp_servers.adapters.phase2_adapters import MOLITAdapter

logger = logging.getLogger(__name__)

class RealEstateTransServer:
    def __init__(self):
        self._molit = MOLITAdapter()
        self.mcp = FastMCP("realestate-trans")
        self._register_tools()
        logger.info("Real Estate Transaction MCP Server initialized")

    def _register_tools(self):
        @self.mcp.tool()
        def realestate_apt_trades(sigungu_code: str = "11110", year_month: str = "") -> dict:
            """아파트 매매 실거래가 조회 (국토부). sigungu_code: 11110=종로, 11140=중구, 41135=성남분당."""
            return self._molit.get_apt_trades(sigungu_code, year_month)

        @self.mcp.tool()
        def realestate_sigungu_codes() -> dict:
            """주요 시군구 코드 목록."""
            codes = {
                "11110": "서울 종로구", "11140": "서울 중구", "11170": "서울 용산구",
                "11200": "서울 성동구", "11215": "서울 광진구", "11230": "서울 동대문구",
                "11260": "서울 중랑구", "11290": "서울 성북구", "11305": "서울 강북구",
                "11320": "서울 도봉구", "11350": "서울 노원구", "11380": "서울 은평구",
                "11410": "서울 서대문구", "11440": "서울 마포구", "11470": "서울 양천구",
                "11500": "서울 강서구", "11530": "서울 구로구", "11545": "서울 금천구",
                "11560": "서울 영등포구", "11590": "서울 동작구", "11620": "서울 관악구",
                "11650": "서울 서초구", "11680": "서울 강남구", "11710": "서울 송파구",
                "11740": "서울 강동구",
                "41135": "성남 분당구", "41463": "수원 영통구", "41285": "용인 수지구",
            }
            return {"success": True, "count": len(codes), "codes": codes}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    RealEstateTransServer().mcp.run(transport="stdio")
