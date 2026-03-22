# Sprint 27, Session 1: SynchronousEventBus + BacktestEngineConfig

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/event_bus.py` (production EventBus — reference for interface design)
   - `argus/backtest/config.py` (existing BacktestConfig and StrategyType — extend this file)
   - `docs/sprints/sprint-27/design-summary.md` (sprint context)
2. Run the test baseline (DEC-328 — Session 1, full suite):
   ```bash
   python -m pytest --ignore=tests/test_main.py -n auto -q
   ```
   Expected: ≥2,925 tests, all passing
3. Verify you are on the correct branch: `main`

## Objective
Build the SynchronousEventBus (a new parallel class to EventBus for backtest-speed dispatch) and extend the backtest config module with BacktestEngineConfig and new StrategyType enum values for all 7 strategies.

## Requirements

1. **Create `argus/core/sync_event_bus.py`:**
   - Class `SyncEventBus` with the same conceptual interface as `EventBus`:
     - `subscribe(event_type, handler)` — register an async handler for an event type
     - `unsubscribe(event_type, handler)` — remove a handler
     - `async publish(event)` — assign monotonic sequence number, then `await handler(event)` for each subscriber **sequentially** (in subscription order)
     - `async drain()` — no-op (all handlers complete within publish)
     - `subscriber_count(event_type)` — return count
     - `reset()` — clear all subscriptions and reset sequence counter
   - Error isolation: if a handler raises, log the exception and continue to the next handler (same as production EventBus)
   - **Critical differences from production EventBus:**
     - NO `asyncio.create_task()` — handlers are awaited directly
     - NO `asyncio.Lock` — single-threaded, no contention
     - NO `self._pending` set — no background tasks
   - Use `dataclasses.replace(event, sequence=seq)` for stamping, same as production
   - Import `Event` from `argus.core.events`
   - ~40 lines of implementation

2. **Modify `argus/backtest/config.py`:**
   - Add `BULL_FLAG = "bull_flag"` and `FLAT_TOP_BREAKOUT = "flat_top_breakout"` to `StrategyType` enum
   - Add new `BacktestEngineConfig` Pydantic model:
     ```python
     class BacktestEngineConfig(BaseModel):
         """Configuration for BacktestEngine runs."""
         # Strategy
         strategy_type: StrategyType = StrategyType.ORB_BREAKOUT
         strategy_id: str = "strat_orb_breakout"
         symbols: list[str] | None = None  # None = all available

         # Date range
         start_date: date
         end_date: date

         # Data
         data_source: str = Field(default="databento", pattern=r"^(databento|parquet)$")
         cache_dir: Path = Path("data/databento_cache")
         verify_zero_cost: bool = True

         # Execution
         engine_mode: str = Field(default="sync", pattern=r"^(sync)$")  # Only sync for now
         initial_cash: float = Field(default=100_000.0, gt=0)
         slippage_per_share: float = Field(default=0.01, ge=0.0)

         # Scanner
         scanner_min_gap_pct: float = Field(default=0.02, ge=0.0)
         scanner_min_price: float = Field(default=10.0, ge=0.0)
         scanner_max_price: float = Field(default=500.0, gt=0.0)
         scanner_fallback_all_symbols: bool = True

         # EOD
         eod_flatten_time: str = "15:50"

         # Output
         output_dir: Path = Path("data/backtest_runs")
         log_level: str = Field(default="WARNING", pattern=r"^(DEBUG|INFO|WARNING|ERROR)$")

         # Config overrides (strategy parameter overrides)
         config_overrides: dict[str, Any] = Field(default_factory=dict)
     ```
   - Ensure existing `BacktestConfig`, `DataFetcherConfig`, and original `StrategyType` values are untouched

## Constraints
- Do NOT modify: `argus/core/event_bus.py`, any file in `argus/strategies/`, any file in `argus/ui/`
- Do NOT change: existing StrategyType enum values or their string representations
- Do NOT add: any imports to production code that reference sync_event_bus

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write in `tests/core/test_sync_event_bus.py`:
  1. `test_subscribe_and_publish` — handler receives published event
  2. `test_publish_multiple_handlers` — all handlers called in subscription order
  3. `test_publish_no_subscribers` — no error, returns cleanly
  4. `test_sequence_numbers` — events get incrementing sequence numbers
  5. `test_error_isolation` — handler exception doesn't prevent other handlers
  6. `test_unsubscribe` — removed handler not called
  7. `test_drain_is_noop` — drain completes immediately
  8. `test_reset` — clears subscribers and resets sequence
- New tests to write in `tests/backtest/test_config.py` (extend existing file):
  9. `test_backtest_engine_config_defaults` — model instantiates with only required fields (start_date, end_date)
  10. `test_backtest_engine_config_rejects_invalid_engine_mode` — validation error for unknown mode
  11. `test_strategy_type_bull_flag` — `StrategyType("bull_flag")` resolves
  12. `test_strategy_type_flat_top` — `StrategyType("flat_top_breakout")` resolves
  13. `test_existing_strategy_types_unchanged` — all 5 original values still resolve
- Minimum new test count: 13
- Test command (scoped): `python -m pytest tests/core/test_sync_event_bus.py tests/backtest/test_config.py -x -q`

## Definition of Done
- [ ] `argus/core/sync_event_bus.py` created with SyncEventBus class
- [ ] `argus/backtest/config.py` extended with BULL_FLAG, FLAT_TOP_BREAKOUT, BacktestEngineConfig
- [ ] All existing tests pass
- [ ] 13 new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Production EventBus unchanged | `git diff HEAD argus/core/event_bus.py` → no changes |
| Existing StrategyType values resolve | Test: `StrategyType("orb")` through `StrategyType("red_to_green")` all work |
| Existing BacktestConfig instantiation works | Test: `BacktestConfig(start_date=..., end_date=...)` with no other args |
| No strategy files modified | `git diff HEAD argus/strategies/` → no changes |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
docs/sprints/sprint-27/session-1-closeout.md

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-27/review-context.md`
2. The close-out report path: `docs/sprints/sprint-27/session-1-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/core/test_sync_event_bus.py tests/backtest/test_config.py -x -q`
5. Files that should NOT have been modified: `argus/core/event_bus.py`, `argus/backtest/replay_harness.py`, `argus/strategies/`

The @reviewer will produce its review report and write it to:
docs/sprints/sprint-27/session-1-review.md

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review files per the template instructions.

## Session-Specific Review Focus (for @reviewer)
1. Verify SyncEventBus dispatches handlers in subscription order (FIFO) — test must prove ordering
2. Verify SyncEventBus uses `await handler(event)` directly — NOT `asyncio.create_task()`
3. Verify no `asyncio.Lock` in SyncEventBus
4. Verify `drain()` is a no-op (not `asyncio.gather` on pending)
5. Verify new StrategyType values don't appear in any existing switch/match logic in walk_forward.py or replay_harness.py
6. Verify BacktestEngineConfig has all fields from the spec: engine_mode, data_source, cache_dir, verify_zero_cost, log_level

## Sprint-Level Regression Checklist (for @reviewer)
| # | Check | How to Verify |
|---|-------|---------------|
| R1 | Production EventBus unchanged | `git diff HEAD argus/core/event_bus.py` → no changes |
| R2 | Replay Harness unchanged | `git diff HEAD argus/backtest/replay_harness.py` → no changes |
| R5 | All strategy files unchanged | `git diff HEAD argus/strategies/` → no changes |
| R6 | No frontend files modified | `git diff HEAD argus/ui/` → no changes |
| R8 | No system.yaml changes | `git diff HEAD config/system.yaml config/system_live.yaml` → no changes |
| R13 | Existing StrategyType enum values resolve | Check test |
| R14 | BacktestConfig model backward compatible | Check test |

## Sprint-Level Escalation Criteria (for @reviewer)
1. SynchronousEventBus produces different handler dispatch order than production EventBus for the same subscription set.
2. Any existing backtest test fails.
10. Session compaction occurs before completing core deliverables.
