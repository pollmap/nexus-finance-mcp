"""Consumer/Retail Adapter — FRED series, Eurostat."""
import logging
import os
import requests
from utils.http_client import get_session
from typing import Any, Dict

logger = logging.getLogger(__name__)
_session = get_session("consumer_adapter")


class ConsumerAdapter:
    """Consumer and retail economic data — free APIs."""

    def __init__(self):
        self._fred_key = os.getenv("FRED_API_KEY", "")

    def _get_fred_series(self, series_id: str, limit: int = 60) -> Dict[str, Any]:
        """Generic FRED series fetcher."""
        try:
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {"series_id": series_id, "api_key": self._fred_key, "file_type": "json",
                      "sort_order": "desc", "limit": limit}
            resp = _session.get(url, params=params, timeout=15)
            data = (resp.json() if resp.status_code == 200 else {}).get("observations", [])
            records = [{"date": d["date"], "value": d["value"]} for d in data if d["value"] != "."]
            return {"success": True, "source": f"FRED/{series_id}", "count": len(records), "data": records}
        except Exception as e:
            logger.error(f"FRED {series_id} error: {e}")
            return {"error": True, "message": f"FRED data retrieval failed for {series_id}"}

    def get_us_retail_sales(self, limit: int = 60) -> Dict[str, Any]:
        """미국 소매판매 (Advance Retail Sales)."""
        result = self._get_fred_series("RSXFS", limit)
        if result.get("success"):
            result["series"] = "Advance Retail Sales: Retail and Food Services"
            result["unit"] = "Millions of Dollars"
        return result

    def get_us_consumer_sentiment(self, limit: int = 60) -> Dict[str, Any]:
        """미시간대 소비자심리지수."""
        result = self._get_fred_series("UMCSENT", limit)
        if result.get("success"):
            result["series"] = "University of Michigan Consumer Sentiment"
            result["unit"] = "Index 1966:Q1=100"
        return result

    def get_us_housing_starts(self, limit: int = 60) -> Dict[str, Any]:
        """미국 주택착공 건수."""
        result = self._get_fred_series("HOUST", limit)
        if result.get("success"):
            result["series"] = "Housing Starts: Total"
            result["unit"] = "Thousands of Units"
        return result

    def get_eu_hicp(self, limit: int = 30) -> Dict[str, Any]:
        """유럽 소비자물가 조화지수 (HICP)."""
        try:
            url = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/PRC_HICP_MANR/M.RCH_A.CP00.EA/"
            params = {"format": "JSON", "lang": "en"}
            resp = _session.get(url, params=params, timeout=20)
            if resp.status_code != 200:
                return {"error": True, "message": f"Eurostat HTTP {resp.status_code}"}

            data = resp.json()
            values = data.get("value", {})
            dimensions = data.get("dimension", {}).get("time", {}).get("category", {}).get("index", {})

            records = []
            for time_key, idx in sorted(dimensions.items(), key=lambda x: x[0], reverse=True)[:limit]:
                val = values.get(str(idx))
                if val is not None:
                    records.append({"date": time_key, "value": val})

            return {"success": True, "source": "Eurostat/HICP", "series": "Euro Area HICP Annual Rate", "unit": "%", "count": len(records), "data": records}
        except Exception as e:
            return {"error": True, "message": str(e)}
