# Sprint 32, Session 3: Runtime Wiring

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/patterns/factory.py` (S2 output — factory + fingerprint)
   - `argus/main.py` (lines ~500–620: pattern construction, lines ~1375–1395: shadow routing)
   - `argus/backtest/vectorbt_pattern.py` (lines ~948–1000: `_create_pattern_by_name`)
   - `argus/analytics/trade_logger.py` (trade recording schema)
   - `argus/db/schema.sql` (trades table DDL)
2. Run the test baseline (DEC-328 — Session 2+):
   Scoped: `python -m pytest tests/strategies/patterns/test_factory.py tests/test_config_param_alignment.py -v`
   Expected: all passing
3. Verify Sessions 1+2 committed (config fields + factory present)

## Objective
Replace hardcoded pattern constructors with factory calls in `main.py` and PatternBacktester. Wire parameter fingerprint into trade records.

## Requirements

1. In `argus/main.py`, replace each of the 7 PatternModule pattern constructions with factory calls. Current pattern (repeated 7 times):
   ```python
   bull_flag_pattern = BullFlagPattern()
   bull_flag_strategy = PatternBasedStrategy(pattern=bull_flag_pattern, config=bull_flag_config, ...)
   ```
   Replace with:
   ```python
   from argus.strategies.patterns.factory import build_pattern_from_config
   bull_flag_pattern = build_pattern_from_config(bull_flag_config, "bull_flag")
   bull_flag_strategy = PatternBasedStrategy(pattern=bull_flag_pattern, config=bull_flag_config, ...)
   ```
   Remove the direct pattern class imports from the top of `main.py` (the factory handles lazy imports). Keep the PatternBasedStrategy import.

2. In `argus/backtest/vectorbt_pattern.py`, replace the body of `_create_pattern_by_name()` with a factory call:
   ```python
   def _create_pattern_by_name(name: str, config_path: Path) -> PatternModule:
       from argus.strategies.patterns.factory import build_pattern_from_config
       # Load YAML into the appropriate config model
       config = _load_pattern_config(name, config_path)
       return build_pattern_from_config(config, name)
   ```
   Create a helper `_load_pattern_config(name: str, config_path: Path) -> StrategyConfig` that maps pattern names to config loader functions (the `load_*_config()` functions already exist in `config.py`). This resolves DEF-121 — all 7 patterns now supported.

3. In `argus/analytics/trade_logger.py` (or `argus/db/schema.sql` if schema is managed there):
   - Add `config_fingerprint TEXT` column to the `trades` table (nullable, for backward compat with existing records)
   - When recording a trade, populate `config_fingerprint` from the strategy's config. The fingerprint should be computed once at strategy instantiation and stored on the strategy instance (add a `config_fingerprint` property or attribute to `PatternBasedStrategy`, set during construction).

4. In `argus/strategies/pattern_strategy.py` (minimal change):
   - Add `self._config_fingerprint: str | None = None` in `__init__`
   - Add a `config_fingerprint` property that returns it
   - The fingerprint is set externally after construction (by main.py or the variant spawner)

5. Wire fingerprint population: in `main.py`, after constructing each PatternBasedStrategy, compute and set the fingerprint:
   ```python
   from argus.strategies.patterns.factory import compute_parameter_fingerprint, get_pattern_class
   pattern_cls = get_pattern_class("bull_flag")
   bull_flag_strategy._config_fingerprint = compute_parameter_fingerprint(bull_flag_config, pattern_cls)
   ```

## Constraints
- Do NOT modify `argus/core/orchestrator.py`
- Do NOT change any strategy's runtime behavior — only how it's constructed
- Do NOT remove the `params_to_dict()` function from `vectorbt_pattern.py` (still used elsewhere)
- Do NOT change the PatternBacktester's public API — only the internal factory method
- Fingerprint column is nullable — existing trade records get NULL, not retroactively computed

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests in `tests/test_runtime_wiring.py`:
  - Integration: mock startup path, verify all 7 patterns constructed via factory with correct params
  - PatternBacktester: `_create_pattern_by_name` works for all 7 patterns (was 3)
  - Trade fingerprint: mock trade record, verify `config_fingerprint` column populated
  - Backward compat: historical trade records (without fingerprint) still queryable
- Minimum new test count: 8
- Test command: `python -m pytest tests/test_runtime_wiring.py -v`

## Definition of Done
- [ ] 7 pattern constructions in main.py use factory
- [ ] PatternBacktester supports all 7 patterns (DEF-121 resolved)
- [ ] trades table has config_fingerprint column
- [ ] PatternBasedStrategy has config_fingerprint attribute
- [ ] All existing tests pass
- [ ] New integration tests pass
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| R1: All 12 strategies instantiate | Startup test shows all 12 IDs |
| R3: Defaults unchanged | Factory with default config → same behavior |
| R4+R5: Backtester supports all 7 | Test calls factory for each |
| R8: Non-PatternModule untouched | `git diff` on protected files |
| R15: trades migration backward compat | Query historical records succeeds |

## Close-Out
**Write the close-out report to:** docs/sprints/sprint-32/session-3-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-32/review-context.md`
2. Close-out report: `docs/sprints/sprint-32/session-3-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/test_runtime_wiring.py tests/strategies/patterns/test_factory.py -v`
5. Files that should NOT have been modified: `orchestrator.py`, any non-PatternModule strategy file, any frontend file

## Post-Review Fix Documentation
If @reviewer reports CONCERNS, fix and update both files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify main.py pattern imports removed (factory handles lazy imports)
2. Verify `_create_pattern_by_name` replacement handles all 7 patterns
3. Verify fingerprint column is nullable (not breaking existing records)
4. Verify pattern_strategy.py change is minimal (attribute + property only)
5. Verify no behavioral change to any strategy's signal generation

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-32/review-context.md`

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-32/review-context.md`
