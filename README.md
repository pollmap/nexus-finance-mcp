# Nexus Finance MCP Server

> **131 tools for Korean & global financial research** — Built for AI agents by [Luxon AI](https://github.com/pollmap).

The most comprehensive Korean financial data MCP server. 27 servers, 15 adapters, 131 tools covering Korean macro, real estate, stocks, crypto, global markets, and enterprise valuation — all through a single gateway.

## Quick Connect

### Claude Desktop / Claude Code (원격 접속)

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

- **Claude Desktop:** `%APPDATA%\Claude\claude_desktop_config.json` 에 위 내용 추가 → 재시작
- **Claude Code:** `claude mcp add nexus-finance --transport streamable-http --url http://62.171.141.206/mcp`

### Self-hosted (직접 설치)

```bash
git clone https://github.com/pollmap/nexus-finance-mcp.git
cd nexus-finance-mcp
pip install -r requirements.txt
cp .env.template .env   # API 키 설정
python server.py --transport streamable-http --port 8100
```

## Tools (131)

### Korean Economy (한국 경제)

| Server | Tools | Description |
|--------|-------|-------------|
| **ECOS** (7) | 기준금리, M2, GDP, 환율, CPI, PPI, 경상수지 외 | 한국은행 경제통계 (30개 지표) |
| **KOSIS** (5) | 인구, 실업률, 주택가격, GDP, 가계소득 외 | 통계청 국가통계 (51개 테이블) |
| **DART** (5) | 기업정보, 재무제표, 재무비율, 대주주, 기업검색 | 금융감독원 공시 (52개 종목) |
| **FSC** (2) | 주가, 채권가격 | 금융위원회 data.go.kr |
| **Stocks** (5) | 실시간 시세, 검색, 히스토리, 베타, 시장개요 | KIS + pykrx + Yahoo |

### Korean Real Estate (부동산)

| Server | Tools | Description |
|--------|-------|-------------|
| **R-ONE** (6) | 매매가격지수, 전세지수, PIR, 지역비교, 시장요약 | 한국부동산원 (72개 지역) |
| **Realestate** (2) | 아파트 매매 실거래가, 시군구코드 목록 | 국토부 실거래가 (130+ 시군구) |

### Global Markets

| Server | Tools | Description |
|--------|-------|-------------|
| **FRED** (via Global Macro) | 40개 시리즈 (금리, GDP, CPI, 고용, 부동산, VIX) | 미국 연준 경제데이터 |
| **US Equity** (4) | 미국 주가, 기업 프로필, 시장 뉴스, 경제일정 | Finnhub |
| **Global Macro** (6) | OECD, IMF, BIS, World Bank (20개 지표), 한국 스냅샷 | 국제기구 데이터 |
| **Crypto** (8) | 시세, 오더북, 김프, 거래소 비교, OHLCV | CCXT (Upbit/Binance 등) |
| **Hist Crypto** (3) | 일봉/시간봉 OHLCV, 시총 상위 코인 | CryptoCompare (51개 코인) |
| **DeFi** (4) | 프로토콜, TVL, Fear & Greed | DeFi Llama + Alternative.me |

### Analysis & Valuation

| Server | Tools | Description |
|--------|-------|-------------|
| **Valuation** (10) | DCF, WACC, 민감도분석, 피어비교, 크로스마켓 | DART + ECOS 연동 |
| **Visualization** (10) | 라인, 바, 캔들, 히트맵, 산점도, 워터폴 등 | Plotly + Matplotlib |

### News & Research

| Server | Tools | Description |
|--------|-------|-------------|
| **News** (4) | 뉴스 검색, 감성분석 (98개 키워드), 키워드 볼륨, 트렌드 | Naver API |
| **Global News** (3) | GDELT 글로벌 뉴스, 한국 뉴스, 타임라인 | GDELT |
| **Academic** (9) | arXiv, Semantic Scholar, OpenAlex, 인용분석, 트렌딩 | 학술 데이터 |
| **Prediction** (3) | 예측시장, 이벤트, 마켓 디테일 | Polymarket |

### Real Economy (실물 경제)

| Server | Tools | Description |
|--------|-------|-------------|
| **Maritime** (4) | BDI, 컨테이너지수, 항만통계 (12개 항만), 운임 스냅샷 | FRED + 참조 |
| **Aviation** (3) | 출발편 조회, 실시간 항공기, 한국 공항 (14개) | OpenSky |
| **Energy** (5) | 원유, 천연가스, 에너지 스냅샷, 날씨 예보 (17개 도시) | EIA + Open-Meteo |
| **Agriculture** (4) | 농산물 가격 (42개 품목코드), FAO 지수, 스냅샷 | KAMIS + FAO |
| **Trade** (3) | 한국 수출입, 국가코드 (55개국) | UN Comtrade |
| **Politics** (3) | 국회 법안, 금융 관련 법안, 최근 법안 | 국회 API |
| **Patent** (2) | 특허 검색, 트렌딩 | KIPRIS |

### Infrastructure

| Server | Tools | Description |
|--------|-------|-------------|
| **Vault** (6) | Obsidian 노트 읽기/쓰기/검색/목록/태그/최근 | 공유 지식베이스 |
| **OnChain** (3) | ETH 잔액, 가스, 트랜잭션 | Etherscan |
| **Gateway** (2) | 상태, 도구 목록 | 내부 |

## API Keys

| Key | Source | Required | Coverage |
|-----|--------|----------|----------|
| `BOK_ECOS_API_KEY` | [ECOS](https://ecos.bok.or.kr) | **Yes** | 30 경제지표, 20 통화 환율 |
| `DART_API_KEY` | [OpenDART](https://opendart.fss.or.kr) | **Yes** | 52개 종목 재무제표/공시 |
| `KOSIS_API_KEY` | [KOSIS](https://kosis.kr/openapi/) | Optional | 51개 통계 테이블 |
| `RONE_API_KEY` | [data.go.kr](https://data.go.kr) 한국부동산원 | Optional | 72개 지역 부동산 지표 |
| `FRED_API_KEY` | [FRED](https://fred.stlouisfed.org/docs/api/) | Optional | 40개 미국 경제지표 |
| `MOLIT_API_KEY` | [data.go.kr](https://data.go.kr) 국토부 | Optional | 130+ 시군구 실거래가 |
| `FINNHUB_API_KEY` | [Finnhub](https://finnhub.io) | Optional | 미국 주식/경제일정 |
| `NAVER_CLIENT_ID/SECRET` | [Naver Developers](https://developers.naver.com) | Optional | 뉴스 검색/감성분석 |
| `ETHERSCAN_API_KEY` | [Etherscan](https://etherscan.io/apis) | Optional | 온체인 데이터 |
| `EIA_API_KEY` | [EIA](https://www.eia.gov/opendata/) | Optional | 에너지 가격 |
| `KIS_API_KEY` | [한국투자증권](https://apiportal.koreainvestment.com) | Optional | 실시간 한국 주가 |

## Usage Examples

```
"삼성전자 DCF 분석해줘"
→ DART 실제 재무제표 → ECOS 기준금리 → DCF 적정주가 산출

"현재 한국 매크로 상황"
→ 기준금리, 환율, GDP, M2, CPI, 실업률, BSI, CSI 스냅샷

"SK하이닉스 vs 마이크론 비교"
→ K-IFRS ↔ US-GAAP 정규화 → 멀티플 비교 → 코리아 디스카운트 분석

"서울 강남구 아파트 실거래가"
→ 국토부 실거래가 API (시군구코드 11680)

"전월세전환율 찾아줘"
→ KOSIS 51개 테이블에서 검색 → DT_30404_N0033

"비트코인 김치 프리미엄"
→ 업비트 vs 바이낸스 실시간 비교

"한국 수출 동향 (미국, 중국, 베트남)"
→ UN Comtrade 데이터 (55개국 코드)

"금리 관련 ECOS 통계 검색"
→ 834개 ECOS 테이블에서 키워드 필터링 → 21건 매칭
```

## Architecture

```
Client (Claude Desktop / Claude Code / AI Agent)
        │
        ▼ streamable-http
   Gateway Server (FastMCP v3.x)
   ├─ /health (헬스체크)
   ├─ /mcp (MCP 엔드포인트)
   │
   ├── 27 Sub-servers
   │   ├── Korean Economy: ECOS, KOSIS, DART, FSC, Stocks
   │   ├── Real Estate: R-ONE, Realestate Trans
   │   ├── Global: FRED/Macro, US Equity, Crypto, DeFi
   │   ├── Analysis: Valuation, Visualization
   │   ├── News: News, Global News, Academic, Prediction
   │   ├── Real Economy: Maritime, Aviation, Energy, Agriculture, Trade, Politics, Patent
   │   └── Infra: Vault, OnChain, Gateway
   │
   ├── 15 Adapters
   │   DART, KIS, KRX, Yahoo, FRED, CoinGecko, CCXT,
   │   Naver, Finnhub, Etherscan, CryptoCompare, MOLIT, FSC,
   │   Global Macro (OECD/IMF/BIS/WB), Phase3 (Maritime/Aviation/...)
   │
   └── Core
       ├── Cache Manager (4-tier TTL)
       ├── Rate Limiter (per-source)
       └── Fallback Chain
```

## Data Policy

**Real data only.** No sample data, mock data, or fake data — ever.
API 호출 실패 시 가짜 데이터로 대체하지 않고 명확한 에러 메시지를 반환합니다.

## Deployment

```bash
# systemd service
sudo cp nexus-finance-mcp.service /etc/systemd/system/
sudo systemctl enable nexus-finance-mcp
sudo systemctl start nexus-finance-mcp

# Health check
curl http://127.0.0.1:8100/health
# {"status":"ok","loaded_servers":27,"tool_count":131}

# nginx reverse proxy (optional, for public access)
# See /etc/nginx/sites-enabled/default
```

## License

MIT

---

*Part of the [Luxon AI Agent Network](https://github.com/pollmap)*
