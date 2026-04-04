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
        def energy_eia_series(route: str, series_id: str = "", frequency: str = "monthly", limit: int = 30) -> dict:
            """EIA API v2 범용 시계열 조회. route 예: petroleum/pri/spt, electricity/retail-sales."""
            return self._energy.get_eia_series(route, series_id, frequency, limit)
        @self.mcp.tool()
        def energy_electricity(limit: int = 30) -> dict:
            """미국 전력 소매 판매 데이터 (EIA). [주의: 응답 구조 차이로 빈 결과 가능]"""
            return self._energy.get_electricity_data(limit)
        @self.mcp.tool()
        def energy_bunker_fuel() -> dict:
            """벙커유(VLSFO proxy) 가격 — 해운업 원가 핵심 지표."""
            return self._energy.get_bunker_fuel_price()
        @self.mcp.tool()
        def energy_opec_production() -> dict:
            """OPEC 원유 생산량 (EIA 국제 데이터)."""
            return self._energy.get_opec_production()
        @self.mcp.tool()
        def energy_weather_forecast(lat: float = 37.5665, lon: float = 126.978, days: int = 7) -> dict:
            """날씨 예보 (Open-Meteo). 기본=서울. 기온, 강수량. 에너지 수요 예측용."""
            return self._weather.get_forecast(lat, lon, days)
        @self.mcp.tool()
        def energy_weather_cities() -> dict:
            """한국 전체 광역시도 날씨 (17개 시도). 에너지 수요/냉난방 분석용."""
            cities = [
                ("서울", 37.5665, 126.978), ("부산", 35.1796, 129.0756),
                ("대구", 35.8714, 128.6014), ("인천", 37.4563, 126.7052),
                ("광주", 35.1595, 126.8526), ("대전", 36.3504, 127.3845),
                ("울산", 35.5384, 129.3114), ("세종", 36.4800, 127.2890),
                ("수원", 37.2636, 127.0286), ("청주", 36.6424, 127.4890),
                ("천안", 36.8151, 127.1139), ("전주", 35.8242, 127.1480),
                ("목포", 34.8118, 126.3922), ("포항", 36.0190, 129.3435),
                ("창원", 35.2280, 128.6811), ("제주", 33.4996, 126.5312),
                ("강릉", 37.7519, 128.8761),
            ]
            results = {}
            for name, lat, lon in cities:
                results[name] = self._weather.get_forecast(lat, lon, 3)
            return {"success": True, "cities": results}
