# Nexus Finance MCP — 연결 가이드

> 396 Tools · 64 Servers · Streamable HTTP  
> 금융 데이터 인프라 — 한국/글로벌 시장, 퀀트, 암호화폐, 대체데이터

## Quick Connect

**MCP Endpoint:** `http://62.171.141.206/mcp`

> 도메인 설정 후 HTTPS 엔드포인트로 변경됩니다.

---

## Claude Code (CLI)

```bash
claude mcp add nexus-finance --transport http http://62.171.141.206/mcp
```

연결 확인:
```bash
claude mcp list
```

## Cursor / VS Code

`settings.json` 또는 `.cursor/mcp.json`:

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

`.windsurfrules` 또는 MCP 설정:

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

## cURL (직접 테스트)

```bash
# Initialize
curl -X POST http://62.171.141.206/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# List tools
curl -X POST http://62.171.141.206/mcp \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: <session-id-from-above>" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

## Health Check

```bash
curl http://62.171.141.206/health
# {"status": "ok"}
```

---

## 사용 가능한 도구 카테고리 (396 tools)

| 카테고리 | 서버 수 | 도구 수 | 설명 |
|---------|---------|---------|------|
| Korean Finance | 8 | 60+ | ECOS, DART, KOSIS, KRX, 부동산 |
| Global Markets | 6 | 45+ | US Equity, SEC, Global Macro |
| Crypto | 6 | 50+ | CoinGecko, CCXT, DeFi, On-chain |
| Quant Analysis | 8 | 65+ | Factor, Signal, Portfolio, Backtest |
| Alternative Data | 5 | 35+ | Climate, Conflict, Space, Energy |
| Research | 4 | 30+ | arXiv, Semantic Scholar, News |
| Visualization | 3 | 33+ | Plotly charts, dashboards |
| Knowledge | 3 | 20+ | Vault, Memory, Ontology |

## Rate Limits

- Global: 10 req/s (burst 20)
- MCP endpoint: 5 req/s (burst 10)
- 인증: 불필요 (public open)

## 문의

- GitHub: [luxon-ai](https://github.com/luxon-ai)
- Smithery: (등록 예정)
