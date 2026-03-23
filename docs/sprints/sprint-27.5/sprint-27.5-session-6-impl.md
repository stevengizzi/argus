# Sprint 27.5, Session 6: Integration Wiring + End-to-End Tests

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/analytics/evaluation.py` (S1)
   - `argus/analytics/comparison.py` (S3)
   - `argus/analytics/ensemble_evaluation.py` (S4)
   - `argus/analytics/slippage_model.py` (S5)
   - `argus/backtest/engine.py` (S2 already modified — verify regime tagging exists)
   - `argus/backtest/config.py` (will modify)
   - `docs/sprints/sprint-27.5/review-context.md`
2. Run scoped test baseline (DEC-328):
   ```bash
   python -m pytest tests/backtest/ tests/analytics/ -x -q
   ```
   Expected: all passing (includes S1–S5 tests)
3. Verify all prior sessions (S1–S5) are committed

## Objective
Wire the slippage model into BacktestEngine as an optional parameter, populate `execution_quality_adjustment` on MultiObjectiveResult output, and verify the full pipeline works end-to-end with integration tests covering BacktestEngine → MOR → compare → ensemble evaluation.

## Requirements

1. In `argus/backtest/config.py`, add to `BacktestEngineConfig`:
   - `slippage_model_path: str | None = Field(default=None, description="Path to calibrated StrategySlippageModel JSON. When set, loads calibrated slippage for execution_quality_adjustment computation.")`
   - Verify the field name matches exactly (Pydantic won't error on mismatch — it silently ignores)

2. In `argus/backtest/engine.py`, in `__init__` or `run()` setup:
   - If `config.slippage_model_path` is not None: `self._slippage_model = load_slippage_model(config.slippage_model_path)`
   - If None: `self._slippage_model = None`
   - Import `load_slippage_model` from `argus.analytics.slippage_model`

3. In `argus/backtest/engine.py`, in `to_multi_objective_result()`:
   - After building the MOR, if `self._slippage_model` is not None and confidence is not INSUFFICIENT:
     - Compute `execution_quality_adjustment`: estimated Sharpe impact from real vs model slippage
     - Formula: `adjustment = -(model.estimated_mean_slippage_bps - config.slippage_per_share * 10000 / avg_entry_price) * sqrt(252) / portfolio_return_std` (simplified approximation — the exact formula depends on trade frequency and sizing)
     - Simpler acceptable approach: `adjustment = -(model.estimated_mean_slippage_bps - default_slippage_bps) / 100 * total_trades / trading_days * sqrt(252)` normalized by return std
     - If computation is unreliable (e.g., zero std, zero trades): leave as None
   - Set `mor.execution_quality_adjustment = adjustment` (note: MOR is a dataclass, may need to use `dataclasses.replace()` or make the field mutable during construction)

4. Write **integration tests** in `tests/integration/test_evaluation_pipeline.py`:

   a. `test_full_pipeline_roundtrip`:
      - Create a minimal BacktestEngine with test Parquet data (2–3 days, 1 strategy)
      - Run backtest → get BacktestResult
      - Call `to_multi_objective_result()` → get MOR with regime data
      - Verify MOR has correct metrics matching BacktestResult
      - Verify regime_results is populated

   b. `test_compare_two_backtest_runs`:
      - Run BacktestEngine twice with different configs (e.g., different slippage)
      - Convert both to MOR
      - Call `compare(mor_a, mor_b)` → verify ComparisonVerdict is reasonable

   c. `test_ensemble_from_backtest_results`:
      - Run BacktestEngine for 2+ strategies
      - Convert each to MOR
      - Call `build_ensemble_result(mors)` → valid EnsembleResult
      - Verify marginal_contributions has entries for each strategy

   d. `test_cohort_addition_integration`:
      - Build baseline ensemble from 2 MORs
      - Call `evaluate_cohort_addition(baseline, [new_mor])` → valid verdict

   e. `test_slippage_model_wiring`:
      - Create a temp slippage model JSON file
      - Configure BacktestEngineConfig with `slippage_model_path` pointing to it
      - Run BacktestEngine → call `to_multi_objective_result()`
      - Verify `execution_quality_adjustment` is not None (or is None with valid reason)

   f. `test_slippage_model_none_backward_compat`:
      - BacktestEngineConfig with `slippage_model_path=None`
      - Run BacktestEngine → call `to_multi_objective_result()`
      - Verify `execution_quality_adjustment` is None
      - Verify all other MOR fields are correct

   g. `test_format_reports`:
      - `format_comparison_report(mor_a, mor_b)` → non-empty string
      - `format_ensemble_report(ensemble)` → non-empty string

   h. `test_no_circular_imports`:
      - Import all 4 new analytics modules in sequence
      - Import `argus.backtest.engine`
      - All succeed without ImportError

   Note: Integration tests may use a small synthetic Parquet dataset. If setting up BacktestEngine is too heavyweight, use the MOR factories and synthetic data directly — the key is testing the interface contracts, not re-testing BacktestEngine internals.

## Constraints
- Do NOT modify `argus/backtest/metrics.py`
- Do NOT modify any analytics modules from S1/S3/S4/S5 (only import from them)
- Do NOT add API endpoints
- The `execution_quality_adjustment` computation can be a simplified approximation — document the formula and note it's a first-order estimate

## Config Validation
Write a test that verifies the `slippage_model_path` field is recognized by BacktestEngineConfig:
1. Construct `BacktestEngineConfig(slippage_model_path="/tmp/test.json")`
2. Verify `config.slippage_model_path == "/tmp/test.json"`
3. Construct `BacktestEngineConfig()` (no arg)
4. Verify `config.slippage_model_path is None`

| YAML Key | Model Field |
|----------|-------------|
| slippage_model_path | slippage_model_path |

## Test Targets
- New tests in `tests/integration/test_evaluation_pipeline.py` (create directory if needed)
- Minimum new test count: 8
- Test command (final session — full suite per DEC-328):
  ```bash
  python -m pytest --ignore=tests/test_main.py -n auto -q
  ```

## Definition of Done
- [ ] All requirements implemented
- [ ] Full pytest suite passes (final session — run full suite)
- [ ] Integration tests written and passing (≥8)
- [ ] Config validation test passing
- [ ] `execution_quality_adjustment` populated when slippage model available
- [ ] `execution_quality_adjustment` is None when no slippage model
- [ ] No circular imports across all new + modified modules
- [ ] Close-out report written to `docs/sprints/sprint-27.5/session-6-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| BacktestEngine backward compat | Existing engine tests pass with no slippage_model_path |
| Config backward compat | `BacktestEngineConfig()` with no slippage arg → no error, None default |
| metrics.py untouched | `git diff argus/backtest/metrics.py` empty |
| walk_forward.py untouched | `git diff argus/backtest/walk_forward.py` empty |
| No circular imports | Run all module imports in test |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
`docs/sprints/sprint-27.5/session-6-closeout.md`

This is the **final session** — the close-out must run the full test suite per DEC-328.

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: `docs/sprints/sprint-27.5/review-context.md`
2. Close-out: `docs/sprints/sprint-27.5/session-6-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command (**final session — full suite**): `python -m pytest --ignore=tests/test_main.py -n auto -q`
5. Files NOT modified: `argus/backtest/metrics.py`, `argus/backtest/walk_forward.py`, `argus/core/regime.py`, `argus/analytics/performance.py`, all strategy files, all frontend files, all API routes

Write review to: `docs/sprints/sprint-27.5/session-6-review.md`

## Post-Review Fix Documentation
If CONCERNS → fix and update both close-out and review files per template.

## Session-Specific Review Focus (for @reviewer)
1. Verify `slippage_model_path` field on BacktestEngineConfig defaults to None (backward compat)
2. Verify slippage model loading handles FileNotFoundError gracefully (log warning, proceed without model)
3. Verify `execution_quality_adjustment` computation formula is documented and reasonable
4. Verify `execution_quality_adjustment` is None when slippage model is None or INSUFFICIENT
5. Verify integration tests cover the full pipeline (engine → MOR → compare → ensemble)
6. Verify no circular imports (run import test)
7. Verify `dataclasses.replace()` or equivalent used correctly if MOR fields are set post-construction
8. Verify full test suite passes (this is the final session — run `--ignore=tests/test_main.py -n auto`)

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Full pytest suite passes with `--ignore=tests/test_main.py` (≥3,071 + ~65 new ≈ ≥3,136)
- [ ] Full Vitest suite passes (≥620, unchanged)
- [ ] No new test hangs or timeouts
- [ ] `BacktestEngine.run()` returns identical BacktestResult for same inputs
- [ ] Existing BacktestEngine tests pass without modification
- [ ] CLI entry point produces same output format
- [ ] `BacktestEngineConfig` with no `slippage_model_path` behaves identically
- [ ] `backtest/metrics.py` not modified
- [ ] `backtest/walk_forward.py` not modified
- [ ] `core/regime.py` not modified
- [ ] `analytics/performance.py` not modified
- [ ] No circular imports among new analytics modules
- [ ] Each new analytics module imports independently
- [ ] Protected files have zero diff

## Sprint-Level Escalation Criteria (for @reviewer)
**Hard Stops:** BacktestEngine regression, circular imports, BacktestResult interface change.
**Escalate to Tier 3:** MOR schema diverges from DEC-357, ConfidenceTier thresholds miscalibrated.
**Scope Creep:** API endpoints, persistence/DB tables, walk_forward.py modifications.
