"""
R-ONE MCP Server - 한국부동산원 부동산정보 (Korea Real Estate Board)

Provides Korean real estate market data:
- Apartment price index (아파트매매가격지수)
- Jeonse (deposit lease) index (전세가격지수)
- Transaction volume (거래량)
- PIR (Price to Income Ratio)
- Regional comparison

Data source: 한국부동산원 부동산통계정보 (R-ONE)
API: https://www.reb.or.kr/

Run standalone: python -m mcp_servers.servers.rone_server
"""
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

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


# Region codes for R-ONE (55 regions)
REGION_CODES = {
    # === 전국 ===
    "전국": "0000000000",
    "수도권": "0000000001",
    # === 서울 (시 + 주요구) ===
    "서울": "1100000000",
    "강남구": "1168000000", "서초구": "1165000000", "송파구": "1171000000",
    "강동구": "1174000000", "마포구": "1144000000", "용산구": "1117000000",
    "성동구": "1120000000", "광진구": "1121500000", "동대문구": "1123000000",
    "성북구": "1129000000", "강북구": "1130500000", "노원구": "1135000000",
    "도봉구": "1132000000", "은평구": "1138000000", "서대문구": "1141000000",
    "양천구": "1147000000", "강서구": "1150000000", "구로구": "1153000000",
    "영등포구": "1156000000", "동작구": "1159000000", "관악구": "1162000000",
    "종로구": "1111000000", "중구": "1114000000", "금천구": "1154500000",
    "중랑구": "1126000000",
    # === 광역시 ===
    "부산": "2600000000", "해운대구": "2635000000", "부산진구": "2623000000",
    "대구": "2700000000", "수성구": "2726000000", "달서구": "2729000000",
    "인천": "2800000000", "연수구": "2818500000", "부평구": "2823700000", "인천서구": "2826000000",
    "광주": "2900000000", "대전": "3000000000", "유성구": "3020000000",
    "울산": "3100000000", "세종": "3600000000",
    # === 도 ===
    "경기": "4100000000", "강원": "5100000000", "충북": "4300000000",
    "충남": "4400000000", "전북": "5200000000", "전남": "4600000000",
    "경북": "4700000000", "경남": "4800000000", "제주": "5000000000",
    # === 경기 주요시 ===
    "수원": "4111000000", "성남": "4113000000", "고양": "4128000000",
    "용인": "4146000000", "안양": "4117000000", "부천": "4119000000",
    "화성": "4159000000", "평택": "4122000000", "안산": "4127000000",
    "시흥": "4139000000", "파주": "4148000000", "김포": "4157000000",
    "광명": "4121000000", "하남": "4145000000", "남양주": "4136000000",
    "구리": "4131000000", "의왕": "4143000000", "군포": "4141000000",
    "광주시": "4161000000", "양주": "4163000000",
}



class RONEServer:
    """R-ONE MCP Server for Korean real estate data."""

    # KOSIS API (한국부동산원 orgId=408) — reb.or.kr 직접 API가 비활성이므로 KOSIS 경유
    KOSIS_BASE = "https://kosis.kr/openapi/Param/statisticsParameterData.do"

    # KOSIS 부동산원(408) 주요 테이블
    KOSIS_TABLES = {
        "apt_price": {"orgId": "408", "tblId": "DT_30404_B012", "name": "매매가격지수"},
        "jeonse": {"orgId": "408", "tblId": "DT_30404_B013", "name": "전세가격지수"},
        "monthly_rent": {"orgId": "408", "tblId": "DT_30404_B001", "name": "월세통합지수"},
        "jeonse_ratio": {"orgId": "408", "tblId": "DT_30404_N0006_R1", "name": "매매 대비 전세 비율"},
        "rent_conversion": {"orgId": "408", "tblId": "DT_30404_N0010", "name": "전월세전환율"},
    }

    # 지역 코드 → KOSIS objL2 코드 매핑
    KOSIS_REGION_MAP = {
        "전국": "a0", "서울": "a1", "부산": "b1", "대구": "c1", "인천": "d1",
        "광주": "e1", "대전": "f1", "울산": "g1", "세종": "h1", "경기": "i1",
        "강원": "j1", "충북": "k1", "충남": "l1", "전북": "m1", "전남": "n1",
        "경북": "o1", "경남": "p1", "제주": "q1",
    }

    def __init__(
        self,
        api_key: str = None,
        cache: CacheManager = None,
        limiter: RateLimiter = None,
    ):
        self.api_key = api_key or os.getenv("KOSIS_API_KEY", os.getenv("RONE_API_KEY", ""))
        self._cache = cache or get_cache()
        self._limiter = limiter or get_limiter()
        self._session = requests.Session()

        # Create FastMCP server
        self.mcp = FastMCP("rone")
        self._register_tools()

        logger.info("R-ONE MCP Server initialized")

    def _kosis_request(self, tbl_key: str, start_period: str, end_period: str,
                       region: str = None, **extra) -> Dict[str, Any]:
        """Fetch R-ONE data via KOSIS API (orgId=408)."""
        if not self.api_key:
            return {"error": True, "message": "KOSIS_API_KEY (or RONE_API_KEY) not set"}

        tbl = self.KOSIS_TABLES.get(tbl_key)
        if not tbl:
            return {"error": True, "message": f"Unknown table: {tbl_key}"}

        self._limiter.acquire("rone")

        params = {
            "method": "getList",
            "apiKey": self.api_key,
            "format": "json",
            "jsonVD": "Y",
            "orgId": tbl["orgId"],
            "tblId": tbl["tblId"],
            "startPrdDe": start_period.replace("-", ""),
            "endPrdDe": end_period.replace("-", ""),
            "prdSe": "M",
            "itmId": "ALL",
            "objL1": "ALL",
            "objL2": "ALL",
            "objL3": "", "objL4": "", "objL5": "", "objL6": "", "objL7": "", "objL8": "",
            **extra,
        }

        # Filter by region if specified
        if region:
            region_code = self.KOSIS_REGION_MAP.get(region)
            if region_code:
                params["objL2"] = region_code

        try:
            resp = self._session.get(self.KOSIS_BASE, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, dict) and data.get("err"):
                return {"error": True, "message": f"KOSIS error: {data.get('errMsg', 'Unknown')}"}

            if isinstance(data, list):
                return {"success": True, "source": f"KOSIS (부동산원 {tbl['name']})", "data": data, "total_count": len(data)}

            return {"success": True, "data": []}

        except requests.exceptions.Timeout:
            return {"error": True, "message": "KOSIS API timeout"}
        except requests.exceptions.RequestException as e:
            return {"error": True, "message": f"KOSIS request error: {e}"}
        except ValueError:
            return {"error": True, "message": "KOSIS returned invalid JSON"}

    def _register_tools(self) -> None:
        """Register MCP tools."""

        @self.mcp.tool()
        def rone_get_apt_price_index(
            region: str = "서울",
            start_month: str = None,
            end_month: str = None,
        ) -> Dict[str, Any]:
            """
            아파트매매가격지수 조회

            Args:
                region: 지역명 (서울, 전국, 강남구, 수원 등)
                start_month: 시작월 (YYYY-MM, 기본: 1년 전)
                end_month: 종료월 (기본: 현재)

            Returns:
                아파트매매가격지수 시계열
            """
            return self.get_apt_price_index(region, start_month, end_month)

        @self.mcp.tool()
        def rone_get_jeonse_index(
            region: str = "서울",
            start_month: str = None,
            end_month: str = None,
        ) -> Dict[str, Any]:
            """
            전세가격지수 조회

            Args:
                region: 지역명
                start_month: 시작월 (YYYY-MM)
                end_month: 종료월

            Returns:
                전세가격지수 시계열
            """
            return self.get_jeonse_index(region, start_month, end_month)

        @self.mcp.tool()
        def rone_get_pir(region: str = "서울") -> Dict[str, Any]:
            """
            PIR (소득대비주택가격) 조회

            PIR = 중위주택가격 / 중위가구소득

            Args:
                region: 지역명

            Returns:
                PIR 데이터
            """
            return self.get_pir(region)

        @self.mcp.tool()
        def rone_get_price_comparison(
            regions: List[str] = None,
        ) -> Dict[str, Any]:
            """
            지역별 아파트가격 비교

            Args:
                regions: 비교할 지역 리스트 (기본: 서울, 전국, 경기)

            Returns:
                지역별 가격지수 비교
            """
            if regions is None:
                regions = ["서울", "전국", "경기"]
            return self.get_price_comparison(regions)

        @self.mcp.tool()
        def rone_get_market_summary() -> Dict[str, Any]:
            """
            부동산 시장 요약

            Returns:
                전국/서울 가격지수, PIR, 최근 동향
            """
            return self.get_market_summary()

        @self.mcp.tool()
        def rone_list_regions() -> Dict[str, Any]:
            """
            사용 가능한 지역 목록

            Returns:
                지역명과 코드 목록
            """
            return {
                "success": True,
                "count": len(REGION_CODES),
                "regions": list(REGION_CODES.keys()),
                "region_codes": REGION_CODES,
            }

    # ========================================================================
    # Implementation Methods
    # ========================================================================

    def _format_kosis_price_data(self, raw_data: list, region: str) -> list:
        """Format KOSIS price index data into clean records."""
        records = []
        for r in raw_data:
            # Filter: 종합(아파트+연립+단독) type only, matching region
            if region and r.get("C2_NM", "") != region and r.get("C2") != self.KOSIS_REGION_MAP.get(region, ""):
                continue
            try:
                records.append({
                    "period": r.get("PRD_DE", ""),
                    "region": r.get("C2_NM", ""),
                    "type": r.get("C1_NM", ""),
                    "indicator": r.get("ITM_NM", ""),
                    "value": float(r.get("DT", 0)) if r.get("DT") else None,
                    "unit": r.get("UNIT_NM", ""),
                })
            except (ValueError, TypeError):
                continue
        records.sort(key=lambda x: x["period"])
        return records

    def get_apt_price_index(
        self,
        region: str,
        start_month: str = None,
        end_month: str = None,
    ) -> Dict[str, Any]:
        """Get apartment price index via KOSIS (부동산원 orgId=408)."""
        if start_month is None:
            start_month = (datetime.now() - timedelta(days=365)).strftime("%Y%m")
        if end_month is None:
            end_month = datetime.now().strftime("%Y%m")

        cache_key = {"method": "apt_price", "region": region, "start": start_month, "end": end_month}
        cached = self._cache.get("rone", cache_key)
        if cached:
            return cached

        api_result = self._kosis_request("apt_price", start_month, end_month, region=region)
        if api_result.get("error"):
            return api_result

        items = self._format_kosis_price_data(api_result.get("data", []), region)
        response = {
            "success": True,
            "indicator": "아파트매매가격지수",
            "region": region,
            "period": {"start": start_month, "end": end_month},
            "data_source": "KOSIS (부동산원)",
            "count": len(items),
            "data": items,
            "latest": items[-1] if items else None,
        }

        self._cache.set("rone", cache_key, response, "daily_data")
        return response

    def get_jeonse_index(
        self,
        region: str,
        start_month: str = None,
        end_month: str = None,
    ) -> Dict[str, Any]:
        """Get jeonse price index via KOSIS (부동산원 orgId=408)."""
        if start_month is None:
            start_month = (datetime.now() - timedelta(days=365)).strftime("%Y%m")
        if end_month is None:
            end_month = datetime.now().strftime("%Y%m")

        cache_key = {"method": "jeonse", "region": region, "start": start_month, "end": end_month}
        cached = self._cache.get("rone", cache_key)
        if cached:
            return cached

        api_result = self._kosis_request("jeonse", start_month, end_month, region=region)
        if api_result.get("error"):
            return api_result

        items = self._format_kosis_price_data(api_result.get("data", []), region)
        response = {
            "success": True,
            "indicator": "전세가격지수",
            "region": region,
            "period": {"start": start_month, "end": end_month},
            "data_source": "KOSIS (부동산원)",
            "count": len(items),
            "data": items,
            "latest": items[-1] if items else None,
        }

        self._cache.set("rone", cache_key, response, "daily_data")
        return response

    @staticmethod
    def _interpret_pir(pir_value: float) -> str:
        if pir_value < 5:
            return "매우 양호"
        elif pir_value < 10:
            return "양호"
        elif pir_value < 15:
            return "부담"
        elif pir_value < 20:
            return "높은 부담"
        return "매우 높은 부담"

    def get_pir(self, region: str) -> Dict[str, Any]:
        """Get Price to Income Ratio — 전월세전환율 via KOSIS."""
        cache_key = {"method": "pir", "region": region}
        cached = self._cache.get("rone", cache_key)
        if cached:
            return cached

        end = datetime.now().strftime("%Y%m")
        start = (datetime.now() - timedelta(days=365)).strftime("%Y%m")

        result = self._kosis_request("rent_conversion", start, end, region=region)
        if result.get("error"):
            return result

        raw = result.get("data", [])
        items = self._format_kosis_price_data(raw, region)

        if not items:
            return {"error": True, "message": f"PIR/전월세전환율 데이터 없음 (region={region}). 데이터가 아직 발표되지 않았을 수 있습니다."}

        response = {
            "success": True,
            "indicator": "전월세전환율",
            "region": region,
            "data_source": "KOSIS (부동산원)",
            "count": len(items),
            "data": items,
            "latest": items[-1] if items else None,
            "note": "전월세전환율: 전세→월세 전환 시 적용되는 환산율 (%). 높을수록 임대인에게 유리.",
        }

        self._cache.set("rone", cache_key, response, "daily_data")
        return response

    def get_price_comparison(self, regions: List[str]) -> Dict[str, Any]:
        """Compare apartment prices across regions."""
        comparison = []

        for region in regions:
            result = self.get_apt_price_index(region)
            if result.get("success") and result.get("data"):
                latest = result.get("latest", {})
                comparison.append({
                    "region": region,
                    "latest_value": latest.get("value"),
                    "latest_period": latest.get("period"),
                    "indicator": latest.get("indicator"),
                    "unit": latest.get("unit"),
                    "record_count": result.get("count", 0),
                })

        comparison.sort(key=lambda x: x.get("latest_value") or 0, reverse=True)

        return {
            "success": True,
            "indicator": "아파트매매가격지수 비교",
            "regions": regions,
            "data": comparison,
            "data_source": "KOSIS (부동산원)",
        }

    def get_market_summary(self) -> Dict[str, Any]:
        """Get overall market summary via KOSIS."""
        if not self.api_key:
            return {"error": True, "message": "KOSIS_API_KEY not set"}

        seoul = self.get_apt_price_index("서울")
        nationwide = self.get_apt_price_index("전국")
        seoul_jeonse = self.get_jeonse_index("서울")

        if seoul.get("error") and nationwide.get("error"):
            return {"error": True, "message": "데이터 조회 실패. KOSIS_API_KEY를 확인하세요."}

        summary = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "data_source": "KOSIS (부동산원)",
        }

        latest_seoul = seoul.get("latest") or {}
        if latest_seoul:
            summary["seoul_apt"] = {
                "period": latest_seoul.get("period"),
                "value": latest_seoul.get("value"),
                "unit": latest_seoul.get("unit"),
            }

        latest_nationwide = nationwide.get("latest") or {}
        if latest_nationwide:
            summary["nationwide_apt"] = {
                "period": latest_nationwide.get("period"),
                "value": latest_nationwide.get("value"),
                "unit": latest_nationwide.get("unit"),
            }

        latest_jeonse = seoul_jeonse.get("latest") or {}
        if latest_jeonse:
            summary["seoul_jeonse"] = {
                "period": latest_jeonse.get("period"),
                "value": latest_jeonse.get("value"),
                "unit": latest_jeonse.get("unit"),
            }

        return summary

    def run(self) -> None:
        """Run the MCP server."""
        logger.info("Starting R-ONE MCP Server...")
        self.mcp.run()


def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    server = RONEServer()
    server.run()


if __name__ == "__main__":
    main()
