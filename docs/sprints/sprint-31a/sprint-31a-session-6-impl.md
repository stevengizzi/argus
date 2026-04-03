# Sprint 31A, Session 6: Full Parameter Sweep + Experiments Config

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `scripts/run_experiment.py` (sweep CLI entry point — understand `--pattern`, `--cache-dir`, `--params`, `--dry-run` flags)
   - `config/experiments.yaml` (current config — 2 Dip-and-Rip variants)
   - `argus/intelligence/experiments/runner.py` (`_PATTERN_TO_STRATEGY_TYPE` — verify all 10 patterns mapped)
   - `argus/strategies/patterns/factory.py` (verify all 10 patterns registered)
2. Run the test baseline (DEC-328):
   Scoped: `python -m pytest tests/intelligence/experiments/ tests/backtest/ -x -q -n auto`
   Expected: all passing (including S1–S5 changes)
3. Verify you are on the correct branch: `main` (with S1–S5 committed)
4. Verify Parquet cache is accessible: `ls data/databento_cache/ | head -5` (or confirm the path — it may be on LaCie at `/Volumes/LaCie/argus-cache`)

## Objective
Run parameter sweeps across all 10 PatternModule patterns against the historical Parquet cache. Write qualifying variants (Sharpe > 0.5, trades ≥ 30, expectancy > 0) to `config/experiments.yaml` as shadow-mode variants.

## Requirements

### 1. Integration Verification

Before sweeping, verify all 10 patterns run in BacktestEngine:

```bash
# Quick smoke test for each pattern (dry-run to check grid size)
for pattern in bull_flag flat_top_breakout dip_and_rip hod_break gap_and_go abcd premarket_high_break micro_pullback vwap_bounce narrow_range_breakout; do
    echo "=== $pattern ==="
    python scripts/run_experiment.py --pattern $pattern --cache-dir data/databento_cache --dry-run 2>&1 | tail -3
done
```

If any pattern fails to initialize, fix before proceeding (this would indicate a wiring issue from S3–S5).

### 2. Sweep Methodology

For each of the 10 patterns:

**Step A: Identify high-impact params**
Run single-param sensitivity sweeps on the top 2–3 detection parameters (the ones most likely to affect trade count and quality). Use `--params` flag to override one param at a time.

Recommended param priorities per pattern:
- **Bull Flag:** `pole_min_percent`, `flag_max_range_atr`
- **Flat-Top Breakout:** `resistance_tolerance_percent`, `consolidation_min_bars`
- **Dip-and-Rip:** `min_dip_percent`, `min_recovery_volume_ratio` (already swept — use existing data)
- **HOD Break:** `consolidation_min_bars`, `consolidation_max_range_atr`
- **Gap-and-Go:** `min_gap_percent`, `entry_mode` (if parameterized)
- **ABCD:** `fib_b_min`, `fib_b_max` (note: O(n³) — runs slower per DEF-122)
- **Pre-Market High Break:** `min_pm_volume`, `breakout_margin_percent`
- **Micro Pullback:** `ema_period`, `min_impulse_percent`, `pullback_tolerance_atr`
- **VWAP Bounce:** `vwap_touch_tolerance_pct`, `min_prior_trend_bars`
- **Narrow Range Breakout:** `min_narrowing_bars`, `range_decay_tolerance`, `consolidation_max_range_atr`

**Step B: Multi-param optimization**
For patterns where Step A reveals 2+ high-impact params, run a combined sweep on the top combinations.

**Step C: Evaluate results**
Qualification criteria: trades ≥ 30, expectancy > 0, Sharpe > 0.5.

**Symbol set:** Use the established 24-symbol momentum set: AAPL, NVDA, AMD, TSLA, MARA, RIOT, COIN, HOOD, GME, AMC, SPCE, PLUG, SNAP, UBER, PLTR, RBLX, AFRM, SOFI, LCID, RIVN, NIO, SMCI, IONQ, HIMS.

**Date range:** 2025-01-01 to 2025-12-31.

### 3. Update experiments.yaml

For each qualifying variant:
- Add under the appropriate pattern key in `variants:`
- Use naming convention: `strat_{pattern_name}__v{N}_{descriptive_suffix}`
- Set `mode: "shadow"`
- Include a comment block with backtest metrics (Sharpe, trades, expectancy, win rate)
- Include a rationale comment explaining why this param combination was selected

Preserve existing Dip-and-Rip v2 and v3 entries unchanged.

### 4. Document non-qualifying patterns

For patterns that produce no qualifying variants, add a comment block in experiments.yaml explaining:
- Best configuration found
- Why it didn't qualify (too few trades? negative expectancy? low Sharpe?)
- Whether the base configuration is acceptable or needs attention

### 5. Write sweep results summary

Create `docs/sprints/sprint-31a/sweep-results.md` with:
- Per-pattern summary table (best Sharpe, best expectancy, trade count range)
- Qualifying variants listed with full metrics
- Non-qualifying patterns with explanation
- Any interesting observations (e.g., "NR Breakout works best with 5+ narrowing bars and strict volume filter")

## Constraints
- Do NOT modify any Python source files (this is a sweep + config session)
- Do NOT lower qualification thresholds (Sharpe > 0.5, trades ≥ 30, expectancy > 0)
- Do NOT change existing Dip-and-Rip variant entries
- Do NOT set `auto_promote: true` (stays false — promotion requires observation)
- If ABCD sweeps take >30 min per config, document timing and use a smaller grid (this is expected per DEF-122)
- If the Parquet cache path differs from `data/databento_cache`, adjust the `--cache-dir` flag accordingly

## Test Targets
- Write 3 integration tests:
  1. All 10 StrategyType enum values are present in `_PATTERN_TO_STRATEGY_TYPE`
  2. All 10 pattern names are present in `_PATTERN_REGISTRY`
  3. Loading `config/experiments.yaml` succeeds without parse errors (YAML validity)
- Minimum new test count: 3
- Test command (final session — full suite): `python -m pytest -x -q -n auto && cd ui && npx vitest run --reporter=verbose 2>&1 | tail -5`

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No Python source changes | `git diff --name-only HEAD~1` shows only .yaml, .md files |
| Existing variants preserved | Diff experiments.yaml: strat_dip_and_rip__v2 and __v3 entries unchanged |
| All new variants shadow mode | `grep "mode:" config/experiments.yaml` — all new entries are "shadow" |
| Full test suite green | pytest + Vitest both pass |

## Sprint-Level Escalation Criteria
1. Parameter sweep shows BacktestEngine still ignoring config_overrides → STOP, escalate
2. Test count decreases → STOP, investigate
3. Any pattern fails to initialize in BacktestEngine → wiring bug from S3–S5, fix before sweeping

## Definition of Done
- [ ] All 10 patterns verified runnable in BacktestEngine (smoke test passes)
- [ ] Sensitivity sweeps completed for all 10 patterns
- [ ] Multi-param optimization completed where warranted
- [ ] Qualifying variants added to experiments.yaml
- [ ] Non-qualifying patterns documented
- [ ] Sweep results summary written
- [ ] Integration tests pass
- [ ] Full test suite passes (final session of sprint)
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
Write to: `docs/sprints/sprint-31a/session-6-closeout.md`

**IMPORTANT:** This is the final session of Sprint 31A. The close-out must include the full test suite run (not scoped).

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context file: `docs/sprints/sprint-31a/review-context.md`
2. Close-out: `docs/sprints/sprint-31a/session-6-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command (FINAL SESSION): `python -m pytest -x -q -n auto && cd ui && npx vitest run --reporter=verbose 2>&1 | tail -5`
5. NOT modified: any Python source file (only experiments.yaml and docs)

## Session-Specific Review Focus (for @reviewer)
1. Verify no Python source changes (only config + docs)
2. Verify existing Dip-and-Rip variants preserved unchanged in experiments.yaml
3. Verify all new variants use `mode: "shadow"` (not live)
4. Verify variant naming follows convention: `strat_{pattern}__v{N}_{suffix}`
5. Verify qualification criteria were applied consistently (Sharpe > 0.5, trades ≥ 30, exp > 0)
6. Verify sweep results doc covers all 10 patterns (including non-qualifying)
7. Full test suite green (both pytest and Vitest)
