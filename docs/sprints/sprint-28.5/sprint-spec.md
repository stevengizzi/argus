# Sprint 28.5: Exit Management

> **Revision:** Post-adversarial review (March 29, 2026). 12 amendments incorporated (AMD-1 through AMD-12).

## Goal

Deliver configurable, per-strategy exit management to the Order Manager, BacktestEngine, and CounterfactualTracker — trailing stops (ATR/percent/fixed), partial profit-taking with trail on T1 remainder, and time-based exit escalation (progressive stop tightening) — so that ARGUS can capture more profit on winning trades and reduce give-back on extended holds.

## Scope

### Deliverables

1. **Exit math pure functions** (`argus/core/exit_math.py`) — Stateless computation library for trailing stop price, escalation stop price, and effective stop (max of all stop sources). Shared by Order Manager, BacktestEngine, and CounterfactualTracker. Same design pattern as `core/fill_model.py`.

2. **Exit management config system** (`config/exit_management.yaml` + Pydantic models) — Global defaults for trailing stop and escalation parameters. Per-strategy overrides via `exit_management:` key in strategy YAMLs with **field-level deep merge** (AMD-1). Config-gated: both trailing and escalation default to `enabled: false`.

3. **SignalEvent `atr_value` field** — `atr_value: float | None = None` on SignalEvent and SignalRejectedEvent. All 7 strategies emit ATR(14) on 1-minute bars via IndicatorEngine for consistency (AMD-9). Strategies without IndicatorEngine ATR access emit `atr_value=None` and trail falls back to percent mode. Backward compatible (None default).

4. **Order Manager trailing stop engine** — Upgrade the existing disabled trailing stop skeleton in `on_tick()` to a full implementation using exit_math. Per-strategy config lookup. Three trail types: ATR-based, percent-based, fixed-distance. Configurable activation trigger (after T1, after profit %, immediate). Belt-and-suspenders: server-side trail operates above broker safety stop at breakeven. Flatten order: sell first, cancel safety stop second (AMD-2).

5. **Order Manager time-based exit escalation** — Progressive stop tightening as hold time increases, defined as phases relative to `time_stop_seconds`. Phases evaluated in the fallback poll loop. Escalation inactive when signal has no time_stop. Compatible with trailing stop (effective stop = max of trail, escalation, and broker safety stop). Escalation stop updates exempt from DEC-372 retry cap (AMD-6).

6. **BacktestEngine trail/escalation alignment** — Trail and escalation state per BacktestPosition. Per bar: compute effective stop from PRIOR bar's state, evaluate exit, THEN update high watermark and trail state for next bar (AMD-7). Existing non-trail behavior unchanged.

7. **CounterfactualTracker trail/escalation alignment** — Trail and escalation state per ShadowPosition. Same per-bar logic as BacktestEngine (AMD-7 ordering). Existing non-trail behavior unchanged.

### Acceptance Criteria

1. **Exit math pure functions:**
   - `compute_trailing_stop(high_watermark, atr_value, config)` returns correct trail price for all three types (ATR, percent, fixed)
   - Returns None when trailing is disabled or ATR is None/zero/negative with ATR type selected (AMD-12). Negative ATR is invalid input and must not produce a trail price.
   - Falls back to percent-based trail if `atr_value` is None and `config.type == "atr"` but `config.percent > 0`
   - `compute_escalation_stop(entry_price, high_watermark, current_price, elapsed_seconds, time_stop_seconds, config)` returns correct stop for each phase. `high_watermark` is used as the dynamic profit reference for all profit-based phases (AMD-5).
   - Returns None when escalation is disabled or time_stop_seconds is None
   - `compute_effective_stop(original_stop, trail_stop, escalation_stop)` returns the tightest (highest for longs) non-None value
   - `min_trail_distance` floor enforced — trail never tighter than this value below high watermark
   - All functions are pure (no side effects, no I/O, no state)
   - **`stop_to` enum values and formulas (AMD-5):**

     | Value | Formula | Description |
     |-------|---------|-------------|
     | `"breakeven"` | `entry_price` | Lock in zero loss |
     | `"quarter_profit"` | `entry_price + 0.25 × (high_watermark - entry_price)` | Lock in 25% of unrealized gain |
     | `"half_profit"` | `entry_price + 0.50 × (high_watermark - entry_price)` | Lock in 50% of unrealized gain |
     | `"three_quarter_profit"` | `entry_price + 0.75 × (high_watermark - entry_price)` | Lock in 75% of unrealized gain |

     All profit-based values reference `high_watermark` (dynamic, tracks position's best price), not T1/T2 targets (static).

2. **Exit management config system:**
   - `config/exit_management.yaml` loads without error and all fields map to Pydantic model fields
   - No silently ignored keys (test: add unknown key, verify Pydantic raises or warns)
   - **Per-strategy override uses field-level deep merge (AMD-1):** a strategy's `trailing_stop.atr_multiplier: 3.0` overrides only that field; all other `trailing_stop` fields inherit from the global `exit_management.yaml`. This matches the `risk_overrides` pattern (DEC-359). Implementation: load global config as base dict, `deep_update()` with strategy-specific dict, then validate merged result via Pydantic.
   - **Merge example:** Global config has `trailing_stop.atr_multiplier: 2.5`, `trailing_stop.percent: 0.02`. Strategy YAML has `exit_management: { trailing_stop: { atr_multiplier: 3.0 } }`. Merged result: `atr_multiplier=3.0`, `percent=0.02` (inherited). Strategy does NOT need to repeat fields it doesn't want to change.
   - Validation: `atr_multiplier > 0`, `0 < percent <= 0.2`, `fixed_distance > 0`, `0 < elapsed_pct <= 1.0`, phases sorted by elapsed_pct ascending
   - **Deprecated config warning (AMD-10):** At startup, if legacy `enable_trailing_stop` is `true` or `trailing_stop_atr_multiplier` differs from its default (2.0), log a WARNING: "Legacy trailing stop config detected (enable_trailing_stop / trailing_stop_atr_multiplier). These fields are deprecated — use config/exit_management.yaml instead. Legacy fields are ignored."

3. **SignalEvent `atr_value` field:**
   - Field exists with `None` default — existing code unaffected
   - **ATR standardization (AMD-9):** All strategies emit ATR(14) computed on 1-minute bars via IndicatorEngine for consistency. If a strategy does not have access to IndicatorEngine ATR (e.g., PatternBasedStrategy), it emits `atr_value=None` and the trail falls back to percent-based mode. Document the ATR source in each strategy's signal emission code comment.
   - At least ORB Breakout, VWAP Reclaim, and Afternoon Momentum emit non-None `atr_value`
   - All 7 strategies emit `atr_value` (may be None for strategies without ATR computation — they use percent fallback)

4. **Order Manager trailing stop engine:**
   - Trailing stop activates after T1 fill when `trailing_stop.enabled: true` for that strategy
   - Trail price updates on every tick via `compute_trailing_stop()` using position's high watermark
   - Position flattens when tick price ≤ trail stop price
   - Broker safety stop remains at breakeven — not cancelled when trail activates
   - **Trail-triggered flatten order of operations (AMD-2):** (1) Check `_flatten_pending` guard — if already pending for this symbol, the trail exit is a complete no-op: no cancellations, no submissions, no state changes (AMD-8); (2) add symbol to `_flatten_pending`; (3) submit market sell for remaining shares; (4) cancel broker safety stop. If broker safety stop fills before cancel completes, DEC-374 dedup handles the double fill. This order minimizes the naked-position window on server crash.
   - **`shares_remaining > 0` guard (AMD-4):** Trail-triggered exits verify `position.shares_remaining > 0` before submitting any sell order. If shares_remaining is 0 (e.g., T2 filled during the same tick), the trail exit is a no-op and trail state is cleared.
   - Strategy with `trailing_stop.enabled: false` → identical behavior to pre-sprint (breakeven stop after T1, no trail)
   - `activation: "after_profit_pct"` → trail activates only after unrealized P&L exceeds threshold
   - `activation: "immediate"` → trail activates at entry (no T1 prerequisite)

5. **Order Manager time-based exit escalation:**
   - Escalation phases evaluated in fallback poll loop (5-second interval)
   - At each phase boundary: stop ratchets to specified level per AMD-5 formulas (breakeven, quarter_profit, half_profit, three_quarter_profit)
   - Escalation-adjusted stop submitted to broker as new stop order (cancel old, submit new)
   - **Escalation stop update failure recovery (AMD-3):** If escalation stop resubmission fails (broker rejects or no acknowledgment within 5s), Order Manager immediately attempts to flatten the position via `_flatten_position()`. Escalation stop update failures logged at ERROR level with position ID, attempted stop price, and broker response.
   - **Escalation updates exempt from DEC-372 retry cap (AMD-6):** Escalation uses a single-attempt submit: cancel old stop → submit new stop. If the new stop submission fails, trigger AMD-3 recovery (flatten). The DEC-372 retry cap and exponential backoff apply only to connectivity-failure retry loops, not to intentional stop price changes.
   - **`shares_remaining > 0` guard (AMD-4):** Escalation-triggered exits verify `position.shares_remaining > 0` before submitting any sell order. If shares_remaining is 0, the escalation exit is a no-op and escalation state is cleared.
   - **`_flatten_pending` check first (AMD-8):** Escalation-triggered exits MUST check `_flatten_pending[symbol]` as the FIRST step. Complete no-op if flatten already pending.
   - Escalation inactive when `time_stop_seconds` is None on the signal
   - Escalation inactive when `escalation.enabled: false`
   - Effective stop = max(original_stop, trail_stop, escalation_stop, broker_safety_stop)

6. **BacktestEngine trail/escalation alignment:**
   - BacktestPosition carries trail/escalation state (high_watermark, trail_active, escalation_phase)
   - **Bar-processing order (AMD-7):** Per bar: (1) compute effective stop from PRIOR bar's trail/escalation state; (2) pass effective stop to `evaluate_bar_exit()` against current bar's high/low/close; (3) if not exited: update high_watermark from current bar's high, recompute trail stop for next bar, advance escalation phase if applicable. This preserves worst-case-for-longs semantics — the stop used for exit evaluation never incorporates the current bar's high watermark.
   - **AMD-7 regression test:** Bar with high=$52, low=$49 where prior trail stop=$49.50 and updated trail (from $52 high) would be $50.50. Exit triggers at $49.50 (prior state), NOT $50.50 (updated state). Verify exit price uses prior-bar trail.
   - Strategy without exit management config → BacktestEngine produces bit-identical results to pre-sprint
   - Strategy with trailing stop → BacktestEngine correctly simulates trail activation, trail price updates, and trail-triggered exits

7. **CounterfactualTracker trail/escalation alignment:**
   - ShadowPosition carries trail/escalation state
   - Per-bar logic identical to BacktestEngine — same AMD-7 bar-processing order (both use exit_math)
   - Shadow positions for non-trail strategies → identical behavior to pre-sprint

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| `on_tick()` latency increase | < 5μs per tick | Profile with existing tick volume (~8,000 symbols) |
| BacktestEngine per-bar overhead | < 1μs per bar per position | Profile single-strategy backtest |
| Config loading | < 50ms | Startup timing logs |

No significant performance impact expected — exit_math functions are simple arithmetic, and trailing/escalation checks are O(1) per position per tick/bar.

### Config Changes

New file `config/exit_management.yaml`:

| YAML Path | Pydantic Model | Field Name | Default | Notes |
|-----------|---------------|------------|---------|-------|
| `trailing_stop.enabled` | `TrailingStopConfig` | `enabled` | `false` | |
| `trailing_stop.type` | `TrailingStopConfig` | `type` | `"atr"` | |
| `trailing_stop.atr_multiplier` | `TrailingStopConfig` | `atr_multiplier` | `2.5` | Must be > 0 |
| `trailing_stop.percent` | `TrailingStopConfig` | `percent` | `0.02` | Must be > 0, ≤ 0.2 |
| `trailing_stop.fixed_distance` | `TrailingStopConfig` | `fixed_distance` | `0.50` | Must be > 0 |
| `trailing_stop.activation` | `TrailingStopConfig` | `activation` | `"after_t1"` | |
| `trailing_stop.activation_profit_pct` | `TrailingStopConfig` | `activation_profit_pct` | `0.005` | |
| `trailing_stop.min_trail_distance` | `TrailingStopConfig` | `min_trail_distance` | `0.05` | Default $0.05 calibrated for $5–$200 range (AMD-11). Per-strategy override for stocks outside this range. |
| `escalation.enabled` | `ExitEscalationConfig` | `enabled` | `false` | |
| `escalation.phases` | `ExitEscalationConfig` | `phases` | `[]` | |
| `escalation.phases[].elapsed_pct` | `EscalationPhase` | `elapsed_pct` | — (required) | Must be > 0, ≤ 1.0 |
| `escalation.phases[].stop_to` | `EscalationPhase` | `stop_to` | — (required) | Enum: `"breakeven"`, `"quarter_profit"`, `"half_profit"`, `"three_quarter_profit"` (AMD-5) |

**`stop_to` enum definitions (AMD-5):**

| Value | Formula (longs) | Description |
|-------|-----------------|-------------|
| `"breakeven"` | `entry_price` | Lock in zero loss |
| `"quarter_profit"` | `entry_price + 0.25 × (high_watermark - entry_price)` | Lock in 25% of unrealized gain |
| `"half_profit"` | `entry_price + 0.50 × (high_watermark - entry_price)` | Lock in 50% of unrealized gain |
| `"three_quarter_profit"` | `entry_price + 0.75 × (high_watermark - entry_price)` | Lock in 75% of unrealized gain |

All profit-based values reference `high_watermark` (dynamic), not T1/T2 targets (static).

New field on `SignalEvent` and `SignalRejectedEvent`:

| Field | Type | Default |
|-------|------|---------|
| `atr_value` | `float \| None` | `None` |

**Per-strategy override with field-level deep merge (AMD-1):** `exit_management:` key in each strategy YAML uses same structure as global. Merged via `deep_update()` over global defaults, then validated via Pydantic. Strategy only specifies fields it wants to change — unspecified fields inherit from global.

## Dependencies

- Sprint 28 (Learning Loop V1) complete ✅
- Post-sprint test triage complete (0 failures) ✅
- IntradayCandleStore operational (Sprint 27.65) ✅ — used by CounterfactualTracker backfill
- CounterfactualTracker operational (Sprint 27.7) ✅
- BacktestEngine operational (Sprint 27) ✅
- TheoreticalFillModel in `core/fill_model.py` (Sprint 27.7) ✅ — stays unchanged, exit_math supplements it

## Relevant Decisions

- **DEC-027:** Risk Manager approve-with-modification — never modify stops or entry. All exit management is Order Manager's responsibility. This sprint does not change Risk Manager behavior.
- **DEC-039:** T1/T2 split as separate orders. Sprint 28.5 adds trail logic after T1 fill but preserves the T1/T2 order structure.
- **DEC-117:** Atomic bracket orders. Bracket structure unchanged; trail operates on the stop leg after T1.
- **DEC-122:** Per-signal time stops. Escalation is defined relative to these time stops.
- **DEC-363:** Flatten-pending guard. Trail and escalation exits must check this FIRST before any broker interaction (AMD-8).
- **DEC-366:** Bracket leg amendment on fill slippage. Trail stop updates use the same cancel-and-resubmit pattern.
- **DEC-372/373:** Stop resubmission cap + revision-rejected handling. Escalation stop updates are exempt from the retry cap (AMD-6) — they are intentional scheduled transitions, not connectivity retries.
- **DEC-374:** Duplicate fill dedup. Handles race condition where broker safety stop fills while trail flatten is in flight. AMD-2 order-of-operations (sell first, cancel second) makes this the expected failure mode rather than the dangerous one (naked position).
- **DEC-375:** Overflow routing. Shadow positions from overflow also get trail/escalation in CounterfactualTracker.

## Relevant Risks

- **RSK-022:** IBKR Gateway nightly resets. Trail state is in-memory (ManagedPosition). Gateway reset during a trailing position could cause the broker safety stop to be the only protection. Acceptable: breakeven stop is the belt, trail is the suspenders.
- **Bracket order race conditions:** Cancel-and-resubmit of escalation-adjusted stops has the same risks as existing stop management (DEC-372/373). Mitigated by AMD-3 recovery (flatten on failure) and AMD-6 (escalation exempt from retry cap).
- **Backtest result interpretation:** Strategies with trailing stops enabled will produce different backtest results than without. Must clearly document that trail-enabled backtests are not comparable to non-trail backtests for the same strategy.
- **Escalation stop update failure (AMD-3):** If cancel-and-resubmit fails, position could be left without broker stop. Mitigated by immediate flatten attempt on failure.

## Session Count Estimate

6 sessions + 1 contingency (S5f). Linear dependency chain. Estimated ~58–68 new tests. The split is driven by Order Manager complexity (safety-critical, ~1800 lines) and the protocol requirement to keep compaction scores below 14.
