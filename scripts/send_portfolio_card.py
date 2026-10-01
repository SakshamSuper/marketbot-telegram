import sys, os
sys.path.insert(0, ".")
import requests
from dotenv import load_dotenv
load_dotenv()
from fetchers import portfolio

summary = portfolio.get_live_portfolio_summary()

total_pnl = summary["total_pnl"]
sign = "+" if total_pnl >= 0 else ""
pnl_arrow = "▲" if total_pnl >= 0 else "▼"
pct = summary["total_pnl_pct"]
pnl_badge = f"<code>{pnl_arrow} {sign}₹{abs(total_pnl):,.2f} ({sign}{pct}%)</code>"

lines = [
    "💼 <b>YOUR PORTFOLIO INTELLIGENCE</b>",
    f"👤 <i>Client: {summary.get('client_name', 'Saksham Aggarwal')} • {summary['holdings_count']} Holdings</i>",
    "━━━━━━━━━━━━━━━━━━━━",
    f"\n💰 <b>Invested Value:</b> ₹{summary['invested_value']:,.2f}",
    f"📊 <b>Current Value:</b> ₹{summary['current_value']:,.2f}",
    f"📈 <b>Unrealised P&L:</b> {pnl_badge}",
]

if summary.get("top_gainers"):
    lines.append("\n🟢 <b>Top Profit Contributors</b>")
    for g in summary["top_gainers"]:
        name = g["name"][:22]
        lines.append(f"• <b>{name}:</b> +₹{g['pnl']:,.0f} <code>(+{g['pnl_pct']}%)</code>")

if summary.get("top_draggers"):
    lines.append("\n🔴 <b>Major Loss Draggers</b>")
    for d in summary["top_draggers"]:
        name = d["name"][:22]
        lines.append(f"• <b>{name}:</b> -₹{abs(d['pnl']):,.0f} <code>({d['pnl_pct']}%)</code>")

lines.append("\n⚖️ <b>Portfolio Allocation & Risk Analysis</b>")
lines.append("• <b>Vedanta Group (~45%):</b> ₹2.58L in VEDL + demerged units. High metal price sensitivity.")
lines.append("• <b>Silver ETFs (~28%):</b> ₹1.58L across Tata, Nippon & HDFC Silver. Silver commodity hedge.")
lines.append("• <b>Banking & Finance (~16%):</b> ₹92k in SBI, BSE Ltd, Axis Bank & HDFC Bank.")
lines.append("• <b>Defence & Drones (~8%):</b> ₹46k in Drone Destination, Mazdock & BEL.")

lines.append("\n💡 <i>Send /portfolio anytime in this chat to see live updates.</i>")
lines.append("━━━━━━━━━━━━━━━━━━━━")

card_text = "\n".join(lines)

token = os.getenv("BOT_TOKEN")
chat_id = os.getenv("CHAT_ID")

resp = requests.post(
    f"https://api.telegram.org/bot{token}/sendMessage",
    json={"chat_id": chat_id, "text": card_text, "parse_mode": "HTML"},
    timeout=15,
)
print("Telegram Send Status:", resp.status_code, resp.json().get("ok"))
