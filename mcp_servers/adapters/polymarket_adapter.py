"""
Polymarket Adapter — Prediction market data.

Three APIs, all free for read-only:
- Gamma API: Market metadata, events, conditions
- CLOB API: Prices, orderbooks
- Data API: User positions, price history

No authentication needed for read endpoints. ~60 req/min.
"""
import logging
from typing import Any, Dict, Optional
from utils.http_client import get_session

logger = logging.getLogger(__name__)
_session = get_session("polymarket")

GAMMA_URL = "https://gamma-api.polymarket.com"
CLOB_URL = "https://clob.polymarket.com"


class PolymarketAdapter:
    """Polymarket prediction market data."""

    def get_markets(self, limit: int = 20, active: bool = True) -> Dict[str, Any]:
        """Get markets list."""
        try:
            params = {"limit": limit, "active": active, "order": "volume", "ascending": False}
            resp = _session.get(f"{GAMMA_URL}/markets", params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            markets = []
            for m in data[:limit]:
                markets.append({
                    "id": m.get("id"),
                    "condition_id": m.get("conditionId"),
                    "question": m.get("question"),
                    "volume": m.get("volume"),
                    "liquidity": m.get("liquidity"),
                    "end_date": m.get("endDate"),
                    "outcome_prices": m.get("outcomePrices"),
                    "category": m.get("category"),
                })

            return {"success": True, "count": len(markets), "markets": markets}
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_market_detail(self, condition_id: str) -> Dict[str, Any]:
        """Get single market detail by condition ID."""
        try:
            resp = _session.get(f"{GAMMA_URL}/markets/{condition_id}", timeout=15)
            resp.raise_for_status()
            m = resp.json()

            return {
                "success": True,
                "question": m.get("question"),
                "description": m.get("description", "")[:500],
                "volume": m.get("volume"),
                "liquidity": m.get("liquidity"),
                "outcome_prices": m.get("outcomePrices"),
                "outcomes": m.get("outcomes"),
                "end_date": m.get("endDate"),
                "category": m.get("category"),
                "tags": m.get("tags"),
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_events(self, limit: int = 10) -> Dict[str, Any]:
        """Get events (groups of related markets)."""
        try:
            params = {"limit": limit, "active": True, "order": "volume", "ascending": False}
            resp = _session.get(f"{GAMMA_URL}/events", params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            events = []
            for e in data[:limit]:
                events.append({
                    "id": e.get("id"),
                    "title": e.get("title"),
                    "volume": e.get("volume"),
                    "markets_count": len(e.get("markets", [])),
                    "category": e.get("category"),
                })

            return {"success": True, "count": len(events), "events": events}
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_prices(self, token_id: str) -> Dict[str, Any]:
        """Get current price for a market token."""
        try:
            resp = _session.get(f"{CLOB_URL}/price", params={"token_id": token_id}, timeout=10)
            resp.raise_for_status()
            return {"success": True, "token_id": token_id, "price": resp.json()}
        except Exception as e:
            return {"error": True, "message": str(e)}
