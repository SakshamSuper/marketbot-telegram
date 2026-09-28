"""
config.py — Centralised configuration for v2 AI-powered Telegram bot.
All modules import from here; never read os.environ directly elsewhere.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ──────────────────────────────────────────────────────────────────
BOT_TOKEN: str = os.environ["BOT_TOKEN"]
CHAT_ID: str = os.environ["CHAT_ID"]

# ── Gemini AI ─────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# ── Webhook Security ──────────────────────────────────────────────────────────
WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "changeme")

# ── Indian Stock Watchlist (NSE suffix .NS, BSE suffix .BO) ───────────────────
INDIAN_STOCKS: list[str] = [
    s.strip()
    for s in os.getenv(
        "INDIAN_STOCKS", "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS"
    ).split(",")
    if s.strip()
]

# ── US Stock Watchlist ────────────────────────────────────────────────────────
US_STOCKS: list[str] = [
    s.strip()
    for s in os.getenv("US_STOCKS", "AAPL,TSLA,GOOGL,MSFT,NVDA").split(",")
    if s.strip()
]

# ── Crypto Watchlist (CoinGecko IDs) ─────────────────────────────────────────
CRYPTO_IDS: list[str] = [
    c.strip()
    for c in os.getenv("CRYPTO_IDS", "bitcoin,ethereum,solana").split(",")
    if c.strip()
]

# ── Market Indices ────────────────────────────────────────────────────────────
INDICES: dict[str, str] = {
    "Nifty 50": "^NSEI",
    "Sensex": "^BSESN",
    "India VIX": "^INDIAVIX",
    "S&P Fut": "ES=F",
    "Dow Fut": "YM=F",
    "Nasdaq Fut": "NQ=F",
}

# ── Currency Pairs ────────────────────────────────────────────────────────────
CURRENCY_PAIRS: dict[str, str] = {
    "USD/INR": "USDINR=X",
    "EUR/INR": "EURINR=X",
    "GBP/INR": "GBPINR=X",
}

# ── Smart Alert Settings ──────────────────────────────────────────────────────
PRICE_CHANGE_THRESHOLD_PCT: float = float(os.getenv("PRICE_CHANGE_THRESHOLD_PCT", "2.0"))
ALERT_COOLDOWN_HOURS: float = float(os.getenv("ALERT_COOLDOWN_HOURS", "4.0"))

# ── Scheduling (IST times — Asia/Kolkata) ─────────────────────────────────────
SCHEDULE_PREMARKET_HOUR: int = int(os.getenv("SCHEDULE_PREMARKET_HOUR", "8"))
SCHEDULE_PREMARKET_MIN: int = int(os.getenv("SCHEDULE_PREMARKET_MIN", "0"))
SCHEDULE_OPEN_HOUR: int = int(os.getenv("SCHEDULE_OPEN_HOUR", "9"))
SCHEDULE_OPEN_MIN: int = int(os.getenv("SCHEDULE_OPEN_MIN", "15"))
SCHEDULE_EVENING_HOUR: int = int(os.getenv("SCHEDULE_EVENING_HOUR", "20"))
SCHEDULE_EVENING_MIN: int = int(os.getenv("SCHEDULE_EVENING_MIN", "0"))

# Smart alert polling interval (seconds)
ALERT_POLL_INTERVAL: int = int(os.getenv("ALERT_POLL_INTERVAL", "300"))  # 5 min

# ── News Preferences ──────────────────────────────────────────────────────────
NEWS_MAX_PER_SOURCE: int = int(os.getenv("NEWS_MAX_PER_SOURCE", "3"))

# ── Polymarket ────────────────────────────────────────────────────────────────
POLYMARKET_TOP_N: int = int(os.getenv("POLYMARKET_TOP_N", "5"))

# ── Server ────────────────────────────────────────────────────────────────────
PORT: int = int(os.getenv("PORT", "8080"))

# ── In-memory stores (shared mutable state) ───────────────────────────────────
# Price alert thresholds set by user via /alert command
# Format: { "RELIANCE.NS": [{"direction": "above"|"below", "price": 2500.0}] }
PRICE_ALERTS: dict[str, list[dict]] = {}

# Last seen prices for smart alert engine (deduplication)
# Format: { "RELIANCE.NS": {"price": 2490.0, "last_alert_ts": 1234567890.0} }
LAST_PRICE_SNAPSHOT: dict[str, dict] = {}
