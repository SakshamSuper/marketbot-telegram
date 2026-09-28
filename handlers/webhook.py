"""
handlers/webhook.py
────────────────────
Flask HTTP server providing a /trigger endpoint.
Lets any external app or script send a Telegram message to you.

Usage:
  POST http://your-app.railway.app/trigger
  Headers: Content-Type: application/json
  Body: {"message": "Deploy succeeded! 🚀", "secret": "your_secret"}
"""

import logging
import threading
from flask import Flask, request, jsonify
import config

logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

# Bot instance is injected at startup
_bot_ref = None
_chat_id_ref = None


def init(bot, chat_id: str) -> None:
    """Inject bot and chat_id before starting the Flask server."""
    global _bot_ref, _chat_id_ref
    _bot_ref = bot
    _chat_id_ref = chat_id


@flask_app.route("/health", methods=["GET"])
def health():
    """Health check for Railway uptime monitoring."""
    return jsonify({"status": "ok", "bot": "MarketBot"}), 200


@flask_app.route("/trigger", methods=["POST"])
def trigger():
    """Receive a POST request and forward the message to Telegram."""
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    # Secret validation
    if data.get("secret") != config.WEBHOOK_SECRET:
        logger.warning("Webhook: invalid secret from %s", request.remote_addr)
        return jsonify({"error": "Unauthorized"}), 401

    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message field is required"}), 400

    if len(message) > 4096:
        message = message[:4090] + "\n<i>...truncated</i>"

    if _bot_ref is None:
        logger.error("Webhook: bot not initialised")
        return jsonify({"error": "Bot not ready"}), 503

    # Send via asyncio in a thread-safe way
    import asyncio

    async def _send():
        await _bot_ref.send_message(
            chat_id    = _chat_id_ref,
            text       = f"🔗 <b>WEBHOOK TRIGGER</b>\n{message}",
            parse_mode = "HTML",
        )

    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_send())
        loop.close()
        logger.info("Webhook message sent successfully")
        return jsonify({"status": "sent"}), 200
    except Exception as exc:
        logger.error("Webhook send failed: %s", exc)
        return jsonify({"error": str(exc)}), 500


def run_flask(port: int) -> None:
    """Start Flask in a background daemon thread."""
    def _run():
        flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

    thread = threading.Thread(target=_run, daemon=True, name="flask-webhook")
    thread.start()
    logger.info("Webhook server started on port %d", port)
