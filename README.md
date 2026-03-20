# Nexus Finance MCP Server

> **48 tools for Korean & US financial research** — Built for AI agents by [Luxon AI](https://github.com/pollmap).

The most comprehensive Korean financial data MCP server. DART filings, BOK rates, KOSIS statistics, real estate indices, DCF valuation, and real-time stock quotes — all in one gateway.

## Tools (48)

| Server | Tools | Data Source |
|--------|-------|-------------|
| **ECOS** (7) | Base rate, M2, GDP, Exchange rate, CPI, Macro snapshot | 한국은행 (Bank of Korea) |
| **Valuation** (10) | DCF, WACC, Sensitivity, Peer comparison, GAAP normalization | DART + ECOS + KRX |
| **Visualization** (10) | Line, Bar, Candlestick, Heatmap, Scatter, Waterfall, etc. | Built-in Plotly |
| **KOSIS** (5) | Population, Unemployment, Housing price index | 통계청 (Statistics Korea) |
| **R-ONE** (6) | Apartment price, Jeonse, PIR, Regional comparison | 한국부동산원 |
| **Stocks** (5) | Real-time quotes, Search, History, Beta, Market overview | KIS + pykrx + Yahoo |
| **Gateway** (2) | Status, Tool listing | — |

## Quick Start

```bash
# Clone
git clone https://github.com/pollmap/nexus-finance-mcp.git
cd nexus-finance-mcp

# Install
pip install -r requirements.txt

# Configure API keys
cp .env.template .env
# Edit .env with your API keys

# Run (HTTP)
python server.py --transport streamable-http --port 8100

# Run (stdio for Claude Code)
python server.py --transport stdio
```

## API Keys

| Key | Source | Required |
|-----|--------|----------|
| `BOK_ECOS_API_KEY` | [ECOS](https://ecos.bok.or.kr) | Yes |
| `DART_API_KEY` | [OpenDART](https://opendart.fss.or.kr) | Yes |
| `KOSIS_API_KEY` | [KOSIS](https://kosis.kr) | Optional |
| `RONE_API_KEY` | [부동산원](https://www.reb.or.kr) | Optional |
| `FRED_API_KEY` | [FRED](https://fred.stlouisfed.org) | Optional |
| `KIS_API_KEY` | [한국투자증권](https://apiportal.koreainvestment.com) | Optional |

## Usage Examples

```
"삼성전자 DCF 분석해줘"
→ DART 재무제표 → ECOS 기준금리 → DCF 적정주가 산출

"현재 한국 매크로 상황"
→ 기준금리 2.50%, 환율, GDP, M2 스냅샷

"SK하이닉스 vs 마이크론 비교"
→ K-IFRS ↔ US-GAAP 정규화 → 멀티플 비교

"서울 아파트 가격 추이"
→ R-ONE 아파트매매가격지수 + 시각화
```

## Architecture

```
Client (AI Agent / Claude Code)
        │
        ▼
   Gateway Server (FastMCP)
        │
   ┌────┴────────────────────────────────┐
   │  /ecos  /valuation  /viz            │
   │  /kosis  /rone  /stocks             │
   └────┬────────────────────────────────┘
        │
   ┌────┴────────────────────────────────┐
   │  Adapters: DART, KRX, Yahoo,       │
   │            FRED, CoinGecko, KIS     │
   └────┬────────────────────────────────┘
        │
   ┌────┴────────────────────────────────┐
   │  Core: Cache (4-tier), Rate Limiter,│
   │        Fallback Chain               │
   └─────────────────────────────────────┘
```

## Smithery

Published at: `luxon/nexus-finance-mcp`

## License

MIT

---

*Part of the [Luxon AI Agent Network](https://github.com/pollmap) — "각자 다르게 생각하고, 하나의 지갑으로 번다."*
