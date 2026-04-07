"""
KRX Adapter - Korea Exchange Market Data.

Wraps pykrx library for accessing Korean stock market data:
- Stock prices (OHLCV)
- Market cap / shares outstanding
- Index data (KOSPI, KOSDAQ)
- Beta calculation

Requires: pip install pykrx

Run standalone test: python -m mcp_servers.adapters.krx_adapter
"""
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.core.cache_manager import CacheManager, get_cache
from mcp_servers.core.rate_limiter import RateLimiter, get_limiter
from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)


class KRXAdapter:
    """
    Adapter for pykrx (Korea Exchange data).

    Provides stock prices, market data, and calculated metrics like beta.
    """

    # Major indices
    INDICES = {
        "KOSPI": "1001",
        "KOSDAQ": "2001",
        "KOSPI200": "1028",
        "KRX100": "5042",
    }

    def __init__(
        self,
        cache: CacheManager = None,
        limiter: RateLimiter = None,
    ):
        """
        Initialize KRX adapter.

        Args:
            cache: Cache manager instance
            limiter: Rate limiter instance
        """
        self._cache = cache or get_cache()
        self._limiter = limiter or get_limiter()

        # Initialize pykrx
        self._stock = None
        try:
            from pykrx import stock
            self._stock = stock
            logger.info("pykrx initialized successfully")
        except ImportError:
            logger.error("pykrx not installed. Run: pip install pykrx")
        except Exception as e:
            logger.error(f"Failed to initialize pykrx: {e}")

    @staticmethod
    def _validate_stock_code(stock_code: str) -> bool:
        """Validate Korean stock code format (6 digits)."""
        import re
        return bool(re.match(r'^\d{6}$', str(stock_code)))

    def _format_date(self, date: datetime) -> str:
        """Format date for pykrx (YYYYMMDD)."""
        return date.strftime("%Y%m%d")

    def get_stock_price(
        self,
        stock_code: str,
        start_date: str = None,
        end_date: str = None,
    ) -> Dict[str, Any]:
        """
        Get stock OHLCV data.

        Args:
            stock_code: Stock code (e.g., "005930")
            start_date: Start date (YYYYMMDD, default: 1 year ago)
            end_date: End date (YYYYMMDD, default: today)

        Returns:
            OHLCV data dict
        """
        if not self._validate_stock_code(stock_code):
            return error_response(f"Invalid stock code format: {stock_code}. Must be 6 digits (e.g., 005930)", code="INVALID_INPUT")
        if not self._stock:
            return error_response("pykrx not initialized", code="NOT_INITIALIZED")

        try:
            self._limiter.acquire("krx")

            if end_date is None:
                end_date = self._format_date(datetime.now())
            if start_date is None:
                start_date = self._format_date(datetime.now() - timedelta(days=365))

            cache_key = {"method": "price", "code": stock_code, "start": start_date, "end": end_date}
            cached = self._cache.get("krx", cache_key)
            if cached:
                return cached

            # Get OHLCV data
            df = self._stock.get_market_ohlcv_by_date(start_date, end_date, stock_code)

            if df is None or df.empty:
                return success_response(data=[], source="KRX", stock_code=stock_code, message="No price data")

            # Reset index to include date
            df = df.reset_index()

            # Map pykrx Korean column names to English (robust handling)
            korean_to_english = {
                "날짜": "date",
                "시가": "open",
                "고가": "high",
                "저가": "low",
                "종가": "close",
                "거래량": "volume",
                "거래대금": "value",
                "등락률": "change",
                "등락": "change",
            }

            # Rename columns using mapping, fall back to lowercase original
            new_columns = []
            for col in df.columns:
                col_str = str(col)
                if col_str in korean_to_english:
                    new_columns.append(korean_to_english[col_str])
                else:
                    # First column is usually the date index
                    new_columns.append(col_str.lower().replace(" ", "_"))
            df.columns = new_columns

            # Ensure date column exists
            if "date" not in df.columns and len(df.columns) > 0:
                df.columns = ["date"] + list(df.columns[1:])

            # Convert to records
            df["date"] = df["date"].astype(str)
            records = df.to_dict("records")

            result = success_response(
                data=records,
                source="KRX",
                stock_code=stock_code,
                period={"start": start_date, "end": end_date},
                latest=records[-1] if records else None,
            )

            self._cache.set("krx", cache_key, result, "daily_data")
            return result

        except Exception as e:
            logger.error(f"KRX price error: {e}")
            return error_response(str(e))

    def get_market_cap(self, stock_code: str, date: str = None) -> Dict[str, Any]:
        """
        Get market cap and shares outstanding.

        Args:
            stock_code: Stock code
            date: Date (YYYYMMDD, default: today)

        Returns:
            Market cap info dict
        """
        if not self._validate_stock_code(stock_code):
            return error_response(f"Invalid stock code format: {stock_code}. Must be 6 digits (e.g., 005930)", code="INVALID_INPUT")
        if not self._stock:
            return error_response("pykrx not initialized", code="NOT_INITIALIZED")

        try:
            self._limiter.acquire("krx")

            if date is None:
                date = self._format_date(datetime.now())

            cache_key = {"method": "market_cap", "code": stock_code, "date": date}
            cached = self._cache.get("krx", cache_key)
            if cached:
                return cached

            # Get market cap data
            df = self._stock.get_market_cap_by_date(date, date, stock_code)

            if df is None or df.empty:
                return success_response(data=None, source="KRX", stock_code=stock_code, message="No market cap data")

            # Get latest row
            row = df.iloc[-1]

            result = success_response(
                data=None,
                source="KRX",
                stock_code=stock_code,
                date=date,
                market_cap=int(row.get("시가총액", 0)),
                shares_outstanding=int(row.get("상장주식수", 0)),
                volume=int(row.get("거래량", 0)),
            )

            self._cache.set("krx", cache_key, result, "daily_data")
            return result

        except Exception as e:
            logger.error(f"KRX market cap error: {e}")
            return error_response(str(e))

    def get_index_data(
        self,
        index_code: str = "1001",  # KOSPI
        start_date: str = None,
        end_date: str = None,
    ) -> Dict[str, Any]:
        """
        Get index OHLCV data.

        Args:
            index_code: Index code (1001=KOSPI, 2001=KOSDAQ)
            start_date: Start date
            end_date: End date

        Returns:
            Index data dict
        """
        if not self._stock:
            return error_response("pykrx not initialized", code="NOT_INITIALIZED")

        try:
            self._limiter.acquire("krx")

            if end_date is None:
                end_date = self._format_date(datetime.now())
            if start_date is None:
                start_date = self._format_date(datetime.now() - timedelta(days=365))

            cache_key = {"method": "index", "code": index_code, "start": start_date, "end": end_date}
            cached = self._cache.get("krx", cache_key)
            if cached:
                return cached

            # Get index data — pykrx may crash on '지수명' KeyError (library bug)
            df = None
            try:
                df = self._stock.get_index_ohlcv_by_date(start_date, end_date, index_code)
            except KeyError:
                # pykrx internal bug: IndexTicker '지수명' column missing
                # Fallback to Yahoo Finance
                try:
                    import yfinance as yf
                    yahoo_map = {"1001": "^KS11", "2001": "^KQ11", "1028": "^KS200"}
                    yticker = yahoo_map.get(index_code, "^KS11")
                    sd = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
                    ed = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
                    ydf = yf.Ticker(yticker).history(start=sd, end=ed)
                    if ydf is not None and not ydf.empty:
                        ydf = ydf.reset_index()
                        ydf.columns = [c.lower().replace(" ", "_") for c in ydf.columns]
                        if "date" in ydf.columns:
                            ydf["date"] = ydf["date"].astype(str).str[:10]
                        df = ydf
                except Exception:
                    pass

            if df is None or df.empty:
                return success_response(data=[], source="KRX", index_code=index_code, message="No index data (pykrx 지수명 bug, Yahoo fallback also failed)")

            df = df.reset_index()

            # Use same robust Korean→English mapping as get_stock_price
            korean_to_english = {
                "날짜": "date", "시가": "open", "고가": "high", "저가": "low",
                "종가": "close", "거래량": "volume", "거래대금": "value",
                "등락률": "change", "상장시가총액": "market_cap",
                "지수명": "index_name", "시가총액": "market_cap",
            }
            new_columns = []
            for col in df.columns:
                col_str = str(col)
                if col_str in korean_to_english:
                    new_columns.append(korean_to_english[col_str])
                else:
                    new_columns.append(col_str.lower().replace(" ", "_"))
            df.columns = new_columns
            if "date" not in df.columns and len(df.columns) > 0:
                df.columns = ["date"] + list(df.columns[1:])
            df["date"] = df["date"].astype(str)
            records = df.to_dict("records")

            # Find index name
            index_name = next((k for k, v in self.INDICES.items() if v == index_code), index_code)

            result = success_response(
                data=records,
                source="KRX",
                index_code=index_code,
                index_name=index_name,
                period={"start": start_date, "end": end_date},
                latest=records[-1] if records else None,
            )

            self._cache.set("krx", cache_key, result, "daily_data")
            return result

        except Exception as e:
            logger.error(f"KRX index error: {e}")
            return error_response(str(e))

    def calculate_beta(
        self,
        stock_code: str,
        index_code: str = "1001",  # KOSPI
        period_days: int = 252,  # 1 year trading days
    ) -> Dict[str, Any]:
        """
        Calculate stock beta relative to market index.

        Beta = Cov(Ri, Rm) / Var(Rm)

        Args:
            stock_code: Stock code
            index_code: Index code for market returns
            period_days: Number of days for calculation

        Returns:
            Beta and related statistics
        """
        if not self._validate_stock_code(stock_code):
            return error_response(f"Invalid stock code format: {stock_code}. Must be 6 digits (e.g., 005930)", code="INVALID_INPUT")
        if not self._stock:
            return error_response("pykrx not initialized", code="NOT_INITIALIZED")

        try:
            end_date = self._format_date(datetime.now())
            start_date = self._format_date(datetime.now() - timedelta(days=int(period_days * 1.5)))

            cache_key = {"method": "beta", "code": stock_code, "index": index_code, "days": period_days}
            cached = self._cache.get("krx", cache_key)
            if cached:
                return cached

            # Get stock prices
            stock_result = self.get_stock_price(stock_code, start_date, end_date)
            if stock_result.get("error"):
                return stock_result

            # Get index prices
            index_result = self.get_index_data(index_code, start_date, end_date)
            if index_result.get("error"):
                return index_result

            # Convert to DataFrames
            stock_df = pd.DataFrame(stock_result["data"])
            index_df = pd.DataFrame(index_result["data"])

            if stock_df.empty or index_df.empty:
                return error_response("Insufficient data for beta calculation", code="NOT_FOUND")

            # Ensure "close" column exists (pykrx may return Korean names)
            close_map = {"종가": "close"}
            for col_name in close_map:
                if col_name in stock_df.columns and "close" not in stock_df.columns:
                    stock_df = stock_df.rename(columns={col_name: "close"})
                if col_name in index_df.columns and "close" not in index_df.columns:
                    index_df = index_df.rename(columns={col_name: "close"})

            if "close" not in stock_df.columns or "close" not in index_df.columns:
                resp = error_response(
                    f"'close' column not found. Stock cols: {list(stock_df.columns)}, Index cols: {list(index_df.columns)}",
                    code="NOT_FOUND",
                )
                resp["suggestion"] = "Try period_days=252 or check stock_code validity"
                return resp

            # Calculate returns
            stock_df["date"] = pd.to_datetime(stock_df["date"])
            index_df["date"] = pd.to_datetime(index_df["date"])

            stock_df = stock_df.set_index("date").sort_index()
            index_df = index_df.set_index("date").sort_index()

            # Align dates
            common_dates = stock_df.index.intersection(index_df.index)
            stock_returns = stock_df.loc[common_dates, "close"].pct_change().dropna()
            index_returns = index_df.loc[common_dates, "close"].pct_change().dropna()

            # Ensure same length
            min_len = min(len(stock_returns), len(index_returns), period_days)
            stock_returns = stock_returns.tail(min_len)
            index_returns = index_returns.tail(min_len)

            if len(stock_returns) < 20:
                return error_response("Insufficient data points for beta calculation", code="NOT_FOUND")

            # Calculate beta
            covariance = np.cov(stock_returns, index_returns)[0, 1]
            variance = np.var(index_returns)

            if variance == 0:
                return error_response("Zero variance in index returns", code="INVALID_INPUT")

            beta = covariance / variance

            # Calculate additional statistics
            correlation = np.corrcoef(stock_returns, index_returns)[0, 1]
            stock_volatility = np.std(stock_returns) * np.sqrt(252) * 100  # Annualized
            index_volatility = np.std(index_returns) * np.sqrt(252) * 100

            result = success_response(
                data=None,
                source="KRX",
                stock_code=stock_code,
                index_code=index_code,
                index_name=next((k for k, v in self.INDICES.items() if v == index_code), index_code),
                beta=round(beta, 4),
                correlation=round(correlation, 4),
                stock_volatility_annual=round(stock_volatility, 2),
                index_volatility_annual=round(index_volatility, 2),
                data_points=len(stock_returns),
                period_days=period_days,
            )

            self._cache.set("krx", cache_key, result, "daily_data")
            return result

        except Exception as e:
            logger.error(f"KRX beta calculation error: {e}")
            return error_response(str(e))

    def get_stock_name(self, stock_code: str) -> str:
        """Get stock name from code."""
        if not self._stock:
            return stock_code

        try:
            name = self._stock.get_market_ticker_name(stock_code)
            return name if name else stock_code
        except Exception:
            return stock_code

    def get_stock_list(self, market: str = "KOSPI") -> Dict[str, Any]:
        """
        Get list of stocks in a market.

        Args:
            market: Market name (KOSPI, KOSDAQ, KONEX)

        Returns:
            List of stock codes and names
        """
        if not self._stock:
            return error_response("pykrx not initialized", code="NOT_INITIALIZED")

        try:
            self._limiter.acquire("krx")

            date = self._format_date(datetime.now())
            tickers = self._stock.get_market_ticker_list(date, market=market)

            stocks = []
            for ticker in tickers[:100]:  # Limit to 100
                name = self._stock.get_market_ticker_name(ticker)
                stocks.append({"code": ticker, "name": name})

            return success_response(
                data=stocks,
                source="KRX",
                market=market,
            )

        except Exception as e:
            logger.error(f"KRX stock list error: {e}")
            return error_response(str(e))


def test_krx_adapter():
    """Test KRX adapter functionality."""
    logging.basicConfig(level=logging.INFO)

    adapter = KRXAdapter()

    if not adapter._stock:
        print("pykrx not initialized.")
        return

    print("=" * 60)
    print("KRX Adapter Test")
    print("=" * 60)

    # Use past dates to ensure data availability
    # pykrx may fail if dates are too recent or in the future
    end_date = "20250314"  # Use a known past date
    start_date = "20240314"

    # Test stock price
    print("\n1. Stock Price (Samsung Electronics)")
    result = adapter.get_stock_price("005930", start_date, end_date)
    if result.get("success"):
        latest = result.get("latest", {})
        print(f"   Records: {result.get('count', 0)}")
        if latest:
            # Find close value from various possible column names
            close_val = latest.get("close") or latest.get(4, 0)
            if close_val:
                print(f"   Latest Close: {close_val:,}")
    elif result.get("error"):
        print(f"   Error: {result.get('message', 'Unknown error')}")

    # Test market cap (might fail due to API issues)
    print("\n2. Market Cap")
    result = adapter.get_market_cap("005930", end_date)
    if result.get("success"):
        print(f"   Market Cap: {result.get('market_cap', 0):,}")
        print(f"   Shares: {result.get('shares_outstanding', 0):,}")
    elif result.get("error"):
        print(f"   Error: {result.get('message', 'Unknown error')}")

    # Test beta calculation (most complex, might fail)
    print("\n3. Beta Calculation")
    result = adapter.calculate_beta("005930", period_days=100)
    if result.get("success"):
        print(f"   Beta: {result.get('beta', 0):.4f}")
        print(f"   Correlation: {result.get('correlation', 0):.4f}")
        print(f"   Stock Volatility: {result.get('stock_volatility_annual', 0):.2f}%")
    elif result.get("error"):
        print(f"   Error: {result.get('message', 'Unknown error')}")

    # Test index data
    print("\n4. KOSPI Index")
    result = adapter.get_index_data("1001", start_date, end_date)
    if result.get("success"):
        latest = result.get("latest", {})
        if latest:
            close_val = latest.get("close", 0)
            print(f"   Latest Close: {close_val:,.2f}" if close_val else "   No data")
    elif result.get("error"):
        print(f"   Error: {result.get('message', 'Unknown error')}")

    print("\n" + "=" * 60)
    print("Test Complete")


if __name__ == "__main__":
    test_krx_adapter()
