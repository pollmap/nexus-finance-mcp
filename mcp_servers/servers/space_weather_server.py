"""Space Weather MCP Server — NOAA SWPC, NASA DONKI, SILSO (5 tools)."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.space_weather_adapter import SpaceWeatherAdapter
logger = logging.getLogger(__name__)

class SpaceWeatherServer:
    def __init__(self):
        self._a = SpaceWeatherAdapter()
        self.mcp = FastMCP("space_weather")
        self._register()
        logger.info("Space Weather MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def space_sunspot_data(period: str = "monthly") -> dict:
            """SILSO 월별 태양흑점 수 (최근 120개월). 태양 활동 주기 분석."""
            return self._a.get_sunspot_data(period)
        @self.mcp.tool()
        def space_solar_flares(days: int = 30) -> dict:
            """NASA DONKI 태양 플레어 이벤트 (classType, 시작/피크 시각)."""
            return self._a.get_solar_flares(days)
        @self.mcp.tool()
        def space_geomagnetic() -> dict:
            """NOAA SWPC 행성 Kp 지수 — 지자기 폭풍 수준 (0~9)."""
            return self._a.get_geomagnetic_index()
        @self.mcp.tool()
        def space_solar_wind() -> dict:
            """NOAA SWPC 태양풍 플라즈마 (밀도, 속도, 온도) 최근 48건."""
            return self._a.get_solar_wind()
        @self.mcp.tool()
        def space_cme_events(days: int = 30) -> dict:
            """NASA DONKI 코로나 질량 방출(CME) 이벤트."""
            return self._a.get_cme_events(days)
