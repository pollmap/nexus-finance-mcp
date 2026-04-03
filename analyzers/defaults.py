"""
Default market assumptions for financial analysis.

These are fallback values used when real-time data (e.g., ECOS base rate)
is unavailable. All values should be treated as approximations.

When these defaults are used, a warning flag should be included in the
response so the caller knows the analysis uses assumed values.
"""

# Korean market defaults (updated periodically)
MARKET_DEFAULTS = {
    "risk_free_rate": 0.035,      # 3.5% (한국은행 기준금리 근사)
    "market_risk_premium": 0.06,  # 6% (한국 시장 ERP 역사적 평균)
    "default_beta": 1.0,          # 시장 평균
    "default_tax_rate": 0.22,     # 한국 법인세율 22%
    "terminal_growth_rate": 0.02, # 영구 성장률 2% (명목 GDP 성장률 하한)
    "projection_years": 5,        # 5년 추정
}

# Backward compatibility alias
TEST_VALUES = MARKET_DEFAULTS
