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
from mcp_servers.adapters.gdelt_academic_adapter import GDELTAdapter

logger = logging.getLogger(__name__)


class NewsServer:
    def __init__(self):
        self._naver = NaverAdapter()
        self._gdelt = None
        try:
            self._gdelt = GDELTAdapter()
        except Exception as e:
            logger.warning(f"GDELT adapter init failed: {e}")
        self.mcp = FastMCP("news")
        self._register_tools()
        logger.info("News MCP Server initialized")

    def _register_tools(self):

        @self.mcp.tool()
        def news_search(query: str, count: int = 10, sort: str = "date", language: str = "ko") -> dict:
            """
            뉴스 검색. 한국어=네이버, 영어=GDELT 자동 전환.

            Args:
                query: 검색어 (예: 삼성전자, VLGC freight rate)
                count: 결과 수 (최대 100)
                sort: date(최신순) 또는 sim(정확도순)
                language: ko(한국어, 네이버) 또는 en(영어, GDELT)
            """
            if language == "en" and self._gdelt:
                return self._gdelt.search_articles(query, max_records=count, sourcelang="english", timespan="30d")

            result = self._naver.search_news(query, display=count, sort=sort)

            # Auto-fallback: 네이버 결과 0건이고 GDELT 사용 가능하면 영문 검색
            if result.get("total", result.get("count", 0)) == 0 and self._gdelt:
                gdelt_result = self._gdelt.search_articles(query, max_records=count, sourcelang="english", timespan="30d")
                if gdelt_result.get("count", 0) > 0:
                    gdelt_result["fallback"] = "GDELT (네이버 결과 0건)"
                    return gdelt_result

            return result

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

            positive_words = [
                "상승", "호재", "성장", "최고", "돌파", "기대", "흑자", "증가",
                "급등", "반등", "회복", "호황", "강세", "수혜", "호실적", "사상최고",
                "매수", "순매수", "유입", "확대", "개선", "안정", "긍정", "낙관",
                "수출증가", "투자확대", "고용증가", "실적개선", "매출증가", "이익증가",
                "배당확대", "승인", "상장", "인수합병", "신고가", "목표가상향",
                "금리인하", "부양", "완화", "경기회복", "소비증가", "수주", "계약",
                "혁신", "신기술", "특허", "수상", "선정", "1위", "대박",
            ]
            negative_words = [
                "하락", "악재", "위기", "최저", "폭락", "우려", "적자", "감소",
                "급락", "폭등", "불안", "침체", "약세", "손실", "부진", "사상최저",
                "매도", "순매도", "유출", "축소", "악화", "불안정", "부정", "비관",
                "수출감소", "투자축소", "고용감소", "실적부진", "매출감소", "이익감소",
                "배당축소", "제재", "상장폐지", "파산", "신저가", "목표가하향",
                "금리인상", "긴축", "규제", "경기둔화", "소비위축", "해지", "취소",
                "리콜", "소송", "벌금", "퇴출", "디폴트", "부도", "구조조정",
            ]

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
