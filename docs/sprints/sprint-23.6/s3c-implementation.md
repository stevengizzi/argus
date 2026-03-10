# Sprint 23.6, Session 3c: Polling Loop

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/startup.py` (S3a — where to add polling function)
   - `argus/api/server.py` (S3b — lifespan handler, where to start/stop polling)
   - `argus/intelligence/config.py` (polling interval config)
2. Run the test suite: `python -m pytest tests/intelligence/ tests/api/ -x -q`
   Expected: all passing (including S3a, S3b changes)
3. Verify S3b completed: intelligence init in lifespan, AppState populated
4. Verify you are on the correct branch: `sprint-23.6`

## Objective
Add a scheduled polling loop that calls `pipeline.run_poll()` at configurable intervals, with market-hours-aware interval switching.

## Requirements

1. **In `argus/intelligence/startup.py`**, add a polling function:
   ```python
   async def run_polling_loop(
       pipeline: CatalystPipeline,
       config: CatalystConfig,
       get_symbols: Callable[[], list[str]],
       market_open: str = "09:30",
       market_close: str = "16:00",
   ) -> None:
   ```

   The loop should:
   - Run indefinitely until cancelled.
   - Each iteration: get current symbols via `get_symbols()`, call `pipeline.run_poll(symbols)`, sleep for the appropriate interval.
   - Determine interval: if current ET time is between `market_open` and `market_close`, use `config.polling_interval_session_seconds`. Otherwise use `config.polling_interval_premarket_seconds`.
   - If `get_symbols()` returns empty: log WARNING and sleep (don't crash).
   - If `run_poll()` raises: log ERROR and continue (don't crash the loop).
   - If a poll cycle takes longer than the interval: skip the sleep, log WARNING about slow poll.

2. **In `argus/api/server.py`**, in the lifespan handler, after intelligence initialization:
   - Create a `get_symbols` callback that returns Universe Manager viable_symbols (if universe_manager exists and has symbols) or cached watchlist symbols.
   - Start the polling task: `polling_task = asyncio.create_task(run_polling_loop(pipeline, config, get_symbols, ...))`
   - In the shutdown section, cancel the polling task: `polling_task.cancel()` with `try/except asyncio.CancelledError`.
   - Only start polling if `intelligence_initialized_here` is True.

3. **Overlap protection:** If a poll cycle is still running when the next interval fires, don't start a second concurrent poll. Use a simple flag or `asyncio.Lock`.

## Constraints
- Do NOT modify `argus/intelligence/__init__.py` (pipeline code already done)
- Do NOT modify any strategy, execution, or AI file
- Do NOT create a separate scheduler service — keep it as a simple asyncio task
- Polling symbols come from Universe Manager or watchlist — do NOT query FMP directly for symbols in the polling loop

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests in `tests/intelligence/test_startup.py` (or new `test_polling.py`):
  1. `test_polling_loop_calls_run_poll` — mock pipeline, verify run_poll called with symbols
  2. `test_polling_loop_uses_premarket_interval` — outside market hours, sleeps premarket interval
  3. `test_polling_loop_uses_session_interval` — during market hours, sleeps session interval
  4. `test_polling_loop_handles_empty_symbols` — empty symbols → WARNING, continues
  5. `test_polling_loop_handles_poll_error` — run_poll raises → ERROR logged, loop continues
- Minimum new test count: 5
- Test command: `python -m pytest tests/intelligence/test_startup.py -x -q`

## Definition of Done
- [ ] Polling loop runs at configurable intervals
- [ ] Market-hours interval switching works
- [ ] Polling task started in lifespan, cancelled on shutdown
- [ ] Overlap protection prevents concurrent polls
- [ ] Error handling: empty symbols and poll errors don't crash the loop
- [ ] All existing tests pass
- [ ] 5+ new tests written and passing

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing intelligence tests pass | `python -m pytest tests/intelligence/ -x -q` |
| Existing server tests pass | `python -m pytest tests/api/ -x -q` |
| No changes to protected files | `git diff HEAD -- argus/strategies/ argus/core/ argus/execution/ argus/ai/ argus/ui/` empty |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.
The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
See `sprint-23.6/review-context.md`.

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
See `sprint-23.6/review-context.md`.
