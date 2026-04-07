"""
CCXT Adapter - Unified Crypto Exchange Interface.

Supports Korean exchanges (Upbit, Bithumb, Korbit, Coinone) + global (Binance).
Public API only — no authentication needed for market data.

Key feature: Kimchi premium calculation (Korean vs global price spread).
"""
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)

# Lazy import — ccxt is heavy
_exchanges = {}


def _get_exchange(exchange_id: str):
    """Get or create exchange instance (lazy singleton)."""
    global _exchanges
    if exchange_id not in _exchanges:
        try:
            import ccxt
            cls = getattr(ccxt, exchange_id, None)
            if cls is None:
                return None
            _exchanges[exchange_id] = cls({"enableRateLimit": True, "timeout": 30000})
        except ImportError:
            logger.error("ccxt not installed. Run: pip install ccxt")
            return None
    return _exchanges[exchange_id]


KOREAN_EXCHANGES = ["upbit", "bithumb", "korbit", "coinone"]
GLOBAL_EXCHANGES = ["binance", "bybit", "okx"]
ALL_EXCHANGES = KOREAN_EXCHANGES + GLOBAL_EXCHANGES


class CCXTAdapter:
    """Unified crypto exchange adapter via ccxt."""

    def get_ticker(self, exchange_id: str, symbol: str) -> Dict[str, Any]:
        """
        Get ticker for a symbol on an exchange.

        Args:
            exchange_id: Exchange name (upbit, bithumb, binance, etc.)
            symbol: Trading pair (BTC/KRW, ETH/USDT, etc.)
        """
        ex = _get_exchange(exchange_id)
        if not ex:
            return error_response(f"Exchange '{exchange_id}' not available", code="NOT_INITIALIZED")

        try:
            ticker = ex.fetch_ticker(symbol)
            return success_response(
                data=None,
                source="CCXT",
                exchange=exchange_id,
                symbol=symbol,
                last=ticker.get("last"),
                bid=ticker.get("bid"),
                ask=ticker.get("ask"),
                high=ticker.get("high"),
                low=ticker.get("low"),
                volume=ticker.get("baseVolume"),
                quote_volume=ticker.get("quoteVolume"),
                change_pct=ticker.get("percentage"),
                timestamp=ticker.get("datetime"),
            )
        except Exception as e:
            return error_response(str(e))

    def get_orderbook(self, exchange_id: str, symbol: str, limit: int = 10) -> Dict[str, Any]:
        """Get orderbook (bids/asks)."""
        ex = _get_exchange(exchange_id)
        if not ex:
            return error_response(f"Exchange '{exchange_id}' not available", code="NOT_INITIALIZED")

        try:
            ob = ex.fetch_order_book(symbol, limit=limit)
            return success_response(
                data=None,
                source="CCXT",
                exchange=exchange_id,
                symbol=symbol,
                bids=[{"price": b[0], "amount": b[1]} for b in ob.get("bids", [])[:limit]],
                asks=[{"price": a[0], "amount": a[1]} for a in ob.get("asks", [])[:limit]],
                timestamp=ob.get("datetime"),
            )
        except Exception as e:
            return error_response(str(e))

    def get_ohlcv(
        self, exchange_id: str, symbol: str, timeframe: str = "1d", limit: int = 100
    ) -> Dict[str, Any]:
        """Get OHLCV candle data."""
        ex = _get_exchange(exchange_id)
        if not ex:
            return error_response(f"Exchange '{exchange_id}' not available", code="NOT_INITIALIZED")

        try:
            candles = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            data = [
                {
                    "timestamp": c[0],
                    "open": c[1],
                    "high": c[2],
                    "low": c[3],
                    "close": c[4],
                    "volume": c[5],
                }
                for c in candles
            ]
            return success_response(
                data=data,
                source="CCXT",
                exchange=exchange_id,
                symbol=symbol,
                timeframe=timeframe,
            )
        except Exception as e:
            return error_response(str(e))

    def get_all_tickers(self, exchange_id: str) -> Dict[str, Any]:
        """Get all tickers from an exchange."""
        ex = _get_exchange(exchange_id)
        if not ex:
            return error_response(f"Exchange '{exchange_id}' not available", code="NOT_INITIALIZED")

        try:
            tickers = ex.fetch_tickers()
            summary = []
            for sym, t in sorted(tickers.items(), key=lambda x: -(x[1].get("quoteVolume") or 0)):
                summary.append({
                    "symbol": sym,
                    "last": t.get("last"),
                    "change_pct": t.get("percentage"),
                    "volume": t.get("quoteVolume"),
                })
            return success_response(
                data=summary[:50],
                count=len(summary),
                source="CCXT",
                exchange=exchange_id,
            )
        except Exception as e:
            return error_response(str(e))

    def calculate_kimchi_premium(self, coin: str = "BTC") -> Dict[str, Any]:
        """
        Calculate kimchi premium — Korean vs global price spread.

        Pulls KRW price from Upbit, USDT price from Binance,
        and KRW/USDT rate from Upbit's USDT/KRW pair.
        """
        try:
            upbit = _get_exchange("upbit")
            binance = _get_exchange("binance")
            if not upbit or not binance:
                return error_response("Upbit or Binance not available", code="NOT_INITIALIZED")

            krw_ticker = upbit.fetch_ticker(f"{coin}/KRW")
            usdt_ticker = binance.fetch_ticker(f"{coin}/USDT")

            # Get USDT/KRW rate
            try:
                usdt_krw = upbit.fetch_ticker("USDT/KRW")
                usdt_krw_rate = usdt_krw["last"]
            except Exception:
                usdt_krw_rate = float(os.environ.get("USDT_KRW_FALLBACK_RATE", "1450"))
                logger.warning(f"Using fallback USDT/KRW rate: {usdt_krw_rate}")

            krw_price = krw_ticker["last"]
            usdt_price = usdt_ticker["last"]
            global_krw_price = usdt_price * usdt_krw_rate

            premium_pct = ((krw_price - global_krw_price) / global_krw_price) * 100

            return success_response(
                data=None,
                source="CCXT",
                coin=coin,
                upbit_krw=krw_price,
                binance_usdt=usdt_price,
                usdt_krw_rate=usdt_krw_rate,
                binance_krw_equivalent=round(global_krw_price),
                premium_krw=round(krw_price - global_krw_price),
                premium_pct=round(premium_pct, 2),
                interpretation=(
                    "프리미엄 (한국이 비쌈)" if premium_pct > 0.5
                    else "디스카운트 (한국이 쌈)" if premium_pct < -0.5
                    else "균형"
                ),
            )
        except Exception as e:
            return error_response(str(e))

    def exchange_compare(self, symbol_base: str = "BTC") -> Dict[str, Any]:
        """Compare prices across Korean exchanges."""
        results = []
        pairs = {
            "upbit": f"{symbol_base}/KRW",
            "bithumb": f"{symbol_base}/KRW",
            "korbit": f"{symbol_base}/KRW",
            "binance": f"{symbol_base}/USDT",
        }

        for ex_id, symbol in pairs.items():
            ticker = self.get_ticker(ex_id, symbol)
            if ticker.get("success"):
                results.append({
                    "exchange": ex_id,
                    "symbol": symbol,
                    "price": ticker["last"],
                    "volume": ticker.get("volume"),
                })

        if not results:
            return error_response("No exchange data available", code="NOT_FOUND")

        return success_response(
            data=results,
            source="CCXT",
            base=symbol_base,
        )
