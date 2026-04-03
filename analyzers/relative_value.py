"""
Relative Value Analyzer for peer comparison.

Provides tools for relative valuation including:
- Multiple comparison (P/E, P/B, EV/EBITDA, etc.)
- Peer group analysis
- Cross-market comparison (Korea vs US)
- Valuation percentile ranking

Note: Phase 3 uses hardcoded test values. Real data integration in Phase 5.
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CompanyMultiples:
    """Company valuation multiples."""

    stock_code: str
    company_name: str
    country: str = "KR"
    sector: str = ""
    industry: str = ""

    # Price multiples
    price: float = 0.0
    market_cap: float = 0.0
    pe_ratio: float = 0.0          # Price / EPS
    pb_ratio: float = 0.0          # Price / Book Value
    ps_ratio: float = 0.0          # Price / Sales

    # Enterprise multiples
    ev: float = 0.0                 # Enterprise Value
    ev_ebitda: float = 0.0         # EV / EBITDA
    ev_ebit: float = 0.0           # EV / EBIT
    ev_sales: float = 0.0          # EV / Sales

    # Profitability metrics
    roe: float = 0.0               # Return on Equity
    roa: float = 0.0               # Return on Assets
    roic: float = 0.0              # Return on Invested Capital
    gross_margin: float = 0.0
    operating_margin: float = 0.0
    net_margin: float = 0.0

    # Growth metrics
    revenue_growth: float = 0.0
    earnings_growth: float = 0.0

    # Dividend
    dividend_yield: float = 0.0
    payout_ratio: float = 0.0


@dataclass
class PeerComparisonResult:
    """Result of peer comparison analysis."""

    target: CompanyMultiples
    peers: List[CompanyMultiples]
    peer_avg: Dict[str, float]
    peer_median: Dict[str, float]
    percentile_rank: Dict[str, float]
    implied_values: Dict[str, float]
    recommendation: str = ""


class RelativeValueAnalyzer:
    """
    Relative Valuation Engine.

    Compares companies using multiples:
    - P/E, P/B, P/S (Price multiples)
    - EV/EBITDA, EV/EBIT, EV/Sales (Enterprise multiples)
    - ROE, ROIC (Profitability)
    """

    # Key multiples for comparison
    PRICE_MULTIPLES = ["pe_ratio", "pb_ratio", "ps_ratio"]
    EV_MULTIPLES = ["ev_ebitda", "ev_ebit", "ev_sales"]
    PROFITABILITY_METRICS = ["roe", "roa", "roic", "operating_margin"]

    # Multiple names for display
    MULTIPLE_NAMES = {
        "pe_ratio": "P/E",
        "pb_ratio": "P/B",
        "ps_ratio": "P/S",
        "ev_ebitda": "EV/EBITDA",
        "ev_ebit": "EV/EBIT",
        "ev_sales": "EV/Sales",
        "roe": "ROE",
        "roa": "ROA",
        "roic": "ROIC",
        "operating_margin": "Operating Margin",
        "dividend_yield": "Dividend Yield",
    }

    def __init__(self):
        """Initialize Relative Value Analyzer."""
        logger.info("Relative Value Analyzer initialized")

    def compare_multiples(
        self,
        target: CompanyMultiples,
        peers: List[CompanyMultiples],
        multiples: List[str] = None,
    ) -> PeerComparisonResult:
        """
        Compare target company with peers across multiples.

        Args:
            target: Target company multiples
            peers: List of peer company multiples
            multiples: Specific multiples to compare (default: all)

        Returns:
            PeerComparisonResult with analysis
        """
        if multiples is None:
            multiples = self.PRICE_MULTIPLES + self.EV_MULTIPLES

        peer_data = {m: [] for m in multiples}
        target_data = {}

        # Collect peer data
        for peer in peers:
            for m in multiples:
                value = getattr(peer, m, 0)
                if value is not None and value > 0:  # Only include positive values
                    peer_data[m].append(value)

        # Get target data
        for m in multiples:
            target_data[m] = getattr(target, m, 0)

        # Calculate peer statistics
        peer_avg = {}
        peer_median = {}
        percentile_rank = {}
        implied_values = {}

        for m in multiples:
            values = peer_data[m]
            if values:
                peer_avg[m] = np.mean(values)
                peer_median[m] = np.median(values)

                # Calculate percentile rank of target
                if target_data[m] > 0:
                    percentile_rank[m] = (
                        sum(1 for v in values if v < target_data[m]) / len(values) * 100
                    )
                else:
                    percentile_rank[m] = None

                # Calculate implied value based on peer median
                implied_values[m] = self._calculate_implied_value(
                    target, m, peer_median[m]
                )

        # Generate recommendation
        recommendation = self._generate_recommendation(
            target_data, peer_avg, peer_median, percentile_rank
        )

        return PeerComparisonResult(
            target=target,
            peers=peers,
            peer_avg=peer_avg,
            peer_median=peer_median,
            percentile_rank=percentile_rank,
            implied_values=implied_values,
            recommendation=recommendation,
        )

    def _calculate_implied_value(
        self,
        target: CompanyMultiples,
        multiple: str,
        peer_multiple: float,
    ) -> float:
        """
        Calculate implied stock price based on peer multiple.

        Args:
            target: Target company
            multiple: Multiple name
            peer_multiple: Peer average/median multiple

        Returns:
            Implied stock price
        """
        if peer_multiple <= 0:
            return 0.0

        current_price = target.price
        current_multiple = getattr(target, multiple, 0)

        if current_multiple <= 0:
            return 0.0

        # Implied price = Current Price × (Peer Multiple / Current Multiple)
        implied_price = current_price * (peer_multiple / current_multiple)

        return implied_price

    def _generate_recommendation(
        self,
        target_data: Dict[str, float],
        peer_avg: Dict[str, float],
        peer_median: Dict[str, float],
        percentile_rank: Dict[str, float],
    ) -> str:
        """Generate valuation recommendation based on comparison."""
        undervalued_count = 0
        overvalued_count = 0

        for m in self.PRICE_MULTIPLES:
            if m in percentile_rank and percentile_rank[m] is not None:
                if percentile_rank[m] < 30:
                    undervalued_count += 1
                elif percentile_rank[m] > 70:
                    overvalued_count += 1

        if undervalued_count >= 2:
            return "UNDERVALUED - Trading at discount to peers"
        elif overvalued_count >= 2:
            return "OVERVALUED - Trading at premium to peers"
        else:
            return "FAIRLY VALUED - In line with peers"

    def create_comparison_table(
        self,
        result: PeerComparisonResult,
        multiples: List[str] = None,
    ) -> pd.DataFrame:
        """
        Create comparison table for display.

        Args:
            result: PeerComparisonResult
            multiples: Multiples to include

        Returns:
            DataFrame with comparison data
        """
        if multiples is None:
            multiples = self.PRICE_MULTIPLES + self.EV_MULTIPLES[:2]

        data = []

        # Target row
        target_row = {"Company": result.target.company_name, "Type": "Target"}
        for m in multiples:
            target_row[self.MULTIPLE_NAMES.get(m, m)] = getattr(result.target, m, 0)
        data.append(target_row)

        # Peer rows
        for peer in result.peers:
            peer_row = {"Company": peer.company_name, "Type": "Peer"}
            for m in multiples:
                peer_row[self.MULTIPLE_NAMES.get(m, m)] = getattr(peer, m, 0)
            data.append(peer_row)

        # Average row
        avg_row = {"Company": "Peer Average", "Type": "Avg"}
        for m in multiples:
            avg_row[self.MULTIPLE_NAMES.get(m, m)] = result.peer_avg.get(m, 0)
        data.append(avg_row)

        # Median row
        median_row = {"Company": "Peer Median", "Type": "Median"}
        for m in multiples:
            median_row[self.MULTIPLE_NAMES.get(m, m)] = result.peer_median.get(m, 0)
        data.append(median_row)

        df = pd.DataFrame(data)
        return df

    def cross_market_comparison(
        self,
        kr_company: CompanyMultiples,
        us_company: CompanyMultiples,
        discount_rate: float = 0.20,  # Korea discount
    ) -> Dict[str, Any]:
        """
        Compare Korean company with US peer, applying Korea discount.

        Args:
            kr_company: Korean company multiples
            us_company: US company multiples
            discount_rate: Korea market discount (default 20%)

        Returns:
            Comparison analysis
        """
        comparison = {}

        for m in self.PRICE_MULTIPLES + self.EV_MULTIPLES[:2]:
            kr_value = getattr(kr_company, m, 0)
            us_value = getattr(us_company, m, 0)

            if kr_value > 0 and us_value > 0:
                # Raw discount
                raw_discount = (us_value - kr_value) / us_value * 100

                # Adjusted for Korea discount
                expected_kr = us_value * (1 - discount_rate)
                adjusted_discount = (expected_kr - kr_value) / expected_kr * 100

                comparison[m] = {
                    "kr_value": kr_value,
                    "us_value": us_value,
                    "raw_discount_pct": raw_discount,
                    "expected_kr_value": expected_kr,
                    "adjusted_discount_pct": adjusted_discount,
                    "valuation": "Cheap" if adjusted_discount > 10 else (
                        "Expensive" if adjusted_discount < -10 else "Fair"
                    ),
                }

        return {
            "kr_company": kr_company.company_name,
            "us_company": us_company.company_name,
            "korea_discount_applied": discount_rate,
            "comparisons": comparison,
        }

    def calculate_target_price(
        self,
        target: CompanyMultiples,
        peer_median: Dict[str, float],
        weights: Dict[str, float] = None,
    ) -> Dict[str, Any]:
        """
        Calculate weighted target price based on multiple implied values.

        Args:
            target: Target company
            peer_median: Peer median multiples
            weights: Weights for each multiple (default: equal)

        Returns:
            Target price analysis
        """
        if weights is None:
            weights = {
                "pe_ratio": 0.35,
                "pb_ratio": 0.15,
                "ev_ebitda": 0.35,
                "ev_sales": 0.15,
            }

        implied_prices = {}
        weighted_sum = 0.0
        total_weight = 0.0

        for m, weight in weights.items():
            implied = self._calculate_implied_value(target, m, peer_median.get(m, 0))
            if implied > 0:
                implied_prices[m] = implied
                weighted_sum += implied * weight
                total_weight += weight

        if total_weight > 0:
            weighted_target = weighted_sum / total_weight
        else:
            weighted_target = target.price

        upside = ((weighted_target / target.price) - 1) * 100 if target.price > 0 else 0

        return {
            "current_price": target.price,
            "implied_prices": implied_prices,
            "weighted_target_price": weighted_target,
            "upside_potential_pct": upside,
            "weights_used": weights,
        }


# ============================================================================
# Sample Data for Testing
# ============================================================================

def create_sample_peer_group() -> List[CompanyMultiples]:
    """Create sample semiconductor peer group for testing."""
    return [
        CompanyMultiples(
            stock_code="000660",
            company_name="SK하이닉스",
            country="KR",
            sector="Technology",
            industry="Semiconductors",
            price=180000,
            market_cap=131_000_000_000_000,
            pe_ratio=8.5,
            pb_ratio=1.8,
            ps_ratio=2.1,
            ev=145_000_000_000_000,
            ev_ebitda=4.5,
            ev_ebit=7.0,
            ev_sales=2.3,
            roe=22.0,
            operating_margin=25.0,
        ),
        CompanyMultiples(
            stock_code="MU",
            company_name="Micron Technology",
            country="US",
            sector="Technology",
            industry="Semiconductors",
            price=95,
            market_cap=105_000_000_000,  # USD
            pe_ratio=12.0,
            pb_ratio=2.2,
            ps_ratio=3.5,
            ev=115_000_000_000,
            ev_ebitda=6.0,
            ev_ebit=9.5,
            ev_sales=3.8,
            roe=18.0,
            operating_margin=22.0,
        ),
        CompanyMultiples(
            stock_code="INTC",
            company_name="Intel Corporation",
            country="US",
            sector="Technology",
            industry="Semiconductors",
            price=45,
            market_cap=190_000_000_000,
            pe_ratio=25.0,
            pb_ratio=1.5,
            ps_ratio=3.2,
            ev=210_000_000_000,
            ev_ebitda=8.0,
            ev_ebit=15.0,
            ev_sales=3.5,
            roe=8.0,
            operating_margin=12.0,
        ),
    ]


def create_sample_target() -> CompanyMultiples:
    """Create sample target company (삼성전자) for testing."""
    return CompanyMultiples(
        stock_code="005930",
        company_name="삼성전자",
        country="KR",
        sector="Technology",
        industry="Semiconductors",
        price=67000,
        market_cap=400_000_000_000_000,
        pe_ratio=11.5,
        pb_ratio=1.15,
        ps_ratio=1.35,
        ev=330_000_000_000_000,
        ev_ebitda=4.2,
        ev_ebit=7.5,
        ev_sales=1.1,
        roe=10.0,
        operating_margin=15.0,
    )


if __name__ == "__main__":
    # Test the relative value analyzer
    logging.basicConfig(level=logging.INFO)

    analyzer = RelativeValueAnalyzer()

    target = create_sample_target()
    peers = create_sample_peer_group()

    print("=" * 60)
    print("Relative Value Analysis - 삼성전자 vs Peers")
    print("=" * 60)

    result = analyzer.compare_multiples(target, peers)

    print("\nPeer Comparison:")
    table = analyzer.create_comparison_table(result)
    print(table.to_string(index=False))

    print(f"\nRecommendation: {result.recommendation}")

    print("\nPercentile Rankings:")
    for m, pct in result.percentile_rank.items():
        if pct is not None:
            name = analyzer.MULTIPLE_NAMES.get(m, m)
            print(f"  {name}: {pct:.0f}th percentile")

    print("\nImplied Stock Prices:")
    for m, price in result.implied_values.items():
        if price > 0:
            name = analyzer.MULTIPLE_NAMES.get(m, m)
            print(f"  Based on {name}: {price:,.0f}원")

    # Target price calculation
    print("\n" + "=" * 60)
    print("Target Price Analysis")
    print("=" * 60)

    target_analysis = analyzer.calculate_target_price(target, result.peer_median)
    print(f"Current Price: {target_analysis['current_price']:,}원")
    print(f"Weighted Target: {target_analysis['weighted_target_price']:,.0f}원")
    print(f"Upside Potential: {target_analysis['upside_potential_pct']:.1f}%")
