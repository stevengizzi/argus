# Sprint 32.9 Session 2 — Close-Out Report

**DEF-141 (Intelligence polling crash) + DEF-142 (Reconciliation qty→shares) + Margin Circuit Breaker**

---

## Change Manifest

### Production Code

**`argus/core/config.py`**
- Added to `OrderManagerConfig`:
  - `margin_rejection_threshold: int = Field(default=10, ge=1)`
  - `margin_circuit_reset_positions: int = Field(default=20, ge=1)`

**`config/order_manager.yaml`**
- Added:
  - `margin_rejection_threshold: 10`
  - `margin_circuit_reset_positions: 20`

**`argus/execution/order_manager.py`**
- Added import: `SignalRejectedEvent` from `argus.core.events`
- Added instance variables in `__init__`:
  - `self._margin_rejection_count: int = 0`
  - `self._margin_circuit_open: bool = False`
- Added margin rejection detection in `on_cancel()`:
  - Only for `order_type == "entry"` (bracket legs and flattens excluded)
  - Checks `reason.lower()` for "available funds" or "insufficient"
  - Increments counter; opens circuit at threshold with WARNING log
- Added entry gate in `on_approved()` (before `place_bracket_order`):
  - If `_margin_circuit_open`: publishes `SignalRejectedEvent`, logs INFO, returns early
  - Does NOT affect flatten, stop resubmission, bracket amendments, or EOD flatten paths
- Added auto-reset in `_poll_loop()` (before time-stop loop):
  - When circuit open: queries `broker.get_positions()`, resets if count < threshold
  - Wrapped in `try/except` to prevent reset check failure from crashing the loop
- Added daily reset in `reset_daily_state()`:
  - `self._margin_rejection_count = 0`
  - `self._margin_circuit_open = False`

**`argus/intelligence/startup.py`** (DEF-141 fix)
- In `run_polling_loop()`, inside `async with poll_lock:` try block:
  - Added `symbols: list[str] = []` initialization before the `if firehose:` branch
  - Fixes `UnboundLocalError` crash when `firehose=True` and `asyncio.TimeoutError` fires
    (timeout handler referenced `symbols` which was only assigned in the `else:` branch)
- Changed `except Exception as e: logger.error(...)` → added `exc_info=True` for full traceback

**`argus/main.py`** (DEF-142 fix)
- In `_run_position_reconciliation()` loop (~line 1400):
  - Changed `getattr(pos, "qty", 0)` → `getattr(pos, "shares", 0)`
  - This was silently building an empty `broker_positions` dict (every position had qty=0),
    causing `reconcile_positions()` to always see zero broker positions

### Test Files

**`tests/execution/test_order_manager_sprint329.py`** (12 new tests appended)
- `TestConfigValidation::test_order_manager_yaml_has_margin_circuit_fields`: YAML has new fields
- `TestMarginCircuitOpens` (3 tests):
  - Opens after threshold (10 rejections, "Available Funds" message)
  - Stays closed below threshold (9 rejections)
  - Non-margin cancellations (e.g., "Revision rejected") do not increment counter
- `TestMarginCircuitGate` (3 tests):
  - Blocks new entries when open (no broker call, `SignalRejectedEvent` published)
  - Allows flatten orders (bypass via `_flatten_position` → `place_order` directly)
  - Allows bracket-leg-adjacent paths (`close_position` → `place_order` directly)
- `TestMarginCircuitReset` (3 tests):
  - Resets when position count drops below threshold (poll loop integration)
  - Does NOT reset when position count still above threshold
  - Daily reset clears both fields
- `TestPollingLoopSurvivesException` (1 test):
  - Polling loop catches exception, continues, and calls `run_poll` a second time
- `TestReconciliationReadsSharesNotQty` (1 test):
  - Code inspection: `main.py` reads `pos.shares`, not `pos.qty`

---

## Judgment Calls

1. **Gate in `on_approved()`, not Risk Manager**: The spec explicitly states "the margin circuit breaker is in Order Manager, not Risk Manager". Placement is correct — the gate checks `_margin_circuit_open` before `place_bracket_order`.

2. **Only `order_type == "entry"` triggers the counter**: The spec says "only track entry orders". In `on_cancel()`, when an order is cancelled and the pending order's `order_type` is `"entry"`, the reason is checked for margin text. Stop/target/flatten cancellations are intentionally excluded from the counter.

3. **`rejection_stage = "RISK_MANAGER"` for the `SignalRejectedEvent`**: The spec says "rejection_stage = 'RISK_MANAGER' (or whichever RejectionStage enum value is appropriate)". Since the margin gate is in Order Manager (which sits after the Risk Manager in the pipeline), `RISK_MANAGER` is the closest semantic match to the existing rejection stages. The counterfactual tracker receives it via the same path as other risk-manager-stage rejections.

4. **Polling loop test uses `asyncio.sleep(0)` in `bad_poll`**: With `interval=1` and a tight async loop, the event waiter needs explicit yield points inside `bad_poll` to process between iterations. The `await asyncio.sleep(0)` is a standard asyncio yield idiom and does not change the semantics of the test. Without it, the test hung indefinitely due to the event loop not processing the `loop_ran_twice.set()` callback before the next iteration began.

5. **`main.py` variable renamed from `qty` to `qty` (still named `qty`)**: The variable `qty` holds the result of `getattr(pos, "shares", 0)` — the variable name was not changed, only the attribute being read. This preserves the existing code structure while fixing the root cause.

---

## Scope Verification

| Requirement | Status |
|-------------|--------|
| `_margin_rejection_count` instance variable | ✅ |
| `_margin_circuit_open` instance variable | ✅ |
| Rejection detection in `on_cancel()` — entry orders only | ✅ |
| Threshold check opens circuit with WARNING log | ✅ |
| Entry gate in `on_approved()` before `place_bracket_order` | ✅ |
| `SignalRejectedEvent` published when gate blocks entry | ✅ |
| Flatten/bracket/stop paths NOT gated | ✅ |
| Auto-reset in `_poll_loop()` via broker position count | ✅ |
| Daily reset in `reset_daily_state()` | ✅ |
| Config fields `margin_rejection_threshold` and `margin_circuit_reset_positions` | ✅ |
| YAML fields in `config/order_manager.yaml` | ✅ |
| DEF-141: `symbols` initialized before `if firehose:` | ✅ |
| DEF-141: `except Exception` logs `exc_info=True` | ✅ |
| DEF-142: `main.py` reconciliation reads `pos.shares` | ✅ |
| No remaining `getattr(pos, "qty"` in `argus/` for Position objects | ✅ |
| 8+ new tests | ✅ (12 new tests) |
| All existing tests passing | ✅ |
| No changes to strategy files, UI, API routes, backtest | ✅ |

---

## Regression Checklist

| Check | Result |
|-------|--------|
| EOD flatten from S1 | ✅ All `tests/execution/` pass |
| Signal cutoff from S3 | ✅ `tests/core/test_signal_cutoff.py` passes |
| Quality config from S3 | ✅ `tests/intelligence/test_quality_config.py` passes |
| Normal entry order flow (circuit closed) | ✅ Existing order tests pass |
| Bracket orders never blocked by circuit | ✅ New test confirms |
| Flatten orders never blocked by circuit | ✅ New test confirms |
| Overflow routing still works | ✅ `tests/test_overflow_routing.py` passes |
| Intelligence polling loop starts and runs | ✅ New test confirms |
| `getattr(pos, "qty"` grep — only Order object reads remain | ✅ Confirmed one instance (`order_manager.py:1971` reads from Order, not Position) |

---

## Test Results

- New tests: **12 passing** (appended to `tests/execution/test_order_manager_sprint329.py`)
- File total: **25 passing** (13 from S1 + 12 from S2)
- Full suite: **4,579 passing, 0 failing** (up from 4,566 before session, +13 net)

---

## Post-Review Fixes

**F2 resolved (from Tier 2 review):** `rejection_stage` in `on_approved()` was `"RISK_MANAGER"` (uppercase). The `RejectionStage` StrEnum values are lowercase (`"risk_manager"`). Fixed to `"risk_manager"` in the gate and corrected the corresponding test assertion. Without this fix, the `CounterfactualTracker` would silently drop margin-rejected signals due to `ValueError` in the enum construction.

---

## Self-Assessment

**CLEAN**

All spec requirements met. Margin circuit breaker correctly gates only new entries; flatten/bracket paths are unchanged. DEF-141 and DEF-142 fixes are minimal and correct. Test count increased by 12. No regressions.

---

## Context State

**GREEN** — Session completed well within context limits.
