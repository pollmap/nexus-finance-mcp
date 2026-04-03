"""
Research/Academic Adapter — Korean research databases.
Covers: RISS, NKIS, PRISM, National Library, National Assembly Library, Google Scholar.
Most use data.go.kr unified gateway API key.
"""
import logging
import os
import requests
from utils.http_client import get_session
from typing import Any, Dict

logger = logging.getLogger(__name__)
_session = get_session("research_adapter")


class ResearchAdapter:
    """Korean academic & policy research data — free APIs."""

    def __init__(self):
        self._data_go_kr_key = os.getenv("DATA_GO_KR_API_KEY", "")
        self._riss_key = os.getenv("RISS_API_KEY", self._data_go_kr_key)
        self._nl_key = os.getenv("NL_CERT_KEY", self._data_go_kr_key)

    def search_riss(self, query: str, page: int = 1, count: int = 10) -> Dict[str, Any]:
        """RISS 학술논문 검색."""
        try:
            url = "https://www.riss.kr/openapi/search/Search.do"
            params = {
                "apiKey": self._riss_key,
                "query": query,
                "startCount": (page - 1) * count,
                "maxCount": count,
                "output": "json",
            }
            resp = _session.get(url, params=params, timeout=15)
            data = resp.json() if resp.status_code == 200 else {}

            items = data.get("result", data.get("items", []))
            if isinstance(items, dict):
                items = items.get("items", items.get("item", []))
            if not isinstance(items, list):
                items = []

            records = []
            for item in items[:count]:
                records.append({
                    "title": item.get("title", ""),
                    "author": item.get("creator", item.get("author", "")),
                    "journal": item.get("publisher", ""),
                    "year": item.get("date", ""),
                    "url": item.get("link", item.get("url", "")),
                })

            return {"success": True, "source": "RISS", "query": query, "count": len(records), "data": records}
        except Exception as e:
            logger.error(f"RISS search error: {e}")
            return {"error": True, "message": str(e)}

    def search_nkis(self, query: str, page: int = 1, count: int = 10) -> Dict[str, Any]:
        """NKIS 국책연구원 보고서 검색."""
        try:
            url = "https://apis.data.go.kr/B553530/nkis/openDescApi"
            params = {
                "serviceKey": self._data_go_kr_key,
                "query": query,
                "pageNo": page,
                "numOfRows": count,
                "type": "json",
            }
            resp = _session.get(url, params=params, timeout=15)
            data = resp.json() if resp.status_code == 200 else {}

            body = data.get("response", {}).get("body", {})
            items = body.get("items", body.get("item", []))
            if isinstance(items, dict):
                items = items.get("item", [])
            if not isinstance(items, list):
                items = []

            records = []
            for item in items[:count]:
                records.append({
                    "title": item.get("title", item.get("TITLE", "")),
                    "author": item.get("author", item.get("AUTHOR", "")),
                    "institute": item.get("institute", item.get("INST_NM", "")),
                    "year": item.get("year", item.get("PUB_YEAR", "")),
                    "abstract": item.get("abstract", item.get("ABSTRACT", ""))[:300],
                })

            return {"success": True, "source": "NKIS", "query": query, "count": len(records), "data": records}
        except Exception as e:
            logger.error(f"NKIS search error: {e}")
            return {"error": True, "message": str(e)}

    def search_prism(self, query: str, page: int = 1, count: int = 10) -> Dict[str, Any]:
        """PRISM 정부 정책연구과제 검색."""
        try:
            url = "https://apis.data.go.kr/1741000/prism_policy_research/getList"
            params = {
                "serviceKey": self._data_go_kr_key,
                "searchTxt": query,
                "pageNo": page,
                "numOfRows": count,
                "type": "json",
            }
            resp = _session.get(url, params=params, timeout=15)
            data = resp.json() if resp.status_code == 200 else {}

            body = data.get("response", {}).get("body", {})
            items = body.get("items", body.get("item", []))
            if isinstance(items, dict):
                items = items.get("item", [])
            if not isinstance(items, list):
                items = []

            records = []
            for item in items[:count]:
                records.append({
                    "title": item.get("rsrchRptNm", item.get("title", "")),
                    "researcher": item.get("rsrchNm", item.get("researcher", "")),
                    "ministry": item.get("dmnstInsttNm", item.get("ministry", "")),
                    "year": (item.get("rsrchEndDe") or item.get("year") or "")[:4],
                })

            return {"success": True, "source": "PRISM", "query": query, "count": len(records), "data": records}
        except Exception as e:
            logger.error(f"PRISM search error: {e}")
            return {"error": True, "message": str(e)}

    def search_nl(self, query: str, page: int = 1, count: int = 10) -> Dict[str, Any]:
        """국립중앙도서관 서지정보 검색."""
        try:
            url = "https://www.nl.go.kr/seoji/SearchApi.do"
            params = {
                "cert_key": self._nl_key,
                "result_style": "json",
                "page_no": page,
                "page_size": count,
                "kwd": query,
            }
            resp = _session.get(url, params=params, timeout=15)
            data = resp.json() if resp.status_code == 200 else {}

            items = data.get("docs", data.get("result", []))
            if not isinstance(items, list):
                items = []

            records = []
            for item in items[:count]:
                records.append({
                    "title": item.get("TITLE", item.get("title", "")),
                    "author": item.get("AUTHOR", item.get("author", "")),
                    "publisher": item.get("PUBLISHER", item.get("publisher", "")),
                    "isbn": item.get("EA_ISBN", item.get("isbn", "")),
                    "year": (item.get("PUBLISH_PREDATE") or item.get("year") or "")[:4],
                })

            return {"success": True, "source": "NL", "query": query, "count": len(records), "data": records}
        except Exception as e:
            logger.error(f"NL search error: {e}")
            return {"error": True, "message": str(e)}

    def search_nanet(self, query: str, page: int = 1, count: int = 10) -> Dict[str, Any]:
        """국회전자도서관 K-Scholar 검색."""
        try:
            url = "https://apis.data.go.kr/9710000/NationalAssemblyLibraryOpenAPI/getKScholarData"
            params = {
                "serviceKey": self._data_go_kr_key,
                "query": query,
                "pageNo": page,
                "numOfRows": count,
                "type": "json",
            }
            resp = _session.get(url, params=params, timeout=15)
            data = resp.json() if resp.status_code == 200 else {}

            body = data.get("response", {}).get("body", {})
            items = body.get("items", body.get("item", []))
            if isinstance(items, dict):
                items = items.get("item", [])
            if not isinstance(items, list):
                items = []

            records = []
            for item in items[:count]:
                records.append({
                    "title": item.get("title", item.get("TITLE", "")),
                    "author": item.get("author", item.get("AUTHOR", "")),
                    "type": item.get("type", item.get("DOC_TYPE", "")),
                    "year": item.get("year", item.get("PUB_YEAR", "")),
                    "url": item.get("url", item.get("LINK", "")),
                })

            return {"success": True, "source": "NANET", "query": query, "count": len(records), "data": records}
        except Exception as e:
            logger.error(f"NANET search error: {e}")
            return {"error": True, "message": str(e)}

    def search_scholar(self, query: str, count: int = 5) -> Dict[str, Any]:
        """Google Scholar 검색 (scholarly 라이브러리)."""
        try:
            from scholarly import scholarly as sch
            results = sch.search_pubs(query)

            records = []
            for i, result in enumerate(results):
                if i >= count:
                    break
                bib = result.get("bib", {})
                records.append({
                    "title": bib.get("title", ""),
                    "author": ", ".join(bib.get("author", []))[:200],
                    "year": bib.get("pub_year", ""),
                    "venue": bib.get("venue", ""),
                    "abstract": bib.get("abstract", "")[:300],
                    "citations": result.get("num_citations", 0),
                    "url": result.get("pub_url", result.get("eprint_url", "")),
                })

            return {"success": True, "source": "Google Scholar", "query": query, "count": len(records), "data": records}
        except ImportError:
            return {"error": True, "message": "scholarly not installed. pip install scholarly"}
        except Exception as e:
            logger.error(f"Scholar search error: {e}")
            return {"error": True, "message": str(e)}
