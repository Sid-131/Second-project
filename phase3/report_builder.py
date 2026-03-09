"""
phase3/report_builder.py
-------------------------
Phase 3 – Weekly Pulse Report Generator.

Uses Gemini 2.5 Flash to synthesise the grouped Phase 2 report into a
single-page, structured Markdown note (≤ 400 words) containing:

  - Top 3 Themes
  - 3 Real User Quotes (verbatim, with star ratings)
  - 3 Action Ideas (concrete recommendations)

PII is scrubbed before being shown to the model; any residual names in
the LLM output are also replaced with [User].

Output is saved as both pulse-YYYY-MM-DD.md and pulse-YYYY-MM-DD.txt.
"""

from __future__ import annotations

import logging
import os
import random
import re

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PII name scrubber (simple heuristic – capitalised first-name patterns)
# ---------------------------------------------------------------------------
_NAME_PATTERN = re.compile(
    r"\b(?:Hi|Hello|Dear|Thanks?|Regards?,?)?\s*[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?\b"
)


def _redact_names(text: str) -> str:
    """Replace likely proper-name references with [User]."""
    # Only replace salutation-adjacent names to avoid killing normal words
    return re.sub(
        r"\b(Hi|Hello|Dear|Thanks?|Regards?,?)\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?",
        r"\1 [User]",
        text,
    )


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a senior product analyst writing a concise weekly pulse report.

RULES (STRICT):
1. Total word count of the entire note MUST be ≤ 400 words.
2. Return ONLY Markdown — no code fences, no extra prose outside the note.
3. Use EXACTLY this structure (do not rename the headings):

# Weekly Pulse — {date}

## Top 3 Themes
1. **<Theme label>** — <one-sentence summary>
2. **<Theme label>** — <one-sentence summary>
3. **<Theme label>** — <one-sentence summary>

## Real User Quotes
> "<exact verbatim quote>" ⭐ <N>/5
> "<exact verbatim quote>" ⭐ <N>/5
> "<exact verbatim quote>" ⭐ <N>/5

## Action Ideas
1. <concrete recommendation>
2. <concrete recommendation>
3. <concrete recommendation>

4. Quotes must be taken verbatim from the reviews you are given. Do NOT paraphrase.
5. If any quote contains a user's name, replace it with [User].
6. Be specific and actionable in the Action Ideas section.
"""


def _build_user_prompt(report: dict, run_date: str) -> str:
    """Compose the user-facing prompt from the Phase 2 report dict."""
    themes = report.get("themes", [])
    lines: list[str] = [
        f"App: {report.get('app_id', 'unknown')}",
        f"Report date: {run_date}",
        f"Total reviews classified: {report.get('total_reviews_classified', 0)}",
        "",
        "=== THEMES AND SAMPLE REVIEWS ===",
    ]

    for theme in themes:
        slug = theme.get("slug", "")
        label = theme.get("label", slug)
        description = theme.get("description", "")
        review_count = theme.get("review_count", 0)
        lines.append(f"\n### Theme: {label} ({review_count} reviews)")
        lines.append(f"Description: {description}")

        # Take at most 2 sample reviews per theme — keeps the prompt compact
        # so Gemini has plenty of output-token budget for the full note.
        theme_reviews = theme.get("reviews", [])
        sample = random.sample(theme_reviews, min(2, len(theme_reviews)))
        for r in sample:
            text = _redact_names(r.get("text", ""))
            score = r.get("score", 0)
            lines.append(f'  • [{score}★] "{text}"')

    lines.append(
        "\nNow write the Weekly Pulse note following the RULES above exactly."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main builder function
# ---------------------------------------------------------------------------

def build_pulse_report(
    report: dict,
    run_date: str,
    api_key: str | None = None,
    model: str | None = None,
) -> str:
    """
    Call Gemini to generate the weekly pulse Markdown note.

    Parameters
    ----------
    report:   Phase 2 grouped_reviews dict.
    run_date: ISO date string (YYYY-MM-DD) for the report header.
    api_key:  Gemini API key (falls back to GEMINI_API_KEY env var).
    model:    Gemini model name (falls back to GEMINI_MODEL env var).

    Returns
    -------
    The generated Markdown string.
    """
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Add it to your .env file.")

    client = genai.Client(api_key=api_key)
    user_prompt = _build_user_prompt(report, run_date)

    logger.info("Calling Gemini (%s) to generate weekly pulse report.", model)
    logger.info("Prompt length: %d chars.", len(user_prompt))

    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT.replace("{date}", run_date),
            temperature=0.4,
            max_output_tokens=8192,  # raised from 1024 — previous limit caused truncation
        ),
    )

    markdown = response.text.strip()

    # Truncation guard — warn if any required section is missing
    required_sections = ["## Top 3 Themes", "## Real User Quotes", "## Action Ideas"]
    missing = [s for s in required_sections if s not in markdown]
    if missing:
        logger.warning(
            "Generated pulse is missing sections: %s. "
            "finish_reason=%s. Consider re-running.",
            missing,
            getattr(response.candidates[0], 'finish_reason', 'unknown') if response.candidates else 'unknown',
        )

    # Final safety pass — redact any names the model may have left in
    markdown = _redact_names(markdown)

    logger.info("Pulse report generated (%d words).", len(markdown.split()))
    return markdown
