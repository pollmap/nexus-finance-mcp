# Luxon AI — 전체 생태계 도식화

> 5 GitHub Repos · 31 Skills · 3 Agents · 50+ Cron Jobs · 14 Ports
> 생성일: 2026-04-08

---

## 1. 생태계 전체 구조 (Ecosystem Overview)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LUXON AI ECOSYSTEM                                    │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  GitHub Repos │  │   31 Skills  │  │  3 AI Agents │  │    Infra     │    │
│  │  (5 repos)    │  │  (Claude     │  │  (OpenClaw)  │  │  (VPS +     │    │
│  │               │  │   Code)      │  │              │  │   WSL)      │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │              │
│         └─────────────────┴─────────────────┴─────────────────┘              │
│                                     │                                        │
│                              Obsidian Vault                                  │
│                          (Shared Brain, 490 commits)                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. GitHub 레포 구조 (5 Repos)

```
pollmap (GitHub)
│
├─── 📊 nexus-finance-mcp ★ Main Product
│    ├── 396 tools / 64 servers
│    ├── Finance & Research Intelligence Platform
│    ├── Commits: 23 | Last: 2026-04-08
│    ├── Tech: Python 3.12 + FastMCP 3.x
│    ├── URL: http://62.171.141.206/mcp
│    └── Docs: README + 10 docs/ files
│
├─── 📝 luxon-blog (luxon-github-blog)
│    ├── Astro 기반 기술 블로그
│    ├── 70+ 포스트 (퀀트, 크립토, 매크로, 저널클럽)
│    ├── Commits: 89 | Last: 2026-04-07
│    ├── Tech: Astro + Tailwind + Three.js
│    ├── 폰트: Pretendard + JetBrains Mono
│    └── 자동 포스팅: cron (blog backfill, channel engine)
│
├─── 🧠 luxon-vault (obsidian-vault)
│    ├── 멀티에이전트 공유 뇌 (PARA 방법론)
│    ├── 5 에이전트가 공동 사용
│    ├── Commits: 490 | Last: 2026-04-08
│    ├── 구조: 00-Inbox → 01-Projects → 02-Areas → 03-Resources → 04-Archive
│    ├── 자동 동기화: VPS ↔ WSL (hourly git push)
│    └── 시맨틱 검색: Ollama bge-m3 (3시간 인덱싱)
│
├─── ₿ luxon-korean-crypto-intel (luxon-mcp)
│    ├── 한국 크립토 인텔 MCP 서버
│    ├── Upbit/Bithumb 가격, 김치프리미엄
│    ├── Commits: 2 | Last: 2026-03-16
│    ├── Tech: Node.js + MCP SDK
│    ├── 기능: 커뮤니티 감성, FSC 규제, 알파시그널
│    └── Port: 8000
│
└─── 🌟 awesome-mcp-servers (포크)
     ├── MCP 서버 큐레이션 리스트 기여
     ├── Branch: add-nexus-finance-mcp
     ├── Commits: 4650 | Last: 2026-03-20
     └── 상태: nexus-finance-mcp 등록 PR 작업 중
```

---

## 3. 스킬 생태계 (31 Skills)

```
/root/claude-skills-local/skills/ (31 skills)
│
├─── 💰 금융 분석 (4 skills) ──── nexus-finance MCP 연동
│    ├── cufa-equity-report      CUFA 기업분석보고서 (HTML+XLSX+MD, 60K+자)
│    ├── quant-fund              AI 헤지펀드 운용 (7단계 파이프라인)
│    ├── macro-dashboard         거시경제 10대지표 다크테마 차트
│    └── competition-arsenal     공모전 통합무기고 (데이터→보고서→발표)
│
├─── 📄 보고서 생성 (3 skills)
│    ├── research-report         한국어 연구보고서 (DOCX+HTML, 40K+자)
│    ├── claude-deep-research    딥리서치 (인용 추적, 소스 신뢰도)
│    └── debate-arsenal          토론 대비 (반박표+화법대본+PPT)
│
├─── 📊 문서/프레젠테이션 (6 skills)
│    ├── docx                    Word 문서 생성/편집
│    ├── xlsx                    Excel 스프레드시트
│    ├── pptx                    PowerPoint 프레젠테이션
│    ├── pdf                     PDF 처리 (읽기/합치기/분할/워터마크)
│    ├── markitdown              10+ 포맷 → 마크다운 변환
│    └── mla-dsa-analysis        인터랙티브 의사결정 HTML
│
├─── 🎨 디자인/크리에이티브 (4 skills)
│    ├── frontend-design         프로덕션급 웹 UI
│    ├── algorithmic-art         p5.js 제너레이티브 아트
│    ├── theme-factory           10종 프리셋 테마 적용
│    └── json-canvas             Obsidian 캔버스/마인드맵
│
├─── 🔧 인프라/개발 (6 skills)
│    ├── claude-api              Claude API/SDK 통합
│    ├── mcp-builder             MCP 서버 빌드 가이드
│    ├── gsd-workflow            대규모 작업 오케스트레이션
│    ├── smux                    tmux 크로스페인 통신
│    ├── webapp-testing          Playwright 웹앱 테스트
│    └── skill-forge             스킬 생성/테스트 메타스킬
│
├─── 🧠 지식/리서치 (4 skills)
│    ├── obsidian                Obsidian Vault 통합
│    ├── think-tank              장기 사고 파트너
│    ├── defuddle                웹페이지 클린 추출
│    └── product-self-knowledge  Anthropic 제품 지식
│
├─── 🎯 특수 목적 (4 skills)
│    ├── luxon-problem-solving   Luxon 검증 문제해결 패턴
│    ├── notebooklm-pipeline     NotebookLM 콘텐츠 생성
│    └── (... 기타)
│
└─── 📈 MCP 연동 의존성 맵
     │
     │   cufa-equity-report ──→ DART + MCP 396도구
     │   quant-fund ──────────→ nexus-finance 364도구
     │   competition-arsenal ─→ nexus-finance 126도구
     │   macro-dashboard ─────→ nexus-finance + FRED
     │
     └── 나머지 27개: MCP 독립 (자체 완결형)
```

---

## 4. 에이전트 아키텍처 (3 Agents)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      MULTI-AGENT SYSTEM (OpenClaw)                           │
│                                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐    │
│  │  HERMES (ENTJ)      │  │  NEXUS (ENFJ)       │  │  DOGE (INTP)    │    │
│  │  범용 서비스 거래자  │  │  금융·지정학 분석가  │  │  리서치 탐험가  │    │
│  ├─────────────────────┤  ├─────────────────────┤  ├──────────────────┤    │
│  │ Port: 18789         │  │ Port: 18790         │  │ (WSL SSH)       │    │
│  │ Model: gpt-5.4      │  │ Model: gpt-5.4      │  │ tmux: doge      │    │
│  │ Fallback: 5.3-spark │  │ Fallback: 5.3-spark │  │                 │    │
│  │ Discord: 6 channels │  │ Discord: 7 channels │  │                 │    │
│  │ Memory: 503MB       │  │ Memory: 468MB       │  │                 │    │
│  │                     │  │                     │  │                 │    │
│  │ 역할:               │  │ 역할:               │  │ 역할:           │    │
│  │ • 수익 창출         │  │ • 금융 데이터 분석  │  │ • 학술 리서치   │    │
│  │ • 클라이언트 대응   │  │ • 알파 시그널 생성  │  │ • 논문 탐색     │    │
│  │ • 블로그 콘텐츠     │  │ • 보고서 생성       │  │ • 실험적 분석   │    │
│  │ • 일일 리포트       │  │ • 퀀트 파이프라인   │  │ • 저널 클럽     │    │
│  └─────────┬───────────┘  └─────────┬───────────┘  └────────┬─────────┘    │
│            │                       │                        │               │
│            └───────────────────────┼────────────────────────┘               │
│                                    │                                        │
│                          ┌─────────▼──────────┐                             │
│                          │   Obsidian Vault    │                             │
│                          │   (Shared Brain)    │                             │
│                          │                     │                             │
│                          │  00-Inbox/          │                             │
│                          │  ├── HERMES/        │                             │
│                          │  ├── NEXUS/         │                             │
│                          │  └── DOGE/          │                             │
│                          │  01-Projects/       │                             │
│                          │  02-Areas/          │                             │
│                          │  03-Resources/      │                             │
│                          └────────────────────┘                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. 인프라 포트 맵 (VPS: 62.171.141.206)

```
                    ┌──────────────────────────────┐
                    │    VPS (vmi3138243)            │
                    │    62.171.141.206              │
                    └──────────────┬───────────────┘
                                   │
    ┌──────────────────────────────┼──────────────────────────────┐
    │                              │                              │
┌───▼───┐  ┌───────┐  ┌───────┐  │  ┌────────┐  ┌────────┐     │
│  :22  │  │  :80  │  │ :443  │  │  │ :8000  │  │ :8100  │     │
│  SSH  │  │ HTTP  │  │ HTTPS │  │  │ Luxon  │  │ Nexus  │     │
│       │  │ nginx │  │ nginx │  │  │ MCP    │  │Finance │     │
└───────┘  └───┬───┘  └───┬───┘  │  │(Node)  │  │MCP     │     │
               │          │      │  └────────┘  │(Python)│     │
               │          │      │              └────────┘     │
               ▼          ▼      │                              │
        ┌──────────────────┐     │  ┌────────┐  ┌────────┐     │
        │  nginx Routes    │     │  │ :8300  │  │:11434  │     │
        ├──────────────────┤     │  │ Kakao  │  │Adapter │     │
        │ /mcp  → :8100    │     │  │Adapter │  │Bridge  │     │
        │ /site → static   │     │  └────────┘  └────────┘     │
        │ /avatar → :12393 │     │                              │
        │ /kakao → :8300   │     │  ┌────────┐  ┌────────┐     │
        │ /api/mcp → :8100 │     │  │:12393  │  │:20241  │     │
        │ /api/luxon→:8000 │     │  │Avatar  │  │Cloud-  │     │
        └──────────────────┘     │  │VTuber  │  │flare   │     │
                                 │  │(WS)    │  │Tunnel  │     │
                                 │  └────────┘  └────────┘     │
    ┌────────────────────────────┤                              │
    │   Agent Gateways           │                              │
    │   (loopback only)          │                              │
    │                            │                              │
    │  ┌────────┐ ┌────────┐    │                              │
    │  │:18788  │ │:18789  │    │                              │
    │  │ Main   │ │HERMES  │    │                              │
    │  │Gateway │ │Gateway │    │                              │
    │  └────────┘ └────────┘    │                              │
    │             ┌────────┐    │                              │
    │             │:18790  │    │                              │
    │             │NEXUS   │    │                              │
    │             │Gateway │    │                              │
    │             └────────┘    │                              │
    └───────────────────────────┴──────────────────────────────┘
```

---

## 6. 자동화 크론 타임라인 (50+ Jobs)

```
┌──────────────────────────────────────────────────────────────────────┐
│                     24-HOUR CRON TIMELINE (UTC)                       │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  EVERY MINUTE ····················································· │
│  │ agent-status.sh · clear_stale_locks.sh                            │
│                                                                       │
│  EVERY 5 MIN ······················································ │
│  │ cleanup-locks · dashboard-data · mcp-cache · guardian             │
│                                                                       │
│  EVERY 30 MIN ····················································· │
│  │ session-monitor · agent-health-report · zombie-check · token-mon  │
│                                                                       │
│  HOURLY ··························································· │
│  │ dashboard-build · memory-sync · cron-health · vault-push-wsl      │
│                                                                       │
│  3-HOURLY ························································· │
│  │ vault-indexing (Ollama bge-m3 시맨틱 인덱스 재구축)               │
│                                                                       │
│  ──────────── DAILY CYCLE ──────────────────────────────────────────  │
│                                                                       │
│  00:00  Upbit connector · agent cleanup · DOGE research start        │
│  03:00  Log cleanup (7-day rotation)                                  │
│  04:00  Chart file cleanup · vault linker                             │
│  06:00  Daily infrastructure audit                                    │
│  09:05  Research router (morning batch)                               │
│  13:00  HERMES daily report generation                                │
│  14:00  Engagement tracker · memory save to vault                     │
│  18:00  Stock analysis (Mon-Fri only)                                 │
│  21:00  Linkareer crawler (공모전/취업 정보)                           │
│  22:00  Luxon feed · member briefs (build → dispatch)                 │
│  22:05  Research router (evening batch)                               │
│  23:00  Blog backfill (자동 포스팅)                                    │
│                                                                       │
│  ──────────── WEEKLY ──────────────────────────────────────────────── │
│                                                                       │
│  SUN 00:00  Corrections check (자기교정 루프)                         │
│  MON-FRI    CUFA watchlist monitor (종목 감시)                         │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 7. 데이터 흐름 전체도 (End-to-End)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  External    │     │   User       │     │  Scheduled   │
│  APIs (50+)  │     │  (Claude     │     │  Cron Jobs   │
│              │     │   Code)      │     │  (50+)       │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌──────────────────────────────────────────────────────────┐
│                  NEXUS FINANCE MCP                         │
│               (396 tools / 64 servers)                     │
│                                                            │
│  Korean ─┐                                                 │
│  Global ─┤                                                 │
│  Crypto ─┼──→ Gateway ──→ JSON Response                    │
│  Quant  ─┤                                                 │
│  Research┘                                                 │
└─────────────────────┬────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌────────────┐ ┌────────────┐ ┌────────────┐
│  31 Skills │ │  3 Agents  │ │  Obsidian  │
│            │ │            │ │  Vault     │
├────────────┤ ├────────────┤ ├────────────┤
│ cufa-report│ │ HERMES     │ │ 00-Inbox   │
│ quant-fund │ │  수익/블로그│ │ 01-Projects│
│ macro-dash │ │ NEXUS      │ │ 02-Areas   │
│ competition│ │  분석/시그널│ │ 03-Resource│
│ research   │ │ DOGE       │ │ 04-Archive │
│ docx/pptx  │ │  리서치    │ │            │
│ ... +25    │ │            │ │ 490 commits│
└─────┬──────┘ └─────┬──────┘ └─────┬──────┘
      │              │              │
      ▼              ▼              ▼
┌──────────────────────────────────────────────┐
│                  OUTPUT                        │
│                                                │
│  📊 Interactive HTML (CUFA 보고서, 대시보드)    │
│  📄 DOCX (연구보고서, 경쟁분석)                 │
│  📈 XLSX (재무모델, 민감도분석)                  │
│  📋 PPTX (발표자료, 토론덱)                     │
│  📉 PNG/SVG (차트 33종, 다크테마)               │
│  📝 Markdown (블로그 포스트, 리서치 노트)        │
│  🔊 Audio (NotebookLM 팟캐스트)                 │
│  💬 Discord/Telegram (에이전트 메시지)           │
└──────────────────────────────────────────────┘
```

---

## 8. 스킬 × MCP 도구 매핑

```
┌─────────────────────────────────────────────────────────────────┐
│              SKILL → MCP TOOL CHAIN MAP                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  cufa-equity-report                                               │
│  ├── dart_company_info → dart_financial_statements                │
│  ├── dart_financial_ratios → dart_cash_flow → dart_dividend       │
│  ├── val_dcf_valuation → val_peer_comparison                     │
│  ├── stocks_quote → stocks_history                                │
│  └── viz_bar_chart → viz_radar → viz_waterfall                   │
│  Output: Interactive HTML (50+ SVG) + XLSX + MD (60K자)          │
│                                                                   │
│  quant-fund                                                       │
│  ├── factor_score → factor_backtest → factor_correlation          │
│  ├── signal_scan → signal_combine → signal_walkforward            │
│  ├── portfolio_optimize → portfolio_risk_parity                   │
│  ├── backtest_run → backtest_drawdown → backtest_risk             │
│  └── vol_garch → math_kalman → mlpipe_triple_barrier             │
│  Output: 포트폴리오 리포트 + 성과분석 + 리스크 대시보드           │
│                                                                   │
│  macro-dashboard                                                  │
│  ├── ecos_get_base_rate → ecos_get_m2 → ecos_get_gdp             │
│  ├── macro_fred("FEDFUNDS") → macro_fred("CPIAUCSL")             │
│  ├── ecos_get_exchange_rate → macro_oecd                          │
│  └── viz_line_chart → viz_dual_axis → viz_bar_chart               │
│  Output: 10대 지표 다크테마 PNG 차트                               │
│                                                                   │
│  competition-arsenal                                              │
│  ├── ecos_* → macro_* → kosis_* (데이터 수집)                    │
│  ├── quant_correlation → quant_regression (분석)                  │
│  ├── viz_* (시각화 검증)                                          │
│  └── docx → pptx → xlsx (산출물 생성)                             │
│  Output: DOCX + PPTX + XLSX + PNG 풀세트                          │
│                                                                   │
│  ───── MCP 독립 스킬 (27개) ────                                  │
│  research-report     → 자체 웹검색 + DOCX/HTML                    │
│  deep-research       → 자체 WebFetch + 인용추적                   │
│  frontend-design     → HTML/CSS/JS 자체 생성                      │
│  algorithmic-art     → p5.js 자체 생성                             │
│  obsidian            → vault CRUD (MCP vault_* 도구와 별개)       │
│  ... 22개 더                                                      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. 프로젝트별 기술 스택

```
┌──────────────────────┬────────────┬───────────────────────────────┐
│ Project              │ Language   │ Stack                          │
├──────────────────────┼────────────┼───────────────────────────────┤
│ nexus-finance-mcp    │ Python     │ FastMCP 3.x + 64 servers      │
│ luxon-blog           │ TypeScript │ Astro + Tailwind + Three.js   │
│ luxon-vault          │ Markdown   │ Obsidian + Git + bge-m3       │
│ luxon-korean-crypto  │ JavaScript │ Node.js + MCP SDK + Express   │
│ luxon-site           │ Python     │ Pelican SSG + Bootstrap       │
│ luxon-avatar         │ Python     │ Open-LLM-VTuber + WebSocket  │
│ 31 Skills            │ Mixed      │ Claude Code SKILL.md format   │
│ Agent System         │ —          │ OpenClaw + systemd + Discord  │
│ Automation           │ Bash       │ 50+ cron jobs + systemd       │
└──────────────────────┴────────────┴───────────────────────────────┘
```

---

## 10. 보안 & 접근 제어 맵

```
┌─────────────────────────────────────────────────────────────────┐
│                    ACCESS CONTROL MAP                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  PUBLIC (인증 없음)                                               │
│  ├── /mcp           Nexus Finance MCP (rate limited)             │
│  ├── /site/         Luxon 포트폴리오 사이트                       │
│  ├── /avatar/       Avatar VTuber WebSocket                      │
│  ├── /kakao/        KakaoTalk 스킬 서버                          │
│  └── /health        헬스체크 엔드포인트                            │
│                                                                   │
│  AUTHENTICATED (Basic Auth)                                       │
│  ├── /              대시보드 (HTTPS only)                         │
│  └── /strategy/     전략 엔진 대시보드                             │
│                                                                   │
│  INTERNAL ONLY (127.0.0.1)                                       │
│  ├── :8100          Nexus Finance MCP (direct)                   │
│  ├── :8000          Luxon MCP HTTP                               │
│  ├── :8300          Kakao Adapter                                │
│  ├── :11434         Adapter Bridge                               │
│  ├── :12393         Avatar Server                                │
│  ├── :18788         Main Agent Gateway (token)                   │
│  ├── :18789         HERMES Gateway (token)                       │
│  └── :18790         NEXUS Gateway (token)                        │
│                                                                   │
│  RATE LIMITS                                                      │
│  ├── api zone:       10 req/s (burst 20)                         │
│  └── mcp_public:     5 req/s (burst 10)                          │
│                                                                   │
│  TLS                                                              │
│  ├── Cert:           Self-signed (2026-03 ~ 2036-03)             │
│  ├── Protocols:      TLSv1.2 + TLSv1.3                          │
│  └── HSTS:           enabled (365 days)                          │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

*Generated by Luxon AI Ecosystem · 2026-04-08*
*5 Repos · 31 Skills · 3 Agents · 396 MCP Tools · 50+ Cron Jobs*
