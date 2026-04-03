"""
Ontology Adapter — Data Relationship & Causal Mapping.

Maps relationships between financial/alternative data domains.
Every data point has meaning (존재론) and connections (관계).

Philosophy: Luxon's 연기론 (Dependent Origination) — nothing exists in isolation.
All data is interconnected through causal chains.

Stores ontology in Obsidian Vault as wikilink-connected notes.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

VAULT_ROOT = Path(os.getenv("OBSIDIAN_VAULT_PATH", "/root/obsidian-vault"))
ONTOLOGY_DIR = VAULT_ROOT / "03-Resources" / "ontology"

# === Core Ontology: Domain → Relationships ===
# Each domain maps to its causal connections with other domains.
# direction: "causes" (→), "correlates" (↔), "leads" (⟹ leading indicator)
ONTOLOGY_GRAPH = {
    "interest_rate": {
        "label": "금리 (Interest Rate)",
        "category": "macro",
        "tools": ["ecos_get_base_rate", "ecos_get_bond_yield"],
        "relations": [
            {"target": "exchange_rate", "type": "causes", "lag": "1-3mo", "description": "금리 인상 → 통화 강세"},
            {"target": "stock_market", "type": "causes", "lag": "3-6mo", "description": "금리 인상 → 할인율↑ → 주가↓"},
            {"target": "real_estate", "type": "causes", "lag": "6-12mo", "description": "금리 인상 → 대출부담↑ → 부동산↓"},
            {"target": "bond_price", "type": "causes", "lag": "immediate", "description": "금리↑ → 채권가격↓ (역관계)"},
            {"target": "consumer_spending", "type": "causes", "lag": "3-6mo", "description": "금리↑ → 소비↓"},
            {"target": "crypto", "type": "correlates", "lag": "1-3mo", "description": "금리↑ → 위험자산 회피 → 크립토↓"},
        ],
    },
    "exchange_rate": {
        "label": "환율 (Exchange Rate)",
        "category": "macro",
        "tools": ["ecos_get_exchange_rate"],
        "relations": [
            {"target": "trade_balance", "type": "causes", "lag": "3-6mo", "description": "원화약세 → 수출경쟁력↑ → 무역흑자"},
            {"target": "stock_market", "type": "correlates", "lag": "immediate", "description": "외국인 자금 유출입 연동"},
            {"target": "commodity_price", "type": "correlates", "lag": "immediate", "description": "달러 강세 → 원자재↓"},
            {"target": "inflation", "type": "causes", "lag": "3-6mo", "description": "원화약세 → 수입물가↑ → 인플레이션"},
        ],
    },
    "inflation": {
        "label": "인플레이션 (CPI/PPI)",
        "category": "macro",
        "tools": ["ecos_get_macro_snapshot", "consumer_eu_hicp"],
        "relations": [
            {"target": "interest_rate", "type": "causes", "lag": "1-3mo", "description": "인플레 → 중앙은행 금리인상"},
            {"target": "consumer_spending", "type": "causes", "lag": "immediate", "description": "물가↑ → 실질구매력↓"},
            {"target": "real_estate", "type": "correlates", "lag": "6-12mo", "description": "인플레 → 실물자산 선호"},
            {"target": "gold_commodity", "type": "correlates", "lag": "1-3mo", "description": "인플레 헤지 → 금 수요↑"},
        ],
    },
    "stock_market": {
        "label": "주식시장 (Equities)",
        "category": "market",
        "tools": ["stocks_quote", "stocks_history", "stocks_market_overview"],
        "relations": [
            {"target": "corporate_earnings", "type": "correlates", "lag": "immediate", "description": "실적 → 주가"},
            {"target": "sentiment", "type": "correlates", "lag": "immediate", "description": "투자 심리 ↔ 주가"},
            {"target": "geopolitical_risk", "type": "causes", "lag": "immediate", "description": "지정학 리스크 → 변동성↑"},
            {"target": "crypto", "type": "correlates", "lag": "1-7d", "description": "위험자산 동조화"},
        ],
    },
    "crypto": {
        "label": "암호화폐 (Crypto)",
        "category": "market",
        "tools": ["crypto_ticker", "crypto_kimchi_premium", "defi_feargreed"],
        "relations": [
            {"target": "sentiment", "type": "correlates", "lag": "immediate", "description": "소셜 센티멘트 ↔ 크립토 가격"},
            {"target": "interest_rate", "type": "correlates", "lag": "1-3mo", "description": "금리환경 → 유동성 → 크립토"},
            {"target": "stock_market", "type": "correlates", "lag": "1-7d", "description": "위험자산 동조화"},
            {"target": "energy_price", "type": "correlates", "lag": "1-3mo", "description": "에너지비용 → 채굴 수익성"},
        ],
    },
    "energy_price": {
        "label": "에너지 가격 (Oil/Gas/Electricity)",
        "category": "commodity",
        "tools": ["energy_crude_oil", "energy_natural_gas", "energy_price_snapshot"],
        "relations": [
            {"target": "inflation", "type": "causes", "lag": "1-3mo", "description": "에너지↑ → 생산비용↑ → CPI↑"},
            {"target": "trade_balance", "type": "causes", "lag": "1-3mo", "description": "유가↑ → 에너지 수입국 적자"},
            {"target": "shipping_cost", "type": "correlates", "lag": "immediate", "description": "연료비 → 운임"},
            {"target": "geopolitical_risk", "type": "correlates", "lag": "immediate", "description": "중동 분쟁 → 유가↑"},
            {"target": "climate", "type": "correlates", "lag": "seasonal", "description": "한파/폭염 → 에너지 수요"},
            {"target": "power_grid", "type": "causes", "lag": "immediate", "description": "에너지가격 → 전력가격"},
        ],
    },
    "agriculture": {
        "label": "농산물 (Agriculture)",
        "category": "commodity",
        "tools": ["agri_kamis_prices", "agri_fao_production", "agri_snapshot"],
        "relations": [
            {"target": "climate", "type": "correlates", "lag": "seasonal", "description": "기후(엘니뇨/가뭄) → 작황 → 가격"},
            {"target": "inflation", "type": "causes", "lag": "1-3mo", "description": "곡물↑ → 식품인플레"},
            {"target": "trade_balance", "type": "correlates", "lag": "3-6mo", "description": "농산물 수출입"},
            {"target": "disaster", "type": "correlates", "lag": "immediate", "description": "홍수/가뭄 → 작황 피해"},
        ],
    },
    "real_estate": {
        "label": "부동산 (Real Estate)",
        "category": "asset",
        "tools": ["rone_get_apt_price_index", "rone_get_jeonse_index", "realestate_apt_trades"],
        "relations": [
            {"target": "interest_rate", "type": "correlates", "lag": "6-12mo", "description": "금리 → 대출부담 → 부동산"},
            {"target": "consumer_spending", "type": "correlates", "lag": "3-6mo", "description": "자산효과: 집값↑ → 소비↑"},
            {"target": "demographic", "type": "correlates", "lag": "years", "description": "인구/가구 구조 → 주택 수요"},
        ],
    },
    "shipping_cost": {
        "label": "해운/물류 (Shipping)",
        "category": "logistics",
        "tools": ["maritime_bdi", "maritime_container_index", "maritime_freight_snapshot"],
        "relations": [
            {"target": "trade_balance", "type": "leads", "lag": "1-3mo", "description": "BDI 선행 → 글로벌 무역 활동"},
            {"target": "inflation", "type": "causes", "lag": "3-6mo", "description": "운임↑ → 수입물가↑"},
            {"target": "energy_price", "type": "correlates", "lag": "immediate", "description": "연료비 → 운임"},
            {"target": "supply_chain", "type": "correlates", "lag": "immediate", "description": "항만 혼잡 → 공급망 차질"},
        ],
    },
    "geopolitical_risk": {
        "label": "지정학 리스크 (Conflict/War)",
        "category": "risk",
        "tools": ["conflict_active_wars", "conflict_peace_index", "conflict_country_risk"],
        "relations": [
            {"target": "energy_price", "type": "causes", "lag": "immediate", "description": "중동/러시아 분쟁 → 유가↑"},
            {"target": "stock_market", "type": "causes", "lag": "immediate", "description": "리스크 → 변동성/하락"},
            {"target": "exchange_rate", "type": "causes", "lag": "immediate", "description": "안전자산 수요 → 달러/엔 강세"},
            {"target": "agriculture", "type": "causes", "lag": "1-3mo", "description": "흑해 분쟁 → 곡물 수출 차질"},
            {"target": "defense_sector", "type": "correlates", "lag": "immediate", "description": "분쟁 → 방산주↑"},
        ],
    },
    "climate": {
        "label": "기후/날씨 (Climate)",
        "category": "environment",
        "tools": ["climate_historical_weather", "climate_enso_index", "climate_temperature_anomaly"],
        "relations": [
            {"target": "agriculture", "type": "causes", "lag": "seasonal", "description": "엘니뇨/가뭄 → 작황 변동"},
            {"target": "energy_price", "type": "causes", "lag": "seasonal", "description": "한파/폭염 → 에너지 수요"},
            {"target": "disaster", "type": "causes", "lag": "immediate", "description": "극한기상 → 자연재해"},
            {"target": "insurance", "type": "causes", "lag": "1-3mo", "description": "기후리스크 → 보험 손실"},
        ],
    },
    "disaster": {
        "label": "자연재해 (Disasters)",
        "category": "risk",
        "tools": ["disaster_earthquakes", "disaster_wildfires", "disaster_active_events"],
        "relations": [
            {"target": "insurance", "type": "causes", "lag": "immediate", "description": "대재해 → 보험금 지급 → 보험주↓"},
            {"target": "supply_chain", "type": "causes", "lag": "1-3mo", "description": "공장/항만 피해 → 공급 차질"},
            {"target": "real_estate", "type": "causes", "lag": "3-6mo", "description": "지진/홍수 → 부동산 피해"},
            {"target": "infrastructure", "type": "causes", "lag": "3-12mo", "description": "재건 수요 → 건설/인프라주↑"},
        ],
    },
    "sunspot_cycle": {
        "label": "태양 흑점 주기 (Sunspot Cycle)",
        "category": "space",
        "tools": ["space_sunspot_data", "space_geomagnetic", "space_solar_flares"],
        "relations": [
            {"target": "power_grid", "type": "causes", "lag": "immediate", "description": "지자기 폭풍 → 전력망 교란"},
            {"target": "satellite_comms", "type": "causes", "lag": "immediate", "description": "태양 플레어 → GPS/통신 장애"},
            {"target": "stock_market", "type": "correlates", "lag": "years", "description": "11년 주기 ↔ 경기순환 (연구 중)"},
            {"target": "climate", "type": "correlates", "lag": "years", "description": "태양 활동 → 기후 변동 (미약)"},
        ],
    },
    "sentiment": {
        "label": "시장 심리 (Sentiment)",
        "category": "behavioral",
        "tools": ["sentiment_google_trends", "sentiment_wiki_pageviews", "sentiment_fear_greed_multi"],
        "relations": [
            {"target": "stock_market", "type": "leads", "lag": "1-7d", "description": "검색량 급증 → 주가 변동 선행"},
            {"target": "crypto", "type": "leads", "lag": "1-3d", "description": "소셜 버즈 → 크립토 변동 선행"},
            {"target": "consumer_spending", "type": "correlates", "lag": "1-3mo", "description": "소비심리 → 소비"},
        ],
    },
    "power_grid": {
        "label": "전력 그리드 (Power Grid)",
        "category": "infrastructure",
        "tools": ["grid_nuclear_status", "grid_carbon_intensity", "grid_eu_generation"],
        "relations": [
            {"target": "energy_price", "type": "correlates", "lag": "immediate", "description": "전력 수급 → 에너지 가격"},
            {"target": "climate", "type": "correlates", "lag": "immediate", "description": "재생에너지 발전 ← 날씨"},
            {"target": "sunspot_cycle", "type": "correlates", "lag": "immediate", "description": "지자기 폭풍 → 전력망 장애"},
        ],
    },
    "trade_balance": {
        "label": "무역수지 (Trade Balance)",
        "category": "macro",
        "tools": ["trade_korea_exports", "trade_korea_imports"],
        "relations": [
            {"target": "exchange_rate", "type": "causes", "lag": "1-3mo", "description": "무역흑자 → 통화 강세"},
            {"target": "stock_market", "type": "correlates", "lag": "1-3mo", "description": "수출 호조 → 수출주↑"},
            {"target": "shipping_cost", "type": "correlates", "lag": "immediate", "description": "무역량 ↔ 해운 수요"},
        ],
    },
    "consumer_spending": {
        "label": "소비 (Consumer Spending)",
        "category": "macro",
        "tools": ["consumer_us_retail", "consumer_us_sentiment"],
        "relations": [
            {"target": "stock_market", "type": "correlates", "lag": "1-3mo", "description": "소비↑ → 기업실적↑ → 주가↑"},
            {"target": "inflation", "type": "causes", "lag": "3-6mo", "description": "수요↑ → 물가↑"},
        ],
    },
}


class OntologyAdapter:
    """Data ontology — relationship mapping between financial/alternative data domains."""

    def get_domain_map(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """Get ontology for a specific domain or all domains."""
        if domain:
            if domain not in ONTOLOGY_GRAPH:
                close = [k for k in ONTOLOGY_GRAPH if domain.lower() in k]
                return {"error": True, "message": f"Domain '{domain}' not found. Did you mean: {close or list(ONTOLOGY_GRAPH.keys())}"}
            node = ONTOLOGY_GRAPH[domain]
            return {
                "success": True,
                "domain": domain,
                "label": node["label"],
                "category": node["category"],
                "tools": node["tools"],
                "relations": node["relations"],
                "connected_domains": [r["target"] for r in node["relations"]],
            }
        # All domains summary
        domains = []
        for key, node in ONTOLOGY_GRAPH.items():
            domains.append({
                "domain": key,
                "label": node["label"],
                "category": node["category"],
                "tool_count": len(node["tools"]),
                "relation_count": len(node["relations"]),
            })
        return {"success": True, "count": len(domains), "domains": domains}

    def get_causal_chain(self, source: str, target: str, max_depth: int = 4) -> Dict[str, Any]:
        """Find causal chain between two domains (BFS path finding)."""
        if source not in ONTOLOGY_GRAPH:
            return {"error": True, "message": f"Source domain '{source}' not found"}
        if target not in ONTOLOGY_GRAPH:
            return {"error": True, "message": f"Target domain '{target}' not found"}

        # BFS
        from collections import deque
        queue = deque([(source, [source])])
        visited = {source}

        while queue:
            current, path = queue.popleft()
            if len(path) > max_depth:
                continue

            if current not in ONTOLOGY_GRAPH:
                continue

            for rel in ONTOLOGY_GRAPH[current]["relations"]:
                next_domain = rel["target"]
                if next_domain == target:
                    full_path = path + [next_domain]
                    # Build chain description
                    chain = []
                    for i in range(len(full_path) - 1):
                        src = full_path[i]
                        dst = full_path[i + 1]
                        for r in ONTOLOGY_GRAPH.get(src, {}).get("relations", []):
                            if r["target"] == dst:
                                chain.append({
                                    "from": src,
                                    "to": dst,
                                    "type": r["type"],
                                    "lag": r["lag"],
                                    "description": r["description"],
                                })
                                break
                    return {
                        "success": True,
                        "source": source,
                        "target": target,
                        "path_length": len(full_path) - 1,
                        "path": full_path,
                        "chain": chain,
                        "narrative": " → ".join(
                            f"{c['from']}({c['description']})" for c in chain
                        ) + f" → {target}",
                    }

                if next_domain not in visited and next_domain in ONTOLOGY_GRAPH:
                    visited.add(next_domain)
                    queue.append((next_domain, path + [next_domain]))

        return {"success": True, "source": source, "target": target, "path": None, "message": "No causal chain found within depth limit"}

    def get_impact_analysis(self, domain: str, direction: str = "downstream") -> Dict[str, Any]:
        """Analyze what a domain affects (downstream) or what affects it (upstream)."""
        if domain not in ONTOLOGY_GRAPH:
            return {"error": True, "message": f"Domain '{domain}' not found"}

        if direction == "downstream":
            # What does this domain affect?
            impacts = []
            for rel in ONTOLOGY_GRAPH[domain]["relations"]:
                impacts.append({
                    "affected": rel["target"],
                    "affected_label": ONTOLOGY_GRAPH.get(rel["target"], {}).get("label", rel["target"]),
                    "type": rel["type"],
                    "lag": rel["lag"],
                    "description": rel["description"],
                })
            return {
                "success": True,
                "domain": domain,
                "label": ONTOLOGY_GRAPH[domain]["label"],
                "direction": "downstream",
                "impact_count": len(impacts),
                "impacts": impacts,
            }
        else:
            # What affects this domain? (reverse lookup)
            upstream = []
            for src_key, src_node in ONTOLOGY_GRAPH.items():
                for rel in src_node["relations"]:
                    if rel["target"] == domain:
                        upstream.append({
                            "source": src_key,
                            "source_label": src_node["label"],
                            "type": rel["type"],
                            "lag": rel["lag"],
                            "description": rel["description"],
                        })
            return {
                "success": True,
                "domain": domain,
                "label": ONTOLOGY_GRAPH[domain]["label"],
                "direction": "upstream",
                "driver_count": len(upstream),
                "drivers": upstream,
            }

    def get_tools_for_analysis(self, scenario: str) -> Dict[str, Any]:
        """Suggest MCP tools for a given analysis scenario."""
        scenario_lower = scenario.lower()

        # Match domains by keywords
        matched_domains = []
        keyword_map = {
            "interest_rate": ["금리", "interest", "rate", "기준금리"],
            "exchange_rate": ["환율", "exchange", "원달러", "usd", "krw"],
            "inflation": ["인플레", "inflation", "cpi", "물가"],
            "stock_market": ["주식", "주가", "stock", "kospi", "equity"],
            "crypto": ["크립토", "비트코인", "bitcoin", "crypto", "eth"],
            "energy_price": ["에너지", "유가", "원유", "oil", "gas", "energy"],
            "agriculture": ["농산물", "곡물", "agriculture", "grain", "crop"],
            "real_estate": ["부동산", "아파트", "real estate", "housing"],
            "shipping_cost": ["해운", "shipping", "bdi", "freight", "컨테이너"],
            "geopolitical_risk": ["전쟁", "분쟁", "war", "conflict", "지정학"],
            "climate": ["기후", "날씨", "climate", "weather", "엘니뇨"],
            "disaster": ["재해", "지진", "earthquake", "disaster", "태풍"],
            "sunspot_cycle": ["흑점", "sunspot", "태양", "solar", "우주"],
            "sentiment": ["심리", "sentiment", "google trends", "공포", "탐욕"],
            "power_grid": ["전력", "전기", "power", "grid", "원전"],
            "trade_balance": ["무역", "수출", "수입", "trade"],
            "consumer_spending": ["소비", "consumer", "retail"],
        }

        for domain, keywords in keyword_map.items():
            if any(kw in scenario_lower for kw in keywords):
                matched_domains.append(domain)

        if not matched_domains:
            return {
                "success": True,
                "scenario": scenario,
                "matched_domains": [],
                "message": "No matching domains found. Try keywords like: 금리, 환율, 주식, 에너지, 기후, 분쟁",
            }

        # Collect all tools + related domains
        all_tools = []
        related_domains = set()
        for domain in matched_domains:
            node = ONTOLOGY_GRAPH[domain]
            all_tools.extend(node["tools"])
            for rel in node["relations"]:
                related_domains.add(rel["target"])
                if rel["target"] in ONTOLOGY_GRAPH:
                    all_tools.extend(ONTOLOGY_GRAPH[rel["target"]]["tools"][:2])

        return {
            "success": True,
            "scenario": scenario,
            "matched_domains": matched_domains,
            "related_domains": list(related_domains - set(matched_domains)),
            "recommended_tools": list(dict.fromkeys(all_tools)),  # dedupe preserving order
            "analysis_narrative": " → ".join(
                ONTOLOGY_GRAPH[d]["label"] for d in matched_domains
            ),
        }

    def save_to_vault(self) -> Dict[str, Any]:
        """Save ontology graph as Obsidian notes with wikilinks."""
        try:
            ONTOLOGY_DIR.mkdir(parents=True, exist_ok=True)

            created = []
            for domain_key, node in ONTOLOGY_GRAPH.items():
                filename = f"ONT-{domain_key}.md"
                filepath = ONTOLOGY_DIR / filename

                relations_md = ""
                for rel in node["relations"]:
                    target_file = f"ONT-{rel['target']}"
                    arrow = {"causes": "→", "correlates": "↔", "leads": "⟹"}.get(rel["type"], "→")
                    relations_md += f"- {arrow} [[{target_file}|{rel['target']}]] ({rel['type']}, {rel['lag']}): {rel['description']}\n"

                tools_md = ", ".join(f"`{t}`" for t in node["tools"])

                content = f"""---
title: "{node['label']}"
domain: {domain_key}
category: {node['category']}
tags: [ontology, {node['category']}, data-relationship]
date: {datetime.now().strftime('%Y-%m-%d')}
---

# {node['label']}

**Domain**: `{domain_key}`
**Category**: {node['category']}
**MCP Tools**: {tools_md}

## Relations

{relations_md}
## Related Notes

{chr(10).join(f'- [[ONT-{r["target"]}]]' for r in node['relations'])}

---
*Auto-generated by Ontology Adapter*
"""
                filepath.write_text(content, encoding="utf-8")
                created.append(filename)

            # Create MOC (Map of Content)
            moc_content = f"""---
title: "MOC-Ontology — 데이터 존재론 지도"
tags: [ontology, MOC, data-relationship]
date: {datetime.now().strftime('%Y-%m-%d')}
---

# Data Ontology Map

> 모든 데이터는 연결되어 있다 (연기론). 이 지도는 금융/대체 데이터 간의 인과관계를 보여준다.

## Domains ({len(ONTOLOGY_GRAPH)} nodes)

"""
            by_category = {}
            for key, node in ONTOLOGY_GRAPH.items():
                cat = node["category"]
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append((key, node))

            for cat, nodes in by_category.items():
                moc_content += f"### {cat.title()}\n"
                for key, node in nodes:
                    rel_count = len(node["relations"])
                    moc_content += f"- [[ONT-{key}|{node['label']}]] — {rel_count} connections\n"
                moc_content += "\n"

            moc_content += "---\n*Auto-generated by Ontology Adapter*\n"
            (ONTOLOGY_DIR / "MOC-Ontology.md").write_text(moc_content, encoding="utf-8")
            created.append("MOC-Ontology.md")

            return {
                "success": True,
                "path": str(ONTOLOGY_DIR),
                "files_created": len(created),
                "files": created,
            }
        except Exception as e:
            logger.error(f"Vault save error: {e}")
            return {"error": True, "message": str(e)}
