"""Aviation MCP Server — 3 tools. NEXUS(voyager) 전담."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.phase3_adapters import AviationAdapter
logger = logging.getLogger(__name__)

class AviationServer:
    def __init__(self):
        self._a = AviationAdapter()
        self.mcp = FastMCP("aviation")
        self._register()
        logger.info("Aviation MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def aviation_departures(airport: str = "RKSI", hours: int = 12) -> dict:
            """공항 출발편 조회 (OpenSky). RKSI=인천, RKSS=김포, RKPC=제주."""
            return self._a.get_flights_by_airport(airport, hours)
        @self.mcp.tool()
        def aviation_live_aircraft() -> dict:
            """현재 비행 중인 항공기 (전세계 상위 50)."""
            return self._a.get_all_states()
        @self.mcp.tool()
        def aviation_korea_airports() -> dict:
            """한국 주요 공항 ICAO 코드."""
            return {"success": True, "airports": [
                {"name": "인천국제공항", "icao": "RKSI", "iata": "ICN", "city": "인천"},
                {"name": "김포국제공항", "icao": "RKSS", "iata": "GMP", "city": "서울"},
                {"name": "제주국제공항", "icao": "RKPC", "iata": "CJU", "city": "제주"},
                {"name": "김해국제공항", "icao": "RKPK", "iata": "PUS", "city": "부산"},
                {"name": "대구국제공항", "icao": "RKTN", "iata": "TAE", "city": "대구"},
                {"name": "청주국제공항", "icao": "RKTU", "iata": "CJJ", "city": "청주"},
                {"name": "무안국제공항", "icao": "RKJB", "iata": "MWX", "city": "무안"},
                {"name": "양양국제공항", "icao": "RKNY", "iata": "YNY", "city": "양양"},
                {"name": "광주공항", "icao": "RKJJ", "iata": "KWJ", "city": "광주"},
                {"name": "울산공항", "icao": "RKPU", "iata": "USN", "city": "울산"},
                {"name": "여수공항", "icao": "RKJY", "iata": "RSU", "city": "여수"},
                {"name": "포항공항", "icao": "RKTH", "iata": "KPO", "city": "포항"},
                {"name": "사천공항", "icao": "RKPS", "iata": "HIN", "city": "사천"},
                {"name": "원주공항", "icao": "RKNW", "iata": "WJU", "city": "원주"},
            ]}
