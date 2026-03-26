#!/usr/bin/env python3
"""
Batch re-validation of all remaining strategies using BacktestEngine.

Features:
  - Resumable: skips strategies that already have results with matching date range
  - Per-window progress: shows IS/OOS results for each walk-forward window
  - Clean terminal: "No data for X" warnings go to log file, not console
  - ETA tracking after first strategy completes

Usage:
    python3 scripts/revalidate_all_strategies.py
    python3 scripts/revalidate_all_strategies.py --cache-dir data/databento_cache
    python3 scripts/revalidate_all_strategies.py --force   # re-run even if results exist

Results:  data/backtest_runs/validation/{strategy}_validation.json
Logs:     data/backtest_runs/validation/revalidation.log
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.revalidate_strategy import run_validation, print_summary, parse_args

# ---------------------------------------------------------------------------
# The 6 strategies to validate (Bull Flag already validated in Sprint 21.6)
# ---------------------------------------------------------------------------

STRATEGIES = [
    {"key": "orb",                  "name": "ORB Breakout",        "walk_forward": True},
    {"key": "orb_scalp",            "name": "ORB Scalp",           "walk_forward": True},
    {"key": "vwap_reclaim",         "name": "VWAP Reclaim",        "walk_forward": True},
    {"key": "afternoon_momentum",   "name": "Afternoon Momentum",  "walk_forward": True},
    {"key": "red_to_green",         "name": "Red-to-Green",        "walk_forward": False},
    {"key": "flat_top_breakout",    "name": "Flat-Top Breakout",   "walk_forward": False},
]

WFE_THRESHOLD = 0.3


# ---------------------------------------------------------------------------
# Custom logging: per-window progress to console, noise to file
# ---------------------------------------------------------------------------

class WalkForwardProgressFilter(logging.Filter):
    """Only allow walk-forward window progress messages through to console."""

    _PROGRESS_PREFIXES = (
        "Window ",
        "Fixed-params walk-forward:",
        "Generated ",
        "Fixed-params walk-forward complete:",
    )

    _PROGRESS_MODULES = (
        "argus.backtest.walk_forward",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        # Always show errors
        if record.levelno >= logging.ERROR:
            return True
        # Show walk-forward progress at INFO level
        if record.name in self._PROGRESS_MODULES and record.levelno == logging.INFO:
            msg = record.getMessage()
            if any(msg.startswith(p) for p in self._PROGRESS_PREFIXES):
                return True
        # Show BacktestEngine-level progress
        if record.name == "argus.backtest.engine" and record.levelno == logging.INFO:
            msg = record.getMessage()
            if "Running" in msg or "complete" in msg.lower() or "days" in msg:
                return True
        return False


class CleanProgressFormatter(logging.Formatter):
    """Format progress messages with indentation for readability."""

    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()
        if record.levelno >= logging.ERROR:
            return f"  ⚠ {msg}"
        # Indent walk-forward window messages
        return f"  {msg}"


def setup_logging(output_dir: Path) -> None:
    """Route detailed logs to file, only progress to console."""
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "revalidation.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    # Clear any existing handlers
    root.handlers.clear()

    # File handler — WARNING+ (captures "No data" warnings for post-analysis)
    file_handler = logging.FileHandler(log_path, mode="a")
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    root.addHandler(file_handler)

    # Also log INFO from walk_forward to file for complete record
    wf_file_handler = logging.FileHandler(log_path, mode="a")
    wf_file_handler.setLevel(logging.INFO)
    wf_file_handler.addFilter(logging.Filter("argus.backtest.walk_forward"))
    wf_file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    root.addHandler(wf_file_handler)

    # Console handler — selective progress only
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.addFilter(WalkForwardProgressFilter())
    console_handler.setFormatter(CleanProgressFormatter())
    root.addHandler(console_handler)

    print(f"  Detailed logs → {log_path}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def is_already_completed(output_dir: Path, strategy_name: str, start: str, end: str) -> bool:
    """Check if a valid result file exists with matching date range."""
    json_path = output_dir / f"{strategy_name}_validation.json"
    if not json_path.exists():
        return False
    try:
        data = json.loads(json_path.read_text())
        dr = data.get("date_range", {})
        return dr.get("start") == start and dr.get("end") == end
    except (json.JSONDecodeError, KeyError):
        return False


def get_strategy_yaml_name(key: str) -> str:
    """Map strategy key to YAML config filename."""
    return {
        "orb": "orb_breakout", "orb_scalp": "orb_scalp",
        "vwap_reclaim": "vwap_reclaim", "afternoon_momentum": "afternoon_momentum",
        "red_to_green": "red_to_green", "bull_flag": "bull_flag",
        "flat_top_breakout": "flat_top_breakout",
    }.get(key, key)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run_all(
    cache_dir: str,
    output_dir: str,
    start: str,
    end: str,
    is_months: int,
    oos_months: int,
    step_months: int,
    min_trades: int,
    force: bool,
) -> list[dict[str, Any]]:
    """Run all strategy validations serially with resume support."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Determine what needs to run
    to_run = []
    skipped = []
    for strat in STRATEGIES:
        yaml_name = get_strategy_yaml_name(strat["key"])
        if not force and is_already_completed(output_path, yaml_name, start, end):
            skipped.append(strat)
        else:
            to_run.append(strat)

    print("\n" + "=" * 70)
    print("ARGUS BATCH RE-VALIDATION")
    print("=" * 70)
    print(f"  Date range:  {start} to {end}")
    print(f"  Cache dir:   {cache_dir}")
    print(f"  Output dir:  {output_dir}")
    print(f"  Strategies:  {len(to_run)} to run, {len(skipped)} already complete")

    if skipped:
        print(f"  Skipping:    {', '.join(s['name'] for s in skipped)}")
        print(f"               (use --force to re-run)")

    if not to_run:
        print(f"\n  All strategies already validated for this date range!")
        print(f"  Use --force to re-run.\n")
        results = []
        for strat in STRATEGIES:
            yaml_name = get_strategy_yaml_name(strat["key"])
            json_path = output_path / f"{yaml_name}_validation.json"
            if json_path.exists():
                results.append(json.loads(json_path.read_text()))
        print_consolidated(results, 0)
        return results

    print("=" * 70)

    results: list[dict[str, Any]] = []
    elapsed_times: list[float] = []
    total_start = time.monotonic()

    for i, strat in enumerate(to_run, 1):
        key = strat["key"]
        name = strat["name"]
        remaining = len(to_run) - i
        strat_start = time.monotonic()

        # ETA
        if elapsed_times:
            avg_time = sum(elapsed_times) / len(elapsed_times)
            eta_str = f"~{format_duration(avg_time * (remaining + 1))} remaining"
        else:
            eta_str = "estimating after first strategy..."

        print(f"\n{'━' * 70}")
        print(f"  [{i}/{len(to_run)}]  {name}")
        print(f"  {'─' * 64}")
        print(f"  Walk-forward:  {'Yes (IS+OOS per window)' if strat['walk_forward'] else 'No (BacktestEngine-only, single window)'}")
        print(f"  Started:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  ETA:           {eta_str}")
        print(f"  {'─' * 64}")

        try:
            args = parse_args([
                "--strategy", key,
                "--start", start,
                "--end", end,
                "--cache-dir", cache_dir,
                "--output-dir", output_dir,
                "--is-months", str(is_months),
                "--oos-months", str(oos_months),
                "--step-months", str(step_months),
                "--min-trades", str(min_trades),
                "--log-level", "INFO",  # walk_forward needs INFO for window logging
            ])

            output = await run_validation(args)
            print_summary(output)

            elapsed = time.monotonic() - strat_start
            elapsed_times.append(elapsed)
            output["_elapsed"] = elapsed
            output["_error"] = None
            results.append(output)

            print(f"\n  ✓ {name} completed in {format_duration(elapsed)}")

        except Exception as e:
            elapsed = time.monotonic() - strat_start
            elapsed_times.append(elapsed)
            logging.getLogger(__name__).error(
                "Strategy %s failed: %s", key, e, exc_info=True
            )
            results.append({
                "strategy": key,
                "strategy_type": key,
                "status": "ERROR",
                "new_results": {},
                "_elapsed": elapsed,
                "_error": str(e),
            })
            print(f"\n  ✗ {name} FAILED after {format_duration(elapsed)}: {e}")
            print(f"  Continuing with next strategy...")

    # Load skipped results for consolidated summary
    for strat in skipped:
        yaml_name = get_strategy_yaml_name(strat["key"])
        json_path = output_path / f"{yaml_name}_validation.json"
        if json_path.exists():
            data = json.loads(json_path.read_text())
            data["_elapsed"] = 0
            data["_error"] = None
            data["_skipped"] = True
            results.append(data)

    total_elapsed = time.monotonic() - total_start
    print_consolidated(results, total_elapsed)
    write_consolidated_json(results, output_path, start, end, cache_dir, total_elapsed)

    return results


def print_consolidated(results: list[dict[str, Any]], total_elapsed: float) -> None:
    """Print the final summary table."""
    print("\n\n" + "=" * 70)
    print("CONSOLIDATED RESULTS")
    print("=" * 70)
    print(f"{'Strategy':<25} {'Status':<18} {'OOS Sharpe':>12} {'WFE':>8} {'Trades':>8} {'Time':>8}")
    print("─" * 70)

    passed = failed = errors = zero = 0

    for r in sorted(results, key=lambda x: x.get("strategy", "")):
        name = r.get("strategy", r.get("strategy_type", "?"))
        status = r.get("status", "ERROR")
        new = r.get("new_results", {})
        elapsed = r.get("_elapsed", 0)
        error = r.get("_error")
        was_skipped = r.get("_skipped", False)

        sharpe_str = f"{new['oos_sharpe']:.2f}" if new.get("oos_sharpe") is not None else "N/A"
        wfe_str = f"{new['wfe_pnl']:.2f}" if new.get("wfe_pnl") is not None else "N/A"
        trades_str = str(new.get("total_oos_trades", "N/A"))
        time_str = "(cached)" if was_skipped else format_duration(elapsed)

        if error:
            icon = "💥 ERROR";    errors += 1
        elif status == "PASS":
            icon = "✅ PASS";     passed += 1
        elif status == "NEW_BASELINE":
            icon = "🆕 BASELINE"; passed += 1
        elif status in ("PASS_DIVERGENT", "DIVERGENT"):
            icon = "⚠️  DIVERGENT"; passed += 1
        elif status == "ZERO_TRADES":
            icon = "⬚  NO TRADES"; zero += 1
        elif status in ("WFE_BELOW_THRESHOLD", "FAIL"):
            icon = "❌ FAIL";     failed += 1
        else:
            icon = f"❓ {status}"

        print(f"{name:<25} {icon:<18} {sharpe_str:>12} {wfe_str:>8} {trades_str:>8} {time_str:>8}")

    print("─" * 70)
    parts = []
    if passed: parts.append(f"{passed} passed")
    if failed: parts.append(f"{failed} failed")
    if zero: parts.append(f"{zero} zero-trades")
    if errors: parts.append(f"{errors} errors")

    if total_elapsed > 0:
        print(f"Total: {', '.join(parts)}  |  {format_duration(total_elapsed)} elapsed")
    else:
        print(f"Total: {', '.join(parts)}")
    print(f"WFE threshold (DEC-047): {WFE_THRESHOLD}")
    print("=" * 70)

    if failed:
        print(f"\n⚠️  {failed} strategy(ies) below WFE threshold.")
    if zero:
        print(f"\n⬚  {zero} strategy(ies) produced zero trades — likely BacktestEngine simulation gap.")
    if errors:
        print(f"\n💥 {errors} strategy(ies) errored out. Check revalidation.log for details.")
    if passed == len(results) and not failed and not errors and not zero:
        print(f"\n🎉 All {len(results)} strategies validated! DEC-132 can be marked RESOLVED.")


def write_consolidated_json(
    results: list[dict[str, Any]],
    output_path: Path,
    start: str,
    end: str,
    cache_dir: str,
    total_elapsed: float,
) -> None:
    """Write consolidated results JSON."""
    consolidated = {
        "timestamp": datetime.now().isoformat(),
        "date_range": {"start": start, "end": end},
        "cache_dir": cache_dir,
        "total_elapsed_seconds": total_elapsed,
        "summary": {
            "passed": sum(1 for r in results if r.get("status") in ("PASS", "NEW_BASELINE", "PASS_DIVERGENT")),
            "failed": sum(1 for r in results if r.get("status") in ("WFE_BELOW_THRESHOLD", "FAIL")),
            "zero_trades": sum(1 for r in results if r.get("status") == "ZERO_TRADES"),
            "errors": sum(1 for r in results if r.get("_error")),
        },
        "strategies": [
            {
                "strategy": r.get("strategy"),
                "status": r.get("status"),
                "oos_sharpe": r.get("new_results", {}).get("oos_sharpe"),
                "wfe_pnl": r.get("new_results", {}).get("wfe_pnl"),
                "total_oos_trades": r.get("new_results", {}).get("total_oos_trades"),
                "elapsed_seconds": r.get("_elapsed"),
                "error": r.get("_error"),
            }
            for r in sorted(results, key=lambda x: x.get("strategy", ""))
        ],
    }
    path = output_path / "consolidated_validation.json"
    path.write_text(json.dumps(consolidated, indent=2, default=str))
    print(f"\nConsolidated results: {path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Batch re-validate all 6 remaining strategies.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Resume support:\n"
            "  The script automatically skips strategies that already have\n"
            "  a result file with a matching date range. Just re-run after\n"
            "  Ctrl+C and it picks up where it left off.\n\n"
            "  Use --force to re-run all strategies regardless.\n"
        ),
    )
    parser.add_argument("--cache-dir", default="data/databento_cache")
    parser.add_argument("--output-dir", default="data/backtest_runs/validation")
    parser.add_argument("--start", default="2018-06-01")
    parser.add_argument("--end", default="2026-03-01")
    parser.add_argument("--is-months", type=int, default=4)
    parser.add_argument("--oos-months", type=int, default=2)
    parser.add_argument("--step-months", type=int, default=2)
    parser.add_argument("--min-trades", type=int, default=20)
    parser.add_argument("--force", action="store_true", help="Re-run all strategies even if results exist")

    args = parser.parse_args()

    setup_logging(Path(args.output_dir))

    asyncio.run(run_all(
        cache_dir=args.cache_dir,
        output_dir=args.output_dir,
        start=args.start,
        end=args.end,
        is_months=args.is_months,
        oos_months=args.oos_months,
        step_months=args.step_months,
        min_trades=args.min_trades,
        force=args.force,
    ))


if __name__ == "__main__":
    main()