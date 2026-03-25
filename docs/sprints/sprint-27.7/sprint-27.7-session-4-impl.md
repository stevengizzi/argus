# Sprint 27.7, Session 4: FilterAccuracy + API Endpoint + Integration Tests

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/counterfactual.py` (CounterfactualTracker, CounterfactualPosition, RejectionStage)
   - `argus/intelligence/counterfactual_store.py` (query methods — get_closed_positions, query)
   - `argus/api/routes.py` (existing API endpoint patterns, JWT protection)
   - `argus/main.py` (post-S3b state — full counterfactual wiring)
2. Run scoped test baseline (DEC-328):
   ```
   python -m pytest tests/intelligence/ tests/test_signal_rejected.py -x -q
   ```
   Expected: all passing (Session 3b close-out confirmed full suite)
3. Verify you are on branch `main` or `sprint-27.7`

## Objective
Build the FilterAccuracy computation module that answers "what percentage of rejected signals would have lost money?", expose it via a REST endpoint, and write full lifecycle integration tests proving the complete counterfactual pipeline works end-to-end.

## Requirements

### 1. Create `argus/intelligence/filter_accuracy.py`

1a. Define `FilterAccuracyBreakdown` dataclass:
```python
@dataclass
class FilterAccuracyBreakdown:
    """Accuracy metric for a single filter category."""
    category: str  # The category value (e.g., "QUALITY_FILTER", "B+", "orb_breakout")
    total_rejections: int
    correct_rejections: int  # Would have lost money (stop hit or negative EOD)
    incorrect_rejections: int  # Would have made money (target hit or positive EOD)
    accuracy: float  # correct / total (0.0–1.0)
    avg_theoretical_pnl: float  # Average P&L of all rejected signals in this category
    sample_sufficient: bool  # True if total >= min_sample_count
```

1b. Define `FilterAccuracyReport` dataclass:
```python
@dataclass
class FilterAccuracyReport:
    """Complete filter accuracy analysis."""
    computed_at: datetime
    date_range_start: datetime
    date_range_end: datetime
    total_positions: int
    by_stage: list[FilterAccuracyBreakdown]  # QUALITY_FILTER, POSITION_SIZER, RISK_MANAGER, SHADOW
    by_reason: list[FilterAccuracyBreakdown]  # Top N unique reasons
    by_grade: list[FilterAccuracyBreakdown]  # A+, A, B+, B, C+, C, C-
    by_strategy: list[FilterAccuracyBreakdown]  # Per strategy_id
    by_regime: list[FilterAccuracyBreakdown]  # Per primary_regime from regime_vector_snapshot
```

1c. Define `compute_filter_accuracy()` function:
```python
async def compute_filter_accuracy(
    store: CounterfactualStore,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    strategy_id: str | None = None,
    min_sample_count: int = 10,
) -> FilterAccuracyReport:
```

Logic:
- Query `store.get_closed_positions()` with date/strategy filters
- A rejection is "correct" if `theoretical_pnl <= 0` (the filter saved money by rejecting)
- A rejection is "incorrect" if `theoretical_pnl > 0` (the filter missed a profitable trade)
- Group by stage, rejection_reason, quality_grade, strategy_id, primary_regime
- For each group, compute accuracy = correct / total
- Set `sample_sufficient = (total >= min_sample_count)`
- Breakdowns with total < min_sample_count still included but flagged as insufficient

1d. Handle edge cases:
- Zero positions → return report with empty breakdowns and total_positions=0
- Division by zero → accuracy = 0.0 when total_rejections = 0 (should not occur if position exists, but guard)
- Missing quality_grade or regime_vector → group under "unknown" category
- Positions still open (no exit) → excluded from accuracy computation (only closed positions)

### 2. Add REST endpoint to API

Add `GET /api/v1/counterfactual/accuracy` to the appropriate routes file:

```python
@router.get("/api/v1/counterfactual/accuracy")
async def get_counterfactual_accuracy(
    start_date: str | None = None,  # ISO 8601
    end_date: str | None = None,
    strategy_id: str | None = None,
    min_sample_count: int = 10,
    # JWT auth via dependency
):
```

Returns JSON serialization of `FilterAccuracyReport`. If the counterfactual store is not available (disabled), return 200 with an empty report (not 503).

Parse `start_date`/`end_date` from ISO strings. Validate `min_sample_count >= 1`.

### 3. Full lifecycle integration tests

Write integration tests that exercise the complete pipeline:

3a. **Rejection → tracking → monitoring → close → accuracy:**
- Create a mock signal with known entry/stop/target
- Publish a `SignalRejectedEvent` on a test event bus
- Feed candle events that trigger the stop
- Verify position closed as STOPPED_OUT
- Query filter accuracy, verify correct rejection counted

3b. **Multiple rejections → accuracy by stage:**
- Create 3 rejections: 1 quality filter (target hit = incorrect), 1 sizer (stop hit = correct), 1 risk manager (stop hit = correct)
- Feed candles to close all 3
- Verify accuracy: quality_filter = 0.0, position_sizer = 1.0, risk_manager = 1.0

3c. **EOD close integration:**
- Open counterfactual position, don't trigger stop or target
- Call close_all_eod()
- Verify position closed as EOD_CLOSED with mark-to-market P&L

3d. **Config disabled → nothing happens:**
- Set counterfactual.enabled=false
- Publish rejection events → no counterfactual positions created
- Verify empty accuracy report

## Constraints
- Do NOT modify: `argus/core/risk_manager.py`, `argus/core/regime.py`, `argus/intelligence/counterfactual.py` (read-only consumer), `argus/intelligence/counterfactual_store.py` (read-only consumer), any strategy files, any frontend files
- Do NOT add: Shadow mode (S5), Copilot context injection, WebSocket streaming
- Accuracy computation queries the store — it does NOT modify counterfactual positions

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. **accuracy: correct rejection (stop hit)** — P&L negative → counted as correct
  2. **accuracy: incorrect rejection (target hit)** — P&L positive → counted as incorrect
  3. **accuracy: by stage** — 3 stages, each with known outcomes → correct accuracy per stage
  4. **accuracy: by quality grade** — rejections at different grades → grade breakdown correct
  5. **accuracy: by strategy** — rejections from different strategies → strategy breakdown
  6. **accuracy: min sample threshold** — fewer than 10 → sample_sufficient=False
  7. **accuracy: empty data** — no positions → empty report, total=0
  8. **accuracy: date range filtering** — positions across dates → only filtered range included
  9. **API: endpoint returns 200** — valid request → JSON response with report
  10. **API: endpoint 401 unauthorized** — no JWT → 401
  11. **integration: full lifecycle** — rejection → candle monitoring → close → accuracy
  12. **integration: EOD close lifecycle** — rejection → no trigger → EOD → mark-to-market
- Minimum new test count: 10
- Test files: `tests/intelligence/test_filter_accuracy.py`, `tests/api/test_counterfactual_api.py`, `tests/intelligence/test_counterfactual_integration.py`
- Test command: `python -m pytest tests/intelligence/test_filter_accuracy.py tests/api/test_counterfactual_api.py tests/intelligence/test_counterfactual_integration.py -x -q`

## Definition of Done
- [ ] `argus/intelligence/filter_accuracy.py` created with FilterAccuracyReport and compute_filter_accuracy()
- [ ] `GET /api/v1/counterfactual/accuracy` endpoint working (JWT-protected, 200/401)
- [ ] Full lifecycle integration tests passing
- [ ] Edge cases handled (zero positions, missing grades, min sample threshold)
- [ ] All existing tests pass
- [ ] ≥10 new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| Accuracy computation doesn't modify store data | Verify no writes in filter_accuracy.py — read-only queries |
| API endpoint follows existing patterns (JWT, error handling) | Compare with existing endpoints in routes.py |
| Integration tests don't leave stale DB files | Tests use tmpdir/tmp_path for DB files |
| No changes to counterfactual.py or counterfactual_store.py | `git diff argus/intelligence/counterfactual.py argus/intelligence/counterfactual_store.py` shows no changes |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file:**
`docs/sprints/sprint-27.7/session-4-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-27.7/review-context.md`
2. The close-out report path: `docs/sprints/sprint-27.7/session-4-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/intelligence/test_filter_accuracy.py tests/api/test_counterfactual_api.py tests/intelligence/test_counterfactual_integration.py -x -q`
5. Files that should NOT have been modified: `argus/core/risk_manager.py`, `argus/intelligence/counterfactual.py`, `argus/intelligence/counterfactual_store.py`, any files in `argus/strategies/`, any files in `argus/ui/`

The @reviewer will write its report to:
`docs/sprints/sprint-27.7/session-4-review.md`

## Post-Review Fix Documentation
If CONCERNS, update both close-out and review files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify "correct rejection" definition: theoretical_pnl <= 0 means the filter was right to reject
2. Verify accuracy handles zero-division (no rejections in a category)
3. Verify min_sample_count threshold is respected — breakdowns with fewer samples flagged but included
4. Verify API endpoint returns 200 with empty report when no data exists (not 404 or 500)
5. Verify integration tests cover the full lifecycle (rejection → candle → close → accuracy query)
6. Verify filter_accuracy.py only reads from the store — no writes

## Sprint-Level Regression Checklist (for @reviewer)
(see review-context.md)

## Sprint-Level Escalation Criteria (for @reviewer)
(see review-context.md)
