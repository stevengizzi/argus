# Sprint 28, Session 2b: Correlation Analyzer

**⚠️ PARALLELIZABLE with Session 2a.** S2b creates ONLY `correlation_analyzer.py`. Do NOT touch `weight_analyzer.py` or `threshold_analyzer.py`.

## Pre-Flight Checks
1. Read: `argus/intelligence/learning/models.py`, `argus/intelligence/learning/outcome_collector.py`
2. Run: `python -m pytest tests/intelligence/learning/ -x -q` (S1 tests passing)
3. Verify correct branch

## Objective
Build the pairwise strategy return correlation analyzer.

## Requirements

1. **Create `argus/intelligence/learning/correlation_analyzer.py`:**
   - `CorrelationAnalyzer` class
   - `analyze(records: list[OutcomeRecord], config: LearningLoopConfig) -> CorrelationResult`:
     - Group records by strategy_id and date (ET date)
     - Compute daily P&L per strategy over `correlation_window_days`
     - **Source separation (Amendment 3):** Use trade-sourced records for correlation (counterfactual positions don't have real execution timing). If trade data insufficient, fall back to combined with MODERATE confidence note.
     - Exclude strategies with zero trades in window (add to excluded_strategies)
     - If fewer than 2 strategies have data → return CorrelationResult with empty matrix and informational message
     - Compute Pearson correlation for each strategy pair
     - Flag pairs exceeding `correlation_threshold` (default 0.7)
   - Use numpy for correlation computation (already in ARGUS dependencies)

## Constraints
- Do NOT modify any existing files or S1/S2a files
- Do NOT create weight_analyzer.py or threshold_analyzer.py (S2a)

## Test Targets
- `test_correlation_analyzer.py`: happy path (3+ strategies), single strategy (no matrix), zero trades exclusion, high correlation flagging, empty window, daily P&L aggregation correctness
- Minimum: 8 new tests
- Test command: `python -m pytest tests/intelligence/learning/ -x -q`

## Definition of Done
- [ ] CorrelationAnalyzer with daily P&L correlation computation
- [ ] Source preference for trade data (Amendment 3)
- [ ] Excluded strategies handling, flagged pairs
- [ ] ≥8 new tests
- [ ] Close-out to `docs/sprints/sprint-28/session-2b-closeout.md`
- [ ] @reviewer with review context at `docs/sprints/sprint-28/review-context.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify daily P&L aggregation groups by ET date correctly
2. Verify excluded strategies are properly tracked
3. Verify correlation threshold flagging works
4. Verify single-strategy edge case doesn't error

## Sprint-Level Regression Checklist / Escalation Criteria
*(See review-context.md)*
