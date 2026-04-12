# Nexus Finance MCP Server - 완전 해부 문서

> v8.0.0-phase14 | 2026-04-12 작성 | Luxon AI

---

## 0. 30초 요약 (Elevator Pitch)

**이 프로젝트가 무엇인지:**
Nexus Finance MCP는 AI 에이전트가 금융 데이터에 접근할 수 있게 해주는 "금융 데이터 허브"다. 한국은행 금리부터 미국 SEC 공시, 암호화폐 거래소 시세, 우주 날씨까지 60개 이상의 외부 API를 하나의 엔드포인트(`/mcp`)로 통합하여, AI가 398개의 도구를 호출하면 실시간 금융 데이터를 받아볼 수 있다. MCP(Model Context Protocol) 표준을 따르므로 Claude, Cursor, Windsurf 등 MCP 지원 클라이언트에서 바로 연결 가능하다.

**핵심 문제 1줄 요약:**
AI 에이전트가 실시간 금융 데이터를 수집하려면 수십 개의 API를 각각 연동해야 하는 문제를, 단일 MCP 서버로 통합 해결.

---

## 1. 프로젝트 정체성 & 가치

| 항목 | 내용 |
|------|------|
| **공식 프로젝트명** | Nexus Finance MCP Server |
| **버전** | v8.0.0-phase14 |
| **라이선스** | MIT License (Copyright 2026 Luxon AI) |
| **GitHub** | github.com/pollmap/nexus-finance-mcp |
| **Smithery** | smithery.ai 마켓플레이스 등록 완료 |

### Why does this exist?

AI 에이전트가 금융 분석을 수행하려면 한국은행 ECOS, DART 공시, FRED, SEC EDGAR, CoinGecko 등 수십 개의 API를 각각 인증하고, 응답 포맷을 파싱하고, 에러를 처리해야 한다. 이 작업은 반복적이고 지루하며, API별로 인증 방식/응답 포맷/레이트 리밋이 전부 다르다. Nexus Finance MCP는 이 모든 것을 하나의 표준화된 인터페이스(MCP)로 감싸서, AI 에이전트가 `dart_financial_statements(stock_code="005930")`처럼 함수 하나만 호출하면 삼성전자 재무제표를 받을 수 있게 한다.

### What makes it unique?

1. **한국 금융 특화**: ECOS, DART, KOSIS, KRX, RONE 등 한국 공공데이터 API를 MCP로 제공하는 유일한 서버
2. **규모**: 398개 도구 / 64개 서버 / 51개 어댑터 — 세계 최대 규모의 단일 금융 MCP 서버
3. **퀀트 수학 내장**: DCF, GARCH, Heston, Kalman Filter, HRP, Lopez de Prado ML 등 PhD급 퀀트 분석 엔진 내장
4. **가짜 데이터 없음**: 모든 응답은 실제 API 호출 결과. Mock/샘플 데이터 절대 사용 안 함
5. **무료 호스팅**: API 키 없이도 200+ 도구 사용 가능한 공개 엔드포인트 제공

### 타겟 사용자

- **AI 에이전트 개발자**: Claude Code, Cursor, Windsurf 등에서 금융 데이터 접근
- **퀀트 리서처**: 팩터 분석, 백테스팅, 통계적 차익거래 연구
- **금융 분석가**: 기업 밸류에이션, 거시경제 분석, 크로스마켓 비교
- **개인 투자자**: 한국 주식 공시/재무제표 조회, 김치 프리미엄 계산

### 현재 성숙도

**Beta → Production-ready 전환 단계**
- 64/64 서버 로드 성공 (0 실패)
- 398개 도구 등록 완료
- 8시간+ 연속 가동 (345MB 메모리)
- systemd 자동 재시작 설정 완료
- 하지만 SLA 없음, 단일 서버 운영

### 비즈니스/실용적 가치

| 가치 | 설명 |
|------|------|
| **시간 절감** | API 60개 각각 연동하면 2-3주 → MCP 연결 1분 |
| **비용 절감** | API 키 사전 설정된 호스팅 서버 무료 제공 |
| **분석 품질** | DCF/GARCH/HRP 등 전문가급 분석 도구 내장 |
| **데이터 커버리지** | 한국+미국+일본+아시아+크립토+대체데이터 원스톱 |

---

## 2. 전체 아키텍처 조감도

```
┌─────────────────────────────────────────────────────────────────┐
│            Nexus Finance MCP Server v8.0.0-phase14              │
│                    전체 아키텍처 조감도                            │
└─────────────────────────────────────────────────────────────────┘

[AI 클라이언트]                              [연결 프로토콜]
 Claude Code ─────┐                         ┌─ streamable-http (POST /mcp)
 Cursor IDE ──────┤                         ├─ SSE (GET /sse)
 Windsurf ────────┼── MCP Protocol ─────────┼─ stdio (stdin/stdout)
 Python SDK ──────┤                         └─ (cURL 직접 호출)
 cURL / httpx ────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Nginx Reverse Proxy (62.171.141.206:80 → 127.0.0.1:8100)      │
│  Rate Limit: 5 req/s per IP, 10 req/s global                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  server.py (진입점)                                              │
│  - argparse: --transport, --host, --port, --stateless           │
│  - dotenv 로드 → GatewayServer 생성 → mcp.run()                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  GatewayServer (gateway_server.py)                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ FastMCP("nexus-finance-mcp")                              │  │
│  │                                                           │  │
│  │ mount() x 64 서버 (flat merge, no namespace)              │  │
│  │                                                           │  │
│  │ 6 Gateway Tools:                                          │  │
│  │   gateway_status / list_available_tools /                 │  │
│  │   list_tools_by_domain / list_tools_by_pattern /          │  │
│  │   tool_info / api_call_stats                              │  │
│  │                                                           │  │
│  │ 3 Prompt Templates:                                       │  │
│  │   korean_company_analysis / macro_snapshot /               │  │
│  │   crypto_arbitrage                                        │  │
│  │                                                           │  │
│  │ Custom Routes: GET /health                                │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────┬───────────────────────────────────────┬────────────────┘
         │                                       │
         ▼                                       ▼
┌─────────────────────┐              ┌──────────────────────────┐
│  64 Sub-Servers      │              │  Core Infrastructure     │
│  (BaseMCPServer)     │              │                          │
│                      │              │  ┌──────────────────┐    │
│  각 서버:             │              │  │ CacheManager     │    │
│  - name property     │              │  │ L1: LRU (100)    │    │
│  - _register_tools() │              │  │ L2: TTL (1000)   │    │
│  - adapter 인스턴스   │◀────uses────│  │ L3: DiskCache    │    │
│                      │              │  └──────────────────┘    │
│  도구 호출 흐름:      │              │  ┌──────────────────┐    │
│  @mcp.tool()         │              │  │ RateLimiter      │    │
│    → adapter method  │              │  │ TokenBucket/서비스│    │
│    → external API    │              │  │ 11개 서비스 쿼터   │    │
│    → response format │              │  └──────────────────┘    │
└─────────┬───────────┘              │  ┌──────────────────┐    │
          │                           │  │ APICounter       │    │
          ▼                           │  │ 일별 호출 통계    │    │
┌─────────────────────────────────┐   │  └──────────────────┘    │
│  51 Adapters                     │   │  ┌──────────────────┐    │
│  (외부 API 래퍼)                  │   │  │ responses.py     │    │
│                                  │   │  │ sanitize_records │    │
│  dart_adapter  ccxt_adapter      │   │  │ error_response   │    │
│  krx_adapter   backtest_adapter  │   │  │ success_response │    │
│  ... 47 more adapters            │   │  └──────────────────┘    │
└────────────┬────────────────────┘   └──────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       External APIs (60+)                       │
│                                                                 │
│  [한국 공공]          [글로벌]          [크립토]                   │
│  BOK ECOS             FRED              Binance (via CCXT)      │
│  DART/OpenDART        SEC EDGAR         Upbit                   │
│  KOSIS                Yahoo Finance     CoinGecko               │
│  KRX/pykrx            Finnhub           Etherscan               │
│  한국부동산원(RONE)    World Bank        DefiLlama               │
│  국토부(MOLIT)        BIS               Polymarket              │
│  FSC                  OECD/SDMX                                 │
│                       EDINET (Japan)                            │
│                                                                 │
│  [대체데이터]          [뉴스/리서치]      [실물경제]               │
│  NASA DONKI           GDELT              UN Comtrade            │
│  ENTSO-E              arXiv              USDA PSD               │
│  ACLED                Semantic Scholar   FAO                    │
│  Electricity Maps     Google Scholar     IATA                   │
│  GDACS                Naver News         IMO (Maritime)         │
│                       RSS (14 sources)                          │
└─────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Data / Storage Layer                        │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ .cache/     │  │ output/      │  │ vault/                 │ │
│  │ diskcache/  │  │ api_logs/    │  │ (Obsidian Vault 연동)   │ │
│  │ (SQLite)    │  │ charts/      │  │                        │ │
│  │ L3 캐시      │  │ reports/     │  │ memory/                │ │
│  └─────────────┘  └──────────────┘  │ (벡터 임베딩 + BM25)    │ │
│                                     └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 디렉터리 & 파일 구조 전체 해부

```
nexus-finance-mcp/                          # 프로젝트 루트
├── ★ server.py                             # 진입점 — HTTP/SSE/stdio 서버 부트스트랩 (109줄)
├── ★ requirements.txt                      # Python 의존성 32개 패키지 (70줄)
├── requirements-test.txt                   # 테스트 의존성 (pytest, httpx)
├── pytest.ini                              # pytest 설정 (asyncio_mode=auto)
├── .env.template                           # 환경변수 템플릿 (20+ API 키)
├── .env                                    # 실제 환경변수 (gitignore됨)
├── .gitignore                              # .env*, __pycache__, .cache/, output/ 등
├── .dockerignore                           # Docker 빌드 제외 목록
├── Dockerfile                              # Python 3.12-slim 기반 Docker 이미지 (22줄)
├── deploy.sh                               # VPS 배포 스크립트 (systemd 연동, 89줄)
├── nexus-finance-mcp.service               # systemd 유닛 파일 (25줄)
├── smithery.yaml                           # Smithery 마켓플레이스 설정 (stdio 모드)
├── test_tools.py                           # 루트 레벨 도구 검증 스크립트
├── LICENSE                                 # MIT License
├── README.md                               # 메인 문서 (22,505자)
├── CHANGELOG.md                            # Phase 1~14 변경 이력
├── CONNECT.md                              # 연결 가이드 (8개 클라이언트)
├── CONTRIBUTING.md                         # 기여 가이드
│
├── ★ mcp_servers/                          # 핵심 소스코드
│   ├── __init__.py
│   │
│   ├── ★ gateway/                          # 게이트웨이 레이어
│   │   ├── __init__.py
│   │   └── ★ gateway_server.py             # 64개 서버 마운트 + 6 게이트웨이 도구 (309줄)
│   │
│   ├── ★ core/                             # 핵심 인프라
│   │   ├── __init__.py
│   │   ├── ★ base_server.py                # BaseMCPServer ABC + 데코레이터 (258줄)
│   │   ├── ★ cache_manager.py              # 3-tier 캐시 (L1 LRU/L2 TTL/L3 DiskCache) (313줄)
│   │   ├── ★ rate_limiter.py               # Token Bucket 레이트 리밋 (293줄)
│   │   ├── api_counter.py                  # API 호출 통계 트래커 (104줄)
│   │   ├── responses.py                    # 표준 응답 헬퍼 (sanitize_records 등, 86줄)
│   │   └── tool_metadata.py                # 도구 메타데이터 레지스트리 (자동생성)
│   │
│   ├── ★ adapters/                         # 외부 API 래퍼 (51개 파일, 21,609줄)
│   │   ├── __init__.py
│   │   ├── ★ dart_adapter.py               # DART 공시 시스템 (36KB)
│   │   ├── ★ backtest_adapter.py           # 포트폴리오 백테스팅 (54KB, 최대)
│   │   ├── ★ signal_lab_adapter.py         # 시그널 생성 엔진 (45KB)
│   │   ├── ★ advanced_math_adapter.py      # 퀀트 수학 (40KB)
│   │   ├── ★ factor_engine_adapter.py      # 멀티팩터 스코어링 (38KB)
│   │   ├── ★ volatility_model_adapter.py   # GARCH/Heston/SABR (35KB)
│   │   ├── ★ krx_adapter.py               # 한국거래소 데이터 (21KB)
│   │   ├── stat_arb_adapter.py             # 통계적 차익거래 (31KB)
│   │   ├── historical_data_adapter.py      # 150년+ 역사 데이터 (31KB)
│   │   ├── portfolio_optimizer_adapter.py  # 포트폴리오 최적화 (30KB)
│   │   ├── portfolio_advanced_adapter.py   # HRP/Black-Litterman (29KB)
│   │   ├── quant_analysis_adapter.py       # 기본 퀀트 분석 (28KB)
│   │   ├── ml_pipeline_adapter.py          # Lopez de Prado ML (25KB)
│   │   ├── ontology_adapter.py             # 데이터 존재론 (25KB)
│   │   ├── timeseries_adapter.py           # 시계열 분석 (23KB)
│   │   ├── stochvol_adapter.py             # 확률적 변동성 (23KB)
│   │   ├── microstructure_adapter.py       # 시장 미시구조 (21KB)
│   │   ├── crypto_quant_adapter.py         # 크립토 퀀트 (21KB)
│   │   ├── alpha_research_adapter.py       # 알파 리서치 (21KB)
│   │   ├── onchain_advanced_adapter.py     # 온체인 메트릭 (19KB)
│   │   ├── sec_adapter.py                  # SEC EDGAR (17KB)
│   │   ├── global_macro_adapter.py         # 글로벌 매크로 (16KB)
│   │   ├── regulation_adapter.py           # 규제 데이터 (16KB)
│   │   ├── gdelt_academic_adapter.py       # GDELT + 학술 (15KB)
│   │   ├── climate_adapter.py              # 기후 데이터 (14KB)
│   │   ├── disaster_adapter.py             # 재난 모니터링 (14KB)
│   │   ├── yahoo_adapter.py               # Yahoo Finance (13KB)
│   │   ├── conflict_adapter.py             # 분쟁 데이터 ACLED (13KB)
│   │   ├── kis_adapter.py                  # 한국투자증권 (12KB)
│   │   ├── asia_market_adapter.py          # 아시아 시장 (12KB)
│   │   ├── technical_adapter.py            # 기술적 분석 (11KB)
│   │   ├── sentiment_adapter.py            # 감성 분석 (10KB)
│   │   ├── power_grid_adapter.py           # 전력 그리드 (10KB)
│   │   ├── research_adapter.py             # 리서치 (9KB)
│   │   ├── phase2_adapters.py              # Phase 2 통합 어댑터 (8KB)
│   │   ├── ccxt_adapter.py                 # 100+ 거래소 통합 (8KB)
│   │   ├── india_adapter.py                # 인도 시장 (8KB)
│   │   ├── space_weather_adapter.py        # 우주 날씨 NASA (7KB)
│   │   ├── health_adapter.py               # 건강 데이터 (7KB)
│   │   ├── rss_adapter.py                  # RSS 피드 (7KB)
│   │   ├── edinet_adapter.py               # 일본 EDINET (6KB)
│   │   ├── defi_adapter.py                 # DeFi TVL (4KB)
│   │   ├── naver_adapter.py                # 네이버 뉴스 (4KB)
│   │   ├── polymarket_adapter.py           # 예측 시장 (4KB)
│   │   ├── consumer_adapter.py             # 소비자 데이터 (3KB)
│   │   ├── phase3_adapters.py              # Phase 3 통합 어댑터 (20KB)
│   │   ├── etherscan_adapter.py            # 이더리움 블록체인 (3KB)
│   │   └── environ_adapter.py              # 환경 데이터 (3KB)
│   │
│   └── ★ servers/                          # MCP 서버 등록 (67개 파일, 10,331줄)
│       ├── __init__.py
│       ├── ★ ecos_server.py                # 한국은행 ECOS (1,127줄, 최대)
│       ├── ★ kosis_server.py               # 통계청 KOSIS (831줄)
│       ├── ★ valuation_server.py           # DCF 밸류에이션 (823줄)
│       ├── ★ dart_server.py                # DART 공시 (469줄)
│       ├── ★ rone_server.py                # 한국부동산원 (503줄)
│       ├── vault_index_server.py           # Vault 벡터 검색 (484줄)
│       ├── vault_server.py                 # Obsidian Vault CRUD (397줄)
│       ├── crypto_exchange_server.py       # 크립토 거래소 (349줄)
│       ├── technical_server.py             # 기술적 분석 (242줄)
│       ├── memory_server.py                # 시맨틱 메모리 (234줄)
│       ├── backtest_server.py              # 백테스팅 (234줄)
│       ├── stocks_server.py                # 주가 데이터 (225줄)
│       ├── signal_lab_server.py            # 시그널 랩 (224줄)
│       ├── ... (50+ more servers)
│       │
│       └── viz/                            # 시각화 모듈
│           ├── __init__.py
│           ├── base.py                     # BaseChart 클래스
│           ├── basic_charts.py             # line, bar, scatter 등
│           ├── advanced_charts.py          # candlestick, heatmap 등
│           ├── statistical_charts.py       # histogram, boxplot 등
│           ├── hierarchical_charts.py      # treemap, sunburst 등
│           └── map_charts.py              # choropleth 등
│
├── analyzers/                              # 금융 분석기
│   ├── __init__.py
│   ├── ★ dcf_analyzer.py                  # DCF 밸류에이션 엔진
│   ├── correlation_analyzer.py             # 상관관계 분석
│   ├── growth_calculator.py                # 성장률 계산기
│   ├── pir_calculator.py                   # PIR (가격소득비율)
│   ├── real_price_calculator.py            # 실질가격 계산
│   ├── relative_value.py                   # 상대가치 분석
│   └── defaults.py                         # 시장 기본 가정값
│
├── utils/                                  # 유틸리티
│   ├── __init__.py
│   ├── validation.py                       # 입력 검증 (6개 함수)
│   ├── http_client.py                      # HTTP 클라이언트 (retry + timeout)
│   ├── gaap_mapper.py                      # K-IFRS <-> US GAAP 매퍼
│   ├── sqlite_helpers.py                   # SQLite 유틸
│   └── embedding.py                        # 텍스트 임베딩
│
├── tests/                                  # 테스트 스위트
│   ├── __init__.py
│   ├── conftest.py                         # pytest 픽스처 (mock_env)
│   ├── test_gateway.py                     # 게이트웨이 테스트
│   ├── test_tools.py                       # 도구 호출 테스트
│   ├── test_utils.py                       # 유틸리티 테스트
│   ├── test_adapters/
│   │   └── __init__.py
│   └── framework/                          # 자동 테스트 프레임워크
│       ├── scanner.py                      # 도구 자동 스캔 (9KB)
│       ├── runner.py                       # 비동기 테스트 러너 (10KB)
│       ├── reporter.py                     # 리포트 생성 (12KB)
│       ├── param_inference.py              # 파라미터 자동 추론 (6KB)
│       ├── fixtures.py                     # 테스트 데이터 생성 (5KB)
│       ├── classifier.py                   # 도구 분류기 (2KB)
│       └── regression.py                   # 회귀 테스트 (3KB)
│
├── scripts/                                # 운영 스크립트
│   ├── generate_tool_metadata.py           # 도구 메타데이터 자동 생성
│   └── run_tool_verification.py            # 도구 검증 실행기
│
├── docs/                                   # 문서
│   ├── ARCHITECTURE.md                     # 기술 아키텍처
│   ├── TOOL_CATALOG.md                     # 398 도구 카탈로그
│   ├── USAGE_GUIDE.md                      # 사용 가이드
│   ├── DATA_FLOW.md                        # Mermaid 데이터 흐름도
│   ├── ERROR_REFERENCE.md                  # 에러 코드 레퍼런스
│   ├── PARSING_GUIDE.md                    # 응답 포맷 명세
│   ├── QUICK_REFERENCE.md                  # 한 페이지 치트시트
│   ├── TROUBLESHOOTING.md                  # 트러블슈팅
│   ├── COMPETITIVE_ANALYSIS.md             # 경쟁 분석
│   ├── COVERAGE_AUDIT.md                   # 커버리지 감사
│   ├── internal/                           # 내부 운영 문서
│   └── marketing/                          # 마케팅/프로모션
│
├── data/                                   # 정적 데이터
├── output/                                 # 실행 시 생성되는 출력
│   ├── api_logs/                           # 일별 API 호출 로그 (JSON)
│   ├── charts/                             # 생성된 차트 이미지
│   └── reports/                            # 생성된 리포트
├── memory/                                 # 시맨틱 메모리 저장소
├── vault/                                  # Obsidian Vault 연동 디렉터리
├── docs_cache/                             # 문서 캐시
├── .cache/                                 # DiskCache (L3 캐시, SQLite)
└── .actor/                                 # Apify Actor 설정
```

---

## 4. 기술 스택 & 의존성 지도

### 4-1. 핵심 기술 스택

| 레이어 | 기술 | 버전 | 선택 이유 |
|--------|------|------|-----------|
| **런타임** | Python | 3.12+ | 데이터 과학 생태계, async 지원, 타입힌트 |
| **MCP 프레임워크** | FastMCP | >=3.0.0 | MCP 프로토콜 구현, mount() API로 서버 합성 |
| **MCP 프로토콜** | mcp | >=1.0.0 | Model Context Protocol 표준 |
| **HTTP 서버** | uvicorn + starlette | >=0.30.0 | ASGI 서버, streamable-http 지원 |
| **SSE** | sse-starlette | >=2.0.0 | Server-Sent Events 전송 |
| **캐시 L1/L2** | cachetools | >=5.3.0 | LRU + TTL 인메모리 캐시 |
| **캐시 L3** | diskcache | >=5.6.0 | SQLite 기반 영구 캐시 |
| **데이터 처리** | pandas + numpy | >=2.0 / >=1.24 | 금융 데이터 테이블 처리 |
| **통계** | scipy + statsmodels | >=1.10 / >=0.14 | 통계 분석, ARIMA, Granger 인과 |
| **ML** | scikit-learn | >=1.3.0 | PCA, 클러스터링, 분류 |
| **퀀트 수학** | arch + hmmlearn + PyWavelets | >=7.0 | GARCH, HMM, 웨이블릿 |
| **크립토** | ccxt | >=4.0.0 | 100+ 거래소 통합 API |
| **한국 주식** | pykrx + OpenDartReader | >=1.0 / >=0.2 | 한국거래소/공시 데이터 |
| **시각화** | plotly + matplotlib | >=5.18 / >=3.7 | 인터랙티브 + 정적 차트 |
| **글로벌 매크로** | sdmx1 + wbgapi | >=2.0 / >=1.0 | OECD/World Bank API |
| **HTTP** | requests + aiohttp | >=2.31 / >=3.9 | 동기/비동기 HTTP |

### 4-2. 의존성 그래프

```
server.py
 └──▶ GatewayServer (gateway_server.py)
      ├──▶ FastMCP (fastmcp>=3.0.0)
      │     └──▶ mcp (>=1.0.0)
      │           ├──▶ uvicorn (>=0.30.0)
      │           ├──▶ starlette (>=0.37.0)
      │           └──▶ sse-starlette (>=2.0.0)
      │
      ├──▶ 64x Sub-Servers (BaseMCPServer)
      │     ├──▶ CacheManager
      │     │     ├──▶ cachetools (LRU + TTL)
      │     │     └──▶ diskcache (SQLite L3)
      │     │
      │     ├──▶ RateLimiter
      │     │     └──▶ (stdlib: time, asyncio, threading)
      │     │
      │     └──▶ 51x Adapters
      │           ├──▶ requests + aiohttp
      │           ├──▶ pandas + numpy
      │           ├── [한국] OpenDartReader, PublicDataReader, pykrx
      │           ├── [글로벌] yfinance, sdmx1, wbgapi
      │           ├── [크립토] ccxt
      │           ├── [퀀트] scipy, statsmodels, scikit-learn, arch, hmmlearn, PyWavelets
      │           ├── [시각화] plotly, matplotlib, kaleido
      │           └── [기타] scholarly, feedparser, pytrends, vaderSentiment, entsoe-py
      │
      └──▶ analyzers/ (dcf_analyzer, correlation_analyzer, growth_calculator)
```

---

## 5. 데이터 계층 완전 해부

### 5-1. 데이터 모델 / 스키마

**표준 응답 포맷** (responses.py):

```python
# 성공 응답
{"success": True, "data": [...], "count": 10, "source": "BOK ECOS"}

# 에러 응답
{"error": True, "message": "Stock code not found", "code": "NOT_FOUND"}
```

**핵심 데이터클래스:**

| 클래스 | 파일 | 필드 |
|--------|------|------|
| `CompanyFinancials` | dcf_analyzer.py | stock_code, company_name, revenue, ebit, ebitda, net_income, total_debt, cash, total_equity, shares_outstanding, capex, depreciation, change_in_nwc, market_cap, beta, cost_of_debt, tax_rate |
| `DCFResult` | dcf_analyzer.py | cost_of_equity, cost_of_debt_after_tax, wacc, projected_fcf[], pv_fcf[], terminal_value, pv_terminal_value, enterprise_value, equity_value, per_share_value, current_price, upside_potential |
| `FinancialItem` | gaap_mapper.py | name, value, standard(Enum), adjusted_value, adjustment_note |
| `AccountingStandard` | gaap_mapper.py | K_IFRS, US_GAAP, IFRS |
| `TokenBucket` | rate_limiter.py | capacity, rate, tokens, last_update |

**시장 기본 가정값** (defaults.py):

| 변수 | 값 | 설명 |
|------|-----|------|
| risk_free_rate | 3.5% | 한국은행 기준금리 근사 |
| market_risk_premium | 6% | 한국 시장 ERP 역사적 평균 |
| default_beta | 1.0 | 시장 평균 |
| default_tax_rate | 22% | 한국 법인세율 |
| terminal_growth_rate | 2% | 영구 성장률 |
| projection_years | 5 | DCF 추정 기간 |

### 5-2. 데이터 흐름 다이어그램

```
[AI 클라이언트 요청]
 │  예: dart_financial_statements(stock_code="005930")
 ▼
┌──────────────────────────────────────┐
│ FastMCP Router → @mcp.tool() 매칭     │
└────────────────┬─────────────────────┘
                 ▼
┌──────────────────────────────────────┐
│ Server Layer → validation → counter   │
└────────────────┬─────────────────────┘
                 ▼
┌──────────────────────────────────────┐
│ CacheManager.get()                   │
│  L1(LRU) → L2(TTL) → L3(Disk)       │
│  HIT → 즉시 반환 / MISS → 다음 단계   │
└────────────────┬─────────────────────┘
                 ▼ (캐시 미스)
┌──────────────────────────────────────┐
│ RateLimiter.acquire() → TokenBucket   │
└────────────────┬─────────────────────┘
                 ▼
┌──────────────────────────────────────┐
│ Adapter → http_client.safe_get()      │
│ → requests.Session (retry 3x)        │
│ → timeout 30s                        │
└────────────────┬─────────────────────┘
                 ▼
┌──────────────────────────────────────┐
│ External API (JSON 응답)              │
└────────────────┬─────────────────────┘
                 ▼
┌──────────────────────────────────────┐
│ sanitize_records(df) → NaN→None       │
│ success_response(data, source=...)    │
│ CacheManager.set() → 캐시 저장         │
└────────────────┬─────────────────────┘
                 ▼
┌──────────────────────────────────────┐
│ FastMCP → JSON-RPC 응답 직렬화        │
└──────────────────────────────────────┘
```

### 5-3. 저장소 전략

| 저장소 | 유형 | 경로 | TTL |
|--------|------|------|-----|
| L1 캐시 | 인메모리 LRU | N/A | 크기 제한 (100개) |
| L2 캐시 | 인메모리 TTL | N/A | 1시간 기본 |
| L3 캐시 | SQLite DiskCache | .cache/diskcache/ | 데이터 타입별 |
| API 로그 | JSON 파일 | output/api_logs/ | 일별 파일 |
| 차트 | PNG/HTML | output/charts/ | 수동 삭제 |
| Vault | Markdown | vault/ | 영구 (Git) |
| Memory | JSON+임베딩 | memory/ | 영구 |

**TTL 정책:**

| 데이터 타입 | TTL | 예시 |
|-------------|-----|------|
| realtime_price | 60초 | 주가, 환율, 크립토 시세 |
| daily_data | 1시간 | 일간 OHLCV, 금리, CPI |
| historical | 24시간 | 과거 재무제표 |
| static_meta | 1주 | 기업 정보, 종목 리스트 |

---

## 6. 핵심 워크플로우 & 시퀀스 다이어그램

### 시나리오 1: 한국 기업 종합 분석

```
사용자(AI)       GatewayServer     DARTServer      DartAdapter     OpenDART API
    │                │                │                │                │
    │──korean_company│                │                │                │
    │  _analysis     │                │                │                │
    │  ("005930")───▶│                │                │                │
    │◀──Prompt 반환──│                │                │                │
    │                │                │                │                │
    │──dart_company  │                │                │                │
    │  _info ───────▶│───────────────▶│                │                │
    │                │                │──Cache(MISS)   │                │
    │                │                │──RateLimit ────│                │
    │                │                │──adapter()────▶│──GET──────────▶│
    │                │                │                │◀──JSON─────────│
    │                │                │◀──sanitize+set─│                │
    │◀──success_response─────────────│                │                │
    │                │                │                │                │
    │──(반복 x8 도구)│                │                │                │
```

### 시나리오 2: 크립토 김치 프리미엄

```
사용자(AI)       CryptoServer      CCXTAdapter      Upbit       Binance
    │                │                │              │              │
    │──crypto_kimchi │                │              │              │
    │  _premium──────▶│──adapter()───▶│              │              │
    │                │                │──fetch_ticker─▶│              │
    │                │                │◀──BTC/KRW─────│              │
    │                │                │──fetch_ticker──│─────────────▶│
    │                │                │◀──BTC/USDT────│──────────────│
    │                │                │ (환율 적용, 프리미엄 계산)      │
    │◀──{premium: 2.3%, kr_price, gl_price}          │              │
```

### 시나리오 3: 게이트웨이 상태 (가장 단순)

```
사용자(AI)       GatewayServer
    │                │
    │──gateway_status()──▶│
    │◀──{status:"online", version:"8.0.0-phase14", loaded:64, failed:0}
```

---

## 7. 모듈별 세부 엔지니어링

### 7-1. Core Infrastructure

#### server.py (109줄)
- **목적**: CLI → MCP 서버 부트스트랩
- **핵심**: `create_server()` → GatewayServer, `main()` → argparse + mcp.run()

#### gateway_server.py (309줄)
- **목적**: 64개 서브서버 합성
- **핵심**: `_load_server()` — importlib 동적 로드 + mount()
- **패턴**: Composite Pattern (flat merge, no namespace)

#### base_server.py (258줄)
- **목적**: 서브서버 공통 인프라
- **핵심**: `BaseMCPServer(ABC)` — _cached_request(), _rate_limited()
- **데코레이터**: `tool_handler`, `async_tool_handler`

#### cache_manager.py (313줄)
- **목적**: L1→L2→L3 다단계 캐시
- **핵심**: get() 3-tier 순차 조회 + 상위 승격, set() 모든 tier 저장
- **싱글턴**: `get_cache()` thread-safe lazy init

#### rate_limiter.py (293줄)
- **목적**: 서비스별 API 레이트 제한
- **핵심**: TokenBucket 데이터클래스, RateLimiter.acquire() blocking wait
- **쿼터**: dart(100), ecos(60), kosis(60), fred(120), krx(100), yahoo(200), coingecko(50) RPM

#### responses.py (86줄)
- **목적**: 응답 표준화
- **핵심**: `sanitize_records(df)` — NaN/Inf→None, `success_response()`, `error_response()`

#### api_counter.py (104줄)
- **목적**: 도구 호출 추적
- **핵심**: 싱글턴 APICounter, 100건마다 디스크 저장, 일별 파일

### 7-2. Utilities

#### validation.py (103줄)
- 6개 검증 함수: stock_code, series_id, search_query, date, date_range, positive_int
- 보안: `<>{}|\\^~[]`` 제거 (인젝션 방지)

#### http_client.py (91줄)
- get_session(): 서비스별 Session 풀링, Retry(3x, backoff 0.5s)
- safe_get(): GET + JSON 파싱 + 에러 래핑
- User-Agent: NexusFinanceMCP/3.0

#### gaap_mapper.py
- K-IFRS <-> US GAAP 변환 (R&D 자본화 차이 등)

### 7-3. Analyzers

#### dcf_analyzer.py
- CAPM → WACC → FCF 추정 → Terminal Value → DCF
- Fallback: ECOS 실패 시 MARKET_DEFAULTS 사용 + 경고

### 7-4. 주요 어댑터 (Top 10 by size)

| 어댑터 | 크기 | 외부 API | 주요 기능 |
|--------|------|----------|-----------|
| backtest_adapter | 54KB | 내부 계산 | 6종 전략 백테스트 (RSI/MACD/Bollinger/MA/Mean Rev/Momentum) |
| signal_lab_adapter | 45KB | 내부 계산 | 시그널 생성/조합/성과 측정 |
| advanced_math_adapter | 40KB | 내부 계산 | Hurst, Wavelet, Entropy, Kalman, GARCH |
| factor_engine_adapter | 38KB | 내부 계산 | 5팩터 스코어링 (Momentum/Value/Quality/Size/Vol) |
| dart_adapter | 36KB | OpenDART | 기업 공시 전체 (재무제표/비율/배당/대주주) |
| volatility_model_adapter | 35KB | 내부 계산 | GARCH/Heston/SABR/EWMA |
| stat_arb_adapter | 31KB | 내부 계산 | 공적분/페어스/OU Process |
| historical_data_adapter | 31KB | Shiller/NBER/French | 150년+ 역사 데이터 |
| portfolio_advanced_adapter | 29KB | 내부 계산 | HRP/Black-Litterman |
| ml_pipeline_adapter | 25KB | 내부 계산 | Triple Barrier/Meta-Label/Purged KFold |

---

## 8. API / 인터페이스 명세

### 8-1. 전송 프로토콜

| 프로토콜 | 엔드포인트 | 용도 |
|----------|-----------|------|
| streamable-http | POST /mcp | 권장 |
| SSE | GET /sse | 레거시 |
| stdio | stdin/stdout | 로컬 Claude Code |
| Health | GET /health | 상태 확인 |

### 8-2. Health 엔드포인트

```json
GET /health
{
    "status": "ok",
    "version": "8.0.0-phase14",
    "loaded_servers": 64,
    "failed_servers": 0,
    "tool_count": 398,
    "uptime_seconds": 30627
}
```

### 8-3. 인증

- Bearer Token (선택): MCP_AUTH_TOKEN 환경변수
- 현재: 공개 액세스
- Nginx: IP별 5 req/s, 전역 10 req/s

### 8-4. 게이트웨이 도구 (6개)

| 도구 | 파라미터 | 반환 |
|------|----------|------|
| gateway_status() | - | {status, version, loaded, failed, servers[]} |
| list_available_tools(include_metadata) | bool | {total:398, tools:[...]} |
| list_tools_by_domain(domain) | str | {domain, count, tools[]} |
| list_tools_by_pattern(pattern) | str | {pattern, count, tools[]} |
| tool_info(tool_name) | str | {tool, description, parameters} |
| api_call_stats() | - | {today, total_calls, top_tools[]} |

### 8-5. 에러 코드

| 코드 | 의미 |
|------|------|
| INVALID_INPUT | 파라미터 검증 실패 |
| NOT_FOUND | 데이터 없음 |
| API_UNAVAILABLE | 외부 API 접속 불가 |
| RATE_LIMITED | 레이트 리밋 초과 |
| NOT_INITIALIZED | 초기화 실패 |
| INTERNAL_ERROR | 내부 오류 |
| TOOL_ERROR | 도구 실행 오류 |

---

## 9. 설정 & 환경변수 완전 가이드

| 변수명 | 기본값 | 필수 | 설명 |
|--------|--------|------|------|
| **서버 설정** | | | |
| MCP_TRANSPORT | streamable-http | N | 전송 프로토콜 |
| MCP_HOST | 127.0.0.1 | N | 바인드 호스트 |
| MCP_PORT | 8100 | N | 바인드 포트 |
| MCP_STATELESS | false | N | stateless HTTP 모드 |
| MCP_AUTH_TOKEN | (빈) | N | Bearer 인증 토큰 |
| **한국 공공 API** | | | |
| BOK_ECOS_API_KEY | - | **Y** | 한국은행 ECOS |
| DART_API_KEY | - | **Y** | OpenDART 공시 |
| KOSIS_API_KEY | - | N | 통계청 KOSIS |
| RONE_API_KEY | - | N | 한국부동산원 |
| KRX_API_KEY | - | N | 한국거래소 |
| KIS_API_KEY | - | N | 한국투자증권 |
| MOLIT_API_KEY | - | N | 국토교통부 |
| **한국 검색** | | | |
| NAVER_CLIENT_ID | - | N | 네이버 검색 API |
| NAVER_CLIENT_SECRET | - | N | 네이버 검색 Secret |
| **글로벌 API** | | | |
| FRED_API_KEY | - | N | Federal Reserve FRED |
| FINNHUB_API_KEY | - | N | Finnhub 미국 주식 |
| EIA_API_KEY | - | N | US 에너지정보청 |
| EDINET_API_KEY | - | N | 일본 EDINET |
| **크립토** | | | |
| ETHERSCAN_API_KEY | - | N | Etherscan |
| **대체 데이터** | | | |
| NASA_API_KEY | - | N | NASA (DEMO_KEY 가능) |
| ENTSOE_API_KEY | - | N | ENTSO-E 전력 |
| ELECTRICITY_MAPS_TOKEN | - | N | Electricity Maps |
| ACLED_API_KEY | - | N | ACLED 분쟁 |

> BOK_ECOS_API_KEY, DART_API_KEY만 필수. 나머지 없어도 200+ 도구 사용 가능.

---

## 10. 현황 & 완성도 진단

### 10-1. 구현 완료 기능

- 64/64 서버 로드 성공 (0 실패)
- 398개 도구 등록 및 호출 가능
- 3-Tier 캐시 시스템 (L1/L2/L3)
- Token Bucket 레이트 리미터 (11개 서비스)
- 표준 응답 포맷 (success_response / error_response)
- sanitize_records() 전역 적용
- Streamable HTTP + SSE + stdio 3중 전송
- Stateless HTTP 모드
- Health 엔드포인트
- API 호출 통계 (일별 파일 저장)
- systemd 자동 재시작
- Docker 이미지
- Smithery 마켓플레이스 등록
- 프롬프트 템플릿 3개
- 자동 테스트 프레임워크
- 문서 12개 파일

### 10-2. 부분 구현 기능

- 테스트 커버리지: framework 존재하지만 test_adapters/ 비어있음
- tool_metadata.py: 자동 생성 스크립트 존재하지만 최신 여부 불확실
- 인증: Bearer token만, 사용자별 인증 없음

### 10-3. 미구현 / TODO

- 개별 어댑터 단위 테스트
- CI/CD 파이프라인 (GitHub Actions)
- 사용자별 쿼터 관리
- WebSocket 전송
- 수평 스케일링
- 데이터 품질 자동 모니터링

### 10-4. 알려진 기술 부채

- phase2/3_adapters.py: 단일 파일에 여러 어댑터 합침
- 메모리 345MB (64개 서버 전체 로드)
- DiskCache: 단일 프로세스에서만 안전

### 10-5. 코드 품질 총평

| 항목 | 평가 |
|------|------|
| 아키텍처 일관성 | 높음 — BaseMCPServer 패턴 전체 일관 적용 |
| 응답 표준화 | 높음 — success/error_response 전역 사용 |
| 에러 처리 | 높음 — tool_handler 데코레이터 |
| 보안 | 중간 — 입력 검증 있으나 인증 기본 수준 |
| 테스트 커버리지 | 낮음 — 프레임워크만 존재 |
| 문서화 | 높음 — README 22K자, 12개 문서 |
| 총 코드량 | 33,000+ 줄 (어댑터 21K + 서버 10K + 코어 1.5K) |

---

## 11. 사용 방법

### 11-1. 사전 요구사항

- Python 3.12+
- pip (최신)
- Git

### 11-2. 설치 & 실행

```bash
# 클론
git clone https://github.com/pollmap/nexus-finance-mcp.git
cd nexus-finance-mcp

# 의존성 설치
pip install -r requirements.txt

# 환경 설정
cp .env.template .env
# .env에 API 키 입력

# 실행
python server.py --transport streamable-http --port 8100

# Docker
docker build -t nexus-finance-mcp .
docker run -p 8100:8100 --env-file .env nexus-finance-mcp
```

### 11-3. 기본 사용 예시

```bash
# Claude Code 연결 (호스팅 서버, 설치 불필요)
claude mcp add nexus-finance --transport http http://62.171.141.206/mcp

# Health 확인
curl http://62.171.141.206/health
```

### 11-4. 고급 사용 예시

```python
# Python SDK
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async with streamablehttp_client("http://62.171.141.206/mcp") as (r, w, _):
    async with ClientSession(r, w) as session:
        await session.initialize()
        result = await session.call_tool("dart_financial_statements",
                                          {"stock_code": "005930"})
        print(result)
```

### 11-5. FAQ

| 에러 | 해결 |
|------|------|
| API_UNAVAILABLE | 외부 API 다운 → 재시도 |
| INVALID_INPUT | 종목코드 형식 확인 (6자리) |
| NOT_INITIALIZED | .env에 API 키 추가 후 재시작 |
| port 8100 in use | `lsof -i :8100` → kill |

---

## 12. 소개 방법

### 12-1. 비개발자용 (5분 스피치)

"AI 비서가 금융 데이터를 알아서 찾아주는 시스템입니다. '삼성전자 재무제표 보여줘'라고 하면, AI가 금융감독원에서 직접 데이터를 가져옵니다. 60개 기관의 데이터를 하나의 창구에서 처리합니다."

핵심 임팩트:
1. 60개 API → 1개 엔드포인트 통합
2. 연동 시간 2-3주 → 1분
3. PhD급 분석 엔진 내장

### 12-2. 개발자용

FastMCP 3.x 위에 구축한 금융 MCP 서버. 64개 서브서버를 mount() flat merge. BaseMCPServer ABC가 3-tier 캐시 + Token Bucket + 에러 핸들링 공통 제공. Python 생태계 최대 활용 (OpenDartReader, pykrx, ccxt, arch, scipy).

### 12-3. 1-pager 요약

```
Nexus Finance MCP Server
━━━━━━━━━━━━━━━━━━━━━━━

규모:  398 도구 / 64 서버 / 60+ API / 33,000+ 줄
스택:  Python 3.12 · FastMCP · pandas · ccxt · arch · plotly
기간:  2025.10 ~ 2026.04 (14 Phases)

핵심:  60개 금융 API를 MCP 단일 엔드포인트로 통합
특화:  한국 금융 (ECOS, DART, KOSIS, KRX, RONE)
퀀트:  DCF, GARCH, HRP, Lopez de Prado ML
무료:  API 키 없이 200+ 도구 즉시 사용
```

---

## 13. 확장 & 기여 가이드

### 새 도구 추가 순서

1. `mcp_servers/adapters/xxx_adapter.py` — API 래핑
2. `mcp_servers/servers/xxx_server.py` — BaseMCPServer 상속
3. `gateway_server.py` SERVERS 리스트에 추가
4. `.env.template` (필요 시)
5. `requirements.txt` (필요 시)

### 코딩 컨벤션

- 어댑터: `xxx_adapter.py` → `XxxAdapter`
- 서버: `xxx_server.py` → `XxxServer(BaseMCPServer)`
- 도구명: `prefix_action_target()` (예: `dart_financial_statements`)
- 응답: 항상 `success_response()` / `error_response()`
- 캐시: `_cached_request()` + data_type 지정
- DataFrame 반환: `sanitize_records(df)` 필수

---

## 14. 로드맵 제안

### 단기 (1-2주)
- 핵심 어댑터 단위 테스트 작성 (dart, ecos, ccxt)
- phase2/3_adapters 개별 파일 분리
- tool_metadata 최신화

### 중기 (1-3개월)
- CI/CD (GitHub Actions)
- Prometheus + Grafana 모니터링
- 사용자별 API 키 전달 메커니즘
- WebSocket 실시간 스트리밍

### 장기 (6개월+)
- Redis 캐시 + 로드밸런서 (수평 스케일링)
- GraphQL 레이어
- 실시간 알림 (가격/공시/이상탐지)
- 프리미엄 티어 (SLA 보장)
- AI 에이전트 마켓플레이스
