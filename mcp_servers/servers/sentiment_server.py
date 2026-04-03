"""Sentiment & Attention MCP Server — Trends, Wiki, VADER, Fear&Greed (5 tools)."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from fastmcp import FastMCP
from mcp_servers.adapters.sentiment_adapter import SentimentAdapter
logger = logging.getLogger(__name__)

class SentimentServer:
    def __init__(self):
        self._a = SentimentAdapter()
        self.mcp = FastMCP("sentiment")
        self._register()
        logger.info("Sentiment MCP Server initialized")
    def _register(self):
        @self.mcp.tool()
        def sentiment_google_trends(keywords: list, timeframe: str = "today 3-m", geo: str = "") -> dict:
            """Google Trends 검색 관심도. keywords: 최대 5개, timeframe: 'today 3-m', 'today 12-m' 등."""
            return self._a.get_google_trends(keywords, timeframe, geo)
        @self.mcp.tool()
        def sentiment_wiki_pageviews(articles: list, days: int = 90) -> dict:
            """Wikipedia 문서 페이지뷰 (일별). articles: 문서 제목 리스트."""
            return self._a.get_wiki_pageviews(articles, days)
        @self.mcp.tool()
        def sentiment_news_score(headlines: list) -> dict:
            """VADER 감성분석: 뉴스 헤드라인 긍정/부정/중립 점수. headlines: 문자열 리스트."""
            return self._a.get_news_sentiment(headlines)
        @self.mcp.tool()
        def sentiment_fear_greed_multi() -> dict:
            """Crypto Fear & Greed Index (30일) + 해석. 극단적 공포=매수 신호, 극단적 탐욕=매도 신호."""
            return self._a.get_fear_greed_multi()
        @self.mcp.tool()
        def sentiment_keyword_correlation(keyword: str, stock_symbol: str, days: int = 180) -> dict:
            """키워드 검색량 vs 주가 상관분석용 데이터. stocks_history와 함께 사용."""
            return self._a.get_keyword_correlation(keyword, stock_symbol, days)
