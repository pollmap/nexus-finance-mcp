"""
Advanced Portfolio Construction MCP Server — BL, HRP, RMT, Johansen (6 tools).

Black-Litterman, Hierarchical Risk Parity, Random Matrix Theory,
Johansen cointegration, information theory, method comparison.

Tools:
- portadv_rmt_clean: Random Matrix Theory 상관행렬 정제
- portadv_black_litterman: Black-Litterman 포트폴리오
- portadv_hrp: Hierarchical Risk Parity
- portadv_johansen: Johansen 다변량 공적분 검정
- portadv_info_theory: KL divergence + transfer entropy + mutual info
- portadv_compare: 포트폴리오 방법론 비교
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
from mcp_servers.adapters.portfolio_advanced_adapter import PortfolioAdvancedAdapter

logger = logging.getLogger(__name__)


class PortfolioAdvancedServer(BaseMCPServer):
    @property
    def name(self) -> str:
        return "portfolio_advanced"

    def __init__(self, **kwargs):
        self._adapter = PortfolioAdvancedAdapter()
        super().__init__(**kwargs)

    def _register_tools(self):
        adapter = self._adapter

        @self.mcp.tool()
        def portadv_rmt_clean(series_list: list, names: list) -> dict:
            """
            Random Matrix Theory 상관행렬 정제 — Marchenko-Pastur 노이즈 제거.

            경험적 상관행렬의 고유값 중 MP 분포 경계 이하(=노이즈)를 식별하고
            평균값으로 대체하여 정제된 상관행렬을 반환합니다.
            포트폴리오 최적화의 OOS 성능을 크게 개선합니다.

            Args:
                series_list: 자산별 가격 시계열 [series1, series2, ...] (각 [{date, value}])
                names: 자산명 리스트

            Returns:
                n_signal/noise eigenvalues, cleaned_correlation, mp_bounds, eigenvalue_summary
            """
            return adapter.rmt_clean(series_list, names)

        @self.mcp.tool()
        def portadv_black_litterman(
            series_list: list,
            names: list,
            market_caps: list = None,
            views: list = None,
            tau: float = 0.05,
            risk_free_rate: float = 0.03,
            risk_aversion: float = 2.5,
        ) -> dict:
            """
            Black-Litterman 포트폴리오 — 시장균형 + 투자자 뷰 결합.

            CAPM 균형 수익률에 투자자의 전망(views)을 베이지안으로 결합합니다.
            뷰 없이 호출하면 시장 균형 포트폴리오를 반환합니다.
            views 형식: [{"asset": "삼성전자", "return": 0.15, "confidence": 0.8}]

            Args:
                series_list: 자산별 가격 시계열 [series1, ...] (각 [{date, value}])
                names: 자산명 리스트
                market_caps: 시가총액 리스트 (None=동일가중 사전분포)
                views: 투자자 전망 [{"asset", "return", "confidence"}]
                tau: 불확실성 스케일링 (기본 0.05)
                risk_free_rate: 무위험수익률 (기본 3%)
                risk_aversion: 위험회피계수 (기본 2.5)

            Returns:
                optimal_weights, equilibrium_returns, posterior_returns, sharpe_ratio
            """
            return adapter.black_litterman(series_list, names, market_caps, views, tau, risk_free_rate, risk_aversion)

        @self.mcp.tool()
        def portadv_hrp(series_list: list, names: list) -> dict:
            """
            Hierarchical Risk Parity — 공분산 역행렬 없는 트리 기반 배분.

            López de Prado의 HRP: 상관 거리로 계층적 클러스터링 →
            유사 대각화 → 재귀적 이분할로 가중치 배분.
            Markowitz보다 OOS 안정성이 높고 특이 행렬 문제를 피합니다.

            Args:
                series_list: 자산별 가격 시계열 [series1, ...] (각 [{date, value}])
                names: 자산명 리스트

            Returns:
                weights, diversification_ratio, effective_n, cluster_order
            """
            return adapter.hrp(series_list, names)

        @self.mcp.tool()
        def portadv_johansen(
            series_list: list,
            names: list,
            det_order: int = 0,
            k_ar_diff: int = 1,
        ) -> dict:
            """
            Johansen 다변량 공적분 검정 — N개 자산의 장기 균형 관계.

            Engle-Granger(2변수)의 다변량 확장. Trace/Max-eigenvalue 통계량으로
            공적분 관계 수(rank)를 판정합니다. 3개 이상 자산의 stat arb에 필수.

            Args:
                series_list: 자산별 가격 시계열 [series1, ...] (각 [{date, value}])
                names: 자산명 리스트
                det_order: 결정적 항 (-1=없음, 0=상수, 1=추세)
                k_ar_diff: VAR 차분 차수 (기본 1)

            Returns:
                rank_trace, rank_max_eigenvalue, test_results, cointegrating_vectors
            """
            return adapter.johansen(series_list, names, det_order, k_ar_diff)

        @self.mcp.tool()
        def portadv_info_theory(
            series_a: list,
            series_b: list,
            n_bins: int = 20,
            te_lags: int = 1,
        ) -> dict:
            """
            정보이론 분석 — KL divergence + Transfer Entropy + Mutual Information.

            KL divergence: 두 수익률 분포의 차이 (레짐 전환 탐지).
            Transfer entropy: 방향성 인과 정보 흐름 (A→B vs B→A).
            Mutual information: 비선형 의존성 (상관계수의 일반화).

            Args:
                series_a: 자산 A 가격 [{date, value}]
                series_b: 자산 B 가격 [{date, value}]
                n_bins: 히스토그램 빈 수 (기본 20)
                te_lags: Transfer entropy 시차 (기본 1)

            Returns:
                kl_divergence, jensen_shannon, mutual_information, transfer_entropy, causal_direction
            """
            return adapter.info_theory(series_a, series_b, n_bins, te_lags)

        @self.mcp.tool()
        def portadv_compare(
            series_list: list,
            names: list,
            risk_free_rate: float = 0.03,
        ) -> dict:
            """
            포트폴리오 방법론 비교 — Equal Weight vs Min Variance vs HRP vs Inverse Vol.

            4가지 포트폴리오 구축 방법의 가중치, 기대수익, 변동성, Sharpe를 나란히 비교.
            최적 방법과 근거를 제시합니다.

            Args:
                series_list: 자산별 가격 시계열 [series1, ...] (각 [{date, value}])
                names: 자산명 리스트
                risk_free_rate: 무위험수익률 (기본 3%)

            Returns:
                methods (각각 weights/return/volatility/sharpe), best_method
            """
            return adapter.compare(series_list, names, risk_free_rate)


server = PortfolioAdvancedServer()
mcp = server.mcp

if __name__ == "__main__":
    mcp.run()
