# 🤖 MarketBot — AI-Powered Telegram Market Intelligence Bot

> Personalised market updates on Telegram. Tracks Indian (NSE/BSE) + US stocks, crypto, commodities, news, FII/DII flows, and macro events — with Gemini AI summaries and 4-layer sentiment analysis.

---

## ⚡ Features

| | Feature | Detail |
|---|---|---|
| 📊 | **Indian Indices** | Nifty 50, Sensex, India VIX |
| 🇺🇸 | **US Futures** | S&P 500, Dow, Nasdaq |
| 📈 | **NSE/BSE Stocks** | RELIANCE, TCS, INFY, HDFC, ICICI + more |
| 🌎 | **US Stocks** | AAPL, TSLA, GOOGL, MSFT, NVDA |
| 🪙 | **Crypto** | BTC, ETH, SOL in ₹ + USD |
| 🥇 | **Commodities** | MCX Gold (₹/10g), Silver (₹/kg), Crude ($/bbl) |
| 💱 | **Currency** | USD/INR, EUR/INR, GBP/INR |
| 📰 | **News** | ET, Moneycontrol, Mint, TOI, Bloomberg, Reuters RSS |
| 🤖 | **Gemini AI** | 3-line news digest + market mood score |
| 🟢🔴🟡 | **Sentiment** | 4-layer analysis (Gemini + keyword + agreement + confidence) |
| ⚡ | **Smart Alerts** | >2% moves only, 4hr cooldown, AI explanation |
| 🏦 | **FII/DII Flows** | NSE India daily institutional data |
| 🎲 | **Polymarket** | Top prediction market odds |
| 🏛️ | **Macro Calendar** | RBI, FOMC, CPI, GDP, NFP reminders |
| ⏰ | **IST Schedule** | 8AM / 9:15AM / 4PM / 8PM digests (weekdays) |
| 📅 | **Weekly Digest** | Sunday 9AM full week recap |

---

## 🚀 Quick Setup

### Step 1 — Get Your Keys (one-time, all free)

1. **Telegram Bot Token**
   - Open Telegram → message `@BotFather`
   - Type `/newbot` → follow prompts → copy token

2. **Your Chat ID**
   - Message `@userinfobot` on Telegram
   - Copy your numeric ID (e.g. `123456789`)

3. **Gemini API Key** (free, 1500 req/day)
   - Visit [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
   - Click "Create API Key" → copy

### Step 2 — Configure

```bash
cp .env.example .env
# Open .env and fill in BOT_TOKEN, CHAT_ID, GEMINI_API_KEY
```

### Step 3 — Run Locally

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Start the bot
python main.py
```

### Step 4 — Test

Send these commands to your bot on Telegram:
```
/start          → Welcome message
/price RELIANCE.NS  → NSE stock price
/price AAPL         → US stock price
/crypto btc         → BTC in ₹ + $
/indices            → Nifty/Sensex/VIX
/news               → AI headlines + sentiment
/mood               → Gemini market mood
/poly               → Polymarket odds
/commodities        → Gold/Silver/Crude
/fii                → FII/DII flows
/alert TCS.NS below 3500 → Set price alert
/remind 5 Test reminder  → Fires in 5 min
```

---

## ☁️ Deploy to Railway (Free, 24/7)

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Add Environment Variables in Railway dashboard (same as your `.env`)
4. Railway auto-detects `Procfile` → deploys → bot runs 24/7

---

## 🧠 Sentiment Layers

Every news headline goes through **4 verification layers**:

```
Layer 1 → Gemini AI:     Classify headline as BULLISH / BEARISH / NEUTRAL
Layer 2 → Keyword Rules: Match against ~80 financial keywords
Layer 3 → Agreement:     Compare Layer 1 & 2 results
Layer 4 → Confidence:
            HIGH   = both layers agree
            MEDIUM = one layer is NEUTRAL → trust the other
            LOW    = direct contradiction → mark as 🟡 UNCERTAIN
```

Badge in messages:
- `⚡` = HIGH confidence
- `❓` = LOW confidence (uncertain)
- No badge = MEDIUM confidence

---

## 🔗 Custom Webhook Trigger

Send messages to your Telegram from any app or script:

```bash
curl -X POST https://your-app.railway.app/trigger \
  -H "Content-Type: application/json" \
  -d '{"message": "🚀 Deploy succeeded!", "secret": "your_webhook_secret"}'
```

---

## 📁 Project Structure

```
telegram-notifier/
├── main.py               # Entry point
├── config.py             # All settings
├── scheduler.py          # IST-aware job scheduler
├── ai/
│   ├── gemini_client.py  # Gemini API (retries, JSON parsing)
│   ├── summariser.py     # News digest + market mood
│   └── sentiment.py      # 4-layer sentiment engine
├── fetchers/
│   ├── indices.py        # Nifty, Sensex, VIX, US Futures
│   ├── stocks.py         # NSE/BSE + US stocks
│   ├── crypto.py         # CoinGecko + INR conversion
│   ├── currency.py       # USD/INR, EUR/INR, GBP/INR
│   ├── news_rss.py       # 6 RSS feed sources
│   ├── polymarket.py     # Prediction market odds
│   ├── commodities.py    # Gold, Silver, Crude Oil
│   └── fii_dii.py        # NSE India institutional flows
├── formatters/
│   └── html_cards.py     # All 7 Telegram HTML card builders
├── alerts/
│   └── price_alert.py    # Smart alert engine (>2% threshold)
├── handlers/
│   ├── commands.py       # All /command handlers
│   └── webhook.py        # Flask POST /trigger endpoint
└── data/
    └── macro_calendar.json  # RBI/FOMC/CPI event dates
```

---

## 💰 Cost

**Total: ₹0 / month**

| Service | Cost |
|---|---|
| Telegram Bot API | Free |
| yfinance (stocks/indices) | Free |
| CoinGecko API | Free |
| RSS News Feeds | Free |
| NSE India FII/DII API | Free |
| Polymarket API | Free |
| Google Gemini API | Free (1500 req/day) |
| Railway hosting | Free hobby plan |
