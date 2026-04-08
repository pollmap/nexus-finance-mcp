# Nexus Finance MCP — 배포 가이드

## 현황
- **코드**: 6서버 / 6어댑터 / 48도구 / ~10,500줄
- **포트**: 8100 (기존 MCP 서버 8000과 분리)
- **전환**: stdio → streamable-http (FastMCP 3.1.1)

---

## Step 1: VPS에 파일 업로드

```bash
# 노트북 WSL에서 실행
cd /mnt/c/Users/user1/
scp nexus-finance-mcp-deploy.zip root@62.171.141.206:/root/

# VPS에서 실행
ssh root@62.171.141.206
cd /root
unzip nexus-finance-mcp-deploy.zip -d nexus-finance-mcp
cd nexus-finance-mcp
```

## Step 2: 의존성 설치

```bash
pip install -r requirements.txt --break-system-packages

# 핵심 라이브러리 추가 (requirements.txt에 포함되지만 확인용)
pip install pykrx yfinance PublicDataReader OpenDartReader --break-system-packages
```

## Step 3: .env 확인

```bash
cat .env
# 모든 API 키가 채워져 있는지 확인
# RONE_API_KEY만 비어있음 (한국부동산원 키 별도 발급 필요)
```

## Step 4: 로컬 테스트

```bash
# 게이트웨이 초기화 테스트
python -c "
import sys; sys.path.insert(0, '.')
from mcp_servers.gateway.gateway_server import GatewayServer
g = GatewayServer()
print('OK - servers:', sum(1 for v in g._servers.values() if v))
"

# HTTP 서버 시작 (포그라운드 테스트)
python server.py --transport streamable-http --port 8100

# 다른 터미널에서 헬스체크
curl http://localhost:8100/
```

## Step 5: systemd 서비스 등록

```bash
cp nexus-finance-mcp.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable nexus-finance-mcp
systemctl start nexus-finance-mcp

# 확인
systemctl status nexus-finance-mcp
journalctl -u nexus-finance-mcp -f
```

## Step 6: 방화벽 (필요시)

```bash
ufw allow 8100/tcp
# 또는 Cloudflare Tunnel로 HTTPS 노출
```

---

## Smithery 프리미엄 등록

### Option A: HTTP URL 직접 등록

Smithery에서 Remote Server로 등록:
- **URL**: `http://62.171.141.206:8100/mcp`
- **Transport**: Streamable HTTP

### Option B: GitHub + smithery.yaml

```bash
# GitHub 리포 생성/업데이트
cd /root/nexus-finance-mcp
git init
git remote add origin https://github.com/pollmap/nexus-finance-mcp.git
git add -A
git commit -m "feat: nexus-finance-mcp v2.0 - 48 tools, HTTP/SSE"
git push -u origin main

# Smithery CLI로 publish
npx @smithery/cli publish luxon/nexus-finance-mcp \
  --repo https://github.com/pollmap/nexus-finance-mcp
```

---

## Luxon 에이전트 통합

### NEXUS 에이전트에서 MCP 호출

```python
# NEXUS SOUL.md 또는 handlers.ts에서
import requests

NEXUS_FINANCE_MCP = "http://10.0.0.1:8100"  # VPN 내부 주소

# 예: 기준금리 조회
resp = requests.post(f"{NEXUS_FINANCE_MCP}/mcp", json={
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "ecos_get_base_rate",
        "arguments": {}
    },
    "id": 1
})
```

### HERMES ACP handlers.ts에서 활용

```typescript
// korean_market_intel 서비스에서 MCP 도구 호출
const mcpUrl = "http://10.0.0.1:8100/mcp";

async function getMarketIntel() {
  const macro = await callMCP(mcpUrl, "ecos_get_macro_snapshot", {});
  const stocks = await callMCP(mcpUrl, "stocks_market_overview", {});
  return { macro, stocks };
}
```

---

## 서버 구조

```
nexus-finance-mcp/
├── server.py                     # HTTP 엔트리포인트 ★
├── .env                          # API 키
├── .env.template                 # 키 템플릿
├── requirements.txt              # 의존성
├── smithery.yaml                 # Smithery 매니페스트
├── nexus-finance-mcp.service     # systemd
├── deploy.sh                     # 배포 스크립트
├── README.md                     # GitHub README
│
├── mcp_servers/
│   ├── gateway/gateway_server.py # 통합 게이트웨이
│   ├── servers/                  # MCP 서버 (6개)
│   │   ├── ecos_server.py        # 한국은행
│   │   ├── valuation_server.py   # DCF + 상대가치
│   │   ├── viz_server.py         # 시각화
│   │   ├── kosis_server.py       # 통계청
│   │   ├── rone_server.py        # 부동산원
│   │   └── stocks_server.py      # 주식시세 (NEW)
│   ├── adapters/                 # 외부 API (6개)
│   │   ├── dart_adapter.py       # DART
│   │   ├── krx_adapter.py        # KRX (pykrx)
│   │   ├── kis_adapter.py        # 한국투자증권 (NEW)
│   │   ├── yahoo_adapter.py      # Yahoo Finance
│   │   ├── fred_adapter.py       # FRED
│   │   └── crypto_adapter.py     # CoinGecko
│   └── core/                     # 인프라
│       ├── base_server.py
│       ├── cache_manager.py
│       ├── rate_limiter.py
│       └── fallback_chain.py
│
├── analyzers/                    # 분석 엔진
│   ├── dcf_analyzer.py
│   ├── relative_value.py
│   ├── correlation_analyzer.py
│   ├── growth_calculator.py
│   ├── pir_calculator.py
│   └── real_price_calculator.py
│
└── utils/
    └── gaap_mapper.py            # K-IFRS ↔ US-GAAP
```

---

## 포트 맵 (업데이트)

| 서비스 | 포트 | 상태 |
|--------|------|------|
| MCP (기존, 3도구) | 8000 | 가동 중 |
| **Nexus Finance MCP (48도구)** | **8100** | **NEW** |
| HERMES | 18789 | 가동 중 |
| NEXUS | 18790 | 가동 중 |
| ORACLE | 18800 | 가동 중 |
| x402 | 3402 | 가동 중 |
