"""Tests for sprint runner CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


class TestCLI:
    """Tests for CLI argument parsing."""

    def test_help_works(self) -> None:
        """Test that --help works and shows usage."""
        result = subprocess.run(
            [sys.executable, "scripts/sprint-runner.py", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parents[2],  # repo root
        )

        assert result.returncode == 0
        assert "sprint-runner" in result.stdout
        assert "--config" in result.stdout
        assert "--resume" in result.stdout
        assert "--dry-run" in result.stdout
        assert "--mode" in result.stdout

    def test_config_required(self) -> None:
        """Test that --config is required."""
        result = subprocess.run(
            [sys.executable, "scripts/sprint-runner.py"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parents[2],
        )

        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "config" in result.stderr.lower()

    def test_config_loads(self, valid_config_file: Path) -> None:
        """Test that valid config loads successfully."""
        result = subprocess.run(
            [sys.executable, "scripts/sprint-runner.py", "--config", str(valid_config_file)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parents[2],
        )

        assert result.returncode == 0
        assert "Runner initialized" in result.stdout
