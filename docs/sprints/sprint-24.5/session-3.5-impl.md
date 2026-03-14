# Sprint 24.5, Session 3.5: Evaluation Event Persistence

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/telemetry.py` (S1 — event model and buffer)
   - `argus/api/routes/strategies.py` (S1 — existing decisions endpoint)
   - `argus/db/manager.py` (DB patterns — table creation, async queries)
   - `argus/api/routes/quality.py` (historical query pattern reference)
   - `argus/api/server.py` (server lifespan — where to initialize store)
2. Run scoped test baseline (DEC-328 — Session 2+):
   ```
   python -m pytest tests/test_telemetry.py tests/strategies/ tests/api/test_strategy_decisions.py -x -q
   ```
   Expected: all passing
3. Verify branch: `sprint-24.5`

## Objective
Add SQLite persistence for evaluation events with historical query support and
automatic retention cleanup, so evaluation data survives system restarts and
enables after-close diagnostic review.

## Requirements

1. **Create `argus/strategies/telemetry_store.py`** containing:

   `EvaluationEventStore` class:

   a. `__init__(self, db_path: str)` — store db_path, set
      `RETENTION_DAYS = 7` as class constant

   b. `async def initialize(self) -> None` — create `evaluation_events` table
      if not exists:
      ```sql
      CREATE TABLE IF NOT EXISTS evaluation_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          trading_date TEXT NOT NULL,
          timestamp TEXT NOT NULL,
          symbol TEXT NOT NULL,
          strategy_id TEXT NOT NULL,
          event_type TEXT NOT NULL,
          result TEXT NOT NULL,
          reason TEXT NOT NULL,
          metadata_json TEXT DEFAULT '{}'
      )
      ```
      Create indexes:
      - `CREATE INDEX IF NOT EXISTS idx_eval_date_strategy ON evaluation_events(trading_date, strategy_id)`
      - `CREATE INDEX IF NOT EXISTS idx_eval_date_symbol ON evaluation_events(trading_date, symbol)`

   c. `async def write_event(self, event: EvaluationEvent) -> None` — insert
      event into table. Extract `trading_date` from `event.timestamp` as
      YYYY-MM-DD string. Serialize `event.metadata` to JSON. Use aiosqlite.
      Wrap in try/except — log warning on failure, never raise.

   d. `async def query_events(self, *, strategy_id: str, symbol: str | None = None, date: str | None = None, limit: int = 100) -> list[dict]` —
      query evaluation_events table with filters. Return list of dicts.
      Order by timestamp DESC. If date is None, use today's date (ET).

   e. `async def cleanup_old_events(self) -> None` — delete events where
      trading_date is older than RETENTION_DAYS days ago. Log the count deleted.

   f. Use `aiosqlite` for all DB operations. Follow patterns in `db/manager.py`.

2. **Modify `argus/strategies/telemetry.py`**:

   a. Add optional store reference to `StrategyEvaluationBuffer`:
      ```python
      def set_store(self, store: "EvaluationEventStore") -> None:
          self._store = store
      ```

   b. Modify `record()` to also write to store if set:
      ```python
      def record(self, event: EvaluationEvent) -> None:
          self._events.append(event)
          if self._store is not None:
              # Fire-and-forget async write — schedule on event loop
              try:
                  import asyncio
                  loop = asyncio.get_running_loop()
                  loop.create_task(self._store.write_event(event))
              except Exception:
                  pass  # No event loop or store error — degrade gracefully
      ```

   c. Initialize `self._store = None` in `__init__()`

3. **Modify `argus/api/routes/strategies.py`**:

   a. Add `date` query parameter to the decisions endpoint:
      ```python
      date: str | None = Query(None, description="Date (YYYY-MM-DD) for historical query")
      ```

   b. Logic: if `date` is provided and is NOT today's date, query the store
      (via `state.telemetry_store.query_events(...)`). If `date` is None or
      today, use the ring buffer as before. If store is not available (None),
      fall back to ring buffer regardless of date.

4. **Wire into server lifespan** (`argus/api/server.py` or wherever the
   application lifespan is defined):

   a. During startup, after DB initialization:
      - Create `EvaluationEventStore(db_path=...)` using the same DB path as
        the main database
      - Call `await store.initialize()` to create table
      - Call `await store.cleanup_old_events()` to purge old data
      - Store on `app_state.telemetry_store` (add field to AppState)

   b. After strategies are created, wire the store into each strategy's buffer:
      ```python
      for strategy in state.strategies.values():
          strategy.eval_buffer.set_store(store)
      ```

5. **Modify `argus/api/dependencies.py`** (AppState):
   - Add `telemetry_store: EvaluationEventStore | None = None`

## Constraints
- Do NOT modify: `argus/core/events.py`, `argus/main.py`,
  `argus/core/orchestrator.py`, any strategy files (orb_base, vwap_reclaim, etc.)
- Do NOT create a separate database file — use existing argus.db
- Do NOT add batch writing or write-behind queues — inline async writes
- Persistence failures must never impact ring buffer or strategy operation
- Table creation must be idempotent (IF NOT EXISTS)

## Test Targets
New tests in `tests/test_telemetry_store.py`:
1. `test_store_initialize_creates_table` — table exists after init
2. `test_store_write_and_read_event` — write event, query it back
3. `test_store_query_by_strategy_id` — only matching strategy returned
4. `test_store_query_by_symbol` — only matching symbol returned
5. `test_store_query_by_date` — only matching date returned
6. `test_store_combined_filters` — strategy + symbol + date
7. `test_store_cleanup_purges_old` — events older than 7 days deleted
8. `test_store_cleanup_preserves_recent` — recent events survive cleanup
9. `test_store_write_failure_doesnt_raise` — mock DB failure, no exception
10. `test_rest_date_param_routes_to_store` — API with ?date=past queries store
11. `test_rest_no_date_uses_buffer` — API without date uses ring buffer
- Minimum new test count: 10
- Test command: `python -m pytest tests/test_telemetry_store.py tests/test_telemetry.py tests/api/test_strategy_decisions.py -x -q`

## Definition of Done
- [ ] `telemetry_store.py` created with EvaluationEventStore
- [ ] Buffer forwards events to store when wired
- [ ] REST `?date=` parameter queries SQLite for historical data
- [ ] Store initialized in server lifespan
- [ ] 7-day retention cleanup runs at startup
- [ ] All existing tests pass
- [ ] ≥10 new tests written and passing
- [ ] ruff linting passes
- [ ] Close-out report written to docs/sprints/sprint-24.5/session-3.5-closeout.md
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Ring buffer still works without store | Existing S1 tests pass |
| Existing DB tables unaffected | `python -m pytest tests/ -k "db or trade_logger" -x -q` |
| REST endpoint without date param unchanged | Existing S1 API tests pass |
| Strategy construction unaffected | `python -m pytest tests/strategies/ -x -q --co` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file:**
docs/sprints/sprint-24.5/session-3.5-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-24.5/review-context.md`
2. Close-out: `docs/sprints/sprint-24.5/session-3.5-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command (scoped, non-final): `python -m pytest tests/test_telemetry_store.py tests/test_telemetry.py tests/api/test_strategy_decisions.py -x -q`
5. Files NOT to modify: `argus/core/events.py`, `argus/main.py`, any strategy files

## Session-Specific Review Focus (for @reviewer)
1. Verify table creation is idempotent (IF NOT EXISTS)
2. Verify write_event() has try/except — never raises
3. Verify buffer.record() still works when store is None (graceful degradation)
4. Verify loop.create_task usage is correct for fire-and-forget async
5. Verify cleanup uses ET dates (not UTC) for retention boundary
6. Verify AppState.telemetry_store field added correctly
7. Verify server lifespan wires store into all strategy buffers

## Sprint-Level Regression Checklist
(See review-context.md)

## Sprint-Level Escalation Criteria
(See review-context.md)
