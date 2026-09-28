"""
ai/sentiment.py
───────────────
Multi-layer sentiment analysis for financial headlines.

Layer 1  → Gemini AI classification (primary)
Layer 2  → Keyword-based rule engine (validator / fallback)
Layer 3  → Agreement check + confidence scoring
Layer 4  → Final verdict with emoji label

Confidence levels:
  HIGH   → Both layers agree               → use agreed label
  MEDIUM → One layer returned NEUTRAL      → use non-neutral layer
  LOW    → Layers disagree (Bull vs Bear)  → 🟡 NEUTRAL (uncertain)
"""

import re
import logging
from ai import gemini_client

logger = logging.getLogger(__name__)

# ── Emoji mapping ─────────────────────────────────────────────────────────────
SENTIMENT_EMOJI = {
    "BULLISH": "🟢",
    "BEARISH": "🔴",
    "NEUTRAL": "🟡",
}

# ── Layer 2: Keyword rule engine ──────────────────────────────────────────────
_BULLISH_KEYWORDS = {
    "rise", "rises", "risen", "rally", "rallies", "rallied", "surge", "surges",
    "surged", "gain", "gains", "gained", "jump", "jumps", "jumped", "soar",
    "soars", "soared", "growth", "grow", "grew", "profit", "profits", "beat",
    "beats", "bullish", "optimism", "positive", "strong", "strength", "upgrade",
    "upgrades", "buy", "outperform", "record high", "inflow", "inflows",
    "recover", "recovery", "rebound", "rebounds", "expansion",
}

_BEARISH_KEYWORDS = {
    "fall", "falls", "fell", "drop", "drops", "dropped", "crash", "crashes",
    "crashed", "loss", "losses", "lost", "decline", "declines", "declined",
    "slump", "slumps", "slumped", "sink", "sinks", "sank", "weak", "weakness",
    "miss", "misses", "missed", "bearish", "pessimism", "negative", "cut",
    "cuts", "downgrade", "downgrades", "sell", "underperform", "outflow",
    "outflows", "layoff", "layoffs", "recession", "contraction", "default",
    "bankruptcy", "fraud", "probe", "investigation", "warning", "caution",
}


def _keyword_sentiment(headline: str) -> str:
    """Rule-based keyword classifier. Returns BULLISH / BEARISH / NEUTRAL."""
    words = set(re.findall(r"\b\w+\b", headline.lower()))
    bull_score = len(words & _BULLISH_KEYWORDS)
    bear_score = len(words & _BEARISH_KEYWORDS)

    if bull_score > bear_score:
        return "BULLISH"
    elif bear_score > bull_score:
        return "BEARISH"
    return "NEUTRAL"


def _gemini_sentiment(headline: str) -> str:
    """
    Layer 1: Ask Gemini to classify headline sentiment.
    Returns BULLISH / BEARISH / NEUTRAL (normalised).
    """
    prompt = (
        "You are a financial sentiment classifier for Indian and global markets.\n"
        "Classify the following financial news headline as exactly one of: "
        "BULLISH, BEARISH, or NEUTRAL.\n"
        "Reply with ONLY that single word — no explanation, no punctuation.\n\n"
        f"Headline: {headline}"
    )
    result = gemini_client.ask(prompt, max_tokens=10, temperature=0.0)
    normalised = result.strip().upper()

    if normalised in ("BULLISH", "BEARISH", "NEUTRAL"):
        return normalised

    # Try to extract if model returned extra words
    for label in ("BULLISH", "BEARISH", "NEUTRAL"):
        if label in normalised:
            return label

    logger.warning("Gemini returned unexpected sentiment %r for: %r", result, headline[:60])
    return "NEUTRAL"  # safe fallback


def analyse(headline: str) -> dict:
    """
    Full multi-layer sentiment analysis for a single headline.

    Returns:
        {
            "label":      "BULLISH" | "BEARISH" | "NEUTRAL",
            "emoji":      "🟢" | "🔴" | "🟡",
            "confidence": "HIGH" | "MEDIUM" | "LOW",
            "gemini":     str,    # Layer 1 result
            "keyword":    str,    # Layer 2 result
        }
    """
    # Layer 1 — Gemini
    gemini_label = _gemini_sentiment(headline)

    # Layer 2 — Keywords
    keyword_label = _keyword_sentiment(headline)

    # Layer 3 — Agreement & confidence
    if gemini_label == keyword_label:
        final_label = gemini_label
        confidence = "HIGH"
    elif gemini_label == "NEUTRAL":
        # Gemini uncertain → trust keyword signal
        final_label = keyword_label
        confidence = "MEDIUM"
    elif keyword_label == "NEUTRAL":
        # Keywords found nothing → trust Gemini
        final_label = gemini_label
        confidence = "MEDIUM"
    else:
        # Direct contradiction BULL vs BEAR → call it uncertain
        final_label = "NEUTRAL"
        confidence = "LOW"

    logger.debug(
        "Sentiment [%s|conf=%s] gemini=%s keyword=%s | %s",
        final_label, confidence, gemini_label, keyword_label, headline[:60],
    )

    return {
        "label": final_label,
        "emoji": SENTIMENT_EMOJI[final_label],
        "confidence": confidence,
        "gemini": gemini_label,
        "keyword": keyword_label,
    }


def analyse_batch(headlines: list[str]) -> list[dict]:
    """Analyse a list of headlines, returning a result dict for each."""
    results = []
    for h in headlines:
        try:
            results.append(analyse(h))
        except Exception as exc:
            logger.error("Sentiment analysis failed for %r: %s", h[:60], exc)
            results.append({
                "label": "NEUTRAL",
                "emoji": "🟡",
                "confidence": "LOW",
                "gemini": "ERROR",
                "keyword": _keyword_sentiment(h),
            })
    return results
