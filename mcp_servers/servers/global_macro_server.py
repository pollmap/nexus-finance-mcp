"""
Global Macro MCP Server — OECD/IMF/BIS/World Bank/FRED.

Tools (10):
- macro_oecd: OECD 지표 조회
- macro_imf: IMF 지표 조회
- macro_bis: BIS 지표 조회 (부동산가격, 신용/GDP)
- macro_worldbank: World Bank 지표 조회
- macro_datasets: 사용 가능한 데이터셋 목록
- macro_search_indicators: 지표 키워드 검색
- macro_country_compare: 국가간 경제지표 비교
- macro_fred: FRED 미국 경제데이터 조회
- macro_fred_search: FRED 시리즈 검색
- macro_korea_snapshot: 한국 국제비교 스냅샷
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP
from mcp_servers.adapters.global_macro_adapter import GlobalMacroAdapter

logger = logging.getLogger(__name__)


class GlobalMacroServer:
    def __init__(self):
        self._adapter = GlobalMacroAdapter()
        self.mcp = FastMCP("global-macro")
        self._register_tools()
        logger.info("Global Macro MCP Server initialized")

    def _register_tools(self):

        @self.mcp.tool()
        def macro_oecd(dataset: str = "MEI", country: str = "KOR", subject: str = "", recent: int = 20) -> dict:
            """OECD 지표 조회. dataset: MEI(경제지표), QNA(GDP), KEI(핵심지표). country: KOR, USA, JPN 등."""
            return self._adapter.get_oecd_indicator(dataset, subject, country, recent)

        @self.mcp.tool()
        def macro_imf(database: str = "IFS", country: str = "KR", indicator: str = "", recent: int = 20) -> dict:
            """IMF 지표 조회. database: IFS(국제금융통계), WEO(세계경제전망), DOT(무역방향)."""
            return self._adapter.get_imf_indicator(database, indicator, country, recent)

        @self.mcp.tool()
        def macro_bis(dataset: str = "WS_SPP", country: str = "KR", recent: int = 20) -> dict:
            """BIS 지표 조회. dataset: WS_SPP(부동산가격), WS_CREDIT_GAP(신용/GDP), WS_EER(실효환율)."""
            return self._adapter.get_bis_indicator(dataset, country, recent)

        @self.mcp.tool()
        def macro_worldbank(indicator: str = "NY.GDP.MKTP.CD", country: str = "KOR", recent: int = 20) -> dict:
            """World Bank 지표. indicator: NY.GDP.MKTP.CD(GDP), FP.CPI.TOTL.ZG(물가), SL.UEM.TOTL.ZS(실업률)."""
            return self._adapter.get_worldbank_indicator(indicator, country, recent)

        @self.mcp.tool()
        def macro_datasets(source: str = "OECD") -> dict:
            """사용 가능한 데이터셋 목록. source: OECD, IMF, BIS."""
            return self._adapter.get_available_datasets(source)

        @self.mcp.tool()
        def macro_search_indicators(keyword: str, source: str = "worldbank", limit: int = 30) -> dict:
            """거시경제 지표 키워드 검색. 1500+ World Bank 지표 중 검색. 예: 'inflation', 'GDP', 'unemployment', 'trade'."""
            return self._adapter.search_indicators(keyword, source, limit)

        @self.mcp.tool()
        def macro_country_compare(indicator: str = "NY.GDP.MKTP.CD",
                                   countries: str = "KOR,USA,JPN,CHN,DEU",
                                   recent: int = 10) -> dict:
            """국가간 경제지표 비교 (World Bank). 예: GDP, 물가, 실업률 등 국제비교.

            Args:
                indicator: World Bank 지표 ID (예: NY.GDP.MKTP.CD=GDP, FP.CPI.TOTL.ZG=물가)
                countries: 국가코드 쉼표구분 (ISO3: KOR,USA,JPN,CHN,DEU)
                recent: 최근 N개 데이터
            """
            return self._adapter.country_compare(indicator, countries, recent)

        @self.mcp.tool()
        def macro_fred(series_id: str = "FEDFUNDS", limit: int = 30) -> dict:
            """FRED (미국 연준 경제데이터) 시계열 조회. 미국 금리, 물가, 고용, 환율 등.

            주요 시리즈: FEDFUNDS(기준금리), DGS10(10년국채), CPIAUCSL(CPI),
            UNRATE(실업률), GDP, DEXKOUS(원달러환율), SP500, VIXCLS(VIX), T10Y2Y(장단기스프레드)

            Args:
                series_id: FRED 시리즈 ID
                limit: 최근 N개 관측치
            """
            return self._adapter.get_fred_series(series_id, limit)

        @self.mcp.tool()
        def macro_fred_search(keyword: str, limit: int = 20) -> dict:
            """FRED 시리즈 키워드 검색. 800,000+ 경제 시계열 중 검색.

            Args:
                keyword: 검색어 (예: 'interest rate', 'inflation', 'korea')
                limit: 최대 결과 수
            """
            return self._adapter.search_fred(keyword, limit)

        @self.mcp.tool()
        def macro_korea_snapshot() -> dict:
            """한국 경제 국제비교 스냅샷 — GDP, 물가, 실업률을 World Bank에서 조회."""
            indicators = {
                "GDP (current US$)": "NY.GDP.MKTP.CD",
                "GDP per capita (US$)": "NY.GDP.PCAP.CD",
                "GDP growth (%)": "NY.GDP.MKTP.KD.ZG",
                "Inflation CPI (%)": "FP.CPI.TOTL.ZG",
                "Unemployment (%)": "SL.UEM.TOTL.ZS",
                "Govt Debt/GDP (%)": "GC.DOD.TOTL.GD.ZS",
                "Trade Balance (% GDP)": "NE.RSB.GNFS.ZS",
                "FDI Inflows (% GDP)": "BX.KLT.DINV.WD.GD.ZS",
                "Current Account (% GDP)": "BN.CAB.XOKA.GD.ZS",
                "Population": "SP.POP.TOTL",
                "Life Expectancy": "SP.DYN.LE00.IN",
                "Poverty Rate (%)": "SI.POV.DDAY",
                "Gini Index": "SI.POV.GINI",
                "Exports (% GDP)": "NE.EXP.GNFS.ZS",
                "Industry (% GDP)": "NV.IND.TOTL.ZS",
                "R&D Expenditure (% GDP)": "GB.XPD.RSDV.GD.ZS",
                "CO2 Emissions (metric tons per capita)": "EN.ATM.CO2E.PC",
                "Internet Users (%)": "IT.NET.USER.ZS",
                "Gross Savings (% GDP)": "NY.GNS.ICTR.ZS",
                "Household Consumption (% GDP)": "NE.CON.PRVT.ZS",
            }
            results = {}
            for name, code in indicators.items():
                data = self._adapter.get_worldbank_indicator(code, "KOR", 5)
                if data.get("success"):
                    results[name] = data.get("data", [])
                else:
                    results[name] = {"error": data.get("message")}
            return {"success": True, "country": "Korea", "indicators": results}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = GlobalMacroServer()
    server.mcp.run(transport="stdio")
