"""
Technical Analysis MCP Server — 5 tools.
"""
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP
from mcp_servers.adapters.technical_adapter import TechnicalAdapter

logger = logging.getLogger(__name__)


class TechnicalServer:
    def __init__(self):
        self._ta = TechnicalAdapter()
        self.mcp = FastMCP("technical-analysis")
        self._register_tools()
        logger.info("Technical Analysis MCP Server initialized")

    def _extract_prices(self, data: List[Dict]) -> Dict[str, List[float]]:
        """Extract close, high, low, volume lists from OHLCV data."""
        closes = [float(d["close"]) for d in data]
        highs = [float(d["high"]) for d in data] if all("high" in d for d in data) else []
        lows = [float(d["low"]) for d in data] if all("low" in d for d in data) else []
        volumes = [float(d.get("volume", 0)) for d in data]
        return {"close": closes, "high": highs, "low": lows, "volume": volumes}

    def _register_tools(self):

        @self.mcp.tool()
        def ta_indicators(data: list, indicators: list = None) -> dict:
            """기술 지표 종합 계산. OHLCV 데이터 입력 → SMA, EMA, RSI, MACD, BB 등 계산.
            indicators 예시: ["sma_20", "sma_50", "ema_12", "ema_26", "rsi_14", "macd", "bb_20", "stoch", "atr_14"]"""
            return self._ta.calculate_indicators(data, indicators)

        @self.mcp.tool()
        def ta_rsi(data: list, period: int = 14) -> dict:
            """RSI(상대강도지수) 계산. period 기본값 14."""
            try:
                prices = self._extract_prices(data)
                rsi = self._ta.calculate_rsi(prices["close"], period)
                latest = next((v for v in reversed(rsi) if v is not None), None)
                signal = None
                if latest is not None:
                    if latest >= 70:
                        signal = "overbought"
                    elif latest <= 30:
                        signal = "oversold"
                    else:
                        signal = "neutral"
                return {
                    "success": True,
                    "source": "technical_analysis",
                    "indicator": f"RSI({period})",
                    "latest_value": latest,
                    "signal": signal,
                    "count": len(rsi),
                    "data": rsi,
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.mcp.tool()
        def ta_macd(data: list, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
            """MACD 계산. fast=12, slow=26, signal=9."""
            try:
                prices = self._extract_prices(data)
                macd_result = self._ta.calculate_macd(prices["close"], fast, slow, signal)
                # Latest values
                latest_macd = next((v for v in reversed(macd_result["macd"]) if v is not None), None)
                latest_signal = next((v for v in reversed(macd_result["signal"]) if v is not None), None)
                latest_hist = next((v for v in reversed(macd_result["histogram"]) if v is not None), None)

                trend = None
                if latest_hist is not None:
                    trend = "bullish" if latest_hist > 0 else "bearish"

                return {
                    "success": True,
                    "source": "technical_analysis",
                    "indicator": f"MACD({fast},{slow},{signal})",
                    "latest": {
                        "macd": latest_macd,
                        "signal": latest_signal,
                        "histogram": latest_hist,
                    },
                    "trend": trend,
                    "count": len(macd_result["macd"]),
                    "data": macd_result,
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.mcp.tool()
        def ta_bollinger(data: list, period: int = 20, std_dev: float = 2.0) -> dict:
            """볼린저 밴드 계산. period=20, std_dev=2.0."""
            try:
                prices = self._extract_prices(data)
                bb = self._ta.calculate_bollinger(prices["close"], period, std_dev)
                latest_close = prices["close"][-1] if prices["close"] else None
                latest_upper = next((v for v in reversed(bb["upper"]) if v is not None), None)
                latest_lower = next((v for v in reversed(bb["lower"]) if v is not None), None)

                position = None
                if latest_close is not None and latest_upper is not None and latest_lower is not None:
                    if latest_close >= latest_upper:
                        position = "above_upper_band"
                    elif latest_close <= latest_lower:
                        position = "below_lower_band"
                    else:
                        position = "within_bands"

                return {
                    "success": True,
                    "source": "technical_analysis",
                    "indicator": f"BB({period},{std_dev})",
                    "latest": {
                        "upper": latest_upper,
                        "middle": next((v for v in reversed(bb["middle"]) if v is not None), None),
                        "lower": latest_lower,
                        "close": latest_close,
                    },
                    "position": position,
                    "count": len(bb["upper"]),
                    "data": bb,
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.mcp.tool()
        def ta_summary(data: list) -> dict:
            """기술 분석 종합 요약. 모든 주요 지표 계산 + 매수/매도 시그널 생성."""
            try:
                prices = self._extract_prices(data)
                closes = prices["close"]
                if not closes:
                    return {"success": False, "error": "No close prices in data."}

                latest_close = closes[-1]
                signals = {"buy": [], "sell": [], "neutral": []}

                # RSI
                rsi_vals = self._ta.calculate_rsi(closes, 14)
                latest_rsi = next((v for v in reversed(rsi_vals) if v is not None), None)
                if latest_rsi is not None:
                    if latest_rsi <= 30:
                        signals["buy"].append(f"RSI(14)={latest_rsi:.1f} — oversold")
                    elif latest_rsi >= 70:
                        signals["sell"].append(f"RSI(14)={latest_rsi:.1f} — overbought")
                    else:
                        signals["neutral"].append(f"RSI(14)={latest_rsi:.1f}")

                # MACD
                macd_result = self._ta.calculate_macd(closes)
                latest_hist = next((v for v in reversed(macd_result["histogram"]) if v is not None), None)
                if latest_hist is not None:
                    if latest_hist > 0:
                        signals["buy"].append(f"MACD histogram={latest_hist:.4f} — bullish")
                    else:
                        signals["sell"].append(f"MACD histogram={latest_hist:.4f} — bearish")

                # Bollinger Bands
                bb = self._ta.calculate_bollinger(closes, 20)
                latest_upper = next((v for v in reversed(bb["upper"]) if v is not None), None)
                latest_lower = next((v for v in reversed(bb["lower"]) if v is not None), None)
                if latest_upper is not None and latest_lower is not None:
                    if latest_close >= latest_upper:
                        signals["sell"].append(f"Price at/above upper BB ({latest_upper:.2f})")
                    elif latest_close <= latest_lower:
                        signals["buy"].append(f"Price at/below lower BB ({latest_lower:.2f})")
                    else:
                        signals["neutral"].append("Price within Bollinger Bands")

                # SMA crossover (20 vs 50)
                sma20 = self._ta.calculate_sma(closes, 20)
                sma50 = self._ta.calculate_sma(closes, 50)
                latest_sma20 = next((v for v in reversed(sma20) if v is not None), None)
                latest_sma50 = next((v for v in reversed(sma50) if v is not None), None)
                if latest_sma20 is not None and latest_sma50 is not None:
                    if latest_sma20 > latest_sma50:
                        signals["buy"].append(f"SMA20({latest_sma20:.2f}) > SMA50({latest_sma50:.2f}) — golden cross tendency")
                    else:
                        signals["sell"].append(f"SMA20({latest_sma20:.2f}) < SMA50({latest_sma50:.2f}) — death cross tendency")

                # Stochastic
                if prices["high"] and prices["low"]:
                    stoch = self._ta.calculate_stochastic(prices["high"], prices["low"], closes)
                    latest_k = next((v for v in reversed(stoch["k"]) if v is not None), None)
                    if latest_k is not None:
                        if latest_k <= 20:
                            signals["buy"].append(f"Stochastic %K={latest_k:.1f} — oversold")
                        elif latest_k >= 80:
                            signals["sell"].append(f"Stochastic %K={latest_k:.1f} — overbought")
                        else:
                            signals["neutral"].append(f"Stochastic %K={latest_k:.1f}")

                    # ATR
                    atr = self._ta.calculate_atr(prices["high"], prices["low"], closes)
                    latest_atr = next((v for v in reversed(atr) if v is not None), None)
                else:
                    latest_atr = None

                buy_count = len(signals["buy"])
                sell_count = len(signals["sell"])
                if buy_count > sell_count:
                    overall = "BUY"
                elif sell_count > buy_count:
                    overall = "SELL"
                else:
                    overall = "NEUTRAL"

                return {
                    "success": True,
                    "source": "technical_analysis",
                    "latest_close": latest_close,
                    "overall_signal": overall,
                    "signal_score": f"{buy_count} buy / {sell_count} sell / {len(signals['neutral'])} neutral",
                    "signals": signals,
                    "indicators": {
                        "rsi_14": latest_rsi,
                        "macd_histogram": latest_hist,
                        "sma_20": latest_sma20,
                        "sma_50": latest_sma50,
                        "bb_upper": latest_upper,
                        "bb_lower": latest_lower,
                        "atr_14": latest_atr,
                    },
                }

            except Exception as e:
                logger.error("ta_summary error: %s", e, exc_info=True)
                return {"success": False, "error": str(e)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    TechnicalServer().mcp.run(transport="stdio")
