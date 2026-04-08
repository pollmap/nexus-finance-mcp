"""
Global Macro Adapter — OECD, IMF, BIS, World Bank.

Uses sdmx1 for OECD/IMF/BIS (SDMX protocol) and wbgapi for World Bank.
OECD fallback: direct REST API call when sdmx1 fails (2024 API migration).
All completely free, no API keys needed.
"""
import logging
import sys
import os
import json
from typing import Any, Dict, List, Optional

import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp_servers.core.responses import error_response, success_response, sanitize_records

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
            return error_response("sdmx1 not installed")
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
                    records = sanitize_records(df.tail(recent)) if len(df) > 0 else []
                    return success_response(
                        records[-recent:],
                        count=len(records),
                        source=f"OECD ({client_id})",
                        dataset=dataset,
                        country=country,
                    )
                except Exception:
                    continue
                # Fallback: direct REST API call (bypass sdmx1 library)
            try:
                result = self._oecd_rest_fallback(dataset, country, subject, recent)
                if result.get("success"):
                    return result
            except Exception:
                pass

            return error_response(
                f"OECD dataset '{dataset}' not found via sdmx1 or REST API. "
                f"한국 경제지표는 ecos_* 도구를, 미국은 FRED를 사용하세요. "
                f"macro_search_indicators('GDP') 로 World Bank 지표를 검색할 수 있습니다."
            )
        except Exception as e:
            return error_response(f"OECD query failed: {e}")

    def _oecd_rest_fallback(
        self, dataset: str, country: str, subject: str, recent: int
    ) -> Dict[str, Any]:
        """Direct OECD SDMX REST API call (bypasses sdmx1 library issues)."""
        # OECD new API: https://sdmx.oecd.org/public/rest/data/{dataset}/{filter}
        filter_parts = [country]
        if subject:
            filter_parts.append(subject)
        filter_str = ".".join(filter_parts)

        url = f"https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_KEI@DF_KEI,4.0/{filter_str}"
        headers = {"Accept": "application/vnd.sdmx.data+json;version=2.0.0"}

        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            # Try alternative URL format
            url2 = f"https://sdmx.oecd.org/public/rest/data/{dataset}/{filter_str}?dimensionAtObservation=AllDimensions"
            headers2 = {"Accept": "application/json"}
            resp = requests.get(url2, headers=headers2, timeout=30)
            if resp.status_code != 200:
                return error_response(f"OECD REST API returned {resp.status_code}")

        data = resp.json()

        # Parse SDMX-JSON response
        records = []
        try:
            datasets = data.get("data", {}).get("dataSets", [{}])
            if datasets:
                observations = datasets[0].get("observations", {})
                for key, values in list(observations.items())[:recent]:
                    records.append({"key": key, "value": values[0] if values else None})
        except (KeyError, IndexError, TypeError):
            # Simpler structure
            records = [{"raw": str(data)[:500]}]

        return success_response(
            records[-recent:],
            count=len(records),
            source="OECD (REST fallback)",
            dataset=dataset,
            country=country,
        )

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
            return error_response("sdmx1 not installed")
        try:
            imf = self._sdmx.Client("IMF", timeout=30)
            key = {"REF_AREA": country}
            if indicator:
                key["INDICATOR"] = indicator

            data = imf.data(database, key=key)
            df = data.to_pandas()

            if hasattr(df, 'reset_index'):
                df = df.reset_index()

            records = sanitize_records(df.tail(recent)) if len(df) > 0 else []

            return success_response(
                records[-recent:],
                count=len(records),
                source="IMF",
                database=database,
                country=country,
            )
        except Exception as e:
            return error_response(
                f"IMF query failed: {e}. IMF SDMX API가 변경되었을 수 있습니다. "
                f"한국 데이터는 ecos_* 도구를, 미국은 FRED를, 국제비교는 macro_worldbank를 사용하세요."
            )

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
            return error_response("sdmx1 not installed")
        try:
            bis = self._sdmx.Client("BIS", timeout=30)
            key = {"REF_AREA": country}

            data = bis.data(dataset, key=key)
            df = data.to_pandas()

            if hasattr(df, 'reset_index'):
                df = df.reset_index()

            records = sanitize_records(df.tail(recent)) if len(df) > 0 else []

            return success_response(
                records[-recent:],
                count=len(records),
                source="BIS",
                dataset=dataset,
                country=country,
            )
        except Exception as e:
            return error_response(f"BIS query failed: {e}")

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
            return error_response("wbgapi not installed")
        try:
            data = self._wb.data.DataFrame(indicator, economy=country, mrnev=recent)
            records = []
            if hasattr(data, 'to_dict'):
                for col in data.columns:
                    val = data[col].iloc[0] if len(data) > 0 else None
                    records.append({"year": str(col), "value": val})

            return success_response(
                records,
                count=len(records),
                source="OECD/IMF/BIS/World Bank",
                indicator=indicator,
                country=country,
            )
        except Exception as e:
            return error_response(f"World Bank query failed: {e}")

    def search_indicators(self, keyword: str, source: str = "worldbank", limit: int = 30) -> Dict[str, Any]:
        """Search for indicators by keyword.

        Args:
            keyword: Search term (e.g., "inflation", "GDP", "unemployment")
            source: Data source — "worldbank" (1500+ indicators) or "imf"
            limit: Max results
        """
        if source == "worldbank":
            if not self._wb:
                return error_response("wbgapi not installed")
            try:
                results = []
                info = self._wb.indicator.info(q=keyword)
                for row in info:
                    results.append({
                        "id": row.get("id", ""),
                        "name": row.get("value", ""),
                        "source": row.get("source", {}).get("value", "") if isinstance(row.get("source"), dict) else "",
                    })
                    if len(results) >= limit:
                        break
                return success_response(
                    results,
                    count=len(results),
                    source="OECD/IMF/BIS/World Bank",
                    keyword=keyword,
                    usage="macro_worldbank(indicator='INDICATOR_ID', country='KOR') 로 데이터 조회",
                )
            except Exception as e:
                return error_response(f"World Bank indicator search failed: {e}")
        else:
            return error_response(f"Search not supported for source: {source}. Use 'worldbank'.")

    def get_available_datasets(self, source: str = "OECD") -> Dict[str, Any]:
        """List available datasets from a source."""
        if not self._sdmx:
            return error_response("sdmx1 not installed")
        try:
            client = self._sdmx.Client(source, timeout=30)
            flows = client.dataflow()
            datasets = []
            for key, flow in list(flows.dataflow.items()):
                datasets.append({"id": str(key), "name": str(flow.name)})
            return success_response(datasets, count=len(datasets), source="OECD/IMF/BIS/World Bank")
        except Exception as e:
            return error_response(str(e))

    def country_compare(
        self, indicator: str = "NY.GDP.MKTP.CD",
        countries: str = "KOR,USA,JPN,CHN,DEU",
        recent: int = 10,
    ) -> Dict[str, Any]:
        """Compare an indicator across multiple countries (World Bank).

        Args:
            indicator: World Bank indicator ID
            countries: Comma-separated country codes (ISO3)
            recent: Number of recent data points
        """
        if not self._wb:
            return error_response("wbgapi not installed")
        try:
            country_list = [c.strip() for c in countries.split(",")]
            results = {}
            for country in country_list:
                try:
                    data = self._wb.data.DataFrame(indicator, economy=country, mrnev=recent)
                    records = []
                    if hasattr(data, 'to_dict'):
                        for col in data.columns:
                            val = data[col].iloc[0] if len(data) > 0 else None
                            records.append({"year": str(col), "value": val})
                    results[country] = records
                except Exception as e:
                    results[country] = {"error": str(e)}
            return success_response(
                results,
                source="World Bank",
                indicator=indicator,
                countries=country_list,
            )
        except Exception as e:
            return error_response(f"Country compare failed: {e}")

    def get_fred_series(
        self, series_id: str = "FEDFUNDS", limit: int = 30
    ) -> Dict[str, Any]:
        """Get FRED (Federal Reserve Economic Data) series.

        Free API, popular series:
        - FEDFUNDS: Federal Funds Rate
        - DGS10: 10-Year Treasury Rate
        - CPIAUCSL: CPI (All Urban Consumers)
        - UNRATE: Unemployment Rate
        - GDP: Gross Domestic Product
        - DEXKOUS: KRW/USD Exchange Rate
        - SP500: S&P 500
        - VIXCLS: VIX Volatility Index
        - T10Y2Y: 10Y-2Y Treasury Spread
        - DCOILWTICO: WTI Crude Oil

        Args:
            series_id: FRED series ID
            limit: Number of recent observations
        """
        try:
            api_key = os.getenv("FRED_API_KEY", "")
            if not api_key:
                return error_response(
                    "FRED_API_KEY not set. Get free key at https://fred.stlouisfed.org/docs/api/api_key.html"
                )
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id": series_id,
                "api_key": api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": limit,
            }
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                return error_response(f"FRED API error: {resp.status_code}")
            data = resp.json()
            observations = data.get("observations", [])
            records = [
                {"date": o["date"], "value": float(o["value"]) if o["value"] != "." else None}
                for o in observations
            ]
            records.reverse()  # oldest first
            return success_response(
                records,
                count=len(records),
                source="FRED (Federal Reserve)",
                series_id=series_id,
            )
        except Exception as e:
            return error_response(f"FRED query failed: {e}")

    def search_fred(self, keyword: str, limit: int = 20) -> Dict[str, Any]:
        """Search FRED series by keyword.

        Args:
            keyword: Search term (e.g., "interest rate", "inflation")
            limit: Max results
        """
        try:
            api_key = os.getenv("FRED_API_KEY", "")
            if not api_key:
                return error_response("FRED_API_KEY not set")
            url = "https://api.stlouisfed.org/fred/series/search"
            params = {
                "search_text": keyword,
                "api_key": api_key,
                "file_type": "json",
                "limit": limit,
            }
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                return error_response(f"FRED search error: {resp.status_code}")
            data = resp.json()
            series_list = data.get("seriess", [])
            records = [
                {
                    "id": s["id"],
                    "title": s.get("title", ""),
                    "frequency": s.get("frequency_short", ""),
                    "units": s.get("units_short", ""),
                    "last_updated": s.get("last_updated", ""),
                }
                for s in series_list
            ]
            return success_response(
                records,
                count=len(records),
                source="FRED (Federal Reserve)",
                keyword=keyword,
                usage="macro_fred(series_id='SERIES_ID') 로 데이터 조회",
            )
        except Exception as e:
            return error_response(f"FRED search failed: {e}")
