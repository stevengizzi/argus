# Sprint 23.8, Session 1: Pipeline Resilience + Symbol Scope

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md`
   - `docs/sprints/sprint-23.8-spec.md`
   - `argus/intelligence/startup.py`
   - `argus/intelligence/pipeline.py`
   - `argus/api/server.py`
2. Run the test suite: `python -m pytest tests/ -x -q`
   Expected: 2,511 tests passing (there may be a pre-existing failure in a config alignment test due to `system_live.yaml` modifications from the QA session — if so, note it and continue; fixing that fixture is part of this session)
3. Verify you are on the correct branch: `sprint-23.8-pipeline-fixes`
   If branch doesn't exist: `git checkout -b sprint-23.8-pipeline-fixes main`
4. Check for live debug patches from the QA session (search for `_poll_task_done` and `"Polling loop coroutine entered"` in `server.py` and `startup.py`). These were added as temporary diagnostics — replace them with the clean implementations below, do not layer on top.

## Objective
Make the intelligence polling loop resilient to crashes and hangs, fix the symbol scope from full universe to scanner watchlist, and ensure the task is properly monitored.

## Requirements

1. **In `argus/intelligence/startup.py`:**
   - In the polling loop function, wrap the `asyncio.gather(*fetch_tasks, return_exceptions=True)` call with `asyncio.wait_for(..., timeout=120)`. Catch `asyncio.TimeoutError`, log at CRITICAL level: `f"Poll cycle timed out after 120s waiting for source fetches ({len(sources)} sources, {len(symbols)} symbols)"`, and continue to the next sleep/poll iteration.
   - Ensure the "Polling loop coroutine entered" debug log (if present from QA session) is cleaned up — either keep it at DEBUG level or remove it. The "Polling loop started" INFO log is the canonical entry point log.
   - If there's an existing `try/except` around the poll cycle body, ensure `asyncio.TimeoutError` is caught explicitly (it does NOT inherit from `Exception` in Python 3.11 — it inherits from `BaseException`). Note: Actually in Python 3.11+, `TimeoutError` (which `asyncio.TimeoutError` is aliased to) does inherit from `Exception` via `OSError`. But `asyncio.wait_for` raises `asyncio.TimeoutError` specifically. Verify the exception hierarchy in the codebase and handle correctly.

2. **In `argus/api/server.py`:**
   - Replace the existing `get_symbols()` closure to prioritize scanner watchlist:
     ```python
     def get_symbols() -> list[str]:
         # Priority 1: Scanner watchlist (15 symbols from FMP pre-market scan)
         if app_state.cached_watchlist:
             symbols = [item.symbol for item in app_state.cached_watchlist]
             if symbols:
                 return symbols
         # Priority 2: Viable universe capped at max_batch_size
         if app_state.universe_manager is not None and app_state.universe_manager.viable_count > 0:
             max_batch = config.catalyst.max_batch_size if config.catalyst else 20
             all_viable = list(app_state.universe_manager.viable_symbols)
             return all_viable[:max_batch]
         return []
     ```
   - Add a log line before each poll invocation: `logger.info(f"Polling {len(symbols)} symbols: {symbols[:5]}...")`
   - Store the polling task reference on `app_state`: `app_state.intelligence_poll_task = poll_task`
   - Add a `done_callback` to the task that logs CRITICAL if the task crashed:
     ```python
     def _poll_task_done(task: asyncio.Task) -> None:
         if task.cancelled():
             logger.info("Intelligence polling task was cancelled")
         elif task.exception():
             logger.critical(
                 f"Intelligence polling task CRASHED: {task.exception()}",
                 exc_info=task.exception()
             )
     poll_task.add_done_callback(_poll_task_done)
     ```
   - Clean up any temporary debug patches from the QA session.

3. **Fix the pre-existing config alignment test:**
   - Find the test that validates `system_live.yaml` against the Pydantic config models (likely in `tests/test_config*.py` or similar).
   - The test fails because `system_live.yaml` now has a `catalyst` section that was added during the QA session. Either:
     (a) Update the test fixture/expected values to include the catalyst section, OR
     (b) If the test loads `system_live.yaml` directly, ensure the catalyst section is valid against `CatalystConfig`.
   - The test must pass after this fix.

## Constraints
- Do NOT modify: `core/`, `strategies/`, `execution/`, `ui/`, `ai/` (except what's needed in `server.py`), `backtest/`
- Do NOT change: Polling interval logic, market-hours awareness, pipeline initialization sequence, Event Bus publishing, config schema (Pydantic models)
- Do NOT add: New config fields, new API endpoints, new files (except test files)
- Do NOT modify: `classifier.py`, source files (`sec_edgar.py`, `finnhub.py`, `fmp_news.py`), `databento_data_service.py` — those are Sessions 2 and 3

## Test Targets
After implementation:
- Existing tests: all must still pass (including the fixed config alignment test)
- New tests to write:
  1. Test that `get_symbols()` returns watchlist when `cached_watchlist` is populated
  2. Test that `get_symbols()` returns capped viable universe when watchlist is empty
  3. Test that `get_symbols()` returns `[]` when both sources are empty
  4. Test that `asyncio.wait_for` timeout is applied to the gather (mock a hanging source, verify TimeoutError is caught and logged, loop continues)
  5. Test that `done_callback` logs CRITICAL when task raises an exception
- Minimum new test count: 5
- Test command: `python -m pytest tests/intelligence/ tests/api/ -x -q`

## Definition of Done
- [ ] `asyncio.wait_for(120)` wraps source gather in polling loop
- [ ] `done_callback` on polling task logs CRITICAL on crash
- [ ] Task reference stored on `app_state.intelligence_poll_task`
- [ ] `get_symbols()` returns scanner watchlist (not full universe)
- [ ] Fallback to capped viable universe when watchlist empty
- [ ] Log line shows symbol count and first 5 symbols per cycle
- [ ] Pre-existing config alignment test fixed and passing
- [ ] QA debug patches replaced with clean implementations
- [ ] All existing tests pass
- [ ] 5+ new tests written and passing

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Pipeline starts when enabled | Boot with `catalyst.enabled: true`, see "Intelligence pipeline created" in log |
| Pipeline skipped when disabled | Boot with `catalyst.enabled: false`, see "Intelligence pipeline disabled" in log |
| Polling loop enters and attempts first poll | See "Polling N symbols" log line within seconds of boot |
| Existing API endpoints unaffected | `grep "200 OK" logs/` shows health, account, positions responses |
| No import errors | `python -c "from argus.api.server import create_app"` succeeds |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
See `docs/sprints/sprint-23.8-review-context.md`

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
See `docs/sprints/sprint-23.8-review-context.md`
