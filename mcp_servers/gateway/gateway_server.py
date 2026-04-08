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

        logger.info("Initializing Nexus Finance MCP Gateway v8.0 (Phase 14)...")

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
            # Phase 11 — Academic Alpha Core
            ("stat_arb", "mcp_servers.servers.stat_arb_server", "StatArbServer"),
            ("portfolio_advanced", "mcp_servers.servers.portfolio_advanced_server", "PortfolioAdvancedServer"),
            ("stochvol", "mcp_servers.servers.stochvol_server", "StochVolServer"),
            ("microstructure", "mcp_servers.servers.microstructure_server", "MicrostructureServer"),
            # Phase 12 — Crypto Quant + ML Pipeline
            ("crypto_quant", "mcp_servers.servers.crypto_quant_server", "CryptoQuantServer"),
            ("onchain_advanced", "mcp_servers.servers.onchain_advanced_server", "OnchainAdvancedServer"),
            ("ml_pipeline", "mcp_servers.servers.ml_pipeline_server", "MLPipelineServer"),
            ("alpha_research", "mcp_servers.servers.alpha_research_server", "AlphaResearchServer"),
        ]

        self._total_servers = len(SERVERS)
        for key, mod_path, cls_name in SERVERS:
            self._load_server(key, mod_path, cls_name)

        self._register_gateway_tools()
        self._register_prompts()
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
            return {"status": "online", "version": "8.0.0-phase14", "loaded": len(self._loaded), "failed": len(self._failed), "servers": self._loaded}

        @self.mcp.tool()
        async def list_available_tools(include_metadata: bool = False) -> dict:
            """List all tools. Set include_metadata=True to get domain/pattern/complexity info."""
            tools = await self.mcp.list_tools()
            if not include_metadata:
                tool_names = [t.name for t in tools]
                return {"total": len(tool_names), "tools": tool_names}
            try:
                from mcp_servers.core.tool_metadata import TOOL_METADATA
                enriched = []
                for t in tools:
                    meta = TOOL_METADATA.get(t.name, {})
                    enriched.append({"name": t.name, **meta})
                return {"total": len(enriched), "tools": enriched}
            except ImportError:
                tool_names = [t.name for t in tools]
                return {"total": len(tool_names), "tools": tool_names, "note": "tool_metadata not installed"}

        @self.mcp.tool()
        def api_call_stats() -> dict:
            """API 호출 통계 — 오늘 호출 수, 인기 도구, 세션 총 호출."""
            from mcp_servers.core.api_counter import get_counter
            return get_counter().get_stats()

        @self.mcp.tool()
        def list_tools_by_domain(domain: str) -> dict:
            """도메인별 도구 조회. 도메인: korean_macro, korean_equity, crypto, quant, alternative, news, real_economy, regulatory, infrastructure, global_markets, real_estate, visualization. 도구명 접두사(dart, ecos 등)로도 검색 가능."""
            try:
                from mcp_servers.core.tool_metadata import TOOL_METADATA
                # Exact domain match first
                matches = {k: v for k, v in TOOL_METADATA.items() if v.get("domain") == domain}
                # If no exact match, try prefix search (e.g., "dart" → tools starting with "dart_")
                if not matches:
                    prefix = domain.lower().rstrip("_") + "_"
                    matches = {k: v for k, v in TOOL_METADATA.items() if k.startswith(prefix)}
                # If still no match, try substring in domain name (e.g., "equity" → "korean_equity")
                if not matches:
                    matches = {k: v for k, v in TOOL_METADATA.items() if domain.lower() in v.get("domain", "")}
                domains = sorted(set(v.get("domain", "") for v in TOOL_METADATA.values()))
                resolved_domain = domain if any(v.get("domain") == domain for v in matches.values()) else f"{domain} (prefix/substring match)"
                return {"domain": resolved_domain, "count": len(matches), "tools": list(matches.keys()), "available_domains": domains}
            except ImportError:
                return {"error": True, "message": "tool_metadata not installed. Run scripts/generate_tool_metadata.py first."}

        @self.mcp.tool()
        def list_tools_by_pattern(pattern: str) -> dict:
            """입력 패턴별 도구 조회. 패턴: snapshot, stock_code, series, search, data_columns, composite"""
            try:
                from mcp_servers.core.tool_metadata import TOOL_METADATA
                matches = {k: v for k, v in TOOL_METADATA.items() if v.get("input_pattern") == pattern}
                patterns = sorted(set(v.get("input_pattern", "") for v in TOOL_METADATA.values()))
                return {"pattern": pattern, "count": len(matches), "tools": list(matches.keys()), "available_patterns": patterns}
            except ImportError:
                return {"error": True, "message": "tool_metadata not installed. Run scripts/generate_tool_metadata.py first."}

        @self.mcp.tool()
        async def tool_info(tool_name: str) -> dict:
            """특정 도구의 메타데이터 + 파라미터 스키마 + 실시간 description 조회."""
            try:
                from mcp_servers.core.tool_metadata import TOOL_METADATA
                meta = TOOL_METADATA.get(tool_name, {})
                # Get live schema from FastMCP tool registry
                tools = await self.mcp.list_tools()
                mcp_tool = next((t for t in tools if t.name == tool_name), None)
                if not meta and not mcp_tool:
                    return {"error": True, "message": f"Unknown tool: {tool_name}. Use list_available_tools() to see all tools."}
                result = {"tool": tool_name, **meta}
                if mcp_tool:
                    # Override stale TOOL_METADATA description with live docstring
                    if hasattr(mcp_tool, 'description') and mcp_tool.description:
                        result["description"] = mcp_tool.description
                    # Add parameter schema (inputSchema)
                    if hasattr(mcp_tool, 'parameters') and mcp_tool.parameters:
                        result["parameters"] = mcp_tool.parameters
                return result
            except ImportError:
                return {"error": True, "message": "tool_metadata not installed. Run scripts/generate_tool_metadata.py first."}

    def _register_prompts(self):
        """Register MCP prompt templates for common analysis workflows."""

        @self.mcp.prompt()
        def korean_company_analysis(stock_code: str = "005930") -> str:
            """한국 기업 종합 분석 워크플로우. 기업개황 → 재무제표 → 재무비율 → 밸류에이션."""
            return f"""한국 기업 종합 분석을 수행합니다. 종목코드: {stock_code}

다음 도구를 순서대로 호출하세요:

1. dart_company_info(stock_code="{stock_code}") — 기업개황 (업종, 대표자, 상장일)
2. dart_financial_statements(stock_code="{stock_code}") — 재무제표
3. dart_financial_ratios(stock_code="{stock_code}") — ROE, ROA, 영업이익률, 부채비율
4. dart_cash_flow(stock_code="{stock_code}") — 현금흐름표 (OCF, ICF, FCF)
5. dart_dividend(stock_code="{stock_code}") — 배당 현황
6. dart_major_shareholders(stock_code="{stock_code}") — 대주주 현황
7. dart_executives(stock_code="{stock_code}") — 임원 현황
8. stocks_history(stock_code="{stock_code}") — 주가 히스토리

분석 결과를 종합하여 투자 의견을 제시하세요."""

        @self.mcp.prompt()
        def macro_snapshot() -> str:
            """거시경제 종합 스냅샷. 한국 + 글로벌 비교."""
            return """거시경제 종합 분석을 수행합니다.

다음 도구를 순서대로 호출하세요:

1. ecos_get_macro_snapshot() — 한국 거시경제 현황 (금리, M2, GDP, 환율)
2. ecos_get_base_rate() — 기준금리 시계열
3. ecos_get_exchange_rate() — 주요 환율 (USD, EUR, JPY, CNY)
4. ecos_get_bond_yield() — 국고채 수익률 (3Y, 5Y, 10Y)
5. macro_korea_snapshot() — World Bank 국제비교 (20개 지표)
6. ecos_get_cpi() — 소비자물가지수

금리/물가/환율/성장 트렌드를 분석하고 경제 전망을 제시하세요."""

        @self.mcp.prompt()
        def crypto_arbitrage(coin: str = "BTC") -> str:
            """크립토 차익거래 분석. 김프 + 거래소비교 + 펀딩레이트."""
            return f"""크립토 차익거래 기회를 분석합니다. 코인: {coin}

다음 도구를 순서대로 호출하세요:

1. crypto_kimchi_premium(coin="{coin}") — 김치프리미엄 (한국 vs 글로벌 가격 차이)
2. crypto_exchange_compare(coin="{coin}") — 거래소간 가격 비교
3. crypto_ticker(exchange="binance", symbol="{coin}/USDT") — 바이낸스 시세
4. crypto_ticker(exchange="upbit", symbol="{coin}/KRW") — 업비트 시세
5. crypto_orderbook(exchange="binance", symbol="{coin}/USDT") — 오더북 분석
6. defi_fear_greed() — Fear & Greed Index

김프 수준, 거래소 간 스프레드, 시장 심리를 종합 분석하세요."""

    def _register_health_route(self):
        @self.mcp.custom_route("/health", methods=["GET"])
        async def health(request: Request) -> JSONResponse:
            uptime = int(time.time() - self._start_time)
            tools = await self.mcp.list_tools()
            tool_count = len(tools)
            return JSONResponse({
                "status": "ok",
                "version": "8.0.0-phase14",
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
