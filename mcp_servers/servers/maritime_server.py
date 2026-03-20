"""Maritime MCP Server — 4 tools. NEXUS(voyager) 전담."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.phase3_adapters import MaritimeAdapter
logger = logging.getLogger(__name__)

class MaritimeServer:
    def __init__(self):
        self._a = MaritimeAdapter()
        self.mcp = FastMCP("maritime")
        self._register()
        logger.info("Maritime MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def maritime_bdi() -> dict:
            """Baltic Dry Index (FRED). 벌크선 운임 지표."""
            return self._a.get_bdi_proxy()
        @self.mcp.tool()
        def maritime_container_index() -> dict:
            """Freightos Baltic Container Index. 컨테이너 운임."""
            return self._a.get_container_index()
        @self.mcp.tool()
        def maritime_ports() -> dict:
            """한국 주요 항만 정보."""
            return self._a.get_port_stats()
        @self.mcp.tool()
        def maritime_freight_snapshot() -> dict:
            """해운 운임 종합 (BDI + Container)."""
            return {"bdi": self._a.get_bdi_proxy(), "container": self._a.get_container_index()}
