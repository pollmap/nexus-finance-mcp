"""
Adapters for external MCP servers.

Provides wrappers for external data sources:
- DART: Korean financial disclosure (OpenDART)
- KRX: Korean stock market data (pykrx)
- Yahoo: Global stock data (yfinance)
"""
from .dart_adapter import DARTAdapter
from .krx_adapter import KRXAdapter
from .yahoo_adapter import YahooAdapter
from .quant_analysis_adapter import QuantAnalysisAdapter
from .backtest_adapter import BacktestAdapter

__all__ = [
    "DARTAdapter",
    "KRXAdapter",
    "YahooAdapter",
    "QuantAnalysisAdapter",
    "BacktestAdapter",
]
