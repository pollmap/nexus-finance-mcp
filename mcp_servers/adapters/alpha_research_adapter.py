"""
Alpha Research Toolkit Adapter — Signal Quality & Portfolio Analytics.

1. turnover: Strategy turnover and cost analysis
2. decay: Alpha/signal decay curve across horizons
3. crowding: Signal crowding detector (factor exposure)
4. capacity: Strategy capacity estimation (max AUM)
5. regime_switch: Regime-conditional alpha metrics
6. combine: Multi-alpha combination (equal/IC-weighted/optimized)

References:
- Grinold & Kahn (1999), Active Portfolio Management, 2nd ed.
- López de Prado (2018), Advances in Financial Machine Learning, Ch.6
"""
import logging
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats, optimize

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=RuntimeWarning)


class AlphaResearchAdapter:
    """Alpha research and signal quality analysis tools."""

    # ------------------------------------------------------------------
    # 1. Strategy Turnover
    # ------------------------------------------------------------------
    def turnover(
        self,
        weights_history: List[Dict],
        cost_per_trade: float = 0.001,
    ) -> Dict[str, Any]:
        """Analyze strategy turnover and trading cost impact.

        Args:
            weights_history: [{date, weights: {asset: weight, ...}}, ...]
            cost_per_trade: one-way transaction cost (default 0.1%)
        """
        try:
            if len(weights_history) < 2:
                return error_response("Need >= 2 rebalancing periods")

            turnovers = []
            for i in range(1, len(weights_history)):
                prev = weights_history[i - 1].get("weights", {})
                curr = weights_history[i].get("weights", {})
                all_assets = set(list(prev.keys()) + list(curr.keys()))

                to = sum(abs(curr.get(a, 0) - prev.get(a, 0)) for a in all_assets) / 2
                turnovers.append({
                    "date": weights_history[i].get("date", ""),
                    "turnover": round(float(to), 4),
                    "cost": round(float(to * cost_per_trade * 2), 6),  # round-trip
                })

            avg_turnover = float(np.mean([t["turnover"] for t in turnovers]))
            total_cost = float(np.sum([t["cost"] for t in turnovers]))
            annual_cost = total_cost * 252 / len(turnovers) if turnovers else 0

            # Break-even alpha
            break_even = annual_cost  # alpha must exceed this to be profitable

            return success_response({
                    "avg_turnover": round(avg_turnover, 4),
                    "max_turnover": round(max(t["turnover"] for t in turnovers), 4),
                    "total_cost": round(total_cost, 6),
                    "annualized_cost": round(float(annual_cost), 4),
                    "break_even_alpha": round(float(break_even), 4),
                    "n_rebalances": len(turnovers),
                    "cost_per_trade": cost_per_trade,
                    "recent_turnovers": turnovers[-10:],
                    "interpretation": (
                        f"Avg turnover: {avg_turnover:.1%}/period. "
                        f"Annual cost: {annual_cost:.2%}. "
                        f"Break-even alpha: {break_even:.2%}. "
                        f"{'Low turnover.' if avg_turnover < 0.1 else 'High turnover — costs matter!'}"
                    ),
                })
        except Exception as e:
            logger.exception("turnover failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 2. Alpha Decay
    # ------------------------------------------------------------------
    def decay(
        self,
        signals: List[Dict],
        returns: List[Dict],
        horizons: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Alpha decay curve — IC at different forward horizons.

        Args:
            signals: [{date, value}] — signal values
            returns: [{date, value}] — asset returns
            horizons: forward horizons in days (default [1,2,5,10,20,40,60])
        """
        try:
            if not horizons:
                horizons = [1, 2, 5, 10, 20, 40, 60]

            sig_df = pd.DataFrame(signals)
            sig_df["date"] = pd.to_datetime(sig_df["date"])
            sig_df = sig_df.sort_values("date").set_index("date")["value"].astype(float)

            ret_df = pd.DataFrame(returns)
            ret_df["date"] = pd.to_datetime(ret_df["date"])
            ret_df = ret_df.sort_values("date").set_index("date")["value"].astype(float)

            aligned = pd.DataFrame({"signal": sig_df, "return": ret_df}).dropna()
            n = len(aligned)
            if n < 60:
                return error_response(f"Need >= 60 aligned points, got {n}")

            sig = aligned["signal"].values
            ret = aligned["return"].values

            # Compute IC at each horizon
            ic_curve = []
            for h in horizons:
                if h >= n - 10:
                    continue
                # Forward return = sum of next h returns
                fwd_ret = np.array([np.sum(ret[i + 1:i + h + 1]) for i in range(n - h)])
                sig_aligned = sig[:n - h]

                ic = float(stats.spearmanr(sig_aligned, fwd_ret).statistic)
                ic_curve.append({
                    "horizon_days": h,
                    "ic": round(ic, 4),
                    "abs_ic": round(abs(ic), 4),
                })

            # Half-life of IC decay
            if len(ic_curve) >= 3:
                ics = np.array([x["abs_ic"] for x in ic_curve])
                peak_ic = ics[0]
                half_ic = peak_ic / 2
                half_life = None
                for i, x in enumerate(ic_curve):
                    if x["abs_ic"] < half_ic:
                        half_life = x["horizon_days"]
                        break
            else:
                half_life = None

            return success_response({
                    "ic_curve": ic_curve,
                    "ic_1d": ic_curve[0]["ic"] if ic_curve else 0,
                    "peak_ic": round(max(abs(x["ic"]) for x in ic_curve), 4) if ic_curve else 0,
                    "half_life_days": half_life,
                    "n_observations": n,
                    "interpretation": (
                        f"IC at 1d: {ic_curve[0]['ic']:.4f}. "
                        f"Half-life: {half_life} days. "
                        f"{'Fast decay — short-term signal.' if half_life and half_life < 10 else 'Slow decay — durable signal.' if half_life and half_life > 20 else ''}"
                    ) if ic_curve else "No IC curve computed.",
                })
        except Exception as e:
            logger.exception("decay failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 3. Signal Crowding
    # ------------------------------------------------------------------
    def crowding(
        self,
        signal: List[Dict],
        factor_data: Dict[str, List[Dict]],
    ) -> Dict[str, Any]:
        """Detect how correlated a signal is with known common factors.

        Args:
            signal: [{date, value}]
            factor_data: {"momentum": [{date, value}], "value": [{date, value}], ...}
        """
        try:
            sig_df = pd.DataFrame(signal)
            sig_df["date"] = pd.to_datetime(sig_df["date"])
            sig = sig_df.sort_values("date").set_index("date")["value"].astype(float).rename("signal")

            factors = {}
            for name, data in factor_data.items():
                fdf = pd.DataFrame(data)
                fdf["date"] = pd.to_datetime(fdf["date"])
                factors[name] = fdf.sort_values("date").set_index("date")["value"].astype(float).rename(name)

            all_data = pd.concat([sig] + list(factors.values()), axis=1, join="inner").dropna()
            if len(all_data) < 30:
                return error_response(f"Only {len(all_data)} aligned dates")

            # Individual correlations
            correlations = {}
            for name in factors:
                r = float(all_data["signal"].corr(all_data[name]))
                correlations[name] = round(r, 4)

            # Multiple regression: signal = sum(beta_i * factor_i)
            from numpy.linalg import lstsq
            X = all_data[list(factors.keys())].values
            X_with_const = np.column_stack([np.ones(len(X)), X])
            y = all_data["signal"].values
            coeffs = lstsq(X_with_const, y, rcond=None)[0]

            predicted = X_with_const @ coeffs
            ss_res = np.sum((y - predicted) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

            # Crowding assessment
            if r_squared > 0.7:
                crowding_level = "HIGH"
                advice = "Signal is mostly explained by known factors — low alpha"
            elif r_squared > 0.4:
                crowding_level = "MODERATE"
                advice = "Some unique content but significant factor overlap"
            elif r_squared > 0.2:
                crowding_level = "LOW"
                advice = "Signal has meaningful unique content"
            else:
                crowding_level = "VERY LOW"
                advice = "Signal is largely orthogonal to known factors — potential alpha"

            betas = {list(factors.keys())[i]: round(float(coeffs[i + 1]), 4) for i in range(len(factors))}

            return success_response({
                    "r_squared": round(float(r_squared), 4),
                    "crowding_level": crowding_level,
                    "factor_correlations": correlations,
                    "factor_betas": betas,
                    "n_observations": len(all_data),
                    "advice": advice,
                    "interpretation": (
                        f"Crowding R²={r_squared:.3f} ({crowding_level}). "
                        f"Highest factor corr: "
                        f"{max(correlations, key=lambda k: abs(correlations[k]))}="
                        f"{correlations[max(correlations, key=lambda k: abs(correlations[k]))]}. "
                        f"{advice}."
                    ),
                })
        except Exception as e:
            logger.exception("crowding failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 4. Strategy Capacity
    # ------------------------------------------------------------------
    def capacity(
        self,
        alpha: float,
        turnover: float,
        kyle_lambda: float = 1e-7,
        avg_daily_volume: float = 1e9,
    ) -> Dict[str, Any]:
        """Estimate max AUM before alpha is eroded by market impact.

        capacity ≈ alpha / (2 * lambda * turnover)  (Grinold-Kahn)

        Args:
            alpha: annual alpha (e.g., 0.05 for 5%)
            turnover: annual turnover (e.g., 12 for monthly rebalance)
            kyle_lambda: price impact coefficient
            avg_daily_volume: average daily volume in currency
        """
        try:
            if turnover <= 0:
                return error_response("Turnover must be > 0")
            if kyle_lambda <= 0:
                return error_response("kyle_lambda must be > 0")

            # Grinold-Kahn capacity
            capacity_gk = alpha / (2 * kyle_lambda * turnover)

            # ADV-based capacity (% of volume)
            participation_rates = [0.01, 0.05, 0.10, 0.20]
            adv_capacities = []
            for pr in participation_rates:
                adv_cap = avg_daily_volume * pr / turnover * 252
                adv_capacities.append({
                    "participation_rate": pr,
                    "max_aum": round(float(adv_cap), 0),
                })

            # Conservative estimate = min of all
            conservative = min(capacity_gk, adv_capacities[1]["max_aum"]) if adv_capacities else capacity_gk

            return success_response({
                    "grinold_kahn_capacity": round(float(capacity_gk), 0),
                    "adv_based_capacities": adv_capacities,
                    "conservative_estimate": round(float(conservative), 0),
                    "parameters": {
                        "alpha": alpha,
                        "turnover": turnover,
                        "kyle_lambda": kyle_lambda,
                        "avg_daily_volume": avg_daily_volume,
                    },
                    "interpretation": (
                        f"Max capacity: ~{conservative:,.0f} (conservative). "
                        f"GK model: {capacity_gk:,.0f}. "
                        f"Alpha {alpha:.1%} with turnover {turnover:.0f}x/yr."
                    ),
                })
        except Exception as e:
            logger.exception("capacity failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 5. Regime-Conditional Alpha
    # ------------------------------------------------------------------
    def regime_switch(
        self,
        returns: List[Dict],
        signals: List[Dict],
        n_regimes: int = 2,
    ) -> Dict[str, Any]:
        """Split strategy performance by market regime.

        Uses volatility-based regime classification.
        """
        try:
            ret_df = pd.DataFrame(returns)
            ret_df["date"] = pd.to_datetime(ret_df["date"])
            ret_s = ret_df.sort_values("date").set_index("date")["value"].astype(float)

            sig_df = pd.DataFrame(signals)
            sig_df["date"] = pd.to_datetime(sig_df["date"])
            sig_s = sig_df.sort_values("date").set_index("date")["value"].astype(float)

            aligned = pd.DataFrame({"return": ret_s, "signal": sig_s}).dropna()
            n = len(aligned)
            if n < 60:
                return error_response(f"Need >= 60 observations, got {n}")

            ret = aligned["return"].values
            sig = aligned["signal"].values

            # Rolling volatility for regime detection
            vol = pd.Series(ret).rolling(20).std().values

            # Classify regimes by volatility percentile
            valid = ~np.isnan(vol)
            vol_valid = vol[valid]
            ret_valid = ret[valid]
            sig_valid = sig[valid]

            if n_regimes == 2:
                median_vol = np.median(vol_valid)
                regime_labels = np.where(vol_valid > median_vol, "high_vol", "low_vol")
            else:
                p33 = np.percentile(vol_valid, 33)
                p66 = np.percentile(vol_valid, 66)
                regime_labels = np.where(
                    vol_valid < p33, "low_vol",
                    np.where(vol_valid < p66, "mid_vol", "high_vol")
                )

            regimes = {}
            for regime in np.unique(regime_labels):
                mask = regime_labels == regime
                r = ret_valid[mask]
                s = sig_valid[mask]

                # IC in this regime
                ic = float(stats.spearmanr(s, r).statistic) if len(r) >= 10 else 0

                # Strategy return (signal * return)
                strat_ret = s * r
                sharpe = float(np.mean(strat_ret) / np.std(strat_ret) * np.sqrt(252)) if np.std(strat_ret) > 0 else 0

                regimes[regime] = {
                    "n_observations": int(np.sum(mask)),
                    "pct_of_total": round(np.sum(mask) / len(regime_labels) * 100, 1),
                    "avg_return": round(float(np.mean(r)), 6),
                    "avg_volatility": round(float(np.std(r) * np.sqrt(252)), 4),
                    "ic": round(ic, 4),
                    "strategy_sharpe": round(sharpe, 3),
                }

            # Best regime
            best = max(regimes.items(), key=lambda x: x[1]["strategy_sharpe"])

            return success_response({
                    "regimes": regimes,
                    "n_regimes": n_regimes,
                    "best_regime": best[0],
                    "best_sharpe": best[1]["strategy_sharpe"],
                    "n_observations": len(vol_valid),
                    "interpretation": (
                        f"Best regime: {best[0]} (Sharpe={best[1]['strategy_sharpe']:.2f}). "
                        f"Signal works {'differently' if abs(list(regimes.values())[0]['ic'] - list(regimes.values())[-1]['ic']) > 0.02 else 'similarly'} "
                        f"across regimes."
                    ),
                })
        except Exception as e:
            logger.exception("regime_switch failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 6. Multi-Alpha Combination
    # ------------------------------------------------------------------
    def combine(
        self,
        alpha_series: Dict[str, List[Dict]],
        returns: List[Dict],
        method: str = "ic_weight",
    ) -> Dict[str, Any]:
        """Combine multiple alpha signals.

        Args:
            alpha_series: {"alpha1": [{date, value}], "alpha2": [...], ...}
            returns: forward returns [{date, value}]
            method: "equal", "ic_weight", or "optimize"
        """
        try:
            ret_df = pd.DataFrame(returns)
            ret_df["date"] = pd.to_datetime(ret_df["date"])
            ret_s = ret_df.sort_values("date").set_index("date")["value"].astype(float).rename("return")

            alphas = {}
            for name, data in alpha_series.items():
                adf = pd.DataFrame(data)
                adf["date"] = pd.to_datetime(adf["date"])
                alphas[name] = adf.sort_values("date").set_index("date")["value"].astype(float).rename(name)

            all_data = pd.concat([ret_s] + list(alphas.values()), axis=1, join="inner").dropna()
            n = len(all_data)
            if n < 30:
                return error_response(f"Need >= 30 aligned dates, got {n}")

            alpha_names = list(alphas.keys())
            ret_vals = all_data["return"].values

            # Individual ICs
            individual_ics = {}
            for name in alpha_names:
                ic = float(stats.spearmanr(all_data[name].values, ret_vals).statistic)
                individual_ics[name] = round(ic, 4)

            # Weights
            if method == "equal":
                weights = {name: round(1.0 / len(alpha_names), 4) for name in alpha_names}
            elif method == "ic_weight":
                abs_ics = {name: abs(ic) for name, ic in individual_ics.items()}
                total_ic = sum(abs_ics.values())
                if total_ic > 0:
                    weights = {name: round(abs_ics[name] / total_ic, 4) for name in alpha_names}
                else:
                    weights = {name: round(1.0 / len(alpha_names), 4) for name in alpha_names}
            elif method == "optimize":
                # Maximize IC ratio: w'IC / sqrt(w'Cov_alpha*w)
                alpha_matrix = all_data[alpha_names].values
                ic_vec = np.array([individual_ics[n] for n in alpha_names])
                cov_alpha = np.cov(alpha_matrix.T)

                def neg_ic_ratio(w):
                    w = w / np.sum(np.abs(w))  # normalize
                    port_ic = w @ ic_vec
                    port_vol = np.sqrt(w @ cov_alpha @ w)
                    return -(port_ic / port_vol) if port_vol > 0 else 0

                n_a = len(alpha_names)
                res = optimize.minimize(neg_ic_ratio, np.ones(n_a) / n_a,
                                       method="SLSQP",
                                       bounds=[(0, 1)] * n_a,
                                       constraints={"type": "eq", "fun": lambda w: np.sum(w) - 1})
                weights = {alpha_names[i]: round(float(res.x[i]), 4) for i in range(n_a)}
            else:
                return error_response(f"Unknown method: {method}")

            # Combined signal
            combined = np.zeros(n)
            for name in alpha_names:
                combined += weights[name] * all_data[name].values

            # Combined IC
            combined_ic = float(stats.spearmanr(combined, ret_vals).statistic)

            # Improvement
            best_individual = max(abs(ic) for ic in individual_ics.values())
            improvement = abs(combined_ic) - best_individual

            return success_response({
                    "combined_ic": round(combined_ic, 4),
                    "individual_ics": individual_ics,
                    "weights": weights,
                    "method": method,
                    "improvement_vs_best_single": round(float(improvement), 4),
                    "n_alphas": len(alpha_names),
                    "n_observations": n,
                    "interpretation": (
                        f"Combined IC: {combined_ic:.4f} ({method}). "
                        f"Best individual: {best_individual:.4f}. "
                        f"{'Improvement!' if improvement > 0 else 'No improvement — signals may be redundant.'}"
                    ),
                })
        except Exception as e:
            logger.exception("combine failed")
            return error_response(str(e))
