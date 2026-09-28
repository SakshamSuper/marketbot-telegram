"""
main.py
────────
MarketBot entry point.
Initialises the Telegram Application, registers handlers and jobs,
starts the Flask webhook server, then begins polling.
"""

import logging
import sys
import asyncio

from telegram.ext import Application

import config
from handlers import commands, webhook
from scheduler import register_jobs

# ── Logging setup ─────────────────────────────────────────────────────────────

logging.basicConfig(
    format  = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
    level   = logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

# Reduce noise from third-party libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("yfinance").setLevel(logging.WARNING)

logger = logging.getLogger("main")


def main() -> None:
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("  MarketBot v2  —  Starting up...")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("Model: %s", config.GEMINI_MODEL)
    logger.info("Chat ID: %s", config.CHAT_ID)
    logger.info("Indian stocks: %s", config.INDIAN_STOCKS)
    logger.info("US stocks: %s", config.US_STOCKS)
    logger.info("Crypto IDs: %s", config.CRYPTO_IDS)
    logger.info("Alert threshold: %.1f%%  |  Cooldown: %.0fh", config.PRICE_CHANGE_THRESHOLD_PCT, config.ALERT_COOLDOWN_HOURS)

    # Build the Telegram Application
    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .build()
    )

    # Register all /command handlers
    commands.register(app)
    logger.info("Command handlers registered")

    # Register scheduled jobs
    register_jobs(app)
    logger.info("Scheduled jobs registered")

    # Start Flask webhook server in background thread
    webhook.init(app.bot, config.CHAT_ID)
    webhook.run_flask(config.PORT)
    logger.info("Webhook server running on port %d", config.PORT)

    logger.info("Bot is online — polling for messages...")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Python 3.12+ no longer auto-creates an event loop — set one explicitly
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Start polling — blocks until SIGINT/SIGTERM
    app.run_polling(
        poll_interval        = 1,
        timeout              = 20,
        drop_pending_updates = True,
    )


if __name__ == "__main__":
    main()
