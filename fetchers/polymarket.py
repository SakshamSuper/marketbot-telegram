"""
fetchers/polymarket.py
───────────────────────
Fetches top active prediction markets from Polymarket's public API.
No API key required.
"""

import logging
import requests
import config

logger = logging.getLogger(__name__)

_API_URL = "https://gamma-api.polymarket.com/markets"
_TIMEOUT = 10
_RETRY   = 2


def fetch_top_markets(n: int | None = None) -> list[dict]:
    """
    Fetch top N active Polymarket markets sorted by volume.
    Returns list of validated market dicts.
    """
    limit = n or config.POLYMARKET_TOP_N
    params = {
        "active":   "true",
        "closed":   "false",
        "order":    "volume",
        "ascending":"false",
        "limit":    limit * 3,  # fetch extra so we can filter properly
    }

    last_exc: Exception | None = None
    for attempt in range(1, _RETRY + 2):
        try:
            resp = requests.get(_API_URL, params=params, timeout=_TIMEOUT)
            resp.raise_for_status()
            raw = resp.json()
            break
        except Exception as exc:
            last_exc = exc
            logger.warning("Polymarket attempt %d failed: %s", attempt, exc)
            if attempt <= _RETRY:
                import time; time.sleep(3)
    else:
        logger.error("Polymarket all retries failed: %s", last_exc)
        return []

    markets = []
    for item in raw:
        question = (item.get("question") or item.get("title") or "").strip()
        if not question:
            continue

        # Extract YES probability
        outcomes = item.get("outcomes") or []
        yes_prob = None

        # Try outcomePrices list
        prices = item.get("outcomePrices") or []
        if prices:
            try:
                # First outcome is YES by convention
                yes_prob = round(float(prices[0]) * 100, 1)
            except (ValueError, IndexError):
                pass

        # Fallback: parse from outcomes list
        if yes_prob is None:
            for o in outcomes:
                if isinstance(o, dict) and o.get("name", "").upper() == "YES":
                    try:
                        yes_prob = round(float(o.get("price", 0)) * 100, 1)
                    except (ValueError, TypeError):
                        pass

        if yes_prob is None:
            continue

        # Validate probability range
        if not (0.0 <= yes_prob <= 100.0):
            logger.warning("Polymarket: implausible probability %.1f for %r", yes_prob, question[:40])
            continue

        markets.append({
            "question": question,
            "yes_pct":  yes_prob,
            "volume":   item.get("volume") or 0,
        })

        if len(markets) >= limit:
            break

    logger.info("Polymarket: fetched %d markets", len(markets))
    return markets
