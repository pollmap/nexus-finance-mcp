"""EDINET MCP Server — Japanese Corporate Disclosure (4 tools)."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.edinet_adapter import EDINETAdapter
logger = logging.getLogger(__name__)

class EDINETServer:
    def __init__(self):
        self._a = EDINETAdapter()
        self.mcp = FastMCP("edinet")
        self._register()
        logger.info("EDINET MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def edinet_filings(date: str = "", filing_type: str = "2") -> dict:
            """EDINET 일본 기업공시 검색 (일자별). date: YYYY-MM-DD (기본=오늘)."""
            return self._a.search_filings(date or None, filing_type)
        @self.mcp.tool()
        def edinet_company(edinet_code: str) -> dict:
            """EDINET 기업별 최근 공시 조회. edinet_code: E02529(토요타) 등."""
            return self._a.get_company_filings(edinet_code)
        @self.mcp.tool()
        def edinet_document(doc_id: str) -> dict:
            """EDINET 문서 상세 조회. doc_id: S100XXXX."""
            return self._a.get_document_info(doc_id)
        @self.mcp.tool()
        def edinet_search(security_code: str) -> dict:
            """증권코드로 EDINET 기업 검색. security_code: 7203(토요타), 6758(소니) 등."""
            return self._a.search_by_security_code(security_code)
