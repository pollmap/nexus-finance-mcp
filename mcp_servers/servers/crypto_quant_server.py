"""
Crypto Derivatives & Funding Rate MCP Server (6 tools).

Funding rates, basis term structure, arbitrage scanning,
open interest, liquidation levels, carry backtest.

Tools:
- cquant_funding_rate: 영구선물 펀딩레이트
- cquant_basis_term: 선물 베이시스 기간구조
- cquant_funding_arb: 펀딩레이트 차익 스캐너
- cquant_open_interest: 미결제약정 + 레버리지
- cquant_liquidation_levels: 청산 캐스케이드 레벨
- cquant_carry_backtest: 캐리 전략 백테스트
"""
import logging
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.core.base_server import BaseMCPServer
from mcp_servers.adapters.crypto_quant_adapter import CryptoQuantAdapter

logger = logging.getLogger(__name__)


class CryptoQuantServer(BaseMCPServer):
    @property
    def name(self) -> str:
        return "crypto_quant"

    def __init__(self, **kwargs):
        self._adapter = CryptoQuantAdapter()
        super().__init__(**kwargs)

    def _register_tools(self):
        adapter = self._adapter

        @self.mcp.tool()
        def cquant_funding_rate(
            symbol: str = "BTC/USDT:USDT", exchange: str = "binance",
        ) -> dict:
            """
            영구선물 펀딩레이트 — 현재 + 히스토리 + 연환산.

            8시간마다 롱↔숏 간 지불하는 펀딩레이트를 조회합니다.
            양수: 롱이 숏에 지불 → 숏 포지션이 수익.
            연환산 = rate × 3 × 365. 20%+ 이면 높은 캐리 기회.

            Args:
                symbol: 선물 심볼 (기본 "BTC/USDT:USDT")
                exchange: 거래소 (기본 "binance")

            Returns:
                current_rate, annualized_rate, avg_30, history
            """
            return adapter.funding_rate(symbol, exchange)

        @self.mcp.tool()
        def cquant_basis_term(
            base: str = "BTC", exchange: str = "binance",
        ) -> dict:
            """
            선물 베이시스 기간구조 — 현물 vs 선물 가격 차이.

            Contango (선물 > 현물): 정상, 캐리 수익 가능.
            Backwardation (선물 < 현물): 시장 스트레스 신호.
            분기물 선물이 있으면 기간구조(term structure)도 표시.

            Args:
                base: 기초자산 (기본 "BTC")
                exchange: 거래소 (기본 "binance")

            Returns:
                spot_price, perpetual_price, basis_pct, structure, quarterly_futures
            """
            return adapter.basis_term(base, exchange)

        @self.mcp.tool()
        def cquant_funding_arb(
            symbols: list = None,
            exchange: str = "binance",
            min_annualized: float = 0.05,
        ) -> dict:
            """
            펀딩레이트 차익 스캐너 — 상위 캐리 기회 탐색.

            주요 10개 종목의 펀딩레이트를 스캔하여 연환산 수익 순으로 정렬합니다.
            전략: rate > 0이면 long spot + short perp (delta-neutral carry).

            Args:
                symbols: 스캔할 심볼 리스트 (None=BTC/ETH/SOL 등 10개)
                exchange: 거래소 (기본 "binance")
                min_annualized: 최소 연환산 수익률 (기본 5%)

            Returns:
                opportunities (심볼별 funding/annualized/direction), n_opportunities
            """
            return adapter.funding_arb(symbols, exchange, min_annualized)

        @self.mcp.tool()
        def cquant_open_interest(
            symbol: str = "BTC/USDT:USDT", exchange: str = "binance",
        ) -> dict:
            """
            미결제약정 + 레버리지 메트릭 — 시장 포지셔닝 분석.

            OI(미결제약정): 열린 선물 계약의 총 규모.
            OI/거래량 비율이 높으면 레버리지 축적 → 변동성 폭발 위험.

            Args:
                symbol: 선물 심볼 (기본 "BTC/USDT:USDT")
                exchange: 거래소 (기본 "binance")

            Returns:
                open_interest_usd, volume_24h, oi_volume_ratio
            """
            return adapter.open_interest(symbol, exchange)

        @self.mcp.tool()
        def cquant_liquidation_levels(
            symbol: str = "BTC/USDT:USDT",
            exchange: str = "binance",
            leverage_levels: list = None,
        ) -> dict:
            """
            청산 캐스케이드 레벨 추정 — 레버리지별 청산 가격.

            각 레버리지(2x~100x)에서 롱/숏 포지션이 청산되는 가격대를 계산합니다.
            5% 하락 → 20x 롱 청산, 10% 하락 → 10x 롱 청산.
            이 가격대에서 청산 → 추가 하락 → 연쇄 청산 (cascade).

            Args:
                symbol: 선물 심볼 (기본 "BTC/USDT:USDT")
                exchange: 거래소 (기본 "binance")
                leverage_levels: 레버리지 레벨 리스트 (기본 [2,3,5,10,20,25,50,100])

            Returns:
                levels (leverage별 long/short 청산 가격), high_risk_zone
            """
            return adapter.liquidation_levels(symbol, exchange, leverage_levels)

        @self.mcp.tool()
        def cquant_carry_backtest(
            series: list,
            funding_rates: list,
            initial_capital: float = 10000,
        ) -> dict:
            """
            펀딩레이트 캐리 전략 백테스트 — long spot + short perp.

            Delta-neutral 포지션에서 펀딩레이트 수익만 수집하는 전략.
            ScienceDirect 2025: BTC/ETH 펀딩 캐리 최대 115.9% 반기 수익.

            Args:
                series: 기초자산 가격 [{date, value}]
                funding_rates: 펀딩레이트 시리즈 [{date, value}] (소수점, 예: 0.0001)
                initial_capital: 초기 자본 (기본 10,000)

            Returns:
                total_return, annualized, sharpe, max_drawdown, win_rate
            """
            return adapter.carry_backtest(series, funding_rates, initial_capital)


server = CryptoQuantServer()
mcp = server.mcp

if __name__ == "__main__":
    mcp.run()
