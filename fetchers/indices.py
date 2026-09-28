"""
fetchers/indices.py
────────────────────
Fetches Indian and US market indices with full data validation.
Uses history() as primary method (more reliable for Indian indices),
with fast_info as a fast-path attempt first.
"""

import logging
import yfinance as yf
import config

logger = logging.getLogger(__name__)

# Price sanity bounds — reject obviously wrong data
_BOUNDS = {
    "^NSEI":     (10_000,  80_000),
    "^BSESN":    (30_000, 260_000),
    "^INDIAVIX": (5,       100),
    "ES=F":      (2_000,   10_000),
    "YM=F":      (15_000,  60_000),
    "NQ=F":      (5_000,   30_000),
}


def _validate(ticker: str, price: float) -> bool:
    """Return True if price is within expected realistic bounds."""
    if price is None or price != price:  # NaN check
        return False
    bounds = _BOUNDS.get(ticker)
    if bounds:
        lo, hi = bounds
        if not (lo <= price <= hi):
            logger.warning("Price %s=%.2f out of bounds [%s, %s]", ticker, price, lo, hi)
            return False
    return price > 0


def _fetch_one(ticker: str, label: str) -> dict | None:
    """
    Fetch a single index.
    Strategy: fast_info → history(1mo) → history(3mo) → None
    Tries multiple periods because Yahoo Finance sometimes returns empty
    for Indian indices on weekends or after market close.
    """
    try:
        t = yf.Ticker(ticker)
        price = None
        prev  = None

        # ── Attempt 1: fast_info
        try:
            info  = t.fast_info
            price = getattr(info, "last_price", None)
            prev  = getattr(info, "previous_close", None)
            if price is not None and (price != price or price <= 0):
                price = None
        except Exception as e:
            logger.debug("fast_info failed for %s: %s", ticker, e)
            price = None

        # ── Attempt 2: history() with escalating periods
        if price is None or not _validate(ticker, price):
            for period in ("5d", "1mo", "3mo"):
                try:
                    hist = t.history(period=period, interval="1d", actions=False)
                    if not hist.empty:
                        price = float(hist["Close"].iloc[-1])
                        prev  = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
                        logger.debug("Got %s price via history(period=%s): %.2f", label, period, price)
                        break
                except Exception as he:
                    logger.debug("history(period=%s) failed for %s: %s", period, ticker, he)

        if price is None or not _validate(ticker, price):
            logger.warning("All fetch attempts failed for %s (%s)", label, ticker)
            return None

        prev  = prev or price
        change     = price - prev
        change_pct = (change / prev * 100) if prev else 0.0

        return {
            "ticker":     ticker,
            "label":      label,
            "price":      round(price, 2),
            "prev_close": round(prev, 2),
            "change":     round(change, 2),
            "change_pct": round(change_pct, 2),
            "arrow":      "▲" if change >= 0 else "▼",
        }
    except Exception as exc:
        logger.error("Failed to fetch %s (%s): %s", label, ticker, exc)
        return None


def fetch_all() -> dict[str, dict | None]:
    """Fetch all configured indices. Returns dict keyed by friendly label."""
    results: dict[str, dict | None] = {}
    for label, ticker in config.INDICES.items():
        results[label] = _fetch_one(ticker, label)
    return results
