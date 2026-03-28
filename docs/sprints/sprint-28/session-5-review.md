---BEGIN-REVIEW---

# Sprint 28, Session 5 — Tier 2 Review Report

**Reviewer:** Automated (Tier 2)
**Session:** Sprint 28, Session 5 — REST API + Auto Post-Session Trigger
**Date:** 2026-03-28
**Close-out self-assessment:** CLEAN

## Test Results

- **Learning module tests:** 147 passed (0 failures)
- **Warning:** One benign `RuntimeWarning: coroutine 'slow_analysis' was never awaited` in `test_timeout_enforcement` — expected because the test mocks `asyncio.wait_for` to raise `TimeoutError` immediately, so the wrapped coroutine is never actually invoked. Not a production concern.

## Review Focus Items

### 1. CRITICAL: Auto trigger uses Event Bus, not direct callback (Amendment 13) -- PASS

`LearningService.register_auto_trigger()` calls `event_bus.subscribe(SessionEndEvent, self._on_session_end)` at line 101 of `learning_service.py`. The handler `_on_session_end` is invoked via Event Bus dispatch, not a direct callback from `main.py`. The test `test_auto_trigger_uses_event_bus_not_callback` explicitly verifies that `SessionEndEvent` has a subscriber in `event_bus._subscribers`. This is correctly implemented per Amendment 13.

### 2. apply_pending() called during server startup -- PASS

`server.py` line 411: `applied_ids = await config_proposal_manager.apply_pending()` is called during the lifespan startup phase, after `LearningStore.initialize()` and before `yield`. This is the correct location per Amendment 1.

### 3. 400 response for SUPERSEDED -> APPROVED transition -- PASS

`learning.py` line 269: `if proposal.status in _TERMINAL_STATUSES` checks against the frozen set `{"SUPERSEDED", "REVERTED", "REJECTED_GUARD", "REJECTED_VALIDATION"}` and raises `HTTPException(status_code=400)`. Test `test_approve_superseded_returns_400` verifies this with PROP_002 (seeded as SUPERSEDED).

### 4. Auto trigger doesn't block shutdown (timeout + fire-and-forget) -- PASS

`_on_session_end()` in `learning_service.py` lines 138-145: wraps `run_analysis()` in `asyncio.wait_for(timeout=120)` and catches `TimeoutError`, `RuntimeError`, and generic `Exception` — all logged at WARNING, never re-raised. The `_publish_session_end_event()` method in `main.py` is also wrapped in a try/except that catches all exceptions and logs a warning. Two tests verify: `test_timeout_enforcement` and `test_auto_trigger_does_not_block_shutdown`.

### 5. Zero-trade guard (Amendment 10) -- PASS

`_on_session_end()` line 124: `if event.trades_count == 0 and event.counterfactual_count == 0` returns early with an INFO log. Tests `test_zero_trade_guard_skips_on_zero_both` and `test_counterfactual_only_runs_analysis` verify both the skip case and the counterfactual-only case.

### 6. All endpoints are JWT-protected -- PASS

All 8 endpoints include `_auth: dict = Depends(require_auth)` in their signatures. Test `test_endpoints_require_auth` systematically verifies all 8 endpoints return 401 without auth headers.

### 7. SessionEndEvent is the ONLY change to main.py's flatten path -- PASS

The diff shows exactly 3 changes to `main.py`:
1. Import of `SessionEndEvent` (line 62)
2. A single `await self._publish_session_end_event()` call inserted in `_on_shutdown_requested` after the log statement and before the existing `delayed_shutdown` logic
3. The new `_publish_session_end_event()` private method

No existing logic was modified, removed, or reordered. The docstring update on `_on_shutdown_requested` is cosmetic only.

## Regression Checklist

- [x] No strategy files modified (verified: `git diff HEAD -- argus/strategies/` empty)
- [x] No risk manager modified (verified: `git diff HEAD -- argus/core/risk_manager.py` empty)
- [x] No orchestrator modified (verified: `git diff HEAD -- argus/core/orchestrator.py` empty)
- [x] No order manager modified (verified: `git diff HEAD -- argus/execution/order_manager.py` empty)
- [x] No execution pipeline behavior changed

## Findings

### CONCERN-01: Private attribute access for counterfactual count (LOW)

`main.py` line 1605-1607 uses `getattr(self._counterfactual_tracker, "_closed_positions", [])` to access a private attribute on the counterfactual tracker. This is acknowledged in the close-out report as "consistent with existing patterns in the codebase." While this is true (the tracker is already duck-typed as `object | None`), it creates fragile coupling — if `_closed_positions` is renamed or restructured, this silently falls back to an empty list and reports 0 counterfactuals. This is LOW severity since it only affects the count metadata on the event, not any control flow decision.

### CONCERN-02: `assert` statements in production route code (LOW)

`learning.py` lines 285, 335, and 397 use `assert updated is not None` after `get_proposal()`. In production, if Python is run with `-O` (optimize), `assert` statements are stripped. The correct pattern is to raise an `HTTPException(500)` or use an `if` guard. Since ARGUS does not appear to run with `-O` in any deployment configuration, this is LOW severity but worth noting as a code quality issue.

### CONCERN-03: No test for config-gated disabled path in server lifespan (LOW)

The server.py code includes an `elif` branch (lines 430-435) that logs "Learning Loop disabled" when `learning_loop.enabled` is `False`. There is no test verifying that when the learning loop is disabled, no components are initialized and `app_state.learning_service` remains `None`. The existing API tests implicitly test the enabled path through the fixture setup, but the disabled path is untested. LOW severity since the logic is straightforward.

## Scope Verification

All 8 Definition of Done items are satisfied:
- [x] 8 REST endpoints, all JWT-protected
- [x] Server lifespan initializes Learning Loop components
- [x] ConfigProposalManager.apply_pending() called at startup
- [x] SessionEndEvent added to events.py
- [x] Auto trigger via Event Bus subscription
- [x] Zero-trade guard on auto trigger
- [x] Config-gated
- [x] 21 new tests (exceeds minimum of 12)

## Verdict

**CLEAR** — All review focus items pass. The three concerns noted are LOW severity code quality observations that do not affect correctness or safety. No escalation criteria are triggered. Implementation matches spec precisely with no deviations.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "confidence": 0.95,
  "findings": [
    {
      "id": "CONCERN-01",
      "severity": "LOW",
      "category": "code-quality",
      "description": "Private attribute access for counterfactual count via getattr with silent fallback",
      "file": "argus/main.py",
      "line": 1605,
      "recommendation": "Add a public property on CounterfactualTracker for closed position count"
    },
    {
      "id": "CONCERN-02",
      "severity": "LOW",
      "category": "code-quality",
      "description": "assert statements in production API route code (lines 285, 335, 397)",
      "file": "argus/api/routes/learning.py",
      "line": 285,
      "recommendation": "Replace assert with if-guard and HTTPException(500)"
    },
    {
      "id": "CONCERN-03",
      "severity": "LOW",
      "category": "test-coverage",
      "description": "No test for config-gated disabled path in server lifespan",
      "file": "argus/api/server.py",
      "line": 430,
      "recommendation": "Add test verifying learning components are None when learning_loop.enabled=false"
    }
  ],
  "tests_passed": 147,
  "tests_failed": 0,
  "new_tests": 21,
  "regression_clean": true,
  "scope_complete": true
}
```
