# Sprint 28, Session 5 — Close-Out Report

## Change Manifest

| File | Action | Description |
|------|--------|-------------|
| `argus/core/events.py` | Modified | Added `SessionEndEvent` (Amendment 13) |
| `argus/core/config.py` | Modified | Added `LearningLoopConfig` to `SystemConfig` |
| `argus/api/dependencies.py` | Modified | Added `learning_service`, `learning_store`, `config_proposal_manager` to `AppState` |
| `argus/api/routes/learning.py` | **Created** | 8 REST endpoints (trigger, reports list/detail, proposals list/approve/dismiss/revert, config-history) |
| `argus/api/routes/__init__.py` | Modified | Registered learning router under `/learning` prefix |
| `argus/api/server.py` | Modified | Learning Loop initialization in lifespan + `apply_pending()` at startup + cleanup |
| `argus/intelligence/learning/learning_service.py` | Modified | Added `register_auto_trigger()` + `_on_session_end()` handler |
| `argus/intelligence/learning/learning_store.py` | Modified | Added `get_proposal()` method for single-proposal lookup |
| `argus/main.py` | Modified | Import `SessionEndEvent`, publish from `_on_shutdown_requested` via `_publish_session_end_event()` |
| `tests/api/test_learning_api.py` | **Created** | 14 API endpoint tests |
| `tests/intelligence/learning/test_auto_trigger.py` | **Created** | 7 auto-trigger tests |

## Judgment Calls

1. **SessionEndEvent publish point:** Published from `_on_shutdown_requested` in main.py, which fires after the Order Manager's `eod_flatten()` completes and publishes `ShutdownRequestedEvent`. This is the earliest reliable point after EOD flatten.

2. **Counterfactual count source:** Used `getattr(tracker, '_closed_positions', [])` since `_counterfactual_tracker` is duck-typed as `object | None` in main.py. Accessing the private attribute is consistent with existing patterns in the codebase.

3. **Auto-trigger handler typing:** Used `event: object` parameter type in `_on_session_end()` to avoid circular imports, with runtime `isinstance` check. This matches the existing duck-typing patterns in main.py.

4. **Added `get_proposal()` to LearningStore:** The existing API only had `list_proposals()`. Individual proposal lookup was needed for approve/dismiss/revert endpoints.

## Scope Verification

- [x] 8 REST endpoints, all JWT-protected
- [x] Server lifespan initializes Learning Loop components
- [x] `ConfigProposalManager.apply_pending()` called at startup
- [x] `SessionEndEvent` added to events.py (Amendment 13)
- [x] Auto trigger via Event Bus subscription, not direct callback
- [x] Zero-trade guard on auto trigger (Amendment 10)
- [x] Config-gated (disabled = skip all initialization)
- [x] ≥12 new tests (21 actual: 14 API + 7 auto-trigger)

## Test Results

- **Learning module tests:** 147 passed (126 existing + 21 new)
- **Full suite:** 3,827 passed, 9 failed (all pre-existing xdist failures)
- **New test count:** 21

## Regression Check

- No new test failures introduced
- All 9 xdist failures are pre-existing (pass in isolation):
  - `test_server_intelligence` (xdist race)
  - `test_client` (3 AI client disabled tests, xdist race)
  - `test_config` (AI config defaults, xdist race)
  - `test_counterfactual_wiring` (xdist race)
  - `test_notifications` (sprint runner, xdist race)
  - `test_engine` (2 backtest engine tests, xdist race)

## Self-Assessment

**CLEAN** — All scope items completed, no deviations from spec.

## Context State

**GREEN** — Session completed well within context limits.
