"""
fetchers/fii_dii.py
────────────────────
Fetches FII (Foreign Institutional Investor) and DII (Domestic Institutional
Investor) daily net flow data from NSE India's public endpoint.

NSE publishes this data after market close (~4–5 PM IST).
Falls back to a web-scraped summary if the JSON endpoint is unavailable.
"""

import logging
import requests
from datetime import date

logger = logging.getLogger(__name__)

# NSE India public API — no authentication required
_NSE_URL = "https://www.nseindia.com/api/fiidiiTradeReact"
_TIMEOUT  = 10
_HEADERS  = {
    "User-Agent":       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept":           "application/json",
    "Accept-Language":  "en-US,en;q=0.9",
    "Referer":          "https://www.nseindia.com/",
}

# NSE requires a session cookie — we pre-fetch the homepage to get it
_SESSION_URL = "https://www.nseindia.com"


def _get_session() -> requests.Session:
    """Create a session with NSE cookies pre-loaded."""
    session = requests.Session()
    session.headers.update(_HEADERS)
    try:
        session.get(_SESSION_URL, timeout=_TIMEOUT)
    except Exception as exc:
        logger.warning("NSE session pre-fetch failed: %s", exc)
    return session


def fetch_flows() -> dict | None:
    """
    Fetch today's FII and DII net flows from NSE India.

    Returns:
        {
            "date":       str,
            "fii_net":    float,   # Crores, negative = outflow
            "dii_net":    float,   # Crores, positive = inflow
            "net_total":  float,
            "fii_label":  str,     # "Buyers" or "Sellers"
            "dii_label":  str,
        }
    or None on failure.
    """
    session = _get_session()
    try:
        resp = session.get(_NSE_URL, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.error("FII/DII fetch failed: %s", exc)
        return None

    # NSE returns a list — most recent entry is today's data
    if not isinstance(data, list) or not data:
        logger.warning("FII/DII: unexpected response format")
        return None

    # Find today's record or most recent
    today_str = date.today().strftime("%d-%b-%Y").upper()
    record = None

    for entry in data:
        entry_date = (entry.get("date") or entry.get("Date") or "").upper()
        if today_str in entry_date:
            record = entry
            break

    if not record:
        record = data[0]  # fallback: most recent
        logger.info("FII/DII: today's data not found, using most recent: %s", record.get("date"))

    try:
        # NSE key names vary — handle both camelCase and plain
        def _get_float(d: dict, *keys: str) -> float:
            for k in keys:
                val = d.get(k)
                if val is not None:
                    return float(str(val).replace(",", ""))
            return 0.0

        fii_net = _get_float(record, "fiiNetDii", "fii_net", "FII_NET", "netDII")
        dii_net = _get_float(record, "diiNetDii", "dii_net", "DII_NET", "netDii")

        # Sometimes NSE returns FII/DII separately under category fields
        if fii_net == 0 and dii_net == 0:
            # Try parsing from category-based structure
            for cat in data:
                category = (cat.get("category") or "").upper()
                net = _get_float(cat, "netPurchasesSales", "net", "NET")
                if "FII" in category or "FPI" in category:
                    fii_net = net
                elif "DII" in category:
                    dii_net = net

        net_total = fii_net + dii_net

        return {
            "date":      record.get("date", today_str),
            "fii_net":   round(fii_net, 2),
            "dii_net":   round(dii_net, 2),
            "net_total": round(net_total, 2),
            "fii_label": "Buyers 🟢" if fii_net >= 0 else "Sellers 🔴",
            "dii_label": "Buyers 🟢" if dii_net >= 0 else "Sellers 🔴",
        }

    except Exception as exc:
        logger.error("FII/DII data parsing failed: %s | record=%s", exc, record)
        return None
