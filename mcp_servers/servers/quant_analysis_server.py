"""
Quant Analysis MCP Server — 8 tools for statistical time-series analysis.
"""
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP
from mcp_servers.adapters.quant_analysis_adapter import QuantAnalysisAdapter

logger = logging.getLogger(__name__)


class QuantAnalysisServer:
    def __init__(self):
        self._qa = QuantAnalysisAdapter()
        self.mcp = FastMCP("quant-analysis")
        self._register_tools()
        logger.info("Quant Analysis MCP Server initialized — 8 tools")

    def _register_tools(self):

        @self.mcp.tool()
        def quant_correlation(
            series_a: list, series_b: list, method: str = "pearson"
        ) -> dict:
            """두 시계열 간 상관관계 분석 (Correlation between two time series).

            series_a, series_b: [{"date": "YYYY-MM-DD", "value": float}, ...]
            method: pearson | spearman | kendall
            예시: KOSPI vs S&P500, 금리 vs 부동산 가격"""
            return self._qa.correlation(series_a, series_b, method)

        @self.mcp.tool()
        def quant_lagged_correlation(
            series_a: list, series_b: list, max_lag: int = 12
        ) -> dict:
            """시차 상관분석 — A가 B를 몇 기간 선행하는지 분석 (Lagged correlation).

            series_a, series_b: [{"date": "YYYY-MM-DD", "value": float}, ...]
            max_lag: 탐색할 최대 시차 (기본 12)
            예시: "금리 변경이 6개월 후 부동산에 가장 큰 영향" 발견"""
            return self._qa.lagged_correlation(series_a, series_b, max_lag)

        @self.mcp.tool()
        def quant_regression(
            dependent: list,
            independents: list,
            independent_names: list = None,
            method: str = "OLS",
        ) -> dict:
            """다변량 회귀분석 — Y = b0 + b1*X1 + b2*X2 + ... (Multiple regression).

            dependent: Y 종속변수 [{"date": "YYYY-MM-DD", "value": float}, ...]
            independents: X 독립변수들의 리스트 [[{date,value},...], [{date,value},...]]
            independent_names: 변수명 리스트 ["금리", "환율", ...]
            예시: KOSPI = f(금리, 환율, 유가) 회귀분석"""
            return self._qa.regression(dependent, independents, independent_names, method)

        @self.mcp.tool()
        def quant_granger_causality(
            series_a: list, series_b: list, max_lag: int = 4
        ) -> dict:
            """그레인저 인과관계 검정 — A가 B를 예측하는 데 도움이 되는지 (Granger causality).

            series_a, series_b: [{"date": "YYYY-MM-DD", "value": float}, ...]
            max_lag: 검정할 최대 시차 (기본 4)
            예시: "금리가 주가를 Granger-cause 하는가?" 검정"""
            return self._qa.granger_causality(series_a, series_b, max_lag)

        @self.mcp.tool()
        def quant_cointegration(series_a: list, series_b: list) -> dict:
            """공적분 검정 — 두 시계열 간 장기 균형관계 존재 여부 (Engle-Granger cointegration).

            series_a, series_b: [{"date": "YYYY-MM-DD", "value": float}, ...]
            페어트레이딩, 거시경제 균형 분석에 활용.
            예시: 삼성전자 vs SK하이닉스 공적분 → 스프레드 전략"""
            return self._qa.cointegration(series_a, series_b)

        @self.mcp.tool()
        def quant_var_decomposition(
            series_dict: dict, lags: int = 4, periods: int = 10
        ) -> dict:
            """VAR 분산분해 — 변수 간 상호 영향력 분해 (Variance decomposition).

            series_dict: {"변수명": [{"date": "YYYY-MM-DD", "value": float}, ...], ...}
            lags: VAR 시차 (기본 4), periods: 분해 기간 (기본 10)
            예시: {"금리": [...], "환율": [...], "주가": [...]} → 각 변수의 변동을 설명하는 비율"""
            return self._qa.var_decomposition(series_dict, lags, periods)

        @self.mcp.tool()
        def quant_event_study(
            price_series: list,
            event_dates: list,
            window_before: int = 20,
            window_after: int = 60,
        ) -> dict:
            """이벤트 스터디 — 특정 이벤트 전후 비정상 수익률 분석 (Event study / CAR).

            price_series: 일별 가격 [{"date": "YYYY-MM-DD", "value": float}, ...]
            event_dates: 이벤트 날짜 리스트 ["2024-03-15", "2024-06-20"]
            예시: 금리 인상일 전후 KOSPI 반응 분석"""
            return self._qa.event_study(price_series, event_dates, window_before, window_after)

        @self.mcp.tool()
        def quant_regime_detection(
            series: list, n_regimes: int = 2, rolling_window: int = 20
        ) -> dict:
            """시장 레짐 탐지 — 변동성 기반 국면 분류 (Market regime detection).

            series: 가격 시계열 [{"date": "YYYY-MM-DD", "value": float}, ...]
            n_regimes: 레짐 수 (기본 2: 저변동성/고변동성)
            rolling_window: 롤링 윈도우 크기 (기본 20)
            예시: KOSPI 저변동성/고변동성 국면 자동 분류"""
            return self._qa.regime_detection(series, n_regimes, rolling_window)


# Standalone entry point
if __name__ == "__main__":
    server = QuantAnalysisServer()
    server.mcp.run()
