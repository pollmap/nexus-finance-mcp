# Nexus Finance MCP — 시스템 아키텍처

> 최종 업데이트: 2026-04-07  
> 버전: MCP v8.0.0-phase12  
> 역공학(reverse engineering) 기반 실측 문서. 코드와 불일치 시 코드 우선.

---

## 1. System Overview

| 항목 | 값 |
|------|----|
| 총 도구 수 | 364 tools |
| 서버 수 | 64 servers |
| 어댑터 수 | 48 adapters |
| Core 모듈 | 5 modules |
| Gateway | 1 (단일 진입점) |
| 프레임워크 | FastMCP 3.1.1 |
| 전송 방식 | Streamable HTTP |
| 포트 | 8100 (localhost) |
| 외부 접근 | Nginx 프록시 경유 |

### 전체 구조 요약

```
Client (MCP / curl)
    │
    ▼
Gateway (port 8100)          ← 단일 진입점
    │
    ├── 64 Sub-servers        ← 도메인별 도구 등록
    │       │
    │       └── 46 Adapters  ← 외부 API HTTP 클라이언트
    │
    └── Core Infrastructure  ← 캐시 / 레이트 리밋 / 카운터
```

---

## 2. Layer Architecture

### 2-1. Gateway Layer — `gateway_server.py`

Gateway는 플랫폼의 단일 진입점이다. 64개 서브서버를 동적으로 import하고 FastMCP에 mount한다.

**주요 동작:**
- 시작 시 `servers/` 디렉터리를 스캔하여 64개 서버를 동적 import
- `mount()` 호출 시 **flat namespace** 적용 — 서버 prefix 없이 도구 이름이 직접 노출됨
- 도구 이름 충돌 시 마지막으로 mount된 서버가 우선

**메타 도구 3종 (Gateway 직접 제공):**

| 도구 | 설명 |
|------|------|
| `gateway_status` | 서버 수, 도구 수, 가동 시간 반환 |
| `list_available_tools` | 등록된 전체 도구 목록 및 서버 매핑 |
| `api_call_stats` | 서비스별 API 호출 횟수 통계 |

**Health Endpoint:**
```
GET http://127.0.0.1:8100/health
→ {"status": "ok", "servers": 64, "tools": 364}
```

**인증:**
- 내부(localhost): 인증 없음
- 외부: `MCP_AUTH_TOKEN` 환경변수 → Nginx에서 Bearer 토큰 검증

---

### 2-2. Server Layer — `servers/*.py` (64개 파일)

64개 서버는 두 가지 패턴이 혼재한다.

#### 패턴 A: BaseMCPServer 상속 (14개 서버)
Phase 9–12에서 추가된 서버 및 DART 서버가 해당된다.

```python
class DartServer(BaseMCPServer):
    def __init__(self):
        super().__init__("dart")
        self._register_tools()

    def _register_tools(self):
        @self.mcp.tool()
        async def get_dart_disclosure(...):
            ...
```

#### 패턴 B: 독립 클래스 (50개 서버)
초기 Phase에서 작성된 서버. `BaseMCPServer`를 상속하지 않고 자체적으로 FastMCP 인스턴스를 생성한다.

```python
class YahooFinanceServer:
    def __init__(self):
        self.mcp = FastMCP("yahoo_finance")
        self._register_tools()

    def _register_tools(self):
        @self.mcp.tool()
        async def get_stock_price(...):
            ...
```

**공통 사항:**
- 모든 서버는 `@self.mcp.tool()` 데코레이터로 도구를 등록
- 도구 반환값은 plain dict (강제 스키마 없음)
- 에러 처리는 각 서버가 인라인으로 직접 수행

---

### 2-3. Adapter Layer — `adapters/*.py` (46개 파일)

외부 API에 대한 HTTP 클라이언트 래퍼 계층이다.

**역할:**
- `httpx` / `aiohttp` 기반 비동기 HTTP 요청
- 서비스별 캐시 및 레이트 리밋 적용
- 응답을 dict로 변환하여 서버 계층에 전달

**응답 패턴 (실측):**
```python
# 성공
return {"success": True, "data": {...}, ...domain_extras}

# 실패
return {"error": True, "message": "Rate limit exceeded"}
```

> 중요: 어댑터가 반환하는 형식이 실제 최종 응답 포맷이다.  
> `core/responses.py`의 헬퍼 함수는 어떤 어댑터에서도 사용되지 않는다. → [Dead Code 감사](#4-dead-code-감사-critical) 참조.

---

### 2-4. Core Infrastructure — `core/`

5개 모듈로 구성된다.

| 모듈 | 파일 | 역할 |
|------|------|------|
| Cache Manager | `cache_manager.py` | 3-tier 캐싱 (L1/L2/L3) |
| Rate Limiter | `rate_limiter.py` | Token bucket, 서비스별 quota |
| API Counter | `api_counter.py` | 호출 횟수 추적, 일별 JSON 저장 |
| Base Server | `base_server.py` | ABC, ToolError, 데코레이터 정의 |
| Responses | `responses.py` | error_response / success_response 헬퍼 |

---

## 3. Caching Architecture (3-Tier)

```
Request
  │
  ▼
L1: In-Memory LRU
    - 용량: 100 items
    - TTL: 없음 (LRU 기반 교체)
    - 히트 시: 즉시 반환
  │ miss
  ▼
L2: In-Memory TTL Cache
    - 용량: 1,000 items
    - 기본 TTL: 1시간
    - 히트 시: 반환 + L1 승격
  │ miss
  ▼
L3: DiskCache (SQLite)
    - 용량: 디스크 제한
    - 영속성: 재시작 후에도 유지
    - 히트 시: 반환 + L1/L2 승격
  │ miss
  ▼
외부 API 호출 (fresh fetch)
    │
    └──→ L1 + L2 + L3 모두 저장
```

### 데이터 타입별 TTL

| 타입 | TTL | 대표 예시 |
|------|-----|-----------|
| `realtime_price` | 60초 | 주식 실시간 호가, 크립토 가격 |
| `daily_data` | 1시간 | 일별 OHLCV, 뉴스 |
| `historical` | 24시간 | 역사적 시계열 데이터 |
| `static_meta` | 1주일 | 기업 정보, 메타데이터 |
| `default` | 1시간 | 그 외 모든 데이터 |

---

## 4. Rate Limiting (Token Bucket)

각 서비스별 독립 Token Bucket 방식. 초과 시 `{"error": true, "message": "Rate limit exceeded for {service}"}` 반환.

### 서비스별 Quota (requests per minute)

| 서비스 | Quota (rpm) | 출처 |
|--------|-------------|------|
| `dart` | 100 | OpenDART API |
| `ecos` | 60 | 한국은행 ECOS |
| `kosis` | 60 | 통계청 KOSIS |
| `fred` | 120 | FRED (St. Louis Fed) |
| `krx` | 100 | 한국거래소 KRX |
| `yahoo` | 200 | Yahoo Finance |
| `coingecko` | 50 | CoinGecko Free Tier |
| `sec` | 100 | SEC EDGAR |
| `bis` | 60 | BIS |
| `edinet` | 30 | 일본 EDINET |
| `polymarket` | 60 | Polymarket |
| `default` | 60 | fallback (미등록 서비스) |

> `edinet`이 가장 낮다(30 rpm). EDINET 관련 도구를 대량 호출 시 병목 발생 가능.

---

## 5. Dead Code 감사 (CRITICAL)

**감사 범위:** 64개 서버 + 46개 어댑터 전수 역공학 분석  
**감사 기준:** import 횟수 0 = Dead Code 판정

| 컴포넌트 | 위치 | 상태 | 근거 |
|----------|------|------|------|
| `error_response()` | `core/responses.py` | **DEAD CODE** | 42개 어댑터 + 64개 서버 전체에서 import 0건 |
| `success_response()` | `core/responses.py` | **DEAD CODE** | 동일 — 사용처 없음 |
| `_format_success()` | `base_server.py:215` | **DEAD CODE** | 0건 사용 — 서버들은 dict를 수동 빌드 |
| `_format_error()` | `base_server.py:192` | **DEAD CODE** | 0건 사용 — 서버들은 예외를 인라인 처리 |
| `tool_handler` 데코레이터 | `base_server.py:256` | **DEAD CODE** | 0건 사용 — 어떤 서버도 이 데코레이터 미사용 |
| `async_tool_handler` 데코레이터 | `base_server.py:291` | **DEAD CODE** | 0건 사용 |
| `ToolError` 클래스 | `base_server.py:247` | **DEAD CODE** | 서버에서 import 0건 |

### 실제적 영향

`core/responses.py`와 `base_server.py`의 포맷팅 유틸리티는 설계 의도와 달리 실제 코드 경로에 진입하지 않는다.

**결과:**
- 응답 포맷은 각 어댑터가 ad-hoc으로 결정
- 강제 스키마 없음 — 어댑터마다 미묘하게 다를 수 있음
- `code`, `error_type`, `context` 필드는 dead code에만 존재하며 실제 응답에 나타나지 않음

**파싱 시 주의:**
```python
# 올바른 접근 — 실제 응답 포맷 기준
if response.get("error"):
    handle_error(response["message"])
elif response.get("success"):
    data = response["data"]

# 잘못된 접근 — Dead Code 기준 (실제로 오지 않음)
error_code = response.get("code")       # 항상 None
error_type = response.get("error_type") # 항상 None
```

---

## 6. Response Format — 실제 스펙

Dead Code에 정의된 스펙과 달리, 실제 모든 어댑터가 사용하는 포맷은 다음과 같다.

### 성공 응답
```json
{
  "success": true,
  "data": { ... },
  "...domain_extras": "도메인별 추가 필드 (선택적)"
}
```

### 에러 응답
```json
{
  "error": true,
  "message": "에러 설명 문자열"
}
```

### Dead Code에만 존재하는 필드 (실제 응답에 없음)

| 필드 | 정의 위치 | 실제 응답 여부 |
|------|-----------|----------------|
| `code` | `responses.py` | 없음 |
| `error_type` | `responses.py` | 없음 |
| `context` | `responses.py` | 없음 |
| `timestamp` | `base_server.py` | 없음 |

---

## 7. 인증 및 보안

### 내부 접근 (localhost:8100)
인증 없음. VPS 방화벽(UFW)으로 외부 노출 차단.

### 외부 접근 (Nginx 프록시)
```
Client → Nginx (443/HTTPS)
    → Bearer 토큰 검증 (MCP_AUTH_TOKEN)
    → http://127.0.0.1:8100 프록시
```

### API 키 관리
각 어댑터는 환경변수에서 API 키를 읽는다.  
키 목록은 `/opt/nexus-finance-mcp/.env` 참조.

---

## 8. 확장 이력

| Phase | 추가 내용 |
|-------|-----------|
| Phase 1–8 | 초기 50개 standalone 서버 구축 |
| Phase 9 | BaseMCPServer ABC 도입, 리팩터 시작 |
| Phase 10–11 | DART, BIS, EDINET 서버 추가 |
| Phase 12 | 학술 알파 + 크립토 퀀트 + ML 서버 추가, 364 tools 달성 |

---

## 9. 관련 문서

- [README.md](README.md) — 문서 인덱스
- [PARSING_GUIDE.md](PARSING_GUIDE.md) — 응답 파싱 실전 가이드
- [ERROR_REFERENCE.md](ERROR_REFERENCE.md) — 에러 코드 및 재시도 전략
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — 디버깅 가이드
