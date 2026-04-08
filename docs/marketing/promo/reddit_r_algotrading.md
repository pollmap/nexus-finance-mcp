# r/algotrading Post — Ready to Post

**Subreddit:** r/algotrading  
**Flair:** Tools/Resources  
**Best time:** Tuesday-Thursday, 9-11 AM EST

---

**Title:**

> Open-source MCP server with 396 financial tools — quant analysis, backtesting, factor models, 150+ year historical data

**Body:**

I built an open-source MCP server that gives any AI client (Claude, Cursor, etc.) access to 396 financial research tools. It's designed as a research/analysis toolkit, **not** a trading bot — but it has serious quant depth.

**Quant tools (82 tools):**

- **Volatility modeling:** GARCH family, Heston stochastic vol, realized volatility estimators
- **Portfolio optimization:** Black-Litterman, Hierarchical Risk Parity (HRP), mean-variance, Sharpe maximization
- **Factor engine:** Momentum, value, quality, low-vol factor scoring + correlation analysis
- **Backtesting:** 6 strategy types, drawdown analysis, rolling Sharpe, performance attribution
- **ML pipeline:** Lopez de Prado-style — triple barrier labeling, combinatorial purged CV, feature importance
- **Statistical arbitrage:** Cointegration pairs, Kalman filter, spread z-score
- **Microstructure:** VPIN (volume-synchronized probability of informed trading), order flow toxicity
- **Signal lab:** Multi-factor signal combination, regime detection

**Historical data depth:**

- Shiller CAPE & earnings back to 1871
- NBER business cycles from 1854
- Fama-French factors from 1926
- FRED macro series (century-scale)
- Korean market data via KRX/DART

**Crypto quant (19 tools):**

- CCXT integration (100+ exchanges) — OHLCV, orderbook, funding rates
- On-chain: MVRV, NVT, exchange flows, whale tracking
- DeFi: TVL, yield farming, protocol analytics
- Basis term structure, open interest decomposition

**Data + Visualization:**

- 33 chart types including candlestick, heatmap, correlation matrix, Sankey
- Academic paper search (arXiv, Semantic Scholar) — useful for finding factor research
- Alternative data: climate (ENSO), energy (EIA), agriculture, sentiment

**Connect in 30 seconds:**

```
claude mcp add nexus-finance --transport http http://62.171.141.206/mcp
```

No API keys. No auth. Works with Claude Desktop, Cursor, Windsurf, or any MCP client.

**Example workflow — factor portfolio:**

Ask: *"Build a momentum + value factor portfolio from KRX data and backtest it over 5 years"*

What happens: `factor_score` → `factor_correlation` → `portadv_hrp` → `backtest_portfolio` → `backtest_drawdown`

You get: Optimized portfolio weights, Sharpe ratio, max drawdown chart, factor exposure breakdown.

**GitHub:** https://github.com/pollmap/nexus-finance-mcp (MIT license)

Built by a university student in Korea. Every response uses live API data — zero mock/sample results. Happy to answer questions about the quant architecture or take tool requests.
