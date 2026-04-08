"""
Test fixtures for Nexus Finance MCP tool verification.
Deterministic (seeded) synthetic data covering all input patterns.
"""
import numpy as np
from datetime import datetime, timedelta

np.random.seed(42)

N_DAYS = 252
N_DAYS_LONG = 500
TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
START_DATE = datetime(2024, 1, 2)
TRADING_DATES = [(START_DATE + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(N_DAYS)]
TRADING_DATES_LONG = [(START_DATE + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(N_DAYS_LONG)]


def _gbm_prices(n=N_DAYS, s0=100.0, mu=0.08, sigma=0.20, seed=42):
    rng = np.random.RandomState(seed)
    dt = 1/252
    log_ret = (mu - 0.5*sigma**2)*dt + sigma*np.sqrt(dt)*rng.randn(n-1)
    prices = [s0]
    for lr in log_ret:
        prices.append(prices[-1] * np.exp(lr))
    return prices


# Pattern A: [{date, value}] time series
def make_series(seed=42):
    prices = _gbm_prices(seed=seed)
    return [{"date": TRADING_DATES[i], "value": round(p, 4)} for i, p in enumerate(prices)]

SINGLE_SERIES = make_series(42)
SINGLE_SERIES_B = make_series(99)


# Pattern B: [{date, open, high, low, close, volume}] OHLCV
def make_ohlcv(seed=42, n=N_DAYS):
    dates = TRADING_DATES_LONG[:n] if n > N_DAYS else TRADING_DATES[:n]
    prices = _gbm_prices(n=n, seed=seed)
    rng = np.random.RandomState(seed + 1000)
    candles = []
    for i, close in enumerate(prices):
        spread = close * 0.015
        candles.append({
            "date": dates[i],
            "open": round(close + rng.uniform(-spread*0.5, spread*0.5), 4),
            "high": round(close + rng.uniform(0, spread), 4),
            "low": round(close - rng.uniform(0, spread), 4),
            "close": round(close, 4),
            "volume": int(rng.uniform(500000, 5000000)),
        })
    return candles

OHLCV_DATA = make_ohlcv(42)
OHLCV_DATA_500 = make_ohlcv(42, n=500)


# Pattern C: {ticker: [{date, value}]} multi-asset returns
def make_multi_returns():
    result = {}
    for idx, ticker in enumerate(TICKERS):
        prices = _gbm_prices(seed=42 + idx*10)
        returns = []
        for i in range(1, len(prices)):
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append({"date": TRADING_DATES[i], "value": round(ret, 8)})
        result[ticker] = returns
    return result

def make_multi_prices():
    result = {}
    for idx, ticker in enumerate(TICKERS):
        prices = _gbm_prices(seed=42 + idx*10)
        result[ticker] = [{"date": TRADING_DATES[i], "value": round(p, 4)} for i, p in enumerate(prices)]
    return result

def make_multi_ohlcv():
    return {ticker: make_ohlcv(seed=42 + idx*10) for idx, ticker in enumerate(TICKERS)}

MULTI_ASSET_RETURNS = make_multi_returns()
MULTI_ASSET_PRICES = make_multi_prices()
MULTI_ASSET_OHLCV = make_multi_ohlcv()
SERIES_LIST = [make_series(42 + idx*10) for idx in range(len(TICKERS))]


# Pattern D: Specialized structures
ORDER_BOOK = {
    "bids": [[99.50 - i*0.10, int(np.random.RandomState(i).uniform(500, 5000))] for i in range(20)],
    "asks": [[100.50 + i*0.10, int(np.random.RandomState(i+100).uniform(500, 5000))] for i in range(20)],
}

TRADES_DATA = []
_rng = np.random.RandomState(55)
_mid = 100.0
for i in range(200):
    _mid += _rng.choice([-0.01, 0, 0.01, 0.02, -0.02])
    _sp = 0.05
    TRADES_DATA.append({
        "date": TRADING_DATES[min(i, N_DAYS-1)],
        "price": round(_mid + _rng.uniform(-0.02, 0.02), 4),
        "bid": round(_mid - _sp/2, 4),
        "ask": round(_mid + _sp/2, 4),
    })

FINANCIAL_DATA = {
    "AAPL": {"per": 28.5, "pbr": 45.2, "roe": 0.147, "operating_margin": 0.30, "debt_ratio": 0.82, "market_cap": 3e12},
    "GOOGL": {"per": 24.1, "pbr": 6.8, "roe": 0.235, "operating_margin": 0.28, "debt_ratio": 0.11, "market_cap": 2e12},
    "MSFT": {"per": 35.2, "pbr": 12.5, "roe": 0.388, "operating_margin": 0.42, "debt_ratio": 0.41, "market_cap": 3.1e12},
    "AMZN": {"per": 60.3, "pbr": 8.1, "roe": 0.145, "operating_margin": 0.08, "debt_ratio": 0.59, "market_cap": 1.8e12},
    "TSLA": {"per": 72.0, "pbr": 15.6, "roe": 0.208, "operating_margin": 0.11, "debt_ratio": 0.15, "market_cap": 0.8e12},
}

EQUAL_WEIGHTS = {t: 1.0/len(TICKERS) for t in TICKERS}
SKEWED_WEIGHTS = {"AAPL": 0.40, "GOOGL": 0.25, "MSFT": 0.20, "AMZN": 0.10, "TSLA": 0.05}

WEIGHTS_HISTORY = [
    {"date": f"2024-{m:02d}-01", "weights": {t: round(1/len(TICKERS) + np.random.RandomState(m+ord(t[0])).uniform(-0.05, 0.05), 4) for t in TICKERS}}
    for m in range(1, 13)
]

BINARY_SIGNALS = [{"date": TRADING_DATES[i], "value": int(np.random.RandomState(88+i).choice([-1, 0, 1]))} for i in range(N_DAYS)]

CANDIDATE_FEATURES = [
    {"name": "momentum", "data": make_series(100)},
    {"name": "vol_ratio", "data": make_series(200)},
    {"name": "spread", "data": make_series(300)},
]

SIGNALS_LIST = [
    {"name": "momentum", "data": make_series(100)},
    {"name": "value", "data": make_series(200)},
    {"name": "quality", "data": make_series(300)},
]

BL_VIEWS = [
    {"asset": "AAPL", "return": 0.15, "confidence": 0.8},
    {"asset": "GOOGL", "return": 0.10, "confidence": 0.6},
]

PARAM_RANGES = {"period": [10, 14, 20], "buy_threshold": [25, 30, 35]}
EVENT_DATES = ["2024-03-15", "2024-06-20"]

VALUATION_FINANCIALS = {
    "stock_code": "005930", "company_name": "Samsung Electronics",
    "revenue": 258e12, "ebit": 36e12, "ebitda": 53e12, "net_income": 26e12,
    "total_debt": 30e12, "cash": 100e12, "total_equity": 280e12,
    "shares_outstanding": 5969782550, "market_cap": 400e12,
    "capex": 30e12, "depreciation": 25e12, "change_in_nwc": 2e12,
    "beta": 1.1, "cost_of_debt": 0.04, "tax_rate": 0.22,
}

VIZ_LINE_DATA = [{"date": f"2024-{m:02d}-01", "value": round(100 + m*5 + np.random.RandomState(m).uniform(-10, 10), 1)} for m in range(1, 13)]
VIZ_BAR_DATA = [{"category": c, "value": round(np.random.RandomState(ord(c)).uniform(50, 200), 1)} for c in "ABCDE"]
