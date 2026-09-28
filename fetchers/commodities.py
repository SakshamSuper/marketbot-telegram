"""
fetchers/commodities.py
────────────────────────
Fetches Gold, Silver, and Crude Oil via yfinance with history() fallback.
Returns INR-converted prices for Gold and Silver.
"""

import logging
import yfinance as yf
from fetchers.currency import get_usd_inr

logger = logging.getLogger(__name__)

_COMMODITIES = {
    "Gold":   ("GC=F", "$/troy oz"),
    "Silver": ("SI=F", "$/troy oz"),
    "Crude":  ("CL=F", "$/bbl"),
}

_BOUNDS = {
    "GC=F": (1_000, 4_000),
    "SI=F": (10,    200),
    "CL=F": (20,    200),
}

_TROY_OZ_TO_10G = 0.3215  # 10g / 31.1035g per troy oz


def _fetch_commodity(label: str, ticker: str, unit: str) -> dict | None:
    try:
        t     = yf.Ticker(ticker)
        price = None
        prev  = None

        # Attempt 1: fast_info
        try:
            info  = t.fast_info
            price = getattr(info, "last_price", None)
            prev  = getattr(info, "previous_close", None)
            if price is not None and (price != price or price <= 0):
                price = None
        except Exception:
            price = None

        # Attempt 2: history()
        if price is None or price <= 0:
            hist = t.history(period="5d", interval="1d")
            if hist.empty:
                logger.warning("history() empty for %s (%s)", label, ticker)
                return None
            price = float(hist["Close"].iloc[-1])
            prev  = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price

        lo, hi = _BOUNDS.get(ticker, (0, 1e9))
        if not (lo <= price <= hi):
            logger.warning("Commodity %s price %.2f out of bounds", label, price)
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
