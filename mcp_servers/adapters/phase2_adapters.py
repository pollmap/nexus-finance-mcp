"""
Phase 2 Additional Adapters:
- CryptoCompare: Historical crypto OHLCV (100K calls/month free)
- Finnhub: US stock quotes + economic calendar (60 req/min free)
- MOLIT: Korean real estate transaction prices (via PublicDataReader)
- FSC: Korean financial data from data.go.kr (10K calls/day)
"""
import logging
import os
import requests
from utils.http_client import get_session
from datetime import datetime
from typing import Any, Dict
from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)
_session = get_session("phase2_adapters")


class CryptoCompareAdapter:
    """CryptoCompare — deep historical crypto data."""
    BASE = "https://min-api.cryptocompare.com/data/v2"

    def __init__(self):
        self._api_key = os.getenv("CRYPTOCOMPARE_API_KEY", "")

    def _headers(self):
        h = {}
        if self._api_key:
            h["authorization"] = f"Apikey {self._api_key}"
        return h

    def get_daily_ohlcv(self, fsym: str = "BTC", tsym: str = "USD", limit: int = 100) -> Dict[str, Any]:
        try:
            resp = _session.get(f"{self.BASE}/histoday", headers=self._headers(),
                params={"fsym": fsym, "tsym": tsym, "limit": limit}, timeout=15)
            resp.raise_for_status()
            data = resp.json().get("Data", {}).get("Data", [])
            records = [{"time": d["time"], "open": d["open"], "high": d["high"],
                        "low": d["low"], "close": d["close"], "volume": d["volumefrom"]} for d in data]
            return success_response(records, source="CryptoCompare", pair=f"{fsym}/{tsym}")
        except Exception as e:
            return error_response(str(e))

    def get_hourly_ohlcv(self, fsym: str = "BTC", tsym: str = "USD", limit: int = 100) -> Dict[str, Any]:
        try:
            resp = _session.get(f"{self.BASE}/histohour", headers=self._headers(),
                params={"fsym": fsym, "tsym": tsym, "limit": limit}, timeout=15)
            resp.raise_for_status()
            data = resp.json().get("Data", {}).get("Data", [])
            records = [{"time": d["time"], "open": d["open"], "high": d["high"],
                        "low": d["low"], "close": d["close"], "volume": d["volumefrom"]} for d in data]
            return success_response(records, source="CryptoCompare", pair=f"{fsym}/{tsym}")
        except Exception as e:
            return error_response(str(e))

    def get_top_coins(self, tsym: str = "USD", limit: int = 20) -> Dict[str, Any]:
        try:
            resp = _session.get("https://min-api.cryptocompare.com/data/top/mktcapfull",
                headers=self._headers(), params={"tsym": tsym, "limit": limit}, timeout=15)
            coins = []
            for d in resp.json().get("Data", []):
                info = d.get("CoinInfo", {})
                raw = d.get("RAW", {}).get(tsym, {})
                coins.append({"symbol": info.get("Name"), "name": info.get("FullName"),
                    "price": raw.get("PRICE"), "market_cap": raw.get("MKTCAP"),
                    "change_24h": raw.get("CHANGEPCT24HOUR")})
            return success_response(coins, source="CryptoCompare")
        except Exception as e:
            return error_response(str(e))


class FinnhubAdapter:
    """Finnhub — US stock data + economic calendar."""
    BASE = "https://finnhub.io/api/v1"

    def __init__(self):
        self._api_key = os.getenv("FINNHUB_API_KEY", "")

    def _params(self, **kwargs):
        kwargs["token"] = self._api_key
        return kwargs

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        if not self._api_key:
            return error_response("FINNHUB_API_KEY not set")
        try:
            resp = _session.get(f"{self.BASE}/quote", params=self._params(symbol=symbol), timeout=10)
            d = resp.json()
            return success_response(None, source="Finnhub", symbol=symbol, current=d.get("c"),
                    change=d.get("d"), change_pct=d.get("dp"), high=d.get("h"),
                    low=d.get("l"), open=d.get("o"), prev_close=d.get("pc"))
        except Exception as e:
            return error_response(str(e))

    def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        if not self._api_key:
            return error_response("FINNHUB_API_KEY not set")
        try:
            resp = _session.get(f"{self.BASE}/stock/profile2", params=self._params(symbol=symbol), timeout=10)
            return success_response(resp.json(), source="Finnhub")
        except Exception as e:
            return error_response(str(e))

    def get_economic_calendar(self) -> Dict[str, Any]:
        if not self._api_key:
            return error_response("FINNHUB_API_KEY not set")
        try:
            resp = _session.get(f"{self.BASE}/calendar/economic", params=self._params(), timeout=10)
            events = resp.json().get("economicCalendar", [])[:30]
            return success_response(events, source="Finnhub", count=len(events))
        except Exception as e:
            return error_response(str(e))

    def get_market_news(self, category: str = "general") -> Dict[str, Any]:
        if not self._api_key:
            return error_response("FINNHUB_API_KEY not set")
        try:
            resp = _session.get(f"{self.BASE}/news", params=self._params(category=category), timeout=10)
            news = [{"headline": n.get("headline"), "source": n.get("source"),
                     "url": n.get("url"), "datetime": n.get("datetime")} for n in resp.json()[:20]]
            return success_response(news, source="Finnhub")
        except Exception as e:
            return error_response(str(e))


class MOLITAdapter:
    """MOLIT 실거래가 via PublicDataReader."""

    def get_apt_trades(self, sigungu_code: str = "11110", year_month: str = "") -> Dict[str, Any]:
        try:
            from PublicDataReader import TransactionPrice
            api_key = os.getenv("MOLIT_API_KEY", os.getenv("DATA_GO_KR_API_KEY", ""))
            if not api_key:
                return error_response("data.go.kr API key not set")
            tp = TransactionPrice(api_key)
            if not year_month:
                year_month = datetime.now().strftime("%Y%m")
            df = tp.get_data(property_type="아파트", trade_type="매매",
                           sigungu_code=sigungu_code, year_month=year_month)
            if df is None or df.empty:
                return success_response([], source="MOLIT", message="No data")
            records = df.head(30).to_dict("records")
            return success_response(records, source="MOLIT", sigungu=sigungu_code, period=year_month)
        except ImportError:
            return error_response("PublicDataReader not installed")
        except Exception as e:
            return error_response(str(e))


class FSCAdapter:
    """FSC data.go.kr — Korean financial regulatory data."""
    BASE = "https://apis.data.go.kr/1160100/service"

    def __init__(self):
        self._api_key = os.getenv("MOLIT_API_KEY", os.getenv("DATA_GO_KR_API_KEY", ""))

    def get_stock_price(self, stock_code: str = "005930", num_of_rows: int = 20) -> Dict[str, Any]:
        try:
            url = f"{self.BASE}/GetStockSecuritiesInfoService/getStockPriceInfo"
            params = {"serviceKey": self._api_key, "resultType": "json",
                      "likeSrtnCd": stock_code, "numOfRows": num_of_rows}
            resp = _session.get(url, params=params, timeout=15)
            data = resp.json()
            items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
            return success_response(items[:num_of_rows], source="FSC", stock_code=stock_code)
        except Exception as e:
            return error_response(str(e))

    def get_bond_price(self, num_of_rows: int = 20) -> Dict[str, Any]:
        try:
            url = f"{self.BASE}/GetBondIssuInfoService/getBondPriceInfo"
            params = {"serviceKey": self._api_key, "resultType": "json", "numOfRows": num_of_rows}
            resp = _session.get(url, params=params, timeout=15)
            data = resp.json()
            items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
            return success_response(items, source="FSC")
        except Exception as e:
            return error_response(str(e))
