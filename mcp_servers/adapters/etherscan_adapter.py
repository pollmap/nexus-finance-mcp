"""
Etherscan V2 Adapter — On-chain data (balances, transactions, gas).

Requires: ETHERSCAN_API_KEY (free, 100K calls/day, 5/sec)
Base URL: https://api.etherscan.io/v2/api
"""
import logging
import os
import sys
from pathlib import Path
import requests
from utils.http_client import get_session
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)
_session = get_session("etherscan_adapter")

BASE_URL = "https://api.etherscan.io/v2/api"


class EtherscanAdapter:
    def __init__(self):
        self._api_key = os.getenv("ETHERSCAN_API_KEY", "")
        if not self._api_key:
            logger.warning("ETHERSCAN_API_KEY not set. On-chain tools will return errors.")

    def _call(self, chainid: int = 1, **params) -> Dict[str, Any]:
        """Make Etherscan V2 API call."""
        if not self._api_key:
            return error_response("ETHERSCAN_API_KEY not configured", code="NOT_INITIALIZED")
        try:
            params["apikey"] = self._api_key
            params["chainid"] = chainid
            resp = _session.get(BASE_URL, params=params, timeout=15)
            data = resp.json()
            if data.get("status") == "1" or data.get("message") == "OK":
                return success_response(data.get("result"), source="Etherscan")
            return error_response(data.get("message", "Unknown error"), code="API_UNAVAILABLE")
        except Exception as e:
            return error_response(str(e))

    def get_balance(self, address: str, chainid: int = 1) -> Dict[str, Any]:
        """Get ETH balance for an address."""
        result = self._call(chainid=chainid, module="account", action="balance", address=address, tag="latest")
        if result.get("success"):
            wei = int(result["data"])
            eth = wei / 1e18
            return success_response(None, source="Etherscan", address=address, balance_wei=wei, balance_eth=round(eth, 6))
        return result

    def get_transactions(self, address: str, limit: int = 20, chainid: int = 1) -> Dict[str, Any]:
        """Get recent transactions for an address."""
        result = self._call(
            chainid=chainid, module="account", action="txlist", address=address,
            startblock=0, endblock=99999999, page=1, offset=limit, sort="desc",
        )
        if result.get("success"):
            txns = []
            for tx in result["data"][:limit]:
                txns.append({
                    "hash": tx.get("hash"),
                    "from": tx.get("from"),
                    "to": tx.get("to"),
                    "value_eth": round(int(tx.get("value", 0)) / 1e18, 6),
                    "gas_used": tx.get("gasUsed"),
                    "timestamp": tx.get("timeStamp"),
                })
            return success_response(txns, source="Etherscan", address=address)
        return result

    def get_gas_price(self, chainid: int = 1) -> Dict[str, Any]:
        """Get current gas price."""
        result = self._call(chainid=chainid, module="gastracker", action="gasoracle")
        if result.get("success"):
            r = result["data"]
            return success_response(
                None,
                source="Etherscan",
                safe_gwei=r.get("SafeGasPrice"),
                propose_gwei=r.get("ProposeGasPrice"),
                fast_gwei=r.get("FastGasPrice"),
            )
        return result
