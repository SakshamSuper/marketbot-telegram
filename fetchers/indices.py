"""
fetchers/indices.py
────────────────────
Fetches Indian and US market indices with full data validation.
Uses direct Yahoo chart API first, with yfinance as secondary fallback.
"""

import logging
import yfinance as yf
import config
from fetchers.yahoo_direct import fetch_chart_data

logger = logging.getLogger(__name__)

# Price sanity bounds — reject obviously wrong data
_BOUNDS = {
    "^NSEI":     (10_000,  80_000),
    "^BSESN":    (30_000, 260_000),
    "^INDIAVIX": (5,       100),
    "ES=F":      (2_000,   10_000),
    "YM=F":      (15_000,  60_000),
    "NQ=F":      (5_000,   45_000),
}


def _validate(ticker: str, price: float) -> bool:
    """Return True if price is within expected realistic bounds."""
    if price is None or price != price:
        return False
    bounds = _BOUNDS.get(ticker)
    if bounds:
        lo, hi = bounds
        if not (lo <= price <= hi):
            logger.warning("Price %s=%.2f out of bounds [%s, %s]", ticker, price, lo, hi)
            return False
    return price > 0


def _fetch_one(ticker: str, label: str) -> dict | None:
    try:
        price = None
        prev = None

        # ── Primary Attempt: Direct Yahoo API
        chart = fetch_chart_data(ticker)
        if chart:
            price = chart["price"]
            prev = chart["prev_close"]

        # ── Secondary Attempt: yfinance
        if price is None or not _validate(ticker, price):
            t = yf.Ticker(ticker)
            try:
                hist = t.history(period="5d", interval="1d", actions=False)
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
            except Exception:
                pass

        if price is None or not _validate(ticker, price):
            logger.warning("Fetch failed for %s (%s)", label, ticker)
            return None

        prev = prev or price
        change = price - prev
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
    return {label: _fetch_one(ticker, label) for label, ticker in config.INDICES.items()}
