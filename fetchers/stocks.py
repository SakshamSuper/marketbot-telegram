"""
fetchers/stocks.py
───────────────────
Fetches live prices for Indian (NSE/BSE) and US stocks.
Uses history() as primary method with fast_info fast-path attempt.
Validates data before returning — never sends NaN or zero to Telegram.
"""

import logging
import yfinance as yf

logger = logging.getLogger(__name__)


def _fetch_ticker(symbol: str) -> dict | None:
    """Fetch a single stock with fast_info → history() fallback."""
    try:
        t     = yf.Ticker(symbol)
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
            logger.debug("fast_info failed for %s: %s", symbol, e)
            price = None

        # ── Attempt 2: history()
        if price is None or price <= 0:
            hist = t.history(period="5d", interval="1d")
            if hist.empty:
                logger.warning("history() returned empty for %s", symbol)
                return None
            price = float(hist["Close"].iloc[-1])
            prev  = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price

        # Final validation
        if price is None or price != price or price <= 0:
            logger.warning("Invalid price for %s: %s", symbol, price)
            return None

        prev  = prev or price
        change     = price - prev
        change_pct = (change / prev * 100) if prev else 0.0

        # Reject implausible intra-day swings (>25% likely bad data)
        if abs(change_pct) > 25:
            logger.warning("Suspicious swing for %s: %.2f%% — skipping", symbol, change_pct)
            return None

        currency = "₹" if symbol.endswith((".NS", ".BO")) else "$"

        return {
            "symbol":     symbol,
            "price":      round(price, 2),
            "prev_close": round(prev, 2),
            "change":     round(change, 2),
            "change_pct": round(change_pct, 2),
            "arrow":      "▲" if change >= 0 else "▼",
            "currency":   currency,
        }
    except Exception as exc:
        logger.error("fetch_ticker(%s) failed: %s", symbol, exc)
        return None


def fetch_stocks(symbols: list[str]) -> dict[str, dict | None]:
    """Fetch multiple stocks. Returns dict keyed by symbol."""
    return {sym: _fetch_ticker(sym) for sym in symbols}


def fetch_one(symbol: str) -> dict | None:
    """Public single-stock fetch (used by /price command)."""
    return _fetch_ticker(symbol.upper())
