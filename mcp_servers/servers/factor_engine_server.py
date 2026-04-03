"""
Factor Engine MCP Server — 6 tools for multi-factor quantitative modeling.
"""
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP
from mcp_servers.adapters.factor_engine_adapter import FactorEngineAdapter

logger = logging.getLogger(__name__)


class FactorEngineServer:
    def __init__(self):
        self._fe = FactorEngineAdapter()
        self.mcp = FastMCP("factor-engine")
        self._register_tools()
        logger.info("Factor Engine MCP Server initialized — 6 tools")

    def _register_tools(self):

        @self.mcp.tool()
        def factor_score(
            stocks_data: dict,
            financial_data: dict = None,
            factors: list = None,
        ) -> dict:
            """멀티팩터 스코어 산출 (Multi-factor scoring for stock universe).

            stocks_data: {ticker: [{date, open, high, low, close, volume}, ...]}
            financial_data: {ticker: {per, pbr, roe, operating_margin, debt_ratio, market_cap}} (선택)
            factors: ["momentum","value","quality","low_vol","size","reversal"] (기본: 전체)
            각 종목의 팩터별 z-score + 종합점수 + 순위 산출.
            예시: 코스피200 유니버스 → 멀티팩터 랭킹"""
            return self._fe.factor_score(stocks_data, financial_data, factors)

        @self.mcp.tool()
        def factor_backtest(
            stocks_data: dict,
            factor_name: str,
            n_quantiles: int = 5,
            rebalance_freq: str = "monthly",
        ) -> dict:
            """팩터 롱-숏 백테스트 (Factor long-short backtest by quantile).

            stocks_data: {ticker: [{date, open, high, low, close, volume}, ...]}
            factor_name: momentum | reversal | low_vol
            n_quantiles: 분위 수 (기본 5 = 퀸타일)
            상위 분위 매수 / 하위 분위 매도 → 수익률, IC, t-stat, factor decay 산출.
            예시: 모멘텀 팩터 퀸타일 백테스트"""
            return self._fe.factor_backtest(stocks_data, factor_name, n_quantiles, rebalance_freq)

        @self.mcp.tool()
        def factor_correlation(
            stocks_data: dict,
            financial_data: dict = None,
        ) -> dict:
            """팩터 간 상관관계 분석 (Inter-factor correlation matrix).

            stocks_data: {ticker: [{date, open, high, low, close, volume}, ...]}
            financial_data: {ticker: {per, pbr, roe, ...}} (선택)
            전체 팩터 간 Spearman 상관행렬 + 중복 팩터 쌍 (|r|>0.7) 탐지.
            예시: 모멘텀과 리버설이 얼마나 상관있는지 확인"""
            return self._fe.factor_correlation(stocks_data, financial_data)

        @self.mcp.tool()
        def factor_exposure(
            portfolio_weights: dict,
            stocks_data: dict,
            financial_data: dict = None,
        ) -> dict:
            """포트폴리오 팩터 익스포저 분석 (Portfolio factor exposure analysis).

            portfolio_weights: {ticker: weight} (합계 ~1.0)
            stocks_data: {ticker: [{date, open, high, low, close, volume}, ...]}
            financial_data: {ticker: {per, pbr, roe, ...}} (선택)
            가중평균 팩터 노출도 + HHI 집중도 + 리스크 경고.
            예시: 내 포트폴리오가 모멘텀에 과도하게 노출됐는지 점검"""
            return self._fe.factor_exposure(portfolio_weights, stocks_data, financial_data)

        @self.mcp.tool()
        def factor_timing(
            stocks_data: dict,
            factor_name: str,
            lookback: int = 36,
        ) -> dict:
            """팩터 타이밍 / 레짐 분석 (Factor timing — is this factor working now?).

            stocks_data: {ticker: [{date, open, high, low, close, volume}, ...]}
            factor_name: momentum | reversal | low_vol
            lookback: 분석 기간 (월, 기본 36)
            팩터 수익률 시계열 + 최근 모멘텀 + 추천(STRONG/POSITIVE/FADING/AVOID).
            예시: 현재 시장에서 모멘텀 팩터가 유효한지 확인"""
            return self._fe.factor_timing(stocks_data, factor_name, lookback)

        @self.mcp.tool()
        def factor_custom(
            stocks_data: dict,
            custom_formula: dict,
        ) -> dict:
            """커스텀 팩터 생성 및 검증 (Build and validate a custom factor).

            stocks_data: {ticker: [{date, open, high, low, close, volume}, ...]}
            custom_formula: 팩터 정의 딕셔너리
              - {"type":"ratio", "numerator":"close_12m_ago", "denominator":"close"}
              - {"type":"rank", "field":"volume_20d_avg", "ascending":false}
              - {"type":"return", "period":60}
              - {"type":"volatility", "period":20, "invert":true}
              - {"type":"mean_reversion", "period":20}
            z-score + IC + t-stat + 유의성 검정 결과 반환.
            예시: 60일 수익률 팩터 → IC=0.05, t=2.3 → 유의미"""
            return self._fe.factor_custom(stocks_data, custom_formula)


# Standalone entry point
if __name__ == "__main__":
    server = FactorEngineServer()
    server.mcp.run()
