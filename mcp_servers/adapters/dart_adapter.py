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
            return {"error": True, "message": f"Invalid stock code: {stock_code}. Must be 6 digits."}
        if not self._dart:
            return {"error": True, "message": "DART client not initialized"}

        try:
            self._limiter.acquire("dart")

            cache_key = {"method": "company_info", "code": stock_code}
            cached = self._cache.get("dart", cache_key)
            if cached:
                return cached

            # Get company info (returns dict, not DataFrame)
            info = self._dart.company(stock_code)

            if info is None:
                return {"error": True, "message": f"No company info for {stock_code}"}
            if isinstance(info, dict) and info.get("status") != "000":
                return {"error": True, "message": info.get("message", "Unknown error")}

            result = {
                "success": True,
                "stock_code": stock_code,
                "data": info if isinstance(info, dict) else (info.to_dict() if hasattr(info, 'to_dict') else dict(info)),
            }

            self._cache.set("dart", cache_key, result, "static_meta")
            return result

        except Exception as e:
            logger.error(f"DART company info error: {e}")
            return {"error": True, "message": str(e)}

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
            return {"error": True, "message": f"Invalid stock code: {stock_code}. Must be 6 digits."}
        if not self._dart:
            return {"error": True, "message": "DART client not initialized"}

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
                return {
                    "success": True,
                    "data": [],
                    "message": f"No financial data for {stock_code} in {year}",
                }

            # Convert to records
            records = fs.to_dict("records") if hasattr(fs, 'to_dict') else []

            result = {
                "success": True,
                "stock_code": stock_code,
                "year": year,
                "report_type": report_type,
                "count": len(records),
                "data": records,
            }

            self._cache.set("dart", cache_key, result, "historical")
            return result

        except Exception as e:
            logger.error(f"DART financial statements error: {e}")
            return {"error": True, "message": str(e)}

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
            return {"error": True, "message": f"Invalid stock code: {stock_code}. Must be 6 digits."}
        fs_result = self.get_financial_statements(stock_code, year)

        if fs_result.get("error"):
            return fs_result

        if not fs_result.get("data"):
            return {"error": True, "message": "No financial data available"}

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

            return {
                "success": True,
                "stock_code": stock_code,
                "year": fs_result.get("year"),
                "ratios": ratios,
            }

        except Exception as e:
            logger.error(f"DART ratio calculation error: {e}")
            return {"error": True, "message": str(e)}

    def get_major_shareholders(self, stock_code: str) -> Dict[str, Any]:
        """
        Get major shareholders information.

        Args:
            stock_code: Stock code

        Returns:
            Major shareholders list
        """
        if not self._validate_stock_code(stock_code):
            return {"error": True, "message": f"Invalid stock code: {stock_code}. Must be 6 digits."}
        if not self._dart:
            return {"error": True, "message": "DART client not initialized"}

        try:
            self._limiter.acquire("dart")

            cache_key = {"method": "shareholders", "code": stock_code}
            cached = self._cache.get("dart", cache_key)
            if cached:
                return cached

            # Get major shareholders (method is plural: major_shareholders)
            sh = self._dart.major_shareholders(stock_code)

            if sh is None or (hasattr(sh, 'empty') and sh.empty):
                return {"success": True, "data": [], "message": "No shareholder data"}

            records = sh.to_dict("records") if hasattr(sh, 'to_dict') else []

            result = {
                "success": True,
                "stock_code": stock_code,
                "count": len(records),
                "data": records,
            }

            self._cache.set("dart", cache_key, result, "daily_data")
            return result

        except Exception as e:
            logger.error(f"DART shareholders error: {e}")
            return {"error": True, "message": str(e)}

    def get_cash_flow(self, stock_code: str, year: int = None, report_type: str = "11011") -> Dict[str, Any]:
        """Get cash flow statement using finstate_all (includes CF)."""
        if not self._validate_stock_code(stock_code):
            return {"error": True, "message": f"Invalid stock code: {stock_code}. Must be 6 digits."}
        if not self._dart:
            return {"error": True, "message": "DART client not initialized"}
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
                return {"success": True, "data": [], "message": f"No CF data for {stock_code} in {year}"}

            # Filter for cash flow statement rows
            cf_keywords = ["현금흐름", "CF", "cash"]
            if "sj_div" in fs.columns:
                cf_df = fs[fs["sj_div"].str.contains("|".join(cf_keywords), case=False, na=False)]
            elif "sj_nm" in fs.columns:
                cf_df = fs[fs["sj_nm"].str.contains("|".join(cf_keywords), case=False, na=False)]
            else:
                cf_df = fs

            records = cf_df.to_dict("records") if hasattr(cf_df, 'to_dict') else []

            result = {"success": True, "stock_code": stock_code, "year": year,
                      "report_type": report_type, "count": len(records), "data": records}
            self._cache.set("dart", cache_key, result, "historical")
            return result
        except Exception as e:
            logger.error(f"DART cash flow error: {e}")
            return {"error": True, "message": str(e)}

    def get_dividend(self, stock_code: str, year: int = None) -> Dict[str, Any]:
        """Get dividend info."""
        if not self._validate_stock_code(stock_code):
            return {"error": True, "message": f"Invalid stock code: {stock_code}. Must be 6 digits."}
        if not self._dart:
            return {"error": True, "message": "DART client not initialized"}
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
                return {"success": True, "data": [], "message": f"No dividend data for {stock_code}"}

            records = div.to_dict("records") if hasattr(div, 'to_dict') else []
            result = {"success": True, "stock_code": stock_code, "year": year,
                      "count": len(records), "data": records}
            self._cache.set("dart", cache_key, result, "historical")
            return result
        except Exception as e:
            logger.error(f"DART dividend error: {e}")
            return {"error": True, "message": str(e)}

    def search_company(self, keyword: str) -> Dict[str, Any]:
        """
        Search for company by name.

        Args:
            keyword: Company name to search

        Returns:
            List of matching companies
        """
        if not self._dart:
            return {"error": True, "message": "DART client not initialized"}

        try:
            self._limiter.acquire("dart")

            # Search using corp_code
            result = self._dart.corp_codes

            if result is None:
                return {"success": True, "data": [], "message": "No results"}

            # Filter by keyword (safe boolean indexing, no query injection)
            if hasattr(result, 'columns') and 'corp_name' in result.columns:
                matches = result[result['corp_name'].str.contains(keyword, na=False, regex=False)]
            else:
                matches = result

            if hasattr(matches, 'to_dict'):
                records = matches.head(20).to_dict("records")
            else:
                records = []

            return {
                "success": True,
                "keyword": keyword,
                "count": len(records),
                "data": records,
            }

        except Exception as e:
            logger.error(f"DART search error: {e}")
            return {"error": True, "message": str(e)}


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
