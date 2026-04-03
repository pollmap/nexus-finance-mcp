"""Consumer/Retail MCP Server — US Retail, EU Stats, Sentiment (4 tools)."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.consumer_adapter import ConsumerAdapter
logger = logging.getLogger(__name__)

class ConsumerServer:
    def __init__(self):
        self._a = ConsumerAdapter()
        self.mcp = FastMCP("consumer")
        self._register()
        logger.info("Consumer MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def consumer_us_retail(limit: int = 60) -> dict:
            """미국 소매판매 데이터 (FRED/RSXFS). 월별."""
            return self._a.get_us_retail_sales(limit)
        @self.mcp.tool()
        def consumer_us_sentiment(limit: int = 60) -> dict:
            """미시간대 소비자심리지수 (FRED/UMCSENT)."""
            return self._a.get_us_consumer_sentiment(limit)
        @self.mcp.tool()
        def consumer_us_housing(limit: int = 60) -> dict:
            """미국 주택착공 건수 (FRED/HOUST)."""
            return self._a.get_us_housing_starts(limit)
        @self.mcp.tool()
        def consumer_eu_hicp(limit: int = 30) -> dict:
            """유로존 소비자물가 조화지수 HICP (Eurostat)."""
            return self._a.get_eu_hicp(limit)
