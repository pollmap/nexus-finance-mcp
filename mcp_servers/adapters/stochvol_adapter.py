"""
Stochastic Volatility & Optimal Execution Adapter.

1. heston: Heston stochastic volatility model calibration
2. jump_diffusion: Merton jump-diffusion model
3. var_premium: Variance risk premium (implied - realized)
4. exec_optimal: Almgren-Chriss optimal execution trajectory
5. exec_vwap: VWAP execution plan from volume profile
6. market_impact: Kyle's lambda market impact estimation

References:
- Heston (1993), "A Closed-Form Solution for Options with Stochastic Volatility," RFS 6(2)
- Merton (1976), "Option Pricing when Underlying Stock Returns are Discontinuous," JFE 3
- Almgren & Chriss (2000), "Optimal Execution of Portfolio Transactions," J. Risk 3(2)
- Kyle (1985), "Continuous Auctions and Insider Trading," Econometrica 53(6)
"""
import logging
import warnings
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import optimize, stats

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=RuntimeWarning)


def _ts_to_array(data: List[Dict]) -> tuple:
    """Convert [{date, value}] to (dates_list, values_array)."""
    if not data or len(data) < 2:
        raise ValueError(f"Need >= 2 data points, got {len(data) if data else 0}")
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates("date").dropna(subset=["value"])
    dates = df["date"].dt.strftime("%Y-%m-%d").tolist()
    values = df["value"].astype(float).values
    return dates, values


class StochVolAdapter:
    """Stochastic volatility models and optimal execution algorithms."""

    # ------------------------------------------------------------------
    # 1. Heston Stochastic Volatility
    # ------------------------------------------------------------------
    def heston(self, series: List[Dict]) -> Dict[str, Any]:
        """Calibrate Heston model from return series via method of moments.

        dS/S = mu*dt + sqrt(v)*dW1
        dv = kappa*(theta - v)*dt + xi*sqrt(v)*dW2
        corr(dW1, dW2) = rho
        """
        try:
            dates, prices = _ts_to_array(series)
            if len(prices) < 100:
                return {"error": True, "message": f"Need >= 100 prices, got {len(prices)}"}

            # Log returns
            returns = np.log(prices[1:] / prices[:-1])
            n = len(returns)

            # Realized variance (daily)
            realized_var = returns ** 2

            # Method of moments for Heston parameters
            # mu: drift
            mu = float(np.mean(returns)) * 252

            # v0: current variance (from recent 20-day realized vol)
            v0 = float(np.var(returns[-20:])) * 252

            # theta: long-run variance (full sample)
            theta = float(np.var(returns)) * 252

            # kappa: mean-reversion speed of variance
            # From autocorrelation of squared returns
            rv = realized_var
            acf1 = np.corrcoef(rv[:-1], rv[1:])[0, 1]
            kappa = max(0.1, -np.log(max(acf1, 0.01)) * 252)
            kappa = min(kappa, 20.0)  # cap

            # xi: vol of vol
            # From variance of realized variance
            xi = float(np.std(np.diff(rv))) * np.sqrt(252) * 2
            xi = max(0.1, min(xi, 5.0))

            # rho: return-variance correlation (leverage effect)
            rho = float(np.corrcoef(returns[1:], np.diff(rv))[0, 1])
            rho = max(-0.99, min(rho, 0.99))

            # Feller condition: 2*kappa*theta > xi^2
            feller = 2 * kappa * theta > xi ** 2

            # Implied vol from current variance
            implied_vol = np.sqrt(v0)

            return {
                "success": True,
                "data": {
                    "mu": round(mu, 4),
                    "kappa": round(float(kappa), 3),
                    "theta": round(float(theta), 4),
                    "xi": round(float(xi), 3),
                    "rho": round(float(rho), 3),
                    "v0": round(float(v0), 4),
                    "implied_vol": round(float(implied_vol), 4),
                    "feller_condition": feller,
                    "n_observations": n,
                    "interpretation": (
                        f"Heston model: κ={kappa:.2f} (vol mean-reverts), "
                        f"θ={theta:.4f} (long-run var={np.sqrt(theta):.1%}), "
                        f"ξ={xi:.2f} (vol-of-vol), ρ={rho:.2f} "
                        f"({'negative=leverage effect' if rho < 0 else 'unusual positive'}). "
                        f"Feller: {'satisfied' if feller else 'VIOLATED (var can hit 0)'}."
                    ),
                }
            }
        except Exception as e:
            logger.exception("heston failed")
            return {"error": True, "message": str(e)}

    # ------------------------------------------------------------------
    # 2. Merton Jump-Diffusion
    # ------------------------------------------------------------------
    def jump_diffusion(self, series: List[Dict]) -> Dict[str, Any]:
        """Estimate Merton jump-diffusion: dS/S = (mu-lambda*k)dt + sigma*dW + J*dN.

        J ~ N(mu_j, sigma_j^2), N ~ Poisson(lambda).
        """
        try:
            dates, prices = _ts_to_array(series)
            if len(prices) < 100:
                return {"error": True, "message": f"Need >= 100 prices, got {len(prices)}"}

            returns = np.log(prices[1:] / prices[:-1])
            n = len(returns)

            # Detect jumps using threshold (|r| > 3*sigma)
            sigma_base = np.std(returns)
            jump_threshold = 3 * sigma_base
            jump_mask = np.abs(returns) > jump_threshold
            n_jumps = int(np.sum(jump_mask))

            # Diffusion parameters (from non-jump returns)
            normal_returns = returns[~jump_mask]
            mu_diff = float(np.mean(normal_returns)) * 252
            sigma_diff = float(np.std(normal_returns)) * np.sqrt(252)

            # Jump parameters
            lambda_j = n_jumps / n * 252  # annual jump intensity
            if n_jumps > 0:
                jump_returns = returns[jump_mask]
                mu_j = float(np.mean(jump_returns))
                sigma_j = float(np.std(jump_returns)) if n_jumps > 1 else abs(mu_j) * 0.5
            else:
                mu_j = 0.0
                sigma_j = 0.0

            # Expected jump size
            k = np.exp(mu_j + 0.5 * sigma_j ** 2) - 1

            # Total expected return: mu_total = mu_diff + lambda*E[J-1]
            total_return = mu_diff + lambda_j * mu_j * 252

            # Total variance: sigma^2 + lambda*(mu_j^2 + sigma_j^2)
            total_var = sigma_diff ** 2 + lambda_j * (mu_j ** 2 + sigma_j ** 2) * 252

            # Skewness and kurtosis from jump component
            emp_skew = float(stats.skew(returns))
            emp_kurt = float(stats.kurtosis(returns))

            # Recent jump dates
            jump_dates = [dates[i + 1] for i in range(n) if jump_mask[i]]

            return {
                "success": True,
                "data": {
                    "diffusion_mu": round(mu_diff, 4),
                    "diffusion_sigma": round(sigma_diff, 4),
                    "jump_intensity_annual": round(float(lambda_j), 2),
                    "jump_mean": round(float(mu_j), 4),
                    "jump_std": round(float(sigma_j), 4),
                    "n_jumps_detected": n_jumps,
                    "jump_threshold": round(float(jump_threshold), 4),
                    "total_expected_return": round(float(total_return), 4),
                    "total_variance": round(float(total_var), 4),
                    "empirical_skewness": round(emp_skew, 3),
                    "empirical_kurtosis": round(emp_kurt, 3),
                    "recent_jumps": jump_dates[-10:],
                    "n_observations": n,
                    "interpretation": (
                        f"Merton jump-diffusion: σ={sigma_diff:.1%} diffusion, "
                        f"λ={lambda_j:.1f} jumps/year, jump size μ_J={mu_j:.2%}±{sigma_j:.2%}. "
                        f"{n_jumps} jumps detected (>{jump_threshold:.2%} threshold). "
                        f"Kurtosis={emp_kurt:.1f} ({'fat tails' if emp_kurt > 3 else 'normal'})."
                    ),
                }
            }
        except Exception as e:
            logger.exception("jump_diffusion failed")
            return {"error": True, "message": str(e)}

    # ------------------------------------------------------------------
    # 3. Variance Risk Premium
    # ------------------------------------------------------------------
    def var_premium(
        self, series: List[Dict], vix_series: Optional[List[Dict]] = None, window: int = 20,
    ) -> Dict[str, Any]:
        """Variance risk premium: implied volatility minus realized volatility.

        VRP > 0 means options are "expensive" → selling vol is profitable on average.
        """
        try:
            dates, prices = _ts_to_array(series)
            if len(prices) < 60:
                return {"error": True, "message": f"Need >= 60 prices, got {len(prices)}"}

            returns = np.log(prices[1:] / prices[:-1])

            # Realized volatility (rolling)
            rv_series = pd.Series(returns).rolling(window).std() * np.sqrt(252)
            rv_series = rv_series.dropna()

            if vix_series and len(vix_series) > 0:
                # Use provided implied vol series
                vix_df = pd.DataFrame(vix_series)
                vix_df["date"] = pd.to_datetime(vix_df["date"])
                vix_df = vix_df.sort_values("date").set_index("date")
                iv = vix_df["value"].astype(float) / 100  # VIX is in percentage
                # Align
                common_n = min(len(rv_series), len(iv))
                rv_vals = rv_series.values[-common_n:]
                iv_vals = iv.values[-common_n:]
            else:
                # Estimate implied vol as scaled realized vol (proxy)
                rv_vals = rv_series.values
                # Historical average VRP for equities is ~2-4 vol points
                iv_vals = rv_vals * 1.15  # Rough proxy: IV typically 15% above RV

            vrp = iv_vals - rv_vals
            vrp_var = iv_vals ** 2 - rv_vals ** 2  # variance terms

            # Statistics
            mean_vrp = float(np.mean(vrp))
            median_vrp = float(np.median(vrp))
            current_vrp = float(vrp[-1]) if len(vrp) > 0 else 0
            pct_positive = float(np.mean(vrp > 0))

            # Rolling VRP (last 60 days)
            recent_vrp = [
                round(float(v), 4) for v in vrp[-min(60, len(vrp)):]
            ]

            return {
                "success": True,
                "data": {
                    "current_vrp_vol": round(current_vrp, 4),
                    "current_implied_vol": round(float(iv_vals[-1]), 4) if len(iv_vals) > 0 else None,
                    "current_realized_vol": round(float(rv_vals[-1]), 4) if len(rv_vals) > 0 else None,
                    "mean_vrp": round(mean_vrp, 4),
                    "median_vrp": round(median_vrp, 4),
                    "pct_positive": round(pct_positive, 3),
                    "vrp_std": round(float(np.std(vrp)), 4),
                    "n_observations": len(vrp),
                    "window": window,
                    "using_vix_data": vix_series is not None and len(vix_series) > 0,
                    "interpretation": (
                        f"VRP = {current_vrp:.2%} (IV − RV). "
                        f"{'Positive' if current_vrp > 0 else 'Negative'} → "
                        f"{'vol selling profitable (options expensive)' if current_vrp > 0 else 'vol buying profitable (options cheap)'}. "
                        f"Historically positive {pct_positive:.0%} of the time."
                    ),
                }
            }
        except Exception as e:
            logger.exception("var_premium failed")
            return {"error": True, "message": str(e)}

    # ------------------------------------------------------------------
    # 4. Almgren-Chriss Optimal Execution
    # ------------------------------------------------------------------
    def exec_optimal(
        self,
        total_shares: float,
        horizon_days: int = 5,
        daily_volume: float = 1e6,
        volatility: float = 0.02,
        permanent_impact: float = 1e-7,
        temporary_impact: float = 1e-6,
        risk_aversion: float = 1e-6,
    ) -> Dict[str, Any]:
        """Almgren-Chriss optimal execution trajectory.

        Minimizes E[cost] + lambda * Var[cost].
        Solution: x_k = X * sinh(kappa*(T-t_k)) / sinh(kappa*T)
        """
        try:
            X = total_shares
            T = horizon_days
            sigma = volatility  # daily volatility
            gamma = permanent_impact  # permanent impact
            eta = temporary_impact  # temporary impact
            lam = risk_aversion

            if T < 1:
                return {"error": True, "message": "Horizon must be >= 1 day"}

            # Almgren-Chriss parameters
            # kappa = sqrt(lambda * sigma^2 / eta)
            kappa_sq = lam * sigma ** 2 / eta
            kappa = np.sqrt(kappa_sq)

            # Optimal trajectory: remaining shares at time k
            n_steps = T
            trajectory = []
            for k in range(n_steps + 1):
                t = k
                remaining = X * np.sinh(kappa * (T - t)) / np.sinh(kappa * T) if kappa * T > 0 else X * (1 - t / T)
                trade_k = 0
                if k > 0:
                    prev_remaining = trajectory[-1]["remaining_shares"]
                    trade_k = prev_remaining - remaining

                trajectory.append({
                    "day": k,
                    "remaining_shares": round(float(remaining), 0),
                    "trade_shares": round(float(trade_k), 0) if k > 0 else 0,
                    "pct_of_total": round(float(trade_k / X * 100), 1) if k > 0 and X > 0 else 0,
                    "pct_of_daily_volume": round(float(trade_k / daily_volume * 100), 1) if k > 0 else 0,
                })

            # Expected cost
            # E[cost] ≈ gamma * X^2 / 2 + eta * sum(n_k^2 / tau)
            trades = [t["trade_shares"] for t in trajectory[1:]]
            expected_permanent = gamma * X ** 2 / 2
            expected_temporary = eta * sum(n ** 2 for n in trades)
            expected_total = expected_permanent + expected_temporary

            # Variance of cost
            var_cost = sigma ** 2 * sum(
                trajectory[k]["remaining_shares"] ** 2 for k in range(n_steps)
            )

            # Compare with TWAP (linear execution)
            twap_trade = X / T
            twap_temp = eta * T * twap_trade ** 2
            twap_perm = gamma * X ** 2 / 2
            twap_total = twap_temp + twap_perm

            # Participation rate
            max_participation = max(t["pct_of_daily_volume"] for t in trajectory[1:]) if len(trajectory) > 1 else 0

            return {
                "success": True,
                "data": {
                    "trajectory": trajectory,
                    "kappa": round(float(kappa), 6),
                    "expected_cost": round(float(expected_total), 2),
                    "expected_permanent_impact": round(float(expected_permanent), 2),
                    "expected_temporary_impact": round(float(expected_temporary), 2),
                    "cost_variance": round(float(var_cost), 2),
                    "twap_cost": round(float(twap_total), 2),
                    "savings_vs_twap": round(float(twap_total - expected_total), 2),
                    "max_participation_rate_pct": round(float(max_participation), 1),
                    "parameters": {
                        "total_shares": total_shares,
                        "horizon_days": horizon_days,
                        "daily_volume": daily_volume,
                        "volatility": volatility,
                        "risk_aversion": risk_aversion,
                    },
                    "interpretation": (
                        f"AC optimal: {T}-day execution of {X:,.0f} shares. "
                        f"{'Front-loaded' if kappa > 0.5 else 'Near-linear'} trajectory. "
                        f"Expected cost: {expected_total:,.0f} "
                        f"(saves {twap_total - expected_total:,.0f} vs TWAP). "
                        f"Max participation: {max_participation:.1f}% of daily volume."
                    ),
                }
            }
        except Exception as e:
            logger.exception("exec_optimal failed")
            return {"error": True, "message": str(e)}

    # ------------------------------------------------------------------
    # 5. VWAP Execution Plan
    # ------------------------------------------------------------------
    def exec_vwap(
        self, series: List[Dict], total_shares: float, n_buckets: int = 10,
    ) -> Dict[str, Any]:
        """VWAP execution plan based on historical volume profile.

        Distributes order across time buckets proportional to typical volume.
        """
        try:
            df = pd.DataFrame(series)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").drop_duplicates("date")

            # Need volume data — check for 'volume' key
            if "volume" not in df.columns:
                # If no volume, create equal-weight buckets
                plan = []
                shares_per_bucket = total_shares / n_buckets
                for i in range(n_buckets):
                    plan.append({
                        "bucket": i + 1,
                        "pct_of_total": round(100 / n_buckets, 1),
                        "shares": round(float(shares_per_bucket), 0),
                    })
                return {
                    "success": True,
                    "data": {
                        "plan": plan,
                        "method": "equal_weight (no volume data)",
                        "total_shares": total_shares,
                        "n_buckets": n_buckets,
                        "interpretation": "TWAP fallback: no volume data available, equal distribution.",
                    }
                }

            volumes = df["volume"].astype(float).values
            n = len(volumes)

            # Create intraday volume profile by bucketing
            bucket_size = max(1, n // n_buckets)
            profile = []
            for i in range(n_buckets):
                start = i * bucket_size
                end = min(start + bucket_size, n)
                if start >= n:
                    break
                avg_vol = float(np.mean(volumes[start:end]))
                profile.append(avg_vol)

            # Normalize to proportions
            total_vol = sum(profile)
            if total_vol == 0:
                proportions = [1 / len(profile)] * len(profile)
            else:
                proportions = [v / total_vol for v in profile]

            plan = []
            for i, pct in enumerate(proportions):
                plan.append({
                    "bucket": i + 1,
                    "volume_weight": round(float(pct), 4),
                    "pct_of_total": round(float(pct * 100), 1),
                    "shares": round(float(total_shares * pct), 0),
                })

            return {
                "success": True,
                "data": {
                    "plan": plan,
                    "method": "volume_weighted",
                    "total_shares": total_shares,
                    "n_buckets": len(plan),
                    "max_bucket_pct": round(max(pct * 100 for pct in proportions), 1),
                    "min_bucket_pct": round(min(pct * 100 for pct in proportions), 1),
                    "interpretation": (
                        f"VWAP plan: {len(plan)} buckets. "
                        f"Heaviest bucket: {max(pct * 100 for pct in proportions):.1f}%. "
                        f"Lightest: {min(pct * 100 for pct in proportions):.1f}%."
                    ),
                }
            }
        except Exception as e:
            logger.exception("exec_vwap failed")
            return {"error": True, "message": str(e)}

    # ------------------------------------------------------------------
    # 6. Market Impact Estimation
    # ------------------------------------------------------------------
    def market_impact(
        self, series: List[Dict], window: int = 20,
    ) -> Dict[str, Any]:
        """Estimate Kyle's lambda (price impact coefficient) from price/volume data.

        lambda = Cov(delta_p, volume) / Var(volume)
        """
        try:
            df = pd.DataFrame(series)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").drop_duplicates("date")

            prices = df["value"].astype(float).values
            n = len(prices)

            if n < 30:
                return {"error": True, "message": f"Need >= 30 observations, got {n}"}

            returns = np.diff(np.log(prices))

            # If volume available, use it; otherwise proxy with |returns|
            if "volume" in df.columns:
                volumes = df["volume"].astype(float).values[1:]  # align with returns
                signed_volume = volumes * np.sign(returns)
                has_volume = True
            else:
                # Proxy: use absolute returns as volume proxy
                signed_volume = returns * 1e6  # scale factor
                has_volume = False

            # Kyle's lambda via OLS: delta_p = c + lambda * signed_volume
            n_r = len(returns)
            X = np.column_stack([np.ones(n_r), signed_volume[:n_r]])
            y = returns[:n_r]
            coeffs = np.linalg.lstsq(X, y, rcond=None)[0]
            intercept, kyle_lambda = coeffs[0], coeffs[1]

            # R-squared
            predicted = X @ coeffs
            ss_res = np.sum((y - predicted) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

            # Amihud illiquidity (as comparison)
            if has_volume:
                amihud = float(np.mean(np.abs(returns) / (volumes[:n_r] + 1e-10))) * 1e6
            else:
                amihud = None

            # Roll spread estimate
            autocovar = np.cov(returns[:-1], returns[1:])[0, 1]
            roll_spread = 2 * np.sqrt(max(0, -autocovar))

            return {
                "success": True,
                "data": {
                    "kyle_lambda": round(float(kyle_lambda), 8),
                    "intercept": round(float(intercept), 6),
                    "r_squared": round(float(r_squared), 4),
                    "amihud_illiquidity": round(float(amihud), 4) if amihud is not None else None,
                    "roll_spread": round(float(roll_spread), 6),
                    "has_volume_data": has_volume,
                    "n_observations": n_r,
                    "interpretation": (
                        f"Kyle's λ={kyle_lambda:.2e} ({'positive=expected' if kyle_lambda > 0 else 'negative=unusual'}). "
                        f"R²={r_squared:.3f}. "
                        f"Roll spread={roll_spread:.4%}. "
                        f"{'Volume data used.' if has_volume else 'Returns proxy (no volume).'}"
                    ),
                }
            }
        except Exception as e:
            logger.exception("market_impact failed")
            return {"error": True, "message": str(e)}
