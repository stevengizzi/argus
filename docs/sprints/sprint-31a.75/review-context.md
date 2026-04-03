# Review Context: Sprint 31A.75 — Universe-Aware Sweep Flags

## Sprint Overview

**Sprint:** 31A.75 — Universe-Aware Sweep Flags (impromptu, between 31A.5 and 31.5)
**Sessions:** 1 (single-session impromptu)
**DEF Resolved:** DEF-145
**Urgency:** DISCOVERED — found during Sprint 31A parameter sweep when 24,321-symbol
Parquet cache made sweeps infeasible without scoping.

## Sprint Spec (Condensed)

### Problem
`run_experiment.py` has no way to restrict which symbols BacktestEngine processes.
The Sprint 31A parameter sweep used a hand-picked 24-symbol momentum set because
there was no alternative. That set isn't representative for patterns like Narrow
Range Breakout (2 trades in 4 months on momentum stocks) or VWAP Bounce (negative
dollar P&L on high-beta names). Each pattern already has a production universe
filter in `config/universe_filters/{pattern}.yaml` that defines its natural population.

### Solution
Add `--symbols` and `--universe-filter` CLI flags to `run_experiment.py`. Wire
`HistoricalQueryService.validate_symbol_coverage()` for cache data validation.
Three-layer filtering pipeline: explicit symbols → universe filter (DuckDB query) →
coverage validation. All additive; default behavior (no flags) unchanged.

### Key Design Decisions
- **Static filters only:** DuckDB can compute `AVG(close)` and `AVG(volume)` from
  historical data. Dynamic filters (relative volume, gap percent, pre-market volume)
  are per-session metrics with no historical equivalent — logged as skipped.
- **No production runtime changes:** All changes in `scripts/run_experiment.py`
  and tests. `HistoricalQueryService` and `BacktestEngine` used as-is.
- **`run_sweep()` already accepts `symbols` param:** The wiring from CLI to
  BacktestEngine is already in place; we just need to populate it.

## Specification by Contradiction

### "What if we applied ALL universe filter fields via DuckDB?"
Dynamic fields like `min_relative_volume` and `min_gap_percent` are computed per-session
from live data. Historical Parquet has no relative volume (needs real-time comparison
to moving average) and no gap percent (needs prior day's close vs current open, which
varies daily). Applying these historically would require computing them per-day per-symbol,
which is expensive and semantically different from the live computation. Correct approach:
apply only the static structural filters (price range, volume floor) and document the gap.

### "What if --universe-filter created its own copy of the Parquet cache?"
Massive storage waste. BacktestEngine already accepts `symbols: list[str]` and
only loads those symbols' Parquet files. Filtering at the symbol-list level before
BacktestEngine runs is the correct abstraction boundary.

### "What if we queried FMP reference data for historical filtering?"
FMP provides current reference data (today's avg volume, today's price). For a
2025 backtest sweep, we need 2025-era statistics. DuckDB over Parquet gives us
actual historical averages. FMP would only reflect current fundamentals.

## Regression Checklist

| Check | How to Verify |
|-------|---------------|
| Default CLI behavior unchanged | `--pattern bull_flag --dry-run` works identically to before |
| No production runtime files modified | `git diff --name-only` limited to `scripts/` and `tests/` |
| All tests pass | `python -m pytest tests/ -x -q --tb=short -n auto` |
| ExperimentRunner API unchanged | `run_sweep()` signature and behavior unchanged |

## Escalation Criteria

- ESCALATE if any production runtime file was modified (`argus/core/`, `argus/execution/`,
  `argus/data/`, `argus/strategies/`, `argus/api/`)
- ESCALATE if default CLI behavior changed (no flags → auto-detect all symbols)
- ESCALATE if `BacktestEngine` or `HistoricalQueryService` internals were modified
- ESCALATE if the changes introduce a new runtime dependency (everything should
  use existing imports)
