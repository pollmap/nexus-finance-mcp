"""
Prediction Market MCP Server — Polymarket data.

Tools (3):
- prediction_markets: 활성 예측시장 목록
- prediction_market_detail: 단일 마켓 상세
- prediction_events: 이벤트(마켓 그룹) 목록
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP
from mcp_servers.adapters.polymarket_adapter import PolymarketAdapter

logger = logging.getLogger(__name__)


class PredictionServer:
    def __init__(self):
        self._poly = PolymarketAdapter()
        self.mcp = FastMCP("prediction")
        self._register_tools()
        logger.info("Prediction Market MCP Server initialized")

    def _register_tools(self):

        @self.mcp.tool()
        def prediction_markets(limit: int = 20) -> dict:
            """
            Polymarket 활성 예측시장 목록 (거래량 순).

            Args:
                limit: 상위 N개 (기본 20)

            Returns:
                질문, 확률, 거래량, 유동성
            """
            return self._poly.get_markets(limit=limit)

        @self.mcp.tool()
        def prediction_market_detail(condition_id: str) -> dict:
            """
            단일 예측시장 상세 정보.

            Args:
                condition_id: 마켓 condition ID (markets 목록에서 확인)

            Returns:
                질문, 설명, 확률, 거래량, 마감일
            """
            return self._poly.get_market_detail(condition_id)

        @self.mcp.tool()
        def prediction_events(limit: int = 10) -> dict:
            """
            예측시장 이벤트 목록 (관련 마켓 그룹).

            Args:
                limit: 상위 N개

            Returns:
                이벤트 제목, 거래량, 포함 마켓 수
            """
            return self._poly.get_events(limit=limit)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = PredictionServer()
    server.mcp.run(transport="stdio")
