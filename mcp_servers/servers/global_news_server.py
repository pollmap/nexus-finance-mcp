"""
Global News MCP Server — GDELT (3 tools).
"""
import logging, sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from fastmcp import FastMCP
from mcp_servers.adapters.gdelt_academic_adapter import GDELTAdapter

logger = logging.getLogger(__name__)

class GlobalNewsServer:
    def __init__(self):
        self._gdelt = GDELTAdapter()
        self.mcp = FastMCP("global-news")
        self._register_tools()
        logger.info("Global News MCP Server initialized")

    def _register_tools(self):
        @self.mcp.tool()
        def gdelt_search(query: str, max_records: int = 20, lang: str = "", timespan: str = "7d") -> dict:
            """GDELT 글로벌 뉴스 검색 (100+언어, 15분 업데이트). lang: korean, english 등. timespan: 1d,7d,30d."""
            return self._gdelt.search_articles(query, max_records=max_records, sourcelang=lang, timespan=timespan)

        @self.mcp.tool()
        def gdelt_timeline(query: str, timespan: str = "30d") -> dict:
            """GDELT 뉴스량 타임라인 — 키워드 관련 기사 수 추이."""
            return self._gdelt.get_timeline(query, timespan)

        @self.mcp.tool()
        def gdelt_korea_news(query: str = "South Korea economy", max_records: int = 15) -> dict:
            """한국 관련 글로벌 뉴스 (영어권 매체에서 한국을 어떻게 보도하는지)."""
            return self._gdelt.search_articles(f"{query} South Korea", max_records=max_records, sourcelang="english", timespan="7d")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    GlobalNewsServer().mcp.run(transport="stdio")
