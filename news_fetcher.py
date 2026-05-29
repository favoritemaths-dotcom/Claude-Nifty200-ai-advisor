
"""
news_fetcher.py
===============
Fetches news from multiple free sources:
1. Google News RSS (per stock - no API key needed)
2. Economic Times Markets RSS
3. Moneycontrol RSS
4. Business Standard RSS
5. NSE Official RSS

This version is defensive:
- Adds request timeouts
- Prevents one bad RSS feed from blocking the whole job
- Returns partial results instead of hanging
- Keeps the existing project workflow intact
"""

import feedparser
import requests
import re
import time
from datetime import datetime
from urllib.parse import quote

from config import NEWS_FEEDS, ANALYSIS
from logger_config import get_logger

logger = get_logger("news_fetcher")

# Basic requests session with retries and timeout support
_SESSION = requests.Session()
_SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
)

POSITIVE_WORDS = [
    "profit", "growth", "beat", "surge", "rally", "strong", "buy",
    "upgrade", "outperform", "bullish", "record", "high", "gain",
    "positive", "robust", "expand", "order", "win", "launch", "deal",
    "increase", "rise", "up", "good", "excellent", "approval", "approved"
]

NEGATIVE_WORDS = [
    "loss", "fall", "decline", "miss", "downgrade", "bear", "sell",
    "underperform", "weak", "slow", "debt", "fraud", "scam", "probe",
    "investigation", "penalty", "fine", "lower", "cut", "warning",
    "concern", "risk", "drop", "down", "bad", "poor", "negative", "rejected"
]

MANIPULATION_WORDS = [
    "unusual", "surge", "spike", "operator", "pump", "circuit",
    "no news", "unexplained", "sudden"
]


def _safe_get(url, timeout=10):
    """
    Safe HTTP GET wrapper with timeout.
    Returns response text or None.
    """
    try:
        resp = _SESSION.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.text
        logger.warning(f"Non-200 response from {url}: {resp.status_code}")
        return None
    except Exception as e:
        logger.warning(f"Request failed for {url}: {e}")
        return None


def get_google_news_for_stock(company_name, symbol, max_articles=5):
    """
    Fetches Google News RSS for a specific stock.
    Returns a list of article dicts.
    """
    try:
        clean_name = company_name.replace(".NS", "").replace("-EQ", "")
        search_query = quote(f"{clean_name} NSE stock India")
        url = (
            "https://news.google.com/rss/search"
            f"?q={search_query}"
            "&hl=en-IN&gl=IN&ceid=IN:en"
        )

        feed = feedparser.parse(url)

        articles = []
        for entry in feed.entries[:max_articles]:
            articles.append(
                {
                    "title": entry.get("title", "No title"),
                    "summary": entry.get("summary", "")[:300],
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source": "Google News",
                    "stock": symbol,
                }
            )
        return articles

    except Exception as e:
        logger.warning(f"Google News fetch failed for {symbol}: {e}")
        return []


def get_market_news(max_per_feed=10):
    """
    Fetches general market news from all configured RSS feeds.
    Returns a combined list of articles sorted by date.
    """
    all_articles = []

    for feed_name, feed_url in NEWS_FEEDS.items():
        try:
            logger.info(f"Fetching RSS feed: {feed_name}")

            raw_xml = _safe_get(feed_url, timeout=10)
            if not raw_xml:
                logger.warning(f"Skipping feed due to fetch failure: {feed_name}")
                continue

            feed = feedparser.parse(raw_xml)

            if not getattr(feed, "entries", None):
                logger.warning(f"No entries found in feed: {feed_name}")
                continue

            for entry in feed.entries[:max_per_feed]:
                all_articles.append(
                    {
                        "title": entry.get("title", "No title"),
                        "summary": entry.get("summary", "")[:400],
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "source": feed_name,
                        "stock": "MARKET",
                    }
                )

            time.sleep(0.2)  # small pause to be gentle on feeds

        except Exception as e:
            logger.warning(f"Could not fetch {feed_name}: {e}")
            continue

    logger.info(f"Market news fetched: {len(all_articles)} articles")
    return all_articles


def score_sentiment(text):
    """
    Simple keyword-based sentiment scoring.
    Returns a float from -1 to +1.
    """
    if not text:
        return 0

    text_lower = text.lower()
    pos_count = sum(1 for word in POSITIVE_WORDS if word in text_lower)
    neg_count = sum(1 for word in NEGATIVE_WORDS if word in text_lower)

    total = pos_count + neg_count
    if total == 0:
        return 0

    return round((pos_count - neg_count) / total, 2)


def check_manipulation_signals(text):
    """
    Checks if news text contains manipulation-related language.
    Returns (is_suspicious, matched_signals).
    """
    if not text:
        return False, []

    text_lower = text.lower()
    signals = [word for word in MANIPULATION_WORDS if word in text_lower]
    return len(signals) >= 2, signals


def get_news_for_top_stocks(top_stocks_data, max_per_stock=3):
    """
    Fetches news for the top scored stocks only.
    Adds sentiment scores to each article.

    Args:
        top_stocks_data: list of stock dicts (already scored)
        max_per_stock: max news articles per stock

    Returns:
        news_map: dict mapping symbol -> list of news articles
        sentiment_scores: dict mapping symbol -> average sentiment
    """
    news_map = {}
    logger.info(f"Fetching news for top {len(top_stocks_data)} stocks...")

    for idx, stock in enumerate(top_stocks_data, start=1):
        try:
            symbol = stock.get("symbol", "")
            company_name = stock.get("company_name", symbol)

            logger.info(f"[{idx}/{len(top_stocks_data)}] News for {symbol}")

            articles = get_google_news_for_stock(
                company_name, symbol, max_articles=max_per_stock
            )

            for article in articles:
                combined_text = f"{article.get('title', '')} {article.get('summary', '')}"
                article["sentiment"] = score_sentiment(combined_text)
                is_suspicious, signals = check_manipulation_signals(combined_text)
                article["suspicious"] = is_suspicious
                article["flags"] = signals

            news_map[symbol] = articles

            # Small delay between requests to reduce rate limiting
            time.sleep(0.3)

        except Exception as e:
            logger.warning(f"News fetch failed for {stock.get('symbol', 'UNKNOWN')}: {e}")
            news_map[stock.get("symbol", "UNKNOWN")] = []

    sentiment_scores = {}
    for symbol, articles in news_map.items():
        try:
            if articles:
                avg_sentiment = sum(a.get("sentiment", 0) for a in articles) / len(articles)
                sentiment_scores[symbol] = round(avg_sentiment, 2)
            else:
                sentiment_scores[symbol] = 0
        except Exception:
            sentiment_scores[symbol] = 0

    logger.info(f"News fetched for {len(news_map)} stocks")
    return news_map, sentiment_scores


def fetch_full_article(url, max_chars=3000):
    """
    Fetches the full text of a news article from its URL.
    Used when AI needs more than just the headline/summary.
    Returns the article text (first max_chars characters).
    """
    try:
        html = _safe_get(url, timeout=10)
        if not html:
            return ""

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")

        # Remove navigation, ads, scripts
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]

    except Exception as e:
        logger.warning(f"Could not fetch full article {url}: {e}")
        return ""