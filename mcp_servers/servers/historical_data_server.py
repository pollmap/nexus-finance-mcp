"""
Historical Data MCP Server — 150+ Years of Financial Data.

Tools (6):
- historical_shiller: Shiller S&P 500 + CAPE (1871~현재)
- historical_french_factors: Fama-French 팩터 데이터 (1926~현재)
- historical_nber_cycles: NBER 경기 순환 (1854~현재)
- historical_fred_century: FRED 초장기 시계열 (100년+)
- historical_gold_oil: 금/유가 장기 가격
- historical_crisis_comparison: 위기 간 S&P 500 비교 분석
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP
from mcp_servers.adapters.historical_data_adapter import HistoricalDataAdapter

logger = logging.getLogger(__name__)


class HistoricalDataServer:
    def __init__(self):
        self._adapter = HistoricalDataAdapter()
        self.mcp = FastMCP("historical-data")
        self._register_tools()
        logger.info("Historical Data MCP Server initialized")

    def _register_tools(self):

        @self.mcp.tool()
        def historical_shiller(start_year: int = 1871, end_year: int = 0) -> dict:
            """Shiller S&P 500 장기 데이터 (1871~현재). CAPE ratio, CPI, 배당수익률, 장기금리 포함. / Shiller S&P 500 long-term data with CAPE, CPI, dividend yield, long rate."""
            ey = end_year if end_year > 0 else None
            return self._adapter.get_shiller_data(start_year, ey)

        @self.mcp.tool()
        def historical_french_factors(dataset: str = "5_factors", frequency: str = "monthly") -> dict:
            """Fama-French 팩터 데이터 (1926~현재). dataset: 5_factors/3_factors/momentum. frequency: monthly/annual. / Fama-French academic factor data — the gold standard for asset pricing research."""
            return self._adapter.get_french_factors(dataset, frequency)

        @self.mcp.tool()
        def historical_nber_cycles() -> dict:
            """NBER 미국 경기 순환 날짜 (1854~현재, 34사이클). 현재 국면, 평균 확장/수축 기간 포함. / NBER US Business Cycle dates with contraction/expansion durations."""
            return self._adapter.get_nber_cycles()

        @self.mcp.tool()
        def historical_fred_century(series_id: str = "CPIAUCSL", start: str = "1900-01-01") -> dict:
            """FRED 초장기 시계열. 인기 시리즈: CPIAUCSL(1913), TB3MS(1934), UNRATE(1948), GDP(1947), M2SL(1959), DGS10(1962), SP500(1927). / FRED maximum-history series for century-scale analysis."""
            return self._adapter.get_fred_century(series_id, start)

        @self.mcp.tool()
        def historical_gold_oil(asset: str = "gold", period: str = "max") -> dict:
            """금/유가 초장기 가격. asset: gold(1968+), oil(1986+), brent(1987+). FRED 우선, yfinance 폴백. / Long-term gold & oil prices from FRED with yfinance fallback."""
            return self._adapter.get_gold_oil_long(asset, period)

        @self.mcp.tool()
        def historical_crisis_comparison(events: str = "1929-10-01,2008-09-15,2020-03-11", window_months: int = 24) -> dict:
            """위기 간 S&P 500 비교 — 이벤트 전후 정규화(100 기준). events: 쉼표 구분 날짜. / Cross-century crisis comparison — S&P 500 normalized to 100 at each event date."""
            event_list = [e.strip() for e in events.split(",") if e.strip()]
            return self._adapter.get_cross_century_comparison(event_list, window_months)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = HistoricalDataServer()
    server.mcp.run(transport="stdio")
