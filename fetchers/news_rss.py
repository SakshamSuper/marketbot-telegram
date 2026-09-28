"""
fetchers/news_rss.py
─────────────────────
Fetches news headlines from 6 Indian and global RSS feeds.
Validates entries — rejects empty titles and duplicates.
"""

import logging
import feedparser
import config

logger = logging.getLogger(__name__)

# RSS feeds — all free, no key required
RSS_FEEDS = {
    "ET Markets":   "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "Moneycontrol": "https://www.moneycontrol.com/rss/latestnews.xml",
    "Mint":         "https://www.livemint.com/rss/markets.xml",
    "TOI Business": "https://timesofindia.indiatimes.com/rssfeeds/1898055.cms",
    "Bloomberg":    "https://feeds.bloomberg.com/markets/news.rss",
    "Reuters":      "https://feeds.reuters.com/reuters/businessNews",
}

_TIMEOUT = 8  # seconds per feed


def _fetch_feed(source: str, url: str, max_items: int) -> list[dict]:
    """Fetch and parse a single RSS feed. Returns cleaned article list."""
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "MarketBot/1.0"})

        if feed.bozo and not feed.entries:
            logger.warning("RSS parse error for %s: %s", source, feed.bozo_exception)
            return []

        articles = []
        seen_titles: set[str] = set()

        for entry in feed.entries[:max_items * 2]:  # fetch extra to account for dedup
            title = (entry.get("title") or "").strip()
            if not title or len(title) < 10:
                continue
            # Deduplicate within same source
            key = title.lower()[:60]
            if key in seen_titles:
                continue
            seen_titles.add(key)

            articles.append({
                "source": source,
                "title":  title,
                "link":   entry.get("link", ""),
            })
            if len(articles) >= max_items:
                break

        logger.debug("RSS %s → %d articles", source, len(articles))
        return articles

    except Exception as exc:
        logger.error("RSS fetch failed for %s: %s", source, exc)
        return []


def fetch_all(max_per_source: int | None = None) -> list[dict]:
    """
    Fetch from all RSS sources.
    Returns deduped list of articles sorted: Indian sources first.
    """
    limit = max_per_source or config.NEWS_MAX_PER_SOURCE
    all_articles: list[dict] = []
    global_seen: set[str] = set()

    for source, url in RSS_FEEDS.items():
        feed_articles = _fetch_feed(source, url, limit)
        for art in feed_articles:
            key = art["title"].lower()[:60]
            if key not in global_seen:
                global_seen.add(key)
                all_articles.append(art)

    logger.info("Total news articles fetched: %d", len(all_articles))
    return all_articles


def fetch_headlines_only(max_total: int = 15) -> list[str]:
    """Convenience: returns just title strings for AI summarisation."""
    articles = fetch_all()
    return [a["title"] for a in articles[:max_total]]
