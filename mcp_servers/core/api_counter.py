"""
API Call Counter — tracks tool invocations for monitoring and cost control.
Thread-safe, persists counts to disk daily.
"""
import json
import logging
import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

COUNTER_DIR = Path(__file__).parent.parent.parent / "output" / "api_logs"
COUNTER_DIR.mkdir(parents=True, exist_ok=True)


class APICounter:
    """Tracks API call counts by tool name, with daily file persistence."""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._counts = defaultdict(int)  # tool_name -> count
        self._daily_counts = defaultdict(lambda: defaultdict(int))  # date -> tool_name -> count
        self._total_calls = 0
        self._start_time = time.time()
        self._lock = Lock()
        self._today = datetime.now().strftime("%Y-%m-%d")
        self._load_today()
        self._initialized = True

    def record(self, tool_name: str) -> None:
        """Record a tool invocation."""
        with self._lock:
            today = datetime.now().strftime("%Y-%m-%d")
            if today != self._today:
                self._save_daily()
                self._today = today
                self._counts = defaultdict(int)
            self._counts[tool_name] += 1
            self._daily_counts[today][tool_name] += 1
            self._total_calls += 1

            # Auto-save every 100 calls
            if self._total_calls % 100 == 0:
                self._save_daily()

    def get_stats(self) -> dict:
        """Get current statistics."""
        with self._lock:
            uptime = int(time.time() - self._start_time)
            top_tools = sorted(self._counts.items(), key=lambda x: x[1], reverse=True)[:20]
            return {
                "today": self._today,
                "total_calls_today": sum(self._counts.values()),
                "total_calls_session": self._total_calls,
                "unique_tools_used": len(self._counts),
                "uptime_seconds": uptime,
                "top_tools": [{"tool": k, "calls": v} for k, v in top_tools],
            }

    def _save_daily(self) -> None:
        """Save today's counts to disk."""
        try:
            path = COUNTER_DIR / f"api_calls_{self._today}.json"
            data = dict(self._counts)
            data["_total"] = sum(self._counts.values())
            data["_timestamp"] = datetime.now().isoformat()
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"Failed to save API counter: {e}")

    def _load_today(self) -> None:
        """Load today's counts from disk if exists."""
        try:
            path = COUNTER_DIR / f"api_calls_{self._today}.json"
            if path.exists():
                data = json.loads(path.read_text())
                for k, v in data.items():
                    if not k.startswith("_") and isinstance(v, int):
                        self._counts[k] = v
                self._total_calls = data.get("_total", 0)
        except Exception:
            pass


def get_counter() -> APICounter:
    """Get singleton API counter instance."""
    return APICounter()
