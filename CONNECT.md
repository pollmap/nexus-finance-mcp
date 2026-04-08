# Nexus Finance MCP — Connection Guide

> 396 Tools · 64 Servers · Streamable HTTP  
> Financial data infrastructure — Korean/Global markets, quant, crypto, alternative data

## Quick Connect

**MCP Endpoint:** `http://62.171.141.206/mcp`

No API keys needed. No authentication. Just connect and start querying.

```bash
# Test it right now
curl http://62.171.141.206/health
# → {"status":"ok","version":"8.0.0-phase12","loaded_servers":64,"tool_count":396}
```

---

## Claude Code (CLI)

```bash
claude mcp add nexus-finance --transport http http://62.171.141.206/mcp
```

Verify:
```bash
claude mcp list
```

## Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "nexus-finance": {
      "url": "http://62.171.141.206/mcp",
      "transport": "streamable-http"
    }
  }
}
```

> **Config location:** Windows `%APPDATA%\Claude\claude_desktop_config.json` · macOS `~/Library/Application Support/Claude/claude_desktop_config.json`

## Cursor / VS Code

`settings.json` or `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "nexus-finance": {
      "url": "http://62.171.141.206/mcp"
    }
  }
}
```

## Windsurf

MCP settings:

```json
{
  "mcpServers": {
    "nexus-finance": {
      "serverUrl": "http://62.171.141.206/mcp"
    }
  }
}
```

## Python (mcp SDK)

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async with streamablehttp_client("http://62.171.141.206/mcp") as (read, write, _):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        print(f"Connected! {len(tools.tools)} tools available")
```

## TypeScript (mcp SDK)

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const client = new Client({ name: "my-app", version: "1.0" });
const transport = new StreamableHTTPClientTransport(
  new URL("http://62.171.141.206/mcp")
);
await client.connect(transport);
const tools = await client.listTools();
```

## cURL (Manual Testing)

```bash
# 1. Initialize session
curl -X POST http://62.171.141.206/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# 2. List tools (use Mcp-Session-Id from step 1 response header)
curl -X POST http://62.171.141.206/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: <session-id-from-step-1>" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

# 3. Call a tool
curl -X POST http://62.171.141.206/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: <session-id>" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"gateway_status","arguments":{}}}'
```

> **Important:** The `Accept: application/json, text/event-stream` header is required. Without it you'll get a 406 error.

## Health Check

```bash
curl http://62.171.141.206/health
```

---

## Available Tools (396 total)

| Category | Servers | Tools | Description |
|----------|---------|-------|-------------|
| Korean Finance | 8 | 60+ | ECOS, DART, KOSIS, KRX, Real Estate |
| Global Markets | 6 | 45+ | US Equity, SEC EDGAR, FRED, Global Macro |
| Crypto & DeFi | 6 | 50+ | CoinGecko, CCXT 100+ exchanges, On-chain |
| Quant Analysis | 8 | 65+ | Factor models, Signal lab, Portfolio optimization, Backtest |
| Alternative Data | 5 | 35+ | Climate, Conflict, Space weather, Energy |
| Research | 4 | 30+ | arXiv, Semantic Scholar, News RSS |
| Visualization | 3 | 33+ | Plotly charts — line, candle, heatmap, choropleth |
| Knowledge | 3 | 20+ | Semantic memory, Ontology graph |

> Run `gateway_status()` after connecting to see all servers and tools.

---

## Limitations & Caveats

### Network & Security

- **HTTP only (no TLS)** — traffic is unencrypted. Do not send sensitive data through tool parameters. Domain + HTTPS coming soon.
- **Single server** — hosted on one VPS in Germany (Contabo). No redundancy, no CDN. Latency may be higher from Asia/Americas.
- **Best-effort uptime** — this is a community/research server, not an SLA-backed service. Server may restart for maintenance without notice.

### Rate Limits

| Scope | Limit | Burst |
|-------|-------|-------|
| Global (all endpoints) | 10 req/s per IP | 20 |
| MCP endpoint (`/mcp`) | 5 req/s per IP | 10 |

Exceeding limits returns HTTP 429. Back off and retry after 1 second.

### Data

- **Real data only** — no mock/sample data ever. If an API is down, you get a clear error, not fake numbers.
- **API key-dependent tools** — some tools require upstream API keys (DART, ECOS, etc.). On the hosted server, these keys are pre-configured. If self-hosting, you need your own keys (see README).
- **Market hours** — Korean market data (KRX) is real-time during trading hours (09:00-15:30 KST). Outside hours, you get the last closing data.
- **Data freshness** — most data is fetched live per request. Some endpoints (macro indicators) are cached for up to 1 hour.

### MCP Protocol

- **Transport:** `streamable-http` only (no stdio/SSE on the public endpoint)
- **Session:** stateful — the server tracks sessions via `Mcp-Session-Id` header
- **Max request body:** 2 MB
- **Request timeout:** 300 seconds (5 minutes) — some quant tools with heavy computation may take 10-30 seconds

### What This Server Is NOT

- Not a trading API — no order execution, no account management
- Not a data warehouse — no bulk data download, no historical dumps
- Not a production SaaS — no SLA, no guaranteed uptime, no support tier

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| 406 Not Acceptable | Add `Accept: application/json, text/event-stream` header |
| 429 Too Many Requests | Rate limited — wait 1s and retry |
| Connection refused | Server may be restarting — try again in 30s |
| Timeout on tool call | Some quant tools take 10-30s — increase client timeout to 300s |
| Empty response | Check `Mcp-Session-Id` header — session may have expired |

## Links

- **GitHub:** [pollmap/nexus-finance-mcp](https://github.com/pollmap/nexus-finance-mcp)
- **Health:** [http://62.171.141.206/health](http://62.171.141.206/health)
- **Smithery:** Coming soon
- **Built by:** [Luxon AI](https://github.com/pollmap)
