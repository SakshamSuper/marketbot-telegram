"""
fetchers/portfolio_news.py
───────────────────────────
Targeted news intelligence for stocks owned by the user.
Queries Google News RSS & financial feeds for exact company names in the portfolio.
Categorizes articles by ticker and filters out unrelated noise.
"""

import os
import json
import logging
import urllib.parse
import requests
import feedparser

logger = logging.getLogger(__name__)

HOLDINGS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "user_holdings.json")

# Core keywords to match company names to ticker symbols
STOCK_KEYWORD_MAP = {
    "VEDL": ["Vedanta", "Cairn", "Anil Agarwal"],
    "AXISBANK": ["Axis Bank"],
    "SBIN": ["State Bank of India", "SBI "],
    "BEL": ["Bharat Electronics", " BEL "],
    "BSE": ["BSE Ltd", "BSE Limited", "Bombay Stock Exchange"],
    "HDFCBANK": ["HDFC Bank"],
    "MAZDOCK": ["Mazagon Dock", "Mazagon"],
    "BHARTIARTL": ["Bharti Airtel", "Airtel"],
    "COALINDIA": ["Coal India"],
    "DRONEDESTN": ["Drone Destination"],
    "IRFC": ["Indian Railway Finance", "IRFC"],
    "SILVER": ["Silver price", "MCX Silver", "Silver ETF", "Silver tumbles", "Silver rally"],
    "GOLD": ["Gold price", "MCX Gold", "Gold ETF", "Gold rally"],
    "GTLINFRA": ["GTL Infra"],
    "YESBANK": ["Yes Bank"],
}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


def get_tracked_companies() -> list[str]:
    """Extract list of high-priority company names from user holdings."""
    if not os.path.exists(HOLDINGS_PATH):
        return ["Vedanta", "State Bank of India", "BSE Limited", "Axis Bank", "Bharat Electronics"]
    try:
        with open(HOLDINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        names = []
        for h in data.get("holdings", []):
            name = h.get("name", "").strip()
            # Clean broker suffixes
            clean = name.replace(" LIMITED", "").replace(" LTD", "").replace(" L", "")
            if clean and clean not in names:
                names.append(clean)
        return names
    except Exception as exc:
        logger.error("Failed to load holdings for news: %s", exc)
        return ["Vedanta", "State Bank of India", "BSE Limited", "Axis Bank"]


def fetch_portfolio_news(max_articles: int = 15) -> list[dict]:
    """
    Fetches latest live news matching owned stocks.
    Returns:
      [
        {
          "ticker": str,         # e.g. "VEDL"
          "company": str,        # e.g. "Vedanta"
          "title": str,
          "source": str,
          "link": str,
          "published": str,
        },
        ...
      ]
    """
    companies = [
        "Vedanta",
        "State Bank of India",
        "BSE Limited",
        "Bharat Electronics",
        "Mazagon Dock",
        "Axis Bank",
        "HDFC Bank",
        "Bharti Airtel",
        "Coal India",
        "Drone Destination",
        "IRFC",
    ]

    query = " OR ".join(f'"{c}"' for c in companies[:8])
    encoded_q = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-IN&gl=IN&ceid=IN:en"

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=8)
        if resp.status_code != 200:
            return []

        feed = feedparser.parse(resp.content)
        articles = []
        seen_titles = set()

        for entry in feed.entries:
            title = (entry.get("title") or "").strip()
            if not title or len(title) < 20:
                continue

            # Extract source from title e.g. "Title - Economic Times"
            source = "News"
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0].strip()
                source = parts[1].strip()

            key = title.lower()[:50]
            if key in seen_titles:
                continue
            seen_titles.add(key)

            # Match to specific ticker in user portfolio
            matched_ticker = "PORTFOLIO"
            matched_name = "Owned Stock"
            for ticker, keywords in STOCK_KEYWORD_MAP.items():
                if any(kw.lower() in title.lower() for kw in keywords):
                    matched_ticker = ticker
                    matched_name = keywords[0]
                    break

            articles.append({
                "ticker": matched_ticker,
                "company": matched_name,
                "title": title,
                "source": source,
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            })

            if len(articles) >= max_articles:
                break

        logger.info("Found %d targeted news stories for user portfolio", len(articles))
        return articles
    except Exception as exc:
        logger.error("fetch_portfolio_news failed: %s", exc)
        return []
