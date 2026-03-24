# Sprint 27.6.1 (Impromptu): Observatory Regime Vector Summary Wiring

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/orchestrator.py` (S6 added `_latest_regime_vector` as `object | None`)
   - `argus/api/routes/observatory.py` (SessionSummaryResponse model + get_session_summary endpoint)
   - `argus/api/websocket/observatory_ws.py` (push loop, evaluation_summary message)
   - `argus/api/dependencies.py` (AppState — has `orchestrator` field)
   - `argus/ui/src/api/types.ts` (S10 added `RegimeVectorSummary` interface + `regime_vector_summary?` field on `ObservatorySessionSummaryResponse`)
   - `argus/ui/src/features/observatory/hooks/useSessionVitals.ts` (S10 wired `regimeVector` from session summary)
2. Run scoped test baseline:
   ```
   python -m pytest tests/api/ tests/core/test_regime_integration.py -x -q
   ```
   Expected: all passing
3. Verify you are on the correct branch: `main`

## Objective
Wire the Orchestrator's `_latest_regime_vector` through to the Observatory REST endpoint and WebSocket push, completing the data path so the S10 frontend visualization renders actual regime data during live sessions.

## Context
Sprint 27.6 S10 built the `RegimeVitals` frontend component and typed `regime_vector_summary` as an optional field on the session summary response. But the backend never populates it — the Observatory service and API routes don't read the Orchestrator's latest regime vector. This means the regime visualization renders nothing (returns null). This wiring closes the gap.

## Requirements

1. **Add public property on Orchestrator** (`argus/core/orchestrator.py`):
   - Add a `@property` method `latest_regime_vector_summary` → `dict | None`
   - If `self._latest_regime_vector` is not None and has a `to_dict()` method (duck-type check, matching the existing `object | None` pattern from S6), call `to_dict()` and return the result
   - If None, return None
   - This avoids importing `RegimeVector` (maintaining the S6 circular-import avoidance pattern)

2. **Add `regime_vector_summary` to `SessionSummaryResponse`** (`argus/api/routes/observatory.py`):
   - Add field: `regime_vector_summary: dict | None = None`
   - In `get_session_summary()` endpoint, after building the response, read from `state.orchestrator.latest_regime_vector_summary` (guard with `state.orchestrator is not None` and `hasattr(state.orchestrator, 'latest_regime_vector_summary')`)
   - Pass the value through to the `SessionSummaryResponse` constructor

3. **Include in Observatory WebSocket push** (`argus/api/websocket/observatory_ws.py`):
   - In the push loop, after building the `evaluation_summary` message data dict, add `regime_vector_summary` key
   - Read from `app_state.orchestrator.latest_regime_vector_summary` if `app_state.orchestrator is not None`
   - If None, omit or set to null — the frontend handles both cases

4. **Tests** (~5 new):
   - Test `Orchestrator.latest_regime_vector_summary` returns None when no V2 is wired
   - Test `Orchestrator.latest_regime_vector_summary` returns a dict after V2 computes a vector
   - Test `SessionSummaryResponse` includes `regime_vector_summary` field (schema test)
   - Test `get_session_summary` endpoint includes `regime_vector_summary` when orchestrator has a vector
   - Test `get_session_summary` endpoint returns `regime_vector_summary: null` when orchestrator has no vector

## Constraints
- Do NOT modify: `argus/core/regime.py`, `argus/core/events.py`, `argus/main.py`, `argus/analytics/observatory_service.py`, `argus/strategies/*.py`, `argus/analytics/evaluation.py`
- Do NOT modify any frontend files — S10 already handles the data correctly
- Do NOT import `RegimeVector` in `orchestrator.py` — maintain the existing `object | None` + duck-typing pattern from S6
- The `regime_vector_summary` field MUST be optional (None default) — when regime_intelligence is disabled or Orchestrator hasn't run yet, it must be absent/null, not cause errors

## Test Targets
- Existing tests: all must still pass
- New tests: ~5
- Test command: `python -m pytest tests/api/ tests/core/test_regime_integration.py -x -q -v`

## Definition of Done
- [ ] `Orchestrator.latest_regime_vector_summary` property exists and returns `dict | None`
- [ ] Observatory REST `/session-summary` includes `regime_vector_summary` in response
- [ ] Observatory WebSocket push includes `regime_vector_summary` in evaluation_summary
- [ ] All optional — None/null when regime intelligence disabled or no data yet
- [ ] All existing tests pass
- [ ] 5+ new tests passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Observatory REST endpoint still returns all existing fields | Existing API tests pass |
| Observatory WS still sends pipeline_update, tier_transition, evaluation_summary | Existing WS tests pass (if any) or manual verification |
| Orchestrator without V2 unaffected | Test with orchestrator V2=None returns None for property |
| SessionSummaryResponse backward compat | Field defaults to None, existing consumers unaffected |
| No RegimeVector import in orchestrator.py | `grep "from argus.core.regime import.*RegimeVector" argus/core/orchestrator.py` returns 0 |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.
Write the close-out report to: `docs/sprints/sprint-27.6/session-27.6.1-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After close-out, invoke @reviewer with:
1. Review context file: `docs/sprints/sprint-27.6/review-context.md`
2. Close-out report: `docs/sprints/sprint-27.6/session-27.6.1-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/api/ tests/core/test_regime_integration.py -x -q -v`
5. Files NOT to modify: regime.py, events.py, main.py, observatory_service.py, strategies/*.py, evaluation.py, frontend files

## Session-Specific Review Focus (for @reviewer)
1. Verify `latest_regime_vector_summary` does NOT import RegimeVector — uses duck-typing only
2. Verify REST endpoint returns `regime_vector_summary: null` (not absent) when no vector available
3. Verify WS push includes regime data without breaking existing message structure
4. Verify all new code paths are guarded with None checks (no AttributeError if orchestrator is None)
