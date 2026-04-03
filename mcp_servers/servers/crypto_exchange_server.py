"""
Crypto Exchange MCP Server — Korean + Global exchanges via ccxt.

Tools (8):
- crypto_ticker: 실시간 시세
- crypto_orderbook: 호가창
- crypto_ohlcv: 캔들 데이터
- crypto_all_tickers: 전체 시세
- crypto_kimchi_premium: 김치프리미엄 ★
- crypto_exchange_compare: 거래소간 비교
- crypto_volume_ranking: 거래량 순위
- crypto_spread: 매수/매도 스프레드
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = CryptoExchangeServer()
    server.mcp.run(transport="stdio")
