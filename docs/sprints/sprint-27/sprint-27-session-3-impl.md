# Sprint 27, Session 3: BacktestEngine — Component Assembly + Strategy Factory

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/sync_event_bus.py` (S1 output — SyncEventBus)
   - `argus/backtest/config.py` (S1 output — BacktestEngineConfig, StrategyType)
   - `argus/backtest/backtest_data_service.py` (reused as-is)
   - `argus/backtest/replay_harness.py` (reference: lines 238–480 for _setup, _create_strategy, _create_* methods)
   - `argus/strategies/pattern_strategy.py` (PatternBasedStrategy constructor — needs pattern + config + data_service + clock)
   - `argus/strategies/patterns/bull_flag.py` (BullFlagPattern class)
   - `argus/strategies/patterns/flat_top_breakout.py` (FlatTopBreakoutPattern class)
   - `docs/sprints/sprint-27/design-summary.md`
2. Run the test baseline (DEC-328 — Session 2+, scoped):
   ```bash
   python -m pytest tests/core/test_sync_event_bus.py tests/backtest/test_config.py -x -q
   ```
   Expected: all passing (full suite confirmed by S1/S2 close-outs)
3. Verify you are on the correct branch: `main`

## Objective
Create the BacktestEngine skeleton: constructor, component assembly (_setup), strategy factory for all 7 strategy types (including PatternBasedStrategy-wrapped patterns), and teardown. This session builds the wiring; the bar loop and fill model come in S4.

## Requirements

1. **Create `argus/backtest/engine.py`:**

   Class `BacktestEngine` with this initial structure:

   ```python
   class BacktestEngine:
       """Production-code backtesting engine with synchronous dispatch.

       Wires real ARGUS components (strategies, indicators, risk, orders)
       in fast-replay mode using SyncEventBus instead of async EventBus.
       No tick synthesis — uses bar-level fill model (worst-case priority).

       Usage:
           config = BacktestEngineConfig(start_date=..., end_date=...)
           engine = BacktestEngine(config)
           result = await engine.run()
       """

       def __init__(self, config: BacktestEngineConfig) -> None:
           ...

       async def _setup(self) -> None:
           """Initialize all production components for the backtest."""
           # Follow ReplayHarness._setup() pattern (lines 238-315) but use:
           # - SyncEventBus instead of EventBus
           # - BacktestEngineConfig instead of BacktestConfig
           # - Strategy factory that handles all 7 types
           ...

       def _create_strategy(self, config_dir: Path) -> BaseStrategy:
           """Create strategy instance from config.strategy_type.

           Handles all 7 strategy types:
           - ORB_BREAKOUT → OrbBreakoutStrategy
           - ORB_SCALP → OrbScalpStrategy
           - VWAP_RECLAIM → VwapReclaimStrategy
           - AFTERNOON_MOMENTUM → AfternoonMomentumStrategy
           - RED_TO_GREEN → RedToGreenStrategy
           - BULL_FLAG → PatternBasedStrategy(BullFlagPattern(), config, ...)
           - FLAT_TOP_BREAKOUT → PatternBasedStrategy(FlatTopBreakoutPattern(), config, ...)
           """

       async def _teardown(self) -> None:
           """Clean up all components."""
   ```

2. **_setup() implementation (adapt from ReplayHarness._setup):**
   - Create output directory
   - Generate DB filename per DEC-056 convention
   - Initialize `SyncEventBus` (NOT EventBus)
   - Initialize `FixedClock` at pre-market of first trading day
   - Initialize `DatabaseManager` + `TradeLogger`
   - Initialize `SimulatedBroker` with slippage config
   - Initialize `BacktestDataService` with the SyncEventBus
   - Load risk config and order manager config from YAML
   - Initialize `RiskManager` with (config, broker, event_bus=sync_bus, clock)
   - Initialize `OrderManager` with (event_bus=sync_bus, broker, clock, config, trade_logger)
   - Initialize strategy via `_create_strategy()`
   - Set strategy.allocated_capital
   - Subscribe engine's candle handler to SyncEventBus
   - Apply log level from config

3. **_create_strategy() — all 7 types:**
   - For ORB_BREAKOUT, ORB_SCALP, VWAP_RECLAIM, AFTERNOON_MOMENTUM: follow ReplayHarness pattern (load YAML, create config model, apply overrides, create strategy with data_service and clock)
   - For RED_TO_GREEN: same pattern, load `config/strategies/red_to_green.yaml`, create `RedToGreenStrategy(config, data_service, clock)`
   - For BULL_FLAG: load `config/strategies/bull_flag.yaml`, create `BullFlagPattern()`, create `PatternBasedStrategy(pattern=bull_flag_pattern, config=strategy_config, data_service=self._data_service, clock=self._clock)`
   - For FLAT_TOP_BREAKOUT: same as Bull Flag but with `FlatTopBreakoutPattern()`
   - Apply `config_overrides` from BacktestEngineConfig to the strategy config (follow existing override pattern)
   - Unknown strategy type → raise `ValueError(f"Unknown strategy type: {strategy_type}")`

4. **_teardown() implementation (adapt from ReplayHarness._teardown):**
   - Stop OrderManager
   - Close DatabaseManager
   - Log DB path

5. **Stub `run()` method** — just `_setup()` → `_teardown()` for now (S4/S5 will fill in the execution):
   ```python
   async def run(self) -> BacktestResult:
       await self._setup()
       # Execution loop added in S4/S5
       result = self._empty_result()
       await self._teardown()
       return result
   ```

6. **_empty_result()** — copy from ReplayHarness (line 720–750)

## Constraints
- Do NOT modify: `argus/core/event_bus.py`, `argus/backtest/replay_harness.py`, `argus/backtest/backtest_data_service.py`, any strategy files
- Do NOT change: any existing class interfaces
- Do NOT add: bar processing or fill logic (that's S4)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write in `tests/backtest/test_engine.py`:
  1. `test_setup_creates_sync_event_bus` — verify _event_bus is SyncEventBus, not EventBus
  2. `test_setup_creates_fixed_clock` — verify _clock is FixedClock
  3. `test_setup_creates_simulated_broker` — verify _broker is SimulatedBroker
  4. `test_factory_orb_breakout` — strategy_type=ORB_BREAKOUT → OrbBreakoutStrategy
  5. `test_factory_orb_scalp` — strategy_type=ORB_SCALP → OrbScalpStrategy
  6. `test_factory_vwap_reclaim` — strategy_type=VWAP_RECLAIM → VwapReclaimStrategy
  7. `test_factory_afternoon_momentum` — strategy_type=AFTERNOON_MOMENTUM → AfternoonMomentumStrategy
  8. `test_factory_red_to_green` — strategy_type=RED_TO_GREEN → RedToGreenStrategy
  9. `test_factory_bull_flag` — strategy_type=BULL_FLAG → PatternBasedStrategy with BullFlagPattern
  10. `test_factory_flat_top` — strategy_type=FLAT_TOP_BREAKOUT → PatternBasedStrategy with FlatTopBreakoutPattern
  11. `test_factory_unknown_raises` — invalid strategy type → ValueError
  12. `test_teardown_cleans_up` — run() with stub completes without error, DB file created
- Minimum new test count: 12
- Test command (scoped): `python -m pytest tests/backtest/test_engine.py -x -q`

## Definition of Done
- [ ] `argus/backtest/engine.py` created with BacktestEngine class
- [ ] _setup() wires all components using SyncEventBus
- [ ] _create_strategy() handles all 7 strategy types
- [ ] _teardown() cleans up properly
- [ ] Stub run() works end-to-end (setup → empty result → teardown)
- [ ] All existing tests pass
- [ ] 12 new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Production EventBus not imported in engine.py | `grep "from argus.core.event_bus import" argus/backtest/engine.py` → should NOT appear (use sync_event_bus) |
| Replay Harness unchanged | `git diff HEAD argus/backtest/replay_harness.py` → no changes |
| Strategy files unchanged | `git diff HEAD argus/strategies/` → no changes |
| BacktestDataService unchanged | `git diff HEAD argus/backtest/backtest_data_service.py` → no changes |

## Close-Out
Write the close-out report to: docs/sprints/sprint-27/session-3-closeout.md

Follow the close-out skill. Include structured JSON appendix.

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: `docs/sprints/sprint-27/review-context.md`
2. Close-out: `docs/sprints/sprint-27/session-3-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command: `python -m pytest tests/backtest/test_engine.py -x -q`
5. Do-not-modify: `argus/core/event_bus.py`, `argus/backtest/replay_harness.py`, `argus/backtest/backtest_data_service.py`, `argus/strategies/`

@reviewer writes to: docs/sprints/sprint-27/session-3-review.md

## Session-Specific Review Focus (for @reviewer)
1. Verify engine.py imports SyncEventBus, NOT EventBus
2. Verify _setup() follows ReplayHarness._setup() pattern (same component set, same config loading)
3. Verify PatternBasedStrategy is used for BULL_FLAG and FLAT_TOP_BREAKOUT (not direct strategy subclass)
4. Verify config_overrides are applied to strategy configs (not silently ignored)
5. Verify allocated_capital is set on the strategy after creation
6. Verify _teardown matches ReplayHarness._teardown pattern

## Sprint-Level Regression Checklist (for @reviewer)
| # | Check | How to Verify |
|---|-------|---------------|
| R1 | Production EventBus unchanged | `git diff HEAD argus/core/event_bus.py` |
| R2 | Replay Harness unchanged | `git diff HEAD argus/backtest/replay_harness.py` |
| R3 | BacktestDataService unchanged | `git diff HEAD argus/backtest/backtest_data_service.py` |
| R5 | All strategy files unchanged | `git diff HEAD argus/strategies/` |

## Sprint-Level Escalation Criteria (for @reviewer)
3. Strategy behavior differs between BacktestEngine and direct unit test invocation with identical inputs.
9. Any existing backtest test fails.
10. Session compaction occurs before completing core deliverables.
