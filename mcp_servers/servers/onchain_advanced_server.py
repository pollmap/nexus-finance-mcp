"""
Advanced On-chain Analytics MCP Server — BTC On-chain Metrics (6 tools).

Exchange flow, MVRV, realized cap, HODL waves, whale alert, NVT ratio.

Tools:
- onchain_adv_exchange_flow: 거래소 유입/유출 활동 분석
- onchain_adv_mvrv: MVRV 비율 (시가/실현 시가총액)
- onchain_adv_realized_cap: 실현 시가총액
- onchain_adv_hodl_waves: HODL 파동 (BTC 보유 연령 분포)
- onchain_adv_whale_alert: 고래 거래 추적
- onchain_adv_nvt: NVT 비율 (크립토의 PER)
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.core.base_server import BaseMCPServer
from mcp_servers.adapters.onchain_advanced_adapter import OnchainAdvancedAdapter

logger = logging.getLogger(__name__)


class OnchainAdvancedServer(BaseMCPServer):
    @property
    def name(self) -> str:
        return "onchain_advanced"

    def __init__(self, **kwargs):
        self._adapter = OnchainAdvancedAdapter()
        super().__init__(**kwargs)

    def _register_tools(self):
        adapter = self._adapter

        @self.mcp.tool()
        def onchain_adv_exchange_flow(timespan: str = "90days") -> dict:
            """
            거래소 유입/유출 활동 분석 — 온체인 트랜잭션 패턴.

            트랜잭션 수, 추정 거래량, 고유 주소 수의 30일 vs 90일 추세 비교.
            활동 증가 → 매집 또는 분배 단계. 감소 → 횡보/무관심 단계.

            Args:
                timespan: 분석 기간 (기본 "90days")

            Returns:
                tx_count_trend, volume_trend, unique_addresses, flow_signal
            """
            return adapter.exchange_flow(timespan)

        @self.mcp.tool()
        def onchain_adv_mvrv(timespan: str = "365days") -> dict:
            """
            MVRV 비율 — 시가총액 / 실현시가총액.

            > 3.5: 역사적 고점 구간 (매도 신호). < 1.0: 역사적 저점 구간 (매수 신호).
            1.0~2.5: 적정 가치. 200일 SMA를 실현시가총액 프록시로 사용.

            Args:
                timespan: 분석 기간 (기본 "365days")

            Returns:
                mvrv, zone, signal, history
            """
            return adapter.mvrv(timespan)

        @self.mcp.tool()
        def onchain_adv_realized_cap(timespan: str = "365days") -> dict:
            """
            실현 시가총액 — 각 코인을 마지막 이동 시 가격으로 평가.

            시가총액보다 안정적. 미실현 이익 = (시가총액 - 실현시가총액)/실현시가총액.
            200일 SMA 프록시 사용.

            Args:
                timespan: 분석 기간 (기본 "365days")

            Returns:
                realized_cap_proxy, market_cap, unrealized_profit_pct
            """
            return adapter.realized_cap(timespan)

        @self.mcp.tool()
        def onchain_adv_hodl_waves() -> dict:
            """
            HODL 파동 — BTC 보유 연령 분포 (Bitcoin Days Destroyed 기반).

            BDD(Bitcoin Days Destroyed) 비율로 장기 보유자 행동 추정.
            BDD 급증 → 오래된 코인 이동 → 분배 단계 (약세).
            BDD 감소 → 코인 노화 중 → 매집 단계 (강세).

            Returns:
                bdd_ratio, phase (accumulation/distribution/neutral), signal
            """
            return adapter.hodl_waves()

        @self.mcp.tool()
        def onchain_adv_whale_alert(threshold_btc: float = 100) -> dict:
            """
            고래 거래 추적 — 대량 BTC 이체 감지.

            Blockchain.com 미확인 트랜잭션 풀에서 임계값 이상의 대량 거래를 탐색합니다.
            고래 거래 급증 → 큰 가격 움직임 선행 가능.

            Args:
                threshold_btc: 최소 BTC 임계값 (기본 100 BTC)

            Returns:
                whale_transactions (hash, btc, time), n_whales_found
            """
            return adapter.whale_alert(threshold_btc)

        @self.mcp.tool()
        def onchain_adv_nvt(timespan: str = "365days") -> dict:
            """
            NVT 비율 — 네트워크 가치 / 거래량 (크립토의 PER).

            NVT > 95: 과대평가 (가격이 사용량보다 빠르게 상승).
            NVT < 30: 저평가 (사용량 대비 가격이 낮음).
            주식의 PER처럼 네트워크 활용도 대비 가치 평가.

            Args:
                timespan: 분석 기간 (기본 "365days")

            Returns:
                current_nvt, avg_nvt, zone, signal, history
            """
            return adapter.nvt(timespan)


server = OnchainAdvancedServer()
mcp = server.mcp

if __name__ == "__main__":
    mcp.run()
