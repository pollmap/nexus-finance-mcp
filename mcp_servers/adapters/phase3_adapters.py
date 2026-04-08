"""
Phase 3 Adapters — Real Economy Infrastructure.
All free APIs, minimal or no authentication.

Covers: Maritime, Aviation, Energy, Agriculture, Trade, Politics, Patent.
"""
import logging
import os
import requests
from utils.http_client import get_session
from typing import Any, Dict
from datetime import datetime, timedelta
from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)
_session = get_session("phase3_adapters")


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
            resp = _session.get(url, params=params, timeout=15)
            data = (resp.json() if resp.status_code == 200 else {}).get("observations", [])
            records = [{"date": d["date"], "value": d["value"]} for d in data if d["value"] != "."]
            return success_response(records, source="FRED/DBDI")
        except Exception as e:
            logger.error(f"BDI proxy error: {e}")
            return error_response(f"BDI data retrieval failed: {e}")

    def get_port_stats(self) -> Dict[str, Any]:
        """Korean port statistics summary."""
        major_ports = [
            {"name": "부산항", "code": "KRPUS", "type": "container", "rank_global": 7},
            {"name": "인천항", "code": "KRINC", "type": "general", "rank_korea": 2},
            {"name": "울산항", "code": "KRUSN", "type": "oil/chemical", "rank_korea": 3},
            {"name": "광양항", "code": "KRKWN", "type": "container", "rank_korea": 4},
            {"name": "평택당진항", "code": "KRPTK", "type": "general/auto", "rank_korea": 5},
            {"name": "대산항", "code": "KRDAS", "type": "petrochemical", "rank_korea": 6},
            {"name": "마산항", "code": "KRMAS", "type": "general", "rank_korea": 7},
            {"name": "동해항", "code": "KRDHE", "type": "general/coal", "rank_korea": 8},
            {"name": "포항항", "code": "KRPOH", "type": "steel", "rank_korea": 9},
            {"name": "목포항", "code": "KRMOK", "type": "general", "rank_korea": 10},
            {"name": "군산항", "code": "KRKSN", "type": "general", "rank_korea": 11},
            {"name": "여수항", "code": "KRYOS", "type": "petrochemical", "rank_korea": 12},
        ]
        return success_response(
            major_ports,
            source="manual/reference",
            note="For live vessel tracking, use AISstream.io WebSocket (requires separate integration).",
        )

    def get_container_index(self) -> Dict[str, Any]:
        """Get Freightos Baltic Index (container shipping) from FRED."""
        try:
            url = "https://api.stlouisfed.org/fred/series/observations"
            api_key = os.getenv("FRED_API_KEY", "")
            params = {"series_id": "FBXIUS", "api_key": api_key, "file_type": "json",
                      "sort_order": "desc", "limit": 30}
            resp = _session.get(url, params=params, timeout=15)
            data = (resp.json() if resp.status_code == 200 else {}).get("observations", [])
            records = [{"date": d["date"], "value": d["value"]} for d in data if d["value"] != "."]
            return success_response(records, source="FRED/FBXIUS", index="Freightos Baltic Index (US)")
        except Exception as e:
            logger.error(f"Container index error: {e}")
            return error_response(f"Container index data retrieval failed: {e}")


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
            resp = _session.get(f"{self.BASE}/flights/departure", params={"airport": airport, "begin": begin, "end": end}, timeout=20)
            if resp.status_code == 200:
                flights = resp.json()
                return success_response(flights, source="OpenSky", airport=airport)
            return error_response(f"HTTP {resp.status_code}")
        except Exception as e:
            return error_response(str(e))

    def get_all_states(self, country: str = "") -> Dict[str, Any]:
        """Get all aircraft currently in the air."""
        try:
            params = {}
            if country:
                params["icao24"] = country
            resp = _session.get(f"{self.BASE}/states/all", params=params, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                states = data.get("states", [])
                aircraft = [{"icao24": s[0], "callsign": (s[1] or "").strip(), "country": s[2],
                            "longitude": s[5], "latitude": s[6], "altitude": s[7]}
                           for s in states if len(s) >= 8]
                return success_response(aircraft, source="OpenSky", total=data.get("time"))
            return error_response(f"HTTP {resp.status_code}")
        except Exception as e:
            return error_response(str(e))


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
            resp = _session.get(url, params=params, timeout=15)
            data = resp.json().get("response", {}).get("data", [])
            records = [{"date": d.get("period"), "price": d.get("value"), "unit": "$/barrel"} for d in data]
            return success_response(records, source="EIA", series="WTI Crude")
        except Exception as e:
            return error_response(str(e))

    def get_natural_gas_price(self, limit: int = 30) -> Dict[str, Any]:
        """Get Henry Hub natural gas spot price."""
        try:
            url = f"{self.BASE}/natural-gas/pri/fut/data/"
            params = {"api_key": self._api_key, "frequency": "daily", "data[0]": "value",
                      "sort[0][column]": "period", "sort[0][direction]": "desc", "length": limit}
            resp = _session.get(url, params=params, timeout=15)
            data = resp.json().get("response", {}).get("data", [])
            records = [{"date": d.get("period"), "price": d.get("value")} for d in data]
            return success_response(records, source="EIA", series="Natural Gas")
        except Exception as e:
            return error_response(str(e))

    # Allowed EIA API routes to prevent path traversal
    ALLOWED_EIA_ROUTES = {
        "petroleum/pri/spt", "natural-gas/pri/fut", "electricity/retail-sales",
        "international", "petroleum/stoc/wstk", "coal/production",
    }

    def get_eia_series(self, route: str, series_id: str = "", frequency: str = "monthly", limit: int = 30) -> Dict[str, Any]:
        """범용 EIA API v2 시계열 조회. route 예: petroleum/pri/spt, electricity/retail-sales."""
        if route not in self.ALLOWED_EIA_ROUTES:
            return error_response(f"Unknown EIA route. Allowed: {', '.join(sorted(self.ALLOWED_EIA_ROUTES))}")
        try:
            url = f"{self.BASE}/{route}/data/"
            params = {"api_key": self._api_key, "frequency": frequency, "data[0]": "value",
                      "sort[0][column]": "period", "sort[0][direction]": "desc", "length": limit}
            if series_id:
                params["facets[series][]"] = series_id
            resp = _session.get(url, params=params, timeout=15)
            data = resp.json().get("response", {}).get("data", [])
            records = [{"date": d.get("period"), "value": d.get("value"), "unit": d.get("units", "")} for d in data]
            return success_response(records, source="EIA", route=route)
        except Exception as e:
            return error_response(str(e))

    def get_electricity_data(self, limit: int = 30) -> Dict[str, Any]:
        """미국 전력 소매 판매 데이터."""
        return self.get_eia_series("electricity/retail-sales", frequency="monthly", limit=limit)

    def get_bunker_fuel_price(self) -> Dict[str, Any]:
        """벙커유(VLSFO) 가격 — FRED 시리즈 또는 EIA 잔사유 가격."""
        try:
            # Try FRED for residual fuel oil (closest proxy for bunker)
            api_key = os.getenv("FRED_API_KEY", "")
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {"series_id": "DHOILNYH", "api_key": api_key, "file_type": "json",
                      "sort_order": "desc", "limit": 30}
            resp = _session.get(url, params=params, timeout=15)
            data = (resp.json() if resp.status_code == 200 else {}).get("observations", [])
            records = [{"date": d["date"], "price": d["value"], "unit": "$/gallon"} for d in data if d["value"] != "."]
            if records:
                return success_response(records, source="FRED/DHOILNYH", series="NY Harbor No.2 Heating Oil (bunker proxy)")
            return success_response([], source="FRED/DHOILNYH", message="No bunker fuel data available")
        except Exception as e:
            return error_response(str(e))

    def get_opec_production(self) -> Dict[str, Any]:
        """OPEC 원유 생산량 — EIA 국제 데이터."""
        return self.get_eia_series("international", series_id="INTL.57-1-OPEC-TBPD.M", frequency="monthly", limit=120)


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
            resp = _session.get(self.BASE, params=params, timeout=10)
            data = resp.json()
            daily = data.get("daily", {})
            records = []
            dates = daily.get("time", [])
            for i, d in enumerate(dates):
                records.append({"date": d, "temp_max": daily.get("temperature_2m_max", [None])[i],
                    "temp_min": daily.get("temperature_2m_min", [None])[i],
                    "precip_mm": daily.get("precipitation_sum", [None])[i]})
            return success_response(records, source="Open-Meteo", location=f"{lat},{lon}")
        except Exception as e:
            return error_response(str(e))


# ============================================================
# AGRICULTURE — KAMIS (Korean Agricultural Market Info)
# ============================================================
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
                      "p_cert_key": api_key, "p_cert_id": os.getenv("KAMIS_CERT_ID", "luxon"), "p_returntype": "json"}
            resp = _session.get(url, params=params, timeout=15)
            data = resp.json()
            raw = data.get("data", {})
            if isinstance(raw, list):
                items = raw
            elif isinstance(raw, dict):
                items = raw.get("item", [])
            else:
                items = []
            return success_response(items, source="KAMIS")
        except Exception as e:
            return error_response(str(e))

    def get_fao_food_price_index(self) -> Dict[str, Any]:
        """FAO Food Price Index (public data)."""
        return success_response(
            None,
            source="FAO",
            note="FAO Food Price Index available at https://www.fao.org/worldfoodsituation/foodpricesindex/en/",
            api="Use FAOSTAT bulk download or sdmx1 for programmatic access.",
        )

    def get_fao_production(self, item_code: str = "0015", area_code: str = "410", limit: int = 20) -> Dict[str, Any]:
        """FAOSTAT 농업 생산 데이터. item_code: 0015=Wheat, 0027=Rice. area_code: 410=Korea."""
        try:
            url = "https://fenixservices.fao.org/faostat/api/v1/en/data/QCL"
            params = {"area": area_code, "item": item_code, "element": "5510",
                      "year": ",".join(str(y) for y in range(2015, 2026)),
                      "output_type": "objects", "limit": limit}
            resp = _session.get(url, params=params, timeout=20)
            data = resp.json().get("data", [])
            records = [{"year": d.get("Year"), "value": d.get("Value"), "unit": d.get("Unit"), "item": d.get("Item")} for d in data]
            return success_response(records, source="FAOSTAT/QCL")
        except Exception as e:
            return error_response(str(e))

    def get_fao_trade(self, item_code: str = "0015", area_code: str = "410", limit: int = 20) -> Dict[str, Any]:
        """FAOSTAT 농산물 무역 데이터."""
        try:
            url = "https://fenixservices.fao.org/faostat/api/v1/en/data/TCL"
            params = {"area": area_code, "item": item_code, "element": "5910",
                      "year": ",".join(str(y) for y in range(2015, 2026)),
                      "output_type": "objects", "limit": limit}
            resp = _session.get(url, params=params, timeout=20)
            data = resp.json().get("data", [])
            records = [{"year": d.get("Year"), "value": d.get("Value"), "unit": d.get("Unit"), "item": d.get("Item")} for d in data]
            return success_response(records, source="FAOSTAT/TCL")
        except Exception as e:
            return error_response(str(e))

    def get_usda_psd(self, commodity: str = "Rice, Milled", country: str = "Korea, South") -> Dict[str, Any]:
        """USDA FAS Production, Supply, and Distribution data."""
        try:
            url = "https://apps.fas.usda.gov/PSDOnline/api/CommodityData"
            params = {"commodityName": commodity, "countryName": country}
            resp = _session.get(url, params=params, timeout=20)
            if resp.status_code == 200:
                raw = resp.json()
                data = raw if isinstance(raw, list) else []
                return success_response(data, source="USDA/PSD", commodity=commodity, country=country)
            return error_response(f"HTTP {resp.status_code}")
        except Exception as e:
            return error_response(str(e))


# ============================================================
# TRADE — UN Comtrade
# ============================================================
class TradeAdapter:
    """International trade data — UN Comtrade."""
    BASE = "https://comtradeapi.un.org/public/v1/preview"

    def get_trade_data(self, reporter: str = "410", partner: str = "0",
                       flow: str = "X", hs_code: str = "TOTAL", period: str = "2023") -> Dict[str, Any]:
        """Get trade data. reporter 410=Korea, partner 0=World, flow X=Export/M=Import."""
        try:
            url = f"{self.BASE}/C/A/HS"
            params = {"reporterCode": reporter, "partnerCode": partner, "flowCode": flow,
                      "cmdCode": hs_code, "period": period}
            resp = _session.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                data = result.get("data", [])
                records = []
                for r in data:
                    records.append({
                        "period": r.get("period"),
                        "reporter": r.get("reporterCode"),
                        "partner": r.get("partnerCode"),
                        "flow": r.get("flowCode"),
                        "commodity": r.get("cmdCode"),
                        "trade_value": r.get("primaryValue"),
                        "net_weight_kg": r.get("netWgt"),
                    })
                return success_response(records, source="UN Comtrade")
            return error_response(f"HTTP {resp.status_code}")
        except Exception as e:
            return error_response(str(e))


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
            resp = _session.get(url, params=params, timeout=15)
            data = resp.json()
            rows = data.get("TVBPMBILL11", [{}])
            if len(rows) > 1:
                items = rows[1].get("row", [])
                return success_response(items[:limit], source="National Assembly", count=len(items))
            return success_response([], source="National Assembly", message="No data")
        except Exception as e:
            return error_response(str(e))


# ============================================================
# PATENT — KIPRIS (Korean IP)
# ============================================================
class PatentAdapter:
    """Korean patent search — KIPRIS."""

    def search_patents(self, keyword: str, limit: int = 10) -> Dict[str, Any]:
        """Search Korean patents via KIPRIS open API."""
        try:
            api_key = os.getenv("KIPRIS_API_KEY", os.getenv("DATA_GO_KR_API_KEY", ""))
            url = "https://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getAdvancedSearch"
            params = {"ServiceKey": api_key, "word": keyword, "numOfRows": limit, "pageNo": 1}
            resp = _session.get(url, params=params, timeout=15)
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
                return success_response(items, source="KIPRIS", query=keyword)
            return success_response([], source="KIPRIS", message="Unexpected response format")
        except Exception as e:
            return error_response(str(e))
