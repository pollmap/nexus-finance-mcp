"""
Advanced Math MCP Server - PhD-Level Mathematical Analysis (6 tools).

칼만 필터, 허스트 지수, 정보 엔트로피, 웨이블릿 분해, 프랙탈 차원, 몬테카를로 시뮬레이션.
금융 시계열의 숨겨진 구조를 수학적으로 분석하는 고급 도구 모음.

Tools:
- math_kalman: 칼만 필터 (노이즈 제거 + 추세 추출)
- math_hurst: 허스트 지수 (추세 지속성 vs 평균 회귀)
- math_entropy: 정보 엔트로피 (예측 가능성 측정)
- math_wavelets: 웨이블릿 분해 (다중 주파수 분석)
- math_fractal: 프랙탈 차원 (시장 복잡도 측정)
- math_monte_carlo: 몬테카를로 시뮬레이션 (미래 가격 확률 분포)

Run standalone: python -m mcp_servers.servers.advanced_math_server
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
from mcp_servers.adapters.advanced_math_adapter import AdvancedMathAdapter

logger = logging.getLogger(__name__)


class AdvancedMathServer(BaseMCPServer):
    """Advanced Math MCP Server wrapping AdvancedMathAdapter."""

    @property
    def name(self) -> str:
        return "advanced_math"

    def __init__(self, **kwargs):
        self._adapter = AdvancedMathAdapter()
        super().__init__(**kwargs)

    def _register_tools(self):
        adapter = self._adapter

        @self.mcp.tool()
        def math_kalman(
            series: list,
            process_noise: float = 1e-5,
            measurement_noise: float = 1e-2,
            benchmark: list = None,
        ) -> dict:
            """
            칼만 필터 — 노이즈 제거 + 동적 추세 추출. Kalman Filter for noise removal & trend extraction.

            가격 시계열에서 관측 노이즈를 제거하고 숨겨진 추세(velocity)를 추출합니다.
            State-space model: state=[price, velocity], measurement=observed price.
            RTS smoother로 후방 패스까지 수행하여 최적 추정치 제공.
            벤치마크 시리즈 제공 시 동적 베타(time-varying beta)도 계산합니다.

            Args:
                series: 가격 시계열 [{date, value}] (30개 이상)
                process_noise: 프로세스 노이즈 (기본 1e-5, 클수록 빠른 추적)
                measurement_noise: 관측 노이즈 (기본 1e-2, 클수록 강한 평활)
                benchmark: 벤치마크 시리즈 (동적 베타 계산용, 선택)

            Returns:
                filtered_signal, smoothed_signal, estimated_velocity, trend_direction, dynamic_beta
            """
            return adapter.kalman_filter(series, process_noise, measurement_noise, benchmark)

        @self.mcp.tool()
        def math_hurst(
            series: list,
            method: str = "rs",
        ) -> dict:
            """
            허스트 지수 — 추세 지속성 vs 평균 회귀 판별. Hurst Exponent for regime detection.

            H > 0.5: 추세 지속(모멘텀), H < 0.5: 평균 회귀, H ≈ 0.5: 랜덤워크.
            R/S(Rescaled Range) 분석 또는 DFA(Detrended Fluctuation Analysis)로 추정.
            트레이딩 전략 선택의 수학적 근거를 제공합니다.

            Args:
                series: 시계열 [{date, value}] (100개 이상)
                method: "rs" (R/S 분석, 기본) 또는 "dfa" (비추세 변동 분석)

            Returns:
                hurst_exponent, regime (trending/mean_reverting/random_walk), confidence, interpretation
            """
            return adapter.hurst_exponent(series, method)

        @self.mcp.tool()
        def math_entropy(
            series: list,
            n_bins: int = 20,
            apen_m: int = 2,
            apen_r_factor: float = 0.2,
        ) -> dict:
            """
            정보 엔트로피 — 시계열 예측 가능성 측정. Information Entropy for predictability scoring.

            Shannon 엔트로피: 수익률 분포의 불확실성 측정.
            Approximate Entropy (ApEn): 시계열 패턴의 규칙성 측정.
            Sample Entropy (SampEn): ApEn의 편향 보정 버전.
            세 지표의 앙상블로 종합 예측가능성 점수(0~1) 산출.

            Args:
                series: 시계열 [{date, value}] (100개 이상)
                n_bins: Shannon 엔트로피 히스토그램 빈 수 (기본 20)
                apen_m: 임베딩 차원 (기본 2)
                apen_r_factor: 허용 오차 = r_factor × std (기본 0.2)

            Returns:
                shannon_entropy, approx_entropy, sample_entropy, predictability_score, interpretation
            """
            return adapter.information_entropy(series, n_bins, apen_m, apen_r_factor)

        @self.mcp.tool()
        def math_wavelets(
            series: list,
            wavelet: str = "db4",
            levels: int = 5,
        ) -> dict:
            """
            웨이블릿 분해 — 다중 시간 스케일 분석. Wavelet Decomposition for multi-resolution analysis.

            이산 웨이블릿 변환(DWT)으로 시계열을 주파수 대역별로 분해합니다.
            Level 1: 고주파(2-4일 주기) = 노이즈/단기 변동
            Level 3-4: 중주파(8-32일 주기) = 단기 추세
            Approximation: 저주파 = 장기 추세
            각 대역의 에너지 비율로 지배적 시간 스케일을 식별합니다.

            Args:
                series: 가격 시계열 [{date, value}] (2^levels 이상)
                wavelet: 웨이블릿 함수 ("db4", "haar", "sym5", "coif3" 등)
                levels: 분해 깊이 (기본 5)

            Returns:
                levels (주파수 대역별 에너지/추세), dominant_scale, power_spectrum
            """
            return adapter.wavelet_decompose(series, wavelet, levels)

        @self.mcp.tool()
        def math_fractal(
            series: list,
            method: str = "box_counting",
        ) -> dict:
            """
            프랙탈 차원 — 시장 복잡도/효율성 측정. Fractal Dimension for market complexity analysis.

            박스 카운팅 방법으로 시계열의 프랙탈 차원을 측정합니다.
            D ≈ 1.0: 매끄러운 추세 (예측 가능, 비효율적 시장)
            D ≈ 1.5: 브라운 운동 (랜덤워크, 효율적 시장)
            D ≈ 2.0: 공간 충전 (매우 노이지, 혼돈적)
            효율적 시장 가설(EMH)의 수학적 검증 도구입니다.

            Args:
                series: 가격 시계열 [{date, value}] (200개 이상)
                method: "box_counting" (기본)

            Returns:
                fractal_dimension, market_efficiency, interpretation, r_squared
            """
            return adapter.fractal_dimension(series, method)

        @self.mcp.tool()
        def math_monte_carlo(
            series: list,
            n_simulations: int = 10000,
            horizon: int = 60,
            model: str = "gbm",
        ) -> dict:
            """
            몬테카를로 시뮬레이션 — 미래 가격 확률 분포 추정. Monte Carlo Simulation for forward projection.

            기하 브라운 운동(GBM) 모델로 n개 경로를 시뮬레이션합니다.
            dS = mu*S*dt + sigma*S*dW (리스크 중립이 아닌 실제 측도 사용)
            역사적 드리프트와 변동성을 기반으로 미래 가격 분포를 생성합니다.
            VaR, CVaR, 손실 확률 등 리스크 지표도 함께 산출합니다.

            Args:
                series: 가격 시계열 [{date, value}] (60개 이상)
                n_simulations: 시뮬레이션 경로 수 (기본 10000, 최대 50000)
                horizon: 전망 기간 (거래일 기준, 기본 60일)
                model: "gbm" (기하 브라운 운동)

            Returns:
                percentiles_by_step, final_distribution, mc_var_95, mc_cvar_95, probability_of_loss
            """
            return adapter.monte_carlo_simulation(series, n_simulations, horizon, model)


# ------------------------------------------------------------------
# Standalone entry point
# ------------------------------------------------------------------
server = AdvancedMathServer()
mcp = server.mcp

if __name__ == "__main__":
    mcp.run()
