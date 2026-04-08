# r/LocalLLaMA Post — Ready to Post

**Subreddit:** r/LocalLLaMA  
**Flair:** Tools  
**Best time:** Tuesday-Thursday, 9-11 AM EST

---

**Title:**

> 396-tool MCP server for Claude/Cursor/any LLM — Korean & global finance, crypto, academic research

**Body:**

I open-sourced an MCP server with 396 financial tools across 64 sub-servers. It works with **any MCP client** — not just Claude.

**Why this matters for the MCP ecosystem:**

MCP (Model Context Protocol) is becoming the standard way to give LLMs access to external tools. This server provides a single endpoint with 396 tools that any compatible client can use immediately. No vendor lock-in — if your client speaks MCP streamable-http, it works.

**Tested with:**

| Client | Status |
|--------|--------|
| Claude Desktop | Works |
| Claude Code | Works |
| Cursor | Works |
| Windsurf | Works |
| Cline (VS Code) | Works |
| Continue | Works |
| Any HTTP MCP client | Works |

**What's in the 396 tools:**

- **Korean markets (41 tools):** DART financial disclosures, Bank of Korea ECOS, KRX stock data, KOSIS statistics — you won't find this coverage in any other MCP server
- **US/Global (32 tools):** FRED macro, SEC EDGAR, India NSE, Japan EDINET
- **Crypto (73 tools):** CCXT (100+ exchanges), on-chain analytics, DeFi TVL, funding rates
- **Quant analysis (82 tools):** GARCH, Black-Litterman, HRP, factor models, backtesting, Lopez de Prado ML pipeline
- **Research (88 tools):** arXiv, Semantic Scholar, PubMed, GDELT news, Google Trends, patents
- **Visualization (33 chart types):** Candlestick, heatmap, treemap, sankey, choropleth, radar
- **Alternative data:** Climate (ENSO), energy (EIA), agriculture, space weather, maritime AIS

**Architecture:**

FastMCP gateway mounts 64 sub-servers. Each sub-server is a self-contained module with standardized adapters. Streamable-HTTP transport. The gateway handles routing — clients see a flat list of 396 tools.

**Self-hosting:**

```bash
git clone https://github.com/pollmap/nexus-finance-mcp
cd nexus-finance-mcp
pip install -e .
python -m nexus_finance_mcp.main
```

Or connect to the hosted instance instantly:

```
claude mcp add nexus-finance --transport http http://62.171.141.206/mcp
```

No API keys needed. No auth required. MIT licensed.

**GitHub:** https://github.com/pollmap/nexus-finance-mcp

Built by a university student in Korea. Every single tool returns real data from live APIs — zero mock/sample responses. The Korean financial data coverage (DART, ECOS, KRX) is unique — no other MCP server has it.

Feature requests welcome. What tools would you want to see added?
