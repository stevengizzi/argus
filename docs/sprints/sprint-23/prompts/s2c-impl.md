# Sprint 23, Session 2c: VWAP + Afternoon Momentum Filter Declarations

## Pre-Flight Checks
1. Read: `argus/core/config.py` (UniverseFilterConfig), `config/strategies/vwap_reclaim.yaml`, `config/strategies/afternoon_momentum.yaml`, `argus/strategies/vwap_reclaim.py`, `argus/strategies/afternoon_momentum.py`
2. Run: `python -m pytest tests/ -x -q` — all passing
3. Branch: `sprint-23`

## Objective
Extract implicit filter logic from VWAP Reclaim and Afternoon Momentum strategies and declare explicit `universe_filter` sections in their YAML configs.

## Requirements

1. Read each strategy's Python code to identify implicit assumptions about price, volume, market cap, sector.

2. Add `universe_filter:` to `config/strategies/vwap_reclaim.yaml`. VWAP Reclaim is a mean-reversion strategy — may prefer:
   - Higher liquidity (wider float, higher volume) for clean VWAP behavior
   - Mid-to-large cap (VWAP more meaningful with institutional flow)

3. Add `universe_filter:` to `config/strategies/afternoon_momentum.yaml`. Afternoon Momentum targets consolidation breakouts — may prefer:
   - Active stocks with sufficient volume for afternoon session
   - Price range appropriate for momentum plays

4. Verify both configs load and validate.

## Constraints
- Do NOT modify strategy Python code — only YAML configs
- Do NOT modify `argus/core/config.py`
- If no implicit assumption exists for a field, omit it from YAML (defaults to None)

## Test Targets
- New tests:
  1. `test_vwap_reclaim_config_loads_with_filter`
  2. `test_afternoon_momentum_config_loads_with_filter`
  3. `test_vwap_reclaim_filter_values_reasonable`
  4. `test_afternoon_momentum_filter_values_reasonable`
  5. `test_vwap_reclaim_yaml_keys_match_model`
  6. `test_afternoon_momentum_yaml_keys_match_model`
- Minimum: 6 tests
- Command: `python -m pytest tests/ -k "vwap_filter or afternoon_filter" -v`

## Definition of Done
- [ ] Both YAML configs have `universe_filter` sections
- [ ] All existing tests pass
- [ ] 6+ new tests passing

## Close-Out
Follow `.claude/skills/close-out.md`.

## Sprint-Level Regression Checklist
R1–R3, R8 (VWAP loads), R9 (Afternoon loads), R11 (YAML↔model match).

## Sprint-Level Escalation Criteria
E5: Existing strategy tests fail → ESCALATE. E13: YAML↔Pydantic mismatch → ESCALATE.
