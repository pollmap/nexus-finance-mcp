# Competitive Analysis — Finance & Research Intelligence Platform

> v8.0.0-phase14 / 2026-04-08 기준 경쟁 환경 분석

## Nexus Finance MCP 포지셔닝

**396 tools / 64 servers / 48 adapters** — Finance & Research Intelligence Platform 중 도구 수 1위.

---

## 주요 경쟁사

### Tier 1: 직접 경쟁

| 경쟁사 | 도구 수 | 데이터 소스 | 핵심 강점 | 약점 |
|--------|---------|-------------|-----------|------|
| **FMP MCP** | 250+ | Financial Modeling Prep API | 펀더멘탈 깊이, 7만+ 데이터포인트, 24+ 카테고리 | 단일 소스 의존 |
| **EODHD MCP** | 77 | EODHD API (30+ 글로벌 거래소) | 문서 100+페이지, OAuth, 프롬프트 템플릿 3개 | 단일 소스, 도구 수 적음 |
| **Alpaca MCP** | ~50 | Alpaca (주식/ETF/크립토/옵션) | **실시간 트레이딩 실행** (유일), 자연어 매매 | 데이터 분석 기능 부족 |
| **QuantConnect MCP** | 60+ | QuantConnect (10년+ 히스토리) | 업계 최고 백테스트, 리서치→실전 배포 파이프라인 | 데이터 폭 좁음 |

### Tier 2: 부분 경쟁

| 경쟁사 | 도구 수 | 특화 영역 |
|--------|---------|-----------|
| Yahoo Finance MCP (다수 구현) | ~20 | 무료 주가 데이터 |
| Financial Datasets MCP | ~15 | 재무제표 |
| CoinGecko MCP | ~30 | 크립토 (15,000+ 코인) |
| Alpha Vantage MCP | ~25 | 기술적 분석, 외환 |
| Crypto Trading MCP | ~20 | 멀티 거래소 크립토 매매 |

---

## 비교 분석

### 도구 수 비교
```
Nexus Finance  ████████████████████████████████████████ 396
FMP MCP        █████████████████████████               250
EODHD MCP      ████████                             77
QuantConnect   ██████                               60
Alpaca MCP     █████                                50
CoinGecko MCP  ███                                  30
Alpha Vantage  ███                                  25
```

### 차원별 비교

| 차원 | Nexus | 최고 경쟁사 | 격차 |
|------|-------|-------------|------|
| **도구 수** | 396 | FMP 250 | **+58% (1위)** |
| **데이터 소스 수** | 64 | EODHD 1, FMP 1 | **독보적** |
| **한국 시장** | ECOS+DART+KOSIS+KRX+네이버 | 없음 | **독점** |
| **퀀트 분석** | 88 tools (Tier 3-4) | QuantConnect 60 | **+47%** |
| **대안 데이터** | 32 tools (우주/재해/기후) | 없음 | **독점** |
| **문서 품질** | 7개 docs (신규) | EODHD 100+페이지 | 격차 있음 |
| **실시간 매매** | 없음 | Alpaca (유일) | **부재** |
| **OAuth** | Bearer token | EODHD OAuth2 | 격차 있음 |
| **프롬프트 템플릿** | 없음 | EODHD 3개 | **부재** |

---

## SWOT 분석

### Strengths (강점)
- **도구 수 1위** (396 vs 2위 FMP 250)
- **64개 데이터 소스 통합** — 단일 게이트웨이로 접근
- **한국 시장 유일한 MCP** — ECOS, DART, KOSIS, KRX
- **대안 데이터 독점** — 우주기상, 재해, 기후, 분쟁 (API 키 불필요)
- **PhD급 퀀트** — Heston, Almgren-Chriss, VPIN 등 경쟁사에 없는 도구
- **150년 역사 데이터** — Shiller 1871, NBER 1854

### Weaknesses (약점)
- ~~문서 부족~~ → 7개 docs 작성으로 해소 중
- 실시간 매매 실행 기능 없음
- OAuth2 미지원 (Bearer token만)
- 프롬프트 템플릿 없음
- 응답 포맷 표준화 진행 중 (48개 어댑터 중 4개 완료)

### Opportunities (기회)
- EODHD의 프롬프트 템플릿 패턴 도입 가능
- Alpaca 연동으로 실시간 매매 추가 가능
- 한국 시장 MCP로 국내 독점 포지션
- Smithery 등록으로 글로벌 노출 확대

### Threats (위협)
- FMP이 도구 수 추가 확장 시 격차 축소
- QuantConnect가 MCP 고도화하면 백테스트 영역 위협
- 대형 플랫폼(Bloomberg, Refinitiv)이 MCP 직접 제공 시

---

## 경쟁사에서 배울 점

### 1. EODHD — 문서 품질 벤치마크
- 100+ 페이지 내장 문서 (MCP 리소스로 임베드)
- 프롬프트 템플릿 3개 (분석 시나리오별)
- OAuth2 지원
- **적용**: 우리 docs/ 7개 → MCP 리소스로 임베드 고려

### 2. Alpaca — 실행 기능
- 자연어로 매매 주문
- 포트폴리오 관리
- **적용**: KIS API 연동으로 한국 시장 실시간 매매 추가 가능

### 3. FMP — 동적 도구 탐색
- 24+ 카테고리로 자동 분류
- 도구 메타데이터 내장
- **적용**: tool_metadata.py + Gateway 3도구로 이미 구현 시작

### 4. QuantConnect — 엔드투엔드 파이프라인
- 리서치 → 백테스트 → 최적화 → 라이브 배포
- **적용**: backtest_run → signal_scan → portfolio_markowitz 파이프라인 문서화

---

## 전략적 포지셔닝

> **"글로벌 금융 데이터 통합 허브"** — 64개 소스를 하나의 MCP로

경쟁사가 단일 API(FMP, EODHD)에 의존하는 반면,
Nexus는 BOK ECOS + DART + FRED + SEC + CCXT + GDELT + NASA 등
**64개 독립 소스를 단일 게이트웨이로 통합**한 유일한 플랫폼.

### 핵심 차별화 3가지
1. **한국 + 글로벌 동시 커버** — 경쟁사 0
2. **대안 데이터 (우주/재해/기후)** — 경쟁사 0
3. **PhD급 퀀트 (88 tools)** — QuantConnect 유일한 부분 경쟁

---

*이 문서는 주기적으로 업데이트해야 함. MCP 생태계는 빠르게 변화 중.*
