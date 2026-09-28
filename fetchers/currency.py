"""
fetchers/currency.py
─────────────────────
Fetches live currency exchange rates via direct Yahoo chart API with yfinance fallback.
"""

import logging
import yfinance as yf
import config
from fetchers.yahoo_direct import fetch_chart_data

logger = logging.getLogger(__name__)

_BOUNDS = {
    "USDINR=X": (60.0,  120.0),
    "EURINR=X": (65.0,  130.0),
    "GBPINR=X": (75.0,  155.0),
}


def _fetch_rate(pair_label: str, ticker: str) -> dict | None:
    try:
        rate = None
        prev = None

        chart = fetch_chart_data(ticker)
        if chart:
            rate = chart["price"]
            prev = chart["prev_close"]

        if rate is None or rate <= 0:
            t = yf.Ticker(ticker)
            try:
                hist = t.history(period="5d", interval="1d", actions=False)
                if not hist.empty:
                    rate = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else rate
            except Exception:
                pass

        lo, hi = _BOUNDS.get(ticker, (0, 1e9))
        if rate is None or not (lo <= rate <= hi):
            logger.warning("Rate %s=%.4f out of bounds [%.1f, %.1f]", ticker, rate or 0, lo, hi)
            return None

        prev = prev or rate
        change_pct = ((rate - prev) / prev * 100) if prev else 0.0

        return {
            "pair":       pair_label,
            "ticker":     ticker,
            "rate":       round(rate, 4),
            "change_pct": round(change_pct, 3),
            "arrow":      "▲" if change_pct >= 0 else "▼",
        }
    except Exception as exc:
        logger.error("fetch_rate(%s) failed: %s", pair_label, exc)
        return None


def fetch_all() -> dict[str, dict | None]:
    return {label: _fetch_rate(label, ticker) for label, ticker in config.CURRENCY_PAIRS.items()}


def get_usd_inr() -> float:
    data = _fetch_rate("USD/INR", "USDINR=X")
    return data["rate"] if data else 86.5
