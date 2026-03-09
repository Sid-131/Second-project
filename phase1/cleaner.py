"""
phase1/cleaner.py
-----------------
Cleans and filters raw Play Store reviews.

Steps applied in order:
  1. Word-count filter  – drop if fewer than MIN_WORD_COUNT words.
  2. Language filter    – drop if langdetect says the text is not English.
  3. Emoji removal      – strip all emoji / pictographic characters.
  4. PII scrubbing      – remove emails, phone numbers, URLs, Aadhaar numbers.
  5. Field projection   – keep only the fields we want to persist.
"""

from __future__ import annotations

import logging
import re

import emoji
from langdetect import DetectorFactory, LangDetectException, detect

# Make langdetect deterministic
DetectorFactory.seed = 42

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PII regex patterns
# ---------------------------------------------------------------------------
_PII_PATTERNS: list[re.Pattern] = [
    # Email addresses
    re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.]+", re.IGNORECASE),
    # URLs
    re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE),
    # Phone numbers (international / Indian formats)
    re.compile(r"\+?\d[\d\s\-(). ]{7,}\d"),
    # Aadhaar-style 12-digit numbers
    re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
]


def _count_words(text: str) -> int:
    return len(text.split())


def _is_english(text: str) -> bool:
    try:
        return detect(text) == "en"
    except LangDetectException:
        return False


def _remove_emojis(text: str) -> str:
    return emoji.replace_emoji(text, replace="").strip()


def _scrub_pii(text: str) -> str:
    for pattern in _PII_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text.strip()


def clean_reviews(
    raw_reviews: list[dict],
    min_word_count: int = 5,
) -> list[dict]:
    """
    Apply all cleaning / filtering steps to a list of raw scraper dicts.

    Returns a list of cleaned review dicts with the schema::

        {
            "review_id":  str,
            "score":      int,          # 1-5 star rating
            "date":       str,          # ISO-8601 datetime string
            "text":       str,
            "thumbs_up":  int,
        }

    Note: ``title`` / ``userName`` / ``replyContent`` are intentionally excluded.
    """
    cleaned: list[dict] = []
    stats = {
        "total": len(raw_reviews),
        "dropped_word_count": 0,
        "dropped_language": 0,
        "passed": 0,
    }

    for r in raw_reviews:
        text: str = (r.get("content") or "").strip()

        # 1. Word-count filter
        if _count_words(text) < min_word_count:
            stats["dropped_word_count"] += 1
            continue

        # 2. Language filter
        if not _is_english(text):
            stats["dropped_language"] += 1
            continue

        # 3. Emoji removal
        text = _remove_emojis(text)

        # 4. PII scrubbing
        text = _scrub_pii(text)

        # After cleaning, re-check minimum word count (PII removal may shorten)
        if _count_words(text) < min_word_count:
            stats["dropped_word_count"] += 1
            continue

        # 5. Field projection – NO title stored
        review_date = r.get("at")
        date_str = review_date.isoformat() if review_date else None

        cleaned.append(
            {
                "review_id": r.get("reviewId", ""),
                "score": r.get("score", 0),
                "date": date_str,
                "text": text,
                "thumbs_up": r.get("thumbsUpCount", 0),
            }
        )
        stats["passed"] += 1

    logger.info(
        "Cleaning complete | total=%d | dropped_word_count=%d | "
        "dropped_language=%d | passed=%d",
        stats["total"],
        stats["dropped_word_count"],
        stats["dropped_language"],
        stats["passed"],
    )
    return cleaned
