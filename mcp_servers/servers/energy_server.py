"""Energy MCP Server — 5 tools. EIA + Open-Meteo weather. NEXUS(voyager) 전담."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.phase3_adapters import EnergyAdapter, WeatherAdapter
logger = logging.getLogger(__name__)

class EnergyServer:
    def __init__(self):
        self._energy = EnergyAdapter()
        self._weather = WeatherAdapter()
        self.mcp = FastMCP("energy")
        self._register()
        logger.info("Energy MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def energy_crude_oil(limit: int = 30) -> dict:
            """WTI 원유 가격 (EIA). 일별 스팟."""
            return self._energy.get_crude_oil_price(limit)
        @self.mcp.tool()
        def energy_natural_gas(limit: int = 30) -> dict:
            """Henry Hub 천연가스 가격 (EIA)."""
            return self._energy.get_natural_gas_price(limit)
        @self.mcp.tool()
        def energy_price_snapshot() -> dict:
            """에너지 가격 종합 (원유 + 천연가스)."""
            return {"oil": self._energy.get_crude_oil_price(5), "gas": self._energy.get_natural_gas_price(5)}
        @self.mcp.tool()
        def weather_forecast(lat: float = 37.5665, lon: float = 126.978, days: int = 7) -> dict:
            """날씨 예보 (Open-Meteo). 기본=서울. 기온, 강수량."""
            return self._weather.get_forecast(lat, lon, days)
        @self.mcp.tool()
        def weather_major_cities() -> dict:
            """한국 주요 도시 날씨 (서울/부산/대전/제주)."""
            cities = [("서울", 37.5665, 126.978), ("부산", 35.1796, 129.0756),
                      ("대전", 36.3504, 127.3845), ("제주", 33.4996, 126.5312)]
            results = {}
            for name, lat, lon in cities:
                results[name] = self._weather.get_forecast(lat, lon, 3)
            return {"success": True, "cities": results}
