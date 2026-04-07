"""Quant Analysis Adapter — Statistical analysis engine for any two time series.

Correlation, lagged correlation, regression, Granger causality, cointegration,
VAR decomposition, event study, regime detection.
Works with the universal format: [{"date": "YYYY-MM-DD", "value": float}, ...]
"""
import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcp_servers.core.responses import error_response, success_response

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans

logger = logging.getLogger(__name__)


class QuantAnalysisAdapter:
    """Statistical analysis engine operating on time-series in universal format."""

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _to_series(data: List[Dict], name: str = "value") -> pd.Series:
        """Convert [{"date": ..., "value": ...}] to a pandas Series indexed by date."""
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.drop_duplicates(subset="date").sort_values("date").set_index("date")
        return df["value"].astype(float).rename(name)

    @staticmethod
    def _align(*series_list: pd.Series, ffill: bool = True) -> pd.DataFrame:
        """Align multiple series by date (inner join), optionally forward-fill first."""
        df = pd.concat(series_list, axis=1, join="inner")
        if ffill:
            df = df.ffill()
        df = df.dropna()
        return df

    @staticmethod
    def _significance(p: float) -> str:
        if p < 0.01:
            return "***"
        elif p < 0.05:
            return "**"
        elif p < 0.1:
            return "*"
        return ""

    @staticmethod
    def _interpret_corr(r: float) -> str:
        ar = abs(r)
        direction = "positive" if r >= 0 else "negative"
        if ar >= 0.8:
            strength = "very strong"
        elif ar >= 0.6:
            strength = "strong"
        elif ar >= 0.4:
            strength = "moderate"
        elif ar >= 0.2:
            strength = "weak"
        else:
            strength = "very weak"
        return f"{strength} {direction}"

    # ------------------------------------------------------------------ #
    # 1. correlation
    # ------------------------------------------------------------------ #

    def correlation(
        self,
        series_a: List[Dict],
        series_b: List[Dict],
        method: str = "pearson",
    ) -> Dict[str, Any]:
        """Compute correlation between two time series.

        Args:
            series_a: [{"date": "YYYY-MM-DD", "value": float}, ...]
            series_b: same format
            method: pearson | spearman | kendall
        """
        try:
            sa = self._to_series(series_a, "a")
            sb = self._to_series(series_b, "b")
            df = self._align(sa, sb)

            if len(df) < 3:
                return error_response(f"Insufficient overlapping data: {len(df)} points (need >= 3)")

            a_vals, b_vals = df["a"].values, df["b"].values

            method = method.lower()
            if method == "pearson":
                r, p = stats.pearsonr(a_vals, b_vals)
            elif method == "spearman":
                r, p = stats.spearmanr(a_vals, b_vals)
            elif method == "kendall":
                r, p = stats.kendalltau(a_vals, b_vals)
            else:
                return error_response(f"Unknown method: {method}. Use pearson/spearman/kendall")

            return success_response(
                {
                    "method": method,
                    "correlation": round(float(r), 6),
                    "p_value": round(float(p), 8),
                    "significance": self._significance(p),
                    "n_observations": len(df),
                    "interpretation": self._interpret_corr(r),
                    "date_range": {
                        "start": str(df.index.min().date()),
                        "end": str(df.index.max().date()),
                    },
                },
                source="Quant Analysis",
            )
        except Exception as e:
            logger.exception("correlation failed")
            return error_response(str(e))

    # ------------------------------------------------------------------ #
    # 2. lagged_correlation
    # ------------------------------------------------------------------ #

    def lagged_correlation(
        self,
        series_a: List[Dict],
        series_b: List[Dict],
        max_lag: int = 12,
    ) -> Dict[str, Any]:
        """Compute correlation at each lag 0..max_lag (shift series_b forward).

        Positive lag means series_b is shifted forward — i.e. series_a *leads* series_b.
        """
        try:
            sa = self._to_series(series_a, "a")
            sb = self._to_series(series_b, "b")
            df = self._align(sa, sb)

            if len(df) < max_lag + 5:
                return error_response(f"Insufficient data: {len(df)} points for max_lag={max_lag}")

            results = []
            for lag in range(0, max_lag + 1):
                if lag == 0:
                    a_v = df["a"].values
                    b_v = df["b"].values
                else:
                    a_v = df["a"].values[:-lag]
                    b_v = df["b"].values[lag:]

                if len(a_v) < 3:
                    continue
                r, p = stats.pearsonr(a_v, b_v)
                results.append({
                    "lag": lag,
                    "correlation": round(float(r), 6),
                    "p_value": round(float(p), 8),
                    "significance": self._significance(p),
                    "n_observations": len(a_v),
                })

            if not results:
                return error_response("No valid lag results computed")

            best = max(results, key=lambda x: abs(x["correlation"]))

            return success_response(
                {
                    "lag_results": results,
                    "best_lag": best["lag"],
                    "best_correlation": best["correlation"],
                    "best_p_value": best["p_value"],
                    "interpretation": (
                        f"Strongest relationship at lag {best['lag']} "
                        f"({self._interpret_corr(best['correlation'])}). "
                        f"Series A leads series B by {best['lag']} period(s)."
                        if best["lag"] > 0
                        else f"Strongest at lag 0 ({self._interpret_corr(best['correlation'])}). Contemporaneous."
                    ),
                    "n_total_observations": len(df),
                },
                source="Quant Analysis",
            )
        except Exception as e:
            logger.exception("lagged_correlation failed")
            return error_response(str(e))

    # ------------------------------------------------------------------ #
    # 3. regression
    # ------------------------------------------------------------------ #

    def regression(
        self,
        dependent: List[Dict],
        independents: List[List[Dict]],
        independent_names: Optional[List[str]] = None,
        method: str = "OLS",
    ) -> Dict[str, Any]:
        """Multi-variable regression: Y = b0 + b1*X1 + b2*X2 + ...

        Args:
            dependent: Y series [{date, value}]
            independents: list of X series, each [{date, value}]
            independent_names: labels for X variables
            method: OLS (default)
        """
        try:
            import statsmodels.api as sm

            y_s = self._to_series(dependent, "Y")
            x_series = []
            for i, ind in enumerate(independents):
                name = independent_names[i] if independent_names and i < len(independent_names) else f"X{i+1}"
                x_series.append(self._to_series(ind, name))

            all_s = [y_s] + x_series
            df = self._align(*all_s)

            if len(df) < len(x_series) + 2:
                return error_response(f"Insufficient data after alignment: {len(df)} rows")

            Y = df["Y"]
            X = df.drop(columns=["Y"])
            X = sm.add_constant(X)

            model = sm.OLS(Y, X).fit()

            coefs = {}
            for name, coef, pval in zip(model.params.index, model.params.values, model.pvalues.values):
                coefs[name] = {
                    "coefficient": round(float(coef), 8),
                    "p_value": round(float(pval), 8),
                    "significance": self._significance(pval),
                }

            residuals = model.resid
            return success_response(
                {
                    "method": method,
                    "coefficients": coefs,
                    "r_squared": round(float(model.rsquared), 6),
                    "adj_r_squared": round(float(model.rsquared_adj), 6),
                    "f_statistic": round(float(model.fvalue), 4),
                    "f_p_value": round(float(model.f_pvalue), 8),
                    "f_significance": self._significance(model.f_pvalue),
                    "n_observations": int(model.nobs),
                    "residual_stats": {
                        "mean": round(float(residuals.mean()), 8),
                        "std": round(float(residuals.std()), 6),
                        "min": round(float(residuals.min()), 6),
                        "max": round(float(residuals.max()), 6),
                    },
                    "durbin_watson": round(float(sm.stats.durbin_watson(residuals)), 4),
                    "date_range": {
                        "start": str(df.index.min().date()),
                        "end": str(df.index.max().date()),
                    },
                },
                source="Quant Analysis",
            )
        except Exception as e:
            logger.exception("regression failed")
            return error_response(str(e))

    # ------------------------------------------------------------------ #
    # 4. granger_causality
    # ------------------------------------------------------------------ #

    def granger_causality(
        self,
        series_a: List[Dict],
        series_b: List[Dict],
        max_lag: int = 4,
    ) -> Dict[str, Any]:
        """Granger causality test: does A Granger-cause B?

        Tests whether lagged values of A improve prediction of B
        beyond B's own lagged values.
        """
        try:
            from statsmodels.tsa.stattools import grangercausalitytests

            sa = self._to_series(series_a, "a")
            sb = self._to_series(series_b, "b")
            df = self._align(sa, sb)

            if len(df) < max_lag * 3 + 5:
                return error_response(f"Insufficient data: {len(df)} rows for max_lag={max_lag}")

            # grangercausalitytests expects [Y, X] — tests if X Granger-causes Y
            # We test: does A Granger-cause B → pass [B, A]
            data_array = df[["b", "a"]].values
            gc_results = grangercausalitytests(data_array, maxlag=max_lag, verbose=False)

            lag_results = []
            any_significant = False
            best_lag = None
            best_p = 1.0

            for lag in range(1, max_lag + 1):
                test_result = gc_results[lag]
                # test_result[0] is dict of test results
                f_stat = test_result[0]["ssr_ftest"][0]
                p_val = test_result[0]["ssr_ftest"][1]
                significant = p_val < 0.05

                if significant:
                    any_significant = True
                if p_val < best_p:
                    best_p = p_val
                    best_lag = lag

                lag_results.append({
                    "lag": lag,
                    "f_statistic": round(float(f_stat), 4),
                    "p_value": round(float(p_val), 8),
                    "significance": self._significance(p_val),
                    "significant_at_5pct": significant,
                })

            if any_significant:
                interp = f"A Granger-causes B (strongest at lag {best_lag}, p={best_p:.6f})"
            else:
                interp = "No Granger causality found from A to B at any tested lag"

            return success_response(
                {
                    "direction": "A → B",
                    "lag_results": lag_results,
                    "granger_causes": any_significant,
                    "best_lag": best_lag,
                    "best_p_value": round(float(best_p), 8),
                    "interpretation": interp,
                    "n_observations": len(df),
                },
                source="Quant Analysis",
            )
        except Exception as e:
            logger.exception("granger_causality failed")
            return error_response(str(e))

    # ------------------------------------------------------------------ #
    # 5. cointegration
    # ------------------------------------------------------------------ #

    def cointegration(
        self,
        series_a: List[Dict],
        series_b: List[Dict],
    ) -> Dict[str, Any]:
        """Engle-Granger cointegration test between two series.

        Tests whether a long-run equilibrium relationship exists
        (useful for pairs trading, macro analysis).
        """
        try:
            from statsmodels.tsa.stattools import coint

            sa = self._to_series(series_a, "a")
            sb = self._to_series(series_b, "b")
            df = self._align(sa, sb)

            if len(df) < 20:
                return error_response(f"Insufficient data: {len(df)} rows (need >= 20)")

            coint_stat, p_value, crit_values = coint(df["a"].values, df["b"].values)

            # Hedge ratio via OLS: a = beta * b + alpha
            import statsmodels.api as sm
            X = sm.add_constant(df["b"].values)
            model = sm.OLS(df["a"].values, X).fit()
            hedge_ratio = float(model.params[1])

            cointegrated = p_value < 0.05

            return success_response(
                {
                    "coint_statistic": round(float(coint_stat), 6),
                    "p_value": round(float(p_value), 8),
                    "significance": self._significance(p_value),
                    "critical_values": {
                        "1%": round(float(crit_values[0]), 6),
                        "5%": round(float(crit_values[1]), 6),
                        "10%": round(float(crit_values[2]), 6),
                    },
                    "cointegrated": cointegrated,
                    "hedge_ratio": round(hedge_ratio, 6),
                    "interpretation": (
                        f"Long-run equilibrium exists (p={p_value:.4f}). "
                        f"Hedge ratio: {hedge_ratio:.4f}"
                        if cointegrated
                        else f"No cointegration found (p={p_value:.4f})"
                    ),
                    "n_observations": len(df),
                    "date_range": {
                        "start": str(df.index.min().date()),
                        "end": str(df.index.max().date()),
                    },
                },
                source="Quant Analysis",
            )
        except Exception as e:
            logger.exception("cointegration failed")
            return error_response(str(e))

    # ------------------------------------------------------------------ #
    # 6. var_decomposition
    # ------------------------------------------------------------------ #

    def var_decomposition(
        self,
        series_dict: Dict[str, List[Dict]],
        lags: int = 4,
        periods: int = 10,
    ) -> Dict[str, Any]:
        """Fit a VAR model and compute forecast error variance decomposition.

        Args:
            series_dict: {"name1": [{date, value}], "name2": [...], ...}
            lags: number of lags for VAR
            periods: forecast horizon for decomposition
        """
        try:
            from statsmodels.tsa.api import VAR

            if len(series_dict) < 2:
                return error_response("Need at least 2 variables for VAR decomposition")

            all_series = []
            names = list(series_dict.keys())
            for name in names:
                all_series.append(self._to_series(series_dict[name], name))

            df = self._align(*all_series)

            if len(df) < lags * 3 + 10:
                return error_response(f"Insufficient data: {len(df)} rows for {lags} lags")

            # Difference if needed for stationarity (simple first-difference)
            df_diff = df.diff().dropna()

            model = VAR(df_diff)
            fitted = model.fit(maxlags=lags, ic=None)

            fevd = fitted.fevd(periods)

            # Build decomposition table
            decomp = {}
            for i, target_name in enumerate(names):
                decomp[target_name] = {}
                # fevd.decomp is array (n_periods, n_vars, n_vars)
                # fevd.decomp[period][target_var][shock_var]
                for j, shock_name in enumerate(names):
                    # Take last period (full horizon)
                    pct = float(fevd.decomp[i][-1][j]) * 100
                    decomp[target_name][shock_name] = round(pct, 2)

            return success_response(
                {
                    "lags_used": lags,
                    "forecast_horizon": periods,
                    "variables": names,
                    "variance_decomposition": decomp,
                    "aic": round(float(fitted.aic), 4),
                    "bic": round(float(fitted.bic), 4),
                    "interpretation": (
                        f"VAR({lags}) fitted on {len(names)} variables, "
                        f"{len(df_diff)} observations. "
                        f"Decomposition shows % of forecast error variance "
                        f"explained by each variable at horizon {periods}."
                    ),
                    "n_observations": len(df_diff),
                },
                source="Quant Analysis",
            )
        except Exception as e:
            logger.exception("var_decomposition failed")
            return error_response(str(e))

    # ------------------------------------------------------------------ #
    # 7. event_study
    # ------------------------------------------------------------------ #

    def event_study(
        self,
        price_series: List[Dict],
        event_dates: List[str],
        window_before: int = 20,
        window_after: int = 60,
    ) -> Dict[str, Any]:
        """Event study: measure average abnormal returns around event dates.

        Args:
            price_series: daily prices [{date, value}]
            event_dates: list of "YYYY-MM-DD" event dates
            window_before: trading days before event
            window_after: trading days after event
        """
        try:
            s = self._to_series(price_series, "price")
            s = s.sort_index()

            # Compute daily returns
            returns = s.pct_change().dropna()

            if len(returns) < window_before + window_after + 10:
                return error_response("Insufficient price data for the requested window")

            event_dates_parsed = pd.to_datetime(event_dates)
            total_window = window_before + window_after + 1

            # Collect return windows around each event
            windows = []
            valid_events = []
            for ev_date in event_dates_parsed:
                # Find nearest trading date
                idx = returns.index.searchsorted(ev_date)
                if idx >= len(returns.index):
                    idx = len(returns.index) - 1
                actual_date = returns.index[idx]

                pos = returns.index.get_loc(actual_date)
                start = pos - window_before
                end = pos + window_after + 1

                if start < 0 or end > len(returns):
                    continue

                window_returns = returns.iloc[start:end].values
                if len(window_returns) == total_window:
                    windows.append(window_returns)
                    valid_events.append(str(actual_date.date()))

            if not windows:
                return error_response("No events had sufficient data within the requested window")

            windows_arr = np.array(windows)
            avg_returns = np.mean(windows_arr, axis=0)
            car = np.cumsum(avg_returns)

            # T-test on CAR at event+window_after
            if len(windows) > 1:
                final_cars = np.sum(windows_arr[:, window_before:], axis=1)
                t_stat, t_p = stats.ttest_1samp(final_cars, 0)
            else:
                t_stat = float("nan")
                t_p = float("nan")

            # Build day-by-day results
            daily = []
            for i in range(total_window):
                day_rel = i - window_before
                daily.append({
                    "relative_day": day_rel,
                    "avg_return": round(float(avg_returns[i]), 8),
                    "cumulative_abnormal_return": round(float(car[i]), 8),
                })

            significant = not np.isnan(t_p) and t_p < 0.05

            return success_response(
                {
                    "n_events": len(windows),
                    "valid_event_dates": valid_events,
                    "window_before": window_before,
                    "window_after": window_after,
                    "daily_results": daily,
                    "car_at_end": round(float(car[-1]), 6),
                    "t_statistic": round(float(t_stat), 4) if not np.isnan(t_stat) else None,
                    "p_value": round(float(t_p), 8) if not np.isnan(t_p) else None,
                    "significance": self._significance(t_p) if not np.isnan(t_p) else "",
                    "significant": significant,
                    "interpretation": (
                        f"CAR = {car[-1]:.4%} over {window_after} days post-event "
                        f"across {len(windows)} events. "
                        + (f"Statistically significant (p={t_p:.4f})." if significant
                           else "Not statistically significant." if not np.isnan(t_p)
                           else "Only 1 event — no t-test.")
                    ),
                },
                source="Quant Analysis",
            )
        except Exception as e:
            logger.exception("event_study failed")
            return error_response(str(e))

    # ------------------------------------------------------------------ #
    # 8. regime_detection
    # ------------------------------------------------------------------ #

    def regime_detection(
        self,
        series: List[Dict],
        n_regimes: int = 2,
        rolling_window: int = 20,
    ) -> Dict[str, Any]:
        """Detect market regimes using rolling statistics + K-means clustering.

        Uses rolling mean return and volatility over `rolling_window` periods,
        then clusters them into `n_regimes` regimes.
        """
        try:
            s = self._to_series(series, "value")
            s = s.sort_index()

            returns = s.pct_change().dropna()

            if len(returns) < rolling_window + 10:
                return error_response(f"Insufficient data: {len(returns)} return observations")

            roll_mean = returns.rolling(rolling_window).mean().dropna()
            roll_std = returns.rolling(rolling_window).std().dropna()

            # Align
            common_idx = roll_mean.index.intersection(roll_std.index)
            features = pd.DataFrame({
                "mean_return": roll_mean[common_idx].values,
                "volatility": roll_std[common_idx].values,
            }, index=common_idx)

            if len(features) < n_regimes * 3:
                return error_response(f"Insufficient data for {n_regimes} regimes after rolling")

            # Normalize for clustering
            feat_norm = (features - features.mean()) / features.std()

            kmeans = KMeans(n_clusters=n_regimes, n_init=10, random_state=42)
            labels = kmeans.fit_predict(feat_norm.values)
            features["regime"] = labels

            # Order regimes by volatility (0 = lowest vol)
            regime_vols = features.groupby("regime")["volatility"].mean().sort_values()
            regime_map = {old: new for new, old in enumerate(regime_vols.index)}
            features["regime"] = features["regime"].map(regime_map)

            # Build regime segments
            regimes = []
            current_regime = int(features["regime"].iloc[0])
            seg_start = features.index[0]

            for i in range(1, len(features)):
                r = int(features["regime"].iloc[i])
                if r != current_regime:
                    seg_end = features.index[i - 1]
                    seg_data = features.loc[seg_start:seg_end]
                    regimes.append({
                        "start_date": str(seg_start.date()),
                        "end_date": str(seg_end.date()),
                        "regime_id": current_regime,
                        "mean_return": round(float(seg_data["mean_return"].mean()), 8),
                        "volatility": round(float(seg_data["volatility"].mean()), 8),
                        "duration_days": (seg_end - seg_start).days,
                    })
                    current_regime = r
                    seg_start = features.index[i]

            # Last segment
            seg_end = features.index[-1]
            seg_data = features.loc[seg_start:seg_end]
            regimes.append({
                "start_date": str(seg_start.date()),
                "end_date": str(seg_end.date()),
                "regime_id": current_regime,
                "mean_return": round(float(seg_data["mean_return"].mean()), 8),
                "volatility": round(float(seg_data["volatility"].mean()), 8),
                "duration_days": (seg_end - seg_start).days,
            })

            # Regime summary
            summary = {}
            for rid in range(n_regimes):
                mask = features["regime"] == rid
                if mask.sum() == 0:
                    continue
                summary[f"regime_{rid}"] = {
                    "mean_return": round(float(features.loc[mask, "mean_return"].mean()), 8),
                    "avg_volatility": round(float(features.loc[mask, "volatility"].mean()), 8),
                    "pct_of_time": round(float(mask.sum() / len(features) * 100), 2),
                }

            current = int(features["regime"].iloc[-1])

            return success_response(
                {
                    "n_regimes": n_regimes,
                    "rolling_window": rolling_window,
                    "regimes": regimes,
                    "regime_summary": summary,
                    "current_regime": current,
                    "current_regime_since": regimes[-1]["start_date"],
                    "total_segments": len(regimes),
                    "interpretation": (
                        f"Detected {n_regimes} regimes over {len(features)} periods. "
                        f"Currently in regime {current} "
                        f"(since {regimes[-1]['start_date']}). "
                        f"Regime 0 = low volatility, Regime {n_regimes-1} = high volatility."
                    ),
                    "n_observations": len(features),
                },
                source="Quant Analysis",
            )
        except Exception as e:
            logger.exception("regime_detection failed")
            return error_response(str(e))
