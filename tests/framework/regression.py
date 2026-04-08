"""Regression detection: compare current test run with previous."""
import json
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class RegressionReport:
    newly_broken: list  # [(tool, prev_status, curr_status, error_msg)]
    newly_fixed: list   # [(tool, prev_status, curr_status)]
    still_broken: list  # [(tool, status, error_msg)]
    perf_regressions: list  # [(tool, prev_ms, curr_ms)]

    def has_regressions(self) -> bool:
        return len(self.newly_broken) > 0

    def summary(self) -> str:
        lines = []
        if self.newly_broken:
            lines.append(f"  NEW FAILURES ({len(self.newly_broken)}):")
            for tool, prev, curr, err in self.newly_broken[:10]:
                lines.append(f"    ✗ {tool}: {prev} → {curr} ({err[:60] if err else ''})")
        if self.newly_fixed:
            lines.append(f"  FIXED ({len(self.newly_fixed)}):")
            for tool, prev, curr in self.newly_fixed[:10]:
                lines.append(f"    ✓ {tool}: {prev} → {curr}")
        if self.perf_regressions:
            lines.append(f"  SLOWER (>2x) ({len(self.perf_regressions)}):")
            for tool, prev_ms, curr_ms in self.perf_regressions[:10]:
                lines.append(f"    ⚠ {tool}: {prev_ms:.0f}ms → {curr_ms:.0f}ms ({curr_ms/prev_ms:.1f}x)")
        if not lines:
            lines.append("  No regressions detected.")
        return "\n".join(lines)


class RegressionDetector:
    PASS_STATUSES = {"PASS", "SOFT_PASS"}
    FAIL_STATUSES = {"FAIL", "TIMEOUT"}

    def __init__(self, current_results: list, previous_path: str):
        self.current = {}
        for r in current_results:
            name = r.get("tool_name") if isinstance(r, dict) else getattr(r, "tool_name", "")
            self.current[name] = r
        self.previous = self._load(previous_path)

    def _load(self, path: str) -> dict:
        try:
            with open(path, "r") as f:
                data = json.load(f)
            results = data.get("results", [])
            return {r["tool_name"]: r for r in results}
        except Exception:
            return {}

    def _get(self, r, key):
        return r.get(key) if isinstance(r, dict) else getattr(r, key, None)

    def detect(self) -> RegressionReport:
        newly_broken = []
        newly_fixed = []
        still_broken = []
        perf_regressions = []

        for name, curr in self.current.items():
            prev = self.previous.get(name)
            if not prev:
                continue

            curr_status = self._get(curr, "status")
            prev_status = self._get(prev, "status")
            curr_ms = self._get(curr, "response_time_ms") or 0
            prev_ms = self._get(prev, "response_time_ms") or 0

            # Newly broken
            if prev_status in self.PASS_STATUSES and curr_status in self.FAIL_STATUSES:
                err = self._get(curr, "error_message") or ""
                newly_broken.append((name, prev_status, curr_status, err))

            # Newly fixed
            elif prev_status in self.FAIL_STATUSES and curr_status in self.PASS_STATUSES:
                newly_fixed.append((name, prev_status, curr_status))

            # Still broken
            elif prev_status in self.FAIL_STATUSES and curr_status in self.FAIL_STATUSES:
                err = self._get(curr, "error_message") or ""
                still_broken.append((name, curr_status, err))

            # Performance regression (>2x slower, minimum 100ms to avoid noise)
            if prev_ms > 100 and curr_ms > prev_ms * 2:
                perf_regressions.append((name, prev_ms, curr_ms))

        return RegressionReport(
            newly_broken=sorted(newly_broken),
            newly_fixed=sorted(newly_fixed),
            still_broken=sorted(still_broken),
            perf_regressions=sorted(perf_regressions, key=lambda x: x[2]/x[1], reverse=True),
        )
