# Contributing to Nexus Finance MCP

## Project Structure

```
mcp_servers/
├── gateway/
│   └── gateway_server.py      # Single entry point — mounts all 64 servers
├── servers/                    # 64 server files (one per domain)
│   ├── ecos_server.py
│   ├── dart_server.py
│   └── ...
├── adapters/                   # 60 adapter files (HTTP client wrappers)
│   ├── ecos_adapter.py
│   ├── ccxt_adapter.py
│   └── ...
└── core/                       # Shared infrastructure
    ├── base_server.py          # BaseMCPServer ABC + decorators
    ├── cache_manager.py        # 3-tier caching (LRU → TTL → Disk)
    ├── rate_limiter.py         # Token bucket rate limiter
    ├── api_counter.py          # Daily API call tracking
    └── responses.py            # Response helpers (currently unused)
```

---

## Adding a New Server

### Step 1: Create the Adapter

Adapters wrap external APIs. Create `mcp_servers/adapters/your_adapter.py`:

```python
import httpx
import logging

logger = logging.getLogger(__name__)

class YourAdapter:
    BASE_URL = "https://api.example.com"

    def __init__(self):
        self._client = httpx.Client(timeout=30.0)

    def get_data(self, param: str) -> dict:
        try:
            resp = self._client.get(f"{self.BASE_URL}/data/{param}")
            resp.raise_for_status()
            data = resp.json()
            return {"success": True, "data": data, "source": "YourAPI"}
        except httpx.HTTPError as e:
            return {"error": True, "message": f"API error: {e}"}
        except Exception as e:
            return {"error": True, "message": str(e)}
```

### Step 2: Create the Server

Two patterns available:

**Pattern A: BaseMCPServer (recommended for new servers)**

```python
import logging
from mcp_servers.core.base_server import BaseMCPServer
from mcp_servers.adapters.your_adapter import YourAdapter

logger = logging.getLogger(__name__)

class YourServer(BaseMCPServer):
    @property
    def name(self) -> str:
        return "your-domain"

    def _register_tools(self):
        adapter = YourAdapter()

        @self.mcp.tool()
        def your_get_data(param: str = "default") -> dict:
            """
            Short description of what this tool does.

            Args:
                param: Description of parameter

            Returns:
                Data from YourAPI
            """
            return self._cached_request(
                key=f"data:{param}",
                fetch_func=lambda: adapter.get_data(param),
                data_type="daily_data",
            )
```

**Pattern B: Direct FastMCP (simpler, no built-in caching)**

```python
from fastmcp import FastMCP
from mcp_servers.adapters.your_adapter import YourAdapter

class YourServer:
    def __init__(self):
        self._adapter = YourAdapter()
        self.mcp = FastMCP("your-domain")
        self._register_tools()

    def _register_tools(self):
        @self.mcp.tool()
        def your_get_data(param: str = "default") -> dict:
            """Short description."""
            return self._adapter.get_data(param)
```

### Step 3: Register in Gateway

Add to the `SERVERS` list in `mcp_servers/gateway/gateway_server.py`:

```python
SERVERS = [
    # ... existing servers ...
    # Your Phase
    ("your_domain", "mcp_servers.servers.your_server", "YourServer"),
]
```

### Step 4: Test

```bash
# Quick import test
python -c "from mcp_servers.servers.your_server import YourServer; s = YourServer(); print(len(s.mcp._tool_manager._tools))"

# Full server test
python server.py --transport streamable-http --port 8100
# Then call your tool via any MCP client
```

---

## Naming Conventions

### Tool Names

Prefix with the domain:

```
ecos_get_macro_snapshot     # Korean macro
dart_company_info           # Korean disclosures
crypto_ticker               # Crypto
quant_correlation           # Quant analysis
viz_line_chart              # Visualization
```

### Response Format

All tools must return a dict:

```python
# Success
{"success": True, "data": {...}, "source": "API_NAME"}

# Error
{"error": True, "message": "Human-readable error description"}
```

**Rules:**
- Never return mock/sample/fake data
- Always include `"source"` field on success
- Error messages should suggest a fix when possible
- No bare exceptions — catch and wrap with descriptive message

---

## Code Style

- Python 3.12+
- Korean comments in code are acceptable
- Tool docstrings should describe what the tool does (used as MCP description)
- Type hints for tool parameters (affects MCP schema generation)
- No unnecessary dependencies — check if existing adapters already cover the API

---

## Architecture Diagrams

See [docs/DATA_FLOW.md](docs/DATA_FLOW.md) for visual architecture reference.
When adding a server, update the domain tree diagram in DATA_FLOW.md if it introduces a new domain.

---

## Questions?

Open an issue at [github.com/pollmap/nexus-finance-mcp](https://github.com/pollmap/nexus-finance-mcp/issues).
