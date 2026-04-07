"""Space Weather Adapter — NOAA SWPC, NASA DONKI, SILSO Sunspot."""
import logging
import os
import sys
from pathlib import Path
import requests
from utils.http_client import get_session

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_servers.core.responses import error_response, success_response
from datetime import datetime, timedelta
from typing import Any, Dict

logger = logging.getLogger(__name__)
_session = get_session("space_weather_adapter")


class SpaceWeatherAdapter:
    """Space weather data — solar activity, geomagnetic indices, CMEs."""

    def __init__(self):
        self._nasa_key = os.getenv("NASA_API_KEY", "DEMO_KEY")

    def get_sunspot_data(self, period: str = "monthly") -> Dict[str, Any]:
        """SILSO 월별 태양흑점 수 (최근 120개월)."""
        try:
            url = "https://www.sidc.be/SILSO/INFO/snmtotcsv.php"
            resp = _session.get(url, timeout=20)
            if resp.status_code != 200:
                return error_response(f"SILSO API returned {resp.status_code}")

            lines = resp.text.strip().split("\n")
            records = []
            for line in lines:
                parts = [p.strip() for p in line.split(";")]
                if len(parts) < 4:
                    continue
                try:
                    year = int(parts[0])
                    month = int(parts[1])
                    sunspot_number = float(parts[3])
                    std_dev = float(parts[4]) if len(parts) > 4 else None
                    records.append({
                        "year_month": f"{year:04d}-{month:02d}",
                        "sunspot_number": sunspot_number,
                        "std_dev": std_dev,
                    })
                except (ValueError, IndexError):
                    continue

            # Return last 120 months
            records = records[-120:]
            return success_response(records, source="SILSO/WDC-SILSO", period=period)
        except Exception as e:
            return error_response(str(e))

    def get_solar_flares(self, days: int = 30) -> Dict[str, Any]:
        """NASA DONKI 태양 플레어 이벤트."""
        try:
            start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            end = datetime.now().strftime("%Y-%m-%d")
            url = "https://api.nasa.gov/DONKI/FLR"
            params = {
                "startDate": start,
                "endDate": end,
                "api_key": self._nasa_key,
            }
            resp = _session.get(url, params=params, timeout=20)
            if resp.status_code != 200:
                return error_response(f"NASA DONKI returned {resp.status_code}")

            data = resp.json()
            records = []
            for flare in data:
                records.append({
                    "flare_id": flare.get("flrID", ""),
                    "class_type": flare.get("classType", ""),
                    "begin_time": flare.get("beginTime", ""),
                    "peak_time": flare.get("peakTime", ""),
                    "end_time": flare.get("endTime", ""),
                    "source_location": flare.get("sourceLocation", ""),
                    "active_region": flare.get("activeRegionNum"),
                })

            return success_response(records, source="NASA/DONKI", period_days=days)
        except Exception as e:
            return error_response(str(e))

    def get_geomagnetic_index(self) -> Dict[str, Any]:
        """NOAA SWPC 행성 Kp 지수 (지자기 활동)."""
        try:
            url = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
            resp = _session.get(url, timeout=15)
            if resp.status_code != 200:
                return error_response(f"NOAA SWPC returned {resp.status_code}")

            data = resp.json()
            if not data:
                return success_response([], source="NOAA/SWPC")

            records = []
            for row in data:
                if isinstance(row, dict):
                    records.append({
                        "time_tag": row.get("time_tag", ""),
                        "kp": row.get("Kp"),
                        "a_running": row.get("a_running"),
                        "station_count": row.get("station_count"),
                    })
                elif isinstance(row, list) and len(row) >= 2:
                    records.append({
                        "time_tag": row[0],
                        "kp": row[1],
                        "a_running": row[3] if len(row) > 3 else None,
                        "station_count": row[4] if len(row) > 4 else None,
                    })

            # Return last 24 entries
            records = records[-24:]
            return success_response(records, source="NOAA/SWPC")
        except Exception as e:
            return error_response(str(e))

    def get_solar_wind(self) -> Dict[str, Any]:
        """NOAA SWPC 태양풍 플라즈마 데이터 (7일)."""
        try:
            url = "https://services.swpc.noaa.gov/products/solar-wind/plasma-7-day.json"
            resp = _session.get(url, timeout=15)
            if resp.status_code != 200:
                return error_response(f"NOAA SWPC returned {resp.status_code}")

            data = resp.json()
            # First row is header: ["time_tag", "density", "speed", "temperature"]
            if not data or len(data) < 2:
                return success_response([], source="NOAA/SWPC")

            records = []
            for row in data[1:]:
                if len(row) < 4:
                    continue
                records.append({
                    "time_tag": row[0],
                    "density": row[1],
                    "speed": row[2],
                    "temperature": row[3],
                })

            # Return last 48 entries (roughly 1 day at ~30min intervals)
            records = records[-48:]
            return success_response(records, source="NOAA/SWPC",
                                    description="Solar wind plasma (density p/cm3, speed km/s, temperature K)")
        except Exception as e:
            return error_response(str(e))

    def get_cme_events(self, days: int = 30) -> Dict[str, Any]:
        """NASA DONKI 코로나 질량 방출(CME) 이벤트."""
        try:
            start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            end = datetime.now().strftime("%Y-%m-%d")
            url = "https://api.nasa.gov/DONKI/CME"
            params = {
                "startDate": start,
                "endDate": end,
                "api_key": self._nasa_key,
            }
            resp = _session.get(url, params=params, timeout=20)
            if resp.status_code != 200:
                return error_response(f"NASA DONKI returned {resp.status_code}")

            data = resp.json()
            records = []
            for cme in data:
                records.append({
                    "activity_id": cme.get("activityID", ""),
                    "start_time": cme.get("startTime", ""),
                    "source_location": cme.get("sourceLocation", ""),
                    "active_region": cme.get("activeRegionNum"),
                    "note": (cme.get("note") or "")[:300],
                    "instruments": [i.get("displayName", "") for i in (cme.get("instruments") or [])],
                })

            return success_response(records, source="NASA/DONKI", period_days=days)
        except Exception as e:
            return error_response(str(e))
