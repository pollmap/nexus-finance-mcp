"""
ECOS MCP Server - 한국은행 경제통계시스템 (Bank of Korea ECOS)

Provides access to Korean macroeconomic data through the BOK ECOS API.
Uses PublicDataReader library for API wrapper.

Key stat codes:
- 722Y001: 기준금리 (Base Rate)
- 101Y004: M2 통화량 (M2 Money Supply)
- 200Y102: GDP (Gross Domestic Product)
- 731Y001: 환율 (Exchange Rates)
- 901Y009: 소비자물가지수 (CPI)
- 121Y002: 국제수지 (Balance of Payments)

Run standalone: python -m mcp_servers.servers.ecos_server
"""
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from fastmcp import FastMCP

from mcp_servers.core.cache_manager import CacheManager, get_cache
from mcp_servers.core.rate_limiter import RateLimiter, get_limiter

logger = logging.getLogger(__name__)

# Key ECOS stat codes with metadata
ECOS_STAT_CODES = {
    "base_rate": {
        "code": "722Y001",
        "item_code": "0101000",
        "name": "기준금리",
        "name_en": "Base Rate",
        "unit": "%",
        "frequency": "D",  # Daily
    },
    "m2": {
        "code": "101Y004",
        "item_code": "BBHA00",
        "name": "M2 (광의통화)",
        "name_en": "M2 Money Supply",
        "unit": "십억원",
        "frequency": "M",  # Monthly
    },
    "gdp": {
        "code": "200Y102",
        "item_code": "10111",
        "name": "국내총생산(GDP)",
        "name_en": "GDP",
        "unit": "십억원",
        "frequency": "Q",  # Quarterly
    },
    "exchange_rate_usd": {
        "code": "731Y001",
        "item_code": "0000001",
        "name": "원/달러 환율",
        "name_en": "KRW/USD Exchange Rate",
        "unit": "원",
        "frequency": "D",
    },
    "cpi": {
        "code": "901Y009",
        "item_code": "0",
        "name": "소비자물가지수",
        "name_en": "Consumer Price Index",
        "unit": "2020=100",
        "frequency": "M",
    },
    "unemployment_rate": {
        "code": "901Y027",
        "item_code": "I16AA",
        "name": "실업률",
        "name_en": "Unemployment Rate",
        "unit": "%",
        "frequency": "M",
    },
}


class ECOSServer:
    """ECOS MCP Server for Bank of Korea economic statistics."""

    def __init__(
        self,
        api_key: str = None,
        cache: CacheManager = None,
        limiter: RateLimiter = None,
    ):
        """
        Initialize ECOS server.

        Args:
            api_key: BOK ECOS API key (uses env var if not provided)
            cache: Cache manager instance
            limiter: Rate limiter instance
        """
        self.api_key = api_key or os.getenv("BOK_ECOS_API_KEY", "")
        if not self.api_key:
            logger.warning("BOK_ECOS_API_KEY not set. ECOS queries will fail.")

        self._cache = cache or get_cache()
        self._limiter = limiter or get_limiter()

        # Initialize PublicDataReader for ECOS
        try:
            from PublicDataReader import Ecos
            self._ecos = Ecos(self.api_key)
            logger.info("ECOS client initialized successfully")
        except ImportError:
            logger.error("PublicDataReader not installed. Run: pip install PublicDataReader")
            self._ecos = None
        except Exception as e:
            logger.error(f"Failed to initialize ECOS client: {e}")
            self._ecos = None

        # Create FastMCP server
        self.mcp = FastMCP("ecos")
        self._register_tools()

    def _register_tools(self) -> None:
        """Register MCP tools."""

        @self.mcp.tool()
        def ecos_search_stat_list(keyword: str) -> Dict[str, Any]:
            """
            한국은행 ECOS 통계 목록 검색

            Args:
                keyword: 검색 키워드 (예: "금리", "GDP", "물가")

            Returns:
                검색된 통계 목록
            """
            return self.search_stat_list(keyword)

        @self.mcp.tool()
        def ecos_get_stat_data(
            stat_code: str,
            item_code: str,
            start_date: str,
            end_date: str = None,
            frequency: str = "M",
        ) -> Dict[str, Any]:
            """
            ECOS 통계 데이터 조회

            Args:
                stat_code: 통계표 코드 (예: "722Y001" 기준금리)
                item_code: 통계항목 코드 (예: "0101000")
                start_date: 시작일 (YYYYMMDD 또는 YYYY)
                end_date: 종료일 (기본값: 오늘)
                frequency: 주기 (D:일, M:월, Q:분기, A:연)

            Returns:
                통계 데이터
            """
            return self.get_stat_data(stat_code, item_code, start_date, end_date, frequency)

        @self.mcp.tool()
        def ecos_get_base_rate(
            start_date: str = None,
            end_date: str = None,
        ) -> Dict[str, Any]:
            """
            한국은행 기준금리 조회

            Args:
                start_date: 시작일 (YYYYMMDD, 기본값: 1년 전)
                end_date: 종료일 (기본값: 오늘)

            Returns:
                기준금리 시계열 데이터
            """
            return self.get_base_rate(start_date, end_date)

        @self.mcp.tool()
        def ecos_get_m2(
            start_date: str = None,
            end_date: str = None,
        ) -> Dict[str, Any]:
            """
            M2 통화량 조회 (광의통화)

            Args:
                start_date: 시작월 (YYYYMM, 기본값: 5년 전)
                end_date: 종료월 (기본값: 최신)

            Returns:
                M2 통화량 시계열 데이터
            """
            return self.get_m2(start_date, end_date)

        @self.mcp.tool()
        def ecos_get_gdp(
            start_year: str = None,
            end_year: str = None,
        ) -> Dict[str, Any]:
            """
            GDP (국내총생산) 조회

            Args:
                start_year: 시작연도 (YYYY, 기본값: 10년 전)
                end_year: 종료연도 (기본값: 최신)

            Returns:
                GDP 시계열 데이터 (분기별)
            """
            return self.get_gdp(start_year, end_year)

        @self.mcp.tool()
        def ecos_get_macro_snapshot(date: str = None) -> Dict[str, Any]:
            """
            주요 거시경제 지표 스냅샷

            Args:
                date: 기준일 (YYYYMMDD, 기본값: 최신)

            Returns:
                기준금리, M2, GDP, 환율, CPI, 실업률 등 주요 지표
            """
            return self.get_macro_snapshot(date)

        @self.mcp.tool()
        def ecos_get_exchange_rate(
            currency: str = "USD",
            start_date: str = None,
            end_date: str = None,
        ) -> Dict[str, Any]:
            """
            환율 조회

            Args:
                currency: 통화 코드 (USD, EUR, JPY, CNY 등)
                start_date: 시작일 (YYYYMMDD, 기본값: 1년 전)
                end_date: 종료일 (기본값: 오늘)

            Returns:
                환율 시계열 데이터
            """
            return self.get_exchange_rate(currency, start_date, end_date)

    # Implementation methods

    def search_stat_list(self, keyword: str) -> Dict[str, Any]:
        """Search for statistics by keyword."""
        if not self._ecos:
            return {"error": True, "message": "ECOS client not initialized"}

        try:
            self._limiter.acquire("ecos")

            # Check cache
            cache_key = {"method": "search", "keyword": keyword}
            cached = self._cache.get("ecos", cache_key)
            if cached:
                return cached

            # Search using PublicDataReader
            df = self._ecos.get_statistic_table_list(keyword)

            if df is None or df.empty:
                return {"success": True, "data": [], "message": f"No results for '{keyword}'"}

            # Convert to list of dicts
            results = df.to_dict("records")

            response = {
                "success": True,
                "keyword": keyword,
                "count": len(results),
                "data": results[:50],  # Limit to 50 results
            }

            self._cache.set("ecos", cache_key, response, "static_meta")
            return response

        except Exception as e:
            logger.error(f"ECOS search error: {e}")
            return {"error": True, "message": str(e)}

    def get_stat_data(
        self,
        stat_code: str,
        item_code: str,
        start_date: str,
        end_date: str = None,
        frequency: str = "M",
    ) -> Dict[str, Any]:
        """Get statistical data from ECOS."""
        if not self._ecos:
            return {"error": True, "message": "ECOS client not initialized"}

        try:
            self._limiter.acquire("ecos")

            if end_date is None:
                end_date = datetime.now().strftime("%Y%m%d")

            # Check cache
            cache_key = {
                "method": "get_data",
                "stat_code": stat_code,
                "item_code": item_code,
                "start": start_date,
                "end": end_date,
                "freq": frequency,
            }
            cached = self._cache.get("ecos", cache_key)
            if cached:
                return cached

            # Fetch data using positional arguments to avoid Korean encoding issues
            # Order: stat_code, frequency, start_date, end_date, item_code1
            df = self._ecos.get_statistic_search(
                stat_code,      # 통계표코드
                frequency,      # 주기
                start_date,     # 검색시작일자
                end_date,       # 검색종료일자
                item_code,      # 통계항목코드1
            )

            if df is None or df.empty:
                return {
                    "success": True,
                    "data": [],
                    "message": "No data found for the specified parameters",
                }

            # Process dataframe
            records = df.to_dict("records")

            response = {
                "success": True,
                "stat_code": stat_code,
                "item_code": item_code,
                "frequency": frequency,
                "period": {"start": start_date, "end": end_date},
                "count": len(records),
                "data": records,
            }

            # Cache based on frequency
            data_type = "daily_data" if frequency == "D" else "historical"
            self._cache.set("ecos", cache_key, response, data_type)

            return response

        except Exception as e:
            logger.error(f"ECOS get_stat_data error: {e}")
            return {"error": True, "message": str(e)}

    def get_base_rate(
        self,
        start_date: str = None,
        end_date: str = None,
    ) -> Dict[str, Any]:
        """Get Bank of Korea base rate."""
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        stat_info = ECOS_STAT_CODES["base_rate"]

        result = self.get_stat_data(
            stat_code=stat_info["code"],
            item_code=stat_info["item_code"],
            start_date=start_date,
            end_date=end_date,
            frequency="D",
        )

        if result.get("success"):
            result["indicator"] = stat_info["name"]
            result["indicator_en"] = stat_info["name_en"]
            result["unit"] = stat_info["unit"]

            # Extract latest value
            if result.get("data"):
                latest = result["data"][-1]
                result["latest"] = {
                    "date": latest.get("시점", latest.get("TIME", "")),
                    "value": latest.get("값", latest.get("DATA_VALUE", "")),
                }

        return result

    def get_m2(
        self,
        start_date: str = None,
        end_date: str = None,
    ) -> Dict[str, Any]:
        """Get M2 money supply data."""
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365*5)).strftime("%Y%m")
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m")

        stat_info = ECOS_STAT_CODES["m2"]

        result = self.get_stat_data(
            stat_code=stat_info["code"],
            item_code=stat_info["item_code"],
            start_date=start_date,
            end_date=end_date,
            frequency="M",
        )

        if result.get("success"):
            result["indicator"] = stat_info["name"]
            result["indicator_en"] = stat_info["name_en"]
            result["unit"] = stat_info["unit"]

            if result.get("data"):
                latest = result["data"][-1]
                result["latest"] = {
                    "date": latest.get("시점", latest.get("TIME", "")),
                    "value": latest.get("값", latest.get("DATA_VALUE", "")),
                }

        return result

    def get_gdp(
        self,
        start_year: str = None,
        end_year: str = None,
    ) -> Dict[str, Any]:
        """Get GDP data."""
        if start_year is None:
            start_year = str(datetime.now().year - 10)
        if end_year is None:
            end_year = str(datetime.now().year)

        stat_info = ECOS_STAT_CODES["gdp"]

        result = self.get_stat_data(
            stat_code=stat_info["code"],
            item_code=stat_info["item_code"],
            start_date=start_year + "Q1",
            end_date=end_year + "Q4",
            frequency="Q",
        )

        if result.get("success"):
            result["indicator"] = stat_info["name"]
            result["indicator_en"] = stat_info["name_en"]
            result["unit"] = stat_info["unit"]

            if result.get("data"):
                latest = result["data"][-1]
                result["latest"] = {
                    "period": latest.get("시점", latest.get("TIME", "")),
                    "value": latest.get("값", latest.get("DATA_VALUE", "")),
                }

        return result

    def get_exchange_rate(
        self,
        currency: str = "USD",
        start_date: str = None,
        end_date: str = None,
    ) -> Dict[str, Any]:
        """Get exchange rate data."""
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        # Currency code mapping for ECOS
        currency_codes = {
            "USD": "0000001",
            "EUR": "0000002",
            "JPY": "0000003",
            "CNY": "0000053",
            "GBP": "0000005",
        }

        item_code = currency_codes.get(currency.upper(), "0000001")

        result = self.get_stat_data(
            stat_code="731Y001",
            item_code=item_code,
            start_date=start_date,
            end_date=end_date,
            frequency="D",
        )

        if result.get("success"):
            result["indicator"] = f"원/{currency} 환율"
            result["indicator_en"] = f"KRW/{currency} Exchange Rate"
            result["currency"] = currency

            if result.get("data"):
                latest = result["data"][-1]
                result["latest"] = {
                    "date": latest.get("시점", latest.get("TIME", "")),
                    "value": latest.get("값", latest.get("DATA_VALUE", "")),
                }

        return result

    def get_macro_snapshot(self, date: str = None) -> Dict[str, Any]:
        """Get snapshot of key macroeconomic indicators."""
        try:
            snapshot = {
                "success": True,
                "date": date or datetime.now().strftime("%Y-%m-%d"),
                "indicators": {},
            }

            # Fetch each indicator
            indicators_to_fetch = [
                ("base_rate", self.get_base_rate),
                ("m2", self.get_m2),
                ("gdp", self.get_gdp),
                ("exchange_rate", lambda: self.get_exchange_rate("USD")),
            ]

            for name, fetch_func in indicators_to_fetch:
                try:
                    result = fetch_func()
                    if result.get("success") and result.get("latest"):
                        snapshot["indicators"][name] = {
                            "name": result.get("indicator", name),
                            "name_en": result.get("indicator_en", name),
                            "value": result["latest"].get("value"),
                            "date": result["latest"].get("date") or result["latest"].get("period"),
                            "unit": result.get("unit", ""),
                        }
                except Exception as e:
                    logger.warning(f"Failed to fetch {name}: {e}")
                    snapshot["indicators"][name] = {"error": str(e)}

            return snapshot

        except Exception as e:
            logger.error(f"ECOS macro snapshot error: {e}")
            return {"error": True, "message": str(e)}

    def run(self) -> None:
        """Run the MCP server."""
        logger.info("Starting ECOS MCP Server...")
        self.mcp.run()


# Standalone server entry point
def main():
    """Main entry point for standalone server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    server = ECOSServer()
    server.run()


if __name__ == "__main__":
    main()
