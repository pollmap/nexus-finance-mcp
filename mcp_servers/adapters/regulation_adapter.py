"""Regulation & Compliance Adapter — EU regulations (EUR-Lex), US FINRA."""
import logging
import sys
from pathlib import Path
import requests
from utils.http_client import get_session
from typing import Any, Dict
from urllib.parse import quote

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)
_session = get_session("regulation_adapter")

# Key EU financial regulations — curated reference (CELEX numbers verified)
KEY_REGULATIONS = {
    "MiFID_II": {"celex": "32014L0065", "name": "Markets in Financial Instruments Directive II", "year": 2014,
                 "type": "Directive", "summary": "Framework for EU securities markets, investor protection, trading venues."},
    "MiFIR": {"celex": "32014R0600", "name": "Markets in Financial Instruments Regulation", "year": 2014,
              "type": "Regulation", "summary": "Trade transparency, transaction reporting, derivatives trading on organised venues."},
    "GDPR": {"celex": "32016R0679", "name": "General Data Protection Regulation", "year": 2016,
             "type": "Regulation", "summary": "Personal data protection, privacy rights, cross-border data transfer rules."},
    "DORA": {"celex": "32022R2554", "name": "Digital Operational Resilience Act", "year": 2022,
             "type": "Regulation", "summary": "ICT risk management for financial entities, digital resilience testing, third-party risk."},
    "AI_Act": {"celex": "32024R1689", "name": "Artificial Intelligence Act", "year": 2024,
               "type": "Regulation", "summary": "Risk-based AI regulation, prohibited practices, high-risk AI systems, transparency."},
    "MiCA": {"celex": "32023R1114", "name": "Markets in Crypto-Assets Regulation", "year": 2023,
             "type": "Regulation", "summary": "Crypto-asset issuance, trading, custody; stablecoin rules; service provider licensing."},
    "SFDR": {"celex": "32019R2088", "name": "Sustainable Finance Disclosure Regulation", "year": 2019,
             "type": "Regulation", "summary": "ESG disclosure obligations for financial market participants and advisers."},
    "EU_Taxonomy": {"celex": "32020R0852", "name": "EU Taxonomy Regulation", "year": 2020,
                    "type": "Regulation", "summary": "Classification system for environmentally sustainable economic activities."},
    "PSD2": {"celex": "32015L2366", "name": "Payment Services Directive 2", "year": 2015,
             "type": "Directive", "summary": "Open banking, payment service providers, strong customer authentication (SCA)."},
    "AIFMD": {"celex": "32011L0061", "name": "Alternative Investment Fund Managers Directive", "year": 2011,
              "type": "Directive", "summary": "Regulation of hedge funds, private equity, real estate funds managers."},
    "UCITS_V": {"celex": "32014L0091", "name": "UCITS V Directive", "year": 2014,
                "type": "Directive", "summary": "Depositary duties, remuneration policies, sanctions for investment funds."},
    "CRD_V": {"celex": "32019L0878", "name": "Capital Requirements Directive V", "year": 2019,
              "type": "Directive", "summary": "Bank capital adequacy, supervisory review, market discipline (Basel III implementation)."},
    "CRR_II": {"celex": "32019R0876", "name": "Capital Requirements Regulation II", "year": 2019,
               "type": "Regulation", "summary": "Prudential requirements for credit institutions: leverage ratio, NSFR, TLAC."},
    "EMIR": {"celex": "32012R0648", "name": "European Market Infrastructure Regulation", "year": 2012,
             "type": "Regulation", "summary": "OTC derivatives, central counterparties (CCPs), trade repositories."},
    "BMR": {"celex": "32016R1011", "name": "EU Benchmarks Regulation", "year": 2016,
            "type": "Regulation", "summary": "Governance and integrity of financial benchmarks (LIBOR, EURIBOR replacements)."},
    "CSRD": {"celex": "32022L2464", "name": "Corporate Sustainability Reporting Directive", "year": 2022,
             "type": "Directive", "summary": "Mandatory ESG/sustainability reporting for large companies, EU sustainability standards."},
    "NIS2": {"celex": "32022L2555", "name": "Network and Information Security Directive 2", "year": 2022,
             "type": "Directive", "summary": "Cybersecurity obligations for essential/important entities including financial sector."},
    "eIDAS2": {"celex": "32024R1183", "name": "eIDAS 2.0 Regulation", "year": 2024,
               "type": "Regulation", "summary": "European Digital Identity Wallet, electronic identification, trust services."},
    "AMLD6": {"celex": "32024L1640", "name": "Anti-Money Laundering Directive 6", "year": 2024,
              "type": "Directive", "summary": "AML/CFT framework, beneficial ownership, virtual asset service providers."},
}

# Key FINRA rules — curated reference
KEY_FINRA_RULES = {
    "Rule_2111": {"name": "Suitability", "summary": "Brokers must have reasonable basis to recommend securities based on customer profile."},
    "Rule_2210": {"name": "Communications with the Public", "summary": "Standards for retail/institutional communications, advertisements, correspondence."},
    "Rule_3110": {"name": "Supervision", "summary": "Firms must establish supervisory systems, written procedures, and compliance oversight."},
    "Rule_4512": {"name": "Customer Account Information", "summary": "Requirements for maintaining customer account records and essential facts."},
    "Rule_4530": {"name": "Reporting Requirements", "summary": "Quarterly statistical/summary reports; reporting of specified events."},
    "Rule_5310": {"name": "Best Execution", "summary": "Obligation to seek the most favorable terms for customer orders."},
    "Rule_6730": {"name": "TRACE Transaction Reporting", "summary": "Reporting requirements for OTC transactions in TRACE-eligible securities."},
    "Reg_BI": {"name": "Regulation Best Interest", "summary": "SEC rule: broker-dealers must act in retail customers' best interest when recommending securities."},
    "Rule_3310": {"name": "AML Compliance Program", "summary": "Anti-money laundering program requirements, suspicious activity monitoring."},
    "Rule_2232": {"name": "Customer Confirmations", "summary": "Requirements for transaction confirmations sent to customers."},
    "Rule_4370": {"name": "Business Continuity Plans", "summary": "Emergency preparedness, business continuity and contingency planning."},
    "Rule_2165": {"name": "Financial Exploitation of Specified Adults",
                  "summary": "Protections for senior investors and vulnerable adults; temporary holds on disbursements."},
}


class RegulationAdapter:
    """EU regulations (EUR-Lex) and US FINRA compliance data — free, no auth required."""

    BASE_EURLEX = "https://eur-lex.europa.eu"
    CELLAR_SPARQL = "https://publications.europa.eu/webapi/rdf/sparql"

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "NexusFinanceMCP/1.0 (research; https://github.com/luxon-ai)",
            "Accept": "application/json",
        })

    def search_eu_regulations(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search EU regulations via CELLAR SPARQL endpoint."""
        try:
            # Sanitize query to prevent SPARQL injection
            import re
            query = re.sub(r'["\'\\\{\}\(\)<>]', '', query).strip()
            if not query or len(query) > 200:
                return error_response("Query must be 1-200 characters, no special characters")

            sparql = f"""
            PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT DISTINCT ?celex ?title ?date ?type WHERE {{
                ?work cdm:resource_legal_id_celex ?celex .
                ?work cdm:work_has_resource-type ?rtype .
                ?rtype skos:prefLabel ?type .
                FILTER(LANG(?type) = "en")
                ?exp cdm:expression_belongs_to_work ?work .
                ?exp cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/ENG> .
                ?exp cdm:expression_title ?title .
                OPTIONAL {{ ?work cdm:work_date_document ?date . }}
                FILTER(CONTAINS(LCASE(?title), LCASE("{query}")))
            }}
            ORDER BY DESC(?date)
            LIMIT {min(limit, 50)}
            """
            resp = self._session.get(
                self.CELLAR_SPARQL,
                params={"query": sparql, "format": "application/sparql-results+json"},
                timeout=20,
            )
            if resp.status_code != 200:
                return self._fallback_search(query, limit)

            results = resp.json().get("results", {}).get("bindings", [])
            records = []
            for r in results:
                celex = r.get("celex", {}).get("value", "")
                records.append({
                    "celex": celex,
                    "title": r.get("title", {}).get("value", ""),
                    "date": r.get("date", {}).get("value", ""),
                    "type": r.get("type", {}).get("value", ""),
                    "url": f"{self.BASE_EURLEX}/legal-content/EN/TXT/?uri=CELEX:{celex}",
                })
            return success_response(records, source="EUR-Lex/CELLAR SPARQL", query=query)
        except Exception as e:
            logger.error(f"EUR-Lex SPARQL search error: {e}")
            return self._fallback_search(query, limit)

    def _fallback_search(self, query: str, limit: int) -> Dict[str, Any]:
        """Fallback: return matching key regulations + search URL."""
        q_lower = query.lower()
        matches = []
        for key, reg in KEY_REGULATIONS.items():
            if (q_lower in reg["name"].lower() or q_lower in key.lower()
                    or q_lower in reg.get("summary", "").lower()):
                matches.append({
                    "key": key,
                    "celex": reg["celex"],
                    "name": reg["name"],
                    "year": reg["year"],
                    "type": reg["type"],
                    "summary": reg.get("summary", ""),
                    "url": f"{self.BASE_EURLEX}/legal-content/EN/TXT/?uri=CELEX:{reg['celex']}",
                })
        search_url = f"{self.BASE_EURLEX}/search.html?type=advanced&text={quote(query)}&qid=&DTS_DOM=ALL&scope=EURLEX"
        return success_response(
            matches[:limit],
            source="EUR-Lex/curated+search_url",
            query=query,
            search_url=search_url,
            note="Curated matches from key financial regulations. Use search_url for full EUR-Lex search.",
        )

    def get_regulation_text(self, celex_number: str) -> Dict[str, Any]:
        """Fetch regulation summary text from EUR-Lex by CELEX number."""
        try:
            url = f"{self.BASE_EURLEX}/legal-content/EN/TXT/HTML/?uri=CELEX:{celex_number}"
            resp = self._session.get(url, timeout=20, headers={"Accept": "text/html"})
            if resp.status_code != 200:
                # Try curated data
                for key, reg in KEY_REGULATIONS.items():
                    if reg["celex"] == celex_number:
                        return success_response(
                            None,
                            source="EUR-Lex/curated",
                            celex=celex_number,
                            title=reg["name"],
                            year=reg["year"],
                            type=reg["type"],
                            summary=reg.get("summary", ""),
                            url=f"{self.BASE_EURLEX}/legal-content/EN/TXT/?uri=CELEX:{celex_number}",
                            note="Full text unavailable; curated summary returned.",
                        )
                return error_response(f"EUR-Lex returned HTTP {resp.status_code} for CELEX {celex_number}")

            # Extract text from HTML (simple extraction without heavy parsing)
            from html.parser import HTMLParser

            class _TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self._texts = []
                    self._skip = False

                def handle_starttag(self, tag, attrs):
                    if tag in ("script", "style", "nav", "header", "footer"):
                        self._skip = True

                def handle_endtag(self, tag):
                    if tag in ("script", "style", "nav", "header", "footer"):
                        self._skip = False

                def handle_data(self, data):
                    if not self._skip:
                        stripped = data.strip()
                        if stripped:
                            self._texts.append(stripped)

            extractor = _TextExtractor()
            extractor.feed(resp.text)
            full_text = " ".join(extractor._texts)

            # Find title from curated data if available
            title = ""
            reg_type = ""
            year = ""
            for key, reg in KEY_REGULATIONS.items():
                if reg["celex"] == celex_number:
                    title = reg["name"]
                    reg_type = reg["type"]
                    year = reg["year"]
                    break

            # Limit text to 5000 chars
            text_excerpt = full_text[:5000]
            if len(full_text) > 5000:
                text_excerpt += "... [truncated]"

            return success_response(
                text_excerpt,
                source="EUR-Lex",
                celex=celex_number,
                title=title or "See document",
                type=reg_type or "Unknown",
                year=year or "Unknown",
                text_length=len(full_text),
                url=f"{self.BASE_EURLEX}/legal-content/EN/TXT/?uri=CELEX:{celex_number}",
            )
        except Exception as e:
            logger.error(f"EUR-Lex text fetch error for {celex_number}: {e}")
            return error_response(f"Failed to retrieve regulation text for CELEX {celex_number}")

    def get_key_financial_regulations(self) -> Dict[str, Any]:
        """Return curated list of 19 key EU financial regulations."""
        data = {}
        for key, reg in KEY_REGULATIONS.items():
            data[key] = {
                **reg,
                "url": f"{self.BASE_EURLEX}/legal-content/EN/TXT/?uri=CELEX:{reg['celex']}",
            }
        return success_response(
            data,
            source="EUR-Lex/curated",
            categories={
                "securities_markets": ["MiFID_II", "MiFIR", "EMIR", "BMR"],
                "banking_prudential": ["CRD_V", "CRR_II"],
                "investment_funds": ["AIFMD", "UCITS_V"],
                "payments": ["PSD2"],
                "crypto_digital": ["MiCA", "DORA", "eIDAS2"],
                "sustainability_esg": ["SFDR", "EU_Taxonomy", "CSRD"],
                "data_privacy_security": ["GDPR", "NIS2"],
                "aml_compliance": ["AMLD6"],
                "artificial_intelligence": ["AI_Act"],
            },
        )

    def search_finra_rules(self) -> Dict[str, Any]:
        """Return curated FINRA rules reference + useful links."""
        return success_response(
            KEY_FINRA_RULES,
            source="FINRA/curated",
            links={
                "finra_rulebook": "https://www.finra.org/rules-guidance/rulebooks/finra-rules",
                "finra_rule_search": "https://www.finra.org/rules-guidance/rulebooks/search",
                "sec_edgar": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany",
                "sec_reg_bi": "https://www.sec.gov/regulation-best-interest",
                "finra_brokercheck": "https://brokercheck.finra.org/",
            },
            note="FINRA does not provide a public REST API. Use links for detailed rule text.",
        )
