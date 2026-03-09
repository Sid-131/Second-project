"""
tests/test_phase2.py
---------------------
Unit tests for Phase 2 (Theme Discovery & Classification).

The Groq client is fully mocked — no API calls are made.
"""

from __future__ import annotations

import json
import sys
import os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from phase2.classifier import classify_reviews

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

THEMES = [
    {"id": "theme_001", "slug": "login_issues",       "label": "Login Issues",         "description": "Problems logging in."},
    {"id": "theme_002", "slug": "slow_performance",   "label": "Slow Performance",     "description": "App feels laggy."},
    {"id": "theme_003", "slug": "ui_design",           "label": "UI/UX Design",         "description": "Comments on the interface."},
    {"id": "theme_004", "slug": "portfolio_tracking",  "label": "Portfolio Tracking",   "description": "Features for tracking investments."},
    {"id": "theme_005", "slug": "customer_support",    "label": "Customer Support",     "description": "Experience with support team."},
]

MOCK_REVIEWS = [
    {"review_id": "r01", "text": "The app keeps logging me out every time I open it.", "score": 2},
    {"review_id": "r02", "text": "Charts load very slow and the app freezes often.", "score": 2},
    {"review_id": "r03", "text": "The new dashboard looks clean and modern.", "score": 5},
    {"review_id": "r04", "text": "Cannot log in after the latest update broke everything.", "score": 1},
    {"review_id": "r05", "text": "Portfolio view is great, easy to track my stocks.", "score": 5},
    {"review_id": "r06", "text": "Customer support resolved my issue within one day.", "score": 4},
    {"review_id": "r07", "text": "Login with biometrics is broken since last update.", "score": 1},
    {"review_id": "r08", "text": "Performance improved but UI still needs work overall.", "score": 3},
    {"review_id": "r09", "text": "Mutual fund investment tracking is accurate and helpful.", "score": 5},
    {"review_id": "r10", "text": "Support team was slow to respond but eventually helped.", "score": 3},
]


def _make_llm_response(review_ids: list[str], themes: list[dict]) -> str:
    """
    Build a deterministic mock LLM classification response.

    Assigns each review_id a theme round-robin from the available slugs.
    """
    slugs = [t["slug"] for t in themes]
    classifications = [
        {"review_id": rid, "theme_slug": slugs[i % len(slugs)], "confidence": 0.9}
        for i, rid in enumerate(review_ids)
    ]
    return json.dumps({"classifications": classifications})


# ---------------------------------------------------------------------------
# Test 1: Every review_id maps to a valid theme_slug
# ---------------------------------------------------------------------------

def test_all_reviews_mapped_to_valid_theme():
    """
    Provide 10 mock reviews. Verify that classify_reviews returns a result
    for every single review_id and each result maps to a valid theme slug.
    """
    valid_slugs = {t["slug"] for t in THEMES}
    review_ids = [r["review_id"] for r in MOCK_REVIEWS]

    # Build a mock LLM response for the single batch (10 reviews < 50 batch_size)
    mock_content = _make_llm_response(review_ids, THEMES)

    # Mock the Groq client
    mock_choice = MagicMock()
    mock_choice.message.content = mock_content

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch("phase2.classifier.Groq", return_value=mock_client):
        results = classify_reviews(
            reviews=MOCK_REVIEWS,
            themes=THEMES,
            api_key="fake-key",
            model="llama-3.3-70b-versatile",
        )

    assert len(results) == len(MOCK_REVIEWS), (
        f"Expected {len(MOCK_REVIEWS)} classifications, got {len(results)}"
    )

    result_ids = {r["review_id"] for r in results}
    for rid in review_ids:
        assert rid in result_ids, f"review_id {rid!r} was not classified"

    for clf in results:
        assert clf["theme_slug"] in valid_slugs, (
            f"review_id={clf['review_id']} has invalid theme_slug={clf['theme_slug']!r}. "
            f"Valid slugs: {valid_slugs}"
        )


# ---------------------------------------------------------------------------
# Test 2: Invalid slug from LLM is corrected to the first valid theme
# ---------------------------------------------------------------------------

def test_invalid_slug_is_corrected():
    """
    If the LLM returns a slug that is not in the theme list,
    the classifier must correct it to the first valid theme.
    """
    bad_response = json.dumps({
        "classifications": [
            {"review_id": "r01", "theme_slug": "totally_made_up_slug", "confidence": 0.5},
        ]
    })

    mock_choice = MagicMock()
    mock_choice.message.content = bad_response

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch("phase2.classifier.Groq", return_value=mock_client):
        results = classify_reviews(
            reviews=MOCK_REVIEWS[:1],  # only need one review for this test
            themes=THEMES,
            api_key="fake-key",
        )

    assert len(results) == 1
    assert results[0]["theme_slug"] == THEMES[0]["slug"], (
        "Invalid slug should have been corrected to the first theme"
    )


# ---------------------------------------------------------------------------
# Test 3: Batching — 10 reviews with batch_size=3 triggers multiple LLM calls
# ---------------------------------------------------------------------------

def test_batching_multiple_llm_calls():
    """
    With batch_size=3 and 10 reviews, we expect ceil(10/3) = 4 LLM calls.
    """
    def side_effect(*args, **kwargs):
        # Extract reviews from the user message to return correct review_ids
        user_msg = kwargs["messages"][-1]["content"]
        # Parse review_ids from the prompt (they appear as "review_id": "rXX")
        import re
        ids_in_batch = re.findall(r'"review_id":\s*"([^"]+)"', user_msg)
        content = _make_llm_response(ids_in_batch, THEMES)
        mock_choice = MagicMock()
        mock_choice.message.content = content
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        return mock_completion

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = side_effect

    with patch("phase2.classifier.Groq", return_value=mock_client):
        results = classify_reviews(
            reviews=MOCK_REVIEWS,
            themes=THEMES,
            api_key="fake-key",
            batch_size=3,
        )

    import math
    expected_calls = math.ceil(len(MOCK_REVIEWS) / 3)
    assert mock_client.chat.completions.create.call_count == expected_calls, (
        f"Expected {expected_calls} LLM calls, got "
        f"{mock_client.chat.completions.create.call_count}"
    )
    assert len(results) == len(MOCK_REVIEWS)


# ---------------------------------------------------------------------------
# Test 4: max_reviews cap is respected
# ---------------------------------------------------------------------------

def test_max_reviews_cap():
    """Only the first max_reviews reviews should be sent to the LLM."""
    MAX = 5

    mock_choice = MagicMock()
    mock_choice.message.content = _make_llm_response(
        [r["review_id"] for r in MOCK_REVIEWS[:MAX]], THEMES
    )

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch("phase2.classifier.Groq", return_value=mock_client):
        results = classify_reviews(
            reviews=MOCK_REVIEWS,
            themes=THEMES,
            api_key="fake-key",
            max_reviews=MAX,
        )

    assert len(results) == MAX, f"Expected {MAX} results, got {len(results)}"
