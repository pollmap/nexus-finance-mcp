"""
Advanced Math Adapter - PhD-Level Mathematical Analysis for Financial Time Series.

Implements six core mathematical tools that go beyond standard technical analysis:

1. kalman_filter: State-space filtering with dynamic beta estimation
2. hurst_exponent: R/S analysis + DFA for regime detection
3. information_entropy: Shannon, ApEn, SampEn for predictability scoring
4. wavelet_decompose: Multi-resolution analysis via DWT (pywt)
5. fractal_dimension: Box-counting dimension for complexity measurement
6. monte_carlo_simulation: GBM-based forward simulation with risk metrics

Input format: list[dict] with {"date": "YYYY-MM-DD", "value": float}

Run standalone test: python -m mcp_servers.adapters.advanced_math_adapter
"""
import logging
import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=RuntimeWarning)


def _ts_to_array(data: List[Dict]) -> Tuple[List[str], np.ndarray]:
    """Convert list[dict] with {date, value} to (dates, values) arrays."""
    if not data:
        raise ValueError("Empty series provided")
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates("date").dropna(subset=["value"])
    dates = df["date"].dt.strftime("%Y-%m-%d").tolist()
    values = df["value"].astype(float).values
    return dates, values


def _to_log_returns(values: np.ndarray) -> np.ndarray:
    """Convert price series to log returns."""
    prices = values[values > 0]
    if len(prices) < 2:
        raise ValueError("Need at least 2 positive prices for returns")
    return np.log(prices[1:] / prices[:-1])


def _is_return_series(values: np.ndarray) -> bool:
    """Heuristic: if mean is near 0 and range is small, treat as returns."""
    if len(values) < 10:
        return False
    return abs(np.mean(values)) < 0.01 and np.std(values) < 0.2


class AdvancedMathAdapter:
    """PhD-level mathematical analysis for financial time series.

    All methods accept series as list[dict] with {"date": "YYYY-MM-DD", "value": float}.
    Auto-detects whether input is price series or return series.
    Returns {"success": True, "data": ...} on success.
    """

    # ------------------------------------------------------------------
    # 1. Kalman Filter
    # ------------------------------------------------------------------
    def kalman_filter(
        self,
        series: List[Dict],
        process_noise: float = 1e-5,
        measurement_noise: float = 1e-2,
        benchmark: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """1D Kalman filter with state = [price, velocity].

        Filters noisy price series to extract smooth trend + velocity.
        Optionally computes dynamic beta against a benchmark.

        Args:
            series: Price time series [{date, value}]
            process_noise: Process noise covariance scalar (Q scaling)
            measurement_noise: Measurement noise covariance scalar (R)
            benchmark: Optional benchmark series for dynamic beta

        Returns:
            filtered_signal, smoothed_signal, kalman_gain_history,
            estimated_velocity, dynamic_beta (if benchmark provided)
        """
        try:
            dates, values = _ts_to_array(series)
            n = len(values)
            if n < 30:
                return {"success": False, "error": f"Kalman filter requires 30+ observations, got {n}"}

            # State: [price, velocity], Measurement: observed price
            F = np.array([[1.0, 1.0], [0.0, 1.0]])  # state transition
            H = np.array([[1.0, 0.0]])                # measurement matrix
            Q = process_noise * np.eye(2)              # process noise covariance
            R = np.array([[measurement_noise]])        # measurement noise covariance
            I = np.eye(2)

            # Initialize state
            x = np.array([values[0], 0.0])  # initial: first price, zero velocity
            P = np.eye(2) * 1.0             # initial state covariance

            filtered_states = np.zeros((n, 2))
            kalman_gains = np.zeros(n)
            predicted_states = np.zeros((n, 2))
            predicted_covs = np.zeros((n, 2, 2))

            # Forward pass (filtering)
            for t in range(n):
                # Predict
                x_pred = F @ x
                P_pred = F @ P @ F.T + Q

                # Store predictions for smoother
                predicted_states[t] = x_pred
                predicted_covs[t] = P_pred

                # Update
                z = values[t]
                y = z - H @ x_pred  # innovation
                S = H @ P_pred @ H.T + R  # innovation covariance
                K = P_pred @ H.T @ np.linalg.inv(S)  # Kalman gain

                x = x_pred + K.flatten() * y
                P = (I - K @ H) @ P_pred

                filtered_states[t] = x
                kalman_gains[t] = K[0, 0]

            # Backward pass (RTS smoother)
            smoothed_states = np.copy(filtered_states)
            for t in range(n - 2, -1, -1):
                try:
                    P_pred_inv = np.linalg.inv(predicted_covs[t + 1])
                except np.linalg.LinAlgError:
                    P_pred_inv = np.linalg.pinv(predicted_covs[t + 1])
                # Approximate smoother gain using filtered covariance proxy
                C = Q @ F.T @ P_pred_inv  # simplified RTS gain
                smoothed_states[t] = filtered_states[t] + C @ (smoothed_states[t + 1] - predicted_states[t + 1])

            # Build result
            filtered_signal = [
                {"date": dates[i], "value": round(float(filtered_states[i, 0]), 6)}
                for i in range(n)
            ]
            smoothed_signal = [
                {"date": dates[i], "value": round(float(smoothed_states[i, 0]), 6)}
                for i in range(n)
            ]
            velocity = [
                {"date": dates[i], "value": round(float(filtered_states[i, 1]), 8)}
                for i in range(n)
            ]
            gain_history = [
                {"date": dates[i], "value": round(float(kalman_gains[i]), 6)}
                for i in range(n)
            ]

            # Latest velocity interpretation
            last_vel = filtered_states[-1, 1]
            avg_vel = np.mean(filtered_states[max(0, n - 20):, 1])
            if avg_vel > 0.001 * np.std(values):
                trend_direction = "uptrend"
            elif avg_vel < -0.001 * np.std(values):
                trend_direction = "downtrend"
            else:
                trend_direction = "sideways"

            result = {
                "filtered_signal": filtered_signal,
                "smoothed_signal": smoothed_signal,
                "estimated_velocity": velocity,
                "kalman_gain_history": gain_history,
                "trend_direction": trend_direction,
                "latest_velocity": round(float(last_vel), 8),
                "avg_velocity_20d": round(float(avg_vel), 8),
                "params": {
                    "process_noise": process_noise,
                    "measurement_noise": measurement_noise,
                    "observations": n,
                },
            }

            # Dynamic beta against benchmark
            if benchmark:
                try:
                    beta_result = self._compute_dynamic_beta(
                        series, benchmark, process_noise, measurement_noise
                    )
                    result["dynamic_beta"] = beta_result
                except Exception as e:
                    result["dynamic_beta"] = {"error": str(e)}

            return {"success": True, "data": result}

        except Exception as e:
            logger.error(f"Kalman filter error: {e}")
            return {"success": False, "error": str(e)}

    def _compute_dynamic_beta(
        self,
        series: List[Dict],
        benchmark: List[Dict],
        process_noise: float,
        measurement_noise: float,
    ) -> Dict[str, Any]:
        """Compute time-varying beta using Kalman filter on returns regression."""
        _, asset_vals = _ts_to_array(series)
        _, bench_vals = _ts_to_array(benchmark)

        # Align lengths
        min_len = min(len(asset_vals), len(bench_vals))
        asset_vals = asset_vals[:min_len]
        bench_vals = bench_vals[:min_len]

        # Convert to returns
        asset_ret = _to_log_returns(asset_vals)
        bench_ret = _to_log_returns(bench_vals)

        n = len(asset_ret)
        if n < 30:
            return {"error": "Need 30+ aligned return observations for dynamic beta"}

        # State: beta (scalar), Observation: asset_ret = beta * bench_ret + noise
        beta = 1.0
        P = 1.0
        q = process_noise * 10  # beta process noise
        betas = np.zeros(n)

        for t in range(n):
            # Predict
            beta_pred = beta
            P_pred = P + q

            # Update
            h = bench_ret[t]
            y = asset_ret[t] - h * beta_pred
            S = h * P_pred * h + measurement_noise
            K = P_pred * h / S if abs(S) > 1e-15 else 0.0

            beta = beta_pred + K * y
            P = (1 - K * h) * P_pred
            betas[t] = beta

        return {
            "latest_beta": round(float(betas[-1]), 4),
            "avg_beta_20d": round(float(np.mean(betas[-20:])), 4),
            "beta_std": round(float(np.std(betas[-60:])), 4) if n >= 60 else None,
            "beta_trend": "increasing" if betas[-1] > np.mean(betas[-20:]) else "decreasing",
            "n_observations": n,
        }

    # ------------------------------------------------------------------
    # 2. Hurst Exponent
    # ------------------------------------------------------------------
    def hurst_exponent(
        self,
        series: List[Dict],
        method: str = "rs",
    ) -> Dict[str, Any]:
        """Hurst exponent estimation via R/S analysis or DFA.

        H > 0.5: persistent (trending), momentum strategies work
        H < 0.5: anti-persistent (mean-reverting), mean-reversion strategies work
        H ~ 0.5: random walk, no exploitable pattern

        Args:
            series: Time series [{date, value}]
            method: "rs" (Rescaled Range) or "dfa" (Detrended Fluctuation Analysis)

        Returns:
            hurst_exponent, method, interpretation, confidence
        """
        try:
            dates, values = _ts_to_array(series)
            n = len(values)
            if n < 100:
                return {"success": False, "error": f"Hurst exponent requires 100+ observations, got {n}"}

            # Work with returns if price series
            if _is_return_series(values):
                returns = values
            else:
                returns = _to_log_returns(values)

            if method == "dfa":
                H, se, r2 = self._hurst_dfa(returns)
            else:
                H, se, r2 = self._hurst_rs(returns)

            # Interpretation
            if H > 0.65:
                interpretation = "Strong persistence (trending). Momentum strategies favored."
            elif H > 0.55:
                interpretation = "Mild persistence. Weak trend-following signal."
            elif H > 0.45:
                interpretation = "Near random walk. No clear exploitable pattern."
            elif H > 0.35:
                interpretation = "Mild anti-persistence. Weak mean-reversion signal."
            else:
                interpretation = "Strong anti-persistence (mean-reverting). Mean-reversion strategies favored."

            # Confidence based on standard error
            if se < 0.05:
                confidence = "high"
            elif se < 0.10:
                confidence = "medium"
            else:
                confidence = "low"

            return {
                "success": True,
                "data": {
                    "hurst_exponent": round(float(H), 4),
                    "method": method,
                    "interpretation": interpretation,
                    "standard_error": round(float(se), 4),
                    "r_squared": round(float(r2), 4),
                    "confidence": confidence,
                    "n_observations": n,
                    "regime": (
                        "trending" if H > 0.55
                        else "mean_reverting" if H < 0.45
                        else "random_walk"
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Hurst exponent error: {e}")
            return {"success": False, "error": str(e)}

    def _hurst_rs(self, series: np.ndarray, min_window: int = 10) -> Tuple[float, float, float]:
        """Rescaled Range (R/S) analysis."""
        n = len(series)
        # Generate window sizes: powers of 2 within data range
        max_k = int(np.log2(n))
        window_sizes = []
        for exp in range(int(np.log2(min_window)), max_k + 1):
            ws = 2 ** exp
            if ws >= min_window and ws <= n // 2:
                window_sizes.append(ws)

        if len(window_sizes) < 3:
            # Fallback: use linear spacing
            window_sizes = list(range(min_window, n // 2, max(1, (n // 2 - min_window) // 10)))

        rs_values = []
        for size in window_sizes:
            n_windows = n // size
            if n_windows < 1:
                continue
            rs_list = []
            for i in range(n_windows):
                subseries = series[i * size:(i + 1) * size]
                if len(subseries) < 2:
                    continue
                mean = np.mean(subseries)
                deviate = np.cumsum(subseries - mean)
                R = np.max(deviate) - np.min(deviate)
                S = np.std(subseries, ddof=1)
                if S > 1e-15:
                    rs_list.append(R / S)
            if rs_list:
                rs_values.append((size, np.mean(rs_list)))

        if len(rs_values) < 3:
            return 0.5, 0.5, 0.0  # fallback

        log_n = np.log(np.array([r[0] for r in rs_values]))
        log_rs = np.log(np.array([r[1] for r in rs_values]))

        slope, intercept, r_value, p_value, std_err = stats.linregress(log_n, log_rs)
        return slope, std_err, r_value ** 2

    def _hurst_dfa(self, series: np.ndarray, min_window: int = 10) -> Tuple[float, float, float]:
        """Detrended Fluctuation Analysis."""
        n = len(series)
        cumsum = np.cumsum(series - np.mean(series))

        # Window sizes
        max_window = n // 4
        n_windows_list = 15
        window_sizes = np.unique(
            np.logspace(np.log10(min_window), np.log10(max_window), n_windows_list).astype(int)
        )
        window_sizes = window_sizes[window_sizes >= min_window]

        fluctuations = []
        valid_sizes = []

        for size in window_sizes:
            n_segs = n // size
            if n_segs < 1:
                continue
            f2_sum = 0.0
            count = 0
            for seg in range(n_segs):
                start = seg * size
                end = start + size
                segment = cumsum[start:end]
                x = np.arange(size)
                # Linear detrend
                coeffs = np.polyfit(x, segment, 1)
                trend = np.polyval(coeffs, x)
                f2_sum += np.mean((segment - trend) ** 2)
                count += 1
            if count > 0:
                fluctuations.append(np.sqrt(f2_sum / count))
                valid_sizes.append(size)

        if len(valid_sizes) < 3:
            return 0.5, 0.5, 0.0

        log_n = np.log(np.array(valid_sizes, dtype=float))
        log_f = np.log(np.array(fluctuations))

        slope, intercept, r_value, p_value, std_err = stats.linregress(log_n, log_f)
        return slope, std_err, r_value ** 2

    # ------------------------------------------------------------------
    # 3. Information Entropy
    # ------------------------------------------------------------------
    def information_entropy(
        self,
        series: List[Dict],
        n_bins: int = 20,
        apen_m: int = 2,
        apen_r_factor: float = 0.2,
    ) -> Dict[str, Any]:
        """Multi-entropy analysis: Shannon, Approximate, and Sample Entropy.

        Higher entropy = more random/unpredictable.
        Lower entropy = more structured/predictable.

        Args:
            series: Time series [{date, value}]
            n_bins: Number of histogram bins for Shannon entropy
            apen_m: Embedding dimension for ApEn/SampEn
            apen_r_factor: Tolerance factor (fraction of std)

        Returns:
            shannon_entropy, approx_entropy, sample_entropy, predictability_score
        """
        try:
            dates, values = _ts_to_array(series)
            n = len(values)
            if n < 100:
                return {"success": False, "error": f"Entropy analysis requires 100+ observations, got {n}"}

            # Work with returns
            if _is_return_series(values):
                returns = values
            else:
                returns = _to_log_returns(values)

            # Shannon entropy
            shannon = self._shannon_entropy(returns, n_bins)

            # Maximum possible entropy for normalization
            max_entropy = np.log2(n_bins)
            normalized_shannon = shannon / max_entropy if max_entropy > 0 else 1.0

            # Approximate entropy (use subset for performance if large)
            data_for_apen = returns[:2000] if len(returns) > 2000 else returns
            apen = self._approx_entropy(data_for_apen, apen_m, apen_r_factor)

            # Sample entropy
            sampen = self._sample_entropy(data_for_apen, apen_m, apen_r_factor)

            # Predictability score: 1 - normalized entropy (ensemble of measures)
            # Scale ApEn/SampEn to [0,1] heuristically (typical range 0-3)
            apen_norm = min(apen / 2.0, 1.0) if apen > 0 else 0.0
            sampen_norm = min(sampen / 2.0, 1.0) if sampen > 0 and not np.isinf(sampen) else apen_norm
            predictability = 1.0 - np.mean([normalized_shannon, apen_norm, sampen_norm])
            predictability = max(0.0, min(1.0, predictability))

            # Interpretation
            if predictability > 0.6:
                interpretation = "High predictability. Structured patterns likely exploitable."
            elif predictability > 0.4:
                interpretation = "Moderate predictability. Some patterns present."
            elif predictability > 0.2:
                interpretation = "Low predictability. Mostly random with faint structure."
            else:
                interpretation = "Very low predictability. Near-random behavior."

            return {
                "success": True,
                "data": {
                    "shannon_entropy": round(float(shannon), 4),
                    "shannon_normalized": round(float(normalized_shannon), 4),
                    "approx_entropy": round(float(apen), 4),
                    "sample_entropy": round(float(sampen), 4) if not np.isinf(sampen) else None,
                    "predictability_score": round(float(predictability), 4),
                    "interpretation": interpretation,
                    "params": {
                        "n_bins": n_bins,
                        "apen_m": apen_m,
                        "apen_r_factor": apen_r_factor,
                    },
                    "n_observations": n,
                },
            }

        except Exception as e:
            logger.error(f"Information entropy error: {e}")
            return {"success": False, "error": str(e)}

    def _shannon_entropy(self, returns: np.ndarray, n_bins: int) -> float:
        """Shannon entropy of return distribution."""
        hist, bin_edges = np.histogram(returns, bins=n_bins, density=True)
        bin_width = bin_edges[1] - bin_edges[0]
        # Probability mass for each bin
        probs = hist * bin_width
        probs = probs[probs > 0]
        return float(-np.sum(probs * np.log2(probs)))

    def _approx_entropy(self, data: np.ndarray, m: int = 2, r_factor: float = 0.2) -> float:
        """Approximate Entropy (ApEn)."""
        N = len(data)
        r = r_factor * np.std(data)
        if r < 1e-15 or N < m + 2:
            return 0.0

        def _phi(m_val):
            patterns = np.array([data[i:i + m_val] for i in range(N - m_val + 1)])
            n_patterns = len(patterns)
            counts = np.zeros(n_patterns)
            for i in range(n_patterns):
                # Max norm distance
                dists = np.max(np.abs(patterns - patterns[i]), axis=1)
                counts[i] = np.sum(dists <= r)
            counts = counts / n_patterns
            return np.sum(np.log(counts[counts > 0])) / n_patterns

        return float(_phi(m) - _phi(m + 1))

    def _sample_entropy(self, data: np.ndarray, m: int = 2, r_factor: float = 0.2) -> float:
        """Sample Entropy (SampEn) - bias-corrected version of ApEn."""
        N = len(data)
        r = r_factor * np.std(data)
        if r < 1e-15 or N < m + 2:
            return 0.0

        def _count_matches(m_val):
            patterns = np.array([data[i:i + m_val] for i in range(N - m_val)])
            n_patterns = len(patterns)
            count = 0
            for i in range(n_patterns):
                for j in range(i + 1, n_patterns):
                    if np.max(np.abs(patterns[i] - patterns[j])) <= r:
                        count += 1
            return count

        A = _count_matches(m + 1)
        B = _count_matches(m)

        if B == 0:
            return float("inf")
        if A == 0:
            return float("inf")
        return float(-np.log(A / B))

    # ------------------------------------------------------------------
    # 4. Wavelet Decomposition
    # ------------------------------------------------------------------
    def wavelet_decompose(
        self,
        series: List[Dict],
        wavelet: str = "db4",
        levels: int = 5,
    ) -> Dict[str, Any]:
        """Discrete Wavelet Transform (DWT) multi-resolution analysis.

        Decomposes price series into frequency bands:
        - Level 1: highest frequency (2-4 day cycles) = noise
        - Level 2-3: medium frequency (4-16 day cycles) = short-term trends
        - Level 4-5: low frequency (16-64 day cycles) = medium-term trends
        - Approximation: lowest frequency = long-term trend

        Args:
            series: Time series [{date, value}]
            wavelet: Wavelet family ("db4", "haar", "sym5", "coif3", etc.)
            levels: Decomposition depth (auto-limited by data length)

        Returns:
            levels detail, dominant_scale, power_spectrum, energy_distribution
        """
        try:
            import pywt

            dates, values = _ts_to_array(series)
            n = len(values)
            min_required = 2 ** levels
            if n < min_required:
                return {
                    "success": False,
                    "error": f"Wavelet decomposition with {levels} levels requires {min_required}+ observations, got {n}",
                }

            # Auto-adjust levels if needed
            max_level = pywt.dwt_max_level(n, pywt.Wavelet(wavelet).dec_len)
            actual_levels = min(levels, max_level)

            # Perform DWT
            coeffs = pywt.wavedec(values, wavelet, level=actual_levels)
            # coeffs[0] = approximation (cA), coeffs[1:] = details (cD_n, ..., cD_1)

            # Total energy
            total_energy = sum(np.sum(c ** 2) for c in coeffs)
            if total_energy < 1e-15:
                total_energy = 1.0

            level_details = []

            # Approximation coefficients (lowest frequency)
            approx_energy = np.sum(coeffs[0] ** 2)
            # Reconstruct approximation
            approx_recon = pywt.waverec(
                [coeffs[0]] + [np.zeros_like(c) for c in coeffs[1:]], wavelet
            )[:n]
            approx_trend = "up" if approx_recon[-1] > approx_recon[-min(20, len(approx_recon))] else "down"

            level_details.append({
                "level": "approximation",
                "frequency_band": f">{2 ** actual_levels} periods (long-term trend)",
                "energy_pct": round(float(approx_energy / total_energy * 100), 2),
                "trend_direction": approx_trend,
                "last_5_values": [round(float(v), 4) for v in approx_recon[-5:]],
            })

            # Detail coefficients (high to low frequency)
            dominant_energy = 0.0
            dominant_level = 0
            for i, detail_coeff in enumerate(coeffs[1:]):
                level_num = actual_levels - i  # levels go from highest to lowest
                period_low = 2 ** (i + 1)
                period_high = 2 ** (i + 2)
                energy = np.sum(detail_coeff ** 2)
                energy_pct = energy / total_energy * 100

                if energy > dominant_energy:
                    dominant_energy = energy
                    dominant_level = level_num

                # Reconstruct this level only
                recon_coeffs = [np.zeros_like(coeffs[0])] + [
                    detail_coeff if j == i else np.zeros_like(coeffs[j + 1])
                    for j in range(len(coeffs) - 1)
                ]
                detail_recon = pywt.waverec(recon_coeffs, wavelet)[:n]

                # Recent trend of this frequency component
                recent = detail_recon[-min(10, len(detail_recon)):]
                if len(recent) >= 2:
                    detail_trend = "up" if recent[-1] > np.mean(recent[:-1]) else "down"
                else:
                    detail_trend = "neutral"

                level_details.append({
                    "level": level_num,
                    "frequency_band": f"{period_low}-{period_high} periods",
                    "energy_pct": round(float(energy_pct), 2),
                    "trend_direction": detail_trend,
                    "last_5_values": [round(float(v), 4) for v in detail_recon[-5:]],
                })

            # Power spectrum (energy per level)
            power_spectrum = [
                {"level": d["level"], "energy_pct": d["energy_pct"]}
                for d in level_details
            ]

            return {
                "success": True,
                "data": {
                    "levels": level_details,
                    "dominant_scale": dominant_level,
                    "dominant_scale_energy_pct": round(float(dominant_energy / total_energy * 100), 2),
                    "power_spectrum": power_spectrum,
                    "wavelet": wavelet,
                    "actual_levels": actual_levels,
                    "n_observations": n,
                    "interpretation": (
                        f"Dominant energy at level {dominant_level} "
                        f"({2 ** dominant_level}-{2 ** (dominant_level + 1)} period cycles). "
                        f"Approximation (trend) holds {round(float(approx_energy / total_energy * 100), 1)}% of energy."
                    ),
                },
            }

        except ImportError:
            return {"success": False, "error": "pywt (PyWavelets) not installed. Run: pip install PyWavelets"}
        except Exception as e:
            logger.error(f"Wavelet decomposition error: {e}")
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # 5. Fractal Dimension
    # ------------------------------------------------------------------
    def fractal_dimension(
        self,
        series: List[Dict],
        method: str = "box_counting",
    ) -> Dict[str, Any]:
        """Fractal dimension via box-counting method.

        D ~ 1.0: smooth curve (predictable, trending)
        D ~ 1.5: Brownian motion (random walk, efficient market)
        D ~ 2.0: space-filling (very noisy, chaotic)

        Args:
            series: Time series [{date, value}]
            method: "box_counting" (default)

        Returns:
            fractal_dimension, interpretation, r_squared
        """
        try:
            dates, values = _ts_to_array(series)
            n = len(values)
            if n < 200:
                return {"success": False, "error": f"Fractal dimension requires 200+ observations, got {n}"}

            if method == "box_counting":
                D, r2, se = self._box_counting_dimension(values)
            else:
                return {"success": False, "error": f"Unknown method: {method}. Use 'box_counting'."}

            # Interpretation
            if D < 1.2:
                interpretation = "Very smooth/trending. Strong directional bias. Low complexity."
            elif D < 1.4:
                interpretation = "Moderately smooth. Some trend structure exploitable."
            elif D < 1.6:
                interpretation = "Near Brownian motion. Efficient market behavior."
            elif D < 1.8:
                interpretation = "Moderately noisy. High-frequency structure present."
            else:
                interpretation = "Very noisy/chaotic. Space-filling behavior. Extremely complex."

            # Market efficiency assessment
            efficiency = abs(D - 1.5)  # distance from random walk
            if efficiency < 0.1:
                market_efficiency = "efficient"
            elif efficiency < 0.25:
                market_efficiency = "weakly_inefficient"
            else:
                market_efficiency = "inefficient"

            return {
                "success": True,
                "data": {
                    "fractal_dimension": round(float(D), 4),
                    "interpretation": interpretation,
                    "r_squared": round(float(r2), 4),
                    "standard_error": round(float(se), 4),
                    "market_efficiency": market_efficiency,
                    "distance_from_random_walk": round(float(efficiency), 4),
                    "n_observations": n,
                },
            }

        except Exception as e:
            logger.error(f"Fractal dimension error: {e}")
            return {"success": False, "error": str(e)}

    def _box_counting_dimension(self, series: np.ndarray) -> Tuple[float, float, float]:
        """Box-counting fractal dimension."""
        n = len(series)
        # Normalize to [0, 1] x [0, 1]
        x = np.linspace(0, 1, n)
        y_min, y_max = np.min(series), np.max(series)
        if y_max - y_min < 1e-15:
            return 1.0, 1.0, 0.0
        y = (series - y_min) / (y_max - y_min)

        dimensions = []
        for k in range(2, 10):  # box sizes: 1/4, 1/8, ..., 1/512
            box_size = 1.0 / (2 ** k)
            if box_size < 1e-15:
                break
            boxes = set()
            for xi, yi in zip(x, y):
                box_x = int(xi / box_size)
                box_y = int(yi / box_size)
                boxes.add((box_x, box_y))
            if len(boxes) > 0:
                dimensions.append((box_size, len(boxes)))

        if len(dimensions) < 3:
            return 1.5, 0.0, 0.5

        log_eps = np.log(np.array([1.0 / d[0] for d in dimensions]))
        log_n = np.log(np.array([float(d[1]) for d in dimensions]))

        slope, intercept, r_value, p_value, std_err = stats.linregress(log_eps, log_n)
        return slope, r_value ** 2, std_err

    # ------------------------------------------------------------------
    # 6. Monte Carlo Simulation
    # ------------------------------------------------------------------
    def monte_carlo_simulation(
        self,
        series: List[Dict],
        n_simulations: int = 10000,
        horizon: int = 60,
        model: str = "gbm",
    ) -> Dict[str, Any]:
        """Monte Carlo simulation for forward price projection.

        Generates n_simulations paths using Geometric Brownian Motion (GBM):
        dS = mu*S*dt + sigma*S*dW

        Args:
            series: Historical price series [{date, value}]
            n_simulations: Number of simulation paths (default 10000)
            horizon: Forward projection in trading days (default 60)
            model: "gbm" (Geometric Brownian Motion)

        Returns:
            percentiles at each horizon step, final_distribution stats,
            mc_var_95, mc_cvar_95, probability_of_loss, expected_shortfall
        """
        try:
            dates, values = _ts_to_array(series)
            n = len(values)
            if n < 60:
                return {"success": False, "error": f"Monte Carlo requires 60+ observations, got {n}"}

            # Cap simulations for performance
            n_simulations = min(n_simulations, 50000)

            # Calculate parameters from historical data
            returns = _to_log_returns(values)
            mu = float(np.mean(returns) * 252)   # annualized drift
            sigma = float(np.std(returns) * np.sqrt(252))  # annualized vol
            S0 = float(values[-1])  # last observed price
            dt = 1.0 / 252

            if model != "gbm":
                return {"success": False, "error": f"Unknown model: {model}. Use 'gbm'."}

            # Vectorized GBM simulation
            z = np.random.standard_normal((n_simulations, horizon))
            log_increments = (mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * z
            log_paths = np.cumsum(log_increments, axis=1)
            paths = S0 * np.exp(log_paths)

            # Percentiles at each timestep
            percentile_levels = [5, 10, 25, 50, 75, 90, 95]
            percentiles_by_step = []
            # Sample steps to keep output manageable
            step_indices = sorted(set(
                [0, 4, 9, 19, 29, 44, 59, horizon - 1]
            ))
            step_indices = [s for s in step_indices if s < horizon]

            for t in step_indices:
                step_vals = paths[:, t]
                pcts = {f"p{p}": round(float(np.percentile(step_vals, p)), 2) for p in percentile_levels}
                pcts["day"] = t + 1
                pcts["mean"] = round(float(np.mean(step_vals)), 2)
                percentiles_by_step.append(pcts)

            # Final distribution statistics
            final_prices = paths[:, -1]
            final_returns = (final_prices - S0) / S0

            skewness = float(stats.skew(final_returns))
            kurt = float(stats.kurtosis(final_returns))

            # Risk metrics
            var_95 = float(np.percentile(final_returns, 5))  # 5th percentile return
            worst_5pct = final_returns[final_returns <= var_95]
            cvar_95 = float(np.mean(worst_5pct)) if len(worst_5pct) > 0 else var_95
            prob_loss = float(np.mean(final_returns < 0))

            return {
                "success": True,
                "data": {
                    "percentiles_by_step": percentiles_by_step,
                    "final_distribution": {
                        "mean_price": round(float(np.mean(final_prices)), 2),
                        "median_price": round(float(np.median(final_prices)), 2),
                        "std_price": round(float(np.std(final_prices)), 2),
                        "mean_return": round(float(np.mean(final_returns)), 4),
                        "std_return": round(float(np.std(final_returns)), 4),
                        "skewness": round(skewness, 4),
                        "kurtosis": round(kurt, 4),
                    },
                    "risk_metrics": {
                        "mc_var_95": round(float(var_95), 4),
                        "mc_var_95_dollar": round(float(var_95 * S0), 2),
                        "mc_cvar_95": round(float(cvar_95), 4),
                        "mc_cvar_95_dollar": round(float(cvar_95 * S0), 2),
                        "probability_of_loss": round(float(prob_loss), 4),
                        "expected_shortfall_pct": round(float(cvar_95 * 100), 2),
                    },
                    "model_params": {
                        "model": model,
                        "annualized_drift": round(mu, 4),
                        "annualized_volatility": round(sigma, 4),
                        "last_price": S0,
                        "horizon_days": horizon,
                        "n_simulations": n_simulations,
                    },
                    "n_observations": n,
                },
            }

        except Exception as e:
            logger.error(f"Monte Carlo simulation error: {e}")
            return {"success": False, "error": str(e)}


# ------------------------------------------------------------------
# Standalone test
# ------------------------------------------------------------------
if __name__ == "__main__":
    import json
    from datetime import timedelta

    logging.basicConfig(level=logging.INFO)

    # Generate synthetic price series (GBM with known parameters)
    np.random.seed(42)
    n_days = 500
    dt = 1 / 252
    mu, sigma = 0.08, 0.20
    prices = [100.0]
    for _ in range(n_days - 1):
        prices.append(prices[-1] * np.exp((mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * np.random.randn()))

    base_date = datetime(2024, 1, 1)
    series = [
        {"date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"), "value": p}
        for i, p in enumerate(prices)
    ]

    adapter = AdvancedMathAdapter()

    print("=" * 60)
    print("1. Kalman Filter")
    result = adapter.kalman_filter(series)
    print(f"   Success: {result['success']}")
    if result["success"]:
        d = result["data"]
        print(f"   Trend: {d['trend_direction']}, Velocity: {d['latest_velocity']}")

    print("\n2. Hurst Exponent (R/S)")
    result = adapter.hurst_exponent(series, method="rs")
    print(f"   Success: {result['success']}")
    if result["success"]:
        d = result["data"]
        print(f"   H = {d['hurst_exponent']}, Regime: {d['regime']}")

    print("\n3. Hurst Exponent (DFA)")
    result = adapter.hurst_exponent(series, method="dfa")
    print(f"   Success: {result['success']}")
    if result["success"]:
        d = result["data"]
        print(f"   H = {d['hurst_exponent']}, Regime: {d['regime']}")

    print("\n4. Information Entropy")
    result = adapter.information_entropy(series)
    print(f"   Success: {result['success']}")
    if result["success"]:
        d = result["data"]
        print(f"   Shannon: {d['shannon_entropy']}, ApEn: {d['approx_entropy']}, Predictability: {d['predictability_score']}")

    print("\n5. Wavelet Decomposition")
    result = adapter.wavelet_decompose(series, levels=5)
    print(f"   Success: {result['success']}")
    if result["success"]:
        d = result["data"]
        print(f"   Dominant scale: {d['dominant_scale']}, Levels: {d['actual_levels']}")
        for lvl in d["levels"]:
            print(f"     Level {lvl['level']}: {lvl['energy_pct']}% energy, {lvl['trend_direction']}")

    print("\n6. Fractal Dimension")
    result = adapter.fractal_dimension(series)
    print(f"   Success: {result['success']}")
    if result["success"]:
        d = result["data"]
        print(f"   D = {d['fractal_dimension']}, Efficiency: {d['market_efficiency']}")

    print("\n7. Monte Carlo Simulation")
    result = adapter.monte_carlo_simulation(series, n_simulations=5000, horizon=60)
    print(f"   Success: {result['success']}")
    if result["success"]:
        d = result["data"]
        print(f"   Mean price: {d['final_distribution']['mean_price']}")
        print(f"   VaR 95: {d['risk_metrics']['mc_var_95']}")
        print(f"   P(loss): {d['risk_metrics']['probability_of_loss']}")

    print("\n" + "=" * 60)
    print("All tests completed.")
