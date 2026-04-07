# Tool Catalog

> 364 tools / 64 servers — 복잡도, 도메인, 입력 패턴별 분류

## Complexity Tiers

### Tier 1: Simple (86 tools) — 파라미터 0~1개, 직접 조회

즉시 결과 반환. 데이터 변환 불필요.

| 유형 | 도구 수 | 대표 예시 |
|------|---------|-----------|
| Zero-param Snapshots | 52 | `ecos_get_macro_snapshot()`, `gateway_status()`, `crypto_fear_greed()` |
| stock_code 단건 조회 | 34 | `dart_company_info("005930")`, `stocks_quote("005930")` |

### Tier 2: Parameterized (~120 tools) — 파라미터 2~4개, 날짜/필터

날짜 범위, 키워드, 필터 조건 지정 필요.

| 유형 | 도구 수 | 대표 예시 |
|------|---------|-----------|
| keyword 검색 | 24 | `ecos_search_stat_list("금리")`, `academic_search("GARCH")` |
| 날짜 범위 조회 | ~50 | `ecos_get_base_rate(start_date, end_date)`, `stocks_history(...)` |
| 필터 조합 | ~46 | `crypto_ohlcv(symbol, timeframe)`, `energy_oil_price(period)` |

### Tier 3: Analytical (~80 tools) — 복잡 입력, 계산된 출력

사전 수집된 데이터를 입력으로 받아 분석 수행.

| 유형 | 도구 수 | 대표 예시 |
|------|---------|-----------|
| 상관/인과 분석 | 8 | `quant_lagged_correlation(series1, series2)` |
| 시계열 분석 | 6 | `ts_forecast(series, horizon)`, `ts_decompose(series)` |
| 백테스트 | 8 | `backtest_run(stock, strategy, years)` |
| 팩터 분석 | 6 | `factor_momentum_score(returns)` |
| 포트폴리오 최적화 | 6 | `portfolio_markowitz(returns, cov_matrix)` |
| 밸류에이션 | 10 | `val_dcf_valuation(...)`, `val_peer_comparison(...)` |
| 시각화 | 33 | `viz_line_chart(data, x_column, y_columns)` |

### Tier 4: Pipeline (~78 tools) — 다단계, 체인 입력

한 도구의 출력이 다른 도구의 입력이 되는 파이프라인.

| 유형 | 도구 수 | 대표 예시 |
|------|---------|-----------|
| 시그널 랩 | 6 | `signal_scan(...)`, `signal_combine(...)`, `signal_walkforward(...)` |
| 포트폴리오 고급 | 6 | `portadv_black_litterman(...)`, `portadv_hrp(...)` |
| 변동성 모델 | 6 | `vol_garch(...)`, `vol_heston(...)`, `vol_hmm_regime(...)` |
| 고급 수학 | 6 | `math_kalman_filter(...)`, `math_wavelet(...)` |
| 통계적 차익 | 6 | `stat_arb_ou_fit(...)`, `stat_arb_copula(...)` |
| 확률적 변동성 | 6 | `stochvol_heston(...)`, `stochvol_almgren_chriss(...)` |
| 마이크로구조 | 6 | `micro_kyle_lambda(...)`, `micro_vpin(...)` |
| 크립토 퀀트 | 6 | `cquant_funding_rate(...)`, `cquant_basis_term(...)` |
| 온체인 고급 | 6 | `onchain_mvrv(...)`, `onchain_hodl_waves(...)` |
| ML 파이프라인 | 6 | `ml_volume_bars(...)`, `ml_triple_barrier(...)`, `ml_purged_cv(...)` |
| 알파 리서치 | 6 | `alpha_turnover(...)`, `alpha_crowding(...)`, `alpha_combine(...)` |
| 150년 역사 | 6 | `hist_shiller_data()`, `hist_french_factors()`, `hist_nber_cycles()` |

---

## 도메인별 카탈로그

### 1. Korean Economy (한국 경제) — 27 tools

**ECOS** (8 tools) — 한국은행 경제통계
| Tool | Input Pattern | Tier | 설명 |
|------|---------------|------|------|
| `ecos_get_base_rate` | snapshot/date | 1-2 | 기준금리 |
| `ecos_get_m2` | snapshot/date | 1-2 | M2 통화량 |
| `ecos_get_gdp` | snapshot/date | 1-2 | GDP |
| `ecos_get_exchange_rate` | snapshot/date | 1-2 | 원/달러 환율 |
| `ecos_get_cpi` | snapshot/date | 1-2 | 소비자물가지수 |
| `ecos_get_ppi` | snapshot/date | 1-2 | 생산자물가지수 |
| `ecos_get_current_account` | snapshot/date | 1-2 | 경상수지 |
| `ecos_search_stat_list` | search | 2 | 통계표 검색 |

**DART** (7 tools) — 금감원 OpenDART
| Tool | Input Pattern | Tier | 설명 |
|------|---------------|------|------|
| `dart_company_info` | stock_code | 1 | 기업개황 |
| `dart_financial_statements` | stock_code | 1 | 재무제표 |
| `dart_financial_ratios` | stock_code | 1 | 재무비율 |
| `dart_major_shareholders` | stock_code | 1 | 대주주 |
| `dart_cash_flow` | stock_code | 1 | 현금흐름표 |
| `dart_dividend` | stock_code | 1 | 배당 정보 |
| `dart_search_company` | search | 2 | 기업 검색 |

**KOSIS** (5 tools), **FSC** (2 tools), **Stocks** (5 tools) — README.md 참조

### 2. Crypto & DeFi — 25 tools

| Tool Prefix | Count | Input Pattern | 설명 |
|-------------|-------|---------------|------|
| `crypto_` | 8 | symbol/params | 시세, 오더북, 김프, 거래소비교, OHLCV |
| `cquant_` | 6 | composite | 펀딩레이트, 베이시스, 캐리 백테스트 |
| `defi_` | 4 | snapshot/params | 프로토콜 TVL, Fear & Greed |
| `onchain_` | 3 | params | ETH 잔액, 가스, 트랜잭션 |
| `onchain_advanced_` | 4 | composite | MVRV, HODL waves, NVT |

### 3. Quant Analysis — 88 tools

| Sub-domain | Prefix | Count | Tier | 핵심 메서드 |
|------------|--------|-------|------|------------|
| 상관/인과 분석 | `quant_` | 8 | 3 | 상관, 시차상관, 회귀, Granger, 공적분, VAR |
| 시계열 분석 | `ts_` | 6 | 3 | 분해, ADF/KPSS, ARIMA, 계절성, 구조변화 |
| 백테스트 | `backtest_` | 8 | 3 | 6전략, 비교, 최적화, VaR/CVaR |
| 팩터 엔진 | `factor_` | 6 | 3-4 | 모멘텀, 가치, 퀄리티, 저변동성 |
| 시그널 랩 | `signal_` | 6 | 4 | 스캔, 결합, 워크포워드, IC |
| 포트폴리오 | `portfolio_` | 6 | 3-4 | Markowitz, 리스크패리티, 켈리 |
| 포트폴리오 고급 | `portadv_` | 6 | 4 | BL, HRP, RMT clean, Johansen |
| 변동성 모델 | `vol_` | 6 | 4 | GARCH, EGARCH, HMM, VIX |
| 고급 수학 | `math_` | 6 | 4 | 칼만, Hurst, 엔트로피, 웨이블릿, 프랙탈 |
| 통계적 차익 | `stat_arb_` | 6 | 4 | OU, pairs, copula, spread z-score |
| 확률적 변동성 | `stochvol_` | 6 | 4 | Heston, jump-diffusion, Almgren-Chriss |
| 마이크로구조 | `micro_` | 6 | 4 | Kyle's λ, VPIN, Roll spread, Amihud |
| ML 파이프라인 | `ml_` | 6 | 4 | López de Prado: volume bars, triple barrier |
| 알파 리서치 | `alpha_` | 6 | 4 | 턴오버, 디케이, 크라우딩, 용량 |

### 4. Alternative Data — 32 tools

| Sub-domain | Prefix | Count | API 키 | 설명 |
|------------|--------|-------|--------|------|
| 우주 기상 | `space_` | 5 | 불필요 | 흑점(1818~), 태양 플레어, Kp지수 |
| 재해 | `disaster_` | 6 | 불필요 | 지진, 화산, 산불, 홍수 |
| 기후 | `climate_` | 6 | 불필요 | 과거날씨(1940~), ENSO, 온도이상 |
| 센티멘트 | `sentiment_` | 5 | 불필요 | Google Trends, 위키, VADER |
| 분쟁 | `conflict_` | 5 | 토큰 | 분쟁, 국가리스크, 평화지수 |
| 전력 | `power_` | 5 | 선택 | EU 발전, 전력가격, 원전 |

### 5. News & Research — 29 tools

| Sub-domain | Prefix | Count | 설명 |
|------------|--------|-------|------|
| 뉴스 | `news_` | 4 | 네이버 뉴스 검색, 감성분석 |
| 글로벌 뉴스 | `global_news_` | 3 | GDELT |
| 학술 | `academic_` | 9 | arXiv, Semantic Scholar, OpenAlex |
| 연구기관 | `research_` | 6 | NANET, NKIS, RISS |
| RSS | `rss_` | 4 | Bloomberg, WSJ, CNBC, Reuters |
| 예측시장 | `prediction_` | 3 | Polymarket |

### 6. Real Economy — 31 tools

| Sub-domain | Prefix | Count | 설명 |
|------------|--------|-------|------|
| 에너지 | `energy_` | 9 | 원유, 가스, OPEC, EIA |
| 농업 | `agri_` | 7 | 42품목, FAO, USDA |
| 해운 | `maritime_` | 4 | BDI, 컨테이너지수 |
| 항공 | `aviation_` | 3 | OpenSky |
| 무역 | `trade_` | 3 | UN Comtrade |
| 정치 | `politics_` | 3 | 국회 법안 |
| 특허 | `patent_` | 2 | KIPRIS |

### 7. Infrastructure — 22 tools

| Sub-domain | Prefix | Count | 설명 |
|------------|--------|-------|------|
| Vault | `vault_` | 6 | Obsidian 노트 CRUD |
| Memory | `memory_` | 5 | 벡터+BM25 검색 |
| Vault Index | `vault_index_` | 3 | 시맨틱 인덱싱 |
| Ontology | `ontology_` | 5 | 도메인 관계 지도, 인과 체인 |
| Gateway | `gateway_` | 3 | 상태, 도구 목록, 통계 |

---

## Input Pattern Quick Reference

| Pattern | 도구 수 | 비율 | 식별 방법 | Prefix 예시 |
|---------|---------|------|-----------|-------------|
| snapshot (0 params) | 52 | 14% | 파라미터 없음 | `*_snapshot`, `*_status`, `*_active_*` |
| stock_code | 34 | 9% | `stock_code` 필수 | `dart_*`, `stocks_*`, `val_*` |
| series | 28 | 8% | `series`/`series_list` 필수 | `quant_*`, `ts_*`, `portadv_*`, `factor_*` |
| search | 24 | 7% | `keyword`/`query` 필수 | `*_search*`, `academic_*` |
| data+columns | 33 | 9% | `data` + `columns` 필수 | `viz_*` |
| composite | 193 | 53% | 도메인별 고유 조합 | 다양 |

---

## Geographic Coverage

| Region | Tools | 주요 소스 |
|--------|-------|-----------|
| 한국 | ~59 | BOK ECOS, DART, KOSIS, KRX, 네이버 |
| 미국 | ~25 | FRED, SEC, Finnhub, EIA |
| 아시아 | ~22 | Yahoo (HK, TW, CN, IN), EDINET (JP) |
| 유럽 | ~15 | EUR-Lex, ENTSO-E, Eurostat |
| 글로벌 | ~60+ | Crypto, OECD, IMF, BIS, NASA |

## Temporal Coverage

| Dataset | 시작년도 | 소스 |
|---------|----------|------|
| Shiller PE/Earnings | 1871 | Robert Shiller |
| 흑점수 | 1818 | SILSO |
| French Factors | 1926 | Kenneth French |
| NBER 경기순환 | 1854 | NBER |
| 과거 날씨 | 1940 | Open-Meteo |
| 한국 거시경제 | ~1990 | BOK ECOS |
