"""Factor Engine Adapter — Multi-factor quantitative model engine.

Compute factor scores (momentum, value, quality, low_vol, size, reversal),
backtest factors, analyze correlations, measure portfolio exposure,
detect factor timing regimes, and build custom factors.

Universal format:
  stocks_data: {ticker: [{"date","open","high","low","close","volume"}, ...]}
  financial_data: {ticker: {"per","pbr","roe","operating_margin","debt_ratio","market_cap"}}
"""
import logging
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcp_servers.core.responses import error_response, success_response

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

# Default factor list
DEFAULT_FACTORS = ["momentum", "value", "quality", "low_vol", "size", "reversal"]
# Factors that require financial_data
FINANCIAL_FACTORS = {"value", "quality", "size"}


class FactorEngineAdapter:
    """Multi-factor quantitative model engine."""

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _to_df(ohlcv_list: List[Dict]) -> pd.DataFrame:
        """Convert list of OHLCV dicts to DataFrame indexed by date."""
        df = pd.DataFrame(ohlcv_list)
        df["date"] = pd.to_datetime(df["date"])
        df = df.drop_duplicates(subset="date").sort_values("date").set_index("date")
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    @staticmethod
    def _zscore(series: pd.Series) -> pd.Series:
        """Cross-sectional z-score (across stocks)."""
        m = series.mean()
        s = series.std()
        if s == 0 or pd.isna(s):
            return pd.Series(0.0, index=series.index)
        return (series - m) / s

    @staticmethod
    def _spearman_ic(factor_scores: pd.Series, forward_returns: pd.Series) -> float:
        """Information Coefficient = Spearman rank correlation."""
        aligned = pd.concat([factor_scores, forward_returns], axis=1).dropna()
        if len(aligned) < 5:
            return float("nan")
        corr, _ = stats.spearmanr(aligned.iloc[:, 0], aligned.iloc[:, 1])
        return float(corr)

    def _build_stock_dfs(
        self, stocks_data: Dict[str, List[Dict]]
    ) -> Dict[str, pd.DataFrame]:
        """Convert all tickers to DataFrames."""
        result = {}
        for ticker, ohlcv_list in stocks_data.items():
            try:
                df = self._to_df(ohlcv_list)
                if len(df) >= 5:
                    result[ticker] = df
            except Exception as e:
                logger.warning("Failed to parse %s: %s", ticker, e)
        return result

    # ------------------------------------------------------------------ #
    # raw factor computations (per-stock)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _calc_momentum(df: pd.DataFrame) -> Optional[float]:
        """12-month return excluding last month."""
        if len(df) < 252:
            # fallback: use available data minus last 21 days
            if len(df) < 42:
                return None
            ret_12m = df["close"].iloc[-22] / df["close"].iloc[0] - 1.0
            return float(ret_12m)
        close = df["close"]
        ret = close.iloc[-22] / close.iloc[-252] - 1.0
        return float(ret)

    @staticmethod
    def _calc_reversal(df: pd.DataFrame) -> Optional[float]:
        """Short-term reversal: -1 * 5-day return."""
        if len(df) < 6:
            return None
        ret_5d = df["close"].iloc[-1] / df["close"].iloc[-6] - 1.0
        return -1.0 * float(ret_5d)

    @staticmethod
    def _calc_low_vol(df: pd.DataFrame) -> Optional[float]:
        """Low volatility: -1 * 60-day rolling std of daily returns."""
        if len(df) < 61:
            return None
        returns = df["close"].pct_change().dropna()
        if len(returns) < 60:
            return None
        vol = returns.iloc[-60:].std()
        return -1.0 * float(vol)

    @staticmethod
    def _calc_value(fin: Dict) -> Optional[float]:
        """Value = 1/PER (or 1/PBR if PER missing)."""
        per = fin.get("per")
        pbr = fin.get("pbr")
        if per and float(per) > 0:
            return 1.0 / float(per)
        if pbr and float(pbr) > 0:
            return 1.0 / float(pbr)
        return None

    @staticmethod
    def _calc_quality(fin: Dict) -> Optional[float]:
        """Quality = ROE * operating_margin / (1 + debt_ratio)."""
        roe = fin.get("roe")
        om = fin.get("operating_margin")
        dr = fin.get("debt_ratio")
        if roe is None or om is None or dr is None:
            return None
        try:
            roe_f = float(roe)
            om_f = float(om)
            dr_f = float(dr)
            return roe_f * om_f / (1.0 + dr_f)
        except (ValueError, ZeroDivisionError):
            return None

    @staticmethod
    def _calc_size(fin: Dict) -> Optional[float]:
        """Size = -1 * log(market_cap) (small cap premium)."""
        mc = fin.get("market_cap")
        if mc is None or float(mc) <= 0:
            return None
        return -1.0 * math.log(float(mc))

    def _compute_raw_factors(
        self,
        stock_dfs: Dict[str, pd.DataFrame],
        financial_data: Optional[Dict[str, Dict]],
        factors: List[str],
    ) -> Dict[str, Dict[str, Optional[float]]]:
        """Compute raw factor values for each ticker.

        Returns: {ticker: {factor_name: raw_value}}
        """
        financial_data = financial_data or {}
        raw = {}
        for ticker, df in stock_dfs.items():
            fin = financial_data.get(ticker, {})
            vals = {}
            for f in factors:
                if f == "momentum":
                    vals[f] = self._calc_momentum(df)
                elif f == "reversal":
                    vals[f] = self._calc_reversal(df)
                elif f == "low_vol":
                    vals[f] = self._calc_low_vol(df)
                elif f == "value":
                    vals[f] = self._calc_value(fin) if fin else None
                elif f == "quality":
                    vals[f] = self._calc_quality(fin) if fin else None
                elif f == "size":
                    vals[f] = self._calc_size(fin) if fin else None
                else:
                    vals[f] = None
            raw[ticker] = vals
        return raw

    def _cross_sectional_zscore(
        self, raw: Dict[str, Dict[str, Optional[float]]], factors: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """Convert raw factor values to cross-sectional z-scores.

        Returns: {ticker: {factor_name: z_score}}
        """
        tickers = list(raw.keys())
        zscores = {t: {} for t in tickers}
        for f in factors:
            series = pd.Series(
                {t: raw[t].get(f) for t in tickers}, dtype=float
            ).dropna()
            if len(series) < 2:
                for t in tickers:
                    zscores[t][f] = 0.0
                continue
            z = self._zscore(series)
            for t in tickers:
                zscores[t][f] = float(z.get(t, 0.0))
        return zscores

    # ------------------------------------------------------------------ #
    # 1. factor_score
    # ------------------------------------------------------------------ #

    def factor_score(
        self,
        stocks_data: Dict[str, List[Dict]],
        financial_data: Optional[Dict[str, Dict]] = None,
        factors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Compute multi-factor scores for a universe of stocks.

        Args:
            stocks_data: {ticker: [{date, open, high, low, close, volume}, ...]}
            financial_data: {ticker: {per, pbr, roe, operating_margin, debt_ratio, market_cap}}
            factors: list of factor names. Default all 6 factors.

        Returns:
            {ticker: {factor_scores: {name: z}, composite: z, rank: int}}
        """
        try:
            if factors is None:
                factors = list(DEFAULT_FACTORS)

            # Skip financial factors if no financial_data provided
            if not financial_data:
                skipped = [f for f in factors if f in FINANCIAL_FACTORS]
                if skipped:
                    logger.info(
                        "No financial_data provided — skipping factors: %s", skipped
                    )
                    factors = [f for f in factors if f not in FINANCIAL_FACTORS]

            if not factors:
                return error_response("No computable factors after filtering")

            stock_dfs = self._build_stock_dfs(stocks_data)
            if len(stock_dfs) < 2:
                return error_response(f"Need at least 2 valid stocks, got {len(stock_dfs)}")

            # Compute raw → z-scores
            raw = self._compute_raw_factors(stock_dfs, financial_data, factors)
            zscores = self._cross_sectional_zscore(raw, factors)

            # Composite score = equal-weighted sum of z-scores
            composites = {}
            for t in zscores:
                valid_z = [v for v in zscores[t].values() if not math.isnan(v)]
                composites[t] = sum(valid_z) / len(valid_z) if valid_z else 0.0

            # Rank by composite (1 = best)
            sorted_tickers = sorted(composites, key=composites.get, reverse=True)
            ranks = {t: i + 1 for i, t in enumerate(sorted_tickers)}

            result = {}
            for t in zscores:
                result[t] = {
                    "factor_scores": {
                        f: round(zscores[t].get(f, 0.0), 4) for f in factors
                    },
                    "composite": round(composites[t], 4),
                    "rank": ranks[t],
                }

            return success_response(
                result,
                source="Factor Engine",
                factors_computed=factors,
                n_stocks=len(result),
            )

        except Exception as e:
            logger.exception("factor_score failed")
            return error_response(str(e))

    # ------------------------------------------------------------------ #
    # 2. factor_backtest
    # ------------------------------------------------------------------ #

    def factor_backtest(
        self,
        stocks_data: Dict[str, List[Dict]],
        factor_name: str,
        n_quantiles: int = 5,
        rebalance_freq: str = "monthly",
    ) -> Dict[str, Any]:
        """Long-short backtest for a single factor.

        Sorts stocks into quantiles by factor score each period.
        Top quantile = long, bottom quantile = short.

        Args:
            stocks_data: {ticker: [{date, open, high, low, close, volume}, ...]}
            factor_name: one of momentum, reversal, low_vol
            n_quantiles: 5 = quintile
            rebalance_freq: "monthly"

        Returns:
            long_return, short_return, long_short_return, IC stats, factor_decay
        """
        try:
            stock_dfs = self._build_stock_dfs(stocks_data)
            if len(stock_dfs) < n_quantiles:
                return error_response(f"Need at least {n_quantiles} stocks for {n_quantiles}-quantile sort")

            # Build combined close price panel
            close_dict = {}
            for ticker, df in stock_dfs.items():
                close_dict[ticker] = df["close"]
            panel = pd.DataFrame(close_dict).dropna(axis=0, how="all").ffill()
            if panel.empty:
                return error_response("No overlapping date range")

            # Monthly returns
            monthly = panel.resample("ME").last()
            monthly_ret = monthly.pct_change().dropna(how="all")

            if len(monthly_ret) < 3:
                return error_response("Not enough monthly data for backtest")

            tickers = list(stock_dfs.keys())
            ic_list = []
            long_returns = []
            short_returns = []
            long_short_returns = []

            # Factor decay: IC at lag 1, 2, 3 months
            decay_ics = {1: [], 2: [], 3: []}

            for i in range(len(monthly_ret) - 1):
                date = monthly_ret.index[i]
                fwd_ret = monthly_ret.iloc[i + 1]

                # Compute factor score at this point
                factor_vals = {}
                for t in tickers:
                    if t not in stock_dfs:
                        continue
                    df = stock_dfs[t]
                    subset = df[df.index <= date]
                    if factor_name == "momentum":
                        val = self._calc_momentum(subset)
                    elif factor_name == "reversal":
                        val = self._calc_reversal(subset)
                    elif factor_name == "low_vol":
                        val = self._calc_low_vol(subset)
                    else:
                        val = self._calc_momentum(subset)  # fallback
                    if val is not None:
                        factor_vals[t] = val

                if len(factor_vals) < n_quantiles:
                    continue

                scores = pd.Series(factor_vals)
                fwd = fwd_ret.reindex(scores.index).dropna()
                scores = scores.reindex(fwd.index).dropna()
                fwd = fwd.reindex(scores.index)

                if len(scores) < n_quantiles:
                    continue

                # IC
                ic = self._spearman_ic(scores, fwd)
                if not math.isnan(ic):
                    ic_list.append(ic)

                # Factor decay (IC at further forward periods)
                for lag in decay_ics:
                    if i + 1 + lag < len(monthly_ret):
                        fwd_lag = monthly_ret.iloc[i + 1 + lag].reindex(scores.index).dropna()
                        sc_lag = scores.reindex(fwd_lag.index).dropna()
                        fwd_lag = fwd_lag.reindex(sc_lag.index)
                        if len(sc_lag) >= n_quantiles:
                            ic_lag = self._spearman_ic(sc_lag, fwd_lag)
                            if not math.isnan(ic_lag):
                                decay_ics[lag].append(ic_lag)

                # Quantile sort
                try:
                    quantile_labels = pd.qcut(scores, n_quantiles, labels=False, duplicates="drop")
                except ValueError:
                    continue

                top_q = quantile_labels.max()
                bot_q = quantile_labels.min()

                long_tickers = quantile_labels[quantile_labels == top_q].index
                short_tickers = quantile_labels[quantile_labels == bot_q].index

                long_r = fwd.reindex(long_tickers).mean()
                short_r = fwd.reindex(short_tickers).mean()

                if not math.isnan(long_r):
                    long_returns.append(float(long_r))
                if not math.isnan(short_r):
                    short_returns.append(float(short_r))
                if not math.isnan(long_r) and not math.isnan(short_r):
                    long_short_returns.append(float(long_r - short_r))

            if not ic_list:
                return error_response("Could not compute any IC values")

            ic_arr = np.array(ic_list)
            ic_mean = float(np.mean(ic_arr))
            ic_std = float(np.std(ic_arr, ddof=1)) if len(ic_arr) > 1 else 0.0
            t_stat = float(ic_mean / (ic_std / math.sqrt(len(ic_arr)))) if ic_std > 0 else 0.0

            # Cumulative returns
            long_cum = float(np.prod([1 + r for r in long_returns]) - 1) if long_returns else 0.0
            short_cum = float(np.prod([1 + r for r in short_returns]) - 1) if short_returns else 0.0
            ls_cum = float(np.prod([1 + r for r in long_short_returns]) - 1) if long_short_returns else 0.0

            # Annualized
            n_months = len(long_returns) if long_returns else 1
            ann_factor = 12.0 / n_months if n_months > 0 else 1.0

            long_ann = float((1 + long_cum) ** ann_factor - 1)
            short_ann = float((1 + short_cum) ** ann_factor - 1)
            ls_ann = float((1 + ls_cum) ** ann_factor - 1)

            factor_decay = {
                f"lag_{lag}": round(float(np.mean(v)), 4) if v else None
                for lag, v in decay_ics.items()
            }

            return success_response(
                {
                    "factor": factor_name,
                    "n_quantiles": n_quantiles,
                    "n_periods": len(long_returns),
                    "long_return_cumulative": round(long_cum, 4),
                    "short_return_cumulative": round(short_cum, 4),
                    "long_short_return_cumulative": round(ls_cum, 4),
                    "long_return_annualized": round(long_ann, 4),
                    "short_return_annualized": round(short_ann, 4),
                    "long_short_return_annualized": round(ls_ann, 4),
                    "IC_mean": round(ic_mean, 4),
                    "IC_std": round(ic_std, 4),
                    "t_stat": round(t_stat, 4),
                    "significant": abs(t_stat) > 1.96,
                    "factor_decay": factor_decay,
                },
                source="Factor Engine",
            )

        except Exception as e:
            logger.exception("factor_backtest failed")
            return error_response(str(e))

    # ------------------------------------------------------------------ #
    # 3. factor_correlation
    # ------------------------------------------------------------------ #

    def factor_correlation(
        self,
        stocks_data: Dict[str, List[Dict]],
        financial_data: Optional[Dict[str, Dict]] = None,
    ) -> Dict[str, Any]:
        """Compute correlation matrix between all factors.

        Args:
            stocks_data: {ticker: [{date, open, high, low, close, volume}, ...]}
            financial_data: optional {ticker: {per, pbr, roe, ...}}

        Returns:
            correlation_matrix, redundant pairs (|r| > 0.7)
        """
        try:
            factors = list(DEFAULT_FACTORS)
            if not financial_data:
                factors = [f for f in factors if f not in FINANCIAL_FACTORS]

            stock_dfs = self._build_stock_dfs(stocks_data)
            if len(stock_dfs) < 3:
                return error_response("Need at least 3 stocks")

            raw = self._compute_raw_factors(stock_dfs, financial_data, factors)

            # Build factor matrix: rows=tickers, cols=factors
            tickers = list(raw.keys())
            factor_df = pd.DataFrame(
                {f: {t: raw[t].get(f) for t in tickers} for f in factors},
                dtype=float,
            )
            factor_df = factor_df.dropna(how="all")

            if len(factor_df) < 3:
                return error_response("Not enough stocks with factor data")

            corr = factor_df.corr(method="spearman")

            # Find redundant pairs
            redundant = []
            for i in range(len(factors)):
                for j in range(i + 1, len(factors)):
                    r = corr.iloc[i, j]
                    if not math.isnan(r) and abs(r) > 0.7:
                        redundant.append({
                            "factor_a": factors[i],
                            "factor_b": factors[j],
                            "correlation": round(float(r), 4),
                        })

            corr_dict = {}
            for f in corr.columns:
                corr_dict[f] = {
                    f2: round(float(corr.loc[f, f2]), 4)
                    for f2 in corr.columns
                    if not math.isnan(corr.loc[f, f2])
                }

            return success_response(
                {
                    "correlation_matrix": corr_dict,
                    "redundant_pairs": redundant,
                    "n_factors": len(factors),
                    "n_stocks": len(factor_df),
                    "factors": factors,
                },
                source="Factor Engine",
            )

        except Exception as e:
            logger.exception("factor_correlation failed")
            return error_response(str(e))

    # ------------------------------------------------------------------ #
    # 4. factor_exposure
    # ------------------------------------------------------------------ #

    def factor_exposure(
        self,
        portfolio_weights: Dict[str, float],
        stocks_data: Dict[str, List[Dict]],
        financial_data: Optional[Dict[str, Dict]] = None,
    ) -> Dict[str, Any]:
        """Compute weighted-average factor exposure of a portfolio.

        Args:
            portfolio_weights: {ticker: weight} (should sum to ~1.0)
            stocks_data: {ticker: [{date, open, high, low, close, volume}, ...]}
            financial_data: optional {ticker: {per, pbr, roe, ...}}

        Returns:
            {factor_name: portfolio_exposure}, risk assessment
        """
        try:
            factors = list(DEFAULT_FACTORS)
            if not financial_data:
                factors = [f for f in factors if f not in FINANCIAL_FACTORS]

            stock_dfs = self._build_stock_dfs(stocks_data)
            if not stock_dfs:
                return error_response("No valid stock data")

            raw = self._compute_raw_factors(stock_dfs, financial_data, factors)
            zscores = self._cross_sectional_zscore(raw, factors)

            total_weight = sum(portfolio_weights.values())
            if total_weight == 0:
                return error_response("Portfolio weights sum to 0")

            # Normalize weights
            norm_weights = {
                t: w / total_weight for t, w in portfolio_weights.items()
            }

            exposures = {}
            for f in factors:
                weighted_sum = 0.0
                covered_weight = 0.0
                for t, w in norm_weights.items():
                    if t in zscores and f in zscores[t]:
                        z = zscores[t][f]
                        if not math.isnan(z):
                            weighted_sum += w * z
                            covered_weight += w
                exposures[f] = round(weighted_sum, 4) if covered_weight > 0 else None

            # Risk assessment
            risk_warnings = []
            for f, exp in exposures.items():
                if exp is not None:
                    if abs(exp) > 1.5:
                        risk_warnings.append(
                            f"High {f} exposure ({exp:+.2f}): concentrated factor bet"
                        )
                    elif abs(exp) > 1.0:
                        risk_warnings.append(
                            f"Moderate {f} exposure ({exp:+.2f}): above average tilt"
                        )

            # Portfolio concentration
            weights_arr = np.array(list(norm_weights.values()))
            hhi = float(np.sum(weights_arr ** 2))

            return success_response(
                {
                    "factor_exposures": exposures,
                    "risk_warnings": risk_warnings,
                    "portfolio_hhi": round(hhi, 4),
                    "n_holdings": len(portfolio_weights),
                    "total_weight_input": round(total_weight, 4),
                    "factors_analyzed": factors,
                },
                source="Factor Engine",
            )

        except Exception as e:
            logger.exception("factor_exposure failed")
            return error_response(str(e))

    # ------------------------------------------------------------------ #
    # 5. factor_timing
    # ------------------------------------------------------------------ #

    def factor_timing(
        self,
        stocks_data: Dict[str, List[Dict]],
        factor_name: str,
        lookback: int = 36,
    ) -> Dict[str, Any]:
        """Detect whether a factor is 'working' recently (factor timing / regime).

        For each month in lookback, compute factor return (top quintile - bottom quintile).
        Assess recent momentum of factor returns.

        Args:
            stocks_data: {ticker: [{date, open, high, low, close, volume}, ...]}
            factor_name: one of momentum, reversal, low_vol
            lookback: number of months to analyze (default 36)

        Returns:
            factor_returns_history, current_momentum, recommendation
        """
        try:
            stock_dfs = self._build_stock_dfs(stocks_data)
            if len(stock_dfs) < 5:
                return error_response("Need at least 5 stocks")

            # Build monthly close panel
            close_dict = {t: df["close"] for t, df in stock_dfs.items()}
            panel = pd.DataFrame(close_dict).dropna(axis=0, how="all").ffill()
            monthly = panel.resample("ME").last()
            monthly_ret = monthly.pct_change().dropna(how="all")

            if len(monthly_ret) < 6:
                return error_response("Not enough monthly data")

            # Limit to lookback
            monthly_ret = monthly_ret.iloc[-min(lookback, len(monthly_ret)):]

            tickers = list(stock_dfs.keys())
            factor_returns = []

            for i in range(len(monthly_ret) - 1):
                date = monthly_ret.index[i]
                fwd = monthly_ret.iloc[i + 1]

                # Compute factor scores at this date
                scores = {}
                for t in tickers:
                    if t not in stock_dfs:
                        continue
                    df = stock_dfs[t]
                    subset = df[df.index <= date]
                    if factor_name == "momentum":
                        val = self._calc_momentum(subset)
                    elif factor_name == "reversal":
                        val = self._calc_reversal(subset)
                    elif factor_name == "low_vol":
                        val = self._calc_low_vol(subset)
                    else:
                        val = self._calc_momentum(subset)
                    if val is not None:
                        scores[t] = val

                if len(scores) < 5:
                    continue

                s = pd.Series(scores)
                f = fwd.reindex(s.index).dropna()
                s = s.reindex(f.index).dropna()
                f = f.reindex(s.index)

                if len(s) < 5:
                    continue

                try:
                    q = pd.qcut(s, 5, labels=False, duplicates="drop")
                except ValueError:
                    continue

                top = f[q == q.max()].mean()
                bot = f[q == q.min()].mean()

                if not math.isnan(top) and not math.isnan(bot):
                    factor_returns.append({
                        "date": str(date.date()),
                        "factor_return": round(float(top - bot), 6),
                        "long_return": round(float(top), 6),
                        "short_return": round(float(bot), 6),
                    })

            if not factor_returns:
                return error_response("Could not compute factor returns")

            fr_series = pd.Series([r["factor_return"] for r in factor_returns])

            # Current momentum: last 6 months avg vs full avg
            recent = fr_series.iloc[-min(6, len(fr_series)):].mean()
            full = fr_series.mean()
            momentum_ratio = float(recent / full) if full != 0 else 0.0

            # Cumulative factor return
            cum_ret = float(np.prod([1 + r for r in fr_series]) - 1)

            # Win rate
            win_rate = float((fr_series > 0).mean())

            # Recommendation
            if recent > 0 and momentum_ratio > 1.2:
                recommendation = "STRONG: Factor is working well and accelerating"
            elif recent > 0:
                recommendation = "POSITIVE: Factor is generating positive returns"
            elif momentum_ratio < 0.5 and full > 0:
                recommendation = "FADING: Factor was working but is losing efficacy"
            elif recent < 0:
                recommendation = "AVOID: Factor is currently underperforming"
            else:
                recommendation = "NEUTRAL: No clear signal"

            return success_response(
                {
                    "factor": factor_name,
                    "n_periods": len(factor_returns),
                    "factor_returns_history": factor_returns,
                    "cumulative_return": round(cum_ret, 4),
                    "mean_monthly_return": round(float(fr_series.mean()), 6),
                    "win_rate": round(win_rate, 4),
                    "recent_6m_avg": round(float(recent), 6),
                    "full_period_avg": round(float(full), 6),
                    "current_momentum": round(momentum_ratio, 4),
                    "recommendation": recommendation,
                },
                source="Factor Engine",
            )

        except Exception as e:
            logger.exception("factor_timing failed")
            return error_response(str(e))

    # ------------------------------------------------------------------ #
    # 6. factor_custom
    # ------------------------------------------------------------------ #

    def factor_custom(
        self,
        stocks_data: Dict[str, List[Dict]],
        custom_formula: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build and validate a custom factor.

        custom_formula examples:
          {"type": "ratio", "numerator": "close_12m_ago", "denominator": "close"}
          {"type": "rank", "field": "volume_20d_avg", "ascending": False}
          {"type": "return", "period": 60}  (60-day return)
          {"type": "volatility", "period": 20}  (20-day vol)

        Args:
            stocks_data: {ticker: [{date, open, high, low, close, volume}, ...]}
            custom_formula: dict describing computation

        Returns:
            factor_scores, IC, t_stat, significant
        """
        try:
            stock_dfs = self._build_stock_dfs(stocks_data)
            if len(stock_dfs) < 5:
                return error_response("Need at least 5 stocks")

            formula_type = custom_formula.get("type", "return")
            raw_scores = {}

            for ticker, df in stock_dfs.items():
                try:
                    if formula_type == "ratio":
                        num_field = custom_formula.get("numerator", "close")
                        den_field = custom_formula.get("denominator", "close")
                        num_val = self._resolve_field(df, num_field)
                        den_val = self._resolve_field(df, den_field)
                        if num_val is not None and den_val is not None and den_val != 0:
                            raw_scores[ticker] = num_val / den_val

                    elif formula_type == "rank":
                        field = custom_formula.get("field", "volume_20d_avg")
                        val = self._resolve_field(df, field)
                        if val is not None:
                            ascending = custom_formula.get("ascending", True)
                            raw_scores[ticker] = val if ascending else -val

                    elif formula_type == "return":
                        period = int(custom_formula.get("period", 20))
                        if len(df) > period:
                            ret = df["close"].iloc[-1] / df["close"].iloc[-period - 1] - 1.0
                            raw_scores[ticker] = float(ret)

                    elif formula_type == "volatility":
                        period = int(custom_formula.get("period", 20))
                        returns = df["close"].pct_change().dropna()
                        if len(returns) >= period:
                            vol = returns.iloc[-period:].std()
                            invert = custom_formula.get("invert", False)
                            raw_scores[ticker] = -float(vol) if invert else float(vol)

                    elif formula_type == "mean_reversion":
                        period = int(custom_formula.get("period", 20))
                        if len(df) >= period:
                            ma = df["close"].iloc[-period:].mean()
                            current = df["close"].iloc[-1]
                            raw_scores[ticker] = float((ma - current) / current)

                    else:
                        return error_response(
                            f"Unknown formula type: {formula_type}. "
                            f"Supported: ratio, rank, return, volatility, mean_reversion"
                        )

                except Exception as e:
                    logger.warning("Custom factor failed for %s: %s", ticker, e)

            if len(raw_scores) < 5:
                return error_response(f"Only {len(raw_scores)} stocks computed, need >= 5")

            # Z-score
            scores_series = pd.Series(raw_scores)
            z = self._zscore(scores_series)

            # Compute IC using forward 1-month return
            close_dict = {t: df["close"] for t, df in stock_dfs.items()}
            panel = pd.DataFrame(close_dict).dropna(axis=0, how="all").ffill()
            monthly = panel.resample("ME").last()
            monthly_ret = monthly.pct_change().dropna(how="all")

            ic_list = []
            if len(monthly_ret) >= 2:
                # Use last available forward return
                fwd_ret = monthly_ret.iloc[-1]
                aligned_scores = scores_series.reindex(fwd_ret.dropna().index).dropna()
                aligned_fwd = fwd_ret.reindex(aligned_scores.index).dropna()
                aligned_scores = aligned_scores.reindex(aligned_fwd.index)

                if len(aligned_scores) >= 5:
                    ic = self._spearman_ic(aligned_scores, aligned_fwd)
                    if not math.isnan(ic):
                        ic_list.append(ic)

                # Compute IC over multiple periods for t-stat
                for i in range(max(0, len(monthly_ret) - 12), len(monthly_ret) - 1):
                    fwd = monthly_ret.iloc[i + 1]
                    sc = scores_series.reindex(fwd.dropna().index).dropna()
                    fw = fwd.reindex(sc.index).dropna()
                    sc = sc.reindex(fw.index)
                    if len(sc) >= 5:
                        ic_val = self._spearman_ic(sc, fw)
                        if not math.isnan(ic_val):
                            ic_list.append(ic_val)

            ic_mean = float(np.mean(ic_list)) if ic_list else 0.0
            ic_std = float(np.std(ic_list, ddof=1)) if len(ic_list) > 1 else 0.0
            t_stat = (
                float(ic_mean / (ic_std / math.sqrt(len(ic_list))))
                if ic_std > 0 and len(ic_list) > 1
                else 0.0
            )

            factor_scores_dict = {
                t: round(float(z.get(t, 0.0)), 4) for t in z.index
            }

            # Rank
            sorted_t = sorted(factor_scores_dict, key=factor_scores_dict.get, reverse=True)
            ranked = {t: {"z_score": factor_scores_dict[t], "rank": i + 1} for i, t in enumerate(sorted_t)}

            return success_response(
                {
                    "formula": custom_formula,
                    "factor_scores": ranked,
                    "n_stocks": len(ranked),
                    "IC": round(ic_mean, 4),
                    "IC_std": round(ic_std, 4),
                    "t_stat": round(t_stat, 4),
                    "significant": abs(t_stat) > 1.96,
                    "n_ic_observations": len(ic_list),
                },
                source="Factor Engine",
            )

        except Exception as e:
            logger.exception("factor_custom failed")
            return error_response(str(e))

    # ------------------------------------------------------------------ #
    # field resolver for custom factors
    # ------------------------------------------------------------------ #

    @staticmethod
    def _resolve_field(df: pd.DataFrame, field: str) -> Optional[float]:
        """Resolve a field name to a value from the DataFrame.

        Supports:
          close, open, high, low, volume (latest value)
          close_Nm_ago (N months ago close)
          volume_Nd_avg (N-day average volume)
          return_Nd (N-day return)
        """
        if field in ("close", "open", "high", "low", "volume"):
            return float(df[field].iloc[-1])

        # close_12m_ago
        if field.startswith("close_") and field.endswith("m_ago"):
            try:
                months = int(field.split("_")[1].replace("m", ""))
                days = months * 21
                if len(df) > days:
                    return float(df["close"].iloc[-days])
            except (ValueError, IndexError):
                pass
            return None

        # volume_20d_avg
        if field.startswith("volume_") and field.endswith("d_avg"):
            try:
                days = int(field.split("_")[1].replace("d", ""))
                if len(df) >= days:
                    return float(df["volume"].iloc[-days:].mean())
            except (ValueError, IndexError):
                pass
            return None

        # return_60d
        if field.startswith("return_") and field.endswith("d"):
            try:
                days = int(field.replace("return_", "").replace("d", ""))
                if len(df) > days:
                    return float(df["close"].iloc[-1] / df["close"].iloc[-days - 1] - 1.0)
            except (ValueError, IndexError):
                pass
            return None

        return None
