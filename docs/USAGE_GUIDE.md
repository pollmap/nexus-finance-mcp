# Nexus Finance MCP — 사용 가이드 (USAGE GUIDE)

> 대상: Nexus Finance MCP를 처음 사용하거나 체계적인 활용 패턴을 익히고 싶은 개발자/분석가
> 기준: 398 tools / 48 adapters / 64 servers (v8.0.0-phase14)

---

## 1. Quick Start (빠른 시작)

### 연결 방법

**Claude Desktop (권장)**

`claude_desktop_config.json`에 아래 블록 추가:

```json
{
  "mcpServers": {
    "nexus-finance": {
      "command": "python",
      "args": ["/opt/nexus-finance-mcp/server.py"],
      "env": {}
    }
  }
}
```

**직접 헬스체크 (curl)**

```bash
curl http://127.0.0.1:8100/health
```

정상 응답: `{"status": "ok", "tools": 398}`

### 첫 3번의 호출 (필수 워밍업)

```
1. gateway_status()          # 서버 상태, 도구 수, 버전 확인
2. list_available_tools()    # 전체 398개 도구 이름 목록
3. api_call_stats()          # 호출량 통계 및 도메인별 분포
```

이 3개 호출로 서버 상태와 사용 가능한 도메인을 파악한 뒤 본격 작업을 시작한다.

---

## 2. Tool Discovery (도구 탐색)

### 핵심 탐색 도구

| 도구 | 설명 | 반환값 예시 |
|------|------|------------|
| `gateway_status()` | 서버/도구 수, 버전, 가동 시간 | `{"tools": 398, "version": "8.0.0"}` |
| `list_available_tools()` | 전체 도구 이름 목록 (398개) | `["ecos_get_base_rate", "dart_company_info", ...]` |
| `api_call_stats()` | 도메인별 호출량, 에러율, 응답시간 | `{"ecos": 1204, "dart": 893, ...}` |

### 도구 네이밍 규칙 (Tool Naming Convention)

접두사(prefix)가 도메인을 나타낸다. 접두사만 봐도 어떤 API를 호출하는지 알 수 있다.

| 접두사 | 도메인 | 주요 데이터 |
|--------|--------|------------|
| `ecos_` | BOK ECOS (한국은행) | 기준금리, 환율, 거시지표 |
| `dart_` | OpenDART | 공시, 재무제표, 기업개황 |
| `kosis_` | KOSIS (통계청) | 인구, 경제, 산업 통계 |
| `crypto_` | CCXT (거래소) | 암호화폐 시세, OHLCV |
| `defi_` | DeFi / CoinGecko | Fear & Greed, TVL |
| `quant_` | 자체 Quant Engine | 상관분석, 인과검정, 팩터 |
| `factor_` | Factor Model | 모멘텀, 밸류, 퀄리티 스코어 |
| `backtest_` | Backtest Engine | 전략 시뮬레이션, VaR |
| `val_` | Valuation | DCF, PER/PBR 밸류에이션 |
| `viz_` | Visualization | 차트, 히트맵, 산점도 |
| `stocks_` | KRX / Yahoo Finance | 주가, 검색, 히스토리 |
| `news_` | 네이버 뉴스 / 글로벌 뉴스 | 키워드 기사 검색 |
| `academic_` | arXiv / Semantic Scholar | 논문 검색 |
| `space_` | NASA / 기상 데이터 | 흑점수, 위성 데이터 |
| `macro_` | FRED / BIS | 미국·글로벌 거시지표 |
| `ts_` | Time Series Analysis | 분해, 이상탐지, 예측 |

---

## 3. 5가지 입력 패턴 (Input Patterns)

398개 도구를 리버스 엔지니어링해 도출한 입력 패턴 분류.  
도구 docstring을 보기 전에 이 패턴부터 매핑하면 파라미터 파악 시간이 크게 줄어든다.

---

### Pattern 1: Zero-param Snapshots (52 tools, 14%)

파라미터 없이 호출. 현재 상태/스냅샷을 즉시 반환한다.

```python
ecos_get_macro_snapshot()     # 한국 거시경제 전체 현황 스냅샷
disaster_active_events()      # 실시간 재해/이벤트 현황
gateway_status()              # MCP 서버 상태
crypto_fear_greed()           # 암호화폐 Fear & Greed Index
```

**적합한 use case:** 대시보드 위젯, 모니터링, 헬스체크, 브리핑 자동화

---

### Pattern 2: stock_code (34 tools, 9%)

종목코드 단일 파라미터. 한국 종목은 6자리 숫자, 미국 종목은 티커 문자열.

```python
dart_company_info(stock_code="005930")       # 삼성전자 기업개황
dart_financial_ratios(stock_code="005930")   # 재무비율 (ROE, PER, PBR 등)
stocks_quote(stock_code="005930")            # 현재 주가
stocks_history(stock_code="AAPL")           # 애플 주가 히스토리
```

**적합한 use case:** 종목별 기업 분석, 개별 주식 리서치

---

### Pattern 3: series / series_list (28 tools, 8%)

시계열 데이터를 직접 입력으로 받아 분석을 수행한다.  
앞선 API 호출로 수집한 `data` 배열을 그대로 넘기는 파이프라인 패턴.

```python
quant_lagged_correlation(
    series1=[3.5, 3.25, 3.0, ...],     # 금리 시계열
    series2=[1200, 1180, 1250, ...],   # 환율 시계열
    max_lag=12
)

ts_decompose(
    series=[...],          # 임의 시계열
    period=12              # 계절성 주기 (월간=12)
)
```

**적합한 use case:** 퀀트 분석, 팩터 모델, 예측 모델 입력 전처리

---

### Pattern 4: query / keyword 검색 (24 tools, 7%)

텍스트 검색어를 받아 매칭 결과를 반환한다.

```python
ecos_search_stat_list(keyword="금리")          # ECOS 통계 목록 검색
stocks_search(keyword="삼성")                   # 종목명 검색
academic_search(query="machine learning alpha") # 논문 검색
news_search(keyword="반도체 수출")              # 뉴스 기사 검색
```

**적합한 use case:** 종목코드 모를 때, 데이터 탐색, 리서치 초기 단계

---

### Pattern 5: data + columns 시각화 (33 tools, 9%)

데이터 배열과 컬럼명을 받아 차트를 생성한다.  
반환값은 파일 경로(PNG/HTML)이며 Obsidian Vault에 저장 가능.

```python
viz_line_chart(
    data=[{"date": "2024-01", "rate": 3.5}, ...],
    x_column="date",
    y_columns=["rate"],
    title="기준금리 추이"
)

viz_heatmap(
    data=[...],
    columns=["종목A", "종목B", "종목C"],
    title="상관관계 히트맵"
)
```

**적합한 use case:** 시각화, 보고서 자동화, 슬라이드 첨부 이미지

---

### 나머지 193 tools (53%)

도메인 특화 파라미터 조합. 각 도구의 docstring에서 파라미터 스펙 확인 필요.  
`list_available_tools()`로 이름을 확인 후 Claude에게 직접 `<tool_name>`의 파라미터를 물어볼 수 있다.

---

## 4. 5가지 도메인 워크플로우 (End-to-End)

실제 분석 시나리오별 도구 호출 순서. 각 단계 출력이 다음 단계 입력으로 연결되는 파이프라인 구조다.

---

### Workflow 1: 한국 거시경제 스냅샷 (Korean Macro Snapshot)

```
1. ecos_get_macro_snapshot()
   → 금리/환율/물가/성장률 현황 한눈에 파악

2. ecos_get_base_rate()
   → 기준금리 시계열 데이터 수집

3. ecos_get_exchange_rate()
   → USD/KRW 환율 시계열 수집

4. viz_line_chart(data=base_rate_data, x_column="date", y_columns=["rate"])
   → 금리 추이 차트 생성

5. viz_line_chart(data=exchange_rate_data, x_column="date", y_columns=["rate"])
   → 환율 추이 차트 생성
```

---

### Workflow 2: 기업 펀더멘털 분석 (Company Fundamental Analysis)

```
1. dart_search_company(keyword="삼성전자")
   → stock_code="005930" 확인

2. dart_company_info(stock_code="005930")
   → 기업개황 (업종, 자본금, 주요 사업)

3. dart_financial_ratios(stock_code="005930")
   → ROE, PER, PBR, EPS 등 재무비율

4. dart_cash_flow(stock_code="005930")
   → 현금흐름표 (영업/투자/재무 CF)

5. val_dcf_valuation(
       free_cash_flow=[...],    # dart_cash_flow 결과 활용
       growth_rate=0.05,
       discount_rate=0.10
   )
   → DCF 내재가치 산출
```

---

### Workflow 3: 퀀트 팩터 파이프라인 (Quant Factor Pipeline)

```
1. stocks_history(stock_code="005930")
   → 일별 OHLCV 수집

2. ecos_get_base_rate()
   → 무위험 수익률 (Rf) 확보

3. quant_lagged_correlation(
       series1=stock_returns,
       series2=rate_series,
       max_lag=12
   )
   → 금리와 주가 수익률 상관관계

4. factor_momentum_score(stock_code="005930")
   → 모멘텀 팩터 스코어 (1~100)

5. backtest_run(
       strategy="Momentum",
       universe=["005930", "000660", "035420"],
       start="2020-01-01"
   )
   → 전략 시뮬레이션

6. backtest_risk(results=backtest_output)
   → VaR / CVaR / MDD / Sharpe Ratio
```

---

### Workflow 4: 크립토 Cross-Market 분석

```
1. crypto_ticker(symbol="BTC/KRW")
   → 업비트/빗썸 BTC 원화 가격

2. crypto_ticker(symbol="BTC/USDT")
   → 바이낸스 BTC 달러 가격

3. crypto_kimchi_premium()
   → 김치 프리미엄 (%) 실시간

4. crypto_ohlcv(symbol="BTC/USDT", timeframe="1d", limit=365)
   → 1년치 일봉 데이터

5. defi_fear_greed()
   → Fear & Greed Index + 시계열
```

---

### Workflow 5: 대안 데이터 상관분석 (Alternative Data Correlation)

태양 흑점 주기와 금리·증시 관계를 검증하는 학술 수준 분석.

```
1. space_sunspot_data()
   → 1818년 이후 월별 흑점수 데이터

2. ecos_get_base_rate()
   → 한국 기준금리 시계열

3. quant_lagged_correlation(
       series1=sunspot_series,
       series2=rate_series,
       max_lag=24        # 최대 24개월 래그
   )
   → 시차별 피어슨 상관계수

4. quant_granger_causality(
       cause=sunspot_series,
       effect=rate_series,
       max_lag=12
   )
   → 그랜저 인과관계 검정 (p-value)

5. viz_scatter(
       data=merged_data,
       x_column="sunspot",
       y_column="rate",
       title="흑점수 vs 기준금리"
   )
   → 산점도 시각화
```

---

## 5. 운영 팁 (Operational Tips)

- **도구 이름 오타 주의**: `list_available_tools()`로 정확한 이름 확인 후 호출
- **파이프라인 저장**: 워크플로우 결과를 Obsidian Vault (`/root/obsidian-vault/03-Resources/`)에 저장하면 재사용 가능
- **대량 데이터**: `stocks_history()`, `space_sunspot_data()` 등은 수백~수천 건 반환. `viz_` 도구에 바로 넘길 수 있음
- **API Key 미설정**: 일부 도구는 `.env` 파일에 키가 없으면 즉시 에러. `ERROR_REFERENCE.md` 참조

---

*최종 업데이트: 2026-04-08 | Nexus Finance MCP v8.0.0-phase14 기준*

---

## Natural Language Prompt Examples

아래 프롬프트를 Claude에 그대로 입력하면 MCP 도구가 자동으로 연결되어 End-to-End 분석이 실행된다.

### Equity Analysis
> "Analyze Samsung Electronics (005930) — get current price, 3-year financials, DCF valuation, and compare against semiconductor peers."

### Macro Research
> "Compare US and Korean base interest rates over 5 years. Run Granger causality and forecast Korean rates for 12 months."

### Academic Survey
> "Search arXiv and Semantic Scholar for 'transformer financial forecasting' papers from 2024-2025. Rank by citations."

### Crypto Quant
> "Analyze BTC market structure: funding rates, basis term structure, MVRV, and open interest. Any funding rate arb opportunity?"

### Alternative Data
> "Get sunspot data from 1950 and compare with KOSPI returns using lagged correlation. Check ENSO and geopolitical risk."

### Portfolio Construction
> "Score top 50 KOSPI stocks on momentum/value/quality factors. Optimize with HRP and backtest against KOSPI for 3 years."
