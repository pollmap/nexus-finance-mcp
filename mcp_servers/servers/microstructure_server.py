"""
Market Microstructure MCP Server — Order Flow & Liquidity Analysis (6 tools).

Kyle's lambda, Lee-Ready classification, Roll spread, Amihud illiquidity,
order book imbalance, VPIN toxicity.

Tools:
- micro_kyle_lambda: Kyle's λ 가격충격 계수
- micro_lee_ready: Lee-Ready 거래 분류 (매수/매도 주도)
- micro_roll_spread: Roll 유효 스프레드
- micro_amihud: Amihud 비유동성 비율
- micro_orderbook_imbalance: 호가창 불균형
- micro_toxicity: VPIN 독성흐름 확률
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.core.base_server import BaseMCPServer
from mcp_servers.adapters.microstructure_adapter import MicrostructureAdapter

logger = logging.getLogger(__name__)


class MicrostructureServer(BaseMCPServer):
    @property
    def name(self) -> str:
        return "microstructure"

    def __init__(self, **kwargs):
        self._adapter = MicrostructureAdapter()
        super().__init__(**kwargs)

    def _register_tools(self):
        adapter = self._adapter

        @self.mcp.tool()
        def micro_kyle_lambda(series: list, window: int = 20) -> dict:
            """
            Kyle's λ 가격충격 계수 — 주문흐름 1단위당 가격 변화.

            OLS 회귀: Δprice = c + λ·signed_volume + ε.
            λ > 0: 매수 주문 → 가격 상승 (정상). λ가 클수록 비유동적.
            거래량 데이터 없으면 수익률 크기를 프록시로 사용합니다.

            Args:
                series: OHLCV 데이터 [{date, value, volume(선택)}] (30개 이상)
                window: 롤링 윈도우 (기본 20)

            Returns:
                kyle_lambda, r_squared, rolling_lambdas
            """
            return adapter.kyle_lambda(series, window)

        @self.mcp.tool()
        def micro_lee_ready(trades: list) -> dict:
            """
            Lee-Ready 거래 분류 — 매수/매도 주도 거래 식별.

            Quote rule: 거래가 > mid → 매수 주도. Tick test: 상승틱 → 매수.
            호가 데이터(bid/ask) 있으면 quote rule 우선, 없으면 tick test만 사용.
            Order Flow Imbalance (OFI) 계산: 매수 vs 매도 비율.

            Args:
                trades: [{date, value/price, bid(선택), ask(선택)}]

            Returns:
                n_buys, n_sells, buy_pct, order_flow_imbalance
            """
            return adapter.lee_ready(trades)

        @self.mcp.tool()
        def micro_roll_spread(series: list) -> dict:
            """
            Roll 유효 스프레드 — 가격변동 자기공분산으로 스프레드 추정.

            spread = 2·√(−Cov(Δp_t, Δp_{t-1})). 호가 데이터 없이도 추정 가능.
            음의 자기공분산 = bid-ask bounce = 유효 스프레드 존재.
            양의 자기공분산이면 추정 불가 (모멘텀 효과).

            Args:
                series: 가격 시계열 [{date, value}] (30개 이상)

            Returns:
                roll_spread, roll_spread_pct, serial_covariance, rolling_spreads
            """
            return adapter.roll_spread(series)

        @self.mcp.tool()
        def micro_amihud(series: list) -> dict:
            """
            Amihud 비유동성 비율 — |수익률|/거래대금 일별 평균.

            값이 클수록 비유동적. 소형주 > 대형주. 위기 시 급등.
            거래량 데이터 포함 시 정확한 비율, 없으면 플레이스홀더 사용.

            Args:
                series: OHLCV 데이터 [{date, value, volume(선택)}] (30개 이상)

            Returns:
                amihud_ratio, amihud_percentile, rolling_amihud
            """
            return adapter.amihud(series)

        @self.mcp.tool()
        def micro_orderbook_imbalance(orderbook: dict) -> dict:
            """
            호가창 불균형 — 매수/매도 물량비 (1/5/10/20 호가).

            OBI = (bid_vol − ask_vol)/(bid_vol + ask_vol).
            양수 = 매수 압력, 음수 = 매도 압력. 단기 방향성 예측에 유용.
            스프레드(bps), 가중 중간가도 함께 계산합니다.

            Args:
                orderbook: {"bids": [[price, vol], ...], "asks": [[price, vol], ...]}

            Returns:
                imbalances (depth 1/5/10/20), spread_bps, weighted_mid
            """
            return adapter.orderbook_imbalance(orderbook)

        @self.mcp.tool()
        def micro_toxicity(
            series: list,
            bucket_volume: float = None,
            n_buckets: int = 50,
        ) -> dict:
            """
            VPIN 독성흐름 — 정보 비대칭 거래 확률 (Easley, López de Prado & O'Hara).

            볼륨 동기화 샘플링 후 BVC(Bulk Volume Classification)로 매수/매도 분류.
            VPIN > 0.5 → 정보 거래자 활동 증가 → Flash crash 위험.
            VPIN > 0.6 → 마켓메이커 스프레드 확대 가능성 높음.

            Args:
                series: OHLCV [{date, value, volume(선택)}] (50개 이상)
                bucket_volume: 버킷당 거래량 (None=자동)
                n_buckets: 평균 버킷 수 (기본 50)

            Returns:
                vpin, current_vpin, vpin_percentile, recent_vpin
            """
            return adapter.toxicity(series, bucket_volume, n_buckets)


server = MicrostructureServer()
mcp = server.mcp

if __name__ == "__main__":
    mcp.run()
