"""
tests/test_phase1.py
--------------------
Unit tests for Phase 1 (Review Ingestion & Cleaning).

All external I/O is mocked — no network calls are made.
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from phase1.cleaner import clean_reviews


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_raw_review(
    review_id: str,
    content: str,
    score: int = 4,
    thumbs_up: int = 0,
    at: datetime | None = None,
) -> dict:
    return {
        "reviewId": review_id,
        "userName": "Test User",
        "content": content,
        "score": score,
        "thumbsUpCount": thumbs_up,
        "at": at or datetime(2024, 1, 1, tzinfo=timezone.utc),
        "replyContent": None,
        "repliedAt": None,
        # 'title' is intentionally NOT included — scraper doesn't expose it
    }


# ---------------------------------------------------------------------------
# Test 1: Reviews with fewer than 5 words are dropped
# ---------------------------------------------------------------------------

def test_short_reviews_filtered():
    raw = [
        _make_raw_review("r1", "Good"),                      # 1 word → drop
        _make_raw_review("r2", "Nice app"),                  # 2 words → drop
        _make_raw_review("r3", "Love this app so much"),     # 5 words → keep
        _make_raw_review("r4", "ok"),                        # 1 word → drop
    ]
    result = clean_reviews(raw, min_word_count=5)
    ids = [r["review_id"] for r in result]
    assert "r3" in ids, "5-word review should pass"
    assert "r1" not in ids
    assert "r2" not in ids
    assert "r4" not in ids


# ---------------------------------------------------------------------------
# Test 2: Non-English reviews are filtered out
# ---------------------------------------------------------------------------

def test_non_english_reviews_filtered():
    raw = [
        _make_raw_review("en1", "This is a great investment app I use daily"),
        _make_raw_review("hi1", "यह एक बहुत अच्छा निवेश ऐप है जो मुझे पसंद है"),  # Hindi
        _make_raw_review("te1", "ఈ యాప్ చాలా బాగుంది నేను దీన్ని ప్రతిరోజూ ఉపయోగిస్తాను"),  # Telugu
    ]
    result = clean_reviews(raw, min_word_count=5)
    ids = [r["review_id"] for r in result]
    assert "en1" in ids, "English review should pass"
    assert "hi1" not in ids, "Hindi review should be filtered"
    assert "te1" not in ids, "Telugu review should be filtered"


# ---------------------------------------------------------------------------
# Test 3: PII (email) is scrubbed from review text
# ---------------------------------------------------------------------------

def test_pii_email_scrubbed():
    raw = [
        _make_raw_review(
            "pii1",
            "Please contact me at john.doe@example.com for more details about this issue",
        )
    ]
    result = clean_reviews(raw, min_word_count=5)
    assert len(result) == 1
    assert "john.doe@example.com" not in result[0]["text"]
    assert "[REDACTED]" in result[0]["text"]


# ---------------------------------------------------------------------------
# Test 4: PII (phone number) is scrubbed
# ---------------------------------------------------------------------------

def test_pii_phone_scrubbed():
    raw = [
        _make_raw_review(
            "pii2",
            "Call me at +91 98765 43210 to resolve my account issue please",
        )
    ]
    result = clean_reviews(raw, min_word_count=5)
    assert len(result) == 1
    assert "98765" not in result[0]["text"]


# ---------------------------------------------------------------------------
# Test 5: Emoji characters are removed from text
# ---------------------------------------------------------------------------

def test_emoji_removed():
    raw = [
        _make_raw_review(
            "emoji1",
            "Amazing app I love trading stocks here every day 🚀🔥💯",
        )
    ]
    result = clean_reviews(raw, min_word_count=5)
    assert len(result) == 1
    text = result[0]["text"]
    # No emoji Unicode characters should remain
    assert "🚀" not in text
    assert "🔥" not in text
    assert "💯" not in text


# ---------------------------------------------------------------------------
# Test 6: Output dicts do NOT contain a 'title' field
# ---------------------------------------------------------------------------

def test_title_not_stored():
    raw = [
        _make_raw_review(
            "notitle",
            "The portfolio tracker works really well and is easy to use",
        )
    ]
    result = clean_reviews(raw, min_word_count=5)
    assert len(result) == 1
    assert "title" not in result[0], "title must not be persisted"
    assert "userName" not in result[0], "userName must not be persisted"


# ---------------------------------------------------------------------------
# Test 7: A clean, valid review passes all filters intact
# ---------------------------------------------------------------------------

def test_valid_review_passes_all_filters():
    raw = [
        _make_raw_review(
            "valid1",
            "The portfolio tracker works really well and is very easy to use daily",
            score=5,
            thumbs_up=10,
        )
    ]
    result = clean_reviews(raw, min_word_count=5)
    assert len(result) == 1
    r = result[0]
    assert r["review_id"] == "valid1"
    assert r["score"] == 5
    assert r["thumbs_up"] == 10
    assert len(r["text"]) > 0


# ---------------------------------------------------------------------------
# Test 8: Mocked scraper → pipeline saves correct file
# ---------------------------------------------------------------------------

def test_pipeline_save_output(tmp_path):
    """
    Mock the scraper at the pipeline level and verify:
     - output file is created at the expected path
     - file contains valid JSON with the correct structure
    """
    from datetime import datetime, timedelta, timezone

    # Use a date within the last 1 week so it passes the date-window filter
    recent_date = datetime.now(tz=timezone.utc) - timedelta(days=1)

    fake_raw = [
        _make_raw_review("p1", "The app is excellent and works perfectly for my needs", at=recent_date),
        _make_raw_review("p2", "Bad", at=recent_date),  # too short
    ]

    mock_return = (fake_raw, None)  # (reviews, continuation_token)

    with patch("phase1.scraper.reviews", return_value=mock_return):
        from phase1.pipeline import run
        import json

        out_file = run(
            app_id="com.test.app",
            window_weeks=1,
            min_word_count=5,
            output_dir=str(tmp_path),
        )

        assert out_file.exists(), "Output file should be created"
        payload = json.loads(out_file.read_text(encoding="utf-8"))
        assert payload["app_id"] == "com.test.app"
        assert isinstance(payload["reviews"], list)
        # Only the long review should survive
        assert payload["review_count"] == 1
        assert payload["reviews"][0]["review_id"] == "p1"
