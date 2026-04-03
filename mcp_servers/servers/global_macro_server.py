"""
Global Macro MCP Server — OECD/IMF/BIS/World Bank.

Tools (6):
- macro_oecd: OECD 지표 조회
- macro_imf: IMF 지표 조회
- macro_bis: BIS 지표 조회 (부동산가격, 신용/GDP)
- macro_worldbank: World Bank 지표 조회
- macro_datasets: 사용 가능한 데이터셋 목록
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
