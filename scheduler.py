"""
scheduler.py
─────────────
IST-aware job scheduler.
Registers all timed digest jobs with the python-telegram-bot JobQueue.

Schedule (Asia/Kolkata, weekdays only unless noted):
  08:00  → Pre-Market Digest
  09:15  → Market Open Flash
  16:00  → FII/DII Flows
  20:00  → Evening Global Wrap
  Every ALERT_POLL_INTERVAL → Smart Price Alerts
  Sunday 09:00 → Weekly Digest
"""

import logging
from datetime import time as dtime

import pytz
from telegram.ext import Application

import config
from fetchers import indices, crypto, currency, news_rss, polymarket, commodities, fii_dii, stocks
from ai import sentiment as sentiment_mod, summariser
from formatters import html_cards
from alerts.price_alert import run_smart_alert_cycle

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

# ── Digest builders ───────────────────────────────────────────────────────────

def _upcoming_macro_events(days_ahead: int = 1) -> list[dict]:
    """Return macro events happening within `days_ahead` days."""
    import json, os
    from datetime import date, timedelta

    calendar_path = os.path.join(os.path.dirname(__file__), "data", "macro_calendar.json")
    try:
        with open(calendar_path, encoding="utf-8") as f:
            calendar = json.load(f)
    except Exception as exc:
        logger.warning("macro_calendar.json load failed: %s", exc)
        return []

    today     = date.today()
    cutoff    = today + timedelta(days=days_ahead)
    upcoming  = []

    for event in calendar:
        for date_str in event.get("dates", []):
            try:
                ev_date = date.fromisoformat(date_str)
            except ValueError:
                continue
            if today <= ev_date <= cutoff:
                upcoming.append({
                    "name":     event["name"],
                    "date":     ev_date.strftime("%a, %d %b"),
                    "time_ist": event.get("time_ist", ""),
                    "note":     event.get("note", ""),
                })

    return upcoming


async def _send(context, card: str) -> None:
    """Send a card message to CHAT_ID with delivery logging."""
    try:
        await context.bot.send_message(
            chat_id    = config.CHAT_ID,
            text       = card,
            parse_mode = "HTML",
        )
        logger.info("Digest card sent successfully (%d chars)", len(card))
    except Exception as exc:
        logger.error("Failed to send digest card: %s", exc)


# ── Job: Pre-Market Digest (8:00 AM) ─────────────────────────────────────────

async def job_premarket(context) -> None:
    logger.info("Running pre-market digest job")

    idx   = indices.fetch_all()
    crp   = crypto.fetch_prices()
    comms = commodities.fetch_all()
    curr  = currency.fetch_all()
    arts  = news_rss.fetch_all()
    macro = _upcoming_macro_events(days_ahead=1)

    # Sentiment on top articles
    for art in arts[:8]:
        art["sentiment"] = sentiment_mod.analyse(art["title"])

    headlines_only = [a["title"] for a in arts[:10]]
    ai_summary = summariser.summarise_news(arts[:10])
    ai_mood    = summariser.market_mood(idx, crp, headlines_only)

    from fetchers import portfolio_news
    p_news = portfolio_news.fetch_portfolio_news(max_articles=3)

    card = html_cards.build_premarket_card(
        indices        = idx,
        crypto         = crp,
        commodities    = comms,
        currency       = curr,
        articles       = arts[:4],
        ai_summary     = ai_summary,
        ai_mood        = ai_mood,
        macro_events   = macro,
        portfolio_news = p_news,
    )
    await _send(context, card)


# ── Job: Market Open Flash (9:15 AM) ─────────────────────────────────────────

async def job_market_open(context) -> None:
    logger.info("Running market open flash job")

    idx = indices.fetch_all()

    # Top movers from watchlist
    all_stocks = stocks.fetch_stocks(config.INDIAN_STOCKS)
    movers = sorted(
        [d for d in all_stocks.values() if d],
        key=lambda x: abs(x["change_pct"]),
        reverse=True,
    )[:5]

    nifty_d   = idx.get("Nifty 50", {}) or {}
    direction = "positive" if (nifty_d.get("change_pct", 0) or 0) >= 0 else "negative"
    top_names  = ", ".join(m["symbol"].replace(".NS","").replace(".BO","") for m in movers[:3])

    ai_prompt = (
        f"Indian markets opened {direction} today. "
        f"Top movers include: {top_names}. "
        "In 2 sentences, brief an Indian investor on what to watch in the first hour."
    )
    from ai import gemini_client
    ai_comment = gemini_client.ask(ai_prompt, max_tokens=80)

    card = html_cards.build_market_open_card(
        indices     = idx,
        top_movers  = movers,
        ai_comment  = ai_comment,
    )
    await _send(context, card)


# ── Job: FII/DII Flows (4:00 PM) ─────────────────────────────────────────────

async def job_fii_dii(context) -> None:
    logger.info("Running FII/DII flows job")

    data = fii_dii.fetch_flows()
    if not data:
        logger.warning("FII/DII: no data available, skipping digest")
        return

    from ai import gemini_client
    prompt = (
        f"FII net: ₹{data['fii_net']:+,.0f} Cr. DII net: ₹{data['dii_net']:+,.0f} Cr. "
        "In 2 sentences, explain what this means for tomorrow's Indian markets."
    )
    ai_comment = gemini_client.ask(prompt, max_tokens=80)
    card = html_cards.build_fii_dii_card(data, ai_comment)
    await _send(context, card)


# ── Job: Evening Global Wrap (8:00 PM) ───────────────────────────────────────

async def job_evening_wrap(context) -> None:
    logger.info("Running evening global wrap job")

    idx    = indices.fetch_all()
    crp    = crypto.fetch_prices()
    poly   = polymarket.fetch_top_markets()
    arts   = news_rss.fetch_headlines_only(8)

    ai_summary = summariser.summarise_news([{"source": "Evening", "title": h} for h in arts])

    card = html_cards.build_evening_card(
        indices      = idx,
        crypto       = crp,
        poly_markets = poly,
        ai_summary   = ai_summary,
    )
    await _send(context, card)


# ── Job: Smart Price Alerts (every N seconds) ─────────────────────────────────

async def job_smart_alerts(context) -> None:
    await run_smart_alert_cycle(context.bot, config.CHAT_ID)


# ── Job: Macro Reminder (daily check) ────────────────────────────────────────

async def job_macro_reminder(context) -> None:
    events = _upcoming_macro_events(days_ahead=1)
    if not events:
        return
    card = html_cards.build_macro_reminder_card(events)
    await _send(context, card)


# ── Job: Weekly Digest (Sunday 9:00 AM) ──────────────────────────────────────

async def _build_weekly_card_data() -> str:
    """Build the weekly digest card — shared between the scheduled job and /week command."""
    import yfinance as yf

    # Weekly % change for indices
    indices_weekly: dict = {}
    for label, ticker in config.INDICES.items():
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if len(hist) >= 2:
                start = hist["Close"].iloc[0]
                end   = hist["Close"].iloc[-1]
                pct   = (end - start) / start * 100
                indices_weekly[label] = {"change_pct": round(pct, 2), "arrow": "▲" if pct >= 0 else "▼"}
        except Exception as exc:
            logger.warning("Weekly index fetch failed for %s: %s", label, exc)

    # Weekly % change for watchlist stocks
    stocks_weekly: dict = {}
    for sym in config.INDIAN_STOCKS + config.US_STOCKS:
        try:
            t    = yf.Ticker(sym)
            hist = t.history(period="5d")
            if len(hist) >= 2:
                start = hist["Close"].iloc[0]
                end   = hist["Close"].iloc[-1]
                pct   = (end - start) / start * 100
                stocks_weekly[sym] = {"change_pct": round(pct, 2), "arrow": "▲" if pct >= 0 else "▼"}
        except Exception:
            pass

    # Crypto weekly
    crypto_weekly = crypto.fetch_prices()  # 24h change only; CoinGecko free tier limitation

    # Commodities weekly
    comms = commodities.fetch_all()

    # AI review
    summary_prompt = (
        f"Weekly market recap for an Indian investor:\n"
        f"Nifty weekly: {indices_weekly.get('Nifty 50', {}).get('change_pct', 0):+.1f}%\n"
        f"Sensex weekly: {indices_weekly.get('Sensex', {}).get('change_pct', 0):+.1f}%\n"
        "Write a 3-sentence week-in-review covering key themes and what to watch next week."
    )
    from ai import gemini_client
    ai_review = gemini_client.ask(summary_prompt, max_tokens=120)

    return html_cards.build_weekly_card(
        indices_weekly     = indices_weekly,
        stocks_weekly      = stocks_weekly,
        crypto_weekly      = crypto_weekly,
        commodities_weekly = {k: {"change_pct": v["change_pct"], "arrow": v["arrow"]} for k, v in comms.items() if v},
        ai_review          = ai_review,
    )


async def job_weekly_digest(context) -> None:
    logger.info("Running weekly digest job")
    card = await _build_weekly_card_data()
    await _send(context, card)


async def job_keep_alive(context) -> None:
    """Ping health endpoint every 9 minutes so Render free tier never sleeps."""
    import urllib.request
    try:
        req = urllib.request.Request(
            "https://marketbot-telegram.onrender.com/health",
            headers={"User-Agent": "MarketBot-KeepAlive/1.0"},
        )
        urllib.request.urlopen(req, timeout=10)
        logger.debug("Keep-alive ping sent to Render")
    except Exception as exc:
        logger.debug("Keep-alive ping: %s", exc)


# ── Register all jobs ─────────────────────────────────────────────────────────

def register_jobs(app: Application) -> None:
    """Register all scheduled jobs with the bot's JobQueue."""
    jq = app.job_queue

    # IST daily jobs — weekdays only (Mon=0 … Fri=4)
    weekdays = tuple(range(5))

    # Helper: create IST-aware time object
    def ist(hour: int, minute: int = 0) -> dtime:
        return dtime(hour=hour, minute=minute, tzinfo=IST)

    jq.run_daily(job_premarket,      ist(config.SCHEDULE_PREMARKET_HOUR, config.SCHEDULE_PREMARKET_MIN), days=weekdays, name="premarket")
    jq.run_daily(job_market_open,    ist(config.SCHEDULE_OPEN_HOUR,      config.SCHEDULE_OPEN_MIN),      days=weekdays, name="market_open")
    jq.run_daily(job_fii_dii,        ist(16, 0),                                                          days=weekdays, name="fii_dii")
    jq.run_daily(job_evening_wrap,   ist(config.SCHEDULE_EVENING_HOUR,   config.SCHEDULE_EVENING_MIN),   days=weekdays, name="evening_wrap")
    jq.run_daily(job_macro_reminder, ist(7, 45),                                                          name="macro_reminder")

    # Sunday weekly digest (day 6 = Sunday)
    jq.run_daily(job_weekly_digest,  ist(9, 0),  days=(6,), name="weekly_digest")

    # Smart alert polling — every N seconds, all week
    jq.run_repeating(job_smart_alerts, interval=config.ALERT_POLL_INTERVAL, first=30, name="smart_alerts")

    # Keep-alive pinger — every 9 minutes, keeps Render container awake 24/7
    jq.run_repeating(job_keep_alive, interval=540, first=60, name="keep_alive")

    logger.info(
        "Jobs registered: premarket=%02d:%02d, open=%02d:%02d, fii=16:00, evening=%02d:%02d, alerts=every %ds (all IST)",
        config.SCHEDULE_PREMARKET_HOUR, config.SCHEDULE_PREMARKET_MIN,
        config.SCHEDULE_OPEN_HOUR,      config.SCHEDULE_OPEN_MIN,
        config.SCHEDULE_EVENING_HOUR,   config.SCHEDULE_EVENING_MIN,
        config.ALERT_POLL_INTERVAL,
    )
