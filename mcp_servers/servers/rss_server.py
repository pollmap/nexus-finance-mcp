"""
Financial News RSS MCP Server — 4 tools.
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP
from mcp_servers.adapters.rss_adapter import RSSAdapter, CRYPTO_FEEDS

logger = logging.getLogger(__name__)


class RSSServer:
    def __init__(self):
        self._rss = RSSAdapter()
        self.mcp = FastMCP("rss-news")
        self._register_tools()
        logger.info("RSS News MCP Server initialized")

    def _register_tools(self):

        @self.mcp.tool()
        def rss_financial_news(feed: str = "all", limit: int = 15) -> dict:
            """금융 뉴스 RSS 피드 조회. feed='all'이면 전체, 아니면 특정 피드(bloomberg, wsj_markets, cnbc_top 등)."""
            if feed.lower().strip() == "all":
                return self._rss.fetch_all_feeds(limit_per_feed=max(1, limit // len(self._rss.list_feeds()["data"])))
            return self._rss.fetch_feed(feed, limit=limit)

        @self.mcp.tool()
        def rss_search_news(query: str, limit: int = 15) -> dict:
            """전체 금융 RSS 피드에서 키워드 검색 (제목+요약, 대소문자 무관)."""
            return self._rss.search_feeds(query, limit=limit)

        @self.mcp.tool()
        def rss_available_feeds() -> dict:
            """사용 가능한 RSS 피드 목록 반환 (Bloomberg, WSJ, CNBC, Reuters, FT 등 14개)."""
            return self._rss.list_feeds()

        @self.mcp.tool()
        def rss_crypto_news(limit: int = 10) -> dict:
            """암호화폐 뉴스 (CoinDesk + CoinTelegraph RSS)."""
            all_entries = []
            errors = []
            per_feed = max(1, limit // len(CRYPTO_FEEDS))

            for feed_name in CRYPTO_FEEDS:
                result = self._rss.fetch_feed(feed_name, limit=per_feed)
                if result.get("success"):
                    all_entries.extend(result.get("data", []))
                else:
                    errors.append(feed_name)

            all_entries.sort(
                key=lambda x: x.get("published") or "0000-00-00",
                reverse=True,
            )
            all_entries = all_entries[:limit]

            result = {
                "success": True,
                "source": "RSS",
                "feed": "crypto",
                "count": len(all_entries),
                "data": all_entries,
            }
            if errors:
                result["failed_feeds"] = errors
            return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    RSSServer().mcp.run(transport="stdio")
