"""
Price-to-Income Ratio (PIR) calculator for housing affordability analysis.
"""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class PIRCalculator:
    """Calculate Price-to-Income Ratio for housing affordability analysis."""

    # PIR thresholds (Demographia methodology)
    THRESHOLDS = {
        "affordable": 3.0,
        "moderately_unaffordable": 5.0,
        "seriously_unaffordable": 7.0,
        # > 7.0 is "severely unaffordable"
    }

    def __init__(self):
        self.results = None

    def calculate_pir(
        self,
        housing_price: float,
        annual_income: float,
    ) -> float:
        """
        Calculate basic PIR.

        PIR = Median House Price / Median Annual Household Income

        Args:
            housing_price: Median or average house price
            annual_income: Median or average annual household income

        Returns:
            Price-to-income ratio

        Interpretation (Demographia):
        - < 3.0: Affordable
        - 3.0 - 5.0: Moderately unaffordable
        - 5.1 - 7.0: Seriously unaffordable
        - > 7.0: Severely unaffordable
        """
        if annual_income <= 0 or pd.isna(annual_income):
            return np.nan
        if pd.isna(housing_price):
            return np.nan

        return housing_price / annual_income

    def calculate_index_based_pir(
        self,
        df: pd.DataFrame,
        hpi_col: str = "value_rebased",
        income_index_col: str = "income_index",
        output_col: str = "pir_index",
    ) -> pd.DataFrame:
        """
        Calculate relative PIR change using indices.

        When absolute prices/incomes aren't available, use indices to track
        relative affordability changes.

        Relative PIR Index = (HPI / Income Index) * 100

        Args:
            df: DataFrame with HPI and income index
            hpi_col: Housing price index column
            income_index_col: Income index column
            output_col: Output column name

        Returns:
            DataFrame with PIR index
        """
        df = df.copy()

        if income_index_col not in df.columns:
            logger.warning("Income index not available, cannot calculate PIR index")
            df[output_col] = np.nan
            return df

        # Handle zeros and NaN
        income = df[income_index_col].replace(0, np.nan)
        df[output_col] = (df[hpi_col] / income) * 100

        return df

    def calculate_pir_series(
        self,
        housing_df: pd.DataFrame,
        income_df: pd.DataFrame,
        city_col: str = "city",
        date_col: str = "date",
        housing_value_col: str = "value",
        income_value_col: str = "value",
    ) -> pd.DataFrame:
        """
        Calculate PIR time series for multiple cities.

        Args:
            housing_df: DataFrame with housing prices
            income_df: DataFrame with income data
            city_col: City column name
            date_col: Date column name

        Returns:
            DataFrame with PIR for each city and date
        """
        # Merge housing and income data
        housing_df = housing_df.copy()
        income_df = income_df.copy()

        housing_df[date_col] = pd.to_datetime(housing_df[date_col])
        income_df[date_col] = pd.to_datetime(income_df[date_col])

        # Create quarter column for merging
        housing_df["quarter"] = housing_df[date_col].dt.to_period("Q")
        income_df["quarter"] = income_df[date_col].dt.to_period("Q")

        merged = housing_df.merge(
            income_df[[city_col, "quarter", income_value_col]].rename(
                columns={income_value_col: "income"}
            ),
            on=[city_col, "quarter"],
            how="left",
        )

        # Calculate PIR
        merged["pir"] = merged.apply(
            lambda row: self.calculate_pir(row[housing_value_col], row["income"]),
            axis=1,
        )

        return merged

    def categorize_affordability(self, pir: float) -> str:
        """
        Categorize PIR into affordability buckets.

        Args:
            pir: Price-to-income ratio

        Returns:
            Affordability category string
        """
        if pd.isna(pir):
            return "Unknown"
        elif pir < self.THRESHOLDS["affordable"]:
            return "Affordable"
        elif pir < self.THRESHOLDS["moderately_unaffordable"]:
            return "Moderately Unaffordable"
        elif pir < self.THRESHOLDS["seriously_unaffordable"]:
            return "Seriously Unaffordable"
        else:
            return "Severely Unaffordable"

    def add_affordability_category(
        self,
        df: pd.DataFrame,
        pir_col: str = "pir",
        output_col: str = "affordability_category",
    ) -> pd.DataFrame:
        """
        Add affordability category column to DataFrame.

        Args:
            df: DataFrame with PIR column
            pir_col: PIR column name
            output_col: Output column name

        Returns:
            DataFrame with affordability category
        """
        df = df.copy()
        df[output_col] = df[pir_col].apply(self.categorize_affordability)
        return df

    def calculate_affordability_summary(
        self,
        df: pd.DataFrame,
        city_col: str = "city",
        pir_col: str = "pir",
        date_col: str = "date",
    ) -> pd.DataFrame:
        """
        Calculate affordability summary by city.

        Args:
            df: DataFrame with PIR data

        Returns:
            Summary DataFrame with statistics by city
        """
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])

        summary = []

        for city in df[city_col].unique():
            city_df = df[df[city_col] == city].sort_values(date_col)

            if city_df[pir_col].isna().all():
                continue

            latest_pir = city_df[pir_col].iloc[-1]
            avg_pir = city_df[pir_col].mean()
            min_pir = city_df[pir_col].min()
            max_pir = city_df[pir_col].max()
            min_date = city_df.loc[city_df[pir_col].idxmin(), date_col]
            max_date = city_df.loc[city_df[pir_col].idxmax(), date_col]

            summary.append({
                "city": city,
                "latest_pir": round(latest_pir, 1) if not pd.isna(latest_pir) else None,
                "avg_pir": round(avg_pir, 1) if not pd.isna(avg_pir) else None,
                "min_pir": round(min_pir, 1) if not pd.isna(min_pir) else None,
                "max_pir": round(max_pir, 1) if not pd.isna(max_pir) else None,
                "min_pir_date": min_date,
                "max_pir_date": max_date,
                "latest_category": self.categorize_affordability(latest_pir),
            })

        return pd.DataFrame(summary)

    def calculate_pir_change(
        self,
        df: pd.DataFrame,
        city_col: str = "city",
        pir_col: str = "pir",
        date_col: str = "date",
        periods: int = 4,  # 4 quarters = 1 year
    ) -> pd.DataFrame:
        """
        Calculate PIR change over time.

        Args:
            df: DataFrame with PIR data
            periods: Number of periods for change calculation

        Returns:
            DataFrame with PIR change columns
        """
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values([city_col, date_col])

        # Calculate absolute and percentage change
        df["pir_change"] = df.groupby(city_col)[pir_col].diff(periods)
        df["pir_change_pct"] = df.groupby(city_col)[pir_col].pct_change(periods) * 100

        return df
