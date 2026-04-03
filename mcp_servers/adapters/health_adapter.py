"""Health/Biotech Adapter — FDA, ClinicalTrials.gov, PubMed, WHO."""
import logging
import os
import requests
from utils.http_client import get_session
from typing import Any, Dict

logger = logging.getLogger(__name__)
_session = get_session("health_adapter")


class HealthAdapter:
    """Global health & biotech data — free APIs."""

    def __init__(self):
        self._fda_key = os.getenv("OPENFDA_API_KEY", "")
        self._ncbi_key = os.getenv("NCBI_API_KEY", "")

    def search_fda_drugs(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """openFDA 의약품 라벨 검색."""
        try:
            url = "https://api.fda.gov/drug/label.json"
            params = {"search": query, "limit": limit}
            if self._fda_key:
                params["api_key"] = self._fda_key
            resp = _session.get(url, params=params, timeout=15)
            data = resp.json() if resp.status_code == 200 else {}

            results = data.get("results", [])
            records = []
            for r in results[:limit]:
                openfda = r.get("openfda", {})
                records.append({
                    "brand_name": (openfda.get("brand_name") or [""])[0],
                    "generic_name": (openfda.get("generic_name") or [""])[0],
                    "manufacturer": (openfda.get("manufacturer_name") or [""])[0],
                    "indications": (r.get("indications_and_usage") or [""])[:1],
                    "route": (openfda.get("route") or [""])[0],
                })

            return {"success": True, "source": "openFDA/drug/label", "query": query, "count": len(records), "data": records}
        except Exception as e:
            return {"error": True, "message": str(e)}

    def search_fda_recalls(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """openFDA 리콜/집행조치 검색."""
        try:
            url = "https://api.fda.gov/drug/enforcement.json"
            params = {"search": query, "limit": limit}
            if self._fda_key:
                params["api_key"] = self._fda_key
            resp = _session.get(url, params=params, timeout=15)
            data = resp.json() if resp.status_code == 200 else {}

            results = data.get("results", [])
            records = []
            for r in results[:limit]:
                records.append({
                    "product": r.get("product_description", "")[:200],
                    "reason": r.get("reason_for_recall", "")[:200],
                    "classification": r.get("classification", ""),
                    "status": r.get("status", ""),
                    "date": r.get("report_date", ""),
                    "company": r.get("recalling_firm", ""),
                })

            return {"success": True, "source": "openFDA/enforcement", "query": query, "count": len(records), "data": records}
        except Exception as e:
            return {"error": True, "message": str(e)}

    def search_clinical_trials(self, query: str, status: str = "RECRUITING", limit: int = 10) -> Dict[str, Any]:
        """ClinicalTrials.gov v2 API 임상시험 검색."""
        try:
            url = "https://clinicaltrials.gov/api/v2/studies"
            params = {"query.term": query, "filter.overallStatus": status, "pageSize": limit, "format": "json"}
            resp = _session.get(url, params=params, timeout=15)
            data = resp.json() if resp.status_code == 200 else {}

            studies = data.get("studies", [])
            records = []
            for s in studies[:limit]:
                proto = s.get("protocolSection", {})
                ident = proto.get("identificationModule", {})
                status_mod = proto.get("statusModule", {})
                design = proto.get("designModule", {})
                cond = proto.get("conditionsModule", {})
                sponsor = proto.get("sponsorCollaboratorsModule", {})

                records.append({
                    "nct_id": ident.get("nctId", ""),
                    "title": ident.get("briefTitle", ""),
                    "status": status_mod.get("overallStatus", ""),
                    "phase": ", ".join(design.get("phases", [])),
                    "conditions": cond.get("conditions", [])[:3],
                    "sponsor": sponsor.get("leadSponsor", {}).get("name", ""),
                    "start_date": status_mod.get("startDateStruct", {}).get("date", ""),
                })

            return {"success": True, "source": "ClinicalTrials.gov", "query": query, "count": len(records), "data": records}
        except Exception as e:
            return {"error": True, "message": str(e)}

    def search_pubmed(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """PubMed/NCBI 논문 검색."""
        try:
            # Step 1: Search for IDs
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            params = {"db": "pubmed", "term": query, "retmax": limit, "retmode": "json"}
            if self._ncbi_key:
                params["api_key"] = self._ncbi_key
            resp = _session.get(search_url, params=params, timeout=15)
            search_data = (resp.json() if resp.status_code == 200 else {}).get("esearchresult", {})
            id_list = search_data.get("idlist", [])

            if not id_list:
                return {"success": True, "source": "PubMed", "query": query, "count": 0, "data": []}

            # Step 2: Fetch summaries
            summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            params = {"db": "pubmed", "id": ",".join(id_list), "retmode": "json"}
            if self._ncbi_key:
                params["api_key"] = self._ncbi_key
            resp = _session.get(summary_url, params=params, timeout=15)
            result_data = (resp.json() if resp.status_code == 200 else {}).get("result", {})

            records = []
            for pmid in id_list:
                article = result_data.get(pmid, {})
                if not isinstance(article, dict):
                    continue
                authors = article.get("authors", [])
                author_str = ", ".join(a.get("name", "") for a in authors[:3])
                records.append({
                    "pmid": pmid,
                    "title": article.get("title", ""),
                    "authors": author_str,
                    "journal": article.get("fulljournalname", article.get("source", "")),
                    "pubdate": article.get("pubdate", ""),
                    "doi": next((a.get("value", "") for a in article.get("articleids", []) if a.get("idtype") == "doi"), ""),
                })

            return {"success": True, "source": "PubMed", "query": query, "count": len(records), "data": records}
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_who_indicator(self, indicator_code: str = "WHOSIS_000001", country: str = "KOR") -> Dict[str, Any]:
        """WHO GHO API 건강 지표 조회."""
        try:
            url = f"https://ghoapi.azureedge.net/api/{indicator_code}"
            params = {"$filter": f"SpatialDim eq '{country}'", "$orderby": "TimeDim desc", "$top": 20}
            resp = _session.get(url, params=params, timeout=15)
            data = resp.json() if resp.status_code == 200 else {}

            values = data.get("value", [])
            records = [{"year": v.get("TimeDim"), "value": v.get("NumericValue"), "dim": v.get("Dim1")} for v in values]

            return {"success": True, "source": "WHO/GHO", "indicator": indicator_code, "country": country, "count": len(records), "data": records}
        except Exception as e:
            return {"error": True, "message": str(e)}
