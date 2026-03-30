# Sprint 28.5: Regression Checklist

> **Revision:** Post-adversarial review (March 29, 2026). AMD-specific checks added.

Run these checks at session close-outs and during Tier 2 reviews.

---

## Core Invariants

- [ ] **Non-opt-in strategy behavior unchanged.** Strategy with no `exit_management:` key in its YAML AND global `trailing_stop.enabled: false` + `escalation.enabled: false` → zero behavioral change in Order Manager tick handling, T1 fill handling, fallback poll, and flatten logic.

- [ ] **BacktestEngine non-trail regression.** Run existing ORB Breakout backtest with current config (no exit management overrides). Results must be bit-identical to pre-sprint. Verify trade count, total P&L, Sharpe, and win rate match.

- [ ] **CounterfactualTracker non-trail regression.** Shadow positions for strategies without exit management config produce identical outcomes.

- [ ] **SignalEvent backward compatibility.** `atr_value` defaults to `None`. All existing code that constructs or destructures SignalEvent works without specifying `atr_value`.

- [ ] **SignalRejectedEvent backward compatibility.** Same as above — `atr_value` field defaults to `None`.

## Order Manager Safety

- [ ] **T1/T2 bracket order flow preserved.** Entry → atomic bracket → T1 fill → stop adjustment → T2 or time stop. Trail additions do not alter the bracket submission sequence.

- [ ] **Stop-to-breakeven still works.** After T1 fill, stop moves to breakeven even when trailing is enabled (trail operates above breakeven).

- [ ] **Broker safety stop not cancelled prematurely.** When trail activates after T1, broker stop at breakeven remains active until trail triggers flatten.

- [ ] **AMD-2: Flatten order-of-operations.** Trail-triggered flatten: (1) check `_flatten_pending`, (2) add to `_flatten_pending`, (3) submit market sell, (4) cancel broker safety stop. NOT the reverse. Verify with a test that the sell is submitted before the cancel.

- [ ] **AMD-3: Escalation failure recovery.** If escalation stop resubmission fails, position is flattened. Verify: cancel old stop → submit new stop fails → `_flatten_position()` called.

- [ ] **AMD-4: shares_remaining > 0 guard.** Trail and escalation exits do not submit sell orders when shares_remaining == 0. Verify with a test where T2 fills all remaining shares, then trail triggers — should be a no-op.

- [ ] **AMD-6: Escalation exempt from retry cap.** Escalation stop updates do not increment `_stop_retry_count`. Verify counter is unchanged after escalation stop update.

- [ ] **AMD-8: _flatten_pending check FIRST.** Trail and escalation exit code checks `_flatten_pending` before any broker interaction. Verify: if flatten already pending, no cancel or sell orders submitted.

- [ ] **Risk Manager not touched.** No imports added to risk_manager.py. No exit-related logic added. DEC-027 preserved.

- [ ] **EOD flatten unconditional.** 15:50 ET flatten works regardless of trail/escalation state.

- [ ] **Flatten-pending guard (DEC-363) covers trail flattens.** Trail-triggered `_flatten_position()` calls go through the same duplicate-prevention path.

- [ ] **Duplicate fill dedup (DEC-374) covers trail scenarios.** If broker safety stop fills while trail flatten is in flight, dedup prevents double-close.

- [ ] **Overflow routing (DEC-375) unaffected.** Overflow-routed signals produce shadow positions with correct trail/escalation state in CounterfactualTracker.

## BacktestEngine Safety

- [ ] **AMD-7: Bar-processing order.** Per bar: (1) effective stop from PRIOR bar's state, (2) evaluate exit, (3) THEN update high watermark and trail state. Verify with specific test: bar high=$52, low=$49, prior trail=$49.50, updated trail=$50.50 → exit at $49.50 (prior state), not $50.50.

- [ ] **CounterfactualTracker same AMD-7 ordering.** Per-bar processing uses the same prior-state-first order as BacktestEngine.

## Config Safety

- [ ] **All keys in `exit_management.yaml` recognized by Pydantic model.** Test: add an unknown key, verify Pydantic raises ValidationError (extra="forbid") or logs warning.

- [ ] **AMD-1: Field-level deep merge.** Strategy `exit_management: { trailing_stop: { atr_multiplier: 3.0 } }` overrides only atr_multiplier; all other trailing_stop fields inherit global defaults. Verify with explicit test.

- [ ] **AMD-5: stop_to enum values.** EscalationPhase accepts "breakeven", "quarter_profit", "half_profit", "three_quarter_profit" and rejects unknown values.

- [ ] **AMD-10: Deprecated config warning.** If `enable_trailing_stop: true` or `trailing_stop_atr_multiplier != 2.0` in order_manager.yaml, startup WARNING is logged. Legacy fields are ignored (new ExitManagementConfig is canonical).

- [ ] **Existing config files unchanged.** `order_manager.yaml`, `risk_limits.yaml`, `system.yaml`, `system_live.yaml` — no modifications.

## ATR Standardization (AMD-9)

- [ ] **ATR(14) on 1-minute bars.** Strategies with IndicatorEngine access emit ATR(14) consistently. Code comments document the ATR source.

- [ ] **AMD-12: Negative/zero ATR guard.** `compute_trailing_stop()` returns None for atr_value ≤ 0 or None. No trail price produced from invalid input.

## Data Integrity

- [ ] **ExitReason values correct.** Trail-triggered exits logged as `ExitReason.TRAILING_STOP`. Escalation-triggered stop exits use appropriate ExitReason.

- [ ] **Trade Logger records trail exits correctly.** Existing `exit_reason` column handles TRAILING_STOP value.

- [ ] **Learning Loop compatible.** OutcomeCollector can read trades with TRAILING_STOP exit reason without error.

## Test Suite Health

- [ ] **Full pytest suite passes (0 failures).** Run with `-n auto` at sprint entry and final close-out.

- [ ] **Full Vitest suite passes (0 failures).**

- [ ] **No new test isolation issues.** New tests pass both in isolation and as part of full suite.
