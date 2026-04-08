#!/usr/bin/env python3
"""
Nexus Finance MCP — Tool Verification Runner

Usage:
    python scripts/run_tool_verification.py                    # Run all
    python scripts/run_tool_verification.py --tier 1           # Tier 1 only
    python scripts/run_tool_verification.py --server dart      # One server
    python scripts/run_tool_verification.py --compare latest   # With regression
    python scripts/run_tool_verification.py --dry-run          # List tools only
"""
import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Load env
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


def main():
    parser = argparse.ArgumentParser(description="Nexus Finance MCP Tool Verification")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3], help="Run only specific tier")
    parser.add_argument("--server", type=str, help="Run only specific server (e.g., dart)")
    parser.add_argument("--parallel", type=int, default=10, help="Max parallel tests (default: 10)")
    parser.add_argument("--timeout", type=float, default=30.0, help="Per-tool timeout in seconds (default: 30)")
    parser.add_argument("--output-dir", type=str, help="Report output directory")
    parser.add_argument("--compare", type=str, help="Previous report JSON for regression detection")
    parser.add_argument("--dry-run", action="store_true", help="List tools without running")
    args = parser.parse_args()

    print()
    print("=" * 60)
    print("  NEXUS FINANCE MCP TOOL VERIFICATION")
    print("=" * 60)
    print()

    # Step 1: Scan tools
    print("  [1/4] Scanning tools...")
    from tests.framework.scanner import scan_all_servers
    registry = scan_all_servers()
    print(f"         Found {len(registry)} tools across {len(set(v.get('server') for v in registry.values()))} servers")

    # Step 2: Filter
    if args.tier:
        registry = {k: v for k, v in registry.items() if v.get("tier") == args.tier}
        print(f"         Filtered to Tier {args.tier}: {len(registry)} tools")
    if args.server:
        registry = {k: v for k, v in registry.items() if v.get("server") == args.server}
        print(f"         Filtered to server '{args.server}': {len(registry)} tools")

    if not registry:
        print("  No tools to test!")
        return

    # Dry run: just list tools
    if args.dry_run:
        print()
        print(f"  {'Tool Name':<40} {'Server':<20} {'Tier':<6} {'Key'}")
        print(f"  {'-'*40} {'-'*20} {'-'*6} {'-'*20}")
        for name, spec in sorted(registry.items()):
            key = spec.get("requires_key", "")
            key_status = f"{key} ({'OK' if os.environ.get(key, '') else 'MISSING'})" if key else ""
            print(f"  {name:<40} {spec.get('server', ''):<20} {spec.get('tier', 0):<6} {key_status}")
        print(f"\n  Total: {len(registry)} tools")
        return

    # Step 3: Run tests
    print(f"  [2/4] Running {len(registry)} tests (parallel={args.parallel}, timeout={args.timeout}s)...")
    print()

    from tests.framework.runner import AsyncTestRunner
    runner = AsyncTestRunner(max_parallel=args.parallel, timeout=args.timeout)

    start_time = time.monotonic()
    results = asyncio.run(runner.run_all(registry))
    duration = time.monotonic() - start_time

    print()  # Clear progress line
    print()

    # Step 4: Generate reports
    print(f"  [3/4] Generating reports...")
    from tests.framework.reporter import ReportGenerator
    reporter = ReportGenerator(results, duration)
    paths = reporter.generate_all(args.output_dir)

    # Step 5: Regression detection (optional)
    if args.compare:
        print(f"\n  [4/4] Regression detection...")
        compare_path = args.compare
        if compare_path == "latest":
            compare_path = str(PROJECT_ROOT / "output" / "test_reports" / "latest.json")

        from tests.framework.regression import RegressionDetector
        detector = RegressionDetector(
            [r.to_dict() if hasattr(r, 'to_dict') else r for r in results],
            compare_path,
        )
        report = detector.detect()
        print(report.summary())
        if report.has_regressions():
            print("\n  ⚠ REGRESSIONS DETECTED!")
    else:
        print(f"  [4/4] Skipping regression (use --compare latest)")

    print()
    print(f"  Done! Reports at: {paths.get('html', 'N/A')}")
    print()

    # Exit code
    fail_count = sum(1 for r in results if (r.status if hasattr(r, 'status') else r.get('status')) in ("FAIL", "TIMEOUT"))
    sys.exit(1 if fail_count > 0 else 0)


if __name__ == "__main__":
    main()
