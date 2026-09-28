"""
ai/gemini_client.py
───────────────────
Robust Gemini API wrapper with:
 - Exponential backoff retries
 - Rate-limit handling
 - Timeout protection
 - Structured JSON response parsing
"""

import time
import logging
from google import genai
from google.genai import types
import config

logger = logging.getLogger(__name__)

# Initialise the Gemini client once at import time
_client = genai.Client(api_key=config.GEMINI_API_KEY)

# Generation config – deterministic outputs for financial data
_GENERATION_CONFIG = types.GenerateContentConfig(
    temperature=0.2,
    max_output_tokens=512,
)

_RETRY_DELAYS = [2, 5, 10]  # seconds between retries


def ask(prompt: str, *, max_tokens: int = 512, temperature: float = 0.2) -> str:
    """
    Send a prompt to Gemini and return the text response.
    Retries up to 3 times with exponential backoff on transient errors.

    Returns empty string on permanent failure (caller should handle gracefully).
    """
    cfg = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
    )

    last_error: Exception | None = None
    for attempt, delay in enumerate([0] + _RETRY_DELAYS, start=1):
        if delay:
            time.sleep(delay)
        try:
            response = _client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt,
                config=cfg,
            )
            text = response.text.strip() if response.text else ""
            if text:
                logger.debug("Gemini OK on attempt %d", attempt)
                return text
            logger.warning("Gemini returned empty response on attempt %d", attempt)
        except Exception as exc:
            last_error = exc
            logger.warning("Gemini attempt %d failed: %s", attempt, exc)

    logger.error("Gemini failed after %d attempts. Last error: %s", len(_RETRY_DELAYS) + 1, last_error)
    return ""


def ask_json(prompt: str, *, max_tokens: int = 512) -> dict | list | None:
    """
    Ask Gemini for a JSON response. Strips markdown fences before parsing.
    Returns None on parse failure.
    """
    import json
    import re

    raw = ask(prompt, max_tokens=max_tokens)
    if not raw:
        return None

    # Strip ```json ... ``` markdown fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("Gemini JSON parse error: %s | raw=%r", exc, raw[:200])
        return None
