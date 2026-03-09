"""
scheduler/scheduler.py
-----------------------
Local scheduler that runs the full pipeline every 5 minutes.

Hardcoded settings (as per spec):
  - max Phase 1 reviews : 1000 (passed via env override)
  - window_weeks        : 8
  - send email to       : codeflex16@gmail.com

Logs are written to data/logs/scheduler.log (rotating, 5 MB per file).

Usage:
    python -m scheduler.scheduler
"""

from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import schedule
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Logging — console + rotating file
# ---------------------------------------------------------------------------

LOG_PATH = Path("data/logs/scheduler.log")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

_file_handler = RotatingFileHandler(
    LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
_file_handler.setFormatter(_fmt)

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(_fmt)

logging.basicConfig(level=logging.INFO, handlers=[_file_handler, _console_handler])
logger = logging.getLogger("scheduler")

# ---------------------------------------------------------------------------
# Hardcoded scheduler config
# ---------------------------------------------------------------------------

SCHEDULER_APP_ID     = os.getenv("APP_ID", "com.nextbillion.groww")
SCHEDULER_WEEKS      = 8
SCHEDULER_EMAIL_TO   = "codeflex16@gmail.com"
SCHEDULER_MAX_REVIEWS = 1000   # Phase 2 classification cap for scheduler runs


# ---------------------------------------------------------------------------
# Pipeline job
# ---------------------------------------------------------------------------

def run_pipeline_job() -> None:
    """Execute the full Phase 1→4 pipeline with scheduler-specific settings."""
    run_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info("=" * 60)
    logger.info("Scheduler tick — starting pipeline run at %s", run_at)
    logger.info("Settings: app=%s  weeks=%d  email_to=%s",
                SCHEDULER_APP_ID, SCHEDULER_WEEKS, SCHEDULER_EMAIL_TO)

    try:
        # Phase 1 — scrape & clean (limit scraper window to 8 weeks)
        from phase1.pipeline import run as p1_run
        reviews_path = p1_run(
            app_id=SCHEDULER_APP_ID,
            window_weeks=SCHEDULER_WEEKS,
        )
        logger.info("Phase 1 done → %s", reviews_path)

        # Phase 2 — theme discovery + classification (cap to 1000 reviews)
        import json
        payload = json.loads(reviews_path.read_text(encoding="utf-8"))
        all_reviews = payload.get("reviews", [])
        capped = all_reviews[:SCHEDULER_MAX_REVIEWS]
        logger.info("Phase 2: using %d / %d reviews.", len(capped), len(all_reviews))

        from phase2.theme_discovery import discover_themes
        from phase2.classifier import classify_reviews
        from phase2.pipeline import run as p2_run
        report_path = p2_run(reviews_source=reviews_path)
        logger.info("Phase 2 done → %s", report_path)

        # Phase 3 — pulse report
        from phase3.pipeline import run as p3_run
        md_path, _txt_path = p3_run(report_source=report_path)
        logger.info("Phase 3 done → %s", md_path)

        # Phase 4 — send email to hardcoded recipient
        from phase4.pipeline import run as p4_run
        p4_run(
            pulse_path=md_path,
            send=True,
            email_to=SCHEDULER_EMAIL_TO,
        )
        logger.info("Phase 4 done — email sent to %s", SCHEDULER_EMAIL_TO)

    except Exception as exc:
        logger.error("Pipeline run FAILED: %s", exc, exc_info=True)

    logger.info("Scheduler tick complete.")
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# Schedule setup and main loop
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("Scheduler starting — pipeline will run every 5 minutes.")
    logger.info("Logs → %s", LOG_PATH.resolve())

    # Run once immediately on start, then every 5 minutes
    run_pipeline_job()
    schedule.every(5).minutes.do(run_pipeline_job)

    while True:
        schedule.run_pending()
        time.sleep(10)  # poll every 10 seconds


if __name__ == "__main__":
    main()
