"""
Backtest MCP Server - 전략 백테스팅 엔진.

OHLCV 가격 데이터에 대한 매매 전략 시뮬레이션.

Tools:
- backtest_run: 단일 전략 백테스트 실행
- backtest_compare: 복수 전략 비교
- backtest_optimize: 파라미터 최적화 (Grid Search)
- backtest_portfolio: 포트폴리오 백테스트 (리밸런싱)
- backtest_benchmark: 전략 vs 벤치마크 비교
- backtest_risk: 리스크 분석 (VaR, CVaR, Sortino 등)
- backtest_signal_history: 시그널 히스토리 + 후행 수익률
- backtest_drawdown: 낙폭 상세 분석

Built-in strategies: RSI_oversold, MACD_crossover, Bollinger_bounce, MA_cross, Mean_reversion, Momentum

Run standalone: python -m mcp_servers.servers.backtest_server
"""
import logging
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.core.base_server import BaseMCPServer
from mcp_servers.adapters.backtest_adapter import BacktestAdapter, STRATEGIES

logger = logging.getLogger(__name__)


class BacktestServer(BaseMCPServer):
    """Backtest MCP Server wrapping BacktestAdapter."""

    @property
    def name(self) -> str:
        return "backtest"

    def __init__(self, **kwargs):
        self._adapter = BacktestAdapter()
        super().__init__(**kwargs)

    def _register_tools(self):
        adapter = self._adapter

        @self.mcp.tool()
        def backtest_run(
            ohlcv_data: list,
            strategy_name: str,
            initial_capital: float = 10_000_000,
            commission: float = 0.0018,
            tax: float = 0.0018,
            params: Optional[dict] = None,
            stop_loss: Optional[float] = None,
            take_profit: Optional[float] = None,
            position_size: float = 0.95,
            allow_short: bool = False,
        ) -> dict:
            """
            전략 백테스트 실행 (커스텀 전략/복합 조건/손익절/공매도 지원).

            Args:
                ohlcv_data: OHLCV 가격 데이터 (list[dict] with date, open, high, low, close, volume)
                strategy_name: 전략 이름. 내장: RSI_oversold, MACD_crossover, Bollinger_bounce, MA_cross, Mean_reversion, Momentum.
                    특수: "combo" (복합 AND/OR), "custom" (사용자 정의 규칙)
                initial_capital: 초기 자본금 (기본 1,000만원)
                commission: 매매수수료 (기본 0.18% 한국, 0 미국)
                tax: 증권거래세 (기본 0.18% 한국, 0 미국)
                params: 전략 파라미터 오버라이드. combo용: {"strategies": ["RSI_oversold","MACD_crossover"], "mode": "all"}.
                    custom용: {"buy_rules": [{"indicator":"RSI","op":"<","value":30}], "sell_rules": [{"indicator":"RSI","op":">","value":70}]}
                stop_loss: 손절 비율 (예: 0.05 = -5%에서 자동 매도, None=비활성)
                take_profit: 익절 비율 (예: 0.10 = +10%에서 자동 매도, None=비활성)
                position_size: 자본 대비 포지션 비중 (0.0~1.0, 기본 0.95)
                allow_short: 공매도 허용 (기본 False)

            Returns:
                수익률, Sharpe, 최대낙폭, 승률, 매매내역, 자산곡선
            """
            return adapter.run(
                ohlcv_data, strategy_name, initial_capital, commission, tax,
                params, stop_loss, take_profit, position_size, allow_short,
            )

        @self.mcp.tool()
        def backtest_compare(
            ohlcv_data: list,
            strategy_names: list,
            initial_capital: float = 10_000_000,
        ) -> dict:
            """
            복수 전략 비교 백테스트. Compare multiple strategies on the same data.

            Args:
                ohlcv_data: OHLCV 가격 데이터
                strategy_names: 비교할 전략 이름 목록 (예: ["RSI_oversold", "MACD_crossover"])
                initial_capital: 초기 자본금 (기본 1,000만원)

            Returns:
                전략별 수익률, Sharpe, 최대낙폭 비교 테이블 + 최적 전략
            """
            return adapter.compare(ohlcv_data, strategy_names, initial_capital)

        @self.mcp.tool()
        def backtest_optimize(
            ohlcv_data: list,
            strategy_name: str,
            param_ranges: dict,
            initial_capital: float = 10_000_000,
        ) -> dict:
            """
            전략 파라미터 최적화 (Grid Search). Optimize strategy parameters.

            Args:
                ohlcv_data: OHLCV 가격 데이터
                strategy_name: 전략 이름
                param_ranges: 파라미터별 탐색 범위 (예: {"period": [10, 14, 20], "buy_threshold": [25, 30, 35]})
                initial_capital: 초기 자본금

            Returns:
                최적 파라미터, 최고 Sharpe, Top-10 결과
            """
            return adapter.optimize(ohlcv_data, strategy_name, param_ranges, initial_capital)

        @self.mcp.tool()
        def backtest_portfolio(
            assets_data: dict,
            weights: dict,
            rebalance_freq: str = "monthly",
            initial_capital: float = 10_000_000,
        ) -> dict:
            """
            포트폴리오 백테스트 (자산배분 + 리밸런싱). Portfolio backtest with rebalancing.

            Args:
                assets_data: 자산별 OHLCV 데이터 ({ticker: ohlcv_list})
                weights: 자산별 비중 ({ticker: weight}, 합계 1.0)
                rebalance_freq: 리밸런싱 주기 ("monthly" 또는 "quarterly")
                initial_capital: 초기 자본금

            Returns:
                포트폴리오 성과 + 자산별 기여도 + 리밸런싱 이력
            """
            return adapter.portfolio(assets_data, weights, rebalance_freq, initial_capital)

        @self.mcp.tool()
        def backtest_benchmark(
            ohlcv_data: list,
            strategy_name: str,
            benchmark_data: list,
            initial_capital: float = 10_000_000,
        ) -> dict:
            """
            전략 vs 벤치마크 비교. Compare strategy against buy-and-hold benchmark.

            Args:
                ohlcv_data: 전략 대상 OHLCV 데이터
                strategy_name: 전략 이름
                benchmark_data: 벤치마크 OHLCV 데이터 (예: KOSPI)
                initial_capital: 초기 자본금

            Returns:
                alpha, beta, information ratio, tracking error, 초과수익률
            """
            return adapter.benchmark(ohlcv_data, strategy_name, benchmark_data, initial_capital)

        @self.mcp.tool()
        def backtest_risk(
            ohlcv_data: list,
            strategy_name: str,
            initial_capital: float = 10_000_000,
        ) -> dict:
            """
            전략 리스크 분석. Strategy risk analysis.

            VaR (95%, 99%), CVaR, 연환산 변동성, 최대낙폭, Calmar ratio, Sortino ratio.

            Args:
                ohlcv_data: OHLCV 가격 데이터
                strategy_name: 전략 이름
                initial_capital: 초기 자본금

            Returns:
                종합 리스크 지표 (VaR, CVaR, Sortino, Calmar, 변동성, 최대낙폭)
            """
            return adapter.risk_analysis(ohlcv_data, strategy_name, initial_capital)

        @self.mcp.tool()
        def backtest_signal_history(
            ohlcv_data: list,
            strategy_name: str,
            params: Optional[dict] = None,
        ) -> dict:
            """
            전략 시그널 히스토리 + 후행 수익률. Historical signal analysis with forward returns.

            Args:
                ohlcv_data: OHLCV 가격 데이터
                strategy_name: 전략 이름
                params: 전략 파라미터 오버라이드 (선택)

            Returns:
                시그널 목록, 5/10/20/60일 후행 수익률, 평균 수익률
            """
            return adapter.signal_history(ohlcv_data, strategy_name, params)

        @self.mcp.tool()
        def backtest_drawdown(
            ohlcv_data: list,
            strategy_name: str,
            initial_capital: float = 10_000_000,
        ) -> dict:
            """
            낙폭(Drawdown) 상세 분석. Detailed drawdown period analysis.

            Args:
                ohlcv_data: OHLCV 가격 데이터
                strategy_name: 전략 이름
                initial_capital: 초기 자본금

            Returns:
                낙폭 구간 (시작일, 종료일, 깊이, 회복일, 기간) + 현재 낙폭
            """
            return adapter.drawdown_analysis(ohlcv_data, strategy_name, initial_capital)


# ── Standalone entry point ─────────────────────────────────────────────
if __name__ == "__main__":
    server = BacktestServer()
    server.mcp.run()
