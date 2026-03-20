"""
Historical Crypto MCP Server — CryptoCompare (3 tools).
"""
import logging, sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from fastmcp import FastMCP
from mcp_servers.adapters.phase2_adapters import CryptoCompareAdapter

logger = logging.getLogger(__name__)

class HistCryptoServer:
    def __init__(self):
        self._cc = CryptoCompareAdapter()
        self.mcp = FastMCP("hist-crypto")
        self._register_tools()
        logger.info("Historical Crypto MCP Server initialized")

    def _register_tools(self):
        @self.mcp.tool()
        def crypto_daily_history(coin: str = "BTC", currency: str = "USD", days: int = 100) -> dict:
            """크립토 일봉 히스토리 (CryptoCompare). 5300+ 코인 지원."""
            return self._cc.get_daily_ohlcv(coin, currency, days)

        @self.mcp.tool()
        def crypto_hourly_history(coin: str = "BTC", currency: str = "USD", hours: int = 100) -> dict:
            """크립토 시간봉 히스토리."""
            return self._cc.get_hourly_ohlcv(coin, currency, hours)

        @self.mcp.tool()
        def crypto_top_coins(currency: str = "USD", limit: int = 20) -> dict:
            """시가총액 상위 코인 목록 (가격, 시총, 24h변동)."""
            return self._cc.get_top_coins(currency, limit)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    HistCryptoServer().mcp.run(transport="stdio")
