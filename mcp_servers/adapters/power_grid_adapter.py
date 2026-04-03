"""Power Grid & Energy Adapter — Electricity Maps, EIA, ENTSO-E."""
import logging
import os
import requests
from utils.http_client import get_session
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
_session = get_session("power_grid_adapter")


class PowerGridAdapter:
    """Electricity generation, carbon intensity, nuclear status, renewables."""

    def __init__(self):
        self._elecmaps_token = os.getenv("ELECTRICITY_MAPS_TOKEN", "")
        self._eia_key = os.getenv("EIA_API_KEY", os.getenv("FRED_API_KEY", ""))
        self._entsoe_key = os.getenv("ENTSOE_API_KEY", "")

    def get_eu_generation(self, country_code: str = "DE") -> Dict[str, Any]:
        """ENTSO-E electricity generation by source (requires entsoe-py library)."""
        try:
            try:
                from entsoe import EntsoePandasClient
            except ImportError:
                return {
                    "error": True,
                    "message": (
                        "entsoe-py library not installed. "
                        "Install with: pip install entsoe-py. "
                        "Also requires ENTSOE_API_KEY env variable from "
                        "https://transparency.entsoe.eu/ (free registration)."
                    ),
                }

            if not self._entsoe_key:
                return {"error": True, "message": "ENTSOE_API_KEY not set. Register free at https://transparency.entsoe.eu/"}

            import pandas as pd
            client = EntsoePandasClient(api_key=self._entsoe_key)
            start = pd.Timestamp(datetime.now().strftime("%Y-%m-%d"), tz="Europe/Berlin")
            end = start + pd.Timedelta(days=1)

            generation = client.query_generation(country_code, start=start, end=end)

            # Convert DataFrame to dict
            if hasattr(generation, "columns"):
                latest = generation.iloc[-1] if len(generation) > 0 else generation.iloc[0]
                gen_data = {}
                for col in generation.columns:
                    col_name = col if isinstance(col, str) else " ".join(str(c) for c in col)
                    val = latest[col]
                    gen_data[col_name] = round(float(val), 1) if not (val != val) else None  # NaN check
            else:
                gen_data = {"raw": str(generation)[:1000]}

            return {
                "success": True,
                "source": "ENTSO-E Transparency Platform",
                "country_code": country_code,
                "timestamp": datetime.now().isoformat(),
                "unit": "MW",
                "data": gen_data,
            }
        except Exception as e:
            return {"error": True, "message": f"ENTSO-E query failed: {str(e)}"}

    def get_eu_price(self, country_code: str = "DE") -> Dict[str, Any]:
        """ENTSO-E day-ahead electricity prices (requires entsoe-py library)."""
        try:
            try:
                from entsoe import EntsoePandasClient
            except ImportError:
                return {
                    "error": True,
                    "message": (
                        "entsoe-py library not installed. "
                        "Install with: pip install entsoe-py. "
                        "Also requires ENTSOE_API_KEY env variable."
                    ),
                }

            if not self._entsoe_key:
                return {"error": True, "message": "ENTSOE_API_KEY not set. Register free at https://transparency.entsoe.eu/"}

            import pandas as pd
            client = EntsoePandasClient(api_key=self._entsoe_key)
            start = pd.Timestamp(datetime.now().strftime("%Y-%m-%d"), tz="Europe/Berlin")
            end = start + pd.Timedelta(days=1)

            prices = client.query_day_ahead_prices(country_code, start=start, end=end)

            records = []
            for ts, price in prices.items():
                records.append({
                    "timestamp": ts.isoformat(),
                    "price_eur_mwh": round(float(price), 2),
                })

            avg_price = round(float(prices.mean()), 2) if len(prices) > 0 else None
            min_price = round(float(prices.min()), 2) if len(prices) > 0 else None
            max_price = round(float(prices.max()), 2) if len(prices) > 0 else None

            return {
                "success": True,
                "source": "ENTSO-E Transparency Platform",
                "country_code": country_code,
                "unit": "EUR/MWh",
                "average_price": avg_price,
                "min_price": min_price,
                "max_price": max_price,
                "count": len(records),
                "data": records,
            }
        except Exception as e:
            return {"error": True, "message": f"ENTSO-E price query failed: {str(e)}"}

    def get_carbon_intensity(self, zone: str = "DE") -> Dict[str, Any]:
        """Electricity Maps — real-time carbon intensity (gCO2eq/kWh)."""
        try:
            url = f"https://api.electricitymap.org/v3/carbon-intensity/latest"
            params = {"zone": zone}
            headers = {"Accept": "application/json"}
            if self._elecmaps_token:
                headers["auth-token"] = self._elecmaps_token

            resp = _session.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 401:
                return {
                    "error": True,
                    "message": (
                        "Electricity Maps API requires auth token. "
                        "Set ELECTRICITY_MAPS_TOKEN env variable. "
                        "Free tier available at https://app.electricitymap.org/map"
                    ),
                }
            if resp.status_code != 200:
                return {"error": True, "message": f"Electricity Maps returned {resp.status_code}: {resp.text[:200]}"}

            data = resp.json()
            return {
                "success": True,
                "source": "Electricity Maps",
                "zone": zone,
                "carbon_intensity_gco2_kwh": data.get("carbonIntensity"),
                "fossil_fuel_percentage": data.get("fossilFuelPercentage"),
                "renewable_percentage": data.get("renewablePercentage"),
                "datetime": data.get("datetime"),
                "updated_at": data.get("updatedAt"),
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_nuclear_status(self) -> Dict[str, Any]:
        """EIA — US nuclear electricity generation (daily, last 30 days)."""
        try:
            if not self._eia_key:
                return {"error": True, "message": "EIA_API_KEY not set. Free key at https://www.eia.gov/opendata/register.php"}

            url = "https://api.eia.gov/v2/electricity/rto/daily-fuel-type-data/data/"
            params = {
                "api_key": self._eia_key,
                "facets[respondent][]": "US48",
                "facets[fueltype][]": "NUC",
                "length": 30,
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "frequency": "daily",
            }
            resp = _session.get(url, params=params, timeout=20)
            if resp.status_code != 200:
                return {"error": True, "message": f"EIA API returned {resp.status_code}"}

            data = resp.json()
            response_data = data.get("response", {}).get("data", [])
            records = []
            for entry in response_data:
                records.append({
                    "period": entry.get("period", ""),
                    "generation_mwh": entry.get("value"),
                    "respondent": entry.get("respondent-name", ""),
                    "fueltype": entry.get("fueltype", ""),
                    "type_name": entry.get("type-name", ""),
                })

            return {
                "success": True,
                "source": "EIA (US Energy Information Administration)",
                "description": "US48 nuclear electricity generation (daily)",
                "unit": "MWh",
                "count": len(records),
                "data": records,
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_renewable_forecast(self, zone: str = "DE") -> Dict[str, Any]:
        """Electricity Maps — power production breakdown by source."""
        try:
            url = "https://api.electricitymap.org/v3/power-breakdown/latest"
            params = {"zone": zone}
            headers = {"Accept": "application/json"}
            if self._elecmaps_token:
                headers["auth-token"] = self._elecmaps_token

            resp = _session.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 401:
                return {
                    "error": True,
                    "message": (
                        "Electricity Maps API requires auth token for this endpoint. "
                        "Set ELECTRICITY_MAPS_TOKEN env variable."
                    ),
                }
            if resp.status_code != 200:
                return {"error": True, "message": f"Electricity Maps returned {resp.status_code}: {resp.text[:200]}"}

            data = resp.json()

            production = data.get("powerProductionBreakdown", {})
            imports = data.get("powerImportBreakdown", {})
            consumption = data.get("powerConsumptionBreakdown", {})

            # Calculate renewable total
            renewable_sources = ["wind", "solar", "hydro", "biomass", "geothermal"]
            renewable_total = sum(
                production.get(src, 0) or 0 for src in renewable_sources
            )
            total_production = sum(
                v for v in production.values() if v is not None and isinstance(v, (int, float))
            )
            renewable_pct = round(renewable_total / total_production * 100, 1) if total_production > 0 else None

            return {
                "success": True,
                "source": "Electricity Maps",
                "zone": zone,
                "datetime": data.get("datetime"),
                "renewable_percentage": renewable_pct,
                "total_production_mw": round(total_production, 1) if total_production else None,
                "power_production_breakdown": production,
                "power_import_breakdown": imports,
                "power_consumption_breakdown": consumption,
                "fossil_fuel_percentage": data.get("fossilFuelPercentage"),
            }
        except Exception as e:
            return {"error": True, "message": str(e)}
