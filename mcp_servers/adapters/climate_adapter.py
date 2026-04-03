"""Climate Data Adapter — Open-Meteo, NASA GISS, NOAA ENSO."""
import logging
import csv
import io
import requests
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ClimateAdapter:
    """Climate and weather data — all free APIs, no keys required."""

    def __init__(self):
        self._meteo_base = "https://archive-api.open-meteo.com/v1/archive"
        self._giss_url = "https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv"
        self._enso_url = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"

    def get_historical_weather(
        self, latitude: float, longitude: float, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """Open-Meteo archive — daily weather history for any location."""
        try:
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date,
                "end_date": end_date,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
                "timezone": "auto",
            }
            resp = requests.get(self._meteo_base, params=params, timeout=30)
            if resp.status_code != 200:
                return {"error": True, "message": f"Open-Meteo returned {resp.status_code}: {resp.text[:200]}"}

            data = resp.json()
            daily = data.get("daily", {})
            dates = daily.get("time", [])
            records = []
            for i, d in enumerate(dates):
                records.append({
                    "date": d,
                    "temp_max_c": daily.get("temperature_2m_max", [None])[i] if i < len(daily.get("temperature_2m_max", [])) else None,
                    "temp_min_c": daily.get("temperature_2m_min", [None])[i] if i < len(daily.get("temperature_2m_min", [])) else None,
                    "precipitation_mm": daily.get("precipitation_sum", [None])[i] if i < len(daily.get("precipitation_sum", [])) else None,
                    "windspeed_max_kmh": daily.get("windspeed_10m_max", [None])[i] if i < len(daily.get("windspeed_10m_max", [])) else None,
                })

            return {
                "success": True,
                "source": "Open-Meteo/Archive",
                "location": {"latitude": latitude, "longitude": longitude},
                "period": {"start": start_date, "end": end_date},
                "count": len(records),
                "data": records,
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_temperature_anomaly(self, period: str = "monthly") -> Dict[str, Any]:
        """NASA GISS global temperature anomaly — last 120 months."""
        try:
            resp = requests.get(self._giss_url, timeout=20)
            if resp.status_code != 200:
                return {"error": True, "message": f"NASA GISS returned {resp.status_code}"}

            text = resp.text
            reader = csv.reader(io.StringIO(text))
            rows = list(reader)

            # Find the header row with month names
            header_idx = None
            for i, row in enumerate(rows):
                if len(row) > 1 and row[0].strip() == "Year":
                    header_idx = i
                    break

            if header_idx is None:
                return {"error": True, "message": "Could not parse NASA GISS CSV header"}

            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

            records = []
            for row in rows[header_idx + 1:]:
                if len(row) < 13:
                    continue
                year_str = row[0].strip()
                if not year_str.isdigit():
                    continue
                year = int(year_str)
                for m_idx, m_name in enumerate(month_names):
                    val_str = row[m_idx + 1].strip()
                    if val_str == "" or val_str == "***":
                        continue
                    try:
                        anomaly = float(val_str)
                        records.append({
                            "year": year,
                            "month": m_idx + 1,
                            "month_name": m_name,
                            "anomaly_celsius": anomaly,
                        })
                    except ValueError:
                        continue

            # Return last 120 months
            records = records[-120:]

            return {
                "success": True,
                "source": "NASA/GISS",
                "description": "Global Land-Ocean Temperature Anomaly (base: 1951-1980)",
                "period_type": period,
                "count": len(records),
                "data": records,
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_extreme_events(
        self, latitude: float, longitude: float, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """Count extreme weather days — heat (>35C), cold (<-10C), heavy rain (>50mm)."""
        try:
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date,
                "end_date": end_date,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto",
            }
            resp = requests.get(self._meteo_base, params=params, timeout=30)
            if resp.status_code != 200:
                return {"error": True, "message": f"Open-Meteo returned {resp.status_code}"}

            data = resp.json()
            daily = data.get("daily", {})
            dates = daily.get("time", [])
            temp_max = daily.get("temperature_2m_max", [])
            temp_min = daily.get("temperature_2m_min", [])
            precip = daily.get("precipitation_sum", [])

            total_days = len(dates)
            heat_days, cold_days, heavy_rain_days = 0, 0, 0
            heat_events, cold_events, rain_events = [], [], []

            for i in range(total_days):
                if i < len(temp_max) and temp_max[i] is not None and temp_max[i] > 35:
                    heat_days += 1
                    if len(heat_events) < 5:
                        heat_events.append({"date": dates[i], "temp_max_c": temp_max[i]})
                if i < len(temp_min) and temp_min[i] is not None and temp_min[i] < -10:
                    cold_days += 1
                    if len(cold_events) < 5:
                        cold_events.append({"date": dates[i], "temp_min_c": temp_min[i]})
                if i < len(precip) and precip[i] is not None and precip[i] > 50:
                    heavy_rain_days += 1
                    if len(rain_events) < 5:
                        rain_events.append({"date": dates[i], "precipitation_mm": precip[i]})

            return {
                "success": True,
                "source": "Open-Meteo/Archive",
                "location": {"latitude": latitude, "longitude": longitude},
                "period": {"start": start_date, "end": end_date},
                "total_days": total_days,
                "extreme_counts": {
                    "heat_days_above_35c": heat_days,
                    "cold_days_below_neg10c": cold_days,
                    "heavy_rain_days_above_50mm": heavy_rain_days,
                },
                "sample_events": {
                    "heat": heat_events,
                    "cold": cold_events,
                    "heavy_rain": rain_events,
                },
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_enso_index(self) -> Dict[str, Any]:
        """NOAA Oceanic Nino Index (ONI) — last 24 quarters."""
        try:
            resp = requests.get(self._enso_url, timeout=20)
            if resp.status_code != 200:
                return {"error": True, "message": f"NOAA ENSO returned {resp.status_code}"}

            lines = resp.text.strip().split("\n")
            # Format: " SEAS  YR   TOTAL   ANOM" — each line is one season
            records = []
            for line in lines[1:]:  # skip header
                parts = line.split()
                if len(parts) < 4:
                    continue
                try:
                    season = parts[0]
                    year = int(parts[1])
                    oni_val = float(parts[3])  # ANOM column
                except (ValueError, IndexError):
                    continue
                classification = "Neutral"
                if oni_val >= 0.5:
                    classification = "El Nino"
                elif oni_val <= -0.5:
                    classification = "La Nina"
                records.append({
                    "year": year,
                    "season": season,
                    "oni_index": oni_val,
                    "classification": classification,
                })

            # Return last 24 quarters
            records = records[-24:]

            return {
                "success": True,
                "source": "NOAA/CPC",
                "description": "Oceanic Nino Index (ONI): +0.5=El Nino, -0.5=La Nina",
                "count": len(records),
                "data": records,
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_city_comparison(self, cities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare weather across multiple cities — last 365 days."""
        try:
            end_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=370)).strftime("%Y-%m-%d")
            results = []

            for city in cities[:10]:  # max 10 cities
                name = city.get("name", "Unknown")
                lat = city.get("lat")
                lon = city.get("lon")
                if lat is None or lon is None:
                    results.append({"name": name, "error": "Missing lat/lon"})
                    continue

                params = {
                    "latitude": lat,
                    "longitude": lon,
                    "start_date": start_date,
                    "end_date": end_date,
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
                    "timezone": "auto",
                }
                resp = requests.get(self._meteo_base, params=params, timeout=30)
                if resp.status_code != 200:
                    results.append({"name": name, "error": f"HTTP {resp.status_code}"})
                    continue

                data = resp.json().get("daily", {})
                temp_max = [v for v in data.get("temperature_2m_max", []) if v is not None]
                temp_min = [v for v in data.get("temperature_2m_min", []) if v is not None]
                precip = [v for v in data.get("precipitation_sum", []) if v is not None]
                wind = [v for v in data.get("windspeed_10m_max", []) if v is not None]

                avg_temp = round((sum(temp_max) / len(temp_max) + sum(temp_min) / len(temp_min)) / 2, 1) if temp_max and temp_min else None
                total_precip = round(sum(precip), 1) if precip else None
                max_wind = round(max(wind), 1) if wind else None

                results.append({
                    "name": name,
                    "latitude": lat,
                    "longitude": lon,
                    "avg_temp_c": avg_temp,
                    "total_precipitation_mm": total_precip,
                    "max_windspeed_kmh": max_wind,
                    "days_analyzed": len(data.get("time", [])),
                })

            return {
                "success": True,
                "source": "Open-Meteo/Archive",
                "period": {"start": start_date, "end": end_date},
                "count": len(results),
                "data": results,
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_crop_weather(self) -> Dict[str, Any]:
        """Crop weather for major agricultural regions — last 30 days."""
        try:
            regions = [
                {"name": "US Midwest (Iowa)", "lat": 41.8, "lon": -93.1},
                {"name": "Brazil Mato Grosso", "lat": -13.5, "lon": -56.1},
                {"name": "Ukraine Black Sea", "lat": 48.5, "lon": 35.0},
            ]

            end_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=35)).strftime("%Y-%m-%d")
            results = []

            for region in regions:
                params = {
                    "latitude": region["lat"],
                    "longitude": region["lon"],
                    "start_date": start_date,
                    "end_date": end_date,
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
                    "timezone": "auto",
                }
                resp = requests.get(self._meteo_base, params=params, timeout=30)
                if resp.status_code != 200:
                    results.append({"region": region["name"], "error": f"HTTP {resp.status_code}"})
                    continue

                data = resp.json().get("daily", {})
                temp_max = [v for v in data.get("temperature_2m_max", []) if v is not None]
                temp_min = [v for v in data.get("temperature_2m_min", []) if v is not None]
                precip = [v for v in data.get("precipitation_sum", []) if v is not None]
                wind = [v for v in data.get("windspeed_10m_max", []) if v is not None]

                avg_high = round(sum(temp_max) / len(temp_max), 1) if temp_max else None
                avg_low = round(sum(temp_min) / len(temp_min), 1) if temp_min else None
                total_precip = round(sum(precip), 1) if precip else None
                max_wind = round(max(wind), 1) if wind else None
                frost_days = sum(1 for v in temp_min if v < 0)

                results.append({
                    "region": region["name"],
                    "latitude": region["lat"],
                    "longitude": region["lon"],
                    "avg_high_c": avg_high,
                    "avg_low_c": avg_low,
                    "total_precipitation_mm": total_precip,
                    "max_windspeed_kmh": max_wind,
                    "frost_days": frost_days,
                    "days_analyzed": len(data.get("time", [])),
                })

            return {
                "success": True,
                "source": "Open-Meteo/Archive",
                "description": "30-day crop weather for major agricultural regions",
                "period": {"start": start_date, "end": end_date},
                "count": len(results),
                "data": results,
            }
        except Exception as e:
            return {"error": True, "message": str(e)}
