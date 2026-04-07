"""
Crypto Exchange MCP Server — Korean + Global exchanges via ccxt.

Tools (14):
- crypto_ticker: 실시간 시세
- crypto_orderbook: 호가창
- crypto_ohlcv: 캔들 데이터
- crypto_all_tickers: 전체 시세
- crypto_kimchi_premium: 김치프리미엄 ★
- crypto_exchange_compare: 거래소간 비교
- crypto_volume_ranking: 거래량 순위
- crypto_spread: 매수/매도 스프레드
- crypto_list_exchanges: 지원 거래소 목록
- crypto_list_symbols: 거래쌍 목록
- crypto_recent_trades: 최근 체결 내역
- crypto_funding_rate: 선물 펀딩 레이트
- crypto_ticker_24h: 24시간 상세 통계
- crypto_market_structure: 시장 구조 정보
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP
from mcp_servers.adapters.ccxt_adapter import CCXTAdapter

logger = logging.getLogger(__name__)


class CryptoExchangeServer:
    def __init__(self):
        self._adapter = CCXTAdapter()
        self.mcp = FastMCP("crypto-exchange")
        self._register_tools()
        logger.info("Crypto Exchange MCP Server initialized")

    def _register_tools(self):

        @self.mcp.tool()
        def crypto_ticker(exchange: str = "upbit", symbol: str = "BTC/KRW") -> dict:
            """
            크립토 실시간 시세 조회.

            Args:
                exchange: 거래소 (upbit, bithumb, binance, korbit, coinone)
                symbol: 거래쌍 (BTC/KRW, ETH/USDT 등)

            Returns:
                현재가, bid/ask, 24h변동률, 거래량
            """
            return self._adapter.get_ticker(exchange, symbol)

        @self.mcp.tool()
        def crypto_orderbook(exchange: str = "upbit", symbol: str = "BTC/KRW", limit: int = 10) -> dict:
            """
            호가창 (매수/매도 호가).

            Args:
                exchange: 거래소
                symbol: 거래쌍
                limit: 호가 단계 수 (기본 10)
            """
            return self._adapter.get_orderbook(exchange, symbol, limit)

        @self.mcp.tool()
        def crypto_ohlcv(
            exchange: str = "upbit",
            symbol: str = "BTC/KRW",
            timeframe: str = "1d",
            limit: int = 100,
        ) -> dict:
            """
            OHLCV 캔들 데이터.

            Args:
                exchange: 거래소
                symbol: 거래쌍
                timeframe: 봉 주기 (1m, 5m, 1h, 4h, 1d, 1w)
                limit: 캔들 수 (기본 100)
            """
            return self._adapter.get_ohlcv(exchange, symbol, timeframe, limit)

        @self.mcp.tool()
        def crypto_all_tickers(exchange: str = "upbit") -> dict:
            """
            거래소 전체 시세 (거래량 상위 50개).

            Args:
                exchange: 거래소
            """
            return self._adapter.get_all_tickers(exchange)

        @self.mcp.tool()
        def crypto_kimchi_premium(coin: str = "BTC") -> dict:
            """
            김치프리미엄 계산 — 업비트(KRW) vs 바이낸스(USDT) 가격차.

            Args:
                coin: 코인 (BTC, ETH, XRP 등)

            Returns:
                premium_pct, 업비트가격, 바이낸스가격, USDT환율
            """
            return self._adapter.calculate_kimchi_premium(coin)

        @self.mcp.tool()
        def crypto_exchange_compare(coin: str = "BTC") -> dict:
            """
            한국 거래소 + 바이낸스 가격 비교.

            Args:
                coin: 코인 (BTC, ETH 등)
            """
            return self._adapter.exchange_compare(coin)

        @self.mcp.tool()
        def crypto_volume_ranking(exchange: str = "upbit", limit: int = 20) -> dict:
            """
            거래량 상위 종목 순위.

            Args:
                exchange: 거래소
                limit: 상위 N개
            """
            result = self._adapter.get_all_tickers(exchange)
            if result.get("error"):
                return result
            return {
                "success": True,
                "exchange": exchange,
                "ranking": result.get("data", [])[:limit],
            }

        @self.mcp.tool()
        def crypto_spread(exchange: str = "upbit", symbol: str = "BTC/KRW") -> dict:
            """
            매수/매도 스프레드 계산.

            Args:
                exchange: 거래소
                symbol: 거래쌍
            """
            ticker = self._adapter.get_ticker(exchange, symbol)
            if ticker.get("error"):
                return ticker

            bid = ticker.get("bid") or 0
            ask = ticker.get("ask") or 0
            mid = (bid + ask) / 2 if bid and ask else 0
            spread_pct = ((ask - bid) / mid * 100) if mid > 0 else 0

            return {
                "success": True,
                "exchange": exchange,
                "symbol": symbol,
                "bid": bid,
                "ask": ask,
                "spread": ask - bid,
                "spread_pct": round(spread_pct, 4),
            }


        # === 검색/탐색 도구 추가 ===

        @self.mcp.tool()
        def crypto_list_exchanges() -> dict:
            """지원하는 크립토 거래소 목록 조회. CCXT 라이브러리가 지원하는 모든 거래소."""
            try:
                import ccxt
                exchanges = ccxt.exchanges
                # 주요 거래소 하이라이트
                korean = [e for e in exchanges if e in ("upbit", "bithumb", "korbit", "coinone")]
                global_major = [e for e in exchanges if e in ("binance", "bybit", "okx", "kraken", "coinbase", "bitfinex", "huobi", "kucoin", "gate")]
                return {
                    "success": True,
                    "total": len(exchanges),
                    "korean": korean,
                    "global_major": global_major,
                    "all_exchanges": exchanges,
                }
            except ImportError:
                return {"error": True, "message": "ccxt not installed"}

        @self.mcp.tool()
        def crypto_list_symbols(exchange: str = "binance", quote_currency: str = "") -> dict:
            """거래소에서 거래 가능한 심볼(거래쌍) 목록 조회.

            Args:
                exchange: 거래소명 (binance, upbit, bithumb 등)
                quote_currency: 필터 — 특정 기준통화만 (예: KRW, USDT, BTC). 빈 값이면 전체.
            """
            from mcp_servers.adapters.ccxt_adapter import _get_exchange
            ex = _get_exchange(exchange)
            if not ex:
                return {"error": True, "message": f"Exchange '{exchange}' not available"}
            try:
                ex.load_markets()
                symbols = list(ex.symbols)
                if quote_currency:
                    symbols = [s for s in symbols if s.endswith(f"/{quote_currency}")]
                return {
                    "success": True,
                    "exchange": exchange,
                    "count": len(symbols),
                    "data": sorted(symbols),
                }
            except Exception as e:
                return {"error": True, "message": str(e)}

        @self.mcp.tool()
        def crypto_recent_trades(exchange: str = "binance", symbol: str = "BTC/USDT", limit: int = 20) -> dict:
            """최근 체결 내역 조회.

            Args:
                exchange: 거래소명
                symbol: 거래쌍
                limit: 조회 건수 (최대 100)
            """
            from mcp_servers.adapters.ccxt_adapter import _get_exchange
            ex = _get_exchange(exchange)
            if not ex:
                return {"error": True, "message": f"Exchange '{exchange}' not available"}
            try:
                limit = min(limit, 100)
                trades = ex.fetch_trades(symbol, limit=limit)
                records = [{
                    "timestamp": t.get("datetime"),
                    "side": t.get("side"),
                    "price": t.get("price"),
                    "amount": t.get("amount"),
                    "cost": t.get("cost"),
                } for t in trades]
                return {
                    "success": True,
                    "exchange": exchange,
                    "symbol": symbol,
                    "count": len(records),
                    "data": records,
                }
            except Exception as e:
                return {"error": True, "message": str(e)}

        # === 파생/통계 도구 추가 ===

        @self.mcp.tool()
        def crypto_funding_rate(exchange: str = "binance", symbol: str = "BTC/USDT:USDT") -> dict:
            """선물 펀딩 레이트 조회. 양수=롱 지배적, 음수=숏 지배적.

            Args:
                exchange: 선물 지원 거래소 (binance, bybit, okx)
                symbol: 선물 거래쌍 (BTC/USDT:USDT, ETH/USDT:USDT)
            """
            from mcp_servers.adapters.ccxt_adapter import _get_exchange
            ex = _get_exchange(exchange)
            if not ex:
                return {"error": True, "message": f"Exchange '{exchange}' not available"}
            try:
                if not hasattr(ex, 'fetch_funding_rate'):
                    return {"error": True, "message": f"{exchange} does not support funding rate"}
                rate = ex.fetch_funding_rate(symbol)
                return {
                    "success": True,
                    "exchange": exchange,
                    "symbol": symbol,
                    "funding_rate": rate.get("fundingRate"),
                    "funding_timestamp": rate.get("fundingDatetime"),
                    "next_funding_timestamp": rate.get("nextFundingDatetime"),
                    "data": rate,
                }
            except Exception as e:
                return {"error": True, "message": str(e)}

        @self.mcp.tool()
        def crypto_ticker_24h(exchange: str = "binance", symbol: str = "BTC/USDT") -> dict:
            """24시간 상세 거래 통계 (고가/저가/거래대금/변동률).

            Args:
                exchange: 거래소
                symbol: 거래쌍
            """
            from mcp_servers.adapters.ccxt_adapter import _get_exchange
            ex = _get_exchange(exchange)
            if not ex:
                return {"error": True, "message": f"Exchange '{exchange}' not available"}
            try:
                t = ex.fetch_ticker(symbol)
                return {
                    "success": True,
                    "exchange": exchange,
                    "symbol": symbol,
                    "last": t.get("last"),
                    "open": t.get("open"),
                    "high": t.get("high"),
                    "low": t.get("low"),
                    "close": t.get("close"),
                    "volume": t.get("baseVolume"),
                    "quote_volume": t.get("quoteVolume"),
                    "change": t.get("change"),
                    "change_pct": t.get("percentage"),
                    "vwap": t.get("vwap"),
                    "bid": t.get("bid"),
                    "ask": t.get("ask"),
                    "timestamp": t.get("datetime"),
                }
            except Exception as e:
                return {"error": True, "message": str(e)}

        @self.mcp.tool()
        def crypto_market_structure(exchange: str = "binance", symbol: str = "BTC/USDT") -> dict:
            """거래쌍 시장 구조 정보 (최소주문, 수수료, 가격단위 등).

            Args:
                exchange: 거래소
                symbol: 거래쌍
            """
            from mcp_servers.adapters.ccxt_adapter import _get_exchange
            ex = _get_exchange(exchange)
            if not ex:
                return {"error": True, "message": f"Exchange '{exchange}' not available"}
            try:
                ex.load_markets()
                market = ex.market(symbol)
                return {
                    "success": True,
                    "exchange": exchange,
                    "symbol": symbol,
                    "type": market.get("type"),
                    "spot": market.get("spot"),
                    "futures": market.get("future"),
                    "base": market.get("base"),
                    "quote": market.get("quote"),
                    "min_amount": market.get("limits", {}).get("amount", {}).get("min"),
                    "min_cost": market.get("limits", {}).get("cost", {}).get("min"),
                    "price_precision": market.get("precision", {}).get("price"),
                    "amount_precision": market.get("precision", {}).get("amount"),
                    "maker_fee": market.get("maker"),
                    "taker_fee": market.get("taker"),
                }
            except Exception as e:
                return {"error": True, "message": str(e)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = CryptoExchangeServer()
    server.mcp.run(transport="stdio")
