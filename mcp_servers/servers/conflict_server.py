"""Conflict & Geopolitical Risk MCP Server — UCDP, ACLED, GPI (5 tools)."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.conflict_adapter import ConflictAdapter
logger = logging.getLogger(__name__)

class ConflictServer:
    def __init__(self):
        self._a = ConflictAdapter()
        self.mcp = FastMCP("conflict")
        self._register()
        logger.info("Conflict MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def conflict_active_wars(year: int = 0) -> dict:
            """UCDP 활성 무력 충돌 이벤트 (state-based, non-state, one-sided). year=0이면 올해."""
            return self._a.get_active_conflicts(year if year > 0 else None)
        @self.mcp.tool()
        def conflict_battle_deaths(country: str = "", years: int = 5) -> dict:
            """UCDP 전투 사망자 연도별 시계열. 국가 미지정 시 글로벌 집계."""
            return self._a.get_battle_deaths(country if country else None, years)
        @self.mcp.tool()
        def conflict_country_risk(country_name: str = "Ukraine") -> dict:
            """국가별 분쟁 위험도 평가 — UCDP 3년 이벤트 기반 (low/medium/high/critical)."""
            return self._a.get_country_risk(country_name)
        @self.mcp.tool()
        def conflict_peace_index() -> dict:
            """Global Peace Index 2024 — 가장 평화로운/위험한 국가 top/bottom 10."""
            return self._a.get_peace_index()
        @self.mcp.tool()
        def conflict_geopolitical_events(query: str = "Ukraine", days: int = 30) -> dict:
            """분쟁 관련 최근 이벤트 검색 (ACLED 키 있으면 ACLED, 없으면 UCDP)."""
            return self._a.get_geopolitical_events(query, days)
