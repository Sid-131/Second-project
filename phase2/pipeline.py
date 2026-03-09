"""
phase2/pipeline.py
------------------
Orchestrates the full Phase 2 pipeline:
  load Phase 1 reviews → discover themes → classify reviews → save report

Output: data/reports/grouped_reviews-YYYY-MM-DD.json

Usage (directly):
    python -m phase2.pipeline [path/to/reviews.json]

Or call ``run()`` programmatically.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from phase2.classifier import classify_reviews
from phase2.theme_discovery import discover_themes

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _load_reviews(reviews_path: Path) -> list[dict]:
    with reviews_path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    return payload.get("reviews", payload) if isinstance(payload, dict) else payload


def run(
    reviews_source: str | Path | list[dict] | None = None,
    output_dir: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> Path:
    """
    Execute Phase 2a (theme discovery) and Phase 2b (classification).

    Parameters
    ----------
    reviews_source: Path to a Phase 1 JSON file, a list of review dicts,
                    or None to auto-find the latest file in REVIEWS_DIR.
    output_dir:     Directory for the output report (default: data/reports).
    api_key:        Groq API key (falls back to env).
    model:          Groq model name (falls back to env).

    Returns the path of the saved report JSON.
    """
    output_dir = output_dir or os.getenv("REPORTS_DIR", "data/reports")

    # --- Load reviews ---
    if isinstance(reviews_source, list):
        reviews = reviews_source
        logger.info("Using %d reviews supplied directly.", len(reviews))
    else:
        if reviews_source is None:
            reviews_dir = Path(os.getenv("REVIEWS_DIR", "data/reviews"))
            candidates = sorted(reviews_dir.glob("*.json"), reverse=True)
            if not candidates:
                raise FileNotFoundError(
                    f"No review files found in {reviews_dir}. Run Phase 1 first."
                )
            reviews_source = candidates[0]
            logger.info("Auto-selected latest reviews file: %s", reviews_source)
        reviews = _load_reviews(Path(reviews_source))
        logger.info("Loaded %d reviews from %s.", len(reviews), reviews_source)

    logger.info("=== Phase 2 Start ===")

    # --- Phase 2a: Theme Discovery ---
    themes = discover_themes(reviews, api_key=api_key, model=model)

    # --- Phase 2b: Classification ---
    classifications = classify_reviews(reviews, themes, api_key=api_key, model=model)

    # --- Build grouped output ---
    # Index reviews by review_id for fast lookup
    review_index = {r["review_id"]: r for r in reviews}

    # Build theme → reviews mapping
    theme_map: dict[str, list[dict]] = {t["slug"]: [] for t in themes}
    classification_lookup: dict[str, dict] = {}

    for clf in classifications:
        rid = clf.get("review_id", "")
        slug = clf.get("theme_slug", "")
        classification_lookup[rid] = clf
        if slug in theme_map and rid in review_index:
            theme_map[slug].append(
                {
                    **review_index[rid],
                    "confidence": clf.get("confidence", 0.0),
                }
            )

    grouped_themes = []
    for theme in themes:
        slug = theme["slug"]
        grouped_themes.append(
            {
                **theme,
                "review_count": len(theme_map[slug]),
                "reviews": theme_map[slug],
            }
        )

    run_date = date.today().isoformat()
    out_path = Path(output_dir) / f"grouped_reviews-{run_date}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "run_date": run_date,
        "app_id": os.getenv("APP_ID", "com.nextbillion.groww"),
        "total_reviews_classified": len(classifications),
        "themes": grouped_themes,
    }

    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, default=str)

    logger.info("Saved report → %s", out_path)
    logger.info("=== Phase 2 Complete ===")
    return out_path


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else None
    saved = run(reviews_source=source)
    print(f"Report: {saved}")
