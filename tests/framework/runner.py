"""
Async test runner for Nexus Finance MCP tool verification.
Runs all tools with rate-limited parallelism and timeout handling.
"""
import asyncio
import importlib
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)

MISSING = type('MISSING', (), {'__repr__': lambda self: 'MISSING', '__bool__': lambda self: False})()


@dataclass
class ToolTestResult:
    tool_name: str
    server: str
    tier: int
    status: str  # PASS, SOFT_PASS, EXPECTED_FAIL, FAIL, TIMEOUT, SKIP
    response_time_ms: float = 0.0
    error_message: Optional[str] = None
    response_preview: Optional[str] = None
    timestamp: str = ""

    def to_dict(self):
        return asdict(self)


# Rate limit concurrency per service group
SERVICE_CONCURRENCY = {
    "dart": 3, "ecos": 2, "kosis": 2, "edinet": 1, "sec": 2,
    "crypto": 5, "defi": 5, "news": 3, "energy": 3,
    # Computation servers: high concurrency (no API calls)
    "advanced_math": 10, "factor_engine": 10, "portfolio_optimizer": 10,
    "portfolio_advanced": 10, "quant_analysis": 10, "technical": 10,
    "timeseries": 10, "volatility_model": 10, "stochvol": 10,
    "signal_lab": 10, "stat_arb": 10, "microstructure": 10,
    "backtest": 10, "alpha_research": 10, "viz": 10,
    "ontology": 10, "valuation": 10, "ml_pipeline": 10,
    "crypto_quant": 10,
}
DEFAULT_CONCURRENCY = 5


class AsyncTestRunner:
    """Run tool verification tests with async parallelism."""

    def __init__(self, max_parallel: int = 10, timeout: float = 30.0):
        self.max_parallel = max_parallel
        self.timeout = timeout
        self.results: List[ToolTestResult] = []
        self.completed = 0
        self.total = 0
        self._server_instances = {}
        self._start_time = 0.0

    async def run_all(self, registry: Dict[str, dict]) -> List[ToolTestResult]:
        """Run all tools in the registry."""
        from tests.framework.param_inference import infer_test_args
        from tests.framework.classifier import classify_result, TestStatus

        self.total = len(registry)
        self.completed = 0
        self._start_time = time.monotonic()

        # Group tools by server
        by_server: Dict[str, list] = {}
        for tool_name, spec in registry.items():
            server = spec.get("server", "unknown")
            by_server.setdefault(server, []).append((tool_name, spec))

        # Create per-service semaphores
        service_semas = {}
        for server_key in by_server:
            concurrency = SERVICE_CONCURRENCY.get(server_key, DEFAULT_CONCURRENCY)
            service_semas[server_key] = asyncio.Semaphore(concurrency)

        # Global concurrency limiter
        global_sema = asyncio.Semaphore(self.max_parallel)

        # Build tasks
        tasks = []
        for server_key, tools in by_server.items():
            for tool_name, spec in tools:
                # Infer test arguments
                kwargs = infer_test_args(spec)
                tasks.append(
                    self._run_one(
                        tool_name, spec, kwargs,
                        service_semas[server_key], global_sema,
                        classify_result, TestStatus,
                    )
                )

        # Execute all
        self.results = await asyncio.gather(*tasks)
        return self.results

    async def _run_one(
        self, tool_name, spec, kwargs,
        service_sema, global_sema,
        classify_result, TestStatus,
    ) -> ToolTestResult:
        """Run a single tool test."""
        server = spec.get("server", "unknown")
        tier = spec.get("tier", 0)
        requires_key = spec.get("requires_key")

        # Check if API key is available
        if requires_key and not os.environ.get(requires_key, ""):
            self.completed += 1
            self._print_progress(tool_name, "EXPECTED_FAIL")
            return ToolTestResult(
                tool_name=tool_name, server=server, tier=tier,
                status="EXPECTED_FAIL", response_time_ms=0,
                error_message=f"Missing env var: {requires_key}",
                timestamp=datetime.utcnow().isoformat(),
            )

        async with global_sema:
            async with service_sema:
                start = time.monotonic()
                try:
                    # Run tool with timeout
                    result = await asyncio.wait_for(
                        asyncio.to_thread(self._invoke_tool, tool_name, spec, kwargs),
                        timeout=self.timeout,
                    )
                    elapsed_ms = (time.monotonic() - start) * 1000

                    status = classify_result(result)
                    status_str = status.value

                    self.completed += 1
                    self._print_progress(tool_name, status_str)

                    return ToolTestResult(
                        tool_name=tool_name, server=server, tier=tier,
                        status=status_str, response_time_ms=round(elapsed_ms, 1),
                        error_message=result.get("message") if isinstance(result, dict) and result.get("error") else None,
                        response_preview=str(result)[:200] if result else None,
                        timestamp=datetime.utcnow().isoformat(),
                    )

                except asyncio.TimeoutError:
                    elapsed_ms = (time.monotonic() - start) * 1000
                    self.completed += 1
                    self._print_progress(tool_name, "TIMEOUT")
                    return ToolTestResult(
                        tool_name=tool_name, server=server, tier=tier,
                        status="TIMEOUT", response_time_ms=round(elapsed_ms, 1),
                        error_message=f"Timed out after {self.timeout}s",
                        timestamp=datetime.utcnow().isoformat(),
                    )

                except Exception as e:
                    elapsed_ms = (time.monotonic() - start) * 1000
                    self.completed += 1
                    self._print_progress(tool_name, "FAIL")
                    return ToolTestResult(
                        tool_name=tool_name, server=server, tier=tier,
                        status="FAIL", response_time_ms=round(elapsed_ms, 1),
                        error_message=str(e)[:500],
                        timestamp=datetime.utcnow().isoformat(),
                    )

    def _invoke_tool(self, tool_name: str, spec: dict, kwargs: dict) -> Any:
        """Invoke a tool by importing and calling it directly via FastMCP get_tool()."""
        server_key = spec.get("server", "")

        # Map server key to module path and class name
        server_map = self._get_server_map()
        if server_key not in server_map:
            return {"error": True, "message": f"Unknown server: {server_key}"}

        mod_path, cls_name = server_map[server_key]

        # Get or create server instance (cached)
        if server_key not in self._server_instances:
            try:
                mod = importlib.import_module(mod_path)
                cls = getattr(mod, cls_name)
                self._server_instances[server_key] = cls()
            except Exception as e:
                return {"error": True, "message": f"Failed to init {cls_name}: {e}"}

        instance = self._server_instances[server_key]

        # Get mcp instance
        mcp = instance.mcp if hasattr(instance, 'mcp') else None
        if mcp is None:
            return {"error": True, "message": f"Server {server_key} has no mcp instance"}

        # FastMCP 3.x: get_tool() is async, returns FunctionTool with .fn attribute
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            tool = loop.run_until_complete(mcp.get_tool(tool_name))
            loop.close()
        except Exception as e:
            return {"error": True, "message": f"Tool {tool_name} not found: {e}"}

        if tool is None:
            return {"error": True, "message": f"Tool {tool_name} not found on server {server_key}"}

        # Get the underlying function
        tool_fn = getattr(tool, 'fn', None)
        if tool_fn is None:
            return {"error": True, "message": f"Tool {tool_name} has no callable fn"}

        # Call the tool function
        try:
            result = tool_fn(**kwargs)
            if result is None:
                return {"success": True, "data": None}
            return result
        except TypeError as e:
            # Parameter mismatch - try with no args (snapshot tools)
            try:
                result = tool_fn()
                return result if result else {"success": True, "data": None}
            except Exception:
                pass
            return {"error": True, "message": f"TypeError: {e}"}

    def _get_server_map(self) -> Dict[str, tuple]:
        """Auto-generate server map from server files (matches scanner's naming)."""
        if hasattr(self, '_cached_server_map'):
            return self._cached_server_map

        import glob
        server_dir = PROJECT_ROOT / "mcp_servers" / "servers"
        result = {}
        for fpath in sorted(server_dir.glob("*_server.py")):
            fname = fpath.stem  # e.g. "crypto_exchange_server"
            server_key = fname.replace("_server", "")  # e.g. "crypto_exchange"
            mod_path = f"mcp_servers.servers.{fname}"

            # Extract class name from file (find class that ends with Server)
            import ast
            try:
                tree = ast.parse(fpath.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name.endswith("Server"):
                        result[server_key] = (mod_path, node.name)
                        break
            except Exception:
                pass

        self._cached_server_map = result
        return result

    def _print_progress(self, tool_name: str, status: str):
        """Print progress indicator."""
        elapsed = time.monotonic() - self._start_time
        pct = (self.completed / self.total * 100) if self.total > 0 else 0

        # Status emoji
        icons = {
            "PASS": "+", "SOFT_PASS": "~", "EXPECTED_FAIL": "?",
            "FAIL": "X", "TIMEOUT": "!", "SKIP": "-",
        }
        icon = icons.get(status, "?")

        print(
            f"\r  [{self.completed}/{self.total}] {pct:5.1f}% "
            f"| {elapsed:.0f}s | [{icon}] {tool_name:<40}",
            end="", flush=True,
        )
