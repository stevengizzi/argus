# Sprint 23, Session 2b: ORB Family Filter Declarations

## Pre-Flight Checks
1. Read: `argus/core/config.py` (Session 2a output — UniverseFilterConfig), `config/strategies/orb_breakout.yaml`, `config/strategies/orb_scalp.yaml`, `argus/strategies/orb_base.py`, `argus/strategies/orb_breakout.py`, `argus/strategies/orb_scalp.py`
2. Run: `python -m pytest tests/ -x -q` — all passing
3. Branch: `sprint-23`

## Objective
Extract implicit filter logic from ORB Breakout and ORB Scalp strategy code and declare explicit `universe_filter` sections in their YAML configs.

## Requirements

1. Read each ORB strategy's Python code to identify implicit assumptions about:
   - Price range (any min/max price checks in `on_candle` or entry logic)
   - Volume requirements (RVOL thresholds, minimum volume checks)
   - Market cap preferences (any checks or assumptions)
   - Sector preferences (any sector-based logic)

2. Add `universe_filter:` section to `config/strategies/orb_breakout.yaml`:
   ```yaml
   universe_filter:
     min_price: 10.0       # From existing scanner config / strategy assumptions
     max_price: 500.0      # From existing scanner config
     min_avg_volume: 500000 # Momentum stocks need liquidity
     # min_market_cap, min_float, sectors: set based on code analysis
   ```

3. Add `universe_filter:` section to `config/strategies/orb_scalp.yaml` with appropriate values (may differ from breakout — scalp may prefer higher liquidity).

4. Verify both configs load and validate:
   ```python
   from argus.core.config import load_orb_config
   config = load_orb_config("config/strategies/orb_breakout.yaml")
   assert config.universe_filter is not None
   ```

## Constraints
- Do NOT modify strategy Python code (`.py` files) — only YAML configs
- Do NOT modify `argus/core/config.py` (already done in 2a)
- Filter values should reflect what the strategy actually needs, not aspirational values
- If the strategy has no implicit assumption for a field, leave it as `None` (omit from YAML)

## Test Targets
- New tests:
  1. `test_orb_breakout_config_loads_with_filter`: config loads, universe_filter populated
  2. `test_orb_scalp_config_loads_with_filter`: config loads, universe_filter populated
  3. `test_orb_breakout_filter_values_reasonable`: min_price > 0, min_avg_volume > 0
  4. `test_orb_scalp_filter_values_reasonable`: same
  5. `test_orb_breakout_yaml_keys_match_model`: no unrecognized keys in universe_filter
  6. `test_orb_scalp_yaml_keys_match_model`: same
- Minimum: 6 tests
- Command: `python -m pytest tests/ -k "orb" -k "filter" -v`

## Definition of Done
- [ ] Both ORB YAML configs have `universe_filter` sections
- [ ] Filter values extracted from actual strategy code/assumptions
- [ ] All existing tests pass
- [ ] 6+ new tests passing
- [ ] Configs load without errors

## Close-Out
Follow `.claude/skills/close-out.md`.

## Sprint-Level Regression Checklist
R1–R3, R6 (ORB Breakout loads), R7 (ORB Scalp loads), R10 (mutual exclusion), R11 (YAML↔model match).

## Sprint-Level Escalation Criteria
E5: Existing ORB tests fail → ESCALATE. E13: YAML↔Pydantic mismatch → ESCALATE.
