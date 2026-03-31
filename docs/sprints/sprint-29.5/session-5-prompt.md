# Sprint 29.5, Session 5: Log Noise Reduction

## Pre-Flight Checks
1. Read: `argus/execution/ibkr_broker.py` (logging setup, error handling), `argus/core/risk_manager.py` (weekly limit logging), `argus/main.py` (shutdown sequence), `argus/utils/throttled_logger.py`
2. Run scoped baseline: `python -m pytest tests/execution/test_ibkr_broker.py tests/core/test_risk_manager.py -x -q`
3. Verify branch: `sprint-29.5`

## Objective
Reduce log noise from ~48K lines/session to a manageable level by filtering IBKR validation warnings, rate-limiting repetitive risk warnings, and cleaning up asyncio task shutdown.

## Requirements

1. **Filter `ib_async.wrapper` warnings** in `argus/execution/ibkr_broker.py`:
   - In `__init__` or at module level, set: `logging.getLogger('ib_async.wrapper').setLevel(logging.ERROR)`
   - Create a wrapper that specifically re-logs IBKR error codes 404 and 202 at WARNING level through the Argus logger (`argus.execution.ibkr_broker`). These are the actionable codes.
   - Other `ib_async.wrapper` messages (order validation, repricing notices) stay at ERROR level (effectively muted since most are currently WARNING).

2. **Rate-limit weekly loss rejection** in `argus/core/risk_manager.py`:
   - Find the `Signal rejected: weekly loss limit reached` log line
   - Replace with ThrottledLogger: `self._throttled_logger.warning(...)` with 60s interval
   - Import ThrottledLogger from `argus/utils/throttled_logger.py`

3. **Consolidate reconciliation warnings** in `argus/main.py` or wherever reconciliation logging happens:
   - Find the dual-log pattern (mismatch detail + mismatch count)
   - Consolidate to single WARNING per cycle: "Position reconciliation: {N} mismatch(es) — {symbols}" (already partially done — verify only one line per cycle emitted, remove duplicate)

4. **Clean asyncio shutdown** in `argus/main.py`:
   - In the shutdown sequence, collect all known background tasks (polling loop, VIX update, regime reclassification, evaluation health check, reconciliation task, action manager cleanup, candle store)
   - Cancel them explicitly: `for task in tasks: task.cancel()`
   - `await asyncio.gather(*tasks, return_exceptions=True)`
   - Close aiohttp client sessions explicitly before event loop teardown
   - This eliminates the "Task was destroyed but it is pending!" errors at shutdown

## Constraints
- Do NOT filter out error 404 or 202 — these must remain visible at WARNING
- Do NOT change log levels for non-ib_async loggers
- Do NOT modify the reconciliation logic itself — only its logging
- Preserve all existing log messages at DEBUG level (for troubleshooting)

## Test Targets
- New tests:
  1. `test_ib_async_wrapper_log_level_set` — verify ib_async.wrapper logger level is ERROR
  2. `test_ibkr_error_404_logged_at_warning` — verify specific codes re-logged via Argus logger
  3. `test_weekly_limit_warning_throttled` — simulate 10 rejections in 5s, verify only 1 WARNING emitted
  4. `test_shutdown_tasks_cancelled_cleanly` — verify no pending tasks after shutdown
- Minimum: 4 new tests
- Test command: `python -m pytest tests/execution/test_ibkr_broker.py tests/core/test_risk_manager.py -x -q`

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| IBKR connection still works | Existing IBKR connection tests pass |
| Error codes still logged | test_ibkr_error_404_logged_at_warning |
| Risk manager still rejects over-limit | Existing risk manager tests pass |
| Shutdown still completes | Existing shutdown tests pass |

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass
- [ ] 4+ new tests
- [ ] Close-out report written to `docs/sprints/sprint-29.5/session-5-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
Write to: `docs/sprints/sprint-29.5/session-5-closeout.md`

## Tier 2 Review
Test command: `python -m pytest tests/execution/ tests/core/test_risk_manager.py -x -q`
Files NOT modified: `argus/intelligence/`, `argus/strategies/`, `argus/analytics/`

## Session-Specific Review Focus
1. Verify error 404 is still visible in logs (not accidentally muted)
2. Verify ThrottledLogger import and usage pattern matches existing usage in codebase
3. Verify shutdown task cancellation doesn't interfere with debrief export (export must complete before tasks cancelled)
