# Sprint 23, Session 4b: Main.py Startup Wiring

## Pre-Flight Checks
1. Read: `argus/main.py` (full file — understand the 12-phase startup sequence, especially Phases 7–11), `argus/data/universe_manager.py` (all sessions' output), `argus/data/databento_data_service.py` (Session 3b output — set_viable_universe), `argus/core/config.py` (UniverseManagerConfig in SystemConfig)
2. Run: `python -m pytest tests/ -x -q` — all passing
3. Branch: `sprint-23`

## Objective
Wire the Universe Manager into the startup sequence, replacing the scanner→set_watchlist→data_service.start flow when enabled while preserving full backward compatibility.

## Requirements

1. In `argus/main.py`, modify the startup sequence (around Phase 7–11):

   **When `config.system.universe_manager.enabled is True` AND `broker_source != "simulated"` (not backtest/replay):**

   a. After Phase 7 (Scanner):
      - Create `FMPReferenceClient` with config
      - Create `UniverseManager` with reference client, config, and scanner
      - Call `universe_manager.build_viable_universe()` with scanner results as fallback
      - If FMP fails, call `universe_manager.build_viable_universe_fallback(scanner_symbols)`
      - Log viable universe size

   b. In Phase 8 (Strategy Instances):
      - Still create strategies as before
      - But do NOT call `strategy.set_watchlist(symbols)` with scanner symbols
      - Instead, strategies will receive candles via routing (set up in Phase 10.5)

   c. After Phase 9 (Orchestrator):
      - Call `universe_manager.build_routing_table(strategy_configs)` using the strategies' configs
      - Log per-strategy match counts

   d. In Phase 10.5 (Event Routing):
      - Modify `_on_candle_for_strategies` to use routing table:
        ```python
        async def _on_candle_for_strategies(self, event: CandleEvent):
            if self._universe_manager and self._universe_manager.is_built:
                matching_strategy_ids = self._universe_manager.route_candle(event.symbol)
                for strategy_id in matching_strategy_ids:
                    strategy = self._strategies.get(strategy_id)
                    if strategy and strategy.is_active:
                        signal = await strategy.on_candle(event)
                        if signal:
                            await self._event_bus.publish(signal)
            else:
                # Original path: iterate all strategies, check watchlist
                for strategy in self._strategies.values():
                    if strategy.is_active and event.symbol in strategy.watchlist:
                        signal = await strategy.on_candle(event)
                        if signal:
                            await self._event_bus.publish(signal)
        ```

   e. In Phase 11 (Start Streaming):
      - Call `self._data_service.set_viable_universe(universe_manager.viable_symbols)`
      - Start data service: `await self._data_service.start(symbols=[], timeframes=["1m"])`
        (symbols list doesn't matter when ALL_SYMBOLS is configured in Databento config)

   f. Store `self._universe_manager` for API access (Session 5a will expose it)

   **When `universe_manager.enabled is False` OR backtest/replay mode:**
   - Existing flow unchanged: scanner.scan() → set_watchlist(symbols) → data_service.start(symbols)
   - `self._universe_manager = None`

2. Also store universe_manager in AppState for API access:
   - In the API server setup section, add universe_manager to app_state
   - `app_state.universe_manager = self._universe_manager`
   - Add `universe_manager: UniverseManager | None = None` field to AppState dataclass in `argus/api/dependencies.py`

## Constraints
- Do NOT modify orchestrator.py, risk_manager.py, or any strategy code
- Do NOT modify the AI layer
- Preserve exact existing behavior when universe_manager.enabled=false
- The data_service.start() call may need Databento config to specify ALL_SYMBOLS — verify config/system.yaml `databento.symbols` field supports this

## Canary Tests
Before making changes, verify:
- Existing startup flow works: `python -m pytest tests/ -k "startup or main" -v` (if such tests exist)
- All strategy tests pass: `python -m pytest tests/strategies/ -v`

## Test Targets
- New tests:
  1. `test_startup_with_um_enabled`: mock FMP + Databento, verify UM path executes
  2. `test_startup_with_um_disabled`: verify old scanner path executes
  3. `test_startup_um_enabled_fmp_fails`: verify graceful degradation to scanner symbols
  4. `test_candle_routing_um_active`: candle dispatched only to matching strategies
  5. `test_candle_routing_um_disabled`: candle dispatched via old watchlist path
  6. `test_backtest_mode_ignores_um`: simulated broker → old path regardless of config
  7. `test_universe_manager_in_app_state`: verify accessible via AppState
  8. `test_strategy_not_called_for_non_matching_symbol`: strategy.on_candle NOT called for symbol outside its filter
- Minimum: 8 tests
- Command: `python -m pytest tests/ -k "startup or universe_manager" -v`

## Definition of Done
- [ ] Universe Manager wired into startup sequence
- [ ] Candle routing uses routing table when UM enabled
- [ ] Backward compatibility verified (UM disabled, backtest mode)
- [ ] Universe Manager accessible in AppState
- [ ] All existing tests pass (this is the critical session — EVERY existing test must pass)
- [ ] 8+ new tests passing

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| ALL existing pytest tests pass | `python -m pytest tests/ -x -q` — must be 1,977+ |
| ALL existing Vitest tests pass | `cd argus/ui && npx vitest run` — 377+ |
| ORB mutual exclusion | `python -m pytest tests/ -k "exclusion" -v` |
| Risk Manager tests | `python -m pytest tests/ -k "risk" -v` |
| API tests | `python -m pytest tests/ -k "api" -v` |
| Replay tests | `python -m pytest tests/ -k "replay" -v` |

## Close-Out
Follow `.claude/skills/close-out.md`.

## Sprint-Level Regression Checklist
R1–R26 (FULL checklist — this is the integration session).

## Sprint-Level Escalation Criteria
E1–E13 (ALL criteria apply — this is the highest-risk session). Especially: E5 (any existing test fails), E6 (ORB exclusion), E9 (Databento errors), E10 (backtest affected).
