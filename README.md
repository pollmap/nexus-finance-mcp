<p align="center">
  <h1 align="center">Nexus Finance MCP Server</h1>
  <p align="center">
    <strong>The most comprehensive financial MCP server — 396 tools across 64 servers</strong>
  </p>
  <p align="center">
    <a href="#quick-start"><img src="https://img.shields.io/badge/Quick_Start-blue?style=for-the-badge" alt="Quick Start"></a>
    <a href="#tools-396"><img src="https://img.shields.io/badge/Tools-396-green?style=for-the-badge" alt="396 Tools"></a>
    <a href="#api-keys"><img src="https://img.shields.io/badge/API_Keys-optional-orange?style=for-the-badge" alt="API Keys"></a>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/version-v8.0.0--phase14-blue" alt="Version">
    <img src="https://img.shields.io/badge/servers-64-brightgreen" alt="64 Servers">
    <img src="https://img.shields.io/badge/tools-396-brightgreen" alt="396 Tools">
    <img src="https://img.shields.io/badge/python-3.12+-blue" alt="Python 3.12+">
    <img src="https://img.shields.io/badge/transport-streamable--http-purple" alt="Transport">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
    <a href="https://smithery.ai"><img src="https://img.shields.io/badge/Smithery-registered-orange" alt="Smithery"></a>
  </p>
</p>

---

Korean/global macro, equities, crypto, real estate, energy, climate, disasters, space weather, geopolitics, sentiment, quant analysis, time series, backtesting, factor models, portfolio optimization, 150-year historical data, GARCH volatility, PhD-level math, statistical arbitrage, Black-Litterman, HRP, Heston stochastic vol, Almgren-Chriss execution, market microstructure (VPIN/Kyle's λ), crypto derivatives (funding rate arb), on-chain analytics (MVRV/NVT), López de Prado ML pipeline, alpha research toolkit, and 33 visualization types — all through a single MCP gateway.

Built for AI agents by [Luxon AI](https://github.com/pollmap).

## Table of Contents

- [Features](#features)
- [Supported Clients](#supported-clients)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Tool Overview](#tool-overview)
- [Tools (396)](#tools-396)
- [Response Format](#response-format)
- [Example Workflows](#example-workflows)
- [API Keys](#api-keys)
- [Architecture](#architecture)
- [Documentation](#documentation)
- [Data Policy](#data-policy)
- [Contributing](#contributing)
- [Star History](#star-history)
- [License](#license)

## Features

| Feature | Description |
|---------|-------------|
| **396 Tools / 64 Servers** | World's largest financial MCP — Korean + global markets, quant, crypto, alternative data |
| **Single Gateway** | One endpoint, all tools — FastMCP mount architecture with streamable-http transport |
| **Real Data Only** | Zero mock/sample data. Every response comes from live APIs with graceful error handling |
| **PhD-Level Quant** | GARCH, Heston, Black-Litterman, HRP, Kalman filter, López de Prado ML pipeline |
| **150+ Year History** | Shiller (1871~), NBER cycles (1854~), French factors (1926~), FRED century-scale |
| **33 Chart Types** | Line, candlestick, heatmap, treemap, sankey, choropleth map, violin, radar, and more |
| **Semantic Memory** | Hybrid vector + BM25 search, Obsidian Vault integration, ontology graph |
| **Smithery Ready** | Listed on [Smithery](https://smithery.ai) marketplace — plug and play |
| **Bearer Auth** | Optional token-based authentication for production deployments |

## Supported Clients

Works with any MCP-compatible client:

| Client | Transport | Setup |
|--------|-----------|-------|
| **Claude Desktop** | streamable-http | Add to `claude_desktop_config.json` ([details](#option-1-remote-hosted)) |
| **Claude Code** | streamable-http | `claude mcp add nexus-finance ...` ([details](#option-1-remote-hosted)) |
| **Cursor** | streamable-http | Settings → MCP → Add server URL |
| **Windsurf** | streamable-http | Settings → MCP Servers → Add |
| **Cline (VS Code)** | streamable-http | Extension settings → MCP Servers |
| **Continue** | streamable-http | `config.json` → mcpServers |
| **ChatGPT (Actions)** | HTTP | Via OpenAPI schema wrapper |
| **Custom HTTP Client** | streamable-http | `POST http://host:8100/mcp` |
| **Smithery** | stdio | One-click install on [smithery.ai](https://smithery.ai) |

> Any client supporting [MCP streamable-http transport](https://modelcontextprotocol.io) can connect.

## Quick Start

### Option 1: Remote (Hosted)

Connect instantly — no installation required.

**Claude Code (one command):**

```bash
claude mcp add nexus-finance --transport streamable-http --url http://62.171.141.206/mcp --header "Authorization: Bearer YOUR_TOKEN"
```

**Claude Desktop (`claude_desktop_config.json`):**

```json
{
  "mcpServers": {
    "nexus-finance": {
      "url": "http://62.171.141.206/mcp",
      "transport": "streamable-http",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

> **Config location:** Windows `%APPDATA%\Claude\claude_desktop_config.json` · macOS `~/Library/Application Support/Claude/claude_desktop_config.json`
>
> Bearer 토큰은 관리자에게 문의하세요.

### Option 2: Self-Hosted

```bash
git clone https://github.com/pollmap/nexus-finance-mcp.git
cd nexus-finance-mcp
pip install -r requirements.txt
cp .env.template .env   # Fill in your API keys
python server.py --transport streamable-http --port 8100
```

### Option 3: Docker

```bash
docker build -t nexus-finance-mcp .
docker run -p 8100:8100 --env-file .env nexus-finance-mcp
```

### Option 4: Smithery

Search "nexus-finance" on [smithery.ai](https://smithery.ai) and install directly.

## Installation

### Requirements

- **Python 3.12+**
- API keys (see [API Keys](#api-keys) — most tools work without any keys)

### Environment Variables

Copy `.env.template` to `.env` and configure:

```bash
# === Required (core Korean data) ===
BOK_ECOS_API_KEY=        # 한국은행 ECOS (https://ecos.bok.or.kr)
DART_API_KEY=            # OpenDART (https://opendart.fss.or.kr)

# === Recommended ===
KOSIS_API_KEY=           # 통계청 KOSIS (https://kosis.kr)
FRED_API_KEY=            # Federal Reserve FRED (https://fred.stlouisfed.org)

# === Optional (expand coverage) ===
FINNHUB_API_KEY=         # 미국 주식 (https://finnhub.io)
ETHERSCAN_API_KEY=       # 이더리움 온체인 (https://etherscan.io)
EIA_API_KEY=             # 미국 에너지 (https://www.eia.gov)
NAVER_CLIENT_ID=         # 네이버 뉴스 (https://developers.naver.com)
NAVER_CLIENT_SECRET=
KIS_API_KEY=             # 한국투자증권 실시간
NASA_API_KEY=            # NASA (DEMO_KEY works without registration)
ENTSOE_API_KEY=          # ENTSO-E European Grid
ACLED_API_KEY=           # ACLED Conflict Data

# === Server Config ===
MCP_TRANSPORT=streamable-http
MCP_HOST=127.0.0.1
MCP_PORT=8100
MCP_AUTH_TOKEN=          # Bearer token (optional)
```

### Transport Options

| Transport | Command | Use Case |
|-----------|---------|----------|
| `streamable-http` | `python server.py --transport streamable-http --port 8100` | Production (Claude Desktop, remote) |
| `stdio` | `python server.py --transport stdio` | Local (Smithery, direct pipe) |

## Tool Overview

At a glance — 396 tools across 15 domains:

| Domain | Servers | Tools | Highlights |
|--------|---------|-------|------------|
| **Korean Economy** | 5 | 41 | ECOS, DART 20종, KOSIS, FSC, KRX/pykrx |
| **Korean Real Estate** | 2 | 8 | 아파트 실거래가, 매매/전세 지수, PIR |
| **Global Markets** | 6 | 37 | US/Asia/India equities, SEC EDGAR, EDINET, FRED |
| **Crypto & DeFi** | 6 | 36 | CCXT 100+ exchanges, on-chain, DeFi TVL, funding rate |
| **News & Research** | 6 | 31 | Naver, GDELT, RSS 14개, arXiv, RISS, Semantic Scholar |
| **Real Economy** | 7 | 31 | Energy, agriculture, maritime, aviation, trade, consumer |
| **Regulatory & Environment** | 6 | 26 | Valuation DCF, EU regulation, FDA, EPA, patents |
| **Quant Alternative Data** | 5 | 32 | Space weather, disasters, climate, conflict, power grid |
| **Analysis & Visualization** | 2 | 38 | Technical indicators + 33 chart types (Plotly/Matplotlib) |
| **Quant Engine** | 3 | 22 | Correlation, Granger, ARIMA, backtest with 6 strategies |
| **Professional Quant** | 3 | 18 | Factor engine, signal lab, portfolio optimization |
| **PhD-Level Math** | 3 | 18 | GARCH, Kalman, Hurst, wavelets, 150-year history |
| **Academic Alpha** | 4 | 24 | Stat arb, Black-Litterman, Heston, microstructure VPIN |
| **Crypto Quant + ML** | 4 | 24 | López de Prado ML, alpha research, funding arb |
| **Infrastructure** | 5 | 25 | Obsidian Vault, semantic memory, ontology, gateway meta |
| | **64** | **396** | |

> Full tool details with function names below. See also [Tool Catalog](docs/TOOL_CATALOG.md) for domain/complexity classification.

## Tools (396)

### Korean Economy (한국 경제) — 41 tools

| Server | Count | Tools | Data Source |
|--------|-------|-------|------------|
| **ECOS** | 9 | `ecos_search_stat_list`, `ecos_get_stat_data`, `ecos_get_base_rate`, `ecos_get_m2`, `ecos_get_gdp`, `ecos_get_macro_snapshot`, `ecos_get_exchange_rate`, `ecos_get_bond_yield`, `ecos_list_indicators` | 한국은행 ECOS |
| **KOSIS** | 5 | `kosis_search_tables`, `kosis_get_population`, `kosis_get_unemployment`, `kosis_get_housing_price`, `kosis_get_table` | 통계청 KOSIS |
| **DART** | 20 | `dart_company_info`, `dart_financial_statements`, `dart_financial_ratios`, `dart_major_shareholders`, `dart_search_company`, `dart_cash_flow`, `dart_dividend`, `dart_executives`, `dart_executive_compensation`, `dart_shareholder_changes`, `dart_capital_changes`, `dart_mergers`, `dart_convertible_bonds`, `dart_treasury_stock`, `dart_related_party`, `dart_5pct_disclosure`, `dart_disclosure_search`, `dart_events`, `dart_full_financial`, `dart_document` | 금융감독원 OpenDART |
| **FSC** | 2 | `fsc_stock_price`, `fsc_bond_price` | 금융위원회 data.go.kr |
| **Stocks** | 5 | `stocks_quote`, `stocks_search`, `stocks_history`, `stocks_beta`, `stocks_market_overview` | KIS + pykrx + Yahoo |

### Korean Real Estate (부동산) — 8 tools

| Server | Count | Tools | Data Source |
|--------|-------|-------|------------|
| **R-ONE** | 6 | `rone_get_apt_price_index`, `rone_get_jeonse_index`, `rone_get_pir`, `rone_get_price_comparison`, `rone_get_market_summary`, `rone_list_regions` | KOSIS (부동산원 orgId=408) |
| **Realestate** | 2 | `realestate_apt_trades`, `realestate_sigungu_codes` | 국토부 MOLIT |

### Global Markets — 37 tools

| Server | Count | Tools | Data Source |
|--------|-------|-------|------------|
| **Global Macro** | 10 | `macro_oecd`, `macro_imf`, `macro_bis`, `macro_worldbank`, `macro_datasets`, `macro_search_indicators`, `macro_country_compare`, `macro_fred`, `macro_fred_search`, `macro_korea_snapshot` | OECD, IMF, BIS, World Bank, FRED |
| **US Equity** | 4 | `us_stock_quote`, `us_company_profile`, `us_economic_calendar`, `us_market_news` | Finnhub |
| **Asia Market** | 8 | `asia_china_quote`, `asia_china_index`, `asia_china_history`, `asia_taiwan_quote`, `asia_taiwan_index`, `asia_hk_quote`, `asia_hk_index`, `asia_market_overview` | Yahoo Finance |
| **India** | 3 | `india_stock_quote`, `india_index`, `india_stock_history` | Yahoo Finance |
| **SEC** | 8 | `sec_company_filings`, `sec_company_facts`, `sec_xbrl_concept`, `sec_list_concepts`, `sec_filing_text`, `sec_submission_metadata`, `sec_insider_transactions`, `sec_institutional_holders` | SEC EDGAR |
| **EDINET** | 4 | `edinet_filings`, `edinet_company`, `edinet_document`, `edinet_search` | 일본 EDINET |

### Crypto & DeFi — 36 tools

| Server | Count | Tools | Data Source |
|--------|-------|-------|------------|
| **Crypto Exchange** | 14 | `crypto_ticker`, `crypto_orderbook`, `crypto_ohlcv`, `crypto_all_tickers`, `crypto_kimchi_premium`, `crypto_exchange_compare`, `crypto_volume_ranking`, `crypto_spread`, `crypto_list_exchanges`, `crypto_list_symbols`, `crypto_recent_trades`, `crypto_funding_rate`, `crypto_ticker_24h`, `crypto_market_structure` | CCXT (100+ exchanges) |
| **Hist Crypto** | 3 | `crypto_daily_history`, `crypto_hourly_history`, `crypto_top_coins` | CoinGecko |
| **DeFi** | 4 | `defi_protocols`, `defi_protocol_detail`, `defi_chains`, `defi_feargreed` | DefiLlama |
| **OnChain** | 3 | `onchain_balance`, `onchain_transactions`, `onchain_gas` | Etherscan |
| **OnChain Advanced** | 6 | `onchain_adv_exchange_flow`, `onchain_adv_mvrv`, `onchain_adv_realized_cap`, `onchain_adv_hodl_waves`, `onchain_adv_whale_alert`, `onchain_adv_nvt` | Blockchain.com |
| **Crypto Quant** | 6 | `cquant_funding_rate`, `cquant_basis_term`, `cquant_funding_arb`, `cquant_open_interest`, `cquant_liquidation_levels`, `cquant_carry_backtest` | CCXT Derivatives |

### News & Research — 31 tools

| Server | Count | Tools | Data Source |
|--------|-------|-------|------------|
| **News** | 4 | `news_search`, `news_trend`, `news_market_sentiment`, `news_keyword_volume` | Naver API |
| **Global News** | 3 | `global_news_search`, `global_news_timeline`, `global_news_korea` | GDELT |
| **RSS** | 4 | `rss_financial_news`, `rss_search_news`, `rss_available_feeds`, `rss_crypto_news` | Bloomberg, WSJ, CNBC, Reuters, FT 등 14개 피드 |
| **Academic** | 9 | `academic_arxiv`, `academic_semantic_scholar`, `academic_openalex`, `academic_multi_search`, `academic_trending`, `academic_paper_detail`, `academic_citations`, `academic_author`, `academic_concepts` | arXiv, Semantic Scholar, OpenAlex |
| **Research** | 6 | `research_riss`, `research_nkis`, `research_prism`, `research_nl`, `research_nanet`, `research_scholar` | RISS, NKIS, PRISM, 국립중앙도서관, NANET |
| **Sentiment** | 5 | `sentiment_google_trends`, `sentiment_wiki_pageviews`, `sentiment_news_score`, `sentiment_fear_greed_multi`, `sentiment_keyword_correlation` | pytrends, Wikipedia, VADER |

### Real Economy — 31 tools

| Server | Count | Tools | Data Source |
|--------|-------|-------|------------|
| **Energy** | 9 | `energy_crude_oil`, `energy_natural_gas`, `energy_price_snapshot`, `energy_eia_series`, `energy_electricity`, `energy_bunker_fuel`, `energy_opec_production`, `energy_weather_forecast`, `energy_weather_cities` | EIA + Open-Meteo |
| **Agriculture** | 7 | `agri_kamis_prices`, `agri_fao_info`, `agri_product_codes`, `agri_snapshot`, `agri_fao_production`, `agri_fao_trade`, `agri_usda_psd` | KAMIS + FAO + USDA |
| **Maritime** | 4 | `maritime_bdi`, `maritime_container_index`, `maritime_ports`, `maritime_freight_snapshot` | FRED |
| **Aviation** | 3 | `aviation_departures`, `aviation_live_aircraft`, `aviation_korea_airports` | OpenSky |
| **Trade** | 3 | `trade_korea_exports`, `trade_korea_imports`, `trade_country_codes` | UN Comtrade |
| **Consumer** | 4 | `consumer_us_retail`, `consumer_us_sentiment`, `consumer_us_housing`, `consumer_eu_hicp` | FRED + Eurostat |
| **Prediction** | 3 | `prediction_markets`, `prediction_market_detail`, `prediction_events` | Polymarket |

### Regulatory & Environment — 26 tools

| Server | Count | Tools | Data Source |
|--------|-------|-------|------------|
| **Valuation** | 10 | `val_calculate_wacc`, `val_dcf_valuation`, `val_dcf_sample`, `val_sensitivity_analysis`, `val_peer_comparison`, `val_peer_comparison_sample`, `val_cross_market_comparison`, `val_normalize_gaap`, `val_get_market_assumptions`, `val_refresh_market_data` | DART + ECOS |
| **Regulation** | 4 | `regulation_eu_search`, `regulation_eu_text`, `regulation_key_financial`, `regulation_finra_info` | EUR-Lex + FINRA |
| **Politics** | 3 | `politics_bills`, `politics_recent_bills`, `politics_finance_bills` | 국회 API |
| **Health** | 5 | `health_fda_drugs`, `health_fda_recalls`, `health_clinical_trials`, `health_pubmed_search`, `health_who_indicators` | openFDA + NCBI + WHO |
| **Environ** | 2 | `environ_epa_air_quality`, `environ_carbon_price` | EPA + KRBN ETF |
| **Patent** | 2 | `patent_search`, `patent_trending` | KIPRIS |

### Quant Alternative Data — 32 tools

| Server | Count | Tools | Data Source | API Key |
|--------|-------|-------|------------|---------|
| **Space Weather** | 5 | `space_sunspot_data`, `space_solar_flares`, `space_geomagnetic`, `space_solar_wind`, `space_cme_events` | SILSO + NASA + NOAA | Not required |
| **Disaster** | 6 | `disaster_earthquakes`, `disaster_volcanoes`, `disaster_wildfires`, `disaster_floods`, `disaster_active_events`, `disaster_history` | USGS + NASA EONET + GDACS | Not required |
| **Climate** | 6 | `climate_historical_weather`, `climate_temperature_anomaly`, `climate_extreme_events`, `climate_enso_index`, `climate_city_comparison`, `climate_crop_weather` | Open-Meteo + NASA GISS | Not required |
| **Conflict** | 5 | `conflict_active_wars`, `conflict_battle_deaths`, `conflict_country_risk`, `conflict_peace_index`, `conflict_geopolitical_events` | UCDP + GPI | Token required |
| **Power Grid** | 5 | `power_grid_eu_generation`, `power_grid_eu_price`, `power_grid_carbon_intensity`, `power_grid_nuclear_status`, `power_grid_renewable_forecast` | ENTSO-E + EIA | Optional |

### Analysis & Visualization — 38 tools

| Server | Count | Tools | Data Source |
|--------|-------|-------|------------|
| **Technical** | 5 | `ta_indicators`, `ta_rsi`, `ta_macd`, `ta_bollinger`, `ta_summary` | pykrx |
| **Viz** | 33 | **Basic(10):** `viz_line_chart`, `viz_bar_chart`, `viz_candlestick`, `viz_heatmap`, `viz_scatter`, `viz_waterfall`, `viz_dual_axis`, `viz_pie_chart`, `viz_correlation_matrix`, `viz_sensitivity_heatmap` · **Advanced(8):** `viz_radar`, `viz_bubble`, `viz_lollipop`, `viz_slope`, `viz_parallel`, `viz_combo`, `viz_gantt`, `viz_marimekko` · **Hierarchical(6):** `viz_treemap`, `viz_sunburst`, `viz_funnel`, `viz_gauge`, `viz_bullet`, `viz_sankey` · **Map(3):** `viz_map_choropleth`, `viz_map_scatter`, `viz_map_flow` · **Statistical(6):** `viz_area_chart`, `viz_stacked_bar`, `viz_histogram`, `viz_box_plot`, `viz_violin`, `viz_density` | Plotly + Matplotlib |

### Quant Analysis Engine (Phase 8) — 22 tools

| Server | Count | Tools | Description |
|--------|-------|-------|-------------|
| **Quant Analysis** | 8 | `quant_correlation`, `quant_lagged_correlation`, `quant_regression`, `quant_granger_causality`, `quant_cointegration`, `quant_var_decomposition`, `quant_event_study`, `quant_regime_detection` | Relationship analysis between any two series |
| **Time Series** | 6 | `ts_decompose`, `ts_stationarity`, `ts_forecast`, `ts_seasonality`, `ts_changepoint`, `ts_cross_correlation` | Pattern analysis & ARIMA forecasting |
| **Backtest** | 8 | `backtest_run`, `backtest_compare`, `backtest_optimize`, `backtest_portfolio`, `backtest_benchmark`, `backtest_risk`, `backtest_signal_history`, `backtest_drawdown` | Full simulation with fees & taxes |

### Professional Quant (Phase 9) — 18 tools

| Server | Count | Tools | Description |
|--------|-------|-------|-------------|
| **Factor Engine** | 6 | `factor_score`, `factor_backtest`, `factor_correlation`, `factor_exposure`, `factor_timing`, `factor_custom` | Fama-French style factor analysis |
| **Signal Lab** | 6 | `signal_scan`, `signal_combine`, `signal_decay`, `signal_capacity`, `signal_regime_select`, `signal_walkforward` | Alpha signal discovery + ensemble |
| **Portfolio Optimizer** | 6 | `portfolio_optimize`, `portfolio_risk_parity`, `portfolio_kelly`, `portfolio_correlation_matrix`, `portfolio_stress_test`, `portfolio_rebalance` | Markowitz, risk parity, Kelly criterion |

### PhD-Level Quant Math (Phase 10) — 18 tools

| Server | Count | Tools | Description |
|--------|-------|-------|-------------|
| **Historical Data** | 6 | `historical_shiller`, `historical_french_factors`, `historical_nber_cycles`, `historical_fred_century`, `historical_gold_oil`, `historical_crisis_comparison` | 150-year data (Shiller 1871~, NBER 1854~) |
| **Volatility Model** | 6 | `vol_garch`, `vol_egarch`, `vol_surface`, `vol_regime`, `vol_forecast_ensemble`, `vol_vix_term` | GARCH, EGARCH, HMM regime, VIX term structure |
| **Advanced Math** | 6 | `math_kalman`, `math_hurst`, `math_entropy`, `math_wavelets`, `math_fractal`, `math_monte_carlo` | Kalman filter, Hurst, entropy, wavelets, fractal, MC |

### Academic Alpha Core (Phase 11) — 24 tools

| Server | Count | Tools | Key Methods |
|--------|-------|-------|-------------|
| **Stat Arb** | 6 | `stat_arb_ou_fit`, `stat_arb_pairs_distance`, `stat_arb_spread_zscore`, `stat_arb_copula`, `stat_arb_halflife`, `stat_arb_backtest` | OU MLE, Gatev distance, Clayton/Gumbel copula |
| **Portfolio Advanced** | 6 | `portadv_rmt_clean`, `portadv_black_litterman`, `portadv_hrp`, `portadv_johansen`, `portadv_info_theory`, `portadv_compare` | Marchenko-Pastur, BL posterior, HRP, transfer entropy |
| **StochVol** | 6 | `stochvol_heston`, `stochvol_jump_diffusion`, `stochvol_var_premium`, `stochvol_exec_optimal`, `stochvol_exec_vwap`, `stochvol_impact` | Heston calibration, Merton jump, Almgren-Chriss |
| **Microstructure** | 6 | `micro_kyle_lambda`, `micro_lee_ready`, `micro_roll_spread`, `micro_amihud`, `micro_orderbook_imbalance`, `micro_toxicity` | Kyle's λ, VPIN, trade classification |

### Crypto Quant + ML Pipeline (Phase 12) — 24 tools

| Server | Count | Tools | Key Methods |
|--------|-------|-------|-------------|
| **Crypto Quant** | 6 | `cquant_funding_rate`, `cquant_basis_term`, `cquant_funding_arb`, `cquant_open_interest`, `cquant_liquidation_levels`, `cquant_carry_backtest` | Perp funding, cash-and-carry, leverage cascade |
| **OnChain Advanced** | 6 | `onchain_adv_exchange_flow`, `onchain_adv_mvrv`, `onchain_adv_realized_cap`, `onchain_adv_hodl_waves`, `onchain_adv_whale_alert`, `onchain_adv_nvt` | MVRV, NVT, HODL waves, BDD ratio |
| **ML Pipeline** | 6 | `mlpipe_volume_bars`, `mlpipe_frac_diff`, `mlpipe_triple_barrier`, `mlpipe_meta_label`, `mlpipe_purged_cv`, `mlpipe_feature_importance` | López de Prado AFML full pipeline |
| **Alpha Research** | 6 | `alpha_turnover`, `alpha_decay`, `alpha_crowding`, `alpha_capacity`, `alpha_regime_switch`, `alpha_combine` | Grinold-Kahn, IC decay, IR optimization |

### Infrastructure & Knowledge — 25 tools

| Server | Count | Tools | Data Source |
|--------|-------|-------|------------|
| **Vault** | 6 | `vault_search`, `vault_read`, `vault_list`, `vault_recent`, `vault_tags`, `vault_write` | Obsidian Vault (PARA) |
| **Vault Index** | 3 | `vault_index`, `vault_semantic_search`, `vault_related` | Ollama bge-m3 |
| **Memory** | 5 | `memory_store`, `memory_search`, `memory_list`, `memory_forget`, `memory_stats` | SQLite + Ollama vector |
| **Ontology** | 5 | `ontology_map`, `ontology_chain`, `ontology_impact`, `ontology_suggest`, `ontology_save` | 17-domain knowledge graph |
| **Gateway** | 6 | `gateway_status`, `list_available_tools`, `api_call_stats`, `list_tools_by_domain`, `list_tools_by_pattern`, `tool_info` | Internal meta |

## Response Format

All tools return structured JSON. Example:

### `stocks_quote("005930")` — Samsung Electronics

```json
{
  "name": "삼성전자",
  "code": "005930",
  "price": 67800,
  "change": -200,
  "change_pct": -0.29,
  "volume": 12345678,
  "market_cap": 404700000000000,
  "per": 12.5,
  "pbr": 1.2,
  "high_52w": 88800,
  "low_52w": 53000
}
```

### `ecos_get_base_rate()`

```json
{
  "indicator": "한국은행 기준금리",
  "value": 2.75,
  "unit": "%",
  "date": "2025-11",
  "source": "BOK ECOS"
}
```

### Error Response

```json
{
  "error": true,
  "message": "DART API key not configured. Set DART_API_KEY in .env"
}
```

> All error responses include a descriptive `message` field. No fake/fallback data is ever returned.

## Example Workflows

### 1. Korean Equity Research

```
stocks_quote("005930")                          → 삼성전자 현재가
dart_financial_statements("삼성전자", "2024")    → 재무제표
dart_financial_ratios("삼성전자")                → ROE, PER, PBR
val_dcf_valuation("005930")                     → DCF 적정가
val_peer_comparison("005930")                   → 피어 비교
viz_bar_chart(peer_data)                        → 시각화
```

### 2. Macro Analysis Pipeline

```
ecos_get_base_rate()                            → 한국 기준금리
macro_fred("FEDFUNDS")                          → 미국 기준금리
quant_granger_causality(fed_rate, bok_rate)      → 인과관계 검정
ts_forecast(bok_rate, horizon=12)               → 금리 예측
viz_dual_axis(bok_rate, fed_rate)               → 한미 금리 비교 차트
```

### 3. Crypto Quant Pipeline

```
crypto_market_structure("BTC")                  → BTC 시장 구조
cquant_funding_rate("BTC")                      → 펀딩비
cquant_basis_term("BTC")                        → 선현물 괴리
onchain_adv_mvrv("BTC")                         → MVRV 비율
mlpipe_triple_barrier(btc_data)                 → 트리플 배리어 레이블링
alpha_decay(signal)                             → 알파 디케이 분석
stochvol_exec_optimal(trade_params)             → 최적 실행
```

### 4. Alternative Data & Quant

```
space_sunspot_data()                            → 흑점 데이터 (1818~)
quant_lagged_correlation(sunspot, kospi, 24)    → 흑점-코스피 시차상관
climate_enso_index()                            → ENSO 지수
disaster_earthquakes()                          → 최근 지진
conflict_country_risk("KOR")                    → 한국 지정학 리스크
```

### Built-in Backtest Strategies

| Strategy | Logic | Best For |
|----------|-------|----------|
| `RSI_oversold` | RSI < 30 buy, > 70 sell | Mean reversion |
| `MACD_crossover` | MACD-signal crossover | Trend reversal |
| `Bollinger_bounce` | Lower band touch | Volatility reversion |
| `MA_cross` | 20/50 golden cross | Medium-term trend |
| `Mean_reversion` | Mean -2σ buy | Statistical reversion |
| `Momentum` | N-day positive return | Momentum |

> All backtests include commission (0.18%) and tax (0.18%) by default.

## API Keys

| Key | Required | Coverage | Get it at |
|-----|----------|----------|-----------|
| `BOK_ECOS_API_KEY` | **Required** | 한국은행 30+ macro indicators | [ecos.bok.or.kr](https://ecos.bok.or.kr) |
| `DART_API_KEY` | **Required** | 금감원 20 disclosure tools | [opendart.fss.or.kr](https://opendart.fss.or.kr) |
| `KOSIS_API_KEY` | Recommended | 통계청 + 부동산원 | [kosis.kr](https://kosis.kr) |
| `FRED_API_KEY` | Recommended | US Fed + century-scale data | [fred.stlouisfed.org](https://fred.stlouisfed.org) |
| `FINNHUB_API_KEY` | Optional | US equities | [finnhub.io](https://finnhub.io) |
| `ETHERSCAN_API_KEY` | Optional | Ethereum on-chain | [etherscan.io](https://etherscan.io) |
| `EIA_API_KEY` | Optional | US energy data | [eia.gov](https://www.eia.gov) |
| `NAVER_CLIENT_ID/SECRET` | Optional | Korean news | [developers.naver.com](https://developers.naver.com) |
| `KIS_API_KEY` | Optional | Korean securities realtime | [apiportal.koreainvestment.com](https://apiportal.koreainvestment.com) |
| `NASA_API_KEY` | Optional | NASA (DEMO_KEY works) | [api.nasa.gov](https://api.nasa.gov) |

> **200+ tools require NO API keys** — quant analysis, backtesting, factor models, volatility, math, ML pipeline, visualizations, and most alternative data sources work out of the box.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Client Layer                       │
│  Claude Desktop · Claude Code · HTTP · Smithery       │
└────────────────────────┬────────────────────────────┘
                         │
                    HTTPS (443)
                         │
┌────────────────────────▼────────────────────────────┐
│              nginx Reverse Proxy                      │
│         IP Restriction + Basic Auth                   │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│           MCP Gateway (127.0.0.1:8100)               │
│              streamable-http transport                 │
│                                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ 64 Servers   │  │ Tool Metadata │  │ API Counter │ │
│  │ (FastMCP     │  │ (domain,      │  │ (daily      │ │
│  │  mount)      │  │  pattern,     │  │  stats)     │ │
│  │              │  │  complexity)  │  │             │ │
│  └─────────────┘  └──────────────┘  └─────────────┘ │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │              Bearer Token Auth (opt-in)          │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Gateway Meta Tools

The gateway itself provides 6 tools for discovery and monitoring:

```
gateway_status()                    → Server health + version
list_available_tools()              → All 396 tool names
list_tools_by_domain("crypto")      → Filter by domain
list_tools_by_pattern("snapshot")   → Filter by input pattern
tool_info("stocks_quote")           → Tool schema + metadata
api_call_stats()                    → Daily call counts
```

## Documentation

| Document | Description |
|----------|-------------|
| [Usage Guide](docs/USAGE_GUIDE.md) | 5 input patterns, workflow examples |
| [Tool Catalog](docs/TOOL_CATALOG.md) | All 396 tools by domain/complexity |
| [Parsing Guide](docs/PARSING_GUIDE.md) | Response format spec, parsing strategies |
| [Error Reference](docs/ERROR_REFERENCE.md) | Error codes, retry strategies |
| [Architecture](docs/ARCHITECTURE.md) | System architecture, caching, rate limiting |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Operational debugging guide |

## Data Policy

**Real data only.** No sample data, mock data, or fake data — ever.

- API call failure → clear error message with cause
- Missing API key → graceful fallback + log warning
- Rate limit hit → retry guidance in error response
- Never substitutes fake data for failed requests

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/new-server`)
3. Add server in `mcp_servers/servers/` + adapter in `mcp_servers/adapters/`
4. Register in `gateway_server.py` SERVERS list
5. Test: `python -c "from mcp_servers.servers.your_server import YourServer; s = YourServer(); print(len(s.mcp.tools))"`
6. Submit PR

See [Architecture docs](docs/ARCHITECTURE.md) for the server development guide.

## Star History

<a href="https://star-history.com/#pollmap/nexus-finance-mcp&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=pollmap/nexus-finance-mcp&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=pollmap/nexus-finance-mcp&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=pollmap/nexus-finance-mcp&type=Date" />
 </picture>
</a>

## License

MIT

---

<p align="center">
  <strong>v8.0.0-phase14</strong> · 396 tools · 64 servers · Built by <a href="https://github.com/pollmap">Luxon AI</a>
</p>
