"""
KOSIS MCP Server - 통계청 국가통계포털 (Korean Statistical Information Service)

Provides access to Korean government statistics:
- Population data (인구)
- Employment/Labor (고용/노동)
- Housing statistics (주택)
- Economic indicators (경제지표)

Requires KOSIS API key from: https://kosis.kr/openapi/

Run standalone: python -m mcp_servers.servers.kosis_server
"""
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from fastmcp import FastMCP

from mcp_servers.core.cache_manager import CacheManager, get_cache
from mcp_servers.core.rate_limiter import RateLimiter, get_limiter

logger = logging.getLogger(__name__)


# Key KOSIS statistics
KOSIS_TABLES = {
    "population": {
        "org_id": "101",
        "tbl_id": "DT_1B040A3",
        "name": "주민등록인구",
        "name_en": "Registered Population",
    },
    "employment": {
        "org_id": "101",
        "tbl_id": "DT_1DA7002S",
        "name": "경제활동인구",
        "name_en": "Economically Active Population",
    },
    "unemployment": {
        "org_id": "101",
        "tbl_id": "DT_1DA7012S",
        "name": "실업률",
        "name_en": "Unemployment Rate",
    },
    "housing_price": {
        "org_id": "408",
        "tbl_id": "DT_30404_N0010",
        "name": "주택매매가격지수",
        "name_en": "Housing Price Index",
    },
    "cpi": {
        "org_id": "101",
        "tbl_id": "DT_1J17001",
        "name": "소비자물가지수",
        "name_en": "Consumer Price Index",
    },
    "gdp": {
        "org_id": "301",
        "tbl_id": "DT_200Y001",
        "name": "국내총생산",
        "name_en": "Gross Domestic Product",
    },
}


class KOSISServer:
    """KOSIS MCP Server for Korean government statistics."""

    BASE_URL = "https://kosis.kr/openapi/Param/statisticsParameterData.do"

    def __init__(
        self,
        api_key: str = None,
        cache: CacheManager = None,
        limiter: RateLimiter = None,
    ):
        """
        Initialize KOSIS server.

        Args:
            api_key: KOSIS API key (uses env var if not provided)
            cache: Cache manager instance
            limiter: Rate limiter instance
        """
        self.api_key = api_key or os.getenv("KOSIS_API_KEY", "")
        if not self.api_key:
            logger.warning("KOSIS_API_KEY not set. KOSIS queries will fail.")

        self._cache = cache or get_cache()
        self._limiter = limiter or get_limiter()

        # HTTP session
        self._session = requests.Session()

        # Create FastMCP server
        self.mcp = FastMCP("kosis")
        self._register_tools()

        logger.info("KOSIS MCP Server initialized")

    def _make_request(
        self,
        org_id: str,
        tbl_id: str,
        start_period: str,
        end_period: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Make KOSIS API request."""
        self._limiter.acquire("kosis")

        params = {
            "method": "getList",
            "apiKey": self.api_key,
            "format": "json",
            "jsonVD": "Y",
            "orgId": org_id,
            "tblId": tbl_id,
            "startPrdDe": start_period,
            "endPrdDe": end_period,
            **kwargs,
        }

        try:
            response = self._session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and data.get("err"):
                return {"error": True, "message": data.get("errMsg", "Unknown error")}

            return {"success": True, "data": data}

        except requests.exceptions.RequestException as e:
            logger.error(f"KOSIS request error: {e}")
            return {"error": True, "message": str(e)}

    def _register_tools(self) -> None:
        """Register MCP tools."""

        @self.mcp.tool()
        def kosis_search_tables(keyword: str) -> Dict[str, Any]:
            """
            KOSIS 통계표 검색

            Args:
                keyword: 검색어 (예: "인구", "실업", "주택")

            Returns:
                매칭되는 통계표 목록
            """
            return self.search_tables(keyword)

        @self.mcp.tool()
        def kosis_get_population(
            region_code: str = "00",
            start_year: str = None,
            end_year: str = None,
        ) -> Dict[str, Any]:
            """
            인구통계 조회

            Args:
                region_code: 지역코드 (00=전국, 11=서울, 26=부산, 28=인천, 41=경기)
                start_year: 시작연도 (기본: 5년 전)
                end_year: 종료연도 (기본: 현재)

            Returns:
                인구 데이터
            """
            return self.get_population(region_code, start_year, end_year)

        @self.mcp.tool()
        def kosis_get_unemployment(
            start_month: str = None,
            end_month: str = None,
        ) -> Dict[str, Any]:
            """
            실업률 조회

            Args:
                start_month: 시작월 (YYYYMM, 기본: 2년 전)
                end_month: 종료월 (기본: 현재)

            Returns:
                실업률 데이터
            """
            return self.get_unemployment(start_month, end_month)

        @self.mcp.tool()
        def kosis_get_housing_price(
            region_code: str = "00",
            start_month: str = None,
            end_month: str = None,
        ) -> Dict[str, Any]:
            """
            주택가격지수 조회

            Args:
                region_code: 지역코드 (00=전국, 11=서울)
                start_month: 시작월 (YYYYMM)
                end_month: 종료월

            Returns:
                주택가격지수 데이터
            """
            return self.get_housing_price(region_code, start_month, end_month)

        @self.mcp.tool()
        def kosis_get_table(
            org_id: str,
            tbl_id: str,
            start_period: str,
            end_period: str,
        ) -> Dict[str, Any]:
            """
            KOSIS 통계표 직접 조회

            Args:
                org_id: 기관코드 (예: "101" 통계청)
                tbl_id: 통계표ID (예: "DT_1B040A3")
                start_period: 시작기간
                end_period: 종료기간

            Returns:
                통계 데이터
            """
            return self.get_table(org_id, tbl_id, start_period, end_period)

    # ========================================================================
    # Implementation Methods
    # ========================================================================

    def search_tables(self, keyword: str) -> Dict[str, Any]:
        """Search for tables matching keyword."""
        matches = []

        for key, info in KOSIS_TABLES.items():
            if keyword.lower() in info["name"].lower() or keyword.lower() in info["name_en"].lower():
                matches.append({
                    "key": key,
                    "org_id": info["org_id"],
                    "tbl_id": info["tbl_id"],
                    "name": info["name"],
                    "name_en": info["name_en"],
                })

        return {
            "success": True,
            "keyword": keyword,
            "count": len(matches),
            "data": matches,
            "note": "Use kosis_get_table(org_id, tbl_id, ...) to fetch data",
        }

    def get_population(
        self,
        region_code: str,
        start_year: str = None,
        end_year: str = None,
    ) -> Dict[str, Any]:
        """Get population data."""
        if not self.api_key:
            return {"error": True, "message": "KOSIS API key not configured"}

        if start_year is None:
            start_year = str(datetime.now().year - 5)
        if end_year is None:
            end_year = str(datetime.now().year)

        cache_key = {"method": "population", "region": region_code, "start": start_year, "end": end_year}
        cached = self._cache.get("kosis", cache_key)
        if cached:
            return cached

        info = KOSIS_TABLES["population"]
        result = self._make_request(
            org_id=info["org_id"],
            tbl_id=info["tbl_id"],
            start_period=start_year,
            end_period=end_year,
            itmId="T10",  # 총인구
            objL1=region_code,
        )

        if result.get("error"):
            return result

        response = {
            "success": True,
            "indicator": info["name"],
            "region_code": region_code,
            "period": {"start": start_year, "end": end_year},
            "data": result.get("data", []),
        }

        self._cache.set("kosis", cache_key, response, "historical")
        return response

    def get_unemployment(
        self,
        start_month: str = None,
        end_month: str = None,
    ) -> Dict[str, Any]:
        """Get unemployment rate data."""
        if not self.api_key:
            return {"error": True, "message": "KOSIS API key not configured"}

        if start_month is None:
            start_month = (datetime.now() - timedelta(days=730)).strftime("%Y%m")
        if end_month is None:
            end_month = datetime.now().strftime("%Y%m")

        cache_key = {"method": "unemployment", "start": start_month, "end": end_month}
        cached = self._cache.get("kosis", cache_key)
        if cached:
            return cached

        info = KOSIS_TABLES["unemployment"]
        result = self._make_request(
            org_id=info["org_id"],
            tbl_id=info["tbl_id"],
            start_period=start_month,
            end_period=end_month,
        )

        if result.get("error"):
            return result

        response = {
            "success": True,
            "indicator": info["name"],
            "period": {"start": start_month, "end": end_month},
            "data": result.get("data", []),
        }

        self._cache.set("kosis", cache_key, response, "historical")
        return response

    def get_housing_price(
        self,
        region_code: str,
        start_month: str = None,
        end_month: str = None,
    ) -> Dict[str, Any]:
        """Get housing price index data."""
        if not self.api_key:
            return {"error": True, "message": "KOSIS API key not configured"}

        if start_month is None:
            start_month = (datetime.now() - timedelta(days=365 * 3)).strftime("%Y%m")
        if end_month is None:
            end_month = datetime.now().strftime("%Y%m")

        cache_key = {"method": "housing", "region": region_code, "start": start_month, "end": end_month}
        cached = self._cache.get("kosis", cache_key)
        if cached:
            return cached

        info = KOSIS_TABLES["housing_price"]
        result = self._make_request(
            org_id=info["org_id"],
            tbl_id=info["tbl_id"],
            start_period=start_month,
            end_period=end_month,
        )

        if result.get("error"):
            return result

        response = {
            "success": True,
            "indicator": info["name"],
            "region_code": region_code,
            "period": {"start": start_month, "end": end_month},
            "data": result.get("data", []),
        }

        self._cache.set("kosis", cache_key, response, "historical")
        return response

    def get_table(
        self,
        org_id: str,
        tbl_id: str,
        start_period: str,
        end_period: str,
    ) -> Dict[str, Any]:
        """Get data from a specific KOSIS table."""
        if not self.api_key:
            return {"error": True, "message": "KOSIS API key not configured"}

        cache_key = {"method": "table", "org": org_id, "tbl": tbl_id, "start": start_period, "end": end_period}
        cached = self._cache.get("kosis", cache_key)
        if cached:
            return cached

        result = self._make_request(org_id, tbl_id, start_period, end_period)

        if result.get("error"):
            return result

        response = {
            "success": True,
            "org_id": org_id,
            "tbl_id": tbl_id,
            "period": {"start": start_period, "end": end_period},
            "data": result.get("data", []),
        }

        self._cache.set("kosis", cache_key, response, "historical")
        return response

    def run(self) -> None:
        """Run the MCP server."""
        logger.info("Starting KOSIS MCP Server...")
        self.mcp.run()


def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    server = KOSISServer()
    server.run()


if __name__ == "__main__":
    main()
