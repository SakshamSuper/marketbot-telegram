"""
alerts/price_alert.py
──────────────────────
Smart price alert engine.

Rules:
  1. Only fires if price moved >PRICE_CHANGE_THRESHOLD_PCT since last snapshot
  2. Won't re-alert the same symbol within ALERT_COOLDOWN_HOURS
  3. Runs multi-layer sentiment on the move
  4. Includes AI-generated explanation (Gemini)
  5. User-defined threshold alerts (/alert command) are also checked here
"""

import time
import logging
from datetime import datetime

import config
from fetchers import stocks
from ai import sentiment as sentiment_mod
from ai import summariser
from formatters import html_cards

logger = logging.getLogger(__name__)

ALL_SYMBOLS = config.INDIAN_STOCKS + config.US_STOCKS


def _is_cooldown_active(symbol: str) -> bool:
    """Return True if we already alerted this symbol within cooldown window."""
    snap = config.LAST_PRICE_SNAPSHOT.get(symbol, {})
    last_ts = snap.get("last_alert_ts")
    if not last_ts:
        return False
    elapsed_hrs = (time.time() - last_ts) / 3600
    return elapsed_hrs < config.ALERT_COOLDOWN_HOURS


def _record_alert(symbol: str, price: float) -> None:
    if symbol not in config.LAST_PRICE_SNAPSHOT:
        config.LAST_PRICE_SNAPSHOT[symbol] = {}
    config.LAST_PRICE_SNAPSHOT[symbol]["last_alert_ts"] = time.time()
    config.LAST_PRICE_SNAPSHOT[symbol]["price"] = price


def _update_snapshot(symbol: str, price: float) -> None:
    """Update price without touching the alert timestamp."""
    if symbol not in config.LAST_PRICE_SNAPSHOT:
        config.LAST_PRICE_SNAPSHOT[symbol] = {}
    config.LAST_PRICE_SNAPSHOT[symbol]["price"] = price


async def run_smart_alert_cycle(bot, chat_id: str) -> None:
    """
    Run one full cycle of smart alerts across all watched symbols.
    Called every ALERT_POLL_INTERVAL seconds by the scheduler.
    """
    all_data = stocks.fetch_stocks(ALL_SYMBOLS)

    for symbol, data in all_data.items():
        if not data:
            continue

        current_price = data["price"]
        change_pct    = data["change_pct"]

        _update_snapshot(symbol, current_price)

        # Skip if move is below threshold
        if abs(change_pct) < config.PRICE_CHANGE_THRESHOLD_PCT:
            continue

        # Skip if in cooldown
        if _is_cooldown_active(symbol):
            logger.debug("Alert cooldown active for %s", symbol)
            continue

        logger.info("SMART ALERT: %s moved %.2f%%", symbol, change_pct)
        _record_alert(symbol, current_price)

        # Multi-layer sentiment on the move itself
        move_description = (
            f"{symbol} {'surged' if change_pct > 0 else 'dropped'} "
            f"{abs(change_pct):.1f}% to {data['currency']}{current_price:,.2f}"
        )
        sent = sentiment_mod.analyse(move_description)

        # AI explanation
        ai_reason = summariser.explain_price_move(symbol, change_pct)

        card = html_cards.build_alert_card(
            symbol     = symbol,
            price      = current_price,
            change_pct = change_pct,
            currency   = data["currency"],
            ai_reason  = ai_reason,
            sentiment  = sent,
            threshold  = config.PRICE_CHANGE_THRESHOLD_PCT,
        )

        try:
            await bot.send_message(
                chat_id    = chat_id,
                text       = card,
                parse_mode = "HTML",
            )
            logger.info("Smart alert sent for %s", symbol)
        except Exception as exc:
            logger.error("Failed to send alert for %s: %s", symbol, exc)

        # Also check user-defined /alert thresholds
        await _check_user_thresholds(bot, chat_id, symbol, current_price, data)


async def _check_user_thresholds(bot, chat_id: str, symbol: str, price: float, data: dict) -> None:
    """Check user-set /alert thresholds for this symbol."""
    thresholds = config.PRICE_ALERTS.get(symbol, [])
    remaining  = []

    for rule in thresholds:
        direction   = rule["direction"]
        target      = rule["price"]
        triggered   = (direction == "above" and price >= target) or \
                      (direction == "below" and price <= target)

        if triggered:
            msg = (
                f"🎯 <b>THRESHOLD ALERT</b>  —  <b>{symbol}</b>\n"
                f"Price <b>{data['currency']}{price:,.2f}</b> is now "
                f"<b>{direction} {data['currency']}{target:,.2f}</b>\n"
                f"<i>Current change: {data['arrow']} {data['change_pct']:+.2f}%</i>"
            )
            try:
                await bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
                logger.info("Threshold alert fired: %s %s %.2f", symbol, direction, target)
            except Exception as exc:
                logger.error("Threshold alert send failed: %s", exc)
            # Remove fired threshold (one-time trigger)
        else:
            remaining.append(rule)

    config.PRICE_ALERTS[symbol] = remaining
