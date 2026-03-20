"""
K-IFRS ↔ US GAAP Mapper for Cross-Border Comparison.

Handles accounting standard differences between Korean IFRS and US GAAP
to enable meaningful cross-market company comparisons.

Key Differences Handled:
- R&D capitalization (K-IFRS) vs expensing (US GAAP)
- Development cost treatment
- Financial instrument classification
- Lease accounting nuances
- Revenue recognition timing
"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AccountingStandard(Enum):
    """Supported accounting standards."""
    K_IFRS = "K-IFRS"
    US_GAAP = "US-GAAP"
    IFRS = "IFRS"


@dataclass
class FinancialItem:
    """Financial statement item with GAAP adjustments."""

    name: str
    value: float
    standard: AccountingStandard
    adjusted_value: Optional[float] = None
    adjustment_note: str = ""


# ============================================================================
# Adjustment Factors
# ============================================================================

# R&D capitalization adjustment
# K-IFRS allows capitalizing development costs, US GAAP expenses them
RND_CAPITALIZATION_ADJUSTMENT = {
    "description": "R&D Capitalization Adjustment",
    "k_ifrs_to_us_gaap": {
        # Reduce assets by capitalized R&D
        # Reduce equity by same amount
        # Increase R&D expense (reduce operating income)
        "asset_reduction_rate": 1.0,  # Remove 100% of capitalized R&D
        "income_impact": "expense_capitalized_amount",
    },
    "us_gaap_to_k_ifrs": {
        # Would need to estimate capitalizable portion
        "capitalization_rate": 0.4,  # Estimate 40% of R&D could be capitalized
    },
}

# Goodwill impairment testing differences
GOODWILL_ADJUSTMENT = {
    "description": "Goodwill Testing Frequency",
    "note": "K-IFRS tests annually or when trigger, US GAAP similar but different CGU definition",
}

# Operating lease adjustments (mostly converged now with IFRS 16 / ASC 842)
LEASE_ADJUSTMENT = {
    "description": "Lease Accounting",
    "note": "Largely converged since 2019, minor differences in transition",
}


class GAAPMapper:
    """
    Mapper for converting financials between K-IFRS and US GAAP.

    Enables apples-to-apples comparison of Korean and US companies.
    """

    def __init__(self):
        """Initialize GAAP Mapper."""
        logger.info("GAAP Mapper initialized")

    def normalize_financials(
        self,
        financials: Dict[str, float],
        source_standard: AccountingStandard,
        target_standard: AccountingStandard,
        company_info: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Normalize financials from source to target accounting standard.

        Args:
            financials: Dictionary of financial items
            source_standard: Source accounting standard
            target_standard: Target accounting standard
            company_info: Additional company info (sector, etc.)

        Returns:
            Normalized financials with adjustments
        """
        if source_standard == target_standard:
            return {"financials": financials, "adjustments": [], "normalized": True}

        adjustments = []
        normalized = financials.copy()

        # K-IFRS to US GAAP adjustments
        if source_standard == AccountingStandard.K_IFRS and target_standard == AccountingStandard.US_GAAP:
            normalized, adj = self._adjust_k_ifrs_to_us_gaap(financials, company_info)
            adjustments.extend(adj)

        # US GAAP to K-IFRS adjustments
        elif source_standard == AccountingStandard.US_GAAP and target_standard == AccountingStandard.K_IFRS:
            normalized, adj = self._adjust_us_gaap_to_k_ifrs(financials, company_info)
            adjustments.extend(adj)

        return {
            "original_standard": source_standard.value,
            "target_standard": target_standard.value,
            "original_financials": financials,
            "normalized_financials": normalized,
            "adjustments": adjustments,
            "normalized": True,
        }

    def _adjust_k_ifrs_to_us_gaap(
        self,
        financials: Dict[str, float],
        company_info: Dict[str, Any] = None,
    ) -> tuple:
        """
        Adjust K-IFRS financials to US GAAP basis.

        Key adjustments:
        1. Expense capitalized development costs
        2. Adjust for any revaluation reserves
        """
        adjusted = financials.copy()
        adjustments = []

        # 1. R&D Capitalization Adjustment
        capitalized_rnd = financials.get("capitalized_development_costs", 0)
        rnd_amortization = financials.get("rnd_amortization", 0)

        if capitalized_rnd > 0:
            # Remove from intangible assets
            adjusted["intangible_assets"] = adjusted.get("intangible_assets", 0) - capitalized_rnd

            # Add back to R&D expense (reduce operating income)
            # Net impact = capitalized amount - amortization already taken
            net_rnd_adjustment = capitalized_rnd - rnd_amortization
            adjusted["operating_income"] = adjusted.get("operating_income", 0) - net_rnd_adjustment
            adjusted["rnd_expense"] = adjusted.get("rnd_expense", 0) + net_rnd_adjustment

            # Reduce equity (through retained earnings)
            tax_rate = company_info.get("tax_rate", 0.22) if company_info else 0.22
            after_tax_impact = net_rnd_adjustment * (1 - tax_rate)
            adjusted["total_equity"] = adjusted.get("total_equity", 0) - after_tax_impact

            adjustments.append({
                "type": "R&D Capitalization",
                "description": "Expensed capitalized development costs",
                "impact_operating_income": -net_rnd_adjustment,
                "impact_assets": -capitalized_rnd,
                "impact_equity": -after_tax_impact,
            })

        # 2. Revaluation Reserve Adjustment
        revaluation_reserve = financials.get("revaluation_reserve", 0)

        if revaluation_reserve > 0:
            # US GAAP doesn't allow upward revaluation
            adjusted["ppe_net"] = adjusted.get("ppe_net", 0) - revaluation_reserve
            adjusted["total_equity"] = adjusted.get("total_equity", 0) - revaluation_reserve

            adjustments.append({
                "type": "Revaluation Reserve",
                "description": "Removed upward revaluation of assets",
                "impact_assets": -revaluation_reserve,
                "impact_equity": -revaluation_reserve,
            })

        return adjusted, adjustments

    def _adjust_us_gaap_to_k_ifrs(
        self,
        financials: Dict[str, float],
        company_info: Dict[str, Any] = None,
    ) -> tuple:
        """
        Adjust US GAAP financials to K-IFRS basis.

        Key adjustments:
        1. Estimate capitalizable R&D
        """
        adjusted = financials.copy()
        adjustments = []

        # Estimate capitalizable R&D (simplified)
        rnd_expense = financials.get("rnd_expense", 0)
        capitalization_rate = 0.4  # Assume 40% could be capitalized under K-IFRS

        if rnd_expense > 0:
            capitalizable_amount = rnd_expense * capitalization_rate

            # Add to intangible assets
            adjusted["intangible_assets"] = adjusted.get("intangible_assets", 0) + capitalizable_amount

            # Reduce R&D expense (increase operating income)
            adjusted["operating_income"] = adjusted.get("operating_income", 0) + capitalizable_amount
            adjusted["rnd_expense"] = rnd_expense - capitalizable_amount

            # Increase equity
            tax_rate = company_info.get("tax_rate", 0.21) if company_info else 0.21
            after_tax_impact = capitalizable_amount * (1 - tax_rate)
            adjusted["total_equity"] = adjusted.get("total_equity", 0) + after_tax_impact

            adjustments.append({
                "type": "R&D Capitalization (Estimated)",
                "description": f"Estimated {capitalization_rate:.0%} of R&D as capitalizable",
                "impact_operating_income": capitalizable_amount,
                "impact_assets": capitalizable_amount,
                "impact_equity": after_tax_impact,
                "note": "This is an estimate - actual capitalization depends on project specifics",
            })

        return adjusted, adjustments

    def calculate_adjusted_multiples(
        self,
        financials: Dict[str, float],
        market_cap: float,
        source_standard: AccountingStandard,
        target_standard: AccountingStandard = AccountingStandard.US_GAAP,
    ) -> Dict[str, Any]:
        """
        Calculate valuation multiples on normalized basis.

        Args:
            financials: Company financials
            market_cap: Market capitalization
            source_standard: Source accounting standard
            target_standard: Target standard for normalization

        Returns:
            Original and adjusted multiples
        """
        # Normalize financials
        result = self.normalize_financials(financials, source_standard, target_standard)
        normalized = result["normalized_financials"]

        # Calculate multiples
        def safe_divide(num, denom):
            return num / denom if denom and denom != 0 else 0

        original_multiples = {
            "pe_ratio": safe_divide(market_cap, financials.get("net_income", 0)),
            "pb_ratio": safe_divide(market_cap, financials.get("total_equity", 0)),
            "ev_ebitda": safe_divide(
                market_cap + financials.get("total_debt", 0) - financials.get("cash", 0),
                financials.get("ebitda", 0)
            ),
        }

        adjusted_multiples = {
            "pe_ratio": safe_divide(market_cap, normalized.get("net_income", financials.get("net_income", 0))),
            "pb_ratio": safe_divide(market_cap, normalized.get("total_equity", 0)),
            "ev_ebitda": safe_divide(
                market_cap + normalized.get("total_debt", financials.get("total_debt", 0)) -
                normalized.get("cash", financials.get("cash", 0)),
                normalized.get("ebitda", financials.get("ebitda", 0))
            ),
        }

        return {
            "original_multiples": original_multiples,
            "adjusted_multiples": adjusted_multiples,
            "adjustments_applied": result["adjustments"],
            "source_standard": source_standard.value,
            "target_standard": target_standard.value,
        }

    def get_adjustment_summary(
        self,
        source_standard: AccountingStandard,
        target_standard: AccountingStandard,
    ) -> Dict[str, str]:
        """
        Get summary of adjustments needed between standards.

        Args:
            source_standard: Source accounting standard
            target_standard: Target accounting standard

        Returns:
            Dictionary describing adjustments
        """
        if source_standard == target_standard:
            return {"summary": "No adjustment needed - same standard"}

        if source_standard == AccountingStandard.K_IFRS and target_standard == AccountingStandard.US_GAAP:
            return {
                "summary": "K-IFRS to US GAAP Adjustments",
                "key_differences": [
                    "R&D: K-IFRS allows capitalizing development costs, US GAAP expenses all R&D",
                    "Revaluation: K-IFRS allows upward revaluation of assets, US GAAP does not",
                    "Inventory: Some LIFO usage in US GAAP (not allowed in IFRS)",
                ],
                "typical_impact": {
                    "assets": "Lower (remove capitalized R&D, revaluation)",
                    "equity": "Lower (related adjustments)",
                    "operating_income": "Lower (R&D expensed)",
                    "multiples": "P/E typically higher after adjustment",
                },
            }

        elif source_standard == AccountingStandard.US_GAAP and target_standard == AccountingStandard.K_IFRS:
            return {
                "summary": "US GAAP to K-IFRS Adjustments",
                "key_differences": [
                    "R&D: Estimate portion that could be capitalized",
                    "Some US companies use LIFO (needs conversion to FIFO)",
                ],
                "typical_impact": {
                    "assets": "Higher (estimated capitalizable R&D)",
                    "equity": "Higher (related adjustments)",
                    "operating_income": "Higher (capitalized R&D)",
                    "multiples": "P/E typically lower after adjustment",
                },
            }

        return {"summary": "Adjustment path not implemented"}


if __name__ == "__main__":
    # Test GAAP Mapper
    logging.basicConfig(level=logging.INFO)

    mapper = GAAPMapper()

    # Sample Korean company financials (K-IFRS)
    kr_financials = {
        "revenue": 300_000_000_000_000,
        "operating_income": 45_000_000_000_000,
        "net_income": 35_000_000_000_000,
        "ebitda": 80_000_000_000_000,
        "total_equity": 350_000_000_000_000,
        "total_debt": 30_000_000_000_000,
        "cash": 100_000_000_000_000,
        "intangible_assets": 20_000_000_000_000,
        "ppe_net": 150_000_000_000_000,
        "capitalized_development_costs": 5_000_000_000_000,  # 5조원 자본화된 R&D
        "rnd_amortization": 1_000_000_000_000,  # 1조원 상각
        "rnd_expense": 15_000_000_000_000,  # 15조원 R&D 비용
    }

    print("=" * 60)
    print("K-IFRS to US GAAP Normalization")
    print("=" * 60)

    result = mapper.normalize_financials(
        kr_financials,
        AccountingStandard.K_IFRS,
        AccountingStandard.US_GAAP,
    )

    print("\nAdjustments Applied:")
    for adj in result["adjustments"]:
        print(f"  - {adj['type']}: {adj['description']}")
        if "impact_operating_income" in adj:
            print(f"    Operating Income Impact: {adj['impact_operating_income']/1e12:,.1f}조원")

    print("\nOriginal vs Normalized (in 조원):")
    for key in ["operating_income", "total_equity", "intangible_assets"]:
        orig = kr_financials.get(key, 0) / 1e12
        norm = result["normalized_financials"].get(key, 0) / 1e12
        print(f"  {key}: {orig:,.1f} → {norm:,.1f}")

    # Calculate adjusted multiples
    print("\n" + "=" * 60)
    print("Adjusted Multiples")
    print("=" * 60)

    multiples = mapper.calculate_adjusted_multiples(
        kr_financials,
        market_cap=400_000_000_000_000,
        source_standard=AccountingStandard.K_IFRS,
    )

    print("\nOriginal Multiples (K-IFRS):")
    for k, v in multiples["original_multiples"].items():
        print(f"  {k}: {v:.2f}")

    print("\nAdjusted Multiples (US GAAP basis):")
    for k, v in multiples["adjusted_multiples"].items():
        print(f"  {k}: {v:.2f}")
