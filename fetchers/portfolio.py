"""
fetchers/portfolio.py
──────────────────────
Manages the user's personal investment portfolio.
Loads holdings from data/user_holdings.json and fetches live prices
to compute real-time portfolio valuation, daily P&L, and asset breakdown.
"""

import os
import json
import logging
from fetchers.yahoo_direct import fetch_chart_data

logger = logging.getLogger(__name__)

HOLDINGS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "user_holdings.json")


def load_holdings() -> dict:
    if not os.path.exists(HOLDINGS_PATH):
        return {}
    try:
        with open(HOLDINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.error("Failed to load user_holdings.json: %s", exc)
        return {}


def get_live_portfolio_summary() -> dict:
    """
    Computes real-time valuation of user holdings based on live market prices.
    Returns:
      {
        "invested_value": float,
        "current_value": float,
        "total_pnl": float,
        "total_pnl_pct": float,
        "top_gainers": list[dict],
        "top_draggers": list[dict],
        "holdings_count": int,
        "as_of_date": str
      }
    """
    data = load_holdings()
    if not data:
        return {}

    holdings = data.get("holdings", [])
    invested_total = data.get("invested_value", 0.0)
    current_total = 0.0

    items_with_live = []

    for h in holdings:
        ticker = h.get("ticker")
        qty = h.get("quantity", 0)
        invested = h.get("invested_value", 0.0)
        fallback_price = h.get("closing_price", 0.0)

        live_price = fallback_price
        if ticker:
            chart = fetch_chart_data(ticker)
            if chart and chart.get("price"):
                live_price = chart["price"]

        curr_val = round(live_price * qty, 2)
        pnl = round(curr_val - invested, 2)
        pnl_pct = round((pnl / invested * 100) if invested else 0.0, 2)

        current_total += curr_val

        items_with_live.append({
            "name": h["name"],
            "ticker": ticker,
            "quantity": qty,
            "invested": invested,
            "current_price": live_price,
            "current_value": curr_val,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
        })

    current_total = round(current_total, 2)
    total_pnl = round(current_total - invested_total, 2)
    total_pnl_pct = round((total_pnl / invested_total * 100) if invested_total else 0.0, 2)

    # Sort to find gainers and draggers
    sorted_by_pnl = sorted(items_with_live, key=lambda x: x["pnl_pct"], reverse=True)
    top_gainers = [x for x in sorted_by_pnl if x["pnl"] > 0][:4]
    top_draggers = [x for x in sorted_by_pnl if x["pnl"] < 0][-4:]

    return {
        "client_name": data.get("client_name", "Saksham Aggarwal"),
        "invested_value": invested_total,
        "current_value": current_total,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "top_gainers": top_gainers,
        "top_draggers": top_draggers,
        "holdings_count": len(holdings),
        "items": items_with_live,
    }
