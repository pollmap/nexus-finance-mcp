"""SEC EDGAR Adapter — US financial disclosure system. No auth required."""
import logging
import os
import re
from urllib.parse import urlparse, urlencode
import requests
from typing import Any, Dict

from mcp_servers.core.rate_limiter import get_limiter

logger = logging.getLogger(__name__)

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
                resp = requests.get("https://www.sec.gov/files/company_tickers.json", headers=HEADERS, timeout=10)
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
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)

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

            return {"success": True, "source": "SEC EDGAR", "query": query, "count": len(records), "data": records}
        except Exception as e:
            logger.error(f"SEC search error: {e}")
            return {"error": True, "message": f"SEC EDGAR search failed: {e}"}

    def get_company_facts(self, ticker: str) -> Dict[str, Any]:
        """Get XBRL company facts (structured financials)."""
        try:
            self._rate_limit()
            cik = self._get_cik(ticker)
            if not cik:
                return {"error": True, "message": f"Ticker '{ticker}' not found in SEC database"}

            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                return {"error": True, "message": f"SEC API returned HTTP {resp.status_code}"}

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

            return {
                "success": True, "source": "SEC EDGAR XBRL",
                "ticker": ticker, "cik": cik,
                "company": data.get("entityName", ""),
                "metrics_count": len(key_metrics),
                "data": key_metrics,
            }
        except Exception as e:
            logger.error(f"SEC company facts error: {e}")
            return {"error": True, "message": f"SEC XBRL data retrieval failed: {e}"}

    def get_filing_text(self, filing_url: str, max_chars: int = 5000) -> Dict[str, Any]:
        """Fetch filing document text (HTML stripped). Only SEC domains allowed."""
        try:
            self._rate_limit()
            # C1 FIX: SSRF protection — allowlist SEC domains only
            parsed = urlparse(filing_url)
            if parsed.hostname not in ALLOWED_SEC_HOSTS or parsed.scheme not in ("https", "http"):
                return {"error": True, "message": "Only SEC EDGAR URLs (sec.gov) are allowed"}

            resp = requests.get(filing_url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                return {"error": True, "message": f"HTTP {resp.status_code}"}

            text = re.sub(r'<[^>]+>', ' ', resp.text)
            text = re.sub(r'\s+', ' ', text).strip()

            return {
                "success": True, "source": "SEC EDGAR",
                "url": filing_url,
                "text_length": len(text),
                "text": text[:max_chars],
                "truncated": len(text) > max_chars,
            }
        except Exception as e:
            logger.error(f"SEC filing text error: {e}")
            return {"error": True, "message": f"SEC filing text retrieval failed: {e}"}
