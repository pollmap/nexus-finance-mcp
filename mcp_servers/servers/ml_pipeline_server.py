"""
López de Prado ML Pipeline MCP Server (6 tools).

Volume bars, fractional differentiation, triple-barrier labeling,
meta-labeling, purged cross-validation, feature importance.

Tools:
- mlpipe_volume_bars: 볼륨/달러/틱 바 생성
- mlpipe_frac_diff: 분수 차분 (정상성 + 메모리 보존)
- mlpipe_triple_barrier: 트리플 배리어 라벨링
- mlpipe_meta_label: 메타 라벨링
- mlpipe_purged_cv: Purged K-Fold CV
- mlpipe_feature_importance: 피처 중요도 3종 (MDI/MDA/SFI)
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
from mcp_servers.adapters.ml_pipeline_adapter import MLPipelineAdapter

logger = logging.getLogger(__name__)


class MLPipelineServer(BaseMCPServer):
    @property
    def name(self) -> str:
        return "ml_pipeline"

    def __init__(self, **kwargs):
        self._adapter = MLPipelineAdapter()
        super().__init__(**kwargs)

    def _register_tools(self):
        adapter = self._adapter

        @self.mcp.tool()
        def mlpipe_volume_bars(
            series: list, threshold: float = None, bar_type: str = "volume",
        ) -> dict:
            """
            볼륨/달러/틱 바 — 정보 기반 샘플링 (López de Prado Ch.2).

            시간 바(1분/1시간) 대신 거래량이 임계값에 도달할 때마다 바를 생성합니다.
            시장이 활발할 때 더 많은 바 → 정보 밀도 균일화.
            수익률 분포가 시간 바보다 정규분포에 가까워집니다.

            Args:
                series: OHLCV [{date, value, volume}] (50개 이상)
                threshold: 바당 거래량/달러 (None=자동 설정)
                bar_type: "volume" (기본), "dollar", "tick"

            Returns:
                bars (OHLCV), compression_ratio, normality_test
            """
            return adapter.volume_bars(series, threshold, bar_type)

        @self.mcp.tool()
        def mlpipe_frac_diff(
            series: list, d: float = None, threshold: float = 1e-5,
        ) -> dict:
            """
            분수 차분 — 정상성 확보 + 메모리 보존 (López de Prado Ch.5).

            정수 차분(d=1)은 정상성 확보하지만 모든 메모리 파괴.
            분수 차분(d=0.3~0.5)은 정상성 + 원본과의 높은 상관 유지.
            d=None이면 ADF 검정으로 최소 d를 자동 탐색합니다.

            Args:
                series: 가격 시계열 [{date, value}] (50개 이상)
                d: 차분 차수 (None=자동 탐색, 0.0~1.0)
                threshold: 가중치 절삭 임계값 (기본 1e-5)

            Returns:
                optimal_d, adf_pvalue, correlation_with_original, output_series
            """
            return adapter.frac_diff(series, d, threshold)

        @self.mcp.tool()
        def mlpipe_triple_barrier(
            series: list,
            profit_taking: float = 0.02,
            stop_loss: float = 0.02,
            max_holding: int = 10,
        ) -> dict:
            """
            트리플 배리어 라벨링 — ML 학습용 라벨 생성 (López de Prado Ch.3).

            각 관측치에 3개 배리어 중 먼저 도달한 것으로 라벨 부여:
            +1: 이익실현 배리어 도달 (profit_taking)
            -1: 손절 배리어 도달 (stop_loss)
             0: 시간 만료 (max_holding일 내 어느 배리어도 미도달)

            Args:
                series: 가격 시계열 [{date, value}] (30개 이상)
                profit_taking: 이익실현 비율 (기본 2%)
                stop_loss: 손절 비율 (기본 2%)
                max_holding: 최대 보유 기간 (기본 10일)

            Returns:
                label distribution (+1/-1/0), avg returns by label, recent_labels
            """
            return adapter.triple_barrier(series, profit_taking, stop_loss, max_holding)

        @self.mcp.tool()
        def mlpipe_meta_label(
            series: list,
            signals: list,
            profit_taking: float = 0.02,
            stop_loss: float = 0.02,
            max_holding: int = 10,
        ) -> dict:
            """
            메타 라벨링 — 1차 모델이 맞는 타이밍 학습 (López de Prado Ch.3).

            1차 모델(방향 예측) 위에 2차 분류기를 얹어 "이 시그널이 맞을까?"를 학습.
            결과: 1차 모델의 정확한 시그널만 실행 → 승률과 수익 향상.

            Args:
                series: 가격 시계열 [{date, value}]
                signals: 1차 모델 시그널 [{date, value}] (value: -1/0/1)
                profit_taking: 이익실현 비율 (기본 2%)
                stop_loss: 손절 비율 (기본 2%)
                max_holding: 최대 보유 기간 (기본 10일)

            Returns:
                primary_model_accuracy, n_correct/wrong, recent_meta_labels
            """
            return adapter.meta_label(series, signals, profit_taking, stop_loss, max_holding)

        @self.mcp.tool()
        def mlpipe_purged_cv(
            n_samples: int,
            n_folds: int = 5,
            embargo_pct: float = 0.01,
            label_horizon: int = 10,
        ) -> dict:
            """
            Purged K-Fold CV — 미래정보 누출 방지 교차검증 (López de Prado Ch.7).

            일반 K-Fold는 시계열에서 미래 정보가 학습에 포함됨.
            Purged CV: 테스트셋과 라벨이 겹치는 학습 데이터 제거(purge) + embargo.
            금융 ML에서 과적합 방지의 핵심.

            Args:
                n_samples: 총 샘플 수
                n_folds: 폴드 수 (기본 5)
                embargo_pct: embargo 비율 (기본 1%)
                label_horizon: 라벨 기간 (기본 10일)

            Returns:
                splits (각 fold의 train/test 범위), total_purged
            """
            return adapter.purged_cv(n_samples, n_folds, embargo_pct, label_horizon)

        @self.mcp.tool()
        def mlpipe_feature_importance(
            features: list,
            labels: list,
            feature_names: list = None,
            n_estimators: int = 100,
        ) -> dict:
            """
            피처 중요도 3종 — MDI + MDA + SFI (López de Prado Ch.8).

            MDI (Mean Decrease Impurity): 트리 분할 기여도. 빠르지만 편향.
            MDA (Mean Decrease Accuracy): 순열 중요도. 느리지만 정확.
            SFI (Single Feature Importance): 단일 피처 모델 정확도.
            3가지 방법의 평균 순위로 종합 랭킹 산출.

            Args:
                features: [{feat1: val, feat2: val, ...}, ...]
                labels: 타겟 값 [0, 1, 0, ...]
                feature_names: 피처명 리스트 (선택)
                n_estimators: Random Forest 트리 수 (기본 100)

            Returns:
                ranking (종합), mdi/mda/sfi importance
            """
            return adapter.feature_importance(features, labels, feature_names, n_estimators)


server = MLPipelineServer()
mcp = server.mcp

if __name__ == "__main__":
    mcp.run()
