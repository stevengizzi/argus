# Tier 2 Review: Sprint 23.8, Session 1

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-23.8-review-context.md`

## Tier 1 Close-Out Report
---BEGIN-CLOSE-OUT---

**Session:** Sprint 23.8 — Session 1: Pipeline Resilience + Symbol Scope
**Date:** 2026-03-12
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/intelligence/startup.py | modified | Added asyncio.wait_for timeout, symbol log line, cleaned QA debug log |
| argus/api/server.py | modified | Cleaned get_symbols() to match spec, removed inline logging |
| config/system.yaml | modified | Updated stale comment for catalyst.enabled |
| tests/intelligence/test_config.py | modified | Fixed assertion to match catalyst.enabled=true |
| tests/intelligence/test_startup.py | modified | Added timeout test |
| tests/api/test_server_intelligence.py | modified | Added get_symbols and done_callback tests |
| dev-logs/2026-03-12_sprint23.8-session1.md | added | Dev log entry |

### Judgment Calls
- Moved symbol-count logging from `get_symbols()` in server.py to the polling loop in startup.py: the spec placed it "before each poll invocation" which is the polling loop, not the callback. The `get_symbols` closure is now a pure data function.
- For the timeout test, mocked `asyncio.wait_for` to pass through while making `run_poll` raise `TimeoutError` directly, rather than waiting 120s in a real timeout. Functionally equivalent but fast.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| asyncio.wait_for(120) wraps source gather | DONE | startup.py:241-244 |
| done_callback on polling task logs CRITICAL | DONE | server.py:172-182 (pre-existing, verified) |
| Task reference stored on app_state | DONE | server.py:192 (pre-existing, verified) |
| get_symbols returns scanner watchlist | DONE | server.py:156-169 |
| Fallback to capped viable universe | DONE | server.py:163-168 |
| Log line shows symbol count per cycle | DONE | startup.py:236-240 |
| Config alignment test fixed | DONE | test_config.py:103,107 |
| QA debug patches replaced | DONE | startup.py:194 (INFO→DEBUG), server.py get_symbols cleaned |
| All existing tests pass | DONE | 2,516 passed |
| 5+ new tests written | DONE | 5 new tests |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Pipeline starts when enabled | PASS | Verified via test_lifespan_catalyst_enabled |
| Pipeline skipped when disabled | PASS | Verified via test_lifespan_catalyst_disabled |
| Polling loop enters and attempts first poll | PASS | Log line "Polling N symbols" added |
| Existing API endpoints unaffected | PASS | All 506 api+intelligence tests pass |
| No import errors | PASS | `python -c "from argus.api.server import create_app"` succeeds |

### Test Results
- Tests run: 2,516
- Tests passed: 2,516
- Tests failed: 0
- New tests added: 5
- Command used: `python -m pytest tests/ -x -q`

### Unfinished Work
None

### Notes for Reviewer
- The `_poll_task_done` callback and `app_state.intelligence_polling_task` were already implemented in server.py from the QA session — they were clean implementations, not debug patches. Verified they match the spec and left in place.
- The `asyncio.wait_for` timeout in startup.py is in addition to the existing timeout in `pipeline.py:run_poll()`. The startup.py timeout protects against the entire `run_poll` hanging (including classification, storage, publishing), while the pipeline.py timeout only covers source fetches.

---END-CLOSE-OUT---

## Review Scope
- Diff to review: `git diff HEAD~1` (or the appropriate range for Session 1 commits)
- Test command: `python -m pytest tests/ -x -q`
- Files that should NOT have been modified: `core/`, `strategies/`, `execution/`, `ui/`, `ai/` (except `server.py`), `backtest/`, `classifier.py`, source files (`sec_edgar.py`, `finnhub.py`, `fmp_news.py`), `databento_data_service.py`

## Session-Specific Review Focus
1. Verify `asyncio.wait_for()` wraps the gather with a 120s timeout — not the entire poll loop iteration, just the gather call
2. Verify `asyncio.TimeoutError` is caught correctly and does NOT crash the loop — it must log CRITICAL and continue to the next sleep/poll cycle
3. Verify `get_symbols()` prioritizes scanner watchlist over viable universe — check the fallback order is: watchlist → capped viable → empty list
4. Verify the `max_batch_size` cap is applied when falling back to viable universe — hard-coding a cap instead of reading config is a CONCERN
5. Verify `done_callback` logs at CRITICAL level (not WARNING or ERROR) when the task raises an exception
6. Verify task reference is stored on `app_state` (not a local variable) to prevent garbage collection
7. Verify the QA session debug patches were replaced, not layered — search for any remaining temporary diagnostic code
8. Verify the config alignment test fix is correct — the test should validate `system_live.yaml` including the catalyst section, not skip it
9. Verify no changes were made to polling interval logic or market-hours awareness

## Additional Context
This session replaces temporary debug patches added during a live QA session on March 12, 2026. The debug patches (a `done_callback` and a "Polling loop coroutine entered" log) confirmed the task was alive but hanging. Those patches were intentionally quick-and-dirty — this session should replace them with production-quality implementations.

The `get_symbols()` change is architecturally significant: it determines what the intelligence pipeline monitors. The QA session proved that passing the full viable universe (6,342 symbols) causes the poll to timeout. The fix scopes to the scanner watchlist (15 symbols). A future Sprint 24 design decision (DEC-327) will revisit this with a firehose architecture. For now, the watchlist is the correct scope.
