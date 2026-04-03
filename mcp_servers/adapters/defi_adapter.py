"""
DeFi Adapter — DefiLlama (TVL/protocols) + Fear & Greed Index.

Both APIs are completely free, no authentication needed.
"""
import logging
from typing import Any, Dict
from utils.http_client import get_session

logger = logging.getLogger(__name__)
_session = get_session("defi")

DEFILLAMA_BASE = "https://api.llama.fi"
FEARGREED_URL = "https://api.alternative.me/fng/"


class DefiLlamaAdapter:
    """DefiLlama API — DeFi TVL, protocols, stablecoins."""

    def get_protocols(self, limit: int = 30) -> Dict[str, Any]:
        """Get top protocols by TVL."""
        try:
            resp = _session.get(f"{DEFILLAMA_BASE}/protocols", timeout=15)
            resp.raise_for_status()
            data = resp.json()
            protocols = [
                {
                    "name": p.get("name"),
                    "tvl": p.get("tvl"),
                    "chain": p.get("chain"),
                    "category": p.get("category"),
                    "change_1d": p.get("change_1d"),
                    "change_7d": p.get("change_7d"),
                }
                for p in data[:limit]
            ]
            return {"success": True, "count": len(protocols), "data": protocols}
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_protocol(self, slug: str) -> Dict[str, Any]:
        """Get single protocol detail by slug (e.g., 'aave', 'uniswap')."""
        try:
            resp = _session.get(f"{DEFILLAMA_BASE}/protocol/{slug}", timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return {
                "success": True,
                "name": data.get("name"),
                "tvl": data.get("tvl"),
                "chain_tvls": data.get("chainTvls", {}),
                "category": data.get("category"),
                "url": data.get("url"),
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_chains(self) -> Dict[str, Any]:
        """Get TVL by chain."""
        try:
            resp = _session.get(f"{DEFILLAMA_BASE}/v2/chains", timeout=15)
            resp.raise_for_status()
            data = resp.json()
            chains = [
                {"name": c.get("name"), "tvl": c.get("tvl")}
                for c in sorted(data, key=lambda x: -(x.get("tvl") or 0))[:30]
            ]
            return {"success": True, "count": len(chains), "data": chains}
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_stablecoins(self) -> Dict[str, Any]:
        """Get stablecoin market cap data."""
        try:
            resp = _session.get(f"{DEFILLAMA_BASE}/stablecoins", timeout=15)
            resp.raise_for_status()
            data = resp.json()
            stables = []
            for s in data.get("peggedAssets", [])[:20]:
                stables.append({
                    "name": s.get("name"),
                    "symbol": s.get("symbol"),
                    "circulating": s.get("circulating", {}).get("peggedUSD"),
                })
            return {"success": True, "count": len(stables), "data": stables}
        except Exception as e:
            return {"error": True, "message": str(e)}


class FearGreedAdapter:
    """Crypto Fear & Greed Index — alternative.me API."""

    def get_current(self) -> Dict[str, Any]:
        """Get current Fear & Greed value."""
        try:
            resp = _session.get(f"{FEARGREED_URL}?limit=1&date_format=kr", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            entry = data.get("data", [{}])[0]
            return {
                "success": True,
                "value": int(entry.get("value", 0)),
                "classification": entry.get("value_classification"),
                "timestamp": entry.get("timestamp"),
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_history(self, days: int = 30) -> Dict[str, Any]:
        """Get historical Fear & Greed values."""
        try:
            resp = _session.get(f"{FEARGREED_URL}?limit={days}&date_format=kr", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            history = [
                {
                    "value": int(e.get("value", 0)),
                    "classification": e.get("value_classification"),
                    "timestamp": e.get("timestamp"),
                }
                for e in data.get("data", [])
            ]
            return {"success": True, "count": len(history), "data": history}
        except Exception as e:
            return {"error": True, "message": str(e)}
