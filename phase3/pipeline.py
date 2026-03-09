"""
phase3/pipeline.py
------------------
Orchestrates Phase 3: load Phase 2 report → generate pulse → save .md + .txt

Output files:
  data/pulse/pulse-YYYY-MM-DD.md
  data/pulse/pulse-YYYY-MM-DD.txt

Usage (directly):
    python -m phase3.pipeline [path/to/grouped_reviews.json]

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

from phase3.report_builder import build_pulse_report

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _load_report(report_path: Path) -> dict:
    with report_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def run(
    report_source: str | Path | dict | None = None,
    output_dir: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    topics: str | None = None,
) -> tuple[Path, Path]:
    """
    Execute the Phase 3 pipeline.

    Parameters
    ----------
    report_source: Path to a Phase 2 JSON file, a dict, or None to
                   auto-find the latest file in REPORTS_DIR.
    output_dir:    Directory for pulse files (default: data/pulse).
    api_key:       Gemini API key (falls back to env).
    model:         Gemini model name (falls back to env).
    topics:        Comma-separated topics (or 'all').

    Returns
    -------
    Tuple of (md_path, txt_path) for the saved files.
    """
    output_dir = output_dir or os.getenv("PULSE_DIR", "data/pulse")

    # --- Load Phase 2 report ---
    if isinstance(report_source, dict):
        report = report_source
        logger.info("Using report dict supplied directly.")
    else:
        if report_source is None:
            reports_dir = Path(os.getenv("REPORTS_DIR", "data/reports"))
            candidates = sorted(reports_dir.glob("grouped_reviews-*.json"), reverse=True)
            if not candidates:
                raise FileNotFoundError(
                    f"No grouped_reviews files found in {reports_dir}. Run Phase 2 first."
                )
            report_source = candidates[0]
            logger.info("Auto-selected latest report: %s", report_source)
        report = _load_report(Path(report_source))
        logger.info("Loaded report from %s.", report_source)

    logger.info("=== Phase 3 Start ===")
    run_date = date.today().isoformat()

    # --- Generate pulse markdown ---
    markdown = build_pulse_report(report, run_date, api_key=api_key, model=model, topics=topics)

    # --- Save outputs ---
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path = out_dir / f"pulse-{run_date}.md"
    txt_path = out_dir / f"pulse-{run_date}.txt"

    md_path.write_text(markdown, encoding="utf-8")
    txt_path.write_text(markdown, encoding="utf-8")

    word_count = len(markdown.split())
    logger.info(
        "Pulse saved → %s and %s (%d words)", md_path.name, txt_path.name, word_count
    )
    if word_count > 400:
        logger.warning(
            "Word count %d exceeds the 400-word limit! Consider re-running.", word_count
        )

    logger.info("=== Phase 3 Complete ===")
    return md_path, txt_path


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else None
    md, txt = run(report_source=source)
    print(f"Markdown: {md}")
    print(f"Plain text: {txt}")
