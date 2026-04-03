"""
GDELT Adapter — Global news monitoring (100+ languages, 15-min updates).
Academic Adapter — arXiv, Semantic Scholar, OpenAlex paper search.

Both completely free, no API keys needed.
"""
import logging
import os
import requests
from typing import Any, Dict, List
from urllib.parse import quote

logger = logging.getLogger(__name__)


class GDELTAdapter:
    """GDELT DOC 2.0 API — global event/news monitoring."""

    BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

    def search_articles(
        self, query: str, mode: str = "ArtList", max_records: int = 20,
        sourcelang: str = "", timespan: str = "7d"
    ) -> Dict[str, Any]:
        """Search GDELT articles."""
        try:
            params = {
                "query": query,
                "mode": mode,
                "maxrecords": min(max_records, 250),
                "format": "json",
                "timespan": timespan,
            }
            if sourcelang:
                params["sourcelang"] = sourcelang

            resp = requests.get(self.BASE_URL, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()

            articles = []
            for a in data.get("articles", [])[:max_records]:
                articles.append({
                    "title": a.get("title"),
                    "url": a.get("url"),
                    "source": a.get("domain"),
                    "language": a.get("language"),
                    "date": a.get("seendate"),
                    "tone": a.get("tone"),
                })

            return {"success": True, "query": query, "count": len(articles), "articles": articles}
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_timeline(self, query: str, timespan: str = "30d") -> Dict[str, Any]:
        """Get article volume timeline for a query."""
        try:
            params = {
                "query": query, "mode": "TimelineVol",
                "format": "json", "timespan": timespan,
            }
            resp = requests.get(self.BASE_URL, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            timeline = data.get("timeline", [{}])
            series = timeline[0].get("data", []) if timeline else []
            return {"success": True, "query": query, "count": len(series), "timeline": series[:60]}
        except Exception as e:
            return {"error": True, "message": str(e)}


class AcademicAdapter:
    """Academic paper search — arXiv, Semantic Scholar, OpenAlex."""

    def search_arxiv(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search arXiv papers."""
        try:
            url = "http://export.arxiv.org/api/query"
            params = {"search_query": f"all:{query}", "max_results": max_results, "sortBy": "submittedDate", "sortOrder": "descending"}
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()

            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            papers = []
            for entry in root.findall("atom:entry", ns)[:max_results]:
                title = entry.find("atom:title", ns)
                summary = entry.find("atom:summary", ns)
                published = entry.find("atom:published", ns)
                link = entry.find("atom:id", ns)
                papers.append({
                    "title": title.text.strip() if title is not None else "",
                    "summary": (summary.text.strip()[:300] + "...") if summary is not None else "",
                    "published": published.text if published is not None else "",
                    "url": link.text if link is not None else "",
                })

            return {"success": True, "source": "arXiv", "query": query, "count": len(papers), "papers": papers}
        except Exception as e:
            return {"error": True, "message": str(e)}

    def search_semantic_scholar(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search Semantic Scholar."""
        try:
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {"query": query, "limit": limit, "fields": "title,year,citationCount,url,abstract"}
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            papers = []
            for p in data.get("data", []):
                abstract = p.get("abstract") or ""
                papers.append({
                    "title": p.get("title"),
                    "year": p.get("year"),
                    "citations": p.get("citationCount"),
                    "url": p.get("url"),
                    "abstract": abstract[:300] + "..." if len(abstract) > 300 else abstract,
                })

            return {"success": True, "source": "Semantic Scholar", "query": query, "count": len(papers), "papers": papers}
        except Exception as e:
            return {"error": True, "message": str(e)}

    def search_openalex(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search OpenAlex (250M+ works, CC0 license)."""
        try:
            url = "https://api.openalex.org/works"
            params = {"search": query, "per_page": limit, "sort": "publication_date:desc"}
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            papers = []
            for w in data.get("results", []):
                papers.append({
                    "title": w.get("display_name"),
                    "year": w.get("publication_year"),
                    "citations": w.get("cited_by_count"),
                    "doi": w.get("doi"),
                    "type": w.get("type"),
                    "open_access": w.get("open_access", {}).get("is_oa"),
                })

            return {"success": True, "source": "OpenAlex", "query": query, "count": len(papers), "papers": papers}
        except Exception as e:
            return {"error": True, "message": str(e)}

    # ── 추가 도구 (v2.4) ──────────────────────────────────────

    def get_paper_detail(self, arxiv_id: str) -> Dict[str, Any]:
        """Get full detail for one arXiv paper by ID."""
        try:
            url = "http://export.arxiv.org/api/query"
            params = {"id_list": arxiv_id}
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()

            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            entry = root.find("atom:entry", ns)
            if entry is None:
                return {"error": True, "message": f"Paper {arxiv_id} not found"}

            authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns) if a.find("atom:name", ns) is not None]
            categories = [c.get("term") for c in entry.findall("atom:category", ns)]
            summary = entry.find("atom:summary", ns)
            title = entry.find("atom:title", ns)
            published = entry.find("atom:published", ns)
            updated = entry.find("atom:updated", ns)
            pdf_link = None
            for link in entry.findall("atom:link", ns):
                if link.get("title") == "pdf":
                    pdf_link = link.get("href")

            return {
                "success": True, "arxiv_id": arxiv_id,
                "title": title.text.strip() if title is not None else "",
                "authors": authors,
                "abstract": summary.text.strip() if summary is not None else "",
                "categories": categories,
                "published": published.text if published is not None else "",
                "updated": updated.text if updated is not None else "",
                "pdf_url": pdf_link or f"https://arxiv.org/pdf/{arxiv_id}",
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_citations(self, arxiv_id: str = "", doi: str = "", title: str = "") -> Dict[str, Any]:
        """Get citation network from OpenAlex. Provide arxiv_id, doi, or title."""
        try:
            headers = {"User-Agent": f"NexusFinanceMCP/1.0 (mailto:{os.getenv('CONTACT_EMAIL', 'nexus-finance-mcp@users.noreply.github.com')})"}

            # Resolve work ID
            if arxiv_id:
                filter_str = f"ids.openalex:https://arxiv.org/abs/{arxiv_id}"
                search_url = f"https://api.openalex.org/works?filter={filter_str}"
                resp = requests.get(search_url, headers=headers, timeout=15)
                if resp.status_code != 200 or not resp.json().get("results"):
                    search_url = f"https://api.openalex.org/works?search={quote(arxiv_id)}&per_page=1"
                    resp = requests.get(search_url, headers=headers, timeout=15)
            elif doi:
                search_url = f"https://api.openalex.org/works/doi:{doi}"
                resp = requests.get(search_url, headers=headers, timeout=15)
                if resp.ok:
                    work = resp.json()
                    work_id = work.get("id", "").split("/")[-1]
                    return self._build_citation_result(work, work_id, headers)
                return {"error": True, "message": f"DOI {doi} not found"}
            else:
                search_url = f"https://api.openalex.org/works?search={quote(title)}&per_page=1"
                resp = requests.get(search_url, headers=headers, timeout=15)

            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [data] if "id" in data else [])
            if not results:
                return {"error": True, "message": "Paper not found in OpenAlex"}

            work = results[0]
            work_id = work.get("id", "").split("/")[-1]
            return self._build_citation_result(work, work_id, headers)
        except Exception as e:
            return {"error": True, "message": str(e)}

    def _build_citation_result(self, work: dict, work_id: str, headers: dict) -> Dict[str, Any]:
        """Build citation result from an OpenAlex work."""
        # Cited-by (top 10)
        cited_by = []
        try:
            cb_url = f"https://api.openalex.org/works?filter=cites:{work_id}&sort=cited_by_count:desc&per_page=10"
            cb_resp = requests.get(cb_url, headers=headers, timeout=15)
            if cb_resp.ok:
                for w in cb_resp.json().get("results", []):
                    cited_by.append({"title": w.get("display_name"), "year": w.get("publication_year"), "citations": w.get("cited_by_count")})
        except Exception:
            pass

        # Referenced works (top 10)
        refs = []
        ref_ids = work.get("referenced_works", [])[:10]
        for ref_id in ref_ids:
            try:
                r = requests.get(ref_id, headers=headers, timeout=10)
                if r.ok:
                    rw = r.json()
                    refs.append({"title": rw.get("display_name"), "year": rw.get("publication_year"), "citations": rw.get("cited_by_count")})
            except Exception:
                continue

        return {
            "success": True,
            "title": work.get("display_name"),
            "cited_by_count": work.get("cited_by_count", 0),
            "top_cited_by": cited_by,
            "top_references": refs,
        }

    def get_author_info(self, author_name: str) -> Dict[str, Any]:
        """Get author profile from OpenAlex."""
        try:
            headers = {"User-Agent": f"NexusFinanceMCP/1.0 (mailto:{os.getenv('CONTACT_EMAIL', 'nexus-finance-mcp@users.noreply.github.com')})"}
            url = f"https://api.openalex.org/authors?search={quote(author_name)}&per_page=1"
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if not results:
                return {"error": True, "message": f"Author '{author_name}' not found"}

            a = results[0]
            institution = a.get("last_known_institutions", [{}])
            inst_name = institution[0].get("display_name") if institution else None

            # Recent works (top 5)
            author_id = a.get("id", "").split("/")[-1]
            recent = []
            try:
                w_url = f"https://api.openalex.org/works?filter=author.id:{author_id}&sort=publication_date:desc&per_page=5"
                w_resp = requests.get(w_url, headers=headers, timeout=15)
                if w_resp.ok:
                    for w in w_resp.json().get("results", []):
                        recent.append({"title": w.get("display_name"), "year": w.get("publication_year"), "citations": w.get("cited_by_count")})
            except Exception:
                pass

            return {
                "success": True,
                "display_name": a.get("display_name"),
                "institution": inst_name,
                "h_index": a.get("summary_stats", {}).get("h_index"),
                "cited_by_count": a.get("cited_by_count"),
                "works_count": a.get("works_count"),
                "recent_papers": recent,
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def search_concepts(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search academic concepts/topics from OpenAlex."""
        try:
            headers = {"User-Agent": f"NexusFinanceMCP/1.0 (mailto:{os.getenv('CONTACT_EMAIL', 'nexus-finance-mcp@users.noreply.github.com')})"}
            url = f"https://api.openalex.org/concepts?search={quote(query)}&per_page={limit}"
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            results = resp.json().get("results", [])

            concepts = []
            for c in results:
                concepts.append({
                    "name": c.get("display_name"),
                    "level": c.get("level"),
                    "works_count": c.get("works_count"),
                    "cited_by_count": c.get("cited_by_count"),
                    "description": c.get("description"),
                })

            return {"success": True, "query": query, "count": len(concepts), "concepts": concepts}
        except Exception as e:
            return {"error": True, "message": str(e)}
