# Nexus Finance MCP — 전체 현황 도식화

> v8.0.0-phase14 · 396 tools · 64 servers · Finance & Research Intelligence Platform
> 생성일: 2026-04-08

---

## 1. 시스템 계층도 (System Hierarchy)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER (외부 접속)                            │
│                                                                             │
│   Claude Desktop    Claude Code    Cursor    Windsurf    Smithery    HTTP    │
│        │                │            │          │           │          │     │
│        └────────────────┴────────────┴──────────┴───────────┴──────────┘     │
│                                     │                                        │
│                              MCP Protocol                                    │
│                        (streamable-http / stdio)                             │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PROXY LAYER (nginx)                                   │
│                                                                             │
│   ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐                │
│   │  TLS (443)  │    │ Rate Limit   │    │  Open Access    │                │
│   │  Termination│    │ 10 req/burst │    │  (No Auth)      │                │
│   └─────────────┘    └──────────────┘    └─────────────────┘                │
│                                                                             │
│   Public:  http://62.171.141.206/mcp                                        │
│   Internal: http://127.0.0.1:8100/mcp                                       │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     GATEWAY LAYER (FastMCP 3.x)                              │
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │  GatewayServer (server.py → gateway_server.py)                   │      │
│   │                                                                  │      │
│   │  ┌────────────┐  ┌──────────────┐  ┌─────────────┐              │      │
│   │  │ 64 Servers  │  │ Tool Metadata│  │ API Counter │              │      │
│   │  │ (dynamic    │  │ (domain,     │  │ (daily call │              │      │
│   │  │  mount)     │  │  pattern,    │  │  stats)     │              │      │
│   │  │             │  │  complexity) │  │             │              │      │
│   │  └────────────┘  └──────────────┘  └─────────────┘              │      │
│   │                                                                  │      │
│   │  Gateway Meta Tools (6):                                         │      │
│   │  gateway_status · list_available_tools · api_call_stats          │      │
│   │  list_tools_by_domain · list_tools_by_pattern · tool_info        │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└──────────────┬──────────────┬──────────────┬──────────────┬─────────────────┘
               │              │              │              │
               ▼              ▼              ▼              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        SERVER LAYER (64 Servers)                              │
│                                                                              │
│  각 서버는 FastMCP 인스턴스로 독립 동작 → Gateway에 mount                       │
│  importlib.import_module() → cls() → gateway.mcp.mount(sub.mcp)              │
│                                                                              │
│  (아래 도메인별 상세 참조)                                                      │
└──────────────────────────────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER (외부 API)                                │
│                                                                              │
│  한국: ECOS · DART · KOSIS · KRX · MOLIT · KAMIS · FSC · 국회              │
│  글로벌: FRED · OECD · IMF · BIS · World Bank · Finnhub · SEC EDGAR         │
│  크립토: CCXT(100+거래소) · CoinGecko · DefiLlama · Etherscan · Blockchain   │
│  학술: arXiv · Semantic Scholar · OpenAlex · RISS · PubMed · KIPRIS         │
│  대안: NASA · NOAA · USGS · GDACS · UCDP · ENTSO-E · Open-Meteo           │
│  뉴스: Naver · GDELT · RSS(14피드) · pytrends · Wikipedia                   │
│                                                                              │
│  ⚠️ 200+ tools require NO API keys                                          │
│  ⚠️ Required keys: BOK_ECOS_API_KEY, DART_API_KEY only                      │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 도메인별 서버 구조 (15 Domains × 64 Servers × 396 Tools)

```
NEXUS FINANCE MCP (396 tools)
│
├─── 🇰🇷 Korean Economy (41 tools / 5 servers)
│    ├── ecos (9)         한국은행 기준금리, M2, GDP, 환율, 채권
│    ├── dart (20)        삼성전자 재무제표, 주주, 배당, 공시, 임원
│    ├── kosis (5)        인구, 실업률, 주택가격
│    ├── fsc (2)          주가, 채권가격
│    └── stocks (5)       시세, 검색, 히스토리, 베타, 시장개요
│
├─── 🏠 Korean Real Estate (8 tools / 2 servers)
│    ├── rone (6)         아파트 매매/전세 지수, PIR
│    └── realestate (2)   실거래가, 시군구 코드
│
├─── 🌍 Global Markets (37 tools / 6 servers)
│    ├── global_macro (10) OECD, IMF, BIS, World Bank, FRED
│    ├── us_equity (4)     Finnhub 미국 주식
│    ├── asia_market (8)   중국, 대만, 홍콩
│    ├── india (3)         인도 주식/지수
│    ├── sec (8)           SEC EDGAR 10-K, 내부자거래
│    └── edinet (4)        일본 EDINET
│
├─── ₿ Crypto & DeFi (36 tools / 6 servers)
│    ├── crypto (14)       CCXT 100+ 거래소, 김치프리미엄
│    ├── hist_crypto (3)   CoinGecko 일봉/시봉
│    ├── defi (4)          DefiLlama TVL, Fear & Greed
│    ├── onchain (3)       Etherscan 잔고/트랜잭션/가스
│    ├── onchain_adv (6)   MVRV, NVT, HODL Waves, 고래
│    └── crypto_quant (6)  펀딩비, 베이시스, OI, 청산
│
├─── 📰 News & Research (31 tools / 6 servers)
│    ├── news (4)          네이버 검색, 트렌드, 감성
│    ├── global_news (3)   GDELT 글로벌 뉴스
│    ├── rss (4)           Bloomberg, WSJ, Reuters 등 14피드
│    ├── academic (9)      arXiv, Semantic Scholar, OpenAlex
│    ├── research (6)      RISS, NKIS, PRISM, 국립중앙도서관
│    └── sentiment (5)     Google Trends, Wikipedia, VADER
│
├─── 🏭 Real Economy (31 tools / 7 servers)
│    ├── energy (9)        원유, 가스, 전력, OPEC
│    ├── agriculture (7)   KAMIS, FAO, USDA
│    ├── maritime (4)      BDI, 컨테이너 운임
│    ├── aviation (3)      OpenSky 항공
│    ├── trade (3)         한국 수출입, UN Comtrade
│    ├── consumer (4)      미국 소매/심리, EU HICP
│    └── prediction (3)    Polymarket 예측시장
│
├─── ⚖️ Regulatory & Environment (26 tools / 6 servers)
│    ├── valuation (10)    WACC, DCF, 피어비교, GAAP 정규화
│    ├── regulation (4)    EU EUR-Lex, FINRA
│    ├── politics (3)      국회 법안
│    ├── health (5)        FDA, PubMed, WHO, 임상시험
│    ├── environ (2)       EPA 대기질, 탄소가격
│    └── patent (2)        KIPRIS 특허검색
│
├─── 🛰️ Quant Alternative Data (32 tools / 5 servers)
│    ├── space_weather (5) 흑점(1818~), 태양풍, CME
│    ├── disaster (6)      지진, 화산, 산불, 홍수
│    ├── climate (6)       기온 이상, ENSO, 극한기후
│    ├── conflict (5)      전쟁, 사망자, 지정학리스크
│    └── power_grid (5)    EU 발전량, 탄소집약도, 원전
│
├─── 📊 Analysis & Visualization (38 tools / 2 servers)
│    ├── technical (5)     RSI, MACD, 볼린저, TA 요약
│    └── viz (33)          line, bar, candlestick, heatmap,
│                          treemap, sunburst, sankey, radar,
│                          choropleth map, violin, bubble...
│
├─── 🔬 Quant Engine (22 tools / 3 servers) — Phase 8
│    ├── quant_analysis (8) 상관, 회귀, Granger, 공적분
│    ├── timeseries (6)     분해, 정상성, ARIMA 예측
│    └── backtest (8)       전략 실행, 최적화, 위험분석
│
├─── 🎯 Professional Quant (18 tools / 3 servers) — Phase 9
│    ├── factor_engine (6)  팩터 스코어링, Fama-French
│    ├── signal_lab (6)     알파 시그널, 앙상블, 워크포워드
│    └── portfolio_opt (6)  Markowitz, 리스크패리티, Kelly
│
├─── 🧮 PhD-Level Math (18 tools / 3 servers) — Phase 10
│    ├── historical_data (6) Shiller(1871~), NBER(1854~)
│    ├── volatility (6)      GARCH, EGARCH, VIX 텀스트럭처
│    └── advanced_math (6)   Kalman, Hurst, 엔트로피, 웨이블릿
│
├─── 🎓 Academic Alpha (24 tools / 4 servers) — Phase 11
│    ├── stat_arb (6)       OU 피팅, 쌍거래, 코퓰라
│    ├── portfolio_adv (6)  Black-Litterman, HRP, RMT
│    ├── stochvol (6)       Heston, 점프확산, Almgren-Chriss
│    └── microstructure (6) Kyle's λ, VPIN, Amihud
│
├─── 🤖 Crypto Quant + ML (24 tools / 4 servers) — Phase 12
│    ├── crypto_quant (6)   펀딩비 아비트라지, 캐리
│    ├── onchain_adv (6)    거래소 흐름, HODL Waves
│    ├── ml_pipeline (6)    López de Prado AFML 전체
│    └── alpha_research (6) 턴오버, 디케이, 크라우딩
│
└─── 🧠 Infrastructure (25 tools / 5 servers)
     ├── vault (6)          Obsidian Vault CRUD
     ├── vault_index (3)    시맨틱 검색 (bge-m3)
     ├── memory (5)         SQLite + 벡터 메모리
     ├── ontology (5)       17-도메인 지식그래프
     └── gateway (6)        상태, 도구목록, 통계
```

---

## 3. 데이터 흐름 워크플로우 (Data Flow)

### 3-1. 단일 질의 흐름

```
┌──────────────────────────────────────────────────────────────────────┐
│                        USER QUERY                                     │
│  "삼성전자 투자 분석해줘"                                               │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     AI CLIENT (Claude Code)                           │
│                                                                       │
│  1. 질의 해석 → 필요한 도구 판단                                        │
│  2. MCP 도구 순차/병렬 호출                                             │
│  3. 결과 합성 → 사용자에게 보고                                         │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ MCP Protocol (streamable-http)
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      NEXUS GATEWAY                                    │
│                                                                       │
│  tools/call: stocks_quote(005930)                                     │
│       │                                                               │
│       ├──→ StocksServer.stocks_quote("005930")                        │
│       │         └──→ pykrx API → {price: 67800, per: 12.5, ...}      │
│       │                                                               │
│  tools/call: dart_financial_statements(삼성전자, 2024)                  │
│       │                                                               │
│       ├──→ DARTServer.dart_financial_statements(...)                   │
│       │         └──→ OpenDART API → {revenue: 258T, ...}              │
│       │                                                               │
│  tools/call: val_dcf_valuation(005930)                                │
│       │                                                               │
│       ├──→ ValuationServer.val_dcf_valuation(...)                     │
│       │         └──→ DART + ECOS data → {fair_value: 82000, ...}      │
│       │                                                               │
│  tools/call: val_peer_comparison(005930)                              │
│       │                                                               │
│       ├──→ ValuationServer.val_peer_comparison(...)                   │
│       │         └──→ DART + Yahoo → {peers: [...], chart_data: ...}   │
│       │                                                               │
│  tools/call: viz_bar_chart(peer_data)                                 │
│       │                                                               │
│       └──→ VizServer.viz_bar_chart(...)                               │
│                 └──→ Plotly → base64 PNG chart                        │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       USER OUTPUT                                     │
│                                                                       │
│  "삼성전자 현재가 67,800원 (PER 12.5배)                                 │
│   DCF 적정가 82,000원 → 현재 17% 저평가                                 │
│   반도체 피어 대비 PBR 하단                                              │
│   [피어 비교 차트 첨부]"                                                 │
└──────────────────────────────────────────────────────────────────────┘
```

### 3-2. 멀티도메인 리서치 워크플로우

```
USER: "BTC 펀딩비 이상 + 태양 흑점 상관관계 분석해줘"
                    │
    ┌───────────────┼───────────────┐
    │               │               │
    ▼               ▼               ▼
┌────────┐   ┌──────────┐   ┌───────────┐
│ Crypto │   │  Space   │   │  Quant    │
│ Quant  │   │  Weather │   │  Analysis │
├────────┤   ├──────────┤   ├───────────┤
│funding │   │sunspot   │   │lagged     │
│_rate   │   │_data     │   │_correlation│
│basis   │   │solar     │   │granger    │
│_term   │   │_flares   │   │_causality │
│open    │   │          │   │regression │
│_interest│  │          │   │           │
└───┬────┘   └────┬─────┘   └─────┬─────┘
    │             │               │
    └─────────────┴───────────────┘
                  │
                  ▼
           ┌────────────┐
           │ Viz Server │
           ├────────────┤
           │ heatmap    │
           │ dual_axis  │
           │ scatter    │
           └─────┬──────┘
                 │
                 ▼
    ┌──────────────────────┐
    │   COMBINED OUTPUT     │
    │                       │
    │  • 펀딩비 시계열      │
    │  • 흑점 데이터 오버레이│
    │  • 시차 상관 히트맵   │
    │  • Granger 인과검정   │
    │  • 산점도 + 회귀선    │
    └──────────────────────┘
```

---

## 4. 도구 입력 패턴 분류 (Input Patterns)

```
396 Tools
│
├── stock_code (종목코드)     예: "005930", "AAPL"
│   └── 50+ tools: stocks_*, dart_*, val_*, factor_*, backtest_*
│
├── keyword (검색어)           예: "삼성전자", "transformer"
│   └── 40+ tools: news_*, academic_*, research_*, patent_*
│
├── indicator (지표코드)       예: "FEDFUNDS", "722Y001"
│   └── 30+ tools: ecos_*, macro_*, kosis_*
│
├── symbol (크립토 심볼)       예: "BTC", "ETH/USDT"
│   └── 36 tools: crypto_*, cquant_*, onchain_*, defi_*
│
├── data_array (데이터 배열)   예: [100, 102, 98, ...]
│   └── 80+ tools: quant_*, ts_*, vol_*, math_*, viz_*
│
├── no_input (파라미터 없음)   예: gateway_status()
│   └── 60+ tools: *_snapshot, *_overview, *_status
│
└── composite (복합)           예: {stock:"005930", period:"2024"}
    └── 30+ tools: val_dcf_*, backtest_portfolio, portadv_*
```

---

## 5. 핵심 워크플로우 7선 (Use Case Map)

```
┌─────────────────────────────────────────────────────────────────┐
│                    7 CORE WORKFLOWS                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ① Equity Deep Dive ─────────────────────────────────────────── │
│     stocks → dart → valuation → viz                              │
│     "삼성전자 종합 분석" → DCF 적정가 + 피어 차트                   │
│                                                                   │
│  ② Macro Policy Research ────────────────────────────────────── │
│     ecos → fred → granger → forecast → dual_axis                 │
│     "한미 금리 비교" → 인과관계 + 12개월 예측                       │
│                                                                   │
│  ③ Academic Literature Survey ───────────────────────────────── │
│     arxiv → semantic_scholar → citations                         │
│     "transformer 금융 논문" → 인용순 Top 10                       │
│                                                                   │
│  ④ Crypto Quant Signal ─────────────────────────────────────── │
│     market_structure → funding → basis → mvrv → arb              │
│     "BTC 펀딩비 분석" → 아비트라지 기회 탐지                        │
│                                                                   │
│  ⑤ Alternative Data Correlation ────────────────────────────── │
│     sunspot → lagged_corr → enso → risk → heatmap               │
│     "흑점-시장 상관" → 시차 상관 히트맵                              │
│                                                                   │
│  ⑥ Competition Report ──────────────────────────────────────── │
│     ecos → country_compare → decompose → choropleth              │
│     "가계부채 분석" → 국제비교 + 지도 시각화                         │
│                                                                   │
│  ⑦ Multi-Factor Portfolio ──────────────────────────────────── │
│     factor_score → hrp → backtest → drawdown → chart             │
│     "팩터 포트폴리오" → 최적화 + 백테스트 결과                       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. 기술 스택 & 의존성

```
┌─────────────────────────────────────────────────────────────────┐
│                      TECH STACK                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Runtime          Python 3.12+                                    │
│  MCP Framework    FastMCP 3.x (streamable-http, stdio, sse)       │
│  Web Server       nginx 1.24 (reverse proxy, rate limiting)       │
│  Process Manager  systemd (nexus-finance-mcp.service)             │
│                                                                   │
│  Core Libraries:                                                  │
│  ├── pykrx         한국 주식 데이터                                 │
│  ├── ccxt           100+ 크립토 거래소                               │
│  ├── plotly         인터랙티브 차트 (33종)                           │
│  ├── matplotlib     정적 차트                                       │
│  ├── scipy          통계분석, 최적화                                  │
│  ├── statsmodels    GARCH, ARIMA, Granger                          │
│  ├── arch           EGARCH, 변동성 모델                              │
│  ├── numpy/pandas   데이터 처리                                      │
│  ├── scikit-learn   ML 파이프라인                                    │
│  └── httpx/aiohttp  비동기 API 호출                                  │
│                                                                   │
│  Infrastructure:                                                  │
│  ├── Obsidian Vault   지식 저장소 (PARA 방법론)                      │
│  ├── Ollama bge-m3    시맨틱 검색 임베딩                              │
│  ├── SQLite           메모리 + 벡터 DB                               │
│  └── systemd          서비스 관리 + 자동 재시작                        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. 서버 마운트 순서 (Phase별 진화)

```
v2.0 ──→ Phase 1 ──→ Phase 2 ──→ ... ──→ Phase 12 ──→ Phase 14
 (7)       (+5)        (+7)                  (+4)        (+32)

Timeline:
┌─────┬─────────┬───────┬────────────────────────────────────────┐
│Phase│ Servers │ Tools │ Added Domains                           │
├─────┼─────────┼───────┼────────────────────────────────────────┤
│ v2  │   7     │  ~60  │ ECOS, DART, Valuation, Viz, KOSIS     │
│  1  │  +5     │  +30  │ Crypto, DeFi, OnChain, News           │
│  2  │  +7     │  +40  │ Global Macro, US Equity, Academic      │
│  3  │  +7     │  +30  │ Maritime, Aviation, Energy, Agriculture│
│  4  │  +5     │  +20  │ Research (RISS), SEC, Health, Consumer │
│  5  │  +1     │  +4   │ Japan EDINET                           │
│  6  │  +5     │  +20  │ RSS, Technical, Asia, India, Regulation│
│  7  │  +6     │  +32  │ Space Weather, Disaster, Climate       │
│  8  │  +3     │  +22  │ Quant Analysis, TimeSeries, Backtest   │
│  9  │  +3     │  +18  │ Factor Engine, Signal Lab, Portfolio   │
│ 10  │  +3     │  +18  │ Historical(150yr), GARCH, Kalman       │
│ 11  │  +4     │  +24  │ Stat Arb, Black-Litterman, Heston     │
│ 12  │  +4     │  +24  │ Crypto Quant, ML Pipeline, Alpha      │
│ 13  │   —     │   —   │ (표준화/문서화, 도구 수 변경 없음)       │
│ 14  │  +4     │  +32  │ DART 확장, CCXT, SEC, ECOS, FRED 추가  │
├─────┼─────────┼───────┼────────────────────────────────────────┤
│TOTAL│  64     │  396  │ 15 domains, 50+ API sources            │
└─────┴─────────┴───────┴────────────────────────────────────────┘
```

---

## 8. API 키 의존성 맵

```
                    ┌─────────────────┐
                    │   API KEY MAP   │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼─────┐      ┌─────▼────┐       ┌──────▼──────┐
    │ REQUIRED │      │RECOMMEND │       │  OPTIONAL   │
    │  (2 keys)│      │ (2 keys) │       │ (8+ keys)   │
    ├──────────┤      ├──────────┤       ├─────────────┤
    │BOK_ECOS  │      │KOSIS     │       │FINNHUB      │
    │DART      │      │FRED      │       │ETHERSCAN    │
    │          │      │          │       │EIA          │
    │ → 41 tools│     │ → 15 tools│      │NAVER        │
    │ (한국경제)│      │ (통계+US)│       │KIS          │
    └──────────┘      └──────────┘       │NASA         │
                                         │ENTSOE       │
                                         │ACLED        │
                                         │ → 30+ tools │
                                         └─────────────┘

    ┌──────────────────────────────────────┐
    │  NO KEY REQUIRED: 200+ tools         │
    │                                      │
    │  퀀트분석 · 백테스트 · 팩터모델      │
    │  변동성 · 수학 · ML 파이프라인       │
    │  시각화(33종) · 대안데이터 대부분    │
    │  크립토(CCXT) · 메모리 · Vault       │
    └──────────────────────────────────────┘
```

---

*Generated by Nexus Finance MCP · v8.0.0-phase14 · 2026-04-08*
