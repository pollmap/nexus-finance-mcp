"""
Crypto Adapter - Cryptocurrency Market Data.

Provides cryptocurrency data from CoinGecko API:
- Price data
- Market cap
- Trading volume
- Historical data

Uses free CoinGecko API (rate limited to 50 req/min).

Run standalone test: python -m mcp_servers.adapters.crypto_adapter
"""
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import time

import requests

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.core.cache_manager import CacheManager, get_cache
from mcp_servers.core.rate_limiter import RateLimiter, get_limiter

logger = logging.getLogger(__name__)


class CryptoAdapter:
    """
    Adapter for cryptocurrency data via CoinGecko API.

    Free tier: 50 requests/minute

    DEPRECATED: crypto_exchange_server uses CCXTAdapter instead.
    This adapter is retained for potential CoinGecko-specific use cases.
    """

    BASE_URL = "https://api.coingecko.com/api/v3"

    # Common coin IDs (top 50 by market cap)
    COINS = {
        "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
        "XRP": "ripple", "SOL": "solana", "ADA": "cardano",
        "DOGE": "dogecoin", "TRX": "tron", "AVAX": "avalanche-2",
        "DOT": "polkadot", "LINK": "chainlink", "MATIC": "matic-network",
        "TON": "the-open-network", "SHIB": "shiba-inu", "DAI": "dai",
        "LTC": "litecoin", "BCH": "bitcoin-cash", "UNI": "uniswap",
        "ATOM": "cosmos", "XLM": "stellar", "ETC": "ethereum-classic",
        "NEAR": "near", "ICP": "internet-computer", "APT": "aptos",
        "FIL": "filecoin", "STX": "blockstack", "ARB": "arbitrum",
        "IMX": "immutable-x", "OP": "optimism", "HBAR": "hedera-hashgraph",
        "VET": "vechain", "MKR": "maker", "AAVE": "aave",
        "ALGO": "algorand", "GRT": "the-graph", "FTM": "fantom",
        "SAND": "the-sandbox", "MANA": "decentraland", "THETA": "theta-token",
        "AXS": "axie-infinity", "EGLD": "elrond-erd-2", "EOS": "eos",
        "FLOW": "flow", "XTZ": "tezos", "CFX": "conflux-token",
        "NEO": "neo", "KLAY": "klay-token", "CRO": "crypto-com-chain",
        "USDT": "tether", "USDC": "usd-coin", "SUI": "sui",
    }

    def __init__(
        self,
        cache: CacheManager = None,
        limiter: RateLimiter = None,
    ):
        """
        Initialize Crypto adapter.

        Args:
            cache: Cache manager instance
            limiter: Rate limiter instance
        """
        self._cache = cache or get_cache()
        self._limiter = limiter or get_limiter()

        # Session for requests
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
        })

        logger.info("Crypto adapter initialized")

    MAX_RETRIES = 3

    def _make_request(self, endpoint: str, params: Dict = None, _retry_count: int = 0) -> Dict[str, Any]:
        """Make API request with rate limiting and bounded retries."""
        self._limiter.acquire("coingecko")

        url = f"{self.BASE_URL}/{endpoint}"

        try:
            response = self._session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return {"success": True, "data": response.json()}

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                if _retry_count >= self.MAX_RETRIES:
                    return {"error": True, "message": f"Rate limited by CoinGecko after {self.MAX_RETRIES} retries"}
                logger.warning(f"Rate limited by CoinGecko, retry {_retry_count + 1}/{self.MAX_RETRIES}...")
                time.sleep(60)
                return self._make_request(endpoint, params, _retry_count + 1)
            return {"error": True, "message": f"HTTP Error: {e}"}

        except requests.exceptions.RequestException as e:
            return {"error": True, "message": f"Request Error: {e}"}

    def get_price(
        self,
        coin_id: str,
        vs_currencies: str = "usd,krw",
    ) -> Dict[str, Any]:
        """
        Get current price for a coin.

        Args:
            coin_id: Coin ID (e.g., "bitcoin") or symbol (e.g., "BTC")
            vs_currencies: Comma-separated currencies

        Returns:
            Price data dict
        """
        # Convert symbol to ID if needed
        if coin_id.upper() in self.COINS:
            coin_id = self.COINS[coin_id.upper()]

        cache_key = {"method": "price", "coin": coin_id, "vs": vs_currencies}
        cached = self._cache.get("crypto", cache_key)
        if cached:
            return cached

        result = self._make_request(
            "simple/price",
            {
                "ids": coin_id,
                "vs_currencies": vs_currencies,
                "include_market_cap": "true",
                "include_24hr_vol": "true",
                "include_24hr_change": "true",
            }
        )

        if result.get("error"):
            return result

        data = result["data"].get(coin_id, {})

        response = {
            "success": True,
            "coin_id": coin_id,
            "prices": data,
            "timestamp": datetime.now().isoformat(),
        }

        self._cache.set("crypto", cache_key, response, "realtime_price")
        return response

    def get_market_data(
        self,
        vs_currency: str = "usd",
        order: str = "market_cap_desc",
        per_page: int = 100,
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Get market data for top coins.

        Args:
            vs_currency: Quote currency
            order: Sort order
            per_page: Results per page
            page: Page number

        Returns:
            Market data list
        """
        cache_key = {"method": "markets", "vs": vs_currency, "page": page}
        cached = self._cache.get("crypto", cache_key)
        if cached:
            return cached

        result = self._make_request(
            "coins/markets",
            {
                "vs_currency": vs_currency,
                "order": order,
                "per_page": per_page,
                "page": page,
                "sparkline": "false",
            }
        )

        if result.get("error"):
            return result

        response = {
            "success": True,
            "vs_currency": vs_currency,
            "count": len(result["data"]),
            "data": result["data"],
        }

        self._cache.set("crypto", cache_key, response, "realtime_price")
        return response

    def get_coin_detail(self, coin_id: str) -> Dict[str, Any]:
        """
        Get detailed info for a coin.

        Args:
            coin_id: Coin ID or symbol

        Returns:
            Coin detail dict
        """
        if coin_id.upper() in self.COINS:
            coin_id = self.COINS[coin_id.upper()]

        cache_key = {"method": "detail", "coin": coin_id}
        cached = self._cache.get("crypto", cache_key)
        if cached:
            return cached

        result = self._make_request(
            f"coins/{coin_id}",
            {
                "localization": "false",
                "tickers": "false",
                "community_data": "false",
                "developer_data": "false",
            }
        )

        if result.get("error"):
            return result

        data = result["data"]

        response = {
            "success": True,
            "coin_id": coin_id,
            "name": data.get("name"),
            "symbol": data.get("symbol", "").upper(),
            "market_cap_rank": data.get("market_cap_rank"),
            "market_data": {
                "current_price": data.get("market_data", {}).get("current_price", {}),
                "market_cap": data.get("market_data", {}).get("market_cap", {}),
                "total_volume": data.get("market_data", {}).get("total_volume", {}),
                "high_24h": data.get("market_data", {}).get("high_24h", {}),
                "low_24h": data.get("market_data", {}).get("low_24h", {}),
                "price_change_24h": data.get("market_data", {}).get("price_change_24h"),
                "price_change_percentage_24h": data.get("market_data", {}).get("price_change_percentage_24h"),
                "price_change_percentage_7d": data.get("market_data", {}).get("price_change_percentage_7d"),
                "price_change_percentage_30d": data.get("market_data", {}).get("price_change_percentage_30d"),
                "ath": data.get("market_data", {}).get("ath", {}),
                "ath_date": data.get("market_data", {}).get("ath_date", {}),
                "circulating_supply": data.get("market_data", {}).get("circulating_supply"),
                "total_supply": data.get("market_data", {}).get("total_supply"),
                "max_supply": data.get("market_data", {}).get("max_supply"),
            },
            "description": data.get("description", {}).get("en", "")[:500],
        }

        self._cache.set("crypto", cache_key, response, "daily_data")
        return response

    def get_historical_price(
        self,
        coin_id: str,
        vs_currency: str = "usd",
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get historical price data.

        Args:
            coin_id: Coin ID or symbol
            vs_currency: Quote currency
            days: Number of days (1, 7, 14, 30, 90, 180, 365, max)

        Returns:
            Historical price data
        """
        if coin_id.upper() in self.COINS:
            coin_id = self.COINS[coin_id.upper()]

        cache_key = {"method": "history", "coin": coin_id, "vs": vs_currency, "days": days}
        cached = self._cache.get("crypto", cache_key)
        if cached:
            return cached

        result = self._make_request(
            f"coins/{coin_id}/market_chart",
            {
                "vs_currency": vs_currency,
                "days": days,
            }
        )

        if result.get("error"):
            return result

        data = result["data"]

        # Process price data
        prices = []
        for timestamp, price in data.get("prices", []):
            prices.append({
                "date": datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M"),
                "price": price,
            })

        response = {
            "success": True,
            "coin_id": coin_id,
            "vs_currency": vs_currency,
            "days": days,
            "count": len(prices),
            "data": prices,
        }

        # Cache based on data freshness
        data_type = "realtime_price" if days <= 1 else "daily_data"
        self._cache.set("crypto", cache_key, response, data_type)
        return response

    def get_global_data(self) -> Dict[str, Any]:
        """
        Get global cryptocurrency market data.

        Returns:
            Global market stats
        """
        cache_key = {"method": "global"}
        cached = self._cache.get("crypto", cache_key)
        if cached:
            return cached

        result = self._make_request("global")

        if result.get("error"):
            return result

        data = result["data"].get("data", {})

        response = {
            "success": True,
            "data": {
                "total_market_cap": data.get("total_market_cap", {}),
                "total_volume": data.get("total_volume", {}),
                "market_cap_percentage": data.get("market_cap_percentage", {}),
                "market_cap_change_percentage_24h_usd": data.get("market_cap_change_percentage_24h_usd"),
                "active_cryptocurrencies": data.get("active_cryptocurrencies"),
                "markets": data.get("markets"),
                "updated_at": data.get("updated_at"),
            },
        }

        self._cache.set("crypto", cache_key, response, "realtime_price")
        return response

    def search_coins(self, query: str) -> Dict[str, Any]:
        """
        Search for coins by name or symbol.

        Args:
            query: Search query

        Returns:
            Matching coins
        """
        result = self._make_request("search", {"query": query})

        if result.get("error"):
            return result

        coins = result["data"].get("coins", [])[:20]

        return {
            "success": True,
            "query": query,
            "count": len(coins),
            "data": [
                {
                    "id": c.get("id"),
                    "name": c.get("name"),
                    "symbol": c.get("symbol", "").upper(),
                    "market_cap_rank": c.get("market_cap_rank"),
                }
                for c in coins
            ],
        }


def test_crypto_adapter():
    """Test Crypto adapter functionality."""
    logging.basicConfig(level=logging.INFO)

    adapter = CryptoAdapter()

    print("=" * 60)
    print("Crypto Adapter Test")
    print("=" * 60)

    # Test price
    print("\n1. Bitcoin Price")
    result = adapter.get_price("bitcoin")
    if result.get("success"):
        prices = result.get("prices", {})
        print(f"   USD: ${prices.get('usd', 0):,.2f}")
        print(f"   KRW: {prices.get('krw', 0):,.0f} KRW")
        print(f"   24h Change: {prices.get('usd_24h_change', 0):.2f}%")

    # Test market data
    print("\n2. Top 10 by Market Cap")
    result = adapter.get_market_data(per_page=10)
    if result.get("success"):
        for coin in result.get("data", [])[:5]:
            print(f"   {coin.get('market_cap_rank')}. {coin.get('symbol', '').upper()}: ${coin.get('current_price', 0):,.2f}")

    # Test coin detail
    print("\n3. Ethereum Detail")
    result = adapter.get_coin_detail("ethereum")
    if result.get("success"):
        print(f"   Name: {result.get('name')}")
        print(f"   Rank: {result.get('market_cap_rank')}")
        md = result.get("market_data", {})
        print(f"   Price: ${md.get('current_price', {}).get('usd', 0):,.2f}")

    # Test global data
    print("\n4. Global Market Data")
    result = adapter.get_global_data()
    if result.get("success"):
        data = result.get("data", {})
        total_mcap = data.get("total_market_cap", {}).get("usd", 0)
        print(f"   Total Market Cap: ${total_mcap/1e12:.2f}T")
        print(f"   BTC Dominance: {data.get('market_cap_percentage', {}).get('btc', 0):.1f}%")

    print("\n" + "=" * 60)
    print("Test Complete")


if __name__ == "__main__":
    test_crypto_adapter()
