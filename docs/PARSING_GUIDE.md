# Nexus Finance MCP — 응답 파싱 가이드 (PARSING GUIDE)

> 대상: MCP 도구 응답을 코드에서 안정적으로 처리하려는 개발자
> 기준: 42개 어댑터 실제 코드 리버스 엔지니어링 결과 (v8.0.0-phase12)

---

## 1. Response Envelope (응답 구조 현실)

> 이 섹션의 내용은 `base_server.py` 스펙이 아니라 **42개 어댑터가 실제로 반환하는 구조** 기준이다.

### 성공 응답 (Success Response)

```json
{
  "success": true,
  "data": [...],           // Primary payload. 성공 시 항상 존재
  "count": 42,             // 레코드 수. 대부분의 도구에서 포함
  "source": "BOK ECOS",   // 데이터 출처. 일부 도구에서 포함
  // ...도메인별 추가 필드 (아래 섹션 참조)
}
```

### 에러 응답 (Error Response)

```json
{
  "error": true,
  "message": "사람이 읽을 수 있는 에러 설명"
}
```

### 주의: 사용하지 않는 필드

`base_server.py`에 정의된 `code`, `error_type`, `context`, `details` 필드는  
**현재 어떤 어댑터에서도 프로덕션에서 사용하지 않는다.**  
이 필드에 의존하는 파싱 코드를 작성하면 안 된다.

---

## 2. 신뢰할 수 있는 파싱 전략 (3-Step)

```python
def parse_mcp_response(response: dict):
    """
    Nexus Finance MCP 응답 표준 파싱.
    모든 도구에 공통 적용 가능.
    """
    # Step 1: 에러 먼저 체크
    if response.get("error"):
        raise Exception(response.get("message", "Unknown error"))

    # Step 2: 기본 데이터 추출
    data = response.get("data", [])

    # Step 3: 도메인별 추가 필드는 보너스로 활용
    count = response.get("count", len(data) if isinstance(data, list) else 0)
    source = response.get("source", "unknown")

    return data
```

**핵심 원칙:**
- `response.get("error")` 체크를 **항상 먼저** 한다
- `data` 키 부재 시 빈 리스트 `[]`로 폴백한다
- `count`, `source` 등 부가 필드는 존재하면 활용, 없으면 무시한다

---

## 3. 도메인별 추가 응답 필드

각 도메인 어댑터가 `success` + `data` + `count` 외에 추가로 반환하는 필드 목록.

| 도메인 | 추가 필드 | 대표 도구 |
|--------|----------|----------|
| ECOS / Macro | `indicator`, `unit`, `frequency`, `latest`, `period` | `ecos_get_base_rate` |
| DART / Equity | `stock_code`, `year`, `report_type` | `dart_financial_ratios` |
| Crypto (CCXT) | `exchange`, `symbol`, `last`, `bid`, `ask`, `volume` | `crypto_ticker` |
| Quant Analysis | `method`, `parameters`, `statistics` | `quant_lagged_correlation` |
| News | `articles`, `query` | `news_search` |
| Visualization | `chart_type`, `file_path` | `viz_line_chart` |
| Academic | `papers`, `total_results` | `academic_search` |
| Backtest | `strategy`, `sharpe`, `mdd`, `cagr` | `backtest_run` |
| Valuation | `model`, `intrinsic_value`, `upside` | `val_dcf_valuation` |

### 도메인별 파싱 예시

**ECOS 기준금리 응답 처리:**

```python
response = ecos_get_base_rate()
data = parse_mcp_response(response)

# 부가 필드 활용
indicator = response.get("indicator", "기준금리")
unit = response.get("unit", "%")
latest = response.get("latest")     # 최신값 바로 접근

print(f"{indicator}: {latest}{unit}")
```

**Crypto 시세 응답 처리:**

```python
response = crypto_ticker(symbol="BTC/KRW")
data = parse_mcp_response(response)

# CCXT 특화 필드
exchange = response.get("exchange", "unknown")
last_price = response.get("last")    # 현재가 (data 배열 말고 루트 레벨)
bid = response.get("bid")
ask = response.get("ask")
```

**Visualization 응답 처리:**

```python
response = viz_line_chart(data=rate_data, x_column="date", y_columns=["rate"])
# viz_ 도구는 data 배열이 아닌 file_path가 핵심

file_path = response.get("file_path")   # 생성된 PNG/HTML 경로
chart_type = response.get("chart_type", "line")
```

---

## 4. 데이터 타입별 Cache TTL

도구 호출 결과가 언제까지 신선한지 판단하는 기준.  
실시간 데이터를 저장해두고 재사용할 때 TTL을 초과하면 재호출이 필요하다.

| 데이터 타입 | TTL | 해당 도구 예시 | 주의 사항 |
|-------------|-----|---------------|----------|
| `realtime_price` | 60초 | `crypto_ticker`, `stocks_quote` | 1분 이내 재호출 시 캐시값 가능 |
| `daily_data` | 1시간 | `ecos_get_base_rate`, `kosis_*` | 장 마감 후 업데이트 |
| `historical` | 24시간 | `stocks_history`, `space_sunspot_data` | 일 1회 이상 호출 불필요 |
| `static_meta` | 1주일 | `dart_company_info`, `list_available_tools` | 기업 정보, 도구 목록 |

---

## 5. 일반적인 데이터 형태 (Common Data Shapes)

실제 `data` 필드 안에서 만나게 되는 구조 3가지.

### Shape A: 레코드 배열 (가장 흔한 형태)

시계열 및 목록 데이터의 기본 형태.

```json
{
  "success": true,
  "data": [
    {"date": "2024-01", "value": 3.5},
    {"date": "2024-02", "value": 3.5},
    {"date": "2024-03", "value": 3.25}
  ],
  "count": 3,
  "source": "BOK ECOS"
}
```

```python
# 파이썬 처리
data = parse_mcp_response(response)
dates = [row["date"] for row in data]
values = [row["value"] for row in data]
```

### Shape B: 단일 객체 (Single Object)

기업 정보, 현재 상태 등 단건 데이터.

```json
{
  "success": true,
  "data": {
    "company": "삼성전자",
    "stock_code": "005930",
    "sector": "전자",
    "market_cap": 4000000000000
  }
}
```

```python
data = parse_mcp_response(response)
# data가 dict인지 list인지 확인 후 처리
if isinstance(data, dict):
    company_name = data.get("company")
```

### Shape C: 중첩 구조 + 메타데이터 (Nested with Metadata)

복합 결과를 반환하는 분석 도구나 검색 도구.

```json
{
  "success": true,
  "data": {
    "records": [
      {"date": "2024-01", "roe": 12.5},
      {"date": "2023-01", "roe": 14.2}
    ],
    "summary": {
      "avg_roe": 13.35,
      "period": "2023-2024"
    }
  },
  "source": "DART"
}
```

```python
data = parse_mcp_response(response)
records = data.get("records", [])
summary = data.get("summary", {})
avg_roe = summary.get("avg_roe")
```

---

## 6. 빈 결과 vs 에러 구분 (Empty vs Error)

이 두 가지를 혼동하는 버그가 가장 흔하다.

**빈 결과 (정상):**
```json
{"success": true, "data": [], "count": 0, "message": "No data found for given period"}
```
- `error` 키가 없거나 `false`
- `data`가 빈 배열
- `len(data) == 0` 으로 체크

**실제 에러:**
```json
{"error": true, "message": "ECOS_API_KEY not set"}
```
- `error` 키가 `true`
- `data` 키 없음

```python
response = ecos_get_base_rate()

# 올바른 처리 순서
if response.get("error"):
    print(f"에러: {response.get('message')}")
else:
    data = response.get("data", [])
    if not data:
        print("데이터 없음 (정상 빈 결과)")
    else:
        # 정상 처리
        process(data)
```

---

## 7. 타입 검증 유틸리티 (Type Validation Utility)

프로덕션 코드에서 사용할 수 있는 방어적 파싱 헬퍼.

```python
from typing import Union

def safe_get_records(response: dict) -> list[dict]:
    """에러/빈값/단일객체를 모두 처리하는 범용 헬퍼."""
    if response.get("error"):
        raise ValueError(response.get("message", "MCP error"))

    data = response.get("data", [])

    if isinstance(data, dict):
        # Shape C: 중첩 구조 — records 서브키 시도
        return data.get("records", [data])

    if isinstance(data, list):
        return data

    return []


def safe_get_single(response: dict) -> dict:
    """단일 객체 응답 전용 헬퍼."""
    records = safe_get_records(response)
    return records[0] if records else {}
```

---

*최종 업데이트: 2026-04-07 | Nexus Finance MCP v8.0.0-phase12 기준*
