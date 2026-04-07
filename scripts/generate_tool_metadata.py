#!/usr/bin/env python3
"""
Generate tool_metadata.py from all 64 MCP server files.

Scans each server's @self.mcp.tool() decorated functions,
extracts parameter signatures, and classifies input patterns.

Usage:
    python scripts/generate_tool_metadata.py
"""
import ast
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SERVERS_DIR = PROJECT_ROOT / "mcp_servers" / "servers"
OUTPUT_FILE = PROJECT_ROOT / "mcp_servers" / "core" / "tool_metadata.py"

# Server → domain mapping
SERVER_DOMAIN = {
    "ecos": "korean_macro",
    "dart": "korean_equity",
    "kosis": "korean_macro",
    "rone": "real_estate",
    "stocks": "korean_equity",
    "fsc": "korean_equity",
    "realestate_trans": "real_estate",
    "crypto_exchange": "crypto",
    "defi": "crypto",
    "onchain": "crypto",
    "crypto_quant": "crypto",
    "onchain_advanced": "crypto",
    "global_macro": "global_markets",
    "us_equity": "global_markets",
    "asia_market": "global_markets",
    "india": "global_markets",
    "hist_crypto": "crypto",
    "news": "news",
    "global_news": "news",
    "academic": "news",
    "research": "news",
    "rss": "news",
    "prediction": "news",
    "energy": "real_economy",
    "agriculture": "real_economy",
    "maritime": "real_economy",
    "aviation": "real_economy",
    "trade": "real_economy",
    "politics": "real_economy",
    "patent": "real_economy",
    "sec": "regulatory",
    "edinet": "regulatory",
    "regulation": "regulatory",
    "consumer": "regulatory",
    "health": "regulatory",
    "environ": "regulatory",
    "valuation": "visualization",
    "technical": "visualization",
    "viz": "visualization",
    "space_weather": "alternative",
    "disaster": "alternative",
    "conflict": "alternative",
    "climate": "alternative",
    "power_grid": "alternative",
    "sentiment": "alternative",
    "quant_analysis": "quant",
    "timeseries": "quant",
    "backtest": "quant",
    "factor_engine": "quant",
    "signal_lab": "quant",
    "portfolio_optimizer": "quant",
    "historical_data": "quant",
    "volatility_model": "quant",
    "advanced_math": "quant",
    "stat_arb": "quant",
    "portfolio_advanced": "quant",
    "stochvol": "quant",
    "microstructure": "quant",
    "ml_pipeline": "quant",
    "alpha_research": "quant",
    "vault": "infrastructure",
    "memory": "infrastructure",
    "vault_index": "infrastructure",
    "ontology": "infrastructure",
}

# API key requirements by server
SERVER_REQUIRES_KEY = {
    "ecos": "BOK_ECOS_API_KEY",
    "dart": "DART_API_KEY",
    "kosis": "KOSIS_API_KEY",
    "rone": "KOSIS_API_KEY",
    "fsc": None,
    "stocks": "KIS_API_KEY",
    "us_equity": "FINNHUB_API_KEY",
    "onchain": "ETHERSCAN_API_KEY",
    "energy": "EIA_API_KEY",
    "news": "NAVER_CLIENT_ID",
}


def classify_input_pattern(params: list[str]) -> str:
    """Classify tool input pattern based on parameter names."""
    param_set = set(p.lower() for p in params)

    if len(params) == 0:
        return "snapshot"
    if "stock_code" in param_set or "corp_code" in param_set:
        return "stock_code"
    if param_set & {"series", "series1", "series_list", "returns", "prices"}:
        return "series"
    if param_set & {"keyword", "query", "search_term", "term"}:
        return "search"
    if param_set & {"data", "records"} and param_set & {"columns", "x_column", "y_columns", "y_column"}:
        return "data_columns"
    return "composite"


def classify_complexity(params: list[str], domain: str) -> int:
    """Estimate complexity tier (1-4)."""
    if len(params) == 0:
        return 1
    if len(params) == 1 and classify_input_pattern(params) in ("stock_code", "search"):
        return 1
    if domain == "quant" and len(params) >= 3:
        return 4
    if domain in ("quant", "visualization") and len(params) >= 2:
        return 3
    return 2


def extract_tools_from_file(filepath: Path) -> list[dict]:
    """Extract tool definitions from a server file using AST parsing."""
    tools = []
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return tools

    # Find server name from filename
    server_key = filepath.stem.replace("_server", "")

    # Find all function definitions decorated with @self.mcp.tool()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Check if decorated with mcp.tool
            is_tool = False
            for dec in node.decorator_list:
                dec_str = ast.dump(dec)
                if "mcp" in dec_str and "tool" in dec_str:
                    is_tool = True
                    break

            if not is_tool:
                continue

            # Extract parameter names (skip 'self')
            params = []
            for arg in node.args.args:
                name = arg.arg
                if name != "self":
                    params.append(name)

            # Get docstring
            docstring = ast.get_docstring(node) or ""
            first_line = docstring.split("\n")[0].strip() if docstring else ""

            domain = SERVER_DOMAIN.get(server_key, "unknown")
            input_pattern = classify_input_pattern(params)
            complexity = classify_complexity(params, domain)

            tools.append({
                "name": node.name,
                "server": server_key,
                "domain": domain,
                "input_pattern": input_pattern,
                "complexity": complexity,
                "params": params,
                "description": first_line,
                "requires_key": SERVER_REQUIRES_KEY.get(server_key),
            })

    return tools


def main():
    all_tools = {}

    server_files = sorted(SERVERS_DIR.glob("*_server.py"))
    print(f"Scanning {len(server_files)} server files...")

    for sf in server_files:
        tools = extract_tools_from_file(sf)
        for t in tools:
            all_tools[t["name"]] = t
        if tools:
            print(f"  {sf.stem}: {len(tools)} tools")

    print(f"\nTotal: {len(all_tools)} tools")

    # Generate output
    lines = [
        '"""',
        "Tool metadata registry for Nexus Finance MCP.",
        "",
        f"Auto-generated by scripts/generate_tool_metadata.py",
        f"Total: {len(all_tools)} tools across {len(set(t['server'] for t in all_tools.values()))} servers",
        "",
        "Fields:",
        '  domain: korean_macro, korean_equity, crypto, quant, alternative,',
        '          news, real_economy, regulatory, visualization, infrastructure,',
        '          global_markets, real_estate',
        '  input_pattern: snapshot, stock_code, series, search, data_columns, composite',
        '  complexity: 1 (simple) to 4 (pipeline)',
        '  server: server key name',
        '  requires_key: API key env var name (None if not needed)',
        '"""',
        "",
        "",
        "TOOL_METADATA = {",
    ]

    for name in sorted(all_tools.keys()):
        t = all_tools[name]
        key_str = f'"{t["requires_key"]}"' if t["requires_key"] else "None"
        desc_escaped = t["description"].replace('"', '\\"')[:80]
        lines.append(f'    "{name}": {{')
        lines.append(f'        "domain": "{t["domain"]}",')
        lines.append(f'        "input_pattern": "{t["input_pattern"]}",')
        lines.append(f'        "complexity": {t["complexity"]},')
        lines.append(f'        "server": "{t["server"]}",')
        lines.append(f'        "requires_key": {key_str},')
        lines.append(f'        "description": "{desc_escaped}",')
        lines.append(f"    }},")

    lines.append("}")
    lines.append("")

    OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWritten to {OUTPUT_FILE}")

    # Print summary
    from collections import Counter
    domains = Counter(t["domain"] for t in all_tools.values())
    patterns = Counter(t["input_pattern"] for t in all_tools.values())
    complexities = Counter(t["complexity"] for t in all_tools.values())

    print("\n--- Domain Distribution ---")
    for d, c in domains.most_common():
        print(f"  {d}: {c}")

    print("\n--- Input Pattern Distribution ---")
    for p, c in patterns.most_common():
        print(f"  {p}: {c}")

    print("\n--- Complexity Distribution ---")
    for t, c in sorted(complexities.items()):
        print(f"  Tier {t}: {c}")


if __name__ == "__main__":
    main()
