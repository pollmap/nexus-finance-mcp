# Nexus Finance MCP — 에러 레퍼런스 (ERROR REFERENCE)

> 대상: MCP 도구 호출 시 에러를 진단하고 빠르게 해결하려는 개발자/운영자
> 기준: 42개 어댑터, 50+ 외부 API 연동 (v8.0.0-phase12)

---

## 1. 에러 감지 (Error Detection)

모든 에러는 아래 구조를 따른다:

```json
{"error": true, "message": "Human-readable error description"}
```

**필수 원칙:** `response.get("data")`에 접근하기 **전에** 반드시 `response.get("error")`를 먼저 체크한다.

```python
response = some_tool(...)

# 올바른 순서
if response.get("error"):
    raise Exception(response.get("message"))

data = response.get("data", [])
```

### 빈 결과와 에러 구분

`{"success": true, "data": [], "message": "No data found"}` 는 에러가 아니다.  
`error` 키가 없으면 정상 응답이다. `len(data) == 0` 으로 빈 결과를 체크한다.

---

## 2. 에러 카테고리 (Error Categories)

---

### Category 1: API Key 미설정

**패턴:**
```
"ECOS_API_KEY not set"
"DART client not initialized"
"* client not initialized"
```

**영향 받는 서비스:**

| 서비스 | 환경변수 키 | 발급처 |
|--------|------------|--------|
| ECOS (한국은행) | `ECOS_API_KEY` | ecos.bok.or.kr |
| DART (금감원) | `DART_API_KEY` | opendart.fss.or.kr |
| KOSIS (통계청) | `KOSIS_API_KEY` | kosis.kr |
| FRED (미 연준) | `FRED_API_KEY` | fred.stlouisfed.org |
| Finnhub | `FINNHUB_API_KEY` | finnhub.io |
| Etherscan | `ETHERSCAN_API_KEY` | etherscan.io |
| EIA (미 에너지) | `EIA_API_KEY` | eia.gov |
| Naver 뉴스 | `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` | developers.naver.com |
| KIS (한투증권) | `KIS_APP_KEY`, `KIS_APP_SECRET` | apiportal.koreainvestment.com |
| NASA | `NASA_API_KEY` | api.nasa.gov |

**해결:**
```bash
# 키 설정
vi /opt/nexus-finance-mcp/.env

# 서버 재시작 필요 (환경변수는 시작 시 로드)
systemctl restart nexus-finance-mcp
```

**Retryable:** No (키 설정 전까지 재시도 의미 없음)

---

### Category 2: Rate Limit 초과

**패턴:**
```
HTTP 429
"timeout waiting for rate limit token"
```

**동작 방식:**  
Token Bucket 알고리즘으로 요청을 자동 제어한다.  
대부분의 경우 클라이언트는 이 에러를 보지 못한다 — 서버가 내부적으로 대기(blocking)하기 때문.

**클라이언트가 보게 되는 경우:** 버스트 요청량이 버킷 용량을 초과하거나 외부 API가 자체 429를 반환할 때.

**해결:**
- 요청 간격을 늘린다 (배치 간 `time.sleep(1)` 추가)
- 동시 요청 수를 줄인다
- Rate Limit이 낮은 서비스(`edinet`: 30/min, `coingecko`: 50/min)는 순차 처리

**Retryable:** Yes (자동 처리, 필요 시 수동 재시도)

---

### Category 3: 외부 API HTTP 에러

**패턴:** `"API returned {status_code}"`

| HTTP 코드 | 의미 | 해결 방법 | Retryable |
|-----------|------|----------|-----------|
| 400 | 잘못된 요청 (파라미터 오류) | 파라미터 확인 후 재호출 | No |
| 403 | API Key 무효/만료 | `.env`에서 키 갱신 | No |
| 404 | 리소스 없음 (잘못된 종목코드 등) | 입력값 검증 | No |
| 429 | 외부 API 자체 Rate Limit | Exponential backoff 후 재시도 | Yes |
| 500 | 외부 API 서버 오류 | 잠시 후 재시도 | Yes |
| 503 | 외부 API 서비스 불가 | 상태 페이지 확인 후 재시도 | Yes |

---

### Category 4: 데이터 없음 (Data Not Found)

**패턴:**
```json
{"success": true, "data": [], "message": "No data found for stock_code: 999999"}
```

이것은 에러 응답이 아니다. `success: true` 에 주목.

**주요 원인:**
- 잘못된 종목코드 (한국: 6자리 숫자, 예: "005930")
- 조회 기간에 데이터 없음 (상장 전 날짜, 거래정지 기간)
- 검색 키워드 오타

**진단:**
```python
data = response.get("data", [])
if not data:
    message = response.get("message", "")
    print(f"빈 결과: {message}")
    # 종목코드 재확인 또는 dart_search_company(keyword=...) 로 탐색
```

**Retryable:** No (입력값 수정 후 재호출)

---

### Category 5: Client Not Initialized

**패턴:**
```
"DART client not initialized"
"ECOS client not initialized"
```

Category 1(Key 미설정)과 유사하지만, 키가 있어도 형식이 잘못된 경우에도 발생한다.

**원인:**
1. `.env` 파일에 키 없음
2. 키 형식 오류 (공백 포함, 잘못된 따옴표)
3. 서버 시작 시 초기화 실패

**진단:**
```bash
# .env 파일 확인
cat /opt/nexus-finance-mcp/.env | grep -E "DART|ECOS"

# 서버 로그 확인
journalctl -u nexus-finance-mcp -n 50 | grep "ERROR\|initialized"
```

**Retryable:** No (설정 수정 + 서버 재시작 필요)

---

## 3. Retry 전략 매트릭스

```python
import time

def call_with_retry(tool_fn, *args, **kwargs):
    """MCP 도구 호출 표준 재시도 래퍼."""
    max_retries = 3
    base_wait = 1  # seconds

    for attempt in range(max_retries + 1):
        response = tool_fn(*args, **kwargs)

        # 에러 체크
        if not response.get("error"):
            return response  # 성공

        message = response.get("message", "")

        # API Key 미설정 / 클라이언트 초기화 실패 → 즉시 중단
        if "not set" in message or "not initialized" in message:
            raise Exception(f"설정 오류 (재시도 불가): {message}")

        # 파라미터 오류 → 즉시 중단
        if "400" in message or "Invalid" in message:
            raise Exception(f"파라미터 오류 (재시도 불가): {message}")

        # 마지막 시도였으면 예외
        if attempt == max_retries:
            raise Exception(f"최대 재시도 초과: {message}")

        # 재시도 가능한 에러 → Exponential backoff
        wait = base_wait * (2 ** attempt)
        print(f"재시도 {attempt + 1}/{max_retries} — {wait}초 대기: {message}")
        time.sleep(wait)
```

| 에러 타입 | Retryable | 대기 전략 | 최대 재시도 |
|-----------|-----------|----------|------------|
| Rate limit (429) | Yes | Token bucket 자동 대기 | 무제한 (자동) |
| HTTP 5xx | Yes | Exponential backoff (1s, 2s, 4s) | 3회 |
| API Key 미설정 | No | N/A | 0 |
| 파라미터 오류 (400) | No | 파라미터 수정 후 1회 | 1 |
| 데이터 없음 | No | N/A | 0 |
| 네트워크 타임아웃 | Yes | Linear backoff (5s) | 3회 |
| Client 미초기화 | No | 설정 수정 + 서버 재시작 | 0 |

---

## 4. 서비스별 Rate Limit 목록

호출 빈도 계획 수립 시 참고. 아래 수치를 초과하면 Token Bucket이 대기를 걸거나 외부 API가 429를 반환한다.

| 서비스 | 한도 (req/min) | 출처 | 주의 사항 |
|--------|--------------|------|----------|
| `dart` | 100 | OpenDART | 공시 데이터 대량 수집 시 주의 |
| `ecos` | 60 | BOK ECOS | 시계열 다중 조회 시 분산 필요 |
| `kosis` | 60 | KOSIS | 통계 목록 탐색 시 주의 |
| `fred` | 120 | FRED | 미국 거시지표 수집에 여유 있음 |
| `krx` | 100 | KRX | 장 중 실시간 시세 주의 |
| `yahoo` | 200 | Yahoo Finance | 상대적으로 여유 |
| `coingecko` | 50 | CoinGecko Free | 무료 플랜 제한. 버스트 금지 |
| `sec` | 100 | SEC EDGAR | 10-K/10-Q 대량 수집 시 주의 |
| `bis` | 60 | BIS | 국제결제은행 데이터 |
| `edinet` | 30 | EDINET | 일본 공시. 가장 보수적인 한도 |
| `polymarket` | 60 | Polymarket | 예측시장 데이터 |
| `default` | 60 | 내부 폴백 | 목록에 없는 서비스 기본값 |

---

## 5. 빠른 진단 체크리스트 (Quick Diagnosis Checklist)

에러 발생 시 순서대로 확인한다.

```
[ ] 1. response.get("error") 가 true 인가?
        → Yes: message 내용 확인

[ ] 2. message에 "not set" 또는 "not initialized" 포함?
        → Yes: .env 파일 확인 → 서버 재시작

[ ] 3. message에 "API returned 403" 포함?
        → Yes: API Key 만료 → 재발급 후 .env 갱신

[ ] 4. message에 "API returned 429" 포함?
        → Yes: 요청 빈도 줄이기 → Exponential backoff 적용

[ ] 5. message에 "API returned 500/503" 포함?
        → Yes: 외부 API 장애 → 잠시 후 재시도

[ ] 6. data가 빈 배열 []?
        → error 키 없으면 정상 빈 결과
        → 종목코드/날짜/키워드 재확인

[ ] 7. 위 모두 해당 없음?
        → journalctl -u nexus-finance-mcp -n 100 로 서버 로그 확인
```

---

## 6. 서버 로그 확인 명령어

```bash
# 실시간 로그
journalctl -u nexus-finance-mcp -f

# 최근 100줄
journalctl -u nexus-finance-mcp -n 100

# 에러만 필터
journalctl -u nexus-finance-mcp -n 200 | grep -i "error\|exception\|failed"

# 서비스 상태
systemctl status nexus-finance-mcp

# 설정 파일 확인
cat /opt/nexus-finance-mcp/.env
```

---

*최종 업데이트: 2026-04-07 | Nexus Finance MCP v8.0.0-phase12 기준*
