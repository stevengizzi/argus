# Sprint 26, Session 9: Integration Wiring

## Pre-Flight Checks
1. Read:
   - `argus/main.py` (Phase 8 strategy creation, Phase 9 orchestrator registration)
   - `argus/strategies/__init__.py`
   - `argus/strategies/red_to_green.py`, `argus/strategies/pattern_strategy.py`
   - `argus/strategies/patterns/__init__.py` (exports)
   - `argus/core/config.py` (all new config loaders)
   - `config/strategies/red_to_green.yaml`, `bull_flag.yaml`, `flat_top_breakout.yaml`
2. Scoped test:
   ```
   python -m pytest tests/strategies/ tests/backtest/ -x -q
   ```
3. Verify branch

## Objective
Wire RedToGreenStrategy, BullFlagPattern (as PatternBasedStrategy), and FlatTopBreakoutPattern (as PatternBasedStrategy) into main.py, Orchestrator, and verify API serves all 7 strategies.

## Requirements

1. **Update `argus/main.py` Phase 8 — add after Afternoon Momentum section:**

   a. **Red-to-Green (optional, config-gated):**
   ```python
   # Red-to-Green (optional — only if config file exists)
   r2g_strategy: RedToGreenStrategy | None = None
   r2g_yaml = self._config_dir / "strategies" / "red_to_green.yaml"
   if r2g_yaml.exists():
       r2g_config = load_red_to_green_config(r2g_yaml)
       r2g_strategy = RedToGreenStrategy(
           config=r2g_config,
           data_service=self._data_service,
           clock=self._clock,
       )
       if not use_universe_manager:
           r2g_strategy.set_watchlist(symbols)
       strategies_created.append("RedToGreen")
   ```

   b. **Bull Flag (optional, PatternBasedStrategy wrapper):**
   ```python
   # Bull Flag (optional — PatternBasedStrategy wrapping BullFlagPattern)
   bull_flag_strategy: PatternBasedStrategy | None = None
   bull_flag_yaml = self._config_dir / "strategies" / "bull_flag.yaml"
   if bull_flag_yaml.exists():
       bull_flag_config = load_bull_flag_config(bull_flag_yaml)
       bull_flag_pattern = BullFlagPattern()
       bull_flag_strategy = PatternBasedStrategy(
           pattern=bull_flag_pattern,
           config=bull_flag_config,
           data_service=self._data_service,
           clock=self._clock,
       )
       if not use_universe_manager:
           bull_flag_strategy.set_watchlist(symbols)
       strategies_created.append("BullFlag")
   ```

   c. **Flat-Top Breakout (same pattern as Bull Flag)**

   d. **Phase 9 registration:** Add all 3 to Orchestrator (same `if not None` pattern)

2. **Update `argus/main.py` imports:**
   - Add: `from argus.strategies.red_to_green import RedToGreenStrategy`
   - Add: `from argus.strategies.patterns import PatternBasedStrategy, BullFlagPattern, FlatTopBreakoutPattern`
   - Add: `from argus.core.config import load_red_to_green_config, load_bull_flag_config, load_flat_top_breakout_config`

3. **Verify `argus/strategies/__init__.py`** has all necessary exports.

4. **Create strategy spec sheets (can be stubs with TODO for backtest data):**
   - `docs/strategies/STRATEGY_RED_TO_GREEN.md`
   - `docs/strategies/STRATEGY_BULL_FLAG.md`
   - `docs/strategies/STRATEGY_FLAT_TOP_BREAKOUT.md`
   Follow template from `STRATEGY_VWAP_RECLAIM.md`. Include: identity, description, market conditions, operating window, entry criteria, exit rules, position sizing, risk limits, benchmarks, backtest results (from S7/S8), universe filter.

## Constraints
- Do NOT modify `orchestrator.py`, `risk_manager.py`, `universe_manager.py`, `event_bus.py`
- Do NOT modify existing strategy creation blocks in main.py (only ADD new ones after them)
- Follow EXACT same creation pattern as existing strategies (if yaml.exists(), load config, create, optional watchlist, register)

## Test Targets
New tests in `tests/test_integration_sprint26.py`:
1. `test_r2g_strategy_creation_from_config` — create R2G from YAML, verify instance
2. `test_bull_flag_pattern_strategy_creation` — create PatternBasedStrategy with BullFlagPattern
3. `test_flat_top_pattern_strategy_creation` — same with FlatTopBreakoutPattern
4. `test_orchestrator_registers_7_strategies` — mock orchestrator, register all 7, verify count
5. `test_api_strategies_returns_7` — mock API endpoint returns 7 strategy entries
6. `test_disabled_strategy_not_created` — config with enabled:false → strategy not created
7. `test_missing_yaml_skips_strategy` — missing YAML file → strategy skipped gracefully
8. `test_orchestrator_allocation_with_7_strategies` — verify each gets allocated_capital > 0
- Minimum new test count: 8
- Test: `python -m pytest tests/test_integration_sprint26.py -x -v`

## Definition of Done
- [ ] R2G, Bull Flag, Flat-Top all created in main.py Phase 8
- [ ] All 3 registered with Orchestrator in Phase 9
- [ ] Config-gated: missing YAML skips, enabled:false skips
- [ ] Strategy spec sheets created
- [ ] API /strategies returns 7 strategies
- [ ] All existing tests pass, 8+ new tests
- [ ] Close-out: `docs/sprints/sprint-26/session-9-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
Write to: `docs/sprints/sprint-26/session-9-closeout.md`

## Tier 2 Review
Review context: `docs/sprints/sprint-26/review-context.md`
Close-out: `docs/sprints/sprint-26/session-9-closeout.md`
Test: `python -m pytest tests/test_integration_sprint26.py -x -v`
**This is a non-final session — use scoped test command above.**
Do-not-modify: orchestrator.py, risk_manager.py, universe_manager.py, event_bus.py, existing strategy creation blocks

## Session-Specific Review Focus
1. New strategy creation follows EXACT same pattern as existing (if/else, optional, config-gated)
2. Orchestrator.register_strategy called for all 3 new strategies
3. No modifications to Orchestrator or UM code
4. Import statements added correctly
5. 7-strategy allocation test verifies non-zero capital for each
6. Strategy spec sheets follow template structure

## Sprint-Level Regression/Escalation
See `docs/sprints/sprint-26/review-context.md`.
