"""Health/Biotech MCP Server — FDA, ClinicalTrials, PubMed, WHO (5 tools)."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.health_adapter import HealthAdapter
logger = logging.getLogger(__name__)

class HealthServer:
    def __init__(self):
        self._a = HealthAdapter()
        self.mcp = FastMCP("health")
        self._register()
        logger.info("Health MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def health_fda_drugs(query: str, limit: int = 10) -> dict:
            """openFDA 의약품 검색 (브랜드명, 성분명, 적응증)."""
            return self._a.search_fda_drugs(query, limit)
        @self.mcp.tool()
        def health_fda_recalls(query: str, limit: int = 10) -> dict:
            """openFDA 리콜/집행조치 검색."""
            return self._a.search_fda_recalls(query, limit)
        @self.mcp.tool()
        def health_clinical_trials(query: str, status: str = "RECRUITING", limit: int = 10) -> dict:
            """ClinicalTrials.gov 임상시험 검색 (status: RECRUITING, COMPLETED, NOT_YET_RECRUITING)."""
            return self._a.search_clinical_trials(query, status, limit)
        @self.mcp.tool()
        def health_pubmed_search(query: str, limit: int = 10) -> dict:
            """PubMed 의학/생명과학 논문 검색."""
            return self._a.search_pubmed(query, limit)
        @self.mcp.tool()
        def health_who_indicators(indicator_code: str = "WHOSIS_000001", country: str = "KOR") -> dict:
            """WHO GHO 건강 지표 (WHOSIS_000001=기대수명, NCD_BMI_30A=비만율 등)."""
            return self._a.get_who_indicator(indicator_code, country)
