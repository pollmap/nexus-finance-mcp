"""
Statistical Arbitrage Adapter — Pairs Trading & Mean-Reversion Framework.

Implements six tools for systematic stat-arb:

1. ou_fit: Ornstein-Uhlenbeck process parameter estimation (MLE)
2. pairs_distance: Distance-method pair selection from universe
3. spread_zscore: Hedge ratio, spread construction, z-score signals
4. copula_fit: Bivariate copula dependence modeling
5. halflife: Mean-reversion half-life via AR(1)
6. backtest: Z-score mean-reversion strategy backtest

Input format: list[dict] with {"date": "YYYY-MM-DD", "value": float}

References:
- Gatev, Goetzmann & Rouwenhorst (2006), "Pairs Trading," RFS 19: 797–827
- Leung & Li (2015), Optimal Mean Reversion Trading (World Scientific)
- Engle & Granger (1987), "Co-integration and Error Correction," Econometrica 55(2)
"""
import logging
import sys
import os
import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import optimize, stats

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=RuntimeWarning)


def _ts_to_series(data: List[Dict], name: str = "value") -> pd.Series:
    """Convert [{date, value}] to pd.Series indexed by date."""
    if not data or len(data) < 2:
        raise ValueError(f"Need at least 2 data points, got {len(data) if data else 0}")
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates("date").dropna(subset=["value"])
    return df.set_index("date")["value"].astype(float).rename(name)


def _align_series(s1: pd.Series, s2: pd.Series) -> pd.DataFrame:
    """Align two series by inner-join on date index."""
    df = pd.concat([s1, s2], axis=1, join="inner").dropna()
    if len(df) < 30:
        raise ValueError(f"Only {len(df)} overlapping dates; need at least 30")
    return df


class StatArbAdapter:
    """Statistical Arbitrage analysis engine for pairs trading."""

    # ------------------------------------------------------------------
    # 1. Ornstein-Uhlenbeck MLE Fit
    # ------------------------------------------------------------------
    def ou_fit(self, series: List[Dict]) -> Dict[str, Any]:
        """Fit OU process dX = theta*(mu - X)*dt + sigma*dW via MLE.

        Returns theta (mean-reversion speed), mu (long-run mean),
        sigma (diffusion), half-life, and model diagnostics.
        """
        try:
            s = _ts_to_series(series, "spread")
            x = s.values
            n = len(x)
            if n < 30:
                return error_response(f"Need >= 30 data points, got {n}")

            dt = 1.0  # daily

            # MLE for OU: X_{t+1} = X_t + theta*(mu - X_t)*dt + sigma*sqrt(dt)*eps
            # Rewrite as AR(1): X_{t+1} = a + b*X_t + eps
            y = x[1:]
            x_lag = x[:-1]

            # OLS regression: y = a + b * x_lag
            from numpy.linalg import lstsq
            A = np.column_stack([np.ones(len(x_lag)), x_lag])
            result = lstsq(A, y, rcond=None)
            coeffs = result[0]
            a, b = coeffs[0], coeffs[1]

            residuals = y - (a + b * x_lag)
            sigma_eps = np.std(residuals)

            # OU parameters from AR(1) mapping
            # b = exp(-theta*dt), so theta = -ln(b)/dt
            if b <= 0 or b >= 1:
                # Not mean-reverting
                return success_response(
                    {
                        "mean_reverting": False,
                        "ar1_coeff": round(float(b), 6),
                        "interpretation": "Series is NOT mean-reverting (AR(1) coeff outside (0,1)). "
                                          "Pairs/stat-arb not recommended.",
                        "n_observations": n,
                    },
                    source="Stat Arb",
                )

            theta = -np.log(b) / dt
            mu = a / (1 - b)
            sigma = sigma_eps * np.sqrt(-2 * np.log(b) / (dt * (1 - b**2)))
            half_life = np.log(2) / theta

            # Stationary distribution: X ~ N(mu, sigma^2 / (2*theta))
            stationary_std = sigma / np.sqrt(2 * theta)

            # Current deviation from mu in stationary std units
            current_z = (x[-1] - mu) / stationary_std if stationary_std > 0 else 0

            # R-squared of AR(1) fit
            ss_res = np.sum(residuals**2)
            ss_tot = np.sum((y - np.mean(y))**2)
            r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

            return success_response(
                {
                    "mean_reverting": True,
                    "theta": round(float(theta), 6),
                    "mu": round(float(mu), 4),
                    "sigma": round(float(sigma), 6),
                    "half_life_days": round(float(half_life), 1),
                    "stationary_std": round(float(stationary_std), 4),
                    "current_value": round(float(x[-1]), 4),
                    "current_z_score": round(float(current_z), 3),
                    "ar1_coeff": round(float(b), 6),
                    "r_squared": round(float(r_squared), 4),
                    "n_observations": n,
                    "interpretation": (
                        f"OU process: theta={theta:.3f}, half-life={half_life:.1f} days. "
                        f"Current z-score: {current_z:.2f} "
                        f"({'ENTRY LONG' if current_z < -2 else 'ENTRY SHORT' if current_z > 2 else 'no signal'})."
                    ),
                },
                source="Stat Arb",
            )
        except Exception as e:
            logger.exception("ou_fit failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 2. Distance-Method Pair Selection
    # ------------------------------------------------------------------
    def pairs_distance(
        self,
        universe: List[List[Dict]],
        names: List[str],
        top_n: int = 5,
        formation_days: int = 252,
    ) -> Dict[str, Any]:
        """Find top comoving pairs from a universe using sum of squared deviations.

        Args:
            universe: list of time series (each is [{date, value}])
            names: ticker/name for each series
            top_n: number of top pairs to return
            formation_days: lookback for formation period
        """
        try:
            if len(universe) != len(names):
                return error_response("universe and names must have same length")
            if len(universe) < 2:
                return error_response("Need at least 2 series")

            # Convert to DataFrame
            all_series = {}
            for i, (data, name) in enumerate(zip(universe, names)):
                try:
                    s = _ts_to_series(data, name)
                    all_series[name] = s
                except Exception:
                    continue

            if len(all_series) < 2:
                return error_response("Less than 2 valid series after parsing")

            df = pd.DataFrame(all_series)
            df = df.dropna()
            if formation_days and len(df) > formation_days:
                df = df.iloc[-formation_days:]

            if len(df) < 30:
                return error_response(f"Only {len(df)} overlapping dates; need 30+")

            # Normalize to start at 1.0
            norm = df / df.iloc[0]

            # Compute pairwise SSD
            tickers = list(norm.columns)
            n_tickers = len(tickers)
            pairs = []
            for i in range(n_tickers):
                for j in range(i + 1, n_tickers):
                    ssd = float(np.sum((norm[tickers[i]] - norm[tickers[j]])**2))
                    # Also compute correlation
                    corr = float(norm[tickers[i]].corr(norm[tickers[j]]))
                    pairs.append({
                        "pair": f"{tickers[i]}/{tickers[j]}",
                        "asset_a": tickers[i],
                        "asset_b": tickers[j],
                        "ssd": round(ssd, 4),
                        "correlation": round(corr, 4),
                    })

            # Sort by SSD (lower = more comoving)
            pairs.sort(key=lambda x: x["ssd"])
            top_pairs = pairs[:top_n]

            return success_response(
                {
                    "top_pairs": top_pairs,
                    "total_pairs_evaluated": len(pairs),
                    "n_assets": n_tickers,
                    "formation_period_days": len(df),
                    "method": "Gatev-Goetzmann-Rouwenhorst distance method",
                    "interpretation": (
                        f"Top pair: {top_pairs[0]['pair']} (SSD={top_pairs[0]['ssd']:.4f}, "
                        f"corr={top_pairs[0]['correlation']:.3f}). "
                        f"Lower SSD = more similar normalized price paths."
                    ),
                },
                source="Stat Arb",
            )
        except Exception as e:
            logger.exception("pairs_distance failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 3. Spread Z-Score + Entry/Exit Signals
    # ------------------------------------------------------------------
    def spread_zscore(
        self,
        series_a: List[Dict],
        series_b: List[Dict],
        window: int = 60,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
    ) -> Dict[str, Any]:
        """Compute hedge ratio, spread, rolling z-score, and trade signals.

        Args:
            series_a, series_b: two price series [{date, value}]
            window: rolling window for z-score
            entry_z: z-score threshold for entry (default 2.0)
            exit_z: z-score threshold for exit (default 0.5)
        """
        try:
            sa = _ts_to_series(series_a, "A")
            sb = _ts_to_series(series_b, "B")
            df = _align_series(sa, sb)

            prices_a = df["A"].values
            prices_b = df["B"].values

            # Hedge ratio via OLS: A = beta * B + alpha + epsilon
            from numpy.linalg import lstsq
            X = np.column_stack([np.ones(len(prices_b)), prices_b])
            result = lstsq(X, prices_a, rcond=None)
            alpha, beta = result[0][0], result[0][1]

            # Spread = A - beta * B
            spread = prices_a - beta * prices_b
            residuals = spread - alpha  # de-meaned

            # ADF test on spread
            from statsmodels.tsa.stattools import adfuller
            adf_result = adfuller(spread, maxlag=int(np.sqrt(len(spread))))
            adf_stat, adf_pvalue = adf_result[0], adf_result[1]
            is_cointegrated = adf_pvalue < 0.05

            # Rolling z-score
            spread_series = pd.Series(spread, index=df.index)
            roll_mean = spread_series.rolling(window).mean()
            roll_std = spread_series.rolling(window).std()
            zscore = ((spread_series - roll_mean) / roll_std).dropna()

            # Current signal
            current_z = float(zscore.iloc[-1]) if len(zscore) > 0 else 0
            if current_z < -entry_z:
                signal = "LONG_SPREAD"
                action = f"Buy A, Sell {beta:.3f}×B (spread undervalued)"
            elif current_z > entry_z:
                signal = "SHORT_SPREAD"
                action = f"Sell A, Buy {beta:.3f}×B (spread overvalued)"
            elif abs(current_z) < exit_z:
                signal = "EXIT"
                action = "Close any existing position"
            else:
                signal = "HOLD"
                action = "No action"

            # Z-score history
            recent_z = [
                {"date": d.strftime("%Y-%m-%d"), "zscore": round(float(v), 3)}
                for d, v in zscore.items()
            ]

            return success_response(
                {
                    "hedge_ratio": round(float(beta), 4),
                    "intercept": round(float(alpha), 4),
                    "spread_mean": round(float(np.mean(spread)), 4),
                    "spread_std": round(float(np.std(spread)), 4),
                    "current_zscore": round(current_z, 3),
                    "signal": signal,
                    "action": action,
                    "adf_statistic": round(float(adf_stat), 4),
                    "adf_pvalue": round(float(adf_pvalue), 4),
                    "is_cointegrated": is_cointegrated,
                    "entry_threshold": entry_z,
                    "exit_threshold": exit_z,
                    "window": window,
                    "n_observations": len(df),
                    "recent_zscore": recent_z,
                    "interpretation": (
                        f"Hedge ratio: A = {beta:.3f}×B + {alpha:.2f}. "
                        f"{'Cointegrated' if is_cointegrated else 'NOT cointegrated'} "
                        f"(ADF p={adf_pvalue:.4f}). "
                        f"Current z={current_z:.2f} → {signal}."
                    ),
                },
                source="Stat Arb",
            )
        except Exception as e:
            logger.exception("spread_zscore failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 4. Copula Dependence
    # ------------------------------------------------------------------
    def copula_fit(
        self,
        series_a: List[Dict],
        series_b: List[Dict],
        copula_type: str = "gaussian",
    ) -> Dict[str, Any]:
        """Fit copula to bivariate returns for tail dependence analysis.

        Args:
            series_a, series_b: price series [{date, value}]
            copula_type: "gaussian", "student_t", "clayton", or "gumbel"
        """
        try:
            sa = _ts_to_series(series_a, "A")
            sb = _ts_to_series(series_b, "B")
            df = _align_series(sa, sb)

            # Log returns
            ret_a = np.log(df["A"] / df["A"].shift(1)).dropna().values
            ret_b = np.log(df["B"] / df["B"].shift(1)).dropna().values
            n = min(len(ret_a), len(ret_b))
            ret_a, ret_b = ret_a[:n], ret_b[:n]

            if n < 50:
                return error_response(f"Need >= 50 returns, got {n}")

            # Transform to pseudo-uniform using empirical CDF (ranks)
            u = stats.rankdata(ret_a) / (n + 1)
            v = stats.rankdata(ret_b) / (n + 1)

            # Fit copula based on type
            if copula_type == "gaussian":
                # Gaussian copula: parameter = Pearson correlation of normal quantiles
                z_u = stats.norm.ppf(u)
                z_v = stats.norm.ppf(v)
                rho = float(np.corrcoef(z_u, z_v)[0, 1])
                param = rho
                lower_tail_dep = 0.0  # Gaussian has no tail dependence
                upper_tail_dep = 0.0
                name = "Gaussian"

            elif copula_type == "student_t":
                # Student-t copula: rho + nu (degrees of freedom)
                z_u = stats.norm.ppf(u)
                z_v = stats.norm.ppf(v)
                rho = float(np.corrcoef(z_u, z_v)[0, 1])
                # Estimate nu via method of moments on joint tail
                joint_tail = np.mean((u < 0.1) & (v < 0.1)) / 0.01
                nu_est = max(3, min(30, 4.0 / max(joint_tail - 1, 0.01)))
                param = {"rho": round(rho, 4), "nu": round(nu_est, 1)}
                # Tail dependence for t-copula
                t_val = stats.t.ppf(0.5, nu_est + 1) * np.sqrt((nu_est + 1) * (1 - rho) / (1 + rho))
                lower_tail_dep = upper_tail_dep = round(2 * stats.t.cdf(-abs(t_val), nu_est + 1), 4)
                name = "Student-t"

            elif copula_type == "clayton":
                # Clayton copula: theta via Kendall's tau
                tau = stats.kendalltau(ret_a, ret_b).statistic
                if tau <= 0:
                    return error_response("Clayton copula requires positive dependence (tau > 0)")
                theta = 2 * tau / (1 - tau)
                param = round(float(theta), 4)
                lower_tail_dep = round(2 ** (-1 / theta), 4) if theta > 0 else 0
                upper_tail_dep = 0.0
                name = "Clayton"

            elif copula_type == "gumbel":
                # Gumbel copula: theta via Kendall's tau
                tau = stats.kendalltau(ret_a, ret_b).statistic
                if tau <= 0:
                    return error_response("Gumbel copula requires positive dependence (tau > 0)")
                theta = 1 / (1 - tau)
                param = round(float(theta), 4)
                lower_tail_dep = 0.0
                upper_tail_dep = round(2 - 2 ** (1 / theta), 4) if theta > 1 else 0
                name = "Gumbel"

            else:
                return error_response(f"Unknown copula type: {copula_type}. Use gaussian/student_t/clayton/gumbel")

            # Kendall's tau and Spearman's rho for comparison
            kendall_tau = float(stats.kendalltau(ret_a, ret_b).statistic)
            spearman_rho = float(stats.spearmanr(ret_a, ret_b).statistic)

            # Joint tail frequencies (empirical)
            q10 = 0.10
            q90 = 0.90
            lower_joint = float(np.mean((u < q10) & (v < q10)))
            upper_joint = float(np.mean((u > q90) & (v > q90)))
            expected_independent = q10 ** 2

            return success_response(
                {
                    "copula_type": name,
                    "parameter": param,
                    "lower_tail_dependence": float(lower_tail_dep),
                    "upper_tail_dependence": float(upper_tail_dep),
                    "kendall_tau": round(kendall_tau, 4),
                    "spearman_rho": round(spearman_rho, 4),
                    "empirical_lower_joint_10pct": round(lower_joint, 4),
                    "empirical_upper_joint_90pct": round(upper_joint, 4),
                    "expected_if_independent": round(expected_independent, 4),
                    "n_observations": n,
                    "interpretation": (
                        f"{name} copula fitted. "
                        f"Lower tail dep: {lower_tail_dep:.3f}, Upper tail dep: {upper_tail_dep:.3f}. "
                        f"{'Strong lower tail dependence — assets crash together!' if lower_tail_dep > 0.3 else ''}"
                        f"{'Symmetric tail risk.' if abs(float(lower_tail_dep) - float(upper_tail_dep)) < 0.05 else ''}"
                    ),
                },
                source="Stat Arb",
            )
        except Exception as e:
            logger.exception("copula_fit failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 5. Half-Life of Mean Reversion
    # ------------------------------------------------------------------
    def halflife(self, series: List[Dict]) -> Dict[str, Any]:
        """Estimate mean-reversion half-life via AR(1) regression.

        half_life = -ln(2) / ln(b) where y_t = a + b*y_{t-1} + eps.
        """
        try:
            s = _ts_to_series(series, "spread")
            x = s.values
            n = len(x)
            if n < 30:
                return error_response(f"Need >= 30 points, got {n}")

            # AR(1) regression: x_t = a + b * x_{t-1}
            y = x[1:]
            x_lag = x[:-1]
            X = np.column_stack([np.ones(len(x_lag)), x_lag])
            coeffs = np.linalg.lstsq(X, y, rcond=None)[0]
            a, b = coeffs[0], coeffs[1]

            # Residual analysis
            residuals = y - (a + b * x_lag)
            ss_res = np.sum(residuals**2)
            ss_tot = np.sum((y - np.mean(y))**2)
            r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

            # Durbin-Watson for autocorrelation in residuals
            dw = float(np.sum(np.diff(residuals)**2) / np.sum(residuals**2))

            if b <= 0:
                return success_response(
                    {
                        "mean_reverting": True,
                        "half_life_days": 0.5,
                        "ar1_coeff": round(float(b), 6),
                        "interpretation": "Very strong mean reversion (b <= 0). Half-life < 1 day.",
                        "n_observations": n,
                    },
                    source="Stat Arb",
                )

            if b >= 1:
                return success_response(
                    {
                        "mean_reverting": False,
                        "half_life_days": float("inf"),
                        "ar1_coeff": round(float(b), 6),
                        "interpretation": "No mean reversion (unit root). Series is non-stationary.",
                        "n_observations": n,
                    },
                    source="Stat Arb",
                )

            hl = -np.log(2) / np.log(b)

            # Classification
            if hl < 5:
                speed = "very fast"
                recommendation = "Intraday/short-term strategy"
            elif hl < 20:
                speed = "fast"
                recommendation = "Swing trading (hold 1-4 weeks)"
            elif hl < 60:
                speed = "moderate"
                recommendation = "Position trading (hold 1-3 months)"
            elif hl < 120:
                speed = "slow"
                recommendation = "Long-term position (hold 3-6 months)"
            else:
                speed = "very slow"
                recommendation = "Too slow for practical trading"

            return success_response(
                {
                    "mean_reverting": True,
                    "half_life_days": round(float(hl), 1),
                    "ar1_coeff": round(float(b), 6),
                    "intercept": round(float(a), 6),
                    "r_squared": round(float(r_squared), 4),
                    "durbin_watson": round(dw, 3),
                    "speed": speed,
                    "recommendation": recommendation,
                    "n_observations": n,
                    "interpretation": (
                        f"Half-life: {hl:.1f} days ({speed}). "
                        f"AR(1) b={b:.4f}, R²={r_squared:.3f}. "
                        f"{recommendation}."
                    ),
                },
                source="Stat Arb",
            )
        except Exception as e:
            logger.exception("halflife failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 6. Z-Score Mean-Reversion Backtest
    # ------------------------------------------------------------------
    def backtest(
        self,
        series_a: List[Dict],
        series_b: List[Dict],
        window: int = 60,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
        stop_loss_z: float = 4.0,
        commission_pct: float = 0.001,
    ) -> Dict[str, Any]:
        """Backtest z-score mean-reversion pairs strategy.

        Long spread when z < -entry_z, short when z > entry_z, exit at |z| < exit_z.
        """
        try:
            sa = _ts_to_series(series_a, "A")
            sb = _ts_to_series(series_b, "B")
            df = _align_series(sa, sb)

            prices_a = df["A"].values
            prices_b = df["B"].values
            dates = df.index

            # Compute spread using rolling OLS hedge ratio
            n = len(prices_a)
            spread = np.zeros(n)
            hedge_ratios = np.zeros(n)

            for i in range(window, n):
                y_win = prices_a[i - window:i]
                x_win = prices_b[i - window:i]
                X = np.column_stack([np.ones(window), x_win])
                coeffs = np.linalg.lstsq(X, y_win, rcond=None)[0]
                hedge_ratios[i] = coeffs[1]
                spread[i] = prices_a[i] - coeffs[1] * prices_b[i] - coeffs[0]

            # Z-score
            spread_series = pd.Series(spread[window:], index=dates[window:])
            roll_mean = spread_series.rolling(window).mean()
            roll_std = spread_series.rolling(window).std()
            zscore = ((spread_series - roll_mean) / roll_std).dropna()

            if len(zscore) < 20:
                return error_response("Not enough data after z-score computation")

            # Simulate trading
            position = 0  # 1=long spread, -1=short spread, 0=flat
            trades = []
            pnl_daily = []
            entry_price_a = entry_price_b = 0
            entry_date = None
            current_hedge = 1.0

            valid_dates = zscore.index
            for i, date in enumerate(valid_dates):
                z = zscore.loc[date]
                idx_in_df = df.index.get_loc(date)
                pa = prices_a[idx_in_df]
                pb = prices_b[idx_in_df]
                hr = hedge_ratios[idx_in_df] if idx_in_df < len(hedge_ratios) else current_hedge

                daily_pnl = 0
                if position != 0:
                    # PnL from spread change
                    if i > 0:
                        prev_date = valid_dates[i - 1]
                        prev_idx = df.index.get_loc(prev_date)
                        delta_a = prices_a[idx_in_df] - prices_a[prev_idx]
                        delta_b = prices_b[idx_in_df] - prices_b[prev_idx]
                        daily_pnl = position * (delta_a - current_hedge * delta_b)

                # Entry signals
                if position == 0:
                    if z < -entry_z:
                        position = 1  # long spread: buy A, sell B
                        entry_price_a, entry_price_b = pa, pb
                        current_hedge = hr
                        entry_date = date
                        daily_pnl -= commission_pct * (pa + hr * pb)
                    elif z > entry_z:
                        position = -1  # short spread: sell A, buy B
                        entry_price_a, entry_price_b = pa, pb
                        current_hedge = hr
                        entry_date = date
                        daily_pnl -= commission_pct * (pa + hr * pb)

                # Exit signals
                elif position != 0:
                    should_exit = False
                    if abs(z) < exit_z:
                        should_exit = True
                        exit_reason = "mean_reversion"
                    elif abs(z) > stop_loss_z:
                        should_exit = True
                        exit_reason = "stop_loss"

                    if should_exit:
                        trade_pnl = position * ((pa - entry_price_a) - current_hedge * (pb - entry_price_b))
                        trade_pnl -= commission_pct * (pa + current_hedge * pb)  # exit commission
                        trades.append({
                            "entry_date": entry_date.strftime("%Y-%m-%d"),
                            "exit_date": date.strftime("%Y-%m-%d"),
                            "direction": "LONG" if position == 1 else "SHORT",
                            "pnl": round(float(trade_pnl), 2),
                            "exit_reason": exit_reason,
                            "holding_days": (date - entry_date).days,
                        })
                        position = 0

                pnl_daily.append(daily_pnl)

            # Performance metrics
            pnl_array = np.array(pnl_daily)
            cumulative = np.cumsum(pnl_array)

            total_return = float(np.sum(pnl_array))
            n_trades = len(trades)
            if n_trades > 0:
                wins = [t for t in trades if t["pnl"] > 0]
                win_rate = len(wins) / n_trades
                avg_win = np.mean([t["pnl"] for t in wins]) if wins else 0
                losses = [t for t in trades if t["pnl"] <= 0]
                avg_loss = np.mean([abs(t["pnl"]) for t in losses]) if losses else 0
                avg_hold = np.mean([t["holding_days"] for t in trades])
                profit_factor = (sum(t["pnl"] for t in wins) / abs(sum(t["pnl"] for t in losses))) if losses and sum(t["pnl"] for t in losses) != 0 else float("inf")
            else:
                win_rate = avg_win = avg_loss = avg_hold = 0
                profit_factor = 0

            # Sharpe ratio (annualized)
            if len(pnl_array) > 0 and np.std(pnl_array) > 0:
                sharpe = float(np.mean(pnl_array) / np.std(pnl_array) * np.sqrt(252))
            else:
                sharpe = 0

            # Max drawdown
            peak = np.maximum.accumulate(cumulative)
            drawdown = cumulative - peak
            max_dd = float(np.min(drawdown)) if len(drawdown) > 0 else 0

            return success_response(
                {
                    "total_pnl": round(total_return, 2),
                    "n_trades": n_trades,
                    "win_rate": round(float(win_rate), 3),
                    "avg_win": round(float(avg_win), 2),
                    "avg_loss": round(float(avg_loss), 2),
                    "profit_factor": round(float(profit_factor), 2) if profit_factor != float("inf") else "inf",
                    "sharpe_ratio": round(sharpe, 3),
                    "max_drawdown": round(max_dd, 2),
                    "avg_holding_days": round(float(avg_hold), 1),
                    "trading_period_days": len(pnl_daily),
                    "parameters": {
                        "window": window,
                        "entry_z": entry_z,
                        "exit_z": exit_z,
                        "stop_loss_z": stop_loss_z,
                        "commission_pct": commission_pct,
                    },
                    "recent_trades": trades[-10:] if trades else [],
                    "interpretation": (
                        f"{n_trades} trades over {len(pnl_daily)} days. "
                        f"Win rate: {win_rate:.1%}, Sharpe: {sharpe:.2f}, "
                        f"Max DD: {max_dd:.2f}. "
                        f"{'PROFITABLE' if total_return > 0 else 'UNPROFITABLE'} strategy."
                    ),
                },
                source="Stat Arb",
            )
        except Exception as e:
            logger.exception("backtest failed")
            return error_response(str(e))


# ------------------------------------------------------------------
# Standalone test
# ------------------------------------------------------------------
if __name__ == "__main__":
    import random
    logging.basicConfig(level=logging.INFO)
    adapter = StatArbAdapter()

    # Generate synthetic OU process for testing
    np.random.seed(42)
    n = 500
    theta, mu, sigma = 0.1, 100, 2
    x = [mu]
    for _ in range(n - 1):
        dx = theta * (mu - x[-1]) + sigma * np.random.randn()
        x.append(x[-1] + dx)
    test_data = [{"date": f"2024-{(i//30)+1:02d}-{(i%30)+1:02d}", "value": v} for i, v in enumerate(x)]

    result = adapter.ou_fit(test_data)
    print("OU Fit:", result)

    result = adapter.halflife(test_data)
    print("Half-life:", result)
