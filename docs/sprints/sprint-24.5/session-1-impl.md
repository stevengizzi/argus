# Sprint 24.5, Session 1: Telemetry Infrastructure + REST Endpoint

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/base_strategy.py`
   - `argus/core/events.py` (examine `QualitySignalEvent` for style consistency)
   - `argus/api/routes/strategies.py`
   - `argus/api/routes/quality.py` (endpoint pattern reference)
2. Run the test baseline (DEC-328 — Session 1, full suite):
   ```
   python -m pytest -x -q -n auto 2>&1 | tail -5
   cd argus/ui && npx vitest run 2>&1 | tail -5
   ```
   Expected: ~2,709 pytest passing (excluding DEF-048/049 known xdist failures), ~503 Vitest passing
3. Verify you are on the correct branch: `sprint-24.5`
   (Create branch from main if it doesn't exist: `git checkout -b sprint-24.5 main`)

## Objective
Create the evaluation event model, ring buffer, BaseStrategy integration, and
REST endpoint for querying strategy decisions. This is the foundation for all
subsequent sessions.

## Requirements

1. **Create `argus/strategies/telemetry.py`** containing:

   a. `EvaluationEventType` — StrEnum with values: `TIME_WINDOW_CHECK`,
      `INDICATOR_STATUS`, `OPENING_RANGE_UPDATE`, `ENTRY_EVALUATION`,
      `CONDITION_CHECK`, `SIGNAL_GENERATED`, `SIGNAL_REJECTED`,
      `STATE_TRANSITION`, `QUALITY_SCORED`

   b. `EvaluationResult` — StrEnum with values: `PASS`, `FAIL`, `INFO`

   c. `EvaluationEvent` — frozen dataclass with fields:
      - `timestamp: datetime` (ET naive datetime per DEC-276)
      - `symbol: str`
      - `strategy_id: str`
      - `event_type: EvaluationEventType`
      - `result: EvaluationResult`
      - `reason: str` (human-readable explanation)
      - `metadata: dict[str, object]` (default_factory=dict, strategy-specific data)

   d. `StrategyEvaluationBuffer` — class wrapping `collections.deque(maxlen=1000)`:
      - `__init__(self, maxlen: int = 1000)` — create deque
      - `record(self, event: EvaluationEvent) -> None` — append to deque
      - `query(self, *, symbol: str | None = None, limit: int = 100) -> list[EvaluationEvent]` — filter and return. Iterate deque in reverse (newest first), apply symbol filter if provided, stop at limit.
      - `snapshot(self) -> list[EvaluationEvent]` — return `list(self._events)` for thread-safe reads
      - `__len__(self) -> int` — return len of deque
      - Use `BUFFER_MAX_SIZE = 1000` as module-level constant

2. **Modify `argus/strategies/base_strategy.py`**:

   a. Import `EvaluationEvent`, `EvaluationEventType`, `EvaluationResult`,
      `StrategyEvaluationBuffer` from `argus.strategies.telemetry`

   b. In `__init__()`, add: `self._eval_buffer = StrategyEvaluationBuffer()`

   c. Add property:
      ```python
      @property
      def eval_buffer(self) -> StrategyEvaluationBuffer:
          return self._eval_buffer
      ```

   d. Add convenience method:
      ```python
      def record_evaluation(
          self,
          symbol: str,
          event_type: EvaluationEventType,
          result: EvaluationResult,
          reason: str,
          metadata: dict[str, object] | None = None,
      ) -> None:
          """Record a strategy evaluation event. Fire-and-forget — never raises."""
          try:
              et_tz = ZoneInfo("America/New_York")
              event = EvaluationEvent(
                  timestamp=datetime.now(et_tz).replace(tzinfo=None),
                  symbol=symbol,
                  strategy_id=self.strategy_id,
                  event_type=event_type,
                  result=result,
                  reason=reason,
                  metadata=metadata or {},
              )
              self._eval_buffer.record(event)
          except Exception:
              pass  # Telemetry must never impact strategy operation
      ```
      Add necessary imports: `from datetime import datetime` and `from zoneinfo import ZoneInfo`

3. **Modify `argus/api/routes/strategies.py`**:

   Add a new endpoint:
   ```python
   @router.get("/{strategy_id}/decisions")
   async def get_strategy_decisions(
       strategy_id: str,
       symbol: str | None = Query(None),
       limit: int = Query(100, ge=1, le=500),
       state: AppState = Depends(get_app_state),
       _user=Depends(require_auth),
   ):
   ```
   - Look up strategy by `strategy_id` in `state.strategies`
   - If not found, raise `HTTPException(404, detail=f"Strategy {strategy_id} not found")`
   - Call `strategy.eval_buffer.query(symbol=symbol, limit=limit)`
   - Return list of events serialized as dicts (dataclasses.asdict)

## Constraints
- Do NOT modify: `argus/core/events.py`, `argus/main.py`,
  `argus/api/websocket/live.py`, `argus/core/orchestrator.py`
- Do NOT add EventBus event types for evaluation events
- Do NOT add config fields — buffer size is a code constant
- Preserve all existing endpoints in `strategies.py` exactly as-is

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write in `tests/test_telemetry.py`:
  1. `test_evaluation_event_type_enum_values` — 9 values exist
  2. `test_evaluation_result_enum_values` — 3 values exist
  3. `test_evaluation_event_construction` — all fields populated correctly
  4. `test_evaluation_event_frozen` — cannot modify after creation
  5. `test_buffer_record_and_query` — record events, query returns them
  6. `test_buffer_fifo_eviction` — exceed maxlen, oldest evicted
  7. `test_buffer_query_symbol_filter` — filter by symbol
  8. `test_buffer_query_limit` — limit results
  9. `test_buffer_snapshot_returns_copy` — snapshot is a separate list
  10. `test_record_evaluation_swallows_exceptions` — mock buffer.record to raise, verify no exception propagates
- New test in `tests/api/test_strategy_decisions.py`:
  11. `test_get_decisions_returns_events` — mock strategy with buffer events, verify 200 response
  12. `test_get_decisions_unknown_strategy_404` — verify 404 for unknown ID
  13. `test_get_decisions_requires_auth` — verify 401 without JWT
- Minimum new test count: 10
- Test command (scoped): `python -m pytest tests/test_telemetry.py tests/api/test_strategy_decisions.py -x -q`

## Definition of Done
- [ ] `argus/strategies/telemetry.py` created with all types and buffer class
- [ ] `BaseStrategy` has `_eval_buffer`, `eval_buffer` property, `record_evaluation()` method
- [ ] REST endpoint `GET /{strategy_id}/decisions` works with symbol/limit params
- [ ] All existing tests pass
- [ ] ≥10 new tests written and passing
- [ ] ruff linting passes
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| BaseStrategy subclasses still construct | `python -m pytest tests/ -k "test_orb or test_vwap or test_afternoon" -x -q --co` (collect without errors) |
| Existing strategy endpoints unchanged | `python -m pytest tests/api/ -k "strateg" -x -q` |
| record_evaluation never raises | Test #10 above |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file:**
docs/sprints/sprint-24.5/session-1-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-24.5/review-context.md`
2. The close-out report path: `docs/sprints/sprint-24.5/session-1-closeout.md`
3. The diff range: `git diff main...HEAD`
4. The test command (scoped, non-final): `python -m pytest tests/test_telemetry.py tests/api/test_strategy_decisions.py -x -q`
5. Files that should NOT have been modified: `argus/core/events.py`, `argus/main.py`, `argus/api/websocket/live.py`, `argus/core/orchestrator.py`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out report and review report files per the
template instructions.

## Session-Specific Review Focus (for @reviewer)
1. Verify `EvaluationEvent` is a frozen dataclass (not mutable)
2. Verify `record_evaluation()` has try/except around the entire body
3. Verify timestamps use ET naive datetimes (no tzinfo on stored datetime)
4. Verify REST endpoint is JWT-protected
5. Verify no changes to existing strategy endpoints in strategies.py
6. Verify `StrategyEvaluationBuffer.query()` returns newest-first ordering

## Sprint-Level Regression Checklist
(See review-context.md — embedded there for reviewer access)

## Sprint-Level Escalation Criteria
(See review-context.md — embedded there for reviewer access)
