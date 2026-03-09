"""
tests/test_cli.py
------------------
Unit tests for main.py CLI argument parsing.
No phase pipelines are actually invoked — only `build_parser` + `parse_args` is tested.
"""

from __future__ import annotations

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import build_parser


def _parse(args: list[str]):
    return build_parser().parse_args(args)


# ---------------------------------------------------------------------------
# Test 1: defaults — no arguments
# ---------------------------------------------------------------------------

def test_defaults_no_args():
    args = _parse([])
    assert args.phase == "all"
    assert args.weeks == 12
    assert args.send is False


# ---------------------------------------------------------------------------
# Test 2: --phase all --weeks 8 --send
# ---------------------------------------------------------------------------

def test_phase_all_weeks_send():
    args = _parse(["--phase", "all", "--weeks", "8", "--send"])
    assert args.phase == "all"
    assert args.weeks == 8
    assert args.send is True


# ---------------------------------------------------------------------------
# Test 3: single phase (Phase 1)
# ---------------------------------------------------------------------------

def test_phase_single_one():
    args = _parse(["--phase", "1"])
    assert args.phase == "1"
    assert args.send is False


# ---------------------------------------------------------------------------
# Test 4: --phase 4 --send
# ---------------------------------------------------------------------------

def test_phase_four_with_send():
    args = _parse(["--phase", "4", "--send"])
    assert args.phase == "4"
    assert args.send is True


# ---------------------------------------------------------------------------
# Test 5: invalid phase value raises SystemExit
# ---------------------------------------------------------------------------

def test_invalid_phase_raises_system_exit():
    with pytest.raises(SystemExit):
        _parse(["--phase", "99"])


# ---------------------------------------------------------------------------
# Test 6: --weeks accepts arbitrary int
# ---------------------------------------------------------------------------

def test_custom_weeks():
    args = _parse(["--weeks", "4"])
    assert args.weeks == 4


# ---------------------------------------------------------------------------
# Test 7: --app-id override
# ---------------------------------------------------------------------------

def test_app_id_override():
    args = _parse(["--app-id", "com.example.myapp"])
    assert args.app_id == "com.example.myapp"


# ---------------------------------------------------------------------------
# Test 8: all valid phase values are accepted
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("phase", ["1", "2", "3", "4", "all"])
def test_all_valid_phase_values(phase):
    args = _parse(["--phase", phase])
    assert args.phase == phase
