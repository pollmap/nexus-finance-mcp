"""
Enhanced AST Scanner for Nexus Finance MCP test framework.

Scans all mcp_servers/servers/*_server.py files and extracts tool metadata
including full parameter signatures (types, defaults, required flags),
API key requirements, and tier classification.

Usage:
    from tests.framework.scanner import scan_all_servers, MISSING
    tools = scan_all_servers()
"""
import ast
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
SERVERS_DIR = PROJECT_ROOT / "mcp_servers" / "servers"

# Sentinel for parameters with no default value
MISSING = object()

# Known API key environment variables per server
SERVER_API_KEYS: Dict[str, str] = {
    "dart": "DART_API_KEY",
    "ecos": "BOK_ECOS_API_KEY",
    "kosis": "KOSIS_API_KEY",
    "stocks": "FINNHUB_API_KEY",
    "onchain": "ETHERSCAN_API_KEY",
    "news": "NAVER_CLIENT_ID",
    "energy": "EIA_API_KEY",
    "edinet": "EDINET_API_KEY",
    "realestate_trans": "MOLIT_API_KEY",
    "fsc": "MOLIT_API_KEY",
}

# Tier 1: Pure computation servers (no external API calls)
TIER1_SERVERS = frozenset({
    "advanced_math", "factor_engine", "portfolio_optimizer",
    "portfolio_advanced", "quant_analysis", "technical",
    "timeseries", "volatility_model", "stochvol", "signal_lab",
    "stat_arb", "microstructure", "backtest", "alpha_research",
    "viz", "ontology", "valuation",
})


def _annotation_to_str(node: Optional[ast.AST]) -> str:
    """Convert an AST annotation node to a readable string.

    Handles:
      - str, int, float, bool, list, dict -> simple name
      - Optional[X] -> "Optional[X]"
      - List[dict], Dict[str, Any] -> string repr
      - No annotation (None) -> "Any"
    """
    if node is None:
        return "Any"

    # Simple name: str, int, float, bool, list, dict, Any
    if isinstance(node, ast.Name):
        return node.id

    # Attribute access: e.g. typing.Optional
    if isinstance(node, ast.Attribute):
        return node.attr

    # Constant (Python 3.8+ for string annotations stored as constants)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value

    # Subscript: Optional[X], List[X], Dict[X, Y]
    if isinstance(node, ast.Subscript):
        base = _annotation_to_str(node.value)
        slice_node = node.slice

        # Handle Tuple slices like Dict[str, Any]
        if isinstance(slice_node, ast.Tuple):
            parts = [_annotation_to_str(el) for el in slice_node.elts]
            return f"{base}[{', '.join(parts)}]"
        else:
            inner = _annotation_to_str(slice_node)
            return f"{base}[{inner}]"

    # Fallback: use ast.dump as string repr
    try:
        return ast.unparse(node)
    except AttributeError:
        return "Any"


def _is_optional(annotation_str: str) -> bool:
    """Check if annotation string represents an Optional type."""
    return annotation_str.startswith("Optional[")


def _extract_default(node: ast.AST) -> Any:
    """Extract a default value from an AST node.

    Returns the Python value for simple literals, or MISSING if unparseable.
    """
    if node is None:
        return MISSING

    # ast.Constant covers str, int, float, bool, None in Python 3.8+
    if isinstance(node, ast.Constant):
        return node.value

    # ast.NameConstant (Python 3.7 compat) for True/False/None
    if isinstance(node, ast.NameConstant):
        return node.value

    # ast.Num / ast.Str (Python 3.7 compat)
    if isinstance(node, ast.Num):
        return node.n
    if isinstance(node, ast.Str):
        return node.s

    # Unary operator: negative numbers like -1, -0.5
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = _extract_default(node.operand)
        if inner is not MISSING and isinstance(inner, (int, float)):
            return -inner

    # ast.List / ast.Dict for empty defaults [] / {}
    if isinstance(node, ast.List) and len(node.elts) == 0:
        return []
    if isinstance(node, ast.Dict) and len(node.keys) == 0:
        return {}

    # Name references like None
    if isinstance(node, ast.Name) and node.id == "None":
        return None

    # Try literal_eval on the unparsed string as last resort
    try:
        source = ast.unparse(node)
        return ast.literal_eval(source)
    except Exception:
        # Return the string representation as a fallback
        try:
            return ast.unparse(node)
        except Exception:
            return MISSING


def _extract_params(func_node: ast.FunctionDef) -> List[Dict[str, Any]]:
    """Extract parameter metadata from a function definition.

    Handles right-alignment of defaults to args (Python semantics):
    if there are N args and M defaults, defaults align to the last M args.
    """
    args_node = func_node.args
    all_args = args_node.args  # list of ast.arg

    # Skip 'self' if present (shouldn't be in nested tool functions, but safety)
    arg_list = [a for a in all_args if a.arg != "self"]

    defaults = args_node.defaults  # right-aligned to args
    num_args = len(arg_list)
    num_defaults = len(defaults)
    # Pad defaults with None on the left so indexing aligns
    padded_defaults = [None] * (num_args - num_defaults) + list(defaults)

    params = []
    for i, arg in enumerate(arg_list):
        annotation_str = _annotation_to_str(arg.annotation)
        default_node = padded_defaults[i]

        if default_node is not None:
            default_val = _extract_default(default_node)
        else:
            default_val = MISSING

        # Determine required flag
        if default_val is not MISSING:
            required = False
        elif _is_optional(annotation_str):
            # Optional[X] with no explicit default -> treat as required=False, default=None
            required = False
            default_val = None
        else:
            required = True

        params.append({
            "name": arg.arg,
            "type": annotation_str,
            "default": default_val,
            "required": required,
        })

    return params


def _is_mcp_tool_decorator(dec: ast.AST) -> bool:
    """Check if a decorator is @self.mcp.tool() or similar."""
    dec_str = ast.dump(dec)
    return "mcp" in dec_str and "tool" in dec_str


def extract_tools_from_file(filepath: Path) -> List[Dict[str, Any]]:
    """Extract all @self.mcp.tool() decorated functions from a server file.

    Returns a list of tool metadata dicts.
    """
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"  WARNING: Failed to parse {filepath.name}: {e}")
        return []

    server_name = filepath.stem.replace("_server", "")
    requires_key = SERVER_API_KEYS.get(server_name)

    # Classify tier
    if server_name in TIER1_SERVERS:
        tier = 1
    elif requires_key is not None:
        tier = 3
    else:
        tier = 2

    tools = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        is_tool = any(_is_mcp_tool_decorator(dec) for dec in node.decorator_list)
        if not is_tool:
            continue

        # Extract docstring first line
        docstring = ast.get_docstring(node) or ""
        description = docstring.split("\n")[0].strip() if docstring else ""

        params = _extract_params(node)

        tools.append({
            "name": node.name,
            "server": server_name,
            "description": description,
            "params": params,
            "requires_key": requires_key,
            "tier": tier,
        })

    return tools


def scan_all_servers() -> Dict[str, Dict[str, Any]]:
    """Scan all server files and return a dict of tool metadata.

    Returns:
        Dict keyed by tool name, each value containing:
          - server: str
          - description: str
          - params: list of param dicts (name, type, default, required)
          - requires_key: Optional[str] - env var name or None
          - tier: int (1=computation, 2=free API, 3=API key required)
    """
    if not SERVERS_DIR.exists():
        raise FileNotFoundError(f"Servers directory not found: {SERVERS_DIR}")

    all_tools: Dict[str, Dict[str, Any]] = {}
    server_files = sorted(SERVERS_DIR.glob("*_server.py"))

    for sf in server_files:
        tools = extract_tools_from_file(sf)
        for t in tools:
            all_tools[t["name"]] = t

    return all_tools


def scan_summary() -> None:
    """Print a summary of scanned tools (for debugging)."""
    tools = scan_all_servers()
    servers = set(t["server"] for t in tools.values())
    tiers = {1: 0, 2: 0, 3: 0}
    for t in tools.values():
        tiers[t["tier"]] = tiers.get(t["tier"], 0) + 1

    print(f"Scanned {len(tools)} tools across {len(servers)} servers")
    print(f"  Tier 1 (computation): {tiers.get(1, 0)}")
    print(f"  Tier 2 (free API):    {tiers.get(2, 0)}")
    print(f"  Tier 3 (API key):     {tiers.get(3, 0)}")


if __name__ == "__main__":
    scan_summary()
