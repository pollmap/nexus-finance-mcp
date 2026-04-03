"""Conflict & Geopolitical Risk Adapter — UCDP, ACLED, Global Peace Index."""
import logging
import os
import requests
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ConflictAdapter:
    """Armed conflict data, peace indices, and geopolitical risk assessment."""

    def __init__(self):
        self._acled_key = os.getenv("ACLED_API_KEY", "")
        self._acled_email = os.getenv("ACLED_EMAIL", "")
        self._ucdp_base = "https://ucdpapi.pcr.uu.se/api"
        self._ucdp_token = os.getenv("UCDP_API_TOKEN", "")

    def get_active_conflicts(self, year: Optional[int] = None) -> Dict[str, Any]:
        """UCDP GED events — active armed conflict events for a given year."""
        try:
            if year is None:
                year = datetime.now().year
            url = f"{self._ucdp_base}/gedevents/25.0.0"
            params = {
                "pagesize": 100,
                "Year": year,
            }
            headers = {"Accept": "application/json"}
            if self._ucdp_token:
                headers["x-ucdp-access-token"] = self._ucdp_token
            else:
                return {"error": True, "message": "UCDP API requires token. Set UCDP_API_TOKEN env var. Register free at https://ucdp.uu.se/apidocs/"}
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            if resp.status_code != 200:
                return {"error": True, "message": f"UCDP GED API returned {resp.status_code}"}

            data = resp.json()
            results = data.get("Result", [])
            records = []
            for ev in results:
                type_of_violence = ev.get("type_of_violence", 0)
                if type_of_violence not in [1, 2, 3]:
                    continue
                violence_labels = {1: "state-based", 2: "non-state", 3: "one-sided"}
                records.append({
                    "conflict_name": ev.get("dyad_name", ev.get("conflict_name", "Unknown")),
                    "country": ev.get("country", ""),
                    "region": ev.get("region", ""),
                    "type_of_violence": type_of_violence,
                    "violence_type_label": violence_labels.get(type_of_violence, "unknown"),
                    "deaths_total": ev.get("best", 0),
                    "deaths_low": ev.get("low", 0),
                    "deaths_high": ev.get("high", 0),
                    "date_start": ev.get("date_start", ""),
                    "date_end": ev.get("date_end", ""),
                    "latitude": ev.get("latitude"),
                    "longitude": ev.get("longitude"),
                })

            return {
                "success": True,
                "source": "UCDP/GED v25.0",
                "year": year,
                "count": len(records),
                "data": records,
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_battle_deaths(self, country: Optional[str] = None, years: int = 5) -> Dict[str, Any]:
        """UCDP GED — aggregate battle deaths by year, optionally filtered by country."""
        if not self._ucdp_token:
            return {"error": True, "message": "UCDP API requires token. Set UCDP_API_TOKEN env var."}
        try:
            current_year = datetime.now().year
            yearly_data = []
            for yr in range(current_year - years, current_year + 1):
                url = f"{self._ucdp_base}/gedevents/25.0.0"
                params = {"pagesize": 100, "Year": yr}
                if country:
                    params["Country"] = country
                headers = {"Accept": "application/json", "x-ucdp-access-token": self._ucdp_token}
                resp = requests.get(url, params=params, headers=headers, timeout=30)
                if resp.status_code != 200:
                    yearly_data.append({"year": yr, "total_deaths": None, "events": 0, "error": f"HTTP {resp.status_code}"})
                    continue

                data = resp.json()
                results = data.get("Result", [])
                total_deaths = sum(ev.get("best", 0) for ev in results)
                yearly_data.append({
                    "year": yr,
                    "total_deaths": total_deaths,
                    "events": len(results),
                    "total_pages": data.get("TotalPages", 1),
                })

            return {
                "success": True,
                "source": "UCDP/GED v25.0",
                "country": country or "Global",
                "years_range": f"{current_year - years}-{current_year}",
                "note": "Page 1 only (up to 100 events/year). Actual totals may be higher.",
                "data": yearly_data,
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_country_risk(self, country_name: str) -> Dict[str, Any]:
        """UCDP-based country conflict risk — event counts and deaths over last 3 years."""
        if not self._ucdp_token:
            return {"error": True, "message": "UCDP API requires token. Set UCDP_API_TOKEN env var."}
        try:
            current_year = datetime.now().year
            total_events = 0
            total_deaths = 0
            yearly_breakdown = []

            for yr in range(current_year - 2, current_year + 1):
                url = f"{self._ucdp_base}/gedevents/25.0.0"
                params = {"pagesize": 100, "Year": yr, "Country": country_name}
                headers = {"Accept": "application/json", "x-ucdp-access-token": self._ucdp_token}
                resp = requests.get(url, params=params, headers=headers, timeout=30)
                if resp.status_code != 200:
                    continue

                data = resp.json()
                results = data.get("Result", [])
                yr_deaths = sum(ev.get("best", 0) for ev in results)
                total_events += len(results)
                total_deaths += yr_deaths
                yearly_breakdown.append({
                    "year": yr,
                    "events": len(results),
                    "deaths": yr_deaths,
                })

            # Risk level thresholds
            if total_events == 0:
                risk_level = "low"
            elif total_events < 10 and total_deaths < 100:
                risk_level = "low"
            elif total_events < 50 and total_deaths < 1000:
                risk_level = "medium"
            elif total_events < 200 and total_deaths < 5000:
                risk_level = "high"
            else:
                risk_level = "critical"

            return {
                "success": True,
                "source": "UCDP/GED v25.0",
                "country": country_name,
                "period": f"{current_year - 2}-{current_year}",
                "event_count": total_events,
                "total_deaths": total_deaths,
                "risk_level": risk_level,
                "yearly_breakdown": yearly_breakdown,
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_peace_index(self) -> Dict[str, Any]:
        """Global Peace Index 2024 — top 10 most peaceful and bottom 10 least peaceful."""
        try:
            # GPI 2024 curated data from Vision of Humanity (annual release, June 2024)
            # Scale: 1 = most peaceful, 5 = least peaceful
            gpi_data = [
                # Top 10 most peaceful
                {"rank": 1, "country": "Iceland", "score": 1.124, "change_from_previous": 0.007},
                {"rank": 2, "country": "Ireland", "score": 1.263, "change_from_previous": -0.012},
                {"rank": 3, "country": "Austria", "score": 1.300, "change_from_previous": -0.013},
                {"rank": 4, "country": "New Zealand", "score": 1.313, "change_from_previous": 0.024},
                {"rank": 5, "country": "Singapore", "score": 1.339, "change_from_previous": -0.017},
                {"rank": 6, "country": "Switzerland", "score": 1.357, "change_from_previous": 0.011},
                {"rank": 7, "country": "Portugal", "score": 1.372, "change_from_previous": 0.031},
                {"rank": 8, "country": "Denmark", "score": 1.377, "change_from_previous": 0.002},
                {"rank": 9, "country": "Slovenia", "score": 1.380, "change_from_previous": -0.032},
                {"rank": 10, "country": "Malaysia", "score": 1.382, "change_from_previous": -0.049},
                # Bottom 10 least peaceful (out of 163 countries)
                {"rank": 154, "country": "DR Congo", "score": 3.166, "change_from_previous": 0.093},
                {"rank": 155, "country": "Russia", "score": 3.180, "change_from_previous": 0.027},
                {"rank": 156, "country": "South Sudan", "score": 3.221, "change_from_previous": -0.034},
                {"rank": 157, "country": "Israel", "score": 3.254, "change_from_previous": 0.721},
                {"rank": 158, "country": "Somalia", "score": 3.252, "change_from_previous": -0.053},
                {"rank": 159, "country": "Ukraine", "score": 3.280, "change_from_previous": -0.088},
                {"rank": 160, "country": "Syria", "score": 3.294, "change_from_previous": -0.162},
                {"rank": 161, "country": "Afghanistan", "score": 3.294, "change_from_previous": -0.080},
                {"rank": 162, "country": "Sudan", "score": 3.428, "change_from_previous": 0.410},
                {"rank": 163, "country": "Yemen", "score": 3.449, "change_from_previous": 0.016},
            ]

            return {
                "success": True,
                "source": "Vision of Humanity / Global Peace Index 2024",
                "total_countries": 163,
                "scale": "1 (most peaceful) to 5 (least peaceful)",
                "note": "Curated top 10 and bottom 10. Full index published annually in June.",
                "data": gpi_data,
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_geopolitical_events(self, query: str, days: int = 30) -> Dict[str, Any]:
        """Search recent conflict-related events via UCDP or ACLED."""
        try:
            # Try ACLED first if key available
            if self._acled_key and self._acled_email:
                return self._acled_search(query, days)

            # Fallback: UCDP search
            url = f"{self._ucdp_base}/gedevents/25.0.0"
            params = {
                "pagesize": 50,
                "Country": query,
            }
            headers = {"Accept": "application/json"}
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            if resp.status_code != 200:
                return {"error": True, "message": f"UCDP API returned {resp.status_code}"}

            data = resp.json()
            results = data.get("Result", [])
            records = []
            for ev in results[:50]:
                records.append({
                    "conflict_name": ev.get("dyad_name", ""),
                    "country": ev.get("country", ""),
                    "date_start": ev.get("date_start", ""),
                    "deaths": ev.get("best", 0),
                    "type_of_violence": ev.get("type_of_violence", 0),
                    "source_article": ev.get("source_article", ""),
                })

            return {
                "success": True,
                "source": "UCDP/GED v25.0",
                "query": query,
                "count": len(records),
                "data": records,
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def _acled_search(self, query: str, days: int) -> Dict[str, Any]:
        """ACLED conflict events search (requires free API key)."""
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            url = "https://api.acleddata.com/acled/read"
            params = {
                "key": self._acled_key,
                "email": self._acled_email,
                "country": query,
                "event_date": f"{start_date}|",
                "event_date_where": "BETWEEN",
                "limit": 50,
            }
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code != 200:
                return {"error": True, "message": f"ACLED API returned {resp.status_code}"}

            data = resp.json()
            if not data.get("success"):
                return {"error": True, "message": data.get("error", "ACLED query failed")}

            records = []
            for ev in data.get("data", []):
                records.append({
                    "event_date": ev.get("event_date", ""),
                    "event_type": ev.get("event_type", ""),
                    "sub_event_type": ev.get("sub_event_type", ""),
                    "country": ev.get("country", ""),
                    "location": ev.get("location", ""),
                    "fatalities": ev.get("fatalities", 0),
                    "source": ev.get("source", ""),
                    "notes": (ev.get("notes") or "")[:200],
                })

            return {
                "success": True,
                "source": "ACLED",
                "query": query,
                "period_days": days,
                "count": len(records),
                "data": records,
            }
        except Exception as e:
            return {"error": True, "message": str(e)}
