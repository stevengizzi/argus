# Sprint 25.5, Session 2: Zero-Evaluation Health Warning + E2E Telemetry Verification

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/health.py` (HealthMonitor class — understand component status model and existing checks)
   - `argus/strategies/base_strategy.py` (focus on `record_evaluation()`, `_eval_buffer`, watchlist property)
   - `argus/strategies/telemetry_store.py` (EvaluationEventStore — SQLite persistence)
   - `argus/api/server.py` (focus on EvaluationEventStore wiring to strategy buffers, Observatory init)
   - `argus/analytics/observatory_service.py` (understand `get_pipeline_stages()`, `get_session_summary()`)
   - `docs/sprints/sprint-25.5/session-1-closeout.md` (verify Session 1 completed successfully)
2. Run the test baseline (DEC-328 — Session 2, scoped):
   ```bash
   pytest tests/core/test_health.py tests/test_telemetry.py tests/test_telemetry_store.py -v
   ```
   Expected: all passing (full suite confirmed by Session 1 close-out)
3. Verify Session 1 changes are committed and present:
   - `base_strategy.py` has `_watchlist: set[str]`
   - `main.py` has UM watchlist population block after Phase 9.5

## Objective
Add a health warning that detects when an active strategy has zero evaluation events after its time window opens (preventing future silent failures like the 10-day gap). Write end-to-end tests confirming the full evaluation telemetry pipeline: candle → strategy → ring buffer → SQLite → Observatory endpoints.

## Requirements

1. **In `argus/core/health.py`:**
   - Add a method `check_strategy_evaluations(self, strategies: dict, eval_store, clock)` that:
     - For each strategy in the dict:
       - Skip if strategy is not active (`not strategy.is_active`)
       - Skip if strategy watchlist is empty (`len(strategy.watchlist) == 0`) — this means UM legitimately routed 0 symbols, not a bug
       - Determine if current time is past the strategy's time window start + 5 minutes. Each strategy has a configured entry window start time. Check the strategy's config for the window start (e.g., `strategy.config.entry_window_start` or similar — read the actual config structure from the strategy configs in `config/strategies/`).
       - If past window + 5 min: query `eval_store` for today's evaluation count for this strategy. If count == 0, emit a WARNING log: `"Strategy {strategy_id} has 0 evaluation events {minutes}min after window opened (watchlist: {count} symbols) — possible pipeline issue"`
       - Also update the per-strategy health component to `DEGRADED` with a descriptive message
     - This method should be safe to call repeatedly (idempotent — if evaluations appear later, the warning stops)
   - The method should be callable from `main.py` or `server.py` on a periodic timer (e.g., every 60 seconds during market hours). Wire it into an appropriate existing periodic check, or add a simple asyncio task.

2. **Wiring the health check:**
   - In `argus/main.py` or `argus/api/server.py` (whichever is more appropriate based on where the eval_store and strategies references are accessible), add a periodic asyncio task that calls `check_strategy_evaluations()` every 60 seconds during market hours (9:30–16:00 ET). The check only needs to run after each strategy's window start + 5 min — it's fine to call it every 60s and let the method short-circuit for strategies whose window hasn't opened yet.

3. **In `tests/test_evaluation_telemetry_e2e.py` (new file):**
   - Write end-to-end tests that verify the full telemetry pipeline:
     a. Create a strategy with a populated watchlist, deliver a candle event, verify `record_evaluation()` was called and an event appears in the ring buffer (`strategy._eval_buffer`)
     b. Verify that events in the ring buffer are persisted to the `evaluation_events` SQLite table via `EvaluationEventStore`
     c. Verify that `ObservatoryService.get_pipeline_stages()` returns non-empty data when evaluation events exist for the current trading date
     d. Verify that `ObservatoryService.get_session_summary()` returns non-empty data when evaluation events exist
   - Write health warning tests (can be in `tests/core/test_health.py` or the new e2e file):
     e. Health warning fires: active strategy, non-empty watchlist, 0 evaluations, time past window + 5 min
     f. No warning: strategy has ≥1 evaluation event
     g. No warning: strategy watchlist is empty (UM routed 0 symbols)
     h. No warning: current time is before strategy window start + 5 min

## Constraints
- Do NOT modify: `argus/data/universe_manager.py`, `argus/strategies/orb_base.py`, `argus/strategies/vwap_reclaim.py`, `argus/strategies/afternoon_momentum.py`, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`, `argus/execution/order_manager.py`, `argus/analytics/observatory_service.py`, any config YAML files, any frontend files
- Do NOT change: strategy `on_candle()` logic, candle routing, quality pipeline, Event Bus delivery
- Do NOT add: new API endpoints, config fields, database tables, or frontend components
- The health check must be **idempotent** — safe to call repeatedly, and self-correcting when evaluations start appearing

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests:
  1. `test_e2e_candle_to_ring_buffer` — candle → strategy → `record_evaluation()` → event in ring buffer
  2. `test_e2e_ring_buffer_to_sqlite` — events in buffer → persisted to `evaluation_events` table
  3. `test_e2e_observatory_pipeline_has_data` — `get_pipeline_stages()` non-empty with evaluation data
  4. `test_e2e_observatory_session_summary_has_data` — `get_session_summary()` non-empty with evaluation data
  5. `test_health_warning_fires_zero_evaluations` — active strategy, non-empty watchlist, 0 evals, past window → WARNING
  6. `test_health_no_warning_with_evaluations` — ≥1 eval → no warning
  7. `test_health_no_warning_empty_watchlist` — empty watchlist → no warning
  8. `test_health_no_warning_before_window` — before window + 5 min → no warning
- Minimum new test count: 8
- Test command: `pytest tests/test_evaluation_telemetry_e2e.py tests/core/test_health.py -v`

## Definition of Done
- [ ] `check_strategy_evaluations()` method implemented in health.py
- [ ] Periodic asyncio task calls the check every 60s during market hours
- [ ] WARNING logged when active strategy has 0 evals after window + 5 min
- [ ] No false warnings (empty watchlist, before window, evals present)
- [ ] E2E tests verify candle → ring buffer → SQLite → Observatory
- [ ] All existing tests pass
- [ ] 8+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| HealthMonitor existing components unchanged | Existing health tests pass |
| No false warnings during pre-market | Test with clock before window start |
| No warning when watchlist empty (UM routed 0) | Test with empty watchlist strategy |
| Warning self-corrects when evaluations appear | Call check twice: once with 0 evals (warns), once with 1+ eval (no warn) |
| Observatory endpoints still return 200 | `curl` test or integration test |

## Sprint-Level Regression Checklist
- [ ] Scanner-only flow unchanged (UM disabled → strategies get scanner symbols)
- [ ] `watchlist` property returns `list[str]` (not set)
- [ ] `set_watchlist()` accepts `list[str]` input
- [ ] Strategy `on_candle()` evaluation logic unchanged
- [ ] Risk Manager not affected
- [ ] Event Bus FIFO ordering preserved
- [ ] Order Manager not affected
- [ ] Quality pipeline not affected
- [ ] Observatory endpoints return 200
- [ ] No files in "do not modify" list were changed
- [ ] All pre-existing tests pass
- [ ] Candle routing path in main.py (lines 724-745) unchanged

## Sprint-Level Escalation Criteria
1. Performance degradation: heartbeat candle counts drop significantly or API latency degrades
2. More than 5 existing tests break from list→set conversion
3. Evaluation events not in SQLite despite ring buffer being populated
4. Observatory endpoints empty despite evaluation_events having rows
- Session 2 specific: Session 1 review REJECT → do not start; HealthMonitor lacks time-delayed check mechanism → redesign before implementing

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
docs/sprints/sprint-25.5/session-2-closeout.md

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-25.5/review-context.md`
2. The close-out report path: `docs/sprints/sprint-25.5/session-2-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (final session, full suite): `pytest --ignore=tests/test_main.py -n auto`
5. Files that should NOT have been modified: `argus/data/universe_manager.py`, `argus/strategies/orb_base.py`, `argus/strategies/vwap_reclaim.py`, `argus/strategies/afternoon_momentum.py`, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`, `argus/execution/order_manager.py`, `argus/analytics/observatory_service.py`, any config YAML files, any frontend files

The @reviewer will produce its review report and write it to:
docs/sprints/sprint-25.5/session-2-review.md

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, you MUST update the artifact trail:

1. Append a "Post-Review Fixes" section to `docs/sprints/sprint-25.5/session-2-closeout.md`
2. Append a "Resolved" annotation to `docs/sprints/sprint-25.5/session-2-review.md` and update the structured verdict to `CONCERNS_RESOLVED`

If the reviewer reports CLEAR or ESCALATE, skip this step.

## Session-Specific Review Focus (for @reviewer)
1. Verify `check_strategy_evaluations()` correctly distinguishes empty-watchlist (no warn) from populated-watchlist-zero-evals (warn)
2. Verify the periodic task only runs during market hours and does not spin outside 9:30–16:00 ET
3. Verify the method is idempotent — calling it repeatedly doesn't produce duplicate warnings or degrade health status incorrectly
4. Verify e2e tests actually exercise the full pipeline (candle → buffer → SQLite), not just mocking intermediate steps
5. Verify the health check reads strategy time window configs correctly (check against actual YAML values in `config/strategies/`)
6. Verify no changes to Observatory service or its endpoints — only querying existing functionality
