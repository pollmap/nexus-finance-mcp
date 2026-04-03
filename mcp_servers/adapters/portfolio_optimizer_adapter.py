"""
Portfolio Optimizer Adapter - 포트폴리오 최적화 엔진.

Markowitz mean-variance optimization, Risk Parity, Kelly Criterion,
correlation analysis, stress testing, and rebalancing checks.

Methods:
- optimize: Markowitz 평균-분산 최적화 (max_sharpe, min_variance, target_return, equal_weight)
- risk_parity: 리스크 패리티 (동일 위험 기여)
- kelly: 켈리 기준 최적 베팅 비율
- correlation_matrix: 상관행렬 + 분산비율 + 레짐 감지
- stress_test: 스트레스 테스트 (2008, 2020, 2022 시나리오)
- rebalance_check: 리밸런싱 필요 여부 + 비용 분석

Run standalone test: python -m mcp_servers.adapters.portfolio_optimizer_adapter
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import minimize

logger = logging.getLogger(__name__)

# ── Historical stress scenarios (actual approximate drawdowns) ────────
STRESS_SCENARIOS = {
    "2008_crisis": {
        "KOSPI": -0.40, "SPX": -0.37, "gold": +0.05, "BTC": 0.0,
        "bonds": +0.10, "USD_KRW": +0.30,
    },
    "2020_covid": {
        "KOSPI": -0.35, "SPX": -0.34, "gold": -0.05, "BTC": -0.50,
        "bonds": +0.08, "USD_KRW": +0.08,
    },
    "2022_rate_hike": {
        "KOSPI": -0.25, "SPX": -0.19, "gold": -0.01, "BTC": -0.65,
        "bonds": -0.15, "USD_KRW": +0.15,
    },
}


class PortfolioOptimizerAdapter:
    """Portfolio optimization engine with Markowitz, Risk Parity, Kelly, and Stress Testing."""

    # ──────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_returns(assets_returns: Dict[str, List[dict]]) -> Tuple[np.ndarray, List[str]]:
        """Parse assets_returns dict into aligned numpy returns matrix.

        Args:
            assets_returns: {ticker: [{"date": str, "value": float}, ...]}

        Returns:
            (returns_matrix [T x N], tickers list)
        """
        tickers = sorted(assets_returns.keys())
        if len(tickers) < 2:
            raise ValueError("최소 2개 이상의 자산이 필요합니다 (Need at least 2 assets)")
        if len(tickers) > 30:
            raise ValueError("최대 30개 자산까지 지원합니다 (Max 30 assets)")

        # Build per-ticker date→value maps
        series = {}
        all_dates = set()
        for tk in tickers:
            entries = assets_returns[tk]
            mapping = {}
            for e in entries:
                mapping[e["date"]] = float(e["value"])
            series[tk] = mapping
            all_dates.update(mapping.keys())

        # Align on common dates, sorted
        common_dates = sorted(all_dates)
        # Keep only dates present in ALL tickers
        for tk in tickers:
            common_dates = [d for d in common_dates if d in series[tk]]

        if len(common_dates) < 20:
            raise ValueError(
                f"공통 날짜가 {len(common_dates)}개뿐입니다. 최소 20개 필요 "
                f"(Only {len(common_dates)} common dates, need >= 20)"
            )

        matrix = np.array(
            [[series[tk][d] for tk in tickers] for d in common_dates],
            dtype=np.float64,
        )

        # Replace any NaN/Inf with 0
        matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
        return matrix, tickers

    @staticmethod
    def _annualized_stats(returns_matrix: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Compute annualized expected returns and covariance from daily returns.

        Returns:
            (mu [N], cov [N x N])  — both annualized (252 trading days).
        """
        mu = returns_matrix.mean(axis=0) * 252
        cov = np.cov(returns_matrix.T) * 252
        # Ensure cov is 2-D even for 2 assets
        if cov.ndim == 0:
            cov = np.array([[cov]])
        return mu, cov

    @staticmethod
    def _portfolio_performance(
        weights: np.ndarray, mu: np.ndarray, cov: np.ndarray
    ) -> Tuple[float, float]:
        """Return (annualized return, annualized volatility)."""
        port_ret = float(np.dot(weights, mu))
        port_vol = float(np.sqrt(np.dot(weights.T, np.dot(cov, weights))))
        return port_ret, port_vol

    # ──────────────────────────────────────────────────────────────────
    # 1. optimize — Markowitz mean-variance
    # ──────────────────────────────────────────────────────────────────

    def optimize(
        self,
        assets_returns: Dict[str, List[dict]],
        method: str = "max_sharpe",
        risk_free_rate: float = 0.035,
        target_return: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Markowitz 평균-분산 포트폴리오 최적화.

        Args:
            assets_returns: {ticker: [{"date": ..., "value": ...}, ...]} 일일 수익률
            method: "max_sharpe" | "min_variance" | "target_return" | "equal_weight"
            risk_free_rate: 무위험이자율 (연, 기본 3.5%)
            target_return: method="target_return" 시 목표 수익률 (연)

        Returns:
            optimal_weights, expected_return, expected_volatility, sharpe_ratio,
            efficient_frontier_points (10 points)
        """
        returns_matrix, tickers = self._parse_returns(assets_returns)
        mu, cov = self._annualized_stats(returns_matrix)
        n = len(tickers)
        rf = risk_free_rate

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        bounds = [(0.0, 0.4)] * n
        x0 = np.array([1.0 / n] * n)

        if method == "equal_weight":
            weights = x0.copy()
        elif method == "max_sharpe":
            def neg_sharpe(w):
                ret = np.dot(w, mu)
                vol = np.sqrt(np.dot(w.T, np.dot(cov, w)))
                return -(ret - rf) / max(vol, 1e-12)

            res = minimize(
                neg_sharpe, x0, method="SLSQP",
                bounds=bounds, constraints=constraints,
                options={"maxiter": 1000, "ftol": 1e-12},
            )
            if not res.success:
                logger.warning("max_sharpe optimizer did not converge: %s", res.message)
            weights = res.x

        elif method == "min_variance":
            def portfolio_var(w):
                return np.dot(w.T, np.dot(cov, w))

            res = minimize(
                portfolio_var, x0, method="SLSQP",
                bounds=bounds, constraints=constraints,
                options={"maxiter": 1000, "ftol": 1e-12},
            )
            if not res.success:
                logger.warning("min_variance optimizer did not converge: %s", res.message)
            weights = res.x

        elif method == "target_return":
            if target_return is None:
                raise ValueError("method='target_return'에는 target_return이 필요합니다")

            def portfolio_var(w):
                return np.dot(w.T, np.dot(cov, w))

            cons = [
                {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
                {"type": "eq", "fun": lambda w: np.dot(w, mu) - target_return},
            ]
            res = minimize(
                portfolio_var, x0, method="SLSQP",
                bounds=bounds, constraints=cons,
                options={"maxiter": 1000, "ftol": 1e-12},
            )
            if not res.success:
                logger.warning("target_return optimizer did not converge: %s", res.message)
            weights = res.x

        else:
            raise ValueError(f"Unknown method: {method}")

        # Clip tiny negatives from numerical noise
        weights = np.maximum(weights, 0.0)
        weights /= weights.sum()

        port_ret, port_vol = self._portfolio_performance(weights, mu, cov)
        sharpe = (port_ret - rf) / max(port_vol, 1e-12)

        # ── Efficient frontier (10 points) ────────────────────────────
        min_ret = float(mu.min())
        max_ret = float(mu.max())
        target_rets = np.linspace(min_ret, max_ret, 10)
        frontier = []
        for tr in target_rets:
            def pvar(w):
                return np.dot(w.T, np.dot(cov, w))

            cons_ef = [
                {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
                {"type": "eq", "fun": lambda w, _tr=tr: np.dot(w, mu) - _tr},
            ]
            res_ef = minimize(
                pvar, x0, method="SLSQP",
                bounds=bounds, constraints=cons_ef,
                options={"maxiter": 500, "ftol": 1e-10},
            )
            if res_ef.success:
                ef_vol = float(np.sqrt(res_ef.fun))
                frontier.append({"return": round(float(tr), 6), "volatility": round(ef_vol, 6)})

        weight_dict = {tickers[i]: round(float(weights[i]), 6) for i in range(n)}

        logger.info(
            "optimize(%s): method=%s, sharpe=%.3f, return=%.3f, vol=%.3f",
            list(tickers), method, sharpe, port_ret, port_vol,
        )

        return {
            "success": True,
            "data": {
                "method": method,
                "optimal_weights": weight_dict,
                "expected_return": round(port_ret, 6),
                "expected_volatility": round(port_vol, 6),
                "sharpe_ratio": round(sharpe, 4),
                "risk_free_rate": rf,
                "efficient_frontier_points": frontier,
                "n_assets": n,
                "n_observations": returns_matrix.shape[0],
            },
        }

    # ──────────────────────────────────────────────────────────────────
    # 2. risk_parity
    # ──────────────────────────────────────────────────────────────────

    def risk_parity(self, assets_returns: Dict[str, List[dict]]) -> Dict[str, Any]:
        """리스크 패리티 — 각 자산의 위험 기여도가 동일한 포트폴리오.

        Args:
            assets_returns: {ticker: [{"date": ..., "value": ...}, ...]}

        Returns:
            weights, risk_contributions (should be equal), total_risk
        """
        returns_matrix, tickers = self._parse_returns(assets_returns)
        _, cov = self._annualized_stats(returns_matrix)
        n = len(tickers)

        def risk_budget_objective(w):
            """Minimize sum of squared differences in risk contributions."""
            w = np.maximum(w, 1e-10)
            port_vol = np.sqrt(np.dot(w.T, np.dot(cov, w)))
            marginal_risk = np.dot(cov, w)
            risk_contrib = w * marginal_risk / max(port_vol, 1e-12)
            target_contrib = port_vol / n
            return np.sum((risk_contrib - target_contrib) ** 2)

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        bounds = [(0.01, 0.4)] * n  # min 1% to avoid zero-weight degeneracy
        x0 = np.array([1.0 / n] * n)

        res = minimize(
            risk_budget_objective, x0, method="SLSQP",
            bounds=bounds, constraints=constraints,
            options={"maxiter": 1000, "ftol": 1e-14},
        )

        if not res.success:
            logger.warning("risk_parity optimizer did not converge: %s", res.message)

        weights = np.maximum(res.x, 0.0)
        weights /= weights.sum()

        # Compute actual risk contributions
        port_vol = float(np.sqrt(np.dot(weights.T, np.dot(cov, weights))))
        marginal = np.dot(cov, weights)
        risk_contribs = weights * marginal / max(port_vol, 1e-12)

        weight_dict = {tickers[i]: round(float(weights[i]), 6) for i in range(n)}
        rc_dict = {tickers[i]: round(float(risk_contribs[i]), 6) for i in range(n)}

        logger.info("risk_parity(%s): total_risk=%.4f", list(tickers), port_vol)

        return {
            "success": True,
            "data": {
                "weights": weight_dict,
                "risk_contributions": rc_dict,
                "total_risk": round(port_vol, 6),
                "n_assets": n,
                "n_observations": returns_matrix.shape[0],
                "max_contribution_diff": round(
                    float(np.max(risk_contribs) - np.min(risk_contribs)), 6
                ),
            },
        }

    # ──────────────────────────────────────────────────────────────────
    # 3. kelly
    # ──────────────────────────────────────────────────────────────────

    def kelly(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fraction: float = 0.5,
    ) -> Dict[str, Any]:
        """켈리 기준 (Kelly Criterion) — 최적 베팅/포지션 비율.

        Args:
            win_rate: 승률 (0~1)
            avg_win: 평균 수익 (예: 0.05 = 5%)
            avg_loss: 평균 손실 (양수, 예: 0.03 = 3%)
            fraction: 켈리 비율 (0.5 = 하프 켈리, 안전 운용)

        Returns:
            full_kelly_pct, recommended_pct, expected_growth_rate
        """
        if not 0 < win_rate < 1:
            raise ValueError(f"win_rate must be between 0 and 1, got {win_rate}")
        if avg_win <= 0:
            raise ValueError(f"avg_win must be positive, got {avg_win}")
        if avg_loss <= 0:
            raise ValueError(f"avg_loss must be positive, got {avg_loss}")
        if not 0 < fraction <= 1:
            raise ValueError(f"fraction must be between 0 and 1, got {fraction}")

        p = win_rate
        q = 1.0 - p
        b = avg_win / avg_loss  # win/loss ratio

        # Kelly formula: f* = (p * b - q) / b
        full_kelly = (p * b - q) / b
        recommended = full_kelly * fraction

        # Expected geometric growth rate: g = p * ln(1 + f*b) + q * ln(1 - f)
        # Use recommended (fractional Kelly) for growth rate
        if recommended > 0 and recommended < 1:
            growth = p * np.log(1 + recommended * avg_win) + q * np.log(
                1 - recommended * avg_loss
            )
        else:
            growth = 0.0

        # Edge = expected value per unit bet
        edge = p * avg_win - q * avg_loss

        logger.info(
            "kelly: win_rate=%.2f, avg_win=%.3f, avg_loss=%.3f, full=%.3f, rec=%.3f",
            win_rate, avg_win, avg_loss, full_kelly, recommended,
        )

        return {
            "success": True,
            "data": {
                "full_kelly_pct": round(full_kelly * 100, 2),
                "recommended_pct": round(recommended * 100, 2),
                "fraction_used": fraction,
                "expected_growth_rate": round(float(growth), 6),
                "edge_per_trade": round(edge, 6),
                "win_loss_ratio": round(b, 4),
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "note": (
                    "베팅 금지 (음수 기대값)"
                    if full_kelly <= 0
                    else "하프 켈리 권장 (변동성 감소)"
                    if fraction < 1
                    else "풀 켈리 (공격적)"
                ),
            },
        }

    # ──────────────────────────────────────────────────────────────────
    # 4. correlation_matrix
    # ──────────────────────────────────────────────────────────────────

    def correlation_matrix(
        self,
        assets_returns: Dict[str, List[dict]],
        window: int = 60,
    ) -> Dict[str, Any]:
        """상관행렬 분석 — 현재/롤링 상관계수 + 분산비율 + 레짐 감지.

        Args:
            assets_returns: {ticker: [{"date": ..., "value": ...}, ...]}
            window: 롤링 윈도우 크기 (기본 60 거래일)

        Returns:
            current_matrix, rolling_avg_matrix, diversification_ratio,
            max_correlation_pair
        """
        returns_matrix, tickers = self._parse_returns(assets_returns)
        n = len(tickers)
        T = returns_matrix.shape[0]

        # Current full-sample correlation
        current_corr = np.corrcoef(returns_matrix.T)
        current_corr = np.nan_to_num(current_corr, nan=0.0)

        # Rolling average correlation
        if T >= window:
            rolling_corrs = []
            for start in range(T - window + 1):
                chunk = returns_matrix[start : start + window]
                rc = np.corrcoef(chunk.T)
                rc = np.nan_to_num(rc, nan=0.0)
                rolling_corrs.append(rc)
            rolling_avg = np.mean(rolling_corrs, axis=0)

            # Recent vs historical — regime detection
            recent_corr = rolling_corrs[-1]
            historical_avg = np.mean(rolling_corrs[: len(rolling_corrs) // 2], axis=0)
            regime_shift = float(np.mean(np.abs(recent_corr - historical_avg)))
        else:
            rolling_avg = current_corr.copy()
            regime_shift = 0.0

        # Find max correlation pair (off-diagonal)
        max_corr = -2.0
        max_pair = ("", "")
        min_corr = 2.0
        min_pair = ("", "")
        for i in range(n):
            for j in range(i + 1, n):
                c = current_corr[i, j]
                if c > max_corr:
                    max_corr = c
                    max_pair = (tickers[i], tickers[j])
                if c < min_corr:
                    min_corr = c
                    min_pair = (tickers[i], tickers[j])

        # Diversification ratio (equal-weight as reference)
        vols = np.std(returns_matrix, axis=0) * np.sqrt(252)
        ew = np.array([1.0 / n] * n)
        weighted_vol_sum = float(np.dot(ew, vols))
        port_vol = float(np.sqrt(np.dot(ew.T, np.dot(np.cov(returns_matrix.T) * 252, ew))))
        div_ratio = weighted_vol_sum / max(port_vol, 1e-12)

        def _matrix_to_dict(mat):
            return {
                tickers[i]: {tickers[j]: round(float(mat[i, j]), 4) for j in range(n)}
                for i in range(n)
            }

        logger.info(
            "correlation_matrix(%s): max_pair=%s (%.3f), div_ratio=%.3f",
            list(tickers), max_pair, max_corr, div_ratio,
        )

        return {
            "success": True,
            "data": {
                "current_matrix": _matrix_to_dict(current_corr),
                "rolling_avg_matrix": _matrix_to_dict(rolling_avg),
                "diversification_ratio": round(div_ratio, 4),
                "max_correlation_pair": {
                    "assets": list(max_pair),
                    "correlation": round(float(max_corr), 4),
                },
                "min_correlation_pair": {
                    "assets": list(min_pair),
                    "correlation": round(float(min_corr), 4),
                },
                "regime_shift_magnitude": round(regime_shift, 4),
                "window": window,
                "n_observations": T,
            },
        }

    # ──────────────────────────────────────────────────────────────────
    # 5. stress_test
    # ──────────────────────────────────────────────────────────────────

    def stress_test(
        self,
        portfolio_weights: Dict[str, float],
        assets_returns: Optional[Dict[str, List[dict]]] = None,
        scenario: str = "2008_crisis",
        custom_shocks: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """스트레스 테스트 — 역사적/커스텀 시나리오 충격 시뮬레이션.

        Args:
            portfolio_weights: {ticker: weight} 현재 포트폴리오 비중
            assets_returns: (optional) 히스토리컬 VaR 계산용
            scenario: "2008_crisis" | "2020_covid" | "2022_rate_hike" | "custom"
            custom_shocks: scenario="custom" 시 {ticker: shock_pct} (예: {"KOSPI": -0.30})

        Returns:
            portfolio_impact_pct, per_asset_impact, worst_asset, best_hedge
        """
        if scenario == "custom":
            if not custom_shocks:
                raise ValueError("scenario='custom'에는 custom_shocks가 필요합니다")
            shocks = custom_shocks
        elif scenario in STRESS_SCENARIOS:
            shocks = STRESS_SCENARIOS[scenario]
        else:
            raise ValueError(
                f"Unknown scenario: {scenario}. "
                f"Available: {list(STRESS_SCENARIOS.keys())} or 'custom'"
            )

        # Normalize weights
        total_w = sum(portfolio_weights.values())
        weights = {k: v / total_w for k, v in portfolio_weights.items()}

        per_asset = {}
        portfolio_impact = 0.0
        worst_asset = None
        worst_impact = 0.0
        best_hedge = None
        best_impact = float("-inf")

        for asset, weight in weights.items():
            shock = shocks.get(asset, 0.0)
            impact = weight * shock
            per_asset[asset] = {
                "weight": round(weight, 4),
                "shock_pct": round(shock * 100, 2),
                "impact_pct": round(impact * 100, 2),
            }
            portfolio_impact += impact

            if impact < worst_impact:
                worst_impact = impact
                worst_asset = asset
            if shock > 0 and impact > best_impact:
                best_impact = impact
                best_hedge = asset

        # Historical VaR if data provided
        historical_var = None
        if assets_returns:
            try:
                returns_matrix, tickers = self._parse_returns(assets_returns)
                w_vec = np.array([weights.get(tk, 0.0) for tk in tickers])
                w_vec /= max(w_vec.sum(), 1e-12)
                port_returns = returns_matrix @ w_vec
                historical_var = {
                    "VaR_95": round(float(np.percentile(port_returns, 5)), 6),
                    "VaR_99": round(float(np.percentile(port_returns, 1)), 6),
                    "CVaR_95": round(
                        float(port_returns[port_returns <= np.percentile(port_returns, 5)].mean()),
                        6,
                    ),
                }
            except Exception as e:
                logger.warning("Historical VaR calculation failed: %s", e)

        logger.info(
            "stress_test(%s): scenario=%s, impact=%.2f%%",
            list(weights.keys()), scenario, portfolio_impact * 100,
        )

        return {
            "success": True,
            "data": {
                "scenario": scenario,
                "portfolio_impact_pct": round(portfolio_impact * 100, 2),
                "per_asset_impact": per_asset,
                "worst_asset": worst_asset,
                "best_hedge": best_hedge,
                "historical_var": historical_var,
            },
        }

    # ──────────────────────────────────────────────────────────────────
    # 6. rebalance_check
    # ──────────────────────────────────────────────────────────────────

    def rebalance_check(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        threshold: float = 0.05,
        transaction_cost: float = 0.003,
    ) -> Dict[str, Any]:
        """리밸런싱 필요 여부 확인 + 거래비용 vs 최적화 이익 비교.

        Args:
            current_weights: {ticker: current_weight} 현재 비중
            target_weights: {ticker: target_weight} 목표 비중
            threshold: 드리프트 허용 한도 (기본 5%p)
            transaction_cost: 편도 거래비용 (기본 0.3%)

        Returns:
            rebalance_needed, drifted_assets, trades_required, estimated_cost, net_benefit
        """
        all_assets = sorted(set(list(current_weights.keys()) + list(target_weights.keys())))

        drifted = {}
        trades = {}
        total_turnover = 0.0

        for asset in all_assets:
            curr = current_weights.get(asset, 0.0)
            tgt = target_weights.get(asset, 0.0)
            diff = tgt - curr

            if abs(diff) > threshold:
                drifted[asset] = {
                    "current": round(curr, 4),
                    "target": round(tgt, 4),
                    "drift": round(abs(diff), 4),
                }

            if abs(diff) > 1e-6:
                trades[asset] = {
                    "direction": "BUY" if diff > 0 else "SELL",
                    "amount_pct": round(abs(diff) * 100, 2),
                }
                total_turnover += abs(diff)

        # Cost = turnover * transaction_cost (buy + sell counted once each)
        estimated_cost = total_turnover * transaction_cost

        # Benefit estimate: tracking error reduction
        # Simple heuristic: sum of squared drifts (tracking variance proxy)
        drift_var = sum(
            (current_weights.get(a, 0.0) - target_weights.get(a, 0.0)) ** 2
            for a in all_assets
        )
        # Annualized tracking benefit (rough heuristic)
        benefit_proxy = np.sqrt(drift_var) * 0.5  # ~ half-year drag from misallocation

        rebalance_needed = len(drifted) > 0
        net_benefit = benefit_proxy - estimated_cost

        logger.info(
            "rebalance_check: drifted=%d assets, turnover=%.2f%%, cost=%.4f, net=%.4f",
            len(drifted), total_turnover * 100, estimated_cost, net_benefit,
        )

        return {
            "success": True,
            "data": {
                "rebalance_needed": rebalance_needed,
                "drifted_assets": drifted,
                "trades_required": trades,
                "total_turnover_pct": round(total_turnover * 100, 2),
                "estimated_cost_pct": round(estimated_cost * 100, 4),
                "benefit_proxy_pct": round(benefit_proxy * 100, 4),
                "net_benefit_pct": round(net_benefit * 100, 4),
                "threshold": threshold,
                "transaction_cost": transaction_cost,
                "recommendation": (
                    "리밸런싱 권장 (드리프트 초과 + 순이익 양수)"
                    if rebalance_needed and net_benefit > 0
                    else "리밸런싱 보류 (비용 > 이익)"
                    if rebalance_needed and net_benefit <= 0
                    else "리밸런싱 불필요 (허용 범위 내)"
                ),
            },
        }


# ── Standalone test ───────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)
    adapter = PortfolioOptimizerAdapter()

    # Generate synthetic daily returns for testing
    np.random.seed(42)
    dates = [f"2025-{m:02d}-{d:02d}" for m in range(1, 7) for d in range(1, 21)]
    sample = {
        "AAPL": [{"date": d, "value": float(r)} for d, r in zip(dates, np.random.normal(0.0005, 0.015, len(dates)))],
        "MSFT": [{"date": d, "value": float(r)} for d, r in zip(dates, np.random.normal(0.0004, 0.014, len(dates)))],
        "GOOGL": [{"date": d, "value": float(r)} for d, r in zip(dates, np.random.normal(0.0006, 0.016, len(dates)))],
        "BONDS": [{"date": d, "value": float(r)} for d, r in zip(dates, np.random.normal(0.0001, 0.003, len(dates)))],
    }

    print("=== optimize (max_sharpe) ===")
    print(json.dumps(adapter.optimize(sample, method="max_sharpe"), indent=2, ensure_ascii=False))

    print("\n=== risk_parity ===")
    print(json.dumps(adapter.risk_parity(sample), indent=2, ensure_ascii=False))

    print("\n=== kelly ===")
    print(json.dumps(adapter.kelly(0.55, 0.08, 0.05, fraction=0.5), indent=2, ensure_ascii=False))

    print("\n=== correlation_matrix ===")
    print(json.dumps(adapter.correlation_matrix(sample, window=30), indent=2, ensure_ascii=False))

    print("\n=== stress_test ===")
    weights = {"KOSPI": 0.3, "SPX": 0.3, "gold": 0.1, "bonds": 0.2, "BTC": 0.1}
    print(json.dumps(adapter.stress_test(weights, scenario="2008_crisis"), indent=2, ensure_ascii=False))

    print("\n=== rebalance_check ===")
    current = {"AAPL": 0.35, "MSFT": 0.30, "GOOGL": 0.20, "BONDS": 0.15}
    target = {"AAPL": 0.25, "MSFT": 0.25, "GOOGL": 0.25, "BONDS": 0.25}
    print(json.dumps(adapter.rebalance_check(current, target), indent=2, ensure_ascii=False))
