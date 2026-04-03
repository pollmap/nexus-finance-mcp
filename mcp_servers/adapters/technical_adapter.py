"""Technical Analysis Adapter — RSI, MACD, BB, SMA, EMA, Stochastic, ATR, etc."""
import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class TechnicalAdapter:
    """Pure pandas/numpy technical indicator calculations."""

    def calculate_sma(self, prices: List[float], period: int = 20) -> List[Optional[float]]:
        """Simple Moving Average.

        Returns list same length as prices, with None for insufficient data points.
        """
        if not prices or period < 1:
            return []
        s = pd.Series(prices, dtype=float)
        sma = s.rolling(window=period, min_periods=period).mean()
        return [round(v, 6) if pd.notna(v) else None for v in sma]

    def calculate_ema(self, prices: List[float], period: int = 20) -> List[Optional[float]]:
        """Exponential Moving Average.

        Uses pandas ewm with span=period, adjust=False for standard EMA.
        """
        if not prices or period < 1:
            return []
        s = pd.Series(prices, dtype=float)
        ema = s.ewm(span=period, adjust=False).mean()
        # First (period-1) values are warming up; still return them
        return [round(v, 6) if pd.notna(v) else None for v in ema]

    def calculate_rsi(self, prices: List[float], period: int = 14) -> List[Optional[float]]:
        """Relative Strength Index (Wilder's smoothing).

        RSI = 100 - 100 / (1 + avg_gain / avg_loss)
        """
        if not prices or len(prices) < period + 1:
            return [None] * len(prices)

        s = pd.Series(prices, dtype=float)
        delta = s.diff()

        gain = delta.clip(lower=0)
        loss = (-delta.clip(upper=0))

        # Wilder's smoothing (equivalent to EMA with alpha=1/period)
        avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))

        result = [None] * len(prices)
        for i in range(len(prices)):
            if pd.notna(rsi.iloc[i]) and i >= period:
                result[i] = round(float(rsi.iloc[i]), 2)
        return result

    def calculate_macd(
        self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Dict[str, List[Optional[float]]]:
        """MACD (Moving Average Convergence Divergence).

        Returns: {"macd": [...], "signal": [...], "histogram": [...]}
        """
        if not prices or len(prices) < slow:
            n = len(prices)
            return {"macd": [None] * n, "signal": [None] * n, "histogram": [None] * n}

        s = pd.Series(prices, dtype=float)
        ema_fast = s.ewm(span=fast, adjust=False).mean()
        ema_slow = s.ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        def _to_list(series: pd.Series, min_idx: int) -> List[Optional[float]]:
            result = []
            for i, v in enumerate(series):
                if pd.notna(v) and i >= min_idx:
                    result.append(round(float(v), 6))
                else:
                    result.append(None)
            return result

        return {
            "macd": _to_list(macd_line, slow - 1),
            "signal": _to_list(signal_line, slow + signal - 2),
            "histogram": _to_list(histogram, slow + signal - 2),
        }

    def calculate_bollinger(
        self, prices: List[float], period: int = 20, std_dev: float = 2.0
    ) -> Dict[str, List[Optional[float]]]:
        """Bollinger Bands.

        Returns: {"upper": [...], "middle": [...], "lower": [...]}
        """
        if not prices or len(prices) < period:
            n = len(prices)
            return {"upper": [None] * n, "middle": [None] * n, "lower": [None] * n}

        s = pd.Series(prices, dtype=float)
        middle = s.rolling(window=period, min_periods=period).mean()
        rolling_std = s.rolling(window=period, min_periods=period).std()

        upper = middle + std_dev * rolling_std
        lower = middle - std_dev * rolling_std

        def _to_list(series: pd.Series) -> List[Optional[float]]:
            return [round(float(v), 6) if pd.notna(v) else None for v in series]

        return {
            "upper": _to_list(upper),
            "middle": _to_list(middle),
            "lower": _to_list(lower),
        }

    def calculate_stochastic(
        self,
        high: List[float],
        low: List[float],
        close: List[float],
        k_period: int = 14,
        d_period: int = 3,
    ) -> Dict[str, List[Optional[float]]]:
        """Stochastic Oscillator.

        %K = (close - lowest_low_n) / (highest_high_n - lowest_low_n) * 100
        %D = SMA(%K, d_period)

        Returns: {"k": [...], "d": [...]}
        """
        n = len(close)
        if n < k_period or len(high) != n or len(low) != n:
            return {"k": [None] * n, "d": [None] * n}

        h = pd.Series(high, dtype=float)
        l = pd.Series(low, dtype=float)
        c = pd.Series(close, dtype=float)

        lowest_low = l.rolling(window=k_period, min_periods=k_period).min()
        highest_high = h.rolling(window=k_period, min_periods=k_period).max()

        denom = highest_high - lowest_low
        # Avoid division by zero
        denom = denom.replace(0, np.nan)

        k_pct = ((c - lowest_low) / denom) * 100.0
        d_pct = k_pct.rolling(window=d_period, min_periods=d_period).mean()

        def _to_list(series: pd.Series) -> List[Optional[float]]:
            return [round(float(v), 2) if pd.notna(v) else None for v in series]

        return {"k": _to_list(k_pct), "d": _to_list(d_pct)}

    def calculate_atr(
        self, high: List[float], low: List[float], close: List[float], period: int = 14
    ) -> List[Optional[float]]:
        """Average True Range.

        TR = max(high-low, abs(high-prev_close), abs(low-prev_close))
        ATR = Wilder's smoothed TR over period.
        """
        n = len(close)
        if n < 2 or len(high) != n or len(low) != n:
            return [None] * n

        h = pd.Series(high, dtype=float)
        l = pd.Series(low, dtype=float)
        c = pd.Series(close, dtype=float)

        prev_close = c.shift(1)
        tr1 = h - l
        tr2 = (h - prev_close).abs()
        tr3 = (l - prev_close).abs()

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

        result: List[Optional[float]] = []
        for i, v in enumerate(atr):
            if pd.notna(v) and i >= period:
                result.append(round(float(v), 6))
            else:
                result.append(None)
        return result

    def calculate_indicators(
        self, data: List[Dict], indicators: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Calculate multiple technical indicators on OHLCV data.

        Args:
            data: List of dicts with keys: date, open, high, low, close, volume.
            indicators: List of indicator names. Default:
                ["sma_20", "sma_50", "ema_12", "ema_26", "rsi_14", "macd", "bb_20"]

        Returns:
            {"success": True, "count": N, "data": [...with indicator columns...]}
        """
        if not data:
            return {"success": False, "error": "No data provided."}

        if indicators is None:
            indicators = ["sma_20", "sma_50", "ema_12", "ema_26", "rsi_14", "macd", "bb_20"]

        try:
            df = pd.DataFrame(data)
            required = {"close"}
            if not required.issubset(set(df.columns)):
                return {"success": False, "error": "Data must contain at least 'close' column."}

            closes = df["close"].astype(float).tolist()
            highs = df["high"].astype(float).tolist() if "high" in df.columns else None
            lows = df["low"].astype(float).tolist() if "low" in df.columns else None

            for ind in indicators:
                ind_lower = ind.lower().strip()

                if ind_lower.startswith("sma_"):
                    period = int(ind_lower.split("_")[1])
                    df[ind_lower] = self.calculate_sma(closes, period)

                elif ind_lower.startswith("ema_"):
                    period = int(ind_lower.split("_")[1])
                    df[ind_lower] = self.calculate_ema(closes, period)

                elif ind_lower.startswith("rsi"):
                    period = 14
                    if "_" in ind_lower:
                        period = int(ind_lower.split("_")[1])
                    df[f"rsi_{period}"] = self.calculate_rsi(closes, period)

                elif ind_lower == "macd":
                    macd_result = self.calculate_macd(closes)
                    df["macd"] = macd_result["macd"]
                    df["macd_signal"] = macd_result["signal"]
                    df["macd_histogram"] = macd_result["histogram"]

                elif ind_lower.startswith("bb"):
                    period = 20
                    if "_" in ind_lower:
                        period = int(ind_lower.split("_")[1])
                    bb_result = self.calculate_bollinger(closes, period)
                    df[f"bb_upper_{period}"] = bb_result["upper"]
                    df[f"bb_middle_{period}"] = bb_result["middle"]
                    df[f"bb_lower_{period}"] = bb_result["lower"]

                elif ind_lower.startswith("stoch"):
                    if highs and lows:
                        stoch = self.calculate_stochastic(highs, lows, closes)
                        df["stoch_k"] = stoch["k"]
                        df["stoch_d"] = stoch["d"]

                elif ind_lower.startswith("atr"):
                    period = 14
                    if "_" in ind_lower:
                        period = int(ind_lower.split("_")[1])
                    if highs and lows:
                        df[f"atr_{period}"] = self.calculate_atr(highs, lows, closes, period)

                else:
                    logger.warning("Unknown indicator: %s", ind)

            # Replace NaN with None for JSON serialization
            df = df.where(pd.notna(df), None)

            return {
                "success": True,
                "source": "technical_analysis",
                "count": len(df),
                "indicators_calculated": indicators,
                "data": df.to_dict(orient="records"),
            }

        except Exception as e:
            logger.error("calculate_indicators error: %s", e, exc_info=True)
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ta = TechnicalAdapter()

    # Quick self-test with synthetic data
    prices = [float(100 + i * 0.5 + (i % 7) * 0.3) for i in range(60)]
    print("SMA(20) last 5:", ta.calculate_sma(prices, 20)[-5:])
    print("EMA(12) last 5:", ta.calculate_ema(prices, 12)[-5:])
    print("RSI(14) last 5:", ta.calculate_rsi(prices, 14)[-5:])
    macd = ta.calculate_macd(prices)
    print("MACD last 3:", macd["macd"][-3:])
    bb = ta.calculate_bollinger(prices)
    print("BB upper last 3:", bb["upper"][-3:])
