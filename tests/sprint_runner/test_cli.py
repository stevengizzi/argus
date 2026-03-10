"""Tests for CLI helper module."""

from __future__ import annotations

import io
import sys

import pytest


class TestCliModuleImports:
    """Tests for CLI module import functionality."""

    def test_cli_module_imports(self) -> None:
        """Verify all expected exports can be imported from cli module."""
        from scripts.sprint_runner.cli import (
            Colors,
            build_argument_parser,
            print_error,
            print_header,
            print_progress,
            print_success,
            print_summary_table,
            print_warning,
        )

        # Verify all are not None
        assert Colors is not None
        assert build_argument_parser is not None
        assert print_error is not None
        assert print_header is not None
        assert print_progress is not None
        assert print_success is not None
        assert print_summary_table is not None
        assert print_warning is not None


class TestBuildArgumentParser:
    """Tests for argument parser construction."""

    def test_build_argument_parser(self) -> None:
        """Parser has expected arguments."""
        from scripts.sprint_runner.cli import build_argument_parser

        parser = build_argument_parser()

        # Check prog name
        assert parser.prog == "sprint-runner"

        # Parse with required --config
        args = parser.parse_args(["--config", "test.yaml"])
        assert args.config == "test.yaml"

        # Check boolean flags exist
        args = parser.parse_args(["--config", "test.yaml", "--resume"])
        assert args.resume is True

        args = parser.parse_args(["--config", "test.yaml", "--pause"])
        assert args.pause is True

        args = parser.parse_args(["--config", "test.yaml", "--dry-run"])
        assert getattr(args, "dry_run") is True

    def test_parser_has_from_session_option(self) -> None:
        """Parser has --from-session option."""
        from scripts.sprint_runner.cli import build_argument_parser

        parser = build_argument_parser()
        args = parser.parse_args(["--config", "test.yaml", "--from-session", "S3"])
        assert getattr(args, "from_session") == "S3"

    def test_parser_has_skip_session_option(self) -> None:
        """Parser has --skip-session option that can be repeated."""
        from scripts.sprint_runner.cli import build_argument_parser

        parser = build_argument_parser()
        args = parser.parse_args([
            "--config", "test.yaml",
            "--skip-session", "S2",
            "--skip-session", "S4",
        ])
        assert getattr(args, "skip_session") == ["S2", "S4"]

    def test_parser_has_stop_after_option(self) -> None:
        """Parser has --stop-after option."""
        from scripts.sprint_runner.cli import build_argument_parser

        parser = build_argument_parser()
        args = parser.parse_args(["--config", "test.yaml", "--stop-after", "S5"])
        assert getattr(args, "stop_after") == "S5"

    def test_parser_has_mode_option(self) -> None:
        """Parser has --mode option with valid choices."""
        from scripts.sprint_runner.cli import build_argument_parser

        parser = build_argument_parser()
        args = parser.parse_args(["--config", "test.yaml", "--mode", "autonomous"])
        assert args.mode == "autonomous"

        args = parser.parse_args(["--config", "test.yaml", "--mode", "human-in-the-loop"])
        assert args.mode == "human-in-the-loop"


class TestPrintFunctionsCallable:
    """Tests for print function callability."""

    def test_print_functions_callable(self) -> None:
        """All print_* functions are callable without error."""
        from scripts.sprint_runner.cli import (
            print_error,
            print_header,
            print_progress,
            print_success,
            print_summary_table,
            print_warning,
        )

        # Redirect stdout/stderr to capture output
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        try:
            # These should not raise
            print_header("Test Header")
            print_progress(1, 5, "S1", "RUNNING")
            print_summary_table([("S1", "CLEAR", 5, "1m 30s")])
            print_error("Test error")
            print_warning("Test warning")
            print_success("Test success")
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def test_print_progress_status_colors(self) -> None:
        """Print progress handles different status values."""
        from scripts.sprint_runner.cli import print_progress

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            # Test various statuses
            print_progress(1, 5, "S1", "PENDING")
            print_progress(2, 5, "S2", "RUNNING")
            print_progress(3, 5, "S3", "COMPLETE")
            print_progress(4, 5, "S4", "FAILED")
            print_progress(5, 5, "S5", "SKIPPED")
            print_progress(5, 5, "S6", "UNKNOWN")  # Fallback to WHITE
        finally:
            sys.stdout = old_stdout

    def test_print_summary_table_with_various_data(self) -> None:
        """Print summary table handles various data scenarios."""
        from scripts.sprint_runner.cli import print_summary_table

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            # Test with positive test delta
            print_summary_table([("S1", "CLEAR", 10, "2m 30s")])

            # Test with negative test delta
            print_summary_table([("S2", "CONCERNS", -2, "1m")])

            # Test with None values
            print_summary_table([("S3", "SKIPPED", None, None)])

            # Test with zero delta
            print_summary_table([("S4", "COMPLETE", 0, "30s")])
        finally:
            sys.stdout = old_stdout


class TestColorsClass:
    """Tests for Colors class."""

    def test_colors_has_required_attributes(self) -> None:
        """Colors class has all required ANSI code attributes."""
        from scripts.sprint_runner.cli import Colors

        # Basic attributes
        assert hasattr(Colors, "RESET")
        assert hasattr(Colors, "BOLD")
        assert hasattr(Colors, "DIM")

        # Foreground colors
        assert hasattr(Colors, "RED")
        assert hasattr(Colors, "GREEN")
        assert hasattr(Colors, "YELLOW")
        assert hasattr(Colors, "BLUE")
        assert hasattr(Colors, "MAGENTA")
        assert hasattr(Colors, "CYAN")
        assert hasattr(Colors, "WHITE")

        # Background colors
        assert hasattr(Colors, "BG_RED")
        assert hasattr(Colors, "BG_GREEN")
        assert hasattr(Colors, "BG_YELLOW")
        assert hasattr(Colors, "BG_BLUE")

    def test_colors_are_ansi_escape_sequences(self) -> None:
        """Color values are valid ANSI escape sequences."""
        from scripts.sprint_runner.cli import Colors

        assert Colors.RESET.startswith("\033[")
        assert Colors.BOLD.startswith("\033[")
        assert Colors.RED.startswith("\033[")
