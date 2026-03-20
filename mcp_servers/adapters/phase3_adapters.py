"""
Phase 3 Adapters — Real Economy Infrastructure.
All free APIs, minimal or no authentication.

Covers: Maritime, Aviation, Energy, Agriculture, Trade, Politics, Patent.
"""
import logging
import os
import requests
from typing import Any, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ============================================================
# MARITIME — Baltic Dry Index + Vessel data
# ============================================================
class MaritimeAdapter:
    """Maritime/shipping data — free sources."""

    def get_bdi_proxy(self) -> Dict[str, Any]:
        """Get Baltic Dry Index proxy from public sources."""
        try:
            url = "https://api.stlouisfed.org/fred/series/observations"
            api_key = os.getenv("FRED_API_KEY", "")
            params = {"series_id": "DBDI", "api_key": api_key, "file_type": "json",
                      "sort_order": "desc", "limit": 30}
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json().get("observations", [])
            records = [{"date": d["date"], "value": d["value"]} for d in data if d["value"] != "."]
            return {"success": True, "source": "FRED/DBDI", "count": len(records), "data": records}
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_port_stats(self) -> Dict[str, Any]:
        """Korean port statistics summary."""
        return {
            "success": True,
            "source": "manual/reference",
            "major_ports": [
                {"name": "부산항", "code": "KRPUS", "type": "container", "rank_global": 7},
                {"name": "인천항", "code": "KRINC", "type": "general", "rank_korea": 2},
                {"name": "울산항", "code": "KRUSN", "type": "oil/chemical", "rank_korea": 3},
                {"name": "광양항", "code": "KRKWN", "type": "container", "rank_korea": 4},
            ],
            "note": "For live vessel tracking, use AISstream.io WebSocket (requires separate integration).",
        }

    def get_container_index(self) -> Dict[str, Any]:
        """Get Freightos Baltic Index (container shipping) from FRED."""
        try:
            url = "https://api.stlouisfed.org/fred/series/observations"
            api_key = os.getenv("FRED_API_KEY", "")
            params = {"series_id": "FBXIUS", "api_key": api_key, "file_type": "json",
                      "sort_order": "desc", "limit": 30}
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json().get("observations", [])
            records = [{"date": d["date"], "value": d["value"]} for d in data if d["value"] != "."]
            return {"success": True, "source": "FRED/FBXIUS", "index": "Freightos Baltic Index (US)", "count": len(records), "data": records}
        except Exception as e:
            return {"error": True, "message": str(e)}


# ============================================================
# AVIATION — OpenSky Network
# ============================================================
class AviationAdapter:
    """Aviation data — OpenSky Network (free, 4K/day)."""
    BASE = "https://opensky-network.org/api"

    def get_flights_by_airport(self, airport: str = "RKSI", hours: int = 12) -> Dict[str, Any]:
        """Get recent departures from airport (ICAO code)."""
        try:
            end = int(datetime.now().timestamp())
            begin = end - (hours * 3600)
            resp = requests.get(f"{self.BASE}/flights/departure", params={"airport": airport, "begin": begin, "end": end}, timeout=20)
            if resp.status_code == 200:
                flights = resp.json()[:30]
                return {"success": True, "airport": airport, "count": len(flights), "flights": flights}
            return {"error": True, "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_all_states(self, country: str = "") -> Dict[str, Any]:
        """Get all aircraft currently in the air."""
        try:
            params = {}
            if country:
                params["icao24"] = country
            resp = requests.get(f"{self.BASE}/states/all", params=params, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                states = data.get("states", [])[:50]
                aircraft = [{"icao24": s[0], "callsign": (s[1] or "").strip(), "country": s[2],
                            "longitude": s[5], "latitude": s[6], "altitude": s[7]} for s in states]
                return {"success": True, "total": data.get("time"), "count": len(aircraft), "aircraft": aircraft}
            return {"error": True, "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"error": True, "message": str(e)}


# ============================================================
# ENERGY — EIA (US Energy Information Administration)
# ============================================================
class EnergyAdapter:
    """US EIA API v2 — crude oil, natural gas, electricity."""
    BASE = "https://api.eia.gov/v2"

    def __init__(self):
        self._api_key = os.getenv("EIA_API_KEY", "")

    def get_crude_oil_price(self, limit: int = 30) -> Dict[str, Any]:
        """Get WTI crude oil spot price."""
        try:
            url = f"{self.BASE}/petroleum/pri/spt/data/"
            params = {"api_key": self._api_key, "frequency": "daily", "data[0]": "value",
                      "facets[series][]": "RWTC", "sort[0][column]": "period",
                      "sort[0][direction]": "desc", "length": limit}
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json().get("response", {}).get("data", [])
            records = [{"date": d.get("period"), "price": d.get("value"), "unit": "$/barrel"} for d in data]
            return {"success": True, "source": "EIA", "series": "WTI Crude", "count": len(records), "data": records}
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_natural_gas_price(self, limit: int = 30) -> Dict[str, Any]:
        """Get Henry Hub natural gas spot price."""
        try:
            url = f"{self.BASE}/natural-gas/pri/fut/data/"
            params = {"api_key": self._api_key, "frequency": "daily", "data[0]": "value",
                      "sort[0][column]": "period", "sort[0][direction]": "desc", "length": limit}
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json().get("response", {}).get("data", [])
            records = [{"date": d.get("period"), "price": d.get("value")} for d in data]
            return {"success": True, "source": "EIA", "series": "Natural Gas", "count": len(records), "data": records}
        except Exception as e:
            return {"error": True, "message": str(e)}


# ============================================================
# WEATHER — Open-Meteo (completely free, no key)
# ============================================================
class WeatherAdapter:
    """Open-Meteo — weather data (10K/day, no key)."""
    BASE = "https://api.open-meteo.com/v1/forecast"

    def get_forecast(self, lat: float = 37.5665, lon: float = 126.978, days: int = 7) -> Dict[str, Any]:
        """Get weather forecast. Default: Seoul."""
        try:
            params = {"latitude": lat, "longitude": lon, "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                      "timezone": "Asia/Seoul", "forecast_days": days}
            resp = requests.get(self.BASE, params=params, timeout=10)
            data = resp.json()
            daily = data.get("daily", {})
            records = []
            dates = daily.get("time", [])
            for i, d in enumerate(dates):
                records.append({"date": d, "temp_max": daily.get("temperature_2m_max", [None])[i],
                    "temp_min": daily.get("temperature_2m_min", [None])[i],
                    "precip_mm": daily.get("precipitation_sum", [None])[i]})
            return {"success": True, "source": "Open-Meteo", "location": f"{lat},{lon}", "data": records}
        except Exception as e:
            return {"error": True, "message": str(e)}


# ============================================================
# AGRICULTURE — KAMIS (Korean Agricultural Market Info)
# ================================================= ===========
class AgricultureAdapter:
    """Korean agricultural prices — KAMIS + FAO."""

    def get_kamis_prices(self, product_cls_code: str = "100", country_code: str = "1101") -> Dict[str, Any]:
        """KAMIS agricultural product prices."""
        try:
            api_key = os.getenv("KAMIS_API_KEY", os.getenv("DATA_GO_KR_API_KEY", ""))
            url = "https://www.kamis.or.kr/service/price/xml.do"
            today = datetime.now().strftime("%Y-%m-%d")
            params = {"action": "periodProductList", "p_productclscode": product_cls_code,
                      "p_regday": today, "p_countrycode": country_code,
                      "p_cert_key": api_key, "p_cert_id": "luxon", "p_returntype": "json"}
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()
            items = data.get("data", {}).get("item", [])[:20]
            return {"success": True, "source": "KAMIS", "count": len(items), "data": items}
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_fao_food_price_index(self) -> Dict[str, Any]:
        """FAO Food Price Index (public data)."""
        return {
            "success": True,
            "source": "FAO",
            "note": "FAO Food Price Index available at https://www.fao.org/worldfoodsituation/foodpricesindex/en/",
            "api": "Use FAOSTAT bulk download or sdmx1 for programmatic access.",
        }


# ============================================================
# TRADE — UN Comtrade
# ============================================================
class TradeAdapter:
    """International trade data — UN Comtrade."""
    BASE = "https://comtradeapi.un.org/public/v1/preview"

    def get_trade_data(self, reporter: str = "410", partner: str = "0",
                       flow: str = "X", hs_code: str = "TOTAL", period: str = "2024") -> Dict[str, Any]:
        """Get trade data. reporter 410=Korea, partner 0=World, flow X=Export/M=Import."""
        try:
            params = {"reporterCode": reporter, "partnerCode": partner, "flowCode": flow,
                      "cmdCode": hs_code, "period": period, "maxRecords": 20}
            resp = requests.get(self.BASE + "/getTarifflineData", params=params, timeout=20)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                return {"success": True, "source": "UN Comtrade", "count": len(data), "data": data[:20]}
            return {"error": True, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"error": True, "message": str(e)}


# ============================================================
# POLITICS — Korean National Assembly
# ============================================================
class PoliticsAdapter:
    """Korean National Assembly open data."""
    BASE = "https://open.assembly.go.kr/portal/openapi"

    def get_bills(self, age: str = "22", limit: int = 20) -> Dict[str, Any]:
        """Get recent bills from Korean National Assembly."""
        try:
            api_key = os.getenv("ASSEMBLY_API_KEY", os.getenv("DATA_GO_KR_API_KEY", ""))
            url = f"{self.BASE}/TVBPMBILL11"
            params = {"Key": api_key, "Type": "json", "pSize": limit, "AGE": age}
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()
            rows = data.get("TVBPMBILL11", [{}])
            if len(rows) > 1:
                items = rows[1].get("row", [])
                return {"success": True, "source": "National Assembly", "count": len(items), "bills": items[:limit]}
            return {"success": True, "data": [], "message": "No data"}
        except Exception as e:
            return {"error": True, "message": str(e)}


# ============================================================
# PATENT — KIPRIS (Korean IP)
# ============================================================
class PatentAdapter:
    """Korean patent search — KIPRIS."""

    def search_patents(self, keyword: str, limit: int = 10) -> Dict[str, Any]:
        """Search Korean patents via KIPRIS open API."""
        try:
            api_key = os.getenv("KIPRIS_API_KEY", os.getenv("DATA_GO_KR_API_KEY", ""))
            url = "http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getAdvancedSearch"
            params = {"ServiceKey": api_key, "word": keyword, "numOfRows": limit, "pageNo": 1}
            resp = requests.get(url, params=params, timeout=15)
            if "xml" in resp.headers.get("content-type", ""):
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.text)
                items = []
                for item in root.findall(".//item")[:limit]:
                    items.append({
                        "title": item.findtext("inventionTitle", ""),
                        "applicant": item.findtext("applicantName", ""),
                        "date": item.findtext("applicationDate", ""),
                        "number": item.findtext("applicationNumber", ""),
                    })
                return {"success": True, "source": "KIPRIS", "query": keyword, "count": len(items), "patents": items}
            return {"success": True, "data": [], "message": "Unexpected response format"}
        except Exception as e:
            return {"error": True, "message": str(e)}
