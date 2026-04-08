# Changelog

All notable changes to Nexus Finance MCP are documented here.

## v8.0.0-phase14 (2026-04)

**396 tools / 64 servers**

### Added
- DART expanded (20 disclosure tools)
- CCXT multi-exchange support (100+ exchanges)
- SEC EDGAR expanded filings
- ECOS expanded macro indicators
- FRED Federal Reserve integration
- Public MCP endpoint (no auth, CORS-enabled)
- CONNECT.md connection guide
- public-deploy.sh (domain + SSL automation)

---

## v8.0.0-phase13 (2026-03)

**380+ tools / 64 servers**

### Added
- Documentation overhaul: 9 docs created (ARCHITECTURE, USAGE_GUIDE, TOOL_CATALOG, PARSING_GUIDE, ERROR_REFERENCE, TROUBLESHOOTING, COMPETITIVE_ANALYSIS, COVERAGE_AUDIT, MCP_OVERVIEW)
- Adapter standardization: 48/48 adapters follow consistent response format

### Changed
- All adapters unified to `{"success": true, "data": ...}` / `{"error": true, "message": ...}` pattern

---

## v8.0.0-phase12 (2026-03)

**364 tools / 64 servers**

### Added
- `crypto_quant` — Funding rate analysis, basis term structure, funding arbitrage
- `onchain_advanced` — MVRV, NVT, realized cap, SOPR
- `ml_pipeline` — Lopez de Prado ML: triple barrier, meta-labeling, purged CV
- `alpha_research` — Alpha decay analysis, signal half-life

---

## v8.0.0-phase11 (2026-03)

**340+ tools / 60 servers**

### Added
- `stat_arb` — Pairs trading, cointegration, Ornstein-Uhlenbeck
- `portfolio_advanced` — Black-Litterman, HRP, risk parity
- `stochvol` — Stochastic volatility models (SABR, Heston simulation)
- `microstructure` — VPIN, Kyle's lambda, Amihud illiquidity

---

## v8.0.0-phase10 (2026-03)

**320+ tools / 56 servers**

### Added
- `historical_data` — 150+ year data: Shiller (1871~), NBER cycles (1854~), French factors (1926~)
- `volatility_model` — GARCH family, Heston calibration, volatility surface
- `advanced_math` — Hurst exponent, wavelet analysis, Kalman filter, entropy measures

---

## v8.0.0-phase9 (2026-03)

**300+ tools / 53 servers**

### Added
- `factor_engine` — Multi-factor scoring (momentum, value, quality, size, volatility)
- `signal_lab` — Signal scanning, combining, walk-forward optimization
- `portfolio_optimizer` — Markowitz, minimum variance, max Sharpe, equal risk contribution

### Changed
- Introduced `BaseMCPServer` abstract base class (14 servers adopted)
- Added `core/base_server.py` with caching and rate limiting helpers

---

## v7.0.0-phase8 (2026-02)

**270+ tools / 50 servers**

### Added
- `quant_analysis` — Correlation, Granger causality, cointegration, regression
- `timeseries` — ARIMA, decomposition, forecasting, change-point detection
- `backtest` — 6 built-in strategies, commission/tax modeling, drawdown analysis

---

## v7.0.0-phase7 (2026-02)

**240+ tools / 47 servers**

### Added
- `space_weather` — Sunspot data, geomagnetic storms, solar activity
- `disaster` — GDACS alerts, earthquake/flood monitoring
- `conflict` — ACLED conflict events, country risk scoring
- `climate` — ENSO index, greenhouse gas, temperature anomalies
- `power_grid` — ENTSO-E European electricity grid data
- `sentiment` — Google Trends integration
- `ontology` — Data ontology and causal relationship graph

---

## v6.0.0-phase6 (2026-02)

**200+ tools / 40 servers**

### Added
- `rss` — 14 financial RSS feeds (FT, Bloomberg, Reuters, etc.)
- `technical` — 20+ technical analysis indicators (RSI, MACD, Bollinger, etc.)
- `asia_market` — Asian equity markets (Japan, HK, China)
- `india` — India NSE/BSE market data
- `regulation` — EU SFDR, taxonomy, regulatory filings
- `vault` — Obsidian Vault integration (read/write/search)
- `memory` — Hybrid vector + BM25 semantic search
- `vault_index` — Full-text vault indexing

---

## v5.0.0-phase5 (2026-02)

### Added
- `edinet` — Japan EDINET financial disclosure system

---

## v4.0.0-phase4 (2026-01)

### Added
- `research` — RISS (Korean academic), PubMed, patent search
- `sec` — SEC EDGAR (US filings, 10-K, 10-Q)
- `health` — FDA approvals, WHO data
- `consumer` — Consumer sentiment, retail data
- `environ` — EPA air quality, environmental data

---

## v3.0.0-phase3 (2026-01)

### Added
- `maritime` — AIS ship tracking, port data
- `aviation` — Flight tracking, airport statistics
- `energy` — EIA oil/gas prices, OPEC data
- `agriculture` — KAMIS agricultural prices
- `trade` — UN Comtrade international trade data
- `politics` — Government policy announcements
- `patent` — Patent search and analysis

---

## v2.0.0-phase2 (2025-12)

### Added
- `global_macro` — FRED, BIS, World Bank macro data
- `global_news` — GDELT global news events
- `academic` — arXiv, Semantic Scholar paper search
- `hist_crypto` — Historical cryptocurrency data
- `us_equity` — US equity data (Yahoo Finance, Finnhub)
- `realestate_trans` — Korean real estate transactions
- `fsc` — Korean Financial Services Commission data

---

## v1.0.0-phase1 (2025-11)

### Added
- `crypto` — CCXT multi-exchange crypto data
- `defi` — DeFi protocol TVL, yield data
- `onchain` — Etherscan on-chain data
- `news` — Naver news search
- `prediction` — Polymarket prediction markets

---

## v0.1.0 (2025-10)

**Initial release — 7 servers**

### Added
- `ecos` — Bank of Korea ECOS macro indicators
- `dart` — OpenDART financial disclosures
- `valuation` — DCF valuation, peer comparison
- `viz` — Plotly visualization (33 chart types)
- `kosis` — Statistics Korea KOSIS
- `rone` — Korea Real Estate Board
- `stocks` — KRX stock data via pykrx
