"""
Stocks MCP Server - Korean & Global Stock Market Data.

Combines KIS API (official brokerage) + pykrx (scraping) + Yahoo Finance.
Provides real-time quotes, historical data, and market overview.

Tools:
- stocks_quote: 실시간 주가 조회
- stocks_search: 종목 검색
- stocks_history: 과거 주가 데이터
- stocks_beta: 베타 계산
- stocks_market_overview: 시장 개요 (KOSPI/KOSDAQ/S&P500)
"""
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from fastmcp import FastMCP

from mcp_servers.core.cache_manager import get_cache
from mcp_servers.core.rate_limiter import get_limiter
from mcp_servers.adapters.kis_adapter import KISAdapter
from mcp_servers.adapters.krx_adapter import KRXAdapter
from mcp_servers.adapters.yahoo_adapter import YahooAdapter

logger = logging.getLogger(__name__)


class StocksServer:
    """Stocks MCP Server combining KIS + pykrx + Yahoo Finance."""

    def __init__(self):
        self._cache = get_cache()
        self._limiter = get_limiter()

        self._kis = KISAdapter(cache=self._cache, limiter=self._limiter)
        self._krx = KRXAdapter(cache=self._cache, limiter=self._limiter)
        self._yahoo = None
        try:
            self._yahoo = YahooAdapter(cache=self._cache, limiter=self._limiter)
        except Exception as e:
            logger.warning(f"Yahoo adapter init failed: {e}")

        self.mcp = FastMCP("stocks")
        self._register_tools()
        logger.info("Stocks MCP Server initialized")

    def _register_tools(self):

        @self.mcp.tool()
        def stocks_quote(
            stock_code: str,
            market: str = "KR",
        ) -> dict:
            """
            실시간 주가 조회 (한국: KIS/pykrx, 미국: Yahoo Finance).

            Args:
                stock_code: 종목코드 (한국: 005930, 미국: AAPL)
                market: KR (한국) 또는 US (미국)

            Returns:
                현재가, 등락률, 거래량, PER, PBR 등
            """
            if market.upper() == "KR":
                return self._kis.get_stock_quote(stock_code)
            elif market.upper() == "US" and self._yahoo:
                return self._yahoo.get_stock_price(stock_code)
            else:
                return {"error": True, "message": f"Unsupported market: {market}"}

        @self.mcp.tool()
        def stocks_search(keyword: str) -> dict:
            """
            종목 검색 (한국어 회사명 또는 코드).

            Args:
                keyword: 검색어 (예: 삼성전자, 카카오, 005930)

            Returns:
                매칭 종목 목록
            """
            return self._kis.search_stock(keyword)

        @self.mcp.tool()
        def stocks_history(
            stock_code: str,
            start_date: str = None,
            end_date: str = None,
            market: str = "KR",
            interval: str = "daily",
            limit: int = 0,
        ) -> dict:
            """
            과거 주가 데이터 (OHLCV).

            Args:
                stock_code: 종목코드
                start_date: 시작일 (YYYYMMDD)
                end_date: 종료일 (YYYYMMDD)
                market: KR 또는 US
                interval: daily(기본), weekly, monthly — 주봉/월봉 리샘플링
                limit: 최근 N건만 반환 (0=전체)

            Returns:
                OHLCV 데이터
            """
            if market.upper() == "KR":
                result = self._krx.get_stock_price(stock_code, start_date, end_date)
            elif market.upper() == "US" and self._yahoo:
                result = self._yahoo.get_stock_price(stock_code, start_date, end_date)
            else:
                return {"error": True, "message": f"Unsupported market: {market}"}

            if result.get("error") or not result.get("data"):
                return result

            # Resample if needed
            if interval in ("weekly", "monthly"):
                import pandas as pd
                df = pd.DataFrame(result["data"])
                df.columns = [c.lower() for c in df.columns]
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date").sort_index()
                rule = "W" if interval == "weekly" else "ME"
                agg = {}
                for col in df.columns:
                    if col == "open":
                        agg[col] = "first"
                    elif col == "high":
                        agg[col] = "max"
                    elif col == "low":
                        agg[col] = "min"
                    elif col == "close":
                        agg[col] = "last"
                    elif col in ("volume", "value"):
                        agg[col] = "sum"
                    else:
                        agg[col] = "last"
                df = df.resample(rule).agg(agg).dropna(subset=["close"])
                df = df.reset_index()
                df["date"] = df["date"].astype(str)
                from mcp_servers.core.responses import sanitize_records
                result["data"] = sanitize_records(df)
                result["interval"] = interval
                result["count"] = len(result["data"])

            # Apply limit
            if limit > 0 and len(result.get("data", [])) > limit:
                result["data"] = result["data"][-limit:]
                result["count"] = len(result["data"])
                result["limited"] = True

            return result

        @self.mcp.tool()
        def stocks_beta(
            stock_code: str,
            index_code: str = "1001",
            period_days: int = 252,
        ) -> dict:
            """
            베타(β) 계산 — 종목의 시장 대비 민감도.

            Args:
                stock_code: 종목코드 (예: 005930)
                index_code: 지수코드 (1001=KOSPI, 2001=KOSDAQ)
                period_days: 계산 기간 (거래일 수, 기본 252일=1년)

            Returns:
                베타, 상관계수, 변동성
            """
            return self._krx.calculate_beta(stock_code, index_code, period_days)

        @self.mcp.tool()
        def stocks_market_overview() -> dict:
            """
            한국 + 글로벌 시장 개요 — KOSPI, KOSDAQ, 원/달러.

            Returns:
                주요 지수 현재값, 등락률
            """
            overview = {"timestamp": datetime.now().isoformat(), "indices": {}}

            # KOSPI
            try:
                kospi = self._krx.get_index_data("1001")
                if kospi.get("success") and kospi.get("latest"):
                    overview["indices"]["KOSPI"] = kospi["latest"]
            except Exception as e:
                overview["indices"]["KOSPI"] = {"error": str(e)}

            # KOSDAQ
            try:
                kosdaq = self._krx.get_index_data("2001")
                if kosdaq.get("success") and kosdaq.get("latest"):
                    overview["indices"]["KOSDAQ"] = kosdaq["latest"]
            except Exception as e:
                overview["indices"]["KOSDAQ"] = {"error": str(e)}

            # S&P 500 via Yahoo
            if self._yahoo:
                try:
                    sp500 = self._yahoo.get_stock_price("^GSPC")
                    if sp500 and not sp500.get("error"):
                        overview["indices"]["SP500"] = sp500
                except Exception as e:
                    overview["indices"]["SP500"] = {"error": str(e)}

            return overview


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = StocksServer()
    server.mcp.run(transport="stdio")
