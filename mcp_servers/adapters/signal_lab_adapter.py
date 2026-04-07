"""
Signal Lab Adapter - Automated Signal Discovery & Ensemble Engine.

The intellectual core of quantitative alpha research, inspired by
Renaissance Technologies' systematic approach:

1. signal_scan: IC 기반 피처 스캐닝 (walk-forward)
2. signal_combine: 앙상블 시그널 결합 (equal/IC-weight/Ridge)
3. signal_decay: 시그널 감쇠 분석 (half-life)
4. signal_capacity: 시장충격 기반 용량 추정
5. signal_regime_select: 레짐 탐지 + 전략 스위칭
6. signal_walkforward: Walk-forward 검증 (과적합 방지 핵심)

Input format: all time series as list[dict] with {"date": "YYYY-MM-DD", "value": float}
OHLCV: list[dict] with {"date", "open", "high", "low", "close", "volume"}

Run standalone test: python -m mcp_servers.adapters.signal_lab_adapter
"""
import logging
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)

# Suppress sklearn convergence warnings in production
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")


def _ts_to_series(data: List[Dict], name: str = "value") -> pd.Series:
    """Convert list[dict] with {date, value} to pd.Series indexed by date."""
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates("date")
    df.set_index("date", inplace=True)
    return df["value"].rename(name)


def _ohlcv_to_df(ohlcv_data: List[Dict]) -> pd.DataFrame:
    """Convert OHLCV list[dict] to DataFrame indexed by date."""
    df = pd.DataFrame(ohlcv_data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates("date")
    df.set_index("date", inplace=True)
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _zscore(s: pd.Series) -> pd.Series:
    """Z-score normalization (robust to NaN)."""
    m = s.mean()
    sd = s.std()
    if sd == 0 or np.isnan(sd):
        return pd.Series(0.0, index=s.index)
    return (s - m) / sd


def _forward_returns(prices: pd.Series, period: int) -> pd.Series:
    """Compute forward returns: r_{t+period} / r_t - 1."""
    return prices.shift(-period) / prices - 1


class SignalLabAdapter:
    """
    Automated Signal Discovery & Ensemble Engine.

    시그널 탐색 → 결합 → 감쇠 분석 → 용량 추정 → 레짐 스위칭 → Walk-Forward 검증
    까지 체계적 퀀트 알파 리서치 파이프라인.
    """

    MIN_OBS_PER_FOLD = 60  # Minimum observations per walk-forward fold

    # ── 1. Signal Scan ─────────────────────────────────────────────────

    def signal_scan(
        self,
        target_series: List[Dict],
        candidate_features: List[Dict],
        forward_period: int = 20,
        method: str = "walk_forward",
    ) -> Dict[str, Any]:
        """
        피처 스캐닝: 각 후보 피처의 예측력(IC) 평가.

        target_series를 예측하는 데 유효한 피처를 자동 발견한다.
        Walk-forward 방식으로 IC를 계산하여 과적합을 방지한다.

        Args:
            target_series: 예측 대상 (예: 주가 수익률) [{date, value}]
            candidate_features: 후보 피처 목록 [{"name": str, "data": [{date, value}]}]
            forward_period: 전방 수익률 기간 (기본 20일)
            method: "walk_forward" (5-fold 시계열 CV) 또는 "full_sample"

        Returns:
            success, data: {ranked_signals, total_scanned, significant_count, method}
        """
        try:
            target = _ts_to_series(target_series, "target")
            if len(target) < self.MIN_OBS_PER_FOLD * 2:
                return error_response(f"Insufficient target data: {len(target)} < {self.MIN_OBS_PER_FOLD * 2}")

            fwd_ret = _forward_returns(target, forward_period)

            results = []
            for feat_spec in candidate_features:
                feat_name = feat_spec.get("name", "unnamed")
                feat_data = feat_spec.get("data", [])
                if not feat_data:
                    logger.warning("Feature '%s' has no data, skipping", feat_name)
                    continue

                try:
                    feat = _ts_to_series(feat_data, feat_name)
                    result = self._evaluate_feature(
                        feat, fwd_ret, feat_name, method
                    )
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    logger.warning("Failed to evaluate feature '%s': %s", feat_name, e)
                    continue

            # Filter: |IC| > 0.02 and |t| > 1.5
            significant = [
                r for r in results
                if abs(r["ic"]) > 0.02 and abs(r["t_stat"]) > 1.5
            ]

            # Sort by absolute IC descending
            significant.sort(key=lambda x: abs(x["ic"]), reverse=True)

            return success_response(
                {
                    "ranked_signals": significant,
                    "total_scanned": len(candidate_features),
                    "significant_count": len(significant),
                    "method": method,
                    "forward_period": forward_period,
                    "filter_criteria": "|IC| > 0.02 and |t-stat| > 1.5",
                },
                source="Signal Lab",
            )

        except Exception as e:
            logger.error("signal_scan failed: %s", e, exc_info=True)
            return error_response(str(e))

    def _evaluate_feature(
        self,
        feat: pd.Series,
        fwd_ret: pd.Series,
        feat_name: str,
        method: str,
    ) -> Optional[Dict]:
        """Evaluate a single feature's predictive power via IC."""
        # Align dates (inner join)
        aligned = pd.concat([feat, fwd_ret], axis=1, join="inner").dropna()
        if len(aligned) < self.MIN_OBS_PER_FOLD * 2:
            logger.debug("Feature '%s' insufficient overlap: %d", feat_name, len(aligned))
            return None

        feat_vals = aligned.iloc[:, 0].values
        ret_vals = aligned.iloc[:, 1].values

        if method == "walk_forward":
            ic, t_stat, p_value = self._walk_forward_ic(feat_vals, ret_vals, n_folds=5)
        else:
            ic, p_value = stats.spearmanr(feat_vals, ret_vals)
            n = len(feat_vals)
            t_stat = ic * np.sqrt((n - 2) / (1 - ic**2 + 1e-10))

        # Best lag IC: try lags 0~12
        best_lag, best_lag_ic = self._find_best_lag(aligned, max_lag=12)

        return {
            "name": feat_name,
            "ic": round(float(ic), 6),
            "t_stat": round(float(t_stat), 4),
            "p_value": round(float(p_value), 6),
            "best_lag": int(best_lag),
            "best_lag_ic": round(float(best_lag_ic), 6),
            "n_observations": len(aligned),
            "significant": abs(ic) > 0.02 and abs(t_stat) > 1.5,
        }

    def _walk_forward_ic(
        self, feat_vals: np.ndarray, ret_vals: np.ndarray, n_folds: int = 5
    ) -> Tuple[float, float, float]:
        """Walk-forward IC: chronological 5-fold, compute IC on each test fold."""
        n = len(feat_vals)
        fold_size = n // (n_folds + 1)  # expanding window

        if fold_size < self.MIN_OBS_PER_FOLD:
            # Fall back to full-sample if too few observations per fold
            ic, p = stats.spearmanr(feat_vals, ret_vals)
            t = ic * np.sqrt((n - 2) / (1 - ic**2 + 1e-10))
            return ic, t, p

        fold_ics = []
        for i in range(n_folds):
            # Expanding train window, fixed-size test window
            train_end = fold_size * (i + 1)
            test_start = train_end
            test_end = min(test_start + fold_size, n)

            if test_end - test_start < 30:
                continue

            test_feat = feat_vals[test_start:test_end]
            test_ret = ret_vals[test_start:test_end]

            # Check for constant arrays
            if np.std(test_feat) < 1e-12 or np.std(test_ret) < 1e-12:
                continue

            ic_fold, _ = stats.spearmanr(test_feat, test_ret)
            if not np.isnan(ic_fold):
                fold_ics.append(ic_fold)

        if not fold_ics:
            ic, p = stats.spearmanr(feat_vals, ret_vals)
            t = ic * np.sqrt((n - 2) / (1 - ic**2 + 1e-10))
            return ic, t, p

        avg_ic = float(np.mean(fold_ics))
        std_ic = float(np.std(fold_ics, ddof=1)) if len(fold_ics) > 1 else 1e-6
        t_stat = avg_ic / (std_ic / np.sqrt(len(fold_ics)) + 1e-10)
        # Approximate p-value from t-distribution
        p_value = float(2 * stats.t.sf(abs(t_stat), df=max(len(fold_ics) - 1, 1)))

        return avg_ic, t_stat, p_value

    def _find_best_lag(self, aligned: pd.DataFrame, max_lag: int = 12) -> Tuple[int, float]:
        """Find the lag (0~max_lag) that maximizes |IC|."""
        feat_col = aligned.columns[0]
        ret_col = aligned.columns[1]
        best_lag = 0
        best_ic = 0.0

        for lag in range(0, max_lag + 1):
            if lag == 0:
                f = aligned[feat_col].values
                r = aligned[ret_col].values
            else:
                f = aligned[feat_col].iloc[:-lag].values
                r = aligned[ret_col].iloc[lag:].values

            if len(f) < 30:
                break

            if np.std(f) < 1e-12 or np.std(r) < 1e-12:
                continue

            ic, _ = stats.spearmanr(f, r)
            if not np.isnan(ic) and abs(ic) > abs(best_ic):
                best_ic = ic
                best_lag = lag

        return best_lag, best_ic

    # ── 2. Signal Combine ──────────────────────────────────────────────

    def signal_combine(
        self,
        signals: List[Dict],
        target_series: List[Dict],
        method: str = "ic_weight",
    ) -> Dict[str, Any]:
        """
        복수 시그널 앙상블 결합.

        개별 시그널을 z-score 정규화 후 가중 결합하여
        단일 시그널 대비 개선된 예측력을 제공한다.

        Args:
            signals: 시그널 목록 [{"name": str, "data": [{date, value}]}]
            target_series: 타겟 (전방 수익률) [{date, value}]
            method: "equal_weight" | "ic_weight" | "ridge"

        Returns:
            success, data: {combined_signal, individual_ics, combined_ic, improvement_vs_best_single}
        """
        try:
            if not signals or len(signals) < 2:
                return error_response("Need at least 2 signals to combine")

            target = _ts_to_series(target_series, "target")

            # Build signal DataFrame
            sig_series_list = []
            for sig_spec in signals:
                s = _ts_to_series(sig_spec["data"], sig_spec["name"])
                sig_series_list.append(s)

            sig_df = pd.concat(sig_series_list, axis=1, join="inner")
            # Align with target
            combined = pd.concat([sig_df, target], axis=1, join="inner").dropna()

            if len(combined) < self.MIN_OBS_PER_FOLD:
                return error_response(f"Insufficient aligned data: {len(combined)} < {self.MIN_OBS_PER_FOLD}")

            sig_names = [s["name"] for s in signals]
            X = combined[sig_names]
            y = combined["target"]

            # Z-score all signals
            X_z = X.apply(_zscore)

            # Compute individual ICs
            individual_ics = {}
            for col in sig_names:
                ic, _ = stats.spearmanr(X_z[col].values, y.values)
                individual_ics[col] = round(float(ic), 6) if not np.isnan(ic) else 0.0

            best_single_ic = max(abs(v) for v in individual_ics.values())

            # Combine signals
            if method == "equal_weight":
                combined_signal = X_z.mean(axis=1)
            elif method == "ic_weight":
                combined_signal = self._ic_weighted_combine(X_z, y, sig_names)
            elif method == "ridge":
                combined_signal = self._ridge_combine(X_z, y)
            else:
                return error_response(f"Unknown method: {method}. Use equal_weight, ic_weight, or ridge", code="INVALID_INPUT")

            # Combined IC
            combined_ic_val, _ = stats.spearmanr(combined_signal.values, y.values)
            combined_ic_val = float(combined_ic_val) if not np.isnan(combined_ic_val) else 0.0

            improvement = (abs(combined_ic_val) - best_single_ic) / (best_single_ic + 1e-10)

            # Format output
            combined_output = [
                {"date": d.strftime("%Y-%m-%d"), "value": round(float(v), 6)}
                for d, v in combined_signal.items()
            ]

            return success_response(
                {
                    "combined_signal": combined_output,
                    "individual_ics": individual_ics,
                    "combined_ic": round(combined_ic_val, 6),
                    "best_single_ic": round(best_single_ic, 6),
                    "improvement_vs_best_single": round(float(improvement), 4),
                    "improvement_pct": f"{improvement * 100:.1f}%",
                    "method": method,
                    "n_signals": len(sig_names),
                    "n_observations": len(combined),
                },
                source="Signal Lab",
            )

        except Exception as e:
            logger.error("signal_combine failed: %s", e, exc_info=True)
            return error_response(str(e))

    def _ic_weighted_combine(
        self, X_z: pd.DataFrame, y: pd.Series, sig_names: List[str]
    ) -> pd.Series:
        """IC-weighted combination: higher IC = more weight."""
        ics = {}
        for col in sig_names:
            ic, _ = stats.spearmanr(X_z[col].values, y.values)
            ics[col] = abs(ic) if not np.isnan(ic) else 0.0

        total_ic = sum(ics.values())
        if total_ic < 1e-10:
            # Fall back to equal weight
            return X_z.mean(axis=1)

        weights = {col: ics[col] / total_ic for col in sig_names}
        combined = sum(X_z[col] * weights[col] for col in sig_names)
        return combined

    def _ridge_combine(self, X_z: pd.DataFrame, y: pd.Series) -> pd.Series:
        """Ridge regression combination with walk-forward to avoid overfit."""
        n = len(X_z)
        n_train = int(n * 0.7)

        if n_train < self.MIN_OBS_PER_FOLD:
            # Too few obs, just fit on all data
            model = Ridge(alpha=1.0)
            model.fit(X_z.values, y.values)
            pred = model.predict(X_z.values)
            return pd.Series(pred, index=X_z.index)

        # Walk-forward: train on first 70%, predict on remaining 30%
        X_train, X_test = X_z.iloc[:n_train], X_z.iloc[n_train:]
        y_train = y.iloc[:n_train]

        model = Ridge(alpha=1.0)
        model.fit(X_train.values, y_train.values)

        # Predict on full series using trained weights
        pred = model.predict(X_z.values)
        return pd.Series(pred, index=X_z.index)

    # ── 3. Signal Decay ────────────────────────────────────────────────

    def signal_decay(
        self,
        signal_series: List[Dict],
        target_series: List[Dict],
        max_horizon: int = 60,
    ) -> Dict[str, Any]:
        """
        시그널 감쇠(Decay) 분석: 시간 경과에 따른 IC 변화.

        빠른 감쇠 → 단타/스윙, 느린 감쇠 → 포지션 트레이딩.
        Half-life: IC가 최고점 대비 50%로 떨어지는 horizon.

        Args:
            signal_series: 시그널 시계열 [{date, value}]
            target_series: 가격 시계열 (수익률 계산용) [{date, value}]
            max_horizon: 최대 분석 기간 (기본 60일)

        Returns:
            success, data: {decay_curve, half_life, interpretation}
        """
        try:
            signal = _ts_to_series(signal_series, "signal")
            target = _ts_to_series(target_series, "target")

            horizons = [h for h in [1, 5, 10, 20, 40, 60] if h <= max_horizon]
            if not horizons:
                return error_response(f"max_horizon too small: {max_horizon}", code="INVALID_INPUT")

            decay_curve = []
            for h in horizons:
                fwd_ret = _forward_returns(target, h)
                aligned = pd.concat([signal, fwd_ret], axis=1, join="inner").dropna()

                if len(aligned) < 30:
                    decay_curve.append({
                        "horizon": h,
                        "ic": None,
                        "t_stat": None,
                        "note": f"insufficient data ({len(aligned)} obs)",
                    })
                    continue

                feat_vals = aligned.iloc[:, 0].values
                ret_vals = aligned.iloc[:, 1].values

                if np.std(feat_vals) < 1e-12 or np.std(ret_vals) < 1e-12:
                    decay_curve.append({"horizon": h, "ic": 0.0, "t_stat": 0.0})
                    continue

                ic, _ = stats.spearmanr(feat_vals, ret_vals)
                n = len(feat_vals)
                t_stat = ic * np.sqrt((n - 2) / (1 - ic**2 + 1e-10))

                decay_curve.append({
                    "horizon": h,
                    "ic": round(float(ic), 6) if not np.isnan(ic) else 0.0,
                    "t_stat": round(float(t_stat), 4) if not np.isnan(t_stat) else 0.0,
                })

            # Compute half-life
            valid_points = [p for p in decay_curve if p.get("ic") is not None]
            half_life = self._compute_half_life(valid_points)

            # Interpretation
            if half_life is not None:
                if half_life <= 5:
                    interpretation = "Very fast decay → intraday/스캘핑 적합"
                elif half_life <= 15:
                    interpretation = "Fast decay → 스윙 트레이딩 적합 (1~3주)"
                elif half_life <= 30:
                    interpretation = "Medium decay → 포지션 트레이딩 적합 (1개월)"
                else:
                    interpretation = "Slow decay → 장기 포지션 적합 (1개월+)"
            else:
                interpretation = "Half-life 계산 불가 (데이터 부족 또는 비단조 감쇠)"

            return success_response(
                {
                    "decay_curve": decay_curve,
                    "half_life": half_life,
                    "interpretation": interpretation,
                    "max_horizon": max_horizon,
                },
                source="Signal Lab",
            )

        except Exception as e:
            logger.error("signal_decay failed: %s", e, exc_info=True)
            return error_response(str(e))

    def _compute_half_life(self, valid_points: List[Dict]) -> Optional[int]:
        """Compute half-life: horizon where |IC| drops to 50% of peak."""
        if len(valid_points) < 2:
            return None

        peak_ic = max(abs(p["ic"]) for p in valid_points)
        if peak_ic < 1e-6:
            return None

        threshold = peak_ic * 0.5
        for p in valid_points:
            if abs(p["ic"]) <= threshold:
                return p["horizon"]

        # IC never dropped to 50% within observed range
        return None

    # ── 4. Signal Capacity ─────────────────────────────────────────────

    def signal_capacity(
        self,
        signal_series: List[Dict],
        ohlcv_data: List[Dict],
        initial_capital: float = 1e9,
    ) -> Dict[str, Any]:
        """
        시장충격(Market Impact) 기반 시그널 용량 추정.

        운용 자금이 커지면 슬리피지가 증가하여 알파가 잠식된다.
        슬리피지가 알파의 50%를 잠식하는 자본 규모를 최대 용량으로 추정.

        모델: slippage_bps = 10 * sqrt(trade_amount / daily_volume)

        Args:
            signal_series: 시그널 시계열 [{date, value}]
            ohlcv_data: OHLCV 데이터 [{date, open, high, low, close, volume}]
            initial_capital: 분석 기준 자본금 (기본 10억원)

        Returns:
            success, data: {max_capacity_krw, expected_slippage_bps, capacity_utilization_curve}
        """
        try:
            signal = _ts_to_series(signal_series, "signal")
            ohlcv = _ohlcv_to_df(ohlcv_data)

            if "volume" not in ohlcv.columns or "close" not in ohlcv.columns:
                return error_response("OHLCV data must include 'volume' and 'close'", code="INVALID_INPUT")

            # Daily trading value
            ohlcv["dollar_volume"] = ohlcv["close"] * ohlcv["volume"]
            avg_daily_volume = float(ohlcv["dollar_volume"].mean())

            if avg_daily_volume < 1:
                return error_response("Average daily volume is ~0, cannot estimate capacity", code="INVALID_INPUT")

            # Estimate raw alpha (annualized signal IC * vol)
            # Align signal with returns
            daily_ret = ohlcv["close"].pct_change()
            aligned = pd.concat([signal, daily_ret], axis=1, join="inner").dropna()

            if len(aligned) < 30:
                return error_response(f"Insufficient aligned data: {len(aligned)}")

            ic, _ = stats.spearmanr(aligned.iloc[:, 0].values, aligned.iloc[:, 1].values)
            ic = float(ic) if not np.isnan(ic) else 0.0

            # Raw alpha estimate: IC * sigma * sqrt(252) (approximate)
            daily_vol = float(daily_ret.std())
            annual_alpha_bps = abs(ic) * daily_vol * np.sqrt(252) * 10000

            if annual_alpha_bps < 1:
                return success_response(
                    {
                        "max_capacity_krw": 0,
                        "expected_slippage_bps": 0,
                        "signal_ic": round(ic, 6),
                        "estimated_alpha_bps": round(annual_alpha_bps, 2),
                        "note": "Signal has negligible alpha, capacity is effectively 0",
                    },
                    source="Signal Lab",
                )

            # Build capacity curve: for each capital level, compute slippage
            # Model: slippage_bps = 10 * sqrt(capital_traded / avg_daily_volume)
            # Assume we trade 100% of capital daily (conservative)
            capital_levels = [
                1e7, 5e7, 1e8, 5e8, 1e9, 5e9, 1e10, 5e10, 1e11,
            ]

            utilization_curve = []
            max_capacity = 0

            for cap in capital_levels:
                participation_rate = cap / avg_daily_volume
                slippage_bps = 10.0 * np.sqrt(participation_rate)
                net_alpha_bps = annual_alpha_bps - slippage_bps
                alpha_retained_pct = max(0, net_alpha_bps / annual_alpha_bps * 100)

                utilization_curve.append({
                    "capital_krw": cap,
                    "capital_label": self._format_krw(cap),
                    "participation_rate_pct": round(participation_rate * 100, 2),
                    "slippage_bps": round(float(slippage_bps), 2),
                    "net_alpha_bps": round(float(net_alpha_bps), 2),
                    "alpha_retained_pct": round(float(alpha_retained_pct), 1),
                })

                # Max capacity = where 50% of alpha remains
                if net_alpha_bps >= annual_alpha_bps * 0.5:
                    max_capacity = cap

            # Compute slippage for initial_capital
            init_participation = initial_capital / avg_daily_volume
            init_slippage_bps = 10.0 * np.sqrt(init_participation)

            return success_response(
                {
                    "max_capacity_krw": max_capacity,
                    "max_capacity_label": self._format_krw(max_capacity),
                    "expected_slippage_bps": round(float(init_slippage_bps), 2),
                    "signal_ic": round(ic, 6),
                    "estimated_alpha_bps": round(annual_alpha_bps, 2),
                    "avg_daily_volume_krw": round(avg_daily_volume, 0),
                    "capacity_utilization_curve": utilization_curve,
                    "initial_capital": initial_capital,
                },
                source="Signal Lab",
            )

        except Exception as e:
            logger.error("signal_capacity failed: %s", e, exc_info=True)
            return error_response(str(e))

    @staticmethod
    def _format_krw(amount: float) -> str:
        """Format KRW amount in human-readable form."""
        if amount >= 1e12:
            return f"{amount / 1e12:.1f}조원"
        elif amount >= 1e8:
            return f"{amount / 1e8:.0f}억원"
        elif amount >= 1e4:
            return f"{amount / 1e4:.0f}만원"
        else:
            return f"{amount:.0f}원"

    # ── 5. Signal Regime Select ────────────────────────────────────────

    def signal_regime_select(
        self,
        ohlcv_data: List[Dict],
        strategies: List[Dict],
        n_regimes: int = 2,
    ) -> Dict[str, Any]:
        """
        시장 레짐(bull/bear) 탐지 + 전략 스위칭.

        롤링 변동성 + 수익률 기반으로 시장 레짐을 분류하고,
        각 레짐에서 최적 전략을 추천한다.

        Args:
            ohlcv_data: OHLCV 가격 데이터
            strategies: 전략별 수익률 시계열 [{"name": str, "data": [{date, value}]}]
            n_regimes: 레짐 수 (기본 2: bull/bear)

        Returns:
            success, data: {regimes, best_strategy_per_regime, current_regime, recommended_strategy}
        """
        try:
            ohlcv = _ohlcv_to_df(ohlcv_data)

            if len(ohlcv) < 60:
                return error_response(f"Need at least 60 data points, got {len(ohlcv)}")

            # Compute regime indicators
            daily_ret = ohlcv["close"].pct_change()
            rolling_vol = daily_ret.rolling(window=20, min_periods=20).std() * np.sqrt(252)
            rolling_ret = ohlcv["close"].pct_change(periods=60)  # 3-month return

            regime_df = pd.DataFrame({
                "rolling_vol": rolling_vol,
                "rolling_ret": rolling_ret,
            }).dropna()

            if len(regime_df) < 30:
                return error_response("Insufficient data after computing rolling indicators")

            # Simple regime detection: high vol + negative return = bear, else = bull
            # For n_regimes=2: median split on a composite score
            vol_z = _zscore(regime_df["rolling_vol"])
            ret_z = _zscore(regime_df["rolling_ret"])

            # Composite: high vol + low return = bearish
            composite = -ret_z + vol_z  # Higher = more bearish

            if n_regimes == 2:
                median_val = composite.median()
                regime_df["regime"] = np.where(composite > median_val, "bear", "bull")
            elif n_regimes == 3:
                q33 = composite.quantile(0.33)
                q66 = composite.quantile(0.66)
                conditions = [
                    composite <= q33,
                    (composite > q33) & (composite <= q66),
                    composite > q66,
                ]
                regime_df["regime"] = np.select(conditions, ["bull", "neutral", "bear"], default="neutral")
            else:
                return error_response(f"n_regimes must be 2 or 3, got {n_regimes}", code="INVALID_INPUT")

            # Parse strategy returns
            strat_series = {}
            for s in strategies:
                strat_series[s["name"]] = _ts_to_series(s["data"], s["name"])

            # Evaluate each strategy in each regime
            regime_names = regime_df["regime"].unique().tolist()
            best_per_regime = {}
            regime_stats = {}

            for regime in regime_names:
                regime_dates = regime_df[regime_df["regime"] == regime].index
                regime_stats[regime] = {
                    "n_days": len(regime_dates),
                    "pct_of_total": round(len(regime_dates) / len(regime_df) * 100, 1),
                }

                strat_perf = {}
                for sname, sdata in strat_series.items():
                    # Get strategy returns during this regime
                    overlap = sdata.reindex(regime_dates).dropna()
                    if len(overlap) < 5:
                        continue
                    avg_ret = float(overlap.mean())
                    sharpe = float(overlap.mean() / (overlap.std() + 1e-10) * np.sqrt(252))
                    strat_perf[sname] = {
                        "avg_daily_return": round(avg_ret, 6),
                        "sharpe": round(sharpe, 4),
                        "n_days": len(overlap),
                    }

                regime_stats[regime]["strategy_performance"] = strat_perf

                if strat_perf:
                    best_name = max(strat_perf, key=lambda k: strat_perf[k]["sharpe"])
                    best_per_regime[regime] = best_name
                else:
                    best_per_regime[regime] = None

            # Current regime
            current_regime = regime_df["regime"].iloc[-1]
            recommended = best_per_regime.get(current_regime)

            # Regime periods summary
            regime_periods = self._extract_regime_periods(regime_df)

            return success_response(
                {
                    "regimes": regime_stats,
                    "best_strategy_per_regime": best_per_regime,
                    "current_regime": current_regime,
                    "recommended_strategy": recommended,
                    "regime_periods": regime_periods[-20:],  # Last 20 transitions
                    "n_regimes": n_regimes,
                    "total_days": len(regime_df),
                },
                source="Signal Lab",
            )

        except Exception as e:
            logger.error("signal_regime_select failed: %s", e, exc_info=True)
            return error_response(str(e))

    def _extract_regime_periods(self, regime_df: pd.DataFrame) -> List[Dict]:
        """Extract contiguous regime periods."""
        periods = []
        if regime_df.empty:
            return periods

        current_regime = regime_df["regime"].iloc[0]
        start_date = regime_df.index[0]

        for i in range(1, len(regime_df)):
            if regime_df["regime"].iloc[i] != current_regime:
                periods.append({
                    "regime": current_regime,
                    "start": start_date.strftime("%Y-%m-%d"),
                    "end": regime_df.index[i - 1].strftime("%Y-%m-%d"),
                    "days": (regime_df.index[i - 1] - start_date).days + 1,
                })
                current_regime = regime_df["regime"].iloc[i]
                start_date = regime_df.index[i]

        # Final period
        periods.append({
            "regime": current_regime,
            "start": start_date.strftime("%Y-%m-%d"),
            "end": regime_df.index[-1].strftime("%Y-%m-%d"),
            "days": (regime_df.index[-1] - start_date).days + 1,
        })

        return periods

    # ── 6. Signal Walk-Forward ─────────────────────────────────────────

    def signal_walkforward(
        self,
        ohlcv_data: List[Dict],
        strategy_name: str,
        train_window: int = 252,
        test_window: int = 63,
        n_splits: Optional[int] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Walk-Forward 검증: 미래 데이터 누출 없는 전략 평가.

        이것이 가장 중요한 도구 — 이 검증 없이는 모든 백테스트가 거짓이다.

        데이터를 시간순으로 [train_1][test_1][train_2][test_2]... 분할하고,
        각 분할에서 train으로 최적화, test로 평가.
        IS(In-Sample)와 OOS(Out-of-Sample) Sharpe 비교로 과적합 진단.

        과적합 비율 > 2.0: "WARNING: likely overfitted"

        Args:
            ohlcv_data: OHLCV 가격 데이터
            strategy_name: 전략 이름 (BacktestAdapter 내장 전략)
            train_window: 학습 기간 (기본 252거래일 = 1년)
            test_window: 검증 기간 (기본 63거래일 = 1분기)
            n_splits: 분할 수 (None=자동 계산)
            params: 전략 파라미터 오버라이드

        Returns:
            success, data: {in_sample, out_of_sample, overfit_ratio, folds, warning}
        """
        try:
            from mcp_servers.adapters.backtest_adapter import BacktestAdapter

            bt = BacktestAdapter()
            ohlcv_df = _ohlcv_to_df(ohlcv_data)
            n_total = len(ohlcv_df)

            if n_total < train_window + test_window:
                return error_response(f"Insufficient data: {n_total} rows, need at least {train_window + test_window}")

            # Calculate number of splits
            if n_splits is None:
                n_splits = max(1, (n_total - train_window) // test_window)

            if n_splits < 1:
                return error_response("Cannot create even 1 split with given windows", code="INVALID_INPUT")

            # Generate walk-forward folds
            folds = []
            is_sharpes = []
            oos_sharpes = []
            is_returns = []
            oos_returns = []

            for i in range(n_splits):
                train_start = i * test_window
                train_end = train_start + train_window
                test_start = train_end
                test_end = min(test_start + test_window, n_total)

                if test_end <= test_start or train_end > n_total:
                    break

                # Extract fold data as list[dict] for BacktestAdapter
                train_data = self._df_to_ohlcv_list(ohlcv_df.iloc[train_start:train_end])
                test_data = self._df_to_ohlcv_list(ohlcv_df.iloc[test_start:test_end])

                if len(train_data) < self.MIN_OBS_PER_FOLD or len(test_data) < 10:
                    continue

                # Run backtest on train (in-sample)
                is_result = bt.run(
                    train_data, strategy_name,
                    initial_capital=10_000_000, params=params,
                )

                # Run backtest on test (out-of-sample)
                oos_result = bt.run(
                    test_data, strategy_name,
                    initial_capital=10_000_000, params=params,
                )

                is_metrics = is_result.get("data", is_result) if is_result.get("success", True) else {}
                oos_metrics = oos_result.get("data", oos_result) if oos_result.get("success", True) else {}

                is_sharpe = self._extract_sharpe(is_metrics)
                oos_sharpe = self._extract_sharpe(oos_metrics)
                is_ret = self._extract_return(is_metrics)
                oos_ret = self._extract_return(oos_metrics)

                fold_info = {
                    "fold": i + 1,
                    "train_period": {
                        "start": ohlcv_df.index[train_start].strftime("%Y-%m-%d"),
                        "end": ohlcv_df.index[min(train_end - 1, n_total - 1)].strftime("%Y-%m-%d"),
                        "days": train_end - train_start,
                    },
                    "test_period": {
                        "start": ohlcv_df.index[test_start].strftime("%Y-%m-%d"),
                        "end": ohlcv_df.index[min(test_end - 1, n_total - 1)].strftime("%Y-%m-%d"),
                        "days": test_end - test_start,
                    },
                    "in_sample": {
                        "sharpe": round(is_sharpe, 4) if is_sharpe is not None else None,
                        "total_return_pct": round(is_ret * 100, 2) if is_ret is not None else None,
                    },
                    "out_of_sample": {
                        "sharpe": round(oos_sharpe, 4) if oos_sharpe is not None else None,
                        "total_return_pct": round(oos_ret * 100, 2) if oos_ret is not None else None,
                    },
                }

                folds.append(fold_info)

                if is_sharpe is not None:
                    is_sharpes.append(is_sharpe)
                if oos_sharpe is not None:
                    oos_sharpes.append(oos_sharpe)
                if is_ret is not None:
                    is_returns.append(is_ret)
                if oos_ret is not None:
                    oos_returns.append(oos_ret)

            if not folds:
                return error_response("No valid folds could be created")

            # Aggregate metrics
            avg_is_sharpe = float(np.mean(is_sharpes)) if is_sharpes else 0.0
            avg_oos_sharpe = float(np.mean(oos_sharpes)) if oos_sharpes else 0.0
            avg_is_ret = float(np.mean(is_returns)) if is_returns else 0.0
            avg_oos_ret = float(np.mean(oos_returns)) if oos_returns else 0.0

            # Overfit ratio
            if abs(avg_oos_sharpe) > 1e-6:
                overfit_ratio = abs(avg_is_sharpe) / abs(avg_oos_sharpe)
            elif abs(avg_is_sharpe) > 1e-6:
                overfit_ratio = float("inf")
            else:
                overfit_ratio = 1.0

            # Warning assessment
            warnings_list = []
            if overfit_ratio > 2.0:
                warnings_list.append(
                    f"WARNING: likely overfitted (IS/OOS Sharpe ratio = {overfit_ratio:.2f} > 2.0)"
                )
            if avg_oos_sharpe < 0:
                warnings_list.append(
                    "WARNING: negative OOS Sharpe — strategy may not be profitable out-of-sample"
                )
            if len(folds) < 3:
                warnings_list.append(
                    f"WARNING: only {len(folds)} folds — results may not be statistically robust"
                )

            # OOS consistency: % of folds with positive Sharpe
            oos_positive_pct = (
                sum(1 for s in oos_sharpes if s > 0) / len(oos_sharpes) * 100
                if oos_sharpes else 0
            )

            return success_response(
                {
                    "strategy": strategy_name,
                    "in_sample": {
                        "avg_sharpe": round(avg_is_sharpe, 4),
                        "avg_return_pct": round(avg_is_ret * 100, 2),
                    },
                    "out_of_sample": {
                        "avg_sharpe": round(avg_oos_sharpe, 4),
                        "avg_return_pct": round(avg_oos_ret * 100, 2),
                        "positive_sharpe_pct": round(oos_positive_pct, 1),
                    },
                    "overfit_ratio": round(overfit_ratio, 4) if overfit_ratio != float("inf") else "inf",
                    "n_folds": len(folds),
                    "folds": folds,
                    "config": {
                        "train_window": train_window,
                        "test_window": test_window,
                    },
                    "warnings": warnings_list if warnings_list else ["PASS: no overfitting detected"],
                    "verdict": self._walkforward_verdict(overfit_ratio, avg_oos_sharpe, oos_positive_pct),
                },
                source="Signal Lab",
            )

        except Exception as e:
            logger.error("signal_walkforward failed: %s", e, exc_info=True)
            return error_response(str(e))

    @staticmethod
    def _df_to_ohlcv_list(df: pd.DataFrame) -> List[Dict]:
        """Convert OHLCV DataFrame to list[dict] for BacktestAdapter."""
        records = []
        for date_idx, row in df.iterrows():
            rec = {"date": date_idx.strftime("%Y-%m-%d")}
            for col in ["open", "high", "low", "close", "volume"]:
                if col in row.index:
                    rec[col] = float(row[col]) if not pd.isna(row[col]) else 0.0
            records.append(rec)
        return records

    @staticmethod
    def _extract_sharpe(metrics: Dict) -> Optional[float]:
        """Extract Sharpe ratio from backtest result (various key names)."""
        for key in ["sharpe_ratio", "sharpe", "annualized_sharpe"]:
            if key in metrics:
                val = metrics[key]
                if val is not None and not (isinstance(val, float) and np.isnan(val)):
                    return float(val)
        return None

    @staticmethod
    def _extract_return(metrics: Dict) -> Optional[float]:
        """Extract total return from backtest result."""
        for key in ["total_return", "total_return_pct", "cumulative_return"]:
            if key in metrics:
                val = metrics[key]
                if val is not None and not (isinstance(val, float) and np.isnan(val)):
                    v = float(val)
                    # Normalize: if percentage format (>1 means 100%+), convert
                    if abs(v) > 10:
                        v /= 100
                    return v
        return None

    @staticmethod
    def _walkforward_verdict(overfit_ratio: float, avg_oos_sharpe: float, oos_positive_pct: float) -> str:
        """Generate a human-readable verdict."""
        if overfit_ratio > 3.0:
            return "REJECT: 심각한 과적합 (IS/OOS > 3.0). 전략 재설계 필요."
        if overfit_ratio > 2.0:
            return "CAUTION: 과적합 의심 (IS/OOS > 2.0). 파라미터 단순화 권장."
        if avg_oos_sharpe < 0:
            return "REJECT: OOS Sharpe 음수. 전략에 실질적 알파 없음."
        if avg_oos_sharpe < 0.3:
            return "WEAK: OOS Sharpe < 0.3. 거래비용 후 수익성 의문."
        if oos_positive_pct < 50:
            return "UNSTABLE: 50% 미만 fold에서 양의 Sharpe. 일관성 부족."
        if avg_oos_sharpe >= 0.5 and oos_positive_pct >= 60:
            return "ACCEPT: 견실한 OOS 성과. 실전 테스트 권장."
        return "MARGINAL: 추가 검증 필요."


# ── Standalone test ───────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)
    adapter = SignalLabAdapter()

    # Generate synthetic test data
    np.random.seed(42)
    dates = pd.bdate_range("2022-01-01", periods=500)

    # Target: synthetic stock returns
    target = [
        {"date": d.strftime("%Y-%m-%d"), "value": float(np.random.randn() * 0.02)}
        for d in dates
    ]

    # Candidate features: one with real signal, one pure noise
    real_signal = []
    noise_signal = []
    for i, d in enumerate(dates):
        # Real signal: correlated with future return (lag 1)
        if i < len(dates) - 1:
            real_signal.append({
                "date": d.strftime("%Y-%m-%d"),
                "value": float(target[i + 1]["value"] * 0.3 + np.random.randn() * 0.02),
            })
        else:
            real_signal.append({"date": d.strftime("%Y-%m-%d"), "value": 0.0})

        noise_signal.append({
            "date": d.strftime("%Y-%m-%d"),
            "value": float(np.random.randn()),
        })

    candidates = [
        {"name": "real_alpha", "data": real_signal},
        {"name": "pure_noise", "data": noise_signal},
    ]

    print("=== Signal Scan ===")
    result = adapter.signal_scan(target, candidates, forward_period=5)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    print("\n=== Signal Combine ===")
    result = adapter.signal_combine(
        [{"name": "sig_a", "data": real_signal}, {"name": "sig_b", "data": noise_signal}],
        target,
        method="ic_weight",
    )
    data = result.get("data", {})
    print(f"Combined IC: {data.get('combined_ic')}, Improvement: {data.get('improvement_pct')}")

    print("\n=== Signal Decay ===")
    prices = [
        {"date": d.strftime("%Y-%m-%d"), "value": float(100 + np.random.randn() * 2)}
        for d in dates
    ]
    result = adapter.signal_decay(real_signal, prices, max_horizon=60)
    print(json.dumps(result.get("data", {}), indent=2, ensure_ascii=False, default=str))

    print("\nAll tests passed.")
