# Sprint 27.5, Session 5: Slippage Model Calibration

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/execution/execution_record.py` (ExecutionRecord — the source data model)
   - `argus/db/manager.py` (DatabaseManager — DB access pattern)
   - `docs/sprints/sprint-27.5/review-context.md`
2. Run scoped test baseline (DEC-328):
   ```bash
   python -m pytest tests/execution/ -x -q
   ```
   Expected: all passing
3. This session has no dependency on S2/S3/S4 — only requires S1 for type consistency

## Objective
Build the slippage model calibration utility that queries real execution records to produce a per-strategy slippage model, enabling BacktestEngine to use calibrated fills instead of fixed assumptions.

## Requirements

1. Create `argus/analytics/slippage_model.py` with:

   a. **`SlippageConfidence` enum** (StrEnum):
      - `HIGH = "high"` — 50+ execution records
      - `MODERATE = "moderate"` — 20–49 records
      - `LOW = "low"` — 5–19 records
      - `INSUFFICIENT = "insufficient"` — <5 records

   b. **`StrategySlippageModel` dataclass**:
      - `strategy_id: str`
      - `estimated_mean_slippage_bps: float` — mean observed slippage in basis points
      - `estimated_std_slippage_bps: float` — std dev of slippage
      - `time_of_day_adjustment: dict[str, float]` — `{"pre_10am": float, "10am_2pm": float, "post_2pm": float}` — additive bps adjustment
      - `size_adjustment_slope: float` — additional bps per 100 shares order size
      - `sample_count: int`
      - `confidence: SlippageConfidence`
      - `last_calibrated: datetime`
      - `to_dict()` / `from_dict()`

   c. **`async def calibrate_slippage_model(db_manager: DatabaseManager, strategy_id: str) → StrategySlippageModel`**:
      - Query `execution_records` table for the given strategy_id
      - If <5 records: return model with all zeros, confidence=INSUFFICIENT
      - Compute `estimated_mean_slippage_bps` = mean of `actual_slippage_bps` across all records
      - Compute `estimated_std_slippage_bps` = std dev of `actual_slippage_bps`
      - Time-of-day adjustment:
        - Group records by time bucket: pre-10:00 ET, 10:00–14:00 ET, post-14:00 ET
        - For each bucket: `bucket_mean - overall_mean` = adjustment (additive bps)
        - If bucket has <3 records, use 0.0 adjustment (insufficient data)
      - Size adjustment:
        - If sufficient variation in order sizes (std of order_size_shares > 0): linear regression of `actual_slippage_bps` on `order_size_shares / 100`, take slope
        - If insufficient variation: slope = 0.0
      - Confidence: based on record count (50+→HIGH, 20–49→MODERATE, 5–19→LOW)
      - `last_calibrated` = `datetime.now(UTC)`

   d. **`def save_slippage_model(model: StrategySlippageModel, path: str) → None`**:
      - Write `model.to_dict()` as JSON to the given file path
      - Atomic write (write to temp file, then rename)

   e. **`def load_slippage_model(path: str) → StrategySlippageModel`**:
      - Read JSON from path, return `StrategySlippageModel.from_dict()`
      - Raise `FileNotFoundError` if path doesn't exist
      - Raise `ValueError` if JSON is malformed

2. Add `__all__` exports.

3. The DB query should use `db_manager.execute()` with a raw SQL query against the `execution_records` table. Match the column names from `execution_record.py` (`actual_slippage_bps`, `time_of_day`, `order_size_shares`, `strategy_id`).

## Constraints
- Do NOT modify any existing files
- Do NOT modify the `execution_records` table schema
- Do NOT import from `argus/backtest/` — this is a standalone analytics utility
- Linear regression: use simple numpy-free computation (sum of products / sum of squares) — avoid adding numpy dependency just for one slope calculation

## Test Targets
New tests in `tests/analytics/test_slippage_model.py`:
1. `test_calibrate_sufficient_records` — 50 synthetic records → HIGH confidence, correct mean/std
2. `test_calibrate_moderate_records` — 25 records → MODERATE confidence
3. `test_calibrate_insufficient_records` — 3 records → INSUFFICIENT confidence, zeroed model
4. `test_time_of_day_adjustment` — records clustered morning/afternoon → different adjustments
5. `test_size_adjustment_slope` — larger orders have higher slippage → positive slope
6. `test_zero_slippage_records` — all zero slippage (paper trading) → mean=0.0, no error
7. `test_save_load_roundtrip` — save → load → identical model (use tmp_path fixture)
8. `test_load_missing_file` — FileNotFoundError raised
- Minimum new test count: 6
- Test command: `python -m pytest tests/analytics/test_slippage_model.py -x -v`

Note: Tests should use an in-memory SQLite database with synthetic execution records, not the production database.

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass
- [ ] New tests written and passing (≥6)
- [ ] `import argus.analytics.slippage_model` succeeds independently
- [ ] Close-out report written to `docs/sprints/sprint-27.5/session-5-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No existing file modifications | `git diff --name-only` shows only new files |
| execution_record.py not modified | `git diff argus/execution/execution_record.py` empty |
| DB schema unchanged | No new CREATE TABLE or ALTER TABLE statements |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
`docs/sprints/sprint-27.5/session-5-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-27.5/review-context.md`
2. Close-out: `docs/sprints/sprint-27.5/session-5-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command (scoped): `python -m pytest tests/analytics/test_slippage_model.py -x -v`
5. Files NOT modified: all existing files

Write review to: `docs/sprints/sprint-27.5/session-5-review.md`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review report files per the template
instructions (Post-Review Fixes section + CONCERNS_RESOLVED verdict).

## Session-Specific Review Focus (for @reviewer)
1. Verify DB query matches actual `execution_records` table column names
2. Verify time-of-day bucketing uses ET (Eastern Time), not UTC
3. Verify linear regression is correct (slope = Σ(xi-x̄)(yi-ȳ) / Σ(xi-x̄)²)
4. Verify atomic file write (temp file → rename, not direct write)
5. Verify <5 records returns a valid (zeroed) model, not an error
6. Verify no numpy dependency added

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Full pytest suite passes (≥3,071)
- [ ] No existing file modifications

## Sprint-Level Escalation Criteria (for @reviewer)
**Scope Creep:** Do not add calibration scheduling or auto-refresh.
