# Nexus Finance MCP 문서

> **396 tools / 64 servers** — AI 에이전트를 위한 글로벌 퀀트 금융 플랫폼

## Quick Start (3단계)

```bash
# 1. 서버 상태 확인
curl http://127.0.0.1:8100/health

# 2. 도구 목록 조회 (MCP client에서)
gateway_status()              # → loaded: 64, tool_count: 396
list_available_tools()        # → 396개 도구 이름 목록

# 3. 첫 번째 데이터 호출
ecos_get_macro_snapshot()     # → 한국 거시경제 현황 (파라미터 불필요)
```

**응답 파싱 핵심**: 
```python
if response.get("error"):     # 에러 먼저 확인
    print(response["message"])
else:
    data = response["data"]    # 데이터 접근
```

## 문서 목록

### 시작하기
| 문서 | 설명 | 핵심 내용 |
|------|------|-----------|
| [USAGE_GUIDE.md](USAGE_GUIDE.md) | 사용법 가이드 | 5가지 입력 패턴, 5개 워크플로우 예제 |
| [PARSING_GUIDE.md](PARSING_GUIDE.md) | 응답 파싱 가이드 | 응답 포맷 스펙, 도메인별 필드, 3단계 파싱 |

### 레퍼런스
| 문서 | 설명 | 핵심 내용 |
|------|------|-----------|
| [TOOL_CATALOG.md](TOOL_CATALOG.md) | 도구 카탈로그 | Tier 1-4 복잡도, 11개 도메인, 입력 패턴 |
| [ERROR_REFERENCE.md](ERROR_REFERENCE.md) | 에러 레퍼런스 | 5개 에러 카테고리, 재시도 전략, 레이트 리밋 |

### 운영/개발
| 문서 | 설명 | 핵심 내용 |
|------|------|-----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 아키텍처 | 3-tier 캐시, Dead Code 감사, 레이어 구조 |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | 트러블슈팅 | API 키, 캐시, Gateway 디버깅 체크리스트 |
| [COMPETITIVE_ANALYSIS.md](COMPETITIVE_ANALYSIS.md) | 경쟁사 분석 | FMP/EODHD/Alpaca/QuantConnect 벤치마크, SWOT |
| [COVERAGE_AUDIT.md](COVERAGE_AUDIT.md) | API 커버리지 감사 | ECOS/DART/CCXT/SEC 등 소스별 노출률, 개선 로드맵 |

## 도구 한눈에 보기

```
Korean Economy (27)  ──  ecos_, dart_, kosis_, stocks_, fsc_
Global Markets (36)  ──  global_, us_, asia_, india_, crypto_
Quant Analysis (88)  ──  quant_, ts_, backtest_, factor_, signal_, portfolio_
Alternative Data(32) ──  space_, disaster_, climate_, conflict_, sentiment_
News & Research (29) ──  news_, academic_, research_, rss_, prediction_
Real Economy   (31)  ──  energy_, agri_, maritime_, aviation_, trade_
Regulatory     (22)  ──  sec_, edinet_, regulation_, health_, environ_
Visualization  (48)  ──  val_, ta_, viz_
Infrastructure (22)  ──  vault_, memory_, ontology_, gateway_
PhD-Level Math (48)  ──  stat_arb_, stochvol_, micro_, ml_, alpha_, vol_, math_
```

## 연관 문서

- [README.md](../README.md) — 프로젝트 메인 README (연결 설정, API 키)
- [DEPLOY_GUIDE.md](../DEPLOY_GUIDE.md) — 배포 가이드 (설치, systemd)
- [.env.template](../.env.template) — API 키 템플릿
