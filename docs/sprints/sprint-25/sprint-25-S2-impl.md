# Sprint 25, Session 2: Backend — WebSocket Live Updates

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/sprints/sprint-25/sprint-spec.md`
   - `argus/api/websocket/ai_chat.py` (existing WS pattern — follow this pattern)
   - `argus/analytics/observatory_service.py` (S1 output — your data source)
   - `server.py` (WS mount pattern)
   - `argus/config/` (ObservatoryConfig from S1)
2. Run scoped test baseline (DEC-328):
   `python -m pytest tests/analytics/test_observatory_service.py tests/api/test_observatory_routes.py -x -q`
   Expected: all passing
3. Verify you are on the correct branch

## Objective
Create a WebSocket endpoint that pushes real-time Observatory data (pipeline stage counts, tier transitions, evaluation summaries) to connected clients at a configurable interval. This drives the live-updating behavior of all Observatory frontend views.

## Requirements

1. **Create `argus/api/websocket/observatory_ws.py`:**

   WebSocket endpoint at `/ws/v1/observatory` following the pattern established in `ai_chat.py`:
   - JWT authentication on connection (same pattern as ai_chat)
   - Accept connection, begin push loop
   - Push interval driven by `ObservatoryConfig.ws_update_interval_ms` (default 1000ms)

   Each push sends a JSON message with type field:

   a. `pipeline_update` — full pipeline stage counts (calls `ObservatoryService.get_pipeline_stages()`). Sent every interval.

   b. `tier_transition` — when a symbol's tier changes between updates. Compare current pipeline state with previous state to detect transitions. Include: `symbol`, `from_tier`, `to_tier`, `timestamp`. Sent as they occur (piggybacked on the next interval push).

   c. `evaluation_summary` — compact summary of evaluation activity since last push: `evaluations_count`, `signals_count`, `new_near_triggers` (list of symbol+strategy that crossed the 50% condition threshold). Sent every interval.

   Message format:
   ```json
   {
     "type": "pipeline_update",
     "timestamp": "2026-03-17T10:30:01.000",
     "data": { ... }
   }
   ```

   Connection lifecycle:
   - On connect: authenticate JWT, send initial full state
   - On interval: compute diff from previous state, send updates
   - On disconnect: clean up (remove from connected clients)
   - On error: log warning, attempt graceful close
   - Reconnection: client-side responsibility (frontend will implement exponential backoff)

2. **Modify `server.py`:**
   Mount the Observatory WebSocket endpoint, gated on `observatory.enabled`. Follow the mount pattern used for `/ws/v1/ai/chat`. The Observatory WS must not share any state or connection pool with the AI chat WS — fully independent.

3. **Tier transition detection logic:**
   ObservatoryService needs a lightweight method to track symbol tier assignments between intervals. Add `get_symbol_tiers() -> dict[str, str]` that returns current tier for each symbol. The WS handler diffs this between intervals to detect transitions. Keep the previous state in memory (per-connection or shared) — no DB writes for transition tracking.

## Constraints
- Do NOT modify `argus/api/websocket/ai_chat.py` — the Observatory WS is a separate endpoint
- Do NOT modify any trading pipeline files
- Do NOT add Event Bus subscribers — the WS reads from ObservatoryService which reads from DB
- The WS push loop must not block the asyncio event loop — use `asyncio.sleep()` for intervals
- Handle the case where ObservatoryService queries take longer than the push interval — skip the push, don't queue backlog

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write (~10):
  - `test_observatory_ws_requires_auth` — connection without JWT rejected
  - `test_observatory_ws_sends_initial_state` — first message is full pipeline state
  - `test_observatory_ws_pipeline_update_format` — message has correct type and data fields
  - `test_observatory_ws_interval_configurable` — mock config with different interval, verify timing
  - `test_observatory_ws_tier_transition_detected` — seed state change, verify transition message
  - `test_observatory_ws_evaluation_summary_counts` — verify summary counts match reality
  - `test_observatory_ws_graceful_disconnect` — client disconnects, no errors logged
  - `test_observatory_ws_independent_from_ai_ws` — both endpoints can be connected simultaneously
  - `test_observatory_ws_disabled_config` — when observatory.enabled=false, WS endpoint not mounted
  - `test_observatory_ws_slow_query_no_backlog` — if service query exceeds interval, skip don't queue
- Minimum new test count: 10
- Test command: `python -m pytest tests/api/test_observatory_ws.py -x -q`

## Definition of Done
- [ ] Observatory WebSocket endpoint created at `/ws/v1/observatory`
- [ ] JWT authentication on connection
- [ ] Pipeline updates pushed at configurable interval
- [ ] Tier transition detection working
- [ ] Evaluation summary pushed each interval
- [ ] Independent from AI chat WebSocket
- [ ] Config-gated: not mounted when observatory.enabled=false
- [ ] All existing tests pass
- [ ] 10+ new tests written and passing
- [ ] Close-out report written to `docs/sprints/sprint-25/session-2-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| AI chat WS still functional | Existing AI WS tests pass |
| No trading pipeline files modified | `git diff --name-only` check |
| server.py changes only add Observatory WS mount | Review diff of server.py |

## Close-Out
Follow close-out skill. Write to: `docs/sprints/sprint-25/session-2-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide @reviewer with:
1. Review context: `docs/sprints/sprint-25/review-context.md`
2. Close-out: `docs/sprints/sprint-25/session-2-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command: `python -m pytest tests/api/test_observatory_ws.py -x -q`
5. Do not modify: `argus/api/websocket/ai_chat.py`, trading pipeline files

Write review to: `docs/sprints/sprint-25/session-2-review.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify Observatory WS is completely independent from AI chat WS (no shared state)
2. Verify push loop uses asyncio.sleep, not blocking sleep
3. Verify tier transition detection compares states without DB writes
4. Verify slow query handling — skip, don't queue
5. Verify JWT auth follows same pattern as ai_chat.py
6. Verify config-gating prevents mount when disabled

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-25/regression-checklist.md`

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-25/escalation-criteria.md`
