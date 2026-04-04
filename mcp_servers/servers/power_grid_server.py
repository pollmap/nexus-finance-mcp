"""Power Grid & Energy MCP Server — Electricity Maps, EIA, ENTSO-E (5 tools)."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.power_grid_adapter import PowerGridAdapter
logger = logging.getLogger(__name__)

class PowerGridServer:
    def __init__(self):
        self._a = PowerGridAdapter()
        self.mcp = FastMCP("power_grid")
        self._register()
        logger.info("Power Grid MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def power_grid_eu_generation(country_code: str = "DE") -> dict:
            """ENTSO-E 유럽 전력 발전원별 현황 (nuclear, wind, solar, gas, coal 등)."""
            return self._a.get_eu_generation(country_code)
        @self.mcp.tool()
        def power_grid_eu_price(country_code: str = "DE") -> dict:
            """ENTSO-E 유럽 전력 Day-ahead 가격 (EUR/MWh)."""
            return self._a.get_eu_price(country_code)
        @self.mcp.tool()
        def power_grid_carbon_intensity(zone: str = "DE") -> dict:
            """Electricity Maps 실시간 탄소 집약도 (gCO2eq/kWh) 및 재생에너지 비율."""
            return self._a.get_carbon_intensity(zone)
        @self.mcp.tool()
        def power_grid_nuclear_status() -> dict:
            """EIA 미국 원자력 발전량 일별 데이터 (최근 30일)."""
            return self._a.get_nuclear_status()
        @self.mcp.tool()
        def power_grid_renewable_forecast(zone: str = "DE") -> dict:
            """Electricity Maps 발전원별 전력 생산 분석 (풍력/태양광/수력/바이오매스 등)."""
            return self._a.get_renewable_forecast(zone)
