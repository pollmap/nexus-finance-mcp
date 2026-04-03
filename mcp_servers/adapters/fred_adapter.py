"""
FRED Adapter - Federal Reserve Economic Data.

Provides US macroeconomic data from FRED API:
- Interest rates (Fed Funds Rate, Treasury yields)
- GDP, Inflation, Unemployment
- Money supply (M1, M2)
- Housing data

Requires FRED API key from: https://fred.stlouisfed.org/docs/api/api_key.html

Run standalone test: python -m mcp_servers.adapters.fred_adapter
"""
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.core.cache_manager import CacheManager, get_cache
from mcp_servers.core.rate_limiter import RateLimiter, get_limiter

logger = logging.getLogger(__name__)


# Key FRED series IDs (35+ indicators)
FRED_SERIES = {
    # === 금리 ===
    "fed_funds_rate": {"id": "FEDFUNDS", "name": "Federal Funds Effective Rate", "unit": "%", "frequency": "M"},
    "treasury_3m": {"id": "DTB3", "name": "3-Month Treasury Bill Rate", "unit": "%", "frequency": "D"},
    "treasury_1y": {"id": "GS1", "name": "1-Year Treasury Rate", "unit": "%", "frequency": "M"},
    "treasury_2y": {"id": "GS2", "name": "2-Year Treasury Rate", "unit": "%", "frequency": "M"},
    "treasury_3y": {"id": "GS3", "name": "3-Year Treasury Rate", "unit": "%", "frequency": "M"},
    "treasury_5y": {"id": "GS5", "name": "5-Year Treasury Rate", "unit": "%", "frequency": "M"},
    "treasury_7y": {"id": "GS7", "name": "7-Year Treasury Rate", "unit": "%", "frequency": "M"},
    "treasury_10y": {"id": "GS10", "name": "10-Year Treasury Rate", "unit": "%", "frequency": "M"},
    "treasury_20y": {"id": "GS20", "name": "20-Year Treasury Rate", "unit": "%", "frequency": "M"},
    "treasury_30y": {"id": "GS30", "name": "30-Year Treasury Rate", "unit": "%", "frequency": "M"},
    "sofr": {"id": "SOFR", "name": "Secured Overnight Financing Rate", "unit": "%", "frequency": "D"},
    "aaa_corporate": {"id": "AAA", "name": "Moody's AAA Corporate Bond Yield", "unit": "%", "frequency": "D"},
    "baa_corporate": {"id": "BAA", "name": "Moody's BAA Corporate Bond Yield", "unit": "%", "frequency": "D"},
    "ted_spread": {"id": "TEDRATE", "name": "TED Spread", "unit": "%", "frequency": "D"},
    # === GDP/성장 ===
    "gdp": {"id": "GDP", "name": "Gross Domestic Product", "unit": "Billions $", "frequency": "Q"},
    "gdp_growth": {"id": "A191RL1Q225SBEA", "name": "Real GDP Growth Rate", "unit": "%", "frequency": "Q"},
    # === 물가 ===
    "cpi": {"id": "CPIAUCSL", "name": "Consumer Price Index (All)", "unit": "Index 1982-84=100", "frequency": "M"},
    "core_cpi": {"id": "CPILFESL", "name": "Core CPI (excl Food & Energy)", "unit": "Index", "frequency": "M"},
    "pce": {"id": "PCEPI", "name": "PCE Price Index", "unit": "Index 2017=100", "frequency": "M"},
    "core_pce": {"id": "PCEPILFE", "name": "Core PCE (excl Food & Energy)", "unit": "Index", "frequency": "M"},
    "inflation": {"id": "FPCPITOTLZGUSA", "name": "Inflation Rate (CPI YoY)", "unit": "%", "frequency": "A"},
    "inflation_expect_5y": {"id": "T5YIE", "name": "5-Year Breakeven Inflation", "unit": "%", "frequency": "D"},
    "inflation_expect_10y": {"id": "T10YIE", "name": "10-Year Breakeven Inflation", "unit": "%", "frequency": "D"},
    # === 고용 ===
    "unemployment": {"id": "UNRATE", "name": "Unemployment Rate", "unit": "%", "frequency": "M"},
    "nonfarm_payroll": {"id": "PAYEMS", "name": "Nonfarm Payrolls", "unit": "Thousands", "frequency": "M"},
    "initial_claims": {"id": "ICSA", "name": "Initial Jobless Claims", "unit": "Persons", "frequency": "W"},
    "labor_participation": {"id": "CIVPART", "name": "Labor Force Participation Rate", "unit": "%", "frequency": "M"},
    "avg_hourly_earnings": {"id": "CES0500000003", "name": "Average Hourly Earnings", "unit": "$", "frequency": "M"},
    # === 통화 ===
    "m2": {"id": "M2SL", "name": "M2 Money Stock", "unit": "Billions $", "frequency": "M"},
    # === 주식 ===
    "sp500": {"id": "SP500", "name": "S&P 500 Index", "unit": "Index", "frequency": "D"},
    "vix": {"id": "VIXCLS", "name": "CBOE Volatility Index (VIX)", "unit": "Index", "frequency": "D"},
    # === 부동산 ===
    "house_price_index": {"id": "CSUSHPINSA", "name": "Case-Shiller Home Price Index", "unit": "Index", "frequency": "M"},
    "mortgage_30y": {"id": "MORTGAGE30US", "name": "30-Year Mortgage Rate", "unit": "%", "frequency": "W"},
    "existing_home_sales": {"id": "EXHOSLUSM495S", "name": "Existing Home Sales", "unit": "Millions", "frequency": "M"},
    "new_home_sales": {"id": "HSN1F", "name": "New Home Sales", "unit": "Thousands", "frequency": "M"},
    "building_permits": {"id": "PERMIT", "name": "Building Permits", "unit": "Thousands", "frequency": "M"},
    # === 경기 ===
    "retail_sales": {"id": "RSAFS", "name": "Retail Sales", "unit": "Millions $", "frequency": "M"},
    "industrial_production": {"id": "INDPRO", "name": "Industrial Production Index", "unit": "Index 2017=100", "frequency": "M"},
    "consumer_sentiment": {"id": "UMCSENT", "name": "Univ. of Michigan Consumer Sentiment", "unit": "Index", "frequency": "M"},
    "dxy": {"id": "DTWEXBGS", "name": "US Dollar Index (Broad)", "unit": "Index", "frequency": "D"},
}


class FREDAdapter:
    """
    Adapter for FRED API.

    Provides US macroeconomic data from Federal Reserve Economic Data.
    """

    BASE_URL = "https://api.stlouisfed.org/fred"

    def __init__(
        self,
        api_key: str = None,
        cache: CacheManager = None,
        limiter: RateLimiter = None,
    ):
        """
        Initialize FRED adapter.

        Args:
            api_key: FRED API key (uses env var if not provided)
            cache: Cache manager instance
            limiter: Rate limiter instance
        """
        self.api_key = api_key or os.getenv("FRED_API_KEY", "")
        self._cache = cache or get_cache()
        self._limiter = limiter or get_limiter()

        # HTTP session
        self._session = requests.Session()

        if not self.api_key:
            logger.warning("FRED_API_KEY not set. FRED queries will fail.")

        logger.info("FRED adapter initialized")

    def _make_request(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """Make FRED API request."""
        if not self.api_key:
            return {"error": True, "message": "FRED API key not configured"}

        self._limiter.acquire("fred")

        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}
        params["api_key"] = self.api_key
        params["file_type"] = "json"

        try:
            response = self._session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return {"success": True, "data": response.json()}

        except requests.exceptions.HTTPError as e:
            logger.error(f"FRED HTTP error: {e}")
            return {"error": True, "message": f"HTTP Error: {e}"}

        except requests.exceptions.RequestException as e:
            logger.error(f"FRED request error: {e}")
            return {"error": True, "message": str(e)}

    def get_series(
        self,
        series_id: str,
        start_date: str = None,
        end_date: str = None,
    ) -> Dict[str, Any]:
        """
        Get time series data.

        Args:
            series_id: FRED series ID (e.g., "FEDFUNDS", "GDP")
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Time series data
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        cache_key = {"method": "series", "id": series_id, "start": start_date, "end": end_date}
        cached = self._cache.get("fred", cache_key)
        if cached:
            return cached

        result = self._make_request(
            "series/observations",
            {
                "series_id": series_id,
                "observation_start": start_date,
                "observation_end": end_date,
            }
        )

        if result.get("error"):
            return result

        observations = result["data"].get("observations", [])

        # Process observations
        data = []
        for obs in observations:
            try:
                value = float(obs["value"]) if obs["value"] != "." else None
                data.append({
                    "date": obs["date"],
                    "value": value,
                })
            except (ValueError, KeyError):
                continue

        # Get series info
        series_info = FRED_SERIES.get(series_id.lower(), {})

        response = {
            "success": True,
            "series_id": series_id,
            "name": series_info.get("name", series_id),
            "unit": series_info.get("unit", ""),
            "period": {"start": start_date, "end": end_date},
            "count": len(data),
            "data": data,
            "latest": data[-1] if data else None,
        }

        self._cache.set("fred", cache_key, response, "daily_data")
        return response

    def get_fed_funds_rate(
        self,
        start_date: str = None,
        end_date: str = None,
    ) -> Dict[str, Any]:
        """Get Federal Funds Rate."""
        result = self.get_series("FEDFUNDS", start_date, end_date)
        if result.get("success"):
            result["indicator"] = "Federal Funds Effective Rate"
        return result

    def get_treasury_yield(
        self,
        maturity: str = "10y",
        start_date: str = None,
        end_date: str = None,
    ) -> Dict[str, Any]:
        """
        Get Treasury yield.

        Args:
            maturity: Maturity period (2y, 5y, 10y, 30y)
        """
        series_map = {
            "3m": "DTB3", "1y": "GS1", "2y": "GS2", "3y": "GS3",
            "5y": "GS5", "7y": "GS7", "10y": "GS10", "20y": "GS20", "30y": "GS30",
        }
        series_id = series_map.get(maturity, "GS10")
        result = self.get_series(series_id, start_date, end_date)
        if result.get("success"):
            result["indicator"] = f"{maturity.upper()} Treasury Yield"
        return result

    def get_gdp(
        self,
        start_date: str = None,
        end_date: str = None,
    ) -> Dict[str, Any]:
        """Get US GDP data."""
        result = self.get_series("GDP", start_date, end_date)
        if result.get("success"):
            result["indicator"] = "US Gross Domestic Product"
        return result

    def get_unemployment(
        self,
        start_date: str = None,
        end_date: str = None,
    ) -> Dict[str, Any]:
        """Get US unemployment rate."""
        result = self.get_series("UNRATE", start_date, end_date)
        if result.get("success"):
            result["indicator"] = "US Unemployment Rate"
        return result

    def get_inflation(
        self,
        start_date: str = None,
        end_date: str = None,
    ) -> Dict[str, Any]:
        """Get US CPI/Inflation data."""
        result = self.get_series("CPIAUCSL", start_date, end_date)
        if result.get("success"):
            result["indicator"] = "Consumer Price Index"
            # Calculate YoY inflation rate
            if len(result.get("data", [])) >= 13:
                data = result["data"]
                latest = data[-1]["value"]
                year_ago = data[-13]["value"]
                if latest and year_ago:
                    inflation_rate = ((latest - year_ago) / year_ago) * 100
                    result["inflation_rate_yoy"] = round(inflation_rate, 2)
        return result

    def get_m2_money_supply(
        self,
        start_date: str = None,
        end_date: str = None,
    ) -> Dict[str, Any]:
        """Get M2 money supply."""
        result = self.get_series("M2SL", start_date, end_date)
        if result.get("success"):
            result["indicator"] = "M2 Money Stock"
        return result

    def get_house_price_index(
        self,
        start_date: str = None,
        end_date: str = None,
    ) -> Dict[str, Any]:
        """Get Case-Shiller Home Price Index."""
        result = self.get_series("CSUSHPINSA", start_date, end_date)
        if result.get("success"):
            result["indicator"] = "S&P/Case-Shiller U.S. National Home Price Index"
        return result

    def get_mortgage_rate(
        self,
        start_date: str = None,
        end_date: str = None,
    ) -> Dict[str, Any]:
        """Get 30-year mortgage rate."""
        result = self.get_series("MORTGAGE30US", start_date, end_date)
        if result.get("success"):
            result["indicator"] = "30-Year Fixed Rate Mortgage"
        return result

    def get_macro_snapshot(self) -> Dict[str, Any]:
        """Get current snapshot of key US macro indicators."""
        snapshot = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "indicators": {},
        }

        # Fed Funds Rate
        result = self.get_fed_funds_rate()
        if result.get("latest"):
            snapshot["indicators"]["fed_funds_rate"] = {
                "value": result["latest"]["value"],
                "unit": "%",
                "date": result["latest"]["date"],
            }

        # 10Y Treasury
        result = self.get_treasury_yield("10y")
        if result.get("latest"):
            snapshot["indicators"]["treasury_10y"] = {
                "value": result["latest"]["value"],
                "unit": "%",
                "date": result["latest"]["date"],
            }

        # Unemployment
        result = self.get_unemployment()
        if result.get("latest"):
            snapshot["indicators"]["unemployment"] = {
                "value": result["latest"]["value"],
                "unit": "%",
                "date": result["latest"]["date"],
            }

        # Inflation
        result = self.get_inflation()
        if result.get("inflation_rate_yoy") is not None:
            snapshot["indicators"]["inflation_yoy"] = {
                "value": result["inflation_rate_yoy"],
                "unit": "%",
            }

        return snapshot

    def search_series(self, keyword: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search for FRED series.

        Args:
            keyword: Search keyword
            limit: Max results

        Returns:
            Matching series
        """
        result = self._make_request(
            "series/search",
            {
                "search_text": keyword,
                "limit": limit,
            }
        )

        if result.get("error"):
            return result

        series_list = result["data"].get("seriess", [])

        return {
            "success": True,
            "keyword": keyword,
            "count": len(series_list),
            "data": [
                {
                    "id": s.get("id"),
                    "title": s.get("title"),
                    "frequency": s.get("frequency"),
                    "units": s.get("units"),
                    "popularity": s.get("popularity"),
                }
                for s in series_list
            ],
        }


def test_fred_adapter():
    """Test FRED adapter functionality."""
    logging.basicConfig(level=logging.INFO)

    adapter = FREDAdapter()

    if not adapter.api_key:
        print("FRED API key not set. Using limited test.")
        print("Get your free API key from: https://fred.stlouisfed.org/docs/api/api_key.html")
        return

    print("=" * 60)
    print("FRED Adapter Test")
    print("=" * 60)

    # Test Fed Funds Rate
    print("\n1. Federal Funds Rate")
    result = adapter.get_fed_funds_rate()
    if result.get("success") and result.get("latest"):
        print(f"   Latest: {result['latest']['value']}%")
        print(f"   Date: {result['latest']['date']}")

    # Test Treasury Yield
    print("\n2. 10-Year Treasury Yield")
    result = adapter.get_treasury_yield("10y")
    if result.get("success") and result.get("latest"):
        print(f"   Latest: {result['latest']['value']}%")

    # Test Unemployment
    print("\n3. Unemployment Rate")
    result = adapter.get_unemployment()
    if result.get("success") and result.get("latest"):
        print(f"   Latest: {result['latest']['value']}%")

    # Test Macro Snapshot
    print("\n4. Macro Snapshot")
    result = adapter.get_macro_snapshot()
    if result.get("success"):
        for name, data in result.get("indicators", {}).items():
            print(f"   {name}: {data['value']}{data['unit']}")

    print("\n" + "=" * 60)
    print("Test Complete")


if __name__ == "__main__":
    test_fred_adapter()
