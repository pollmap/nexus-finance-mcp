"""
Statistical Arbitrage MCP Server — Pairs Trading & Mean-Reversion (6 tools).

OU process fitting, distance-method pair selection, spread z-score,
copula dependence, mean-reversion half-life, z-score backtest.

Tools:
- stat_arb_ou_fit: OU 프로세스 피팅 (반감기, 회귀속도)
- stat_arb_pairs_distance: Distance method 페어 선별
- stat_arb_spread_zscore: 스프레드 z-score + 매매 시그널
- stat_arb_copula: 코풀라 꼬리 의존성 분석
- stat_arb_halflife: 평균 회귀 반감기 추정
- stat_arb_backtest: z-score 평균회귀 전략 백테스트
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.core.base_server import BaseMCPServer
from mcp_servers.adapters.stat_arb_adapter import StatArbAdapter

logger = logging.getLogger(__name__)


class StatArbServer(BaseMCPServer):
    """Statistical Arbitrage MCP Server wrapping StatArbAdapter."""

    @property
    def name(self) -> str:
        return "stat_arb"

    def __init__(self, **kwargs):
        self._adapter = StatArbAdapter()
        super().__init__(**kwargs)

    def _register_tools(self):
        adapter = self._adapter

        @self.mcp.tool()
        def stat_arb_ou_fit(series: list) -> dict:
            """
            Ornstein-Uhlenbeck 프로세스 피팅 — 평균회귀 파라미터 추정.

            스프레드 시계열에 OU 모델 dX = θ(μ-X)dt + σdW를 MLE로 피팅합니다.
            회귀 속도(θ), 장기 평균(μ), 확산 계수(σ), 반감기를 추정하고
            현재 z-score 기반 진입 시그널을 제공합니다.

            Args:
                series: 스프레드/가격 시계열 [{date, value}] (30개 이상)

            Returns:
                theta, mu, sigma, half_life_days, current_z_score, mean_reverting
            """
            return adapter.ou_fit(series)

        @self.mcp.tool()
        def stat_arb_pairs_distance(
            universe: list,
            names: list,
            top_n: int = 5,
            formation_days: int = 252,
        ) -> dict:
            """
            Distance method 페어 선별 — Gatev-Goetzmann-Rouwenhorst 방법.

            N개 종목의 정규화 가격 경로 간 SSD(Sum of Squared Deviations)로
            가장 유사하게 움직이는 페어를 찾습니다.

            Args:
                universe: 종목별 시계열 리스트 [series1, series2, ...] (각 [{date, value}])
                names: 종목명 리스트 ["삼성전자", "SK하이닉스", ...]
                top_n: 상위 N개 페어 반환 (기본 5)
                formation_days: 형성기간 일수 (기본 252)

            Returns:
                top_pairs (SSD, 상관계수), total_pairs_evaluated
            """
            return adapter.pairs_distance(universe, names, top_n, formation_days)

        @self.mcp.tool()
        def stat_arb_spread_zscore(
            series_a: list,
            series_b: list,
            window: int = 60,
            entry_z: float = 2.0,
            exit_z: float = 0.5,
        ) -> dict:
            """
            스프레드 z-score 분석 — 헤지비율 + 매매 시그널 생성.

            OLS 헤지비율로 스프레드를 구성하고 롤링 z-score를 계산합니다.
            ADF 공적분 검정, 진입/청산 시그널, 최근 z-score 히스토리 제공.
            z < -entry → LONG_SPREAD, z > entry → SHORT_SPREAD, |z| < exit → EXIT.

            Args:
                series_a: 자산 A 가격 [{date, value}]
                series_b: 자산 B 가격 [{date, value}]
                window: 롤링 윈도우 (기본 60일)
                entry_z: 진입 z-score 임계값 (기본 2.0)
                exit_z: 청산 z-score 임계값 (기본 0.5)

            Returns:
                hedge_ratio, current_zscore, signal, is_cointegrated, recent_zscore
            """
            return adapter.spread_zscore(series_a, series_b, window, entry_z, exit_z)

        @self.mcp.tool()
        def stat_arb_copula(
            series_a: list,
            series_b: list,
            copula_type: str = "gaussian",
        ) -> dict:
            """
            코풀라 의존성 분석 — 꼬리 의존성 측정.

            두 자산 수익률의 결합 분포를 코풀라로 모델링합니다.
            선형 상관으로 포착 못하는 꼬리 의존성(tail dependence)을 측정:
            "두 자산이 동시에 폭락할 확률은?"

            Args:
                series_a: 자산 A 가격 [{date, value}]
                series_b: 자산 B 가격 [{date, value}]
                copula_type: "gaussian" (기본), "student_t", "clayton" (하방), "gumbel" (상방)

            Returns:
                parameter, lower_tail_dependence, upper_tail_dependence, kendall_tau
            """
            return adapter.copula_fit(series_a, series_b, copula_type)

        @self.mcp.tool()
        def stat_arb_halflife(series: list) -> dict:
            """
            평균 회귀 반감기 — AR(1) 기반 추정.

            스프레드가 편차의 절반만큼 회귀하는 데 걸리는 기간(일).
            half_life = -ln(2)/ln(b), b는 AR(1) 계수.
            < 5일: 초단기 | 5-20일: 스윙 | 20-60일: 포지션 | > 60일: 장기.

            Args:
                series: 스프레드 시계열 [{date, value}] (30개 이상)

            Returns:
                half_life_days, ar1_coeff, speed, recommendation
            """
            return adapter.halflife(series)

        @self.mcp.tool()
        def stat_arb_backtest(
            series_a: list,
            series_b: list,
            window: int = 60,
            entry_z: float = 2.0,
            exit_z: float = 0.5,
            stop_loss_z: float = 4.0,
            commission_pct: float = 0.001,
        ) -> dict:
            """
            z-score 평균회귀 전략 백테스트 — 페어 트레이딩 시뮬레이션.

            롤링 OLS 헤지비율 + z-score 기반 진입/청산으로 페어 트레이딩을 백테스트합니다.
            손절(stop_loss_z), 수수료, 보유기간 분석 포함.

            Args:
                series_a: 자산 A 가격 [{date, value}]
                series_b: 자산 B 가격 [{date, value}]
                window: 롤링 윈도우 (기본 60)
                entry_z: 진입 z-score (기본 2.0)
                exit_z: 청산 z-score (기본 0.5)
                stop_loss_z: 손절 z-score (기본 4.0)
                commission_pct: 수수료율 (기본 0.1%)

            Returns:
                total_pnl, n_trades, win_rate, sharpe_ratio, max_drawdown, recent_trades
            """
            return adapter.backtest(series_a, series_b, window, entry_z, exit_z, stop_loss_z, commission_pct)


# ------------------------------------------------------------------
server = StatArbServer()
mcp = server.mcp

if __name__ == "__main__":
    mcp.run()
