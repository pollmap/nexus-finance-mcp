"""
Alpha Research Toolkit MCP Server (6 tools).

Strategy turnover, alpha decay, crowding detection, capacity estimation,
regime-conditional alpha, multi-alpha combination.

Tools:
- alpha_turnover: 전략 회전율 + 비용 분석
- alpha_decay: 알파 감쇠 곡선 (기간별 IC)
- alpha_crowding: 시그널 군집도 탐지
- alpha_capacity: 전략 용량 추정 (최대 AUM)
- alpha_regime_switch: 레짐별 알파 성과
- alpha_combine: 멀티 알파 결합
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
from mcp_servers.adapters.alpha_research_adapter import AlphaResearchAdapter

logger = logging.getLogger(__name__)


class AlphaResearchServer(BaseMCPServer):
    @property
    def name(self) -> str:
        return "alpha_research"

    def __init__(self, **kwargs):
        self._adapter = AlphaResearchAdapter()
        super().__init__(**kwargs)

    def _register_tools(self):
        adapter = self._adapter

        @self.mcp.tool()
        def alpha_turnover(weights_history: list, cost_per_trade: float = 0.001) -> dict:
            """
            전략 회전율 분석 — 포지션 변경 빈도 + 거래비용 영향.

            매 리밸런싱마다 포지션 변경량(turnover)과 누적 거래비용을 계산합니다.
            연간 비용 > 알파면 전략이 의미 없음 (break-even alpha 제공).

            Args:
                weights_history: [{date, weights: {asset: weight, ...}}, ...]
                cost_per_trade: 편도 거래비용 (기본 0.1%)

            Returns:
                avg_turnover, annualized_cost, break_even_alpha
            """
            return adapter.turnover(weights_history, cost_per_trade)

        @self.mcp.tool()
        def alpha_decay(signals: list, returns: list, horizons: list = None) -> dict:
            """
            알파 감쇠 곡선 — 시그널 예측력의 기간별 퇴화.

            1일, 2일, 5일, ... 60일 전방 수익률에 대한 IC(정보계수)를 측정합니다.
            IC 반감기: 시그널 예측력이 절반으로 줄어드는 기간.
            짧은 반감기 → 단기 전략, 긴 반감기 → 장기 전략에 적합.

            Args:
                signals: 시그널 [{date, value}]
                returns: 수익률 [{date, value}]
                horizons: 전방 기간 리스트 (기본 [1,2,5,10,20,40,60])

            Returns:
                ic_curve, half_life_days, peak_ic
            """
            return adapter.decay(signals, returns, horizons)

        @self.mcp.tool()
        def alpha_crowding(signal: list, factor_data: dict) -> dict:
            """
            시그널 군집도 탐지 — 공통 팩터 노출 측정.

            시그널을 알려진 팩터(모멘텀/가치/사이즈 등)로 회귀합니다.
            R² 높으면 → 시그널이 공통 팩터의 재포장 (낮은 알파 가능성).
            R² 낮으면 → 독자적 시그널 (알파 가능성 높음).

            Args:
                signal: 시그널 [{date, value}]
                factor_data: {"momentum": [{date, value}], "value": [{date, value}], ...}

            Returns:
                r_squared, crowding_level, factor_correlations, factor_betas
            """
            return adapter.crowding(signal, factor_data)

        @self.mcp.tool()
        def alpha_capacity(
            alpha: float,
            turnover: float,
            kyle_lambda: float = 1e-7,
            avg_daily_volume: float = 1e9,
        ) -> dict:
            """
            전략 용량 추정 — 알파 소멸 전 최대 운용 규모.

            Grinold-Kahn: capacity = alpha / (2·λ·turnover).
            ADV 기반: 시장 참여율별 최대 AUM.
            보수적 추정치는 두 방법 중 작은 값.

            Args:
                alpha: 연간 알파 (예: 0.05 = 5%)
                turnover: 연간 회전율 (예: 12 = 월간 리밸런스)
                kyle_lambda: 가격 충격 계수 (기본 1e-7)
                avg_daily_volume: 일평균 거래대금 (기본 10억)

            Returns:
                grinold_kahn_capacity, adv_based_capacities, conservative_estimate
            """
            return adapter.capacity(alpha, turnover, kyle_lambda, avg_daily_volume)

        @self.mcp.tool()
        def alpha_regime_switch(returns: list, signals: list, n_regimes: int = 2) -> dict:
            """
            레짐별 알파 — HMM/변동성 기반 레짐 분할 후 성과 비교.

            시장 레짐(고변동/저변동)별로 시그널의 IC와 Sharpe를 분리 측정합니다.
            "이 전략은 어떤 시장 환경에서 작동하는가?"에 답합니다.

            Args:
                returns: 자산 수익률 [{date, value}]
                signals: 시그널 [{date, value}]
                n_regimes: 레짐 수 (기본 2: 고/저 변동성)

            Returns:
                regimes (각 regime별 IC/Sharpe/n), best_regime
            """
            return adapter.regime_switch(returns, signals, n_regimes)

        @self.mcp.tool()
        def alpha_combine(alpha_series: dict, returns: list, method: str = "ic_weight") -> dict:
            """
            멀티 알파 결합 — 여러 시그널을 하나의 종합 시그널로.

            방법: "equal" (동일가중), "ic_weight" (IC 비례), "optimize" (IR 최대화).
            개별 시그널보다 결합 시그널의 IC가 높아야 의미 있음.
            시그널 간 상관이 낮을수록 결합 효과 큼.

            Args:
                alpha_series: {"alpha1": [{date, value}], "alpha2": [...], ...}
                returns: 전방 수익률 [{date, value}]
                method: "equal", "ic_weight" (기본), "optimize"

            Returns:
                combined_ic, weights, improvement_vs_best_single
            """
            return adapter.combine(alpha_series, returns, method)


server = AlphaResearchServer()
mcp = server.mcp

if __name__ == "__main__":
    mcp.run()
