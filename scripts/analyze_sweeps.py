#!/usr/bin/env python3
"""Analyze sweep results from individual SQLite backtest files.

Queries ``data/backtest_runs/`` for per-run SQLite databases produced by
``run_experiment.py`` and generates a Markdown summary with per-pattern
metrics and top qualifying variants.

Relocated from ``data/sweep_logs/analyze_sweeps.py`` for discoverability.

Usage:
    python scripts/analyze_sweeps.py
"""

from __future__ import annotations

import glob
import json
import math
import os
import sqlite3
from datetime import datetime
from pathlib import Path

# Sweep run date prefix — only analyze files from today's run
RUN_DATE = "20260403"
BACKTEST_DIR = Path("data/backtest_runs")
OUTPUT_PATH = Path("data/sweep_logs/sweep_summary_20260403.md")

PATTERNS = [
    "narrow_range_breakout",
    "vwap_bounce",
    "micro_pullback",
    "hod_break",
    "bull_flag",
    "flat_top_breakout",
    "gap_and_go",
    "premarket_high_break",
    "abcd",
]

PARAMS_USED = {
    "narrow_range_breakout": "min_narrowing_bars,min_breakout_volume_ratio",
    "vwap_bounce": "vwap_touch_tolerance_pct,min_prior_trend_bars",
    "micro_pullback": "min_impulse_percent,max_impulse_bars",
    "hod_break": "hod_proximity_percent,breakout_margin_percent",
    "bull_flag": "pole_min_move_pct,flag_max_retrace_pct",
    "flat_top_breakout": "resistance_tolerance_pct,max_range_narrowing",
    "gap_and_go": "min_gap_percent,target_ratio",
    "premarket_high_break": "pm_high_proximity_percent,min_breakout_volume_ratio",
    "abcd": "fib_b_min,fib_c_min",
}

GRID_SIZES = {
    "narrow_range_breakout": 54,
    "vwap_bounce": 20,
    "micro_pullback": 24,
    "hod_break": 30,
    "bull_flag": 25,
    "flat_top_breakout": 16,
    "gap_and_go": 60,
    "premarket_high_break": 45,
    "abcd": 25,
}

SYMBOL_COUNTS = {
    "narrow_range_breakout": 39,
    "vwap_bounce": 26,
    "micro_pullback": 38,
    "hod_break": 50,
    "bull_flag": 38,
    "flat_top_breakout": 26,
    "gap_and_go": 24,
    "premarket_high_break": 24,
    "abcd": 27,
}


def compute_metrics(trades: list[tuple]) -> dict:
    """Compute aggregate metrics from a list of (outcome, net_pnl, r_multiple) rows."""
    if not trades:
        return {"trades": 0, "win_rate": 0.0, "net_pnl": 0.0, "avg_r": 0.0, "sharpe": 0.0, "expectancy": 0.0}

    total = len(trades)
    wins = sum(1 for t in trades if t[0] == "win")
    net_pnl = sum(t[1] for t in trades if t[1] is not None)
    rs = [t[2] for t in trades if t[2] is not None]
    avg_r = sum(rs) / len(rs) if rs else 0.0
    std_r = math.sqrt(sum((r - avg_r) ** 2 for r in rs) / len(rs)) if len(rs) > 1 else 0.0
    sharpe = avg_r / std_r if std_r > 0 else 0.0
    win_rate = wins / total if total > 0 else 0.0
    # Expectancy = avg_r (R-multiple based)
    return {
        "trades": total,
        "win_rate": round(win_rate * 100, 1),
        "net_pnl": round(net_pnl, 2),
        "avg_r": round(avg_r, 4),
        "sharpe": round(sharpe, 3),
        "expectancy": round(avg_r, 4),
    }


def analyze_pattern(pattern_name: str) -> dict:
    """Analyze all backtest SQLite files for a given pattern."""
    # Match files: strat_{pattern_snake}_20250101_20251231_{RUN_DATE}_*.db
    pattern_snake = pattern_name.replace("-", "_")
    glob_pattern = str(BACKTEST_DIR / f"strat_{pattern_snake}_20250101_20251231_{RUN_DATE}_*.db")
    db_files = [f for f in glob.glob(glob_pattern) if f.endswith(".db")]

    results = []
    failed = 0

    for db_path in sorted(db_files):
        try:
            conn = sqlite3.connect(db_path)
            trades = conn.execute(
                "SELECT outcome, net_pnl, r_multiple FROM trades"
            ).fetchall()
            conn.close()

            metrics = compute_metrics(trades)
            # Use db filename timestamp as identifier (no fingerprint available)
            ts = os.path.basename(db_path).split("_")[-1].replace(".db", "")
            metrics["db_file"] = os.path.basename(db_path)
            metrics["run_ts"] = ts
            results.append(metrics)
        except Exception:
            failed += 1

    return {
        "pattern": pattern_name,
        "symbol_count": SYMBOL_COUNTS.get(pattern_name, "?"),
        "grid_size": GRID_SIZES.get(pattern_name, "?"),
        "params_used": PARAMS_USED.get(pattern_name, "?"),
        "completed": len(results),
        "failed": failed,
        "results": results,
    }


def find_top_variants(results: list[dict], n: int = 3) -> list[dict]:
    """Return top N variants by Sharpe ratio, filtered by min 20 trades."""
    qualified = [r for r in results if r["trades"] >= 20 and r["sharpe"] > 0]
    return sorted(qualified, key=lambda x: x["sharpe"], reverse=True)[:n]


def generate_markdown(pattern_data: list[dict]) -> str:
    """Generate the sweep summary markdown."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []

    lines.append("# Universe-Aware Sweep Summary — 2026-04-03")
    lines.append("")
    lines.append(f"**Generated:** {now}")
    lines.append("**Date range:** 2025-01-01 to 2025-12-31")
    lines.append("**Worker count:** 2 (memory constraint: ~1.07GB/worker; only ~1.7GB free on 18GB system)")
    lines.append("**Patterns swept:** 9 (dip_and_rip skipped — 2 qualifying variants already in shadow mode)")
    lines.append("")

    # Infrastructure notes
    lines.append("## Infrastructure Notes")
    lines.append("")
    lines.append("### Grid Size Reduction (--params flag required)")
    lines.append("All patterns required `--params` restriction. Full Cartesian products range from 96 (flat_top_breakout)")
    lines.append("to 27.7 billion (narrow_range_breakout, 11 params). Only 2 detection-sensitivity params swept per pattern.")
    lines.append("")
    lines.append("### --universe-filter Skipped (Incompatible with 1-min Bar Data)")
    lines.append("The `--universe-filter` flag uses `HAVING AVG(volume) >= threshold` on the Parquet cache,")
    lines.append("which contains 1-minute bars (AAPL avg ~4,532 per bar vs daily threshold of 300,000+).")
    lines.append("Zero symbols pass any filter. Universe intent encoded directly in per-pattern symbol files.")
    lines.append("")
    lines.append("### ExperimentStore Persistence Bug (Pre-existing DEF)")
    lines.append("`ExperimentStore.save_experiment()` calls `json.dumps(record.backtest_result)` which fails")
    lines.append("with `TypeError: Object of type date is not JSON serializable` for every record.")
    lines.append("Root cause: `BacktestResult.daily_equity: list[tuple[date, float]]` contains nested `date`")
    lines.append("objects that survive `_backtest_result_to_dict()`. `to_multi_objective_result()` fails first")
    lines.append("with `RuntimeError: Database not initialized` in subprocess context, triggering the broken")
    lines.append("fallback path. All results queried from individual SQLite files in `data/backtest_runs/`.")
    lines.append("")

    # Per-pattern summary table
    lines.append("## Per-Pattern Summary")
    lines.append("")
    lines.append("| Pattern | Symbols | Grid | Completed | Failed | Best Sharpe | Best WR% | Best Trades |")
    lines.append("|---------|---------|------|-----------|--------|-------------|----------|-------------|")

    for pd in pattern_data:
        top = find_top_variants(pd["results"], n=1)
        best_sharpe = f"{top[0]['sharpe']:.3f}" if top else "n/a"
        best_wr = f"{top[0]['win_rate']:.1f}%" if top else "n/a"
        best_trades = str(top[0]["trades"]) if top else "n/a"
        lines.append(
            f"| {pd['pattern']} | {pd['symbol_count']} | {pd['completed']}/{pd['grid_size']} | "
            f"{pd['completed']} | {pd['failed']} | {best_sharpe} | {best_wr} | {best_trades} |"
        )

    lines.append("")

    # Per-pattern detail
    lines.append("## Per-Pattern Detail")
    lines.append("")

    for pd in pattern_data:
        lines.append(f"### {pd['pattern']}")
        lines.append(f"- **Symbols:** {pd['symbol_count']} | **Params swept:** `{pd['params_used']}`")
        lines.append(f"- **Grid size:** {pd['grid_size']} | **Completed:** {pd['completed']} | **Failed:** {pd['failed']}")
        lines.append("")

        top3 = find_top_variants(pd["results"], n=3)
        if top3:
            lines.append("**Top 3 qualifying variants (Sharpe > 0, min 20 trades):**")
            lines.append("")
            lines.append("| Rank | DB File | Trades | Win Rate | Net PnL | Avg R | Sharpe |")
            lines.append("|------|---------|--------|----------|---------|-------|--------|")
            for i, v in enumerate(top3, 1):
                lines.append(
                    f"| {i} | `{v['db_file'][-30:]}` | {v['trades']} | {v['win_rate']}% | "
                    f"${v['net_pnl']:,.0f} | {v['avg_r']:.4f} | {v['sharpe']:.3f} |"
                )
        else:
            lines.append("**No qualifying variants** (Sharpe > 0 with min 20 trades).")
            # Show best available
            if pd["results"]:
                sorted_results = sorted(pd["results"], key=lambda x: x["sharpe"], reverse=True)[:3]
                lines.append("")
                lines.append("Best results regardless of threshold:")
                for r in sorted_results:
                    lines.append(f"- {r['db_file'][-30:]}: {r['trades']} trades, WR={r['win_rate']}%, Sharpe={r['sharpe']:.3f}, PnL=${r['net_pnl']:,.0f}")

        lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    lines.append("")
    lines.append("1. **Fix ExperimentStore JSON serialization bug** (high priority): ")
    lines.append("   `_backtest_result_to_dict()` in `runner.py` must recursively convert `date`/`datetime`")
    lines.append("   objects in `daily_equity: list[tuple[date, float]]`. Also fix `to_multi_objective_result()`")
    lines.append("   subprocess context failure (Database not initialized).")
    lines.append("")
    lines.append("2. **Expand to 3-param grids on qualified patterns**: Patterns showing Sharpe > 0.5 on the")
    lines.append("   2-param grid warrant a follow-up sweep adding a 3rd param (e.g., `target_ratio` or")
    lines.append("   `stop_buffer_atr_mult`) once the JSON bug is fixed for proper ExperimentStore tracking.")
    lines.append("")
    lines.append("3. **Representative universe selection**: The momentum symbol set (24 symbols) favored")
    lines.append("   gap-based patterns. Patterns like VWAP Bounce and Narrow Range Breakout need stable,")
    lines.append("   range-bound symbols. Consider separate universe files per pattern type.")
    lines.append("")
    lines.append("4. **ABCD O(n³) optimization** (DEF-122): ABCD sweep runtime will be bottlenecked by swing")
    lines.append("   detection. Pre-compute swing cache before expanding ABCD's param grid.")
    lines.append("")
    lines.append("5. **Fix --universe-filter for 1-min bar data**: Either (a) add a `daily_bars` DuckDB view")
    lines.append("   aggregating 1-min bars to daily OHLCV for volume filtering, or (b) add `--use-daily-volume`")
    lines.append("   flag that queries FMP daily bars instead of the Parquet cache.")
    lines.append("")
    lines.append("6. **Add config_fingerprint wiring in BacktestEngine**: Currently `config_fingerprint` is None")
    lines.append("   in every trade record. Wiring it would enable correlating trade-level results back to")
    lines.append("   specific param combos without relying on ExperimentStore.")

    return "\n".join(lines)


def main() -> None:
    print(f"Phase 4: Analyzing sweep results from {BACKTEST_DIR}...")
    print(f"Run date filter: {RUN_DATE}")

    all_pattern_data = []
    for pattern in PATTERNS:
        print(f"  Analyzing {pattern}...")
        data = analyze_pattern(pattern)
        all_pattern_data.append(data)
        print(f"    -> {data['completed']}/{data['grid_size']} completed, "
              f"{len(find_top_variants(data['results']))} qualifying variants")

    md = generate_markdown(all_pattern_data)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(md)
    print(f"\nSummary written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
