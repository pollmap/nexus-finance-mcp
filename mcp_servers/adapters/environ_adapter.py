"""Environment/Utilities Adapter — EPA, Carbon pricing."""
import logging
import os
import sys
from pathlib import Path
import requests
from utils.http_client import get_session
from typing import Any, Dict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)
_session = get_session("environ_adapter")


class EnvironAdapter:
    """Environmental and utilities data — free APIs."""

    def __init__(self):
        self._fred_key = os.getenv("FRED_API_KEY", "")

    def get_epa_air_quality(self, state: str = "36", year: int = 2024) -> Dict[str, Any]:
        """EPA Air Quality System — 대기질 데이터 (미국 주별)."""
        try:
            url = "https://aqs.epa.gov/data/api/annualData/byState"
            params = {
                "email": os.getenv("CONTACT_EMAIL", "research@nexus.finance"),
                "key": "test",
                "param": "44201",  # Ozone
                "bdate": f"{year}0101",
                "edate": f"{year}1231",
                "state": state,
            }
            resp = _session.get(url, params=params, timeout=60)
            data = resp.json() if resp.status_code == 200 else {}

            results = data.get("Data", [])
            records = []
            for r in results:
                records.append({
                    "site": r.get("local_site_name", ""),
                    "county": r.get("county_name", ""),
                    "parameter": r.get("parameter_name", ""),
                    "mean": r.get("arithmetic_mean"),
                    "max": r.get("first_max_value"),
                    "unit": r.get("units_of_measure", ""),
                    "year": r.get("year", year),
                })

            return success_response(records, source="EPA/KRBN", state=state, year=year)
        except Exception as e:
            return error_response(str(e))

    def get_carbon_price(self, limit: int = 30) -> Dict[str, Any]:
        """탄소배출권 가격 (EU ETS proxy via FRED 또는 Yahoo)."""
        try:
            import yfinance as yf
            # KRBN (KraneShares Global Carbon Strategy ETF) as carbon price proxy
            ticker = yf.Ticker("KRBN")
            hist = ticker.history(period="3mo")
            if hist is not None and not hist.empty:
                hist = hist.reset_index()
                records = [{"date": str(row["Date"].date()), "price": round(row["Close"], 2)} for _, row in hist.iterrows()]
                records = records[-limit:]
                return success_response(
                    records,
                    source="EPA/KRBN",
                    series="Global Carbon Strategy ETF (proxy)",
                )
        except Exception as e:
            logger.warning(f"Carbon price fetch failed (KRBN ETF): {e}")

        # Fallback: FRED EU ETS or just return info
        return success_response(
            [],
            source="EPA/KRBN",
            message="EU ETS carbon price not available via free API. Use KRBN ETF as proxy or check ember-climate.org.",
        )
