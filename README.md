# Nexus Finance MCP Server

> **316 tools for global financial research & quant analysis** — Built for AI agents by [Luxon AI](https://github.com/pollmap).

56 servers, 316 tools covering Korean/global macro, equities, crypto, real estate, energy, climate, disasters, space weather, geopolitics, sentiment, quant analysis, time series, backtesting, factor models, portfolio optimization, 150-year historical data, GARCH volatility, and PhD-level math (Kalman, Hurst, wavelets, fractals, Monte Carlo) — all through a single gateway.

## Quick Connect

### Claude Desktop / Claude Code (원격 접속)

```json
{
  "mcpServers": {
    "nexus-finance": {
      "url": "http://62.171.141.206/mcp",
      "transport": "streamable-http",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

- **Claude Desktop:** `%APPDATA%\Claude\claude_desktop_config.json` 에 추가 → 재시작
- **Claude Code:** `claude mcp add nexus-finance --transport streamable-http --url http://62.171.141.206/mcp`
- Bearer 토큰은 관리자에게 문의

### Self-hosted (직접 설치)

```bash
git clone https://github.com/pollmap/nexus-finance-mcp.git
cd nexus-finance-mcp
pip install -r requirements.txt
cp .env.template .env   # API 키 설정
python server.py --transport streamable-http --port 8100
```

## Tools (316)

### Korean Economy (한국 경제) — 25 tools

| Server | Tools | Data Source |
|--------|-------|------------|
| **ECOS** (8) | 기준금리, M2, GDP, 환율, CPI, PPI, 경상수지, 채권금리 | 한국은행 ECOS |
| **KOSIS** (5) | 인구, 실업률, 주택가격, 통계표 검색/조회 | 통계청 KOSIS |
| **DART** (7) | 기업정보, 재무제표, 재무비율, 대주주, 현금흐름, 배당, 검색 | 금융감독원 OpenDART |
| **FSC** (2) | 주가, 채권가격 | 금융위원회 data.go.kr |
| **Stocks** (5) | 실시간 시세, 검색, 히스토리, 베타, 시장개요 | KIS + pykrx + Yahoo |

### Korean Real Estate (부동산) — 8 tools

| Server | Tools | Data Source |
|--------|-------|------------|
| **R-ONE** (6) | 매매가격지수, 전세지수, 전월세전환율, 지역비교, 시장요약, 지역목록 | KOSIS (부동산원 orgId=408) |
| **Realestate** (2) | 아파트 실거래가, 시군구코드 | 국토부 MOLIT |

### Global Markets — 32 tools

| Server | Tools | Data Source |
|--------|-------|------------|
| **Global Macro** (6) | OECD, IMF, BIS, World Bank, 한국 스냅샷, 데이터셋 | 국제기구 API |
| **US Equity** (4) | 미국 주가, 기업 프로필, 시장 뉴스, 경제일정 | Finnhub |
| **Asia Market** (8) | 홍콩(HSI), 대만(TWSE), 중국 지수/시세/히스토리 | Yahoo Finance |
| **India** (3) | Nifty/Sensex, 인도 주가, 히스토리 | Yahoo Finance |
| **Crypto** (8) | 시세, 오더북, 김프, 거래소비교, OHLCV, 스프레드, 거래량 | CCXT (Upbit/Binance) |
| **DeFi** (4) | 프로토콜 TVL, 체인, Fear & Greed | DefiLlama |
| **OnChain** (3) | ETH 잔액, 가스, 트랜잭션 | Etherscan |

### Analysis & Visualization — 48 tools

| Server | Tools | Data Source |
|--------|-------|------------|
| **Valuation** (10) | DCF, WACC, 민감도분석, 피어비교, 크로스마켓, GAAP정규화 | DART + ECOS |
| **Technical** (5) | RSI, MACD, Bollinger, SMA/EMA, 종합요약 | pykrx |
| **Viz** (33) | 30종 차트 + 지도 3종 (코로플레스/산점도/플로우) | Plotly + Matplotlib |

### News & Research — 29 tools

| Server | Tools | Data Source |
|--------|-------|------------|
| **News** (4) | 뉴스 검색, 감성분석, 키워드 볼륨, 트렌드 | Naver API |
| **Global News** (3) | GDELT 글로벌 뉴스, 한국 뉴스, 타임라인 | GDELT |
| **Academic** (9) | arXiv, Semantic Scholar, OpenAlex, 인용분석, 트렌딩 | 학술 API |
| **Research** (6) | NANET, NKIS, 국립중앙도서관, PRISM, RISS, Scholar | 한국 연구기관 |
| **RSS** (4) | 14개 금융 뉴스 피드 (Bloomberg, WSJ, CNBC, Reuters, FT 등) | RSS |
| **Prediction** (3) | 예측시장, 이벤트, 마켓 디테일 | Polymarket |

### Real Economy — 30 tools

| Server | Tools | Data Source |
|--------|-------|------------|
| **Energy** (9) | 원유, 천연가스, OPEC, 전기, EIA, 벙커유, 스냅샷, 날씨 | EIA + Open-Meteo |
| **Agriculture** (7) | 농산물(42품목), FAO 생산/무역, USDA, 스냅샷 | KAMIS + FAO + USDA |
| **Maritime** (4) | BDI, 컨테이너지수, 항만통계, 운임 | FRED + 참조 |
| **Aviation** (3) | 출발편, 실시간 항공기, 한국 공항 | OpenSky |
| **Trade** (3) | 한국 수출입, 국가코드 | UN Comtrade v1 |
| **Politics** (3) | 국회 법안, 금융 법안, 최근 법안 | 국회 API |
| **Patent** (2) | 특허 검색, 트렌딩 | KIPRIS |

### Regulatory & Filings — 18 tools

| Server | Tools | Data Source |
|--------|-------|------------|
| **SEC** (3) | XBRL 재무데이터, 공시 검색, 공시 텍스트 | SEC EDGAR |
| **EDINET** (4) | 일본 기업/공시 검색, 문서상세, 기업정보 | 일본 EDINET |
| **Regulation** (4) | EU 규제, FINRA, 핵심 금융규제 | EUR-Lex + FINRA |
| **Consumer** (4) | 미국 주택/소매/소비심리, EU HICP | FRED + Eurostat |
| **Health** (5) | FDA 의약품/리콜, 임상시험, PubMed, WHO | openFDA + NCBI |
| **Environ** (2) | EPA 대기질, 탄소배출권 | EPA + KRBN ETF |

### Quant Alternative Data — 32 tools

| Server | Tools | Data Source | API 키 |
|--------|-------|------------|--------|
| **Space Weather** (5) | 흑점수(1818~), 태양 플레어, Kp지수, 태양풍, CME | SILSO + NASA + NOAA | 불필요 |
| **Disaster** (6) | 지진, 화산, 산불, 홍수, 활성재해, 재해통계 | USGS + NASA EONET + GDACS | 불필요 |
| **Climate** (6) | 과거날씨(1940~), 온도이상, 극한기상, ENSO, 도시비교, 곡물날씨 | Open-Meteo + NASA GISS | 불필요 |
| **Sentiment** (5) | Google Trends, 위키 조회수, VADER, Fear&Greed, 키워드상관 | pytrends + Wikipedia | 불필요 |
| **Conflict** (5) | 분쟁, 사상자, 국가리스크, 평화지수(163국), 지정학 이벤트 | UCDP + GPI | 토큰 필요 |
| **Power Grid** (5) | EU 발전믹스, 전력가격, 탄소집약도, 원전상태, 재생에너지 | ENTSO-E + EIA | 선택 |

### Quant Analysis Engine — 22 tools

| Server | Tools | Description |
|--------|-------|-------------|
| **Quant Analysis** (8) | 상관분석, **시차상관**, 회귀분석, 그레인저인과, 공적분, VAR분산분해, 이벤트스터디, 레짐탐지 | 임의의 두 데이터 시리즈 간 관계 분석 |
| **Time Series** (6) | 시계열분해, 정상성검정(ADF/KPSS), ARIMA예측, 계절성, 구조변화점, 교차상관 | 시계열 패턴 분석 및 예측 |
| **Backtest** (8) | 전략백테스트(6내장전략), 비교, 최적화, 포트폴리오, 벤치마크, VaR/CVaR, 시그널이력, 낙폭분석 | 수수료/세금 포함 실전 시뮬레이션 |

### Professional Quant (Phase 9) — 18 tools

| Server | Tools | Description |
|--------|-------|-------------|
| **Factor Engine** (6) | 모멘텀, 가치, 퀄리티, 저변동성, 사이즈, 역추세 팩터 | Fama-French 스타일 팩터 분석 |
| **Signal Lab** (6) | 시그널 스캔(walk-forward IC), 시그널 결합, 워크포워드, IC분석, 시그널 랭크, 시그널 디케이 | 알파 시그널 발굴 + 앙상블 |
| **Portfolio Optimizer** (6) | Markowitz 최적화, 리스크패리티, 켈리기준, 효율적 프론티어, 상관행렬, 리밸런싱 | 최적 포트폴리오 구성 |

### PhD-Level Quant Math (Phase 10) — 18 tools

| Server | Tools | Description |
|--------|-------|-------------|
| **Historical Data** (6) | Shiller(1871~), French Factors(1926~), NBER 경기순환(1854~), FRED 초장기, 금/원유, 세기횡단분석 | 150년 역사 데이터 |
| **Volatility Model** (6) | GARCH, EGARCH, 변동성 표면, HMM 레짐, 앙상블 예측, VIX 기간구조 | 박사급 변동성 모델링 |
| **Advanced Math** (6) | 칼만 필터, 허스트 지수, 정보 엔트로피, 웨이블릿 분해, 프랙탈 차원, 몬테카를로 시뮬레이션 | 르네상스 펀드 수준 수학 |

### Infrastructure — 22 tools

| Server | Tools | Data Source |
|--------|-------|------------|
| **Vault** (6) | Obsidian 노트 CRUD + 검색 + 태그 | Obsidian Vault |
| **Memory** (5) | 벡터+BM25 하이브리드 검색 기억 저장/검색 | SQLite + Ollama |
| **Vault Index** (3) | 시맨틱 인덱싱, 시맨틱 검색, 유사노트 | Ollama bge-m3 |
| **Ontology** (5) | 도메인 관계 지도, 인과체인, 영향분석, 도구추천, Vault 저장 | 17개 도메인 그래프 |
| **Gateway** (3) | 상태, 도구 목록, API 호출 통계 | 내부 |

## Example Workflows

### 퀀트 분석 파이프라인

```
1. 데이터 수집:  space_sunspot_data() + ecos_get_base_rate() + stocks_history("005930")
2. 상관 분석:    quant_lagged_correlation(흑점, 코스피, max_lag=24)
3. 인과 검정:    quant_granger_causality(금리, 아파트, max_lag=12)
4. 시계열 예측:  ts_forecast(아파트지수, horizon=12)
5. 전략 백테스트: backtest_run(삼성전자, "RSI_oversold", 5년)
6. 리스크 분석:  backtest_risk(삼성전자, "Momentum") → VaR/CVaR/Sharpe
7. 시각화:       viz_line_chart(equity_curve) + viz_heatmap(correlation_matrix)
```

### 내장 백테스트 전략 (수수료 0.18% + 세금 0.18%)

| Strategy | Logic | Best For |
|----------|-------|----------|
| `RSI_oversold` | RSI < 30 매수, > 70 매도 | 과매도 반등 |
| `MACD_crossover` | MACD-시그널 돌파 | 추세 전환 |
| `Bollinger_bounce` | 하단밴드 터치 | 변동성 회귀 |
| `MA_cross` | 20/50 골든크로스 | 중기 추세 |
| `Mean_reversion` | 평균 -2σ 매수 | 평균회귀 |
| `Momentum` | N일 수익률 양수 | 모멘텀 |

## API Keys

| Key | Required | Coverage |
|-----|----------|----------|
| `BOK_ECOS_API_KEY` | **Yes** | 한국은행 30+ 경제지표 |
| `DART_API_KEY` | **Yes** | 금감원 기업공시 |
| `KOSIS_API_KEY` | Recommended | 통계청 + 부동산원 |
| `FRED_API_KEY` | Recommended | 미국 연준 |
| `FINNHUB_API_KEY` | Optional | 미국 주식 |
| `ETHERSCAN_API_KEY` | Optional | 이더리움 온체인 |
| `EIA_API_KEY` | Optional | 미국 에너지 |
| `NAVER_CLIENT_ID/SECRET` | Optional | 네이버 뉴스 |
| `KIS_API_KEY` | Optional | 한국투자증권 실시간 |
| `NASA_API_KEY` | Optional | NASA (DEMO_KEY 가능) |

Phase 7 대체데이터 (우주/재해/기후/센티멘트) — 대부분 **API 키 불필요**.

## Data Policy

**Real data only.** No sample data, mock data, or fake data — ever.
API 호출 실패 시 가짜 데이터로 대체하지 않고 명확한 에러 메시지를 반환합니다.

## License

MIT

---

*v7.0.0-phase10 | 316 tools / 56 servers | [Luxon AI Agent Network](https://github.com/pollmap)*
