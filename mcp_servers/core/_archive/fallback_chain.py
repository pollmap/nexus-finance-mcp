"""
Fallback Chain for resilient data fetching.

Provides automatic fallback to alternative data sources when primary
sources fail or are unavailable.

NOTE: This module is not currently used by any server. Retained for future
multi-source fallback patterns. Servers currently call adapters directly.
"""
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FallbackSource:
    """Represents a data source in the fallback chain."""

    name: str
    fetch_func: Callable
    priority: int = 0  # Lower = higher priority
    enabled: bool = True
    last_error: Optional[str] = None
    success_count: int = 0
    failure_count: int = 0


# Default fallback chains by data type
DEFAULT_CHAINS: Dict[str, List[str]] = {
    # Korean stock prices
    "kr_stock_price": ["krx", "pykrx", "yahoo"],

    # Korean macro data
    "kr_macro": ["ecos", "fred"],

    # US stock prices
    "us_stock_price": ["yahoo", "sec"],

    # US disclosure/financials
    "us_disclosure": ["sec", "yahoo"],

    # Global housing prices
    "housing_price": ["bis", "fred", "local"],

    # Crypto prices
    "crypto_price": ["coingecko", "defillama"],

    # Korean real estate
    "kr_real_estate": ["rone", "kb_land", "ecos"],

    # CPI/Inflation
    "cpi": ["fred", "ecos", "bis"],

    # Money supply (M2)
    "money_supply": ["fred", "ecos"],
}


class FallbackChain:
    """
    Manages fallback chains for resilient data fetching.

    Usage:
        chain = FallbackChain()

        # Register sources
        chain.register("kr_stock_price", "krx", fetch_from_krx, priority=0)
        chain.register("kr_stock_price", "yahoo", fetch_from_yahoo, priority=1)

        # Fetch with automatic fallback
        result, source = chain.fetch("kr_stock_price", stock_code="005930")
    """

    def __init__(self, chains: Dict[str, List[str]] = None):
        """
        Initialize fallback chain manager.

        Args:
            chains: Custom chain definitions (uses DEFAULT_CHAINS if not provided)
        """
        self._chains: Dict[str, List[str]] = chains or DEFAULT_CHAINS.copy()
        self._sources: Dict[str, Dict[str, FallbackSource]] = {}

    def register(
        self,
        chain_name: str,
        source_name: str,
        fetch_func: Callable,
        priority: int = None,
    ) -> None:
        """
        Register a data source for a chain.

        Args:
            chain_name: Name of the fallback chain (e.g., 'kr_stock_price')
            source_name: Name of the source (e.g., 'krx')
            fetch_func: Function to fetch data (should accept **kwargs)
            priority: Priority (lower = higher). Auto-assigned from chain order if None.
        """
        if chain_name not in self._sources:
            self._sources[chain_name] = {}

        # Auto-assign priority based on chain order
        if priority is None:
            if chain_name in self._chains:
                chain_order = self._chains[chain_name]
                if source_name in chain_order:
                    priority = chain_order.index(source_name)
                else:
                    priority = len(chain_order)
            else:
                priority = len(self._sources[chain_name])

        self._sources[chain_name][source_name] = FallbackSource(
            name=source_name,
            fetch_func=fetch_func,
            priority=priority,
        )

        logger.debug(
            f"Registered source '{source_name}' for chain '{chain_name}' "
            f"(priority={priority})"
        )

    def unregister(self, chain_name: str, source_name: str) -> bool:
        """Remove a source from a chain."""
        if chain_name in self._sources and source_name in self._sources[chain_name]:
            del self._sources[chain_name][source_name]
            return True
        return False

    def enable_source(self, chain_name: str, source_name: str) -> None:
        """Enable a source."""
        if chain_name in self._sources and source_name in self._sources[chain_name]:
            self._sources[chain_name][source_name].enabled = True

    def disable_source(self, chain_name: str, source_name: str) -> None:
        """Disable a source (will be skipped in fallback)."""
        if chain_name in self._sources and source_name in self._sources[chain_name]:
            self._sources[chain_name][source_name].enabled = False

    def _get_sorted_sources(self, chain_name: str) -> List[FallbackSource]:
        """Get sources sorted by priority (enabled only)."""
        if chain_name not in self._sources:
            return []

        sources = [
            s for s in self._sources[chain_name].values()
            if s.enabled
        ]
        return sorted(sources, key=lambda s: s.priority)

    def fetch(
        self,
        chain_name: str,
        **kwargs,
    ) -> Tuple[Optional[Any], Optional[str]]:
        """
        Fetch data with automatic fallback.

        Args:
            chain_name: Name of the fallback chain
            **kwargs: Arguments to pass to fetch functions

        Returns:
            Tuple of (data, source_name) or (None, None) if all sources fail
        """
        sources = self._get_sorted_sources(chain_name)

        if not sources:
            logger.warning(f"No sources registered for chain '{chain_name}'")
            return None, None

        last_error = None

        for source in sources:
            try:
                logger.debug(f"Trying source '{source.name}' for '{chain_name}'")
                result = source.fetch_func(**kwargs)

                if result is not None:
                    source.success_count += 1
                    source.last_error = None
                    logger.debug(f"Success from '{source.name}'")
                    return result, source.name

            except Exception as e:
                source.failure_count += 1
                source.last_error = str(e)
                last_error = e
                logger.warning(
                    f"Source '{source.name}' failed for '{chain_name}': {e}"
                )
                continue

        logger.error(
            f"All sources failed for chain '{chain_name}'. "
            f"Last error: {last_error}"
        )
        return None, None

    async def fetch_async(
        self,
        chain_name: str,
        **kwargs,
    ) -> Tuple[Optional[Any], Optional[str]]:
        """
        Fetch data with automatic fallback (async version).

        Args:
            chain_name: Name of the fallback chain
            **kwargs: Arguments to pass to fetch functions

        Returns:
            Tuple of (data, source_name) or (None, None) if all sources fail
        """
        sources = self._get_sorted_sources(chain_name)

        if not sources:
            return None, None

        for source in sources:
            try:
                # Check if fetch_func is async
                if asyncio.iscoroutinefunction(source.fetch_func):
                    result = await source.fetch_func(**kwargs)
                else:
                    result = source.fetch_func(**kwargs)

                if result is not None:
                    source.success_count += 1
                    source.last_error = None
                    return result, source.name

            except Exception as e:
                source.failure_count += 1
                source.last_error = str(e)
                logger.warning(f"Source '{source.name}' failed: {e}")
                continue

        return None, None

    def get_chain_info(self, chain_name: str) -> Dict[str, Any]:
        """Get information about a chain and its sources."""
        if chain_name not in self._sources:
            return {"chain": chain_name, "sources": []}

        sources = []
        for source in self._get_sorted_sources(chain_name):
            sources.append({
                "name": source.name,
                "priority": source.priority,
                "enabled": source.enabled,
                "success_count": source.success_count,
                "failure_count": source.failure_count,
                "last_error": source.last_error,
            })

        return {
            "chain": chain_name,
            "sources": sources,
            "available_count": len([s for s in sources if s["enabled"]]),
        }

    def get_all_chains(self) -> List[str]:
        """Get all registered chain names."""
        return list(self._sources.keys())

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all chains."""
        stats = {}
        for chain_name in self._sources:
            stats[chain_name] = self.get_chain_info(chain_name)
        return stats


# Global fallback chain instance
_global_chain: Optional[FallbackChain] = None


def get_fallback_chain() -> FallbackChain:
    """Get or create the global fallback chain instance."""
    global _global_chain
    if _global_chain is None:
        _global_chain = FallbackChain()
    return _global_chain


def initialize_adapters(chain: FallbackChain = None) -> FallbackChain:
    """
    Initialize fallback chain with all available adapters.

    This function registers all available data source adapters
    with the appropriate fallback chains.

    Args:
        chain: FallbackChain instance (uses global if not provided)

    Returns:
        Configured FallbackChain instance
    """
    if chain is None:
        chain = get_fallback_chain()

    # Try to import and register adapters
    adapters_initialized = []

    # KRX Adapter (Korean stock data)
    try:
        from mcp_servers.adapters.krx_adapter import KRXAdapter
        krx = KRXAdapter()
        if krx._stock:
            chain.register("kr_stock_price", "pykrx", krx.get_stock_price, priority=0)
            chain.register("kr_stock_beta", "pykrx", krx.calculate_beta, priority=0)
            adapters_initialized.append("krx")
            logger.info("KRX adapter registered")
    except Exception as e:
        logger.warning(f"KRX adapter not available: {e}")

    # DART Adapter (Korean financial disclosure)
    try:
        from mcp_servers.adapters.dart_adapter import DARTAdapter
        dart = DARTAdapter()
        if dart._dart:
            chain.register("kr_financials", "dart", dart.get_financial_statements, priority=0)
            chain.register("kr_company_info", "dart", dart.get_company_info, priority=0)
            adapters_initialized.append("dart")
            logger.info("DART adapter registered")
    except Exception as e:
        logger.warning(f"DART adapter not available: {e}")

    # Crypto Adapter (CoinGecko)
    try:
        from mcp_servers.adapters.crypto_adapter import CryptoAdapter
        crypto = CryptoAdapter()
        chain.register("crypto_price", "coingecko", crypto.get_price, priority=0)
        chain.register("crypto_market", "coingecko", crypto.get_market_data, priority=0)
        adapters_initialized.append("crypto")
        logger.info("Crypto adapter registered")
    except Exception as e:
        logger.warning(f"Crypto adapter not available: {e}")

    # Yahoo Finance Adapter (Global stocks)
    try:
        from mcp_servers.adapters.yahoo_adapter import YahooAdapter
        yahoo = YahooAdapter()
        if yahoo._yf:
            chain.register("us_stock_price", "yahoo", yahoo.get_stock_price, priority=0)
            chain.register("us_stock_info", "yahoo", yahoo.get_stock_info, priority=0)
            chain.register("us_financials", "yahoo", yahoo.get_financials, priority=0)
            # Fallback for Korean stocks (via .KS suffix)
            chain.register("kr_stock_price", "yahoo", yahoo.get_stock_price, priority=1)
            adapters_initialized.append("yahoo")
            logger.info("Yahoo adapter registered")
    except Exception as e:
        logger.warning(f"Yahoo adapter not available: {e}")

    # FRED Adapter (US macro data)
    try:
        from mcp_servers.adapters.fred_adapter import FREDAdapter
        fred = FREDAdapter()
        if fred.api_key:
            chain.register("us_macro", "fred", fred.get_series, priority=0)
            chain.register("us_interest_rate", "fred", fred.get_fed_funds_rate, priority=0)
            chain.register("us_gdp", "fred", fred.get_gdp, priority=0)
            chain.register("us_inflation", "fred", fred.get_inflation, priority=0)
            adapters_initialized.append("fred")
            logger.info("FRED adapter registered")
    except Exception as e:
        logger.warning(f"FRED adapter not available: {e}")

    logger.info(f"Initialized adapters: {adapters_initialized}")
    return chain
