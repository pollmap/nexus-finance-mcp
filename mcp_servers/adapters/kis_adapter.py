"""
KIS Adapter - Korea Investment & Securities API.

Official brokerage API for Korean stock market data.
More reliable than pykrx scraping.

Provides:
- Real-time / delayed stock quotes
- Stock info (company name, sector, market cap)
- ETF data
- Market indices

Requires: KIS_API_KEY env var
API Docs: https://apiportal.koreainvestment.com

Run standalone test: python -m mcp_servers.adapters.kis_adapter
"""
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.core.cache_manager import CacheManager, get_cache
from mcp_servers.core.rate_limiter import RateLimiter, get_limiter
from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)


class KISAdapter:
    """
    Adapter for Korea Investment & Securities Open API.

    Uses the open trading API for market data queries.
    Note: This adapter is read-only (no order execution).
    """

    BASE_URL = "https://openapi.koreainvestment.com:9443"

    # Top 50 Korean stocks by market cap
    STOCK_CODES = {
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
        "현대건설": "000720", "삼성엔지니어링": "028050", "한화": "000880",
        "삼성중공업": "010140", "대한항공": "003490", "CJ제일제당": "097950",
        "아모레퍼시픽": "090430", "LG생활건강": "051900", "넷마블": "251270",
        "엔씨소프트": "036570", "한국가스공사": "036460",
        "에코프로비엠": "247540", "에코프로": "086520", "알테오젠": "196170",
        "HLB": "028300", "리노공업": "058470",
    }

    def __init__(
        self,
        cache: CacheManager = None,
        limiter: RateLimiter = None,
    ):
        self._cache = cache or get_cache()
        self._limiter = limiter or get_limiter()

        self._app_key = os.getenv("KIS_API_KEY", "")
        self._app_secret = os.getenv("KIS_APP_SECRET", "")
        self._access_token = None
        self._token_expires = None

        if not self._app_key:
            logger.warning("KIS_API_KEY not set. KIS adapter will use fallback mode.")

    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers."""
        headers = {
            "content-type": "application/json; charset=utf-8",
            "appkey": self._app_key,
            "appsecret": self._app_secret,
        }
        if self._access_token:
            headers["authorization"] = f"Bearer {self._access_token}"
        return headers

    def _authenticate(self) -> bool:
        """Get OAuth access token (if app_secret is available)."""
        if not self._app_key or not self._app_secret:
            return False

        if self._access_token and self._token_expires and datetime.now() < self._token_expires:
            return True

        try:
            url = f"{self.BASE_URL}/oauth2/tokenP"
            body = {
                "grant_type": "client_credentials",
                "appkey": self._app_key,
                "appsecret": self._app_secret,
            }
            resp = requests.post(url, json=body, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                self._access_token = data.get("access_token")
                expires_in = int(data.get("expires_in", 86400))
                self._token_expires = datetime.now() + timedelta(seconds=expires_in - 60)
                logger.info("KIS OAuth token acquired")
                return True
        except Exception as e:
            logger.error(f"KIS auth failed: {e}")

        return False

    def get_stock_quote(self, stock_code: str) -> Dict[str, Any]:
        """
        Get current stock quote (price, volume, change).

        Args:
            stock_code: Stock code (e.g., "005930")

        Returns:
            Current quote data
        """
        cache_key = {"method": "quote", "code": stock_code}
        cached = self._cache.get("kis", cache_key)
        if cached:
            return cached

        # Try KIS API first, then fallback to pykrx
        if self._app_key and self._app_secret:
            result = self._fetch_quote_kis(stock_code)
            if result and not result.get("error"):
                self._cache.set("kis", cache_key, result, "realtime_price")
                return result

        # Fallback to pykrx
        result = self._fetch_quote_pykrx(stock_code)
        if result:
            self._cache.set("kis", cache_key, result, "daily_data")
        return result

    def _fetch_quote_kis(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """Fetch quote from KIS API."""
        try:
            self._authenticate()
            self._limiter.acquire("kis")

            url = f"{self.BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"
            headers = self._get_headers()
            headers["tr_id"] = "FHKST01010100"  # 주식현재가 시세

            params = {
                "FID_COND_MRKT_DIV_CODE": "J",  # 주식
                "FID_INPUT_ISCD": stock_code,
            }

            resp = requests.get(url, headers=headers, params=params, timeout=10)
            if resp.status_code != 200:
                return None

            data = resp.json()
            output = data.get("output", {})

            if not output:
                return None

            return success_response(
                None,
                source="KIS",
                stock_code=stock_code,
                stock_name=output.get("stck_shrn_iscd", stock_code),
                current_price=int(output.get("stck_prpr", 0)),
                change=int(output.get("prdy_vrss", 0)),
                change_pct=float(output.get("prdy_ctrt", 0)),
                volume=int(output.get("acml_vol", 0)),
                trade_value=int(output.get("acml_tr_pbmn", 0)),
                high=int(output.get("stck_hgpr", 0)),
                low=int(output.get("stck_lwpr", 0)),
                open=int(output.get("stck_oprc", 0)),
                market_cap=int(output.get("hts_avls", 0)) * 100000000,  # 억원 → 원
                per=float(output.get("per", 0)),
                pbr=float(output.get("pbr", 0)),
                timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            logger.error(f"KIS quote error: {e}")
            return None

    def _fetch_quote_pykrx(self, stock_code: str) -> Dict[str, Any]:
        """Fallback: fetch quote from pykrx."""
        try:
            from pykrx import stock

            today = datetime.now().strftime("%Y%m%d")
            start = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

            df = stock.get_market_ohlcv_by_date(start, today, stock_code)
            if df is None or df.empty:
                return error_response("No data from pykrx")

            latest = df.iloc[-1]
            name = stock.get_market_ticker_name(stock_code)

            return success_response(
                None,
                source="pykrx_fallback",
                stock_code=stock_code,
                stock_name=name or stock_code,
                current_price=int(latest.get("종가", 0)),
                change_pct=float(latest.get("등락률", 0)),
                volume=int(latest.get("거래량", 0)),
                high=int(latest.get("고가", 0)),
                low=int(latest.get("저가", 0)),
                open=int(latest.get("시가", 0)),
                timestamp=datetime.now().isoformat(),
                note="Delayed data (pykrx fallback)",
            )
        except Exception as e:
            logger.error(f"pykrx fallback error: {e}")
            return error_response(f"Both KIS and pykrx failed: {e}")

    def get_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """
        Get stock fundamental info.

        Args:
            stock_code: Stock code

        Returns:
            Company info (sector, market cap, PER, PBR, etc.)
        """
        # This reuses quote data which includes fundamentals
        quote = self.get_stock_quote(stock_code)
        if quote.get("error"):
            return quote

        return success_response(
            None,
            source=quote.get("source", "KIS"),
            stock_code=stock_code,
            stock_name=quote.get("stock_name", stock_code),
            current_price=quote.get("current_price"),
            market_cap=quote.get("market_cap"),
            per=quote.get("per"),
            pbr=quote.get("pbr"),
            volume=quote.get("volume"),
        )

    def search_stock(self, keyword: str) -> Dict[str, Any]:
        """
        Search stock by name or code.

        Args:
            keyword: Company name (Korean) or stock code

        Returns:
            Matching stocks
        """
        # Check preset codes first
        results = []
        for name, code in self.STOCK_CODES.items():
            if keyword in name or keyword == code:
                results.append({"code": code, "name": name})

        if results:
            return success_response(results, source="KIS")

        # Fallback to pykrx search
        try:
            from pykrx import stock
            today = datetime.now().strftime("%Y%m%d")

            for market in ["KOSPI", "KOSDAQ"]:
                tickers = stock.get_market_ticker_list(today, market=market)
                for ticker in tickers:
                    name = stock.get_market_ticker_name(ticker)
                    if name and keyword in name:
                        results.append({"code": ticker, "name": name, "market": market})
                    if len(results) >= 10:
                        break
                if len(results) >= 10:
                    break

            return success_response(results, source="KIS")
        except Exception as e:
            return error_response(str(e))


def test_kis_adapter():
    """Test KIS adapter."""
    logging.basicConfig(level=logging.INFO)
    adapter = KISAdapter()

    print("=" * 60)
    print("KIS Adapter Test")
    print("=" * 60)

    print("\n1. Stock Quote (삼성전자)")
    result = adapter.get_stock_quote("005930")
    if result.get("success"):
        print(f"   Source: {result.get('source')}")
        print(f"   Price: {result.get('current_price', 0):,}")
        print(f"   Change: {result.get('change_pct', 0):.2f}%")
    else:
        print(f"   Error: {result.get('message')}")

    print("\n2. Search (카카오)")
    result = adapter.search_stock("카카오")
    if result.get("success"):
        for s in result.get("data", []):
            print(f"   {s['code']} - {s['name']}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_kis_adapter()
