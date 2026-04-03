"""
Portfolio Optimizer MCP Server - 포트폴리오 최적화 엔진.

Markowitz 평균-분산, 리스크 패리티, 켈리 기준, 상관행렬, 스트레스 테스트, 리밸런싱.

Tools:
- portfolio_optimize: Markowitz 평균-분산 최적화
- portfolio_risk_parity: 리스크 패리티 포트폴리오
- portfolio_kelly: 켈리 기준 최적 베팅 비율
- portfolio_correlation_matrix: 상관행렬 + 분산비율
- portfolio_stress_test: 스트레스 테스트 (역사적/커스텀 시나리오)
- portfolio_rebalance: 리밸런싱 필요 여부 + 비용 분석

Run standalone: python -m mcp_servers.servers.portfolio_optimizer_server
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
from mcp_servers.adapters.portfolio_optimizer_adapter import PortfolioOptimizerAdapter

logger = logging.getLogger(__name__)


class PortfolioOptimizerServer(BaseMCPServer):
    """Portfolio Optimizer MCP Server wrapping PortfolioOptimizerAdapter."""

    @property
    def name(self) -> str:
        return "portfolio_optimizer"

    def __init__(self, **kwargs):
        self._adapter = PortfolioOptimizerAdapter()
        super().__init__(**kwargs)

    def _register_tools(self):
        adapter = self._adapter

        @self.mcp.tool()
        def portfolio_optimize(
            assets_returns: dict,
            method: str = "max_sharpe",
            risk_free_rate: float = 0.035,
            target_return: Optional[float] = None,
        ) -> dict:
            """
            Markowitz 평균-분산 포트폴리오 최적화. Mean-variance portfolio optimization.

            Args:
                assets_returns: 자산별 일일 수익률 {ticker: [{"date": str, "value": float}, ...]}
                method: 최적화 방법 — "max_sharpe" (최대 샤프), "min_variance" (최소 분산),
                    "target_return" (목표 수익률), "equal_weight" (동일 비중 벤치마크)
                risk_free_rate: 무위험이자율 (연, 기본 3.5%)
                target_return: method="target_return" 시 목표 수익률 (연)

            Returns:
                최적 비중, 기대 수익률/변동성, 샤프비율, 효율적 프론티어 10점
            """
            return adapter.optimize(assets_returns, method, risk_free_rate, target_return)

        @self.mcp.tool()
        def portfolio_risk_parity(assets_returns: dict) -> dict:
            """
            리스크 패리티 포트폴리오. Risk Parity — equal risk contribution per asset.

            Args:
                assets_returns: 자산별 일일 수익률 {ticker: [{"date": str, "value": float}, ...]}

            Returns:
                비중, 위험 기여도 (균등해야 함), 총 위험
            """
            return adapter.risk_parity(assets_returns)

        @self.mcp.tool()
        def portfolio_kelly(
            win_rate: float,
            avg_win: float,
            avg_loss: float,
            fraction: float = 0.5,
        ) -> dict:
            """
            켈리 기준 최적 베팅 비율. Kelly Criterion for optimal position sizing.

            Args:
                win_rate: 승률 (0~1, 예: 0.55 = 55%)
                avg_win: 평균 수익률 (예: 0.08 = 8%)
                avg_loss: 평균 손실률 (양수, 예: 0.05 = 5%)
                fraction: 켈리 비율 (0.5 = 하프 켈리 권장, 안전 운용)

            Returns:
                풀 켈리 %, 추천 %, 기대 성장률
            """
            return adapter.kelly(win_rate, avg_win, avg_loss, fraction)

        @self.mcp.tool()
        def portfolio_correlation_matrix(
            assets_returns: dict,
            window: int = 60,
        ) -> dict:
            """
            상관행렬 분석 + 분산비율. Correlation matrix with regime detection.

            Args:
                assets_returns: 자산별 일일 수익률 {ticker: [{"date": str, "value": float}, ...]}
                window: 롤링 윈도우 크기 (기본 60 거래일)

            Returns:
                현재/롤링 상관행렬, 분산비율, 최대 상관 자산 쌍, 레짐 변화
            """
            return adapter.correlation_matrix(assets_returns, window)

        @self.mcp.tool()
        def portfolio_stress_test(
            portfolio_weights: dict,
            scenario: str = "2008_crisis",
            assets_returns: Optional[dict] = None,
            custom_shocks: Optional[dict] = None,
        ) -> dict:
            """
            스트레스 테스트. Stress test with historical/custom scenarios.

            Args:
                portfolio_weights: 현재 포트폴리오 비중 {ticker: weight}
                scenario: 시나리오 — "2008_crisis", "2020_covid", "2022_rate_hike", "custom"
                assets_returns: (선택) 히스토리컬 VaR 계산용 데이터
                custom_shocks: scenario="custom" 시 충격 {ticker: shock_pct} (예: {"KOSPI": -0.30})

            Returns:
                포트폴리오 충격(%), 자산별 영향, 최악 자산, 최적 헤지
            """
            return adapter.stress_test(portfolio_weights, assets_returns, scenario, custom_shocks)

        @self.mcp.tool()
        def portfolio_rebalance(
            current_weights: dict,
            target_weights: dict,
            threshold: float = 0.05,
            transaction_cost: float = 0.003,
        ) -> dict:
            """
            리밸런싱 필요 여부 + 비용 분석. Rebalancing check with cost-benefit analysis.

            Args:
                current_weights: 현재 비중 {ticker: weight}
                target_weights: 목표 비중 {ticker: weight}
                threshold: 드리프트 허용 한도 (기본 5%p)
                transaction_cost: 편도 거래비용 (기본 0.3%)

            Returns:
                리밸런싱 필요 여부, 드리프트 자산, 거래 목록, 비용, 순이익
            """
            return adapter.rebalance_check(current_weights, target_weights, threshold, transaction_cost)


# ── Standalone entry point ─────────────────────────────────────────────
if __name__ == "__main__":
    server = PortfolioOptimizerServer()
    server.mcp.run()
