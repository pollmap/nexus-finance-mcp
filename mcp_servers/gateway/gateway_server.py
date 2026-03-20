import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from fastmcp import FastMCP

logger = logging.getLogger(__name__)


class GatewayServer:
    def __init__(self):
        self.mcp = FastMCP("nexus-finance-mcp")
        self._loaded = []
        self._failed = []

        logger.info("Initializing Nexus Finance MCP Gateway v2.3 (Phase 3, flat)...")

        SERVERS = [
            # v2.0
            ("ecos", "mcp_servers.servers.ecos_server", "ECOSServer"),
            ("valuation", "mcp_servers.servers.valuation_server", "ValuationServer"),
            ("viz", "mcp_servers.servers.viz_server", "VizServer"),
            ("kosis", "mcp_servers.servers.kosis_server", "KOSISServer"),
            ("rone", "mcp_servers.servers.rone_server", "RONEServer"),
            ("stocks", "mcp_servers.servers.stocks_server", "StocksServer"),
            # Phase 1
            ("crypto", "mcp_servers.servers.crypto_exchange_server", "CryptoExchangeServer"),
            ("defi", "mcp_servers.servers.defi_server", "DefiServer"),
            ("onchain", "mcp_servers.servers.onchain_server", "OnChainServer"),
            ("news", "mcp_servers.servers.news_server", "NewsServer"),
            ("prediction", "mcp_servers.servers.prediction_server", "PredictionServer"),
            # Phase 2
            ("global_macro", "mcp_servers.servers.global_macro_server", "GlobalMacroServer"),
            ("global_news", "mcp_servers.servers.global_news_server", "GlobalNewsServer"),
            ("academic", "mcp_servers.servers.academic_server", "AcademicServer"),
            ("hist_crypto", "mcp_servers.servers.hist_crypto_server", "HistCryptoServer"),
            ("us_equity", "mcp_servers.servers.us_equity_server", "USEquityServer"),
            ("realestate_trans", "mcp_servers.servers.realestate_trans_server", "RealEstateTransServer"),
            ("fsc", "mcp_servers.servers.fsc_server", "FSCServer"),
            # Phase 3
            ("maritime", "mcp_servers.servers.maritime_server", "MaritimeServer"),
            ("aviation", "mcp_servers.servers.aviation_server", "AviationServer"),
            ("energy", "mcp_servers.servers.energy_server", "EnergyServer"),
            ("agriculture", "mcp_servers.servers.agriculture_server", "AgricultureServer"),
            ("trade", "mcp_servers.servers.trade_server", "TradeServer"),
            ("politics", "mcp_servers.servers.politics_server", "PoliticsServer"),
            ("patent", "mcp_servers.servers.patent_server", "PatentServer"),
            # Obsidian Vault (공유 지식 베이스)
            ("vault", "mcp_servers.servers.vault_server", "VaultServer"),
        ]

        for key, mod_path, cls_name in SERVERS:
            self._load_server(key, mod_path, cls_name)

        self._register_gateway_tools()
        logger.info(f"Gateway ready: {len(self._loaded)}/{len(self._loaded)+len(self._failed)} servers")

    def _load_server(self, key, module_path, class_name):
        try:
            import importlib
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            instance = cls()
            sub = instance.mcp
            copied = 0
            # FastMCP 3.x: tools stored in _local_provider._components
            if hasattr(sub, '_local_provider') and hasattr(sub._local_provider, '_components'):
                src = sub._local_provider._components
                dst = self.mcp._local_provider._components
                for comp_key, comp in src.items():
                    if comp_key.startswith('tool:'):
                        dst[comp_key] = comp
                        copied += 1
            # Fallback: FastMCP 2.x _tool_manager
            elif hasattr(sub, '_tool_manager') and hasattr(sub._tool_manager, '_tools'):
                for name, tool in sub._tool_manager._tools.items():
                    self.mcp._tool_manager._tools[name] = tool
                    copied += 1
            self._loaded.append(key)
            logger.info(f"  + {key} ({copied} tools)")
        except Exception as e:
            self._failed.append(key)
            logger.error(f"  x {key} failed: {e}")

    def _register_gateway_tools(self):
        @self.mcp.tool()
        def gateway_status() -> dict:
            """Gateway status."""
            return {"status": "online", "version": "2.3.0-phase3", "loaded": len(self._loaded), "failed": len(self._failed), "servers": self._loaded}

        @self.mcp.tool()
        def list_available_tools() -> dict:
            """List all tools."""
            comps = self.mcp._local_provider._components
            tool_names = [k.split(":")[1].split("@")[0] for k in comps if k.startswith("tool:")]
            return {"total": len(tool_names), "tools": tool_names}

    def run(self):
        self.mcp.run()

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    GatewayServer().run()

if __name__ == "__main__":
    main()
