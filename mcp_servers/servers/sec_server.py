"""SEC EDGAR MCP Server — US Financial Disclosure (3 tools)."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.sec_adapter import SECAdapter
logger = logging.getLogger(__name__)

class SECServer:
    def __init__(self):
        self._a = SECAdapter()
        self.mcp = FastMCP("sec")
        self._register()
        logger.info("SEC EDGAR MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def sec_company_filings(query: str, form_type: str = "10-K", limit: int = 10) -> dict:
            """SEC EDGAR 공시 검색 (10-K, 10-Q, 8-K 등)."""
            return self._a.search_filings(query, form_type, limit)
        @self.mcp.tool()
        def sec_company_facts(ticker: str) -> dict:
            """SEC XBRL 재무데이터 자동 추출 (Revenue, NetIncome, Assets 등 시계열)."""
            return self._a.get_company_facts(ticker)
        @self.mcp.tool()
        def sec_filing_text(filing_url: str, max_chars: int = 5000) -> dict:
            """SEC 공시 본문 텍스트 추출 (HTML 제거)."""
            return self._a.get_filing_text(filing_url, max_chars)
