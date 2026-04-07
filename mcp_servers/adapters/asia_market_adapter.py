"""
Asian Markets Adapter — China (SSE/SZSE), Taiwan (TWSE), Hong Kong (HKEX).

Provides stock quotes, indices, and historical data for Greater China markets
via yfinance (Yahoo Finance) as the universal data source.

Symbol conventions:
  - China Shanghai: 600519.SS (Moutai), 601398.SS (ICBC)
  - China Shenzhen: 000001.SZ (Ping An), 000858.SZ (Wuliangye)
  - Taiwan: 2330.TW (TSMC), 2317.TW (Hon Hai)
  - Hong Kong: 0700.HK (Tencent), 9988.HK (Alibaba)

Run standalone test: python -m mcp_servers.adapters.asia_market_adapter
"""
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.core.cache_manager import CacheManager, get_cache
from mcp_servers.core.rate_limiter import RateLimiter, get_limiter
from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)


class AsiaMarketAdapter:
    """Adapter for China, Taiwan, and Hong Kong market data via yfinance."""

    # Major indices
    INDICES = {
        "sse_composite": {"symbol": "000001.SS", "name": "SSE Composite (上证综指)"},
        "szse_component": {"symbol": "399001.SZ", "name": "SZSE Component (深证成指)"},
        "taiex": {"symbol": "^TWII", "name": "TAIEX (加權指數)"},
        "hsi": {"symbol": "^HSI", "name": "Hang Seng Index (恒生指數)"},
    }

    def __init__(
        self,
        cache: CacheManager = None,
        limiter: RateLimiter = None,
    ):
        self._cache = cache or get_cache()
        self._limiter = limiter or get_limiter()
        self._yf = None
        try:
            import yfinance as yf
            self._yf = yf
            logger.info("AsiaMarketAdapter: yfinance initialized")
        except ImportError:
            logger.error("yfinance not installed. Run: pip install yfinance")
        except Exception as e:
            logger.error(f"Failed to initialize yfinance: {e}")

    # ── helpers ───────────────────────────────────────────────────────

    def _get_quote(self, symbol: str, market: str) -> Dict[str, Any]:
        """Generic quote fetcher via yfinance."""
        if not self._yf:
            return error_response("yfinance not initialized")
        try:
            self._limiter.acquire("yahoo")
            cache_key = {"method": "asia_quote", "symbol": symbol}
            cached = self._cache.get("asia_market", cache_key)
            if cached:
                return cached

            ticker = self._yf.Ticker(symbol)
            info = ticker.info

            result = success_response(
                data=None,
                source="Yahoo Finance",
                market=market,
                symbol=symbol,
                name=info.get("longName", info.get("shortName", symbol)),
                price=info.get("currentPrice", info.get("regularMarketPrice")),
                previous_close=info.get("previousClose"),
                change=info.get("regularMarketChange"),
                change_pct=info.get("regularMarketChangePercent"),
                open=info.get("regularMarketOpen"),
                day_high=info.get("regularMarketDayHigh"),
                day_low=info.get("regularMarketDayLow"),
                volume=info.get("regularMarketVolume"),
                market_cap=info.get("marketCap"),
                currency=info.get("currency", ""),
                exchange=info.get("exchange", ""),
            )

            self._cache.set("asia_market", cache_key, result, "realtime")
            return result

        except Exception as e:
            logger.error(f"Quote error for {symbol}: {e}")
            return error_response(f"Quote retrieval failed for {symbol}: {e}")

    def _get_index(self, symbol: str, name: str) -> Dict[str, Any]:
        """Fetch a single index value."""
        if not self._yf:
            return error_response("yfinance not initialized")
        try:
            self._limiter.acquire("yahoo")
            cache_key = {"method": "asia_index", "symbol": symbol}
            cached = self._cache.get("asia_market", cache_key)
            if cached:
                return cached

            ticker = self._yf.Ticker(symbol)
            info = ticker.info

            result = success_response(
                data=None,
                source="Yahoo Finance",
                symbol=symbol,
                name=name,
                value=info.get("regularMarketPrice"),
                previous_close=info.get("previousClose"),
                change=info.get("regularMarketChange"),
                change_pct=info.get("regularMarketChangePercent"),
                day_high=info.get("regularMarketDayHigh"),
                day_low=info.get("regularMarketDayLow"),
                volume=info.get("regularMarketVolume"),
            )

            self._cache.set("asia_market", cache_key, result, "realtime")
            return result

        except Exception as e:
            logger.error(f"Index error for {symbol}: {e}")
            return error_response(f"Index retrieval failed for {symbol}: {e}")

    def _get_history(self, symbol: str, period: str, market: str) -> Dict[str, Any]:
        """Fetch OHLCV history."""
        if not self._yf:
            return error_response("yfinance not initialized")
        try:
            self._limiter.acquire("yahoo")
            cache_key = {"method": "asia_history", "symbol": symbol, "period": period}
            cached = self._cache.get("asia_market", cache_key)
            if cached:
                return cached

            ticker = self._yf.Ticker(symbol)
            hist = ticker.history(period=period)

            if hist.empty:
                return error_response(f"No history data for {symbol}")

            records = []
            for date, row in hist.iterrows():
                records.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": round(float(row["Open"]), 4),
                    "high": round(float(row["High"]), 4),
                    "low": round(float(row["Low"]), 4),
                    "close": round(float(row["Close"]), 4),
                    "volume": int(row["Volume"]),
                })

            result = success_response(
                data=records[-60:] if len(records) > 60 else records,
                source="Yahoo Finance",
                market=market,
                symbol=symbol,
                period=period,
                data_points=len(records),
                summary={
                    "start_date": records[0]["date"],
                    "end_date": records[-1]["date"],
                    "start_close": records[0]["close"],
                    "end_close": records[-1]["close"],
                    "period_return_pct": round(
                        (records[-1]["close"] - records[0]["close"]) / records[0]["close"] * 100, 2
                    ),
                    "highest": max(r["high"] for r in records),
                    "lowest": min(r["low"] for r in records),
                    "avg_volume": int(sum(r["volume"] for r in records) / len(records)),
                },
            )

            self._cache.set("asia_market", cache_key, result, "daily_data")
            return result

        except Exception as e:
            logger.error(f"History error for {symbol}: {e}")
            return error_response(f"History retrieval failed for {symbol}: {e}")

    # ── China (SSE / SZSE) ────────────────────────────────────────────

    def get_china_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get China A-share stock quote.

        Args:
            symbol: Yahoo format — 600519.SS (Shanghai), 000001.SZ (Shenzhen)
        """
        return self._get_quote(symbol, "China A-Share")

    def get_china_index(self) -> Dict[str, Any]:
        """Get SSE Composite and SZSE Component indices."""
        sse = self._get_index(
            self.INDICES["sse_composite"]["symbol"],
            self.INDICES["sse_composite"]["name"],
        )
        szse = self._get_index(
            self.INDICES["szse_component"]["symbol"],
            self.INDICES["szse_component"]["name"],
        )
        return success_response(
            data=None,
            source="Yahoo Finance",
            market="China",
            indices={"sse_composite": sse, "szse_component": szse},
        )

    def get_china_stock_history(
        self, symbol: str, period: str = "1y"
    ) -> Dict[str, Any]:
        """
        Get China stock OHLCV history.

        Args:
            symbol: Yahoo format — 600519.SS, 000001.SZ
            period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, ytd, max
        """
        return self._get_history(symbol, period, "China A-Share")

    # ── Taiwan (TWSE) ─────────────────────────────────────────────────

    def get_taiwan_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get Taiwan stock quote.

        Args:
            symbol: Yahoo format — 2330.TW (TSMC), 2317.TW (Hon Hai)
        """
        return self._get_quote(symbol, "Taiwan TWSE")

    def get_taiwan_index(self) -> Dict[str, Any]:
        """Get TAIEX index."""
        return self._get_index(
            self.INDICES["taiex"]["symbol"],
            self.INDICES["taiex"]["name"],
        )

    def get_taiwan_top_trades(self, date: str = "") -> Dict[str, Any]:
        """
        Get Taiwan top traded stocks from TWSE.

        Args:
            date: Date in YYYYMMDD format (empty = latest)
        """
        import requests

        try:
            url = "https://www.twse.com.tw/exchangeReport/MI_INDEX20"
            params = {"response": "json"}
            if date:
                params["date"] = date

            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()

            if data.get("stat") != "OK":
                return error_response(f"TWSE API returned: {data.get('stat', 'unknown')}")

            fields = data.get("fields", [])
            rows = data.get("data", [])

            records = []
            for row in rows[:20]:
                record = {}
                for i, field in enumerate(fields):
                    if i < len(row):
                        record[field] = row[i]
                records.append(record)

            return success_response(
                data=records,
                source="Yahoo Finance",
                market="Taiwan TWSE",
                date=data.get("date", date),
            )

        except Exception as e:
            logger.error(f"Taiwan top trades error: {e}")
            return error_response(f"TWSE top trades failed: {e}")

    # ── Hong Kong (HKEX) ──────────────────────────────────────────────

    def get_hk_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get Hong Kong stock quote.

        Args:
            symbol: Yahoo format — 0700.HK (Tencent), 9988.HK (Alibaba)
        """
        return self._get_quote(symbol, "Hong Kong HKEX")

    def get_hk_index(self) -> Dict[str, Any]:
        """Get Hang Seng Index."""
        return self._get_index(
            self.INDICES["hsi"]["symbol"],
            self.INDICES["hsi"]["name"],
        )


# ── standalone test ───────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    adapter = AsiaMarketAdapter()

    print("=== China: Moutai (600519.SS) ===")
    print(adapter.get_china_stock_quote("600519.SS"))

    print("\n=== China Indices ===")
    print(adapter.get_china_index())

    print("\n=== Taiwan: TSMC (2330.TW) ===")
    print(adapter.get_taiwan_stock_quote("2330.TW"))

    print("\n=== Taiwan Index ===")
    print(adapter.get_taiwan_index())

    print("\n=== HK: Tencent (0700.HK) ===")
    print(adapter.get_hk_stock_quote("0700.HK"))

    print("\n=== Hang Seng Index ===")
    print(adapter.get_hk_index())
