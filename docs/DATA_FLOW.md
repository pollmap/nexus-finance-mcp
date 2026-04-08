# Nexus Finance MCP — Architecture Diagrams

> Visual reference for system architecture, data flow, and server organization.  
> All diagrams use [Mermaid](https://mermaid.js.org/) — rendered natively by GitHub.

---

## 1. System Architecture

```mermaid
graph TD
    subgraph Clients
        CC[Claude Code]
        CD[Claude Desktop]
        CU[Cursor / VS Code]
        WS[Windsurf]
        SDK[Python / TS SDK]
    end

    subgraph Proxy["Nginx Reverse Proxy"]
        RL[Rate Limiter<br/>5 req/s per IP]
        CORS[CORS Headers]
    end

    subgraph Gateway["MCP Gateway :8100"]
        GW[GatewayServer<br/>FastMCP 3.x]
        META[Meta Tools<br/>gateway_status, list_tools, ...]
    end

    subgraph Servers["64 Sub-Servers"]
        S1[Korean Finance<br/>ecos, dart, kosis, stocks, ...]
        S2[Global Markets<br/>us_equity, sec, asia_market, ...]
        S3[Crypto & DeFi<br/>crypto, defi, onchain, ...]
        S4[Quant Engine<br/>quant, backtest, factor, ...]
        S5[News & Research<br/>news, academic, rss, ...]
        S6[Alternative Data<br/>climate, space, conflict, ...]
        S7[Visualization<br/>viz, technical]
        S8[Knowledge<br/>vault, memory, ontology]
    end

    subgraph Adapters["60 Adapters"]
        A1[HTTP Clients<br/>httpx / aiohttp]
    end

    subgraph Core["Core Infrastructure"]
        CACHE[3-Tier Cache<br/>LRU → TTL → Disk]
        RLM[Rate Limiter<br/>Token Bucket per service]
        CNT[API Counter<br/>Daily call stats]
    end

    subgraph APIs["External APIs"]
        API1[BOK ECOS]
        API2[OpenDART]
        API3[CCXT Exchanges]
        API4[Yahoo Finance]
        API5[FRED / SEC / ...]
    end

    CC & CD & CU & WS & SDK -->|HTTP POST /mcp| Proxy
    Proxy -->|proxy_pass| Gateway
    GW --> META
    GW --> Servers
    S1 & S2 & S3 & S4 & S5 & S6 & S7 & S8 --> Adapters
    Adapters --> Core
    A1 -->|HTTP| APIs
```

---

## 2. Request Lifecycle

```mermaid
sequenceDiagram
    participant C as MCP Client
    participant N as Nginx :80/443
    participant G as Gateway :8100
    participant S as Sub-Server
    participant Ca as Cache (L1/L2/L3)
    participant A as Adapter
    participant E as External API

    C->>N: POST /mcp (JSON-RPC)
    N->>N: Rate limit check
    alt Rate Limited
        N-->>C: 429 Too Many Requests
    end
    N->>G: Proxy request
    G->>G: Route to tool by name
    G->>S: Call tool function

    S->>Ca: Check L1 (LRU)
    alt L1 Hit
        Ca-->>S: Cached data
    else L1 Miss
        S->>Ca: Check L2 (TTL)
        alt L2 Hit
            Ca-->>S: Cached data + promote to L1
        else L2 Miss
            S->>Ca: Check L3 (Disk)
            alt L3 Hit
                Ca-->>S: Cached data + promote to L1/L2
            else L3 Miss
                S->>A: Fetch from external
                A->>E: HTTP request
                E-->>A: Raw JSON
                A-->>S: Normalized dict
                S->>Ca: Store in L1 + L2 + L3
            end
        end
    end

    S-->>G: Response dict
    G-->>N: JSON-RPC response
    N-->>C: SSE event stream
```

---

## 3. Server Domain Tree

```mermaid
graph LR
    GW[Gateway<br/>64 servers / 398 tools]

    subgraph KR["Korean Finance (8 servers)"]
        ecos[ecos<br/>한국은행 ECOS]
        dart[dart<br/>금감원 DART]
        kosis[kosis<br/>통계청 KOSIS]
        stocks[stocks<br/>KRX via pykrx]
        fsc[fsc<br/>금융위원회]
        rone[rone<br/>부동산원]
        val[valuation<br/>DCF/Peer]
        re_trans[realestate_trans<br/>실거래가]
    end

    subgraph GL["Global Markets (6 servers)"]
        us_eq[us_equity<br/>US Stocks]
        sec[sec<br/>SEC EDGAR]
        edinet[edinet<br/>일본 EDINET]
        asia[asia_market<br/>Asia]
        india[india<br/>India NSE]
        g_macro[global_macro<br/>FRED/BIS/WB]
    end

    subgraph CR["Crypto & DeFi (6 servers)"]
        crypto[crypto<br/>CCXT 100+]
        defi[defi<br/>DeFi TVL]
        onchain[onchain<br/>Etherscan]
        hist_c[hist_crypto<br/>Historical]
        onchain_adv[onchain_advanced<br/>MVRV/NVT]
        crypto_q[crypto_quant<br/>Funding Arb]
    end

    subgraph QT["Quant Engine (11 servers)"]
        quant[quant_analysis<br/>Correlation]
        ts[timeseries<br/>ARIMA/Forecast]
        bt[backtest<br/>6 Strategies]
        factor[factor_engine<br/>Multi-Factor]
        signal[signal_lab<br/>Signal Scan]
        port[portfolio_optimizer<br/>Markowitz]
        hist_d[historical_data<br/>150yr Shiller]
        vol[volatility_model<br/>GARCH/Heston]
        math[advanced_math<br/>Wavelets]
        stat[stat_arb<br/>Pairs Trading]
        port_adv[portfolio_advanced<br/>BL/HRP]
    end

    subgraph ML["ML & Alpha (4 servers)"]
        stoch[stochvol<br/>SV Models]
        micro[microstructure<br/>VPIN/Kyle]
        ml[ml_pipeline<br/>Lopez de Prado]
        alpha[alpha_research<br/>Alpha Decay]
    end

    subgraph NR["News & Research (6 servers)"]
        news[news<br/>Naver News]
        g_news[global_news<br/>GDELT]
        rss[rss<br/>14 RSS Feeds]
        academic[academic<br/>arXiv/Scholar]
        research[research<br/>RISS/PubMed]
        sentiment[sentiment<br/>Trends]
    end

    subgraph AD["Alternative Data (7 servers)"]
        energy[energy<br/>EIA Oil/Gas]
        agri[agriculture<br/>KAMIS Prices]
        maritime[maritime<br/>AIS Ships]
        aviation[aviation<br/>Flights]
        trade[trade<br/>UN Comtrade]
        prediction[prediction<br/>Polymarket]
        consumer[consumer<br/>Consumer Data]
    end

    subgraph ENV["Environment & Risk (5 servers)"]
        space[space_weather<br/>Solar/Sunspot]
        disaster[disaster<br/>GDACS]
        conflict[conflict<br/>ACLED]
        climate[climate<br/>ENSO/GHG]
        power[power_grid<br/>ENTSO-E]
    end

    subgraph REG["Regulatory (4 servers)"]
        regulation[regulation<br/>EU SFDR]
        politics[politics<br/>Gov Policy]
        patent[patent<br/>Patents]
        health_s[health<br/>FDA/WHO]
    end

    subgraph VIZ["Visualization (2 servers)"]
        viz[viz<br/>33 Chart Types]
        tech[technical<br/>TA Indicators]
    end

    subgraph ENV2["Environment (1 server)"]
        environ[environ<br/>EPA/Air]
    end

    subgraph INFRA["Knowledge & Infra (4 servers)"]
        vault[vault<br/>Obsidian]
        memory[memory<br/>Vector Search]
        v_idx[vault_index<br/>BM25 Index]
        onto[ontology<br/>Causal Graph]
    end

    GW --> KR & GL & CR & QT & ML & NR & AD & ENV & REG & VIZ & ENV2 & INFRA
```

---

## 4. Caching Architecture (3-Tier)

```mermaid
flowchart TD
    REQ[Incoming Request] --> L1{L1: LRU Cache<br/>100 items, no TTL}

    L1 -->|HIT| RET1[Return cached data]
    L1 -->|MISS| L2{L2: TTL Cache<br/>1000 items, 1hr default}

    L2 -->|HIT| PROM1[Promote to L1<br/>Return data]
    L2 -->|MISS| L3{L3: DiskCache<br/>SQLite, persistent}

    L3 -->|HIT| PROM2[Promote to L1 + L2<br/>Return data]
    L3 -->|MISS| API[External API Call]

    API --> STORE[Store in L1 + L2 + L3<br/>TTL by data type]
    STORE --> RET2[Return fresh data]

    style L1 fill:#1a1a2e,stroke:#7c6af7,color:#e0e0e0
    style L2 fill:#1a1a2e,stroke:#a8ff60,color:#e0e0e0
    style L3 fill:#1a1a2e,stroke:#ff6b6b,color:#e0e0e0
    style API fill:#0d0d1a,stroke:#ffd700,color:#e0e0e0
```

### TTL by Data Type

| Type | TTL | Examples |
|------|-----|---------|
| `realtime_price` | 60s | Stock quotes, crypto tickers |
| `daily_data` | 1 hour | Daily OHLCV, news articles |
| `historical` | 24 hours | Historical time series |
| `static_meta` | 1 week | Company info, metadata |
| `default` | 1 hour | Everything else |

---

## 5. Tool Complexity Distribution

```mermaid
pie title 398 Tools by Complexity Tier
    "Tier 1 — Simple (86)" : 86
    "Tier 2 — Parameterized (120)" : 120
    "Tier 3 — Analytical (80)" : 80
    "Tier 4 — Pipeline (78)" : 78
```

### Input Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| `snapshot` | Zero params, point-in-time | `ecos_get_macro_snapshot()` |
| `stock_code` | Korean equity code | `dart_company_info("005930")` |
| `series` | Date range time series | `ecos_get_base_rate("2020-01", "2024-12")` |
| `search` | Keyword text search | `academic_search("transformer forecasting")` |
| `data_columns` | Column selection from dataset | `kosis_get_data(table_id, columns)` |
| `composite` | Multi-step, chained calls | `backtest_run(stock, strategy, years)` |

---

## 6. Server Implementation Patterns

```mermaid
graph TD
    subgraph PatternA["Pattern A: BaseMCPServer (14 servers)"]
        BSA[BaseMCPServer ABC] -->|inherits| SA1[DartServer]
        BSA -->|inherits| SA2[FactorEngineServer]
        BSA -->|inherits| SA3[SignalLabServer]
        BSA -->|provides| FEAT1[Built-in caching<br/>_cached_request]
        BSA -->|provides| FEAT2[Built-in rate limiting<br/>_rate_limited]
        BSA -->|provides| FEAT3[Error decorators<br/>tool_handler]
    end

    subgraph PatternB["Pattern B: Direct FastMCP (50 servers)"]
        SB1[CryptoExchangeServer] -->|creates| FM1[FastMCP instance]
        SB2[ECOSServer] -->|creates| FM2[FastMCP instance]
        SB3[VizServer] -->|creates| FM3[FastMCP instance]
        SB1 & SB2 & SB3 -->|uses| AD1[Own adapter instance]
    end

    subgraph Mount["Gateway Mount"]
        GW[GatewayServer]
        SA1 & SA2 & SA3 -->|.mcp| GW
        FM1 & FM2 & FM3 -->|.mcp| GW
    end

    style PatternA fill:#1a1a2e,stroke:#7c6af7,color:#e0e0e0
    style PatternB fill:#1a1a2e,stroke:#a8ff60,color:#e0e0e0
```

### When to Use Each Pattern

| | Pattern A (BaseMCPServer) | Pattern B (Direct FastMCP) |
|---|---|---|
| **Use when** | Building new servers (Phase 9+) | Quick prototype or simple wrapper |
| **Caching** | Built-in via `_cached_request()` | Manual adapter-level caching |
| **Rate limiting** | Built-in via `_rate_limited()` | Manual or via adapter |
| **Error handling** | `@tool_handler` decorator available | Inline try/except |
| **Examples** | dart, factor_engine, signal_lab | crypto_exchange, ecos, viz |

---

## Related Docs

- [ARCHITECTURE.md](ARCHITECTURE.md) — Detailed layer-by-layer technical docs
- [TOOL_CATALOG.md](TOOL_CATALOG.md) — Full tool listing by domain and tier
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) — Cheat sheet for daily use
