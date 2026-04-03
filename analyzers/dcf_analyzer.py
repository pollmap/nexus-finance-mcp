"""
DCF (Discounted Cash Flow) Valuation Analyzer.

Provides tools for DCF-based equity valuation including:
- WACC calculation (CAPM-based)
- Free Cash Flow projection
- Terminal Value calculation
- Sensitivity analysis

Uses ECOS real-time data when available, falls back to market defaults with warning.
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from analyzers.defaults import MARKET_DEFAULTS as TEST_VALUES

logger = logging.getLogger(__name__)


@dataclass
class CompanyFinancials:
    """Company financial data for DCF analysis."""

    stock_code: str
    company_name: str

    # Income Statement
    revenue: float = 0.0
    ebit: float = 0.0  # Operating Income
    ebitda: float = 0.0
    net_income: float = 0.0

    # Balance Sheet
    total_debt: float = 0.0
    cash: float = 0.0
    total_equity: float = 0.0
    shares_outstanding: float = 1.0

    # Cash Flow Statement
    capex: float = 0.0
    depreciation: float = 0.0
    change_in_nwc: float = 0.0  # Net Working Capital change

    # Market Data
    market_cap: float = 0.0
    beta: float = TEST_VALUES["default_beta"]

    # Rates
    cost_of_debt: float = 0.05  # 5% default
    tax_rate: float = TEST_VALUES["default_tax_rate"]


@dataclass
class DCFResult:
    """Result of DCF valuation."""

    stock_code: str
    company_name: str

    # WACC components
    cost_of_equity: float = 0.0
    cost_of_debt_after_tax: float = 0.0
    wacc: float = 0.0

    # Valuation
    projected_fcf: List[float] = field(default_factory=list)
    pv_fcf: List[float] = field(default_factory=list)
    terminal_value: float = 0.0
    pv_terminal_value: float = 0.0
    enterprise_value: float = 0.0
    equity_value: float = 0.0
    per_share_value: float = 0.0

    # Comparison
    current_price: float = 0.0
    upside_potential: float = 0.0  # percentage

    # Metadata
    assumptions: Dict[str, Any] = field(default_factory=dict)


class DCFAnalyzer:
    """
    DCF Valuation Engine.

    Implements standard DCF methodology:
    1. Calculate WACC using CAPM
    2. Project Free Cash Flows
    3. Calculate Terminal Value (Gordon Growth)
    4. Discount to present value
    5. Calculate per-share intrinsic value
    """

    def __init__(
        self,
        risk_free_rate: float = None,
        market_risk_premium: float = None,
        terminal_growth_rate: float = None,
    ):
        """
        Initialize DCF Analyzer.

        Args:
            risk_free_rate: Risk-free rate (default: 3.5%)
            market_risk_premium: Market risk premium (default: 6%)
            terminal_growth_rate: Perpetual growth rate (default: 2%)
        """
        self.risk_free_rate = risk_free_rate if risk_free_rate is not None else TEST_VALUES["risk_free_rate"]
        self.market_risk_premium = market_risk_premium if market_risk_premium is not None else TEST_VALUES["market_risk_premium"]
        self.terminal_growth_rate = terminal_growth_rate if terminal_growth_rate is not None else TEST_VALUES["terminal_growth_rate"]

        if risk_free_rate is None or market_risk_premium is None or terminal_growth_rate is None:
            logger.warning("DCF using hardcoded TEST_VALUES for missing parameters")

        logger.info(
            f"DCF Analyzer initialized: Rf={self.risk_free_rate:.2%}, "
            f"ERP={self.market_risk_premium:.2%}, g={self.terminal_growth_rate:.2%}"
        )

    def calculate_cost_of_equity(self, beta: float) -> float:
        """
        Calculate cost of equity using CAPM.

        Ke = Rf + β × (Rm - Rf)

        Args:
            beta: Company beta

        Returns:
            Cost of equity
        """
        return self.risk_free_rate + beta * self.market_risk_premium

    def calculate_wacc(self, financials: CompanyFinancials) -> Tuple[float, Dict[str, float]]:
        """
        Calculate Weighted Average Cost of Capital.

        WACC = (E/V) × Ke + (D/V) × Kd × (1 - T)

        Args:
            financials: Company financial data

        Returns:
            Tuple of (WACC, components dict)
        """
        # Total value = Debt + Equity
        total_value = financials.total_debt + financials.market_cap

        if total_value == 0:
            logger.warning("Total value is zero, using default WACC")
            return 0.10, {}

        # Weight of equity and debt
        weight_equity = financials.market_cap / total_value
        weight_debt = financials.total_debt / total_value

        # Cost of equity (CAPM)
        cost_of_equity = self.calculate_cost_of_equity(financials.beta)

        # Cost of debt after tax
        cost_of_debt_after_tax = financials.cost_of_debt * (1 - financials.tax_rate)

        # WACC
        wacc = (weight_equity * cost_of_equity) + (weight_debt * cost_of_debt_after_tax)

        components = {
            "cost_of_equity": cost_of_equity,
            "cost_of_debt": financials.cost_of_debt,
            "cost_of_debt_after_tax": cost_of_debt_after_tax,
            "weight_equity": weight_equity,
            "weight_debt": weight_debt,
            "tax_rate": financials.tax_rate,
            "beta": financials.beta,
            "risk_free_rate": self.risk_free_rate,
            "market_risk_premium": self.market_risk_premium,
        }

        logger.debug(f"WACC calculated: {wacc:.2%}")
        return wacc, components

    def calculate_fcf(self, financials: CompanyFinancials) -> float:
        """
        Calculate Free Cash Flow to Firm (FCFF).

        FCFF = EBIT × (1 - T) + D&A - CapEx - ΔNWC

        Args:
            financials: Company financial data

        Returns:
            Free Cash Flow
        """
        nopat = financials.ebit * (1 - financials.tax_rate)  # Net Operating Profit After Tax
        fcf = nopat + financials.depreciation - financials.capex - financials.change_in_nwc

        return fcf

    def project_fcf(
        self,
        base_fcf: float,
        growth_rates: List[float] = None,
        years: int = None,
    ) -> List[float]:
        """
        Project future Free Cash Flows.

        Args:
            base_fcf: Current year FCF
            growth_rates: Growth rates for each year (if None, uses declining growth)
            years: Number of years to project

        Returns:
            List of projected FCFs
        """
        years = years if years is not None else TEST_VALUES["projection_years"]

        if growth_rates is None:
            # Default: declining growth from 15% to terminal rate
            start_growth = 0.15
            end_growth = self.terminal_growth_rate + 0.03
            growth_rates = np.linspace(start_growth, end_growth, years).tolist()

        projected = []
        current_fcf = base_fcf

        for rate in growth_rates:
            current_fcf = current_fcf * (1 + rate)
            projected.append(current_fcf)

        return projected

    def calculate_terminal_value(
        self,
        final_fcf: float,
        wacc: float,
        growth_rate: float = None,
    ) -> float:
        """
        Calculate Terminal Value using Gordon Growth Model.

        TV = FCF_n+1 / (WACC - g)

        Args:
            final_fcf: FCF in final projection year
            wacc: Weighted Average Cost of Capital
            growth_rate: Perpetual growth rate

        Returns:
            Terminal Value
        """
        g = growth_rate if growth_rate is not None else self.terminal_growth_rate

        if wacc <= g:
            logger.warning(f"WACC ({wacc:.2%}) <= growth rate ({g:.2%}), adjusting")
            g = wacc - 0.01

        fcf_next = final_fcf * (1 + g)
        terminal_value = fcf_next / (wacc - g)

        return terminal_value

    def discount_cash_flows(
        self,
        cash_flows: List[float],
        discount_rate: float,
    ) -> List[float]:
        """
        Discount future cash flows to present value.

        Args:
            cash_flows: List of future cash flows
            discount_rate: Discount rate (WACC)

        Returns:
            List of present values
        """
        pv = []
        for i, cf in enumerate(cash_flows, 1):
            pv.append(cf / ((1 + discount_rate) ** i))
        return pv

    def run_dcf(
        self,
        financials: CompanyFinancials,
        growth_rates: List[float] = None,
        projection_years: int = None,
    ) -> DCFResult:
        """
        Run complete DCF valuation.

        Args:
            financials: Company financial data
            growth_rates: Optional custom growth rates
            projection_years: Number of years to project

        Returns:
            DCFResult with full valuation
        """
        years = projection_years if projection_years is not None else TEST_VALUES["projection_years"]

        # Step 1: Calculate WACC
        wacc, wacc_components = self.calculate_wacc(financials)

        # Step 2: Calculate base FCF
        base_fcf = self.calculate_fcf(financials)

        if base_fcf <= 0:
            logger.warning(f"Negative FCF ({base_fcf:,.0f}), using EBITDA proxy")
            base_fcf = financials.ebitda * 0.6  # Rough proxy

        # Step 3: Project FCFs
        projected_fcf = self.project_fcf(base_fcf, growth_rates, years)

        # Step 4: Calculate Terminal Value
        terminal_value = self.calculate_terminal_value(projected_fcf[-1], wacc)

        # Step 5: Discount to present value
        pv_fcf = self.discount_cash_flows(projected_fcf, wacc)
        pv_terminal = terminal_value / ((1 + wacc) ** years)

        # Step 6: Calculate Enterprise Value and Equity Value
        enterprise_value = sum(pv_fcf) + pv_terminal
        equity_value = enterprise_value - financials.total_debt + financials.cash

        # Step 7: Per share value
        per_share_value = equity_value / financials.shares_outstanding

        # Step 8: Calculate upside
        current_price = financials.market_cap / financials.shares_outstanding
        upside = ((per_share_value / current_price) - 1) * 100 if current_price > 0 else 0

        result = DCFResult(
            stock_code=financials.stock_code,
            company_name=financials.company_name,
            cost_of_equity=wacc_components.get("cost_of_equity", 0),
            cost_of_debt_after_tax=wacc_components.get("cost_of_debt_after_tax", 0),
            wacc=wacc,
            projected_fcf=projected_fcf,
            pv_fcf=pv_fcf,
            terminal_value=terminal_value,
            pv_terminal_value=pv_terminal,
            enterprise_value=enterprise_value,
            equity_value=equity_value,
            per_share_value=per_share_value,
            current_price=current_price,
            upside_potential=upside,
            assumptions={
                "risk_free_rate": self.risk_free_rate,
                "market_risk_premium": self.market_risk_premium,
                "terminal_growth_rate": self.terminal_growth_rate,
                "projection_years": years,
                "beta": financials.beta,
                "tax_rate": financials.tax_rate,
                **wacc_components,
            },
        )

        logger.info(
            f"DCF Complete: {financials.company_name} - "
            f"Fair Value: {per_share_value:,.0f}, Upside: {upside:.1f}%"
        )

        return result

    def sensitivity_analysis(
        self,
        financials: CompanyFinancials,
        wacc_range: Tuple[float, float] = (0.07, 0.13),
        growth_range: Tuple[float, float] = (0.01, 0.04),
        steps: int = 5,
    ) -> pd.DataFrame:
        """
        Run sensitivity analysis on WACC and terminal growth rate.

        Args:
            financials: Company financial data
            wacc_range: (min, max) WACC values
            growth_range: (min, max) terminal growth rates
            steps: Number of steps for each variable

        Returns:
            DataFrame with sensitivity matrix (per-share values)
        """
        wacc_values = np.linspace(wacc_range[0], wacc_range[1], steps)
        growth_values = np.linspace(growth_range[0], growth_range[1], steps)

        # Store original values
        original_terminal_growth = self.terminal_growth_rate

        results = []

        for wacc in wacc_values:
            row = []
            for growth in growth_values:
                self.terminal_growth_rate = growth

                # Run DCF with fixed WACC
                base_fcf = self.calculate_fcf(financials)
                if base_fcf <= 0:
                    base_fcf = financials.ebitda * 0.6

                projected_fcf = self.project_fcf(base_fcf)
                terminal_value = self.calculate_terminal_value(projected_fcf[-1], wacc, growth)
                pv_fcf = self.discount_cash_flows(projected_fcf, wacc)
                pv_terminal = terminal_value / ((1 + wacc) ** len(projected_fcf))

                ev = sum(pv_fcf) + pv_terminal
                equity_value = ev - financials.total_debt + financials.cash
                per_share = equity_value / financials.shares_outstanding

                row.append(per_share)

            results.append(row)

        # Restore original value
        self.terminal_growth_rate = original_terminal_growth

        # Create DataFrame
        df = pd.DataFrame(
            results,
            index=[f"{w:.1%}" for w in wacc_values],
            columns=[f"{g:.1%}" for g in growth_values],
        )
        df.index.name = "WACC"
        df.columns.name = "Terminal Growth"

        return df


def create_sample_financials() -> CompanyFinancials:
    """Create sample financials for testing (삼성전자 approximate values)."""
    return CompanyFinancials(
        stock_code="005930",
        company_name="삼성전자",
        revenue=300_000_000_000_000,        # 300조원
        ebit=45_000_000_000_000,            # 45조원
        ebitda=80_000_000_000_000,          # 80조원
        net_income=35_000_000_000_000,      # 35조원
        total_debt=30_000_000_000_000,      # 30조원
        cash=100_000_000_000_000,           # 100조원
        total_equity=350_000_000_000_000,   # 350조원
        shares_outstanding=5_969_782_550,    # 약 60억주
        capex=50_000_000_000_000,           # 50조원
        depreciation=40_000_000_000_000,    # 40조원
        change_in_nwc=5_000_000_000_000,    # 5조원
        market_cap=400_000_000_000_000,     # 400조원
        beta=1.1,
        cost_of_debt=0.04,
        tax_rate=0.22,
    )


if __name__ == "__main__":
    # Test the DCF analyzer
    logging.basicConfig(level=logging.INFO)

    analyzer = DCFAnalyzer()
    financials = create_sample_financials()

    print("=" * 60)
    print("DCF Valuation Test - 삼성전자")
    print("=" * 60)

    result = analyzer.run_dcf(financials)

    print(f"\nWACC: {result.wacc:.2%}")
    print(f"Enterprise Value: {result.enterprise_value / 1e12:,.1f}조원")
    print(f"Equity Value: {result.equity_value / 1e12:,.1f}조원")
    print(f"Per Share Value: {result.per_share_value:,.0f}원")
    print(f"Current Price: {result.current_price:,.0f}원")
    print(f"Upside: {result.upside_potential:.1f}%")

    print("\n" + "=" * 60)
    print("Sensitivity Analysis")
    print("=" * 60)

    sensitivity = analyzer.sensitivity_analysis(financials)
    print(sensitivity.round(0).astype(int))
