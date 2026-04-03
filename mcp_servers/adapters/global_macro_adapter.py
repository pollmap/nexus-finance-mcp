"""
Global Macro Adapter — OECD, IMF, BIS, World Bank.

Uses sdmx1 for OECD/IMF/BIS (SDMX protocol) and wbgapi for World Bank.
All completely free, no API keys needed.
"""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class GlobalMacroAdapter:
    """International macro data via sdmx1 + wbgapi."""

    def __init__(self):
        self._sdmx = None
        self._wb = None
        try:
            import sdmx
            self._sdmx = sdmx
            logger.info("sdmx1 loaded")
        except ImportError:
            logger.warning("sdmx1 not installed. Run: pip install sdmx1")
        try:
            import wbgapi as wb
            self._wb = wb
            logger.info("wbgapi loaded")
        except ImportError:
            logger.warning("wbgapi not installed. Run: pip install wbgapi")

    def get_oecd_indicator(
        self, dataset: str, subject: str = "", country: str = "KOR", recent: int = 20
    ) -> Dict[str, Any]:
        """
        Get OECD indicator data.

        Common datasets:
        - MEI: Main Economic Indicators (CLI, CPI, unemployment)
        - QNA: Quarterly National Accounts (GDP)
        - KEI: Key Economic Indicators
        """
        if not self._sdmx:
            return {"error": True, "message": "sdmx1 not installed"}
        try:
            # Try OECD_JSON (stats.oecd.org) first, then new OECD API
            for client_id in ["OECD_JSON", "OECD"]:
                try:
                    client = self._sdmx.Client(client_id, timeout=30)
                    key = {"LOCATION": country}
                    if subject:
                        key["SUBJECT"] = subject
                    data = client.data(dataset, key=key)
                    df = data.to_pandas()
                    if hasattr(df, 'reset_index'):
                        df = df.reset_index()
                    records = df.tail(recent).to_dict("records") if len(df) > 0 else []
                    return {
                        "success": True,
                        "source": f"OECD ({client_id})",
                        "dataset": dataset,
                        "country": country,
                        "count": len(records),
                        "data": records[-recent:],
                    }
                except Exception:
                    continue
            return {
                "error": True,
                "message": f"OECD dataset '{dataset}' not found. OECD API가 2024년 이후 대폭 변경되었습니다. "
                           f"한국 경제지표는 ecos_* 도구를, 미국은 FRED 시리즈를 사용하세요. "
                           f"macro_datasets('OECD')로 사용 가능한 데이터셋을 확인하세요.",
            }
        except Exception as e:
            return {"error": True, "message": f"OECD query failed: {e}"}

    def get_imf_indicator(
        self, database: str = "IFS", indicator: str = "", country: str = "KR", recent: int = 20
    ) -> Dict[str, Any]:
        """
        Get IMF indicator data.

        Common databases:
        - IFS: International Financial Statistics
        - WEO: World Economic Outlook
        - DOT: Direction of Trade Statistics
        """
        if not self._sdmx:
            return {"error": True, "message": "sdmx1 not installed"}
        try:
            imf = self._sdmx.Client("IMF", timeout=30)
            key = {"REF_AREA": country}
            if indicator:
                key["INDICATOR"] = indicator

            data = imf.data(database, key=key)
            df = data.to_pandas()

            if hasattr(df, 'reset_index'):
                df = df.reset_index()

            records = df.tail(recent).to_dict("records") if len(df) > 0 else []

            return {
                "success": True,
                "source": "IMF",
                "database": database,
                "country": country,
                "count": len(records),
                "data": records[-recent:],
            }
        except Exception as e:
            return {
                "error": True,
                "message": f"IMF query failed: {e}. IMF SDMX API가 변경되었을 수 있습니다. "
                           f"한국 데이터는 ecos_* 도구를, 미국은 FRED를, 국제비교는 macro_worldbank를 사용하세요.",
            }

    def get_bis_indicator(
        self, dataset: str = "WS_SPP", country: str = "KR", recent: int = 20
    ) -> Dict[str, Any]:
        """
        Get BIS indicator data.

        Common datasets:
        - WS_SPP: Property prices
        - WS_CREDIT_GAP: Credit-to-GDP gap
        - WS_EER: Effective exchange rates
        - WS_CBS_PUB: Cross-border banking statistics
        """
        if not self._sdmx:
            return {"error": True, "message": "sdmx1 not installed"}
        try:
            bis = self._sdmx.Client("BIS", timeout=30)
            key = {"REF_AREA": country}

            data = bis.data(dataset, key=key)
            df = data.to_pandas()

            if hasattr(df, 'reset_index'):
                df = df.reset_index()

            records = df.tail(recent).to_dict("records") if len(df) > 0 else []

            return {
                "success": True,
                "source": "BIS",
                "dataset": dataset,
                "country": country,
                "count": len(records),
                "data": records[-recent:],
            }
        except Exception as e:
            return {"error": True, "message": f"BIS query failed: {e}"}

    def get_worldbank_indicator(
        self, indicator: str = "NY.GDP.MKTP.CD", country: str = "KOR", recent: int = 20
    ) -> Dict[str, Any]:
        """
        Get World Bank indicator data.

        Common indicators:
        - NY.GDP.MKTP.CD: GDP (current US$)
        - FP.CPI.TOTL.ZG: Inflation (CPI %)
        - SL.UEM.TOTL.ZS: Unemployment (%)
        - BX.KLT.DINV.CD.WD: FDI net inflows
        """
        if not self._wb:
            return {"error": True, "message": "wbgapi not installed"}
        try:
            data = self._wb.data.DataFrame(indicator, economy=country, mrnev=recent)
            records = []
            if hasattr(data, 'to_dict'):
                for col in data.columns:
                    val = data[col].iloc[0] if len(data) > 0 else None
                    records.append({"year": str(col), "value": val})

            return {
                "success": True,
                "source": "World Bank",
                "indicator": indicator,
                "country": country,
                "count": len(records),
                "data": records,
            }
        except Exception as e:
            return {"error": True, "message": f"World Bank query failed: {e}"}

    def get_available_datasets(self, source: str = "OECD") -> Dict[str, Any]:
        """List available datasets from a source."""
        if not self._sdmx:
            return {"error": True, "message": "sdmx1 not installed"}
        try:
            client = self._sdmx.Client(source, timeout=30)
            flows = client.dataflow()
            datasets = []
            for key, flow in list(flows.dataflow.items())[:50]:
                datasets.append({"id": str(key), "name": str(flow.name)})
            return {"success": True, "source": source, "count": len(datasets), "datasets": datasets}
        except Exception as e:
            return {"error": True, "message": str(e)}
