"""
Ontology MCP Server — Data Relationship & Causal Chain Mapping.

Luxon 철학: 연기론(緣起論) — 모든 데이터는 독립적으로 존재하지 않는다.
금리↔환율↔주가↔부동산↔에너지↔기후가 하나의 인과 그래프로 연결된다.

Tools (5):
- ontology_map: 도메인 관계 지도 조회
- ontology_chain: 두 도메인 간 인과 체인 탐색
- ontology_impact: 특정 도메인의 상류/하류 영향 분석
- ontology_suggest: 분석 시나리오에 맞는 MCP 도구 추천
- ontology_save: 온톨로지를 Obsidian Vault에 저장 (wikilink 연결)
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP
from mcp_servers.adapters.ontology_adapter import OntologyAdapter

logger = logging.getLogger(__name__)


class OntologyServer:
    def __init__(self):
        self._adapter = OntologyAdapter()
        self.mcp = FastMCP("ontology")
        self._register_tools()
        logger.info("Ontology MCP Server initialized")

    def _register_tools(self):

        @self.mcp.tool()
        def ontology_map(domain: str = "") -> dict:
            """
            데이터 도메인 관계 지도. 도메인 지정 시 해당 도메인의 연결 관계 반환, 미지정 시 전체 요약.

            Args:
                domain: 도메인 키 (예: interest_rate, exchange_rate, climate, disaster, sunspot_cycle)
                       빈 문자열이면 전체 도메인 목록 반환
            """
            return self._adapter.get_domain_map(domain if domain else None)

        @self.mcp.tool()
        def ontology_chain(source: str, target: str, max_depth: int = 4) -> dict:
            """
            두 도메인 간 인과 체인 탐색. BFS로 최단 경로 찾기.

            Args:
                source: 시작 도메인 (예: interest_rate)
                target: 목표 도메인 (예: real_estate)
                max_depth: 최대 탐색 깊이 (기본 4)

            Example: interest_rate → real_estate = 금리↑ → 대출부담↑ → 부동산↓
            """
            return self._adapter.get_causal_chain(source, target, max_depth)

        @self.mcp.tool()
        def ontology_impact(domain: str, direction: str = "downstream") -> dict:
            """
            특정 도메인의 영향 분석.

            Args:
                domain: 분석 대상 도메인 (예: energy_price)
                direction: "downstream" (이 도메인이 영향 미치는 것) 또는 "upstream" (이 도메인에 영향 주는 것)
            """
            return self._adapter.get_impact_analysis(domain, direction)

        @self.mcp.tool()
        def ontology_suggest(scenario: str) -> dict:
            """
            분석 시나리오에 맞는 MCP 도구 추천. 한국어/영어 키워드 모두 지원.

            Args:
                scenario: 분석하고 싶은 시나리오 (예: "엘니뇨가 곡물가격에 미치는 영향", "금리 인상 시 부동산 전망")
            """
            return self._adapter.get_tools_for_analysis(scenario)

        @self.mcp.tool()
        def ontology_save() -> dict:
            """온톨로지 그래프를 Obsidian Vault에 wikilink 연결 노트로 저장."""
            return self._adapter.save_to_vault()
