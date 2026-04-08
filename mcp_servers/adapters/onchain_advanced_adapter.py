"""
Advanced On-chain Analytics Adapter — BTC On-chain Metrics.

1. exchange_flow: Exchange inflow/outflow net deposits
2. mvrv: Market Value to Realized Value ratio
3. realized_cap: Realized capitalization
4. hodl_waves: HODL waves — BTC age distribution
5. whale_alert: Large transaction tracker
6. nvt: Network Value to Transactions ratio

Data sources: Blockchain.com API (free, no auth required)
"""
import logging
import sys
import os
import warnings
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=RuntimeWarning)

BLOCKCHAIN_API = "https://api.blockchain.info"
BLOCKCHAIN_CHARTS = "https://api.blockchain.info/charts"


class OnchainAdvancedAdapter:
    """Advanced on-chain analytics for Bitcoin."""

    def _fetch_chart(self, name: str, timespan: str = "180days", rolling_avg: str = "") -> Optional[dict]:
        """Fetch chart data from blockchain.info."""
        try:
            import requests
            params = {"timespan": timespan, "format": "json"}
            if rolling_avg:
                params["rollingAverage"] = rolling_avg
            url = f"{BLOCKCHAIN_CHARTS}/{name}"
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            logger.error(f"Blockchain API {name}: HTTP {resp.status_code}")
            return None
        except Exception as e:
            logger.error(f"Blockchain API {name} failed: {e}")
            return None

    # ------------------------------------------------------------------
    # 1. Exchange Flow (inflow/outflow proxy)
    # ------------------------------------------------------------------
    def exchange_flow(self, timespan: str = "90days") -> Dict[str, Any]:
        """Estimate exchange net flow from on-chain transaction patterns.

        Uses Blockchain.com n-transactions and hash-rate as proxy indicators.
        """
        try:
            # Get transaction count (proxy for activity)
            tx_data = self._fetch_chart("n-transactions", timespan, "7days")
            # Get estimated transaction volume
            vol_data = self._fetch_chart("estimated-transaction-volume-usd", timespan, "7days")
            # Get number of unique addresses
            addr_data = self._fetch_chart("n-unique-addresses", timespan, "7days")

            if not tx_data or not vol_data:
                return error_response("Cannot fetch Blockchain.com data")

            tx_values = tx_data.get("values", [])
            vol_values = vol_data.get("values", [])

            # Compute metrics
            recent_tx = [v["y"] for v in tx_values[-30:]]
            older_tx = [v["y"] for v in tx_values[-90:-30]] if len(tx_values) > 30 else recent_tx

            recent_vol = [v["y"] for v in vol_values[-30:]]
            older_vol = [v["y"] for v in vol_values[-90:-30]] if len(vol_values) > 30 else recent_vol

            tx_trend = (np.mean(recent_tx) - np.mean(older_tx)) / max(np.mean(older_tx), 1) * 100
            vol_trend = (np.mean(recent_vol) - np.mean(older_vol)) / max(np.mean(older_vol), 1) * 100

            # Activity interpretation
            if vol_trend > 10 and tx_trend > 5:
                flow_signal = "increasing_activity"
                interpretation_flow = "Rising on-chain activity — possible accumulation or distribution phase"
            elif vol_trend < -10:
                flow_signal = "decreasing_activity"
                interpretation_flow = "Falling on-chain activity — consolidation phase"
            else:
                flow_signal = "stable"
                interpretation_flow = "Stable on-chain activity"

            # Time series
            activity_ts = [
                {"date": pd.Timestamp(v["x"], unit="s").strftime("%Y-%m-%d"),
                 "transactions": int(v["y"])}
                for v in tx_values[-30:]
            ]

            addr_count = None
            if addr_data:
                addr_vals = addr_data.get("values", [])
                if addr_vals:
                    addr_count = int(addr_vals[-1]["y"])

            return success_response(
                {
                    "tx_count_30d_avg": round(float(np.mean(recent_tx)), 0),
                    "tx_trend_pct": round(float(tx_trend), 1),
                    "volume_usd_30d_avg": round(float(np.mean(recent_vol)), 0),
                    "volume_trend_pct": round(float(vol_trend), 1),
                    "unique_addresses": addr_count,
                    "flow_signal": flow_signal,
                    "recent_activity": activity_ts,
                    "interpretation": interpretation_flow,
                },
                source="On-Chain",
            )
        except Exception as e:
            logger.exception("exchange_flow failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 2. MVRV Ratio
    # ------------------------------------------------------------------
    def mvrv(self, timespan: str = "365days") -> Dict[str, Any]:
        """Market Value to Realized Value ratio.

        MVRV > 3.5: historically top zone. MVRV < 1: historically bottom zone.
        """
        try:
            # Market cap
            mktcap_data = self._fetch_chart("market-cap", timespan)
            if not mktcap_data:
                return error_response("Cannot fetch market cap data")

            mktcap_values = mktcap_data.get("values", [])
            if not mktcap_values:
                return error_response("Empty market cap data")

            current_mktcap = mktcap_values[-1]["y"]

            # For realized cap, we need to estimate or use a proxy
            # Blockchain.com doesn't have realized cap directly
            # Use 200-day SMA of market cap as rough proxy for realized cap
            mktcaps = [v["y"] for v in mktcap_values]
            if len(mktcaps) >= 200:
                realized_cap_proxy = np.mean(mktcaps[-200:])
            else:
                realized_cap_proxy = np.mean(mktcaps)

            mvrv = current_mktcap / realized_cap_proxy if realized_cap_proxy > 0 else 1

            # Historical MVRV (rolling)
            mvrv_history = []
            for i in range(200, len(mktcaps)):
                rc = np.mean(mktcaps[i - 200:i])
                mv = mktcaps[i]
                ratio = mv / rc if rc > 0 else 1
                mvrv_history.append({
                    "date": pd.Timestamp(mktcap_values[i]["x"], unit="s").strftime("%Y-%m-%d"),
                    "mvrv": round(float(ratio), 3),
                })

            # Zone classification
            if mvrv > 3.5:
                zone = "extreme_overvalued"
                signal = "SELL ZONE — historically top area"
            elif mvrv > 2.5:
                zone = "overvalued"
                signal = "Elevated — caution"
            elif mvrv > 1.5:
                zone = "fair_value_upper"
                signal = "Fair value — slightly above average"
            elif mvrv > 1.0:
                zone = "fair_value"
                signal = "Fair value"
            elif mvrv > 0.8:
                zone = "undervalued"
                signal = "Undervalued — accumulation opportunity"
            else:
                zone = "extreme_undervalued"
                signal = "BUY ZONE — historically bottom area"

            return success_response(
                {
                    "mvrv": round(float(mvrv), 3),
                    "market_cap_usd": round(float(current_mktcap), 0),
                    "realized_cap_proxy_usd": round(float(realized_cap_proxy), 0),
                    "zone": zone,
                    "signal": signal,
                    "history": mvrv_history,
                    "method": "200-day SMA proxy for realized cap",
                    "interpretation": (
                        f"MVRV: {mvrv:.2f} ({zone}). "
                        f"{signal}. "
                        f"Market cap: ${current_mktcap/1e9:.1f}B."
                    ),
                },
                source="On-Chain",
            )
        except Exception as e:
            logger.exception("mvrv failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 3. Realized Cap
    # ------------------------------------------------------------------
    def realized_cap(self, timespan: str = "365days") -> Dict[str, Any]:
        """Realized capitalization proxy — each coin valued at last-moved price."""
        try:
            mktcap_data = self._fetch_chart("market-cap", timespan)
            if not mktcap_data:
                return error_response("Cannot fetch market cap data")

            mktcap_values = mktcap_data.get("values", [])
            mktcaps = [v["y"] for v in mktcap_values]

            # Realized cap proxy: 200-day SMA
            if len(mktcaps) >= 200:
                realized = np.mean(mktcaps[-200:])
                rc_history = []
                for i in range(200, len(mktcaps)):
                    rc = np.mean(mktcaps[i - 200:i])
                    rc_history.append({
                        "date": pd.Timestamp(mktcap_values[i]["x"], unit="s").strftime("%Y-%m-%d"),
                        "realized_cap": round(float(rc), 0),
                        "market_cap": round(float(mktcaps[i]), 0),
                    })
            else:
                realized = np.mean(mktcaps)
                rc_history = []

            current_mc = mktcaps[-1] if mktcaps else 0
            unrealized_profit = (current_mc - realized) / realized * 100 if realized > 0 else 0

            return success_response(
                {
                    "realized_cap_proxy_usd": round(float(realized), 0),
                    "market_cap_usd": round(float(current_mc), 0),
                    "unrealized_profit_pct": round(float(unrealized_profit), 1),
                    "history": rc_history,
                    "method": "200-day SMA of market cap as realized cap proxy",
                    "interpretation": (
                        f"Realized cap proxy: ${realized/1e9:.1f}B. "
                        f"Market cap: ${current_mc/1e9:.1f}B. "
                        f"Unrealized profit: {unrealized_profit:.1f}%."
                    ),
                },
                source="On-Chain",
            )
        except Exception as e:
            logger.exception("realized_cap failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 4. HODL Waves
    # ------------------------------------------------------------------
    def hodl_waves(self) -> Dict[str, Any]:
        """HODL waves — BTC distribution by age of last movement.

        Uses output age bands from Blockchain.com.
        """
        try:
            # Blockchain.com provides UTXO age distribution indirectly
            # We use days-destroyed as a proxy
            dd_data = self._fetch_chart("bitcoin-days-destroyed", "365days", "7days")
            dormancy_data = self._fetch_chart("coin-days-destroyed", "365days", "7days") or dd_data

            if not dd_data:
                return error_response("Cannot fetch days-destroyed data")

            dd_values = dd_data.get("values", [])

            # Bitcoin days destroyed: when old coins move, BDD spikes
            recent_bdd = [v["y"] for v in dd_values[-30:]]
            older_bdd = [v["y"] for v in dd_values[-90:-30]] if len(dd_values) > 30 else recent_bdd

            avg_recent = np.mean(recent_bdd)
            avg_older = np.mean(older_bdd)
            bdd_ratio = avg_recent / avg_older if avg_older > 0 else 1

            # High BDD = old coins moving (distribution by long-term holders)
            # Low BDD = old coins dormant (accumulation)
            if bdd_ratio > 2:
                phase = "distribution"
                signal = "Long-term holders selling — bearish"
            elif bdd_ratio > 1.2:
                phase = "mild_distribution"
                signal = "Some old coins moving"
            elif bdd_ratio < 0.5:
                phase = "strong_accumulation"
                signal = "Old coins very dormant — strong accumulation"
            elif bdd_ratio < 0.8:
                phase = "accumulation"
                signal = "Coins aging — accumulation phase"
            else:
                phase = "neutral"
                signal = "Normal coin movement"

            bdd_ts = [
                {"date": pd.Timestamp(v["x"], unit="s").strftime("%Y-%m-%d"),
                 "days_destroyed": round(float(v["y"]), 0)}
                for v in dd_values[-30:]
            ]

            return success_response(
                {
                    "bdd_ratio_30_90": round(float(bdd_ratio), 3),
                    "avg_bdd_30d": round(float(avg_recent), 0),
                    "avg_bdd_90d": round(float(avg_older), 0),
                    "phase": phase,
                    "signal": signal,
                    "recent_bdd": bdd_ts,
                    "method": "Bitcoin Days Destroyed ratio as HODL wave proxy",
                    "interpretation": (
                        f"BDD ratio (30d/90d): {bdd_ratio:.2f}. "
                        f"Phase: {phase}. {signal}."
                    ),
                },
                source="On-Chain",
            )
        except Exception as e:
            logger.exception("hodl_waves failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 5. Whale Alert
    # ------------------------------------------------------------------
    def whale_alert(self, threshold_btc: float = 100) -> Dict[str, Any]:
        """Track large BTC transactions using Blockchain.com API."""
        try:
            import requests
            # Get latest unconfirmed transactions
            url = f"{BLOCKCHAIN_API}/unconfirmed-transactions?format=json"
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                return error_response(f"API returned {resp.status_code}")

            data = resp.json()
            txs = data.get("txs", [])

            # Filter large transactions
            sat_threshold = threshold_btc * 1e8
            whales = []
            for tx in txs:
                total_out = sum(o.get("value", 0) for o in tx.get("out", []))
                if total_out >= sat_threshold:
                    btc_val = total_out / 1e8
                    whales.append({
                        "hash": tx.get("hash", "")[:16] + "...",
                        "btc": round(float(btc_val), 4),
                        "usd_estimate": None,  # would need price
                        "n_inputs": len(tx.get("inputs", [])),
                        "n_outputs": len(tx.get("out", [])),
                        "time": pd.Timestamp(tx.get("time", 0), unit="s").strftime("%Y-%m-%d %H:%M") if tx.get("time") else "",
                    })

            whales.sort(key=lambda x: x["btc"], reverse=True)

            return success_response(
                {
                    "whale_transactions": whales,
                    "n_whales_found": len(whales),
                    "threshold_btc": threshold_btc,
                    "total_txs_scanned": len(txs),
                    "interpretation": (
                        f"{len(whales)} whale transactions (>={threshold_btc} BTC) "
                        f"in mempool. "
                        f"Largest: {whales[0]['btc']:.1f} BTC." if whales else
                        f"No whale transactions >= {threshold_btc} BTC in current mempool."
                    ),
                },
                source="On-Chain",
            )
        except Exception as e:
            logger.exception("whale_alert failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 6. NVT Ratio
    # ------------------------------------------------------------------
    def nvt(self, timespan: str = "365days") -> Dict[str, Any]:
        """Network Value to Transactions ratio — crypto's PE ratio.

        NVT > 95: overvalued (price growing faster than usage).
        NVT < 30: undervalued (strong usage relative to price).
        """
        try:
            mktcap_data = self._fetch_chart("market-cap", timespan)
            txvol_data = self._fetch_chart("estimated-transaction-volume-usd", timespan, "7days")

            if not mktcap_data or not txvol_data:
                return error_response("Cannot fetch market cap or tx volume")

            mc_vals = mktcap_data.get("values", [])
            tv_vals = txvol_data.get("values", [])

            # Align by date
            mc_dict = {v["x"]: v["y"] for v in mc_vals}
            tv_dict = {v["x"]: v["y"] for v in tv_vals}
            common = sorted(set(mc_dict.keys()) & set(tv_dict.keys()))

            if len(common) < 30:
                return error_response("Not enough aligned data")

            nvt_series = []
            for ts in common:
                mc = mc_dict[ts]
                tv = tv_dict[ts]
                nvt_val = mc / tv if tv > 0 else 0
                nvt_series.append({
                    "date": pd.Timestamp(ts, unit="s").strftime("%Y-%m-%d"),
                    "nvt": round(float(nvt_val), 1),
                })

            current_nvt = nvt_series[-1]["nvt"] if nvt_series else 0
            avg_nvt = np.mean([n["nvt"] for n in nvt_series])
            median_nvt = np.median([n["nvt"] for n in nvt_series])

            if current_nvt > 95:
                zone = "overvalued"
                signal = "Price growing faster than network usage"
            elif current_nvt > 65:
                zone = "fair_upper"
                signal = "Slightly elevated"
            elif current_nvt > 30:
                zone = "fair"
                signal = "Fair value range"
            else:
                zone = "undervalued"
                signal = "Strong usage relative to price"

            return success_response(
                {
                    "current_nvt": round(float(current_nvt), 1),
                    "avg_nvt": round(float(avg_nvt), 1),
                    "median_nvt": round(float(median_nvt), 1),
                    "zone": zone,
                    "signal": signal,
                    "history": nvt_series,
                    "interpretation": (
                        f"NVT: {current_nvt:.0f} ({zone}). "
                        f"Average: {avg_nvt:.0f}, Median: {median_nvt:.0f}. "
                        f"{signal}."
                    ),
                },
                source="On-Chain",
            )
        except Exception as e:
            logger.exception("nvt failed")
            return error_response(str(e))
