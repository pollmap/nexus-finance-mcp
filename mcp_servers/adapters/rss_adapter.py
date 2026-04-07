"""Financial News RSS Adapter — Bloomberg, WSJ, CNBC, FT, Reuters, MarketWatch, Seeking Alpha."""
import logging
import sys
from pathlib import Path
import feedparser
import requests
from utils.http_client import get_session
from typing import Any, Dict, List, Optional
from datetime import datetime

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)
_session = get_session("rss_adapter")

# Major financial news RSS feeds (all free, no auth)
RSS_FEEDS = {
    "bloomberg": "https://feeds.bloomberg.com/markets/news.rss",
    "wsj_markets": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "cnbc_top": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "cnbc_world": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362",
    "reuters_business": "https://news.google.com/rss/search?q=reuters+finance&hl=en-US&gl=US&ceid=US:en",
    "ft_markets": "https://www.ft.com/markets?format=rss",
    "marketwatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
    "seekingalpha": "https://seekingalpha.com/market_currents.xml",
    "investing_com": "https://www.investing.com/rss/news.rss",
    "yahoo_finance": "https://finance.yahoo.com/news/rssindex",
    # Crypto
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph": "https://cointelegraph.com/rss",
    # Asia
    "nikkei_asia": "https://asia.nikkei.com/rss/feed/nar",
    "scmp_business": "https://www.scmp.com/rss/91/feed",
}

CRYPTO_FEEDS = ["coindesk", "cointelegraph"]

REQUEST_TIMEOUT = 15
USER_AGENT = "NexusFinance-RSS/1.0"


class RSSAdapter:
    """Fetches and parses financial news from major RSS feeds."""

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})

    def _parse_date(self, entry: Any) -> Optional[str]:
        """Extract and normalize published date from a feed entry."""
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if published:
            try:
                return datetime(*published[:6]).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
        # Fallback to raw string
        return entry.get("published") or entry.get("updated") or None

    def _parse_entry(self, entry: Any, feed_name: str) -> Dict[str, Any]:
        """Parse a single feed entry into a normalized dict."""
        summary = entry.get("summary") or entry.get("description") or ""
        # Strip HTML tags simply
        import re
        summary = re.sub(r"<[^>]+>", "", summary).strip()

        return {
            "title": entry.get("title", "").strip(),
            "link": entry.get("link", ""),
            "published": self._parse_date(entry),
            "summary": summary[:200],
            "source": feed_name,
        }

    def _fetch_raw(self, url: str) -> Optional[feedparser.FeedParserDict]:
        """Fetch and parse a single RSS URL with timeout."""
        try:
            resp = self._session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return feedparser.parse(resp.content)
        except requests.RequestException as e:
            logger.warning("RSS fetch failed for %s: %s", url, e)
            return None
        except Exception as e:
            logger.warning("RSS parse failed for %s: %s", url, e)
            return None

    def fetch_feed(self, feed_name: str, limit: int = 15) -> Dict[str, Any]:
        """Fetch a single RSS feed by name.

        Args:
            feed_name: Key from RSS_FEEDS dict.
            limit: Max entries to return.

        Returns:
            {"success": True, "source": "RSS", "feed": feed_name, "count": N, "data": [...]}
        """
        feed_name = feed_name.lower().strip()
        if feed_name not in RSS_FEEDS:
            return error_response(
                f"Unknown feed '{feed_name}'. Use list_feeds() to see available feeds."
            )

        url = RSS_FEEDS[feed_name]
        parsed = self._fetch_raw(url)
        if parsed is None or not parsed.get("entries"):
            return error_response(
                f"Failed to fetch or empty feed: {feed_name}",
                code="API_UNAVAILABLE",
            )

        entries = [self._parse_entry(e, feed_name) for e in parsed.entries[:limit]]
        return success_response(entries, source="RSS", feed=feed_name)

    def fetch_all_feeds(self, limit_per_feed: int = 5) -> Dict[str, Any]:
        """Fetch all feeds, combine, sort by date descending.

        Args:
            limit_per_feed: Max entries per individual feed.

        Returns:
            Combined entries sorted by published date.
        """
        all_entries: List[Dict] = []
        errors: List[str] = []

        for name, url in RSS_FEEDS.items():
            parsed = self._fetch_raw(url)
            if parsed is None or not parsed.get("entries"):
                errors.append(name)
                continue
            for e in parsed.entries[:limit_per_feed]:
                all_entries.append(self._parse_entry(e, name))

        # Sort by date descending (entries without date go to end)
        all_entries.sort(
            key=lambda x: x.get("published") or "0000-00-00",
            reverse=True,
        )

        result = success_response(all_entries, source="RSS", feed="all")
        if errors:
            result["failed_feeds"] = errors
        return result

    def search_feeds(self, query: str, limit: int = 15) -> Dict[str, Any]:
        """Search across all feeds for entries matching query in title or summary.

        Args:
            query: Search term (case-insensitive).
            limit: Max results to return.

        Returns:
            Filtered and sorted entries matching the query.
        """
        if not query or not query.strip():
            return error_response("Query cannot be empty.")

        query_lower = query.lower().strip()
        matched: List[Dict] = []

        for name, url in RSS_FEEDS.items():
            parsed = self._fetch_raw(url)
            if parsed is None or not parsed.get("entries"):
                continue
            for e in parsed.entries:
                entry = self._parse_entry(e, name)
                if (query_lower in entry["title"].lower()
                        or query_lower in entry["summary"].lower()):
                    matched.append(entry)

        matched.sort(
            key=lambda x: x.get("published") or "0000-00-00",
            reverse=True,
        )
        matched = matched[:limit]

        return success_response(matched, source="RSS", query=query)

    def list_feeds(self) -> Dict[str, Any]:
        """Return available feed names and URLs."""
        feeds = [{"name": name, "url": url} for name, url in RSS_FEEDS.items()]
        return success_response(feeds, source="RSS")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    adapter = RSSAdapter()
    result = adapter.list_feeds()
    print(f"Available feeds: {result['count']}")
    for f in result["data"]:
        print(f"  {f['name']}: {f['url']}")
