"""Disaster MCP Server — USGS, NASA EONET, GDACS (6 tools)."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.disaster_adapter import DisasterAdapter
logger = logging.getLogger(__name__)

class DisasterServer:
    def __init__(self):
        self._a = DisasterAdapter()
        self.mcp = FastMCP("disaster")
        self._register()
        logger.info("Disaster MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def disaster_earthquakes(min_magnitude: float = 4.0, days: int = 30, limit: int = 50) -> dict:
            """USGS 지진 데이터 (규모, 위치, 좌표, 쓰나미 여부)."""
            return self._a.get_earthquakes(min_magnitude, days, limit)
        @self.mcp.tool()
        def disaster_volcanoes(days: int = 60, limit: int = 20) -> dict:
            """NASA EONET 화산 활동 이벤트."""
            return self._a.get_volcanoes(days, limit)
        @self.mcp.tool()
        def disaster_wildfires(days: int = 30, limit: int = 20) -> dict:
            """NASA EONET 산불 이벤트."""
            return self._a.get_wildfires(days, limit)
        @self.mcp.tool()
        def disaster_floods(days: int = 30) -> dict:
            """GDACS 홍수 이벤트 (alert level, 국가, 좌표)."""
            return self._a.get_floods(days)
        @self.mcp.tool()
        def disaster_active_events() -> dict:
            """GDACS 현재 활성 재난 이벤트 (최근 7일, 모든 유형)."""
            return self._a.get_active_events()
        @self.mcp.tool()
        def disaster_history(year: int = 2026) -> dict:
            """연간 재난 통계 요약 — 지진 규모별 건수 + EONET 카테고리별 이벤트 수."""
            return self._a.get_disaster_summary(year)
