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
from .quant_analysis_adapter import QuantAnalysisAdapter
from .backtest_adapter import BacktestAdapter

__all__ = [
    "DARTAdapter",
    "KRXAdapter",
    "CryptoAdapter",
    "YahooAdapter",
    "FREDAdapter",
    "QuantAnalysisAdapter",
    "BacktestAdapter",
]
