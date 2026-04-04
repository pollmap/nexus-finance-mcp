"""
Volatility Model MCP Server - 변동성 모델링 엔진.

GARCH/EGARCH, HMM 레짐 탐지, 변동성 표면, 앙상블 예측, VIX 기간구조 분석.

Tools:
- vol_garch: GARCH(p,q) 모델 피팅 + 예측
- vol_egarch: EGARCH 레버리지 효과 분석
- vol_surface: 다중 윈도우 실현변동성 + 변동성 콘
- vol_regime: HMM 변동성 레짐 탐지
- vol_forecast_ensemble: 4-모델 앙상블 변동성 예측
- vol_vix_term: VIX 기간구조 (콘탱고/백워데이션)

Run standalone: python -m mcp_servers.servers.volatility_model_server
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
from mcp_servers.adapters.volatility_model_adapter import VolatilityModelAdapter

logger = logging.getLogger(__name__)


class VolatilityModelServer(BaseMCPServer):
    """Volatility Model MCP Server wrapping VolatilityModelAdapter."""

    @property
    def name(self) -> str:
        return "volatility_model"

    def __init__(self, **kwargs):
        self._adapter = VolatilityModelAdapter()
        super().__init__(**kwargs)

    def _register_tools(self):
        adapter = self._adapter

        @self.mcp.tool()
        def vol_garch(
            returns_series: list,
            p: int = 1,
            q: int = 1,
            horizon: int = 5,
        ) -> dict:
            """
            GARCH(p,q) 변동성 모델 피팅 + 예측.

            Args:
                returns_series: 일별 수익률 또는 가격 데이터 (list[dict] with date, value). 가격 입력 시 자동으로 로그수익률 변환.
                p: GARCH 분산 지연 차수 (기본 1)
                q: ARCH 잔차제곱 지연 차수 (기본 1)
                horizon: 예측 기간 (일, 기본 5)

            Returns:
                모델 파라미터, 지속성(persistence), 조건부 변동성(최근 20일), 예측, AIC/BIC
            """
            return adapter.garch_fit(returns_series, p=p, q=q, horizon=horizon)

        @self.mcp.tool()
        def vol_egarch(
            returns_series: list,
            horizon: int = 5,
        ) -> dict:
            """
            EGARCH(1,1,1) 비대칭 변동성 모델. 레버리지 효과 포착 (하락이 상승보다 변동성 증가에 더 큰 영향).

            Args:
                returns_series: 일별 수익률 또는 가격 데이터 (list[dict] with date, value)
                horizon: 예측 기간 (일, 기본 5)

            Returns:
                파라미터, 레버리지 효과(gamma), 뉴스 충격 곡선(news impact curve), 예측
            """
            return adapter.egarch_fit(returns_series, horizon=horizon)

        @self.mcp.tool()
        def vol_surface(
            returns_series: list,
        ) -> dict:
            """
            변동성 표면: 다중 시간창(5~252일) 실현변동성 + 과거 백분위 + 변동성 콘.

            Args:
                returns_series: 일별 수익률 또는 가격 데이터 (list[dict] with date, value)

            Returns:
                윈도우별 현재 변동성 + 2년 백분위, 변동성 콘(min/25/50/75/max), 레짐 평가
            """
            return adapter.volatility_surface(returns_series)

        @self.mcp.tool()
        def vol_regime(
            returns_series: list,
            n_regimes: int = 2,
        ) -> dict:
            """
            HMM(Hidden Markov Model) 변동성 레짐 탐지. 시장의 숨겨진 상태(저변동/고변동) 식별.

            Args:
                returns_series: 일별 수익률 또는 가격 데이터 (list[dict] with date, value)
                n_regimes: 레짐 수 (기본 2: 저변동/고변동, 최대 4)

            Returns:
                레짐별 수익률/변동성, 전이행렬, 현재 레짐, 최근 60일 상태 시퀀스
            """
            return adapter.hmm_regime(returns_series, n_regimes=n_regimes)

        @self.mcp.tool()
        def vol_forecast_ensemble(
            returns_series: list,
            horizon: int = 5,
        ) -> dict:
            """
            4-모델 앙상블 변동성 예측: GARCH + EWMA(RiskMetrics) + 실현변동성 + 과거평균.
            역예측오차 가중 평균으로 결합.

            Args:
                returns_series: 일별 수익률 또는 가격 데이터 (list[dict] with date, value)
                horizon: 예측 기간 (일, 기본 5)

            Returns:
                앙상블 예측, 개별 모델 예측, 모델 가중치, 최적 모델
            """
            return adapter.vol_forecast_ensemble(returns_series, horizon=horizon)

        @self.mcp.tool()
        def vol_vix_term() -> dict:
            """
            VIX 기간구조 분석: VIX vs VIX3M 콘탱고/백워데이션.
            콘탱고(VIX < VIX3M): 시장 안정/자만. 백워데이션(VIX > VIX3M): 공포/위기.

            Returns:
                VIX 현재값, VIX3M, 비율, 기간구조(contango/backwardation), 30일 이력
            """
            return adapter.vix_term_structure()


# ── Standalone entry point ─────────────────────────────────────────────
if __name__ == "__main__":
    server = VolatilityModelServer()
    server.mcp.run()
