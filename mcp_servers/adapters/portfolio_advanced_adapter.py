"""
Advanced Portfolio Construction Adapter — BL, HRP, RMT, Johansen, Info Theory.

Implements six tools beyond basic Markowitz:

1. rmt_clean: Random Matrix Theory correlation matrix denoising
2. black_litterman: Black-Litterman model with investor views
3. hrp: Hierarchical Risk Parity (López de Prado)
4. johansen: Johansen multivariate cointegration test
5. info_theory: KL divergence, transfer entropy, mutual information
6. compare: Side-by-side portfolio method comparison

References:
- Black & Litterman (1992), Financial Analysts Journal 48(5): 28-43
- López de Prado (2016), "Building Diversified Portfolios that Outperform OOS," JFE
- Laloux, Cizeau, Bouchaud & Potters (1999), PRL 83(7): 1467-1470
- Johansen (1988), J. Economic Dynamics and Control 12: 231-254
"""
import logging
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats, cluster, optimize

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=RuntimeWarning)


def _build_returns_matrix(
    series_list: List[List[Dict]], names: List[str]
) -> pd.DataFrame:
    """Convert list of [{date, value}] series into an aligned returns DataFrame."""
    all_prices = {}
    for data, name in zip(series_list, names):
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").drop_duplicates("date").set_index("date")
        all_prices[name] = df["value"].astype(float)
    prices = pd.DataFrame(all_prices).dropna()
    if len(prices) < 30:
        raise ValueError(f"Only {len(prices)} overlapping dates; need >= 30")
    returns = prices.pct_change().dropna()
    return returns


class PortfolioAdvancedAdapter:
    """Advanced portfolio construction beyond Markowitz."""

    # ------------------------------------------------------------------
    # 1. Random Matrix Theory — Correlation Cleaning
    # ------------------------------------------------------------------
    def rmt_clean(
        self, series_list: List[List[Dict]], names: List[str]
    ) -> Dict[str, Any]:
        """Clean correlation matrix using Marchenko-Pastur distribution.

        Identifies noise eigenvalues and replaces them to improve
        out-of-sample portfolio optimization.
        """
        try:
            returns = _build_returns_matrix(series_list, names)
            T, N = returns.shape
            if N < 2:
                return error_response("Need at least 2 assets")

            # Empirical correlation matrix
            corr = returns.corr().values

            # Eigendecomposition
            eigenvalues, eigenvectors = np.linalg.eigh(corr)
            # Sort descending
            idx = np.argsort(eigenvalues)[::-1]
            eigenvalues = eigenvalues[idx]
            eigenvectors = eigenvectors[:, idx]

            # Marchenko-Pastur bounds
            q = T / N  # ratio of observations to variables
            sigma2 = 1.0  # variance of standardized returns
            lambda_plus = sigma2 * (1 + np.sqrt(1 / q)) ** 2
            lambda_minus = sigma2 * (1 - np.sqrt(1 / q)) ** 2 if q > 1 else 0

            # Classify eigenvalues
            n_signal = int(np.sum(eigenvalues > lambda_plus))
            n_noise = N - n_signal

            # Clean: replace noise eigenvalues with their average
            cleaned_eigenvalues = eigenvalues.copy()
            noise_mask = eigenvalues <= lambda_plus
            if np.sum(noise_mask) > 0:
                avg_noise = np.mean(eigenvalues[noise_mask])
                cleaned_eigenvalues[noise_mask] = avg_noise

            # Reconstruct cleaned correlation matrix
            corr_cleaned = eigenvectors @ np.diag(cleaned_eigenvalues) @ eigenvectors.T
            # Normalize diagonal to 1
            d = np.sqrt(np.diag(corr_cleaned))
            corr_cleaned = corr_cleaned / np.outer(d, d)
            np.fill_diagonal(corr_cleaned, 1.0)

            # Frobenius distance between original and cleaned
            frob_dist = float(np.linalg.norm(corr - corr_cleaned, 'fro'))

            # Eigenvalue summary
            eig_summary = [
                {"index": i, "eigenvalue": round(float(v), 4),
                 "type": "signal" if v > lambda_plus else "noise",
                 "pct_variance": round(float(v / np.sum(eigenvalues) * 100), 1)}
                for i, v in enumerate(eigenvalues[:min(10, N)])
            ]

            return success_response({
                    "n_assets": N,
                    "n_observations": T,
                    "q_ratio": round(float(q), 2),
                    "mp_lambda_plus": round(float(lambda_plus), 4),
                    "mp_lambda_minus": round(float(lambda_minus), 4),
                    "n_signal_eigenvalues": n_signal,
                    "n_noise_eigenvalues": n_noise,
                    "top_eigenvalue": round(float(eigenvalues[0]), 4),
                    "frobenius_distance": round(frob_dist, 4),
                    "eigenvalue_summary": eig_summary,
                    "cleaned_correlation": {
                        names[i]: {names[j]: round(float(corr_cleaned[i, j]), 4)
                                   for j in range(N)}
                        for i in range(N)
                    },
                    "interpretation": (
                        f"{n_noise}/{N} eigenvalues are noise (below MP bound λ+={lambda_plus:.2f}). "
                        f"Top eigenvalue={eigenvalues[0]:.2f} explains "
                        f"{eigenvalues[0]/np.sum(eigenvalues)*100:.1f}% of variance (market factor). "
                        f"Cleaned matrix differs by Frobenius distance {frob_dist:.3f}."
                    ),
                })
        except Exception as e:
            logger.exception("rmt_clean failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 2. Black-Litterman Model
    # ------------------------------------------------------------------
    def black_litterman(
        self,
        series_list: List[List[Dict]],
        names: List[str],
        market_caps: Optional[List[float]] = None,
        views: Optional[List[Dict]] = None,
        tau: float = 0.05,
        risk_free_rate: float = 0.03,
        risk_aversion: float = 2.5,
    ) -> Dict[str, Any]:
        """Black-Litterman portfolio with investor views.

        Args:
            series_list: list of price series
            names: asset names
            market_caps: market capitalizations (None = equal weight prior)
            views: list of {"asset": name, "return": expected, "confidence": 0-1}
            tau: uncertainty scaling (default 0.05)
            risk_free_rate: annual risk-free rate
            risk_aversion: risk aversion coefficient (delta)
        """
        try:
            returns = _build_returns_matrix(series_list, names)
            N = len(names)
            Sigma = returns.cov().values * 252  # annualized

            # Market equilibrium weights
            if market_caps and len(market_caps) == N:
                w_mkt = np.array(market_caps) / np.sum(market_caps)
            else:
                w_mkt = np.ones(N) / N

            # Implied equilibrium returns: Pi = delta * Sigma * w_mkt
            delta = risk_aversion
            Pi = delta * Sigma @ w_mkt

            if not views or len(views) == 0:
                # No views -> return equilibrium
                opt_weights = w_mkt
                posterior_returns = Pi
            else:
                # Construct P (pick matrix), Q (view returns), Omega (view uncertainty)
                n_views = len(views)
                P = np.zeros((n_views, N))
                Q = np.zeros(n_views)
                omega_diag = np.zeros(n_views)

                for k, view in enumerate(views):
                    asset = view.get("asset", "")
                    if asset in names:
                        idx = names.index(asset)
                        P[k, idx] = 1.0
                        Q[k] = view.get("return", 0)
                        confidence = view.get("confidence", 0.5)
                        # Omega: lower confidence -> higher uncertainty
                        # omega_k = (1/confidence - 1) * tau * P_k @ Sigma @ P_k'
                        omega_diag[k] = max(1e-6, (1.0 / max(confidence, 0.01) - 1) * tau * (P[k] @ Sigma @ P[k]))

                Omega = np.diag(omega_diag)

                # BL posterior: E[R] = [(tau*Sigma)^-1 + P'*Omega^-1*P]^-1 * [(tau*Sigma)^-1*Pi + P'*Omega^-1*Q]
                tau_Sigma_inv = np.linalg.inv(tau * Sigma)
                Omega_inv = np.linalg.inv(Omega)

                M = np.linalg.inv(tau_Sigma_inv + P.T @ Omega_inv @ P)
                posterior_returns = M @ (tau_Sigma_inv @ Pi + P.T @ Omega_inv @ Q)

                # Posterior covariance
                posterior_Sigma = Sigma + M

                # Optimal weights from posterior
                opt_weights = (1 / delta) * np.linalg.inv(Sigma) @ posterior_returns
                # Normalize to sum to 1
                opt_weights = opt_weights / np.sum(opt_weights)

            # Expected portfolio metrics
            port_return = float(opt_weights @ posterior_returns)
            port_vol = float(np.sqrt(opt_weights @ Sigma @ opt_weights))
            port_sharpe = (port_return - risk_free_rate) / port_vol if port_vol > 0 else 0

            weights_dict = {names[i]: round(float(opt_weights[i]), 4) for i in range(N)}
            equilibrium_returns = {names[i]: round(float(Pi[i]), 4) for i in range(N)}
            posterior_returns_dict = {names[i]: round(float(posterior_returns[i]), 4) for i in range(N)}

            return success_response({
                    "optimal_weights": weights_dict,
                    "equilibrium_returns": equilibrium_returns,
                    "posterior_returns": posterior_returns_dict,
                    "expected_return": round(port_return, 4),
                    "expected_volatility": round(port_vol, 4),
                    "sharpe_ratio": round(port_sharpe, 3),
                    "risk_aversion": delta,
                    "tau": tau,
                    "n_views": len(views) if views else 0,
                    "n_assets": N,
                    "interpretation": (
                        f"BL portfolio with {len(views) if views else 0} views. "
                        f"Expected return: {port_return:.1%}, Vol: {port_vol:.1%}, "
                        f"Sharpe: {port_sharpe:.2f}. "
                        f"Views tilt weights vs equilibrium."
                    ),
                })
        except Exception as e:
            logger.exception("black_litterman failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 3. Hierarchical Risk Parity (HRP)
    # ------------------------------------------------------------------
    def hrp(
        self, series_list: List[List[Dict]], names: List[str]
    ) -> Dict[str, Any]:
        """Hierarchical Risk Parity — no covariance matrix inversion needed.

        López de Prado's tree-based approach:
        1. Hierarchical clustering on correlation distance
        2. Quasi-diagonalization (seriation)
        3. Recursive bisection allocation
        """
        try:
            returns = _build_returns_matrix(series_list, names)
            N = len(names)

            corr = returns.corr().values
            cov = returns.cov().values * 252  # annualized

            # Step 1: Distance matrix from correlation
            dist = np.sqrt(0.5 * (1 - corr))
            # Condensed distance matrix for scipy
            from scipy.spatial.distance import squareform
            dist_condensed = squareform(dist, checks=False)

            # Step 2: Hierarchical clustering (single linkage)
            link = cluster.hierarchy.linkage(dist_condensed, method="single")

            # Step 3: Quasi-diagonalization (get leaf order)
            sort_ix = cluster.hierarchy.leaves_list(link)

            # Step 4: Recursive bisection
            def _get_cluster_var(cov_mat, cluster_items):
                """Compute inverse-variance portfolio variance for a cluster."""
                c = cov_mat[np.ix_(cluster_items, cluster_items)]
                ivp = 1 / np.diag(c)
                ivp /= ivp.sum()
                return float(ivp @ c @ ivp)

            def _recursive_bisection(cov_mat, sorted_indices):
                """Recursively bisect and allocate weights."""
                w = np.ones(len(sorted_indices))
                items = [sorted_indices.tolist()]

                while len(items) > 0:
                    # Split each cluster into two
                    new_items = []
                    for sublist in items:
                        if len(sublist) <= 1:
                            continue
                        mid = len(sublist) // 2
                        left = sublist[:mid]
                        right = sublist[mid:]

                        # Variance of each sub-cluster
                        var_left = _get_cluster_var(cov_mat, left)
                        var_right = _get_cluster_var(cov_mat, right)

                        # Allocate inversely proportional to variance
                        alpha = 1 - var_left / (var_left + var_right)

                        for i in left:
                            w[sorted_indices.tolist().index(i)] *= alpha
                        for i in right:
                            w[sorted_indices.tolist().index(i)] *= (1 - alpha)

                        if len(left) > 1:
                            new_items.append(left)
                        if len(right) > 1:
                            new_items.append(right)
                    items = new_items

                return w

            weights = _recursive_bisection(cov, sort_ix)
            weights = weights / weights.sum()  # normalize

            # Portfolio metrics
            port_vol = float(np.sqrt(weights @ cov @ weights))
            mean_ret = returns.mean().values * 252
            port_ret = float(weights @ mean_ret)

            # Diversification ratio
            asset_vols = np.sqrt(np.diag(cov))
            div_ratio = float(weights @ asset_vols / port_vol) if port_vol > 0 else 0

            # Effective N (inverse HHI)
            hhi = float(np.sum(weights ** 2))
            eff_n = 1 / hhi if hhi > 0 else N

            weights_dict = {names[sort_ix[i]]: round(float(weights[i]), 4) for i in range(N)}

            return success_response({
                    "weights": weights_dict,
                    "expected_return": round(port_ret, 4),
                    "expected_volatility": round(port_vol, 4),
                    "sharpe_ratio": round(port_ret / port_vol, 3) if port_vol > 0 else 0,
                    "diversification_ratio": round(div_ratio, 3),
                    "effective_n": round(eff_n, 1),
                    "hhi": round(hhi, 4),
                    "n_assets": N,
                    "cluster_order": [names[i] for i in sort_ix],
                    "method": "López de Prado HRP (single linkage, recursive bisection)",
                    "interpretation": (
                        f"HRP: {N} assets, effective N={eff_n:.1f}. "
                        f"Vol={port_vol:.1%}, Div ratio={div_ratio:.2f}. "
                        f"No covariance inversion → more stable OOS than Markowitz."
                    ),
                })
        except Exception as e:
            logger.exception("hrp failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 4. Johansen Multivariate Cointegration
    # ------------------------------------------------------------------
    def johansen(
        self, series_list: List[List[Dict]], names: List[str], det_order: int = 0, k_ar_diff: int = 1,
    ) -> Dict[str, Any]:
        """Johansen cointegration test for N>2 assets.

        Tests for multiple cointegrating relationships using trace and
        max-eigenvalue statistics.
        """
        try:
            # Build price matrix
            all_prices = {}
            for data, name in zip(series_list, names):
                df = pd.DataFrame(data)
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date").drop_duplicates("date").set_index("date")
                all_prices[name] = df["value"].astype(float)
            prices = pd.DataFrame(all_prices).dropna()

            if len(prices) < 50:
                return error_response(f"Need >= 50 observations, got {len(prices)}")

            N = len(names)
            if N < 2:
                return error_response("Need at least 2 series")

            from statsmodels.tsa.vector_ar.vecm import coint_johansen
            result = coint_johansen(prices.values, det_order=det_order, k_ar_diff=k_ar_diff)

            # Trace test
            trace_stats = result.lr1  # trace statistics
            trace_cvs = result.cvt    # critical values (90%, 95%, 99%)

            # Max eigenvalue test
            max_eig_stats = result.lr2
            max_eig_cvs = result.cvm

            # Determine cointegration rank
            rank_trace = 0
            rank_maxeig = 0
            for i in range(N):
                if trace_stats[i] > trace_cvs[i, 1]:  # 95% CV
                    rank_trace = i + 1
                if max_eig_stats[i] > max_eig_cvs[i, 1]:
                    rank_maxeig = i + 1

            # Cointegrating vectors (eigenvectors)
            coint_vectors = result.evec[:, :max(rank_trace, 1)]

            results_table = []
            for i in range(N):
                results_table.append({
                    "h0": f"r <= {i}",
                    "trace_stat": round(float(trace_stats[i]), 3),
                    "trace_cv_95": round(float(trace_cvs[i, 1]), 3),
                    "trace_reject": bool(trace_stats[i] > trace_cvs[i, 1]),
                    "max_eig_stat": round(float(max_eig_stats[i]), 3),
                    "max_eig_cv_95": round(float(max_eig_cvs[i, 1]), 3),
                    "max_eig_reject": bool(max_eig_stats[i] > max_eig_cvs[i, 1]),
                })

            # Format cointegrating vectors
            vectors = []
            for j in range(min(rank_trace, 3)):
                vec = {names[i]: round(float(coint_vectors[i, j]), 4) for i in range(N)}
                vectors.append(vec)

            return success_response({
                    "rank_trace": rank_trace,
                    "rank_max_eigenvalue": rank_maxeig,
                    "n_assets": N,
                    "n_observations": len(prices),
                    "test_results": results_table,
                    "cointegrating_vectors": vectors,
                    "det_order": det_order,
                    "k_ar_diff": k_ar_diff,
                    "interpretation": (
                        f"Johansen test: {rank_trace} cointegrating relationship(s) "
                        f"at 95% (trace), {rank_maxeig} (max-eigenvalue). "
                        f"{'Multi-asset stat arb possible!' if rank_trace >= 1 else 'No cointegration found.'}"
                    ),
                })
        except Exception as e:
            logger.exception("johansen failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 5. Advanced Information Theory
    # ------------------------------------------------------------------
    def info_theory(
        self,
        series_a: List[Dict],
        series_b: List[Dict],
        n_bins: int = 20,
        te_lags: int = 1,
    ) -> Dict[str, Any]:
        """KL divergence, transfer entropy, mutual information between two series.

        Args:
            series_a, series_b: price series [{date, value}]
            n_bins: histogram bins for discretization
            te_lags: lags for transfer entropy
        """
        try:
            sa = pd.DataFrame(series_a)
            sa["date"] = pd.to_datetime(sa["date"])
            sa = sa.sort_values("date").drop_duplicates("date").set_index("date")["value"].astype(float)

            sb = pd.DataFrame(series_b)
            sb["date"] = pd.to_datetime(sb["date"])
            sb = sb.sort_values("date").drop_duplicates("date").set_index("date")["value"].astype(float)

            df = pd.concat([sa.rename("A"), sb.rename("B")], axis=1, join="inner").dropna()
            if len(df) < 50:
                return error_response(f"Need >= 50 points, got {len(df)}")

            ret_a = df["A"].pct_change().dropna().values
            ret_b = df["B"].pct_change().dropna().values
            n = min(len(ret_a), len(ret_b))
            ret_a, ret_b = ret_a[:n], ret_b[:n]

            # 1. KL Divergence (symmetric: Jensen-Shannon)
            # Discretize returns
            bins = np.linspace(min(ret_a.min(), ret_b.min()), max(ret_a.max(), ret_b.max()), n_bins + 1)
            hist_a, _ = np.histogram(ret_a, bins=bins, density=True)
            hist_b, _ = np.histogram(ret_b, bins=bins, density=True)
            # Add small epsilon to avoid log(0)
            eps = 1e-10
            p = hist_a + eps
            q = hist_b + eps
            p = p / p.sum()
            q = q / q.sum()

            kl_ab = float(stats.entropy(p, q))  # KL(A || B)
            kl_ba = float(stats.entropy(q, p))  # KL(B || A)
            js_div = float(0.5 * stats.entropy(p, 0.5 * (p + q)) + 0.5 * stats.entropy(q, 0.5 * (p + q)))

            # 2. Mutual Information
            from sklearn.feature_selection import mutual_info_regression
            mi = float(mutual_info_regression(ret_a.reshape(-1, 1), ret_b, n_neighbors=5, random_state=42)[0])

            # 3. Transfer Entropy (binned estimator)
            # TE(A→B) = H(B_t | B_{t-1}) - H(B_t | B_{t-1}, A_{t-1})
            def _binned_te(source, target, lags, bins_n):
                """Compute transfer entropy from source to target."""
                n_te = len(target) - lags
                if n_te < 30:
                    return 0.0
                # Discretize
                s_binned = np.digitize(source, np.linspace(source.min(), source.max(), bins_n))
                t_binned = np.digitize(target, np.linspace(target.min(), target.max(), bins_n))

                # Count joint and marginal frequencies
                # H(B_t | B_{t-1})
                joint_tb = np.zeros((bins_n + 1, bins_n + 1))
                joint_tbs = np.zeros((bins_n + 1, bins_n + 1, bins_n + 1))
                for i in range(lags, n_te + lags):
                    bt = t_binned[i]
                    bt_lag = t_binned[i - lags]
                    s_lag = s_binned[i - lags]
                    joint_tb[bt, bt_lag] += 1
                    joint_tbs[bt, bt_lag, s_lag] += 1

                # Normalize
                joint_tb_p = joint_tb / joint_tb.sum()
                joint_tbs_p = joint_tbs / joint_tbs.sum()

                # Conditional entropies
                h_t_given_tlag = 0
                h_t_given_tlag_slag = 0

                for bt in range(bins_n + 1):
                    for btl in range(bins_n + 1):
                        if joint_tb_p[bt, btl] > eps:
                            p_btl = joint_tb_p[:, btl].sum()
                            if p_btl > eps:
                                h_t_given_tlag -= joint_tb_p[bt, btl] * np.log2(joint_tb_p[bt, btl] / p_btl)

                for bt in range(bins_n + 1):
                    for btl in range(bins_n + 1):
                        for sl in range(bins_n + 1):
                            if joint_tbs_p[bt, btl, sl] > eps:
                                p_btl_sl = joint_tbs_p[:, btl, sl].sum()
                                if p_btl_sl > eps:
                                    h_t_given_tlag_slag -= joint_tbs_p[bt, btl, sl] * np.log2(
                                        joint_tbs_p[bt, btl, sl] / p_btl_sl)

                return max(0, h_t_given_tlag - h_t_given_tlag_slag)

            te_bins = min(10, n_bins)
            te_ab = _binned_te(ret_a, ret_b, te_lags, te_bins)  # A → B
            te_ba = _binned_te(ret_b, ret_a, te_lags, te_bins)  # B → A
            net_te = te_ab - te_ba

            # Determine dominant direction
            if abs(net_te) < 0.01:
                causal_direction = "bidirectional (symmetric)"
            elif net_te > 0:
                causal_direction = "A → B (A leads B)"
            else:
                causal_direction = "B → A (B leads A)"

            return success_response({
                    "kl_divergence_a_to_b": round(kl_ab, 4),
                    "kl_divergence_b_to_a": round(kl_ba, 4),
                    "jensen_shannon_divergence": round(js_div, 4),
                    "mutual_information": round(mi, 4),
                    "transfer_entropy_a_to_b": round(float(te_ab), 4),
                    "transfer_entropy_b_to_a": round(float(te_ba), 4),
                    "net_transfer_entropy": round(float(net_te), 4),
                    "causal_direction": causal_direction,
                    "n_observations": n,
                    "interpretation": (
                        f"JS divergence: {js_div:.4f} "
                        f"({'similar' if js_div < 0.1 else 'different'} distributions). "
                        f"MI: {mi:.4f}. "
                        f"Transfer entropy: {causal_direction} "
                        f"(net TE={net_te:.4f})."
                    ),
                })
        except Exception as e:
            logger.exception("info_theory failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 6. Portfolio Method Comparison
    # ------------------------------------------------------------------
    def compare(
        self,
        series_list: List[List[Dict]],
        names: List[str],
        risk_free_rate: float = 0.03,
    ) -> Dict[str, Any]:
        """Compare portfolio methods: Equal Weight, Min Variance, HRP, Inverse Vol."""
        try:
            returns = _build_returns_matrix(series_list, names)
            N = len(names)
            cov = returns.cov().values * 252
            mean_ret = returns.mean().values * 252
            asset_vols = np.sqrt(np.diag(cov))

            results = {}

            # 1. Equal Weight
            w_eq = np.ones(N) / N
            ret_eq = float(w_eq @ mean_ret)
            vol_eq = float(np.sqrt(w_eq @ cov @ w_eq))
            results["equal_weight"] = {
                "weights": {names[i]: round(1.0 / N, 4) for i in range(N)},
                "return": round(ret_eq, 4),
                "volatility": round(vol_eq, 4),
                "sharpe": round((ret_eq - risk_free_rate) / vol_eq, 3) if vol_eq > 0 else 0,
            }

            # 2. Minimum Variance
            try:
                ones = np.ones(N)
                cov_inv = np.linalg.inv(cov)
                w_mv = cov_inv @ ones / (ones @ cov_inv @ ones)
                ret_mv = float(w_mv @ mean_ret)
                vol_mv = float(np.sqrt(w_mv @ cov @ w_mv))
                results["min_variance"] = {
                    "weights": {names[i]: round(float(w_mv[i]), 4) for i in range(N)},
                    "return": round(ret_mv, 4),
                    "volatility": round(vol_mv, 4),
                    "sharpe": round((ret_mv - risk_free_rate) / vol_mv, 3) if vol_mv > 0 else 0,
                }
            except np.linalg.LinAlgError:
                results["min_variance"] = {"error": "Singular covariance matrix"}

            # 3. HRP
            hrp_result = self.hrp(series_list, names)
            if hrp_result.get("success"):
                d = hrp_result["data"]
                results["hrp"] = {
                    "weights": d["weights"],
                    "return": d["expected_return"],
                    "volatility": d["expected_volatility"],
                    "sharpe": d["sharpe_ratio"],
                }

            # 4. Inverse Volatility
            w_iv = (1 / asset_vols) / np.sum(1 / asset_vols)
            ret_iv = float(w_iv @ mean_ret)
            vol_iv = float(np.sqrt(w_iv @ cov @ w_iv))
            results["inverse_volatility"] = {
                "weights": {names[i]: round(float(w_iv[i]), 4) for i in range(N)},
                "return": round(ret_iv, 4),
                "volatility": round(vol_iv, 4),
                "sharpe": round((ret_iv - risk_free_rate) / vol_iv, 3) if vol_iv > 0 else 0,
            }

            # Find best Sharpe
            best = max(results.items(), key=lambda x: x[1].get("sharpe", -999) if isinstance(x[1].get("sharpe"), (int, float)) else -999)

            return success_response({
                    "methods": results,
                    "best_method": best[0],
                    "best_sharpe": best[1].get("sharpe", 0),
                    "n_assets": N,
                    "n_observations": len(returns),
                    "interpretation": (
                        f"Best method: {best[0]} (Sharpe={best[1].get('sharpe', 0):.3f}). "
                        f"Compared {len(results)} portfolio construction methods."
                    ),
                })
        except Exception as e:
            logger.exception("compare failed")
            return error_response(str(e))
