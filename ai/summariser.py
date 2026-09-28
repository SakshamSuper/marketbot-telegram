"""
ai/summariser.py
────────────────
Summarises multi-source news headlines into a concise AI digest
and generates an overall market mood score using Gemini.
"""

import logging
from ai import gemini_client

logger = logging.getLogger(__name__)


def summarise_news(articles: list[dict]) -> str:
    """
    Takes a list of article dicts [{"source": str, "title": str}, ...]
    Returns a 3-line plain-text AI summary tailored for an Indian investor.
    Falls back to a bullet list if Gemini fails.
    """
    if not articles:
        return "No news available at this time."

    headlines_text = "\n".join(
        f"- [{a.get('source', 'Unknown')}] {a.get('title', '')}"
        for a in articles[:15]  # cap at 15 to stay within token budget
    )

    prompt = (
        "You are a financial analyst briefing an Indian retail investor.\n"
        "Summarise the following news headlines in EXACTLY 3 concise sentences.\n"
        "Focus on: market impact, key themes, and what to watch.\n"
        "Do NOT use bullet points. Write as flowing sentences.\n"
        "Keep it under 80 words total.\n\n"
        f"Headlines:\n{headlines_text}"
    )

    summary = gemini_client.ask(prompt, max_tokens=150, temperature=0.3)

    if not summary:
        logger.warning("Gemini summariser returned empty — using fallback")
        # Fallback: top 3 headlines as plain text
        fallback_lines = [f"• {a.get('title', '')}" for a in articles[:3]]
        return "\n".join(fallback_lines)

    return summary


def market_mood(
    indices_data: dict,
    crypto_data: list[dict],
    top_headlines: list[str],
) -> dict:
    """
    Generate an overall market mood assessment.

    Returns:
        {
            "mood":  "BULLISH" | "BEARISH" | "NEUTRAL",
            "emoji": "🟢" | "🔴" | "🟡",
            "label": str,   e.g. "Cautiously Bullish"
            "reason": str,  2-sentence reasoning
        }
    """
    # Build context for Gemini
    index_lines = "\n".join(
        f"- {name}: {data.get('price', 'N/A')} ({data.get('change_pct', 0):+.2f}%)"
        for name, data in indices_data.items()
        if data.get("price")
    )

    crypto_lines = "\n".join(
        f"- {c.get('symbol','').upper()}: {c.get('change_pct', 0):+.2f}%"
        for c in crypto_data[:3]
    )

    headlines_text = "\n".join(f"- {h}" for h in top_headlines[:5])

    prompt = (
        "You are a senior market strategist. Based on the data below, assess the overall "
        "market mood for the day from the perspective of an Indian investor.\n\n"
        f"INDICES:\n{index_lines}\n\n"
        f"CRYPTO:\n{crypto_lines}\n\n"
        f"TOP HEADLINES:\n{headlines_text}\n\n"
        "Respond in JSON with exactly these keys:\n"
        '{"mood": "BULLISH|BEARISH|NEUTRAL", "label": "2-3 word phrase", "reason": "2 sentences max"}\n'
        "mood must be exactly one of: BULLISH, BEARISH, NEUTRAL."
    )

    result = gemini_client.ask_json(prompt, max_tokens=200)

    mood_map = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "🟡"}

    if isinstance(result, dict):
        mood = result.get("mood", "NEUTRAL").upper()
        if mood not in mood_map:
            mood = "NEUTRAL"
        return {
            "mood": mood,
            "emoji": mood_map[mood],
            "label": result.get("label", mood.capitalize()),
            "reason": result.get("reason", "Market data analysed."),
        }

    # Fallback
    logger.warning("market_mood: Gemini returned invalid JSON, using fallback")
    return {
        "mood": "NEUTRAL",
        "emoji": "🟡",
        "label": "Mixed Signals",
        "reason": "Unable to determine clear market direction. Exercise caution.",
    }


def explain_price_move(symbol: str, change_pct: float, headline_context: str = "") -> str:
    """
    Generate a brief 2-sentence AI explanation for a significant price move.
    Used in smart price alert cards.
    """
    direction = "dropped" if change_pct < 0 else "surged"
    prompt = (
        f"A stock/asset {symbol} has {direction} {abs(change_pct):.1f}% today.\n"
        + (f"Recent news context: {headline_context}\n" if headline_context else "")
        + "As a financial analyst, explain in EXACTLY 2 short sentences why this likely happened "
        "and what an investor should watch for. Be specific and factual."
    )

    explanation = gemini_client.ask(prompt, max_tokens=100, temperature=0.3)
    return explanation or f"{symbol} moved {change_pct:+.1f}%. Monitor closely for further developments."
