# Sprint 23, Session 3b: Databento Fast-Path + Event Integration

## Pre-Flight Checks
1. Read: `argus/data/databento_data_service.py` (full file — understand candle processing pipeline, _on_ohlcv callback, IndicatorEngine instantiation), `argus/data/universe_manager.py` (Sessions 1b+3a output), `argus/core/events.py` (event types), `argus/core/event_bus.py` (pub/sub pattern)
2. Run: `python -m pytest tests/ -x -q` — all passing
3. Branch: `sprint-23`

## Objective
Add fast-path symbol discard to DatabentoDataService so non-viable symbols are dropped before IndicatorEngine processing. Optionally add a UniverseUpdateEvent for logging.

## Requirements

1. In `argus/data/databento_data_service.py`:

   a. Add field: `_viable_universe: set[str] | None = None`

   b. Add method: `def set_viable_universe(self, symbols: set[str]) -> None`:
      - Stores the viable symbol set
      - Logs count: "Viable universe set: {len(symbols)} symbols"

   c. Modify the candle/tick processing path (likely `_on_ohlcv` or the callback that handles incoming Databento records):
      - BEFORE any processing (before IndicatorEngine lookup, before CandleEvent creation):
        ```python
        if self._viable_universe is not None and symbol not in self._viable_universe:
            return  # Fast-path discard
        ```
      - This must be the FIRST check in the hot path — before any allocation or computation
      - Apply the same check to tick event processing if applicable

   d. Modify IndicatorEngine instantiation:
      - Currently creates IndicatorEngine on first candle for a symbol
      - When `_viable_universe` is set, only create IndicatorEngine for symbols IN the viable set
      - When `_viable_universe` is None (UM disabled), behavior is unchanged — create on first candle for any symbol

2. In `argus/core/events.py` (optional):
   - Add `UniverseUpdateEvent` if useful for logging/UI:
     ```python
     @dataclass
     class UniverseUpdateEvent(Event):
         viable_count: int
         total_fetched: int
         timestamp: datetime
     ```
   - Only add if the event type provides value for API/logging. If not needed, skip.

3. **Critical:** The fast-path discard must not affect the existing behavior when `_viable_universe is None`. In that case, ALL symbols are processed as before (backward compatibility).

## Constraints
- Do NOT modify `argus/core/orchestrator.py`
- Do NOT modify strategy code
- Do NOT modify `argus/main.py` (Session 4b)
- Do NOT change the DatabentoDataService constructor signature
- The `set_viable_universe` method is additive — callers that don't use it get existing behavior
- Keep the fast-path check as lightweight as possible (set membership test only)

## Test Targets
- New tests:
  1. `test_fast_path_discard_non_viable`: candle for non-viable symbol → not processed, no IndicatorEngine created
  2. `test_fast_path_pass_viable`: candle for viable symbol → processed normally
  3. `test_no_viable_set_processes_all`: when _viable_universe is None, all symbols processed (backward compat)
  4. `test_set_viable_universe`: method sets the universe correctly
  5. `test_indicator_engine_only_viable`: IndicatorEngine only instantiated for viable symbols
  6. `test_tick_fast_path_discard`: tick events also discarded for non-viable (if applicable)
  7. `test_fast_path_performance`: verify the check adds negligible overhead (optional timing test)
  8. `test_universe_update_event_published`: if UniverseUpdateEvent added, verify it's published
- Minimum: 8 tests
- Command: `python -m pytest tests/data/test_databento_data_service.py -v -k "viable or universe"`

## Definition of Done
- [ ] Fast-path discard implemented in candle processing path
- [ ] IndicatorEngine only created for viable symbols (when set)
- [ ] Backward compatibility when viable_universe is None
- [ ] All existing DatabentoDataService tests pass
- [ ] 8+ new tests passing

## Close-Out
Follow `.claude/skills/close-out.md`.

## Sprint-Level Regression Checklist
R1–R3, R12 (ALL_SYMBOLS mode), R13 (fast-path discard), R14 (viable candles processed), R15 (backward compat).

## Sprint-Level Escalation Criteria
E1: >50μs per candle overhead → ESCALATE. E8: Viable symbol candles lost → ESCALATE. E9: Databento session errors → ESCALATE.
