# Show HN Post — Ready to Post

**Post to:** https://news.ycombinator.com/submit  
**Best time:** Tuesday-Wednesday, 8-10 AM EST  
**Type:** Show HN (starts with "Show HN:")

---

**Title:**

> Show HN: Nexus Finance MCP – 396 tools for financial research via Model Context Protocol

**URL:** https://github.com/pollmap/nexus-finance-mcp

**Text (if self-post, otherwise leave blank and let the repo speak):**

I'm a university student in Korea. I built nexus-finance-mcp, a single MCP endpoint that exposes 396 financial tools across 64 microservers.

It connects to any MCP client (Claude Desktop, Cursor, Windsurf, etc.) and lets you ask natural language questions backed by real financial data.

Coverage: Korean equities (DART, ECOS, KRX), US macro (FRED, SEC EDGAR), crypto (CCXT 100+ exchanges, on-chain, DeFi), PhD-level quant (GARCH, Heston, Black-Litterman, HRP), 33 chart types, academic paper search, climate/energy/agriculture alternative data.

No authentication required. Connect in 30 seconds:

    claude mcp add nexus-finance --transport streamable-http --url http://62.171.141.206/mcp

Architecture: FastMCP gateway mounts 64 sub-servers, streamable-http transport. Each server is a self-contained module with standardized adapters. Real data only — zero mock/sample responses.

150+ year historical data depth: Shiller (1871~), NBER cycles (1854~), Fama-French factors (1926~).

MIT licensed. https://github.com/pollmap/nexus-finance-mcp
