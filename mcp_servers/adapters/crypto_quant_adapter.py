"""
Crypto Derivatives & Funding Rate Adapter.

1. funding_rate: Perpetual futures funding rate (current + history)
2. basis_term: Futures basis term structure (spot vs futures)
3. funding_arb: Funding rate arbitrage scanner across symbols
4. open_interest: Open interest and leverage metrics
5. liquidation_levels: Estimate liquidation cascade price levels
6. carry_backtest: Funding rate carry strategy backtest

References:
- ScienceDirect 2025: BTC/ETH/SOL funding arb, up to 115.9% over 6 months
- CoinGlass real-time funding rates across exchanges
"""
import logging
import sys
import os
import warnings
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=RuntimeWarning)


class CryptoQuantAdapter:
    """Crypto derivatives quantitative analysis."""

    def __init__(self):
        self._exchange_cache = {}

    def _get_exchange(self, exchange_id: str = "binance"):
        """Lazy-load ccxt exchange."""
        if exchange_id not in self._exchange_cache:
            try:
                import ccxt
                exchange_class = getattr(ccxt, exchange_id)
                self._exchange_cache[exchange_id] = exchange_class({
                    "enableRateLimit": True,
                    "options": {"defaultType": "swap"},  # perpetual futures
                })
            except Exception as e:
                logger.error(f"Failed to init {exchange_id}: {e}")
                return None
        return self._exchange_cache[exchange_id]

    # ------------------------------------------------------------------
    # 1. Funding Rate
    # ------------------------------------------------------------------
    def funding_rate(
        self, symbol: str = "BTC/USDT:USDT", exchange_id: str = "binance",
    ) -> Dict[str, Any]:
        """Get current and recent funding rates for a perpetual futures contract."""
        try:
            exchange = self._get_exchange(exchange_id)
            if not exchange:
                return error_response(f"Cannot initialize {exchange_id}")

            # Current funding rate
            try:
                funding = exchange.fetch_funding_rate(symbol)
            except Exception as e:
                return error_response(f"fetch_funding_rate failed: {e}")

            rate = funding.get("fundingRate", 0) or 0
            next_time = funding.get("fundingDatetime", "")
            mark_price = funding.get("markPrice", 0)
            index_price = funding.get("indexPrice", 0)

            # Annualized (3 funding periods per day × 365)
            annualized = rate * 3 * 365

            # Funding rate history (if available)
            history = []
            try:
                rates = exchange.fetch_funding_rate_history(symbol, limit=200)
                for r in rates:
                    fr = r.get("fundingRate", 0) or 0
                    history.append({
                        "datetime": r.get("datetime", ""),
                        "rate": round(float(fr), 6),
                        "annualized": round(float(fr * 3 * 365), 4),
                    })
            except Exception:
                pass  # Not all exchanges support history

            # Average funding rate
            if history:
                avg_rate = np.mean([h["rate"] for h in history])
                avg_annualized = avg_rate * 3 * 365
            else:
                avg_rate = rate
                avg_annualized = annualized

            return success_response(
                {
                    "symbol": symbol,
                    "exchange": exchange_id,
                    "current_rate": round(float(rate), 6),
                    "annualized_rate": round(float(annualized), 4),
                    "avg_rate_30": round(float(avg_rate), 6),
                    "avg_annualized_30": round(float(avg_annualized), 4),
                    "mark_price": round(float(mark_price), 2) if mark_price else None,
                    "index_price": round(float(index_price), 2) if index_price else None,
                    "next_funding": next_time,
                    "history": history[-10:],
                    "interpretation": (
                        f"{symbol} funding: {rate:.4%} ({annualized:.1%} ann). "
                        f"{'Longs pay shorts' if rate > 0 else 'Shorts pay longs'}. "
                        f"{'HIGH carry opportunity!' if abs(annualized) > 0.20 else 'Moderate carry.' if abs(annualized) > 0.05 else 'Low carry.'}"
                    ),
                },
                source="Crypto Quant",
            )
        except Exception as e:
            logger.exception("funding_rate failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 2. Basis Term Structure
    # ------------------------------------------------------------------
    def basis_term(
        self, base: str = "BTC", exchange_id: str = "binance",
    ) -> Dict[str, Any]:
        """Compute futures basis term structure: spot vs futures prices."""
        try:
            exchange = self._get_exchange(exchange_id)
            if not exchange:
                return error_response(f"Cannot initialize {exchange_id}")

            # Get spot price
            spot_exchange = self._get_exchange(exchange_id)
            # Switch to spot temporarily
            import ccxt
            spot_ex = getattr(ccxt, exchange_id)({"enableRateLimit": True})
            spot_symbol = f"{base}/USDT"

            try:
                spot_ticker = spot_ex.fetch_ticker(spot_symbol)
                spot_price = spot_ticker.get("last", 0)
            except Exception:
                spot_price = 0

            if not spot_price:
                return error_response(f"Cannot fetch spot price for {base}/USDT")

            # Get perpetual price
            perp_symbol = f"{base}/USDT:USDT"
            try:
                perp_ticker = exchange.fetch_ticker(perp_symbol)
                perp_price = perp_ticker.get("last", 0)
            except Exception:
                perp_price = spot_price

            # Basis
            basis = perp_price - spot_price
            basis_pct = basis / spot_price * 100 if spot_price > 0 else 0

            # Annualized basis (assuming perpetual = ~7 day effective)
            basis_annualized = basis_pct * 365 / 7  # rough

            # Try to get quarterly futures
            quarterly_data = []
            try:
                markets = exchange.load_markets()
                for sym, mkt in markets.items():
                    if mkt.get("base") == base and mkt.get("quote") == "USDT" and mkt.get("expiry"):
                        try:
                            ticker = exchange.fetch_ticker(sym)
                            fut_price = ticker.get("last", 0)
                            if fut_price and fut_price > 0:
                                exp = mkt.get("expiry", 0)
                                days_to_exp = max(1, (exp - pd.Timestamp.now().timestamp() * 1000) / (86400 * 1000)) if exp else 90
                                fb = (fut_price - spot_price) / spot_price * 100
                                fb_ann = fb * 365 / days_to_exp
                                quarterly_data.append({
                                    "symbol": sym,
                                    "price": round(float(fut_price), 2),
                                    "basis_pct": round(float(fb), 4),
                                    "annualized_pct": round(float(fb_ann), 2),
                                    "days_to_expiry": round(float(days_to_exp), 0),
                                })
                        except Exception:
                            continue
            except Exception:
                pass

            return success_response(
                {
                    "base": base,
                    "exchange": exchange_id,
                    "spot_price": round(float(spot_price), 2),
                    "perpetual_price": round(float(perp_price), 2),
                    "perp_basis_pct": round(float(basis_pct), 4),
                    "perp_basis_annualized_pct": round(float(basis_annualized), 2),
                    "quarterly_futures": quarterly_data,
                    "structure": "contango" if basis_pct > 0 else "backwardation",
                    "interpretation": (
                        f"{base} basis: {basis_pct:.3f}% "
                        f"({'contango — futures premium' if basis_pct > 0 else 'backwardation — futures discount'}). "
                        f"Annualized: ~{basis_annualized:.1f}%. "
                        f"{'Cash-and-carry opportunity!' if abs(basis_annualized) > 10 else 'Normal.'}"
                    ),
                },
                source="Crypto Quant",
            )
        except Exception as e:
            logger.exception("basis_term failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 3. Funding Rate Arbitrage Scanner
    # ------------------------------------------------------------------
    def funding_arb(
        self,
        symbols: Optional[List[str]] = None,
        exchange_id: str = "binance",
        min_annualized: float = 0.05,
    ) -> Dict[str, Any]:
        """Scan multiple symbols for funding rate arbitrage opportunities."""
        try:
            exchange = self._get_exchange(exchange_id)
            if not exchange:
                return error_response(f"Cannot initialize {exchange_id}")

            if not symbols:
                symbols = [
                    "BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT",
                    "BNB/USDT:USDT", "XRP/USDT:USDT", "DOGE/USDT:USDT",
                    "ADA/USDT:USDT", "AVAX/USDT:USDT", "DOT/USDT:USDT",
                    "MATIC/USDT:USDT",
                ]

            opportunities = []
            for sym in symbols:
                try:
                    funding = exchange.fetch_funding_rate(sym)
                    rate = funding.get("fundingRate", 0) or 0
                    ann = rate * 3 * 365

                    if abs(ann) >= min_annualized:
                        opportunities.append({
                            "symbol": sym,
                            "funding_rate": round(float(rate), 6),
                            "annualized": round(float(ann), 4),
                            "direction": "long_spot_short_perp" if rate > 0 else "short_spot_long_perp",
                            "estimated_daily_carry": round(float(rate * 3), 6),
                        })
                except Exception as e:
                    logger.debug(f"Skipping {sym}: {e}")
                    continue

            # Sort by absolute annualized
            opportunities.sort(key=lambda x: abs(x["annualized"]), reverse=True)

            return success_response(
                {
                    "opportunities": opportunities,
                    "n_scanned": len(symbols),
                    "n_opportunities": len(opportunities),
                    "exchange": exchange_id,
                    "min_annualized_threshold": min_annualized,
                    "interpretation": (
                        f"{len(opportunities)} carry opportunities found "
                        f"(>{min_annualized:.0%} ann) across {len(symbols)} symbols. "
                        f"Top: {opportunities[0]['symbol']} at {opportunities[0]['annualized']:.1%} ann."
                        if opportunities else f"No opportunities above {min_annualized:.0%} threshold."
                    ),
                },
                source="Crypto Quant",
            )
        except Exception as e:
            logger.exception("funding_arb failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 4. Open Interest
    # ------------------------------------------------------------------
    def open_interest(
        self, symbol: str = "BTC/USDT:USDT", exchange_id: str = "binance",
    ) -> Dict[str, Any]:
        """Get open interest and estimated leverage metrics."""
        try:
            exchange = self._get_exchange(exchange_id)
            if not exchange:
                return error_response(f"Cannot initialize {exchange_id}")

            try:
                oi = exchange.fetch_open_interest(symbol)
            except Exception as e:
                return error_response(f"fetch_open_interest failed: {e}")

            oi_value = oi.get("openInterestAmount", 0) or oi.get("openInterest", 0)
            oi_notional = oi.get("openInterestValue", 0) or 0

            # Get ticker for context
            try:
                ticker = exchange.fetch_ticker(symbol)
                price = ticker.get("last", 0)
                volume_24h = ticker.get("quoteVolume", 0) or 0
            except Exception:
                price = 0
                volume_24h = 0

            # OI/Volume ratio (leverage proxy)
            oi_vol_ratio = oi_notional / volume_24h if volume_24h > 0 else 0

            return success_response(
                {
                    "symbol": symbol,
                    "exchange": exchange_id,
                    "open_interest": round(float(oi_value), 4),
                    "open_interest_usd": round(float(oi_notional), 2),
                    "price": round(float(price), 2),
                    "volume_24h_usd": round(float(volume_24h), 2),
                    "oi_volume_ratio": round(float(oi_vol_ratio), 3),
                    "interpretation": (
                        f"{symbol} OI: ${oi_notional:,.0f}. "
                        f"24h volume: ${volume_24h:,.0f}. "
                        f"OI/Vol ratio: {oi_vol_ratio:.2f} "
                        f"({'high leverage' if oi_vol_ratio > 2 else 'moderate' if oi_vol_ratio > 0.5 else 'low leverage'})."
                    ),
                },
                source="Crypto Quant",
            )
        except Exception as e:
            logger.exception("open_interest failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 5. Liquidation Levels
    # ------------------------------------------------------------------
    def liquidation_levels(
        self, symbol: str = "BTC/USDT:USDT", exchange_id: str = "binance",
        leverage_levels: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Estimate liquidation cascade levels based on common leverage."""
        try:
            exchange = self._get_exchange(exchange_id)
            if not exchange:
                return error_response(f"Cannot initialize {exchange_id}")

            if not leverage_levels:
                leverage_levels = [2, 3, 5, 10, 20, 25, 50, 100]

            try:
                ticker = exchange.fetch_ticker(symbol)
                price = ticker.get("last", 0)
            except Exception as e:
                return error_response(f"fetch_ticker failed: {e}")

            if not price:
                return error_response("Cannot get price")

            # Liquidation prices for longs and shorts at each leverage
            levels = []
            for lev in leverage_levels:
                # Long liquidation: price * (1 - 1/leverage) approximately
                # (simplified, ignoring maintenance margin)
                long_liq = price * (1 - 1 / lev)
                long_drop_pct = (price - long_liq) / price * 100

                # Short liquidation: price * (1 + 1/leverage)
                short_liq = price * (1 + 1 / lev)
                short_rise_pct = (short_liq - price) / price * 100

                levels.append({
                    "leverage": lev,
                    "long_liquidation": round(float(long_liq), 2),
                    "long_drop_pct": round(float(long_drop_pct), 2),
                    "short_liquidation": round(float(short_liq), 2),
                    "short_rise_pct": round(float(short_rise_pct), 2),
                })

            return success_response(
                {
                    "symbol": symbol,
                    "current_price": round(float(price), 2),
                    "levels": levels,
                    "high_risk_zone": {
                        "long_cascade_below": round(float(price * 0.95), 2),
                        "short_cascade_above": round(float(price * 1.05), 2),
                        "note": "5% move can trigger 20x liquidations",
                    },
                    "interpretation": (
                        f"{symbol} at ${price:,.2f}. "
                        f"10x longs liquidated at ${price * 0.9:,.2f} (-10%), "
                        f"20x at ${price * 0.95:,.2f} (-5%). "
                        f"Cascade risk highest near round numbers."
                    ),
                },
                source="Crypto Quant",
            )
        except Exception as e:
            logger.exception("liquidation_levels failed")
            return error_response(str(e))

    # ------------------------------------------------------------------
    # 6. Carry Backtest
    # ------------------------------------------------------------------
    def carry_backtest(
        self,
        series: List[Dict],
        funding_rates: List[Dict],
        initial_capital: float = 10000,
    ) -> Dict[str, Any]:
        """Backtest funding rate carry strategy: long spot + short perp.

        Collect funding when positive, pay when negative.
        """
        try:
            # Parse price series
            pdf = pd.DataFrame(series)
            pdf["date"] = pd.to_datetime(pdf["date"])
            pdf = pdf.sort_values("date").set_index("date")
            prices = pdf["value"].astype(float)

            # Parse funding rate series
            fdf = pd.DataFrame(funding_rates)
            fdf["date"] = pd.to_datetime(fdf["date"])
            fdf = fdf.sort_values("date").set_index("date")
            rates = fdf["value"].astype(float)

            # Align
            df = pd.DataFrame({"price": prices, "rate": rates}).dropna()
            if len(df) < 10:
                return error_response(f"Only {len(df)} aligned observations")

            # Simulate carry strategy
            # Position: long 1 unit spot + short 1 unit perp
            # PnL = spot PnL + perp PnL + funding collected
            # For delta-neutral: spot PnL and perp PnL cancel → only funding remains
            # Plus basis change

            capital = initial_capital
            daily_pnl = []
            cumulative = [capital]

            for i in range(1, len(df)):
                price_change_pct = (df["price"].iloc[i] - df["price"].iloc[i - 1]) / df["price"].iloc[i - 1]
                funding_collected = df["rate"].iloc[i] * capital  # funding on notional

                # Basis risk: small P&L from basis change
                basis_pnl = 0  # simplified: assume perfect delta-neutral

                day_pnl = funding_collected + basis_pnl
                capital += day_pnl
                daily_pnl.append(float(day_pnl))
                cumulative.append(float(capital))

            pnl_arr = np.array(daily_pnl)
            total_return = (capital - initial_capital) / initial_capital
            n_days = len(daily_pnl)
            ann_return = total_return * 365 / n_days if n_days > 0 else 0

            # Sharpe
            if np.std(pnl_arr) > 0:
                sharpe = float(np.mean(pnl_arr) / np.std(pnl_arr) * np.sqrt(365))
            else:
                sharpe = 0

            # Max drawdown
            cum_arr = np.array(cumulative)
            peak = np.maximum.accumulate(cum_arr)
            dd = (cum_arr - peak) / peak
            max_dd = float(np.min(dd))

            # Win rate
            win_days = int(np.sum(pnl_arr > 0))
            total_days = len(pnl_arr)

            return success_response(
                {
                    "total_return_pct": round(float(total_return * 100), 2),
                    "annualized_return_pct": round(float(ann_return * 100), 2),
                    "sharpe_ratio": round(sharpe, 3),
                    "max_drawdown_pct": round(float(max_dd * 100), 2),
                    "win_rate": round(win_days / total_days, 3) if total_days > 0 else 0,
                    "n_days": n_days,
                    "initial_capital": initial_capital,
                    "final_capital": round(float(capital), 2),
                    "avg_daily_pnl": round(float(np.mean(pnl_arr)), 2),
                    "interpretation": (
                        f"Carry backtest: {total_return:.1%} total ({ann_return:.1%} ann). "
                        f"Sharpe: {sharpe:.2f}. Max DD: {max_dd:.1%}. "
                        f"Win rate: {win_days}/{total_days} days."
                    ),
                },
                source="Crypto Quant",
            )
        except Exception as e:
            logger.exception("carry_backtest failed")
            return error_response(str(e))
