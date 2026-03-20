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


# Region codes for R-ONE
REGION_CODES = {
    "전국": "0000000000",
    "서울": "1100000000",
    "강남구": "1168000000",
    "서초구": "1165000000",
    "송파구": "1171000000",
    "마포구": "1144000000",
    "용산구": "1117000000",
    "부산": "2600000000",
    "대구": "2700000000",
    "인천": "2800000000",
    "광주": "2900000000",
    "대전": "3000000000",
    "울산": "3100000000",
    "세종": "3600000000",
    "경기": "4100000000",
    "수원": "4111000000",
    "성남": "4113000000",
    "고양": "4128000000",
    "용인": "4146000000",
}

# Sample data for demonstration (when API unavailable)
SAMPLE_DATA = {
    "apt_price_index": {
        "서울": [
            {"date": "2024-01", "index": 100.0, "change_mom": 0.02, "change_yoy": -2.5},
            {"date": "2024-02", "index": 100.1, "change_mom": 0.10, "change_yoy": -2.3},
            {"date": "2024-03", "index": 100.3, "change_mom": 0.20, "change_yoy": -2.0},
            {"date": "2024-04", "index": 100.6, "change_mom": 0.30, "change_yoy": -1.5},
            {"date": "2024-05", "index": 101.0, "change_mom": 0.40, "change_yoy": -1.0},
            {"date": "2024-06", "index": 101.5, "change_mom": 0.50, "change_yoy": -0.3},
            {"date": "2024-07", "index": 102.2, "change_mom": 0.69, "change_yoy": 0.5},
            {"date": "2024-08", "index": 103.0, "change_mom": 0.78, "change_yoy": 1.5},
            {"date": "2024-09", "index": 103.8, "change_mom": 0.78, "change_yoy": 2.5},
            {"date": "2024-10", "index": 104.5, "change_mom": 0.67, "change_yoy": 3.2},
            {"date": "2024-11", "index": 105.0, "change_mom": 0.48, "change_yoy": 3.8},
            {"date": "2024-12", "index": 105.3, "change_mom": 0.29, "change_yoy": 4.0},
        ],
        "전국": [
            {"date": "2024-01", "index": 100.0, "change_mom": -0.05, "change_yoy": -3.0},
            {"date": "2024-06", "index": 100.5, "change_mom": 0.20, "change_yoy": -1.5},
            {"date": "2024-12", "index": 102.0, "change_mom": 0.15, "change_yoy": 1.0},
        ],
    },
    "jeonse_index": {
        "서울": [
            {"date": "2024-01", "index": 95.0, "change_mom": 0.10, "change_yoy": -5.0},
            {"date": "2024-06", "index": 97.0, "change_mom": 0.30, "change_yoy": -3.0},
            {"date": "2024-12", "index": 100.0, "change_mom": 0.40, "change_yoy": 0.5},
        ],
    },
    "pir": {
        "서울": 18.5,
        "전국": 8.2,
        "수도권": 12.3,
        "강남구": 25.0,
    },
}


class RONEServer:
    """R-ONE MCP Server for Korean real estate data."""

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

        # Use sample data if no API key
        self._use_sample = not self.api_key
        if self._use_sample:
            logger.info("R-ONE API key not set. Using sample data.")

        # Create FastMCP server
        self.mcp = FastMCP("rone")
        self._register_tools()

        logger.info("R-ONE MCP Server initialized")

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
        """Get apartment price index."""
        if start_month is None:
            start_month = (datetime.now() - timedelta(days=365)).strftime("%Y-%m")
        if end_month is None:
            end_month = datetime.now().strftime("%Y-%m")

        cache_key = {"method": "apt_price", "region": region, "start": start_month, "end": end_month}
        cached = self._cache.get("rone", cache_key)
        if cached:
            return cached

        if self._use_sample:
            # Use sample data
            data = SAMPLE_DATA["apt_price_index"].get(region, SAMPLE_DATA["apt_price_index"]["전국"])

            # Filter by date range
            filtered = [d for d in data if start_month <= d["date"] <= end_month]

            response = {
                "success": True,
                "indicator": "아파트매매가격지수",
                "region": region,
                "period": {"start": start_month, "end": end_month},
                "data_source": "sample_data",
                "count": len(filtered),
                "data": filtered,
                "latest": filtered[-1] if filtered else None,
            }
        else:
            # Real API call would go here
            response = {
                "success": True,
                "indicator": "아파트매매가격지수",
                "region": region,
                "data_source": "rone_api",
                "data": [],
                "message": "Real API integration pending",
            }

        self._cache.set("rone", cache_key, response, "daily_data")
        return response

    def get_jeonse_index(
        self,
        region: str,
        start_month: str = None,
        end_month: str = None,
    ) -> Dict[str, Any]:
        """Get jeonse (deposit lease) price index."""
        if start_month is None:
            start_month = (datetime.now() - timedelta(days=365)).strftime("%Y-%m")
        if end_month is None:
            end_month = datetime.now().strftime("%Y-%m")

        cache_key = {"method": "jeonse", "region": region, "start": start_month, "end": end_month}
        cached = self._cache.get("rone", cache_key)
        if cached:
            return cached

        if self._use_sample:
            data = SAMPLE_DATA["jeonse_index"].get(region, SAMPLE_DATA["jeonse_index"]["서울"])
            filtered = [d for d in data if start_month <= d["date"] <= end_month]

            response = {
                "success": True,
                "indicator": "전세가격지수",
                "region": region,
                "period": {"start": start_month, "end": end_month},
                "data_source": "sample_data",
                "count": len(filtered),
                "data": filtered,
                "latest": filtered[-1] if filtered else None,
            }
        else:
            response = {
                "success": True,
                "indicator": "전세가격지수",
                "region": region,
                "data_source": "rone_api",
                "data": [],
                "message": "Real API integration pending",
            }

        self._cache.set("rone", cache_key, response, "daily_data")
        return response

    def get_pir(self, region: str) -> Dict[str, Any]:
        """Get Price to Income Ratio."""
        cache_key = {"method": "pir", "region": region}
        cached = self._cache.get("rone", cache_key)
        if cached:
            return cached

        if self._use_sample:
            pir_value = SAMPLE_DATA["pir"].get(region, SAMPLE_DATA["pir"]["전국"])

            # Interpretation
            if pir_value < 5:
                affordability = "매우 양호"
            elif pir_value < 10:
                affordability = "양호"
            elif pir_value < 15:
                affordability = "부담"
            elif pir_value < 20:
                affordability = "높은 부담"
            else:
                affordability = "매우 높은 부담"

            response = {
                "success": True,
                "indicator": "PIR (소득대비주택가격)",
                "region": region,
                "pir": pir_value,
                "interpretation": affordability,
                "note": f"중위가구가 중위주택을 구입하려면 {pir_value:.1f}년 소득이 필요",
                "data_source": "sample_data",
                "comparison": {
                    "서울": SAMPLE_DATA["pir"]["서울"],
                    "전국": SAMPLE_DATA["pir"]["전국"],
                },
            }
        else:
            response = {
                "success": True,
                "indicator": "PIR",
                "region": region,
                "data_source": "rone_api",
                "message": "Real API integration pending",
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
        seoul = self.get_apt_price_index("서울")
        nationwide = self.get_apt_price_index("전국")
        seoul_pir = self.get_pir("서울")
        nationwide_pir = self.get_pir("전국")
        seoul_jeonse = self.get_jeonse_index("서울")

        summary = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "data_source": "sample_data" if self._use_sample else "rone_api",
        }

        # Apartment prices
        if seoul.get("latest"):
            summary["seoul_apt"] = {
                "index": seoul["latest"]["index"],
                "change_mom": f"{seoul['latest']['change_mom']:.2f}%",
                "change_yoy": f"{seoul['latest']['change_yoy']:.2f}%",
            }

        if nationwide.get("latest"):
            summary["nationwide_apt"] = {
                "index": nationwide["latest"]["index"],
                "change_mom": f"{nationwide['latest']['change_mom']:.2f}%",
                "change_yoy": f"{nationwide['latest']['change_yoy']:.2f}%",
            }

        # PIR
        summary["pir"] = {
            "서울": seoul_pir.get("pir"),
            "전국": nationwide_pir.get("pir"),
        }

        # Jeonse
        if seoul_jeonse.get("latest"):
            summary["seoul_jeonse"] = {
                "index": seoul_jeonse["latest"]["index"],
                "change_mom": f"{seoul_jeonse['latest']['change_mom']:.2f}%",
            }

        # Market assessment
        seoul_yoy = seoul["latest"]["change_yoy"] if seoul.get("latest") else 0
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
