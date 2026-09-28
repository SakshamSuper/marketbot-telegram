"""
fetchers/stocks.py
───────────────────
Fetches live prices for Indian (NSE/BSE) and US stocks.
Uses direct Yahoo chart API first, with yfinance as secondary fallback.
"""

import logging
import yfinance as yf
from fetchers.yahoo_direct import fetch_chart_data

logger = logging.getLogger(__name__)


def _fetch_ticker(symbol: str) -> dict | None:
    try:
        price = None
        prev = None

        # ── Primary Attempt: Direct Yahoo API
        chart = fetch_chart_data(symbol)
        if chart:
            price = chart["price"]
            prev = chart["prev_close"]

        # ── Secondary Attempt: yfinance
        if price is None or price <= 0:
            t = yf.Ticker(symbol)
            try:
                hist = t.history(period="5d", interval="1d", actions=False)
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
            except Exception:
                pass

        if price is None or price != price or price <= 0:
            logger.warning("Invalid price for %s: %s", symbol, price)
            return None

        prev = prev or price
        change = price - prev
        change_pct = (change / prev * 100) if prev else 0.0

        if abs(change_pct) > 35:
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
    return {sym: _fetch_ticker(sym) for sym in symbols}


def fetch_one(symbol: str) -> dict | None:
    return _fetch_ticker(symbol.upper())
