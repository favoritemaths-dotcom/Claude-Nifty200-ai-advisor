"""
news_fetcher.py
===============
Fetches news from multiple free sources:
1. Google News RSS (per stock - no API key needed)
2. Economic Times Markets RSS
3. Moneycontrol RSS
4. Business Standard RSS
5. NSE Official RSS

No API key required. Completely free and legal.
"""

import feedparser
import requests
import re
import time
from datetime import datetime, timezone
from config import NEWS_FEEDS, ANALYSIS
from urllib.parse import quote

# ============================================================
# 1. GOOGLE NEWS RSS PER STOCK
# ============================================================

def get_google_news_for_stock(company_name, symbol, max_articles=5):
    """
    Fetches Google News RSS for a specific stock.
    No API key needed - uses Google's public RSS feed.
    Example URL for Reliance:
    https://news.google.com/rss/search?q=Reliance+Industries+NSE+stock&hl=en-IN&gl=IN&ceid=IN:en
    """
    try:
        # Clean company name for search (remove .NS suffix)
        clean_name = company_name.replace(".NS", "").replace("-EQ", "")
        search_query = quote(f"{clean_name} NSE stock India")
        url = (
            f"https://news.google.com/rss/search"
            f"?q={search_query}"
            f"&hl=en-IN&gl=IN&ceid=IN:en"
        )
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries[:max_articles]:
            articles.append({
                "title"    : entry.get("title", "No title"),
                "summary"  : entry.get("summary", "")[:300],  # First 300 chars
                "link"     : entry.get("link", ""),
                "published": entry.get("published", ""),
                "source"   : "Google News",
                "stock"    : symbol,
            })
        return articles
    except Exception as e:
        return []

# ============================================================
# 2. GENERAL MARKET NEWS FROM RSS FEEDS
# ============================================================

def get_market_news(max_per_feed=10):
    """
    Fetches general market news from all configured RSS feeds.
    Returns a combined list of articles sorted by date.
    """
    all_articles = []
    for feed_name, feed_url in NEWS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:max_per_feed]:
                all_articles.append({
                    "title"    : entry.get("title", "No title"),
                    "summary"  : entry.get("summary", "")[:400],
                    "link"     : entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source"   : feed_name,
                    "stock"    : "MARKET",
                })
        except Exception as e:
            print(f"
⚠ Could not fetch {feed_name}: {e}")
    print(f"
✓ Market news: {len(all_articles)} articles from {len(NEWS_FEEDS)} sources")
    return all_articles

# ============================================================
# 3. SIMPLE SENTIMENT SCORER (No AI needed - keyword based)
# ============================================================

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

def score_sentiment(text):
    """
    Simple keyword-based sentiment scoring.
    Returns: score between -1 (very negative) and +1 (very positive)
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
    Returns True if suspicious signals found.
    """
    text_lower = text.lower()
    signals = [word for word in MANIPULATION_WORDS if word in text_lower]
    return len(signals) >= 2, signals

# ============================================================
# 4. FULL NEWS FETCH FOR TOP STOCKS
# ============================================================

def get_news_for_top_stocks(top_stocks_data, max_per_stock=3):
    """
    Fetches news for the top scored stocks only (not all 200 - too slow).
    Adds sentiment scores to each article.

    Args:
        top_stocks_data: list of stock dicts (already scored)
        max_per_stock: max news articles per stock

    Returns:
        dict mapping symbol -> list of news articles with sentiment
    """
    news_map = {}
    print(f"
✓ Fetching news for top {len(top_stocks_data)} stocks...")

    for stock in top_stocks_data:
        symbol       = stock.get("symbol", "")
        company_name = stock.get("company_name", symbol)

        articles = get_google_news_for_stock(
            company_name, symbol, max_articles=max_per_stock
        )

        # Add sentiment score to each article
        for article in articles:
            combined_text = f"{article['title']} {article['summary']}"
            article["sentiment"] = score_sentiment(combined_text)
            is_suspicious, signals = check_manipulation_signals(combined_text)
            article["suspicious"] = is_suspicious
            article["flags"]      = signals

        news_map[symbol] = articles

        # Small delay between requests
        time.sleep(0.5)

    # Calculate overall sentiment per stock
    sentiment_scores = {}
    for symbol, articles in news_map.items():
        if articles:
            avg_sentiment = sum(a["sentiment"] for a in articles) / len(articles)
            sentiment_scores[symbol] = round(avg_sentiment, 2)
        else:
            sentiment_scores[symbol] = 0

    print(f"
✓ News fetched for {len(news_map)} stocks")
    return news_map, sentiment_scores

# ============================================================
# 5. FETCH FULL ARTICLE TEXT (for important stories)
# ============================================================

def fetch_full_article(url, max_chars=3000):
    """
    Fetches the full text of a news article from its URL.
    Used when AI needs more than just the headline/summary.
    Works for most Indian financial news sites.
    Returns the article text (first max_chars characters).
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            # Simple text extraction (removes HTML tags)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "lxml")

            # Remove navigation, ads, scripts
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            text = soup.get_text(separator=" ", strip=True)

            # Clean up whitespace
            text = re.sub(r"s+", " ", text).strip()
            return text[:max_chars]
    except Exception as e:
        return ""
    return ""
