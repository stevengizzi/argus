# Sprint 8 Code Review — Handoff Context

> Paste this into a new Claude.ai conversation along with the Claude Code session transcript.

---

## What Was Built

**Sprint 8: VectorBT Parameter Sweeps** — Fast vectorized exploration of ORB strategy parameter sensitivity. Implementation spec: `docs/sprints/SPRINT_8_SPEC.md`.

This is the VectorBT layer of our two-layer backtest toolkit. It's an intentionally simplified approximation of ORB logic (no VWAP, no volume filter, no T1/T2 split) designed to test 18,000 parameter combinations per symbol in minutes. The Replay Harness (Sprint 7) is the ground truth; VectorBT identifies which parameters to investigate further.

## Pre-Sprint Context

Before Sprint 8 could start, three blockers were found and fixed during the gate check process:

1. **Timezone bug (DEC-061):** `OrbBreakoutStrategy._get_candle_time()` returned UTC time and compared against ET constants. OR never formed. Fixed by adding `.astimezone(ET)` conversion. 8 regression tests added. Also affects live/paper trading (same code path).

2. **Fill price bug:** SimulatedBroker filled market orders at $0.01 (slippage value, not market price). Fixed with `_current_prices` cache and `set_price()` method. Replay harness sets price from bar close before processing.

3. **Trade logging bug:** SimulatedBroker fills synchronously but Order Manager waited for async `OrderFilledEvent` that never came. Fixed with synchronous fill detection in `on_approved()` and `_flatten_position()`.

4. **Data integrity (2 issues):** Stop price recorded final (moved) stop instead of original → added `original_stop_price` field. P&L incorrect for partial exits → added weighted average exit price calculation.

5. **strategy_id mismatch:** BacktestConfig default `"orb_breakout"` didn't match YAML `"strat_orb_breakout"`.

**Tests before Sprint 8: 488** (up from 473 at Sprint 7 completion).

## Gate Check Results (Why the Spec Looks the Way It Does)

A 7-month harness run (June–Dec 2025) with production params produced only **5 trades in 148 days**. Root cause: `max_range_atr_ratio` (default ~2.0) rejected 98.5% of opening ranges. Relaxing to 5.0 produced **59 trades**. This is why `max_range_atr_ratio` was added as a 6th sweep parameter (DEC-062), increasing combinations from 3,000 to 18,000 per symbol.

## Sprint 8 Deliverables (Expected)

| Deliverable | Path | Description |
|-------------|------|-------------|
| VectorBT ORB module | `argus/backtest/vectorbt_orb.py` | SweepConfig, data loading, daily features, sweep engine, aggregation, heatmaps, CLI |
| Tests | `tests/backtest/test_vectorbt_orb.py` | ~15-20 new tests (target ~508 total) |
| Per-symbol results | `data/backtest_runs/sweeps/sweep_{SYMBOL}.parquet` | 18,000 rows per symbol |
| Cross-symbol summary | `data/backtest_runs/sweeps/sweep_summary.parquet` | Aggregated metrics |
| Static heatmaps | `data/backtest_runs/sweeps/*.png` | 5 param pairs × 4 metrics = 20 PNGs |
| Interactive heatmaps | `data/backtest_runs/sweeps/*.html` | Same 20 combinations as HTML |

## Parameter Grid

| Parameter | Values | Count |
|-----------|--------|-------|
| `opening_range_minutes` | 5, 10, 15, 20, 30 | 5 |
| `profit_target_r` | 1.0, 1.5, 2.0, 2.5, 3.0 | 5 |
| `stop_buffer_pct` | 0.0, 0.1, 0.2, 0.5 | 4 |
| `max_hold_minutes` | 15, 30, 45, 60, 90, 120 | 6 |
| `min_gap_pct` | 1.0, 1.5, 2.0, 3.0, 5.0 | 5 |
| `max_range_atr_ratio` | 2.0, 3.0, 4.0, 5.0, 8.0, 999.0 | 6 |
| **Total per symbol** | | **18,000** |

## Key Decisions (Sprint 8)

| Decision | Choice |
|----------|--------|
| DEC-057 | Open-source VectorBT, NumPy fallback |
| DEC-058 | Gap scan pre-filter (same as ScannerSimulator) |
| DEC-059 | Per-symbol sweeps, then aggregate |
| DEC-060 | Dual heatmaps: static PNG + interactive HTML |
| DEC-061 | UTC→ET conversion at consumer (timezone fix) |
| DEC-062 | `max_range_atr_ratio` as 6th sweep parameter |

## What the Simplifications Are (by Design)

The VectorBT sweep is intentionally less detailed than production. This is correct, not a bug:

| Aspect | Production | VectorBT |
|--------|-----------|----------|
| Entry confirmation | Close > OR high + volume > 1.5x + price > VWAP | Close > OR high only |
| Exit: target | T1/T2 split via Order Manager | Single target |
| Stop-to-breakeven | After T1 hit | Not modeled |
| Position sizing | Risk Manager with cash reserve | Fixed $1,000 risk/trade |

## Review Checklist

Please evaluate the Sprint 8 implementation against these criteria:

### 1. Correctness
- Does `compute_opening_range()` correctly handle all `or_minutes` values, including hour rollover (e.g., 30 min → 10:00)?
- Does `sweep_single_combination()` correctly implement: gap filter, OR range filter, breakout detection, stop/target/hold/EOD exits?
- Is `min_gap_pct` treated consistently? (The spec notes it may be percentage points vs decimal — verify against ScannerSimulator)
- Does ATR computation work for short OR windows (5 min = 5 bars, less than ATR(14) requires)?
- Are timestamps correctly handled as ET throughout? (Critical given DEC-061 history)

### 2. Data Integrity
- Do per-symbol Parquet files have the expected 18,000 rows (or close — some combos may have identical results)?
- Does the cross-symbol summary correctly aggregate?
- Are the heatmaps readable and do the values match the underlying data?

### 3. Tests
- Target: ~15-20 new tests, ~508 total passing
- Are edge cases covered? (no qualifying days, short OR windows, single bar, etc.)
- Do tests use synthetic data with known outcomes, not random?
- Are timezone-aware timestamps used in test fixtures?

### 4. Code Quality
- Type hints on all functions?
- Google-style docstrings?
- Ruff clean?
- No hardcoded values that should be configurable?

### 5. CLI
- Does `python -m argus.backtest.vectorbt_orb --help` work?
- Does a small test run complete? (e.g., `--symbols TSLA --start 2025-06-01 --end 2025-06-30`)

### 6. Performance
- What was the wall-clock time for the full sweep (28 symbols × 18K combos)?
- If >30 minutes, is there an obvious optimization path?

### 7. Spec Deviations
- Any implementation choices that differ from `SPRINT_8_SPEC.md`?
- If so, are they improvements or regressions?

### 8. Sweep Results (Sanity Check)
- How many parameter combinations produce >0 trades across symbols?
- Are there parameter combinations that produce unrealistic results (e.g., 100% win rate, infinite profit factor)?
- Does the `max_range_atr_ratio` parameter show the expected dominant effect on trade count?

## After Review

If Sprint 8 passes review:
1. Confirm Sprint 8 complete
2. Draft document updates:
   - 09_PHASE2_SPRINT_PLAN.md: Mark Sprint 8 ✅ COMPLETE with actual test count
   - 02_PROJECT_KNOWLEDGE.md: Update current state, test count
   - CLAUDE.md: Update current sprint to "Sprint 9 — Walk-Forward Analysis"
   - Any new decisions or risks discovered during review
3. Note anything that should be fixed before Sprint 9

If Sprint 8 needs fixes:
1. List specific issues
2. Classify as blockers vs nice-to-haves
3. Draft fix instructions for Claude Code

**Do NOT proceed to Sprint 9 planning — that will happen in a separate session.**

→ PASTE THE CLAUDE CODE SPRINT 8 SESSION TRANSCRIPT BELOW THIS LINE ←
