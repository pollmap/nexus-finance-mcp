"""
News MCP Server — Naver News + DataLab trends.

Tools (4):
- news_search: 네이버 뉴스 검색
- news_trend: 네이버 검색 트렌드
- news_market_sentiment: 종목/키워드 뉴스 감성 요약
- news_keyword_volume: 키워드 검색량 비교
"""
import logging
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP
from mcp_servers.adapters.naver_adapter import NaverAdapter

logger = logging.getLogger(__name__)


class NewsServer:
    def __init__(self):
        self._naver = NaverAdapter()
        self.mcp = FastMCP("news")
        self._register_tools()
        logger.info("News MCP Server initialized")

    def _register_tools(self):

        @self.mcp.tool()
        def news_search(query: str, count: int = 10, sort: str = "date") -> dict:
            """
            네이버 뉴스 검색. 한국 금융/경제 뉴스에 최적화.

            Args:
                query: 검색어 (예: 삼성전자, 비트코인, 기준금리)
                count: 결과 수 (최대 100)
                sort: date(최신순) 또는 sim(정확도순)
            """
            return self._naver.search_news(query, display=count, sort=sort)

        @self.mcp.tool()
        def news_trend(keywords: str, days: int = 30) -> dict:
            """
            네이버 검색 트렌드 (DataLab). 키워드별 검색량 추이 비교.

            Args:
                keywords: 쉼표로 구분된 키워드 (예: "비트코인,이더리움,리플")
                days: 기간 (일 수, 기본 30)
            """
            kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
            if not kw_list:
                return {"error": True, "message": "키워드를 입력하세요"}
            return self._naver.search_trend(kw_list, days=days)

        @self.mcp.tool()
        def news_market_sentiment(keyword: str) -> dict:
            """
            키워드 관련 최신 뉴스 제목에서 감성 요약.

            Args:
                keyword: 종목명 또는 키워드 (예: SK하이닉스)

            Returns:
                최신 뉴스 10개 제목 + 긍정/부정/중립 단순 분류
            """
            result = self._naver.search_news(keyword, display=10, sort="date")
            if result.get("error"):
                return result

            positive_words = ["상승", "호재", "성장", "최고", "돌파", "기대", "흑자", "증가"]
            negative_words = ["하락", "악재", "위기", "최저", "폭락", "우려", "적자", "감소"]

            pos, neg, neutral = 0, 0, 0
            for article in result.get("articles", []):
                title = article.get("title", "")
                if any(w in title for w in positive_words):
                    pos += 1
                elif any(w in title for w in negative_words):
                    neg += 1
                else:
                    neutral += 1

            total = pos + neg + neutral
            return {
                "success": True,
                "keyword": keyword,
                "total_articles": total,
                "positive": pos,
                "negative": neg,
                "neutral": neutral,
                "sentiment_ratio": round(pos / total, 2) if total > 0 else 0,
                "note": "단순 키워드 기반 감성 분류 (NLP 아님). 참고용.",
            }

        @self.mcp.tool()
        def news_keyword_volume(keywords: str, days: int = 7) -> dict:
            """
            키워드 검색량 비교 (최근 N일).

            Args:
                keywords: 쉼표 구분 (최대 5개)
                days: 기간 (기본 7일)
            """
            kw_list = [k.strip() for k in keywords.split(",") if k.strip()][:5]
            if not kw_list:
                return {"error": True, "message": "키워드를 입력하세요"}
            return self._naver.search_trend(kw_list, days=days)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = NewsServer()
    server.mcp.run(transport="stdio")
