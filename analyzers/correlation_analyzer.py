"""
Correlation analyzer for housing prices and macroeconomic indicators.
"""
import pandas as pd
import numpy as np
from scipy import stats
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """Analyze correlations between housing prices and macro indicators."""

    def calculate_correlation(
        self,
        df: pd.DataFrame,
        col1: str,
        col2: str,
        method: str = "pearson",
    ) -> Tuple[float, float]:
        """
        Calculate correlation coefficient and p-value.

        Args:
            df: DataFrame with data
            col1: First column name
            col2: Second column name
            method: 'pearson', 'spearman', or 'kendall'

        Returns:
            Tuple of (correlation coefficient, p-value)
        """
        # Remove missing values
        valid_data = df[[col1, col2]].dropna()

        if len(valid_data) < 3:
            return np.nan, np.nan

        try:
            if method == "pearson":
                corr, pval = stats.pearsonr(valid_data[col1], valid_data[col2])
            elif method == "spearman":
                corr, pval = stats.spearmanr(valid_data[col1], valid_data[col2])
            elif method == "kendall":
                corr, pval = stats.kendalltau(valid_data[col1], valid_data[col2])
            else:
                raise ValueError(f"Unknown method: {method}")

            return corr, pval

        except Exception as e:
            logger.warning(f"Correlation calculation failed: {e}")
            return np.nan, np.nan

    def hpi_m2_correlation(
        self,
        df: pd.DataFrame,
        hpi_col: str = "value",
        m2_col: str = "m2",
        city_col: str = "city",
        date_col: str = "date",
    ) -> pd.DataFrame:
        """
        Calculate HPI vs M2 money supply correlation for each city.

        Tests hypothesis: Money supply growth drives housing price growth.

        Args:
            df: DataFrame with HPI and M2 data
            hpi_col: Housing price index column
            m2_col: Money supply column
            city_col: City column
            date_col: Date column

        Returns:
            DataFrame with correlation results by city
        """
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])

        if m2_col not in df.columns:
            logger.warning("M2 column not found, cannot calculate HPI-M2 correlation")
            return pd.DataFrame()

        results = []

        for city in df[city_col].unique():
            city_df = df[df[city_col] == city].copy()
            city_df = city_df.sort_values(date_col)

            # Correlation in levels
            level_corr, level_p = self.calculate_correlation(city_df, hpi_col, m2_col)

            # Correlation in growth rates (more meaningful economically)
            city_df["hpi_growth"] = city_df[hpi_col].pct_change(4) * 100  # YoY
            city_df["m2_growth"] = city_df[m2_col].pct_change(4) * 100

            growth_corr, growth_p = self.calculate_correlation(
                city_df, "hpi_growth", "m2_growth"
            )

            results.append({
                "city": city,
                "level_correlation": round(level_corr, 3) if not pd.isna(level_corr) else None,
                "level_pvalue": round(level_p, 4) if not pd.isna(level_p) else None,
                "growth_correlation": round(growth_corr, 3) if not pd.isna(growth_corr) else None,
                "growth_pvalue": round(growth_p, 4) if not pd.isna(growth_p) else None,
                "n_observations": len(city_df),
            })

        return pd.DataFrame(results)

    def cross_city_correlation(
        self,
        df: pd.DataFrame,
        value_col: str = "value",
        city_col: str = "city",
        date_col: str = "date",
        use_growth: bool = True,
    ) -> pd.DataFrame:
        """
        Calculate correlation matrix between city housing prices.

        Args:
            df: DataFrame with housing data
            use_growth: If True, calculate correlation of growth rates
                       If False, calculate correlation of levels

        Returns:
            Correlation matrix (cities x cities)
        """
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])

        # Pivot to wide format
        pivot_df = df.pivot_table(
            index=date_col,
            columns=city_col,
            values=value_col,
            aggfunc="first",
        )

        if use_growth:
            # Calculate YoY growth rates
            pivot_df = pivot_df.pct_change(4) * 100

        return pivot_df.corr()

    def hpi_cpi_correlation(
        self,
        df: pd.DataFrame,
        hpi_col: str = "value",
        cpi_col: str = "cpi",
        city_col: str = "city",
        date_col: str = "date",
    ) -> pd.DataFrame:
        """
        Calculate HPI vs CPI correlation for each city.

        Tests how well housing prices track general inflation.

        Args:
            df: DataFrame with HPI and CPI data

        Returns:
            DataFrame with correlation results by city
        """
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])

        if cpi_col not in df.columns:
            logger.warning("CPI column not found")
            return pd.DataFrame()

        results = []

        for city in df[city_col].unique():
            city_df = df[df[city_col] == city].copy()
            city_df = city_df.sort_values(date_col)

            # Correlation in growth rates
            city_df["hpi_growth"] = city_df[hpi_col].pct_change(4) * 100
            city_df["cpi_growth"] = city_df[cpi_col].pct_change(4) * 100

            corr, pval = self.calculate_correlation(city_df, "hpi_growth", "cpi_growth")

            results.append({
                "city": city,
                "correlation": round(corr, 3) if not pd.isna(corr) else None,
                "pvalue": round(pval, 4) if not pd.isna(pval) else None,
            })

        return pd.DataFrame(results)

    def lagged_correlation(
        self,
        df: pd.DataFrame,
        col1: str,
        col2: str,
        max_lag: int = 8,  # 8 quarters = 2 years
    ) -> pd.DataFrame:
        """
        Calculate correlation at different lag periods.

        Useful for testing if one variable leads another.

        Args:
            df: DataFrame with data
            col1: First column (potentially leading)
            col2: Second column (potentially lagging)
            max_lag: Maximum lag to test (in periods)

        Returns:
            DataFrame with correlation at each lag
        """
        results = []

        for lag in range(-max_lag, max_lag + 1):
            df_lagged = df.copy()

            if lag > 0:
                # col1 leads col2
                df_lagged[f"{col2}_lagged"] = df_lagged[col2].shift(lag)
                corr, pval = self.calculate_correlation(df_lagged, col1, f"{col2}_lagged")
            elif lag < 0:
                # col2 leads col1
                df_lagged[f"{col1}_lagged"] = df_lagged[col1].shift(-lag)
                corr, pval = self.calculate_correlation(df_lagged, f"{col1}_lagged", col2)
            else:
                corr, pval = self.calculate_correlation(df_lagged, col1, col2)

            results.append({
                "lag": lag,
                "correlation": corr,
                "pvalue": pval,
            })

        result_df = pd.DataFrame(results)

        # Find optimal lag
        if not result_df["correlation"].isna().all():
            best_idx = result_df["correlation"].abs().idxmax()
            result_df["is_optimal"] = result_df.index == best_idx

        return result_df

    def create_correlation_summary(
        self,
        df: pd.DataFrame,
        hpi_col: str = "value",
        cpi_col: str = "cpi",
        m2_col: str = "m2",
        city_col: str = "city",
    ) -> pd.DataFrame:
        """
        Create comprehensive correlation summary.

        Args:
            df: DataFrame with all data

        Returns:
            Summary DataFrame with multiple correlation measures
        """
        # HPI-M2 correlation
        m2_corr = self.hpi_m2_correlation(df, hpi_col, m2_col, city_col)

        # HPI-CPI correlation
        cpi_corr = self.hpi_cpi_correlation(df, hpi_col, cpi_col, city_col)

        # Merge results
        if not m2_corr.empty and not cpi_corr.empty:
            summary = m2_corr.merge(
                cpi_corr.rename(columns={
                    "correlation": "cpi_correlation",
                    "pvalue": "cpi_pvalue"
                }),
                on="city",
                how="outer"
            )
        elif not m2_corr.empty:
            summary = m2_corr
        elif not cpi_corr.empty:
            summary = cpi_corr
        else:
            return pd.DataFrame()

        return summary
