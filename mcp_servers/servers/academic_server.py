"""
Academic MCP Server — arXiv + Semantic Scholar + OpenAlex (5 tools).
DOGE의 서브에이전트 SCHOLAR가 사용.
"""
import logging, sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from fastmcp import FastMCP
from mcp_servers.adapters.gdelt_academic_adapter import AcademicAdapter

logger = logging.getLogger(__name__)

class AcademicServer:
    def __init__(self):
        self._academic = AcademicAdapter()
        self.mcp = FastMCP("academic")
        self._register_tools()
        logger.info("Academic MCP Server initialized")

    def _register_tools(self):
        @self.mcp.tool()
        def academic_arxiv(query: str, limit: int = 10) -> dict:
            """arXiv 논문 검색. AI, 금융공학, 물리학 등 프리프린트."""
            return self._academic.search_arxiv(query, limit)

        @self.mcp.tool()
        def academic_semantic_scholar(query: str, limit: int = 10) -> dict:
            """Semantic Scholar 검색 (200M+ 논문). 인용 수 포함."""
            return self._academic.search_semantic_scholar(query, limit)

        @self.mcp.tool()
        def academic_openalex(query: str, limit: int = 10) -> dict:
            """OpenAlex 검색 (250M+ 작품, CC0). DOI + OA 여부 포함."""
            return self._academic.search_openalex(query, limit)

        @self.mcp.tool()
        def academic_multi_search(query: str, limit: int = 5) -> dict:
            """3개 소스 동시 검색 (arXiv + Semantic Scholar + OpenAlex)."""
            results = {
                "arxiv": self._academic.search_arxiv(query, limit),
                "semantic_scholar": self._academic.search_semantic_scholar(query, limit),
                "openalex": self._academic.search_openalex(query, limit),
            }
            total = sum(r.get("count", 0) for r in results.values() if r.get("success"))
            return {"success": True, "query": query, "total_papers": total, "sources": results}

        @self.mcp.tool()
        def academic_trending(field: str = "artificial intelligence") -> dict:
            """최신 트렌딩 논문 — OpenAlex에서 최근 인용 급증 논문."""
            return self._academic.search_openalex(field, limit=15)

        @self.mcp.tool()
        def academic_paper_detail(arxiv_id: str) -> dict:
            """arXiv 논문 상세 조회. 전체 초록, 저자, 카테고리, PDF URL."""
            return self._academic.get_paper_detail(arxiv_id)

        @self.mcp.tool()
        def academic_citations(arxiv_id: str = "", doi: str = "", title: str = "") -> dict:
            """논문 인용 네트워크 (OpenAlex). cited_by_count + 인용한 논문 + 참조 논문 각 10개."""
            return self._academic.get_citations(arxiv_id=arxiv_id, doi=doi, title=title)

        @self.mcp.tool()
        def academic_author(author_name: str) -> dict:
            """연구자 프로필 (OpenAlex). h-index, 소속, 인용수, 최근 논문 5개."""
            return self._academic.get_author_info(author_name)

        @self.mcp.tool()
        def academic_concepts(query: str, limit: int = 10) -> dict:
            """학술 개념/토픽 검색 (OpenAlex). 연구 분야 탐색용."""
            return self._academic.search_concepts(query, limit)



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    AcademicServer().mcp.run(transport="stdio")
