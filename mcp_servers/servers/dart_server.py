"""
DART MCP Server - OpenDART 한국 기업공시 데이터.

Provides Korean corporate disclosure data:
- Company info (기업개황)
- Financial statements (재무제표)
- Financial ratios (재무비율)
- Major shareholders (대주주)
- Company search (기업검색)

Data source: OpenDART (https://opendart.fss.or.kr)
Requires: DART_API_KEY in .env

Run standalone: python -m mcp_servers.servers.dart_server
"""
import logging
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.core.base_server import BaseMCPServer
from mcp_servers.adapters.dart_adapter import DARTAdapter

logger = logging.getLogger(__name__)


class DARTServer(BaseMCPServer):
    """DART MCP Server wrapping DARTAdapter for OpenDART API access."""

    @property
    def name(self) -> str:
        return "dart"

    def __init__(self, **kwargs):
        self._adapter = None
        try:
            self._adapter = DARTAdapter()
            if not self._adapter._dart:
                logger.warning("DART adapter initialized but OpenDartReader client is None")
        except Exception as e:
            logger.error(f"Failed to initialize DART adapter: {e}")
        super().__init__(**kwargs)

    def _register_tools(self):

        adapter = self._adapter

        @self.mcp.tool()
        def dart_company_info(stock_code: str) -> dict:
            """
            기업개황 조회 (OpenDART).

            Args:
                stock_code: 종목코드 (예: 005930 = 삼성전자)

            Returns:
                회사명, 대표자, 업종, 설립일, 상장일 등 기본 정보
            """
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.get_company_info(stock_code)

        @self.mcp.tool()
        def dart_financial_statements(
            stock_code: str,
            year: Optional[int] = None,
            report_type: str = "11011",
        ) -> dict:
            """
            재무제표 조회 (OpenDART).

            Args:
                stock_code: 종목코드 (예: 005930)
                year: 사업연도 (기본: 전년도)
                report_type: 보고서 유형
                    - 11011: 사업보고서 (연간)
                    - 11012: 반기보고서
                    - 11013: 1분기보고서
                    - 11014: 3분기보고서

            Returns:
                재무상태표, 손익계산서 등 재무제표 항목
            """
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.get_financial_statements(stock_code, year, report_type)

        @self.mcp.tool()
        def dart_financial_ratios(
            stock_code: str,
            year: Optional[int] = None,
        ) -> dict:
            """
            주요 재무비율 계산 (OpenDART 재무제표 기반).

            Args:
                stock_code: 종목코드 (예: 005930)
                year: 사업연도 (기본: 전년도)

            Returns:
                ROE, ROA, 영업이익률, 순이익률, 부채비율 등
            """
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.get_financial_ratios(stock_code, year)

        @self.mcp.tool()
        def dart_major_shareholders(stock_code: str) -> dict:
            """
            대주주 현황 조회 (OpenDART).

            Args:
                stock_code: 종목코드 (예: 005930)

            Returns:
                대주주 목록 (이름, 지분율, 변동 내역)
            """
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.get_major_shareholders(stock_code)

        @self.mcp.tool()
        def dart_search_company(keyword: str) -> dict:
            """
            기업 검색 (OpenDART).

            Args:
                keyword: 회사명 (예: 삼성, 카카오, LG)

            Returns:
                매칭 기업 목록 (회사명, 종목코드, 법인코드)
            """
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.search_company(keyword)

        @self.mcp.tool()
        def dart_cash_flow(
            stock_code: str,
            year: Optional[int] = None,
            report_type: str = "11011",
        ) -> dict:
            """
            현금흐름표 조회 (OpenDART). OCF, 투자CF, 재무CF, FCF 분석용.

            Args:
                stock_code: 종목코드 (예: 005930)
                year: 사업연도 (기본: 전년도)
                report_type: 보고서 유형 (11011=사업보고서)
            """
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.get_cash_flow(stock_code, year, report_type)

        @self.mcp.tool()
        def dart_dividend(
            stock_code: str,
            year: Optional[int] = None,
        ) -> dict:
            """
            배당 현황 조회 (OpenDART). 배당금, 배당률, 배당수익률.

            Args:
                stock_code: 종목코드 (예: 005930)
                year: 사업연도 (기본: 전년도)
            """
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.get_dividend(stock_code, year)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = DARTServer()
    server.mcp.run(transport="stdio")
