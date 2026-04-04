"""
Stochastic Volatility & Optimal Execution MCP Server (6 tools).

Heston model, Merton jump-diffusion, variance risk premium,
Almgren-Chriss optimal execution, VWAP planning, market impact.

Tools:
- stochvol_heston: Heston 확률적 변동성 모델
- stochvol_jump_diffusion: Merton 점프확산 모델
- stochvol_var_premium: 분산 리스크 프리미엄
- stochvol_exec_optimal: Almgren-Chriss 최적실행
- stochvol_exec_vwap: VWAP 실행 계획
- stochvol_impact: 시장 충격 추정 (Kyle's λ)
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.core.base_server import BaseMCPServer
from mcp_servers.adapters.stochvol_adapter import StochVolAdapter

logger = logging.getLogger(__name__)


class StochVolServer(BaseMCPServer):
    @property
    def name(self) -> str:
        return "stochvol"

    def __init__(self, **kwargs):
        self._adapter = StochVolAdapter()
        super().__init__(**kwargs)

    def _register_tools(self):
        adapter = self._adapter

        @self.mcp.tool()
        def stochvol_heston(series: list) -> dict:
            """
            Heston 확률적 변동성 모델 — 변동성이 확률적으로 변하는 모델 캘리브레이션.

            dS/S = μdt + √v·dW₁, dv = κ(θ-v)dt + ξ√v·dW₂, corr(W₁,W₂)=ρ.
            κ: 변동성 평균회귀 속도, θ: 장기 분산, ξ: vol-of-vol, ρ: 레버리지 효과.
            ρ < 0이면 하락 시 변동성 증가 (레버리지 효과). Feller 조건 검증 포함.

            Args:
                series: 가격 시계열 [{date, value}] (100개 이상)

            Returns:
                kappa, theta, xi, rho, v0, feller_condition, implied_vol
            """
            return adapter.heston(series)

        @self.mcp.tool()
        def stochvol_jump_diffusion(series: list) -> dict:
            """
            Merton 점프확산 모델 — 갑작스런 가격 점프를 포함한 수익률 모델.

            dS/S = (μ-λk)dt + σdW + JdN. J~N(μ_J, σ_J²), N~Poisson(λ).
            Black-Scholes의 확장: 연속적 확산 + 이산적 점프.
            팻테일과 급등/급락을 설명합니다.

            Args:
                series: 가격 시계열 [{date, value}] (100개 이상)

            Returns:
                diffusion_sigma, jump_intensity, jump_mean/std, n_jumps_detected, recent_jumps
            """
            return adapter.jump_diffusion(series)

        @self.mcp.tool()
        def stochvol_var_premium(
            series: list,
            vix_series: list = None,
            window: int = 20,
        ) -> dict:
            """
            분산 리스크 프리미엄 — 내재변동성 vs 실현변동성 스프레드.

            VRP = IV - RV. 양수면 옵션이 비싸다 → 변동성 매도 수익.
            역사적으로 주식 옵션은 평균 2-4%p의 양(+)의 VRP를 보입니다.
            VIX 시리즈 제공 시 실제 내재변동성 사용, 아니면 프록시 추정.

            Args:
                series: 기초자산 가격 [{date, value}] (60개 이상)
                vix_series: VIX/내재변동성 시리즈 [{date, value}] (선택)
                window: 실현변동성 롤링 윈도우 (기본 20일)

            Returns:
                current_vrp, mean_vrp, pct_positive, implied_vol, realized_vol
            """
            return adapter.var_premium(series, vix_series, window)

        @self.mcp.tool()
        def stochvol_exec_optimal(
            total_shares: float,
            horizon_days: int = 5,
            daily_volume: float = 1e6,
            volatility: float = 0.02,
            permanent_impact: float = 1e-7,
            temporary_impact: float = 1e-6,
            risk_aversion: float = 1e-6,
        ) -> dict:
            """
            Almgren-Chriss 최적실행 — 비용+리스크 최소화 실행 궤적.

            min E[cost] + λ·Var[cost]. 해: x_k = X·sinh(κ(T-t_k))/sinh(κT).
            위험회피 높으면 앞쪽에 집중(front-load), 낮으면 균등(TWAP에 근접).
            TWAP 대비 예상 절감액도 계산합니다.

            Args:
                total_shares: 총 실행 수량
                horizon_days: 실행 기간 (일, 기본 5)
                daily_volume: 일평균 거래량 (기본 1,000,000)
                volatility: 일간 변동성 (기본 2%)
                permanent_impact: 영구적 가격 충격 계수
                temporary_impact: 일시적 가격 충격 계수
                risk_aversion: 위험회피 파라미터

            Returns:
                trajectory (일별 수량/비율), expected_cost, savings_vs_twap
            """
            return adapter.exec_optimal(total_shares, horizon_days, daily_volume, volatility,
                                        permanent_impact, temporary_impact, risk_aversion)

        @self.mcp.tool()
        def stochvol_exec_vwap(
            series: list,
            total_shares: float,
            n_buckets: int = 10,
        ) -> dict:
            """
            VWAP 실행 계획 — 과거 거래량 프로파일 기반 시간별 배분.

            과거 거래량 패턴을 분석하여 시간대별 주문 비율을 결정합니다.
            거래량 데이터가 없으면 TWAP(균등 배분)으로 폴백합니다.

            Args:
                series: OHLCV 데이터 [{date, value, volume}]
                total_shares: 총 실행 수량
                n_buckets: 시간 버킷 수 (기본 10)

            Returns:
                plan (버킷별 수량/비율), method, max/min_bucket_pct
            """
            return adapter.exec_vwap(series, total_shares, n_buckets)

        @self.mcp.tool()
        def stochvol_impact(series: list, window: int = 20) -> dict:
            """
            시장 충격 추정 — Kyle's λ + Roll 스프레드 + Amihud.

            Kyle's lambda: 주문흐름 1단위당 가격 변화 (OLS 추정).
            Roll spread: 가격변동 자기공분산으로 유효 스프레드 추정.
            Amihud: |수익률|/거래대금 (유동성 역수).

            Args:
                series: OHLCV 데이터 [{date, value, volume(선택)}] (30개 이상)
                window: 분석 윈도우 (기본 20)

            Returns:
                kyle_lambda, roll_spread, amihud_illiquidity, r_squared
            """
            return adapter.market_impact(series, window)


server = StochVolServer()
mcp = server.mcp

if __name__ == "__main__":
    mcp.run()
