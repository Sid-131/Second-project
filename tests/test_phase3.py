"""
tests/test_phase3.py
---------------------
Unit tests for Phase 3 (Weekly Pulse Report Generation).

Tests verify that the generated Markdown conforms to the required structure:
  - Exactly 3 Top Themes listed
  - Exactly 3 Real User Quotes
  - Exactly 3 Action Ideas listed
  - Total word count ≤ 400

The Gemini API is fully mocked — no API calls are made.
"""

from __future__ import annotations

import sys
import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from phase3.pipeline import run as phase3_run

# ---------------------------------------------------------------------------
# A realistic sample pulse Markdown that satisfies all constraints.
# Used as the mocked Gemini response.
# ---------------------------------------------------------------------------

_VALID_PULSE_MD = """\
# Weekly Pulse — 2026-03-10

## Top 3 Themes
1. **Login & Authentication Issues** — Users are frequently logged out and face biometric failures.
2. **Slow App Performance** — The app lags and freezes, especially on older devices.
3. **Portfolio Tracking** — Users find the portfolio view useful but request more filters.

## Real User Quotes
> "The app keeps logging me out every single time I switch apps, very frustrating." ⭐ 1/5
> "Performance has improved but the charts still take too long to load on my phone." ⭐ 3/5
> "Portfolio tracker is accurate and easy to use, exactly what I need for daily tracking." ⭐ 5/5

## Action Ideas
1. Investigate and fix the session persistence bug causing unexpected logouts on Android.
2. Optimise chart rendering pipeline to reduce load time by at least fifty percent.
3. Add filtering options to the portfolio view to allow users to sort by returns and date.
"""

# A minimal Phase 2 report dict for testing
_SAMPLE_REPORT = {
    "run_date": "2026-03-10",
    "app_id": "com.nextbillion.groww",
    "total_reviews_classified": 10,
    "themes": [
        {
            "id": "theme_001",
            "slug": "login_issues",
            "label": "Login & Authentication Issues",
            "description": "Users face unexpected logouts.",
            "review_count": 4,
            "reviews": [
                {"review_id": "r01", "score": 1, "text": "Keeps logging me out.", "thumbs_up": 2},
            ],
        },
        {
            "id": "theme_002",
            "slug": "slow_performance",
            "label": "Slow App Performance",
            "description": "The app feels laggy.",
            "review_count": 3,
            "reviews": [
                {"review_id": "r02", "score": 2, "text": "Charts load very slowly.", "thumbs_up": 1},
            ],
        },
        {
            "id": "theme_003",
            "slug": "portfolio_tracking",
            "label": "Portfolio Tracking",
            "description": "Positive feedback on portfolio features.",
            "review_count": 3,
            "reviews": [
                {"review_id": "r03", "score": 5, "text": "Great portfolio tracker.", "thumbs_up": 5},
            ],
        },
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_themes_in_md(markdown: str) -> int:
    """Count numbered items under the ## Top 3 Themes heading."""
    in_section = False
    count = 0
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Top 3 Themes"):
            in_section = True
            continue
        if in_section:
            if stripped.startswith("## "):
                break  # next heading
            # Match numbered list items: "1. ", "2. ", etc.
            if stripped and stripped[0].isdigit() and ". " in stripped:
                count += 1
    return count


def _count_quotes_in_md(markdown: str) -> int:
    """Count blockquote lines under the ## Real User Quotes heading."""
    in_section = False
    count = 0
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Real User Quotes"):
            in_section = True
            continue
        if in_section:
            if stripped.startswith("## "):
                break
            if stripped.startswith(">"):
                count += 1
    return count


def _count_actions_in_md(markdown: str) -> int:
    """Count numbered items under the ## Action Ideas heading."""
    in_section = False
    count = 0
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Action Ideas"):
            in_section = True
            continue
        if in_section:
            if stripped.startswith("## "):
                break
            if stripped and stripped[0].isdigit() and ". " in stripped:
                count += 1
    return count


def _word_count(markdown: str) -> int:
    return len(markdown.split())


# ---------------------------------------------------------------------------
# Mock helper
# ---------------------------------------------------------------------------

def _make_gemini_mock(markdown_text: str):
    """Return a mock google.genai.Client whose generate_content returns markdown_text."""
    mock_response = MagicMock()
    mock_response.text = markdown_text

    mock_model_service = MagicMock()
    mock_model_service.generate_content.return_value = mock_response

    mock_client = MagicMock()
    mock_client.models = mock_model_service

    return mock_client


# ---------------------------------------------------------------------------
# Test 1: Exactly 3 Top Themes
# ---------------------------------------------------------------------------

def test_exactly_three_top_themes(tmp_path):
    mock_client = _make_gemini_mock(_VALID_PULSE_MD)
    with patch("phase3.report_builder.genai.Client", return_value=mock_client):
        md_path, _ = phase3_run(
            report_source=_SAMPLE_REPORT,
            output_dir=str(tmp_path),
            api_key="fake-key",
        )

    md = md_path.read_text(encoding="utf-8")
    n = _count_themes_in_md(md)
    assert n == 3, f"Expected exactly 3 Top Themes, found {n}"


# ---------------------------------------------------------------------------
# Test 2: Exactly 3 Real User Quotes
# ---------------------------------------------------------------------------

def test_exactly_three_real_user_quotes(tmp_path):
    mock_client = _make_gemini_mock(_VALID_PULSE_MD)
    with patch("phase3.report_builder.genai.Client", return_value=mock_client):
        md_path, _ = phase3_run(
            report_source=_SAMPLE_REPORT,
            output_dir=str(tmp_path),
            api_key="fake-key",
        )

    md = md_path.read_text(encoding="utf-8")
    n = _count_quotes_in_md(md)
    assert n == 3, f"Expected exactly 3 Real User Quotes, found {n}"


# ---------------------------------------------------------------------------
# Test 3: Exactly 3 Action Ideas
# ---------------------------------------------------------------------------

def test_exactly_three_action_ideas(tmp_path):
    mock_client = _make_gemini_mock(_VALID_PULSE_MD)
    with patch("phase3.report_builder.genai.Client", return_value=mock_client):
        md_path, _ = phase3_run(
            report_source=_SAMPLE_REPORT,
            output_dir=str(tmp_path),
            api_key="fake-key",
        )

    md = md_path.read_text(encoding="utf-8")
    n = _count_actions_in_md(md)
    assert n == 3, f"Expected exactly 3 Action Ideas, found {n}"


# ---------------------------------------------------------------------------
# Test 4: Total word count ≤ 400
# ---------------------------------------------------------------------------

def test_word_count_at_most_400(tmp_path):
    mock_client = _make_gemini_mock(_VALID_PULSE_MD)
    with patch("phase3.report_builder.genai.Client", return_value=mock_client):
        md_path, _ = phase3_run(
            report_source=_SAMPLE_REPORT,
            output_dir=str(tmp_path),
            api_key="fake-key",
        )

    md = md_path.read_text(encoding="utf-8")
    wc = _word_count(md)
    assert wc <= 400, f"Word count {wc} exceeds the 400-word limit"


# ---------------------------------------------------------------------------
# Test 5: Both .md and .txt files are saved
# ---------------------------------------------------------------------------

def test_both_output_files_saved(tmp_path):
    mock_client = _make_gemini_mock(_VALID_PULSE_MD)
    with patch("phase3.report_builder.genai.Client", return_value=mock_client):
        md_path, txt_path = phase3_run(
            report_source=_SAMPLE_REPORT,
            output_dir=str(tmp_path),
            api_key="fake-key",
        )

    assert md_path.exists(), ".md file was not created"
    assert txt_path.exists(), ".txt file was not created"
    assert md_path.suffix == ".md"
    assert txt_path.suffix == ".txt"
    # Both files should have identical content
    assert md_path.read_text(encoding="utf-8") == txt_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test 6: Required section headings are present
# ---------------------------------------------------------------------------

def test_required_headings_present(tmp_path):
    mock_client = _make_gemini_mock(_VALID_PULSE_MD)
    with patch("phase3.report_builder.genai.Client", return_value=mock_client):
        md_path, _ = phase3_run(
            report_source=_SAMPLE_REPORT,
            output_dir=str(tmp_path),
            api_key="fake-key",
        )

    md = md_path.read_text(encoding="utf-8")
    assert "## Top 3 Themes" in md, "Missing '## Top 3 Themes' heading"
    assert "## Real User Quotes" in md, "Missing '## Real User Quotes' heading"
    assert "## Action Ideas" in md, "Missing '## Action Ideas' heading"


# ---------------------------------------------------------------------------
# Test 7: Pulse with word count OVER 400 still saves (but triggers warning)
# ---------------------------------------------------------------------------

def test_oversized_pulse_still_saves(tmp_path):
    """The pipeline should save even if word count > 400 (it just logs a warning)."""
    wordy_md = _VALID_PULSE_MD + "\n\n" + "extra word " * 300  # definitely > 400 words
    mock_client = _make_gemini_mock(wordy_md)
    with patch("phase3.report_builder.genai.Client", return_value=mock_client):
        md_path, txt_path = phase3_run(
            report_source=_SAMPLE_REPORT,
            output_dir=str(tmp_path),
            api_key="fake-key",
        )

    assert md_path.exists()
    assert txt_path.exists()
    wc = _word_count(md_path.read_text(encoding="utf-8"))
    assert wc > 400  # confirm the test scenario is actually over-limit
