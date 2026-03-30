# Sprint 28.5, Session S4b: Order Manager — Trailing Stop + Escalation Logic

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/execution/order_manager.py` (on_tick, _handle_t1_fill, _flatten_position, fallback poll, _flatten_pending, _stop_retry_count)
   - `argus/core/exit_math.py` (compute_trailing_stop, compute_escalation_stop, compute_effective_stop)
   - `argus/core/config.py` (ExitManagementConfig, TrailingStopConfig, ExitEscalationConfig)
   - `config/exit_management.yaml`
2. Run scoped test baseline:
   ```
   python -m pytest tests/unit/execution/test_order_manager*.py -x -q
   ```
3. Verify branch: `sprint-28.5`

## Objective
Upgrade `on_tick()` trailing stop logic to use exit_math, modify `_handle_t1_fill()` to activate trail, add escalation checks to fallback poll loop. This is the safety-critical session — implement AMD-2, AMD-3, AMD-4, AMD-6, AMD-8.

## Requirements

### 1. Trail Activation in _handle_t1_fill()
After T1 fills (in `_handle_t1_fill()`), after moving stop to breakeven:
- If `position.exit_config` is not None and `position.exit_config.trailing_stop.enabled` is True:
  - If `activation == "after_t1"`: set `position.trail_active = True`
  - Compute initial trail stop: `compute_trailing_stop(position.high_watermark, position.atr_value, ...unpacked config...)`
  - Set `position.trail_stop_price` to the result (or 0.0 if None)
- The broker safety stop at breakeven remains (belt-and-suspenders). Trail operates above it.

### 2. Trail Check in on_tick()
Replace the existing disabled trailing stop skeleton with:
```python
# After high_watermark update:
if position.trail_active and position.exit_config:
    trail_cfg = position.exit_config.trailing_stop
    new_trail = compute_trailing_stop(
        position.high_watermark, position.atr_value,
        trail_type=trail_cfg.type, atr_multiplier=trail_cfg.atr_multiplier,
        trail_percent=trail_cfg.percent, fixed_distance=trail_cfg.fixed_distance,
        min_trail_distance=trail_cfg.min_trail_distance, enabled=trail_cfg.enabled,
    )
    if new_trail is not None:
        position.trail_stop_price = max(position.trail_stop_price, new_trail)  # Ratchet up only
    
    effective_stop = compute_effective_stop(
        position.stop_price, position.trail_stop_price or None,
        None  # escalation checked in poll loop
    )
    if event.price <= effective_stop:
        await self._trail_flatten(position)
```

### 3. Trail Flatten (_trail_flatten) — AMD-2, AMD-4, AMD-8
Create a `_trail_flatten(position)` method:
```
Step 1 (AMD-8): Check _flatten_pending[symbol]. If already pending → complete no-op. Return immediately.
                No cancellations, no submissions, no state changes.
Step 2 (AMD-4): Check position.shares_remaining > 0. If zero → no-op, clear trail state. Return.
Step 3: Add symbol to _flatten_pending with a new order_id.
Step 4 (AMD-2): Submit market sell for shares_remaining. (SELL FIRST)
Step 5 (AMD-2): Cancel broker safety stop order. (CANCEL SECOND)
```
If broker safety stop fills before cancel (DEC-374 dedup handles double fill).
Log at INFO: "Trail stop triggered for {symbol}: trail={trail_stop_price}, price={current_price}"

### 4. Trail Activation Modes
- `"after_t1"` (default): trail activates in _handle_t1_fill as described above
- `"after_profit_pct"`: in on_tick, if `trail_active` is False and profit exceeds threshold:
  ```python
  unrealized_pct = (event.price - position.entry_price) / position.entry_price
  if unrealized_pct >= position.exit_config.trailing_stop.activation_profit_pct:
      position.trail_active = True
  ```
- `"immediate"`: trail activates at entry (set trail_active=True in _handle_entry_fill when exit_config has immediate activation)

### 5. Escalation in Fallback Poll Loop — AMD-3, AMD-6, AMD-8
In the fallback poll loop (the 5-second interval task), after existing time stop checks:
```python
if position.exit_config and position.exit_config.escalation.enabled:
    elapsed = (now - position.entry_time).total_seconds()
    esc_stop = compute_escalation_stop(
        position.entry_price, position.high_watermark,
        elapsed, position.time_stop_seconds,
        ...unpacked escalation config...
    )
    if esc_stop is not None:
        effective = compute_effective_stop(position.stop_price, 
                                           position.trail_stop_price or None, esc_stop)
        # Only update broker stop if effective stop is higher than current broker stop
        if effective > position.stop_price:
            # AMD-8: Check _flatten_pending first
            if symbol in self._flatten_pending:
                continue  # Skip, flatten already in flight
            # AMD-6: Do NOT count against stop_cancel_retry_max
            await self._escalation_update_stop(position, effective)
```

### 6. Escalation Stop Update (_escalation_update_stop) — AMD-3, AMD-6
```
1. Cancel current broker stop order
2. Submit new stop at escalation price (single attempt — NOT through retry loop)
3. If submission fails (AMD-3): log ERROR with position_id, attempted price, broker response.
   Immediately call _flatten_position(position, reason="escalation_failure")
4. Update position.stop_price to new effective stop
5. Do NOT increment _stop_retry_count (AMD-6)
```

## Constraints
- Do NOT modify fill_model.py or risk_manager.py
- Do NOT change bracket order submission (on_approved)
- Do NOT change existing T2 check logic in on_tick (T2 coexists with trail)
- Do NOT change EOD flatten behavior
- Preserve ALL existing behavior for positions where exit_config is None or trail/escalation disabled
- _flatten_pending guard from DEC-363 must cover all new flatten paths

## Test Targets
- New test file: `tests/unit/execution/test_order_manager_exit_management.py`
- Minimum new test count: 15
- Tests:
  1. Trail activates on T1 fill when trailing_stop.enabled=true
  2. Trail does NOT activate when trailing_stop.enabled=false
  3. Trail price updates on tick (high watermark up → trail ratchets up)
  4. Trail price only ratchets up (never decreases)
  5. Position flattens when price ≤ trail stop
  6. **AMD-2:** Flatten submits market sell BEFORE cancelling broker safety stop
  7. **AMD-4:** Trail flatten skipped when shares_remaining == 0
  8. **AMD-8:** Trail flatten is complete no-op when _flatten_pending already set
  9. Escalation phase triggers at correct elapsed_pct
  10. Escalation updates broker stop (cancel old, submit new)
  11. **AMD-3:** Escalation stop resubmission failure → _flatten_position called
  12. **AMD-6:** Escalation stop update does NOT increment _stop_retry_count
  13. Effective stop = max(original, trail, escalation)
  14. Strategy with no exit_config → identical behavior to pre-sprint
  15. activation="after_profit_pct" — trail activates only after threshold
- Test command: `python -m pytest tests/unit/execution/test_order_manager_exit_management.py tests/unit/execution/test_order_manager.py -x -q -v`

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Non-trail positions unchanged | Existing OM tests pass (positions without exit_config) |
| T1/T2 bracket flow preserved | Existing T1/T2 tests pass |
| EOD flatten still works | Existing EOD flatten tests pass |
| _flatten_pending covers trail path | AMD-8 test |
| DEC-374 dedup still works | Existing dedup tests pass |
| _stop_retry_count unaffected by escalation | AMD-6 test |

## Definition of Done
- [ ] Trail activation in _handle_t1_fill (after_t1 mode)
- [ ] Trail check in on_tick using exit_math
- [ ] _trail_flatten with AMD-2 order (sell first, cancel second)
- [ ] AMD-4 shares_remaining > 0 guard
- [ ] AMD-8 _flatten_pending check FIRST
- [ ] Escalation in fallback poll loop
- [ ] AMD-3 escalation failure recovery (flatten)
- [ ] AMD-6 escalation exempt from retry cap
- [ ] after_profit_pct and immediate activation modes
- [ ] 15+ new tests passing
- [ ] All existing OM tests passing
- [ ] Close-out written to `docs/sprints/sprint-28.5/session-S4b-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.
The close-out report MUST include a structured JSON appendix fenced with ```json:structured-closeout.
**Write to:** `docs/sprints/sprint-28.5/session-S4b-closeout.md`

## Tier 2 Review
1. Review context: `docs/sprints/sprint-28.5/review-context.md`
2. Close-out: `docs/sprints/sprint-28.5/session-S4b-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test: `python -m pytest tests/unit/execution/test_order_manager_exit_management.py tests/unit/execution/test_order_manager.py -x -q -v`
5. Files NOT to modify: fill_model.py, risk_manager.py, on_approved bracket submission

## Session-Specific Review Focus (for @reviewer)
1. **CRITICAL: AMD-2 order-of-operations.** Verify _trail_flatten submits sell BEFORE cancelling safety stop. This is the #1 safety-critical requirement.
2. **CRITICAL: AMD-8.** Verify _flatten_pending check is the absolute FIRST thing in _trail_flatten and escalation update paths — before ANY broker calls.
3. **AMD-3:** Verify escalation failure triggers flatten, not silent failure.
4. **AMD-4:** Verify shares_remaining guard prevents sell of 0 shares.
5. **AMD-6:** Verify escalation path does not touch _stop_retry_count.
6. Verify non-trail positions (exit_config=None) have zero behavioral change.
7. Verify trail only ratchets up (high watermark → trail price is monotonically non-decreasing).
8. Verify T2 check still works alongside trail (both coexist in on_tick).

## Sprint-Level Regression Checklist
[See review-context.md — full checklist]

## Sprint-Level Escalation Criteria
[See review-context.md — full criteria]
