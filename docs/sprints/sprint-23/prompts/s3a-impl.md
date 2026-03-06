# Sprint 23, Session 3a: Routing Table Construction

## Pre-Flight Checks
1. Read: `argus/data/universe_manager.py` (Session 1b output), `argus/core/config.py` (UniverseFilterConfig from Session 2a)
2. Run: `python -m pytest tests/ -x -q` — all passing
3. Branch: `sprint-23`

## Objective
Add the routing table to Universe Manager — a pre-computed mapping from symbols to qualifying strategy IDs based on each strategy's `universe_filter`.

## Requirements

1. In `argus/data/universe_manager.py`, add:

   a. `def build_routing_table(self, strategy_configs: dict[str, StrategyConfig]) -> None`:
      - For each symbol in `_viable_symbols`:
        - For each strategy in `strategy_configs`:
          - If strategy has no `universe_filter` (None), it matches ALL viable symbols
          - If strategy has `universe_filter`, check each field against the symbol's `SymbolReferenceData`:
            - `min_price` / `max_price`: check against `prev_close` (None reference = pass)
            - `min_market_cap` / `max_market_cap`: check against `market_cap` (None reference = pass)
            - `min_float`: check against `float_shares` (None reference = pass)
            - `min_avg_volume`: check against `avg_volume` (None reference = pass)
            - `sectors`: if non-empty, symbol's `sector` must be in list (None sector = fail)
            - `exclude_sectors`: if non-empty, symbol's `sector` must NOT be in list (None sector = pass)
          - If all checks pass, add strategy_id to symbol's routing set
      - Store as `_routing_table: dict[str, set[str]]`
      - Log: per-strategy match counts

   b. `def route_candle(self, symbol: str) -> set[str]`:
      - O(1) dict lookup: `return self._routing_table.get(symbol, set())`

   c. `def get_strategy_universe_size(self, strategy_id: str) -> int`:
      - Count symbols in routing table that include this strategy_id

   d. `def get_strategy_symbols(self, strategy_id: str) -> set[str]`:
      - Return set of symbols routed to this strategy

   e. `def get_universe_stats(self) -> dict`:
      - Returns dict with: total_viable, per_strategy_counts, last_build_time, cache_age_minutes

2. **Filter matching rule for missing reference data:** When a symbol has `None` for a field (e.g., `market_cap is None`) and the filter has a constraint on that field (e.g., `min_market_cap = 500_000_000`), the symbol PASSES the filter. Rationale: we don't want to exclude symbols just because FMP didn't return complete data. This matches the spec-by-contradiction edge case handling.

## Constraints
- Do NOT modify any file other than `argus/data/universe_manager.py`
- Do NOT touch strategy code, config.py, or YAML files
- Do NOT implement event dispatch (Session 3b)
- Routing table must be rebuildable (call build_routing_table again to refresh)

## Test Targets
- New tests:
  1. `test_route_candle_single_strategy_match`: symbol matches one strategy
  2. `test_route_candle_multi_strategy_match`: symbol matches multiple strategies
  3. `test_route_candle_no_match`: symbol matches no strategies → empty set
  4. `test_sector_include_filter`: only symbols in specified sectors match
  5. `test_sector_exclude_filter`: symbols in excluded sectors don't match
  6. `test_missing_reference_data_passes`: symbol with None market_cap passes min_market_cap filter
  7. `test_no_filter_matches_all`: strategy with universe_filter=None matches all viable
  8. `test_get_strategy_universe_size`: correct counts per strategy
- Minimum: 8 tests
- Command: `python -m pytest tests/data/test_universe_manager.py -v -k "rout"`

## Definition of Done
- [ ] Routing table construction with all filter dimensions
- [ ] O(1) route_candle lookup
- [ ] Per-strategy stats
- [ ] All existing tests pass
- [ ] 8+ new tests passing

## Close-Out
Follow `.claude/skills/close-out.md`.

## Sprint-Level Regression Checklist
R1–R3. No existing behavior changed (modifying new file only).

## Sprint-Level Escalation Criteria
E1: Routing lookup >50μs → ESCALATE. E7/E8: Incorrect routing → ESCALATE.
