"""
Real price calculator for inflation adjustment.
"""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class RealPriceCalculator:
    """Calculate inflation-adjusted (real) housing prices."""

    def __init__(self, base_year: int = 2015):
        """
        Initialize calculator.

        Args:
            base_year: Base year for CPI deflation
        """
        self.base_year = base_year

    def calculate_real_index(
        self,
        df: pd.DataFrame,
        nominal_col: str = "value",
        cpi_col: str = "cpi",
        date_col: str = "date",
        output_col: str = "value_real",
    ) -> pd.DataFrame:
        """
        Calculate real (inflation-adjusted) housing price index.

        Real HPI = (Nominal HPI / CPI) * 100

        Both indices are rebased to the same base year internally.

        Args:
            df: DataFrame with nominal HPI and CPI columns
            nominal_col: Column name for nominal HPI
            cpi_col: Column name for CPI
            date_col: Column name for date
            output_col: Column name for output real index

        Returns:
            DataFrame with real index column added
        """
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])

        # Handle missing CPI
        if cpi_col not in df.columns or df[cpi_col].isna().all():
            logger.warning("No CPI data available, cannot calculate real prices")
            df[output_col] = np.nan
            return df

        # Rebase CPI to base year
        cpi_rebased = self._rebase_series(df, cpi_col, date_col)

        # Calculate real index
        # Real = Nominal / (CPI / 100) = Nominal * 100 / CPI
        df[output_col] = (df[nominal_col] / cpi_rebased) * 100

        logger.info(f"Calculated real prices using CPI, base year {self.base_year}")

        return df

    def _rebase_series(
        self,
        df: pd.DataFrame,
        value_col: str,
        date_col: str,
    ) -> pd.Series:
        """Rebase a series to base year = 100."""
        base_mask = df[date_col].dt.year == self.base_year
        base_values = df.loc[base_mask, value_col]

        if len(base_values) == 0:
            # Find closest year
            available_years = df[date_col].dt.year.unique()
            closest = min(available_years, key=lambda x: abs(x - self.base_year))
            base_mask = df[date_col].dt.year == closest
            base_values = df.loc[base_mask, value_col]
            logger.warning(f"Using {closest} as base year instead of {self.base_year}")

        base_avg = base_values.mean()

        if pd.isna(base_avg) or base_avg == 0:
            return pd.Series([np.nan] * len(df))

        return (df[value_col] / base_avg) * 100

    def calculate_real_by_city(
        self,
        df: pd.DataFrame,
        city_col: str = "city",
        country_col: str = "country",
        nominal_col: str = "value",
        cpi_col: str = "cpi",
        date_col: str = "date",
        output_col: str = "value_real",
    ) -> pd.DataFrame:
        """
        Calculate real prices for multiple cities.

        CPI is matched by country, applied to each city in that country.

        Args:
            df: DataFrame with city, country, nominal price, and CPI

        Returns:
            DataFrame with real prices for all cities
        """
        df = df.copy()

        if cpi_col not in df.columns:
            df[output_col] = np.nan
            return df

        result_dfs = []

        for city in df[city_col].unique():
            city_df = df[df[city_col] == city].copy()
            city_df = self.calculate_real_index(
                city_df, nominal_col, cpi_col, date_col, output_col
            )
            result_dfs.append(city_df)

        return pd.concat(result_dfs, ignore_index=True)

    def calculate_real_growth(
        self,
        df: pd.DataFrame,
        real_col: str = "value_real",
        city_col: str = "city",
        date_col: str = "date",
        periods: int = 4,  # 4 quarters = 1 year
    ) -> pd.DataFrame:
        """
        Calculate year-over-year real price growth.

        Args:
            df: DataFrame with real prices
            real_col: Column with real prices
            periods: Number of periods for growth calculation (4 = YoY for quarterly)

        Returns:
            DataFrame with real_yoy_growth column
        """
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values([city_col, date_col])

        df["real_yoy_growth"] = df.groupby(city_col)[real_col].pct_change(periods) * 100

        return df

    def calculate_inflation_impact(
        self,
        df: pd.DataFrame,
        nominal_col: str = "value",
        real_col: str = "value_real",
        city_col: str = "city",
    ) -> pd.DataFrame:
        """
        Calculate the cumulative impact of inflation on housing prices.

        Returns summary showing how much of price growth is real vs inflation.

        Args:
            df: DataFrame with nominal and real prices

        Returns:
            Summary DataFrame by city
        """
        df = df.copy()

        results = []

        for city in df[city_col].unique():
            city_df = df[df[city_col] == city].sort_values("date")

            if len(city_df) < 2:
                continue

            first_nominal = city_df[nominal_col].iloc[0]
            last_nominal = city_df[nominal_col].iloc[-1]
            first_real = city_df[real_col].iloc[0]
            last_real = city_df[real_col].iloc[-1]

            if pd.isna(first_real) or pd.isna(last_real):
                continue

            nominal_change = ((last_nominal / first_nominal) - 1) * 100
            real_change = ((last_real / first_real) - 1) * 100
            inflation_contribution = nominal_change - real_change

            results.append({
                "city": city,
                "nominal_change_pct": round(nominal_change, 1),
                "real_change_pct": round(real_change, 1),
                "inflation_contribution_pct": round(inflation_contribution, 1),
                "real_share_of_growth": round(
                    (real_change / nominal_change * 100) if nominal_change != 0 else 0, 1
                ),
            })

        return pd.DataFrame(results)
