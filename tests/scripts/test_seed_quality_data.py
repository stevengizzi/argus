"""Tests for the seed_quality_data.py production guard (Sprint 24.1 S1b — DEF-062)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = str(Path(__file__).resolve().parents[2] / "scripts" / "seed_quality_data.py")


def test_seed_script_without_dev_flag_exits_nonzero():
    """Running without --i-know-this-is-dev should exit 1."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--db", "/tmp/nonexistent.db"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "development only" in result.stdout


def test_seed_script_with_dev_flag_does_not_exit_early():
    """Running with --i-know-this-is-dev should pass the guard.

    The script will fail later because the DB doesn't exist, but the
    exit code should be 1 with a 'Database not found' message — not
    the production guard message.
    """
    result = subprocess.run(
        [sys.executable, SCRIPT, "--i-know-this-is-dev", "--db", "/tmp/nonexistent_seed_test.db"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Database not found" in result.stderr
    assert "development only" not in result.stdout
