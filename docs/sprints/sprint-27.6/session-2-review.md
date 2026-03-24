# Sprint 27.6, Session 2 — Tier 2 Review

---BEGIN-REVIEW---

## Verdict: CLEAR

## Spec Compliance

| Spec Item | Status |
|-----------|--------|
| BreadthCalculator class in `argus/core/breadth.py` | PASS |
| Constructor takes `BreadthConfig` | PASS |
| Internal state: `dict[str, deque[float]]` with deque maxlen = `config.ma_period` | PASS |
| `on_candle(event: CandleEvent) -> None` — O(1) per call | PASS |
| `get_breadth_snapshot() -> dict` with correct keys | PASS |
| `universe_breadth_score` = (above - below) / qualifying, range -1.0 to +1.0 | PASS |
| `breadth_thrust` = True when above/qualifying >= thrust_threshold | PASS |
| Returns None when < min_symbols qualify | PASS |
| Symbol qualifies when >= min_bars_for_valid candles in deque | PASS |
| `reset()` clears all state | PASS |
| Memory bounded via deque maxlen | PASS |
| 14+ new tests | PASS (17 tests) |
| No modifications to existing files | PASS |
| No Event Bus subscription in this module | PASS |
| Close-out report written | PASS |

## Session-Specific Focus Areas

### 1. O(1) per-candle update
PASS. `on_candle()` (lines 42-56) does a dict key lookup and a `deque.append()`. No iteration over all symbols. The loop over all symbols only occurs in `get_breadth_snapshot()`, which is called on-demand, not per-candle. This is the correct design per spec.

### 2. Deque maxlen enforced
PASS. Line 55: `deque(maxlen=self._config.ma_period)`. Verified by test `test_deque_maxlen_enforced` which feeds 8 values into a maxlen=5 deque and confirms only the last 5 remain.

### 3. None returned when thresholds not met
PASS. Lines 91-97: when `qualifying_count < self._config.min_symbols`, returns `None` for both `universe_breadth_score` and `breadth_thrust`. Verified by tests: `test_fewer_than_min_symbols_returns_none`, `test_single_symbol_below_min_symbols_returns_none`, `test_empty_universe_returns_none`.

### 4. Field name is `universe_breadth_score`
PASS. The dict key is `"universe_breadth_score"` on lines 93, 102. All tests assert against this exact key name.

### 5. No Event Bus subscription in this module
PASS. Grep for `EventBus`, `event_bus`, and `subscribe` returns zero matches. The module only imports `CandleEvent` (as a type for the `on_candle` method parameter) and `BreadthConfig`. Wiring to the Event Bus is deferred to S6 per spec.

## Code Quality

The implementation is clean and well-structured:

- **Type hints**: Complete on all methods including return types.
- **Docstrings**: Google-style on the class and all public methods.
- **Type validation**: Constructor validates `BreadthConfig` type, `on_candle` validates `CandleEvent` type.
- **`statistics.mean()`**: Reasonable choice for MA computation. Called per-symbol only in `get_breadth_snapshot()`, not per-candle. For 5,000 symbols with deques of 20 floats, this is well within the 1ms budget.
- **Conservative "at MA" handling**: Symbols exactly at their MA count as neither above nor below. This is a sensible choice documented in the close-out.
- **No unnecessary dependencies**: Only stdlib imports (statistics, collections.deque) plus project-internal config and events.

One minor observation: `get_breadth_snapshot()` iterates all tracked symbols (line 78), which is O(N) where N is the number of tracked symbols. This is fine because the spec requires O(1) per *candle* (i.e., `on_candle`), not per snapshot call. The snapshot is called much less frequently (once per regime reclassification cycle, ~300s).

## Test Coverage

17 tests across 11 test classes, exceeding the 14 minimum. Coverage is thorough:

- Construction and type validation (2 tests)
- Per-candle state updates and multi-symbol tracking (3 tests)
- All-above, all-below, and mixed breadth scores (3 tests)
- Thrust true/false/configurable threshold (3 tests)
- Ramp-up: insufficient bars per symbol (1 test)
- Pre-threshold: insufficient qualifying symbols (1 test)
- Memory bounds (1 test)
- Single symbol edge case (1 test)
- Empty universe (1 test)
- Reset (1 test)

Test helpers (`_make_candle`, `_feed_candles`, `_build_calculator`, `_feed_n_rising`, `_feed_n_falling`) are well-factored and make tests readable.

Tests access `calc._symbol_closes` (private attribute) for structural assertions. This is acceptable in tests for verifying internal state correctness.

## Issues Found

None.

## Recommendations

None. The implementation is clean, complete, and matches the spec precisely.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "session": "Sprint 27.6 Session 2",
  "component": "BreadthCalculator",
  "tests_passing": 17,
  "tests_expected": 14,
  "regression_tests_passing": 70,
  "files_created": [
    "argus/core/breadth.py",
    "tests/core/test_breadth.py"
  ],
  "files_modified": [],
  "spec_compliance": "FULL",
  "escalation_triggers": [],
  "concerns": [],
  "notes": "Clean implementation. All 5 session-specific focus areas verified. O(1) per-candle, bounded memory, correct None semantics, correct field naming, no Event Bus subscription."
}
```
