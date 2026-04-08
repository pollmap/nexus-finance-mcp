# r/ClaudeAI Post — Ready to Post

**Subreddit:** r/ClaudeAI  
**Flair:** MCP / Tool  
**Best time:** Tuesday-Thursday, 9-11 AM EST

---

**Title:**

> I built a 396-tool MCP server for finance research — open access, no auth needed

**Body:**

After months of building, I'm open-sourcing **nexus-finance-mcp** — a single MCP endpoint that gives Claude access to 396 financial tools across 64 servers. No API keys, no auth, connect in 30 seconds.

**What it covers:**

- **Korean markets:** Samsung stock quotes, DART financials (20 endpoints), Bank of Korea interest rates, KRX, KOSIS national statistics
- **US/Global:** FRED macro data (century-scale), SEC EDGAR filings, India NSE, Japan EDINET
- **Crypto:** 100+ exchanges via CCXT, on-chain analytics (Etherscan), DeFi TVL, funding rates, basis term structure
- **PhD-level quant:** GARCH volatility, Black-Litterman optimization, HRP portfolios, Heston model, Kalman filter, Lopez de Prado ML pipeline, backtesting with drawdown analysis
- **Research:** arXiv, Semantic Scholar, PubMed, patent search, GDELT news, Google Trends
- **Visualization:** 33 chart types — candlestick, heatmap, treemap, sankey, choropleth, radar, and more

**Setup (30 seconds):**

```
claude mcp add nexus-finance --transport http http://62.171.141.206/mcp
```

That's it. No API keys needed. No auth. Just connect and start asking.

**Example prompts to try:**

1. *"Analyze Samsung Electronics as an investment — DCF + peer comparison"* → Gets live DART financials, runs DCF valuation, generates peer multiples chart
2. *"Compare US and Korean interest rate policy with Granger causality"* → Pulls FRED + ECOS data, runs causality test, produces dual-axis chart
3. *"Is BTC funding rate signaling a reversal?"* → Checks funding rates, basis term structure, MVRV, open interest — multi-signal quant dashboard

**Works with:** Claude Desktop, Cursor, Windsurf, Cline, Continue — any MCP client that supports streamable-http.

**GitHub:** https://github.com/pollmap/nexus-finance-mcp

I'm a university student in Korea building this as part of my startup (Luxon AI). The whole platform runs on real data only — zero mock/sample responses. MIT licensed.

Happy to answer any questions about the architecture, and I'd love to hear what financial tools people want added!
