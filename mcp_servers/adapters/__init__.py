"""
Adapters for external MCP servers.

Provides wrappers for external data sources:
- DART: Korean financial disclosure (OpenDART)
- KRX: Korean stock market data (pykrx)
- Crypto: Cryptocurrency data (CoinGecko)
- Yahoo: Global stock data (yfinance)
- FRED: US macroeconomic data (Federal Reserve)
"""
from .dart_adapter import DARTAdapter
from .krx_adapter import KRXAdapter
from .crypto_adapter import CryptoAdapter
from .yahoo_adapter import YahooAdapter
from .fred_adapter import FREDAdapter

__all__ = [
    "DARTAdapter",
    "KRXAdapter",
    "CryptoAdapter",
    "YahooAdapter",
    "FREDAdapter",
]
