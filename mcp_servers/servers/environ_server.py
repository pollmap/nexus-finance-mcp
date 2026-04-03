"""Environment/Utilities MCP Server — EPA, Carbon Pricing (2 tools)."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.environ_adapter import EnvironAdapter
logger = logging.getLogger(__name__)

class EnvironServer:
    def __init__(self):
        self._a = EnvironAdapter()
        self.mcp = FastMCP("environ")
        self._register()
        logger.info("Environment MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def environ_epa_air_quality(state: str = "36", year: int = 2024) -> dict:
            """EPA 대기질 데이터 (미국 주별 오존/PM2.5). state: 36=NY, 06=CA."""
            return self._a.get_epa_air_quality(state, year)
        @self.mcp.tool()
        def environ_carbon_price(limit: int = 30) -> dict:
            """탄소배출권 가격 (KRBN ETF proxy)."""
            return self._a.get_carbon_price(limit)
