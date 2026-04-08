"""Report generator for MCP tool verification results."""
import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import List

# Import from sibling module
# from tests.framework.runner import ToolTestResult


class ReportGenerator:
    def __init__(self, results: list, duration_seconds: float = 0):
        self.results = results  # list of ToolTestResult (as dicts or objects)
        self.duration = duration_seconds
        self.timestamp = datetime.utcnow().isoformat() + "Z"

    def _get_field(self, r, key):
        """Get field from either dict or object."""
        return r.get(key) if isinstance(r, dict) else getattr(r, key, None)

    def _counts(self):
        c = Counter(self._get_field(r, "status") for r in self.results)
        return c

    def _by_tier(self):
        tiers = defaultdict(lambda: Counter())
        for r in self.results:
            tier = self._get_field(r, "tier")
            status = self._get_field(r, "status")
            tiers[tier][status] += 1
        return dict(tiers)

    def _by_server(self):
        servers = defaultdict(lambda: Counter())
        for r in self.results:
            server = self._get_field(r, "server")
            status = self._get_field(r, "status")
            servers[server][status] += 1
        return dict(servers)

    def _failures(self):
        return [r for r in self.results if self._get_field(r, "status") in ("FAIL", "TIMEOUT")]

    def console_summary(self):
        """Print colored console summary."""
        counts = self._counts()
        total = len(self.results)
        by_tier = self._by_tier()
        failures = self._failures()

        # Calculate pass rate
        pass_count = counts.get("PASS", 0) + counts.get("SOFT_PASS", 0)

        print()
        print("=" * 60)
        print("  NEXUS FINANCE MCP TOOL VERIFICATION")
        print(f"  {self.timestamp} | Duration: {self.duration:.0f}s")
        print("=" * 60)
        print()
        print(f"  PASS: {counts.get('PASS', 0)}/{total}  SOFT_PASS: {counts.get('SOFT_PASS', 0)}")
        print(f"  EXPECTED_FAIL: {counts.get('EXPECTED_FAIL', 0)}  FAIL: {counts.get('FAIL', 0)}  TIMEOUT: {counts.get('TIMEOUT', 0)}")
        print()

        # Tier breakdown
        tier_names = {1: "Tier 1 (computation)", 2: "Tier 2 (free API)", 3: "Tier 3 (API key)"}
        for tier in sorted(by_tier.keys()):
            tc = by_tier[tier]
            tier_total = sum(tc.values())
            tier_pass = tc.get("PASS", 0) + tc.get("SOFT_PASS", 0) + tc.get("EXPECTED_FAIL", 0)
            pct = (tier_pass / tier_total * 100) if tier_total > 0 else 0
            bar_len = 16
            filled = int(bar_len * pct / 100)
            bar = "█" * filled + "░" * (bar_len - filled)
            name = tier_names.get(tier, f"Tier {tier}")
            print(f"  {name:<22} {tier_pass:>3}/{tier_total:<3} [{bar}] {pct:5.1f}%")

        print()

        # Failures
        if failures:
            print("  FAILED TOOLS:")
            for r in failures[:20]:
                name = self._get_field(r, "tool_name")
                status = self._get_field(r, "status")
                err = self._get_field(r, "error_message") or ""
                elapsed = self._get_field(r, "response_time_ms") or 0
                print(f"    ✗ {name:<35} ({status}, {elapsed:.0f}ms) {err[:60]}")
            if len(failures) > 20:
                print(f"    ... and {len(failures) - 20} more")
        else:
            print("  No failures!")

        print()
        print("=" * 60)

    def json_report(self, output_dir: str = None) -> str:
        """Save full JSON report. Returns file path."""
        if output_dir is None:
            output_dir = str(Path(__file__).parent.parent.parent / "output" / "test_reports")

        os.makedirs(output_dir, exist_ok=True)

        counts = self._counts()
        by_tier = self._by_tier()
        by_server = self._by_server()

        report = {
            "meta": {
                "timestamp": self.timestamp,
                "duration_seconds": round(self.duration, 1),
                "total_tools": len(self.results),
                "platform_version": "8.0.0-phase14",
            },
            "summary": {
                "pass": counts.get("PASS", 0),
                "soft_pass": counts.get("SOFT_PASS", 0),
                "expected_fail": counts.get("EXPECTED_FAIL", 0),
                "fail": counts.get("FAIL", 0),
                "timeout": counts.get("TIMEOUT", 0),
                "skip": counts.get("SKIP", 0),
                "by_tier": {str(k): dict(v) for k, v in by_tier.items()},
                "by_server": {k: dict(v) for k, v in sorted(by_server.items())},
            },
            "results": [
                r if isinstance(r, dict) else r.to_dict()
                for r in self.results
            ],
        }

        # Save timestamped report
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(output_dir, f"report_{ts}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        # Save as latest.json
        latest_path = os.path.join(output_dir, "latest.json")
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"  JSON report saved: {filepath}")
        return filepath

    def html_dashboard(self, output_dir: str = None) -> str:
        """Generate self-contained HTML dashboard. Returns file path."""
        if output_dir is None:
            output_dir = str(Path(__file__).parent.parent.parent / "output" / "test_reports")

        os.makedirs(output_dir, exist_ok=True)

        counts = self._counts()
        total = len(self.results)
        pass_count = counts.get("PASS", 0)
        soft_pass = counts.get("SOFT_PASS", 0)
        expected_fail = counts.get("EXPECTED_FAIL", 0)
        fail_count = counts.get("FAIL", 0)
        timeout_count = counts.get("TIMEOUT", 0)

        # Build results JSON for embedding
        results_json = json.dumps([
            r if isinstance(r, dict) else r.to_dict()
            for r in self.results
        ], ensure_ascii=False, default=str)

        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Nexus Finance MCP - Tool Verification Dashboard</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Segoe UI', -apple-system, sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }}
.header {{ text-align: center; padding: 30px 0; border-bottom: 1px solid #30363d; margin-bottom: 20px; }}
.header h1 {{ font-size: 24px; color: #58a6ff; }}
.header .meta {{ color: #8b949e; margin-top: 8px; }}
.cards {{ display: flex; gap: 15px; justify-content: center; margin: 20px 0; flex-wrap: wrap; }}
.card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px 30px; text-align: center; min-width: 120px; }}
.card .num {{ font-size: 32px; font-weight: bold; }}
.card .label {{ font-size: 12px; color: #8b949e; margin-top: 4px; }}
.pass .num {{ color: #3fb950; }}
.soft .num {{ color: #d29922; }}
.expected .num {{ color: #8b949e; }}
.fail .num {{ color: #f85149; }}
.timeout .num {{ color: #f0883e; }}
table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: #161b22; border-radius: 8px; overflow: hidden; }}
th {{ background: #21262d; padding: 10px; text-align: left; font-size: 13px; color: #8b949e; cursor: pointer; }}
td {{ padding: 8px 10px; border-top: 1px solid #21262d; font-size: 13px; }}
tr:hover {{ background: #1c2128; }}
.badge {{ padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }}
.badge-pass {{ background: #238636; color: #fff; }}
.badge-soft {{ background: #9e6a03; color: #fff; }}
.badge-expected {{ background: #30363d; color: #8b949e; }}
.badge-fail {{ background: #da3633; color: #fff; }}
.badge-timeout {{ background: #bd561d; color: #fff; }}
.filters {{ margin: 15px 0; display: flex; gap: 10px; flex-wrap: wrap; }}
.filters select, .filters input {{ background: #21262d; color: #c9d1d9; border: 1px solid #30363d; padding: 6px 10px; border-radius: 4px; }}
</style>
</head>
<body>

<div class="header">
  <h1>Nexus Finance MCP - Tool Verification</h1>
  <div class="meta">{self.timestamp} | Duration: {self.duration:.0f}s | v8.0.0-phase14</div>
</div>

<div class="cards">
  <div class="card pass"><div class="num">{pass_count}</div><div class="label">PASS</div></div>
  <div class="card soft"><div class="num">{soft_pass}</div><div class="label">SOFT PASS</div></div>
  <div class="card expected"><div class="num">{expected_fail}</div><div class="label">EXPECTED FAIL</div></div>
  <div class="card fail"><div class="num">{fail_count}</div><div class="label">FAIL</div></div>
  <div class="card timeout"><div class="num">{timeout_count}</div><div class="label">TIMEOUT</div></div>
</div>

<div class="filters">
  <select id="filterStatus" onchange="filterTable()">
    <option value="">All Status</option>
    <option value="PASS">PASS</option>
    <option value="SOFT_PASS">SOFT_PASS</option>
    <option value="EXPECTED_FAIL">EXPECTED_FAIL</option>
    <option value="FAIL">FAIL</option>
    <option value="TIMEOUT">TIMEOUT</option>
  </select>
  <select id="filterTier" onchange="filterTable()">
    <option value="">All Tiers</option>
    <option value="1">Tier 1 (Computation)</option>
    <option value="2">Tier 2 (Free API)</option>
    <option value="3">Tier 3 (API Key)</option>
  </select>
  <input type="text" id="filterSearch" placeholder="Search tool name..." oninput="filterTable()">
</div>

<table id="resultsTable">
<thead>
<tr>
  <th onclick="sortTable(0)">Tool Name</th>
  <th onclick="sortTable(1)">Server</th>
  <th onclick="sortTable(2)">Tier</th>
  <th onclick="sortTable(3)">Status</th>
  <th onclick="sortTable(4)">Time (ms)</th>
  <th>Error</th>
</tr>
</thead>
<tbody id="tbody"></tbody>
</table>

<script>
const results = {results_json};
const tbody = document.getElementById('tbody');

function badgeClass(s) {{
  return {{'PASS':'badge-pass','SOFT_PASS':'badge-soft','EXPECTED_FAIL':'badge-expected','FAIL':'badge-fail','TIMEOUT':'badge-timeout'}}[s] || '';
}}

function renderTable(data) {{
  tbody.innerHTML = data.map(r => `<tr>
    <td>${{r.tool_name}}</td>
    <td>${{r.server}}</td>
    <td>${{r.tier}}</td>
    <td><span class="badge ${{badgeClass(r.status)}}">${{r.status}}</span></td>
    <td>${{(r.response_time_ms||0).toFixed(0)}}</td>
    <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${{r.error_message||''}}</td>
  </tr>`).join('');
}}

function filterTable() {{
  const status = document.getElementById('filterStatus').value;
  const tier = document.getElementById('filterTier').value;
  const search = document.getElementById('filterSearch').value.toLowerCase();
  let filtered = results;
  if (status) filtered = filtered.filter(r => r.status === status);
  if (tier) filtered = filtered.filter(r => String(r.tier) === tier);
  if (search) filtered = filtered.filter(r => r.tool_name.toLowerCase().includes(search));
  renderTable(filtered);
}}

let sortDir = 1;
function sortTable(col) {{
  const keys = ['tool_name','server','tier','status','response_time_ms'];
  const key = keys[col];
  results.sort((a,b) => {{
    let va = a[key], vb = b[key];
    if (typeof va === 'number') return (va - vb) * sortDir;
    return String(va).localeCompare(String(vb)) * sortDir;
  }});
  sortDir *= -1;
  filterTable();
}}

renderTable(results);
</script>
</body>
</html>"""

        filepath = os.path.join(output_dir, "dashboard.html")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"  HTML dashboard saved: {filepath}")
        return filepath

    def generate_all(self, output_dir: str = None) -> dict:
        """Generate all reports."""
        self.console_summary()
        json_path = self.json_report(output_dir)
        html_path = self.html_dashboard(output_dir)
        return {"json": json_path, "html": html_path}
