"""
phase2/theme_discovery.py
--------------------------
Phase 2a – Theme Discovery via Groq LLM.

Takes a sample of 100-150 cleaned reviews, sends them to the
llama-3.3-70b-versatile model, and asks it to identify exactly 3 to 5
recurring themes.

Returns a list of theme dicts::

    [
        {
            "id":          "theme_001",
            "slug":        "login_issues",
            "label":       "Login & Authentication Issues",
            "description": "Users report being unexpectedly logged out ..."
        },
        ...
    ]
"""

from __future__ import annotations

import json
import logging
import os
import random

from groq import Groq

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a senior UX researcher analysing app store reviews.
Your job is to identify recurring themes in a set of user reviews.

Instructions:
- Identify EXACTLY 3 to 5 distinct, recurring themes across the reviews.
- Each theme must represent a genuine pattern seen in multiple reviews.
- Themes should be specific (not generic like "good app" or "bad app").
- Return ONLY a valid JSON array with no markdown, no prose.

Each object in the array must have exactly these fields:
  "id"          – a zero-padded integer string, e.g. "theme_001"
  "slug"        – a lowercase_snake_case identifier, e.g. "login_issues"
  "label"       – a short human-readable title (3-7 words)
  "description" – 1-2 sentence description of what users say about this theme

Example output (do NOT copy this, generate from the actual reviews):
[
  {
    "id": "theme_001",
    "slug": "login_issues",
    "label": "Login & Authentication Issues",
    "description": "Users frequently report being logged out unexpectedly or unable to log in."
  }
]"""


def _build_user_prompt(reviews: list[dict]) -> str:
    """Format sampled reviews into the prompt body."""
    lines = [f"Review {i + 1}: {r['text']}" for i, r in enumerate(reviews)]
    body = "\n".join(lines)
    return (
        f"Here are {len(reviews)} app store reviews.\n\n"
        f"{body}\n\n"
        "Identify exactly 3 to 5 recurring themes and return the JSON array."
    )


def discover_themes(
    reviews: list[dict],
    sample_size: int = 125,
    api_key: str | None = None,
    model: str | None = None,
) -> list[dict]:
    """
    Sample *sample_size* reviews (between 100 and 150) and ask the Groq LLM to
    identify 3-5 recurring themes.

    Parameters
    ----------
    reviews:     Full list of cleaned review dicts from Phase 1.
    sample_size: How many reviews to send to the LLM (clamped to 100-150).
    api_key:     Groq API key (falls back to GROQ_API_KEY env var).
    model:       Groq model name (falls back to GROQ_MODEL env var).

    Returns
    -------
    List of theme dicts with keys: id, slug, label, description.
    """
    sample_size = max(100, min(150, sample_size))
    api_key = api_key or os.getenv("GROQ_API_KEY")
    model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    if not api_key:
        raise ValueError("GROQ_API_KEY is not set. Add it to your .env file.")

    # Sample reviews randomly (seed for reproducibility)
    population = reviews if len(reviews) <= sample_size else random.sample(reviews, sample_size)
    logger.info("Sending %d reviews to %s for theme discovery.", len(population), model)

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(population)},
        ],
        temperature=0.3,
        max_tokens=1024,
        response_format={"type": "json_object"},
    )

    raw_content: str = response.choices[0].message.content.strip()
    logger.debug("Raw LLM response: %s", raw_content)

    # The model may wrap the array in {"themes": [...]} due to json_object mode
    parsed = json.loads(raw_content)
    if isinstance(parsed, list):
        themes = parsed
    elif isinstance(parsed, dict):
        # Try common wrapper keys
        for key in ("themes", "result", "data", "items"):
            if key in parsed and isinstance(parsed[key], list):
                themes = parsed[key]
                break
        else:
            # Fallback: take the first list value found
            themes = next((v for v in parsed.values() if isinstance(v, list)), [])

    if not (3 <= len(themes) <= 5):
        logger.warning(
            "LLM returned %d themes; expected 3-5. Proceeding with what was returned.",
            len(themes),
        )

    logger.info("Discovered %d themes: %s", len(themes), [t.get("slug") for t in themes])
    return themes
