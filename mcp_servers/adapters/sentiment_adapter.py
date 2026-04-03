"""Sentiment & Attention Adapter — Google Trends, Wikipedia, VADER, Fear&Greed."""
import logging
import requests
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SentimentAdapter:
    """Sentiment and public attention data — free APIs + optional libraries."""

    def __init__(self):
        self._wiki_base = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
        self._fng_url = "https://api.alternative.me/fng/"
        self._user_agent = "NexusFinanceMCP/3.0 (contact@luxon.ai)"

    def get_google_trends(
        self, keywords: List[str], timeframe: str = "today 3-m", geo: str = ""
    ) -> Dict[str, Any]:
        """Google Trends interest over time via pytrends."""
        try:
            from pytrends.request import TrendReq
        except ImportError:
            return {
                "error": True,
                "message": "pytrends not installed. Run: pip install pytrends",
            }

        try:
            keywords = keywords[:5]  # max 5 keywords
            pytrends = TrendReq(hl="en-US", tz=360)
            pytrends.build_payload(keywords, cat=0, timeframe=timeframe, geo=geo)
            df = pytrends.interest_over_time()

            if df is None or df.empty:
                return {
                    "success": True,
                    "source": "Google Trends",
                    "keywords": keywords,
                    "count": 0,
                    "data": [],
                    "message": "No data returned for these keywords/timeframe",
                }

            records = []
            for idx, row in df.iterrows():
                entry = {"date": str(idx.date())}
                for kw in keywords:
                    if kw in df.columns:
                        entry[kw] = int(row[kw])
                records.append(entry)

            return {
                "success": True,
                "source": "Google Trends",
                "keywords": keywords,
                "timeframe": timeframe,
                "geo": geo if geo else "worldwide",
                "count": len(records),
                "data": records,
            }
        except Exception as e:
            return {"error": True, "message": f"Google Trends error: {str(e)}"}

    def get_wiki_pageviews(
        self, articles: List[str], days: int = 90
    ) -> Dict[str, Any]:
        """Wikipedia article pageviews — daily views per article."""
        try:
            end_dt = datetime.now() - timedelta(days=1)
            start_dt = end_dt - timedelta(days=days)
            start_str = start_dt.strftime("%Y%m%d")
            end_str = end_dt.strftime("%Y%m%d")

            results = []
            for article in articles[:10]:  # max 10 articles
                # Replace spaces with underscores for Wikipedia API
                article_clean = article.replace(" ", "_")
                url = (
                    f"{self._wiki_base}/en.wikipedia/all-access/all-agents"
                    f"/{article_clean}/daily/{start_str}/{end_str}"
                )
                headers = {"User-Agent": self._user_agent}
                resp = requests.get(url, headers=headers, timeout=15)

                if resp.status_code != 200:
                    results.append({
                        "article": article,
                        "error": f"HTTP {resp.status_code}",
                        "daily_views": [],
                    })
                    continue

                data = resp.json()
                items = data.get("items", [])
                daily_views = []
                total_views = 0
                for item in items:
                    views = item.get("views", 0)
                    total_views += views
                    ts = item.get("timestamp", "")
                    # timestamp format: 2024010100
                    date_str = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}" if len(ts) >= 8 else ts
                    daily_views.append({"date": date_str, "views": views})

                avg_views = round(total_views / len(daily_views)) if daily_views else 0
                results.append({
                    "article": article,
                    "total_views": total_views,
                    "avg_daily_views": avg_views,
                    "days": len(daily_views),
                    "daily_views": daily_views,
                })

            return {
                "success": True,
                "source": "Wikipedia/Pageviews",
                "period_days": days,
                "count": len(results),
                "data": results,
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_news_sentiment(self, headlines: List[str]) -> Dict[str, Any]:
        """VADER sentiment analysis on headline strings."""
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        except ImportError:
            return {
                "error": True,
                "message": "vaderSentiment not installed. Run: pip install vaderSentiment",
            }

        try:
            analyzer = SentimentIntensityAnalyzer()
            results = []
            compound_sum = 0.0

            for headline in headlines[:50]:  # max 50 headlines
                scores = analyzer.polarity_scores(headline)
                results.append({
                    "headline": headline,
                    "compound": round(scores["compound"], 4),
                    "positive": round(scores["pos"], 4),
                    "negative": round(scores["neg"], 4),
                    "neutral": round(scores["neu"], 4),
                })
                compound_sum += scores["compound"]

            avg_compound = round(compound_sum / len(results), 4) if results else 0.0
            overall = "positive" if avg_compound > 0.05 else "negative" if avg_compound < -0.05 else "neutral"

            return {
                "success": True,
                "source": "VADER Sentiment",
                "count": len(results),
                "overall": {
                    "avg_compound": avg_compound,
                    "sentiment": overall,
                },
                "data": results,
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_fear_greed_multi(self) -> Dict[str, Any]:
        """Crypto Fear & Greed Index — last 30 days with interpretation."""
        try:
            resp = requests.get(self._fng_url, params={"limit": 30}, timeout=15)
            if resp.status_code != 200:
                return {"error": True, "message": f"Fear&Greed API returned {resp.status_code}"}

            data = resp.json().get("data", [])
            records = []
            for item in data:
                value = int(item.get("value", 0))
                classification = item.get("value_classification", "")
                timestamp = item.get("timestamp", "")
                # Convert unix timestamp
                try:
                    date_str = datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d")
                except (ValueError, OSError):
                    date_str = timestamp

                records.append({
                    "date": date_str,
                    "value": value,
                    "classification": classification,
                })

            # Interpretation
            latest = records[0] if records else {}
            latest_val = latest.get("value", 50)
            interpretation = {
                "current_value": latest_val,
                "current_class": latest.get("classification", "N/A"),
                "signal": "Extreme greed often precedes corrections; extreme fear may signal buying opportunities.",
            }
            if latest_val <= 25:
                interpretation["signal"] = "Extreme Fear — historically a contrarian buy signal."
            elif latest_val <= 40:
                interpretation["signal"] = "Fear — market sentiment is cautious."
            elif latest_val <= 60:
                interpretation["signal"] = "Neutral — no strong directional sentiment."
            elif latest_val <= 75:
                interpretation["signal"] = "Greed — market is optimistic, exercise caution."
            else:
                interpretation["signal"] = "Extreme Greed — historically a contrarian sell signal."

            return {
                "success": True,
                "source": "Alternative.me/Crypto Fear & Greed",
                "count": len(records),
                "interpretation": interpretation,
                "data": records,
            }
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_keyword_correlation(
        self, keyword: str, stock_symbol: str, days: int = 180
    ) -> Dict[str, Any]:
        """Google Trends data for a keyword — correlate with stock data separately."""
        try:
            from pytrends.request import TrendReq
        except ImportError:
            return {
                "error": True,
                "message": "pytrends not installed. Run: pip install pytrends",
            }

        try:
            # Determine timeframe from days
            if days <= 7:
                timeframe = "now 7-d"
            elif days <= 30:
                timeframe = "today 1-m"
            elif days <= 90:
                timeframe = "today 3-m"
            elif days <= 365:
                timeframe = "today 12-m"
            else:
                timeframe = "today 5-y"

            pytrends = TrendReq(hl="en-US", tz=360)
            pytrends.build_payload([keyword], cat=0, timeframe=timeframe)
            df = pytrends.interest_over_time()

            if df is None or df.empty:
                return {
                    "success": True,
                    "source": "Google Trends",
                    "keyword": keyword,
                    "stock_symbol": stock_symbol,
                    "count": 0,
                    "data": [],
                    "note": "No trend data returned.",
                }

            records = []
            for idx, row in df.iterrows():
                if keyword in df.columns:
                    records.append({
                        "date": str(idx.date()),
                        "search_interest": int(row[keyword]),
                    })

            return {
                "success": True,
                "source": "Google Trends",
                "keyword": keyword,
                "stock_symbol": stock_symbol,
                "timeframe": timeframe,
                "count": len(records),
                "data": records,
                "note": (
                    f"This returns Google Trends data for '{keyword}'. "
                    f"To correlate with {stock_symbol} stock price, use "
                    f"stocks_quote or stocks_history tools to get price data "
                    f"and compare the time series."
                ),
            }
        except Exception as e:
            return {"error": True, "message": f"Google Trends error: {str(e)}"}
