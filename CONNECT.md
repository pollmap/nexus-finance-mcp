# Nexus Finance MCP — Connection Guide

> 398 Tools · 64 Servers · Streamable HTTP  
> Financial data infrastructure — Korean/Global markets, quant, crypto, alternative data

## Quick Connect

**MCP Endpoint:** `http://62.171.141.206/mcp`

No API keys needed. No authentication. Just connect and start querying.

```bash
# Test it right now
curl http://62.171.141.206/health
# → {"status":"ok","version":"8.0.0-phase14","loaded_servers":64,"tool_count":398}
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

## Cline (VS Code Extension)

VS Code Extension settings → MCP Servers:

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

## Continue (VS Code / JetBrains)

`~/.continue/config.json`:

```json
{
  "mcpServers": [
    {
      "name": "nexus-finance",
      "url": "http://62.171.141.206/mcp",
      "transport": "streamable-http"
    }
  ]
}
```

## Zed

Zed settings (`settings.json`):

```json
{
  "context_servers": {
    "nexus-finance": {
      "url": "http://62.171.141.206/mcp",
      "transport": "streamable-http"
    }
  }
}
```

## OpenClaw / OpenRouter

MCP 서버를 OpenClaw `openclaw.json`에 추가:

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

Full 4-step protocol handshake:

```bash
# 1. Initialize session — get Mcp-Session-Id from response header
curl -v -X POST http://62.171.141.206/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
# → Look for "mcp-session-id: xxx" in response headers

# 2. Send initialized notification (REQUIRED — server won't accept tool calls without this)
curl -X POST http://62.171.141.206/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: <session-id-from-step-1>" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'

# 3. List available tools
curl -X POST http://62.171.141.206/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: <session-id>" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

# 4. Call a tool
curl -X POST http://62.171.141.206/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: <session-id>" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"gateway_status","arguments":{}}}'
```

> **Required headers:**
> - `Accept: application/json, text/event-stream` — without this you get 406
> - `Mcp-Session-Id` — from step 1 response header, required for all subsequent requests

## Health Check

```bash
curl http://62.171.141.206/health
```

---

## Response Format

When you call a tool via MCP, the response follows this structure:

### Transport Layer — SSE

All responses arrive as **Server-Sent Events** (SSE):

```
event: message
data: {"jsonrpc":"2.0","id":3,"result":{...}}
```

MCP SDK clients (Claude Code, Cursor, etc.) handle SSE parsing automatically. You only need to care about this if using raw HTTP/cURL.

### Tool Response Envelope

Inside the JSON-RPC `result`, the tool data is wrapped in the MCP content envelope:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\":true,\"data\":{...}}"
      }
    ],
    "structuredContent": {
      "success": true,
      "data": { ... }
    },
    "isError": false
  }
}
```

| Field | Description |
|-------|-------------|
| `result.content[0].text` | Tool output as JSON string (always present) |
| `result.structuredContent` | Same data as parsed object (when available) |
| `result.isError` | `false` for success, `true` for errors |

### Tool Data Format

Inside `structuredContent` (or parsed from `content[0].text`), each tool returns:

```json
// Success
{
  "success": true,
  "data": { ... },
  "source": "ECOS"
}

// Error
{
  "error": true,
  "message": "Human-readable error description"
}
```

### Parsing in Code

```python
# With MCP SDK — handles SSE and envelope automatically
result = await session.call_tool("ecos_get_macro_snapshot", {})
data = json.loads(result.content[0].text)

if data.get("error"):
    print(f"Error: {data['message']}")
else:
    print(data["data"])
```

```python
# With raw HTTP — parse SSE manually
import httpx, json

resp = httpx.post(url, headers=headers, json=payload)
for line in resp.text.split("\n"):
    if line.startswith("data: "):
        msg = json.loads(line[6:])
        tool_data = json.loads(msg["result"]["content"][0]["text"])
```

### Error Responses

| Error Type | Example |
|------------|---------|
| Unknown tool | `{"isError": true, "content": [{"text": "Unknown tool: 'foo'"}]}` |
| Invalid params | `{"isError": true, "content": [{"text": "Missing required argument..."}]}` |
| API failure | `{"isError": false, "content": [{"text": "{\"error\":true,\"message\":\"Rate limit exceeded\"}"}]}` |
| 406 HTTP | Missing `Accept` header — add `application/json, text/event-stream` |
| 429 HTTP | Rate limited — wait 1 second and retry |

> **Important:** API-level errors (rate limit, missing key) come inside a successful MCP response (`isError: false`) with `{"error": true}` in the tool data. Protocol-level errors (unknown tool, bad params) set `isError: true` at the MCP level.

### Tool Schema Discovery

Each tool has a JSON Schema for its parameters:

```json
{
  "name": "ecos_get_stat_data",
  "description": "ECOS 통계 데이터 조회...",
  "inputSchema": {
    "type": "object",
    "properties": {
      "stat_code": { "type": "string" },
      "item_code": { "type": "string" },
      "start_date": { "type": "string" },
      "end_date": { "type": "string" },
      "frequency": { "type": "string" }
    },
    "required": ["stat_code", "item_code", "start_date"]
  }
}
```

Use `tools/list` to discover all 398 tool schemas programmatically.

---

## Compatibility Matrix

MCP is a protocol — not every AI platform supports it. Here's what works and what doesn't.

### Fully Supported (MCP native)

| Client | Platform | Status |
|--------|----------|--------|
| **Claude Code** | CLI (Win/Mac/Linux) | ✅ Works — `claude mcp add` |
| **Claude Desktop** | App (Win/Mac) | ✅ Works — `claude_desktop_config.json` |
| **Cursor** | IDE | ✅ Works — settings or `.cursor/mcp.json` |
| **Windsurf** | IDE | ✅ Works — MCP settings |
| **Cline** | VS Code extension | ✅ Works — extension settings |
| **Continue** | VS Code / JetBrains | ✅ Works — `config.json` |
| **Zed** | IDE | ✅ Works — `settings.json` |
| **Smithery** | MCP marketplace | ✅ Works — one-click install |
| **Python/TS SDK** | Custom apps | ✅ Works — `mcp` package |
| **OpenClaw** | Self-hosted gateway | ✅ Works — `openclaw.json` |

### Not Supported (no MCP protocol)

| Platform | Why | Workaround |
|----------|-----|------------|
| **ChatGPT** (web/app) | Uses its own "Actions" system (OpenAPI), not MCP | None — ChatGPT cannot connect to MCP servers directly |
| **Gemini** (web/app) | Google's own tool system, no MCP support | None |
| **Copilot** (GitHub/Bing) | Microsoft's own extensions, no MCP | None |
| **Perplexity** | Search-focused, no tool protocol | None |
| **Ollama** (standalone) | LLM runner only — no tool calling framework | Use with a frontend that supports MCP (see below) |
| **llama.cpp** | LLM inference engine, no MCP client | Same — needs an MCP-capable frontend |

### Local LLMs — How to Connect

Ollama/llama.cpp alone can't use MCP. But these **frontends** add MCP support on top of local LLMs:

| Frontend | Local LLM | MCP Support |
|----------|-----------|-------------|
| **Continue** (VS Code) | Ollama, llama.cpp, LM Studio | ✅ Full MCP support |
| **Cline** (VS Code) | Ollama via OpenAI-compatible API | ✅ Full MCP support |
| **Claude Code** (with `--model`) | Any OpenAI-compatible API | ✅ Full MCP support |
| **Open WebUI** | Ollama | ⚠️ Limited (plugin-based, not native MCP) |
| **LM Studio** | Built-in models | ❌ No MCP support yet |
| **Jan** | Ollama, llama.cpp | ❌ No MCP support yet |

**Example: Ollama + Continue + Nexus Finance MCP**

1. Run Ollama: `ollama serve`
2. Install Continue extension in VS Code
3. Configure Continue to use Ollama as LLM
4. Add MCP server in Continue config:
```json
{
  "mcpServers": [
    {
      "name": "nexus-finance",
      "url": "http://62.171.141.206/mcp",
      "transport": "streamable-http"
    }
  ]
}
```
5. Now your local LLM can call 398 financial tools

> **Note:** Tool calling quality depends on the LLM's capability. Large models (Llama 3.1 70B+, Qwen 2.5 72B+) handle tool calls well. Smaller models may struggle with complex multi-tool workflows.

---

## Available Tools (398 total)

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
