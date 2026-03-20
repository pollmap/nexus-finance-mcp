"""
Growth calculator for housing price metrics.
"""
import pandas as pd
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class GrowthCalculator:
    """Calculate various growth metrics for housing prices."""

    def calculate_yoy_growth(
        self,
        df: pd.DataFrame,
        value_col: str = "value",
        date_col: str = "date",
        city_col: str = "city",
        output_col: str = "yoy_growth",
    ) -> pd.DataFrame:
        """
        Calculate year-over-year growth rate.

        Args:
            df: DataFrame with housing data
            value_col: Value column name
            date_col: Date column name
            city_col: City column name
            output_col: Output column name

        Returns:
            DataFrame with YoY growth column
        """
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values([city_col, date_col])

        # For quarterly data, shift by 4 periods for YoY
        df[output_col] = df.groupby(city_col)[value_col].pct_change(periods=4) * 100

        return df

    def calculate_qoq_growth(
        self,
        df: pd.DataFrame,
        value_col: str = "value",
        date_col: str = "date",
        city_col: str = "city",
        output_col: str = "qoq_growth",
    ) -> pd.DataFrame:
        """
        Calculate quarter-over-quarter growth rate.

        Args:
            df: DataFrame with quarterly housing data

        Returns:
            DataFrame with QoQ growth column
        """
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values([city_col, date_col])

        df[output_col] = df.groupby(city_col)[value_col].pct_change(periods=1) * 100

        return df

    @staticmethod
    def calculate_cagr(
        start_value: float,
        end_value: float,
        years: float,
    ) -> float:
        """
        Calculate Compound Annual Growth Rate.

        CAGR = (End Value / Start Value)^(1/years) - 1

        Args:
            start_value: Value at start of period
            end_value: Value at end of period
            years: Number of years

        Returns:
            CAGR as percentage
        """
        if start_value <= 0 or years <= 0 or pd.isna(start_value) or pd.isna(end_value):
            return np.nan
        return ((end_value / start_value) ** (1 / years) - 1) * 100

    def calculate_period_cagr(
        self,
        df: pd.DataFrame,
        value_col: str = "value",
        date_col: str = "date",
        city_col: str = "city",
        start_date: str = None,
        end_date: str = None,
    ) -> pd.DataFrame:
        """
        Calculate CAGR for each city over specified period.

        Args:
            df: DataFrame with housing data
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Summary DataFrame with CAGR by city
        """
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])

        if start_date:
            df = df[df[date_col] >= start_date]
        if end_date:
            df = df[df[date_col] <= end_date]

        results = []

        for city in df[city_col].unique():
            city_df = df[df[city_col] == city].sort_values(date_col)
            city_df = city_df.dropna(subset=[value_col])

            if len(city_df) < 2:
                continue

            start_val = city_df[value_col].iloc[0]
            end_val = city_df[value_col].iloc[-1]
            start_dt = city_df[date_col].iloc[0]
            end_dt = city_df[date_col].iloc[-1]

            years = (end_dt - start_dt).days / 365.25
            cagr = self.calculate_cagr(start_val, end_val, years)

            results.append({
                "city": city,
                "start_date": start_dt,
                "end_date": end_dt,
                "start_value": round(start_val, 2),
                "end_value": round(end_val, 2),
                "years": round(years, 2),
                "cagr": round(cagr, 2) if not pd.isna(cagr) else None,
            })

        return pd.DataFrame(results)

    def calculate_cumulative_return(
        self,
        df: pd.DataFrame,
        value_col: str = "value",
        date_col: str = "date",
        city_col: str = "city",
        output_col: str = "cumulative_return",
    ) -> pd.DataFrame:
        """
        Calculate cumulative return from start of series.

        Args:
            df: DataFrame with housing data

        Returns:
            DataFrame with cumulative return column (as percentage)
        """
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values([city_col, date_col])

        def cum_return(group):
            group = group.copy()
            first_val = group[value_col].iloc[0]
            if pd.isna(first_val) or first_val == 0:
                group[output_col] = np.nan
            else:
                group[output_col] = ((group[value_col] / first_val) - 1) * 100
            return group

        return df.groupby(city_col, group_keys=False).apply(cum_return)

    def calculate_volatility(
        self,
        df: pd.DataFrame,
        value_col: str = "value",
        date_col: str = "date",
        city_col: str = "city",
        window: int = 4,  # 4 quarters = 1 year rolling window
    ) -> pd.DataFrame:
        """
        Calculate rolling volatility (standard deviation of returns).

        Args:
            df: DataFrame with housing data
            window: Rolling window size (in periods)

        Returns:
            DataFrame with volatility column
        """
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values([city_col, date_col])

        # First calculate returns
        df["returns"] = df.groupby(city_col)[value_col].pct_change() * 100

        # Then calculate rolling volatility
        df["volatility"] = df.groupby(city_col)["returns"].transform(
            lambda x: x.rolling(window=window, min_periods=2).std()
        )

        return df

    def calculate_growth_summary(
        self,
        df: pd.DataFrame,
        value_col: str = "value",
        date_col: str = "date",
        city_col: str = "city",
    ) -> pd.DataFrame:
        """
        Calculate comprehensive growth summary by city.

        Args:
            df: DataFrame with housing data

        Returns:
            Summary DataFrame with multiple growth metrics
        """
        # Calculate YoY growth
        df_with_growth = self.calculate_yoy_growth(df, value_col, date_col, city_col)

        # Calculate CAGR
        cagr_df = self.calculate_period_cagr(df, value_col, date_col, city_col)

        # Calculate cumulative return
        df_with_cumret = self.calculate_cumulative_return(df, value_col, date_col, city_col)

        # Calculate volatility
        df_with_vol = self.calculate_volatility(df, value_col, date_col, city_col)

        # Aggregate statistics
        summary = df_with_growth.groupby(city_col).agg(
            avg_yoy_growth=("yoy_growth", "mean"),
            max_yoy_growth=("yoy_growth", "max"),
            min_yoy_growth=("yoy_growth", "min"),
        ).reset_index()

        # Add CAGR
        summary = summary.merge(
            cagr_df[[city_col, "cagr", "years"]],
            on=city_col,
            how="left"
        )

        # Add cumulative return (latest)
        latest_cumret = df_with_cumret.groupby(city_col)["cumulative_return"].last().reset_index()
        summary = summary.merge(latest_cumret, on=city_col, how="left")

        # Add average volatility
        avg_vol = df_with_vol.groupby(city_col)["volatility"].mean().reset_index()
        avg_vol.columns = [city_col, "avg_volatility"]
        summary = summary.merge(avg_vol, on=city_col, how="left")

        # Round values
        numeric_cols = summary.select_dtypes(include=[np.number]).columns
        summary[numeric_cols] = summary[numeric_cols].round(2)

        return summary
