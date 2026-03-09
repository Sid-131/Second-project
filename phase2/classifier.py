"""
phase2/classifier.py
---------------------
Phase 2b – Review Classification via Groq LLM.

Batches reviews into chunks of ~50, sends each batch to the LLM with the
discovered themes, and asks it to classify each review into exactly ONE theme.

Caps the total reviews classified at 200 (PHASE2_MAX_REVIEWS).
"""

from __future__ import annotations

import json
import logging
import os

from groq import Groq

logger = logging.getLogger(__name__)

PHASE2_MAX_REVIEWS = 200
BATCH_SIZE = 50

_SYSTEM_PROMPT = """You are a data analyst classifying app store reviews into predefined themes.

Instructions:
- Classify EACH review into EXACTLY ONE theme from the list provided.
- Choose the theme that best represents the primary concern expressed in the review.
- Return ONLY a valid JSON array with no markdown, no extra prose.

Each object in the returned array must have exactly these fields:
  "review_id"  – the review_id from the input (copy it exactly)
  "theme_slug" – the slug of the matching theme (must be one of the provided slugs)
  "confidence" – a float between 0.0 and 1.0 (your confidence in the classification)"""


def _build_classification_prompt(reviews_batch: list[dict], themes: list[dict]) -> str:
    theme_lines = "\n".join(
        f'  - slug="{t["slug"]}"  label="{t["label"]}"  description="{t["description"]}"'
        for t in themes
    )
    valid_slugs = ", ".join(f'"{t["slug"]}"' for t in themes)

    review_lines = "\n".join(
        f'  {{"review_id": "{r["review_id"]}", "text": {json.dumps(r["text"])}}}'
        for r in reviews_batch
    )

    return (
        f"Available themes (choose slug from: {valid_slugs}):\n"
        f"{theme_lines}\n\n"
        f"Reviews to classify:\n"
        f"[\n{review_lines}\n]\n\n"
        "Return a JSON array where each element has review_id, theme_slug, and confidence."
    )


def classify_reviews(
    reviews: list[dict],
    themes: list[dict],
    api_key: str | None = None,
    model: str | None = None,
    max_reviews: int = PHASE2_MAX_REVIEWS,
    batch_size: int = BATCH_SIZE,
) -> list[dict]:
    """
    Classify up to *max_reviews* reviews into the provided themes using the
    Groq LLM, processing in batches of *batch_size*.

    Parameters
    ----------
    reviews:     Cleaned review dicts from Phase 1.
    themes:      Theme dicts from Phase 2a (must have 'slug' field).
    api_key:     Groq API key (falls back to GROQ_API_KEY env var).
    model:       Groq model name (falls back to GROQ_MODEL env var).
    max_reviews: Maximum total reviews to classify (default 200).
    batch_size:  Reviews per LLM call (default 50).

    Returns
    -------
    List of classification dicts::

        [{"review_id": "...", "theme_slug": "...", "confidence": 0.95}, ...]
    """
    api_key = api_key or os.getenv("GROQ_API_KEY")
    model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    if not api_key:
        raise ValueError("GROQ_API_KEY is not set. Add it to your .env file.")

    valid_slugs = {t["slug"] for t in themes}

    # Cap to max_reviews
    to_classify = reviews[:max_reviews]
    logger.info(
        "Classifying %d reviews in batches of %d using %s.",
        len(to_classify),
        batch_size,
        model,
    )

    client = Groq(api_key=api_key)
    all_classifications: list[dict] = []

    batches = [to_classify[i: i + batch_size] for i in range(0, len(to_classify), batch_size)]

    for batch_num, batch in enumerate(batches, start=1):
        logger.info("Processing batch %d/%d (%d reviews).", batch_num, len(batches), len(batch))

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_classification_prompt(batch, themes)},
            ],
            temperature=0.1,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )

        raw_content: str = response.choices[0].message.content.strip()
        logger.debug("Batch %d raw response: %s", batch_num, raw_content[:300])

        parsed = json.loads(raw_content)
        # Unwrap if the LLM wrapped the array in an object
        if isinstance(parsed, list):
            batch_results = parsed
        elif isinstance(parsed, dict):
            for key in ("classifications", "results", "data", "items", "reviews"):
                if key in parsed and isinstance(parsed[key], list):
                    batch_results = parsed[key]
                    break
            else:
                batch_results = next((v for v in parsed.values() if isinstance(v, list)), [])
        else:
            batch_results = []

        # Validate and sanitise each result
        for item in batch_results:
            slug = item.get("theme_slug", "")
            if slug not in valid_slugs:
                logger.warning(
                    "review_id=%s has invalid theme_slug=%r — assigning first theme.",
                    item.get("review_id"),
                    slug,
                )
                item["theme_slug"] = themes[0]["slug"]
            item["confidence"] = float(item.get("confidence", 0.0))

        all_classifications.extend(batch_results)
        logger.info("Batch %d done: %d classifications.", batch_num, len(batch_results))

    logger.info("Total classified: %d", len(all_classifications))
    return all_classifications
