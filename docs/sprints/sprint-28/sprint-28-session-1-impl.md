# Sprint 28, Session 1: Learning Data Models + Outcome Collector

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/counterfactual_store.py` (counterfactual DB schema)
   - `argus/intelligence/quality_engine.py` (quality scoring structure)
   - `argus/analytics/trade_logger.py` (trades table schema)
   - `argus/intelligence/filter_accuracy.py` (pattern reference for DB queries)
   - `docs/sprints/sprint-28/sprint-28-adversarial-review-output.md` (amendments)
2. Run the test baseline:
   Full suite: `python -m pytest --ignore=tests/test_main.py -n auto -q`
   Expected: ~3,693 tests, all passing
3. Verify you are on the correct branch (sprint-28 or main)
4. **Schema verification (Amendment 8):** Inspect the `quality_history` table in `argus.db`:
   ```sql
   .schema quality_history
   ```
   Confirm whether per-dimension score columns exist (pattern_strength_score, catalyst_quality_score, etc.). If they do NOT exist, flag this in the close-out and adjust OutcomeCollector to work with available columns (quality_score + quality_grade only). This finding affects S2a (WeightAnalyzer) scope.

## Objective
Establish the `argus/intelligence/learning/` package with all data models and the unified data reader that pulls from trades (argus.db), counterfactual positions (counterfactual.db), and quality history (argus.db).

## Requirements

1. **Create `argus/intelligence/learning/__init__.py`:**
   Re-export key classes: `OutcomeCollector`, `LearningReport`, `WeightRecommendation`, `ThresholdRecommendation`, `CorrelationResult`, `OutcomeRecord`, `LearningLoopConfig`, `ConfidenceLevel`.

2. **Create `argus/intelligence/learning/models.py`:**
   - `ConfidenceLevel` StrEnum: `HIGH`, `MODERATE`, `LOW`, `INSUFFICIENT_DATA`
   - `OutcomeRecord` frozen dataclass: symbol, strategy_id, quality_score, quality_grade, dimension_scores (dict[str, float] — per-dimension if available), regime_context (dict — primary_regime + full vector snapshot), pnl (float), r_multiple (float | None), source (Literal["trade", "counterfactual"]), timestamp (datetime), rejection_stage (str | None), rejection_reason (str | None)
   - `DataQualityPreamble` frozen dataclass: trading_days_count, total_trades, total_counterfactual, effective_sample_size, known_data_gaps (list[str]), earliest_date, latest_date
   - `WeightRecommendation` frozen dataclass: dimension, current_weight, recommended_weight, delta, correlation_trade_source (float | None), correlation_counterfactual_source (float | None), p_value (float | None), sample_size, confidence (ConfidenceLevel), regime_breakdown (dict[str, float] — regime→correlation), source_divergence_flag (bool)
   - `ThresholdRecommendation` frozen dataclass: grade, current_threshold, recommended_direction (Literal["raise", "lower"]), missed_opportunity_rate, correct_rejection_rate, sample_size, confidence (ConfidenceLevel)
   - `CorrelationResult` frozen dataclass: strategy_pairs (list of tuples), correlation_matrix (dict[tuple[str,str], float]), flagged_pairs (list — pairs exceeding threshold), excluded_strategies (list — zero trades), window_days (int)
   - `LearningReport` frozen dataclass: report_id (str — ULID), generated_at (datetime), analysis_window_start, analysis_window_end, data_quality (DataQualityPreamble), weight_recommendations (list[WeightRecommendation]), threshold_recommendations (list[ThresholdRecommendation]), correlation_result (CorrelationResult | None), version (int = 1 — for ExperimentRegistry forward-compat). Include `to_dict()` and `from_dict()` methods for JSON serialization.
   - `LearningLoopConfig` Pydantic BaseModel with all 13 config fields (see Review Context File for final field list post-amendment). Include validators: `min_sample_count >= 5`, `max_weight_change_per_cycle` between 0.01 and 0.50, `max_cumulative_drift` between 0.05 and 0.50, `correlation_p_value_threshold` between 0.01 and 0.20.
   - `ConfigProposal` frozen dataclass: proposal_id (ULID), report_id, field_path (str — e.g., "weights.pattern_strength"), current_value (float), proposed_value (float), rationale (str), status (str — PENDING/APPROVED/DISMISSED/SUPERSEDED/REJECTED_GUARD/REJECTED_VALIDATION/APPLIED/REVERTED), created_at, updated_at, human_notes (str | None)

3. **Create `argus/intelligence/learning/outcome_collector.py`:**
   - `OutcomeCollector` class with async methods
   - Constructor takes DB paths: `argus_db_path`, `counterfactual_db_path` (defaulting to standard locations)
   - `async collect(start_date, end_date, strategy_id=None) -> list[OutcomeRecord]`:
     - Query trades table for closed trades in date range → OutcomeRecord(source="trade")
     - Query counterfactual_positions for closed positions in date range → OutcomeRecord(source="counterfactual")
     - Query quality_history for per-dimension scores (join by symbol + timestamp proximity or signal metadata)
     - Normalize into unified OutcomeRecord list
     - Handle empty databases gracefully (return [])
   - `async build_data_quality_preamble(records) -> DataQualityPreamble`:
     - Count trading days, trades vs counterfactual, date range
     - Flag known data gaps (e.g., pre-Sprint-27.95 sessions may have reconciliation artifacts)
   - All queries are read-only. No writes to any database.
   - Use `aiosqlite` for async DB access (existing pattern in ARGUS)

## Constraints
- Do NOT modify any existing files
- Do NOT create any SQLite databases (LearningStore handles that in S3a)
- Do NOT import from modules that don't exist yet (analyzers, store, service)
- Quality_history schema may not have per-dimension columns — handle gracefully (use composite score + grade if per-dimension unavailable, note in close-out)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write in `tests/intelligence/learning/`:
  - `test_models.py`: serialization round-trip for LearningReport, ConfigProposal state values, LearningLoopConfig validation (valid + invalid values)
  - `test_outcome_collector.py`: collect from trades-only, counterfactual-only, both sources, empty DBs, date filtering, strategy filtering, source field correctness, data quality preamble computation
- Minimum new tests: 15
- Test command (scoped): `python -m pytest tests/intelligence/learning/ -x -q`

## Config Validation
Write a test that loads `config/learning_loop.yaml` (created in S4, but test the Pydantic model with inline dict):
1. Construct LearningLoopConfig from a dict with all expected keys
2. Assert all fields have correct defaults
3. Assert validator rejects `min_sample_count: 2` (below minimum)
4. Assert validator rejects `max_weight_change_per_cycle: 0.0` (below minimum)

## Definition of Done
- [ ] `argus/intelligence/learning/` package created with `__init__.py`, `models.py`, `outcome_collector.py`
- [ ] All models are frozen dataclasses (except LearningLoopConfig which is Pydantic)
- [ ] LearningReport has to_dict()/from_dict() for JSON serialization
- [ ] OutcomeCollector reads from trades + counterfactual + quality_history
- [ ] Empty databases return empty list, not error
- [ ] Schema verification finding documented in close-out (Amendment 8)
- [ ] All existing tests pass
- [ ] ≥15 new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No existing files modified | `git diff --name-only` shows only new files in `argus/intelligence/learning/` and `tests/intelligence/learning/` |
| OutcomeCollector is read-only | Grep for INSERT/UPDATE/DELETE in outcome_collector.py — should find none |
| Import doesn't break existing code | `python -c "from argus.intelligence.learning import OutcomeCollector"` succeeds |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.
Write close-out to: `docs/sprints/sprint-28/session-1-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After close-out, invoke @reviewer with:
1. Review context: `docs/sprints/sprint-28/review-context.md`
2. Close-out: `docs/sprints/sprint-28/session-1-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command (scoped): `python -m pytest tests/intelligence/learning/ -x -q`
5. Files NOT modified: everything outside `argus/intelligence/learning/` and `tests/intelligence/learning/`

## Session-Specific Review Focus (for @reviewer)
1. Verify OutcomeCollector queries are read-only (no INSERT/UPDATE/DELETE)
2. Verify LearningReport.to_dict()/from_dict() round-trips correctly
3. Verify LearningLoopConfig Pydantic validators reject invalid values
4. Verify OutcomeRecord.source field is correctly set ("trade" vs "counterfactual")
5. Check whether quality_history schema finding was documented (Amendment 8)
6. Verify ConfigProposal state machine values match Amendment 6 (PENDING/APPROVED/DISMISSED/SUPERSEDED/REJECTED_GUARD/REJECTED_VALIDATION/APPLIED/REVERTED)

## Sprint-Level Regression Checklist
*(See review-context.md)*

## Sprint-Level Escalation Criteria
*(See review-context.md)*
