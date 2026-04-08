# Nexus Finance MCP - GitHub Promotion Strategy

**Goal:** 0 stars → 100+ stars in 60 days, establish as the go-to financial MCP server  
**Repo:** https://github.com/pollmap/nexus-finance-mcp  
**USP:** 396 financial tools, 64 servers, zero auth, one endpoint — the largest open financial MCP  
**Date:** 2026-04-08

---

## Table of Contents

1. [Week 1: Foundation (Directories + Awesome Lists)](#1-week-1-foundation)
2. [Week 2: Reddit Blitz](#2-week-2-reddit-blitz)
3. [Week 3: Hacker News + Dev Blogs](#3-week-3-hacker-news--dev-blogs)
4. [Week 4: Twitter/X Campaign](#4-week-4-twitterx-campaign)
5. [Week 5: Discord + Korean Communities](#5-week-5-discord--korean-communities)
6. [Week 6-8: Content + Sustained Growth](#6-week-6-8-content--sustained-growth)
7. [MCP Directory Checklist](#7-mcp-directory-submissions)
8. [YouTube/Demo Content](#8-youtubedemo-content)
9. [Tracking & Metrics](#9-tracking--metrics)

---

## 1. Week 1: Foundation

**Priority: Get listed everywhere before any social promotion.**

### 1a. Awesome MCP Lists (PRs)

Submit PRs to these repos — each has a "Finance" or "Data" category:

| Repo | Stars | Action | Priority |
|------|-------|--------|----------|
| [wong2/awesome-mcp-servers](https://github.com/wong2/awesome-mcp-servers) | 40k+ | PR to Finance section | **Critical** |
| [appcypher/awesome-mcp-servers](https://github.com/appcypher/awesome-mcp-servers) | 10k+ | PR to Finance section | **Critical** |
| [PipedreamHQ/awesome-mcp-servers](https://github.com/PipedreamHQ/awesome-mcp-servers) | 2k+ | PR | High |
| [TensorBlock/awesome-mcp-servers](https://github.com/TensorBlock/awesome-mcp-servers) | 1k+ | PR | High |
| [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) | Official | PR or Issue | High |
| [tolkonepiu/best-of-mcp-servers](https://github.com/tolkonepiu/best-of-mcp-servers) | Ranked list | Submit | Medium |

**PR description template:**

```markdown
## Add nexus-finance-mcp — 396 financial tools in one MCP endpoint

### Finance / Data
- [nexus-finance-mcp](https://github.com/pollmap/nexus-finance-mcp) — 396 tools across 64 servers: Korean equities (DART, ECOS, KRX), US markets (SEC EDGAR, FRED), crypto (CCXT 100+ exchanges, on-chain, DeFi), quant analysis (GARCH, Black-Litterman, HRP), 33 chart types, academic search. Open access, no auth required. Streamable-HTTP transport.
```

**Effort:** 2 hours  
**Impact:** HIGH — these lists are the #1 discovery channel for MCP servers

### 1b. MCP Directory Submissions

Submit to every directory on the same day:

| Directory | URL | How to Submit | Status |
|-----------|-----|---------------|--------|
| **Smithery** | smithery.ai | Already registered | Done |
| **mcp.so** | mcp.so | Submit button in navbar, or [GitHub issue](https://github.com/chatmcp/mcpso) | TODO |
| **Glama** | glama.ai/mcp/servers | "Add Server" button, then claim ownership | TODO |
| **PulseMCP** | pulsemcp.com | Auto-indexed from GitHub; claim listing | TODO |
| **MCPServers.org** | mcpservers.org/submit | Submit form | TODO |
| **MCP Server Finder** | mcpserverfinder.com | Submit form | TODO |
| **MCPHub** | mcphub.tools | Submit | TODO |
| **MCP Market** | mcpmarket.com | Submit | TODO |
| **MCP Directory** | mcp-server-directory.com | Submit form | TODO |
| **LobeHub** | lobehub.com/mcp | PR to plugin store | TODO |
| **AI Agents List** | aiagentslist.com/mcp-servers | Submit | TODO |

**Effort:** 3 hours  
**Impact:** HIGH — passive discovery from people browsing directories

---

## 2. Week 2: Reddit Blitz

### 2a. r/ClaudeAI (110k+ members)

**Best format:** "I built X" post with concrete demo  
**Best time:** Tuesday-Thursday, 9-11 AM EST  

**Post title:**
```
I built an MCP server with 396 financial tools — connect once and ask Claude anything about markets, quant, or macro
```

**Post body:**
```markdown
After months of building, I'm open-sourcing nexus-finance-mcp — a single MCP endpoint that gives Claude access to 396 financial tools across 64 servers.

**What it does:**
- Korean markets: Samsung stock quote, DART financials, Bank of Korea rates
- US/Global: FRED macro data, SEC EDGAR filings, India/Asia equities
- Crypto: 100+ exchanges via CCXT, on-chain analytics, DeFi TVL, funding rates
- Quant: GARCH volatility, Black-Litterman optimization, HRP portfolios, backtesting
- Research: arXiv papers, Semantic Scholar, patent search, GDELT news
- Visualization: 33 chart types (candlestick, heatmap, treemap, sankey, etc.)

**Setup (30 seconds):**
```
claude mcp add nexus-finance --transport http http://62.171.141.206/mcp
```

No API keys needed. No auth. Just connect and ask.

**Example prompts to try:**
- "Analyze Samsung Electronics as an investment — DCF + peer comparison"
- "Compare US and Korean interest rate policy with Granger causality"
- "Is BTC funding rate signaling a reversal?"
- "Build a momentum + value factor portfolio and backtest it"

GitHub: https://github.com/pollmap/nexus-finance-mcp

I'm a university student in Korea building this as part of my startup (Luxon AI). Happy to answer questions about the architecture or add tools people want.
```

**Expected:** 50-200 upvotes if timed right. r/ClaudeAI loves "I built" MCP posts.

### 2b. r/LocalLLaMA (500k+ members)

**Post title:**
```
Open-source MCP server: 396 financial tools, no auth, works with any MCP client (not just Claude)
```

**Adjust the body to emphasize:**
- Works with Cursor, Windsurf, Continue, any MCP client
- Self-hostable (Docker, pip install)
- No vendor lock-in
- Show the tool count comparison vs. competitors

**Expected:** 30-100 upvotes. This sub values open-source and self-hosting.

### 2c. r/algotrading (300k+ members)

**Post title:**
```
I built 396 financial tools as an MCP server — GARCH, Black-Litterman, HRP, backtesting, factor models — all accessible from Claude/Cursor
```

**Adjust the body to emphasize:**
- PhD-level quant tools: Heston model, Kalman filter, Lopez de Prado ML pipeline
- 150+ year historical data (Shiller 1871~, NBER 1854~, French factors 1926~)
- Backtest with 6 strategies, drawdown analysis, Sharpe optimization
- Stat arb, microstructure (VPIN), signal lab
- NOT a trading bot — it's a research/analysis toolkit

**Expected:** 20-80 upvotes. Quant-focused audience will appreciate the depth.

### 2d. Other subreddits

| Subreddit | Post angle | Impact |
|-----------|-----------|--------|
| r/MachineLearning | ML pipeline tools, Lopez de Prado, academic search | Medium |
| r/artificial | General AI tool showcase | Low |
| r/SideProject | "University student built 396-tool financial MCP" | Medium |
| r/opensource | Open-source financial intelligence platform | Medium |
| r/CryptoCurrency | Crypto quant tools, on-chain analytics, DeFi | Medium |
| r/quant | Professional quant angle, stat arb, microstructure | High |

**Total effort:** 4 hours (write 3 main posts, adapt for others)  
**Total impact:** HIGH — Reddit is the #1 driver for GitHub stars in dev tools

---

## 3. Week 3: Hacker News + Dev Blogs

### 3a. Show HN Post

**Best time:** Tuesday-Wednesday, 8-10 AM EST  
**Key:** Title must be specific and intriguing, not generic

**Title options (pick one):**
```
Show HN: 396 financial tools in one MCP endpoint — Korean/US markets, quant, crypto, climate
```
```
Show HN: Open-source MCP server with 396 finance tools — GARCH, DART, FRED, on-chain, all no-auth
```

**Post text:**
```
I'm a university student in Korea. I built nexus-finance-mcp, a single MCP endpoint
that exposes 396 financial tools across 64 microservers.

It connects to any MCP client (Claude Desktop, Cursor, Windsurf, etc.) and lets you
ask natural language questions backed by real financial data.

Coverage: Korean equities (DART, ECOS, KRX), US macro (FRED, SEC EDGAR), crypto
(CCXT 100+ exchanges, on-chain, DeFi), PhD-level quant (GARCH, Heston,
Black-Litterman, HRP), 33 chart types, academic paper search, climate/energy/
agriculture alternative data.

No authentication required. Connect in 30 seconds:
  claude mcp add nexus-finance --transport http http://62.171.141.206/mcp

Architecture: FastMCP gateway mounts 64 sub-servers, streamable-http transport.
Each server is a self-contained module with standardized adapters. Real data only —
zero mock/sample responses.

MIT licensed. https://github.com/pollmap/nexus-finance-mcp
```

**Expected:** 5-50 points. HN is unpredictable. The "university student in Korea" angle + specific tool count helps.

### 3b. dev.to Article

**Title:** `I Built the World's Largest Financial MCP Server — 396 Tools, Zero Auth, Open Source`

**Structure:**
1. Hook: "What if you could ask Claude to run a DCF valuation, check BTC funding rates, and backtest a factor portfolio — all from one endpoint?"
2. Problem: Financial data is fragmented across 50+ APIs with different auth flows
3. Solution: One MCP server, 396 tools, connect in 30 seconds
4. Architecture diagram (FastMCP gateway → 64 sub-servers)
5. 3 live examples with actual output JSON
6. "Try it now" section with the one-liner
7. What's next: call for contributors

**Tags:** `mcp`, `ai`, `finance`, `opensource`

**Effort:** 3 hours  
**Impact:** Medium — dev.to MCP articles get 2k-10k views

### 3c. Medium Article (cross-post)

Same content as dev.to but posted to:
- **Towards Data Science** publication (submit)
- **The Startup** publication
- Self-publish with tags: AI, Finance, MCP, Open Source, Quant

---

## 4. Week 4: Twitter/X Campaign

### 4a. Launch Thread

**Best time:** Tuesday 10 AM EST / Wednesday 12 PM KST  

**Thread (7 tweets):**

```
1/ I just open-sourced 396 financial tools as a single MCP server.

Connect once → ask your AI anything about markets, quant, or macro.

No API keys. No auth. Just plug and play.

GitHub: https://github.com/pollmap/nexus-finance-mcp

Here's what it can do 🧵

2/ Korean Markets (41 tools)
- DART: 20 financial disclosure endpoints
- Bank of Korea ECOS: interest rates, M2, GDP
- KRX: real-time stock quotes via pykrx
- KOSIS: national statistics
- FSC: regulatory filings

3/ Global + Crypto (73 tools)
- US: FRED macro, SEC EDGAR filings
- Asia: India NSE, Japan EDINET
- Crypto: CCXT (100+ exchanges), on-chain (Etherscan), DeFi TVL
- Funding rates, basis term structure, open interest

4/ PhD-Level Quant (82 tools)
- GARCH, Heston stochastic vol, Kalman filter
- Black-Litterman, HRP portfolio optimization
- Factor engine (momentum, value, quality)
- Lopez de Prado ML pipeline
- Stat arb, microstructure VPIN
- 150+ year historical data (Shiller 1871~)

5/ Research + Alt Data (88 tools)
- arXiv, Semantic Scholar, RISS, PubMed
- GDELT global news, Google Trends
- Climate (ENSO), energy (EIA), agriculture prices
- Space weather, maritime AIS, aviation
- 33 chart types: candlestick, heatmap, sankey...

6/ Setup takes 30 seconds:

claude mcp add nexus-finance --transport http http://62.171.141.206/mcp

Works with Claude Desktop, Cursor, Windsurf, Cline, Continue — any MCP client.

Self-host with Docker if you prefer.

7/ Built by a university student in Korea as part of @LuxonAI.

MIT licensed. Zero mock data — every response is from live APIs.

Star it, try it, break it:
https://github.com/pollmap/nexus-finance-mcp

What financial tools should I add next?
```

### 4b. Accounts to Tag/Mention

| Account | Why | How |
|---------|-----|-----|
| @AnthropicAI | MCP creators | Tag in launch tweet |
| @alexalbert__ | Anthropic, created MCP | Tag in launch tweet |
| @simonw | Influential dev tools blogger | Reply to his MCP-related tweets |
| @mcaborern | MCP ecosystem coverage | Tag |
| @sdkfj (Smithery) | Listed on Smithery | Tag |
| @swyx | AI dev community leader | Tag in quant-specific tweet |
| @bindureddy | AI/fintech | Reply to relevant threads |
| Korean AI accounts | @ai_korea_official etc. | Tag in Korean version |

### 4c. Hashtags

Primary: `#MCP` `#ModelContextProtocol` `#OpenSource` `#FinTech`  
Secondary: `#ClaudeAI` `#QuantFinance` `#AlgoTrading` `#AItools`  
Korean: `#AI개발` `#오픈소스` `#핀테크` `#퀀트`

### 4d. Ongoing Twitter Strategy

- **Monday:** Share a "tool of the week" — pick one of the 396 tools, show input/output
- **Wednesday:** Share a use case / workflow (3-4 tweets)
- **Friday:** Engagement — reply to MCP-related discussions, answer questions

**Effort:** 4 hours (thread + ongoing 30 min/week)  
**Impact:** MEDIUM-HIGH — Twitter drives sustained awareness

---

## 5. Week 5: Discord + Korean Communities

### 5a. Discord Communities

| Server | Channel | What to Post |
|--------|---------|-------------|
| **Anthropic/Claude Discord** | #mcp-showcase or #community-projects | "Built a 396-tool financial MCP — here's how to connect" |
| **MCP Discord** (if exists) | #showcase | Full demo with screenshots |
| **Cursor Discord** | #mcp-servers | "Financial MCP server that works with Cursor" |
| **Windsurf Discord** | #integrations | Same, adapted for Windsurf |
| **QuantConnect** | #general | Quant angle — factor models, backtesting |
| **r/algotrading Discord** | #tools | Trading/analysis toolkit |

**Template message for Discord:**

```
Hey everyone! I built an open-source MCP server with 396 financial tools:

- Korean/US/Asia/crypto markets
- PhD-level quant: GARCH, Black-Litterman, HRP, factor models
- 33 chart types, academic paper search, alternative data
- No auth required — connect in 30 seconds

Works with Claude Desktop, Cursor, Windsurf, any MCP client.

Setup: claude mcp add nexus-finance --transport http http://62.171.141.206/mcp

GitHub: https://github.com/pollmap/nexus-finance-mcp

Happy to answer questions or take feature requests!
```

### 5b. Korean Communities

#### 디시인사이드

| Gallery | Post Title | Angle |
|---------|-----------|-------|
| AI정보 갤러리 | "MCP 서버 만들어서 금융데이터 396개 도구 오픈소스로 풀었습니다" | AI + 금융 데이터 |
| 특이점이 온다 갤러리 | "클로드에 한국 금융데이터 396개 연결하는 MCP 서버 만들었음" | 기술 + 실용성 |
| 주식 갤러리 | "AI로 삼성전자 DCF 밸류에이션 자동으로 돌리는 도구 만들었음" | 투자 실용 |
| 코인 갤러리 | "비트코인 펀딩비+온체인+DeFi 실시간 분석 MCP 도구 396개" | 크립토 |

**디시 포맷 (캐주얼):**

```
충북대 경영학과 3학년인데
클로드AI에 한국 금융데이터 연결하는 MCP 서버 만들었음

삼성전자 현재가, DART 재무제표, 한국은행 기준금리 등
396개 금융 도구를 하나의 엔드포인트로 연결

설정 30초면 됨, API 키 필요없음, 무료 오픈소스

GitHub: https://github.com/pollmap/nexus-finance-mcp

써보고 피드백 주면 감사하겠습니다
```

#### 클리앙 (자유게시판 or 새로운소식)

```
[오픈소스] AI에 한국 금융데이터 396개 연결하는 MCP 서버 만들었습니다

안녕하세요, 충북대 경영학과 학생입니다.
Claude AI, Cursor 등에 한국/미국/암호화폐 금융데이터를 연결하는
MCP(Model Context Protocol) 서버를 오픈소스로 공개했습니다.

주요 기능:
- 한국: DART 재무제표, 한국은행 ECOS, KRX 주가, KOSIS 통계
- 미국: FRED 거시경제, SEC EDGAR 공시
- 암호화폐: 100+ 거래소, 온체인, DeFi
- 퀀트: GARCH, Black-Litterman, HRP, 백테스팅
- 시각화: 33종 차트 (캔들, 히트맵, 산키 등)

설정 30초, API 키 불필요, MIT 라이선스입니다.
GitHub: https://github.com/pollmap/nexus-finance-mcp

피드백 환영합니다!
```

#### 기타 한국 커뮤니티

| Platform | Where | Angle |
|----------|-------|-------|
| **GeekNews** (news.hada.io) | Submit link | HN-style — short title, let content speak |
| **velog.io** | Write article | Korean dev.to — detailed technical article |
| **코인판** (coinpan.com) | 자유게시판 | 크립토 퀀트 도구 강조 |
| **퀀트투자 카페** (Naver) | 게시판 | 퀀트 도구 + 팩터 모델 강조 |
| **AI Korea Slack** | #projects or #tools | 짧은 소개 + GitHub 링크 |
| **OKKY** (okky.kr) | 커뮤니티 | 한국 개발자 — 기술 아키텍처 강조 |
| **인프런 커뮤니티** | 자유 게시판 | 학습/실용 관점 |

**Effort:** 4 hours  
**Impact:** MEDIUM — Korean communities provide niche but engaged audience

---

## 6. Week 6-8: Content + Sustained Growth

### 6a. dev.to Series (3 articles)

**Article 1:** "I Built the World's Largest Financial MCP Server — 396 Tools, Zero Auth"  
**Article 2:** "How I Architected 64 MCP Sub-Servers into One Gateway (FastMCP Deep Dive)"  
**Article 3:** "PhD-Level Quant Analysis from a Chat Prompt: GARCH, Black-Litterman, and Factor Models via MCP"

### 6b. velog.io Series (Korean, 3 articles)

**Article 1:** "한국 금융 데이터 AI 연결의 모든 것 — DART, ECOS, KRX를 MCP로"  
**Article 2:** "대학생이 만든 396개 금융 MCP 도구 — 아키텍처와 교훈"  
**Article 3:** "MCP로 퀀트 투자 리서치하기 — GARCH부터 Black-Litterman까지"

### 6c. Hashnode / Medium Cross-Posts

Cross-post dev.to articles with canonical URLs to avoid SEO duplication.

---

## 7. MCP Directory Submissions

**Complete checklist — do all in Week 1:**

```
[ ] Smithery (smithery.ai) — DONE, optimize description + tags
[ ] mcp.so — Submit via navbar button or GitHub issue
[ ] Glama (glama.ai) — Add Server → claim ownership
[ ] PulseMCP (pulsemcp.com) — Auto-indexed, claim listing
[ ] MCPServers.org — Submit at mcpservers.org/submit
[ ] MCP Server Finder (mcpserverfinder.com) — Submit form
[ ] MCPHub (mcphub.tools) — Submit
[ ] MCP Market (mcpmarket.com) — Submit
[ ] MCP Directory (mcp-server-directory.com) — Submit
[ ] LobeHub (lobehub.com) — PR to MCP plugin store
[ ] AI Agents List (aiagentslist.com) — Submit
[ ] mcp.directory — Submit
```

### Smithery Optimization

Current Smithery listing needs:
- **Title:** "Nexus Finance MCP — 396 Financial Tools, Zero Auth"
- **Description:** Emphasize tool count, Korean + global coverage, no auth
- **Tags:** finance, stocks, crypto, quant, korean, macro, research, visualization
- **Screenshots:** Add 2-3 screenshots showing example outputs

---

## 8. YouTube/Demo Content

### 8a. 60-Second Demo Video

**Script:**

```
[0-5s] Title card: "396 Financial Tools in One MCP Server"

[5-15s] Show terminal: claude mcp add nexus-finance --transport http http://62.171.141.206/mcp
Voice: "One command. 396 tools. No API keys."

[15-25s] Type in Claude: "What's Samsung Electronics' current price and key financials?"
Show the response with real data flowing in.

[25-35s] Type: "Compare US and Korean interest rates with Granger causality"
Show the dual-axis chart output.

[35-45s] Type: "Is BTC funding rate signaling a reversal?"
Show multi-signal quant dashboard.

[45-55s] Type: "Build a momentum + value portfolio and backtest it"
Show Sharpe ratio + drawdown chart.

[55-60s] End card: GitHub link, "Star if useful", MIT License
```

**Tools:** OBS Studio for recording, ScreenPal or Loom for quick capture  
**Publish to:** YouTube Shorts, Twitter/X video, Reddit post embed

### 8b. Longer Demo (5 min)

Show 3 complete workflows:
1. Korean equity analysis (Samsung DCF)
2. Crypto quant dashboard (BTC signals)
3. Portfolio construction (factor + backtest)

Post to YouTube with SEO title: "396 Financial AI Tools in One MCP Server — Full Demo"

**Effort:** 3-5 hours for 60s video, 6-8 hours for 5 min  
**Impact:** HIGH for Twitter/Reddit embedding, MEDIUM standalone

---

## 9. Tracking & Metrics

### KPIs

| Metric | Week 2 Target | Week 4 Target | Week 8 Target |
|--------|--------------|--------------|--------------|
| GitHub Stars | 20 | 50 | 100+ |
| GitHub Forks | 5 | 15 | 30 |
| Unique Cloners | 10 | 30 | 60 |
| Reddit Total Upvotes | 100 | 300 | 500 |
| Twitter Impressions | 5k | 20k | 50k |
| Directory Listings | 12 | 12 | 12 |
| MCP Client Connections (server logs) | 5 | 20 | 50 |

### Weekly Tracking Commands

```bash
# GitHub traffic (requires gh CLI)
gh api repos/pollmap/nexus-finance-mcp/traffic/views
gh api repos/pollmap/nexus-finance-mcp/traffic/clones
gh api repos/pollmap/nexus-finance-mcp/traffic/popular/referrers

# Star count
gh api repos/pollmap/nexus-finance-mcp --jq '.stargazers_count'
```

---

## Priority Execution Order

| Priority | Action | Effort | Expected Stars |
|----------|--------|--------|---------------|
| **P0** | awesome-mcp-servers PRs (wong2 + appcypher) | 1 hour | +20-40 |
| **P0** | 12 directory submissions | 3 hours | +10-20 (passive) |
| **P1** | r/ClaudeAI post | 1 hour | +15-30 |
| **P1** | r/algotrading post | 30 min | +10-20 |
| **P1** | r/LocalLLaMA post | 30 min | +10-20 |
| **P2** | Show HN post | 1 hour | +5-50 (volatile) |
| **P2** | Twitter launch thread | 2 hours | +5-15 |
| **P2** | dev.to article | 3 hours | +5-10 |
| **P3** | Korean communities (dcinside, clien, geeknews) | 2 hours | +5-10 |
| **P3** | Discord communities | 1 hour | +3-5 |
| **P3** | 60-second demo video | 4 hours | +10-20 |
| **P4** | velog.io Korean article | 2 hours | +3-5 |
| **P4** | Medium / Hashnode cross-post | 1 hour | +2-5 |

**Total estimated effort:** ~22 hours over 8 weeks  
**Total expected stars:** 100-250 (conservative-optimistic)

---

## Key Principles

1. **Lead with the number.** "396 tools" is the hook. Always lead with it.
2. **Show, don't tell.** Every post should have a concrete example prompt → output.
3. **"30 seconds to connect" is the CTA.** Lower the barrier. Show the one-liner.
4. **The Korean angle is unique.** No other MCP server covers DART, ECOS, KRX. Emphasize this.
5. **"University student built X" gets sympathy upvotes.** Use it on Reddit and HN.
6. **Post on Tuesday-Wednesday.** Highest engagement across Reddit, HN, and Twitter.
7. **Respond to every comment.** Engagement breeds engagement. Answer within 2 hours.
8. **Never spam.** Space Reddit posts 3-4 days apart. One subreddit per day max.
9. **Update the README star history badge** after reaching milestones (10, 50, 100).
10. **Cross-link everything.** Every post links GitHub. Every directory links README. README links directories.

---

## Pre-Launch README Improvements

Before promoting, ensure the README has:

- [x] Clear one-liner setup command
- [x] Tool count prominently displayed
- [x] Example prompts with expected output
- [ ] **Add:** GIF or screenshot of a live session (terminal or Claude Desktop)
- [ ] **Add:** "Featured on" badges after directory listings
- [ ] **Add:** Comparison table vs. competitors (if any financial MCP exists)
- [ ] **Add:** Star History chart embed: `https://star-history.com/#pollmap/nexus-finance-mcp&Date`
- [ ] **Add:** "Contributors Welcome" section with good-first-issue labels

---

*Strategy authored 2026-04-08. Review and update monthly.*
