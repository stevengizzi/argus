# Sprint 27.5, Session 1: Core Data Models

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/backtest/metrics.py` (BacktestResult — the source model you'll bridge from)
   - `argus/core/regime.py` (MarketRegime enum — regime keys for RegimeMetrics)
   - `docs/sprints/sprint-27.5/review-context.md` (sprint spec + constraints)
2. Run the test baseline (DEC-328 — first session, full suite):
   ```bash
   python -m pytest --ignore=tests/test_main.py -n auto -q
   ```
   Expected: ≥3,071 tests, all passing
   ```bash
   cd argus/ui && npx vitest run --reporter=verbose 2>&1 | tail -5
   ```
   Expected: ≥620 tests, all passing
3. Verify you are on the correct branch (main or sprint-27.5 feature branch)
4. Record the exact pre-flight test counts — these are the sprint baseline

## Objective
Create the foundational data models that every other session in this sprint and every downstream sprint (28, 32.5, 33, 34, 38) depends on: `MultiObjectiveResult`, `RegimeMetrics`, `ConfidenceTier`, `ComparisonVerdict`, serialization, and the `from_backtest_result()` factory.

## Requirements

1. Create `argus/analytics/evaluation.py` with:

   a. **`RegimeMetrics` dataclass** (frozen):
      - `sharpe_ratio: float`
      - `max_drawdown_pct: float` (negative number, e.g. -0.12 = 12%)
      - `profit_factor: float`
      - `win_rate: float`
      - `total_trades: int`
      - `expectancy_per_trade: float`
      - `to_dict() → dict` and `from_dict(d) → RegimeMetrics` methods

   b. **`ConfidenceTier` enum** (StrEnum):
      - `HIGH = "high"` — 50+ trades total AND 15+ trades in ≥3 regime types
      - `MODERATE = "moderate"` — 30–49 trades total AND 10+ trades in ≥2 regime types (OR 50+ trades but insufficient regime coverage for HIGH)
      - `LOW = "low"` — 10–29 trades total
      - `ENSEMBLE_ONLY = "ensemble_only"` — <10 trades total

   c. **`compute_confidence_tier(total_trades: int, regime_trade_counts: dict[str, int]) → ConfidenceTier`**:
      - `total_trades >= 50` AND `sum(1 for c in regime_trade_counts.values() if c >= 15) >= 3` → HIGH
      - `total_trades >= 30` AND `sum(1 for c in regime_trade_counts.values() if c >= 10) >= 2` → MODERATE
      - `total_trades >= 10` → LOW
      - else → ENSEMBLE_ONLY

   d. **`ComparisonVerdict` enum** (StrEnum):
      - `DOMINATES = "dominates"` — A is strictly better
      - `DOMINATED = "dominated"` — B is strictly better
      - `INCOMPARABLE = "incomparable"` — mixed results
      - `INSUFFICIENT_DATA = "insufficient_data"` — confidence too low

   e. **`parameter_hash(config: dict) → str`**:
      - Deterministic hash: `hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode()).hexdigest()[:16]`
      - Same dict with different key ordering → same hash

   f. **`MultiObjectiveResult` dataclass**:
      - Identity: `strategy_id: str`, `parameter_hash: str`, `evaluation_date: datetime`, `data_range: tuple[date, date]`
      - Primary metrics: `sharpe_ratio: float`, `max_drawdown_pct: float`, `profit_factor: float`, `win_rate: float`, `total_trades: int`, `expectancy_per_trade: float`
      - Regime: `regime_results: dict[str, RegimeMetrics]` (string-keyed for forward-compat with Sprint 27.6)
      - Confidence: `confidence_tier: ConfidenceTier`
      - Statistical (placeholders): `p_value: float | None = None`, `confidence_interval: tuple[float, float] | None = None`
      - Walk-forward: `wfe: float = 0.0`, `is_oos: bool = False`
      - Execution quality: `execution_quality_adjustment: float | None = None`
      - Methods: `to_dict() → dict`, `from_dict(d) → MultiObjectiveResult`

   g. **`from_backtest_result(result: BacktestResult, regime_results: dict[str, RegimeMetrics] | None = None, wfe: float = 0.0, is_oos: bool = False, parameter_hash: str = "") → MultiObjectiveResult`**:
      - Maps `result.sharpe_ratio`, `result.max_drawdown_pct`, `result.profit_factor`, `result.win_rate`, `result.total_trades`, `result.expectancy` → corresponding MOR fields
      - Computes `confidence_tier` from `result.total_trades` and regime distribution
      - `evaluation_date` = `datetime.now(UTC)`
      - `data_range` = `(result.start_date, result.end_date)`
      - `execution_quality_adjustment` = `None` (populated in S6)

2. Add `__all__` exports for all public names.

3. Ensure no imports from `argus/backtest/engine.py` (would create circular dependency). The `from_backtest_result` import is from `argus/backtest/metrics.py` only (for the `BacktestResult` type).

## Constraints
- Do NOT modify any existing files
- Do NOT import from `argus/backtest/engine.py` (circular dependency risk)
- Do NOT add persistence, database tables, or SQLite schemas
- Do NOT add REST API endpoints
- All dataclasses should be standard Python dataclasses (not Pydantic) — these are value objects, not config models

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write in `tests/analytics/test_evaluation.py`:
  1. `test_regime_metrics_construction` — all fields present and correct types
  2. `test_regime_metrics_serialization_roundtrip` — to_dict → from_dict → identical
  3. `test_confidence_tier_high` — 50 trades, 15+ in 3 regimes → HIGH
  4. `test_confidence_tier_moderate_by_trades` — 35 trades, 10+ in 2 regimes → MODERATE
  5. `test_confidence_tier_moderate_by_regime_deficit` — 60 trades but only 2 regimes with 15+ → MODERATE (not HIGH)
  6. `test_confidence_tier_low` — 15 trades → LOW
  7. `test_confidence_tier_ensemble_only` — 5 trades → ENSEMBLE_ONLY
  8. `test_confidence_tier_boundary_50` — exactly 50 trades with sufficient regimes → HIGH
  9. `test_confidence_tier_boundary_10` — exactly 10 trades → LOW, 9 → ENSEMBLE_ONLY
  10. `test_multi_objective_result_construction` — all fields
  11. `test_multi_objective_result_serialization_roundtrip` — to_dict → from_dict → identical
  12. `test_parameter_hash_determinism` — same dict different key order → same hash, different dict → different hash
  13. `test_from_backtest_result_mapping` — verify every BacktestResult field maps correctly
  14. `test_from_backtest_result_zero_trades` — empty BacktestResult → ENSEMBLE_ONLY tier
- Minimum new test count: 12
- Test command: `python -m pytest tests/analytics/test_evaluation.py -x -v`

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass
- [ ] New tests written and passing (≥12)
- [ ] `import argus.analytics.evaluation` succeeds with no circular import errors
- [ ] Close-out report written to `docs/sprints/sprint-27.5/session-1-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No circular imports | `python -c "from argus.analytics.evaluation import MultiObjectiveResult"` succeeds |
| No existing file modifications | `git diff --name-only` shows only new files + test files |
| BacktestResult type imported correctly | `from_backtest_result` function signature matches BacktestResult fields |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
`docs/sprints/sprint-27.5/session-1-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-27.5/review-context.md`
2. The close-out report path: `docs/sprints/sprint-27.5/session-1-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (scoped — non-final session): `python -m pytest tests/analytics/test_evaluation.py -x -v`
5. Files that should NOT have been modified: all existing files (this session only creates new files)

The @reviewer will produce its review report and write it to:
`docs/sprints/sprint-27.5/session-1-review.md`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review report files per the template
instructions (Post-Review Fixes section + CONCERNS_RESOLVED verdict).

## Session-Specific Review Focus (for @reviewer)
1. Verify `ConfidenceTier` computation handles ALL boundary conditions correctly (50/49, 30/29, 10/9)
2. Verify `parameter_hash` is truly deterministic — test with reordered dict keys
3. Verify `from_backtest_result` maps EVERY BacktestResult field — no silent drops
4. Verify `regime_results` uses string keys (not MarketRegime enum) for Sprint 27.6 forward-compat
5. Verify no imports from `argus/backtest/engine.py` (only from `argus/backtest/metrics.py`)
6. Verify `to_dict()`/`from_dict()` handle `None` values (`p_value`, `confidence_interval`, `execution_quality_adjustment`)
7. Verify `to_dict()`/`from_dict()` handle `float('inf')` for profit_factor
8. Verify `to_dict()`/`from_dict()` handle `date` and `datetime` serialization correctly

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Full pytest suite passes with `--ignore=tests/test_main.py` (≥3,071 pass, 0 fail)
- [ ] Full Vitest suite passes (≥620 pass, 0 fail)
- [ ] No new test hangs or timeouts
- [ ] Test count does not decrease from sprint entry baseline
- [ ] `BacktestEngine.run()` returns identical `BacktestResult` for same inputs
- [ ] Existing BacktestEngine tests pass without modification
- [ ] `backtest/metrics.py` not modified (git diff)
- [ ] `backtest/walk_forward.py` not modified (git diff)
- [ ] `core/regime.py` not modified (git diff)
- [ ] `analytics/performance.py` not modified (git diff)
- [ ] No circular imports among new analytics modules
- [ ] Protected files have zero diff

## Sprint-Level Escalation Criteria (for @reviewer)
**Hard Stops:** BacktestEngine regression, circular imports, BacktestResult interface change required.
**Escalate to Tier 3:** MOR schema diverges from DEC-357, ConfidenceTier thresholds miscalibrated, regime tagging >80% single-regime.
**Scope Creep:** API endpoints, persistence, walk_forward.py modifications.
