"""
Naver Adapter — News search + DataLab search trends.

Requires: NAVER_CLIENT_ID + NAVER_CLIENT_SECRET
Free: 25,000 calls/day
"""
import logging
import os
import requests
from datetime import datetime, timedelta
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class NaverAdapter:
    """Naver Open API — news search + search trend data."""

    NEWS_URL = "https://openapi.naver.com/v1/search/news.json"
    TREND_URL = "https://openapi.naver.com/v1/datalab/search"

    def __init__(self):
        self._client_id = os.getenv("NAVER_CLIENT_ID", "")
        self._client_secret = os.getenv("NAVER_CLIENT_SECRET", "")
        if not self._client_id:
            logger.warning("NAVER_CLIENT_ID not set. Naver tools will return errors.")

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Naver-Client-Id": self._client_id,
            "X-Naver-Client-Secret": self._client_secret,
        }

    def search_news(self, query: str, display: int = 10, sort: str = "date") -> Dict[str, Any]:
        """
        Search Naver News.

        Args:
            query: Search keyword (Korean supported)
            display: Number of results (1-100)
            sort: 'date' (latest) or 'sim' (relevance)
        """
        if not self._client_id:
            return {"error": True, "message": "NAVER_CLIENT_ID not configured"}

        try:
            params = {"query": query, "display": min(display, 100), "sort": sort}
            resp = requests.get(self.NEWS_URL, headers=self._headers(), params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            articles = []
            for item in data.get("items", []):
                title = item.get("title", "").replace("<b>", "").replace("</b>", "")
                desc = item.get("description", "").replace("<b>", "").replace("</b>", "")
                articles.append({
                    "title": title,
                    "description": desc,
                    "link": item.get("originallink") or item.get("link"),
                    "pubDate": item.get("pubDate"),
                })

            return {
                "success": True,
                "query": query,
                "total": data.get("total", 0),
                "count": len(articles),
                "articles": articles,
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def search_trend(
        self, keywords: List[str], days: int = 30, time_unit: str = "date"
    ) -> Dict[str, Any]:
        """
        Get Naver search trend data.

        Args:
            keywords: List of keywords to compare (max 5)
            days: Period in days (default 30)
            time_unit: 'date' (daily), 'week', 'month'
        """
        if not self._client_id:
            return {"error": True, "message": "NAVER_CLIENT_ID not configured"}

        try:
            end = datetime.now()
            start = end - timedelta(days=days)

            body = {
                "startDate": start.strftime("%Y-%m-%d"),
                "endDate": end.strftime("%Y-%m-%d"),
                "timeUnit": time_unit,
                "keywordGroups": [
                    {"groupName": kw, "keywords": [kw]} for kw in keywords[:5]
                ],
            }

            resp = requests.post(
                self.TREND_URL, headers=self._headers(), json=body, timeout=10
            )
            resp.raise_for_status()
            data = resp.json()

            results = []
            for group in data.get("results", []):
                results.append({
                    "keyword": group.get("title"),
                    "data": [
                        {"period": d.get("period"), "ratio": d.get("ratio")}
                        for d in group.get("data", [])
                    ],
                })

            return {
                "success": True,
                "period": f"{start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}",
                "keywords": keywords,
                "results": results,
            }
        except Exception as e:
            return {"error": True, "message": str(e)}
