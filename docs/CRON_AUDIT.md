# Cron Job Audit Report

**Date:** 2026-04-08
**VPS:** vmi3138243 (Luxon VPS)
**Auditor:** Claude Code (automated)

## Summary

| Status | Count |
|--------|-------|
| HEALTHY | 24 |
| QUESTIONABLE | 7 |
| BROKEN | 12 |
| REDUNDANT | 3 |
| **Total active** | **46** |

---

## Root Crontab (44 active jobs)

### Every Minute

| Schedule | Script | Status | Issue | Recommendation |
|----------|--------|--------|-------|----------------|
| `* * * * *` | `/root/scripts/agent-status.sh` | HEALTHY | Exists, +x, runs every minute | Keep |
| `* * * * *` | `/root/scripts/clear_stale_locks.sh` | REDUNDANT | Overlaps with `cleanup-locks.sh` and `cleanup-stale-locks.sh` -- three scripts doing the same thing | Remove 2 of 3 lock cleanup jobs (see Redundancy section) |

### Every 5 Minutes

| Schedule | Script | Status | Issue | Recommendation |
|----------|--------|--------|-------|----------------|
| `*/5 * * * *` | `/root/scripts/cleanup-locks.sh` | REDUNDANT | Same function as `clear_stale_locks.sh` (every 1min) and `cleanup-stale-locks.sh` | Keep ONE of the three lock cleaners; remove the other two |
| `*/5 * * * *` | `/root/scripts/dashboard-data.sh` | HEALTHY | Exists, +x, runs fine | Keep |
| `*/5 * * * *` | `/root/cleanup-stale-locks.sh` | REDUNDANT | Third lock cleanup script doing the same stale lock removal | Remove -- consolidate into one |
| `*/5 * * * *` | `/root/scripts/mcp-cache.py` | QUESTIONABLE | Exists but no +x (run via `python3` so OK). No errors visible | Keep, but consider adding +x for consistency |
| `*/5 * * * *` | `/root/scripts/guard-openclaw-config.sh` | HEALTHY | Exists, +x | Keep |
| `*/5 * * * *` | `/root/luxon-guardian.sh` | HEALTHY | Exists, +x | Keep |
| `*/5 * * * *` | `/root/nexus-home/.openclaw/workspace/scripts/research_pipeline_watch.sh` | HEALTHY | Exists, +x | Keep |

### Every 10 Minutes

| Schedule | Script | Status | Issue | Recommendation |
|----------|--------|--------|-------|----------------|
| `*/10 * * * *` | `/root/hermes-home/.openclaw/workspace/scripts/macro_pipeline_listener.sh` | HEALTHY | Exists, +x | Keep |

### Every 30 Minutes

| Schedule | Script | Status | Issue | Recommendation |
|----------|--------|--------|-------|----------------|
| `*/30 * * * *` | `/root/nexus-home/.openclaw/workspace/scripts/session_size_monitor.sh` | HEALTHY | Exists, +x | Keep |
| `*/30 * * * *` | `/root/nexus-home/.openclaw/workspace/scripts/agent_health_report.sh` | HEALTHY | Exists, +x | Keep |
| `*/30 * * * *` | `/root/agent-zombie-check.sh` | HEALTHY | Exists, +x | Keep |

### Hourly

| Schedule | Script | Status | Issue | Recommendation |
|----------|--------|--------|-------|----------------|
| `0 * * * *` | `/root/obsidian-vault/scripts/dashboard_builder.py` | HEALTHY | Exists, run via python3 | Keep |
| `0 * * * *` | `/root/obsidian-vault/scripts/sync_memory_to_vault.py` | HEALTHY | Exists, run via python3 | Keep |
| `0 * * * *` | `/root/nexus-home/.openclaw/workspace/scripts/cron_health_check.sh` | HEALTHY | Exists, +x | Keep |
| `5 * * * *` | `/root/obsidian-vault/scripts/push_vault_to_wsl.sh` | HEALTHY | Exists, +x | Keep |
| `30 * * * *` | `/root/scripts/token-monitor.sh` | HEALTHY | Exists, +x | Keep |

### Every 2-6 Hours

| Schedule | Script | Status | Issue | Recommendation |
|----------|--------|--------|-------|----------------|
| `0 */3 * * *` | `/root/obsidian-vault/scripts/index_vault.sh` | HEALTHY | Exists, +x | Keep |
| `0 */2 * * *` | `/root/luxon-blog-writer/channel_engine.py --mode watch` | QUESTIONABLE | Script exists, venv python3 exists. Log shows "0 processed" consistently -- may not be doing useful work | Investigate if watch mode has any content to process |
| `0 */6 * * *` | `/root/strategy-engine/...chart_pattern_cron.py` | BROKEN | **Entire `/root/strategy-engine/` directory is MISSING.** Last successful run was 2026-04-03. Venv python also missing | Remove or recreate strategy-engine |

### Daily Jobs

| Schedule | Script | Status | Issue | Recommendation |
|----------|--------|--------|-------|----------------|
| `0 0 * * *` | `oracle.../upbit_connector.py status` | BROKEN | **Script missing.** `/root/oracle-home/.openclaw/workspace/scripts/` directory does not exist. Logs show repeated "No such file" errors daily | Remove -- oracle workspace was likely deleted/moved |
| `0 0 * * *` | `/root/cleanup-agent-sessions.sh` | HEALTHY | Exists, +x | Keep |
| `0 0,12 * * *` | `/root/scripts/doge_research_collector.py` | HEALTHY | Exists, run via python3 | Keep |
| `0 0,12 * * *` | `oracle.../polymarket_connector.py` | BROKEN | **Script missing.** Same issue as upbit_connector -- oracle workspace gone. Logs show repeated "No such file" errors | Remove |
| `0 3 * * *` | `find /tmp/openclaw/ -name '*.log' -mtime +7 -delete` | HEALTHY | Cleanup command, /tmp/openclaw/ exists with logs | Keep |
| `0 4 * * *` | `find .../output/charts/ -type f -mtime +7 -delete` | QUESTIONABLE | Directory exists but is empty -- cleanup has nothing to do (harmless) | Keep (low cost, good hygiene) |
| `0 4 * * *` | `/root/obsidian-vault/scripts/vault_linker.py` | HEALTHY | Exists, +x | Keep |
| `0 6 * * *` | `/root/scripts/daily-audit.sh` | HEALTHY | Exists, +x | Keep |
| `5 9 * * *` | `/root/scripts/research_router.py` | HEALTHY | Exists, +x | Keep |
| `5 22 * * *` | `/root/scripts/research_router.py` | HEALTHY | Same script, second daily run | Keep |
| `0 13 * * *` | `/root/hermes-daily-report.sh` | HEALTHY | Exists, +x | Keep |
| `0 14 * * *` | `nexus.../engagement_tracker.py` | HEALTHY | Exists, +x | Keep |
| `50 14 * * *` | `nexus.../save_daily_memory.sh` | HEALTHY | Exists, +x | Keep |
| `0 18 * * 1-5` | `/root/tools/daily_stock_analysis/main.py` | BROKEN | Script exists but **`litellm` module missing** -- ImportError every run. No +x but run via python3 | Fix: `pip install litellm` in the project's venv, or remove if not needed |
| `0 18 * * 6` | `/root/obsidian-vault/scripts/auto_archive.sh` | HEALTHY | Exists, +x | Keep |
| `0 21 * * *` | `.openclaw/.../crawlers/linkareer.py` | BROKEN | **Script missing.** `/root/.openclaw/workspace/scripts/crawlers/` directory does not exist | Remove |
| `0 22,9 * * *` | `/root/scripts/luxon_feed.py` | QUESTIONABLE | Exists but no +x (run via python3 so OK) | Keep |
| `0 22 * * *` | `.openclaw/.../build_member_briefs.py` | BROKEN | **Script missing.** `/root/.openclaw/workspace/scripts/` directory does not exist | Remove |
| `10 22 * * *` | `/root/obsidian-vault/scripts/brief_to_inbox.sh` | QUESTIONABLE | Script exists, +x, but depends on output from `build_member_briefs.py` which is broken | Review -- may be useless without brief builder |
| `5 22 * * *` | `.openclaw/.../dispatch_member_briefs.py` | BROKEN | **Script missing.** Same directory issue | Remove |
| `50 22 * * *` | `oracle.../save_daily_memory.sh` | BROKEN | **Script missing.** Oracle workspace gone. Logs confirm daily "No such file" errors | Remove |
| `0 23 * * *` | `/root/luxon-blog-writer/channel_engine.py --mode backfill` | QUESTIONABLE | Same script as watch mode. Exists, venv OK. Processing 0 items | Investigate if backfill has work to do |
| `0 0 * * 1-5` | `nexus.../cufa_watchlist_monitor.py` | HEALTHY | Exists, +x, .env exists | Keep |
| `0 0 * * 0` | `nexus.../check_corrections.sh` | HEALTHY | Exists, +x | Keep |

---

## Nexus User Crontab (2 active jobs)

| Schedule | Script | Status | Issue | Recommendation |
|----------|--------|--------|-------|----------------|
| `*/1 * * * *` | `agent-nexus/.../guest_activity_rollup.py` | BROKEN | **Script missing.** `/home/nexus/.openclaw/workspace/agent-nexus/` directory does not exist. Fails silently every minute | Remove entirely |
| `*/1 * * * *` | `agent-nexus/.../run_owner_digest_bridge.sh` | BROKEN | **Script missing.** Same directory issue. Fails every minute | Remove entirely |

---

## System Cron (/etc/cron.d/) -- All OK

| Source | Status | Notes |
|--------|--------|-------|
| certbot | HEALTHY | Standard renewal, systemd takes precedence |
| e2scrub_all | HEALTHY | Filesystem scrub, standard |
| staticroute | HEALTHY | @reboot route config |
| sysstat | HEALTHY | Activity monitoring |

---

## Critical Findings

### BROKEN Jobs (12 total -- failing silently every run)

1. **Oracle workspace deleted** (4 jobs affected):
   - `upbit_connector.py` -- daily "No such file" errors
   - `polymarket_connector.py` -- daily "No such file" errors
   - `save_daily_memory.sh` (oracle) -- daily "No such file" errors
   - Root cause: `/root/oracle-home/.openclaw/workspace/scripts/` does not exist

2. **Root .openclaw workspace scripts deleted** (3 jobs affected):
   - `linkareer.py` crawler
   - `build_member_briefs.py`
   - `dispatch_member_briefs.py`
   - Root cause: `/root/.openclaw/workspace/scripts/` has no scripts subdirectory

3. **strategy-engine deleted** (1 job):
   - `chart_pattern_cron.py` -- entire `/root/strategy-engine/` directory missing
   - Last successful run was 2026-04-03

4. **daily_stock_analysis broken** (1 job):
   - `main.py` exists but `litellm` Python module is missing
   - Fix: install litellm or set up a proper venv

5. **Nexus user jobs dead** (2 jobs):
   - `/home/nexus/.openclaw/workspace/agent-nexus/` directory does not exist
   - Both scripts fail every minute, wasting cron cycles

### Redundancy: 3 Lock Cleanup Scripts

All three do essentially the same thing (remove stale OpenClaw lock files):
- `clear_stale_locks.sh` -- runs **every minute**
- `cleanup-locks.sh` -- runs every 5 minutes
- `cleanup-stale-locks.sh` -- runs every 5 minutes

**Recommendation:** Keep `clear_stale_locks.sh` (most frequent, already covers it). Remove the other two.

### Resource Impact

- **14 broken/redundant jobs** fire regularly, producing only errors or duplicating work
- The 2 nexus user jobs alone generate 2 failed cron executions per minute (2,880/day)
- The 4 oracle jobs generate 6 failed executions per day
- No MTA installed, so error output is silently discarded ("No MTA installed, discarding output")

---

## Recommended Actions

### Immediate Removal (broken scripts, no fix possible)

```bash
# These reference deleted directories -- safe to remove from crontab
# oracle workspace (4 jobs):
#   upbit_connector.py, polymarket_connector.py, save_daily_memory.sh (oracle)
# .openclaw workspace (3 jobs):
#   linkareer.py, build_member_briefs.py, dispatch_member_briefs.py
# strategy-engine (1 job):
#   chart_pattern_cron.py
# nexus user (2 jobs):
#   guest_activity_rollup.py, run_owner_digest_bridge.sh
```

### Consolidation (redundant)

```bash
# Remove 2 of 3 lock cleanup scripts, keep clear_stale_locks.sh:
#   cleanup-locks.sh (*/5)
#   cleanup-stale-locks.sh (*/5)
```

### Fix Required

```bash
# daily_stock_analysis -- install missing dependency:
cd /root/tools/daily_stock_analysis && pip install litellm
```

### Investigate

- `channel_engine.py` (watch + backfill modes) -- processing 0 items consistently
- `brief_to_inbox.sh` -- depends on broken `build_member_briefs.py`
