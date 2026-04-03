"""
Valuation MCP Server - DCF and Relative Value Analysis.

Provides tools for equity valuation:
- DCF (Discounted Cash Flow) analysis
- WACC calculation
- Sensitivity analysis
- Peer comparison (relative valuation)
- Cross-market comparison (Korea vs US)

Phase 5: Integrated with ECOS for real risk-free rate data.

Run standalone: python -m mcp_servers.servers.valuation_server
"""
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from fastmcp import FastMCP

from mcp_servers.core.cache_manager import CacheManager, get_cache
from mcp_servers.core.rate_limiter import RateLimiter, get_limiter

from analyzers.dcf_analyzer import (
    DCFAnalyzer,
    CompanyFinancials,
    DCFResult,
    TEST_VALUES,
)
from analyzers.relative_value import (
    RelativeValueAnalyzer,
    CompanyMultiples,
)
from utils.gaap_mapper import GAAPMapper, AccountingStandard

logger = logging.getLogger(__name__)

# Default market assumptions (used when ECOS real-time data unavailable)
MARKET_DATA_DEFAULTS = {
    "risk_free_rate": TEST_VALUES["risk_free_rate"],  # 3.5% (한국 국고채 3년 기준)
    "market_risk_premium": TEST_VALUES["market_risk_premium"],  # 6% (한국 시장 평균)
}


class ValuationServer:
    """Valuation MCP Server for DCF and relative value analysis."""

    def __init__(
        self,
        cache: CacheManager = None,
        limiter: RateLimiter = None,
    ):
        """
        Initialize Valuation server.

        Args:
            cache: Cache manager instance
            limiter: Rate limiter instance
        """
        self._cache = cache or get_cache()
        self._limiter = limiter or get_limiter()

        # Initialize ECOS client for real market data (Phase 5)
        self._ecos = None
        self._real_risk_free_rate = None
        self._data_source = "test_values"  # Will be "ecos" if real data available

        try:
            from PublicDataReader import Ecos
            api_key = os.getenv("BOK_ECOS_API_KEY", "")
            if api_key:
                self._ecos = Ecos(api_key)
                # Try to fetch real risk-free rate
                self._real_risk_free_rate = self._fetch_risk_free_rate()
                if self._real_risk_free_rate:
                    self._data_source = "ecos"
                    logger.info(f"Using real risk-free rate from ECOS: {self._real_risk_free_rate:.2%}")
        except ImportError:
            logger.warning("PublicDataReader not installed. Using test values.")
        except Exception as e:
            logger.warning(f"ECOS initialization failed: {e}. Using test values.")

        # Initialize analyzers with real or test data
        risk_free_rate = self._real_risk_free_rate or MARKET_DATA_DEFAULTS["risk_free_rate"]
        self._dcf = DCFAnalyzer(risk_free_rate=risk_free_rate)
        self._relative = RelativeValueAnalyzer()
        self._gaap_mapper = GAAPMapper()

        # Create FastMCP server
        self.mcp = FastMCP("valuation")
        self._register_tools()

        logger.info(f"Valuation MCP Server initialized (data source: {self._data_source})")

    def _fetch_risk_free_rate(self) -> Optional[float]:
        """Fetch current risk-free rate from ECOS (Bank of Korea base rate)."""
        if not self._ecos:
            return None

        try:
            self._limiter.acquire("ecos")

            # Fetch base rate (722Y001, item 0101000)
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

            df = self._ecos.get_statistic_search(
                "722Y001",      # Base rate stat code
                "D",            # Daily frequency
                start_date,
                end_date,
                "0101000",      # Item code
            )

            if df is not None and not df.empty:
                # Get the latest value
                latest_value = df.iloc[-1].get("값", df.iloc[-1].get("DATA_VALUE"))
                if latest_value:
                    rate = float(latest_value) / 100.0  # Convert from percentage
                    logger.info(f"Fetched base rate from ECOS: {rate:.2%}")
                    return rate

        except Exception as e:
            logger.warning(f"Failed to fetch risk-free rate from ECOS: {e}")

        return None

    def _register_tools(self) -> None:
        """Register MCP tools."""

        # ====================================================================
        # DCF Tools
        # ====================================================================

        @self.mcp.tool()
        def val_calculate_wacc(
            market_cap: float,
            total_debt: float,
            beta: float = 1.0,
            cost_of_debt: float = 0.05,
            tax_rate: float = 0.22,
        ) -> Dict[str, Any]:
            """
            WACC (가중평균자본비용) 계산

            Args:
                market_cap: 시가총액 (원)
                total_debt: 총부채 (원)
                beta: 베타 (기본값: 1.0)
                cost_of_debt: 부채비용 (기본값: 5%)
                tax_rate: 법인세율 (기본값: 22%)

            Returns:
                WACC 및 구성요소
            """
            # Input validation
            if market_cap <= 0:
                return {"error": True, "message": "market_cap must be positive"}
            if total_debt < 0:
                return {"error": True, "message": "total_debt cannot be negative"}
            if beta <= 0:
                return {"error": True, "message": "beta must be positive"}
            if not (0 <= tax_rate <= 1):
                return {"error": True, "message": "tax_rate must be between 0 and 1"}
            if not (0 <= cost_of_debt <= 1):
                return {"error": True, "message": "cost_of_debt must be between 0 and 1"}

            return self.calculate_wacc(market_cap, total_debt, beta, cost_of_debt, tax_rate)

        @self.mcp.tool()
        def val_dcf_valuation(
            stock_code: str,
            company_name: str,
            revenue: float,
            ebit: float,
            ebitda: float,
            net_income: float,
            total_debt: float,
            cash: float,
            total_equity: float,
            shares_outstanding: float,
            market_cap: float,
            capex: float,
            depreciation: float,
            change_in_nwc: float = 0,
            beta: float = 1.0,
            cost_of_debt: float = 0.05,
            tax_rate: float = 0.22,
        ) -> Dict[str, Any]:
            """
            DCF 밸류에이션 수행

            Args:
                stock_code: 종목코드 (예: "005930")
                company_name: 회사명
                revenue: 매출액 (원)
                ebit: 영업이익 (원)
                ebitda: EBITDA (원)
                net_income: 순이익 (원)
                total_debt: 총부채 (원)
                cash: 현금 (원)
                total_equity: 자본총계 (원)
                shares_outstanding: 발행주식수
                market_cap: 시가총액 (원)
                capex: 설비투자 (원)
                depreciation: 감가상각비 (원)
                change_in_nwc: 운전자본 변동 (원)
                beta: 베타
                cost_of_debt: 부채비용
                tax_rate: 법인세율

            Returns:
                DCF 밸류에이션 결과 (적정주가, 상승여력 등)
            """
            # Input validation
            if shares_outstanding <= 0:
                return {"error": True, "message": "shares_outstanding must be positive"}
            if market_cap <= 0:
                return {"error": True, "message": "market_cap must be positive"}
            if beta <= 0:
                return {"error": True, "message": "beta must be positive"}
            if not (0 <= tax_rate <= 1):
                return {"error": True, "message": "tax_rate must be between 0 and 1"}
            if not (0 <= cost_of_debt <= 1):
                return {"error": True, "message": "cost_of_debt must be between 0 and 1"}

            financials = CompanyFinancials(
                stock_code=stock_code,
                company_name=company_name,
                revenue=revenue,
                ebit=ebit,
                ebitda=ebitda,
                net_income=net_income,
                total_debt=total_debt,
                cash=cash,
                total_equity=total_equity,
                shares_outstanding=shares_outstanding,
                market_cap=market_cap,
                capex=capex,
                depreciation=depreciation,
                change_in_nwc=change_in_nwc,
                beta=beta,
                cost_of_debt=cost_of_debt,
                tax_rate=tax_rate,
            )
            return self.run_dcf(financials)

        @self.mcp.tool()
        def val_dcf_sample(stock_code: str = "005930") -> Dict[str, Any]:
            """
            DART 재무제표 기반 자동 DCF 밸류에이션

            Args:
                stock_code: 종목코드 (예: "005930" 삼성전자)

            Returns:
                DCF 밸류에이션 결과 (DART 실제 재무데이터 사용)
            """
            return self.run_dcf_from_dart(stock_code)

        @self.mcp.tool()
        def val_sensitivity_analysis(
            stock_code: str,
            company_name: str,
            ebit: float,
            ebitda: float,
            total_debt: float,
            cash: float,
            shares_outstanding: float,
            market_cap: float,
            capex: float,
            depreciation: float,
            wacc_min: float = 0.07,
            wacc_max: float = 0.13,
            growth_min: float = 0.01,
            growth_max: float = 0.04,
        ) -> Dict[str, Any]:
            """
            DCF 민감도 분석 (WACC × 영구성장률)

            Args:
                stock_code: 종목코드
                company_name: 회사명
                ebit: 영업이익 (원)
                ebitda: EBITDA (원)
                total_debt: 총부채 (원)
                cash: 현금 (원)
                shares_outstanding: 발행주식수
                market_cap: 시가총액 (원)
                capex: 설비투자 (원)
                depreciation: 감가상각비 (원)
                wacc_min: WACC 최소값 (기본: 7%)
                wacc_max: WACC 최대값 (기본: 13%)
                growth_min: 영구성장률 최소값 (기본: 1%)
                growth_max: 영구성장률 최대값 (기본: 4%)

            Returns:
                민감도 분석 매트릭스
            """
            financials = CompanyFinancials(
                stock_code=stock_code,
                company_name=company_name,
                ebit=ebit,
                ebitda=ebitda,
                total_debt=total_debt,
                cash=cash,
                shares_outstanding=shares_outstanding,
                market_cap=market_cap,
                capex=capex,
                depreciation=depreciation,
            )
            return self.sensitivity_analysis(
                financials, wacc_min, wacc_max, growth_min, growth_max
            )

        # ====================================================================
        # Relative Value Tools
        # ====================================================================

        @self.mcp.tool()
        def val_peer_comparison(
            target_code: str,
            target_name: str,
            target_price: float,
            target_pe: float,
            target_pb: float,
            target_ev_ebitda: float,
            peer_data: List[Dict[str, Any]],
        ) -> Dict[str, Any]:
            """
            피어 그룹 비교 분석

            Args:
                target_code: 대상 종목코드
                target_name: 대상 회사명
                target_price: 현재 주가
                target_pe: P/E 비율
                target_pb: P/B 비율
                target_ev_ebitda: EV/EBITDA 비율
                peer_data: 피어 데이터 리스트 [{"code": "...", "name": "...", "pe": ..., "pb": ..., "ev_ebitda": ...}]

            Returns:
                피어 비교 분석 결과
            """
            return self.peer_comparison(
                target_code, target_name, target_price,
                target_pe, target_pb, target_ev_ebitda, peer_data
            )

        @self.mcp.tool()
        def val_peer_comparison_sample() -> Dict[str, Any]:
            """
            피어 비교 분석 예시 — val_peer_comparison 도구 사용법 안내

            Returns:
                val_peer_comparison 사용 가이드
            """
            return {
                "success": True,
                "message": "val_peer_comparison 도구를 직접 사용하세요. 샘플 데이터는 제공하지 않습니다.",
                "usage": {
                    "tool": "val_peer_comparison",
                    "required_params": {
                        "target_code": "종목코드 (예: 005930)",
                        "target_name": "기업명",
                        "target_price": "현재 주가",
                        "target_pe": "PER",
                        "target_pb": "PBR",
                        "target_ev_ebitda": "EV/EBITDA",
                        "peer_data": "[{code, name, pe, pb, ev_ebitda}, ...]",
                    },
                    "data_source": "DART 재무제표(dart_financial_statements) + 주가 데이터(stocks_quote)로 파라미터를 구하세요.",
                },
            }

        @self.mcp.tool()
        def val_cross_market_comparison(
            kr_code: str,
            kr_name: str,
            kr_pe: float,
            kr_pb: float,
            kr_ev_ebitda: float,
            us_code: str,
            us_name: str,
            us_pe: float,
            us_pb: float,
            us_ev_ebitda: float,
            korea_discount: float = 0.20,
        ) -> Dict[str, Any]:
            """
            한국-미국 크로스마켓 비교

            Args:
                kr_code: 한국 종목코드
                kr_name: 한국 회사명
                kr_pe: 한국 P/E
                kr_pb: 한국 P/B
                kr_ev_ebitda: 한국 EV/EBITDA
                us_code: 미국 종목코드
                us_name: 미국 회사명
                us_pe: 미국 P/E
                us_pb: 미국 P/B
                us_ev_ebitda: 미국 EV/EBITDA
                korea_discount: 한국 디스카운트 (기본: 20%)

            Returns:
                크로스마켓 비교 결과
            """
            return self.cross_market_comparison(
                kr_code, kr_name, kr_pe, kr_pb, kr_ev_ebitda,
                us_code, us_name, us_pe, us_pb, us_ev_ebitda, korea_discount
            )

        # ====================================================================
        # GAAP Mapping Tools
        # ====================================================================

        @self.mcp.tool()
        def val_normalize_gaap(
            financials: Dict[str, float],
            source_standard: str = "K-IFRS",
            target_standard: str = "US-GAAP",
        ) -> Dict[str, Any]:
            """
            회계기준 정규화 (K-IFRS ↔ US-GAAP)

            Args:
                financials: 재무데이터 딕셔너리
                source_standard: 원본 회계기준 ("K-IFRS", "US-GAAP")
                target_standard: 목표 회계기준

            Returns:
                정규화된 재무데이터 및 조정 내역
            """
            return self.normalize_gaap(financials, source_standard, target_standard)

        @self.mcp.tool()
        def val_get_market_assumptions() -> Dict[str, Any]:
            """
            현재 사용 중인 시장 가정값 조회

            Returns:
                무위험수익률, ERP, 베타, 세율 등 기본 가정값 및 데이터 소스
            """
            return self.get_market_assumptions()

        @self.mcp.tool()
        def val_refresh_market_data() -> Dict[str, Any]:
            """
            시장 데이터 새로고침 (ECOS에서 최신 기준금리 가져오기)

            Returns:
                업데이트된 시장 데이터
            """
            return self.refresh_market_data()

    # ========================================================================
    # Implementation Methods
    # ========================================================================

    def calculate_wacc(
        self,
        market_cap: float,
        total_debt: float,
        beta: float,
        cost_of_debt: float,
        tax_rate: float,
    ) -> Dict[str, Any]:
        """Calculate WACC."""
        financials = CompanyFinancials(
            stock_code="",
            company_name="",
            market_cap=market_cap,
            total_debt=total_debt,
            beta=beta,
            cost_of_debt=cost_of_debt,
            tax_rate=tax_rate,
        )

        wacc, components = self._dcf.calculate_wacc(financials)

        return {
            "success": True,
            "wacc": wacc,
            "wacc_pct": f"{wacc:.2%}",
            "components": {
                "cost_of_equity": f"{components['cost_of_equity']:.2%}",
                "cost_of_debt_after_tax": f"{components['cost_of_debt_after_tax']:.2%}",
                "weight_equity": f"{components['weight_equity']:.2%}",
                "weight_debt": f"{components['weight_debt']:.2%}",
            },
            "inputs": {
                "risk_free_rate": f"{self._dcf.risk_free_rate:.2%}",
                "market_risk_premium": f"{self._dcf.market_risk_premium:.2%}",
                "beta": beta,
                "cost_of_debt": f"{cost_of_debt:.2%}",
                "tax_rate": f"{tax_rate:.2%}",
            },
        }

    def run_dcf(self, financials: CompanyFinancials) -> Dict[str, Any]:
        """Run DCF valuation."""
        try:
            result = self._dcf.run_dcf(financials)

            return {
                "success": True,
                "stock_code": result.stock_code,
                "company_name": result.company_name,
                "valuation": {
                    "wacc": f"{result.wacc:.2%}",
                    "enterprise_value": result.enterprise_value,
                    "equity_value": result.equity_value,
                    "per_share_value": round(result.per_share_value, 0),
                    "current_price": round(result.current_price, 0),
                    "upside_potential": f"{result.upside_potential:.1f}%",
                },
                "cash_flows": {
                    "projected_fcf": [round(f, 0) for f in result.projected_fcf],
                    "pv_fcf": [round(f, 0) for f in result.pv_fcf],
                    "terminal_value": round(result.terminal_value, 0),
                    "pv_terminal_value": round(result.pv_terminal_value, 0),
                },
                "assumptions": result.assumptions,
            }

        except Exception as e:
            logger.error(f"DCF error: {e}")
            return {"error": True, "message": str(e)}

    def run_dcf_from_dart(self, stock_code: str) -> Dict[str, Any]:
        """Run DCF using real DART financial data."""
        try:
            from mcp_servers.adapters.dart_adapter import DARTAdapter
            dart = DARTAdapter()

            if not dart.is_available:
                return {"error": True, "message": "DART client not initialized. DART_API_KEY를 확인하세요."}

            # Get company info
            info = dart.get_company_info(stock_code)
            company_name = "Unknown"
            if info.get("success"):
                data = info.get("data", {})
                company_name = data.get("corp_name", data.get("stock_name", stock_code))

            # Get financial ratios (includes revenue, net_income, etc.)
            ratios = dart.get_financial_ratios(stock_code)
            if ratios.get("error") or not ratios.get("ratios"):
                return {"error": True, "message": f"DART 재무제표 조회 실패: {ratios.get('message', 'No data')}. val_dcf_valuation으로 직접 입력하세요."}

            r = ratios["ratios"]
            revenue = r.get("revenue", 0)
            operating_income = r.get("operating_income", 0)
            net_income = r.get("net_income", 0)
            total_assets = r.get("total_assets", 0)
            total_equity = r.get("total_equity", 0)
            total_debt = r.get("total_debt", 0)

            if revenue == 0:
                return {"error": True, "message": "DART 재무제표에서 매출액을 찾을 수 없습니다. val_dcf_valuation으로 직접 입력하세요."}

            # Estimate EBIT/EBITDA from operating income
            ebit = operating_income
            ebitda = operating_income * 1.15  # rough estimate (depreciation ~15% of EBIT)
            capex = ebitda * 0.3  # rough capex estimate

            # Build CompanyFinancials
            financials = CompanyFinancials(
                stock_code=stock_code,
                company_name=company_name,
                revenue=revenue,
                ebit=ebit,
                ebitda=ebitda,
                net_income=net_income,
                total_debt=total_debt,
                cash=total_assets * 0.05,  # conservative cash estimate
                shares_outstanding=max(total_equity / 50000, 1000000),  # rough estimate
                market_cap=total_equity * 1.5,  # rough market cap
                capex=capex,
                tax_rate=0.22,
                beta=1.0,
                cost_of_debt=0.04,
            )

            result = self.run_dcf(financials)
            if result.get("success"):
                result["data_source"] = "DART 실제 재무제표"
                result["fiscal_year"] = ratios.get("year")
                result["note"] = "EBITDA, CAPEX, 시가총액 등은 추정치. 정확한 분석은 val_dcf_valuation에 직접 입력 권장."
            return result

        except Exception as e:
            logger.error(f"DCF from DART error: {e}")
            return {"error": True, "message": f"DART 기반 DCF 실패: {e}"}

    def sensitivity_analysis(
        self,
        financials: CompanyFinancials,
        wacc_min: float,
        wacc_max: float,
        growth_min: float,
        growth_max: float,
    ) -> Dict[str, Any]:
        """Run sensitivity analysis."""
        try:
            df = self._dcf.sensitivity_analysis(
                financials,
                wacc_range=(wacc_min, wacc_max),
                growth_range=(growth_min, growth_max),
            )

            # Convert to serializable format
            matrix = df.round(0).astype(int).to_dict()

            return {
                "success": True,
                "stock_code": financials.stock_code,
                "company_name": financials.company_name,
                "current_price": round(financials.market_cap / financials.shares_outstanding, 0),
                "sensitivity_matrix": matrix,
                "wacc_range": f"{wacc_min:.1%} - {wacc_max:.1%}",
                "growth_range": f"{growth_min:.1%} - {growth_max:.1%}",
                "note": "Matrix shows per-share fair value at each WACC/Growth combination",
            }

        except Exception as e:
            logger.error(f"Sensitivity analysis error: {e}")
            return {"error": True, "message": str(e)}

    def peer_comparison(
        self,
        target_code: str,
        target_name: str,
        target_price: float,
        target_pe: float,
        target_pb: float,
        target_ev_ebitda: float,
        peer_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Run peer comparison."""
        try:
            target = CompanyMultiples(
                stock_code=target_code,
                company_name=target_name,
                price=target_price,
                pe_ratio=target_pe,
                pb_ratio=target_pb,
                ev_ebitda=target_ev_ebitda,
            )

            peers = []
            for p in peer_data:
                peers.append(CompanyMultiples(
                    stock_code=p.get("code", ""),
                    company_name=p.get("name", ""),
                    pe_ratio=p.get("pe", 0),
                    pb_ratio=p.get("pb", 0),
                    ev_ebitda=p.get("ev_ebitda", 0),
                ))

            result = self._relative.compare_multiples(target, peers)

            return {
                "success": True,
                "target": target_name,
                "peer_count": len(peers),
                "peer_average": {k: round(v, 2) for k, v in result.peer_avg.items()},
                "peer_median": {k: round(v, 2) for k, v in result.peer_median.items()},
                "percentile_rank": {k: round(v, 1) if v else None for k, v in result.percentile_rank.items()},
                "implied_prices": {k: round(v, 0) for k, v in result.implied_values.items() if v > 0},
                "recommendation": result.recommendation,
            }

        except Exception as e:
            logger.error(f"Peer comparison error: {e}")
            return {"error": True, "message": str(e)}

    def cross_market_comparison(
        self,
        kr_code: str,
        kr_name: str,
        kr_pe: float,
        kr_pb: float,
        kr_ev_ebitda: float,
        us_code: str,
        us_name: str,
        us_pe: float,
        us_pb: float,
        us_ev_ebitda: float,
        korea_discount: float,
    ) -> Dict[str, Any]:
        """Run cross-market comparison."""
        try:
            kr_company = CompanyMultiples(
                stock_code=kr_code,
                company_name=kr_name,
                country="KR",
                pe_ratio=kr_pe,
                pb_ratio=kr_pb,
                ev_ebitda=kr_ev_ebitda,
            )

            us_company = CompanyMultiples(
                stock_code=us_code,
                company_name=us_name,
                country="US",
                pe_ratio=us_pe,
                pb_ratio=us_pb,
                ev_ebitda=us_ev_ebitda,
            )

            result = self._relative.cross_market_comparison(
                kr_company, us_company, korea_discount
            )

            return {"success": True, **result}

        except Exception as e:
            logger.error(f"Cross-market comparison error: {e}")
            return {"error": True, "message": str(e)}

    def normalize_gaap(
        self,
        financials: Dict[str, float],
        source_standard: str,
        target_standard: str,
    ) -> Dict[str, Any]:
        """Normalize GAAP."""
        try:
            source = AccountingStandard(source_standard)
            target = AccountingStandard(target_standard)

            result = self._gaap_mapper.normalize_financials(financials, source, target)

            return {"success": True, **result}

        except Exception as e:
            logger.error(f"GAAP normalization error: {e}")
            return {"error": True, "message": str(e)}

    def get_market_assumptions(self) -> Dict[str, Any]:
        """Get current market assumptions."""
        return {
            "success": True,
            "data_source": self._data_source,
            "data_source_description": "ECOS (Bank of Korea)" if self._data_source == "ecos" else "Hardcoded test values",
            "assumptions": {
                "risk_free_rate": f"{self._dcf.risk_free_rate:.2%}",
                "market_risk_premium": f"{self._dcf.market_risk_premium:.2%}",
                "terminal_growth_rate": f"{self._dcf.terminal_growth_rate:.2%}",
                "default_beta": TEST_VALUES["default_beta"],
                "default_tax_rate": f"{TEST_VALUES['default_tax_rate']:.2%}",
                "projection_years": TEST_VALUES["projection_years"],
            },
            "real_data_available": {
                "risk_free_rate": self._real_risk_free_rate is not None,
                "beta": False,  # KRX integration pending
            },
            "note": "Risk-free rate from ECOS. Beta calculation requires KRX connection (currently unavailable).",
        }

    def refresh_market_data(self) -> Dict[str, Any]:
        """Refresh market data from ECOS."""
        old_rate = self._dcf.risk_free_rate
        old_source = self._data_source

        # Try to fetch fresh data
        new_rate = self._fetch_risk_free_rate()

        if new_rate:
            self._real_risk_free_rate = new_rate
            self._data_source = "ecos"
            self._dcf = DCFAnalyzer(risk_free_rate=new_rate)

            return {
                "success": True,
                "updated": True,
                "risk_free_rate": {
                    "old": f"{old_rate:.2%}",
                    "new": f"{new_rate:.2%}",
                    "source": "ECOS (Bank of Korea Base Rate)",
                },
                "data_source": self._data_source,
            }
        else:
            return {
                "success": True,
                "updated": False,
                "message": "Could not fetch fresh data from ECOS. Using previous values.",
                "risk_free_rate": f"{old_rate:.2%}",
                "data_source": old_source,
            }

    def run(self) -> None:
        """Run the MCP server."""
        logger.info("Starting Valuation MCP Server...")
        self.mcp.run()


def main():
    """Main entry point for standalone server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    server = ValuationServer()
    server.run()


if __name__ == "__main__":
    main()
