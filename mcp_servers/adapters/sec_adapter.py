"""SEC EDGAR Adapter — US financial disclosure system. No auth required."""
import logging
import os
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlencode
import requests
from utils.http_client import get_session
from typing import Any, Dict, List

from mcp_servers.core.rate_limiter import get_limiter
from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)
_session = get_session("sec_adapter")

CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "research@nexus.finance")
HEADERS = {"User-Agent": f"NexusFinanceMCP {CONTACT_EMAIL}", "Accept-Encoding": "gzip, deflate"}

# SSRF protection: only allow SEC domains
ALLOWED_SEC_HOSTS = {"www.sec.gov", "sec.gov", "data.sec.gov", "efts.sec.gov"}


class SECAdapter:
    """SEC EDGAR API — company filings, XBRL facts."""

    _ticker_map = None
    _limiter = None

    def _rate_limit(self):
        """Apply rate limiting for SEC API (10 req/sec policy)."""
        if self._limiter is None:
            self._limiter = get_limiter()
        self._limiter.acquire("sec")

    def _get_cik(self, ticker: str) -> str:
        """Resolve ticker to CIK (zero-padded 10 digits)."""
        if self._ticker_map is None:
            try:
                resp = _session.get("https://www.sec.gov/files/company_tickers.json", headers=HEADERS, timeout=10)
                data = resp.json()
                SECAdapter._ticker_map = {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in data.values()}
            except Exception:
                SECAdapter._ticker_map = {}
        return self._ticker_map.get(ticker.upper(), "")

    def search_filings(self, query: str, form_type: str = "10-K", limit: int = 10) -> Dict[str, Any]:
        """EDGAR Full-Text Search."""
        try:
            self._rate_limit()
            url = "https://efts.sec.gov/LATEST/search-index"
            params = {"q": query, "forms": form_type, "dateRange": "custom",
                      "startdt": "2020-01-01", "enddt": "2026-12-31"}
            resp = _session.get(url, params=params, headers=HEADERS, timeout=15)

            data = resp.json() if resp.status_code == 200 else {}
            hits = data.get("hits", {}).get("hits", [])[:limit]

            records = []
            for hit in hits:
                src = hit.get("_source", {})
                # Build correct EDGAR URL using accession number
                accession = (src.get("accession_no", "") or "").replace("-", "")
                entity_id = src.get("entity_id", "")
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{entity_id}/{accession}/" if accession else ""
                records.append({
                    "company": src.get("display_names", [""])[0] if src.get("display_names") else "",
                    "form": src.get("form_type", ""),
                    "date": src.get("file_date", ""),
                    "url": filing_url,
                })

            return success_response(records, source="SEC EDGAR", query=query)
        except Exception as e:
            logger.error(f"SEC search error: {e}")
            return error_response(f"SEC EDGAR search failed: {e}")

    def get_company_facts(self, ticker: str) -> Dict[str, Any]:
        """Get XBRL company facts (structured financials)."""
        try:
            self._rate_limit()
            cik = self._get_cik(ticker)
            if not cik:
                return error_response(f"Ticker '{ticker}' not found in SEC database", code="NOT_FOUND")

            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            resp = _session.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                return error_response(f"SEC API returned HTTP {resp.status_code}")

            data = resp.json()
            facts = data.get("facts", {})

            us_gaap = facts.get("us-gaap", {})
            key_metrics = {}
            target_fields = [
                "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                "NetIncomeLoss", "OperatingIncomeLoss",
                "Assets", "Liabilities", "StockholdersEquity",
                "EarningsPerShareBasic", "EarningsPerShareDiluted",
                "CashAndCashEquivalentsAtCarryingValue",
                "OperatingCashFlow", "NetCashProvidedByOperatingActivities",
            ]

            for field in target_fields:
                if field in us_gaap:
                    units = us_gaap[field].get("units", {})
                    for unit_key, entries in units.items():
                        # C2 FIX: correct boolean filter (was: not X == False)
                        annual = [e for e in entries if e.get("form") == "10-K" and not e.get("frame", "").startswith("CY")]
                        if annual:
                            recent = sorted(annual, key=lambda x: x.get("end", ""))[-3:]
                            key_metrics[field] = [{"period": e.get("end", ""), "value": e.get("val"), "unit": unit_key} for e in recent]
                        break

            return success_response(
                data=key_metrics,
                source="SEC EDGAR",
                ticker=ticker,
                cik=cik,
                company=data.get("entityName", ""),
                metrics_count=len(key_metrics),
            )
        except Exception as e:
            logger.error(f"SEC company facts error: {e}")
            return error_response(f"SEC XBRL data retrieval failed: {e}")

    def _fetch_company_facts(self, ticker: str) -> tuple:
        """Fetch raw company facts JSON. Returns (data_dict, error_response_or_None)."""
        self._rate_limit()
        cik = self._get_cik(ticker)
        if not cik:
            return None, error_response(f"Ticker '{ticker}' not found in SEC database", code="NOT_FOUND")
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        resp = _session.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None, error_response(f"SEC API returned HTTP {resp.status_code}")
        data = resp.json()
        data["_cik"] = cik
        return data, None

    def get_xbrl_concept(self, ticker: str, concept: str, namespace: str = "us-gaap") -> Dict[str, Any]:
        """Query arbitrary XBRL concept for a company.

        Args:
            ticker: Stock ticker (e.g., "AAPL")
            concept: XBRL concept name (e.g., "GrossProfit", "InventoryNet", "DeferredTaxAssets")
            namespace: Taxonomy namespace (default: "us-gaap")
        """
        try:
            data, err = self._fetch_company_facts(ticker)
            if err:
                return err

            facts = data.get("facts", {})
            ns_facts = facts.get(namespace, {})
            if concept not in ns_facts:
                available = [k for k in ns_facts if concept.lower() in k.lower()]
                msg = f"Concept '{concept}' not found in {namespace} for {ticker.upper()}"
                if available:
                    msg += f". Similar: {', '.join(available)}"
                return error_response(msg, code="NOT_FOUND")

            concept_data = ns_facts[concept]
            label = concept_data.get("label", concept)
            description = concept_data.get("description", "")
            units = concept_data.get("units", {})

            result = {}
            for unit_key, entries in units.items():
                annual = [e for e in entries if e.get("form") == "10-K"]
                if annual:
                    recent = sorted(annual, key=lambda x: x.get("end", ""))[-5:]
                    result[unit_key] = [
                        {"period": e.get("end", ""), "value": e.get("val"), "filed": e.get("filed", "")}
                        for e in recent
                    ]

            return success_response(
                data=result,
                source="SEC EDGAR XBRL",
                ticker=ticker.upper(),
                cik=data["_cik"],
                company=data.get("entityName", ""),
                concept=concept,
                namespace=namespace,
                label=label,
                description=description,
            )
        except Exception as e:
            logger.error(f"SEC XBRL concept error: {e}")
            return error_response(f"SEC XBRL concept query failed: {e}")

    def list_xbrl_concepts(self, ticker: str, filter_keyword: str = "") -> Dict[str, Any]:
        """List all XBRL concepts reported by a company, optionally filtered by keyword.

        Args:
            ticker: Stock ticker
            filter_keyword: Optional keyword to filter concept names (case-insensitive)
        """
        try:
            data, err = self._fetch_company_facts(ticker)
            if err:
                return err

            facts = data.get("facts", {})
            us_gaap = facts.get("us-gaap", {})

            concepts: List[Dict[str, str]] = []
            kw = filter_keyword.lower()
            for name, info in us_gaap.items():
                if kw and kw not in name.lower():
                    continue
                concepts.append({
                    "concept": name,
                    "label": info.get("label", ""),
                    "units": list(info.get("units", {}).keys()),
                })

            concepts.sort(key=lambda x: x["concept"])

            return success_response(
                data=concepts,
                count=len(concepts),
                source="SEC EDGAR XBRL",
                ticker=ticker.upper(),
                cik=data["_cik"],
                company=data.get("entityName", ""),
                total_us_gaap_concepts=len(us_gaap),
                filter_keyword=filter_keyword or None,
            )
        except Exception as e:
            logger.error(f"SEC list concepts error: {e}")
            return error_response(f"SEC XBRL concept listing failed: {e}")

    def get_filing_text(self, filing_url: str, max_chars: int = 5000) -> Dict[str, Any]:
        """Fetch filing document text (HTML stripped). Only SEC domains allowed."""
        try:
            self._rate_limit()
            # C1 FIX: SSRF protection — allowlist SEC domains only
            parsed = urlparse(filing_url)
            if parsed.hostname not in ALLOWED_SEC_HOSTS or parsed.scheme not in ("https", "http"):
                return error_response("Only SEC EDGAR URLs (sec.gov) are allowed")

            resp = _session.get(filing_url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                return error_response(f"HTTP {resp.status_code}")

            text = re.sub(r'<[^>]+>', ' ', resp.text)
            text = re.sub(r'\s+', ' ', text).strip()

            return success_response(
                data=text[:max_chars],
                source="SEC EDGAR",
                url=filing_url,
                text_length=len(text),
                truncated=len(text) > max_chars,
            )
        except Exception as e:
            logger.error(f"SEC filing text error: {e}")
            return error_response(f"SEC filing text retrieval failed: {e}")

    def get_submission_metadata(self, ticker: str) -> Dict[str, Any]:
        """Get SEC submission metadata (CIK, recent filings list, SIC code)."""
        try:
            self._rate_limit()
            cik = self._get_cik(ticker)
            if not cik:
                return error_response(f"Ticker '{ticker}' not found in SEC database", code="NOT_FOUND")

            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            resp = _session.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                return error_response(f"SEC API returned HTTP {resp.status_code}")

            data = resp.json()
            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accessions = recent.get("accessionNumber", [])
            descriptions = recent.get("primaryDocDescription", [])
            filings_list = [
                {"form": f, "date": d, "accession": a, "description": desc}
                for f, d, a, desc in zip(forms, dates, accessions, descriptions)
            ]

            return success_response(
                data={
                    "cik": cik,
                    "name": data.get("name"),
                    "sic": data.get("sic"),
                    "sic_description": data.get("sicDescription"),
                    "ticker": ticker.upper(),
                    "exchanges": data.get("exchanges", []),
                    "fiscal_year_end": data.get("fiscalYearEnd"),
                    "recent_filings": filings_list,
                },
                source="SEC EDGAR",
                ticker=ticker.upper(),
                cik=cik,
            )
        except Exception as e:
            logger.error(f"SEC submission metadata error: {e}")
            return error_response(f"SEC submission metadata retrieval failed: {e}")

    def get_insider_transactions(self, ticker: str, limit: int = 20) -> Dict[str, Any]:
        """Get recent insider trading (Form 4) data."""
        try:
            self._rate_limit()
            url = "https://efts.sec.gov/LATEST/search-index"
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")
            params = {
                "q": f'"{ticker.upper()}"',
                "forms": "4",
                "dateRange": "custom",
                "startdt": start_date,
                "enddt": end_date,
            }
            resp = _session.get(url, params=params, headers=HEADERS, timeout=15)

            data = resp.json() if resp.status_code == 200 else {}
            hits = data.get("hits", {}).get("hits", [])[:limit]

            records = []
            for hit in hits:
                src = hit.get("_source", {})
                accession = (src.get("accession_no", "") or "").replace("-", "")
                entity_id = src.get("entity_id", "")
                filing_url = (
                    f"https://www.sec.gov/Archives/edgar/data/{entity_id}/{accession}/"
                    if accession else ""
                )
                records.append({
                    "filer": src.get("display_names", [""])[0] if src.get("display_names") else "",
                    "form": src.get("form_type", ""),
                    "date": src.get("file_date", ""),
                    "url": filing_url,
                })

            return success_response(
                data=records,
                source="SEC EDGAR",
                ticker=ticker.upper(),
                form_type="4",
                count=len(records),
                date_range=f"{start_date} ~ {end_date}",
            )
        except Exception as e:
            logger.error(f"SEC insider transactions error: {e}")
            return error_response(f"SEC insider transactions retrieval failed: {e}")

    def get_institutional_holders(self, ticker: str) -> Dict[str, Any]:
        """Get institutional holdings (13F filings)."""
        try:
            self._rate_limit()
            url = "https://efts.sec.gov/LATEST/search-index"
            params = {
                "q": f'"{ticker.upper()}"',
                "forms": "13F-HR",
                "dateRange": "custom",
                "startdt": (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
                "enddt": datetime.now().strftime("%Y-%m-%d"),
            }
            resp = _session.get(url, params=params, headers=HEADERS, timeout=15)

            data = resp.json() if resp.status_code == 200 else {}
            hits = data.get("hits", {}).get("hits", [])

            records = []
            for hit in hits:
                src = hit.get("_source", {})
                accession = (src.get("accession_no", "") or "").replace("-", "")
                entity_id = src.get("entity_id", "")
                filing_url = (
                    f"https://www.sec.gov/Archives/edgar/data/{entity_id}/{accession}/"
                    if accession else ""
                )
                records.append({
                    "institution": src.get("display_names", [""])[0] if src.get("display_names") else "",
                    "form": src.get("form_type", ""),
                    "date": src.get("file_date", ""),
                    "url": filing_url,
                })

            return success_response(
                data=records,
                source="SEC EDGAR",
                ticker=ticker.upper(),
                form_type="13F-HR",
                count=len(records),
            )
        except Exception as e:
            logger.error(f"SEC institutional holders error: {e}")
            return error_response(f"SEC institutional holders retrieval failed: {e}")
