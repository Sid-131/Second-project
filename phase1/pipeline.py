"""
phase1/pipeline.py
------------------
Orchestrates the Phase 1 pipeline:
  scrape → clean → save to data/reviews/YYYY-MM-DD.json

Usage (directly):
    python -m phase1.pipeline

Or call ``run()`` programmatically from another module.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from phase1.cleaner import clean_reviews
from phase1.scraper import fetch_reviews

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run(
    app_id: str | None = None,
    window_weeks: int | None = None,
    min_word_count: int | None = None,
    output_dir: str | None = None,
) -> Path:
    """
    Execute the full Phase 1 pipeline.

    Parameters fall back to environment variables / defaults when not supplied.

    Returns the path of the saved JSON file.
    """
    app_id = app_id or os.getenv("APP_ID", "com.nextbillion.groww")
    window_weeks = int(window_weeks or os.getenv("WINDOW_WEEKS", "12"))
    min_word_count = int(min_word_count or os.getenv("MIN_WORD_COUNT", "5"))
    output_dir = output_dir or os.getenv("REVIEWS_DIR", "data/reviews")

    logger.info("=== Phase 1 Start ===")
    logger.info("app_id=%s  window_weeks=%d  min_word_count=%d", app_id, window_weeks, min_word_count)

    # --- Scrape ---
    raw = fetch_reviews(app_id, window_weeks=window_weeks)

    # --- Clean ---
    cleaned = clean_reviews(raw, min_word_count=min_word_count)

    # --- Save ---
    run_date = date.today().isoformat()
    out_path = Path(output_dir) / f"{run_date}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "run_date": run_date,
        "app_id": app_id,
        "window_weeks": window_weeks,
        "review_count": len(cleaned),
        "reviews": cleaned,
    }

    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)

    logger.info("Saved %d reviews → %s", len(cleaned), out_path)
    logger.info("=== Phase 1 Complete ===")
    return out_path


if __name__ == "__main__":
    saved = run()
    print(f"Output: {saved}")
