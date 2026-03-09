"""
main.py
-------
Unified CLI entry-point for the App Review Insights Analyser.

Usage examples:
    python main.py                          # run all phases (dry-run)
    python main.py --phase all --send       # run all phases + send email
    python main.py --phase 1               # only Phase 1
    python main.py --phase 2               # only Phase 2
    python main.py --phase 3               # only Phase 3
    python main.py --phase 4 --send        # only Phase 4 + send email
    python main.py --phase all --weeks 8   # custom review window
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


# ---------------------------------------------------------------------------
# Argument parser (importable for tests)
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="App Review Insights Analyser — run one or all pipeline phases.",
    )
    parser.add_argument(
        "--phase",
        choices=["1", "2", "3", "4", "all"],
        default="all",
        metavar="PHASE",
        help="Which phase to run: 1, 2, 3, 4, or all (default: all).",
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=int(os.getenv("WINDOW_WEEKS", "12")),
        metavar="N",
        help="Number of weeks of reviews to fetch (default: 12).",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        default=False,
        help="Send the email via SMTP (default: dry-run writes .eml file).",
    )
    parser.add_argument(
        "--topics",
        default="",
        metavar="TOPICS",
        help="Comma-separated topics to filter for the pulse report (default: all).",
    )
    parser.add_argument(
        "--app-id",
        default=os.getenv("APP_ID", "com.nextbillion.groww"),
        metavar="APP_ID",
        help="Play Store app ID (default: com.nextbillion.groww).",
    )
    return parser


# ---------------------------------------------------------------------------
# Phase runners
# ---------------------------------------------------------------------------

def run_phase1(weeks: int, app_id: str) -> Path:
    from phase1.pipeline import run
    logger.info("━━━ Phase 1: Ingestion & Cleaning ━━━")
    return run(app_id=app_id, window_weeks=weeks)


def run_phase2(reviews_source=None) -> Path:
    from phase2.pipeline import run
    logger.info("━━━ Phase 2: Theme Discovery & Classification ━━━")
    return run(reviews_source=reviews_source)


def run_phase3(report_source=None, topics=None) -> tuple[Path, Path]:
    from phase3.pipeline import run
    logger.info("━━━ Phase 3: Weekly Pulse Report ━━━")
    return run(report_source=report_source, topics=topics)


def run_phase4(pulse_path=None, send: bool = False) -> Path | None:
    from phase4.pipeline import run
    logger.info("━━━ Phase 4: Email Delivery ━━━")
    return run(pulse_path=pulse_path, send=send)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    phase = args.phase
    weeks = args.weeks
    send = args.send
    app_id = args.app_id
    topics = args.topics

    logger.info("Starting pipeline | phase=%s | weeks=%d | send=%s | topics='%s'", phase, weeks, send, topics)

    try:
        if phase in ("1", "all"):
            reviews_path = run_phase1(weeks=weeks, app_id=app_id)

        if phase in ("2", "all"):
            source = reviews_path if phase == "all" else None
            report_path = run_phase2(reviews_source=source)

        if phase in ("3", "all"):
            source = report_path if phase == "all" else None
            md_path, _txt_path = run_phase3(report_source=source, topics=topics)

        if phase in ("4", "all"):
            pulse = md_path if phase == "all" else None
            run_phase4(pulse_path=pulse, send=send)

    except Exception as exc:
        logger.error("Pipeline failed: %s", exc, exc_info=True)
        return 1

    logger.info("Pipeline complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
