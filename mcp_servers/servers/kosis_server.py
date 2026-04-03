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
import ssl
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.util.ssl_ import create_urllib3_context

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
    "industrial_production": {
        "org_id": "101",
        "tbl_id": "DT_1C02",
        "name": "광공업생산지수",
        "name_en": "Industrial Production Index",
    },
    "trade_balance": {
        "org_id": "101",
        "tbl_id": "DT_2KAA802",
        "name": "수출입",
        "name_en": "Trade Balance",
    },
    "household_income": {
        "org_id": "101",
        "tbl_id": "DT_1L9H001",
        "name": "가계소득",
        "name_en": "Household Income",
    },
    "interest_rate": {
        "org_id": "301",
        "tbl_id": "DT_010Y001",
        "name": "금리",
        "name_en": "Interest Rate",
    },
    "exchange_rate": {
        "org_id": "301",
        "tbl_id": "DT_060Y001",
        "name": "환율",
        "name_en": "Exchange Rate",
    },
    "construction": {
        "org_id": "101",
        "tbl_id": "DT_1C03001",
        "name": "건설기성액",
        "name_en": "Construction Output",
    },
    "retail_sales": {
        "org_id": "101",
        "tbl_id": "DT_1C04",
        "name": "소매판매액지수",
        "name_en": "Retail Sales Index",
    },
    "export_price": {
        "org_id": "101",
        "tbl_id": "DT_1E04101",
        "name": "수출물가지수",
        "name_en": "Export Price Index",
    },
    "jeonse_price": {
        "org_id": "408",
        "tbl_id": "DT_30404_N0020",
        "name": "주택전세가격지수",
        "name_en": "Jeonse (Deposit) Price Index",
    },
    "rent_conversion": {
        "org_id": "408",
        "tbl_id": "DT_30404_N0033",
        "name": "전월세전환율",
        "name_en": "Rent Conversion Rate",
    },
    "monthly_rent": {
        "org_id": "408",
        "tbl_id": "DT_30404_N0030",
        "name": "월세가격지수",
        "name_en": "Monthly Rent Price Index",
    },
    "housing_tenure": {
        "org_id": "101",
        "tbl_id": "DT_1SSGA09",
        "name": "점유형태별 가구수 주거실태",
        "name_en": "Housing Tenure Type",
    },
    "household_expenditure": {
        "org_id": "101",
        "tbl_id": "DT_1L9H002",
        "name": "가계동향 지출 주거비",
        "name_en": "Household Expenditure Housing",
    },
    "apt_trade_volume": {
        "org_id": "408",
        "tbl_id": "DT_30404_N0061",
        "name": "아파트 매매거래량",
        "name_en": "Apartment Trade Volume",
    },
    "apt_jeonse_volume": {
        "org_id": "408",
        "tbl_id": "DT_30404_N0062",
        "name": "아파트 전월세 거래량",
        "name_en": "Apartment Jeonse/Rent Volume",
    },
    "land_price": {
        "org_id": "408",
        "tbl_id": "DT_30404_N0040",
        "name": "지가변동률",
        "name_en": "Land Price Change Rate",
    },
    "birth_rate": {
        "org_id": "101",
        "tbl_id": "DT_1B8000G",
        "name": "출생아수 합계출산율",
        "name_en": "Birth Rate",
    },
    "marriage_divorce": {
        "org_id": "101",
        "tbl_id": "DT_1B8000I",
        "name": "혼인 이혼",
        "name_en": "Marriage and Divorce",
    },
    # === 소득/가계 ===
    "household_finance": {
        "org_id": "101", "tbl_id": "DT_1HDLF01",
        "name": "가계금융복지조사", "name_en": "Household Finance Welfare Survey",
    },
    "household_spending": {
        "org_id": "101", "tbl_id": "DT_1L9I001",
        "name": "가계동향 소비지출", "name_en": "Household Spending",
    },
    # === 고용/노동 ===
    "wage": {
        "org_id": "101", "tbl_id": "DT_1DA7104S",
        "name": "임금", "name_en": "Wages",
    },
    "irregular_workers": {
        "org_id": "101", "tbl_id": "DT_1DE7073S",
        "name": "비정규직", "name_en": "Irregular Workers",
    },
    # === 주거/부동산 ===
    "housing_survey": {
        "org_id": "101", "tbl_id": "DT_1SSGA01",
        "name": "주거실태조사", "name_en": "Housing Survey",
    },
    "housing_supply_rate": {
        "org_id": "101", "tbl_id": "DT_1YL21171",
        "name": "주택보급률", "name_en": "Housing Supply Rate",
    },
    "building_permit": {
        "org_id": "101", "tbl_id": "DT_1C11004",
        "name": "건축허가", "name_en": "Building Permits",
    },
    "unsold_housing": {
        "org_id": "408", "tbl_id": "DT_2KAA904",
        "name": "미분양현황", "name_en": "Unsold Housing Units",
    },
    "rent_transaction": {
        "org_id": "408", "tbl_id": "DT_30404_N0063",
        "name": "전월세거래", "name_en": "Rent Transactions",
    },
    # === 산업/경기 ===
    "service_production": {
        "org_id": "101", "tbl_id": "DT_1C07",
        "name": "서비스업생산지수", "name_en": "Service Industry Production Index",
    },
    "equipment_investment": {
        "org_id": "101", "tbl_id": "DT_1C06",
        "name": "설비투자지수", "name_en": "Equipment Investment Index",
    },
    "manufacturing_bsi": {
        "org_id": "101", "tbl_id": "DT_1F01001",
        "name": "제조업경기실사지수(BSI)", "name_en": "Manufacturing BSI",
    },
    # === 인구/사회 ===
    "elderly_ratio": {
        "org_id": "101", "tbl_id": "DT_1BPA001",
        "name": "고령인구비율", "name_en": "Elderly Population Ratio",
    },
    "marriage_count": {
        "org_id": "101", "tbl_id": "DT_1B8000H",
        "name": "혼인건수", "name_en": "Marriage Count",
    },
    "cause_of_death": {
        "org_id": "101", "tbl_id": "DT_1B34E13",
        "name": "사망원인", "name_en": "Cause of Death",
    },
    "household_type": {
        "org_id": "101", "tbl_id": "DT_1JC1501",
        "name": "가구형태", "name_en": "Household Type",
    },
    "education_level": {
        "org_id": "101", "tbl_id": "DT_1PM1502",
        "name": "교육수준", "name_en": "Education Level",
    },
    # === 물가 ===
    "living_price": {
        "org_id": "101", "tbl_id": "DT_1J22001",
        "name": "생활물가지수", "name_en": "Living Price Index",
    },
    "import_price": {
        "org_id": "101", "tbl_id": "DT_1E04201",
        "name": "수입물가지수", "name_en": "Import Price Index",
    },
    # === 무역 ===
    "trade_index": {
        "org_id": "101", "tbl_id": "DT_2KAA808",
        "name": "무역지수", "name_en": "Trade Index",
    },
    "trade_trend": {
        "org_id": "101", "tbl_id": "DT_2KAA001",
        "name": "수출입동향", "name_en": "Trade Trend",
    },
    # === 에너지/환경 ===
    "energy_consumption": {
        "org_id": "101", "tbl_id": "DT_1ES0300",
        "name": "에너지소비", "name_en": "Energy Consumption",
    },
    "electricity_supply": {
        "org_id": "101", "tbl_id": "DT_2GAAA01",
        "name": "전력수급", "name_en": "Electricity Supply and Demand",
    },
    # === 관광 ===
    "tourism_arrival": {
        "org_id": "101", "tbl_id": "DT_1B28025",
        "name": "관광객 입출국", "name_en": "Tourism Arrivals/Departures",
    },
    "tourism_revenue": {
        "org_id": "101", "tbl_id": "DT_2KAAB02",
        "name": "관광수입지출", "name_en": "Tourism Revenue",
    },
    # === 기업 ===
    "business_demographics": {
        "org_id": "101", "tbl_id": "DT_1K61902",
        "name": "기업생멸", "name_en": "Business Demographics",
    },
    "startup_count": {
        "org_id": "101", "tbl_id": "DT_1K11901",
        "name": "창업기업수", "name_en": "Startup Count",
    },
}


class TLS12Adapter(HTTPAdapter):
    """Force TLS 1.2 — KOSIS server rejects TLS 1.3 handshakes."""

    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


class KOSISServer:
    """KOSIS MCP Server for Korean government statistics."""

    BASE_URL = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
    SEARCH_URL = "https://kosis.kr/openapi/statisticsList.do"

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

        # HTTP session with TLS 1.2 + User-Agent + retry
        retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = TLS12Adapter(max_retries=retry_strategy)
        self._session = requests.Session()
        self._session.mount("https://", adapter)
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        # Create FastMCP server
        self.mcp = FastMCP("kosis")
        self._register_tools()

        logger.info("KOSIS MCP Server initialized")

    # Period type mapping for known tables (auto prdSe)
    TABLE_PRD_SE = {
        # 기존
        "DT_1B040A3": "Y",      # 인구 (연간)
        "DT_1DA7002S": "M",     # 경활인구 (월간)
        "DT_1DA7012S": "M",     # 실업률 (월간)
        "DT_30404_N0010": "M",  # 주택매매가격지수
        "DT_1J17001": "M",      # CPI
        "DT_200Y001": "Q",      # GDP
        "DT_1C02": "M",         # 광공업생산
        "DT_2KAA802": "M",      # 수출입
        "DT_1L9H001": "Q",      # 가계소득
        "DT_010Y001": "M",      # 금리
        "DT_060Y001": "D",      # 환율
        "DT_1C03001": "M",      # 건설기성액
        "DT_1C04": "M",         # 소매판매액
        "DT_1E04101": "M",      # 수출물가
        # 부동산
        "DT_30404_N0020": "M",  # 전세가격지수
        "DT_30404_N0033": "M",  # 전월세전환율
        "DT_30404_N0030": "M",  # 월세가격지수
        "DT_1SSGA09": "Y",      # 점유형태
        "DT_1L9H002": "Q",      # 가계지출
        "DT_30404_N0061": "M",  # 아파트매매거래량
        "DT_30404_N0062": "M",  # 아파트전월세거래량
        "DT_30404_N0040": "M",  # 지가변동률
        "DT_1B8000G": "Y",      # 출생아수
        "DT_1B8000I": "Y",      # 혼인이혼
        # 새로 추가
        "DT_1HDLF01": "Y",      # 가계금융복지
        "DT_1L9I001": "Q",      # 가계소비지출
        "DT_1DA7104S": "M",     # 임금
        "DT_1DE7073S": "Y",     # 비정규직
        "DT_1SSGA01": "Y",      # 주거실태
        "DT_1YL21171": "Y",     # 주택보급률
        "DT_1C11004": "M",      # 건축허가
        "DT_2KAA904": "M",      # 미분양
        "DT_30404_N0063": "M",  # 전월세거래
        "DT_1C07": "M",         # 서비스업생산
        "DT_1C06": "M",         # 설비투자
        "DT_1F01001": "M",      # 제조업BSI
        "DT_1BPA001": "Y",      # 고령인구
        "DT_1B8000H": "M",      # 혼인건수
        "DT_1B34E13": "Y",      # 사망원인
        "DT_1JC1501": "Y",      # 가구형태
        "DT_1PM1502": "Y",      # 교육수준
        "DT_1J22001": "M",      # 생활물가
        "DT_1E04201": "M",      # 수입물가
        "DT_2KAA808": "M",      # 무역지수
        "DT_2KAA001": "M",      # 수출입동향
        "DT_1ES0300": "Y",      # 에너지소비
        "DT_2GAAA01": "M",      # 전력수급
        "DT_1B28025": "M",      # 관광입출국
        "DT_2KAAB02": "Q",      # 관광수입지출
        "DT_1K61902": "Y",      # 기업생멸
        "DT_1K11901": "Y",      # 창업기업수
    }

    def _make_request(
        self,
        org_id: str,
        tbl_id: str,
        start_period: str,
        end_period: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Make KOSIS API request with TLS 1.2 + retry."""
        self._limiter.acquire("kosis")

        # Auto-detect prdSe if not provided
        if "prdSe" not in kwargs:
            kwargs["prdSe"] = self.TABLE_PRD_SE.get(tbl_id, "M")

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

        last_err = None
        for attempt in range(3):
            try:
                response = self._session.get(self.BASE_URL, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                if isinstance(data, dict) and data.get("err"):
                    return {"error": True, "message": data.get("errMsg", "Unknown error")}

                return {"success": True, "data": data}

            except (requests.exceptions.ConnectionError, ConnectionResetError) as e:
                last_err = e
                logger.warning(f"KOSIS connection attempt {attempt+1}/3 failed: {e}")
                time.sleep(1 * (attempt + 1))
            except requests.exceptions.RequestException as e:
                logger.error(f"KOSIS request error: {e}")
                return {"error": True, "message": str(e)}

        logger.error(f"KOSIS request failed after 3 attempts: {last_err}")
        return {"error": True, "message": f"Connection failed after 3 retries: {last_err}"}

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
            prd_se: str = "",
            itm_id: str = "",
            obj_l1: str = "",
            obj_l2: str = "",
        ) -> Dict[str, Any]:
            """
            KOSIS 통계표 직접 조회

            Args:
                org_id: 기관코드 (예: "101" 통계청, "301" 한국은행, "408" 한국부동산원)
                tbl_id: 통계표ID (예: "DT_1B040A3")
                start_period: 시작기간 (YYYY, YYYYMM, YYYYMMDD)
                end_period: 종료기간
                prd_se: 수록주기 (Y:연, H:반기, Q:분기, M:월, D:일). 미입력시 자동감지
                itm_id: 항목ID (예: "T10"). 필수인 통계표 있음
                obj_l1: 분류값1 (예: "00" 전국). 필수인 통계표 있음
                obj_l2: 분류값2. 선택

            Returns:
                통계 데이터
            """
            extra = {}
            if prd_se:
                extra["prdSe"] = prd_se
            if itm_id:
                extra["itmId"] = itm_id
            if obj_l1:
                extra["objL1"] = obj_l1
            if obj_l2:
                extra["objL2"] = obj_l2
            return self.get_table(org_id, tbl_id, start_period, end_period, **extra)

    # ========================================================================
    # Implementation Methods
    # ========================================================================

    def search_tables(self, keyword: str) -> Dict[str, Any]:
        """Search for tables matching keyword — local dict + KOSIS API."""
        matches = []
        seen_tbl_ids = set()

        # 1. Local dictionary search (fast, always works)
        for key, info in KOSIS_TABLES.items():
            if keyword.lower() in info["name"].lower() or keyword.lower() in info["name_en"].lower():
                matches.append({
                    "key": key,
                    "org_id": info["org_id"],
                    "tbl_id": info["tbl_id"],
                    "name": info["name"],
                    "name_en": info["name_en"],
                    "source": "local",
                })
                seen_tbl_ids.add(info["tbl_id"])

        # 2. KOSIS statisticsList API search (broader, but flaky connection)
        if self.api_key:
            try:
                params = {
                    "method": "getList",
                    "apiKey": self.api_key,
                    "vwCd": "MT_ZTITLE",
                    "parentListId": "",
                    "format": "json",
                    "jsonVD": "Y",
                    "searchNm": keyword,
                }
                for attempt in range(3):
                    try:
                        resp = self._session.get(self.SEARCH_URL, params=params, timeout=20)
                        resp.raise_for_status()
                        if resp.text.strip():
                            api_data = resp.json()
                            if isinstance(api_data, list):
                                for item in api_data[:50]:
                                    tbl_id = item.get("TBL_ID", "")
                                    if tbl_id and tbl_id not in seen_tbl_ids:
                                        matches.append({
                                            "key": tbl_id,
                                            "org_id": item.get("ORG_ID", ""),
                                            "tbl_id": tbl_id,
                                            "name": item.get("TBL_NM", ""),
                                            "name_en": "",
                                            "source": "api",
                                        })
                                        seen_tbl_ids.add(tbl_id)
                        break
                    except (requests.exceptions.ConnectionError, ConnectionResetError):
                        import time
                        time.sleep(1 * (attempt + 1))
            except Exception as e:
                logger.warning(f"KOSIS API search failed, using local results only: {e}")

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
        **kwargs,
    ) -> Dict[str, Any]:
        """Get data from a specific KOSIS table."""
        if not self.api_key:
            return {"error": True, "message": "KOSIS API key not configured"}

        cache_key = {"method": "table", "org": org_id, "tbl": tbl_id, "start": start_period, "end": end_period, **kwargs}
        cached = self._cache.get("kosis", cache_key)
        if cached:
            return cached

        result = self._make_request(org_id, tbl_id, start_period, end_period, **kwargs)

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
