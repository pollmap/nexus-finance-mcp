"""Politics MCP Server — 3 tools. DOGE 전담."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.phase3_adapters import PoliticsAdapter
logger = logging.getLogger(__name__)

class PoliticsServer:
    def __init__(self):
        self._a = PoliticsAdapter()
        self.mcp = FastMCP("politics")
        self._register()
        logger.info("Politics MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def politics_bills(age: str = "22", limit: int = 20) -> dict:
            """국회 발의 법안 목록. age: 22=22대 국회."""
            return self._a.get_bills(age, limit)
        @self.mcp.tool()
        def politics_recent_bills() -> dict:
            """최근 발의 법안 (22대 국회, 상위 10개)."""
            return self._a.get_bills("22", 10)
        @self.mcp.tool()
        def politics_finance_bills() -> dict:
            """금융 관련 법안 검색 안내."""
            return {"success": True, "note": "국회 API는 키워드 검색 미지원. 전체 법안 중 제목에서 '금융', '투자', '자본시장' 필터링 필요.", "api": "politics_bills로 전체 조회 후 클라이언트에서 필터링"}
