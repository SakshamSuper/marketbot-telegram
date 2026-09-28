"""
formatters/html_cards.py
─────────────────────────
Gorgeously formatted Telegram HTML message cards.
Optimized for mobile readability across iOS & Android screens:
- Proportional bullet layout (never jagged fixed-width columns)
- Distinct badge codes: <code>▲ +1.20%</code>
- Clean dividers & emoji headers
- Pure functions, robust against missing or partial data
"""

from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")
DIVIDER = "━━━━━━━━━━━━━━━━━━━━"


def _now_ist(fmt: str = "%a, %d %b %Y | %I:%M %p IST") -> str:
    return datetime.now(IST).strftime(fmt)


def _fmt_pct(pct: float, arrow: str = "") -> str:
    sign = "+" if pct >= 0 else ""
    return f"{arrow} {sign}{pct:.2f}%".strip()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Pre-Market Digest (8:00 AM)
# ─────────────────────────────────────────────────────────────────────────────

def build_premarket_card(
    indices: dict,
    crypto: list[dict],
    commodities: dict,
    currency: dict,
    articles: list[dict],
    ai_summary: str,
    ai_mood: dict,
    macro_events: list[dict],
) -> str:
    now = _now_ist("%a, %d %b %Y • 8:00 AM IST")
    lines = [
        f"📊 <b>PRE-MARKET INTELLIGENCE</b>",
        f"📅 <i>{now}</i>",
        DIVIDER,
    ]

    # Indian Indices
    lines.append("\n🇮🇳 <b>Indian Indices (Prev Close)</b>")
    for key, name in [("Nifty 50", "Nifty 50"), ("Sensex", "Sensex"), ("India VIX", "India VIX")]:
        d = indices.get(key)
        if d:
            cur = "" if "VIX" in key else "₹"
            lines.append(f"• <b>{name}:</b> {cur}{d['price']:,.2f} <code>{_fmt_pct(d['change_pct'], d['arrow'])}</code>")
        else:
            lines.append(f"• <b>{name}:</b> <i>unavailable</i>")

    # US Futures
    lines.append("\n🇺🇸 <b>Global & US Futures</b>")
    for key, name in [("S&P Fut", "S&P 500 Fut"), ("Nasdaq Fut", "Nasdaq Fut"), ("Dow Fut", "Dow Jones Fut")]:
        d = indices.get(key)
        if d:
            lines.append(f"• <b>{name}:</b> ${d['price']:,.2f} <code>{_fmt_pct(d['change_pct'], d['arrow'])}</code>")

    # Commodities & Forex
    c_gold = commodities.get("Gold")
    c_silver = commodities.get("Silver")
    c_crude = commodities.get("Crude")
    c_usd = currency.get("USD/INR")

    lines.append("\n🥇 <b>Commodities & Currency</b>")
    if c_gold:
        lines.append(f"• <b>MCX Gold (10g):</b> {c_gold.get('inr_display','')} <code>{_fmt_pct(c_gold['change_pct'], c_gold['arrow'])}</code>")
    if c_silver:
        lines.append(f"• <b>Silver (1kg):</b> {c_silver.get('inr_display','')} <code>{_fmt_pct(c_silver['change_pct'], c_silver['arrow'])}</code>")
    if c_crude:
        lines.append(f"• <b>Brent Crude:</b> ${c_crude['usd']:.2f}/bbl <code>{_fmt_pct(c_crude['change_pct'], c_crude['arrow'])}</code>")
    if c_usd:
        lines.append(f"• <b>USD/INR:</b> ₹{c_usd['rate']:.2f} <code>{_fmt_pct(c_usd['change_pct'], c_usd['arrow'])}</code>")

    # Crypto
    if crypto:
        lines.append("\n🪙 <b>Crypto Highlights (24h)</b>")
        for c in crypto[:2]:
            inr = c.get("inr_fmt", f"₹{c['inr']:,.0f}")
            lines.append(f"• <b>{c['symbol']}:</b> {inr} (${c['usd']:,.0f}) <code>{_fmt_pct(c['change_pct'], c['arrow'])}</code>")

    # Macro calendar
    if macro_events:
        lines.append("\n🏛️ <b>Key Macro Events Today</b>")
        for e in macro_events[:2]:
            lines.append(f"⚠️ <b>{e['name']}</b> ({e.get('time_ist','')})\n   <i>{e.get('note','')}</i>")

    # AI Sentiment & Mood
    if ai_mood:
        lines.append(f"\n🧠 <b>AI Market Mood:</b> {ai_mood.get('emoji','🟡')} <b>{ai_mood.get('label','Neutral')}</b>")
        if ai_mood.get("reason"):
            lines.append(f"<i>\"{ai_mood['reason']}\"</i>")

    # AI Brief
    if ai_summary:
        lines.append(f"\n📋 <b>Executive Summary</b>\n{ai_summary}")

    # Top Headlines
    if articles:
        lines.append("\n📰 <b>Top Market News (ET • Moneycontrol • Mint)</b>")
        for a in articles[:4]:
            s = a.get("sentiment", {})
            emoji = s.get("emoji", "🟡")
            src = a.get("source", "")
            title = a.get("title", "")
            if len(title) > 95:
                title = title[:92] + "..."
            lines.append(f"{emoji} <b>[{src}]</b> {title}")

    lines.append(f"\n{DIVIDER}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Market Open Flash (9:15 AM)
# ─────────────────────────────────────────────────────────────────────────────

def build_market_open_card(indices: dict, top_movers: list[dict], ai_comment: str) -> str:
    now = _now_ist("%I:%M %p IST")
    lines = [
        f"🔔 <b>MARKET OPEN FLASH</b>",
        f"📅 <i>{now}</i>",
        DIVIDER,
        "\n🇮🇳 <b>Opening Pulse</b>",
    ]

    for label in ("Nifty 50", "Sensex"):
        d = indices.get(label)
        if d:
            gap = "Gap Up 🟢" if d["change_pct"] > 0.1 else ("Gap Down 🔴" if d["change_pct"] < -0.1 else "Flat 🟡")
            lines.append(f"• <b>{label}:</b> ₹{d['price']:,.2f} <code>{_fmt_pct(d['change_pct'], d['arrow'])}</code> ({gap})")

    if top_movers:
        lines.append("\n🔥 <b>Watchlist Movers at Open</b>")
        for m in top_movers[:5]:
            pct = m.get("change_pct", 0)
            sym = m.get("symbol", "").replace(".NS", "").replace(".BO", "")
            arrow = "▲" if pct >= 0 else "▼"
            cur = m.get("currency", "₹")
            lines.append(f"• <b>{sym}:</b> {cur}{m.get('price',0):,.2f} <code>{arrow} {pct:+.2f}%</code>")

    if ai_comment:
        lines.append(f"\n🤖 <b>Opening Analysis:</b>\n<i>{ai_comment}</i>")

    lines.append(f"\n{DIVIDER}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Smart Price Alert
# ─────────────────────────────────────────────────────────────────────────────

def build_alert_card(
    symbol: str,
    price: float,
    change_pct: float,
    currency: str,
    ai_reason: str,
    sentiment: dict,
    threshold: float = 2.0,
) -> str:
    now = _now_ist("%I:%M %p IST")
    arrow = "▲" if change_pct >= 0 else "▼"
    dir_emoji = "🟢 SURGE" if change_pct >= 0 else "🔴 DROP"
    s_emoji = sentiment.get("emoji", "🟡")
    s_label = sentiment.get("label", "Neutral")
    sym_clean = symbol.replace(".NS", "").replace(".BO", "")

    lines = [
        f"⚡ <b>SMART PRICE ALERT</b>",
        f"📅 <i>{now}</i>",
        DIVIDER,
        f"\n{dir_emoji}: <b>{sym_clean}</b> crossed {threshold:.1f}% move threshold",
        f"• <b>Current Price:</b> {currency}{price:,.2f}",
        f"• <b>Intraday Change:</b> <code>{arrow} {change_pct:+.2f}%</code>",
        f"• <b>Verified Sentiment:</b> {s_emoji} {s_label}",
    ]

    if ai_reason:
        lines.append(f"\n🤖 <b>AI Catalyst Breakdown:</b>\n<i>{ai_reason}</i>")

    lines.append(f"\n{DIVIDER}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 4. FII / DII Institutional Flows (4:00 PM)
# ─────────────────────────────────────────────────────────────────────────────

def build_fii_dii_card(data: dict, ai_comment: str = "") -> str:
    now = _now_ist("%a, %d %b %Y")
    fii = data.get("fii_net", 0)
    dii = data.get("dii_net", 0)
    net = data.get("net_total", 0)
    sign = lambda v: "+" if v >= 0 else ""

    lines = [
        f"🏦 <b>FII / DII INSTITUTIONAL FLOWS</b>",
        f"📅 <i>NSE India Cash Market • {now}</i>",
        DIVIDER,
        f"\n• <b>FII Net:</b> <code>{sign(fii)}₹{abs(fii):,.0f} Cr</code> ({data.get('fii_label','')})",
        f"• <b>DII Net:</b> <code>{sign(dii)}₹{abs(dii):,.0f} Cr</code> ({data.get('dii_label','')})",
        f"• <b>Net Institutional Impact:</b> <code>{sign(net)}₹{abs(net):,.0f} Cr</code>",
    ]

    if ai_comment:
        lines.append(f"\n🤖 <b>Market Implication:</b>\n<i>{ai_comment}</i>")

    lines.append(f"\n{DIVIDER}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Evening Global Wrap (8:00 PM)
# ─────────────────────────────────────────────────────────────────────────────

def build_evening_card(
    indices: dict,
    crypto: list[dict],
    poly_markets: list[dict],
    ai_summary: str,
) -> str:
    now = _now_ist("%a, %d %b %Y • 8:00 PM IST")
    lines = [
        f"🌆 <b>EVENING GLOBAL WRAP</b>",
        f"📅 <i>{now}</i>",
        DIVIDER,
        "\n🇮🇳 <b>India Market Closing</b>",
    ]

    for label in ("Nifty 50", "Sensex"):
        d = indices.get(label)
        if d:
            lines.append(f"• <b>{label}:</b> ₹{d['price']:,.2f} <code>{_fmt_pct(d['change_pct'], d['arrow'])}</code>")

    lines.append("\n🇺🇸 <b>Wall Street & Global (Live)</b>")
    for key, name in [("S&P Fut", "S&P 500"), ("Nasdaq Fut", "Nasdaq"), ("Dow Fut", "Dow Jones")]:
        d = indices.get(key)
        if d:
            lines.append(f"• <b>{name}:</b> ${d['price']:,.2f} <code>{_fmt_pct(d['change_pct'], d['arrow'])}</code>")

    if crypto:
        lines.append("\n🪙 <b>Crypto EOD Status</b>")
        for c in crypto[:2]:
            inr = c.get("inr_fmt", f"₹{c['inr']:,.0f}")
            lines.append(f"• <b>{c['symbol']}:</b> {inr} (${c['usd']:,.0f}) <code>{_fmt_pct(c['change_pct'], c['arrow'])}</code>")

    if poly_markets:
        lines.append("\n🎲 <b>Polymarket Probabilities</b>")
        for m in poly_markets[:3]:
            q = m["question"]
            if len(q) > 65:
                q = q[:62] + "..."
            lines.append(f"• {q}\n  <i>Odds: <b>{m['yes_pct']:.0f}% YES</b></i>")

    if ai_summary:
        lines.append(f"\n🤖 <b>AI Day-End Synthesis:</b>\n{ai_summary}")

    lines.append(f"\n{DIVIDER}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Macro Calendar Reminder
# ─────────────────────────────────────────────────────────────────────────────

def build_macro_reminder_card(events: list[dict]) -> str:
    now = _now_ist("%a, %d %b")
    lines = [
        f"🏛️ <b>MACROECONOMIC RADAR</b>",
        f"📅 <i>Upcoming Events • {now}</i>",
        DIVIDER,
    ]

    for e in events:
        lines.append(f"\n⚠️ <b>{e['name']}</b>")
        lines.append(f"• <b>Date & Time:</b> {e.get('date','')} at {e.get('time_ist','')}")
        if e.get("note"):
            lines.append(f"• <b>Potential Impact:</b> <i>{e['note']}</i>")

    lines.append(f"\n{DIVIDER}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Weekly Recap (Sunday 9:00 AM)
# ─────────────────────────────────────────────────────────────────────────────

def build_weekly_card(
    indices_weekly: dict,
    stocks_weekly: dict,
    crypto_weekly: list[dict],
    commodities_weekly: dict,
    ai_review: str,
) -> str:
    lines = [
        f"📅 <b>WEEKLY MARKET RECAP</b>",
        f"📅 <i>{_now_ist('%d %b %Y')}</i>",
        DIVIDER,
        "\n🇮🇳 <b>Major Indices (Weekly % Change)</b>",
    ]

    for label, d in indices_weekly.items():
        if d:
            lines.append(f"• <b>{label}:</b> <code>{_fmt_pct(d['change_pct'], d['arrow'])}</code>")

    if stocks_weekly:
        lines.append("\n📈 <b>Watchlist Performance This Week</b>")
        sorted_stocks = sorted(
            stocks_weekly.items(),
            key=lambda x: (x[1] or {}).get("change_pct", 0),
            reverse=True,
        )
        for sym, d in sorted_stocks[:6]:
            if d:
                clean_sym = sym.replace(".NS", "").replace(".BO", "")
                lines.append(f"• <b>{clean_sym}:</b> <code>{_fmt_pct(d['change_pct'], d['arrow'])}</code>")

    if commodities_weekly:
        lines.append("\n🥇 <b>Commodities This Week</b>")
        for label, d in commodities_weekly.items():
            if d:
                lines.append(f"• <b>{label}:</b> <code>{_fmt_pct(d['change_pct'], d['arrow'])}</code>")

    if ai_review:
        lines.append(f"\n🤖 <b>AI Strategic Outlook for Next Week:</b>\n{ai_review}")

    lines.append(f"\n{DIVIDER}")
    return "\n".join(lines)
