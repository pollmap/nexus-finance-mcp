"""
Timeseries Adapter - Time Series Analysis Engine.

Provides statistical time series analysis:
- Seasonal decomposition (STL)
- Stationarity tests (ADF, KPSS)
- ARIMA forecasting
- Seasonality pattern extraction
- Changepoint detection (CUSUM-based)
- Cross-correlation analysis

No external API required. Uses statsmodels + scipy + numpy.

Run standalone test: python -m mcp_servers.adapters.timeseries_adapter
"""
import logging
import sys
import os
import warnings
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import signal
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller, kpss

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)


class TimeseriesAdapter:
    """Time series analysis engine using statsmodels + scipy."""

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_series(data: List[Dict[str, Any]]) -> pd.Series:
        """Convert list[{date, value}] → pd.Series with DatetimeIndex.

        Handles NaN via forward fill, sorts by date.
        """
        if not data:
            raise ValueError("Empty series data")

        df = pd.DataFrame(data)
        if "date" not in df.columns or "value" not in df.columns:
            raise ValueError("Each element must have 'date' and 'value' keys")

        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").set_index("date")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df["value"] = df["value"].ffill().bfill()

        series = df["value"]
        series.name = "value"
        return series

    @staticmethod
    def _series_to_list(series: pd.Series) -> List[Dict[str, Any]]:
        """pd.Series → list[{date, value}]."""
        result = []
        for dt, val in series.items():
            v = float(val) if pd.notna(val) else None
            result.append({"date": dt.strftime("%Y-%m-%d"), "value": v})
        return result

    @staticmethod
    def _detect_freq(series: pd.Series) -> int:
        """Auto-detect frequency from median date gap."""
        if len(series) < 3:
            return 12
        diffs = series.index.to_series().diff().dropna()
        median_days = diffs.dt.days.median()
        if median_days <= 1.5:
            return 365  # daily
        elif median_days <= 8:
            return 52  # weekly
        elif median_days <= 35:
            return 12  # monthly
        elif median_days <= 100:
            return 4  # quarterly
        else:
            return 1  # yearly

    # ------------------------------------------------------------------
    # 1. decompose
    # ------------------------------------------------------------------

    def decompose(
        self,
        series: List[Dict[str, Any]],
        freq: Optional[int] = None,
        model: str = "additive",
    ) -> Dict[str, Any]:
        """Seasonal decomposition (trend + seasonal + residual).

        Args:
            series: list of {date, value}
            freq: period (12=monthly, 52=weekly, 365=daily). Auto-detect if None.
            model: 'additive' or 'multiplicative'
        """
        try:
            ts = self._to_series(series)

            if freq is None:
                freq = self._detect_freq(ts)
            freq = min(freq, len(ts) // 2)

            if len(ts) < 2 * freq:
                return error_response(f"Need at least {2 * freq} observations for freq={freq}, got {len(ts)}")

            if model not in ("additive", "multiplicative"):
                model = "additive"

            # multiplicative requires all positive values
            if model == "multiplicative" and (ts <= 0).any():
                model = "additive"
                logger.warning("Switched to additive: series contains non-positive values")

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = seasonal_decompose(ts, model=model, period=freq)

            # seasonal strength: 1 - Var(resid) / Var(seasonal + resid)
            seasonal_plus_resid = result.seasonal + result.resid
            seasonal_plus_resid = seasonal_plus_resid.dropna()
            resid_clean = result.resid.dropna()
            if seasonal_plus_resid.var() > 0:
                seasonal_strength = max(
                    0.0,
                    min(1.0, 1.0 - resid_clean.var() / seasonal_plus_resid.var()),
                )
            else:
                seasonal_strength = 0.0

            return success_response(
                {
                    "model": model,
                    "freq": freq,
                    "trend": self._series_to_list(result.trend.dropna()),
                    "seasonal": self._series_to_list(result.seasonal),
                    "residual": self._series_to_list(result.resid.dropna()),
                    "seasonal_strength": round(seasonal_strength, 4),
                    "n_observations": len(ts),
                },
                source="Time Series",
            )
        except Exception as e:
            logger.exception("decompose failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 2. stationarity_test
    # ------------------------------------------------------------------

    def stationarity_test(self, series: List[Dict[str, Any]]) -> Dict[str, Any]:
        """ADF + KPSS stationarity tests."""
        try:
            ts = self._to_series(series)

            if len(ts) < 8:
                return error_response(f"Need at least 8 observations, got {len(ts)}")

            # ADF test
            adf_result = adfuller(ts, autolag="AIC")
            adf_stat = float(adf_result[0])
            adf_pvalue = float(adf_result[1])

            # KPSS test — suppress warnings about p-value bounds
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                kpss_result = kpss(ts, regression="c", nlags="auto")
            kpss_stat = float(kpss_result[0])
            kpss_pvalue = float(kpss_result[1])

            # Stationary if ADF rejects H0 (p<0.05) AND KPSS fails to reject (p>0.05)
            is_stationary = adf_pvalue < 0.05 and kpss_pvalue > 0.05

            # Determine recommendation
            if is_stationary:
                recommended_action = "Series is stationary. No differencing needed."
            elif adf_pvalue >= 0.05 and kpss_pvalue <= 0.05:
                recommended_action = "Series is non-stationary. Apply first differencing (d=1)."
            elif adf_pvalue < 0.05 and kpss_pvalue <= 0.05:
                recommended_action = "Series is difference-stationary (trend-stationary). Consider detrending or differencing."
            else:
                recommended_action = "Inconclusive. Consider visual inspection and further tests."

            return success_response(
                {
                    "adf_stat": round(adf_stat, 4),
                    "adf_pvalue": round(adf_pvalue, 4),
                    "adf_critical_values": {
                        k: round(v, 4) for k, v in adf_result[4].items()
                    },
                    "kpss_stat": round(kpss_stat, 4),
                    "kpss_pvalue": round(kpss_pvalue, 4),
                    "is_stationary": is_stationary,
                    "recommended_action": recommended_action,
                    "n_observations": len(ts),
                },
                source="Time Series",
            )
        except Exception as e:
            logger.exception("stationarity_test failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 3. forecast
    # ------------------------------------------------------------------

    def forecast(
        self,
        series: List[Dict[str, Any]],
        horizon: int = 6,
        model: str = "auto",
    ) -> Dict[str, Any]:
        """ARIMA forecast with automatic order selection.

        Tries (1,1,1), (2,1,1), (1,1,2), (0,1,1), (1,0,1) and picks best AIC.
        """
        try:
            ts = self._to_series(series)

            if len(ts) < 10:
                return error_response(f"Need at least 10 observations, got {len(ts)}")

            horizon = max(1, min(horizon, 60))

            # Determine differencing via ADF
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                adf_p = adfuller(ts, autolag="AIC")[1]
            d = 0 if adf_p < 0.05 else 1

            # Candidate orders
            orders = [
                (1, d, 1),
                (2, d, 1),
                (1, d, 2),
                (0, d, 1),
                (1, d, 0),
                (2, d, 2),
            ]

            best_aic = np.inf
            best_model = None
            best_order = None

            for order in orders:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        m = ARIMA(ts, order=order).fit()
                    if m.aic < best_aic:
                        best_aic = m.aic
                        best_model = m
                        best_order = order
                except Exception:
                    continue

            if best_model is None:
                return error_response("All ARIMA models failed to fit. Data may be insufficient or degenerate.")

            # Forecast
            fc = best_model.get_forecast(steps=horizon)
            pred_mean = fc.predicted_mean
            ci_80 = fc.conf_int(alpha=0.20)
            ci_95 = fc.conf_int(alpha=0.05)

            # Generate future dates
            last_date = ts.index[-1]
            detected_freq = self._detect_freq(ts)
            if detected_freq >= 365:
                delta = timedelta(days=1)
            elif detected_freq >= 52:
                delta = timedelta(weeks=1)
            elif detected_freq >= 12:
                delta = timedelta(days=30)
            elif detected_freq >= 4:
                delta = timedelta(days=91)
            else:
                delta = timedelta(days=365)

            predictions = []
            for i in range(horizon):
                future_date = last_date + delta * (i + 1)
                predictions.append({
                    "date": future_date.strftime("%Y-%m-%d"),
                    "predicted": round(float(pred_mean.iloc[i]), 4),
                    "lower_80": round(float(ci_80.iloc[i, 0]), 4),
                    "upper_80": round(float(ci_80.iloc[i, 1]), 4),
                    "lower_95": round(float(ci_95.iloc[i, 0]), 4),
                    "upper_95": round(float(ci_95.iloc[i, 1]), 4),
                })

            return success_response(
                {
                    "model": f"ARIMA{best_order}",
                    "aic": round(best_aic, 2),
                    "horizon": horizon,
                    "predictions": predictions,
                    "n_observations": len(ts),
                },
                source="Time Series",
            )
        except Exception as e:
            logger.exception("forecast failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 4. seasonality
    # ------------------------------------------------------------------

    def seasonality(
        self,
        series: List[Dict[str, Any]],
        freq: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Extract seasonal pattern, strength, peak/trough periods."""
        try:
            ts = self._to_series(series)

            if freq is None:
                freq = self._detect_freq(ts)
            freq = min(freq, len(ts) // 2)

            if len(ts) < 2 * freq:
                return error_response(f"Need at least {2 * freq} observations for freq={freq}, got {len(ts)}")

            model = "additive"
            if (ts <= 0).any():
                model = "additive"

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = seasonal_decompose(ts, model=model, period=freq)

            seasonal = result.seasonal.dropna()

            # Compute average seasonal value per period position
            seasonal_pattern: Dict[int, float] = {}
            if freq <= 12:
                # Group by month
                grouped = seasonal.groupby(seasonal.index.month).mean()
                for month, val in grouped.items():
                    seasonal_pattern[int(month)] = round(float(val), 4)
            elif freq <= 52:
                # Group by week
                grouped = seasonal.groupby(seasonal.index.isocalendar().week).mean()
                for week, val in grouped.items():
                    seasonal_pattern[int(week)] = round(float(val), 4)
            else:
                # Group by day-of-year
                grouped = seasonal.groupby(seasonal.index.dayofyear).mean()
                for doy, val in grouped.items():
                    seasonal_pattern[int(doy)] = round(float(val), 4)

            # Seasonal strength
            seasonal_plus_resid = result.seasonal + result.resid
            seasonal_plus_resid = seasonal_plus_resid.dropna()
            resid_clean = result.resid.dropna()
            if seasonal_plus_resid.var() > 0:
                seasonal_strength = max(
                    0.0,
                    min(1.0, 1.0 - resid_clean.var() / seasonal_plus_resid.var()),
                )
            else:
                seasonal_strength = 0.0

            # Peak and trough
            if seasonal_pattern:
                peak_period = max(seasonal_pattern, key=seasonal_pattern.get)
                trough_period = min(seasonal_pattern, key=seasonal_pattern.get)
            else:
                peak_period = None
                trough_period = None

            return success_response(
                {
                    "freq": freq,
                    "seasonal_pattern": seasonal_pattern,
                    "seasonal_strength": round(seasonal_strength, 4),
                    "peak_period": peak_period,
                    "trough_period": trough_period,
                    "n_observations": len(ts),
                },
                source="Time Series",
            )
        except Exception as e:
            logger.exception("seasonality failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 5. changepoint_detection
    # ------------------------------------------------------------------

    def changepoint_detection(
        self,
        series: List[Dict[str, Any]],
        n_changepoints: int = 3,
    ) -> Dict[str, Any]:
        """Detect changepoints using CUSUM + rolling mean approach.

        Finds points where the rolling mean changes most significantly.
        """
        try:
            ts = self._to_series(series)

            if len(ts) < 10:
                return error_response(f"Need at least 10 observations, got {len(ts)}")

            n_changepoints = max(1, min(n_changepoints, len(ts) // 4))
            values = ts.values.astype(float)
            n = len(values)

            # Window size: ~10% of data, at least 3
            window = max(3, n // 10)

            # Rolling mean
            rolling = pd.Series(values).rolling(window=window, center=True).mean().values

            # Compute absolute change in rolling mean
            roll_diff = np.zeros(n)
            for i in range(window, n - window):
                before = np.nanmean(rolling[max(0, i - window) : i])
                after = np.nanmean(rolling[i : min(n, i + window)])
                if not (np.isnan(before) or np.isnan(after)):
                    roll_diff[i] = abs(after - before)

            # Find top n peaks with minimum distance between them
            min_distance = max(window, n // (n_changepoints * 3))
            peaks, _ = signal.find_peaks(roll_diff, distance=min_distance)

            if len(peaks) == 0:
                return success_response(
                    {
                        "changepoints": [],
                        "n_observations": n,
                        "message": "No significant changepoints detected",
                    },
                    source="Time Series",
                )

            # Sort by magnitude and take top n
            peak_magnitudes = roll_diff[peaks]
            top_indices = peaks[np.argsort(peak_magnitudes)[::-1][:n_changepoints]]
            top_indices = np.sort(top_indices)

            changepoints = []
            for idx in top_indices:
                before_mean = float(np.mean(values[max(0, idx - window) : idx]))
                after_mean = float(np.mean(values[idx : min(n, idx + window)]))
                changepoints.append({
                    "date": ts.index[idx].strftime("%Y-%m-%d"),
                    "index": int(idx),
                    "before_mean": round(before_mean, 4),
                    "after_mean": round(after_mean, 4),
                    "change_magnitude": round(after_mean - before_mean, 4),
                })

            return success_response(
                {
                    "changepoints": changepoints,
                    "n_changepoints_requested": n_changepoints,
                    "n_changepoints_found": len(changepoints),
                    "n_observations": n,
                },
                source="Time Series",
            )
        except Exception as e:
            logger.exception("changepoint_detection failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 6. cross_correlation
    # ------------------------------------------------------------------

    def cross_correlation(
        self,
        series_a: List[Dict[str, Any]],
        series_b: List[Dict[str, Any]],
        max_lag: int = 12,
    ) -> Dict[str, Any]:
        """Cross-correlation between two series for lags -max_lag to +max_lag."""
        try:
            ts_a = self._to_series(series_a)
            ts_b = self._to_series(series_b)

            # Align on common dates
            common = ts_a.index.intersection(ts_b.index)
            if len(common) < 5:
                return error_response(f"Only {len(common)} overlapping dates. Need at least 5.")

            a = ts_a.loc[common].values.astype(float)
            b = ts_b.loc[common].values.astype(float)

            max_lag = max(1, min(max_lag, len(common) // 3))

            # Standardize
            a_std = (a - a.mean()) / (a.std() + 1e-12)
            b_std = (b - b.mean()) / (b.std() + 1e-12)

            n = len(a_std)
            ccf_values = []

            for lag in range(-max_lag, max_lag + 1):
                if lag >= 0:
                    corr = np.corrcoef(a_std[: n - lag], b_std[lag:])[0, 1]
                else:
                    corr = np.corrcoef(a_std[-lag:], b_std[: n + lag])[0, 1]
                ccf_values.append({
                    "lag": lag,
                    "ccf": round(float(corr), 4) if not np.isnan(corr) else 0.0,
                })

            # Find max absolute correlation
            max_entry = max(ccf_values, key=lambda x: abs(x["ccf"]))
            max_lag_val = max_entry["lag"]
            max_ccf = max_entry["ccf"]

            # Interpretation
            if abs(max_ccf) < 0.3:
                interpretation = "Weak cross-correlation. No clear lead-lag relationship."
            elif max_lag_val > 0:
                interpretation = f"Series A leads Series B by {max_lag_val} periods (r={max_ccf:.3f})."
            elif max_lag_val < 0:
                interpretation = f"Series B leads Series A by {abs(max_lag_val)} periods (r={max_ccf:.3f})."
            else:
                interpretation = f"Strongest correlation at lag 0 (contemporaneous, r={max_ccf:.3f})."

            return success_response(
                {
                    "ccf_values": ccf_values,
                    "max_ccf_lag": max_lag_val,
                    "max_ccf": max_ccf,
                    "interpretation": interpretation,
                    "n_common_observations": n,
                    "max_lag_tested": max_lag,
                },
                source="Time Series",
            )
        except Exception as e:
            logger.exception("cross_correlation failed")
            return error_response(str(e))


# ------------------------------------------------------------------
# Standalone test
# ------------------------------------------------------------------
if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)
    adapter = TimeseriesAdapter()

    # Generate synthetic monthly data with trend + seasonality
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=60, freq="MS")
    trend = np.linspace(100, 150, 60)
    seasonal = 10 * np.sin(np.linspace(0, 10 * np.pi, 60))
    noise = np.random.normal(0, 2, 60)
    values = trend + seasonal + noise

    test_series = [
        {"date": d.strftime("%Y-%m-%d"), "value": float(v)}
        for d, v in zip(dates, values)
    ]

    print("=== Decompose ===")
    r = adapter.decompose(test_series, freq=12)
    print(f"  success={r.get('success')}, seasonal_strength={r.get('data', {}).get('seasonal_strength')}")

    print("\n=== Stationarity ===")
    r = adapter.stationarity_test(test_series)
    print(f"  success={r.get('success')}, is_stationary={r.get('data', {}).get('is_stationary')}")

    print("\n=== Forecast ===")
    r = adapter.forecast(test_series, horizon=6)
    print(f"  success={r.get('success')}, model={r.get('data', {}).get('model')}")
    if r.get("success"):
        for p in r["data"]["predictions"][:3]:
            print(f"    {p['date']}: {p['predicted']:.2f} [{p['lower_95']:.2f}, {p['upper_95']:.2f}]")

    print("\n=== Seasonality ===")
    r = adapter.seasonality(test_series, freq=12)
    print(f"  success={r.get('success')}, peak={r.get('data', {}).get('peak_period')}, trough={r.get('data', {}).get('trough_period')}")

    print("\n=== Changepoint ===")
    r = adapter.changepoint_detection(test_series, n_changepoints=3)
    print(f"  success={r.get('success')}, found={r.get('data', {}).get('n_changepoints_found')}")

    print("\n=== Cross-Correlation ===")
    # Series B = shifted version of A
    test_series_b = [
        {"date": d.strftime("%Y-%m-%d"), "value": float(v)}
        for d, v in zip(dates, np.roll(values, 3) + np.random.normal(0, 1, 60))
    ]
    r = adapter.cross_correlation(test_series, test_series_b, max_lag=12)
    print(f"  success={r.get('success')}, max_lag={r.get('data', {}).get('max_ccf_lag')}, interpretation={r.get('data', {}).get('interpretation')}")
