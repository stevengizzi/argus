# Sprint 25.6, Session 1: Telemetry Store DB Separation + Log Hygiene

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/telemetry_store.py`
   - `argus/main.py` (search for `EvaluationEventStore` and `_run_evaluation_health_check`)
   - `argus/api/server.py` (search for `EvaluationEventStore` and `telemetry_store`)
   - `argus/intelligence/storage.py` (reference: how `catalyst.db` separation was done — DEC-309 pattern)
2. Run the full test baseline (DEC-328 — Session 1 of sprint):
   ```
   python -m pytest tests/ --ignore=tests/test_main.py -n auto -q
   ```
   Expected: ~2,765 tests, all passing
   ```
   cd argus/ui && npx vitest run
   ```
   Expected: ~599 tests, all passing
3. Verify you are on branch: `main`

## Objective
Move `evaluation_events` to a dedicated `data/evaluation.db` database file (eliminating SQLite write contention with `argus.db`), reuse the store instance in the health check loop (eliminating 60-second initialization spam), and rate-limit repeated write failure warnings.

## Requirements

### 1. Separate evaluation database (DEF-065)
In `argus/strategies/telemetry_store.py`:
- The `__init__` method already accepts `db_path`. No change needed to the constructor.
- The fix is in the *callers* — they must pass `data/evaluation.db` instead of `data/argus.db`.

In `argus/api/server.py` (lifespan initialization):
- Where `EvaluationEventStore` is created (~line 262), change the `db_path` from `data/argus.db` to `data/evaluation.db`.
- Ensure the parent directory exists before connecting (should be `data/` which already exists).

### 2. Reuse store instance in health check (DEF-066)
In `argus/main.py`, method `_run_evaluation_health_check()` (~line 720):
- Currently creates a new `EvaluationEventStore(db_path)` every 60 seconds, calls `initialize()`, uses it, then `close()`.
- Change to: accept the store instance as a parameter or store it on `self`.
- The store is already created in `server.py` lifespan and stored on `app_state`. Pass it to `ArgusSystem` or make it accessible.

Approach: Store the `EvaluationEventStore` instance on `ArgusSystem` as `self._eval_store`. In `server.py`, after initializing the store, set `app_state.system._eval_store = telemetry_store` (the ArgusSystem instance is accessible via `app_state.system`). Then in `_run_evaluation_health_check()`, use `self._eval_store` instead of creating a new one.

If `app_state.system` is not directly accessible, an alternative: have `main.py` create its own `EvaluationEventStore("data/evaluation.db")` during startup (before the API server) and pass it to both `server.py` (for strategy buffer wiring) and the health check loop.

### 3. Rate-limit write failure warnings
In `argus/strategies/telemetry_store.py`, method `write_event()`:
- Add a class-level `_last_warning_time` attribute (initialized to 0).
- In the `except` block, only call `logger.warning("Failed to write evaluation event", exc_info=True)` if at least 60 seconds have elapsed since the last warning.
- Otherwise, silently pass (the event is already lost; spamming the log doesn't help).
- On the first failure after a quiet period, log with `exc_info=True` (full traceback). Subsequent suppressed failures within the window: no log at all.

## Constraints
- Do NOT modify: `argus/db/manager.py`, `argus/analytics/trade_logger.py`, `argus/intelligence/storage.py`, any strategy file
- Do NOT change the `evaluation_events` table schema
- Do NOT change how `ObservatoryService` queries the store (it uses `execute_query()` which works regardless of DB file location)
- Do NOT add new config fields

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. Test that `EvaluationEventStore` connects to `evaluation.db` path (not `argus.db`)
  2. Test that write_event succeeds when no other DB connections contend
  3. Test that the rate-limiting suppresses repeated warnings (mock logger, fire multiple failures within 60s, assert ≤1 warning)
  4. Test that health check method works with pre-initialized store (no `initialize()` call)
  5. Test that `argus.db` tables (trades, quality_history) are unaffected by evaluation.db separation
- Minimum new test count: 5
- Test command: `python -m pytest tests/strategies/test_telemetry_store.py tests/test_evaluation_telemetry_e2e.py -x -v`

## Definition of Done
- [ ] `EvaluationEventStore` initialized with `data/evaluation.db` path
- [ ] Health check loop uses existing store instance (no per-cycle initialization)
- [ ] Write failure warnings rate-limited to 1 per 60 seconds
- [ ] All existing tests pass
- [ ] 5+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Trades still in argus.db | `python -c "import sqlite3; print(sqlite3.connect('data/argus.db').execute('SELECT COUNT(*) FROM trades').fetchone())"` |
| Quality history still in argus.db | Same query for `quality_history` |
| Evaluation events in evaluation.db | Same query on `data/evaluation.db` for `evaluation_events` |
| No store initialization spam | Grep logs for "EvaluationEventStore initialized" — ≤2 |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema and requirements.

**Write the close-out report to a file:**
`docs/sprints/sprint-25.6/session-1-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer subagent.

Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-25.6/review-context.md`
2. Close-out report: `docs/sprints/sprint-25.6/session-1-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command (scoped — non-final session): `python -m pytest tests/strategies/test_telemetry_store.py tests/test_evaluation_telemetry_e2e.py -x -v`
5. Files that should NOT have been modified: `risk_manager.py`, `order_manager.py`, `ibkr_broker.py`, `trade_logger.py`, `db/manager.py`, any strategy file

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this session, update both the close-out and review files per the template instructions.

## Session-Specific Review Focus (for @reviewer)
1. Verify `evaluation.db` is the path used in initialization, not `argus.db`
2. Verify the health check loop does NOT call `EvaluationEventStore()` or `initialize()` on each cycle
3. Verify the rate-limiting logic uses time-based suppression (not a counter)
4. Verify no `argus.db` tables were affected by the change
5. Verify `ObservatoryService` queries still work (it queries through the store's `execute_query()`)

## Sprint-Level Regression Checklist
(See review-context.md)

## Sprint-Level Escalation Criteria
(See review-context.md)
