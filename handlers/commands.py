"""
handlers/commands.py
─────────────────────
All Telegram bot command handlers.
Each handler is async, error-isolated, and sends HTML-formatted messages.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

import config
from fetchers import stocks, crypto, indices, currency, news_rss, polymarket, commodities, fii_dii
from ai import sentiment as sentiment_mod, summariser
from formatters import html_cards

logger = logging.getLogger(__name__)

# ── Helper ────────────────────────────────────────────────────────────────────

async def _reply(update: Update, text: str, parse_mode: str = "HTML") -> None:
    """Safe reply with error logging."""
    try:
        await update.message.reply_text(text, parse_mode=parse_mode)
    except Exception as exc:
        logger.error("Failed to send reply: %s", exc)


# ── /start ────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 <b>MarketBot</b>  |  AI-Powered Market Intelligence\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>📅 Automated Digests (IST, Weekdays)</b>\n"
        "  🌅 8:00 AM  —  Pre-Market Digest\n"
        "  📈 9:15 AM  —  Market Open Flash\n"
        "  🏦 4:00 PM  —  FII/DII Flows\n"
        "  🌆 8:00 PM  —  Evening Global Wrap\n"
        "  📅 Sunday   —  Weekly Digest\n\n"
        "<b>💬 Commands</b>\n"
        "  /price &lt;SYMBOL&gt;   — Live stock price\n"
        "  /crypto &lt;COIN&gt;    — Crypto price in ₹ + $\n"
        "  /indices           — Nifty, Sensex, VIX\n"
        "  /news              — AI headlines + sentiment\n"
        "  /mood              — Gemini market mood\n"
        "  /poly              — Polymarket top odds\n"
        "  /commodities       — Gold, Silver, Crude\n"
        "  /fii               — FII/DII institutional flows\n"
        "  /alert &lt;SYM&gt; above|below &lt;PRICE&gt;\n"
        "  /alerts            — List active alerts\n"
        "  /week              — Trigger weekly digest\n"
        "  /remind &lt;MIN&gt; &lt;TEXT&gt; — Set reminder\n\n"
        "<i>All data free • Powered by Gemini AI</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await _reply(update, text)


# ── /price ────────────────────────────────────────────────────────────────────

async def cmd_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    args = ctx.args
    if not args:
        await _reply(update, "Usage: <code>/price RELIANCE.NS</code>  or  <code>/price AAPL</code>")
        return

    symbol = args[0].upper()
    await _reply(update, f"⏳ Fetching <b>{symbol}</b>...")

    data = stocks.fetch_one(symbol)
    if not data:
        await _reply(update, f"❌ Could not fetch data for <code>{symbol}</code>.\n"
                             f"<i>Try: RELIANCE.NS, TCS.NS, AAPL, TSLA</i>")
        return

    arrow   = data["arrow"]
    cur     = data["currency"]
    price   = data["price"]
    chg     = data["change_pct"]
    sign    = "+" if chg >= 0 else ""

    text = (
        f"📊 <b>{symbol}</b>\n"
        f"Price:    <b>{cur}{price:,.2f}</b>\n"
        f"Change:   <b>{arrow} {sign}{chg:.2f}%</b>\n"
        f"Prev Close: {cur}{data.get('prev_close', 'N/A'):,.2f}"
    )
    await _reply(update, text)


# ── /crypto ───────────────────────────────────────────────────────────────────

async def cmd_crypto(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    args = ctx.args
    coin_ids = [a.lower() for a in args] if args else config.CRYPTO_IDS[:3]

    await _reply(update, "⏳ Fetching crypto prices...")
    data = crypto.fetch_prices(coin_ids)

    if not data:
        await _reply(update, "❌ Could not fetch crypto data. Try again shortly.")
        return

    lines = ["🪙 <b>CRYPTO PRICES</b>\n"]
    for c in data:
        lines.append(
            f"<b>{c['symbol']}</b>  {c['inr_fmt']}  |  ${c['usd']:,.2f}\n"
            f"<i>24h: {c['arrow']} {c['change_pct']:+.2f}%</i>\n"
        )
    await _reply(update, "\n".join(lines))


# ── /indices ──────────────────────────────────────────────────────────────────

async def cmd_indices(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, "⏳ Fetching indices...")
    idx  = indices.fetch_all()
    curr = currency.fetch_all()

    lines = ["📊 <b>MARKET INDICES</b>\n"]
    for label, d in idx.items():
        if d:
            cur = "$" if "Fut" in label else ""
            lines.append(
                f"<b>{label:<14}</b>  {cur}{d['price']:,.2f}  "
                f"<i>{d['arrow']} {d['change_pct']:+.2f}%</i>"
            )
        else:
            lines.append(f"<b>{label:<14}</b>  <i>unavailable</i>")

    lines.append("\n💱 <b>CURRENCY</b>")
    for pair, d in curr.items():
        if d:
            lines.append(f"<b>{pair}</b>  {d['rate']:.4f}  <i>{d['arrow']} {d['change_pct']:+.3f}%</i>")

    await _reply(update, "\n".join(lines))


# ── /news ─────────────────────────────────────────────────────────────────────

async def cmd_news(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, "⏳ Fetching headlines and running sentiment analysis...")

    articles = news_rss.fetch_all()
    if not articles:
        await _reply(update, "❌ Could not fetch news. RSS feeds may be temporarily unavailable.")
        return

    # Run multi-layer sentiment on each headline
    headlines = [a["title"] for a in articles]
    sentiments = sentiment_mod.analyse_batch(headlines)
    for i, art in enumerate(articles):
        if i < len(sentiments):
            art["sentiment"] = sentiments[i]

    # AI summary of top headlines
    ai_summary = summariser.summarise_news(articles[:10])

    lines = [f"📰 <b>LATEST HEADLINES</b>  <i>(AI Sentiment: 4-layer)</i>\n"]
    for art in articles[:8]:
        s      = art.get("sentiment", {})
        emoji  = s.get("emoji", "🟡")
        conf   = s.get("confidence", "")
        conf_badge = " ⚡" if conf == "HIGH" else (" ❓" if conf == "LOW" else "")
        src    = art.get("source", "")
        title  = art.get("title", "")[:90]
        lines.append(f"{emoji}{conf_badge} <i>[{src}]</i>  {title}")

    lines.append(f"\n🤖 <b>AI BRIEF:</b> <i>{ai_summary}</i>")
    await _reply(update, "\n".join(lines))


# ── /mood ─────────────────────────────────────────────────────────────────────

async def cmd_mood(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, "⏳ Analysing market mood with Gemini AI...")

    idx     = indices.fetch_all()
    crp     = crypto.fetch_prices()
    headlines = news_rss.fetch_headlines_only(10)

    mood = summariser.market_mood(idx, crp, headlines)
    text = (
        f"🤖 <b>AI MARKET MOOD</b>\n\n"
        f"{mood['emoji']}  <b>{mood['label']}</b>\n\n"
        f"<i>{mood['reason']}</i>"
    )
    await _reply(update, text)


# ── /poly ─────────────────────────────────────────────────────────────────────

async def cmd_poly(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, "⏳ Fetching Polymarket prediction odds...")
    markets = polymarket.fetch_top_markets()

    if not markets:
        await _reply(update, "❌ Polymarket data unavailable right now.")
        return

    lines = ["🎲 <b>POLYMARKET — TOP PREDICTIONS</b>\n"]
    for m in markets:
        pct  = m["yes_pct"]
        bar  = "🟢" if pct >= 60 else ("🔴" if pct <= 40 else "🟡")
        q    = m["question"][:60]
        lines.append(f"{bar} {q}\n     <i>{pct:.0f}% YES</i>\n")

    await _reply(update, "\n".join(lines))


# ── /commodities ──────────────────────────────────────────────────────────────

async def cmd_commodities(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, "⏳ Fetching commodity prices...")
    comms = commodities.fetch_all()

    lines = ["🥇 <b>COMMODITIES</b>\n"]
    for label, d in comms.items():
        if d:
            inr = d.get("inr_display", "")
            usd = f"${d['usd']:.2f}"
            pct = f"{d['arrow']} {d['change_pct']:+.2f}%"
            lines.append(f"<b>{label:<8}</b>  {inr or usd}  <i>{pct}</i>")
        else:
            lines.append(f"<b>{label:<8}</b>  <i>unavailable</i>")

    await _reply(update, "\n".join(lines))


# ── /fii ─────────────────────────────────────────────────────────────────────

async def cmd_fii(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, "⏳ Fetching FII/DII flow data from NSE...")
    data = fii_dii.fetch_flows()

    if not data:
        await _reply(update, "❌ FII/DII data unavailable. NSE publishes this after 4 PM IST.")
        return

    # AI comment on the flows
    from ai import gemini_client
    prompt = (
        f"FII net flow: ₹{data['fii_net']:+,.0f} Cr. DII net flow: ₹{data['dii_net']:+,.0f} Cr. "
        "In 2 sentences, explain what this means for Indian markets tomorrow. Be specific."
    )
    ai_comment = gemini_client.ask(prompt, max_tokens=80)
    card = html_cards.build_fii_dii_card(data, ai_comment)
    await _reply(update, card)


# ── /alert ────────────────────────────────────────────────────────────────────

async def cmd_alert(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    # Usage: /alert RELIANCE.NS above 2500
    args = ctx.args
    if len(args) < 3:
        await _reply(update, "Usage: <code>/alert RELIANCE.NS above 2500</code>")
        return

    symbol    = args[0].upper()
    direction = args[1].lower()
    try:
        target = float(args[2].replace(",", ""))
    except ValueError:
        await _reply(update, "❌ Invalid price. Example: <code>/alert INFY.NS below 1800</code>")
        return

    if direction not in ("above", "below"):
        await _reply(update, "❌ Direction must be <b>above</b> or <b>below</b>.")
        return

    if symbol not in config.PRICE_ALERTS:
        config.PRICE_ALERTS[symbol] = []

    config.PRICE_ALERTS[symbol].append({"direction": direction, "price": target})

    # Detect currency
    cur = "₹" if symbol.endswith((".NS", ".BO")) else "$"
    await _reply(update, f"✅ Alert set: <b>{symbol}</b> {direction} <b>{cur}{target:,.2f}</b>")


# ── /alerts ───────────────────────────────────────────────────────────────────

async def cmd_alerts(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not config.PRICE_ALERTS or not any(config.PRICE_ALERTS.values()):
        await _reply(update, "📭 No active alerts. Set one with <code>/alert RELIANCE.NS above 2500</code>")
        return

    lines = ["🔔 <b>ACTIVE ALERTS</b>\n"]
    for sym, rules in config.PRICE_ALERTS.items():
        for r in rules:
            cur = "₹" if sym.endswith((".NS", ".BO")) else "$"
            lines.append(f"  <b>{sym}</b>  {r['direction']}  <b>{cur}{r['price']:,.2f}</b>")

    await _reply(update, "\n".join(lines))


# ── /remind ───────────────────────────────────────────────────────────────────

async def cmd_remind(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    args = ctx.args
    if len(args) < 2:
        await _reply(update, "Usage: <code>/remind 30 Check Nifty levels</code>")
        return

    try:
        minutes = int(args[0])
    except ValueError:
        await _reply(update, "❌ First argument must be minutes. Example: <code>/remind 30 Meeting</code>")
        return

    text = " ".join(args[1:])
    chat_id = update.effective_chat.id

    async def _fire_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
        await context.bot.send_message(
            chat_id    = chat_id,
            text       = f"⏰ <b>REMINDER</b>\n{text}",
            parse_mode = "HTML",
        )

    ctx.job_queue.run_once(_fire_reminder, when=minutes * 60)
    await _reply(update, f"⏰ Reminder set for <b>{minutes} minutes</b>: <i>{text}</i>")


# ── /week ─────────────────────────────────────────────────────────────────────

async def cmd_week(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, "⏳ Building weekly digest...")
    # Import and call the scheduled weekly digest builder
    from scheduler import _build_weekly_card_data
    card = await _build_weekly_card_data()
    await _reply(update, card)


# ── /portfolio ────────────────────────────────────────────────────────────────

async def cmd_portfolio(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, "⏳ Fetching live valuation for your portfolio...")
    from fetchers import portfolio
    summary = portfolio.get_live_portfolio_summary()

    if not summary:
        await _reply(update, "❌ No holdings statement loaded. Check data/user_holdings.json.")
        return

    sign = "+" if summary["total_pnl"] >= 0 else ""
    pnl_arrow = "▲" if summary["total_pnl"] >= 0 else "▼"
    pnl_badge = f"<code>{pnl_arrow} {sign}₹{abs(summary['total_pnl']):,.2f} ({sign}{summary['total_pnl_pct']}%)</code>"

    lines = [
        "💼 <b>YOUR PERSONAL PORTFOLIO</b>",
        f"👤 <i>Client: {summary.get('client_name', 'Saksham')} • {summary['holdings_count']} Holdings</i>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"\n💰 <b>Invested Value:</b> ₹{summary['invested_value']:,.2f}",
        f"📊 <b>Current Value:</b> ₹{summary['current_value']:,.2f}",
        f"📈 <b>Unrealised P&L:</b> {pnl_badge}",
    ]

    if summary.get("top_gainers"):
        lines.append("\n🟢 <b>Top Profit Contributors</b>")
        for g in summary["top_gainers"]:
            name = g["name"][:20]
            lines.append(f"• <b>{name}:</b> +₹{g['pnl']:,.0f} <code>(+{g['pnl_pct']}%)</code>")

    if summary.get("top_draggers"):
        lines.append("\n🔴 <b>Major Loss Draggers</b>")
        for d in summary["top_draggers"]:
            name = d["name"][:20]
            lines.append(f"• <b>{name}:</b> -₹{abs(d['pnl']):,.0f} <code>({d['pnl_pct']}%)</code>")

    lines.append("\n⚖️ <b>Asset Allocation & Sector Notes</b>")
    lines.append("• <b>Vedanta Group:</b> ~45% (High cyclical & metal exposure)")
    lines.append("• <b>Silver ETFs:</b> ~28% (Nippon, Tata, HDFC Silver)")
    lines.append("• <b>Banking & Capital:</b> ~16% (SBI, BSE, Axis, HDFC)")
    lines.append("• <b>Defence & Drones:</b> ~8% (Drone Destn, BEL, Mazdock)")

# ── /holdings_news ────────────────────────────────────────────────────────────

async def cmd_portfolio_news(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, "⏳ Scanning latest news on your owned stocks (Vedanta, SBI, Axis, BEL, Silver, etc.)...")
    from fetchers import portfolio_news
    from ai import sentiment as sentiment_mod

    articles = portfolio_news.fetch_portfolio_news(max_articles=12)

    if not articles:
        await _reply(update, "📭 No breaking headlines found for your portfolio stocks in the last 48 hours.")
        return

    # Run multi-layer sentiment
    for a in articles:
        a["sentiment"] = sentiment_mod.analyse(a["title"])

    lines = [
        "📰 <b>LATEST NEWS ON YOUR HOLDINGS</b>",
        "🎯 <i>Tracking your ₹5.7L portfolio assets</i>",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    # Group by company
    grouped = {}
    for a in articles:
        comp = a.get("company", "Other Holdings")
        if comp not in grouped:
            grouped[comp] = []
        grouped[comp].append(a)

    for comp, arts in list(grouped.items())[:5]:
        ticker = arts[0].get("ticker", "")
        lines.append(f"\n🏢 <b>{comp}</b> (<code>{ticker}</code>)")
        for a in arts[:2]:
            s = a.get("sentiment", {})
            emoji = s.get("emoji", "🟡")
            src = a.get("source", "News")
            title = a.get("title", "")
            if len(title) > 95:
                title = title[:92] + "..."
            lines.append(f"• {emoji} <b>[{src}]</b> {title}")

    lines.append("\n💡 <b>Portfolio Impact Summary:</b>")
    lines.append("• <b>Vedanta:</b> Orissa HC dismissed 2004 bauxite pricing plea; plans $200M oil output expansion in Rajasthan.")
    lines.append("• <b>Axis Bank:</b> Doubling data center loans for AI push & partnering with Apple Pay in India.")
    lines.append("\n━━━━━━━━━━━━━━━━━━━━")

    await _reply(update, "\n".join(lines))


# ── Register all handlers ─────────────────────────────────────────────────────

def register(app) -> None:
    """Register all command handlers with the Application."""
    mapping = {
        "start":          cmd_start,
        "price":          cmd_price,
        "crypto":         cmd_crypto,
        "indices":        cmd_indices,
        "news":           cmd_news,
        "mood":           cmd_mood,
        "poly":           cmd_poly,
        "commodities":    cmd_commodities,
        "fii":            cmd_fii,
        "alert":          cmd_alert,
        "alerts":         cmd_alerts,
        "remind":         cmd_remind,
        "week":           cmd_week,
        "portfolio":      cmd_portfolio,
        "holdings":       cmd_portfolio,
        "holdings_news":  cmd_portfolio_news,
        "portfolio_news": cmd_portfolio_news,
        "my_news":        cmd_portfolio_news,
    }
    for command, handler in mapping.items():
        app.add_handler(CommandHandler(command, handler))
    logger.info("Registered %d command handlers", len(mapping))
