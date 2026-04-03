"""Timeseries MCP Server — Time Series Analysis Engine (6 tools)."""
import logging
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.timeseries_adapter import TimeseriesAdapter

logger = logging.getLogger(__name__)


class TimeseriesServer:
    def __init__(self):
        self._a = TimeseriesAdapter()
        self.mcp = FastMCP("timeseries")
        self._register()
        logger.info("Timeseries MCP Server initialized (6 tools)")

    def _register(self):
        @self.mcp.tool()
        def ts_decompose(series: list[dict], freq: Optional[int] = None, model: str = "additive") -> dict:
            """시계열 분해 (trend + seasonal + residual). freq: 12=월별, 52=주별, 365=일별. 자동 감지 가능."""
            return self._a.decompose(series, freq=freq, model=model)

        @self.mcp.tool()
        def ts_stationarity(series: list[dict]) -> dict:
            """정상성 검정 (ADF + KPSS). is_stationary, p-value, 추천 조치 반환."""
            return self._a.stationarity_test(series)

        @self.mcp.tool()
        def ts_forecast(series: list[dict], horizon: int = 6, model: str = "auto") -> dict:
            """ARIMA 예측. 자동 차수 선택 (AIC 기준). 80%/95% 신뢰구간 포함."""
            return self._a.forecast(series, horizon=horizon, model=model)

        @self.mcp.tool()
        def ts_seasonality(series: list[dict], freq: Optional[int] = None) -> dict:
            """계절성 패턴 추출. 월별/주별 평균, 강도, 피크/저점 기간 반환."""
            return self._a.seasonality(series, freq=freq)

        @self.mcp.tool()
        def ts_changepoint(series: list[dict], n_changepoints: int = 3) -> dict:
            """변화점 탐지 (CUSUM + rolling mean). 구조적 변화 지점과 변화 크기 반환."""
            return self._a.changepoint_detection(series, n_changepoints=n_changepoints)

        @self.mcp.tool()
        def ts_cross_correlation(series_a: list[dict], series_b: list[dict], max_lag: int = 12) -> dict:
            """교차상관 분석. 두 시계열 간 선행-후행 관계와 최대 상관 래그 반환."""
            return self._a.cross_correlation(series_a, series_b, max_lag=max_lag)
