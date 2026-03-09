"""
tests/test_phase4.py
---------------------
Unit tests for Phase 4 (Email Delivery).

Tests:
  1. Dry-run mode creates a valid .eml file in the correct directory.
  2. Send mode calls smtplib.SMTP with the correct host and port.
  3. Send mode (SSL/port 465) calls smtplib.SMTP_SSL.
  4. The generated MIME message has the correct headers and both parts.

No real SMTP connections or file I/O outside tmp_path are made.
"""

from __future__ import annotations

import email
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from email.header import decode_header as _decode_header_raw

from phase4.emailer import build_message, send_email, write_eml
from phase4.pipeline import run as phase4_run


def _decode_subject(msg) -> str:
    """Decode an RFC-2047 encoded Subject header back to a plain string."""
    raw = msg["Subject"]
    parts = _decode_header_raw(raw)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8"))
        else:
            decoded.append(part)
    return "".join(decoded)

# ---------------------------------------------------------------------------
# Sample pulse content
# ---------------------------------------------------------------------------

_SAMPLE_MARKDOWN = """\
# Weekly Pulse — 2026-03-10

## Top 3 Themes
1. **Login Issues** — Users are frequently logged out unexpectedly.
2. **Slow Performance** — Charts take too long to load on older devices.
3. **Portfolio Tracking** — Positive feedback on portfolio features.

## Real User Quotes
> "The app keeps logging me out every time I switch apps." ⭐ 1/5
> "Charts load very slowly on my older device." ⭐ 2/5
> "Portfolio tracker is accurate and easy to use daily." ⭐ 5/5

## Action Ideas
1. Fix session persistence bug causing unexpected logouts on Android.
2. Optimise chart rendering to reduce load time by fifty percent.
3. Add sorting and filtering options to the portfolio view screen.
"""

_FROM = "pulse@example.com"
_TO = ["team@example.com"]
_SUBJECT = "📊 Groww App Weekly Pulse — 2026-03-10"


# ---------------------------------------------------------------------------
# Test 1: Dry-run writes a valid .eml file to the correct directory
# ---------------------------------------------------------------------------

def test_dry_run_writes_eml_file(tmp_path):
    """
    When run() is called WITHOUT --send, it must:
      - Create a pulse-YYYY-MM-DD.eml file in the output dir.
      - The file must be parseable as a valid RFC 822 message.
      - No SMTP connection must be made.
    """
    pulse_file = tmp_path / "pulse-2026-03-10.md"
    pulse_file.write_text(_SAMPLE_MARKDOWN, encoding="utf-8")
    reports_dir = tmp_path / "reports"

    with patch("smtplib.SMTP") as mock_smtp, patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
        result = phase4_run(
            pulse_path=pulse_file,
            send=False,  # dry-run
            output_dir=str(reports_dir),
            email_from=_FROM,
            email_to=_TO,
        )

    # --- Verify file was created ---
    assert result is not None, "Dry-run should return the path of the .eml file"
    assert result.exists(), f".eml file does not exist at {result}"
    assert result.suffix == ".eml", f"Expected .eml suffix, got {result.suffix}"
    assert result.parent == reports_dir, "File saved to wrong directory"

    # --- Verify the file is a valid RFC 822 message ---
    raw = result.read_bytes()
    parsed = email.message_from_bytes(raw)
    assert parsed["From"] == _FROM
    assert parsed["To"] == ", ".join(_TO)
    assert _decode_subject(parsed) == _SUBJECT, (
        f"Subject mismatch: {_decode_subject(parsed)!r} != {_SUBJECT!r}"
    )
    assert parsed.get_content_type() == "multipart/alternative"

    # --- Verify no SMTP connection was opened ---
    mock_smtp.assert_not_called()
    mock_smtp_ssl.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2: Send mode calls smtplib.SMTP with the correct host and port (587)
# ---------------------------------------------------------------------------

def test_send_mode_calls_smtp_correct_host_and_port(tmp_path):
    """
    When send=True and port=587, smtplib.SMTP must be called with the
    correct host and port. SMTP_SSL must NOT be called.
    """
    pulse_file = tmp_path / "pulse-2026-03-10.md"
    pulse_file.write_text(_SAMPLE_MARKDOWN, encoding="utf-8")

    mock_server = MagicMock()
    mock_server.__enter__ = MagicMock(return_value=mock_server)
    mock_server.__exit__ = MagicMock(return_value=False)

    with patch("phase4.emailer.smtplib.SMTP", return_value=mock_server) as mock_smtp_cls, \
         patch("phase4.emailer.smtplib.SMTP_SSL") as mock_smtp_ssl_cls:

        phase4_run(
            pulse_path=pulse_file,
            send=True,
            email_from=_FROM,
            email_to=_TO,
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="user@gmail.com",
            smtp_password="secret",
        )

    # SMTP should have been called with the right host and port
    mock_smtp_cls.assert_called_once_with("smtp.gmail.com", 587)

    # SMTP_SSL should NOT have been used for port 587
    mock_smtp_ssl_cls.assert_not_called()

    # login and sendmail must have been called on the server instance
    mock_server.login.assert_called_once_with("user@gmail.com", "secret")
    mock_server.sendmail.assert_called_once()


# ---------------------------------------------------------------------------
# Test 3: Send mode (port 465) calls smtplib.SMTP_SSL
# ---------------------------------------------------------------------------

def test_send_mode_ssl_port_465(tmp_path):
    """
    When port=465, smtplib.SMTP_SSL must be called instead of smtplib.SMTP.
    """
    pulse_file = tmp_path / "pulse-2026-03-10.md"
    pulse_file.write_text(_SAMPLE_MARKDOWN, encoding="utf-8")

    mock_server = MagicMock()
    mock_server.__enter__ = MagicMock(return_value=mock_server)
    mock_server.__exit__ = MagicMock(return_value=False)

    with patch("phase4.emailer.smtplib.SMTP_SSL", return_value=mock_server) as mock_ssl_cls, \
         patch("phase4.emailer.smtplib.SMTP") as mock_smtp_cls:

        phase4_run(
            pulse_path=pulse_file,
            send=True,
            email_from=_FROM,
            email_to=_TO,
            smtp_host="smtp.gmail.com",
            smtp_port=465,
            smtp_user="user@gmail.com",
            smtp_password="secret",
        )

    mock_ssl_cls.assert_called_once()
    # First positional args must be host and port
    call_args = mock_ssl_cls.call_args
    assert "smtp.gmail.com" in call_args[0]
    assert 465 in call_args[0]

    mock_smtp_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: build_message produces correct MIME structure
# ---------------------------------------------------------------------------

def test_build_message_mime_structure():
    """
    build_message() must return a multipart/alternative MIME message with
    exactly one text/plain and one text/html part.
    """
    msg = build_message(_SAMPLE_MARKDOWN, _SUBJECT, _FROM, _TO)

    assert msg["Subject"] == _SUBJECT
    assert msg["From"] == _FROM
    assert msg.get_content_type() == "multipart/alternative"

    parts = msg.get_payload()
    assert len(parts) == 2, f"Expected 2 MIME parts, got {len(parts)}"

    content_types = {p.get_content_type() for p in parts}
    assert "text/plain" in content_types, "Missing text/plain part"
    assert "text/html" in content_types, "Missing text/html part"


# ---------------------------------------------------------------------------
# Test 5: HTML part contains required structural elements
# ---------------------------------------------------------------------------

def test_html_part_contains_headings():
    """The HTML part must contain the main heading and section headings."""
    msg = build_message(_SAMPLE_MARKDOWN, _SUBJECT, _FROM, _TO)
    parts = msg.get_payload()
    html_part = next(p for p in parts if p.get_content_type() == "text/html")
    html_body = html_part.get_payload(decode=True).decode("utf-8")

    assert "<h1>" in html_body, "Missing <h1> heading in HTML"
    assert "<h2>" in html_body, "Missing <h2> headings in HTML"
    assert "Top 3 Themes" in html_body
    assert "Real User Quotes" in html_body
    assert "Action Ideas" in html_body
    assert "<blockquote" in html_body, "Quotes should be rendered as blockquotes"


# ---------------------------------------------------------------------------
# Test 6: write_eml creates the file and it parses correctly
# ---------------------------------------------------------------------------

def test_write_eml_creates_parseable_file(tmp_path):
    """write_eml() must create a file whose bytes parse as a valid email."""
    msg = build_message(_SAMPLE_MARKDOWN, _SUBJECT, _FROM, _TO)
    eml_path = tmp_path / "test.eml"

    result = write_eml(msg, eml_path)

    assert result == eml_path
    assert eml_path.exists()

    parsed = email.message_from_bytes(eml_path.read_bytes())
    assert _decode_subject(parsed) == _SUBJECT, (
        f"Subject mismatch: {_decode_subject(parsed)!r} != {_SUBJECT!r}"
    )
    assert parsed.is_multipart()
