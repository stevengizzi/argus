"""CLI entry point for the sprint runner.

Parses command-line arguments, loads configuration, and initializes the runner.
The actual execution loop comes in a later session.
"""

from __future__ import annotations

import argparse
import sys

from .config import RunnerConfig


def create_parser() -> argparse.ArgumentParser:
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


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = create_parser()
    args = parser.parse_args()

    # Load configuration
    try:
        config = RunnerConfig.from_yaml(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        return 1

    # Apply mode override if specified
    if args.mode:
        config.execution.mode = args.mode

    print("Runner initialized. Config loaded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
