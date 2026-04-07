"""SEC EDGAR MCP Server — US Financial Disclosure (8 tools)."""
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
        def sec_xbrl_concept(ticker: str, concept: str, namespace: str = "us-gaap") -> dict:
            """SEC XBRL 임의 concept 조회. 6000+ US-GAAP concept (예: GrossProfit, InventoryNet, DeferredTaxAssets)."""
            return self._a.get_xbrl_concept(ticker, concept, namespace)
        @self.mcp.tool()
        def sec_list_concepts(ticker: str, filter_keyword: str = "") -> dict:
            """기업이 보고한 XBRL concept 목록 조회. 키워드로 필터 가능."""
            return self._a.list_xbrl_concepts(ticker, filter_keyword)
        @self.mcp.tool()
        def sec_filing_text(filing_url: str, max_chars: int = 5000) -> dict:
            """SEC 공시 본문 텍스트 추출 (HTML 제거)."""
            return self._a.get_filing_text(filing_url, max_chars)
        @self.mcp.tool()
        def sec_submission_metadata(ticker: str) -> dict:
            """SEC 기업 메타데이터 조회 (CIK, SIC코드, 최근 공시 목록, 기업 정보)."""
            return self._a.get_submission_metadata(ticker)
        @self.mcp.tool()
        def sec_insider_transactions(ticker: str, limit: int = 20) -> dict:
            """SEC 내부자 거래 (Form 4) 조회. 임원/이사 매수매도 내역."""
            return self._a.get_insider_transactions(ticker, limit)
        @self.mcp.tool()
        def sec_institutional_holders(ticker: str) -> dict:
            """SEC 기관투자자 보유 (13F) 조회."""
            return self._a.get_institutional_holders(ticker)
