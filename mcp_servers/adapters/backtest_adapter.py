"""
Backtest Adapter - Strategy Backtesting Engine.

Simulates trading strategies on OHLCV price data with realistic
Korean market transaction costs (commission + 증권거래세).

Built-in strategies:
- RSI_oversold: RSI 과매도/과매수 전략
- MACD_crossover: MACD 골든/데드크로스
- Bollinger_bounce: 볼린저밴드 반등
- MA_cross: 이동평균 교차
- Mean_reversion: 평균회귀
- Momentum: 모멘텀

Provides:
- Single strategy backtest (run)
- Multi-strategy comparison (compare)
- Parameter optimization via grid search (optimize)
- Portfolio backtesting with rebalancing (portfolio)
- Benchmark comparison with alpha/beta (benchmark)
- Risk analysis: VaR, CVaR, Sortino, Calmar (risk_analysis)
- Signal history with forward returns (signal_history)
- Drawdown period analysis (drawdown_analysis)

Run standalone test: python -m mcp_servers.adapters.backtest_adapter
"""
import logging
import itertools
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Built-in strategy definitions ──────────────────────────────────────
STRATEGIES = {
    "RSI_oversold": {
        "buy": "RSI < 30",
        "sell": "RSI > 70",
        "params": {"period": 14, "buy_threshold": 30, "sell_threshold": 70},
    },
    "MACD_crossover": {
        "buy": "MACD crosses above signal",
        "sell": "MACD crosses below signal",
        "params": {"fast": 12, "slow": 26, "signal": 9},
    },
    "Bollinger_bounce": {
        "buy": "price touches lower band",
        "sell": "price touches upper band",
        "params": {"period": 20, "std": 2},
    },
    "MA_cross": {
        "buy": "short MA crosses above long MA",
        "sell": "short MA crosses below long MA",
        "params": {"short": 20, "long": 50},
    },
    "Mean_reversion": {
        "buy": "price < MA - 2*std",
        "sell": "price > MA + 2*std",
        "params": {"period": 20, "threshold": 2.0},
    },
    "Momentum": {
        "buy": "N-day return > 0",
        "sell": "N-day return < 0",
        "params": {"period": 20},
    },
    "combo": {
        "buy": "multiple strategies agree (AND/OR)",
        "sell": "multiple strategies agree (AND/OR)",
        "params": {"strategies": [], "mode": "all"},
    },
    "custom": {
        "buy": "user-defined indicator rules",
        "sell": "user-defined indicator rules",
        "params": {"buy_rules": [], "sell_rules": [], "logic": "all"},
    },
}


class BacktestAdapter:
    """
    Strategy backtesting engine with realistic Korean market costs.

    Default costs:
      - commission: 0.18% per trade (매매수수료)
      - tax: 0.18% sell-side only (증권거래세, 2024 기준)
    """

    RISK_FREE_RATE = 0.035  # Korean 1-year T-bond approx

    # ── Strategy signal generators ─────────────────────────────────────

    def _apply_rsi_strategy(self, df: pd.DataFrame, params: dict) -> pd.Series:
        """RSI oversold/overbought strategy signals."""
        period = params.get("period", 14)
        buy_thresh = params.get("buy_threshold", 30)
        sell_thresh = params.get("sell_threshold", 70)

        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0).rolling(window=period, min_periods=period).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(window=period, min_periods=period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        signals = pd.Series(0, index=df.index)
        signals[rsi < buy_thresh] = 1   # buy
        signals[rsi > sell_thresh] = -1  # sell
        return signals

    def _apply_macd_strategy(self, df: pd.DataFrame, params: dict) -> pd.Series:
        """MACD crossover strategy signals."""
        fast = params.get("fast", 12)
        slow = params.get("slow", 26)
        sig_period = params.get("signal", 9)

        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=sig_period, adjust=False).mean()

        signals = pd.Series(0, index=df.index)
        # Golden cross: MACD crosses above signal
        cross_up = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
        # Dead cross: MACD crosses below signal
        cross_down = (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))

        signals[cross_up] = 1
        signals[cross_down] = -1
        return signals

    def _apply_bollinger_strategy(self, df: pd.DataFrame, params: dict) -> pd.Series:
        """Bollinger Band bounce strategy signals."""
        period = params.get("period", 20)
        num_std = params.get("std", 2)

        ma = df["close"].rolling(window=period, min_periods=period).mean()
        std = df["close"].rolling(window=period, min_periods=period).std()
        upper = ma + num_std * std
        lower = ma - num_std * std

        signals = pd.Series(0, index=df.index)
        signals[df["close"] <= lower] = 1   # buy at lower band
        signals[df["close"] >= upper] = -1  # sell at upper band
        return signals

    def _apply_ma_cross_strategy(self, df: pd.DataFrame, params: dict) -> pd.Series:
        """Moving average crossover strategy signals."""
        short_period = params.get("short", 20)
        long_period = params.get("long", 50)

        ma_short = df["close"].rolling(window=short_period, min_periods=short_period).mean()
        ma_long = df["close"].rolling(window=long_period, min_periods=long_period).mean()

        signals = pd.Series(0, index=df.index)
        cross_up = (ma_short > ma_long) & (ma_short.shift(1) <= ma_long.shift(1))
        cross_down = (ma_short < ma_long) & (ma_short.shift(1) >= ma_long.shift(1))

        signals[cross_up] = 1
        signals[cross_down] = -1
        return signals

    def _apply_mean_reversion_strategy(self, df: pd.DataFrame, params: dict) -> pd.Series:
        """Mean reversion strategy signals."""
        period = params.get("period", 20)
        threshold = params.get("threshold", 2.0)

        ma = df["close"].rolling(window=period, min_periods=period).mean()
        std = df["close"].rolling(window=period, min_periods=period).std()

        signals = pd.Series(0, index=df.index)
        signals[df["close"] < (ma - threshold * std)] = 1   # buy below lower band
        signals[df["close"] > (ma + threshold * std)] = -1  # sell above upper band
        return signals

    def _apply_momentum_strategy(self, df: pd.DataFrame, params: dict) -> pd.Series:
        """Momentum strategy signals."""
        period = params.get("period", 20)

        returns_n = df["close"].pct_change(periods=period)

        signals = pd.Series(0, index=df.index)
        signals[returns_n > 0] = 1    # positive momentum → buy
        signals[returns_n < 0] = -1   # negative momentum → sell
        return signals

    # ── Strategy dispatcher ────────────────────────────────────────────

    _STRATEGY_MAP = {
        "RSI_oversold": "_apply_rsi_strategy",
        "MACD_crossover": "_apply_macd_strategy",
        "Bollinger_bounce": "_apply_bollinger_strategy",
        "MA_cross": "_apply_ma_cross_strategy",
        "Mean_reversion": "_apply_mean_reversion_strategy",
        "Momentum": "_apply_momentum_strategy",
    }

    def _get_signals(self, df: pd.DataFrame, strategy_name: str, params: dict = None) -> pd.Series:
        """Dispatch to the correct strategy signal generator.

        Special strategies:
        - "combo": combine multiple strategies (params["strategies"] = list, params["mode"] = "all"/"any")
        - "custom": user-defined rules (params["buy_rules"] + params["sell_rules"])
        """
        # Combo: combine multiple strategies with AND/OR logic
        if strategy_name == "combo":
            return self._apply_combo_strategy(df, params or {})

        # Custom: user-defined indicator-based rules
        if strategy_name == "custom":
            return self._apply_custom_strategy(df, params or {})

        if strategy_name not in self._STRATEGY_MAP:
            raise ValueError(f"Unknown strategy: {strategy_name}. Available: {list(STRATEGIES.keys()) + ['combo', 'custom']}")

        method_name = self._STRATEGY_MAP[strategy_name]
        method = getattr(self, method_name)
        merged_params = {**STRATEGIES[strategy_name]["params"]}
        if params:
            merged_params.update(params)
        return method(df, merged_params)

    def _apply_combo_strategy(self, df: pd.DataFrame, params: dict) -> pd.Series:
        """Combine multiple strategies: AND (all agree) or OR (any agrees).

        params:
            strategies: list of strategy names (e.g., ["RSI_oversold", "MACD_crossover"])
            mode: "all" = all must agree (AND), "any" = any one triggers (OR). Default "all".
            strategy_params: dict of {strategy_name: {param overrides}} (optional)
        """
        strategies = params.get("strategies", [])
        mode = params.get("mode", "all")
        strategy_params = params.get("strategy_params", {})

        if len(strategies) < 2:
            raise ValueError("combo strategy requires at least 2 strategies in params['strategies']")

        all_signals = []
        for strat in strategies:
            sp = strategy_params.get(strat, None)
            sig = self._get_signals(df, strat, sp)
            all_signals.append(sig)

        combined = pd.DataFrame(all_signals).T

        if mode == "all":
            buy = (combined == 1).all(axis=1).astype(int)
            sell = (combined == -1).all(axis=1).astype(int) * -1
        else:  # "any"
            buy = (combined == 1).any(axis=1).astype(int)
            sell = (combined == -1).any(axis=1).astype(int) * -1

        signals = buy + sell
        return signals

    def _apply_custom_strategy(self, df: pd.DataFrame, params: dict) -> pd.Series:
        """User-defined custom strategy using indicator conditions.

        params:
            buy_rules: list of conditions, each is {"indicator": str, "op": str, "value": float}
            sell_rules: list of conditions
            logic: "all" or "any" (default "all")

        Supported indicators: RSI, MACD, MACD_signal, BB_upper, BB_lower, BB_mid,
                              SMA_20, SMA_50, SMA_200, EMA_12, EMA_26, price, volume
        Supported operators: "<", ">", "<=", ">=", "cross_above", "cross_below"

        Example:
            buy_rules: [{"indicator": "RSI", "op": "<", "value": 30}, {"indicator": "MACD", "op": "cross_above", "value": "MACD_signal"}]
            sell_rules: [{"indicator": "RSI", "op": ">", "value": 70}]
        """
        buy_rules = params.get("buy_rules", [])
        sell_rules = params.get("sell_rules", [])
        logic = params.get("logic", "all")

        if not buy_rules or not sell_rules:
            raise ValueError("custom strategy requires both buy_rules and sell_rules")

        # Pre-compute all indicators
        indicators = self._compute_all_indicators(df, params)

        signals = pd.Series(0, index=df.index)

        # Evaluate buy conditions
        buy_conditions = []
        for rule in buy_rules:
            cond = self._eval_condition(indicators, rule)
            buy_conditions.append(cond)

        if buy_conditions:
            if logic == "all":
                buy_mask = pd.concat(buy_conditions, axis=1).all(axis=1)
            else:
                buy_mask = pd.concat(buy_conditions, axis=1).any(axis=1)
            signals[buy_mask] = 1

        # Evaluate sell conditions
        sell_conditions = []
        for rule in sell_rules:
            cond = self._eval_condition(indicators, rule)
            sell_conditions.append(cond)

        if sell_conditions:
            if logic == "all":
                sell_mask = pd.concat(sell_conditions, axis=1).all(axis=1)
            else:
                sell_mask = pd.concat(sell_conditions, axis=1).any(axis=1)
            signals[sell_mask] = -1

        return signals

    def _compute_all_indicators(self, df: pd.DataFrame, params: dict) -> Dict[str, pd.Series]:
        """Pre-compute all technical indicators for custom strategy evaluation."""
        close = df["close"]
        indicators = {"price": close, "volume": df["volume"].astype(float)}

        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(params.get("rsi_period", 14)).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(params.get("rsi_period", 14)).mean()
        rs = gain / loss
        indicators["RSI"] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        indicators["MACD"] = ema12 - ema26
        indicators["MACD_signal"] = indicators["MACD"].ewm(span=9).mean()
        indicators["MACD_histogram"] = indicators["MACD"] - indicators["MACD_signal"]
        indicators["EMA_12"] = ema12
        indicators["EMA_26"] = ema26

        # Bollinger Bands
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        indicators["BB_upper"] = sma20 + 2 * std20
        indicators["BB_lower"] = sma20 - 2 * std20
        indicators["BB_mid"] = sma20

        # Moving Averages
        indicators["SMA_20"] = close.rolling(20).mean()
        indicators["SMA_50"] = close.rolling(50).mean()
        indicators["SMA_200"] = close.rolling(200).mean()

        return indicators

    def _eval_condition(self, indicators: Dict[str, pd.Series], rule: dict) -> pd.Series:
        """Evaluate a single condition rule against pre-computed indicators."""
        ind_name = rule.get("indicator", "")
        op = rule.get("op", ">")
        value = rule.get("value")

        if ind_name not in indicators:
            raise ValueError(f"Unknown indicator: {ind_name}. Available: {list(indicators.keys())}")

        series = indicators[ind_name]

        # Value can be a number or another indicator name
        if isinstance(value, str) and value in indicators:
            compare_to = indicators[value]
        else:
            compare_to = float(value)

        if op == "<":
            return series < compare_to
        elif op == ">":
            return series > compare_to
        elif op == "<=":
            return series <= compare_to
        elif op == ">=":
            return series >= compare_to
        elif op == "cross_above":
            prev = series.shift(1)
            if isinstance(compare_to, pd.Series):
                prev_comp = compare_to.shift(1)
                return (prev <= prev_comp) & (series > compare_to)
            return (prev <= compare_to) & (series > compare_to)
        elif op == "cross_below":
            prev = series.shift(1)
            if isinstance(compare_to, pd.Series):
                prev_comp = compare_to.shift(1)
                return (prev >= prev_comp) & (series < compare_to)
            return (prev >= compare_to) & (series < compare_to)
        else:
            raise ValueError(f"Unknown operator: {op}. Use: <, >, <=, >=, cross_above, cross_below")

    # ── DataFrame builder ──────────────────────────────────────────────

    def _build_df(self, ohlcv_data: List[Dict]) -> pd.DataFrame:
        """Convert list[dict] OHLCV to DatetimeIndex DataFrame."""
        df = pd.DataFrame(ohlcv_data)
        for col in ("open", "high", "low", "close", "volume"):
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        if "date" not in df.columns:
            raise ValueError("Missing required column: date")

        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        df = df.set_index("date")
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["close"])
        return df

    # ── Core simulation engine ─────────────────────────────────────────

    def _simulate(
        self,
        df: pd.DataFrame,
        signals: pd.Series,
        initial_capital: float,
        commission: float,
        tax: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        position_size: float = 0.95,
        allow_short: bool = False,
    ) -> Tuple[float, int, List[Dict], List[Dict]]:
        """
        Core trade simulation with stop-loss, take-profit, position sizing, short support.

        Args:
            stop_loss: 손절 비율 (예: 0.05 = -5%에서 자동 매도)
            take_profit: 익절 비율 (예: 0.10 = +10%에서 자동 매도)
            position_size: 자본 대비 포지션 비중 (0.0~1.0, 기본 0.95)
            allow_short: 공매도 허용 (기본 False)
        """
        cash = float(initial_capital)
        shares = 0
        position = 0  # 1=long, -1=short, 0=flat
        trades: List[Dict] = []
        equity: List[Dict] = []
        entry_price = 0.0

        for i in range(1, len(df)):
            price = float(df.iloc[i]["open"])
            close_price = float(df.iloc[i]["close"])
            signal = int(signals.iloc[i - 1])

            # Stop-loss / Take-profit check (before new signals)
            if position == 1 and shares > 0 and entry_price > 0:
                pnl_pct = (price - entry_price) / entry_price
                if stop_loss and pnl_pct <= -stop_loss:
                    signal = -1  # force sell (stop loss)
                elif take_profit and pnl_pct >= take_profit:
                    signal = -1  # force sell (take profit)

            if position == -1 and shares > 0 and entry_price > 0 and allow_short:
                pnl_pct = (entry_price - price) / entry_price
                if stop_loss and pnl_pct <= -stop_loss:
                    signal = 1  # force cover (stop loss)
                elif take_profit and pnl_pct >= take_profit:
                    signal = 1  # force cover (take profit)

            # LONG entry (or cover short + go long)
            if signal == 1 and position <= 0 and price > 0:
                if position == -1 and shares > 0 and allow_short:
                    # Cover short: P&L = (entry - cover) * shares - costs
                    short_pnl = shares * (entry_price - price) - shares * price * commission - shares * entry_price * tax
                    cash += short_pnl
                    trades.append({"date": str(df.index[i].date()), "action": "COVER", "price": round(price), "shares": shares, "pnl": round(short_pnl)})
                    shares = 0
                    position = 0

                if position == 0:
                    max_shares = int(cash * position_size / (price * (1 + commission)))
                    if max_shares > 0:
                        cost = max_shares * price * (1 + commission)
                        cash -= cost
                        shares = max_shares
                        entry_price = price
                        position = 1
                        trades.append({"date": str(df.index[i].date()), "action": "BUY", "price": round(price), "shares": shares})

            # LONG exit (or sell + go short)
            elif signal == -1 and price > 0:
                if position == 1 and shares > 0:
                    proceeds = shares * price * (1 - commission - tax)
                    pnl = proceeds - (shares * entry_price * (1 + commission))
                    cash += proceeds
                    trades.append({"date": str(df.index[i].date()), "action": "SELL", "price": round(price), "shares": shares, "pnl": round(pnl)})
                    shares = 0
                    position = 0

                if allow_short and position == 0:
                    # Margin-based short: reserve cash, track entry
                    max_shares = int(cash * position_size / (price * (1 + commission)))
                    if max_shares > 0:
                        shares = max_shares
                        entry_price = price
                        position = -1
                        trades.append({"date": str(df.index[i].date()), "action": "SHORT", "price": round(price), "shares": shares})

            # Portfolio value
            if position == 1:
                portfolio_value = cash + shares * close_price
            elif position == -1:
                unrealized = shares * (entry_price - close_price)
                portfolio_value = cash + unrealized
            else:
                portfolio_value = cash

            equity.append({"date": str(df.index[i].date()), "value": round(portfolio_value)})

        return cash, shares, trades, equity

    # ── Metrics calculators ────────────────────────────────────────────

    def _calc_metrics(
        self,
        equity: List[Dict],
        trades: List[Dict],
        initial_capital: float,
    ) -> Dict[str, Any]:
        """Calculate standard backtest metrics from equity curve and trades."""
        if not equity:
            return {
                "total_return_pct": 0.0,
                "annualized_return": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown_pct": 0.0,
                "win_rate": 0.0,
                "total_trades": 0,
                "avg_holding_days": 0,
            }

        values = np.array([e["value"] for e in equity], dtype=float)
        dates = pd.to_datetime([e["date"] for e in equity])

        # Total return
        final_value = values[-1]
        total_return_pct = round((final_value / initial_capital - 1) * 100, 2)

        # Annualized return
        n_days = (dates[-1] - dates[0]).days
        if n_days > 0:
            annualized = ((final_value / initial_capital) ** (365.0 / n_days) - 1) * 100
        else:
            annualized = 0.0
        annualized = round(annualized, 2)

        # Daily returns
        daily_returns = np.diff(values) / values[:-1]
        daily_returns = daily_returns[np.isfinite(daily_returns)]

        # Sharpe ratio (annualized)
        if len(daily_returns) > 1 and np.std(daily_returns) > 0:
            excess = np.mean(daily_returns) - self.RISK_FREE_RATE / 252
            sharpe = excess / np.std(daily_returns) * np.sqrt(252)
        else:
            sharpe = 0.0
        sharpe = round(sharpe, 3)

        # Max drawdown
        peak = np.maximum.accumulate(values)
        drawdown = (values - peak) / peak
        max_dd = round(float(np.min(drawdown)) * 100, 2)

        # Win rate
        sell_trades = [t for t in trades if t.get("action") == "SELL"]
        winning = [t for t in sell_trades if t.get("pnl", 0) > 0]
        win_rate = round(len(winning) / len(sell_trades) * 100, 1) if sell_trades else 0.0
        total_trades = len(sell_trades)

        # Average holding days
        avg_hold = 0
        buy_dates = [t["date"] for t in trades if t["action"] == "BUY"]
        sell_dates = [t["date"] for t in trades if t["action"] == "SELL"]
        if buy_dates and sell_dates:
            hold_days = []
            for b, s in zip(buy_dates, sell_dates):
                bd = pd.Timestamp(b)
                sd = pd.Timestamp(s)
                hold_days.append((sd - bd).days)
            avg_hold = round(np.mean(hold_days)) if hold_days else 0

        return {
            "total_return_pct": total_return_pct,
            "annualized_return": annualized,
            "sharpe_ratio": sharpe,
            "max_drawdown_pct": max_dd,
            "win_rate": win_rate,
            "total_trades": total_trades,
            "avg_holding_days": avg_hold,
        }

    def _calc_risk_metrics(self, equity: List[Dict], initial_capital: float) -> Dict[str, Any]:
        """Calculate risk metrics: VaR, CVaR, Sortino, Calmar, volatility."""
        if len(equity) < 2:
            return {
                "var_95": 0.0, "var_99": 0.0, "cvar_95": 0.0, "cvar_99": 0.0,
                "annualized_volatility": 0.0, "max_drawdown_pct": 0.0,
                "calmar_ratio": 0.0, "sortino_ratio": 0.0,
            }

        values = np.array([e["value"] for e in equity], dtype=float)
        daily_returns = np.diff(values) / values[:-1]
        daily_returns = daily_returns[np.isfinite(daily_returns)]

        if len(daily_returns) < 2:
            return {
                "var_95": 0.0, "var_99": 0.0, "cvar_95": 0.0, "cvar_99": 0.0,
                "annualized_volatility": 0.0, "max_drawdown_pct": 0.0,
                "calmar_ratio": 0.0, "sortino_ratio": 0.0,
            }

        # VaR
        var_95 = round(float(np.percentile(daily_returns, 5)) * 100, 3)
        var_99 = round(float(np.percentile(daily_returns, 1)) * 100, 3)

        # CVaR (Expected Shortfall)
        cvar_95 = round(float(np.mean(daily_returns[daily_returns <= np.percentile(daily_returns, 5)])) * 100, 3)
        cvar_99_mask = daily_returns <= np.percentile(daily_returns, 1)
        cvar_99 = round(float(np.mean(daily_returns[cvar_99_mask])) * 100, 3) if cvar_99_mask.any() else var_99

        # Annualized volatility
        vol = round(float(np.std(daily_returns) * np.sqrt(252)) * 100, 2)

        # Max drawdown
        peak = np.maximum.accumulate(values)
        drawdown = (values - peak) / peak
        max_dd = round(float(np.min(drawdown)) * 100, 2)

        # Calmar ratio = annualized return / abs(max drawdown)
        dates = pd.to_datetime([e["date"] for e in equity])
        n_days = (dates[-1] - dates[0]).days
        ann_ret = ((values[-1] / initial_capital) ** (365.0 / max(n_days, 1)) - 1) if n_days > 0 else 0.0
        calmar = round(ann_ret / abs(max_dd / 100), 3) if max_dd != 0 else 0.0

        # Sortino ratio
        downside = daily_returns[daily_returns < 0]
        downside_std = float(np.std(downside)) if len(downside) > 0 else 0.0
        if downside_std > 0:
            sortino = (np.mean(daily_returns) - self.RISK_FREE_RATE / 252) / downside_std * np.sqrt(252)
        else:
            sortino = 0.0
        sortino = round(sortino, 3)

        return {
            "var_95_pct": var_95,
            "var_99_pct": var_99,
            "cvar_95_pct": cvar_95,
            "cvar_99_pct": cvar_99,
            "annualized_volatility_pct": vol,
            "max_drawdown_pct": max_dd,
            "calmar_ratio": calmar,
            "sortino_ratio": sortino,
        }

    # ── Public methods (8) ─────────────────────────────────────────────

    def run(
        self,
        ohlcv_data: List[Dict],
        strategy_name: str,
        initial_capital: float = 10_000_000,
        commission: float = 0.0018,
        tax: float = 0.0018,
        params: Optional[Dict] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        position_size: float = 0.95,
        allow_short: bool = False,
    ) -> Dict[str, Any]:
        """
        단일 전략 백테스트 실행.

        Args:
            ohlcv_data: OHLCV 데이터 (list[dict] with date, open, high, low, close, volume)
            strategy_name: 전략 이름 (RSI_oversold, MACD_crossover, Bollinger_bounce, MA_cross, Mean_reversion, Momentum, custom)
            initial_capital: 초기 자본금 (기본 1,000만원)
            commission: 매매수수료 (기본 0.18% 한국, 0 미국)
            tax: 증권거래세 매도시 (기본 0.18% 한국, 0 미국)
            params: 전략 파라미터 오버라이드
            stop_loss: 손절 비율 (예: 0.05 = -5%, None=비활성)
            take_profit: 익절 비율 (예: 0.10 = +10%, None=비활성)
            position_size: 자본 대비 포지션 비중 (0.0~1.0, 기본 0.95)
            allow_short: 공매도 허용 (기본 False)

        Returns:
            metrics + equity_curve + trades
        """
        try:
            if strategy_name not in STRATEGIES:
                return {"error": True, "message": f"Unknown strategy: {strategy_name}. Available: {list(STRATEGIES.keys())}"}

            df = self._build_df(ohlcv_data)
            if len(df) < 60:
                return {"error": True, "message": f"Insufficient data: {len(df)} rows. Need at least 60."}

            signals = self._get_signals(df, strategy_name, params)
            cash, shares, trades, equity = self._simulate(
                df, signals, initial_capital, commission, tax,
                stop_loss=stop_loss, take_profit=take_profit,
                position_size=position_size, allow_short=allow_short,
            )

            metrics = self._calc_metrics(equity, trades, initial_capital)

            # Limit equity curve for response size
            equity_sampled = equity
            if len(equity) > 500:
                step = len(equity) // 500
                equity_sampled = equity[::step]

            return {
                "success": True,
                "data": {
                    "strategy": strategy_name,
                    "params": {**STRATEGIES[strategy_name]["params"], **(params or {})},
                    "period": {
                        "start": equity[0]["date"] if equity else None,
                        "end": equity[-1]["date"] if equity else None,
                        "trading_days": len(equity),
                    },
                    "initial_capital": initial_capital,
                    "final_value": equity[-1]["value"] if equity else initial_capital,
                    "costs": {"commission": commission, "tax_sell_side": tax},
                    **metrics,
                    "trades": trades,
                    "equity_curve": equity_sampled,
                },
            }
        except Exception as e:
            logger.exception(f"Backtest run failed: {e}")
            return {"error": True, "message": str(e)}

    def compare(
        self,
        ohlcv_data: List[Dict],
        strategy_names: List[str],
        initial_capital: float = 10_000_000,
        commission: float = 0.0018,
        tax: float = 0.0018,
    ) -> Dict[str, Any]:
        """
        복수 전략 비교 백테스트.

        Args:
            ohlcv_data: OHLCV 데이터
            strategy_names: 비교할 전략 이름 목록
            initial_capital: 초기 자본금

        Returns:
            전략별 지표 비교 테이블
        """
        try:
            results = []
            for name in strategy_names:
                res = self.run(ohlcv_data, name, initial_capital, commission, tax)
                if res.get("error"):
                    results.append({"strategy": name, "error": res["message"]})
                else:
                    d = res["data"]
                    results.append({
                        "strategy": name,
                        "total_return_pct": d["total_return_pct"],
                        "annualized_return": d["annualized_return"],
                        "sharpe_ratio": d["sharpe_ratio"],
                        "max_drawdown_pct": d["max_drawdown_pct"],
                        "win_rate": d["win_rate"],
                        "total_trades": d["total_trades"],
                        "final_value": d["final_value"],
                    })

            # Sort by Sharpe descending
            ranked = sorted(
                [r for r in results if "error" not in r],
                key=lambda x: x["sharpe_ratio"],
                reverse=True,
            )
            errors = [r for r in results if "error" in r]

            return {
                "success": True,
                "data": {
                    "comparison": ranked + errors,
                    "best_strategy": ranked[0]["strategy"] if ranked else None,
                    "strategies_count": len(strategy_names),
                },
            }
        except Exception as e:
            logger.exception(f"Backtest compare failed: {e}")
            return {"error": True, "message": str(e)}

    def optimize(
        self,
        ohlcv_data: List[Dict],
        strategy_name: str,
        param_ranges: Dict[str, List],
        initial_capital: float = 10_000_000,
        commission: float = 0.0018,
        tax: float = 0.0018,
    ) -> Dict[str, Any]:
        """
        전략 파라미터 최적화 (Grid Search).

        Args:
            ohlcv_data: OHLCV 데이터
            strategy_name: 전략 이름
            param_ranges: 파라미터별 탐색 범위 (예: {"period": [10, 14, 20], "buy_threshold": [25, 30, 35]})
            initial_capital: 초기 자본금

        Returns:
            최적 파라미터, 최고 Sharpe, 전체 결과
        """
        try:
            if strategy_name not in STRATEGIES:
                return {"error": True, "message": f"Unknown strategy: {strategy_name}"}

            keys = list(param_ranges.keys())
            value_lists = [param_ranges[k] for k in keys]
            combinations = list(itertools.product(*value_lists))

            if len(combinations) > 500:
                return {"error": True, "message": f"Too many combinations ({len(combinations)}). Max 500. Reduce param_ranges."}

            df = self._build_df(ohlcv_data)
            if len(df) < 60:
                return {"error": True, "message": f"Insufficient data: {len(df)} rows."}

            all_results = []
            for combo in combinations:
                params = dict(zip(keys, combo))
                try:
                    signals = self._get_signals(df, strategy_name, params)
                    cash, shares, trades, equity = self._simulate(df, signals, initial_capital, commission, tax)
                    metrics = self._calc_metrics(equity, trades, initial_capital)
                    all_results.append({
                        "params": params,
                        **metrics,
                    })
                except Exception as ex:
                    logger.debug(f"Optimization combo {params} failed: {ex}")

            if not all_results:
                return {"error": True, "message": "All parameter combinations failed."}

            all_results.sort(key=lambda x: x["sharpe_ratio"], reverse=True)
            best = all_results[0]

            return {
                "success": True,
                "data": {
                    "strategy": strategy_name,
                    "best_params": best["params"],
                    "best_sharpe": best["sharpe_ratio"],
                    "best_return_pct": best["total_return_pct"],
                    "combinations_tested": len(all_results),
                    "top_10": all_results[:10],
                    "all_results": all_results[:50],  # cap response size
                },
            }
        except Exception as e:
            logger.exception(f"Backtest optimize failed: {e}")
            return {"error": True, "message": str(e)}

    def portfolio(
        self,
        assets_data: Dict[str, List[Dict]],
        weights: Dict[str, float],
        rebalance_freq: str = "monthly",
        initial_capital: float = 10_000_000,
    ) -> Dict[str, Any]:
        """
        포트폴리오 백테스트 (자산배분 + 리밸런싱).

        Args:
            assets_data: {ticker: ohlcv_list} 자산별 OHLCV 데이터
            weights: {ticker: weight} 자산별 비중 (합계 1.0)
            rebalance_freq: 리밸런싱 주기 ("monthly" or "quarterly")
            initial_capital: 초기 자본금

        Returns:
            포트폴리오 성과 + 자산별 기여도
        """
        try:
            if abs(sum(weights.values()) - 1.0) > 0.01:
                return {"error": True, "message": f"Weights must sum to 1.0. Current sum: {sum(weights.values()):.3f}"}

            tickers = list(weights.keys())
            dfs = {}
            for ticker in tickers:
                if ticker not in assets_data:
                    return {"error": True, "message": f"Missing data for ticker: {ticker}"}
                dfs[ticker] = self._build_df(assets_data[ticker])

            # Find common date range
            common_start = max(df.index.min() for df in dfs.values())
            common_end = min(df.index.max() for df in dfs.values())
            for t in tickers:
                dfs[t] = dfs[t].loc[common_start:common_end]

            if any(len(df) < 20 for df in dfs.values()):
                return {"error": True, "message": "Insufficient overlapping data (need >= 20 trading days)."}

            # Build daily returns for each asset
            asset_returns = pd.DataFrame({
                t: dfs[t]["close"].pct_change() for t in tickers
            }).dropna()

            # Portfolio simulation with rebalancing
            n_days = len(asset_returns)
            port_values = [float(initial_capital)]
            holdings = {t: initial_capital * weights[t] for t in tickers}
            rebalance_dates = []

            rebal_month_mod = 1 if rebalance_freq == "monthly" else 3

            for i in range(n_days):
                date = asset_returns.index[i]
                ret = asset_returns.iloc[i]

                # Update holdings by daily return
                for t in tickers:
                    holdings[t] *= (1 + ret[t]) if np.isfinite(ret[t]) else 1.0

                total = sum(holdings.values())
                port_values.append(total)

                # Check rebalance
                if i > 0:
                    prev_date = asset_returns.index[i - 1]
                    if date.month != prev_date.month and date.month % rebal_month_mod == 1:
                        for t in tickers:
                            holdings[t] = total * weights[t]
                        rebalance_dates.append(str(date.date()))

            port_values_arr = np.array(port_values[1:], dtype=float)
            equity = [
                {"date": str(asset_returns.index[i].date()), "value": round(port_values_arr[i])}
                for i in range(len(port_values_arr))
            ]

            # Per-asset contribution
            asset_contributions = {}
            for t in tickers:
                asset_ret = dfs[t]["close"].iloc[-1] / dfs[t]["close"].iloc[0] - 1
                asset_contributions[t] = {
                    "weight": weights[t],
                    "return_pct": round(float(asset_ret) * 100, 2),
                    "contribution_pct": round(float(asset_ret) * weights[t] * 100, 2),
                }

            metrics = self._calc_metrics(equity, [], initial_capital)

            return {
                "success": True,
                "data": {
                    "portfolio_metrics": metrics,
                    "final_value": equity[-1]["value"] if equity else initial_capital,
                    "rebalance_freq": rebalance_freq,
                    "rebalance_count": len(rebalance_dates),
                    "rebalance_dates": rebalance_dates,
                    "asset_contributions": asset_contributions,
                    "equity_curve": equity[::max(1, len(equity) // 500)],
                },
            }
        except Exception as e:
            logger.exception(f"Portfolio backtest failed: {e}")
            return {"error": True, "message": str(e)}

    def benchmark(
        self,
        ohlcv_data: List[Dict],
        strategy_name: str,
        benchmark_data: List[Dict],
        initial_capital: float = 10_000_000,
        commission: float = 0.0018,
        tax: float = 0.0018,
    ) -> Dict[str, Any]:
        """
        전략 vs 벤치마크 (Buy & Hold) 비교.

        Args:
            ohlcv_data: 전략 대상 OHLCV 데이터
            strategy_name: 전략 이름
            benchmark_data: 벤치마크 OHLCV 데이터 (KOSPI 등)
            initial_capital: 초기 자본금

        Returns:
            alpha, beta, information_ratio, tracking_error + 양쪽 성과
        """
        try:
            # Run strategy
            strat_result = self.run(ohlcv_data, strategy_name, initial_capital, commission, tax)
            if strat_result.get("error"):
                return strat_result

            # Build benchmark buy-and-hold
            bench_df = self._build_df(benchmark_data)
            bench_returns = bench_df["close"].pct_change().dropna()

            # Strategy equity → daily returns
            strat_equity = strat_result["data"]["equity_curve"]
            strat_values = np.array([e["value"] for e in strat_equity], dtype=float)
            strat_returns = np.diff(strat_values) / strat_values[:-1]

            # Align lengths
            min_len = min(len(strat_returns), len(bench_returns))
            if min_len < 20:
                return {"error": True, "message": "Insufficient overlapping data for benchmark comparison."}

            sr = strat_returns[:min_len]
            br = bench_returns.values[:min_len]

            # Filter non-finite
            mask = np.isfinite(sr) & np.isfinite(br)
            sr = sr[mask]
            br = br[mask]

            if len(sr) < 20:
                return {"error": True, "message": "Too few valid data points after filtering."}

            # Beta = Cov(strategy, benchmark) / Var(benchmark)
            cov_matrix = np.cov(sr, br)
            beta = float(cov_matrix[0, 1] / cov_matrix[1, 1]) if cov_matrix[1, 1] != 0 else 0.0

            # Alpha (annualized Jensen's alpha)
            alpha = float((np.mean(sr) - (self.RISK_FREE_RATE / 252 + beta * (np.mean(br) - self.RISK_FREE_RATE / 252))) * 252)

            # Tracking error
            excess = sr - br
            tracking_error = float(np.std(excess) * np.sqrt(252))

            # Information ratio
            info_ratio = float(np.mean(excess) * 252 / tracking_error) if tracking_error > 0 else 0.0

            # Benchmark buy-and-hold return
            bench_total_ret = float(bench_df["close"].iloc[-1] / bench_df["close"].iloc[0] - 1) * 100

            return {
                "success": True,
                "data": {
                    "strategy": {
                        "name": strategy_name,
                        "total_return_pct": strat_result["data"]["total_return_pct"],
                        "sharpe_ratio": strat_result["data"]["sharpe_ratio"],
                    },
                    "benchmark": {
                        "total_return_pct": round(bench_total_ret, 2),
                    },
                    "alpha": round(alpha * 100, 3),
                    "beta": round(beta, 3),
                    "information_ratio": round(info_ratio, 3),
                    "tracking_error_pct": round(tracking_error * 100, 2),
                    "outperformance_pct": round(
                        strat_result["data"]["total_return_pct"] - bench_total_ret, 2
                    ),
                },
            }
        except Exception as e:
            logger.exception(f"Benchmark comparison failed: {e}")
            return {"error": True, "message": str(e)}

    def risk_analysis(
        self,
        ohlcv_data: List[Dict],
        strategy_name: str,
        initial_capital: float = 10_000_000,
        commission: float = 0.0018,
        tax: float = 0.0018,
    ) -> Dict[str, Any]:
        """
        전략 리스크 분석.

        VaR (95%, 99%), CVaR, 연환산 변동성, 최대낙폭, Calmar ratio, Sortino ratio.

        Args:
            ohlcv_data: OHLCV 데이터
            strategy_name: 전략 이름
            initial_capital: 초기 자본금

        Returns:
            종합 리스크 지표
        """
        try:
            result = self.run(ohlcv_data, strategy_name, initial_capital, commission, tax)
            if result.get("error"):
                return result

            equity = result["data"]["equity_curve"]
            risk = self._calc_risk_metrics(equity, initial_capital)

            return {
                "success": True,
                "data": {
                    "strategy": strategy_name,
                    "initial_capital": initial_capital,
                    "final_value": result["data"]["final_value"],
                    "total_return_pct": result["data"]["total_return_pct"],
                    "risk_metrics": risk,
                },
            }
        except Exception as e:
            logger.exception(f"Risk analysis failed: {e}")
            return {"error": True, "message": str(e)}

    def signal_history(
        self,
        ohlcv_data: List[Dict],
        strategy_name: str,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        전략 시그널 히스토리 + 후행 수익률.

        각 시그널 발생일 이후 5/10/20/60일 수익률 분석.

        Args:
            ohlcv_data: OHLCV 데이터
            strategy_name: 전략 이름
            params: 전략 파라미터 오버라이드

        Returns:
            시그널 목록 + 후행 수익률 + 평균 수익률
        """
        try:
            if strategy_name not in STRATEGIES:
                return {"error": True, "message": f"Unknown strategy: {strategy_name}"}

            df = self._build_df(ohlcv_data)
            if len(df) < 60:
                return {"error": True, "message": f"Insufficient data: {len(df)} rows."}

            signals = self._get_signals(df, strategy_name, params)
            forward_periods = [5, 10, 20, 60]
            signal_records = []

            for i in range(len(signals)):
                sig = int(signals.iloc[i])
                if sig == 0:
                    continue

                date = df.index[i]
                signal_type = "BUY" if sig == 1 else "SELL"
                price = float(df.iloc[i]["close"])
                record = {
                    "date": str(date.date()),
                    "type": signal_type,
                    "price": round(price),
                }

                for period in forward_periods:
                    if i + period < len(df):
                        future_price = float(df.iloc[i + period]["close"])
                        fwd_ret = (future_price / price - 1) * 100
                        # For SELL signals, invert the return interpretation
                        if sig == -1:
                            fwd_ret = -fwd_ret
                        record[f"return_{period}d"] = round(fwd_ret, 2)
                    else:
                        record[f"return_{period}d"] = None

                signal_records.append(record)

            # Average returns by signal type
            avg_returns = {}
            for sig_type in ("BUY", "SELL"):
                type_records = [r for r in signal_records if r["type"] == sig_type]
                if type_records:
                    avg = {}
                    for period in forward_periods:
                        key = f"return_{period}d"
                        vals = [r[key] for r in type_records if r[key] is not None]
                        avg[key] = round(np.mean(vals), 2) if vals else None
                    avg["count"] = len(type_records)
                    avg_returns[sig_type] = avg

            return {
                "success": True,
                "data": {
                    "strategy": strategy_name,
                    "params": {**STRATEGIES[strategy_name]["params"], **(params or {})},
                    "total_signals": len(signal_records),
                    "avg_returns": avg_returns,
                    "signals": signal_records[-100:],  # last 100 signals to limit size
                },
            }
        except Exception as e:
            logger.exception(f"Signal history failed: {e}")
            return {"error": True, "message": str(e)}

    def drawdown_analysis(
        self,
        ohlcv_data: List[Dict],
        strategy_name: str,
        initial_capital: float = 10_000_000,
        commission: float = 0.0018,
        tax: float = 0.0018,
    ) -> Dict[str, Any]:
        """
        낙폭(Drawdown) 상세 분석.

        모든 낙폭 구간: 시작일, 종료일, 깊이, 회복일, 기간(일).

        Args:
            ohlcv_data: OHLCV 데이터
            strategy_name: 전략 이름
            initial_capital: 초기 자본금

        Returns:
            낙폭 구간 목록 (깊이 순 정렬) + 현재 낙폭
        """
        try:
            result = self.run(ohlcv_data, strategy_name, initial_capital, commission, tax)
            if result.get("error"):
                return result

            equity = result["data"]["equity_curve"]
            if len(equity) < 2:
                return {"error": True, "message": "Insufficient equity curve data."}

            values = np.array([e["value"] for e in equity], dtype=float)
            dates = [e["date"] for e in equity]

            peak = np.maximum.accumulate(values)
            dd_pct = (values - peak) / peak

            # Identify drawdown periods
            drawdowns = []
            in_dd = False
            dd_start = None
            dd_peak_val = None

            for i in range(len(values)):
                if dd_pct[i] < 0 and not in_dd:
                    in_dd = True
                    dd_start = i - 1 if i > 0 else 0
                    dd_peak_val = peak[i]
                elif dd_pct[i] >= 0 and in_dd:
                    in_dd = False
                    trough_idx = dd_start + np.argmin(values[dd_start:i + 1])
                    depth = float((values[trough_idx] - dd_peak_val) / dd_peak_val) * 100
                    drawdowns.append({
                        "start_date": dates[dd_start],
                        "trough_date": dates[trough_idx],
                        "recovery_date": dates[i],
                        "depth_pct": round(depth, 2),
                        "duration_days": (pd.Timestamp(dates[i]) - pd.Timestamp(dates[dd_start])).days,
                        "recovery_days": (pd.Timestamp(dates[i]) - pd.Timestamp(dates[trough_idx])).days,
                    })

            # Handle ongoing drawdown
            current_dd = None
            if in_dd and dd_start is not None:
                trough_idx = dd_start + np.argmin(values[dd_start:])
                depth = float((values[trough_idx] - dd_peak_val) / dd_peak_val) * 100
                current_dd = {
                    "start_date": dates[dd_start],
                    "trough_date": dates[trough_idx],
                    "recovery_date": None,
                    "depth_pct": round(depth, 2),
                    "duration_days": (pd.Timestamp(dates[-1]) - pd.Timestamp(dates[dd_start])).days,
                    "current_dd_pct": round(float(dd_pct[-1]) * 100, 2),
                }

            # Sort by depth (most severe first)
            drawdowns.sort(key=lambda x: x["depth_pct"])

            return {
                "success": True,
                "data": {
                    "strategy": strategy_name,
                    "total_drawdown_periods": len(drawdowns),
                    "max_drawdown_pct": drawdowns[0]["depth_pct"] if drawdowns else 0.0,
                    "avg_drawdown_pct": round(np.mean([d["depth_pct"] for d in drawdowns]), 2) if drawdowns else 0.0,
                    "avg_duration_days": round(np.mean([d["duration_days"] for d in drawdowns])) if drawdowns else 0,
                    "current_drawdown": current_dd,
                    "drawdowns": drawdowns[:20],  # top 20 worst
                },
            }
        except Exception as e:
            logger.exception(f"Drawdown analysis failed: {e}")
            return {"error": True, "message": str(e)}


# ── Standalone test ────────────────────────────────────────────────────
if __name__ == "__main__":
    import random

    logging.basicConfig(level=logging.INFO)
    adapter = BacktestAdapter()

    # Generate synthetic OHLCV data for testing
    print("Generating synthetic OHLCV data (500 days)...")
    base_price = 50000
    data = []
    for i in range(500):
        date = pd.Timestamp("2024-01-02") + pd.Timedelta(days=i)
        if date.weekday() >= 5:
            continue
        change = random.gauss(0, 0.02)
        base_price *= (1 + change)
        o = round(base_price * (1 + random.gauss(0, 0.005)))
        h = round(max(o, base_price) * (1 + abs(random.gauss(0, 0.01))))
        l = round(min(o, base_price) * (1 - abs(random.gauss(0, 0.01))))
        c = round(base_price)
        v = random.randint(100000, 1000000)
        data.append({"date": str(date.date()), "open": o, "high": h, "low": l, "close": c, "volume": v})

    print(f"Generated {len(data)} trading days")

    # Test run
    print("\n--- run (RSI_oversold) ---")
    res = adapter.run(data, "RSI_oversold")
    if res.get("success"):
        d = res["data"]
        print(f"  Return: {d['total_return_pct']}%, Sharpe: {d['sharpe_ratio']}, MaxDD: {d['max_drawdown_pct']}%, Trades: {d['total_trades']}")
    else:
        print(f"  ERROR: {res['message']}")

    # Test compare
    print("\n--- compare ---")
    res = adapter.compare(data, ["RSI_oversold", "MACD_crossover", "MA_cross"])
    if res.get("success"):
        for r in res["data"]["comparison"]:
            print(f"  {r['strategy']}: return={r.get('total_return_pct')}%, sharpe={r.get('sharpe_ratio')}")
    else:
        print(f"  ERROR: {res['message']}")

    # Test optimize
    print("\n--- optimize (RSI_oversold) ---")
    res = adapter.optimize(data, "RSI_oversold", {"period": [10, 14, 20], "buy_threshold": [25, 30], "sell_threshold": [65, 70, 75]})
    if res.get("success"):
        d = res["data"]
        print(f"  Best params: {d['best_params']}, Sharpe: {d['best_sharpe']}")
    else:
        print(f"  ERROR: {res['message']}")

    # Test signal_history
    print("\n--- signal_history (MACD_crossover) ---")
    res = adapter.signal_history(data, "MACD_crossover")
    if res.get("success"):
        d = res["data"]
        print(f"  Total signals: {d['total_signals']}, Avg returns: {d['avg_returns']}")
    else:
        print(f"  ERROR: {res['message']}")

    # Test risk_analysis
    print("\n--- risk_analysis (Bollinger_bounce) ---")
    res = adapter.risk_analysis(data, "Bollinger_bounce")
    if res.get("success"):
        d = res["data"]
        print(f"  Risk metrics: {d['risk_metrics']}")
    else:
        print(f"  ERROR: {res['message']}")

    print("\nAll tests complete.")
