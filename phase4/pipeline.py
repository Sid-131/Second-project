"""
phase4/pipeline.py
------------------
Orchestrates Phase 4: load pulse note → build MIME email → dry-run or send.

Usage:
    # Dry-run (default) — writes .eml to data/reports/
    python -m phase4.pipeline

    # Live send via SMTP
    python -m phase4.pipeline --send

    # Point at a specific pulse file
    python -m phase4.pipeline --pulse data/pulse/pulse-2026-03-10.md
    python -m phase4.pipeline --pulse data/pulse/pulse-2026-03-10.md --send
"""

from __future__ import annotations

import argparse
import logging
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from phase4.emailer import build_message, send_email, write_eml

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _find_latest_pulse() -> Path:
    """Auto-find the most recent pulse-*.md in PULSE_DIR."""
    pulse_dir = Path(os.getenv("PULSE_DIR", "data/pulse"))
    candidates = sorted(pulse_dir.glob("pulse-*.md"), reverse=True)
    if not candidates:
        raise FileNotFoundError(
            f"No pulse-*.md files found in {pulse_dir}. Run Phase 3 first."
        )
    return candidates[0]


def run(
    pulse_path: str | Path | None = None,
    send: bool = False,
    output_dir: str | None = None,
    # SMTP overrides (fall back to env vars)
    smtp_host: str | None = None,
    smtp_port: int | None = None,
    smtp_user: str | None = None,
    smtp_password: str | None = None,
    email_from: str | None = None,
    email_to: str | list[str] | None = None,
) -> Path | None:
    """
    Execute Phase 4.

    Parameters
    ----------
    pulse_path:    Path to a pulse .md file (auto-finds latest if None).
    send:          If True, send via SMTP; if False (default), dry-run to .eml.
    output_dir:    Directory for the .eml file (default: data/reports).

    Returns
    -------
    Path to the .eml file written in dry-run mode, or None if live send.
    """
    output_dir = output_dir or os.getenv("REPORTS_DIR", "data/reports")

    # --- Load pulse Markdown ---
    if pulse_path is None:
        pulse_path = _find_latest_pulse()
    pulse_path = Path(pulse_path)
    logger.info("Loading pulse from: %s", pulse_path)
    markdown = pulse_path.read_text(encoding="utf-8")

    # --- Resolve config ---
    run_date = date.today().isoformat()
    subject = f"📊 Groww App Weekly Pulse — {run_date}"

    from_addr = email_from or os.getenv("EMAIL_FROM", "pulse@example.com")

    raw_to = email_to or os.getenv("EMAIL_TO", "team@example.com")
    to_addrs = (
        [a.strip() for a in raw_to.split(",")] if isinstance(raw_to, str) else list(raw_to)
    )

    logger.info("=== Phase 4 Start ===")

    # --- Build MIME message ---
    msg = build_message(markdown, subject, from_addr, to_addrs)

    # --- Dry-run or send ---
    if not send:
        eml_path = Path(output_dir) / f"pulse-{run_date}.eml"
        result = write_eml(msg, eml_path)
        logger.info("=== Phase 4 Complete (dry-run) ===")
        return result

    # Live send
    host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(smtp_port or os.getenv("SMTP_PORT", "587"))
    user = smtp_user or os.getenv("SMTP_USER", "")
    password = smtp_password or os.getenv("SMTP_PASSWORD", "")

    if not user or not password:
        raise ValueError(
            "SMTP_USER and SMTP_PASSWORD must be set in .env to send email."
        )

    send_email(msg, host, port, user, password)
    logger.info("=== Phase 4 Complete (sent) ===")
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 4 – Email the weekly pulse note."
    )
    parser.add_argument(
        "--pulse",
        metavar="PATH",
        default=None,
        help="Path to a pulse-*.md file (default: latest in PULSE_DIR).",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        default=False,
        help="Send via SMTP instead of writing a dry-run .eml file.",
    )
    args = parser.parse_args()

    result = run(pulse_path=args.pulse, send=args.send)
    if result:
        print(f"Dry-run EML: {result}")
    else:
        print("Email sent successfully.")


if __name__ == "__main__":
    main()
