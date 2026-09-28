"""
fetchers/currency.py
─────────────────────
Fetches live currency exchange rates via yfinance.
Uses history() fallback — more reliable than fast_info for FX pairs.
"""

import logging
import yfinance as yf
import config

logger = logging.getLogger(__name__)

_BOUNDS = {
    "USDINR=X": (60.0,  120.0),
    "EURINR=X": (65.0,  130.0),
    "GBPINR=X": (75.0,  155.0),
}


def _fetch_rate(pair_label: str, ticker: str) -> dict | None:
    try:
        t    = yf.Ticker(ticker)
        rate = None
        prev = None

        # Attempt 1: fast_info
        try:
            info = t.fast_info
            rate = getattr(info, "last_price", None)
            prev = getattr(info, "previous_close", None)
            if rate is not None and (rate != rate or rate <= 0):
                rate = None
        except Exception:
            rate = None

        # Attempt 2: history()
        if rate is None or rate <= 0:
            hist = t.history(period="5d", interval="1d")
            if hist.empty:
                logger.warning("history() empty for %s", pair_label)
                return None
            rate = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else rate

        # Bounds check
        lo, hi = _BOUNDS.get(ticker, (0, 1e9))
        if not (lo <= rate <= hi):
            logger.warning("Rate %s=%.4f out of bounds [%.1f, %.1f]", ticker, rate, lo, hi)
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
    """Convenience: return raw USD/INR rate for crypto INR conversion."""
    data = _fetch_rate("USD/INR", "USDINR=X")
    return data["rate"] if data else 84.0
