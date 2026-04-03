"""Regulation & Compliance MCP Server — EU/US financial regulations (4 tools)."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.regulation_adapter import RegulationAdapter
logger = logging.getLogger(__name__)

class RegulationServer:
    def __init__(self):
        self._a = RegulationAdapter()
        self.mcp = FastMCP("regulation")
        self._register()
        logger.info("Regulation MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def regulation_eu_search(query: str, limit: int = 10) -> dict:
            """EU 법규 검색 (EUR-Lex). MiFID, GDPR, DORA, AI Act 등 유럽 금융·디지털 규제 검색."""
            return self._a.search_eu_regulations(query, limit)
        @self.mcp.tool()
        def regulation_eu_text(celex_number: str) -> dict:
            """EU 법규 본문 조회 (CELEX 번호). 예: 32016R0679 (GDPR), 32022R2554 (DORA)."""
            return self._a.get_regulation_text(celex_number)
        @self.mcp.tool()
        def regulation_key_financial() -> dict:
            """핵심 EU 금융 규제 19개 목록. MiFID II, GDPR, DORA, AI Act, MiCA, SFDR, PSD2, EMIR 등."""
            return self._a.get_key_financial_regulations()
        @self.mcp.tool()
        def regulation_finra_info() -> dict:
            """FINRA 주요 규정 참조 (미국). Suitability, Best Execution, Reg BI, AML 등 12개 규칙."""
            return self._a.search_finra_rules()
