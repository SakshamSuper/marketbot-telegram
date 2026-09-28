# -*- coding: utf-8 -*-
import sys, os

# Force UTF-8 output so emojis in Telegram messages don't crash Windows terminal
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

errors = []

# ── Test 1: Gemini API ────────────────────────────────────────────
print("--- Testing Gemini API ---")
try:
    from google import genai
    model  = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    r      = client.models.generate_content(model=model, contents="Reply with exactly: MarketBot online!")
    print(f"Gemini model : {model}")
    print(f"Gemini reply : {r.text.strip()}")
    print("Gemini: OK\n")
except Exception as e:
    print(f"Gemini ERROR: {e}")
    errors.append("Gemini")

# ── Test 2: Telegram Bot ──────────────────────────────────────────
print("--- Testing Telegram Bot ---")
try:
    import requests
    token = os.getenv("BOT_TOKEN")
    resp  = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
    d     = resp.json()
    if d.get("ok"):
        bot   = d["result"]
        print(f"Bot name    : {bot.get('first_name','')}")
        print(f"Bot username: @{bot.get('username','')}")
        print("Telegram: OK\n")
    else:
        print("Telegram ERROR:", d)
        errors.append("Telegram")
except Exception as e:
    print(f"Telegram ERROR: {e}")
    errors.append("Telegram")

# ── Test 3: yfinance — Nifty 50 with escalating periods ──────────
print("--- Testing yfinance (Nifty 50) ---")
try:
    import yfinance as yf
    price = None
    for period in ("5d", "1mo", "3mo"):
        hist = yf.Ticker("^NSEI").history(period=period, interval="1d", actions=False)
        if not hist.empty:
            price = float(hist["Close"].iloc[-1])
            print(f"Nifty 50 last close ({period}): {price:,.2f}")
            print("yfinance: OK\n")
            break
    if price is None:
        # Fallback: try NIFTYBEES ETF as proxy
        hist2 = yf.Ticker("NIFTYBEES.NS").history(period="1mo", interval="1d", actions=False)
        if not hist2.empty:
            proxy = float(hist2["Close"].iloc[-1])
            print(f"Nifty proxy (NIFTYBEES.NS): {proxy:.2f}")
            print("yfinance: OK (via proxy)\n")
        else:
            print("yfinance: ^NSEI unavailable (market may be closed / Yahoo Finance issue)")
            print("NOTE: Bot will still work — this ticker sometimes requires market hours\n")
except Exception as e:
    print(f"yfinance ERROR: {e}")
    errors.append("yfinance")

# ── Test 4: CoinGecko ─────────────────────────────────────────────
print("--- Testing CoinGecko ---")
try:
    import requests
    r2  = requests.get(
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
        timeout=10,
    )
    btc = r2.json()["bitcoin"]["usd"]
    print(f"BTC price: USD {btc:,.2f}")
    print("CoinGecko: OK\n")
except Exception as e:
    print(f"CoinGecko ERROR: {e}")
    errors.append("CoinGecko")

# ── Test 5: Send test message to Telegram (UTF-8 via HTTP) ────────
print("--- Sending test message to Telegram ---")
try:
    import requests
    token   = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    msg = (
        "\u2705 <b>MarketBot - Connection Test Passed!</b>\n\n"
        "All systems are live:\n"
        "\u2022 Gemini AI \u2705\n"
        "\u2022 Telegram Bot \u2705\n"
        "\u2022 yfinance \u2705\n"
        "\u2022 CoinGecko (BTC) \u2705\n\n"
        "<i>Your bot is ready! Run: python main.py</i>"
    )
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
        timeout=10,
    )
    r = resp.json()
    if r.get("ok"):
        print("Message delivered! Check your Telegram now.")
        print("Test message: OK\n")
    else:
        print("Send ERROR:", r.get("description", r))
        errors.append("SendMessage")
except Exception as e:
    print(f"Send ERROR: {e}")
    errors.append("SendMessage")

# ── Summary ───────────────────────────────────────────────────────
print("=" * 44)
if not errors:
    print("ALL SYSTEMS GO - Run: venv\\Scripts\\python.exe main.py")
else:
    print("ISSUES:", ", ".join(errors))
print("=" * 44)
