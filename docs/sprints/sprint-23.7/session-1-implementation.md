# Sprint 23.7, Session 1: Time-Aware Indicator Warm-Up

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/data/databento_data_service.py` (the warm-up logic)
   - `argus/data/indicator_engine.py` (understand the indicator interface)
   - `docs/project-knowledge.md` (architecture context)
   - `CLAUDE.md`
2. Run the test suite: `python -m pytest tests/ -x -q`
   Expected: ~2490 tests, all passing
3. Verify you are on the correct branch: `sprint-23.7` (create from `sprint-23.6`)

## Objective
Replace the blocking per-symbol indicator warm-up with a time-aware approach
that skips warm-up at pre-market boot and performs lazy per-symbol backfill
at mid-session boot, enabling ARGUS to start in seconds with a 6,000+ symbol
universe.

## Requirements

1. **In `argus/data/databento_data_service.py` — add time-aware warm-up
   decision:**
   - At the point where `Warming up indicators for N symbols` currently
     happens, check the current time in ET (America/New_York).
   - If current time is BEFORE 9:30 AM ET (market open): log
     `"Pre-market boot — skipping indicator warm-up (indicators will build
     from live stream)"` and skip the entire warm-up loop. Proceed directly
     to Databento live connection.
   - If current time is AT OR AFTER 9:30 AM ET: do NOT run the blocking
     warm-up loop. Instead, set a flag/state (e.g., `self._needs_warmup = True`
     and store a set of symbols that have NOT yet been warmed up —
     initially the full viable universe set).

2. **In `argus/data/databento_data_service.py` — implement lazy per-symbol
   backfill:**
   - In the candle processing path (where incoming live candles are received
     from the Databento stream and dispatched), add a check: if the symbol
     has not yet been warmed up AND we are in mid-session mode
     (`self._needs_warmup` is True):
     a. Before processing the candle, fetch historical 1-minute OHLCV data
        for this specific symbol from today's market open (9:30 ET) to the
        current time, using the existing Databento historical client.
     b. Feed the historical candles through the IndicatorEngine for this
        symbol (using the same code path the current warm-up uses).
     c. Mark the symbol as warmed up (remove from the pending set).
     d. Then process the incoming live candle normally.
   - If the historical fetch fails (network error, no data returned,
     symbology error): log a warning, mark the symbol as warmed up anyway
     (to prevent retrying on every candle), and process the live candle
     normally. The symbol's indicators will be incomplete, but strategies
     will not fire signals without valid indicator state (fail-closed via
     existing indicator validity checks).
   - This lazy backfill should be synchronous within the candle processing
     path — do not dispatch the candle to strategies until warm-up is
     complete for that symbol. This preserves the FIFO ordering guarantee
     (DEC-025).

3. **In `argus/data/databento_data_service.py` — add logging:**
   - Log the warm-up decision at startup: pre-market skip vs mid-session
     lazy mode.
   - Log each lazy backfill as it happens: `"Lazy warm-up for {symbol}:
     fetched {N} historical candles ({time}s)"` at INFO level.
   - Log lazy backfill failures at WARNING level.
   - Do NOT log at per-candle frequency for already-warmed symbols (this
     would flood the log with 6,000+ symbols × many candles).

4. **Handle the Databento reader thread context:**
   - The current warm-up runs on the main thread before the live stream
     starts. The lazy backfill will run in the Databento callback context
     (reader thread, bridged via `call_soon_threadsafe()` per DEC-088).
   - The historical API call (`self._hist_client.timeseries.get_range()`)
     is a blocking synchronous call. It must NOT block the asyncio event
     loop. If the candle processing path is async, run the historical
     fetch in a thread executor (`await asyncio.to_thread(...)` or
     `loop.run_in_executor()`).
   - Ensure the warm-up set tracking (`self._needs_warmup`,
     `self._warmed_symbols` or similar) is thread-safe if accessed from
     both the reader thread callback and the main async context.

## Constraints
- Do NOT modify: `argus/data/indicator_engine.py` (use its existing interface)
- Do NOT modify: any strategy files, orchestrator, risk manager, order manager
- Do NOT modify: Universe Manager filtering or routing logic
- Do NOT change: the IndicatorEngine API or how strategies consume indicators
- Do NOT change: the Databento live subscription behavior (ALL_SYMBOLS mode)
- Do NOT add: new config fields or dependencies
- PRESERVE: Event Bus FIFO ordering guarantee (DEC-025)
- PRESERVE: existing warm-up behavior for the SimulatedBroker/backtest path
  (if the warm-up code is shared with backtesting, ensure backtest still works)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. Test pre-market boot path: mock time to 9:00 AM ET, verify warm-up is
     skipped (no historical API calls made)
  2. Test mid-session boot path: mock time to 10:30 AM ET, verify warm-up
     flag is set and no blocking warm-up occurs
  3. Test lazy backfill trigger: mock a candle arriving for an un-warmed
     symbol in mid-session mode, verify historical fetch is called once
  4. Test lazy backfill caching: after backfill, verify second candle for
     same symbol does NOT trigger another historical fetch
  5. Test lazy backfill failure: mock historical fetch failure, verify symbol
     is marked warmed (no retry loop), candle is still processed
  6. Test pre-market boot processes candles without backfill: mock time to
     9:00 AM ET, send a candle, verify no historical fetch occurs
  7. Test boundary: mock time to exactly 9:30:00 AM ET, verify treated as
     pre-market (no warm-up)
- Minimum new test count: 7
- Test command: `python -m pytest tests/ -x -q`

## Definition of Done
- [ ] Pre-market boot completes warm-up phase in <5 seconds for 6,000+ symbols
- [ ] Mid-session boot completes warm-up phase in <5 seconds
- [ ] Lazy backfill fires on first candle per un-warmed symbol in mid-session
- [ ] Failed backfills are logged and do not block candle processing
- [ ] All existing tests pass
- [ ] 7+ new tests written and passing
- [ ] Event Bus FIFO ordering preserved

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Pre-market warm-up is a no-op | New test: mock 9:00 AM ET, assert no historical API calls |
| Existing small-universe warm-up still works | Existing DatabentoDataService tests pass |
| Candle processing path unchanged for warmed symbols | Existing integration tests pass |
| Backtest path unaffected | Run backtest-related tests if they exist |
| No asyncio event loop blocking | Review: historical fetch uses thread executor if in async context |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)

| Check | How to Verify |
|-------|---------------|
| All existing pytest tests pass | `python -m pytest tests/ -x -q` |
| DatabentoDataService can still warm up a small symbol set | Existing warm-up tests pass |
| FMPReferenceClient fetch + cache round-trip works | Existing reference client tests pass |
| API server starts on port 8000 without error | Startup sequence test or manual boot |
| Universe Manager routing table builds correctly | Existing Universe Manager tests pass |
| Strategies still receive candles via Event Bus | Existing strategy integration tests pass |

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)

Escalate to Tier 3 if:
- The warm-up changes alter the IndicatorEngine interface
- The lazy backfill introduces async concurrency patterns that could conflict
  with Event Bus FIFO (DEC-025)
- The API server fix requires changes to the FastAPI app factory or middleware
- Any fix touches more than the files listed in the session scope