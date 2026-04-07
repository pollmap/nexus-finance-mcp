"""
Historical Data Adapter - 150+ Years of Financial Data.

Provides ultra-long-term financial and economic datasets:
- Shiller S&P 500 + CAPE ratio (1871-present)
- Fama-French factor data (1926-present)
- NBER business cycle dates (1854-present)
- FRED century-scale series (1900+)
- Gold & Oil long-term prices
- Cross-century crisis comparison

Run standalone test: python -m mcp_servers.adapters.historical_data_adapter
"""
import io
import json
import logging
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.core.cache_manager import CacheManager, get_cache
from mcp_servers.core.rate_limiter import RateLimiter, get_limiter
from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)

# Cache directory for downloaded files
CACHE_DIR = PROJECT_ROOT / ".cache" / "historical"

# Hardcoded NBER business cycle dates (1854-2024, 34 cycles)
# Source: https://www.nber.org/research/data/us-business-cycle-expansions-and-contractions
NBER_CYCLES_BACKUP = [
    {"peak": "1854-12-01", "trough": "1855-12-01"},
    {"peak": "1857-06-01", "trough": "1858-12-01"},
    {"peak": "1860-10-01", "trough": "1861-06-01"},
    {"peak": "1865-04-01", "trough": "1867-12-01"},
    {"peak": "1869-06-01", "trough": "1870-12-01"},
    {"peak": "1873-10-01", "trough": "1879-03-01"},
    {"peak": "1882-03-01", "trough": "1885-05-01"},
    {"peak": "1887-03-01", "trough": "1888-04-01"},
    {"peak": "1890-07-01", "trough": "1891-05-01"},
    {"peak": "1893-01-01", "trough": "1894-06-01"},
    {"peak": "1895-12-01", "trough": "1897-06-01"},
    {"peak": "1899-06-01", "trough": "1900-12-01"},
    {"peak": "1902-09-01", "trough": "1904-08-01"},
    {"peak": "1907-05-01", "trough": "1908-06-01"},
    {"peak": "1910-01-01", "trough": "1912-01-01"},
    {"peak": "1913-01-01", "trough": "1914-12-01"},
    {"peak": "1918-08-01", "trough": "1919-03-01"},
    {"peak": "1920-01-01", "trough": "1921-07-01"},
    {"peak": "1923-05-01", "trough": "1924-07-01"},
    {"peak": "1926-10-01", "trough": "1927-11-01"},
    {"peak": "1929-08-01", "trough": "1933-03-01"},
    {"peak": "1937-05-01", "trough": "1938-06-01"},
    {"peak": "1945-02-01", "trough": "1945-10-01"},
    {"peak": "1948-11-01", "trough": "1949-10-01"},
    {"peak": "1953-07-01", "trough": "1954-05-01"},
    {"peak": "1957-08-01", "trough": "1958-04-01"},
    {"peak": "1960-04-01", "trough": "1961-02-01"},
    {"peak": "1969-12-01", "trough": "1970-11-01"},
    {"peak": "1973-11-01", "trough": "1975-03-01"},
    {"peak": "1980-01-01", "trough": "1980-07-01"},
    {"peak": "1981-07-01", "trough": "1982-11-01"},
    {"peak": "1990-07-01", "trough": "1991-03-01"},
    {"peak": "2001-03-01", "trough": "2001-11-01"},
    {"peak": "2007-12-01", "trough": "2009-06-01"},
    {"peak": "2020-02-01", "trough": "2020-04-01"},
]


class HistoricalDataAdapter:
    """
    Adapter for ultra-long-term financial and economic data.

    Provides 150+ years of financial history from multiple authoritative sources:
    Shiller, Fama-French, NBER, FRED, and market data via yfinance.
    """

    SHILLER_CSV_URL = "https://datahub.io/core/s-and-p-500/r/data.csv"
    FRENCH_BASE_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp"
    FRENCH_DATASETS = {
        "5_factors": "F-F_Research_Data_5_Factors_2x3_CSV.zip",
        "3_factors": "F-F_Research_Data_Factors_CSV.zip",
        "momentum": "F-F_Momentum_Factor_CSV.zip",
    }
    NBER_JSON_URL = "https://data.nber.org/data/cycles/business_cycle_dates.json"
    FRED_BASE_URL = "https://api.stlouisfed.org/fred"

    def __init__(
        self,
        fred_api_key: str = None,
        cache: CacheManager = None,
        limiter: RateLimiter = None,
    ):
        self.fred_api_key = fred_api_key or os.getenv("FRED_API_KEY", "")
        self._cache = cache or get_cache()
        self._limiter = limiter or get_limiter()
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "NexusFinance/4.0"})

        # Ensure cache directory exists
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        if not self.fred_api_key:
            logger.warning("FRED_API_KEY not set. FRED-based queries will fail.")

        logger.info("HistoricalData adapter initialized")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _download_file(self, url: str, cache_name: str, max_age_hours: int = 24) -> Optional[bytes]:
        """Download a file with local disk caching."""
        cache_path = CACHE_DIR / cache_name
        # Use cached file if fresh enough
        if cache_path.exists():
            age_hours = (datetime.now().timestamp() - cache_path.stat().st_mtime) / 3600
            if age_hours < max_age_hours:
                logger.debug(f"Using cached {cache_name} (age={age_hours:.1f}h)")
                return cache_path.read_bytes()

        try:
            resp = self._session.get(url, timeout=60)
            resp.raise_for_status()
            cache_path.write_bytes(resp.content)
            logger.info(f"Downloaded {cache_name} ({len(resp.content)} bytes)")
            return resp.content
        except requests.RequestException as e:
            logger.warning(f"Download failed for {url}: {e}")
            # Fall back to stale cache if available
            if cache_path.exists():
                logger.info(f"Falling back to stale cache for {cache_name}")
                return cache_path.read_bytes()
            return None

    def _fred_request(self, series_id: str, start: str = "1900-01-01") -> List[Dict]:
        """Fetch a FRED series with maximum history."""
        if not self.fred_api_key:
            return []

        self._limiter.acquire("fred")

        try:
            resp = self._session.get(
                f"{self.FRED_BASE_URL}/series/observations",
                params={
                    "series_id": series_id,
                    "api_key": self.fred_api_key,
                    "file_type": "json",
                    "observation_start": start,
                    "sort_order": "asc",
                },
                timeout=30,
            )
            resp.raise_for_status()
            observations = resp.json().get("observations", [])
            data = []
            for obs in observations:
                try:
                    val = float(obs["value"]) if obs["value"] != "." else None
                    if val is not None:
                        data.append({"date": obs["date"], "value": val})
                except (ValueError, KeyError):
                    continue
            return data
        except requests.RequestException as e:
            logger.error(f"FRED request failed for {series_id}: {e}")
            return []

    # ------------------------------------------------------------------
    # 1. Shiller S&P 500 + CAPE
    # ------------------------------------------------------------------

    def get_shiller_data(
        self, start_year: int = 1871, end_year: int = None
    ) -> Dict[str, Any]:
        """
        Shiller S&P 500 장기 데이터 (1871~현재).

        DataHub CSV를 우선 사용하고, 실패 시 FRED SP500 시리즈로 폴백.
        Returns: {date, sp500_price, dividend_yield, earnings, cape_ratio, cpi, long_rate}
        """
        end_year = end_year or datetime.now().year

        # Memory cache
        cache_key = {"method": "shiller", "start": start_year, "end": end_year}
        cached = self._cache.get("historical", cache_key)
        if cached:
            return cached

        data = []
        source = "datahub"

        try:
            import pandas as pd

            raw = self._download_file(self.SHILLER_CSV_URL, "shiller_sp500.csv", max_age_hours=168)
            if raw:
                df = pd.read_csv(io.BytesIO(raw))
                # DataHub CSV columns: Date, SP500, Dividend, Earnings, Consumer Price Index,
                # Long Interest Rate, Real Price, Real Dividend, Real Earnings, PE10 (CAPE)
                col_map = {}
                for col in df.columns:
                    cl = col.strip().lower()
                    if cl == "date":
                        col_map["date"] = col
                    elif cl == "sp500" or cl == "sp_500" or "sp500" in cl.replace(" ", "").lower():
                        col_map["sp500"] = col
                    elif "dividend" in cl and "real" not in cl and "yield" not in cl:
                        col_map["dividend"] = col
                    elif "earning" in cl and "real" not in cl:
                        col_map["earnings"] = col
                    elif "consumer" in cl or "cpi" in cl:
                        col_map["cpi"] = col
                    elif "long" in cl and ("interest" in cl or "rate" in cl):
                        col_map["long_rate"] = col
                    elif cl in ("pe10", "cape"):
                        col_map["cape"] = col

                if "date" in col_map and "sp500" in col_map:
                    for _, row in df.iterrows():
                        try:
                            date_val = str(row[col_map["date"]])
                            # Parse various date formats
                            year = None
                            if len(date_val) == 4:
                                year = int(date_val)
                                date_str = f"{year}-01-01"
                            elif "-" in date_val:
                                date_str = date_val[:10]
                                year = int(date_str[:4])
                            elif "." in date_val:
                                parts = date_val.split(".")
                                year = int(parts[0])
                                month = int(parts[1]) if len(parts) > 1 else 1
                                date_str = f"{year}-{month:02d}-01"
                            else:
                                continue

                            if year and (year < start_year or year > end_year):
                                continue

                            price = float(row[col_map["sp500"]]) if col_map.get("sp500") else None
                            if price is None or price != price:  # NaN check
                                continue

                            entry = {"date": date_str, "sp500_price": round(price, 2)}
                            if "dividend" in col_map:
                                try:
                                    entry["dividend"] = round(float(row[col_map["dividend"]]), 4)
                                except (ValueError, TypeError):
                                    pass
                            if "earnings" in col_map:
                                try:
                                    entry["earnings"] = round(float(row[col_map["earnings"]]), 4)
                                except (ValueError, TypeError):
                                    pass
                            if "cpi" in col_map:
                                try:
                                    entry["cpi"] = round(float(row[col_map["cpi"]]), 2)
                                except (ValueError, TypeError):
                                    pass
                            if "long_rate" in col_map:
                                try:
                                    entry["long_rate"] = round(float(row[col_map["long_rate"]]), 2)
                                except (ValueError, TypeError):
                                    pass
                            if "cape" in col_map:
                                try:
                                    entry["cape_ratio"] = round(float(row[col_map["cape"]]), 2)
                                except (ValueError, TypeError):
                                    pass
                            # Compute dividend yield if possible
                            if "dividend" in entry and price > 0:
                                entry["dividend_yield"] = round(entry["dividend"] / price * 100, 2)

                            data.append(entry)
                        except (ValueError, TypeError, KeyError):
                            continue
                else:
                    logger.warning("Shiller CSV missing expected columns, falling back to FRED")
        except ImportError:
            logger.warning("pandas not available, falling back to FRED for Shiller data")

        # Fallback: use FRED SP500 series
        if not data:
            source = "fred_fallback"
            fred_data = self._fred_request("SP500", f"{start_year}-01-01")
            for item in fred_data:
                yr = int(item["date"][:4])
                if yr < start_year or yr > end_year:
                    continue
                data.append({"date": item["date"], "sp500_price": round(item["value"], 2)})

        result = success_response(
            data,
            source=source,
            description="Shiller S&P 500 long-term data",
            period=f"{start_year}-{end_year}",
        )

        self._cache.set("historical", cache_key, result, "daily_data")
        return result

    # ------------------------------------------------------------------
    # 2. Fama-French Factors
    # ------------------------------------------------------------------

    def get_french_factors(
        self, dataset: str = "5_factors", frequency: str = "monthly"
    ) -> Dict[str, Any]:
        """
        Fama-French 팩터 데이터 (1926~현재, 학술 금융의 gold standard).

        dataset: '5_factors', '3_factors', 'momentum'
        frequency: 'monthly' or 'annual'
        Returns: {date, mkt_rf, smb, hml, [rmw, cma], rf}
        """
        cache_key = {"method": "french", "dataset": dataset, "freq": frequency}
        cached = self._cache.get("historical", cache_key)
        if cached:
            return cached

        zip_name = self.FRENCH_DATASETS.get(dataset)
        if not zip_name:
            return error_response(f"Unknown dataset: {dataset}. Use: {list(self.FRENCH_DATASETS.keys())}")

        url = f"{self.FRENCH_BASE_URL}/{zip_name}"
        raw = self._download_file(url, f"french_{dataset}.zip", max_age_hours=168)
        if not raw:
            return error_response(f"Failed to download French {dataset} data")

        data = []
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                csv_names = [n for n in zf.namelist() if n.endswith(".CSV") or n.endswith(".csv")]
                if not csv_names:
                    return error_response("No CSV found in zip")

                content = zf.read(csv_names[0]).decode("utf-8", errors="replace")
                lines = content.split("\n")

                # Find the header line (contains "Mkt-RF" or similar)
                header_idx = None
                for i, line in enumerate(lines):
                    if "mkt-rf" in line.lower() or "mkt_rf" in line.lower():
                        header_idx = i
                        break

                if header_idx is None:
                    return error_response("Could not find header in French data")

                headers = [h.strip().lower().replace("-", "_") for h in lines[header_idx].split(",")]

                # Parse monthly section (ends at blank line or "Annual" section)
                is_annual = frequency.lower().startswith("a")
                in_target_section = not is_annual  # Start in monthly if monthly
                found_annual = False

                for line in lines[header_idx + 1:]:
                    stripped = line.strip()
                    if not stripped:
                        if not is_annual:
                            break  # End of monthly section
                        in_target_section = False
                        continue

                    # Detect annual section header
                    if "annual" in stripped.lower():
                        found_annual = True
                        # Next data line starts annual
                        in_target_section = is_annual
                        continue

                    if is_annual and not in_target_section:
                        continue

                    parts = [p.strip() for p in stripped.split(",")]
                    if len(parts) < 2:
                        continue

                    date_str = parts[0].strip()
                    # Validate date format: YYYYMM or YYYY
                    if not date_str.isdigit():
                        continue
                    if len(date_str) == 6:
                        year, month = int(date_str[:4]), int(date_str[4:6])
                        if year < 1900 or month < 1 or month > 12:
                            continue
                        iso_date = f"{year}-{month:02d}-01"
                    elif len(date_str) == 4:
                        year = int(date_str)
                        if year < 1900:
                            continue
                        iso_date = f"{year}-01-01"
                    else:
                        continue

                    entry = {"date": iso_date}
                    for j, hdr in enumerate(headers[1:], 1):
                        if j < len(parts):
                            try:
                                val = float(parts[j])
                                entry[hdr] = round(val, 4)
                            except ValueError:
                                pass

                    if len(entry) > 1:
                        data.append(entry)

        except (zipfile.BadZipFile, Exception) as e:
            logger.error(f"Error parsing French data: {e}")
            return error_response(f"Parse error: {e}")

        result = success_response(
            data,
            source="kenneth_french_data_library",
            dataset=dataset,
            frequency=frequency,
            description=f"Fama-French {dataset.replace('_', ' ')} ({frequency})",
            fields=list(data[0].keys()) if data else [],
        )

        self._cache.set("historical", cache_key, result, "daily_data")
        return result

    # ------------------------------------------------------------------
    # 3. NBER Business Cycles
    # ------------------------------------------------------------------

    def get_nber_cycles(self) -> Dict[str, Any]:
        """
        NBER 경기 순환 날짜 (1854~현재, 34사이클).

        Returns: {cycles: [{peak_date, trough_date, contraction_months, expansion_months}],
                  current_phase, months_since_last_trough}
        """
        cache_key = {"method": "nber_cycles"}
        cached = self._cache.get("historical", cache_key)
        if cached:
            return cached

        cycles_raw = None

        # Try fetching from NBER JSON endpoint
        try:
            resp = self._session.get(self.NBER_JSON_URL, timeout=15)
            resp.raise_for_status()
            cycles_raw = resp.json()
            logger.info("Fetched NBER cycles from API")
        except Exception as e:
            logger.info(f"NBER JSON fetch failed ({e}), using hardcoded backup")

        # Build cycles list
        cycles = []
        if cycles_raw and isinstance(cycles_raw, list):
            for item in cycles_raw:
                peak = item.get("peak") or item.get("peak_date")
                trough = item.get("trough") or item.get("trough_date")
                if peak and trough:
                    cycles.append({"peak_date": str(peak)[:10], "trough_date": str(trough)[:10]})
        else:
            # Use hardcoded backup
            for c in NBER_CYCLES_BACKUP:
                cycles.append({"peak_date": c["peak"], "trough_date": c["trough"]})

        # Calculate contraction/expansion months
        for i, cycle in enumerate(cycles):
            try:
                peak_dt = datetime.strptime(cycle["peak_date"], "%Y-%m-%d")
                trough_dt = datetime.strptime(cycle["trough_date"], "%Y-%m-%d")
                contraction = (trough_dt.year - peak_dt.year) * 12 + (trough_dt.month - peak_dt.month)
                cycle["contraction_months"] = contraction

                # Expansion = trough to next peak
                if i + 1 < len(cycles):
                    next_peak_dt = datetime.strptime(cycles[i + 1]["peak_date"], "%Y-%m-%d")
                    expansion = (next_peak_dt.year - trough_dt.year) * 12 + (next_peak_dt.month - trough_dt.month)
                    cycle["expansion_months"] = expansion
                else:
                    # Current expansion (from last trough to now)
                    now = datetime.now()
                    expansion = (now.year - trough_dt.year) * 12 + (now.month - trough_dt.month)
                    cycle["expansion_months"] = expansion
            except (ValueError, KeyError):
                pass

        # Current phase
        last_trough = None
        current_phase = "expansion"
        months_since_trough = 0
        if cycles:
            last = cycles[-1]
            try:
                last_trough_dt = datetime.strptime(last["trough_date"], "%Y-%m-%d")
                last_peak_dt = datetime.strptime(last["peak_date"], "%Y-%m-%d")
                now = datetime.now()
                if last_peak_dt > last_trough_dt:
                    # Peak is after trough — might be in contraction
                    current_phase = "contraction"
                    months_since_trough = 0
                else:
                    current_phase = "expansion"
                    months_since_trough = (now.year - last_trough_dt.year) * 12 + (now.month - last_trough_dt.month)
            except ValueError:
                pass

        result = success_response(
            cycles,
            source="nber",
            description="NBER US Business Cycle Dates (1854-present)",
            total_cycles=len(cycles),
            current_phase=current_phase,
            months_since_last_trough=months_since_trough,
            avg_contraction_months=round(
                sum(c.get("contraction_months", 0) for c in cycles) / max(len(cycles), 1), 1
            ),
            avg_expansion_months=round(
                sum(c.get("expansion_months", 0) for c in cycles) / max(len(cycles), 1), 1
            ),
        )

        self._cache.set("historical", cache_key, result, "daily_data")
        return result

    # ------------------------------------------------------------------
    # 4. FRED Century-scale Series
    # ------------------------------------------------------------------

    def get_fred_century(
        self, series_id: str, start: str = "1900-01-01"
    ) -> Dict[str, Any]:
        """
        FRED 초장기 시계열 (100년+).

        Popular series: CPIAUCSL(1913), TB3MS(1934), UNRATE(1948),
        GDP(1947), M2SL(1959), DGS10(1962), SP500(1927).
        """
        cache_key = {"method": "fred_century", "series": series_id, "start": start}
        cached = self._cache.get("historical", cache_key)
        if cached:
            return cached

        data = self._fred_request(series_id, start)
        if not data:
            return error_response(f"No data for FRED series {series_id}")

        result = success_response(
            data,
            source="fred",
            series_id=series_id,
            description=f"FRED {series_id} long-term series",
            period={"start": data[0]["date"], "end": data[-1]["date"]} if data else {},
        )

        self._cache.set("historical", cache_key, result, "daily_data")
        return result

    # ------------------------------------------------------------------
    # 5. Gold & Oil Long-term
    # ------------------------------------------------------------------

    def get_gold_oil_long(
        self, asset: str = "gold", period: str = "max"
    ) -> Dict[str, Any]:
        """
        금/유가 초장기 가격. Gold: FRED GOLDAMGBD228NLBM (1968+), Oil: FRED DCOILWTICO (1986+).
        yfinance 폴백: GC=F(금), CL=F(유가).
        """
        cache_key = {"method": "gold_oil", "asset": asset, "period": period}
        cached = self._cache.get("historical", cache_key)
        if cached:
            return cached

        data = []
        source = "fred"

        if asset.lower() in ("gold", "au", "xau"):
            asset_name = "Gold"
            # Try FRED first (longer history)
            data = self._fred_request("GOLDAMGBD228NLBM", "1968-01-01")
            if not data:
                # Fallback to yfinance
                data = self._yfinance_fetch("GC=F", period)
                source = "yfinance"
        elif asset.lower() in ("oil", "wti", "crude"):
            asset_name = "WTI Crude Oil"
            data = self._fred_request("DCOILWTICO", "1986-01-01")
            if not data:
                data = self._yfinance_fetch("CL=F", period)
                source = "yfinance"
        elif asset.lower() in ("brent",):
            asset_name = "Brent Crude Oil"
            data = self._fred_request("DCOILBRENTEU", "1987-05-01")
            if not data:
                data = self._yfinance_fetch("BZ=F", period)
                source = "yfinance"
        else:
            return error_response(f"Unknown asset: {asset}. Use: gold, oil, brent")

        if not data:
            return error_response(f"No data available for {asset}")

        # Convert to price format
        formatted = []
        for item in data:
            formatted.append({
                "date": item.get("date", item.get("Date", "")),
                "price": round(item.get("value", item.get("price", 0)), 2),
            })

        result = success_response(
            formatted,
            source=source,
            asset=asset_name,
            period={"start": formatted[0]["date"], "end": formatted[-1]["date"]} if formatted else {},
        )

        self._cache.set("historical", cache_key, result, "daily_data")
        return result

    def _yfinance_fetch(self, ticker: str, period: str = "max") -> List[Dict]:
        """Fetch data from yfinance as fallback."""
        try:
            import yfinance as yf
            tk = yf.Ticker(ticker)
            hist = tk.history(period=period)
            data = []
            for date, row in hist.iterrows():
                data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "value": round(float(row["Close"]), 2),
                })
            return data
        except Exception as e:
            logger.warning(f"yfinance fetch failed for {ticker}: {e}")
            return []

    # ------------------------------------------------------------------
    # 6. Cross-century Crisis Comparison
    # ------------------------------------------------------------------

    def get_cross_century_comparison(
        self, events: List[str], window_months: int = 24
    ) -> Dict[str, Any]:
        """
        위기 간 비교 분석 — 이벤트 전후 S&P 500 정규화.

        events: 날짜 리스트 (e.g. ["1929-10-01", "2008-09-15", "2020-03-11"])
        window_months: 이벤트 전후 기간 (기본 24개월)
        Returns: {event_date: [{month_offset, normalized_price}]} 각 이벤트별 100 기준 정규화
        """
        cache_key = {"method": "cross_century", "events": sorted(events), "window": window_months}
        cached = self._cache.get("historical", cache_key)
        if cached:
            return cached

        # Get full S&P 500 history
        sp_data = self._fred_request("SP500", "1927-01-01")
        if not sp_data:
            # Try yfinance
            sp_data = self._yfinance_fetch("^GSPC", "max")

        if not sp_data:
            return error_response("Cannot retrieve S&P 500 data for comparison")

        # Build date->price lookup (monthly averages)
        monthly_prices = {}
        monthly_sums = {}
        monthly_counts = {}
        for item in sp_data:
            date_str = item.get("date", "")[:7]  # YYYY-MM
            val = item.get("value", item.get("price", 0))
            if date_str and val:
                monthly_sums[date_str] = monthly_sums.get(date_str, 0) + val
                monthly_counts[date_str] = monthly_counts.get(date_str, 0) + 1

        for ym in monthly_sums:
            monthly_prices[ym] = round(monthly_sums[ym] / monthly_counts[ym], 2)

        # Sort month keys
        sorted_months = sorted(monthly_prices.keys())

        comparisons = {}
        for event_date in events:
            event_ym = event_date[:7]
            if event_ym not in monthly_prices:
                # Find nearest month
                nearest = min(sorted_months, key=lambda m: abs(
                    (int(m[:4]) * 12 + int(m[5:7])) - (int(event_ym[:4]) * 12 + int(event_ym[5:7]))
                )) if sorted_months else None
                if nearest:
                    event_ym = nearest
                else:
                    comparisons[event_date] = {"error": "No data available for this period"}
                    continue

            base_price = monthly_prices[event_ym]
            if base_price <= 0:
                comparisons[event_date] = {"error": "Invalid base price"}
                continue

            event_year = int(event_ym[:4])
            event_month = int(event_ym[5:7])

            series = []
            for offset in range(-window_months, window_months + 1):
                total_months = event_year * 12 + event_month - 1 + offset
                y = total_months // 12
                m = total_months % 12 + 1
                ym_key = f"{y}-{m:02d}"

                if ym_key in monthly_prices:
                    normalized = round(monthly_prices[ym_key] / base_price * 100, 2)
                    series.append({"month_offset": offset, "date": f"{ym_key}-01", "normalized_price": normalized})

            comparisons[event_date] = series

        result = success_response(
            comparisons,
            source="Historical Data",
            description="Cross-century crisis comparison (normalized to 100 at event date)",
            window_months=window_months,
            events_count=len(events),
        )

        self._cache.set("historical", cache_key, result, "daily_data")
        return result


# ======================================================================
# Standalone test
# ======================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    adapter = HistoricalDataAdapter()

    print("\n=== NBER Business Cycles ===")
    nber = adapter.get_nber_cycles()
    print(f"Success: {nber['success']}, Cycles: {nber.get('total_cycles')}, Phase: {nber.get('current_phase')}")

    print("\n=== FRED Century (CPIAUCSL) ===")
    cpi = adapter.get_fred_century("CPIAUCSL", "1913-01-01")
    print(f"Success: {cpi['success']}, Count: {cpi.get('count')}")

    print("\n=== Gold Long-term ===")
    gold = adapter.get_gold_oil_long("gold")
    print(f"Success: {gold['success']}, Count: {gold.get('count')}")
