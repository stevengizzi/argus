#!/usr/bin/env python3
"""
Batch re-validation of all remaining strategies using BacktestEngine.

Features:
  - Symbol filtering via symlinked cache: scans Parquet data once, builds
    metadata cache, creates per-strategy symlink directories with only
    qualifying symbols. Walk-forward auto-detects from filtered directory.
  - Resumable: skips strategies with matching date range results
  - Per-window progress: walk-forward window results shown in real time
  - Clean terminal: "No data" warnings go to log file
  - Thread-safe: sets single-threaded math to prevent C++ crashes

Usage:
    python3 scripts/revalidate_all.py
    python3 scripts/revalidate_all.py --cache-dir data/databento_cache
    python3 scripts/revalidate_all.py --force          # re-run all
    python3 scripts/revalidate_all.py --rebuild-meta    # rebuild symbol metadata

Results:  data/backtest_runs/validation/{strategy}_validation.json
Logs:     data/backtest_runs/validation/revalidation.log
Metadata: data/backtest_runs/validation/symbol_metadata.json
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from argus.core.config import load_yaml_file
from scripts.revalidate_strategy import run_validation, print_summary, parse_args

# Prevent C++ threading crashes on large datasets
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMBA_NUM_THREADS", "1")

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

STRATEGIES = [
    {"key": "orb",                  "name": "ORB Breakout",        "yaml": "orb_breakout",       "walk_forward": True},
    {"key": "orb_scalp",            "name": "ORB Scalp",           "yaml": "orb_scalp",           "walk_forward": True},
    {"key": "vwap_reclaim",         "name": "VWAP Reclaim",        "yaml": "vwap_reclaim",        "walk_forward": True},
    {"key": "afternoon_momentum",   "name": "Afternoon Momentum",  "yaml": "afternoon_momentum",  "walk_forward": True},
    {"key": "red_to_green",         "name": "Red-to-Green",        "yaml": "red_to_green",        "walk_forward": False},
    {"key": "flat_top_breakout",    "name": "Flat-Top Breakout",   "yaml": "flat_top_breakout",   "walk_forward": False},
]

WFE_THRESHOLD = 0.3


# ---------------------------------------------------------------------------
# Symbol metadata: one-time scan → cached JSON
# ---------------------------------------------------------------------------

def build_symbol_metadata(cache_dir: Path, output_path: Path) -> dict[str, dict]:
    """Scan Parquet cache, sample one recent file per symbol for price/volume."""
    metadata: dict[str, dict] = {}
    symbol_dirs = sorted([
        d for d in cache_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ])

    total = len(symbol_dirs)
    print(f"  Building symbol metadata: scanning {total} symbols...")
    start_time = time.monotonic()

    for i, sym_dir in enumerate(symbol_dirs):
        symbol = sym_dir.name
        parquet_files = sorted(sym_dir.glob("*.parquet"))

        if not parquet_files:
            continue

        data_months = len(parquet_files)

        try:
            df = pd.read_parquet(parquet_files[-1])
            if df.empty or "close" not in df.columns or "volume" not in df.columns:
                continue

            metadata[symbol] = {
                "median_close": float(df["close"].median()),
                "median_volume": float(df["volume"].median()),
                "data_months": data_months,
            }
        except Exception:
            continue

        if (i + 1) % 2000 == 0:
            elapsed = time.monotonic() - start_time
            rate = (i + 1) / elapsed
            eta = (total - i - 1) / rate
            print(f"    {i + 1}/{total} scanned ({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)")

    elapsed = time.monotonic() - start_time
    print(f"  Metadata: {len(metadata)} symbols with data (of {total} dirs) in {elapsed:.0f}s")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metadata, indent=2))
    print(f"  Cached → {output_path}")

    return metadata


def load_or_build_metadata(cache_dir: Path, output_dir: Path, force: bool = False) -> dict[str, dict]:
    meta_path = output_dir / "symbol_metadata.json"
    if meta_path.exists() and not force:
        print(f"  Loading cached symbol metadata from {meta_path}")
        metadata = json.loads(meta_path.read_text())
        print(f"  Loaded: {len(metadata)} symbols")
        return metadata
    return build_symbol_metadata(cache_dir, meta_path)


def filter_symbols_for_strategy(
    metadata: dict[str, dict],
    strategy_yaml: str,
    min_data_months: int = 6,
) -> list[str]:
    """Filter symbols using strategy's universe_filter criteria."""
    config_path = PROJECT_ROOT / "config" / "strategies" / f"{strategy_yaml}.yaml"
    yaml_config = load_yaml_file(config_path)
    uf = yaml_config.get("universe_filter", {})

    min_price = uf.get("min_price", 0)
    max_price = uf.get("max_price", float("inf"))

    # YAML min_avg_volume is daily, but Parquet median_volume is per-bar.
    # Per-bar doesn't scale linearly to daily (varies by time of day, stock).
    # Empirical calibration: 250 per-bar median ≈ liquid momentum stock.
    # This yields ~5,000-6,000 symbols, matching live UM routing scale.
    min_avg_volume = uf.get("min_avg_volume", 0)
    if min_avg_volume >= 1_000_000:
        min_bar_volume = 250
    elif min_avg_volume >= 500_000:
        min_bar_volume = 125
    else:
        min_bar_volume = 50

    qualifying = []
    for symbol, meta in metadata.items():
        price = meta["median_close"]
        volume = meta["median_volume"]
        months = meta["data_months"]

        if months < min_data_months:
            continue
        if price < min_price or price > max_price:
            continue
        if volume < min_bar_volume:
            continue

        # Skip non-equity symbols (warrants, units, preferred, SPACs)
        if any(c in symbol for c in [" ", "+", "=", "-"]):
            continue
        if len(symbol) > 4 and symbol.endswith("W"):
            continue
        if len(symbol) > 4 and symbol.endswith("U"):
            continue

        qualifying.append(symbol)

    return sorted(qualifying)


def create_filtered_cache(
    cache_dir: Path,
    filtered_dir: Path,
    symbols: list[str],
) -> Path:
    """Create a directory of symlinks to only the qualifying symbol dirs.

    Walk-forward auto-detects symbols from its data_dir, so a filtered
    symlink directory is the simplest way to inject a symbol filter
    without modifying walk_forward.py or revalidate_strategy.py.
    """
    # Clean previous
    if filtered_dir.exists():
        shutil.rmtree(filtered_dir)
    filtered_dir.mkdir(parents=True)

    linked = 0
    for symbol in symbols:
        src = cache_dir / symbol
        dst = filtered_dir / symbol
        if src.exists():
            dst.symlink_to(src.resolve())
            linked += 1

    return filtered_dir


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

class WalkForwardProgressFilter(logging.Filter):
    _PROGRESS_PREFIXES = (
        "Window ",
        "Fixed-params walk-forward:",
        "Generated ",
        "Fixed-params walk-forward complete:",
        "Loaded data:",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno >= logging.ERROR:
            return True
        if record.name == "argus.backtest.walk_forward" and record.levelno == logging.INFO:
            return any(record.getMessage().startswith(p) for p in self._PROGRESS_PREFIXES)
        if record.name == "argus.backtest.engine" and record.levelno == logging.INFO:
            msg = record.getMessage()
            return "Running" in msg or "complete" in msg.lower()
        return False


def setup_logging(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "revalidation.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    fh = logging.FileHandler(log_path, mode="a")
    fh.setLevel(logging.WARNING)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    root.addHandler(fh)

    wf_fh = logging.FileHandler(log_path, mode="a")
    wf_fh.setLevel(logging.INFO)
    wf_fh.addFilter(logging.Filter("argus.backtest.walk_forward"))
    wf_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    root.addHandler(wf_fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.addFilter(WalkForwardProgressFilter())
    ch.setFormatter(logging.Formatter("  %(message)s"))
    root.addHandler(ch)

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
        return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"


def is_already_completed(output_dir: Path, strategy_name: str, start: str, end: str) -> bool:
    json_path = output_dir / f"{strategy_name}_validation.json"
    if not json_path.exists():
        return False
    try:
        data = json.loads(json_path.read_text())
        dr = data.get("date_range", {})
        return dr.get("start") == start and dr.get("end") == end
    except (json.JSONDecodeError, KeyError):
        return False


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
    rebuild_meta: bool,
) -> list[dict[str, Any]]:

    cache_path = Path(cache_dir).resolve()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    filtered_base = output_path / "_filtered_cache"

    metadata = load_or_build_metadata(cache_path, output_path, force=rebuild_meta)

    to_run = []
    skipped = []
    for strat in STRATEGIES:
        if not force and is_already_completed(output_path, strat["yaml"], start, end):
            skipped.append(strat)
        else:
            to_run.append(strat)

    # Pre-compute filtered symbols
    for strat in STRATEGIES:
        symbols = filter_symbols_for_strategy(metadata, strat["yaml"])
        strat["_symbols"] = symbols

    print("\n" + "=" * 70)
    print("ARGUS BATCH RE-VALIDATION")
    print("=" * 70)
    print(f"  Date range:  {start} to {end}")
    print(f"  Cache dir:   {cache_dir}")
    print(f"  Output dir:  {output_dir}")
    print(f"  Metadata:    {len(metadata)} symbols with data")
    print(f"  Strategies:  {len(to_run)} to run, {len(skipped)} already complete")

    for strat in STRATEGIES:
        marker = "  ✓ " if strat in skipped else "  → "
        print(f"  {marker}{strat['name']:<25} {len(strat['_symbols']):>5} symbols")

    if skipped:
        print(f"\n  Skipped strategies have existing results (use --force to re-run)")

    if not to_run:
        print(f"\n  All strategies already validated!")
        results = []
        for strat in STRATEGIES:
            jp = output_path / f"{strat['yaml']}_validation.json"
            if jp.exists():
                results.append(json.loads(jp.read_text()))
        print_consolidated(results, 0)
        return results

    print("=" * 70)

    results: list[dict[str, Any]] = []
    elapsed_times: list[float] = []
    total_start = time.monotonic()

    for i, strat in enumerate(to_run, 1):
        key = strat["key"]
        name = strat["name"]
        symbols = strat["_symbols"]
        remaining = len(to_run) - i
        strat_start = time.monotonic()

        if elapsed_times:
            avg_time = sum(elapsed_times) / len(elapsed_times)
            eta_str = f"~{format_duration(avg_time * (remaining + 1))} remaining"
        else:
            eta_str = "estimating after first strategy..."

        # Create filtered symlink cache for this strategy
        strat_filtered = filtered_base / key
        create_filtered_cache(cache_path, strat_filtered, symbols)

        print(f"\n{'━' * 70}")
        print(f"  [{i}/{len(to_run)}]  {name}")
        print(f"  {'─' * 64}")
        print(f"  Walk-forward:  {'Yes (IS+OOS per window)' if strat['walk_forward'] else 'No (BacktestEngine-only)'}")
        print(f"  Symbols:       {len(symbols)} (filtered from {len(metadata)})")
        print(f"  Started:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  ETA:           {eta_str}")
        print(f"  {'─' * 64}")

        try:
            args = parse_args([
                "--strategy", key,
                "--start", start,
                "--end", end,
                "--cache-dir", str(strat_filtered),
                "--output-dir", output_dir,
                "--is-months", str(is_months),
                "--oos-months", str(oos_months),
                "--step-months", str(step_months),
                "--min-trades", str(min_trades),
                "--log-level", "INFO",
            ])

            output = await run_validation(args)
            print_summary(output)

            elapsed = time.monotonic() - strat_start
            elapsed_times.append(elapsed)
            output["_elapsed"] = elapsed
            output["_error"] = None
            output["_symbol_count"] = len(symbols)
            results.append(output)

            print(f"\n  ✓ {name} completed in {format_duration(elapsed)}")

        except Exception as e:
            elapsed = time.monotonic() - strat_start
            elapsed_times.append(elapsed)
            logging.getLogger(__name__).error("Strategy %s failed: %s", key, e, exc_info=True)
            results.append({
                "strategy": strat["yaml"],
                "strategy_type": key,
                "status": "ERROR",
                "new_results": {},
                "_elapsed": elapsed,
                "_error": str(e),
                "_symbol_count": len(symbols),
            })
            print(f"\n  ✗ {name} FAILED after {format_duration(elapsed)}: {e}")
            print(f"  Continuing with next strategy...")
        finally:
            # Cleanup symlinks
            if strat_filtered.exists():
                shutil.rmtree(strat_filtered)

    # Cleanup filtered cache base dir
    if filtered_base.exists():
        shutil.rmtree(filtered_base)

    # Load skipped
    for strat in skipped:
        jp = output_path / f"{strat['yaml']}_validation.json"
        if jp.exists():
            data = json.loads(jp.read_text())
            data["_elapsed"] = 0
            data["_error"] = None
            data["_skipped"] = True
            results.append(data)

    total_elapsed = time.monotonic() - total_start
    print_consolidated(results, total_elapsed)
    write_consolidated_json(results, output_path, start, end, cache_dir, total_elapsed)

    return results


def print_consolidated(results: list[dict[str, Any]], total_elapsed: float) -> None:
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


def write_consolidated_json(results, output_path, start, end, cache_dir, total_elapsed):
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
                "symbols_tested": r.get("_symbol_count"),
            }
            for r in sorted(results, key=lambda x: x.get("strategy", ""))
        ],
    }
    path = output_path / "consolidated_validation.json"
    path.write_text(json.dumps(consolidated, indent=2, default=str))
    print(f"\nConsolidated results: {path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Batch re-validate all 6 remaining strategies.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Resume: auto-skips completed strategies. Re-run after Ctrl+C.\n"
            "Filtering: builds metadata from Parquet (cached), filters per-strategy\n"
            "  using universe_filter YAML. Typically 24K → 2-3K symbols.\n"
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
    parser.add_argument("--force", action="store_true", help="Re-run all strategies")
    parser.add_argument("--rebuild-meta", action="store_true", help="Rebuild symbol metadata cache")

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
        rebuild_meta=args.rebuild_meta,
    ))


if __name__ == "__main__":
    main()