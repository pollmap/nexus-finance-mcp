# Agent ROI Audit — 2026-04-08

Brutally honest assessment of the 3 AI agents (HERMES, NEXUS, DOGE) running on VPS1.

---

## 1. Resource Consumption

### Memory (RSS, all openclaw processes combined)

| Process         | RSS (MB) | CPU % | Notes              |
|-----------------|----------|-------|--------------------|
| openclaw (main) | 130      | 0.0   | HERMES controller  |
| gateway         | 491      | 0.7   | HERMES gateway     |
| gateway         | 310      | 0.1   | NEXUS gateway      |
| openclaw (main) | 130      | 0.0   | NEXUS controller   |
| gateway         | 466      | 1.1   | Unknown (ORACLE?)  |
| **Total**       | **1,533**| **~2%** | Out of 7.8 GB    |

The agents consume **1.5 GB** (19.6% of total 7.8 GB RAM). With the OS, MCP server, and other services, this leaves about 4.5 GB available — tight but functional.

### Disk

| Agent  | Disk Usage |
|--------|-----------|
| HERMES | 71 MB     |
| NEXUS  | 158 MB    |
| DOGE   | N/A (WSL) |

Disk is negligible. Not a concern.

### VPS Cost Estimate

- **Specs:** 4 vCPU AMD EPYC, 8 GB RAM, 145 GB SSD
- **Provider:** Contabo (likely VPS M or similar)
- **Estimated cost:** ~EUR 8-12/month (~$9-13/month)
- **Agents' share of resources:** ~20% RAM = ~$2-3/month attributed to agents

---

## 2. Agent Output — What Have They Actually Produced?

### HERMES (Content & Revenue Agent)

**Inbox files:** 33 total
**Failure rate:** 2 out of 33 files = "응답 실패" (6%)

**Actual output (all time):**
- Blog posts published: 5 headlines + 10 publications = **15 total**
- Real content posts since March 28: **4 posts** (3 blog + 1 YouTube Short)
- Weekly performance report: 1 (with honest self-assessment)
- Feed files: ~15 daily feeds, most just templates

**Revenue generated: $0**
- ACP service revenue: $0
- x402 API revenue: $0 (server not built)
- Trading P&L: $0 (no execution, no limits set)
- Polymarket P&L: $0
- Blog ad revenue: $0 (no monetization)

**Discord delivery:** FAILING — every DM attempt since April 3 returns exit code 1.

**Verdict:** HERMES writes blog posts nobody reads and reports $0 revenue daily. The blog content quality is decent but has zero distribution. The Discord integration is broken and nobody fixed it in 5+ days.

### NEXUS (Coordination & Finance Agent)

**Inbox files:** 67 total
**Failure/empty rate:** 27 out of 67 = "활동 없음" or failed briefs (**40%**)

**Actual output:**
- CUFA equity reports: 2 (SK Hynix 000660, company 005930) — these have real value
- Semiconductor PPT: 1 (42KB PPTX)
- Daily briefs: ~10, but many are just "수집 실패" or "활동 없음"
- Crontab cleanup note: 1 (actually useful)
- Morning briefs: mostly empty templates ("수집하지 못했습니다")

**Quality check:** The one good daily brief (April 3) was excellent — real news with citations, market data, actionable takeaways. But this quality appears in maybe 1 out of 5 attempts.

**Revenue generated: $0**

**Verdict:** NEXUS has the highest potential (CUFA reports, daily briefs) but 40% of its output is literally "활동 없음" (no activity). When it works, it is genuinely useful. When it does not work, it just logs that it did nothing.

### DOGE (Research & Crypto Intel Agent)

**Inbox files:** 54 total
**Failure rate:** 0 explicit failures in inbox files

**Actual output:**
- Research paper collections: Daily arxiv digests, ~3-4 papers each
- BTC regime snapshots: occasional
- RSS collection summaries: several
- Curiosity briefs: short notes

**Quality check:** DOGE is the most reliable producer. Every day it collects arxiv papers and saves them. However:
- The papers collected are RANDOM arxiv papers, not crypto/finance-specific (quantum thermodynamics, exoplanet spectroscopy, soft robot policies)
- Discord delivery: FAILING since at least April 5
- arXiv rate limiting (HTTP 429) causing missed days (April 7)

**Revenue generated: $0**

**Verdict:** DOGE is the most consistent but collects papers that have zero relevance to the stated mission (crypto quant research). It is a reliable arxiv RSS reader that nobody reads.

---

## 3. Discord Integration — Broken Across All Agents

Every single Discord DM attempt since April 3 has failed:
- HERMES daily report: "Discord DM 실패" every day
- DOGE research: "Discord 전송 (N편) FAIL" every run
- This means the primary delivery channel is dead and has been for **5 days**

Nobody noticed because nobody was checking.

---

## 4. Cost vs. Value Analysis

### Monthly Costs

| Item                    | Monthly Cost |
|-------------------------|-------------|
| VPS (agents' share)     | ~$3         |
| ChatGPT Pro (shared)    | ~$67 (1/3 of $200/month) |
| Electricity/bandwidth   | included    |
| **Total agent cost**    | **~$70/month** |

The real cost is not the VPS — it is the ChatGPT Pro subscription being consumed by agent gateway calls. Each gateway process is an active ChatGPT session.

### Monthly Value Produced

| Output                | Quantity | Estimated Value |
|-----------------------|----------|----------------|
| Blog posts            | ~4/month | $0 (no readers) |
| CUFA equity reports   | ~2/month | $20-50 (saves 2-3 hours of manual work) |
| Daily briefs (good)   | ~6/month | $5-10 (saves 10 min each, when they work) |
| Arxiv digests         | ~25/month| $0 (wrong papers, unread) |
| Revenue generated     | $0       | $0 |
| **Total monthly value** |        | **$25-60** |

### ROI Calculation

```
Monthly cost:  ~$70
Monthly value: ~$25-60
ROI: -14% to -64%
```

**The agents are net negative.** They cost more than they produce.

---

## 5. The Real Question: 24/7 Agents vs. On-Demand

What the agents do 24/7:
- Sit in memory consuming 1.5 GB RAM
- Run cron jobs that mostly fail or produce low-value output
- Log "활동 없음" repeatedly
- Fail to send Discord messages

What could be done on-demand in 5 minutes:
- Run a CUFA report when actually needed
- Check arxiv with a proper crypto-specific query
- Generate a daily brief with the `/brief` skill
- Write a blog post when there is something worth writing about

The 24/7 approach makes sense when agents autonomously generate revenue or provide time-critical alerts. These agents do neither.

---

## 6. Recommendation

### Option A (Recommended): Reduce to 1 Agent + On-Demand

**Keep:** NEXUS only (as the coordination hub)
**Kill:** HERMES and DOGE as 24/7 services
**Why:**
- NEXUS produces the only genuinely valuable output (CUFA reports)
- HERMES blog posts have no audience — write them manually when needed
- DOGE research collection can be a cron script without a full agent
- Saves ~1 GB RAM and 2/3 of ChatGPT Pro usage
- Run HERMES/DOGE tasks on-demand via slash commands when actually needed

### Option B (Minimum Viable): Fix What Is Broken First

Before any ROI discussion, fix these immediately:
1. **Discord integration is dead** — fix it or remove the cron jobs wasting cycles
2. **DOGE arxiv queries** — filter for crypto/finance papers, not random science
3. **NEXUS brief collection** — 40% failure rate is unacceptable, debug the data source
4. **HERMES revenue** — either set up real trading limits or stop pretending it is a revenue agent

### Option C (Nuclear): Go Fully On-Demand

- Stop all 3 agents as systemd services
- Replace with slash commands: `/brief`, `/cufa-equity-report`, `/research`
- Save $45-50/month in ChatGPT Pro usage
- Get the same output quality (probably better, since human triggers the right task at the right time)

---

## Summary Table

| Agent  | Files | Fail% | Revenue | RAM (MB) | Keep? |
|--------|-------|-------|---------|----------|-------|
| HERMES | 33    | 6%    | $0      | 621      | No    |
| NEXUS  | 67    | 40%   | $0      | 440      | Maybe |
| DOGE   | 54    | 0%*   | $0      | 466      | No    |

*DOGE has 0% file failures but collects irrelevant papers and all Discord delivery fails.

---

## Bottom Line

Three agents running 24/7 for 2+ weeks have generated **$0 in revenue**, consumed **1.5 GB of RAM**, and produced output that is either broken (Discord), irrelevant (DOGE arxiv), empty (NEXUS "활동 없음"), or unread (HERMES blog posts).

The honest answer: **go on-demand (Option C)** until there is a clear autonomous task that justifies 24/7 operation. The slash commands already exist to do everything these agents do, but only when you actually need it.

---

*Generated: 2026-04-08 by ROI audit*
