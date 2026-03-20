"""
Yahoo Finance Adapter - Global Stock Market Data.

Provides global stock data via yfinance library:
- Stock prices (OHLCV)
- Company info
- Financial statements
- Historical data

Requires: pip install yfinance

Run standalone test: python -m mcp_servers.adapters.yahoo_adapter
"""
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.core.cache_manager import CacheManager, get_cache
from mcp_servers.core.rate_limiter import RateLimiter, get_limiter

logger = logging.getLogger(__name__)


class YahooAdapter:
    """
    Adapter for Yahoo Finance data via yfinance.

    Provides global stock market data including US, European, and Asian markets.
    """

    def __init__(
        self,
        cache: CacheManager = None,
        limiter: RateLimiter = None,
    ):
        """
        Initialize Yahoo Finance adapter.

        Args:
            cache: Cache manager instance
            limiter: Rate limiter instance
        """
        self._cache = cache or get_cache()
        self._limiter = limiter or get_limiter()

        # Initialize yfinance
        self._yf = None
        try:
            import yfinance as yf
            self._yf = yf
            logger.info("yfinance initialized successfully")
        except ImportError:
            logger.error("yfinance not installed. Run: pip install yfinance")
        except Exception as e:
            logger.error(f"Failed to initialize yfinance: {e}")

    def get_stock_info(self, ticker: str) -> Dict[str, Any]:
        """
        Get company information.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL", "MSFT", "005930.KS")

        Returns:
            Company info dict
        """
        if not self._yf:
            return {"error": True, "message": "yfinance not initialized"}

        try:
            self._limiter.acquire("yahoo")

            cache_key = {"method": "info", "ticker": ticker}
            cached = self._cache.get("yahoo", cache_key)
            if cached:
                return cached

            stock = self._yf.Ticker(ticker)
            info = stock.info

            result = {
                "success": True,
                "ticker": ticker,
                "name": info.get("longName", info.get("shortName", ticker)),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "country": info.get("country"),
                "currency": info.get("currency"),
                "exchange": info.get("exchange"),
                "market_cap": info.get("marketCap"),
                "enterprise_value": info.get("enterpriseValue"),
                "trailing_pe": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "price_to_book": info.get("priceToBook"),
                "ev_to_ebitda": info.get("enterpriseToEbitda"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
                "current_price": info.get("currentPrice", info.get("regularMarketPrice")),
            }

            self._cache.set("yahoo", cache_key, result, "daily_data")
            return result

        except Exception as e:
            logger.error(f"Yahoo info error for {ticker}: {e}")
            return {"error": True, "message": str(e)}

    def get_stock_price(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> Dict[str, Any]:
        """
        Get historical stock prices.

        Args:
            ticker: Stock ticker symbol
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            Historical price data
        """
        if not self._yf:
            return {"error": True, "message": "yfinance not initialized"}

        try:
            self._limiter.acquire("yahoo")

            cache_key = {"method": "price", "ticker": ticker, "period": period, "interval": interval}
            cached = self._cache.get("yahoo", cache_key)
            if cached:
                return cached

            stock = self._yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)

            if df is None or df.empty:
                return {"success": True, "data": [], "message": "No price data"}

            # Convert to records
            df = df.reset_index()
            df.columns = [c.lower().replace(" ", "_") for c in df.columns]

            # Handle datetime index
            if "date" in df.columns:
                df["date"] = df["date"].astype(str)
            elif "datetime" in df.columns:
                df["date"] = df["datetime"].astype(str)
                df = df.drop(columns=["datetime"])

            records = df.to_dict("records")

            result = {
                "success": True,
                "ticker": ticker,
                "period": period,
                "interval": interval,
                "count": len(records),
                "latest": records[-1] if records else None,
                "data": records,
            }

            # Cache based on interval
            data_type = "realtime_price" if interval in ["1m", "2m", "5m"] else "daily_data"
            self._cache.set("yahoo", cache_key, result, data_type)
            return result

        except Exception as e:
            logger.error(f"Yahoo price error for {ticker}: {e}")
            return {"error": True, "message": str(e)}

    def get_financials(self, ticker: str) -> Dict[str, Any]:
        """
        Get company financial statements.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Financial statements dict
        """
        if not self._yf:
            return {"error": True, "message": "yfinance not initialized"}

        try:
            self._limiter.acquire("yahoo")

            cache_key = {"method": "financials", "ticker": ticker}
            cached = self._cache.get("yahoo", cache_key)
            if cached:
                return cached

            stock = self._yf.Ticker(ticker)

            # Get income statement
            income = stock.income_stmt
            balance = stock.balance_sheet
            cash_flow = stock.cashflow

            def df_to_dict(df):
                if df is None or df.empty:
                    return {}
                df = df.fillna(0)
                # Convert columns (dates) to strings
                result = {}
                for col in df.columns:
                    col_str = str(col.date()) if hasattr(col, 'date') else str(col)
                    result[col_str] = df[col].to_dict()
                return result

            result = {
                "success": True,
                "ticker": ticker,
                "income_statement": df_to_dict(income),
                "balance_sheet": df_to_dict(balance),
                "cash_flow": df_to_dict(cash_flow),
            }

            # Extract key metrics from latest period
            if income is not None and not income.empty:
                latest = income.iloc[:, 0]
                result["summary"] = {
                    "revenue": latest.get("Total Revenue", 0),
                    "operating_income": latest.get("Operating Income", 0),
                    "net_income": latest.get("Net Income", 0),
                    "ebitda": latest.get("EBITDA", 0),
                }

            self._cache.set("yahoo", cache_key, result, "daily_data")
            return result

        except Exception as e:
            logger.error(f"Yahoo financials error for {ticker}: {e}")
            return {"error": True, "message": str(e)}

    def get_multiple_quotes(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Get quotes for multiple tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Quotes for all tickers
        """
        if not self._yf:
            return {"error": True, "message": "yfinance not initialized"}

        try:
            self._limiter.acquire("yahoo")

            quotes = []
            for ticker in tickers[:20]:  # Limit to 20
                info = self.get_stock_info(ticker)
                if info.get("success"):
                    quotes.append({
                        "ticker": ticker,
                        "name": info.get("name"),
                        "price": info.get("current_price"),
                        "pe": info.get("trailing_pe"),
                        "market_cap": info.get("market_cap"),
                        "beta": info.get("beta"),
                    })

            return {
                "success": True,
                "count": len(quotes),
                "data": quotes,
            }

        except Exception as e:
            logger.error(f"Yahoo multiple quotes error: {e}")
            return {"error": True, "message": str(e)}

    def compare_stocks(
        self,
        tickers: List[str],
    ) -> Dict[str, Any]:
        """
        Compare multiple stocks.

        Args:
            tickers: List of ticker symbols to compare

        Returns:
            Comparison data
        """
        if not self._yf:
            return {"error": True, "message": "yfinance not initialized"}

        try:
            comparison = []

            for ticker in tickers[:10]:  # Limit to 10
                info = self.get_stock_info(ticker)
                if info.get("success"):
                    comparison.append({
                        "ticker": ticker,
                        "name": info.get("name"),
                        "sector": info.get("sector"),
                        "market_cap": info.get("market_cap"),
                        "pe": info.get("trailing_pe"),
                        "pb": info.get("price_to_book"),
                        "ev_ebitda": info.get("ev_to_ebitda"),
                        "beta": info.get("beta"),
                        "dividend_yield": info.get("dividend_yield"),
                    })

            # Calculate averages
            if comparison:
                avg_pe = sum(c.get("pe") or 0 for c in comparison) / len(comparison)
                avg_pb = sum(c.get("pb") or 0 for c in comparison) / len(comparison)

                return {
                    "success": True,
                    "tickers": tickers,
                    "count": len(comparison),
                    "data": comparison,
                    "averages": {
                        "pe": round(avg_pe, 2),
                        "pb": round(avg_pb, 2),
                    },
                }

            return {"success": True, "data": [], "message": "No data available"}

        except Exception as e:
            logger.error(f"Yahoo comparison error: {e}")
            return {"error": True, "message": str(e)}


def test_yahoo_adapter():
    """Test Yahoo Finance adapter functionality."""
    logging.basicConfig(level=logging.INFO)

    adapter = YahooAdapter()

    if not adapter._yf:
        print("yfinance not initialized.")
        return

    print("=" * 60)
    print("Yahoo Finance Adapter Test")
    print("=" * 60)

    # Test stock info
    print("\n1. Apple (AAPL) Info")
    result = adapter.get_stock_info("AAPL")
    if result.get("success"):
        print(f"   Name: {result.get('name')}")
        print(f"   Price: ${result.get('current_price', 0):,.2f}")
        print(f"   P/E: {result.get('trailing_pe', 0):.2f}")
        print(f"   Market Cap: ${result.get('market_cap', 0)/1e9:.1f}B")

    # Test stock price
    print("\n2. Historical Prices (1 month)")
    result = adapter.get_stock_price("AAPL", period="1mo")
    if result.get("success"):
        print(f"   Records: {result.get('count', 0)}")
        if result.get("latest"):
            print(f"   Latest Close: ${result['latest'].get('close', 0):,.2f}")

    # Test financials
    print("\n3. Financial Statements")
    result = adapter.get_financials("AAPL")
    if result.get("success"):
        summary = result.get("summary", {})
        print(f"   Revenue: ${summary.get('revenue', 0)/1e9:.1f}B")
        print(f"   Net Income: ${summary.get('net_income', 0)/1e9:.1f}B")

    # Test comparison
    print("\n4. Tech Giants Comparison")
    result = adapter.compare_stocks(["AAPL", "MSFT", "GOOGL"])
    if result.get("success"):
        for stock in result.get("data", []):
            print(f"   {stock['ticker']}: P/E={stock.get('pe', 'N/A')}")

    print("\n" + "=" * 60)
    print("Test Complete")


if __name__ == "__main__":
    test_yahoo_adapter()
