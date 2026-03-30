# Sprint 28.5: Adversarial Review Input Package

This document provides all context needed for the adversarial review. The reviewer should also receive the Sprint Spec and Specification by Contradiction as separate documents.

---

## Why This Sprint Warrants Adversarial Review

1. **Order Manager is the most safety-critical component.** It manages position lifecycle for what will eventually be real money. Every exit logic change is a potential source of unexpected position closure or, worse, failure to close.
2. **Fill model alignment affects all historical validation.** Changes to how BacktestEngine and CounterfactualTracker handle exits affect the reliability of all learning data.
3. **The T1→trail transition is a state machine change.** New state: entry → T1 fill → trailing stop (with escalation) → trail trigger or time stop. State transitions are where bugs hide.
4. **IBKR bracket interaction.** The belt-and-suspenders pattern (server trail + broker safety stop) has subtle failure modes.

---

## Architecture Context

### Order Manager (`execution/order_manager.py`, ~1800 lines)

Position management is event-driven. The Order Manager subscribes to OrderApprovedEvent, OrderFilledEvent, OrderCancelledEvent, and TickEvent.

**Current exit flow:**
1. `on_approved()` → submit atomic bracket order (entry + stop + T1 + optional T2) via `place_bracket_order()`
2. Entry fills → `_handle_entry_fill()` creates ManagedPosition with stop_price, t1_price, t2_price, high_watermark, time_stop_seconds
3. T1 fills → `_handle_t1_fill()` cancels old stop, submits new stop at breakeven (if `enable_stop_to_breakeven: true`), updates position state
4. T2 fills → `_handle_t2_fill()` cancels stop, closes position
5. Stop fills → `_handle_stop_fill()` closes position
6. `on_tick()` → updates high_watermark, checks trailing stop (currently disabled), checks T2 price, publishes P&L updates
7. Fallback poll (5s) → checks time stops, EOD flatten

**Current trailing stop skeleton (disabled by default):**
```python
# In on_tick():
if self._config.enable_trailing_stop and position.t1_filled:
    trail_distance = (
        position.high_watermark
        * self._config.trailing_stop_atr_multiplier
        * 0.01  # Simplified: use % instead of ATR for V1
    )
    trailing_stop_price = position.high_watermark - trail_distance
    if event.price <= trailing_stop_price:
        await self._flatten_position(position, reason="trailing_stop")
```

**Key safety mechanisms already in place:**
- `_flatten_pending` guard (DEC-363) — prevents duplicate flatten orders per symbol
- Duplicate fill dedup (DEC-374) — `_last_fill_state` tracks cumulative_qty
- Stop resubmission cap (DEC-372) — exponential backoff, flatten on exhaustion
- Bracket revision-rejected handling (DEC-373) — fresh order on rejection
- Bracket amendment on fill slippage (DEC-366) — delta-based price correction

**ManagedPosition data model:**
```python
@dataclass
class ManagedPosition:
    position_id: str
    strategy_id: str
    symbol: str
    entry_price: float
    entry_time: datetime
    shares_total: int
    shares_remaining: int
    stop_price: float
    original_stop_price: float  # Never changes
    t1_price: float
    t1_shares: int
    t1_filled: bool = False
    t2_price: float
    high_watermark: float
    stop_order_id: str | None = None
    t1_order_id: str | None = None
    t2_order_id: str | None = None
    realized_pnl: float = 0.0
    time_stop_seconds: int | None = None
    bracket_stop_order_id: str | None = None
    bracket_t1_order_id: str | None = None
    bracket_t2_order_id: str | None = None
```

**Sprint 28.5 proposes adding to ManagedPosition:**
- `trail_active: bool = False`
- `trail_stop_price: float = 0.0`
- `escalation_phase_index: int = -1`
- `exit_config: ExitManagementConfig | None = None`
- `atr_value: float | None = None`

### Risk Manager (`core/risk_manager.py`)

**Critical constraint (DEC-027):** Risk Manager approve-with-modification model. Permitted: reduce share count, tighten profit targets. **Prohibited: widen stops, change entry price, change side.** All exit management is Order Manager's responsibility. Sprint 28.5 does not modify Risk Manager.

### Shared Fill Model (`core/fill_model.py`)

Stateless pure functions used by both BacktestEngine and CounterfactualTracker:

```python
def evaluate_bar_exit(
    bar_high, bar_low, bar_close,
    stop_price, target_price, time_stop_expired
) -> ExitResult | None
```

Priority: stop > target > time_stop (worst-case-for-longs).

**Sprint 28.5 does NOT modify this file.** New exit math functions go in a separate `exit_math.py`. BacktestEngine and CounterfactualTracker compute trail/escalation stops externally, then pass the tightest stop to `evaluate_bar_exit()`.

### BacktestEngine (`backtest/engine.py`)

Bar-level fill model. Per position per bar: check stops, check targets, check time stops. Uses `evaluate_bar_exit()` from fill_model.py.

Sprint 28.5 adds: per-position trail state (high_watermark updates from bar.high, trail stop computation via exit_math), escalation state (phase tracking based on elapsed bars), effective stop selection (max of original, trail, escalation), pass effective stop to existing evaluate_bar_exit().

### CounterfactualTracker (`intelligence/counterfactual.py`)

Shadow position monitoring via CandleEvent subscription. Same fill model as BacktestEngine. Backfills from IntradayCandleStore on position open.

Sprint 28.5 adds: same trail/escalation state as BacktestEngine, applied per bar via exit_math functions.

### Broker Abstraction (`execution/broker.py`)

ABC with `place_bracket_order()`, `cancel_order()`, `modify_order()`. IBKRBroker uses native IBKR bracket linkage with transmit-flag pattern for atomic submission.

**Sprint 28.5 does not change the broker interface.** Trail uses the existing `_flatten_position()` → cancel stops → market sell pattern. Escalation uses the existing cancel-and-resubmit stop pattern.

---

## Key Decisions Constraining This Sprint

### DEC-027 | Risk Manager Modification Behavior
RM never modifies stops or entry. All exit management is Order Manager's responsibility.

### DEC-117 | Atomic Bracket Orders
Entry + stop + T1 + T2 submitted atomically. Sprint 28.5 modifies behavior *after* bracket is placed and T1 fills, not during bracket submission.

### DEC-122 | Per-Signal Time Stop
`time_stop_seconds` on SignalEvent carried to ManagedPosition. Escalation is defined relative to this value.

### DEC-363 | Flatten-Pending Guard
`_flatten_pending: dict[str, str]` prevents duplicate flatten orders. Trail-triggered flattens must go through this guard.

### DEC-366 | Bracket Leg Amendment on Fill Slippage
After entry fill, if slippage > $0.01, cancel and resubmit bracket legs with delta-shifted prices. Trail activation happens *after* this amendment (on T1 fill, not entry fill).

### DEC-372 | Stop Resubmission Cap
`stop_cancel_retry_max` (default 3) with exponential backoff. Escalation stop updates use the same cancel-and-resubmit pattern — must they respect this cap? (Reviewers: consider this.)

### DEC-373 | Bracket Revision-Rejected Handling
Fresh order on "Revision rejected" from IBKR. Escalation stop updates may hit the same rejection pattern.

### DEC-374 | Duplicate Fill Dedup
`_last_fill_state` dedup. Must handle: trail triggers flatten, but broker safety stop at breakeven also fills before cancel completes.

### DEC-375 | Overflow Routing
Overflow signals route to CounterfactualTracker as shadow positions. These shadow positions should receive trail/escalation treatment.

---

## Proposed Design: Belt-and-Suspenders Pattern

```
Entry → Atomic Bracket (entry + stop + T1 + T2)
    ↓
Entry Fills → ManagedPosition created
    ↓ (if slippage > $0.01)
Bracket Amendment (DEC-366)
    ↓
T1 Fills → 
    ├── Partial exit recorded (50% of shares)
    ├── Cancel old stop (was for full position)
    ├── Submit breakeven stop for remaining shares (BROKER — crash protection)
    └── Activate server-side trail (if trailing_stop.enabled)
    ↓
on_tick() loop:
    ├── Update high_watermark
    ├── Compute trail_stop = exit_math.compute_trailing_stop(high_watermark, atr_value, config)
    ├── Compute escalation_stop = exit_math.compute_escalation_stop(...)  [if in poll loop]
    ├── effective_stop = max(original_stop, trail_stop, escalation_stop)
    ├── If price ≤ effective_stop:
    │   ├── Cancel broker safety stop
    │   └── Flatten remaining shares (market sell)
    └── If price ≥ T2 (and no broker T2 order): flatten
    ↓
If server crashes:
    └── Broker safety stop at breakeven protects remaining shares
```

**Key questions for adversarial review:**

1. **Race condition: trail flatten vs broker safety stop.** Trail triggers flatten → market sell submitted → but broker safety stop also fills before cancel completes. DEC-374 dedup should catch the duplicate fill, but verify: does the `_flatten_pending` guard prevent the market sell if the safety stop filled first?

2. **Escalation stop update frequency.** Escalation is checked in the fallback poll (5s interval). If an escalation phase triggers, we cancel the current broker stop and submit a new one at the escalation level. This uses the same cancel-and-resubmit pattern as T1→breakeven. Does the stop resubmission cap (DEC-372) apply? Should escalation resets count against the cap? My recommendation: escalation stop updates should NOT count against the retry cap — they're intentional changes, not retry loops.

3. **Trail + escalation + original stop priority.** Three sources of stop price: original (from signal), trail (ratchets up from high_watermark), escalation (ratchets up from time phases). `compute_effective_stop()` takes max of all three. Is this always correct? Could there be a case where escalation should override trail (or vice versa)?

4. **Trail activation with `"immediate"` mode + active T1/T2 brackets.** If trail activates at entry (before T1), the trail could trigger a flatten while T1 and T2 limit orders are still active at the broker. The flatten would need to cancel T1, T2, and stop before placing the market sell. Is this handled by the existing cancel-all-then-flatten pattern in `_flatten_position()`?

5. **BacktestEngine fill model change.** Currently `evaluate_bar_exit()` receives a single stop_price. With trailing, the effective stop changes each bar. The proposal is to compute the effective stop externally and pass it to `evaluate_bar_exit()`. This means the fill model doesn't know about trailing — it just sees a (potentially different) stop each bar. Is this sufficient, or does the bar-level fill model need to consider that the stop moved *during* the bar?

6. **Config merge semantics.** Per-strategy `exit_management:` overrides global defaults. The proposal is a simple top-level key merge (strategy trailing_stop overrides entire global trailing_stop). Should it be field-level merge instead (strategy `trailing_stop.atr_multiplier` overrides just that field, inheriting other trailing_stop fields from global)?

---

## Existing Test Coverage Context

- Full suite: ~3,845 pytest + 680 Vitest, 0 failures
- Order Manager tests: `tests/unit/execution/test_order_manager.py` (~60 tests covering bracket flow, T1/T2 fills, stop management, EOD flatten, flatten-pending guard, dedup, overflow routing)
- BacktestEngine tests: `tests/unit/backtest/test_engine.py` (~40 tests)
- CounterfactualTracker tests: `tests/unit/intelligence/test_counterfactual.py` (~30 tests)
- Fill model tests: `tests/unit/core/test_fill_model.py` (~10 tests)
