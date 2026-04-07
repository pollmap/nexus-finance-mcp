# Nexus Finance MCP Server

> **396 tools for global financial research & quant analysis** — Built for AI agents by [Luxon AI](https://github.com/pollmap).

64 servers, 396 tools covering Korean/global macro, equities, crypto, real estate, energy, climate, disasters, space weather, geopolitics, sentiment, quant analysis, time series, backtesting, factor models, portfolio optimization, 150-year historical data, GARCH volatility, PhD-level math, statistical arbitrage, Black-Litterman, HRP, Heston stochastic vol, Almgren-Chriss execution, market microstructure (VPIN/Kyle's λ), crypto derivatives (funding rate arb), on-chain analytics (MVRV/NVT), López de Prado ML pipeline, alpha research toolkit, and 33 visualization types — all through a single gateway.

## Documentation

> 상세 문서는 [`docs/`](docs/) 디렉토리 참조

| 문서 | 내용 |
|------|------|
| [Usage Guide](docs/USAGE_GUIDE.md) | 5가지 입력 패턴, 워크플로우 예제 |
| [Parsing Guide](docs/PARSING_GUIDE.md) | 응답 포맷 스펙, 파싱 전략 |
| [Tool Catalog](docs/TOOL_CATALOG.md) | 396도구 복잡도/도메인별 분류 |
| [Error Reference](docs/ERROR_REFERENCE.md) | 에러 코드, 재시도 전략 |
| [Architecture](docs/ARCHITECTURE.md) | 시스템 아키텍처, 캐싱, 레이트 리밋 |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | 운영 디버깅 가이드 |

## Quick Connect

### Claude Desktop / Claude Code (원격 접속)

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

- **Claude Desktop:** `%APPDATA%\Claude\claude_desktop_config.json` 에 추가 → 재시작
- **Claude Code:** `claude mcp add nexus-finance --transport streamable-http --url http://62.171.141.206/mcp`
- Bearer 토큰은 관리자에게 문의

### Self-hosted (직접 설치)

```bash
git clone https://github.com/pollmap/nexus-finance-mcp.git
cd nexus-finance-mcp
pip install -r requirements.txt
cp .env.template .env   # API 키 설정
python server.py --transport streamable-http --port 8100
```

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
| **Research** | 6 | `research_riss`, `research_nkis`, `research_prism`, `research_nl`, `research_nanet`, `research_scholar` | 한국 연구기관 (RISS, NKIS, PRISM, NL, NANET) |
| **Sentiment** | 5 | `sentiment_google_trends`, `sentiment_wiki_pageviews`, `sentiment_news_score`, `sentiment_fear_greed_multi`, `sentiment_keyword_correlation` | pytrends, Wikipedia, VADER |

### Real Economy — 31 tools

| Server | Count | Tools | Data Source |
|--------|-------|-------|------------|
| **Energy** | 9 | `energy_crude_oil`, `energy_natural_gas`, `energy_price_snapshot`, `energy_eia_series`, `energy_electricity`, `energy_bunker_fuel`, `energy_opec_production`, `energy_weather_forecast`, `energy_weather_cities` | EIA + Open-Meteo |
| **Agriculture** | 7 | `agri_kamis_prices`, `agri_fao_info`, `agri_product_codes`, `agri_snapshot`, `agri_fao_production`, `agri_fao_trade`, `agri_usda_psd` | KAMIS + FAO + USDA |
| **Maritime** | 4 | `maritime_bdi`, `maritime_container_index`, `maritime_ports`, `maritime_freight_snapshot` | FRED + 참조 |
| **Aviation** | 3 | `aviation_departures`, `aviation_live_aircraft`, `aviation_korea_airports` | OpenSky |
| **Trade** | 3 | `trade_korea_exports`, `trade_korea_imports`, `trade_country_codes` | UN Comtrade |
| **Consumer** | 4 | `consumer_us_retail`, `consumer_us_sentiment`, `consumer_us_housing`, `consumer_eu_hicp` | FRED + Eurostat |
| **Prediction** | 3 | `prediction_markets`, `prediction_market_detail`, `prediction_events` | Polymarket |

### Regulatory & Environment — 22 tools

| Server | Count | Tools | Data Source |
|--------|-------|-------|------------|
| **Regulation** | 4 | `regulation_eu_search`, `regulation_eu_text`, `regulation_key_financial`, `regulation_finra_info` | EUR-Lex + FINRA |
| **Politics** | 3 | `politics_bills`, `politics_recent_bills`, `politics_finance_bills` | 국회 API |
| **Health** | 5 | `health_fda_drugs`, `health_fda_recalls`, `health_clinical_trials`, `health_pubmed_search`, `health_who_indicators` | openFDA + NCBI + WHO |
| **Environ** | 2 | `environ_epa_air_quality`, `environ_carbon_price` | EPA + KRBN ETF |
| **Patent** | 2 | `patent_search`, `patent_trending` | KIPRIS |
| **Valuation** | 10 | `val_calculate_wacc`, `val_dcf_valuation`, `val_dcf_sample`, `val_sensitivity_analysis`, `val_peer_comparison`, `val_peer_comparison_sample`, `val_cross_market_comparison`, `val_normalize_gaap`, `val_get_market_assumptions`, `val_refresh_market_data` | DART + ECOS |

### Quant Alternative Data — 32 tools

| Server | Count | Tools | Data Source | API Key |
|--------|-------|-------|------------|---------|
| **Space Weather** | 5 | `space_sunspot_data`, `space_solar_flares`, `space_geomagnetic`, `space_solar_wind`, `space_cme_events` | SILSO + NASA + NOAA | 불필요 |
| **Disaster** | 6 | `disaster_earthquakes`, `disaster_volcanoes`, `disaster_wildfires`, `disaster_floods`, `disaster_active_events`, `disaster_history` | USGS + NASA EONET + GDACS | 불필요 |
| **Climate** | 6 | `climate_historical_weather`, `climate_temperature_anomaly`, `climate_extreme_events`, `climate_enso_index`, `climate_city_comparison`, `climate_crop_weather` | Open-Meteo + NASA GISS | 불필요 |
| **Conflict** | 5 | `conflict_active_wars`, `conflict_battle_deaths`, `conflict_country_risk`, `conflict_peace_index`, `conflict_geopolitical_events` | UCDP + GPI | 토큰 필요 |
| **Power Grid** | 5 | `power_grid_eu_generation`, `power_grid_eu_price`, `power_grid_carbon_intensity`, `power_grid_nuclear_status`, `power_grid_renewable_forecast` | ENTSO-E + EIA | 선택 |

### Analysis & Visualization — 38 tools

| Server | Count | Tools | Data Source |
|--------|-------|-------|------------|
| **Technical** | 5 | `ta_indicators`, `ta_rsi`, `ta_macd`, `ta_bollinger`, `ta_summary` | pykrx |
| **Viz** | 33 | **Basic(10):** `viz_line_chart`, `viz_bar_chart`, `viz_candlestick`, `viz_heatmap`, `viz_scatter`, `viz_waterfall`, `viz_dual_axis`, `viz_pie_chart`, `viz_correlation_matrix`, `viz_sensitivity_heatmap` · **Advanced(8):** `viz_radar`, `viz_bubble`, `viz_lollipop`, `viz_slope`, `viz_parallel`, `viz_combo`, `viz_gantt`, `viz_marimekko` · **Hierarchical(6):** `viz_treemap`, `viz_sunburst`, `viz_funnel`, `viz_gauge`, `viz_bullet`, `viz_sankey` · **Map(3):** `viz_map_choropleth`, `viz_map_scatter`, `viz_map_flow` · **Statistical(6):** `viz_area_chart`, `viz_stacked_bar`, `viz_histogram`, `viz_box_plot`, `viz_violin`, `viz_density` | Plotly + Matplotlib |

### Quant Analysis Engine (Phase 8) — 22 tools

| Server | Count | Tools | Description |
|--------|-------|-------|-------------|
| **Quant Analysis** | 8 | `quant_correlation`, `quant_lagged_correlation`, `quant_regression`, `quant_granger_causality`, `quant_cointegration`, `quant_var_decomposition`, `quant_event_study`, `quant_regime_detection` | 두 시리즈 간 관계 분석 |
| **Time Series** | 6 | `ts_decompose`, `ts_stationarity`, `ts_forecast`, `ts_seasonality`, `ts_changepoint`, `ts_cross_correlation` | 시계열 패턴 분석 및 예측 |
| **Backtest** | 8 | `backtest_run`, `backtest_compare`, `backtest_optimize`, `backtest_portfolio`, `backtest_benchmark`, `backtest_risk`, `backtest_signal_history`, `backtest_drawdown` | 수수료/세금 포함 실전 시뮬레이션 |

### Professional Quant (Phase 9) — 18 tools

| Server | Count | Tools | Description |
|--------|-------|-------|-------------|
| **Factor Engine** | 6 | `factor_score`, `factor_backtest`, `factor_correlation`, `factor_exposure`, `factor_timing`, `factor_custom` | Fama-French 팩터 분석 |
| **Signal Lab** | 6 | `signal_scan`, `signal_combine`, `signal_decay`, `signal_capacity`, `signal_regime_select`, `signal_walkforward` | 알파 시그널 발굴 + 앙상블 |
| **Portfolio Optimizer** | 6 | `portfolio_optimize`, `portfolio_risk_parity`, `portfolio_kelly`, `portfolio_correlation_matrix`, `portfolio_stress_test`, `portfolio_rebalance` | Markowitz, 리스크패리티, 켈리 |

### PhD-Level Quant Math (Phase 10) — 18 tools

| Server | Count | Tools | Description |
|--------|-------|-------|-------------|
| **Historical Data** | 6 | `historical_shiller`, `historical_french_factors`, `historical_nber_cycles`, `historical_fred_century`, `historical_gold_oil`, `historical_crisis_comparison` | 150년 역사 데이터 (Shiller 1871~, NBER 1854~) |
| **Volatility Model** | 6 | `vol_garch`, `vol_egarch`, `vol_surface`, `vol_regime`, `vol_forecast_ensemble`, `vol_vix_term` | GARCH, EGARCH, HMM 레짐, VIX 기간구조 |
| **Advanced Math** | 6 | `math_kalman`, `math_hurst`, `math_entropy`, `math_wavelets`, `math_fractal`, `math_monte_carlo` | 칼만필터, 허스트지수, 엔트로피, 웨이블릿, 프랙탈, MC |

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
| **Memory** | 5 | `memory_store`, `memory_search`, `memory_list`, `memory_forget`, `memory_stats` | SQLite + Ollama 벡터 |
| **Ontology** | 5 | `ontology_map`, `ontology_chain`, `ontology_impact`, `ontology_suggest`, `ontology_save` | 17개 도메인 그래프 |
| **Gateway** | 6 | `gateway_status`, `list_available_tools`, `api_call_stats`, `list_tools_by_domain`, `list_tools_by_pattern`, `tool_info` | 내부 메타 |

## Example Workflows

### 퀀트 분석 파이프라인

```
1. 데이터 수집:  space_sunspot_data() + ecos_get_base_rate() + stocks_history("005930")
2. 상관 분석:    quant_lagged_correlation(흑점, 코스피, max_lag=24)
3. 인과 검정:    quant_granger_causality(금리, 아파트, max_lag=12)
4. 시계열 예측:  ts_forecast(아파트지수, horizon=12)
5. 전략 백테스트: backtest_run(삼성전자, "RSI_oversold", 5년)
6. 리스크 분석:  backtest_risk(삼성전자, "Momentum") → VaR/CVaR/Sharpe
7. 시각화:       viz_line_chart(equity_curve) + viz_heatmap(correlation_matrix)
```

### 크립토 퀀트 파이프라인

```
1. 시장 구조:    crypto_market_structure("BTC") + cquant_open_interest("BTC")
2. 펀딩 분석:    cquant_funding_rate("BTC") + cquant_basis_term("BTC")
3. 온체인:       onchain_adv_mvrv("BTC") + onchain_adv_hodl_waves("BTC")
4. ML 시그널:    mlpipe_triple_barrier(data) + mlpipe_meta_label(data)
5. 알파 검증:    alpha_decay(signal) + alpha_capacity(signal)
6. 실행 최적화:  stochvol_exec_optimal(trade_params)
```

### 내장 백테스트 전략 (수수료 0.18% + 세금 0.18%)

| Strategy | Logic | Best For |
|----------|-------|----------|
| `RSI_oversold` | RSI < 30 매수, > 70 매도 | 과매도 반등 |
| `MACD_crossover` | MACD-시그널 돌파 | 추세 전환 |
| `Bollinger_bounce` | 하단밴드 터치 | 변동성 회귀 |
| `MA_cross` | 20/50 골든크로스 | 중기 추세 |
| `Mean_reversion` | 평균 -2σ 매수 | 평균회귀 |
| `Momentum` | N일 수익률 양수 | 모멘텀 |

## API Keys

| Key | Required | Coverage |
|-----|----------|----------|
| `BOK_ECOS_API_KEY` | **Yes** | 한국은행 30+ 경제지표 |
| `DART_API_KEY` | **Yes** | 금감원 기업공시 20도구 |
| `KOSIS_API_KEY` | Recommended | 통계청 + 부동산원 |
| `FRED_API_KEY` | Recommended | 미국 연준 + FRED 초장기 |
| `FINNHUB_API_KEY` | Optional | 미국 주식 |
| `ETHERSCAN_API_KEY` | Optional | 이더리움 온체인 |
| `EIA_API_KEY` | Optional | 미국 에너지 |
| `NAVER_CLIENT_ID/SECRET` | Optional | 네이버 뉴스 |
| `KIS_API_KEY` | Optional | 한국투자증권 실시간 |
| `NASA_API_KEY` | Optional | NASA (DEMO_KEY 가능) |

- Phase 7 대체데이터 (우주/재해/기후/센티멘트) — 대부분 **API 키 불필요**
- Phase 8-12 퀀트 도구 — **추가 API 키 불필요** (기존 패키지로 구현)

## Architecture

```
Client (Claude Desktop / Claude Code / HTTP)
  │
  ▼
nginx (443/HTTPS) ─── IP 제한 + Basic Auth
  │
  ▼
Gateway (127.0.0.1:8100, streamable-http)
  │
  ├── 64 MCP Servers (FastMCP mount)
  ├── Tool Metadata (domain/pattern/complexity)
  ├── API Counter (호출 통계)
  └── Bearer Token Auth (opt-in)
```

## Data Policy

**Real data only.** No sample data, mock data, or fake data — ever.
API 호출 실패 시 가짜 데이터로 대체하지 않고 명확한 에러 메시지를 반환합니다.

## License

MIT

---

*v8.0.0-phase14 | 396 tools / 64 servers | [Luxon AI Agent Network](https://github.com/pollmap)*
