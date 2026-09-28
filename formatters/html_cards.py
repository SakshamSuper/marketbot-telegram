"""
formatters/html_cards.py
─────────────────────────
Builds all Telegram HTML-formatted message cards.
Uses Telegram's supported HTML tags: <b>, <i>, <code>, <pre>
Never uses unsupported tags — Telegram will silently drop them.

All builders are pure functions → easy to unit-test.
"""

from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")

LINE = "━" * 30
THIN = "─" * 30


def _now_ist(fmt: str = "%a, %d %b  %I:%M %p IST") -> str:
    return datetime.now(IST).strftime(fmt)


def _pct_str(pct: float, arrow: str = "") -> str:
    sign = "+" if pct >= 0 else ""
    return f"{arrow} {sign}{pct:.2f}%".strip()


def _price_line(label: str, data: dict | None, currency: str = "") -> str:
    if not data:
        return f"  {label:<18} <i>unavailable</i>"
    cur = currency or data.get("currency", "")
    price = f"{cur}{data['price']:,.2f}"
    pct   = _pct_str(data["change_pct"], data["arrow"])
    return f"  <b>{label:<14}</b>  {price}  <i>{pct}</i>"


# ─────────────────────────────────────────────────────────────────────────────
# 1. Pre-Market Digest (8:00 AM)
# ─────────────────────────────────────────────────────────────────────────────

def build_premarket_card(
    indices:     dict,
    crypto:      list[dict],
    commodities: dict,
    currency:    dict,
    articles:    list[dict],     # [{"source", "title", "sentiment": {...}}]
    ai_summary:  str,
    ai_mood:     dict,           # {"emoji", "label", "reason"}
    macro_events: list[dict],    # upcoming events today
) -> str:
    now = _now_ist("%a, %d %b %Y")
    lines = [
        f"{LINE}",
        f"📊 <b>PRE-MARKET DIGEST</b>  |  {now}",
        f"{LINE}",
    ]

    # Indices
    lines.append("\n🇮🇳 <b>INDIA INDICES</b> <i>(prev close)</i>")
    for label in ("Nifty 50", "Sensex", "India VIX"):
        d = indices.get(label)
        lines.append(_price_line(label, d))

    lines.append("\n🇺🇸 <b>US FUTURES</b>")
    for label in ("S&P Fut", "Dow Fut", "Nasdaq Fut"):
        d = indices.get(label)
        lines.append(_price_line(label, d, "$"))

    # Crypto
    if crypto:
        lines.append("\n🪙 <b>CRYPTO</b> <i>(24h change)</i>")
        for c in crypto[:3]:
            inr   = c.get("inr_fmt", f"₹{c['inr']:,.0f}")
            pct   = _pct_str(c["change_pct"], c["arrow"])
            lines.append(f"  <b>{c['symbol']:<6}</b>  {inr}  <i>{pct}</i>")

    # Commodities
    c_gold   = commodities.get("Gold")
    c_silver = commodities.get("Silver")
    c_crude  = commodities.get("Crude")
    if any([c_gold, c_silver, c_crude]):
        lines.append("\n🥇 <b>COMMODITIES</b>")
        if c_gold:
            lines.append(f"  <b>Gold  </b>  {c_gold.get('inr_display', '')}  "
                         f"<i>{_pct_str(c_gold['change_pct'], c_gold['arrow'])}</i>")
        if c_silver:
            lines.append(f"  <b>Silver</b>  {c_silver.get('inr_display', '')}  "
                         f"<i>{_pct_str(c_silver['change_pct'], c_silver['arrow'])}</i>")
        if c_crude:
            lines.append(f"  <b>Crude </b>  ${c_crude['usd']:.2f}/bbl  "
                         f"<i>{_pct_str(c_crude['change_pct'], c_crude['arrow'])}</i>")

    # Currency
    usd_inr = currency.get("USD/INR")
    if usd_inr:
        lines.append(f"\n💱  <b>USD/INR</b>  {usd_inr['rate']:.2f}  "
                     f"<i>{_pct_str(usd_inr['change_pct'], usd_inr['arrow'])}</i>")

    # Macro events today
    if macro_events:
        lines.append("\n🏛️ <b>TODAY'S EVENTS</b>")
        for e in macro_events:
            lines.append(f"  ⚠️  {e['name']}  <i>{e.get('time_ist','')}</i>")

    # AI Mood
    if ai_mood:
        lines.append(
            f"\n🤖 <b>AI MOOD</b>  {ai_mood['emoji']} <b>{ai_mood['label']}</b>\n"
            f"<i>{ai_mood.get('reason', '')}</i>"
        )

    # AI News Summary
    if ai_summary:
        lines.append(f"\n📋 <b>AI MARKET BRIEF</b>\n<i>{ai_summary}</i>")

    # Top Headlines with sentiment
    if articles:
        lines.append(f"\n📰 <b>TOP HEADLINES</b>")
        for art in articles[:5]:
            s    = art.get("sentiment", {})
            emoji = s.get("emoji", "🟡")
            conf  = " <i>(uncertain)</i>" if s.get("confidence") == "LOW" else ""
            src   = art.get("source", "")
            title = art.get("title", "")[:80]
            lines.append(f"  {emoji} <i>[{src}]</i> {title}{conf}")

    lines.append(f"\n{LINE}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Market Open Flash (9:15 AM)
# ─────────────────────────────────────────────────────────────────────────────

def build_market_open_card(
    indices:     dict,
    top_movers:  list[dict],   # [{"symbol", "change_pct", "arrow"}]
    ai_comment:  str,
) -> str:
    now = _now_ist("%I:%M %p IST")
    lines = [
        f"{LINE}",
        f"📈 <b>MARKET OPEN FLASH</b>  |  {now}",
        f"{LINE}",
    ]

    lines.append("\n🇮🇳 <b>OPENING SNAPSHOT</b>")
    for label in ("Nifty 50", "Sensex"):
        d = indices.get(label)
        if d:
            gap = "Gap Up 🟢" if d["change_pct"] > 0.1 else ("Gap Down 🔴" if d["change_pct"] < -0.1 else "Flat 🟡")
            lines.append(f"  <b>{label:<12}</b>  {d['price']:,.2f}  "
                         f"<i>{_pct_str(d['change_pct'], d['arrow'])}  ({gap})</i>")

    if top_movers:
        lines.append("\n🔥 <b>TOP MOVERS</b>")
        for m in top_movers[:5]:
            pct = m.get("change_pct", 0)
            sym = m.get("symbol", "")
            arrow = "▲" if pct >= 0 else "▼"
            flag = "  ⚡" if abs(pct) > 3 else ""
            lines.append(f"  {arrow} <b>{sym}</b>  <i>{pct:+.1f}%</i>{flag}")

    if ai_comment:
        lines.append(f"\n💬 <i>{ai_comment}</i>")

    lines.append(f"\n{LINE}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Smart Price Alert
# ─────────────────────────────────────────────────────────────────────────────

def build_alert_card(
    symbol:      str,
    price:       float,
    change_pct:  float,
    currency:    str,
    ai_reason:   str,
    sentiment:   dict,          # from sentiment.analyse()
    threshold:   float = 2.0,
) -> str:
    now   = _now_ist("%I:%M %p IST")
    arrow = "▲" if change_pct >= 0 else "▼"
    direction = "📈" if change_pct >= 0 else "📉"
    s_emoji = sentiment.get("emoji", "🟡")
    conf = sentiment.get("confidence", "")
    conf_note = "  <i>(low confidence)</i>" if conf == "LOW" else ""

    lines = [
        f"{LINE}",
        f"⚡ <b>SMART ALERT</b>  |  {now}",
        f"{LINE}",
        f"\n{direction} <b>{symbol}</b>  {currency}{price:,.2f}  "
        f"<b>{arrow} {change_pct:+.2f}%</b>",
        f"Threshold crossed: &gt;{threshold:.0f}% move",
        f"Sentiment: {s_emoji} {sentiment.get('label','')}{conf_note}",
    ]

    if ai_reason:
        lines.append(f"\n🤖 <b>AI Analysis:</b>\n<i>{ai_reason}</i>")

    lines.append(f"\n{LINE}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 4. FII/DII Flows Card (4:00 PM)
# ─────────────────────────────────────────────────────────────────────────────

def build_fii_dii_card(data: dict, ai_comment: str = "") -> str:
    now = _now_ist("%a %d %b")
    lines = [
        f"{LINE}",
        f"🏦 <b>FII / DII FLOWS</b>  |  {now}",
        f"{LINE}",
    ]

    fii = data.get("fii_net", 0)
    dii = data.get("dii_net", 0)
    net = data.get("net_total", 0)
    sign = lambda v: "+" if v >= 0 else ""

    lines += [
        f"\n  <b>FII</b>  {sign(fii)}₹{abs(fii):,.0f} Cr  —  {data.get('fii_label','')}",
        f"  <b>DII</b>  {sign(dii)}₹{abs(dii):,.0f} Cr  —  {data.get('dii_label','')}",
        f"  <b>Net</b>  {sign(net)}₹{abs(net):,.0f} Cr",
    ]

    if ai_comment:
        lines.append(f"\n🤖 <i>{ai_comment}</i>")

    lines.append(f"\n{LINE}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Evening Global Wrap (8:00 PM)
# ─────────────────────────────────────────────────────────────────────────────

def build_evening_card(
    indices:     dict,
    crypto:      list[dict],
    poly_markets: list[dict],
    ai_summary:  str,
) -> str:
    now = _now_ist("%a, %d %b %Y")
    lines = [
        f"{LINE}",
        f"🌆 <b>EVENING WRAP</b>  |  {now}",
        f"{LINE}",
    ]

    # India Close
    lines.append("\n🇮🇳 <b>INDIA CLOSE</b>")
    for label in ("Nifty 50", "Sensex"):
        d = indices.get(label)
        lines.append(_price_line(label, d))

    # US Live
    lines.append("\n🇺🇸 <b>US MARKETS</b> <i>(live)</i>")
    for label in ("S&P Fut", "Dow Fut", "Nasdaq Fut"):
        d = indices.get(label)
        display_label = label.replace(" Fut", "")
        lines.append(_price_line(display_label, d, "$"))

    # Crypto EOD
    if crypto:
        lines.append("\n🪙 <b>CRYPTO EOD</b>")
        for c in crypto[:3]:
            inr = c.get("inr_fmt", f"₹{c['inr']:,.0f}")
            lines.append(
                f"  <b>{c['symbol']:<6}</b>  ${c['usd']:,.0f}  |  {inr}  "
                f"<i>{_pct_str(c['change_pct'], c['arrow'])}</i>"
            )

    # Polymarket
    if poly_markets:
        lines.append("\n🎲 <b>POLYMARKET ODDS</b>")
        for m in poly_markets[:5]:
            q   = m["question"][:55]
            pct = m["yes_pct"]
            bar = "🟢" if pct >= 60 else ("🔴" if pct <= 40 else "🟡")
            lines.append(f"  {bar} {q}\n       <i>{pct:.0f}% YES</i>")

    # AI EOD Summary
    if ai_summary:
        lines.append(f"\n🤖 <b>AI EOD SUMMARY</b>\n<i>{ai_summary}</i>")

    lines.append(f"\n{LINE}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Macro Calendar Reminder
# ─────────────────────────────────────────────────────────────────────────────

def build_macro_reminder_card(events: list[dict]) -> str:
    now = _now_ist("%a, %d %b")
    lines = [
        f"{LINE}",
        f"🏛️ <b>UPCOMING MACRO EVENTS</b>  |  {now}",
        f"{LINE}",
    ]

    for e in events:
        lines += [
            f"\n⚠️  <b>{e['name']}</b>",
            f"    📅  {e.get('date','')}  |  {e.get('time_ist','')}",
        ]
        if e.get("note"):
            lines.append(f"    <i>{e['note']}</i>")

    lines.append(f"\n{LINE}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Weekly Digest (Sunday 9 AM)
# ─────────────────────────────────────────────────────────────────────────────

def build_weekly_card(
    indices_weekly:  dict,     # {label: {"change_pct", "arrow"}}
    stocks_weekly:   dict,     # {symbol: {"change_pct", "arrow"}}
    crypto_weekly:   list[dict],
    commodities_weekly: dict,
    ai_review:       str,
) -> str:
    from datetime import timedelta
    today = datetime.now(IST)
    week_start = (today - timedelta(days=today.weekday())).strftime("%d %b")
    week_end   = today.strftime("%d %b")

    lines = [
        f"{LINE}",
        f"📅 <b>WEEKLY RECAP</b>  |  Week of {week_start}–{week_end}",
        f"{LINE}",
    ]

    # Indices weekly
    lines.append("\n🇮🇳 <b>INDICES</b> <i>(weekly)</i>")
    for label, d in indices_weekly.items():
        if d:
            lines.append(f"  <b>{label:<12}</b>  <i>{_pct_str(d['change_pct'], d['arrow'])}</i>")

    # Your watchlist weekly
    if stocks_weekly:
        lines.append("\n📈 <b>YOUR WATCHLIST</b> <i>(weekly change)</i>")
        sorted_stocks = sorted(stocks_weekly.items(), key=lambda x: (x[1] or {}).get("change_pct", 0), reverse=True)
        for sym, d in sorted_stocks:
            if d:
                flag = "  🔴" if d["change_pct"] < -3 else ("  🔥" if d["change_pct"] > 4 else "")
                lines.append(f"  <b>{sym:<16}</b>  <i>{_pct_str(d['change_pct'], d['arrow'])}</i>{flag}")

    # Commodities weekly
    if commodities_weekly:
        lines.append("\n🥇 <b>COMMODITIES</b> <i>(weekly)</i>")
        for label, d in commodities_weekly.items():
            if d:
                lines.append(f"  <b>{label:<8}</b>  <i>{_pct_str(d['change_pct'], d['arrow'])}</i>")

    # Crypto weekly
    if crypto_weekly:
        lines.append("\n🪙 <b>CRYPTO</b> <i>(weekly)</i>")
        for c in crypto_weekly[:3]:
            flag = "  🔥" if c["change_pct"] > 8 else ""
            lines.append(f"  <b>{c['symbol']:<6}</b>  <i>{_pct_str(c['change_pct'], c['arrow'])}</i>{flag}")

    # AI Review
    if ai_review:
        lines.append(f"\n🤖 <b>AI WEEK IN REVIEW</b>\n<i>{ai_review}</i>")

    lines.append(f"\n{LINE}")
    return "\n".join(lines)
