"""Climate Data MCP Server — Open-Meteo, NASA GISS, NOAA ENSO (6 tools)."""
import logging, sys
from pathlib import Path
from typing import List
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.climate_adapter import ClimateAdapter
logger = logging.getLogger(__name__)

class ClimateServer:
    def __init__(self):
        self._a = ClimateAdapter()
        self.mcp = FastMCP("climate")
        self._register()
        logger.info("Climate MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def climate_historical_weather(latitude: float, longitude: float, start_date: str, end_date: str) -> dict:
            """특정 위치의 과거 날씨 데이터 (기온/강수/풍속). Open-Meteo archive API."""
            return self._a.get_historical_weather(latitude, longitude, start_date, end_date)
        @self.mcp.tool()
        def climate_temperature_anomaly(period: str = "monthly", limit: int = 0) -> dict:
            """NASA GISS 글로벌 기온 편차 (1951-1980 기준). limit=0이면 전체(1880년~) 반환."""
            return self._a.get_temperature_anomaly(period, limit)
        @self.mcp.tool()
        def climate_extreme_events(latitude: float, longitude: float, start_date: str, end_date: str) -> dict:
            """극한 기상 일수 카운트: 폭염(>35C), 한파(<-10C), 폭우(>50mm)."""
            return self._a.get_extreme_events(latitude, longitude, start_date, end_date)
        @self.mcp.tool()
        def climate_enso_index() -> dict:
            """NOAA 엘니뇨/라니냐 지수 (ONI). 전체 기간 반환."""
            return self._a.get_enso_index()
        @self.mcp.tool()
        def climate_city_comparison(cities: list) -> dict:
            """도시별 날씨 비교 (최근 365일). cities: [{"name":"Seoul","lat":37.5,"lon":127.0}, ...]"""
            return self._a.get_city_comparison(cities)
        @self.mcp.tool()
        def climate_crop_weather() -> dict:
            """주요 농업지역 작황 날씨 (미국 중서부/브라질/우크라이나). 최근 30일."""
            return self._a.get_crop_weather()
