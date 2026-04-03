"""Research MCP Server — Korean Academic & Policy Research (6 tools)."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.research_adapter import ResearchAdapter
logger = logging.getLogger(__name__)

class ResearchServer:
    def __init__(self):
        self._a = ResearchAdapter()
        self.mcp = FastMCP("research")
        self._register()
        logger.info("Research MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def research_riss(query: str, page: int = 1, count: int = 10) -> dict:
            """RISS 학술논문 검색 (국내 학위/학술지). [주의: API키 별도 승인 필요 — riss.kr/openAPI]"""
            return self._a.search_riss(query, page, count)
        @self.mcp.tool()
        def research_nkis(query: str, page: int = 1, count: int = 10) -> dict:
            """NKIS 국책연구원 27개 보고서 검색 (KDI, KIEP, KIF 등)."""
            return self._a.search_nkis(query, page, count)
        @self.mcp.tool()
        def research_prism(query: str, page: int = 1, count: int = 10) -> dict:
            """PRISM 정부 정책연구과제 검색."""
            return self._a.search_prism(query, page, count)
        @self.mcp.tool()
        def research_nl(query: str, page: int = 1, count: int = 10) -> dict:
            """국립중앙도서관 서지정보 검색 (ISBN, 도서, 자료)."""
            return self._a.search_nl(query, page, count)
        @self.mcp.tool()
        def research_nanet(query: str, page: int = 1, count: int = 10) -> dict:
            """국회전자도서관 K-Scholar 법률/입법자료 검색."""
            return self._a.search_nanet(query, page, count)
        @self.mcp.tool()
        def research_scholar(query: str, count: int = 5) -> dict:
            """Google Scholar 글로벌 학술검색 (rate limit 주의, 5건 기본)."""
            return self._a.search_scholar(query, count)
