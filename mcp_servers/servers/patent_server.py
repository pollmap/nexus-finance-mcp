"""Patent MCP Server — 2 tools. DOGE(scholar) 전담."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.phase3_adapters import PatentAdapter
logger = logging.getLogger(__name__)

class PatentServer:
    def __init__(self):
        self._a = PatentAdapter()
        self.mcp = FastMCP("patent")
        self._register()
        logger.info("Patent MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def patent_search(keyword: str, limit: int = 10) -> dict:
            """한국 특허 검색 (KIPRIS). 키워드로 특허 제목/출원인/날짜 조회."""
            return self._a.search_patents(keyword, limit)
        @self.mcp.tool()
        def patent_trending(keyword: str = "인공지능") -> dict:
            """최근 AI/핀테크/로봇 관련 특허 트렌드."""
            return self._a.search_patents(keyword, 15)
