"""
fetchers/crypto.py
───────────────────
Fetches crypto prices from CoinGecko public API (no API key).
Converts USD prices to INR using live USD/INR rate.
"""

import logging
import requests
from fetchers.currency import get_usd_inr
import config

logger = logging.getLogger(__name__)

_COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
_TIMEOUT = 10  # seconds
_RETRY_COUNT = 2


def _lakh_format(inr: float) -> str:
    """Format large INR amounts as ₹X.XXL (lakhs) or ₹X,XXX for smaller."""
    if inr >= 1_00_000:
        return f"₹{inr / 1_00_000:.2f}L"
    elif inr >= 1_000:
        return f"₹{inr:,.0f}"
    return f"₹{inr:.2f}"


def fetch_prices(coin_ids: list[str] | None = None) -> list[dict]:
    """
    Fetch prices for given CoinGecko coin IDs.
    Returns list of validated price dicts.
    """
    ids = coin_ids or config.CRYPTO_IDS
    if not ids:
        return []

    usd_inr = get_usd_inr()
    params = {
        "ids": ",".join(ids),
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_24hr_vol": "false",
        "include_market_cap": "false",
    }

    last_exc: Exception | None = None
    for attempt in range(1, _RETRY_COUNT + 2):
        try:
            resp = requests.get(_COINGECKO_URL, params=params, timeout=_TIMEOUT)
            resp.raise_for_status()
            raw = resp.json()
            break
        except Exception as exc:
            last_exc = exc
            logger.warning("CoinGecko attempt %d failed: %s", attempt, exc)
            if attempt <= _RETRY_COUNT:
                import time; time.sleep(3 * attempt)
    else:
        logger.error("CoinGecko all retries failed: %s", last_exc)
        return []

    results = []
    for coin_id in ids:
        data = raw.get(coin_id)
        if not data:
            logger.warning("CoinGecko: no data for coin_id=%s", coin_id)
            continue

        usd_price = data.get("usd")
        change_pct = data.get("usd_24h_change", 0.0)

        # Validate
        if usd_price is None or usd_price != usd_price or usd_price <= 0:
            logger.warning("Invalid USD price for %s: %s", coin_id, usd_price)
            continue

        inr_price = usd_price * usd_inr

        results.append({
            "id":         coin_id,
            "symbol":     coin_id[:3].upper(),  # approximation; fine for display
            "usd":        round(usd_price, 2),
            "inr":        round(inr_price, 2),
            "inr_fmt":    _lakh_format(inr_price),
            "change_pct": round(change_pct, 2),
            "arrow":      "▲" if change_pct >= 0 else "▼",
        })

    return results
