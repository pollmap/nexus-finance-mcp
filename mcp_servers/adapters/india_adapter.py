"""
India Market Adapter — NSE/BSE via yfinance.

Provides stock quotes, indices, and historical data for Indian markets.

Symbol conventions:
  - NSE: RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS
  - BSE: RELIANCE.BO, TCS.BO, INFY.BO

Run standalone test: python -m mcp_servers.adapters.india_adapter
"""
import logging
import sys
from pathlib import Path
from typing import Any, Dict

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.core.cache_manager import CacheManager, get_cache
from mcp_servers.core.rate_limiter import RateLimiter, get_limiter
from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)


class IndiaAdapter:
    """Adapter for India NSE/BSE market data via yfinance."""

    INDICES = {
        "nifty50": {"symbol": "^NSEI", "name": "Nifty 50"},
        "sensex": {"symbol": "^BSESN", "name": "BSE Sensex"},
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
            logger.info("IndiaAdapter: yfinance initialized")
        except ImportError:
            logger.error("yfinance not installed. Run: pip install yfinance")
        except Exception as e:
            logger.error(f"Failed to initialize yfinance: {e}")

    def get_india_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get Indian stock quote.

        Args:
            symbol: Yahoo format — RELIANCE.NS (NSE), RELIANCE.BO (BSE)
        """
        if not self._yf:
            return error_response("yfinance not initialized")
        try:
            self._limiter.acquire("yahoo")
            cache_key = {"method": "india_quote", "symbol": symbol}
            cached = self._cache.get("india_market", cache_key)
            if cached:
                return cached

            ticker = self._yf.Ticker(symbol)
            info = ticker.info

            result = success_response(
                data=None,
                source="Yahoo Finance",
                market="India NSE/BSE",
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
                currency=info.get("currency", "INR"),
                exchange=info.get("exchange", ""),
                sector=info.get("sector"),
                industry=info.get("industry"),
            )

            self._cache.set("india_market", cache_key, result, "realtime")
            return result

        except Exception as e:
            logger.error(f"India quote error for {symbol}: {e}")
            return error_response(f"Quote retrieval failed for {symbol}: {e}")

    def get_india_index(self) -> Dict[str, Any]:
        """Get Nifty 50 and BSE Sensex indices."""
        if not self._yf:
            return error_response("yfinance not initialized")

        indices = {}
        for key, meta in self.INDICES.items():
            try:
                self._limiter.acquire("yahoo")
                cache_key = {"method": "india_index", "symbol": meta["symbol"]}
                cached = self._cache.get("india_market", cache_key)
                if cached:
                    indices[key] = cached
                    continue

                ticker = self._yf.Ticker(meta["symbol"])
                info = ticker.info

                idx = success_response(
                    data=None,
                    source="Yahoo Finance",
                    symbol=meta["symbol"],
                    name=meta["name"],
                    value=info.get("regularMarketPrice"),
                    previous_close=info.get("previousClose"),
                    change=info.get("regularMarketChange"),
                    change_pct=info.get("regularMarketChangePercent"),
                    day_high=info.get("regularMarketDayHigh"),
                    day_low=info.get("regularMarketDayLow"),
                    volume=info.get("regularMarketVolume"),
                )

                self._cache.set("india_market", cache_key, idx, "realtime")
                indices[key] = idx

            except Exception as e:
                logger.error(f"India index error for {meta['symbol']}: {e}")
                indices[key] = error_response(str(e))

        return success_response(
            data=None,
            source="Yahoo Finance",
            market="India",
            indices=indices,
        )

    def get_india_stock_history(
        self, symbol: str, period: str = "1y"
    ) -> Dict[str, Any]:
        """
        Get Indian stock OHLCV history.

        Args:
            symbol: Yahoo format — RELIANCE.NS, TCS.NS, INFY.BO
            period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, ytd, max
        """
        if not self._yf:
            return error_response("yfinance not initialized")
        try:
            self._limiter.acquire("yahoo")
            cache_key = {"method": "india_history", "symbol": symbol, "period": period}
            cached = self._cache.get("india_market", cache_key)
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
                    "open": round(float(row["Open"]), 2),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "close": round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                })

            result = success_response(
                data=records,
                source="Yahoo Finance",
                market="India NSE/BSE",
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

            self._cache.set("india_market", cache_key, result, "daily_data")
            return result

        except Exception as e:
            logger.error(f"India history error for {symbol}: {e}")
            return error_response(f"History retrieval failed for {symbol}: {e}")


# ── standalone test ───────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_logger = logging.getLogger("india_adapter.test")
    adapter = IndiaAdapter()

    test_logger.info("=== India: Reliance (RELIANCE.NS) ===")
    test_logger.info(adapter.get_india_stock_quote("RELIANCE.NS"))

    test_logger.info("=== India Indices ===")
    test_logger.info(adapter.get_india_index())

    test_logger.info("=== India: TCS History ===")
    test_logger.info(adapter.get_india_stock_history("TCS.NS", "1mo"))
