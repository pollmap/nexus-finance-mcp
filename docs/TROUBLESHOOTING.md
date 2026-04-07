# Troubleshooting Guide

> Nexus Finance MCP 운영 문제 진단 가이드

## 1. Gateway 헬스체크

```bash
# 기본 상태 확인
curl http://127.0.0.1:8100/health

# 예상 응답:
# {
#   "status": "ok",
#   "version": "8.0.0-phase12",
#   "loaded_servers": 64,
#   "failed_servers": 0,
#   "tool_count": 364,
#   "uptime_seconds": 12345
# }
```

**문제 진단:**
| 증상 | 원인 | 해결 |
|------|------|------|
| `curl: Connection refused` | 서버 미실행 | `systemctl start nexus-finance-mcp` |
| `loaded_servers < 64` | 일부 서버 로드 실패 | 로그에서 `x {key} failed:` 검색 |
| `tool_count < 364` | 서버 로드 실패 + 도구 누락 | `failed_servers` 확인 후 개별 수정 |

## 2. API Key 문제

### 필수/선택 키 매트릭스

| Key | 필수도 | 영향 범위 | 확인 방법 |
|-----|--------|-----------|-----------|
| `BOK_ECOS_API_KEY` | **필수** | ECOS 8개 도구 | `ecos_get_base_rate()` 호출 |
| `DART_API_KEY` | **필수** | DART 7개 도구 | `dart_company_info("005930")` |
| `KOSIS_API_KEY` | 권장 | KOSIS 5 + R-ONE 6 = 11개 | `kosis_search()` |
| `FRED_API_KEY` | 권장 | FRED 기반 도구 | `consumer_housing()` |
| `FINNHUB_API_KEY` | 선택 | US Equity 4개 | `us_stock_quote("AAPL")` |
| `ETHERSCAN_API_KEY` | 선택 | OnChain 3개 | `onchain_eth_balance()` |
| `EIA_API_KEY` | 선택 | Energy 일부 | `energy_eia_data()` |
| `NAVER_CLIENT_ID/SECRET` | 선택 | News 4개 | `news_search("삼성전자")` |
| `KIS_API_KEY` | 선택 | Stocks 실시간 | `stocks_quote()` |
| `NASA_API_KEY` | 선택 | Space 일부 (DEMO_KEY 가능) | `space_solar_flares()` |

### 키 설정 위치

```bash
# .env 파일 위치
/opt/nexus-finance-mcp/.env

# 확인
cat /opt/nexus-finance-mcp/.env | grep -v '^#' | grep -v '^$'

# 템플릿에서 복사
cp /opt/nexus-finance-mcp/.env.template /opt/nexus-finance-mcp/.env
```

### 키 유효성 검증

```bash
# ECOS 키 테스트
curl "https://ecos.bok.or.kr/api/StatisticSearch/YOUR_KEY/json/kr/1/1/722Y001/M/202401/202401/0101000"

# DART 키 테스트
curl "https://opendart.fss.or.kr/api/company.json?crtfc_key=YOUR_KEY&corp_code=00126380"
```

## 3. Rate Limiting 문제

### 증상
- 응답이 평소보다 느림 (토큰 대기 중)
- 타임아웃 발생

### 진단

```
# MCP 도구로 확인
api_call_stats()

# 반환값에서 확인:
# - today_calls: 오늘 총 호출 수
# - top_tools: 가장 많이 호출된 도구
# - session_calls: 세션 내 호출 수
```

### 서비스별 쿼터

| Service | 쿼터 (req/min) | 초과 시 |
|---------|---------------|---------|
| dart | 100 | 토큰 대기 (자동) |
| ecos | 60 | 토큰 대기 |
| yahoo | 200 | 토큰 대기 |
| coingecko | 50 | 토큰 대기 |
| edinet | 30 | 토큰 대기 |
| default | 60 | 토큰 대기 |

### 해결
- 토큰 버킷은 자동 대기 — 대부분 자동 해소
- 과도한 호출 시: 배치 크기 줄이기
- 외부 API의 자체 레이트 리밋 (HTTP 429): 서비스별 backoff

## 4. Cache 문제

### 캐시 위치
```
L1: 메모리 (LRU, 100 items) — 서버 재시작 시 초기화
L2: 메모리 (TTL, 1000 items, 1hr) — 서버 재시작 시 초기화
L3: 디스크 (/opt/nexus-finance-mcp/.cache/diskcache/) — 영구 저장
```

### 스테일 데이터 의심 시
```bash
# 디스크 캐시 크기 확인
du -sh /opt/nexus-finance-mcp/.cache/diskcache/

# 디스크 캐시 완전 초기화 (서비스 중지 후)
rm -rf /opt/nexus-finance-mcp/.cache/diskcache/

# 서비스 재시작 (L1+L2 자동 초기화)
systemctl restart nexus-finance-mcp
```

### TTL 참고
| Data Type | TTL | 설명 |
|-----------|-----|------|
| realtime_price | 60초 | 실시간 시세 |
| daily_data | 1시간 | 일별 데이터 |
| historical | 24시간 | 과거 데이터 |
| static_meta | 1주일 | 기업 정보 등 메타데이터 |
| default | 1시간 | 미분류 |

## 5. Server Load 실패

### 로그 확인
```bash
# systemd 로그
journalctl -u nexus-finance-mcp --since "1 hour ago" | grep "failed"

# 패턴: "x {server_name} failed: {error}"
# 예: "x edinet failed: No module named 'edinet_api'"
```

### 흔한 실패 원인

| 원인 | 로그 패턴 | 해결 |
|------|-----------|------|
| 패키지 미설치 | `No module named '...'` | `pip install ...` |
| API 키 없음 | `API_KEY not set` | `.env`에 키 추가 |
| 포트 충돌 | `Address already in use` | 기존 프로세스 종료 |
| 메모리 부족 | `MemoryError` | 서버 수 줄이기 or 메모리 증설 |
| 외부 API 변경 | `JSONDecodeError`, `KeyError` | 어댑터 업데이트 |

### 개별 서버만 문제인 경우
- 다른 서버에 영향 없음 (독립 로드)
- gateway_status()의 `failed` 배열 확인
- 해당 서버만 수정 후 전체 재시작

## 6. Transport 문제

| Transport | 용도 | 포트 | 설정 |
|-----------|------|------|------|
| streamable-http | 원격 접속 (권장) | 8100 | `--transport streamable-http` |
| stdio | 로컬 Claude Code | N/A | `--transport stdio` |
| sse | 레거시 | 8100 | `--transport sse` |

### 원격 접속 안 될 때
```bash
# 1. 로컬 접속 확인
curl http://127.0.0.1:8100/health

# 2. 방화벽 확인
ufw status | grep 8100

# 3. Nginx 프록시 확인 (외부 접속 시)
nginx -t
systemctl status nginx
```

## 7. 빠른 진단 체크리스트

```
□ curl http://127.0.0.1:8100/health → status: ok?
□ loaded_servers == 64?
□ tool_count == 364?
□ .env 파일 존재하고 키 설정됨?
□ 디스크 공간 충분? (df -h)
□ 메모리 충분? (free -h)
□ systemd 서비스 running? (systemctl status nexus-finance-mcp)
□ 로그에 에러 없음? (journalctl -u nexus-finance-mcp --since "10 min ago")
```
