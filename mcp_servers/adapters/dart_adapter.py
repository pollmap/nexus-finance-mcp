"""
DART (OpenDART) Adapter - Korean Financial Disclosure System.

Wraps OpenDART API for accessing Korean company financial data:
- Financial statements (재무제표)
- Company info (기업개황)
- Major shareholders (대주주)
- Executive compensation (임원보수)

Requires: pip install opendart

Run standalone test: python -m mcp_servers.adapters.dart_adapter
"""
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.core.cache_manager import CacheManager, get_cache
from mcp_servers.core.rate_limiter import RateLimiter, get_limiter
from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)


class DARTAdapter:
    """
    Adapter for OpenDART API.

    Provides simplified interface for common financial data queries.
    """

    # Top 50 Korean stocks by market cap
    STOCK_CODES = {
        # KOSPI 대형주
        "삼성전자": "005930", "SK하이닉스": "000660", "LG에너지솔루션": "373220",
        "삼성바이오로직스": "207940", "현대차": "005380", "기아": "000270",
        "셀트리온": "068270", "POSCO홀딩스": "005490", "KB금융": "105560",
        "신한지주": "055550", "삼성SDI": "006400", "LG화학": "051910",
        "현대모비스": "012330", "NAVER": "035420", "카카오": "035720",
        "삼성물산": "028260", "SK이노베이션": "096770", "SK텔레콤": "017670",
        "LG전자": "066570", "한국전력": "015760", "KT": "030200",
        "삼성생명": "032830", "하나금융지주": "086790", "우리금융지주": "316140",
        "SK": "034730", "삼성화재": "000810", "한화에어로스페이스": "012450",
        "LG": "003550", "HD현대중공업": "329180", "두산에너빌리티": "034020",
        "크래프톤": "259960", "카카오뱅크": "323410", "SK바이오사이언스": "302440",
        "HD한국조선해양": "009540", "한화솔루션": "009830",
        # KOSPI 중형주
        "현대건설": "000720", "삼성엔지니어링": "028050", "한화": "000880",
        "삼성중공업": "010140", "대한항공": "003490", "CJ제일제당": "097950",
        "아모레퍼시픽": "090430", "LG생활건강": "051900", "넷마블": "251270",
        "엔씨소프트": "036570", "한국가스공사": "036460",
        # KOSDAQ 대형주
        "에코프로비엠": "247540", "에코프로": "086520", "알테오젠": "196170",
        "HLB": "028300", "리노공업": "058470", "엘앤에프": "066970",
    }

    def __init__(
        self,
        api_key: str = None,
        cache: CacheManager = None,
        limiter: RateLimiter = None,
    ):
        """
        Initialize DART adapter.

        Args:
            api_key: DART API key (uses env var if not provided)
            cache: Cache manager instance
            limiter: Rate limiter instance
        """
        self.api_key = api_key or os.getenv("DART_API_KEY", "")
        self._cache = cache or get_cache()
        self._limiter = limiter or get_limiter()

        if not self.api_key:
            logger.warning("DART_API_KEY not set. DART queries will fail.")

        # Initialize OpenDART client
        self.is_available = False
        self._dart = None
        try:
            import OpenDartReader
            self._dart = OpenDartReader(self.api_key)
            self.is_available = True
            logger.info("DART client initialized successfully")
        except ImportError:
            logger.error("OpenDartReader not installed. Run: pip install opendart")
        except Exception as e:
            logger.error(f"Failed to initialize DART client: {e}")

    @staticmethod
    def _validate_stock_code(stock_code: str) -> bool:
        import re
        return bool(re.match(r'^\d{6}$', str(stock_code)))

    def get_company_info(self, stock_code: str) -> Dict[str, Any]:
        """
        Get company basic information.

        Args:
            stock_code: Stock code (e.g., "005930")

        Returns:
            Company info dict
        """
        if not self._validate_stock_code(stock_code):
            return error_response(f"Invalid stock code: {stock_code}. Must be 6 digits.", code="INVALID_INPUT")
        if not self._dart:
            return error_response("DART client not initialized", code="NOT_INITIALIZED")

        try:
            self._limiter.acquire("dart")

            cache_key = {"method": "company_info", "code": stock_code}
            cached = self._cache.get("dart", cache_key)
            if cached:
                return cached

            # Get company info (returns dict, not DataFrame)
            info = self._dart.company(stock_code)

            if info is None:
                return error_response(f"No company info for {stock_code}", code="NOT_FOUND")
            if isinstance(info, dict) and info.get("status") != "000":
                return error_response(info.get("message", "Unknown error"))

            result = success_response(
                info if isinstance(info, dict) else (info.to_dict() if hasattr(info, 'to_dict') else dict(info)),
                source="OpenDART", stock_code=stock_code,
            )

            self._cache.set("dart", cache_key, result, "static_meta")
            return result

        except Exception as e:
            logger.error(f"DART company info error: {e}")
            return error_response(str(e))

    def get_financial_statements(
        self,
        stock_code: str,
        year: int = None,
        report_type: str = "11011",  # 사업보고서
    ) -> Dict[str, Any]:
        """
        Get financial statements.

        Args:
            stock_code: Stock code
            year: Fiscal year (default: last year)
            report_type: Report type code
                - 11011: 사업보고서 (Annual)
                - 11012: 반기보고서 (Semi-annual)
                - 11013: 1분기보고서 (Q1)
                - 11014: 3분기보고서 (Q3)

        Returns:
            Financial statements dict
        """
        if not self._validate_stock_code(stock_code):
            return error_response(f"Invalid stock code: {stock_code}. Must be 6 digits.", code="INVALID_INPUT")
        if not self._dart:
            return error_response("DART client not initialized", code="NOT_INITIALIZED")

        try:
            self._limiter.acquire("dart")

            if year is None:
                year = datetime.now().year - 1

            cache_key = {"method": "financials", "code": stock_code, "year": year, "type": report_type}
            cached = self._cache.get("dart", cache_key)
            if cached:
                return cached

            # Get financial statements
            fs = self._dart.finstate(stock_code, year, reprt_code=report_type)

            if fs is None or (hasattr(fs, 'empty') and fs.empty):
                return success_response([], source="OpenDART", message=f"No financial data for {stock_code} in {year}")

            # Convert to records
            records = fs.to_dict("records") if hasattr(fs, 'to_dict') else []

            result = success_response(
                records, count=len(records), source="OpenDART",
                stock_code=stock_code, year=year, report_type=report_type,
            )

            self._cache.set("dart", cache_key, result, "historical")
            return result

        except Exception as e:
            logger.error(f"DART financial statements error: {e}")
            return error_response(str(e))

    def get_financial_ratios(self, stock_code: str, year: int = None) -> Dict[str, Any]:
        """
        Get key financial ratios from financial statements.

        Args:
            stock_code: Stock code
            year: Fiscal year

        Returns:
            Financial ratios dict
        """
        if not self._validate_stock_code(stock_code):
            return error_response(f"Invalid stock code: {stock_code}. Must be 6 digits.", code="INVALID_INPUT")
        fs_result = self.get_financial_statements(stock_code, year)

        if fs_result.get("error"):
            return fs_result

        if not fs_result.get("data"):
            return error_response("No financial data available", code="NOT_FOUND")

        try:
            # Parse key metrics from financial statements
            data = fs_result["data"]

            # Helper function to find value by account name
            def find_value(keywords: List[str], default: float = 0) -> float:
                for item in data:
                    account = item.get("account_nm", "") or item.get("sj_nm", "")
                    for kw in keywords:
                        if kw in account:
                            val = item.get("thstrm_amount", item.get("thstrm_dt"))
                            if val is not None and val != "":
                                try:
                                    return float(str(val).replace(",", ""))
                                except (ValueError, TypeError):
                                    pass
                return default

            # Extract key metrics
            revenue = find_value(["매출액", "영업수익", "수익(매출액)"])
            operating_income = find_value(["영업이익", "영업손익"])
            net_income = find_value(["당기순이익", "분기순이익"])
            total_assets = find_value(["자산총계", "자산 총계"])
            total_equity = find_value(["자본총계", "자본 총계"])
            total_debt = find_value(["부채총계", "부채 총계"])

            # Calculate ratios
            ratios = {
                "revenue": revenue,
                "operating_income": operating_income,
                "net_income": net_income,
                "total_assets": total_assets,
                "total_equity": total_equity,
                "total_debt": total_debt,
            }

            if total_equity > 0:
                ratios["roe"] = (net_income / total_equity) * 100
                ratios["debt_to_equity"] = (total_debt / total_equity) * 100

            if total_assets > 0:
                ratios["roa"] = (net_income / total_assets) * 100

            if revenue > 0:
                ratios["operating_margin"] = (operating_income / revenue) * 100
                ratios["net_margin"] = (net_income / revenue) * 100

            return success_response(
                ratios, source="OpenDART",
                stock_code=stock_code, year=fs_result.get("year"),
            )

        except Exception as e:
            logger.error(f"DART ratio calculation error: {e}")
            return error_response(str(e))

    def get_major_shareholders(self, stock_code: str) -> Dict[str, Any]:
        """
        Get major shareholders information.

        Args:
            stock_code: Stock code

        Returns:
            Major shareholders list
        """
        if not self._validate_stock_code(stock_code):
            return error_response(f"Invalid stock code: {stock_code}. Must be 6 digits.", code="INVALID_INPUT")
        if not self._dart:
            return error_response("DART client not initialized", code="NOT_INITIALIZED")

        try:
            self._limiter.acquire("dart")

            cache_key = {"method": "shareholders", "code": stock_code}
            cached = self._cache.get("dart", cache_key)
            if cached:
                return cached

            # Get major shareholders (method is plural: major_shareholders)
            sh = self._dart.major_shareholders(stock_code)

            if sh is None or (hasattr(sh, 'empty') and sh.empty):
                return success_response([], source="OpenDART", message="No shareholder data")

            records = sh.to_dict("records") if hasattr(sh, 'to_dict') else []

            result = success_response(
                records, count=len(records), source="OpenDART",
                stock_code=stock_code,
            )

            self._cache.set("dart", cache_key, result, "daily_data")
            return result

        except Exception as e:
            logger.error(f"DART shareholders error: {e}")
            return error_response(str(e))

    def get_cash_flow(self, stock_code: str, year: int = None, report_type: str = "11011") -> Dict[str, Any]:
        """Get cash flow statement using finstate_all (includes CF)."""
        if not self._validate_stock_code(stock_code):
            return error_response(f"Invalid stock code: {stock_code}. Must be 6 digits.", code="INVALID_INPUT")
        if not self._dart:
            return error_response("DART client not initialized", code="NOT_INITIALIZED")
        try:
            self._limiter.acquire("dart")
            if year is None:
                year = datetime.now().year - 1

            cache_key = {"method": "cash_flow", "code": stock_code, "year": year, "type": report_type}
            cached = self._cache.get("dart", cache_key)
            if cached:
                return cached

            fs = self._dart.finstate_all(stock_code, year, reprt_code=report_type)
            if fs is None or (hasattr(fs, 'empty') and fs.empty):
                return success_response([], source="OpenDART", message=f"No CF data for {stock_code} in {year}")

            # Filter for cash flow statement rows
            cf_keywords = ["현금흐름", "CF", "cash"]
            if "sj_div" in fs.columns:
                cf_df = fs[fs["sj_div"].str.contains("|".join(cf_keywords), case=False, na=False)]
            elif "sj_nm" in fs.columns:
                cf_df = fs[fs["sj_nm"].str.contains("|".join(cf_keywords), case=False, na=False)]
            else:
                cf_df = fs

            records = cf_df.to_dict("records") if hasattr(cf_df, 'to_dict') else []

            result = success_response(
                records, count=len(records), source="OpenDART",
                stock_code=stock_code, year=year, report_type=report_type,
            )
            self._cache.set("dart", cache_key, result, "historical")
            return result
        except Exception as e:
            logger.error(f"DART cash flow error: {e}")
            return error_response(str(e))

    def get_dividend(self, stock_code: str, year: int = None) -> Dict[str, Any]:
        """Get dividend info."""
        if not self._validate_stock_code(stock_code):
            return error_response(f"Invalid stock code: {stock_code}. Must be 6 digits.", code="INVALID_INPUT")
        if not self._dart:
            return error_response("DART client not initialized", code="NOT_INITIALIZED")
        try:
            self._limiter.acquire("dart")
            if year is None:
                year = datetime.now().year - 1

            cache_key = {"method": "dividend", "code": stock_code, "year": year}
            cached = self._cache.get("dart", cache_key)
            if cached:
                return cached

            div = self._dart.report(stock_code, "배당", year)
            if div is None or (hasattr(div, 'empty') and div.empty):
                return success_response([], source="OpenDART", message=f"No dividend data for {stock_code}")

            records = div.to_dict("records") if hasattr(div, 'to_dict') else []
            result = success_response(
                records, count=len(records), source="OpenDART",
                stock_code=stock_code, year=year,
            )
            self._cache.set("dart", cache_key, result, "historical")
            return result
        except Exception as e:
            logger.error(f"DART dividend error: {e}")
            return error_response(str(e))

    def search_company(self, keyword: str) -> Dict[str, Any]:
        """
        Search for company by name.

        Args:
            keyword: Company name to search

        Returns:
            List of matching companies
        """
        if not self._dart:
            return error_response("DART client not initialized", code="NOT_INITIALIZED")

        try:
            self._limiter.acquire("dart")

            # Search using corp_code
            result = self._dart.corp_codes

            if result is None:
                return success_response([], source="OpenDART", message="No results")

            # Filter by keyword (safe boolean indexing, no query injection)
            if hasattr(result, 'columns') and 'corp_name' in result.columns:
                matches = result[result['corp_name'].str.contains(keyword, na=False, regex=False)]
            else:
                matches = result

            if hasattr(matches, 'to_dict'):
                records = matches.head(20).to_dict("records")
            else:
                records = []

            return success_response(
                records, count=len(records), source="OpenDART",
                keyword=keyword,
            )

        except Exception as e:
            logger.error(f"DART search error: {e}")
            return error_response(str(e))


    def _report_section(self, stock_code: str, section: str, year: int = None,
                         cache_type: str = "historical") -> Dict[str, Any]:
        """Generic helper for DART report sections."""
        if not self._validate_stock_code(stock_code):
            return error_response(f"Invalid stock code: {stock_code}. Must be 6 digits.", code="INVALID_INPUT")
        if not self._dart:
            return error_response("DART client not initialized", code="NOT_INITIALIZED")
        try:
            self._limiter.acquire("dart")
            if year is None:
                year = datetime.now().year - 1

            cache_key = {"method": section, "code": stock_code, "year": year}
            cached = self._cache.get("dart", cache_key)
            if cached:
                return cached

            data = self._dart.report(stock_code, section, year)
            if data is None or (hasattr(data, 'empty') and data.empty):
                return success_response([], source="OpenDART",
                                        message=f"No {section} data for {stock_code}")

            records = data.to_dict("records") if hasattr(data, 'to_dict') else []
            result = success_response(
                records, count=len(records), source="OpenDART",
                stock_code=stock_code, year=year, section=section,
            )
            self._cache.set("dart", cache_key, result, cache_type)
            return result
        except Exception as e:
            logger.error(f"DART {section} error: {e}")
            return error_response(str(e))

    def get_executives(self, stock_code: str, year: int = None) -> Dict[str, Any]:
        """임원현황 조회."""
        return self._report_section(stock_code, "임원현황", year)

    def get_executive_compensation(self, stock_code: str, year: int = None) -> Dict[str, Any]:
        """임원보수 조회."""
        return self._report_section(stock_code, "임원보수", year)

    def get_shareholder_changes(self, stock_code: str, year: int = None) -> Dict[str, Any]:
        """최대주주 변동 조회."""
        return self._report_section(stock_code, "최대주주변동", year)

    def get_capital_changes(self, stock_code: str, year: int = None) -> Dict[str, Any]:
        """증자/감자 조회."""
        return self._report_section(stock_code, "증자감자", year)

    def get_mergers(self, stock_code: str, year: int = None) -> Dict[str, Any]:
        """합병/분할 조회."""
        return self._report_section(stock_code, "합병분할", year)

    def get_convertible_bonds(self, stock_code: str, year: int = None) -> Dict[str, Any]:
        """전환사채/신주인수권 조회."""
        return self._report_section(stock_code, "전환사채", year)

    def get_treasury_stock(self, stock_code: str, year: int = None) -> Dict[str, Any]:
        """자기주식 취득/처분 조회."""
        return self._report_section(stock_code, "자기주식", year)

    def get_related_party(self, stock_code: str, year: int = None) -> Dict[str, Any]:
        """공정공시 (특수관계자 거래) 조회."""
        return self._report_section(stock_code, "공정공시", year)

    def get_5pct_disclosure(self, stock_code: str, year: int = None) -> Dict[str, Any]:
        """지분공시 (5% 룰) 조회."""
        return self._report_section(stock_code, "지분공시", year)

    def get_events(
        self,
        stock_code: str,
        keyword: str = "",
        start_date: str = None,
        end_date: str = None,
    ) -> Dict[str, Any]:
        """
        이벤트 공시 조회 (유상증자, 무상증자, 전환사채, 합병 등 주요 이벤트).

        Args:
            stock_code: 종목코드 (6자리)
            keyword: 이벤트 키워드 (예: 유상증자, 합병)
            start_date: 시작일 YYYYMMDD
            end_date: 종료일 YYYYMMDD

        Returns:
            이벤트 공시 목록
        """
        if not self._validate_stock_code(stock_code):
            return error_response(f"Invalid stock code: {stock_code}. Must be 6 digits.", code="INVALID_INPUT")
        if not self._dart:
            return error_response("DART client not initialized", code="NOT_INITIALIZED")

        try:
            self._limiter.acquire("dart")

            # Resolve corp_code from stock_code
            corp_code = None
            corp_name = None
            try:
                codes_df = self._dart.corp_codes
                if codes_df is not None and 'stock_code' in codes_df.columns:
                    match = codes_df[codes_df['stock_code'] == stock_code]
                    if not match.empty:
                        corp_code = match.iloc[0].get('corp_code', None)
                        corp_name = match.iloc[0].get('corp_name', None)
            except Exception as e:
                logger.warning(f"corp_codes lookup failed: {e}")

            if not corp_code:
                try:
                    info = self._dart.company(stock_code)
                    if info and isinstance(info, dict):
                        corp_code = info.get('corp_code')
                        corp_name = info.get('corp_name')
                except Exception as e:
                    logger.warning(f"company() lookup failed: {e}")

            if not corp_code:
                return error_response(f"Cannot find corp_code for stock_code {stock_code}", code="NOT_FOUND")

            # Default date range
            from datetime import timedelta
            today = datetime.now()
            if not end_date:
                end_date = today.strftime("%Y%m%d")
            if not start_date:
                start_date = (today - timedelta(days=365)).strftime("%Y%m%d")

            cache_key = {
                "method": "events",
                "corp": corp_code,
                "keyword": keyword,
                "start": start_date,
                "end": end_date,
            }
            cached = self._cache.get("dart", cache_key)
            if cached:
                return cached

            # Call OpenDartReader.event()
            df = self._dart.event(corp_code, key_word=keyword or "", start=start_date, end=end_date)

            if df is None or (hasattr(df, 'empty') and df.empty):
                return success_response(
                    [], source="OpenDART",
                    message=f"No events found for {corp_name or corp_code}",
                    corp_code=corp_code, corp_name=corp_name,
                    start_date=start_date, end_date=end_date,
                )

            records = df.to_dict("records") if hasattr(df, 'to_dict') else []

            result = success_response(
                records, count=len(records), source="OpenDART",
                corp_code=corp_code, corp_name=corp_name,
                keyword=keyword, start_date=start_date, end_date=end_date,
            )

            self._cache.set("dart", cache_key, result, "daily_data")
            return result

        except Exception as e:
            logger.error(f"DART events error: {e}")
            return error_response(str(e))

    def get_full_financial_statements(
        self,
        stock_code: str,
        year: int = None,
        report_type: str = "11011",
        fs_div: str = "CFS",
    ) -> Dict[str, Any]:
        """
        전체 재무제표 조회 (개별/연결 선택 가능).

        Args:
            stock_code: 종목코드 (6자리)
            year: 사업연도 (기본: 전년도)
            report_type: 보고서 유형 (11011=사업보고서)
            fs_div: CFS=연결재무제표, OFS=개별재무제표

        Returns:
            전체 재무제표 항목 (BS, IS, CF 모두 포함)
        """
        if not self._validate_stock_code(stock_code):
            return error_response(f"Invalid stock code: {stock_code}. Must be 6 digits.", code="INVALID_INPUT")
        if not self._dart:
            return error_response("DART client not initialized", code="NOT_INITIALIZED")

        try:
            self._limiter.acquire("dart")

            if year is None:
                year = datetime.now().year - 1

            if fs_div not in ("CFS", "OFS"):
                return error_response("fs_div must be 'CFS' (연결) or 'OFS' (개별)", code="INVALID_INPUT")

            cache_key = {
                "method": "full_financial",
                "code": stock_code,
                "year": year,
                "type": report_type,
                "fs_div": fs_div,
            }
            cached = self._cache.get("dart", cache_key)
            if cached:
                return cached

            fs = self._dart.finstate_all(stock_code, year, reprt_code=report_type, fs_div=fs_div)

            if fs is None or (hasattr(fs, 'empty') and fs.empty):
                return success_response(
                    [], source="OpenDART",
                    message=f"No financial data for {stock_code} in {year} ({fs_div})",
                )

            records = fs.to_dict("records") if hasattr(fs, 'to_dict') else []

            result = success_response(
                records, count=len(records), source="OpenDART",
                stock_code=stock_code, year=year, report_type=report_type, fs_div=fs_div,
            )

            self._cache.set("dart", cache_key, result, "historical")
            return result

        except Exception as e:
            logger.error(f"DART full financial statements error: {e}")
            return error_response(str(e))

    def get_document(self, rcp_no: str, max_chars: int = 5000) -> Dict[str, Any]:
        """
        공시 원문 텍스트 조회.

        Args:
            rcp_no: 접수번호 (dart_disclosure_search 결과에서 획득)
            max_chars: 최대 반환 문자 수 (기본: 5000)

        Returns:
            공시 원문 텍스트
        """
        if not rcp_no or not rcp_no.strip():
            return error_response("rcp_no (접수번호) is required.", code="INVALID_INPUT")
        if not self._dart:
            return error_response("DART client not initialized", code="NOT_INITIALIZED")

        try:
            self._limiter.acquire("dart")

            cache_key = {"method": "document", "rcp_no": rcp_no}
            cached = self._cache.get("dart", cache_key)
            if cached:
                return cached

            doc_text = self._dart.document(rcp_no)

            if doc_text is None or (isinstance(doc_text, str) and not doc_text.strip()):
                return success_response(
                    "", source="OpenDART",
                    message=f"No document found for rcp_no: {rcp_no}",
                    rcp_no=rcp_no,
                )

            # Convert to string if needed, truncate to max_chars
            text = str(doc_text)
            truncated = len(text) > max_chars
            if truncated:
                text = text[:max_chars]

            result = success_response(
                text, source="OpenDART",
                rcp_no=rcp_no, total_chars=len(str(doc_text)),
                truncated=truncated, max_chars=max_chars,
            )

            self._cache.set("dart", cache_key, result, "historical")
            return result

        except Exception as e:
            logger.error(f"DART document error: {e}")
            return error_response(str(e))

    def search_disclosures(
        self,
        stock_code: str = None,
        keyword: str = None,
        start_date: str = None,
        end_date: str = None,
        kind: str = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Search corporate disclosures (공시 검색).

        Args:
            stock_code: 6-digit stock code (optional, use keyword if not provided)
            keyword: Company name keyword (used if stock_code not provided)
            start_date: Start date YYYYMMDD (default: 6 months ago)
            end_date: End date YYYYMMDD (default: today)
            kind: Filing type — A=정기, B=주요사항, C=발행, D=지분, E=기타
            limit: Max results (default 20)

        Returns:
            List of disclosure records
        """
        if not self._dart:
            return error_response("DART client not initialized", code="NOT_INITIALIZED")

        if not stock_code and not keyword:
            return error_response("stock_code 또는 keyword 중 하나를 입력하세요.", code="INVALID_INPUT")

        try:
            self._limiter.acquire("dart")

            # Resolve corp_code
            corp_code = None
            corp_name = None

            if stock_code:
                if not self._validate_stock_code(stock_code):
                    return error_response(f"Invalid stock code: {stock_code}. Must be 6 digits.", code="INVALID_INPUT")

                # Look up corp_code from stock_code via corp_codes DataFrame
                try:
                    codes_df = self._dart.corp_codes
                    if codes_df is not None and 'stock_code' in codes_df.columns:
                        match = codes_df[codes_df['stock_code'] == stock_code]
                        if not match.empty:
                            corp_code = match.iloc[0].get('corp_code', None)
                            corp_name = match.iloc[0].get('corp_name', None)
                except Exception as e:
                    logger.warning(f"corp_codes lookup failed: {e}")

                # Fallback: use company() to get corp_code
                if not corp_code:
                    try:
                        info = self._dart.company(stock_code)
                        if info and isinstance(info, dict):
                            corp_code = info.get('corp_code')
                            corp_name = info.get('corp_name')
                    except Exception as e:
                        logger.warning(f"company() lookup failed: {e}")

                if not corp_code:
                    return error_response(f"Cannot find corp_code for stock_code {stock_code}", code="NOT_FOUND")

            elif keyword:
                # Find corp_code by company name keyword
                try:
                    codes_df = self._dart.corp_codes
                    if codes_df is not None and 'corp_name' in codes_df.columns:
                        matches = codes_df[codes_df['corp_name'].str.contains(keyword, na=False, regex=False)]
                        if matches.empty:
                            return error_response(f"No company found for keyword: {keyword}", code="NOT_FOUND")
                        # Use first match
                        corp_code = matches.iloc[0].get('corp_code', None)
                        corp_name = matches.iloc[0].get('corp_name', None)
                except Exception as e:
                    return error_response(f"Company search failed: {e}")

                if not corp_code:
                    return error_response(f"Cannot find corp_code for keyword: {keyword}", code="NOT_FOUND")

            # Default date range: 6 months ago ~ today
            from datetime import timedelta
            today = datetime.now()
            if not end_date:
                end_date = today.strftime("%Y%m%d")
            if not start_date:
                start_date = (today - timedelta(days=180)).strftime("%Y%m%d")

            # Build cache key
            cache_key = {
                "method": "disclosure_search",
                "corp": corp_code,
                "start": start_date,
                "end": end_date,
                "kind": kind,
            }
            cached = self._cache.get("dart", cache_key)
            if cached:
                return cached

            # Call OpenDartReader.list()
            kwargs = {
                "corp": corp_code,
                "start": start_date,
                "end": end_date,
                "final": True,
            }
            if kind:
                kwargs["kind"] = kind

            df = self._dart.list(**kwargs)

            if df is None or (hasattr(df, 'empty') and df.empty):
                return success_response(
                    [], source="OpenDART",
                    message=f"No disclosures found for {corp_name or corp_code}",
                    corp_code=corp_code, corp_name=corp_name,
                    start_date=start_date, end_date=end_date,
                )

            # Limit results
            if hasattr(df, 'head'):
                df = df.head(limit)

            records = df.to_dict("records") if hasattr(df, 'to_dict') else []

            result = success_response(
                records, count=len(records), source="OpenDART",
                corp_code=corp_code, corp_name=corp_name,
                start_date=start_date, end_date=end_date,
                kind=kind,
            )

            self._cache.set("dart", cache_key, result, "daily_data")
            return result

        except Exception as e:
            logger.error(f"DART disclosure search error: {e}")
            return error_response(str(e))


def test_dart_adapter():
    """Test DART adapter functionality."""
    logging.basicConfig(level=logging.INFO)
    test_logger = logging.getLogger("dart_adapter.test")

    adapter = DARTAdapter()

    if not adapter._dart:
        test_logger.warning("DART client not initialized. Check API key.")
        return

    test_logger.info("=" * 60)
    test_logger.info("DART Adapter Test")
    test_logger.info("=" * 60)

    # Test company info
    test_logger.info("1. Company Info (삼성전자)")
    result = adapter.get_company_info("005930")
    test_logger.info(f"   Success: {result.get('success', False)}")

    # Test financial statements
    test_logger.info("2. Financial Statements")
    result = adapter.get_financial_statements("005930", 2023)
    test_logger.info(f"   Success: {result.get('success', False)}")
    test_logger.info(f"   Records: {result.get('count', 0)}")

    # Test financial ratios
    test_logger.info("3. Financial Ratios")
    result = adapter.get_financial_ratios("005930", 2023)
    if result.get("success"):
        ratios = result.get("ratios", {})
        test_logger.info(f"   Revenue: {ratios.get('revenue', 0):,.0f}")
        test_logger.info(f"   ROE: {ratios.get('roe', 0):.2f}%")

    test_logger.info("=" * 60)
    test_logger.info("Test Complete")


if __name__ == "__main__":
    test_dart_adapter()
