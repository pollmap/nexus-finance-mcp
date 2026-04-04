"""
Volatility Model Adapter - Advanced Volatility Analysis Engine.

GARCH/EGARCH modeling, HMM regime detection, volatility surface,
ensemble forecasting, and VIX term structure analysis.

Dependencies: arch, hmmlearn, yfinance, numpy, pandas

Methods:
- garch_fit: GARCH(p,q) model fitting + forecast
- egarch_fit: EGARCH with leverage effect + news impact curve
- volatility_surface: Multi-window realized vol + vol cone + percentile
- hmm_regime: Hidden Markov Model volatility regime detection
- vol_forecast_ensemble: 4-model ensemble forecast (GARCH/EWMA/RV/Historical)
- vix_term_structure: VIX vs VIX3M contango/backwardation analysis

Input format:
- returns_series: list[dict] with {"date": "YYYY-MM-DD", "value": float}
- Accepts both returns (small values) and prices (auto-detected, auto-converted)

Run standalone test: python -m mcp_servers.adapters.volatility_model_adapter
"""
import logging
import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Suppress convergence warnings from arch/hmmlearn
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=FutureWarning)


class VolatilityModelAdapter:
    """Advanced volatility modeling and regime detection."""

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _to_series(data: List[Dict]) -> pd.Series:
        """Convert list[dict] to pandas Series with DatetimeIndex."""
        df = pd.DataFrame(data)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
        series = df["value"].astype(float)
        series.name = "value"
        return series

    @staticmethod
    def _is_prices(series: pd.Series) -> bool:
        """
        Auto-detect if series contains prices (not returns).
        Heuristic: if mean of absolute values > 1, treat as prices.
        """
        return float(np.mean(np.abs(series.dropna()))) > 1.0

    @staticmethod
    def _prices_to_returns(prices: pd.Series) -> pd.Series:
        """Convert price series to log returns."""
        returns = np.log(prices / prices.shift(1)).dropna()
        returns.name = "value"
        return returns

    def _prepare_returns(self, data: List[Dict]) -> Tuple[pd.Series, bool]:
        """
        Prepare returns series from input data.
        Returns (returns_series, was_converted_from_prices).
        """
        series = self._to_series(data)
        if self._is_prices(series):
            returns = self._prices_to_returns(series)
            return returns, True
        return series, False

    # ── 1. GARCH Fit ──────────────────────────────────────────────────

    def garch_fit(
        self,
        series: List[Dict],
        p: int = 1,
        q: int = 1,
        horizon: int = 5,
    ) -> Dict[str, Any]:
        """
        Fit GARCH(p,q) model and produce volatility forecast.

        Args:
            series: list[dict] with {"date", "value"} (returns or prices)
            p: GARCH lag order for variance
            q: ARCH lag order for squared residuals
            horizon: forecast horizon in days

        Returns:
            params, persistence, conditional_volatility, forecast, aic, bic
        """
        try:
            from arch import arch_model
        except ImportError:
            return {
                "success": False,
                "error": "arch package not installed. Run: pip install arch",
            }

        try:
            returns, converted = self._prepare_returns(series)
            if len(returns) < 50:
                return {
                    "success": False,
                    "error": f"Insufficient data: {len(returns)} observations (need >= 50)",
                }

            # GARCH expects returns in percentage
            returns_pct = returns * 100

            model = arch_model(
                returns_pct,
                vol="Garch",
                p=p,
                q=q,
                dist="normal",
                mean="Constant",
            )
            result = model.fit(disp="off", show_warning=False)

            # Extract parameters
            params = {}
            for param_name in result.params.index:
                params[param_name] = round(float(result.params[param_name]), 8)

            # Persistence = sum of alpha + beta coefficients
            alpha_sum = sum(
                v for k, v in params.items() if k.startswith("alpha")
            )
            beta_sum = sum(
                v for k, v in params.items() if k.startswith("beta")
            )
            persistence = round(alpha_sum + beta_sum, 6)

            # Conditional volatility (last 20, convert back from % to decimal)
            cond_vol = result.conditional_volatility
            cond_vol_tail = cond_vol.iloc[-20:]
            cond_vol_list = [
                {
                    "date": d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d),
                    "volatility_daily": round(float(v) / 100, 6),
                    "volatility_annual": round(float(v) / 100 * np.sqrt(252), 6),
                }
                for d, v in cond_vol_tail.items()
            ]

            # Forecast
            forecast = result.forecast(horizon=horizon)
            variance_forecast = forecast.variance.iloc[-1]
            vol_forecast = [
                {
                    "day": i + 1,
                    "volatility_daily": round(float(np.sqrt(v)) / 100, 6),
                    "volatility_annual": round(
                        float(np.sqrt(v)) / 100 * np.sqrt(252), 6
                    ),
                }
                for i, v in enumerate(variance_forecast.values)
            ]

            return {
                "success": True,
                "data": {
                    "model": f"GARCH({p},{q})",
                    "observations": len(returns),
                    "input_converted_from_prices": converted,
                    "params": params,
                    "persistence": persistence,
                    "half_life_days": (
                        round(np.log(0.5) / np.log(persistence), 1)
                        if 0 < persistence < 1
                        else None
                    ),
                    "conditional_volatility_last20": cond_vol_list,
                    "forecast": vol_forecast,
                    "aic": round(float(result.aic), 2),
                    "bic": round(float(result.bic), 2),
                    "log_likelihood": round(float(result.loglikelihood), 2),
                },
            }

        except Exception as e:
            logger.exception("GARCH fit failed")
            return {
                "success": False,
                "error": f"GARCH fitting failed: {str(e)}",
                "hint": "Check data quality: need continuous daily returns, no NaN/Inf",
            }

    # ── 2. EGARCH Fit ─────────────────────────────────────────────────

    def egarch_fit(
        self,
        series: List[Dict],
        horizon: int = 5,
    ) -> Dict[str, Any]:
        """
        Fit EGARCH(1,1,1) model capturing leverage effects.

        Leverage effect: negative shocks (drops) increase volatility
        more than positive shocks (rallies) of the same magnitude.

        Args:
            series: list[dict] with {"date", "value"}
            horizon: forecast horizon in days

        Returns:
            params, leverage_effect, news_impact_curve, forecast
        """
        try:
            from arch import arch_model
        except ImportError:
            return {
                "success": False,
                "error": "arch package not installed. Run: pip install arch",
            }

        try:
            returns, converted = self._prepare_returns(series)
            if len(returns) < 50:
                return {
                    "success": False,
                    "error": f"Insufficient data: {len(returns)} observations (need >= 50)",
                }

            returns_pct = returns * 100

            model = arch_model(
                returns_pct,
                vol="EGARCH",
                p=1,
                o=1,
                q=1,
                dist="normal",
                mean="Constant",
            )
            result = model.fit(disp="off", show_warning=False)

            # Extract params
            params = {}
            for param_name in result.params.index:
                params[param_name] = round(float(result.params[param_name]), 8)

            # Leverage effect: gamma coefficient (the 'o' asymmetry term)
            gamma = None
            for k, v in params.items():
                if "gamma" in k.lower():
                    gamma = v
                    break

            leverage_interpretation = None
            if gamma is not None:
                if gamma < 0:
                    leverage_interpretation = (
                        f"Negative gamma ({gamma:.4f}): negative shocks increase "
                        f"volatility more than positive shocks (leverage effect present)"
                    )
                else:
                    leverage_interpretation = (
                        f"Positive gamma ({gamma:.4f}): no traditional leverage effect"
                    )

            # News impact curve: how shocks of different sizes affect variance
            shock_range = np.linspace(-3, 3, 25)
            # EGARCH log-variance response: omega + alpha*|z| + gamma*z + beta*log(sigma^2)
            omega = params.get("omega", 0)
            alpha_vals = [v for k, v in params.items() if k.startswith("alpha")]
            alpha = alpha_vals[0] if alpha_vals else 0
            gamma_val = gamma if gamma is not None else 0

            news_impact = []
            for shock in shock_range:
                # Simplified NIC: variance response proportional to
                # alpha * |shock| + gamma * shock
                response = alpha * abs(shock) + gamma_val * shock
                news_impact.append({
                    "shock_std": round(float(shock), 2),
                    "log_variance_response": round(float(response), 6),
                })

            # Forecast (EGARCH requires simulation for horizon > 1)
            try:
                if horizon == 1:
                    forecast = result.forecast(horizon=1)
                    variance_forecast = forecast.variance.iloc[-1].values
                else:
                    forecast = result.forecast(
                        horizon=horizon, method="simulation", simulations=1000
                    )
                    variance_forecast = forecast.variance.iloc[-1].values
            except Exception:
                # Fallback: only 1-step forecast
                forecast = result.forecast(horizon=1)
                variance_forecast = forecast.variance.iloc[-1].values
                # Extend with last value for remaining horizon
                last_var = variance_forecast[-1]
                variance_forecast = np.concatenate([
                    variance_forecast, np.full(horizon - 1, last_var)
                ])

            vol_forecast = [
                {
                    "day": i + 1,
                    "volatility_daily": round(float(np.sqrt(v)) / 100, 6),
                    "volatility_annual": round(
                        float(np.sqrt(v)) / 100 * np.sqrt(252), 6
                    ),
                }
                for i, v in enumerate(variance_forecast[:horizon])
            ]

            # Conditional vol last 20
            cond_vol = result.conditional_volatility
            cond_vol_tail = cond_vol.iloc[-20:]
            cond_vol_list = [
                {
                    "date": d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d),
                    "volatility_daily": round(float(v) / 100, 6),
                    "volatility_annual": round(float(v) / 100 * np.sqrt(252), 6),
                }
                for d, v in cond_vol_tail.items()
            ]

            return {
                "success": True,
                "data": {
                    "model": "EGARCH(1,1,1)",
                    "observations": len(returns),
                    "input_converted_from_prices": converted,
                    "params": params,
                    "leverage_effect": {
                        "gamma": gamma,
                        "interpretation": leverage_interpretation,
                    },
                    "news_impact_curve": news_impact,
                    "conditional_volatility_last20": cond_vol_list,
                    "forecast": vol_forecast,
                    "aic": round(float(result.aic), 2),
                    "bic": round(float(result.bic), 2),
                },
            }

        except Exception as e:
            logger.exception("EGARCH fit failed")
            return {
                "success": False,
                "error": f"EGARCH fitting failed: {str(e)}",
                "hint": "EGARCH may fail on very short or very noisy series",
            }

    # ── 3. Volatility Surface ────────────────────────────────────────

    def volatility_surface(
        self,
        series: List[Dict],
    ) -> Dict[str, Any]:
        """
        Compute realized volatility across multiple time windows
        with historical percentiles and volatility cone.

        Args:
            series: list[dict] with {"date", "value"} (returns or prices)

        Returns:
            vol_by_window, vol_cone (min/25/50/75/max per window)
        """
        try:
            returns, converted = self._prepare_returns(series)
            if len(returns) < 60:
                return {
                    "success": False,
                    "error": f"Insufficient data: {len(returns)} observations (need >= 60)",
                }

            windows = [5, 10, 20, 40, 60, 120, 252]
            sqrt252 = np.sqrt(252)

            vol_by_window = []
            vol_cone = []

            for w in windows:
                if len(returns) < w:
                    continue

                # Rolling realized volatility (annualized)
                rolling_vol = returns.rolling(window=w).std() * sqrt252
                rolling_vol = rolling_vol.dropna()

                if len(rolling_vol) == 0:
                    continue

                current_vol = float(rolling_vol.iloc[-1])

                # Historical percentile: current vol vs last 2 years (504 trading days)
                lookback = min(len(rolling_vol), 504)
                recent_vols = rolling_vol.iloc[-lookback:]
                percentile = float(
                    (recent_vols < current_vol).sum() / len(recent_vols) * 100
                )

                vol_by_window.append({
                    "window_days": w,
                    "current_vol_annualized": round(current_vol, 6),
                    "current_vol_daily": round(current_vol / sqrt252, 6),
                    "percentile_2y": round(percentile, 1),
                })

                # Volatility cone: distribution of rolling vol
                vol_cone.append({
                    "window_days": w,
                    "min": round(float(recent_vols.min()), 6),
                    "p25": round(float(recent_vols.quantile(0.25)), 6),
                    "p50": round(float(recent_vols.quantile(0.50)), 6),
                    "p75": round(float(recent_vols.quantile(0.75)), 6),
                    "max": round(float(recent_vols.max()), 6),
                    "current": round(current_vol, 6),
                })

            # Overall regime assessment
            if vol_by_window:
                avg_pct = np.mean([v["percentile_2y"] for v in vol_by_window])
                if avg_pct > 80:
                    regime = "극고변동성 (Extreme High)"
                elif avg_pct > 60:
                    regime = "고변동성 (High)"
                elif avg_pct > 40:
                    regime = "보통 (Normal)"
                elif avg_pct > 20:
                    regime = "저변동성 (Low)"
                else:
                    regime = "극저변동성 (Extreme Low)"
            else:
                regime = "unknown"
                avg_pct = None

            return {
                "success": True,
                "data": {
                    "observations": len(returns),
                    "input_converted_from_prices": converted,
                    "vol_by_window": vol_by_window,
                    "vol_cone": vol_cone,
                    "regime_assessment": regime,
                    "avg_percentile": round(float(avg_pct), 1) if avg_pct is not None else None,
                },
            }

        except Exception as e:
            logger.exception("Volatility surface failed")
            return {"success": False, "error": str(e)}

    # ── 4. HMM Regime Detection ──────────────────────────────────────

    def hmm_regime(
        self,
        series: List[Dict],
        n_regimes: int = 2,
    ) -> Dict[str, Any]:
        """
        Hidden Markov Model for volatility regime detection.

        Args:
            series: list[dict] with {"date", "value"}
            n_regimes: number of hidden states (default 2: low-vol, high-vol)

        Returns:
            regimes, transition_matrix, current_regime, state_sequence
        """
        try:
            from hmmlearn.hmm import GaussianHMM
        except ImportError:
            return {
                "success": False,
                "error": "hmmlearn not installed. Run: pip install hmmlearn",
            }

        try:
            returns, converted = self._prepare_returns(series)
            if len(returns) < 100:
                return {
                    "success": False,
                    "error": f"Insufficient data: {len(returns)} observations (need >= 100 for HMM)",
                }

            # Feature matrix: [return, rolling_vol_10d]
            rolling_vol = returns.rolling(window=10).std().fillna(method="bfill")
            features = np.column_stack([
                returns.values,
                rolling_vol.values,
            ])

            # Fit HMM
            model = GaussianHMM(
                n_components=n_regimes,
                covariance_type="full",
                n_iter=200,
                random_state=42,
                tol=1e-4,
            )
            model.fit(features)
            states = model.predict(features)

            # Compute per-regime statistics
            regime_stats = []
            for i in range(n_regimes):
                mask = states == i
                regime_returns = returns.values[mask]
                regime_stats.append({
                    "regime_id": i,
                    "mean_return_daily": round(float(np.mean(regime_returns)), 6),
                    "mean_return_annual": round(float(np.mean(regime_returns) * 252), 4),
                    "volatility_daily": round(float(np.std(regime_returns)), 6),
                    "volatility_annual": round(
                        float(np.std(regime_returns) * np.sqrt(252)), 4
                    ),
                    "days_in_regime": int(mask.sum()),
                    "pct_of_total": round(float(mask.sum() / len(states) * 100), 1),
                })

            # Sort regimes by volatility (0 = low vol, 1+ = higher vol)
            regime_stats.sort(key=lambda x: x["volatility_daily"])
            # Build mapping: original_id -> sorted_id
            id_map = {
                regime_stats[i]["regime_id"]: i
                for i in range(len(regime_stats))
            }
            # Reassign regime_id to sorted order
            for i, rs in enumerate(regime_stats):
                rs["regime_id"] = i
                rs["label"] = (
                    "저변동성 (Low Vol)" if i == 0
                    else "고변동성 (High Vol)" if i == n_regimes - 1
                    else f"중간변동성 (Mid Vol {i})"
                )

            # Remap states
            sorted_states = np.array([id_map[s] for s in states])

            # Stationary distribution
            try:
                transmat = model.transmat_
                # Remap transition matrix
                order = [
                    k for k, v in sorted(id_map.items(), key=lambda x: x[1])
                ]
                transmat_sorted = transmat[np.ix_(order, order)]

                eigenvalues, eigenvectors = np.linalg.eig(transmat_sorted.T)
                idx = np.argmin(np.abs(eigenvalues - 1.0))
                stationary = np.real(eigenvectors[:, idx])
                stationary = stationary / stationary.sum()

                for i, rs in enumerate(regime_stats):
                    rs["stationary_prob"] = round(float(stationary[i]), 4)
            except Exception:
                transmat_sorted = model.transmat_
                for rs in regime_stats:
                    rs["stationary_prob"] = None

            # Transition matrix as list of lists
            trans_matrix = [
                [round(float(v), 4) for v in row]
                for row in transmat_sorted
            ]

            # Current regime
            current = int(sorted_states[-1])

            # State sequence (last 60 days)
            dates = returns.index[-60:]
            state_seq = [
                {
                    "date": d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d),
                    "regime": int(sorted_states[-(60 - i)]) if len(sorted_states) >= 60 else int(sorted_states[i]),
                }
                for i, d in enumerate(dates)
            ]

            return {
                "success": True,
                "data": {
                    "n_regimes": n_regimes,
                    "observations": len(returns),
                    "input_converted_from_prices": converted,
                    "regimes": regime_stats,
                    "transition_matrix": trans_matrix,
                    "current_regime": current,
                    "current_regime_label": regime_stats[current]["label"],
                    "state_sequence_last60": state_seq,
                    "model_score": round(float(model.score(features)), 2),
                },
            }

        except Exception as e:
            logger.exception("HMM regime detection failed")
            return {
                "success": False,
                "error": f"HMM regime detection failed: {str(e)}",
                "hint": "Ensure sufficient data (>100 obs) and try n_regimes=2 or 3",
            }

    # ── 5. Ensemble Volatility Forecast ──────────────────────────────

    def vol_forecast_ensemble(
        self,
        series: List[Dict],
        horizon: int = 5,
    ) -> Dict[str, Any]:
        """
        Ensemble volatility forecast combining 4 methods:
        - GARCH(1,1)
        - EWMA (RiskMetrics, lambda=0.94)
        - Realized volatility (20-day rolling)
        - Simple historical average

        Weights determined by inverse of recent forecast error.

        Args:
            series: list[dict] with {"date", "value"}
            horizon: forecast horizon in days

        Returns:
            ensemble_forecast, individual_forecasts, model_weights
        """
        try:
            returns, converted = self._prepare_returns(series)
            if len(returns) < 60:
                return {
                    "success": False,
                    "error": f"Insufficient data: {len(returns)} observations (need >= 60)",
                }

            sqrt252 = np.sqrt(252)
            ret_vals = returns.values

            forecasts = {}
            errors = {}

            # ---- Method 1: GARCH(1,1) ----
            garch_forecast = None
            try:
                from arch import arch_model

                returns_pct = returns * 100
                model = arch_model(
                    returns_pct, vol="Garch", p=1, q=1, dist="normal", mean="Constant"
                )
                result = model.fit(disp="off", show_warning=False)
                fc = result.forecast(horizon=horizon)
                garch_daily = [
                    float(np.sqrt(v)) / 100
                    for v in fc.variance.iloc[-1].values
                ]
                garch_forecast = garch_daily

                # Backtest error: compare GARCH 1-day forecast vs realized
                cond_vol = result.conditional_volatility.values / 100
                realized_1d = np.abs(ret_vals)
                overlap = min(len(cond_vol), len(realized_1d))
                eval_window = min(overlap, 60)
                garch_err = float(np.mean(
                    (cond_vol[-eval_window:] - realized_1d[-eval_window:]) ** 2
                ))
                errors["garch"] = garch_err
                forecasts["garch"] = garch_daily
            except Exception as e:
                logger.warning(f"GARCH forecast failed: {e}")

            # ---- Method 2: EWMA (RiskMetrics lambda=0.94) ----
            lam = 0.94
            ewma_var = np.zeros(len(ret_vals))
            ewma_var[0] = ret_vals[0] ** 2
            for t in range(1, len(ret_vals)):
                ewma_var[t] = lam * ewma_var[t - 1] + (1 - lam) * ret_vals[t] ** 2

            # EWMA forecast: variance stays constant at last estimate
            last_ewma_var = ewma_var[-1]
            ewma_daily = [float(np.sqrt(last_ewma_var))] * horizon
            forecasts["ewma"] = ewma_daily

            # EWMA backtest error
            ewma_vol = np.sqrt(ewma_var)
            eval_window = min(len(ewma_vol), 60)
            ewma_err = float(np.mean(
                (ewma_vol[-eval_window:] - np.abs(ret_vals[-eval_window:])) ** 2
            ))
            errors["ewma"] = ewma_err

            # ---- Method 3: Realized Volatility (20-day rolling) ----
            rv_window = 20
            rv = float(np.std(ret_vals[-rv_window:]))
            rv_daily = [rv] * horizon
            forecasts["realized_vol"] = rv_daily

            # RV backtest error
            rolling_rv = pd.Series(ret_vals).rolling(rv_window).std().dropna().values
            eval_len = min(len(rolling_rv), 60)
            rv_err = float(np.mean(
                (rolling_rv[-eval_len:] - np.abs(ret_vals[-eval_len:])) ** 2
            ))
            errors["realized_vol"] = rv_err

            # ---- Method 4: Historical Average ----
            hist_vol = float(np.std(ret_vals))
            hist_daily = [hist_vol] * horizon
            forecasts["historical_avg"] = hist_daily

            # Historical backtest error (constant prediction)
            hist_err = float(np.mean(
                (hist_vol - np.abs(ret_vals[-60:])) ** 2
            ))
            errors["historical_avg"] = hist_err

            # ---- Compute weights (inverse error) ----
            active_models = list(forecasts.keys())
            inv_errors = {}
            for m in active_models:
                err = errors.get(m, 1e-6)
                inv_errors[m] = 1.0 / max(err, 1e-10)

            total_inv = sum(inv_errors.values())
            weights = {m: round(inv_errors[m] / total_inv, 4) for m in active_models}

            # ---- Ensemble forecast ----
            ensemble = []
            for d in range(horizon):
                weighted_vol = sum(
                    weights[m] * forecasts[m][d] for m in active_models
                )
                ensemble.append({
                    "day": d + 1,
                    "volatility_daily": round(weighted_vol, 6),
                    "volatility_annual": round(weighted_vol * sqrt252, 6),
                })

            # Individual forecasts formatted
            individual = {}
            for m in active_models:
                individual[m] = [
                    {
                        "day": d + 1,
                        "volatility_daily": round(forecasts[m][d], 6),
                        "volatility_annual": round(forecasts[m][d] * sqrt252, 6),
                    }
                    for d in range(horizon)
                ]

            return {
                "success": True,
                "data": {
                    "horizon_days": horizon,
                    "observations": len(returns),
                    "input_converted_from_prices": converted,
                    "ensemble_forecast": ensemble,
                    "individual_forecasts": individual,
                    "model_weights": weights,
                    "model_errors_mse": {
                        m: round(errors[m], 8) for m in active_models
                    },
                    "best_model": min(errors, key=errors.get),
                },
            }

        except Exception as e:
            logger.exception("Ensemble forecast failed")
            return {"success": False, "error": str(e)}

    # ── 6. VIX Term Structure ────────────────────────────────────────

    def vix_term_structure(self) -> Dict[str, Any]:
        """
        Fetch VIX and VIX3M to analyze term structure.

        Contango (VIX < VIX3M): normal, complacency
        Backwardation (VIX > VIX3M): fear, crisis

        Returns:
            vix_current, vix3m_current, ratio, structure, historical_ratio
        """
        try:
            import yfinance as yf
        except ImportError:
            return {
                "success": False,
                "error": "yfinance not installed. Run: pip install yfinance",
            }

        try:
            vix_ticker = yf.Ticker("^VIX")
            vix3m_ticker = yf.Ticker("^VIX3M")

            # Fetch 60 days of history (to get ~30 trading days)
            vix_hist = vix_ticker.history(period="3mo")
            vix3m_hist = vix3m_ticker.history(period="3mo")

            if vix_hist.empty:
                return {
                    "success": False,
                    "error": "Failed to fetch VIX data from yfinance",
                }

            vix_current = round(float(vix_hist["Close"].iloc[-1]), 2)

            # VIX3M may not always be available
            vix3m_current = None
            ratio = None
            structure = None
            historical_ratio = []

            if not vix3m_hist.empty:
                vix3m_current = round(float(vix3m_hist["Close"].iloc[-1]), 2)
                ratio = round(vix_current / vix3m_current, 4)

                if ratio < 1.0:
                    structure = "contango"
                    structure_meaning = (
                        "정상 구조: 단기 변동성 < 장기 변동성 → 시장 안정/자만"
                    )
                else:
                    structure = "backwardation"
                    structure_meaning = (
                        "역전 구조: 단기 변동성 > 장기 변동성 → 공포/위기"
                    )

                # Historical ratio (last 30 trading days)
                # Align dates
                common_dates = vix_hist.index.intersection(vix3m_hist.index)
                common_dates = common_dates[-30:]
                for d in common_dates:
                    v = float(vix_hist.loc[d, "Close"])
                    v3m = float(vix3m_hist.loc[d, "Close"])
                    historical_ratio.append({
                        "date": d.strftime("%Y-%m-%d"),
                        "vix": round(v, 2),
                        "vix3m": round(v3m, 2),
                        "ratio": round(v / v3m, 4) if v3m > 0 else None,
                    })
            else:
                structure = "unknown"
                structure_meaning = "VIX3M 데이터 없음"

            # VIX percentile (current vs last 60 trading days)
            vix_closes = vix_hist["Close"].dropna()
            vix_percentile = round(
                float((vix_closes < vix_current).sum() / len(vix_closes) * 100), 1
            )

            # VIX level interpretation
            if vix_current < 12:
                vix_level = "극저 (Extreme Low) - 자만/바닥 경고"
            elif vix_current < 15:
                vix_level = "저 (Low) - 안정"
            elif vix_current < 20:
                vix_level = "보통 (Normal)"
            elif vix_current < 25:
                vix_level = "고 (Elevated)"
            elif vix_current < 30:
                vix_level = "고경계 (High) - 경계"
            elif vix_current < 40:
                vix_level = "매우 높음 (Very High) - 공포"
            else:
                vix_level = "극단 (Extreme) - 패닉/위기"

            return {
                "success": True,
                "data": {
                    "vix_current": vix_current,
                    "vix3m_current": vix3m_current,
                    "ratio": ratio,
                    "structure": structure,
                    "structure_meaning": structure_meaning,
                    "vix_level": vix_level,
                    "vix_percentile_3mo": vix_percentile,
                    "historical_ratio_30d": historical_ratio,
                    "as_of": vix_hist.index[-1].strftime("%Y-%m-%d"),
                },
            }

        except Exception as e:
            logger.exception("VIX term structure failed")
            return {"success": False, "error": str(e)}


# ── Standalone test ──────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    adapter = VolatilityModelAdapter()

    # Generate synthetic daily returns for testing
    np.random.seed(42)
    n = 500
    dates = pd.bdate_range(end="2026-04-03", periods=n)
    # Simulate GARCH-like returns
    returns = []
    vol = 0.01
    for _ in range(n):
        vol = np.sqrt(0.00001 + 0.1 * (returns[-1] if returns else 0) ** 2 + 0.85 * vol ** 2)
        r = np.random.normal(0.0003, vol)
        returns.append(r)

    test_data = [
        {"date": d.strftime("%Y-%m-%d"), "value": r}
        for d, r in zip(dates, returns)
    ]

    print("=" * 60)
    print("1. GARCH(1,1) Fit")
    print("=" * 60)
    result = adapter.garch_fit(test_data)
    print(json.dumps(result, indent=2, default=str)[:1000])

    print("\n" + "=" * 60)
    print("2. EGARCH Fit")
    print("=" * 60)
    result = adapter.egarch_fit(test_data)
    print(json.dumps(result, indent=2, default=str)[:1000])

    print("\n" + "=" * 60)
    print("3. Volatility Surface")
    print("=" * 60)
    result = adapter.volatility_surface(test_data)
    print(json.dumps(result, indent=2, default=str)[:1000])

    print("\n" + "=" * 60)
    print("4. HMM Regime Detection")
    print("=" * 60)
    result = adapter.hmm_regime(test_data)
    print(json.dumps(result, indent=2, default=str)[:1000])

    print("\n" + "=" * 60)
    print("5. Ensemble Forecast")
    print("=" * 60)
    result = adapter.vol_forecast_ensemble(test_data)
    print(json.dumps(result, indent=2, default=str)[:1000])

    print("\n" + "=" * 60)
    print("6. VIX Term Structure")
    print("=" * 60)
    result = adapter.vix_term_structure()
    print(json.dumps(result, indent=2, default=str)[:1000])
