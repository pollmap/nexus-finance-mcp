"""
Automatic parameter inference for MCP tool testing.
Maps parameter names to sensible test values via regex rules + type fallbacks.
"""
import re
from typing import Any

from tests.framework.scanner import MISSING

# Regex pattern -> default test value (ordered by specificity)
SCALAR_RULES: list[tuple[str, Any]] = [
    # Identifiers
    (r"^stock_code$|^corp_code$", "005930"),
    (r"^ticker$", "AAPL"),
    (r"^symbol$", "BTC/USDT"),
    (r"^coin$", "BTC"),
    (r"^exchange$|^exchange_id$", "binance"),
    (r"^address$", "0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe"),
    (r"^slug$", "aave"),
    (r"^edinet_code$", "E02529"),
    (r"^rcp_no$", "20240001000001"),
    (r"^sigungu_code$", "11110"),
    (r"^airport$", "RKSI"),
    (r"^arxiv_id$", "2301.00001"),

    # Search/text
    (r"^keyword$|^query$|^search_term$|^term$", "경제"),
    (r"^author_name$", "Yoshua Bengio"),
    (r"^field$", "artificial intelligence"),
    (r"^filter_keyword$", "Revenue"),
    (r"^title$|^chart_title$", "Test"),

    # Macro identifiers
    (r"^series_id$", "FEDFUNDS"),
    (r"^indicator$", "NY.GDP.MKTP.CD"),
    (r"^stat_code$", "722Y001"),
    (r"^item_code$", "0101000"),
    (r"^dataset$", "MEI"),
    (r"^database$", "IFS"),
    (r"^concept$", "AccountsPayableCurrent"),
    (r"^namespace$", "us-gaap"),
    (r"^country$", "KOR"),
    (r"^countries$", "KOR,USA,JPN,CHN,DEU"),
    (r"^form_type$", "10-K"),
    (r"^report_type$", "11011"),

    # Date/time
    (r"^start_date$|^date$", "20240101"),
    (r"^end_date$", "20241231"),
    (r"^year$", 2025),
    (r"^year_month$", "202401"),
    (r"^timeframe$", "1d"),
    (r"^timespan$", "365days"),

    # Numeric
    (r"^limit$|^count$|^display$|^max_results$", 5),
    (r"^recent$", 10),
    (r"^days$|^hours$", 7),
    (r"^years$", 3),
    (r"^top_n$|^n$", 5),
    (r"^window$|^rolling_window$|^period$", 20),
    (r"^horizon$|^horizon_days$", 5),
    (r"^max_chars$", 5000),
    (r"^depth$|^max_depth$", 4),

    # Rates
    (r"^win_rate$", 0.55),
    (r"^avg_win$", 0.08),
    (r"^avg_loss$", 0.05),
    (r"^risk_free_rate$", 0.035),
    (r"^risk_aversion$", 2.5),
    (r"^commission$", 0.0018),
    (r"^stop_loss$", 0.05),
    (r"^take_profit$", 0.10),
    (r"^initial_capital$", 10000000.0),
    (r"^min_magnitude$", 4.0),

    # Method/strategy selectors
    (r"^method$", "pearson"),
    (r"^strategy_name$", "RSI_oversold"),
    (r"^factor_name$", "momentum"),
    (r"^model$", "additive"),
    (r"^language$|^lang$", "ko"),
    (r"^sort$", "date"),
    (r"^market$", "KR"),
    (r"^source$", "worldbank"),
    (r"^category$|^kind$|^subject$", ""),
    (r"^domain$", "korean_equity"),
    (r"^direction$", "downstream"),
    (r"^fs_div$", "CFS"),
    (r"^quote_currency$", ""),

    # Booleans
    (r"^save_html$|^save_png$|^horizontal$|^allow_short$", False),

    # Column names
    (r"^x_col$|^date_col$", "date"),
    (r"^y_col$|^close_col$", "close"),
    (r"^x_label$|^y_label$", ""),
]

_COMPILED_SCALAR = [(re.compile(pat), val) for pat, val in SCALAR_RULES]


# Complex data fixtures (loaded lazily from fixtures module)
COMPLEX_RULES: list[tuple[str, str]] = [
    # Pattern: param_name_regex -> fixture attribute name
    (r"^ohlcv_data$|^benchmark_data$", "OHLCV_DATA_500"),
    (r"^data$", "OHLCV_DATA"),  # technical/viz tools often use generic "data"
    (r"^series$|^price_series$|^signal_series$|^target_series$|^returns_series$|^vix_series$", "SINGLE_SERIES"),
    (r"^series_a$|^dependent$", "SINGLE_SERIES"),
    (r"^series_b$", "SINGLE_SERIES_B"),
    (r"^assets_returns$|^series_dict$", "MULTI_ASSET_RETURNS"),
    (r"^assets_data$|^stocks_data$", "MULTI_ASSET_OHLCV"),
    (r"^portfolio_weights$|^weights$|^current_weights$", "EQUAL_WEIGHTS"),
    (r"^target_weights$", "EQUAL_WEIGHTS"),
    (r"^financial_data$", "FINANCIAL_DATA"),
    (r"^orderbook$", "ORDER_BOOK"),
    (r"^trades$", "TRADES_DATA"),
    (r"^series_list$|^universe$", "SERIES_LIST"),
    (r"^names$|^asset_names$|^tickers$", "TICKERS"),
    (r"^signals$|^alpha_series$|^signal$", "SINGLE_SERIES"),
    (r"^returns$", "SINGLE_SERIES_B"),
    (r"^candidate_features$", "CANDIDATE_FEATURES"),
    (r"^weights_history$", "WEIGHTS_HISTORY"),
    (r"^views$", "BL_VIEWS"),
    (r"^param_ranges$", "PARAM_RANGES"),
    (r"^event_dates$", "EVENT_DATES"),
    (r"^market_caps$", None),  # Will use [400e12, 120e12, 100e12, 60e12, 50e12]
]

_COMPILED_COMPLEX = [(re.compile(pat), attr) for pat, attr in COMPLEX_RULES]


TYPE_FALLBACKS = {
    "str": "",
    "int": 10,
    "float": 1.0,
    "bool": True,
    "list": [],
    "dict": {},
    "List": [],
    "Dict": {},
}


def _resolve_scalar(name: str) -> tuple[bool, Any]:
    for pattern, val in _COMPILED_SCALAR:
        if pattern.search(name):
            return True, val
    return False, None


def _resolve_complex(name: str) -> tuple[bool, Any]:
    from tests.framework import fixtures
    for pattern, attr in _COMPILED_COMPLEX:
        if pattern.search(name):
            if attr is None:
                # Special cases
                if "market_caps" in name:
                    return True, [400e12, 120e12, 100e12, 60e12, 50e12]
                return False, None
            return True, getattr(fixtures, attr, None)
    return False, None


def _resolve_type(type_hint: str) -> Any:
    if not type_hint or type_hint == "Any":
        return ""
    if type_hint.startswith("Optional"):
        return None
    base = type_hint.split("[")[0].strip()
    return TYPE_FALLBACKS.get(base, "")


def infer_test_args(tool_spec: dict) -> dict:
    """
    Infer test arguments for a tool based on its parameter spec.

    tool_spec = {
        "params": [
            {"name": "stock_code", "type": "str", "default": MISSING, "required": True},
            ...
        ]
    }
    """
    kwargs = {}
    for param in tool_spec.get("params", []):
        name = param["name"]
        ptype = param.get("type", "")
        default = param.get("default", MISSING)

        # Priority 1: Use function's own default
        if default is not MISSING:
            kwargs[name] = default
            continue

        # Priority 2: Complex fixture match
        matched, val = _resolve_complex(name)
        if matched and val is not None:
            kwargs[name] = val
            continue

        # Priority 3: Scalar name match
        matched, val = _resolve_scalar(name)
        if matched:
            kwargs[name] = val
            continue

        # Priority 4: Type fallback
        kwargs[name] = _resolve_type(ptype)

    return kwargs
