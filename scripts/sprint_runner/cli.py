"""CLI helpers for the sprint runner.

Contains terminal output utilities and argument parser construction.
"""

from __future__ import annotations

import argparse
import sys

# ---------------------------------------------------------------------------
# Terminal Colors
# ---------------------------------------------------------------------------


class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


# ---------------------------------------------------------------------------
# Print Functions
# ---------------------------------------------------------------------------


def print_header(text: str) -> None:
    """Print a header line."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}", flush=True)
    print(f"{Colors.BOLD}{Colors.CYAN}{text:^60}{Colors.RESET}", flush=True)
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}\n", flush=True)


def print_progress(
    current: int, total: int, session_id: str, status: str
) -> None:
    """Print a progress line."""
    status_colors = {
        "PENDING": Colors.DIM,
        "RUNNING": Colors.YELLOW,
        "COMPLETE": Colors.GREEN,
        "FAILED": Colors.RED,
        "SKIPPED": Colors.MAGENTA,
    }
    color = status_colors.get(status, Colors.WHITE)
    bar = f"[{current}/{total}]"
    msg = f"{Colors.BOLD}{bar}{Colors.RESET} Session {session_id}: {color}{status}{Colors.RESET}"
    print(msg, flush=True)


def print_summary_table(
    sessions: list[tuple[str, str, int | None, str | None]]
) -> None:
    """Print a summary table of session results.

    Args:
        sessions: List of (session_id, verdict, test_delta, duration).
    """
    header = f"{'Session':<12} {'Verdict':<12} {'Tests':<12} {'Duration':<12}"
    print(f"\n{Colors.BOLD}{header}{Colors.RESET}")
    print("-" * 48)
    for session_id, verdict, test_delta, duration in sessions:
        verdict_color = {
            "CLEAR": Colors.GREEN,
            "CONCERNS": Colors.YELLOW,
            "ESCALATE": Colors.RED,
            "COMPLETE": Colors.GREEN,
            "SKIPPED": Colors.MAGENTA,
        }.get(verdict, Colors.WHITE)

        delta_str = f"+{test_delta}" if test_delta and test_delta > 0 else str(test_delta or "-")
        duration_str = duration or "-"
        print(
            f"{session_id:<12} {verdict_color}{verdict:<12}{Colors.RESET} "
            f"{delta_str:<12} {duration_str:<12}"
        )


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}{Colors.BOLD}ERROR:{Colors.RESET} {message}", file=sys.stderr)


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}WARNING:{Colors.RESET} {message}", flush=True)


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}{Colors.BOLD}SUCCESS:{Colors.RESET} {message}", flush=True)


# ---------------------------------------------------------------------------
# Argument Parser
# ---------------------------------------------------------------------------


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the argument parser.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        prog="sprint-runner",
        description="ARGUS Autonomous Sprint Runner — drives sprint execution via Claude Code CLI",
    )

    parser.add_argument(
        "--config",
        required=True,
        help="Path to the runner configuration YAML file",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing run state (clears stale lock if needed)",
    )

    parser.add_argument(
        "--pause",
        action="store_true",
        help="Pause the runner after the current session completes",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and print session plan without executing",
    )

    parser.add_argument(
        "--from-session",
        type=str,
        metavar="SESSION_ID",
        help="Start from a specific session (skip prior sessions)",
    )

    parser.add_argument(
        "--skip-session",
        type=str,
        action="append",
        metavar="SESSION_ID",
        help="Skip specific session(s) (can be specified multiple times)",
    )

    parser.add_argument(
        "--stop-after",
        type=str,
        metavar="SESSION_ID",
        help="Stop after completing the specified session",
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["autonomous", "human-in-the-loop"],
        help="Override execution mode from config",
    )

    return parser
