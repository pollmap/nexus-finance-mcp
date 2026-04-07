"""Disaster Adapter — USGS Earthquake, NASA EONET, GDACS."""
import logging
import sys
from pathlib import Path
import requests
from utils.http_client import get_session
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)
_session = get_session("disaster_adapter")


class DisasterAdapter:
    """Global disaster and natural hazard data — free APIs."""

    def __init__(self):
        pass

    def get_earthquakes(self, min_magnitude: float = 4.0, days: int = 30, limit: int = 50) -> Dict[str, Any]:
        """USGS 지진 데이터 (규모, 위치, 시각)."""
        try:
            start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            end = datetime.now().strftime("%Y-%m-%d")
            url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
            params = {
                "format": "geojson",
                "starttime": start,
                "endtime": end,
                "minmagnitude": min_magnitude,
                "limit": limit,
                "orderby": "time",
            }
            resp = _session.get(url, params=params, timeout=20)
            if resp.status_code != 200:
                return error_response(f"USGS API returned {resp.status_code}")

            data = resp.json()
            features = data.get("features", [])
            records = []
            for f in features:
                props = f.get("properties", {})
                coords = f.get("geometry", {}).get("coordinates", [None, None, None])
                # USGS time is milliseconds since epoch
                time_ms = props.get("time")
                time_str = datetime.fromtimestamp(time_ms / 1000, tz=None).strftime("%Y-%m-%dT%H:%M:%SZ") if time_ms else None
                records.append({
                    "magnitude": props.get("mag"),
                    "place": props.get("place", ""),
                    "time": time_str,
                    "longitude": coords[0],
                    "latitude": coords[1],
                    "depth_km": coords[2],
                    "type": props.get("type", ""),
                    "tsunami": props.get("tsunami", 0),
                    "url": props.get("url", ""),
                })

            return success_response(
                records,
                source="USGS/EONET",
                min_magnitude=min_magnitude,
                period_days=days,
            )
        except Exception as e:
            return error_response(str(e))

    def _fetch_eonet_events(self, category: str, days: int, limit: int) -> Dict[str, Any]:
        """NASA EONET v3 공통 이벤트 조회."""
        try:
            url = "https://eonet.gsfc.nasa.gov/api/v3/events"
            params = {
                "category": category,
                "days": days,
                "limit": limit,
                "status": "all",
            }
            resp = _session.get(url, params=params, timeout=20)
            if resp.status_code != 200:
                return error_response(f"NASA EONET returned {resp.status_code}")

            data = resp.json()
            events = data.get("events", [])
            records = []
            for ev in events:
                # Get latest geometry
                geometries = ev.get("geometry", [])
                latest_geo = geometries[-1] if geometries else {}
                coords = latest_geo.get("coordinates", [])
                records.append({
                    "id": ev.get("id", ""),
                    "title": ev.get("title", ""),
                    "date": latest_geo.get("date", ""),
                    "longitude": coords[0] if len(coords) > 0 else None,
                    "latitude": coords[1] if len(coords) > 1 else None,
                    "sources": [s.get("url", "") for s in (ev.get("sources") or [])[:2]],
                    "closed": ev.get("closed"),
                })

            return success_response(
                records,
                source="USGS/EONET",
                category=category,
                period_days=days,
            )
        except Exception as e:
            return error_response(str(e))

    def get_volcanoes(self, days: int = 60, limit: int = 20) -> Dict[str, Any]:
        """NASA EONET 화산 활동 이벤트."""
        return self._fetch_eonet_events("volcanoes", days, limit)

    def get_wildfires(self, days: int = 30, limit: int = 20) -> Dict[str, Any]:
        """NASA EONET 산불 이벤트."""
        return self._fetch_eonet_events("wildfires", days, limit)

    def get_floods(self, days: int = 30) -> Dict[str, Any]:
        """GDACS 홍수 이벤트."""
        try:
            url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
            params = {
                "eventtype": "FL",
                "fromDate": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),
                "toDate": datetime.now().strftime("%Y-%m-%d"),
                "alertlevel": "Green;Orange;Red",
            }
            # Try JSON first
            headers = {"Accept": "application/json"}
            resp = _session.get(url, params=params, headers=headers, timeout=20)

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    features = data.get("features", [])
                    records = []
                    for f in features:
                        props = f.get("properties", {})
                        coords = f.get("geometry", {}).get("coordinates", [])
                        records.append({
                            "event_id": props.get("eventid", ""),
                            "event_name": props.get("eventname", props.get("name", "")),
                            "alert_level": props.get("alertlevel", ""),
                            "country": props.get("country", ""),
                            "from_date": props.get("fromdate", ""),
                            "to_date": props.get("todate", ""),
                            "longitude": coords[0] if len(coords) > 0 else None,
                            "latitude": coords[1] if len(coords) > 1 else None,
                            "severity": props.get("severity", {}).get("severity_text", "") if isinstance(props.get("severity"), dict) else str(props.get("severity", "")),
                            "url": props.get("url", {}).get("report", "") if isinstance(props.get("url"), dict) else str(props.get("url", "")),
                        })
                    return success_response(
                        records,
                        source="USGS/EONET",
                        event_type="flood",
                        period_days=days,
                    )
                except (ValueError, KeyError):
                    pass

            # Fallback: parse XML
            resp_xml = _session.get(url, params=params, timeout=20)
            if resp_xml.status_code != 200:
                return error_response(f"GDACS API returned {resp_xml.status_code}")

            return self._parse_gdacs_xml(resp_xml.text, "flood", days)
        except Exception as e:
            return error_response(str(e))

    def _parse_gdacs_xml(self, xml_text: str, event_type: str, days: int) -> Dict[str, Any]:
        """GDACS XML 응답 파싱."""
        try:
            root = ET.fromstring(xml_text)
            ns = {
                "gdacs": "http://www.gdacs.org",
                "georss": "http://www.georss.org/georss",
            }
            records = []
            for item in root.iter("item"):
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")
                alert_level = item.findtext("gdacs:alertlevel", "", ns)
                country = item.findtext("gdacs:country", "", ns)
                point = item.findtext("georss:point", "", ns)
                lat, lon = None, None
                if point:
                    parts = point.strip().split()
                    if len(parts) == 2:
                        lat, lon = float(parts[0]), float(parts[1])
                records.append({
                    "title": title,
                    "alert_level": alert_level,
                    "country": country,
                    "pub_date": pub_date,
                    "latitude": lat,
                    "longitude": lon,
                    "url": link,
                })

            return success_response(
                records,
                source="USGS/EONET",
                event_type=event_type,
                period_days=days,
            )
        except ET.ParseError as e:
            return error_response(f"XML parse error: {str(e)}")

    def get_active_events(self) -> Dict[str, Any]:
        """GDACS 현재 활성 재난 이벤트."""
        try:
            url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
            params = {
                "fromDate": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                "toDate": datetime.now().strftime("%Y-%m-%d"),
                "alertlevel": "Green;Orange;Red",
            }
            headers = {"Accept": "application/json"}
            resp = _session.get(url, params=params, headers=headers, timeout=20)

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    features = data.get("features", [])
                    records = []
                    for f in features:
                        props = f.get("properties", {})
                        coords = f.get("geometry", {}).get("coordinates", [])
                        records.append({
                            "event_id": props.get("eventid", ""),
                            "event_type": props.get("eventtype", ""),
                            "event_name": props.get("eventname", props.get("name", "")),
                            "alert_level": props.get("alertlevel", ""),
                            "country": props.get("country", ""),
                            "from_date": props.get("fromdate", ""),
                            "to_date": props.get("todate", ""),
                            "longitude": coords[0] if len(coords) > 0 else None,
                            "latitude": coords[1] if len(coords) > 1 else None,
                        })
                    return success_response(
                        records,
                        source="USGS/EONET",
                        description="Active events in last 7 days",
                    )
                except (ValueError, KeyError):
                    pass

            # Fallback XML
            resp_xml = _session.get(url, params=params, timeout=20)
            if resp_xml.status_code != 200:
                return error_response(f"GDACS returned {resp_xml.status_code}")
            return self._parse_gdacs_xml(resp_xml.text, "all", 7)
        except Exception as e:
            return error_response(str(e))

    def get_disaster_summary(self, year: Optional[int] = None) -> Dict[str, Any]:
        """연간 재난 통계 요약 (USGS 지진 수 + EONET 이벤트 수)."""
        if year is None:
            year = datetime.now().year
        try:
            summary = {"year": year, "earthquakes": {}, "eonet_events": {}}

            # USGS earthquake count for the year
            start = f"{year}-01-01"
            end = min(f"{year}-12-31", datetime.now().strftime("%Y-%m-%d"))
            eq_url = "https://earthquake.usgs.gov/fdsnws/event/1/count"
            for min_mag, label in [(4.0, "mag4_plus"), (5.0, "mag5_plus"), (6.0, "mag6_plus"), (7.0, "mag7_plus")]:
                try:
                    resp = _session.get(eq_url, params={
                        "format": "text",
                        "starttime": start,
                        "endtime": end,
                        "minmagnitude": min_mag,
                    }, timeout=15)
                    if resp.status_code == 200:
                        summary["earthquakes"][label] = int(resp.text.strip())
                except Exception:
                    summary["earthquakes"][label] = None

            # EONET event counts by category
            for cat in ["wildfires", "volcanoes", "severeStorms", "floods"]:
                try:
                    days_in_year = (datetime.now() - datetime(year, 1, 1)).days
                    if days_in_year <= 0:
                        days_in_year = 365
                    resp = _session.get("https://eonet.gsfc.nasa.gov/api/v3/events", params={
                        "category": cat,
                        "days": min(days_in_year, 365),
                        "limit": 1,
                        "status": "all",
                    }, timeout=15)
                    if resp.status_code == 200:
                        data = resp.json()
                        # EONET doesn't give total count directly; use len of events
                        # Re-fetch with higher limit for count
                        resp2 = _session.get("https://eonet.gsfc.nasa.gov/api/v3/events", params={
                            "category": cat,
                            "days": min(days_in_year, 365),
                            "limit": 500,
                            "status": "all",
                        }, timeout=20)
                        if resp2.status_code == 200:
                            summary["eonet_events"][cat] = len(resp2.json().get("events", []))
                except Exception:
                    summary["eonet_events"][cat] = None

            return success_response(
                summary,
                source="USGS/EONET",
            )
        except Exception as e:
            return error_response(str(e))
