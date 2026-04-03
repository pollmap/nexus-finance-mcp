"""
Signal Lab MCP Server - 자동 시그널 탐색 & 앙상블 엔진.

퀀트 알파 리서치의 핵심: 시그널 스캐닝 → 결합 → 감쇠 분석 →
용량 추정 → 레짐 스위칭 → Walk-Forward 검증.

Tools:
- signal_scan: IC 기반 피처 자동 스캐닝 (walk-forward)
- signal_combine: 복수 시그널 앙상블 결합
- signal_decay: 시그널 감쇠 분석 (half-life)
- signal_capacity: 시장충격 기반 용량 추정
- signal_regime_select: 레짐 탐지 + 전략 스위칭
- signal_walkforward: Walk-Forward 검증 (과적합 방지)

Run standalone: python -m mcp_servers.servers.signal_lab_server
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
from mcp_servers.adapters.signal_lab_adapter import SignalLabAdapter

logger = logging.getLogger(__name__)


class SignalLabServer(BaseMCPServer):
    """Signal Lab MCP Server wrapping SignalLabAdapter."""

    @property
    def name(self) -> str:
        return "signal_lab"

    def __init__(self, **kwargs):
        self._adapter = SignalLabAdapter()
        super().__init__(**kwargs)

    def _register_tools(self):
        adapter = self._adapter

        @self.mcp.tool()
        def signal_scan(
            target_series: list,
            candidate_features: list,
            forward_period: int = 20,
            method: str = "walk_forward",
        ) -> dict:
            """
            IC 기반 피처 자동 스캐닝. Automated feature scanning via Information Coefficient.

            각 후보 피처의 예측력(IC)을 walk-forward 방식으로 평가하여
            유효한 시그널만 필터링. |IC|>0.02, |t|>1.5 기준.

            Args:
                target_series: 예측 대상 시계열 (예: 주가) [{date, value}]
                candidate_features: 후보 피처 [{"name": str, "data": [{date, value}]}]
                forward_period: 전방 수익률 기간 (기본 20일)
                method: "walk_forward" (5-fold 시계열 CV) 또는 "full_sample"

            Returns:
                유효 시그널 순위 (IC, t-stat, best_lag, 유의성)

            Example:
                signal_scan(target_series=prices, candidate_features=[
                    {"name": "VIX", "data": vix_data},
                    {"name": "credit_spread", "data": spread_data},
                ])
            """
            return adapter.signal_scan(target_series, candidate_features, forward_period, method)

        @self.mcp.tool()
        def signal_combine(
            signals: list,
            target_series: list,
            method: str = "ic_weight",
        ) -> dict:
            """
            복수 시그널 앙상블 결합. Combine multiple signals into an ensemble.

            z-score 정규화 후 가중 결합. 단일 시그널 대비 IC 개선율 제공.

            Args:
                signals: 시그널 목록 [{"name": str, "data": [{date, value}]}]
                target_series: 타겟 수익률 [{date, value}]
                method: "equal_weight" | "ic_weight" (IC 가중) | "ridge" (Ridge 회귀)

            Returns:
                결합 시그널, 개별 IC, 결합 IC, 개선율

            Example:
                signal_combine(
                    signals=[{"name": "momentum", "data": mom}, {"name": "value", "data": val}],
                    target_series=returns, method="ic_weight"
                )
            """
            return adapter.signal_combine(signals, target_series, method)

        @self.mcp.tool()
        def signal_decay(
            signal_series: list,
            target_series: list,
            max_horizon: int = 60,
        ) -> dict:
            """
            시그널 감쇠(Decay) 분석. Signal decay analysis with half-life estimation.

            시간 경과에 따른 IC 변화 곡선 + half-life.
            빠른 감쇠 → 단타, 느린 감쇠 → 포지션 트레이딩.

            Args:
                signal_series: 시그널 시계열 [{date, value}]
                target_series: 가격 시계열 [{date, value}]
                max_horizon: 최대 분석 horizon (기본 60일)

            Returns:
                decay_curve (horizon별 IC), half_life, 해석

            Example:
                signal_decay(signal_series=momentum_signal, target_series=prices)
            """
            return adapter.signal_decay(signal_series, target_series, max_horizon)

        @self.mcp.tool()
        def signal_capacity(
            signal_series: list,
            ohlcv_data: list,
            initial_capital: float = 1e9,
        ) -> dict:
            """
            시장충격 기반 시그널 용량 추정. Market impact capacity estimation.

            슬리피지가 알파의 50%를 잠식하는 자본 규모 = 최대 용량.
            모델: slippage = 10 * sqrt(participation_rate)

            Args:
                signal_series: 시그널 시계열 [{date, value}]
                ohlcv_data: OHLCV 데이터 [{date, open, high, low, close, volume}]
                initial_capital: 분석 기준 자본금 (기본 10억원)

            Returns:
                max_capacity_krw, expected_slippage_bps, 용량 활용 곡선

            Example:
                signal_capacity(signal_series=alpha_signal, ohlcv_data=samsung_ohlcv)
            """
            return adapter.signal_capacity(signal_series, ohlcv_data, initial_capital)

        @self.mcp.tool()
        def signal_regime_select(
            ohlcv_data: list,
            strategies: list,
            n_regimes: int = 2,
        ) -> dict:
            """
            시장 레짐 탐지 + 전략 스위칭. Market regime detection with strategy selection.

            롤링 변동성 + 수익률 기반 레짐 분류 (bull/bear),
            각 레짐에서 최적 전략 추천.

            Args:
                ohlcv_data: OHLCV 가격 데이터
                strategies: 전략별 수익률 [{"name": str, "data": [{date, value}]}]
                n_regimes: 레짐 수 (2=bull/bear, 3=bull/neutral/bear)

            Returns:
                레짐 구간, 레짐별 최적 전략, 현재 레짐, 추천 전략

            Example:
                signal_regime_select(ohlcv_data=kospi, strategies=[
                    {"name": "momentum", "data": mom_returns},
                    {"name": "mean_reversion", "data": mr_returns},
                ], n_regimes=2)
            """
            return adapter.signal_regime_select(ohlcv_data, strategies, n_regimes)

        @self.mcp.tool()
        def signal_walkforward(
            ohlcv_data: list,
            strategy_name: str,
            train_window: int = 252,
            test_window: int = 63,
            n_splits: Optional[int] = None,
            params: Optional[dict] = None,
        ) -> dict:
            """
            Walk-Forward 검증 — 과적합 방지 핵심 도구. The most important validation tool.

            미래 데이터 누출 없이 전략을 시간순으로 분할 평가.
            IS/OOS Sharpe 비율로 과적합 진단.
            overfit_ratio > 2.0: "WARNING: likely overfitted"

            이 검증 없이는 모든 백테스트가 거짓이다.

            Args:
                ohlcv_data: OHLCV 가격 데이터
                strategy_name: 전략 이름 (RSI_oversold, MACD_crossover, MA_cross 등)
                train_window: 학습 기간 (기본 252거래일 = 1년)
                test_window: 검증 기간 (기본 63거래일 = 1분기)
                n_splits: 분할 수 (None=자동)
                params: 전략 파라미터 오버라이드

            Returns:
                IS/OOS 지표, overfit_ratio, fold별 상세, 판정(ACCEPT/REJECT)

            Example:
                signal_walkforward(ohlcv_data=samsung_3y, strategy_name="RSI_oversold",
                    train_window=252, test_window=63)
            """
            return adapter.signal_walkforward(
                ohlcv_data, strategy_name, train_window, test_window, n_splits, params
            )


# ── Standalone entry point ─────────────────────────────────────────────
if __name__ == "__main__":
    server = SignalLabServer()
    server.mcp.run()
