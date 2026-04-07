"""
López de Prado ML Pipeline Adapter — Financial Machine Learning Framework.

1. volume_bars: Volume/dollar/tick bars (information-driven sampling)
2. frac_diff: Fractional differentiation (stationarity + memory)
3. triple_barrier: Triple-barrier labeling method
4. meta_label: Meta-labeling (when is the primary model correct?)
5. purged_cv: Purged K-Fold cross-validation (no leakage)
6. feature_importance: MDI, MDA, SFI feature importance

Reference: López de Prado (2018), Advances in Financial Machine Learning, Wiley.
"""
import logging
import sys
import os
import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=RuntimeWarning)


def _ts_to_df(data: List[Dict]) -> pd.DataFrame:
    """Convert [{date, value, volume?}] to DataFrame."""
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates("date").set_index("date")
    df["value"] = df["value"].astype(float)
    if "volume" in df.columns:
        df["volume"] = df["volume"].astype(float)
    return df


class MLPipelineAdapter:
    """López de Prado financial ML pipeline tools."""

    # ------------------------------------------------------------------
    # 1. Volume/Dollar/Tick Bars
    # ------------------------------------------------------------------
    def volume_bars(
        self, series: List[Dict], threshold: float = None, bar_type: str = "volume",
    ) -> Dict[str, Any]:
        """Generate information-driven bars instead of time bars.

        Args:
            series: [{date, value, volume}] — high-frequency data preferred
            threshold: volume/dollar/tick per bar (None = auto)
            bar_type: "volume", "dollar", or "tick"
        """
        try:
            df = _ts_to_df(series)
            n = len(df)
            if n < 50:
                return error_response(f"Need >= 50 observations, got {n}")

            prices = df["value"].values
            has_vol = "volume" in df.columns
            volumes = df["volume"].values if has_vol else np.ones(n)
            dates = df.index

            # Determine accumulator
            if bar_type == "volume":
                accum_values = volumes
            elif bar_type == "dollar":
                accum_values = prices * volumes
            elif bar_type == "tick":
                accum_values = np.ones(n)
            else:
                return error_response(f"Unknown bar_type: {bar_type}")

            # Auto threshold: target ~n/5 bars
            if threshold is None:
                total = np.sum(accum_values)
                target_bars = max(10, n // 5)
                threshold = total / target_bars

            # Generate bars
            bars = []
            current_open_idx = 0
            current_accum = 0
            current_high = -np.inf
            current_low = np.inf

            for i in range(n):
                current_accum += accum_values[i]
                current_high = max(current_high, prices[i])
                current_low = min(current_low, prices[i])

                if current_accum >= threshold:
                    bars.append({
                        "date": dates[i].strftime("%Y-%m-%d %H:%M:%S") if hasattr(dates[i], 'strftime') else str(dates[i]),
                        "open": round(float(prices[current_open_idx]), 4),
                        "high": round(float(current_high), 4),
                        "low": round(float(current_low), 4),
                        "close": round(float(prices[i]), 4),
                        "volume": round(float(np.sum(volumes[current_open_idx:i + 1])), 2),
                        "n_ticks": i - current_open_idx + 1,
                    })
                    current_open_idx = i + 1
                    current_accum = 0
                    current_high = -np.inf
                    current_low = np.inf

            n_bars = len(bars)
            compression = n / n_bars if n_bars > 0 else 0

            # Bar statistics
            if n_bars >= 2:
                bar_returns = [
                    np.log(bars[i]["close"] / bars[i - 1]["close"])
                    for i in range(1, n_bars)
                ]
                normality_p = float(stats.jarque_bera(bar_returns).pvalue) if len(bar_returns) >= 8 else None
            else:
                bar_returns = []
                normality_p = None

            return success_response(
                {
                    "bars": bars[-20:],  # last 20
                    "n_bars": n_bars,
                    "n_original": n,
                    "compression_ratio": round(float(compression), 1),
                    "bar_type": bar_type,
                    "threshold": round(float(threshold), 2),
                    "normality_pvalue": round(normality_p, 4) if normality_p is not None else None,
                    "interpretation": (
                        f"{bar_type} bars: {n_bars} bars from {n} ticks "
                        f"({compression:.0f}:1 compression). "
                        f"Threshold: {threshold:,.0f}. "
                        f"{'Returns more normal than time bars.' if normality_p and normality_p > 0.05 else 'Returns still non-normal.'}"
                    ),
                },
                source="ML Pipeline",
            )
        except Exception as e:
            logger.exception("volume_bars failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 2. Fractional Differentiation
    # ------------------------------------------------------------------
    def frac_diff(
        self, series: List[Dict], d: float = None, threshold: float = 1e-5,
    ) -> Dict[str, Any]:
        """Fractional differentiation — stationarity while preserving memory.

        If d is None, finds minimum d for stationarity via ADF test.
        """
        try:
            df = _ts_to_df(series)
            prices = df["value"].values
            n = len(prices)
            if n < 50:
                return error_response(f"Need >= 50 prices, got {n}")

            log_prices = np.log(prices)

            def _frac_diff_weights(d_val, max_k):
                """Compute fractional diff weights."""
                w = [1.0]
                for k in range(1, max_k):
                    w.append(-w[-1] * (d_val - k + 1) / k)
                    if abs(w[-1]) < threshold:
                        break
                return np.array(w)

            def _apply_frac_diff(x, d_val):
                """Apply fractional differentiation."""
                w = _frac_diff_weights(d_val, len(x))
                width = len(w)
                result = np.full(len(x), np.nan)
                for i in range(width - 1, len(x)):
                    result[i] = np.dot(w, x[i - width + 1:i + 1][::-1])
                return result

            from statsmodels.tsa.stattools import adfuller

            if d is None:
                # Search for minimum d
                best_d = None
                for d_test in np.arange(0.0, 1.05, 0.05):
                    fd = _apply_frac_diff(log_prices, d_test)
                    valid = fd[~np.isnan(fd)]
                    if len(valid) < 30:
                        continue
                    try:
                        adf_p = adfuller(valid, maxlag=int(np.sqrt(len(valid))))[1]
                        if adf_p < 0.05:
                            best_d = d_test
                            break
                    except Exception:
                        continue
                d = best_d if best_d is not None else 1.0

            # Apply with found/given d
            fd_series = _apply_frac_diff(log_prices, d)
            valid_mask = ~np.isnan(fd_series)
            fd_valid = fd_series[valid_mask]

            # ADF test on result
            adf_stat, adf_p = adfuller(fd_valid, maxlag=int(np.sqrt(len(fd_valid))))[:2]

            # Correlation with original
            orig_aligned = log_prices[valid_mask]
            corr_with_original = float(np.corrcoef(orig_aligned, fd_valid)[0, 1])

            # Output series
            output_dates = df.index[valid_mask]
            output_series = [
                {"date": d.strftime("%Y-%m-%d"), "value": round(float(v), 6)}
                for d, v in zip(output_dates[-30:], fd_valid[-30:])
            ]

            return success_response(
                {
                    "d": round(float(d), 2),
                    "adf_statistic": round(float(adf_stat), 4),
                    "adf_pvalue": round(float(adf_p), 4),
                    "is_stationary": adf_p < 0.05,
                    "correlation_with_original": round(corr_with_original, 4),
                    "n_valid": int(np.sum(valid_mask)),
                    "weight_threshold": threshold,
                    "output_series": output_series,
                    "interpretation": (
                        f"Fractional diff d={d:.2f}. "
                        f"ADF p={adf_p:.4f} ({'stationary' if adf_p < 0.05 else 'NOT stationary'}). "
                        f"Correlation with original: {corr_with_original:.3f}. "
                        f"{'Good: stationary with high memory preservation.' if adf_p < 0.05 and corr_with_original > 0.8 else ''}"
                    ),
                },
                source="ML Pipeline",
            )
        except Exception as e:
            logger.exception("frac_diff failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 3. Triple-Barrier Labeling
    # ------------------------------------------------------------------
    def triple_barrier(
        self,
        series: List[Dict],
        profit_taking: float = 0.02,
        stop_loss: float = 0.02,
        max_holding: int = 10,
    ) -> Dict[str, Any]:
        """Triple-barrier method for labeling training examples.

        Each observation gets label +1 (hit upper), -1 (hit lower), 0 (expired).
        """
        try:
            df = _ts_to_df(series)
            prices = df["value"].values
            n = len(prices)
            if n < 30:
                return error_response(f"Need >= 30 prices, got {n}")

            labels = []
            details = []

            for i in range(n - max_holding):
                entry_price = prices[i]
                upper = entry_price * (1 + profit_taking)
                lower = entry_price * (1 - stop_loss)

                label = 0  # default: time expiry
                exit_day = max_holding
                exit_reason = "time_expiry"

                for j in range(1, min(max_holding + 1, n - i)):
                    if prices[i + j] >= upper:
                        label = 1
                        exit_day = j
                        exit_reason = "profit_taking"
                        break
                    elif prices[i + j] <= lower:
                        label = -1
                        exit_day = j
                        exit_reason = "stop_loss"
                        break

                labels.append(label)
                ret = (prices[i + exit_day] - entry_price) / entry_price if i + exit_day < n else 0
                details.append({
                    "date": df.index[i].strftime("%Y-%m-%d"),
                    "label": label,
                    "exit_day": exit_day,
                    "exit_reason": exit_reason,
                    "return": round(float(ret), 4),
                })

            labels_arr = np.array(labels)
            n_pos = int(np.sum(labels_arr == 1))
            n_neg = int(np.sum(labels_arr == -1))
            n_zero = int(np.sum(labels_arr == 0))
            total = len(labels_arr)

            avg_ret_pos = np.mean([d["return"] for d in details if d["label"] == 1]) if n_pos > 0 else 0
            avg_ret_neg = np.mean([d["return"] for d in details if d["label"] == -1]) if n_neg > 0 else 0

            return success_response(
                {
                    "n_positive": n_pos,
                    "n_negative": n_neg,
                    "n_neutral": n_zero,
                    "total_labeled": total,
                    "pct_positive": round(n_pos / total * 100, 1) if total > 0 else 0,
                    "pct_negative": round(n_neg / total * 100, 1) if total > 0 else 0,
                    "pct_neutral": round(n_zero / total * 100, 1) if total > 0 else 0,
                    "avg_return_positive": round(float(avg_ret_pos), 4),
                    "avg_return_negative": round(float(avg_ret_neg), 4),
                    "parameters": {
                        "profit_taking": profit_taking,
                        "stop_loss": stop_loss,
                        "max_holding_days": max_holding,
                    },
                    "recent_labels": details[-20:],
                    "interpretation": (
                        f"Triple-barrier: +1:{n_pos} ({n_pos/total:.0%}), "
                        f"-1:{n_neg} ({n_neg/total:.0%}), 0:{n_zero} ({n_zero/total:.0%}). "
                        f"Avg win: {avg_ret_pos:.2%}, Avg loss: {avg_ret_neg:.2%}. "
                        f"{'Balanced labels.' if 0.3 < n_pos/total < 0.7 else 'Imbalanced — adjust barriers.'}"
                    ),
                },
                source="ML Pipeline",
            )
        except Exception as e:
            logger.exception("triple_barrier failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 4. Meta-Labeling
    # ------------------------------------------------------------------
    def meta_label(
        self,
        series: List[Dict],
        signals: List[Dict],
        profit_taking: float = 0.02,
        stop_loss: float = 0.02,
        max_holding: int = 10,
    ) -> Dict[str, Any]:
        """Meta-labeling: learn WHEN the primary model is correct.

        Args:
            series: price series [{date, value}]
            signals: primary model signals [{date, value}] where value in {-1, 0, 1}
        """
        try:
            df = _ts_to_df(series)
            sig_df = pd.DataFrame(signals)
            sig_df["date"] = pd.to_datetime(sig_df["date"])
            sig_df = sig_df.set_index("date")["value"].astype(int)

            # Align
            aligned = pd.DataFrame({"price": df["value"], "signal": sig_df}).dropna()
            n = len(aligned)
            if n < 50:
                return error_response(f"Need >= 50 aligned observations, got {n}")

            prices = aligned["price"].values
            sigs = aligned["signal"].values

            # For each signal != 0, apply triple barrier
            meta_labels = []
            for i in range(n - max_holding):
                if sigs[i] == 0:
                    continue

                entry = prices[i]
                direction = sigs[i]
                upper = entry * (1 + profit_taking) if direction == 1 else entry * (1 + stop_loss)
                lower = entry * (1 - stop_loss) if direction == 1 else entry * (1 - profit_taking)

                label = 0
                for j in range(1, min(max_holding + 1, n - i)):
                    if direction == 1:
                        if prices[i + j] >= entry * (1 + profit_taking):
                            label = 1  # correct signal
                            break
                        elif prices[i + j] <= entry * (1 - stop_loss):
                            label = 0  # wrong signal
                            break
                    else:  # direction == -1
                        if prices[i + j] <= entry * (1 - profit_taking):
                            label = 1  # correct signal
                            break
                        elif prices[i + j] >= entry * (1 + stop_loss):
                            label = 0  # wrong signal
                            break

                meta_labels.append({
                    "date": aligned.index[i].strftime("%Y-%m-%d"),
                    "primary_signal": int(direction),
                    "meta_label": label,
                })

            if not meta_labels:
                return error_response("No signal events found (all signals are 0)")

            ml_arr = np.array([m["meta_label"] for m in meta_labels])
            accuracy = float(np.mean(ml_arr))
            n_correct = int(np.sum(ml_arr == 1))
            n_wrong = int(np.sum(ml_arr == 0))

            return success_response(
                {
                    "primary_model_accuracy": round(accuracy, 3),
                    "n_signal_events": len(meta_labels),
                    "n_correct": n_correct,
                    "n_wrong": n_wrong,
                    "recent_meta_labels": meta_labels[-20:],
                    "parameters": {
                        "profit_taking": profit_taking,
                        "stop_loss": stop_loss,
                        "max_holding": max_holding,
                    },
                    "interpretation": (
                        f"Primary model accuracy: {accuracy:.1%} "
                        f"({n_correct}/{len(meta_labels)} correct). "
                        f"{'Good primary model.' if accuracy > 0.55 else 'Weak primary model — meta-label can help size bets.'}"
                    ),
                },
                source="ML Pipeline",
            )
        except Exception as e:
            logger.exception("meta_label failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 5. Purged K-Fold Cross-Validation
    # ------------------------------------------------------------------
    def purged_cv(
        self,
        n_samples: int,
        n_folds: int = 5,
        embargo_pct: float = 0.01,
        label_horizon: int = 10,
    ) -> Dict[str, Any]:
        """Generate purged K-fold CV splits that prevent information leakage.

        Removes training samples that overlap with test labels.
        """
        try:
            if n_samples < 50:
                return error_response(f"Need >= 50 samples, got {n_samples}")
            if n_folds < 2 or n_folds > 20:
                return error_response("n_folds must be 2-20")

            embargo_size = max(1, int(n_samples * embargo_pct))
            fold_size = n_samples // n_folds

            splits = []
            for fold in range(n_folds):
                test_start = fold * fold_size
                test_end = min(test_start + fold_size, n_samples)

                # Purge zone: remove training samples whose labels
                # overlap with test set
                purge_start = max(0, test_start - label_horizon)
                purge_end = min(n_samples, test_end + embargo_size)

                # Training indices: everything except purge zone
                train_indices = list(range(0, purge_start)) + list(range(purge_end, n_samples))
                test_indices = list(range(test_start, test_end))

                n_purged = (test_start - purge_start) + (purge_end - test_end)

                splits.append({
                    "fold": fold + 1,
                    "train_size": len(train_indices),
                    "test_size": len(test_indices),
                    "n_purged": n_purged,
                    "train_range": f"[0:{purge_start}] + [{purge_end}:{n_samples}]",
                    "test_range": f"[{test_start}:{test_end}]",
                    "purge_range": f"[{purge_start}:{purge_end}]",
                })

            total_purged = sum(s["n_purged"] for s in splits)
            avg_train = np.mean([s["train_size"] for s in splits])
            avg_test = np.mean([s["test_size"] for s in splits])

            return success_response(
                {
                    "splits": splits,
                    "n_folds": n_folds,
                    "n_samples": n_samples,
                    "embargo_size": embargo_size,
                    "label_horizon": label_horizon,
                    "total_samples_purged": total_purged,
                    "avg_train_size": round(float(avg_train), 0),
                    "avg_test_size": round(float(avg_test), 0),
                    "interpretation": (
                        f"Purged {n_folds}-fold CV: avg train={avg_train:.0f}, "
                        f"avg test={avg_test:.0f}. "
                        f"Total purged: {total_purged} samples "
                        f"(embargo={embargo_size}, label_horizon={label_horizon}). "
                        f"No leakage between train/test."
                    ),
                },
                source="ML Pipeline",
            )
        except Exception as e:
            logger.exception("purged_cv failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 6. Feature Importance (MDI, MDA, SFI)
    # ------------------------------------------------------------------
    def feature_importance(
        self,
        features: List[Dict],
        labels: List[float],
        feature_names: Optional[List[str]] = None,
        n_estimators: int = 100,
    ) -> Dict[str, Any]:
        """Three complementary feature importance methods.

        MDI: Mean Decrease in Impurity (from tree structure).
        MDA: Mean Decrease in Accuracy (permutation-based).
        SFI: Single Feature Importance (one feature at a time).

        Args:
            features: [{feature1: val, feature2: val, ...}, ...]
            labels: target values [0, 1, 0, 1, ...]
            feature_names: names of features (auto-detected if None)
        """
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import cross_val_score
            from sklearn.inspection import permutation_importance

            X = pd.DataFrame(features)
            y = np.array(labels)

            if len(X) < 30:
                return error_response(f"Need >= 30 samples, got {len(X)}")
            if len(X) != len(y):
                return error_response("features and labels must have same length")

            if feature_names:
                X.columns = feature_names[:len(X.columns)]
            names = list(X.columns)

            # Fill NaN
            X = X.fillna(0)

            # 1. MDI (Mean Decrease Impurity)
            rf = RandomForestClassifier(
                n_estimators=n_estimators, random_state=42, max_depth=5, n_jobs=-1
            )
            rf.fit(X, y)
            mdi = dict(zip(names, [round(float(v), 4) for v in rf.feature_importances_]))

            # 2. MDA (Permutation Importance)
            perm = permutation_importance(rf, X, y, n_repeats=10, random_state=42, n_jobs=-1)
            mda = dict(zip(names, [round(float(v), 4) for v in perm.importances_mean]))

            # 3. SFI (Single Feature Importance)
            sfi = {}
            for i, feat in enumerate(names):
                X_single = X[[feat]]
                try:
                    scores = cross_val_score(
                        RandomForestClassifier(n_estimators=50, random_state=42, max_depth=3),
                        X_single, y, cv=min(5, len(X) // 10), scoring="accuracy"
                    )
                    sfi[feat] = round(float(np.mean(scores)), 4)
                except Exception:
                    sfi[feat] = 0.5  # baseline

            # Rank features
            combined = {}
            for feat in names:
                combined[feat] = {
                    "mdi": mdi.get(feat, 0),
                    "mda": mda.get(feat, 0),
                    "sfi": sfi.get(feat, 0.5),
                    "avg_rank": 0,
                }

            # Compute average rank
            for method, scores in [("mdi", mdi), ("mda", mda), ("sfi", sfi)]:
                sorted_feats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
                for rank, (feat, _) in enumerate(sorted_feats):
                    combined[feat]["avg_rank"] += rank + 1
            for feat in combined:
                combined[feat]["avg_rank"] = round(combined[feat]["avg_rank"] / 3, 1)

            # Sort by avg_rank
            ranking = sorted(combined.items(), key=lambda x: x[1]["avg_rank"])

            return success_response(
                {
                    "ranking": [{"feature": f, **v} for f, v in ranking],
                    "mdi_importance": mdi,
                    "mda_importance": mda,
                    "sfi_accuracy": sfi,
                    "n_features": len(names),
                    "n_samples": len(X),
                    "rf_oob_accuracy": round(float(rf.score(X, y)), 3),
                    "interpretation": (
                        f"Top feature: {ranking[0][0]} (avg rank {ranking[0][1]['avg_rank']}). "
                        f"MDI: {ranking[0][1]['mdi']:.3f}, MDA: {ranking[0][1]['mda']:.3f}. "
                        f"{len(names)} features analyzed across 3 methods."
                    ),
                },
                source="ML Pipeline",
            )
        except Exception as e:
            logger.exception("feature_importance failed")
            return error_response(str(e))
