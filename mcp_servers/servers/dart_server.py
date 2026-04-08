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
            재무제표 조회 (OpenDART). 1회 호출 시 당기/전기/전전기 최대 3개년 반환.
            5개년 데이터가 필요하면 year를 바꿔 2회 호출 후 병합하세요.
            금액은 콤마 포함 문자열 (예: "69,458,073,000,000").

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
            1회 호출 시 최대 3개년. 금액은 콤마 포함 문자열.

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


        # === Phase 13: DART Report 확장 (9개 신규 도구) ===

        @self.mcp.tool()
        def dart_executives(stock_code: str, year: Optional[int] = None) -> dict:
            """임원현황 조회 (OpenDART). 이사/감사/집행임원 목록, 직위, 성명, 재직기간."""
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.get_executives(stock_code, year)

        @self.mcp.tool()
        def dart_executive_compensation(stock_code: str, year: Optional[int] = None) -> dict:
            """임원보수 조회 (OpenDART). 이사/감사 보수총액, 1인당 평균, 최고보수자."""
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.get_executive_compensation(stock_code, year)

        @self.mcp.tool()
        def dart_shareholder_changes(stock_code: str, year: Optional[int] = None) -> dict:
            """최대주주 변동 조회 (OpenDART). 지배구조 변화, 경영권 이전 추적."""
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.get_shareholder_changes(stock_code, year)

        @self.mcp.tool()
        def dart_capital_changes(stock_code: str, year: Optional[int] = None) -> dict:
            """증자/감자 조회 (OpenDART). 유상증자, 무상증자, 감자 내역. 희석 리스크 분석용."""
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.get_capital_changes(stock_code, year)

        @self.mcp.tool()
        def dart_mergers(stock_code: str, year: Optional[int] = None) -> dict:
            """합병/분할 조회 (OpenDART). M&A, 인적분할, 물적분할 내역."""
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.get_mergers(stock_code, year)

        @self.mcp.tool()
        def dart_convertible_bonds(stock_code: str, year: Optional[int] = None) -> dict:
            """전환사채/신주인수권 조회 (OpenDART). CB/BW 발행, 전환가, 희석 영향."""
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.get_convertible_bonds(stock_code, year)

        @self.mcp.tool()
        def dart_treasury_stock(stock_code: str, year: Optional[int] = None) -> dict:
            """자기주식 취득/처분 조회 (OpenDART). 자사주 매입, 소각, 처분 내역."""
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.get_treasury_stock(stock_code, year)

        @self.mcp.tool()
        def dart_related_party(stock_code: str, year: Optional[int] = None) -> dict:
            """공정공시 — 특수관계자 거래 조회 (OpenDART). 거버넌스 리스크 분석."""
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.get_related_party(stock_code, year)

        @self.mcp.tool()
        def dart_5pct_disclosure(stock_code: str, year: Optional[int] = None) -> dict:
            """지분공시 (5% 룰) 조회 (OpenDART). 5% 이상 지분 변동 신고 내역."""
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.get_5pct_disclosure(stock_code, year)

        # === Phase 14: 공시 검색 ===

        @self.mcp.tool()
        def dart_disclosure_search(stock_code: str = "", keyword: str = "",
                                   start_date: str = "", end_date: str = "",
                                   kind: str = "") -> dict:
            """기업 공시 검색 (OpenDART). 사업보고서, 주요사항, 지분공시 등.

            Args:
                stock_code: 종목코드 (예: 005930). keyword와 택 1.
                keyword: 회사명 (예: 삼성전자). stock_code와 택 1.
                start_date: 시작일 YYYYMMDD (기본: 6개월 전)
                end_date: 종료일 YYYYMMDD (기본: 오늘)
                kind: 공시유형 — A=정기공시, B=주요사항, C=발행, D=지분, E=기타 (빈값=전체)
            """
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.search_disclosures(
                stock_code=stock_code or None, keyword=keyword or None,
                start_date=start_date or None, end_date=end_date or None,
                kind=kind or None,
            )


        # === Phase 14: 이벤트·전체재무제표·원문 조회 ===

        @self.mcp.tool()
        def dart_events(stock_code: str, keyword: str = "", start_date: str = "", end_date: str = "") -> dict:
            """이벤트 공시 조회 (유상증자, 전환사채, 합병 등 주요 기업 이벤트).

            Args:
                stock_code: 종목코드 (예: 005930)
                keyword: 이벤트 키워드 (예: 유상증자, 합병). 빈값=전체.
                start_date: 시작일 YYYYMMDD (기본: 1년 전)
                end_date: 종료일 YYYYMMDD (기본: 오늘)
            """
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.get_events(
                stock_code=stock_code,
                keyword=keyword or "",
                start_date=start_date or None,
                end_date=end_date or None,
            )

        @self.mcp.tool()
        def dart_full_financial(
            stock_code: str,
            year: Optional[int] = None,
            report_type: str = "11011",
            fs_div: str = "CFS",
        ) -> dict:
            """전체 재무제표 조회 (연결/개별 선택). BS+CIS+CF+SCE 포함.
            1회 호출 시 최대 3개년. 금액은 숫자 문자열 (콤마 없음, 예: "176107659000000").
            sj_div 값: BS(재무상태표), CIS(포괄손익), CF(현금흐름), SCE(자본변동).
            IS가 아닌 CIS로 분류됨에 주의.

            Args:
                stock_code: 종목코드 (예: 005930)
                year: 사업연도 (기본: 전년도)
                report_type: 보고서 유형 (11011=사업보고서, 11012=반기, 11013=1분기, 11014=3분기)
                fs_div: CFS=연결재무제표, OFS=개별재무제표
            """
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.get_full_financial_statements(stock_code, year, report_type, fs_div)

        @self.mcp.tool()
        def dart_document(rcp_no: str, max_chars: int = 5000) -> dict:
            """공시 원문 텍스트 조회. rcp_no는 dart_disclosure_search 결과에서 얻을 수 있음.

            Args:
                rcp_no: 접수번호 (예: 20240315000123)
                max_chars: 최대 반환 문자 수 (기본: 5000)
            """
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}
            return adapter.get_document(rcp_no, max_chars)

        @self.mcp.tool()
        def dart_financial_multi_year(
            stock_code: str,
            years: int = 5,
            report_type: str = "11011",
            fs_div: str = "CFS",
        ) -> dict:
            """복수연도 재무제표 조회 (최대 5~10개년). DART 3년 제한을 자동 우회.
            내부에서 필요한 만큼 API를 호출하고 중복 제거 후 병합하여 반환.

            Args:
                stock_code: 종목코드 (예: 000660 = SK하이닉스)
                years: 조회 연수 (기본: 5년, 최대 10년)
                report_type: 11011=사업보고서, 11012=반기
                fs_div: CFS=연결, OFS=개별

            Returns:
                years개년 재무제표 데이터 (BS+CIS+CF+SCE 통합)
            """
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}

            from datetime import datetime
            from mcp_servers.adapters.dart_adapter import _sanitize_records
            import pandas as pd

            # Latest available fiscal year = last year (current year's report not filed yet)
            latest_year = datetime.now().year - 1
            years = min(years, 10)

            all_records = []
            seen_keys = set()
            call_years = []

            # DART returns 3 years per call (당기/전기/전전기).
            # Query years: latest, latest-3, latest-6, ... to cover full range.
            # Example (2025, years=5): query 2025 → covers 2023~2025, query 2022 → covers 2020~2022
            for offset in range(0, years, 3):
                query_year = latest_year - offset
                call_years.append(query_year)
                result = adapter.get_full_financial_statements(stock_code, query_year, report_type, fs_div)
                if result.get("error"):
                    continue
                records = result.get("data", [])
                if isinstance(records, list):
                    for r in records:
                        # Deduplicate by (sj_div, account_nm, bsns_year)
                        key = (r.get("sj_div", ""), r.get("account_nm", ""), r.get("bsns_year", ""))
                        if key not in seen_keys:
                            seen_keys.add(key)
                            all_records.append(r)

            # Sanitize NaN/Inf → None for valid JSON
            for r in all_records:
                for k, v in r.items():
                    if isinstance(v, float) and (v != v or v == float('inf') or v == float('-inf')):
                        r[k] = None

            # Sort by year descending, then by statement type
            sj_order = {"BS": 0, "CIS": 1, "IS": 1, "CF": 2, "SCE": 3}
            all_records.sort(key=lambda r: (
                -int(r.get("bsns_year", "0") or "0"),
                sj_order.get(r.get("sj_div", ""), 9),
            ))

            # Extract actual years covered
            actual_years = sorted(set(r.get("bsns_year", "") for r in all_records if r.get("bsns_year")), reverse=True)

            return {
                "success": True,
                "data": all_records,
                "count": len(all_records),
                "source": "OpenDART",
                "stock_code": stock_code,
                "years_requested": years,
                "years_covered": actual_years,
                "api_calls": len(call_years),
                "api_call_years": call_years,
                "fs_div": fs_div,
                "note": f"Merged {len(call_years)} API calls. {len(all_records)} records across {len(actual_years)} years ({', '.join(actual_years[:5])}).",
            }

        @self.mcp.tool()
        def dart_equity_analysis(stock_code: str) -> dict:
            """기업 종합 분석 — 1회 호출로 기업개황 + 재무제표 + 재무비율 + 현금흐름 + 배당 통합 조회.
            개별적으로 5개 도구를 호출할 필요 없이 한번에 전체 데이터를 반환.

            Args:
                stock_code: 종목코드 (예: 005930 = 삼성전자, 000660 = SK하이닉스)

            Returns:
                company_info, financial_statements, financial_ratios, cash_flow, dividend 통합 dict
            """
            if not adapter or not adapter._dart:
                return {"error": True, "message": "DART client not initialized. Check DART_API_KEY."}

            results = {}

            # 1. Company info
            try:
                results["company_info"] = adapter.get_company_info(stock_code)
            except Exception as e:
                results["company_info"] = {"error": True, "message": str(e)}

            # 2. Financial statements (latest year)
            try:
                results["financial_statements"] = adapter.get_financial_statements(stock_code)
            except Exception as e:
                results["financial_statements"] = {"error": True, "message": str(e)}

            # 3. Financial ratios
            try:
                results["financial_ratios"] = adapter.get_financial_ratios(stock_code)
            except Exception as e:
                results["financial_ratios"] = {"error": True, "message": str(e)}

            # 4. Cash flow
            try:
                results["cash_flow"] = adapter.get_cash_flow(stock_code)
            except Exception as e:
                results["cash_flow"] = {"error": True, "message": str(e)}

            # 5. Dividend
            try:
                results["dividend"] = adapter.get_dividend(stock_code)
            except Exception as e:
                results["dividend"] = {"error": True, "message": str(e)}

            success_count = sum(1 for v in results.values() if not v.get("error"))

            return {
                "success": True,
                "data": results,
                "stock_code": stock_code,
                "source": "OpenDART",
                "sections": list(results.keys()),
                "sections_ok": success_count,
                "sections_total": len(results),
            }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = DARTServer()
    server.mcp.run(transport="stdio")
