"""
Market Microstructure Adapter — Order Flow, Toxicity, Liquidity Metrics.

1. kyle_lambda: Price impact coefficient from order flow regression
2. lee_ready: Trade classification (buyer/seller-initiated)
3. roll_spread: Roll (1984) effective spread estimator
4. amihud: Amihud (2002) illiquidity ratio
5. orderbook_imbalance: Bid-ask volume imbalance at multiple depths
6. toxicity: VPIN (Volume-Synchronized Probability of Informed Trading)

References:
- Kyle (1985), "Continuous Auctions and Insider Trading," Econometrica 53(6)
- Lee & Ready (1991), "Inferring Trade Direction from Intraday Data," J. Finance 46(2)
- Roll (1984), "A Simple Implicit Measure of the Effective Bid-Ask Spread," J. Finance 39(4)
- Amihud (2002), "Illiquidity and Stock Returns," J. Financial Markets 5(1)
- Easley, López de Prado & O'Hara (2012), "Flow Toxicity and Liquidity," J. Finance 67(4)
"""
import logging
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=RuntimeWarning)


class MicrostructureAdapter:
    """Market microstructure analysis tools."""

    # ------------------------------------------------------------------
    # 1. Kyle's Lambda
    # ------------------------------------------------------------------
    def kyle_lambda(
        self, series: List[Dict], window: int = 20,
    ) -> Dict[str, Any]:
        """Estimate Kyle's lambda via OLS: delta_p = c + lambda * signed_volume.

        Higher lambda = more price impact per unit of order flow = less liquid.
        """
        try:
            df = pd.DataFrame(series)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").drop_duplicates("date")
            prices = df["value"].astype(float).values
            n = len(prices)
            if n < 30:
                return error_response(f"Need >= 30 observations, got {n}", code="INVALID_INPUT")

            returns = np.diff(np.log(prices))

            has_volume = "volume" in df.columns
            if has_volume:
                volumes = df["volume"].astype(float).values[1:]
                signed_vol = volumes * np.sign(returns)
            else:
                signed_vol = np.abs(returns) * 1e6 * np.sign(returns)

            nr = len(returns)
            X = np.column_stack([np.ones(nr), signed_vol[:nr]])
            y = returns[:nr]
            coeffs = np.linalg.lstsq(X, y, rcond=None)[0]
            intercept, lam = coeffs[0], coeffs[1]

            predicted = X @ coeffs
            ss_res = np.sum((y - predicted) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_sq = 1 - ss_res / ss_tot if ss_tot > 0 else 0

            # Rolling lambda (last 5 windows)
            rolling_lambdas = []
            for i in range(max(0, nr - 5 * window), nr - window + 1, window):
                w_sv = signed_vol[i:i + window]
                w_ret = returns[i:i + window]
                if len(w_sv) == window:
                    Xw = np.column_stack([np.ones(window), w_sv])
                    cw = np.linalg.lstsq(Xw, w_ret, rcond=None)[0]
                    rolling_lambdas.append(round(float(cw[1]), 8))

            return success_response({
                    "kyle_lambda": round(float(lam), 8),
                    "intercept": round(float(intercept), 8),
                    "r_squared": round(float(r_sq), 4),
                    "rolling_lambdas": rolling_lambdas,
                    "has_volume_data": has_volume,
                    "n_observations": nr,
                    "interpretation": (
                        f"Kyle's λ = {lam:.2e}. "
                        f"{'Positive (expected)' if lam > 0 else 'Negative (unusual)'}. "
                        f"R² = {r_sq:.3f}. "
                        f"{'Low' if abs(lam) < 1e-7 else 'Moderate' if abs(lam) < 1e-5 else 'High'} price impact."
                    ),
                })
        except Exception as e:
            logger.exception("kyle_lambda failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 2. Lee-Ready Trade Classification
    # ------------------------------------------------------------------
    def lee_ready(self, trades: List[Dict]) -> Dict[str, Any]:
        """Classify trades as buyer/seller-initiated using tick test + quote rule.

        Input: [{date, price, bid, ask}] or [{date, value}] (tick test only).
        """
        try:
            df = pd.DataFrame(trades)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").drop_duplicates("date")
            n = len(df)
            if n < 10:
                return error_response(f"Need >= 10 trades, got {n}")

            has_quotes = "bid" in df.columns and "ask" in df.columns

            if has_quotes:
                prices = df["price"].astype(float).values if "price" in df.columns else df["value"].astype(float).values
                bids = df["bid"].astype(float).values
                asks = df["ask"].astype(float).values
                mids = (bids + asks) / 2

                classifications = []
                for i in range(n):
                    if prices[i] > mids[i]:
                        classifications.append(1)   # buyer
                    elif prices[i] < mids[i]:
                        classifications.append(-1)  # seller
                    else:
                        # At midpoint: use tick test
                        if i > 0 and prices[i] > prices[i - 1]:
                            classifications.append(1)
                        elif i > 0 and prices[i] < prices[i - 1]:
                            classifications.append(-1)
                        else:
                            classifications.append(0)  # indeterminate
            else:
                # Tick test only
                prices = df["value"].astype(float).values if "value" in df.columns else df["price"].astype(float).values
                classifications = [0]  # first trade indeterminate
                for i in range(1, n):
                    if prices[i] > prices[i - 1]:
                        classifications.append(1)
                    elif prices[i] < prices[i - 1]:
                        classifications.append(-1)
                    else:
                        classifications.append(classifications[-1])  # repeat last

            cls = np.array(classifications)
            n_buy = int(np.sum(cls == 1))
            n_sell = int(np.sum(cls == -1))
            n_neutral = int(np.sum(cls == 0))

            # Order flow imbalance
            ofi = (n_buy - n_sell) / max(n_buy + n_sell, 1)

            return success_response({
                    "n_buys": n_buy,
                    "n_sells": n_sell,
                    "n_neutral": n_neutral,
                    "buy_pct": round(n_buy / n * 100, 1),
                    "sell_pct": round(n_sell / n * 100, 1),
                    "order_flow_imbalance": round(float(ofi), 4),
                    "method": "quote_rule + tick_test" if has_quotes else "tick_test_only",
                    "n_trades": n,
                    "interpretation": (
                        f"{n_buy} buys ({n_buy/n:.0%}), {n_sell} sells ({n_sell/n:.0%}). "
                        f"OFI = {ofi:.3f} ({'buy pressure' if ofi > 0.1 else 'sell pressure' if ofi < -0.1 else 'balanced'})."
                    ),
                })
        except Exception as e:
            logger.exception("lee_ready failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 3. Roll Effective Spread
    # ------------------------------------------------------------------
    def roll_spread(self, series: List[Dict]) -> Dict[str, Any]:
        """Roll (1984) effective spread from serial covariance of price changes.

        spread = 2 * sqrt(-Cov(dp_t, dp_{t-1}))
        """
        try:
            df = pd.DataFrame(series)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").drop_duplicates("date")
            prices = df["value"].astype(float).values
            n = len(prices)
            if n < 30:
                return error_response(f"Need >= 30 prices, got {n}")

            dp = np.diff(prices)
            autocovar = np.cov(dp[:-1], dp[1:])[0, 1]

            if autocovar >= 0:
                roll_spread = 0.0
                valid = False
            else:
                roll_spread = 2 * np.sqrt(-autocovar)
                valid = True

            # As percentage of average price
            avg_price = np.mean(prices)
            spread_pct = roll_spread / avg_price * 100 if avg_price > 0 else 0

            # Rolling Roll spread (20-day windows)
            window = min(60, n // 3)
            rolling_spreads = []
            for i in range(0, n - window, window):
                w_dp = np.diff(prices[i:i + window])
                w_cov = np.cov(w_dp[:-1], w_dp[1:])[0, 1]
                if w_cov < 0:
                    rolling_spreads.append(round(2 * np.sqrt(-w_cov), 4))
                else:
                    rolling_spreads.append(0.0)

            return success_response({
                    "roll_spread": round(float(roll_spread), 6),
                    "roll_spread_pct": round(float(spread_pct), 4),
                    "serial_covariance": round(float(autocovar), 8),
                    "valid_estimate": valid,
                    "avg_price": round(float(avg_price), 2),
                    "rolling_spreads": rolling_spreads,
                    "n_observations": n,
                    "interpretation": (
                        f"Roll spread: {roll_spread:.4f} ({spread_pct:.3f}% of price). "
                        f"{'Valid' if valid else 'Invalid (positive autocovariance → no bid-ask bounce)'}. "
                        f"{'Very liquid' if spread_pct < 0.05 else 'Liquid' if spread_pct < 0.2 else 'Illiquid' if spread_pct < 1 else 'Very illiquid'}."
                    ),
                })
        except Exception as e:
            logger.exception("roll_spread failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 4. Amihud Illiquidity
    # ------------------------------------------------------------------
    def amihud(self, series: List[Dict]) -> Dict[str, Any]:
        """Amihud (2002) illiquidity ratio: mean(|return| / dollar_volume).

        Higher = more illiquid = more price impact per dollar traded.
        """
        try:
            df = pd.DataFrame(series)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").drop_duplicates("date")
            prices = df["value"].astype(float).values
            n = len(prices)
            if n < 30:
                return error_response(f"Need >= 30 observations, got {n}")

            returns = np.abs(np.diff(np.log(prices)))

            if "volume" in df.columns:
                volumes = df["volume"].astype(float).values[1:]
                dollar_vol = prices[1:] * volumes
                has_volume = True
            else:
                dollar_vol = np.ones(len(returns)) * 1e9  # placeholder
                has_volume = False

            # Amihud ratio
            valid = dollar_vol > 0
            if np.sum(valid) < 10:
                return error_response("Not enough valid volume data")

            daily_illiq = returns[valid] / dollar_vol[valid]
            amihud_ratio = float(np.mean(daily_illiq)) * 1e6  # scale for readability

            # Rolling (monthly)
            window = min(20, n // 3)
            rolling_amihud = []
            for i in range(0, len(returns) - window + 1, window):
                w_ret = returns[i:i + window]
                w_dv = dollar_vol[i:i + window]
                w_valid = w_dv > 0
                if np.sum(w_valid) > 5:
                    val = float(np.mean(w_ret[w_valid] / w_dv[w_valid])) * 1e6
                    rolling_amihud.append(round(val, 6))

            # Percentile ranking
            if len(rolling_amihud) >= 3:
                current_pctile = float(stats.percentileofscore(rolling_amihud, amihud_ratio))
            else:
                current_pctile = 50

            return success_response({
                    "amihud_ratio": round(amihud_ratio, 6),
                    "amihud_percentile": round(current_pctile, 1),
                    "has_volume_data": has_volume,
                    "rolling_amihud": rolling_amihud[-10:],
                    "n_observations": n,
                    "interpretation": (
                        f"Amihud illiquidity: {amihud_ratio:.4f}×10⁻⁶. "
                        f"Percentile: {current_pctile:.0f}%. "
                        f"{'Very liquid' if amihud_ratio < 0.01 else 'Liquid' if amihud_ratio < 0.1 else 'Moderate' if amihud_ratio < 1 else 'Illiquid'}."
                        f"{'' if has_volume else ' (No volume data, using placeholder).'}"
                    ),
                })
        except Exception as e:
            logger.exception("amihud failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 5. Order Book Imbalance
    # ------------------------------------------------------------------
    def orderbook_imbalance(self, orderbook: Dict) -> Dict[str, Any]:
        """Compute order book imbalance at multiple depth levels.

        OBI = (bid_vol - ask_vol) / (bid_vol + ask_vol)
        Positive = buy pressure, Negative = sell pressure.
        """
        try:
            bids = orderbook.get("bids", [])
            asks = orderbook.get("asks", [])

            if not bids or not asks:
                return error_response("Need non-empty bids and asks")

            # Parse: [[price, volume], ...] or [{"price": p, "volume": v}, ...]
            def _parse_levels(levels):
                parsed = []
                for lvl in levels:
                    if isinstance(lvl, (list, tuple)):
                        parsed.append((float(lvl[0]), float(lvl[1])))
                    elif isinstance(lvl, dict):
                        parsed.append((float(lvl.get("price", 0)), float(lvl.get("volume", lvl.get("amount", 0)))))
                return parsed

            bid_levels = _parse_levels(bids)
            ask_levels = _parse_levels(asks)

            # OBI at various depths
            depths = [1, 5, 10, 20]
            imbalances = {}
            for d in depths:
                bid_vol = sum(v for _, v in bid_levels[:d])
                ask_vol = sum(v for _, v in ask_levels[:d])
                total = bid_vol + ask_vol
                obi = (bid_vol - ask_vol) / total if total > 0 else 0
                imbalances[f"depth_{d}"] = {
                    "obi": round(float(obi), 4),
                    "bid_volume": round(bid_vol, 2),
                    "ask_volume": round(ask_vol, 2),
                }

            # Spread
            best_bid = bid_levels[0][0] if bid_levels else 0
            best_ask = ask_levels[0][0] if ask_levels else 0
            spread = best_ask - best_bid
            mid = (best_bid + best_ask) / 2 if (best_bid + best_ask) > 0 else 1
            spread_bps = spread / mid * 10000

            # Depth-weighted mid price
            total_bid_vol = sum(v for _, v in bid_levels[:10])
            total_ask_vol = sum(v for _, v in ask_levels[:10])
            if total_bid_vol + total_ask_vol > 0:
                weighted_mid = (best_ask * total_bid_vol + best_bid * total_ask_vol) / (total_bid_vol + total_ask_vol)
            else:
                weighted_mid = mid

            obi_1 = imbalances.get("depth_1", {}).get("obi", 0)

            return success_response({
                    "imbalances": imbalances,
                    "best_bid": round(best_bid, 4),
                    "best_ask": round(best_ask, 4),
                    "spread": round(float(spread), 4),
                    "spread_bps": round(float(spread_bps), 2),
                    "weighted_mid": round(float(weighted_mid), 4),
                    "n_bid_levels": len(bid_levels),
                    "n_ask_levels": len(ask_levels),
                    "interpretation": (
                        f"Spread: {spread_bps:.1f} bps. "
                        f"Top-of-book OBI: {obi_1:.3f} "
                        f"({'buy pressure' if obi_1 > 0.2 else 'sell pressure' if obi_1 < -0.2 else 'balanced'}). "
                        f"Depth-10 bid vol: {imbalances.get('depth_10', {}).get('bid_volume', 0):,.0f}, "
                        f"ask vol: {imbalances.get('depth_10', {}).get('ask_volume', 0):,.0f}."
                    ),
                })
        except Exception as e:
            logger.exception("orderbook_imbalance failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 6. VPIN (Volume-Synchronized Probability of Informed Trading)
    # ------------------------------------------------------------------
    def toxicity(
        self, series: List[Dict], bucket_volume: Optional[float] = None, n_buckets: int = 50,
    ) -> Dict[str, Any]:
        """VPIN toxicity metric from volume-synchronized sampling.

        Classifies each volume bucket's trades as buy/sell using bulk
        volume classification (BVC), then computes order imbalance.
        High VPIN = informed traders are active = potential adverse selection.
        """
        try:
            df = pd.DataFrame(series)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").drop_duplicates("date")
            prices = df["value"].astype(float).values
            n = len(prices)
            if n < 50:
                return error_response(f"Need >= 50 observations, got {n}")

            returns = np.diff(np.log(prices))

            if "volume" in df.columns:
                volumes = df["volume"].astype(float).values[1:]
            else:
                # Proxy: use constant volume
                volumes = np.ones(len(returns)) * 1000

            # Determine bucket volume
            if bucket_volume is None:
                total_vol = np.sum(volumes)
                bucket_volume = total_vol / n_buckets

            # Create volume buckets
            buckets = []
            current_buy = 0
            current_sell = 0
            current_vol = 0

            for i in range(len(returns)):
                # BVC: classify volume based on return sign
                # Buy volume = V * CDF(return / sigma)
                sigma = np.std(returns[max(0, i - 20):i + 1]) if i >= 5 else np.std(returns[:i + 1])
                if sigma > 0:
                    z = returns[i] / sigma
                    buy_pct = stats.norm.cdf(z)
                else:
                    buy_pct = 0.5

                v_buy = volumes[i] * buy_pct
                v_sell = volumes[i] * (1 - buy_pct)

                current_buy += v_buy
                current_sell += v_sell
                current_vol += volumes[i]

                # When bucket is full
                if current_vol >= bucket_volume:
                    imbalance = abs(current_buy - current_sell) / max(current_vol, 1e-10)
                    buckets.append({
                        "buy_vol": current_buy,
                        "sell_vol": current_sell,
                        "total_vol": current_vol,
                        "imbalance": imbalance,
                    })
                    current_buy = current_sell = current_vol = 0

            if len(buckets) < 5:
                return error_response(f"Only {len(buckets)} buckets created; need >= 5. Try smaller bucket_volume.")

            # VPIN = average imbalance over last n_buckets
            imbalances = [b["imbalance"] for b in buckets]
            vpin = float(np.mean(imbalances[-n_buckets:]))
            vpin_std = float(np.std(imbalances[-n_buckets:]))
            current_vpin = float(imbalances[-1]) if imbalances else 0

            # Historical percentile
            if len(imbalances) >= 10:
                pctile = float(stats.percentileofscore(imbalances, current_vpin))
            else:
                pctile = 50

            # Recent VPIN trajectory
            recent = [round(v, 4) for v in imbalances[-20:]]

            return success_response({
                    "vpin": round(vpin, 4),
                    "vpin_std": round(vpin_std, 4),
                    "current_vpin": round(current_vpin, 4),
                    "vpin_percentile": round(pctile, 1),
                    "n_buckets_created": len(buckets),
                    "bucket_volume": round(float(bucket_volume), 0),
                    "recent_vpin": recent,
                    "interpretation": (
                        f"VPIN: {vpin:.3f} (current: {current_vpin:.3f}, "
                        f"pctile: {pctile:.0f}%). "
                        f"{'LOW toxicity' if vpin < 0.3 else 'MODERATE toxicity' if vpin < 0.5 else 'HIGH toxicity — informed trading likely!'}. "
                        f"{'⚠ Flash crash risk elevated!' if vpin > 0.6 else ''}"
                    ),
                })
        except Exception as e:
            logger.exception("toxicity failed")
            return error_response(str(e))
