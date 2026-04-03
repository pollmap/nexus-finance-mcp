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

    # R-ONE API base URL (한국부동산원 공공데이터)
    RONE_API_BASE = "https://www.reb.or.kr/r-one/openapi"

    def __init__(
        self,
        api_key: str = None,
        cache: CacheManager = None,
        limiter: RateLimiter = None,
    ):
        """
        Initialize R-ONE server.

        Args:
            api_key: R-ONE API key (uses env var if not provided)
            cache: Cache manager instance
            limiter: Rate limiter instance
        """
        self.api_key = api_key or os.getenv("RONE_API_KEY", "")
        self._cache = cache or get_cache()
        self._limiter = limiter or get_limiter()

        # HTTP session
        self._session = requests.Session()

        # Create FastMCP server
        self.mcp = FastMCP("rone")
        self._register_tools()

        logger.info("R-ONE MCP Server initialized")

    def _make_api_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make R-ONE API request with rate limiting and error handling."""
        self._limiter.acquire("rone")

        url = f"{self.RONE_API_BASE}/{endpoint}"
        request_params = {
            "serviceKey": self.api_key,
            "numOfRows": 100,
            "pageNo": 1,
            "type": "json",
        }
        if params:
            request_params.update(params)

        try:
            response = self._session.get(url, params=request_params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # R-ONE API wraps response in 'response' > 'body' > 'items'
            if isinstance(data, dict):
                body = data.get("response", data).get("body", data)
                items = body.get("items", {})
                if isinstance(items, dict):
                    item_list = items.get("item", [])
                elif isinstance(items, list):
                    item_list = items
                else:
                    item_list = []

                if not isinstance(item_list, list):
                    item_list = [item_list]

                return {"success": True, "data": item_list, "total_count": body.get("totalCount", len(item_list))}

            return {"success": True, "data": data if isinstance(data, list) else []}

        except requests.exceptions.Timeout:
            return {"error": True, "message": "R-ONE API timeout"}
        except requests.exceptions.HTTPError as e:
            return {"error": True, "message": f"R-ONE API HTTP error: {e}"}
        except ValueError:
            return {"error": True, "message": "R-ONE API returned invalid JSON"}
        except requests.exceptions.RequestException as e:
            return {"error": True, "message": f"R-ONE API request error: {e}"}

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

    def get_apt_price_index(
        self,
        region: str,
        start_month: str = None,
        end_month: str = None,
    ) -> Dict[str, Any]:
        """Get apartment price index — real API only, no fake data."""
        if not self.api_key:
            return {"error": True, "message": "RONE_API_KEY not set. data.go.kr에서 한국부동산원 API 키를 발급받아 .env에 설정하세요."}

        if start_month is None:
            start_month = (datetime.now() - timedelta(days=365)).strftime("%Y-%m")
        if end_month is None:
            end_month = datetime.now().strftime("%Y-%m")

        cache_key = {"method": "apt_price", "region": region, "start": start_month, "end": end_month}
        cached = self._cache.get("rone", cache_key)
        if cached:
            return cached

        region_code = REGION_CODES.get(region, "0000000000")
        api_result = self._make_api_request("getAptTradingPriceIndex", {
            "regionCode": region_code,
            "startMonth": start_month.replace("-", ""),
            "endMonth": end_month.replace("-", ""),
        })

        if api_result.get("error"):
            return {"error": True, "message": f"R-ONE API 호출 실패: {api_result['message']}. data.go.kr API 키를 확인하세요."}

        items = api_result.get("data", [])
        response = {
            "success": True,
            "indicator": "아파트매매가격지수",
            "region": region,
            "period": {"start": start_month, "end": end_month},
            "data_source": "rone_api",
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
        """Get jeonse (deposit lease) price index — real API only."""
        if not self.api_key:
            return {"error": True, "message": "RONE_API_KEY not set. data.go.kr에서 API 키를 발급받으세요."}

        if start_month is None:
            start_month = (datetime.now() - timedelta(days=365)).strftime("%Y-%m")
        if end_month is None:
            end_month = datetime.now().strftime("%Y-%m")

        cache_key = {"method": "jeonse", "region": region, "start": start_month, "end": end_month}
        cached = self._cache.get("rone", cache_key)
        if cached:
            return cached

        region_code = REGION_CODES.get(region, "0000000000")
        api_result = self._make_api_request("getAptJeonsePriceIndex", {
            "regionCode": region_code,
            "startMonth": start_month.replace("-", ""),
            "endMonth": end_month.replace("-", ""),
        })

        if api_result.get("error"):
            return {"error": True, "message": f"R-ONE API 호출 실패: {api_result['message']}"}

        items = api_result.get("data", [])
        response = {
            "success": True,
            "indicator": "전세가격지수",
            "region": region,
            "period": {"start": start_month, "end": end_month},
            "data_source": "rone_api",
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
        """Get Price to Income Ratio — real API only."""
        if not self.api_key:
            return {"error": True, "message": "RONE_API_KEY not set. data.go.kr에서 API 키를 발급받으세요."}

        cache_key = {"method": "pir", "region": region}
        cached = self._cache.get("rone", cache_key)
        if cached:
            return cached

        region_code = REGION_CODES.get(region, "0000000000")
        api_result = self._make_api_request("getPIR", {
            "regionCode": region_code,
        })

        if api_result.get("error"):
            return {"error": True, "message": f"R-ONE API 호출 실패: {api_result['message']}"}

        items = api_result.get("data", [])
        pir_value = float(items[0].get("pir", 0)) if items else 0
        affordability = self._interpret_pir(pir_value)

        response = {
            "success": True,
            "indicator": "PIR (소득대비주택가격)",
            "region": region,
            "pir": pir_value,
            "interpretation": affordability,
            "note": f"중위가구가 중위주택을 구입하려면 {pir_value:.1f}년 소득이 필요",
            "data_source": "rone_api",
            "data": items,
        }

        self._cache.set("rone", cache_key, response, "daily_data")
        return response

    def get_price_comparison(self, regions: List[str]) -> Dict[str, Any]:
        """Compare apartment prices across regions."""
        comparison = []

        for region in regions:
            result = self.get_apt_price_index(region)
            if result.get("success") and result.get("latest"):
                latest = result["latest"]
                comparison.append({
                    "region": region,
                    "index": latest.get("index"),
                    "change_mom": latest.get("change_mom"),
                    "change_yoy": latest.get("change_yoy"),
                })

        # Sort by YoY change
        comparison.sort(key=lambda x: x.get("change_yoy", 0), reverse=True)

        return {
            "success": True,
            "indicator": "아파트매매가격지수 비교",
            "regions": regions,
            "data": comparison,
            "highest_growth": comparison[0]["region"] if comparison else None,
            "lowest_growth": comparison[-1]["region"] if comparison else None,
        }

    def get_market_summary(self) -> Dict[str, Any]:
        """Get overall market summary."""
        if not self.api_key:
            return {"error": True, "message": "RONE_API_KEY not set. data.go.kr에서 API 키를 발급받으세요."}

        seoul = self.get_apt_price_index("서울")
        nationwide = self.get_apt_price_index("전국")
        seoul_pir = self.get_pir("서울")
        nationwide_pir = self.get_pir("전국")
        seoul_jeonse = self.get_jeonse_index("서울")

        # If all APIs failed, return error
        if seoul.get("error") and nationwide.get("error"):
            return {"error": True, "message": "R-ONE API 호출 실패. API 키를 확인하세요."}

        summary = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "data_source": "rone_api",
        }

        # Apartment prices (safe access with .get())
        latest_seoul = seoul.get("latest") or {}
        if latest_seoul:
            summary["seoul_apt"] = {
                "index": latest_seoul.get("index"),
                "change_mom": latest_seoul.get("change_mom"),
                "change_yoy": latest_seoul.get("change_yoy"),
            }

        latest_nationwide = nationwide.get("latest") or {}
        if latest_nationwide:
            summary["nationwide_apt"] = {
                "index": latest_nationwide.get("index"),
                "change_mom": latest_nationwide.get("change_mom"),
                "change_yoy": latest_nationwide.get("change_yoy"),
            }

        # PIR
        summary["pir"] = {
            "서울": seoul_pir.get("pir"),
            "전국": nationwide_pir.get("pir"),
        }

        # Jeonse
        latest_jeonse = seoul_jeonse.get("latest") or {}
        if latest_jeonse:
            summary["seoul_jeonse"] = {
                "index": latest_jeonse.get("index"),
                "change_mom": latest_jeonse.get("change_mom"),
            }

        # Market assessment (safe)
        seoul_yoy = float(latest_seoul.get("change_yoy", 0) or 0)
        if seoul_yoy > 5:
            summary["market_condition"] = "과열"
        elif seoul_yoy > 2:
            summary["market_condition"] = "상승"
        elif seoul_yoy > -2:
            summary["market_condition"] = "보합"
        elif seoul_yoy > -5:
            summary["market_condition"] = "하락"
        else:
            summary["market_condition"] = "급락"

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
