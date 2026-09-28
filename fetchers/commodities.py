"""
fetchers/commodities.py
────────────────────────
Fetches Gold, Silver, and Crude Oil via direct Yahoo chart API with yfinance fallback.
Returns INR-converted prices for Gold and Silver.
"""

import logging
import yfinance as yf
from fetchers.currency import get_usd_inr
from fetchers.yahoo_direct import fetch_chart_data

logger = logging.getLogger(__name__)

_COMMODITIES = {
    "Gold":   ("GC=F", "$/troy oz"),
    "Silver": ("SI=F", "$/troy oz"),
    "Crude":  ("CL=F", "$/bbl"),
}

_BOUNDS = {
    "GC=F": (1_000, 5_000),
    "SI=F": (10,    200),
    "CL=F": (20,    200),
}

_TROY_OZ_TO_10G = 0.3215  # 10g / 31.1035g per troy oz


def _fetch_commodity(label: str, ticker: str, unit: str) -> dict | None:
    try:
        price = None
        prev = None

        chart = fetch_chart_data(ticker)
        if chart:
            price = chart["price"]
            prev = chart["prev_close"]

        if price is None or price <= 0:
            t = yf.Ticker(ticker)
            try:
                hist = t.history(period="5d", interval="1d", actions=False)
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
            except Exception:
                pass

        lo, hi = _BOUNDS.get(ticker, (0, 1e9))
        if price is None or not (lo <= price <= hi):
            logger.warning("Commodity %s price %s out of bounds", label, price)
            return None

        prev = prev or price
        change_pct = ((price - prev) / prev * 100) if prev else 0.0

        result = {
            "label":      label,
            "ticker":     ticker,
            "usd":        round(price, 2),
            "unit":       unit,
            "change_pct": round(change_pct, 2),
            "arrow":      "▲" if change_pct >= 0 else "▼",
        }

        usd_inr = get_usd_inr()
        if label == "Gold":
            inr_per_10g = price * _TROY_OZ_TO_10G * usd_inr
            result["inr_display"] = f"₹{inr_per_10g:,.0f}/10g"
        elif label == "Silver":
            inr_per_kg = price * (1000 / 31.1035) * usd_inr
            result["inr_display"] = f"₹{inr_per_kg:,.0f}/kg"

        return result
    except Exception as exc:
        logger.error("fetch_commodity(%s) failed: %s", label, exc)
        return None


def fetch_all() -> dict[str, dict | None]:
    return {
        label: _fetch_commodity(label, ticker, unit)
        for label, (ticker, unit) in _COMMODITIES.items()
    }
