import logging
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# === Auth Token (opt-in) ===
MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "")
AUTH_EXEMPT_PATHS = {"/health", "/favicon.ico"}


class GatewayServer:
    def __init__(self):
        self.mcp = FastMCP("nexus-finance-mcp")
        self._loaded = []
        self._failed = []

        logger.info("Initializing Nexus Finance MCP Gateway v7.0 (Phase 10)...")

        SERVERS = [
            # v2.0
            ("ecos", "mcp_servers.servers.ecos_server", "ECOSServer"),
            ("dart", "mcp_servers.servers.dart_server", "DARTServer"),
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
            # Phase 4 — v3.0 확장
            ("research", "mcp_servers.servers.research_server", "ResearchServer"),
            ("sec", "mcp_servers.servers.sec_server", "SECServer"),
            ("health", "mcp_servers.servers.health_server", "HealthServer"),
            ("consumer", "mcp_servers.servers.consumer_server", "ConsumerServer"),
            ("environ", "mcp_servers.servers.environ_server", "EnvironServer"),
            # Phase 5 — 글로벌 공시
            ("edinet", "mcp_servers.servers.edinet_server", "EDINETServer"),
            # Phase 6 — 글로벌 시장 + 뉴스 + 기술지표 + 규제
            ("rss", "mcp_servers.servers.rss_server", "RSSServer"),
            ("technical", "mcp_servers.servers.technical_server", "TechnicalServer"),
            ("asia_market", "mcp_servers.servers.asia_market_server", "AsiaMarketServer"),
            ("india", "mcp_servers.servers.india_server", "IndiaServer"),
            ("regulation", "mcp_servers.servers.regulation_server", "RegulationServer"),
            # Obsidian Vault (공유 지식 베이스)
            ("vault", "mcp_servers.servers.vault_server", "VaultServer"),
            # Memory & Vault Index (벡터 검색)
            ("memory", "mcp_servers.servers.memory_server", "MemoryServer"),
            ("vault_index", "mcp_servers.servers.vault_index_server", "VaultIndexServer"),
            # Phase 7 — 퀀트 대체데이터
            ("space_weather", "mcp_servers.servers.space_weather_server", "SpaceWeatherServer"),
            ("disaster", "mcp_servers.servers.disaster_server", "DisasterServer"),
            ("conflict", "mcp_servers.servers.conflict_server", "ConflictServer"),
            ("climate", "mcp_servers.servers.climate_server", "ClimateServer"),
            ("power_grid", "mcp_servers.servers.power_grid_server", "PowerGridServer"),
            ("sentiment", "mcp_servers.servers.sentiment_server", "SentimentServer"),
            # Ontology — 데이터 존재론/인과 관계
            ("ontology", "mcp_servers.servers.ontology_server", "OntologyServer"),
            # Phase 8 — 퀀트 분석 엔진
            ("quant_analysis", "mcp_servers.servers.quant_analysis_server", "QuantAnalysisServer"),
            ("timeseries", "mcp_servers.servers.timeseries_server", "TimeseriesServer"),
            ("backtest", "mcp_servers.servers.backtest_server", "BacktestServer"),
            # Phase 9 — 프로페셔널 퀀트
            ("factor_engine", "mcp_servers.servers.factor_engine_server", "FactorEngineServer"),
            ("signal_lab", "mcp_servers.servers.signal_lab_server", "SignalLabServer"),
            ("portfolio_optimizer", "mcp_servers.servers.portfolio_optimizer_server", "PortfolioOptimizerServer"),
            # Phase 10 — 박사급 퀀트 수학 + 150년 역사
            ("historical_data", "mcp_servers.servers.historical_data_server", "HistoricalDataServer"),
            ("volatility_model", "mcp_servers.servers.volatility_model_server", "VolatilityModelServer"),
            ("advanced_math", "mcp_servers.servers.advanced_math_server", "AdvancedMathServer"),
        ]

        self._total_servers = len(SERVERS)
        for key, mod_path, cls_name in SERVERS:
            self._load_server(key, mod_path, cls_name)

        self._register_gateway_tools()
        self._register_health_route()
        self._register_auth_middleware()
        self._start_time = time.time()
        logger.info(f"Gateway ready: {len(self._loaded)}/{self._total_servers} servers")

    def _load_server(self, key, module_path, class_name):
        try:
            import importlib
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            instance = cls()
            sub = instance.mcp
            # Use FastMCP 3.x public mount() API (no namespace = flat merge)
            self.mcp.mount(sub)
            self._loaded.append(key)
            logger.info(f"  + {key} (mounted)")
        except Exception as e:
            self._failed.append(key)
            logger.error(f"  x {key} failed: {e}")

    def _register_gateway_tools(self):
        @self.mcp.tool()
        def gateway_status() -> dict:
            """Gateway status."""
            return {"status": "online", "version": "7.0.0-phase10", "loaded": len(self._loaded), "failed": len(self._failed), "servers": self._loaded}

        @self.mcp.tool()
        async def list_available_tools() -> dict:
            """List all tools."""
            tools = await self.mcp.list_tools()
            tool_names = [t.name for t in tools]
            return {"total": len(tool_names), "tools": tool_names}

        @self.mcp.tool()
        def api_call_stats() -> dict:
            """API 호출 통계 — 오늘 호출 수, 인기 도구, 세션 총 호출."""
            from mcp_servers.core.api_counter import get_counter
            return get_counter().get_stats()

    def _register_health_route(self):
        @self.mcp.custom_route("/health", methods=["GET"])
        async def health(request: Request) -> JSONResponse:
            uptime = int(time.time() - self._start_time)
            tools = await self.mcp.list_tools()
            tool_count = len(tools)
            return JSONResponse({
                "status": "ok",
                "version": "7.0.0-phase10",
                "loaded_servers": len(self._loaded),
                "failed_servers": len(self._failed),
                "tool_count": tool_count,
                "uptime_seconds": uptime,
            })

    def _register_auth_middleware(self):
        """Log auth token status. Actual auth is handled by Nginx or MCP client config."""
        if MCP_AUTH_TOKEN:
            logger.info(f"MCP_AUTH_TOKEN is set ({len(MCP_AUTH_TOKEN)} chars) — use as Bearer token for external access")
        else:
            logger.warning("MCP_AUTH_TOKEN not set — running without authentication")

    def run(self):
        self.mcp.run()

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    GatewayServer().run()

if __name__ == "__main__":
    main()
