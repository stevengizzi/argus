# Sprint 27.65, Session S2: Trade Correctness + Risk Config

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/project-knowledge.md`
   - `argus/execution/order_manager.py`
   - `argus/core/risk_manager.py`
   - `argus/strategies/orb_base.py`
   - `config/system_live.yaml`
   - `docs/sprints/sprint-27.65/S1-closeout.md` (verify S1 complete)
   - `docs/sprints/sprint-27.65/S1-review.md` (S1 CONCERNS to resolve in R4)
2. Run the test baseline (DEC-328):
   Scoped: `python -m pytest tests/execution/ tests/core/test_risk_manager* tests/strategies/test_orb* -x -q`
   Expected: all passing (full suite confirmed by S1 close-out)
3. Verify you are on the correct branch

## Objective
Fix bracket leg pricing after fill slippage (the ZD -$265 "target hit" bug),
make concurrent position limits optional/disableable for paper trading, add a
zero-R signal guard, and resolve the S1 reviewer's CONCERNS (shutdown sequence
integration test + reconciliation endpoint typing).

## Background
- ZD trade: signal entry=$43.38, actual fill=$43.66 (+28¢ slippage). Target
  limit stayed at $43.42 (below cost basis), so "target hit" was a $265 loss.
- Max concurrent positions (2 per-strategy, 10 cross-strategy) blocked hundreds
  of legitimate signals during the session.
- PDBC signal had entry=$16.86 and target=$16.86 (zero profit potential).
- S1 Tier 2 review returned CONCERNS with 3 follow-up items (see below).

## S1 Reviewer Follow-Ups (CONCERNS Resolution)
The S1 reviewer identified 3 findings. All are picked up in this session:
- **MEDIUM:** Shutdown integration test only mocks broker call, doesn't verify
  ordering (cancel before disconnect) in actual shutdown sequence → R4.1
- **LOW:** Reconciliation endpoint uses `type: ignore[arg-type]` due to
  `dict[str, object]` typing on `_last_reconciliation` → R4.2
- **LOW:** SimulatedBroker `cancel_all_orders()` close-out says "no-op" but
  actually clears `_pending_brackets` — documentation mismatch → R4.3

## Requirements

### R1: Bracket leg amendment after fill slippage
1. In OrderManager, after receiving entry fill confirmation (the callback where
   `Position opened` is logged):
   - Compare `actual_fill_price` vs `signal_entry_price`
   - If they differ by more than a configurable tolerance (default: $0.01):
     a. Compute price delta: `delta = actual_fill_price - signal_entry_price`
     b. Compute new stop: `new_stop = original_stop + delta`
     c. Compute new targets: `new_t1 = original_t1 + delta`, `new_t2 = original_t2 + delta`
     d. Cancel existing bracket legs and resubmit with amended prices
     e. Log at INFO: `"Bracket amended for {symbol}: fill slippage {delta:+.2f}, new stop={new_stop}, new T1={new_t1}"`
   - Safety check: if `new_t1 <= actual_fill_price` for a long (shouldn't happen
     with delta approach, but guard anyway), log ERROR and cancel the position
     with a market order.
2. For SimulatedBroker: slippage is zero, so this path should never trigger.
   Add a guard to skip amendment when `broker_source == BrokerSource.SIMULATED`.

### R2: Make concurrent position limits optional
1. In `RiskManager`, modify the concurrent position check:
   - If `max_concurrent_positions` is `0`, `None`, or not present in config:
     skip the check entirely (no limit)
   - Same for cross-strategy `max_concurrent_positions` in the system-level config
   - Log at startup: `"Per-strategy concurrent position limit: {N or 'disabled'}"`
   - Log at startup: `"Cross-strategy concurrent position limit: {N or 'disabled'}"`
2. Update all strategy YAML configs under `config/strategies/`:
   - Set `max_concurrent_positions: 0` (disabled) in each strategy config
3. Update `config/system_live.yaml`:
   - Set the cross-strategy `max_concurrent_positions: 0` (disabled)
4. Ensure the Pydantic config models accept 0 as valid (may need
   `ge=0` instead of `gt=0` or `Optional[int]` with None meaning disabled)

### R3: Zero-R signal guard
1. In the signal generation path for ORB strategies (likely in `OrbBaseStrategy`
   or the individual strategy's signal emission):
   - After computing entry, stop, and target prices:
   - Guard: if `abs(target - entry) < 0.01` (less than 1 cent of profit potential),
     do not emit the signal
   - Log at DEBUG: `"{symbol}: signal suppressed — zero R (entry={entry}, target={target})"`
2. Apply the same guard in `PatternBasedStrategy` for pattern-based signals.
3. This should be a base-level check, not strategy-specific.

### R4: S1 Reviewer CONCERNS Resolution
1. **Shutdown sequence ordering test (MEDIUM):**
   Add an integration test that verifies the shutdown sequence calls methods
   in the correct order: `broker.cancel_all_orders()` → `order_manager.stop()`
   → `broker.disconnect()`. Approach: mock all three methods, call the shutdown
   sequence (or the relevant portion of `ArgusSystem.stop()`), and assert call
   order using `mock.assert_has_calls()` or by recording call timestamps. This
   test belongs in `test_order_manager_safety.py` alongside the existing
   shutdown tests from S1.

2. **Reconciliation endpoint typing (LOW):**
   Replace `_last_reconciliation: dict[str, object]` in OrderManager with a
   proper typed structure. Options (pick whichever fits cleanest):
   - A `ReconciliationResult` dataclass with `status: str`,
     `discrepancies: list[dict]`, `timestamp: str` fields
   - Or a Pydantic model if it's used in the API response serialization
   Remove the `type: ignore[arg-type]` from `argus/api/routes/positions.py`.

3. **SimulatedBroker close-out accuracy (LOW):**
   Update the S1 close-out report (`docs/sprints/sprint-27.65/S1-closeout.md`)
   to correct the description: SimulatedBroker's `cancel_all_orders()` clears
   `_pending_brackets` (not a no-op). Single line edit. Also update the S1
   review report with a post-review resolution table per the workflow protocol:
   append "### Post-Review Resolution" section, change verdict to
   `CONCERNS_RESOLVED`, add `post_review_fixes` array.

## Constraints
- Do NOT modify: Order Manager's flatten_pending guard logic (from S1)
- Do NOT modify: Risk Manager circuit breakers or daily loss limits
- Do NOT modify: strategy evaluation logic or pattern detection
- Bracket amendment must NOT leave a position without stop protection at any point
  (cancel + resubmit should be atomic or have a fallback)
- The 0-means-disabled convention must not break existing tests that may set
  max_concurrent_positions to specific values
- S1 close-out and review report edits (R4.3) must follow the Post-Review Fix
  Documentation protocol exactly (append sections, update verdict to
  CONCERNS_RESOLVED)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. `test_bracket_amendment_on_slippage` — fill price differs from signal, verify bracket legs updated
  2. `test_bracket_amendment_skipped_when_no_slippage` — fill matches signal, verify no amendment
  3. `test_bracket_amendment_safety_check` — pathological case where amended target < fill, verify position cancelled
  4. `test_bracket_amendment_skipped_for_simulated` — SimulatedBroker, verify no amendment attempt
  5. `test_concurrent_limit_disabled_when_zero` — max=0, verify check skipped, signal approved
  6. `test_concurrent_limit_disabled_when_none` — max=None, same behavior
  7. `test_concurrent_limit_still_works_when_set` — max=5, verify limit still enforced
  8. `test_cross_strategy_limit_disabled` — system max=0, verify no cross-strategy blocking
  9. `test_zero_r_signal_suppressed` — entry=target, verify no signal emitted
  10. `test_normal_r_signal_not_affected` — entry < target, verify signal emitted normally
  11. `test_shutdown_sequence_ordering` — (R4.1) verify cancel_all_orders → order_manager.stop → broker.disconnect ordering
  12. `test_reconciliation_result_typed` — (R4.2) verify ReconciliationResult fields, no type: ignore in endpoint
- Minimum new test count: 12
- Test command: `python -m pytest tests/ --ignore=tests/test_main.py -x -q -n auto`

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Normal bracket orders still placed correctly | Existing bracket order tests pass |
| Stop-loss still fires and closes position | Existing stop tests pass |
| Risk Manager still enforces concentration limits | Existing concentration tests pass |
| Risk Manager still enforces daily loss limit | Existing circuit breaker tests pass |
| SimulatedBroker backtest path unaffected | Existing backtest tests pass |
| Config models accept 0 for concurrent limits | New config validation test |
| S1 flatten_pending guard still works | Existing S1 tests pass (no modifications to guard logic) |
| Reconciliation endpoint still works | Existing S1 reconciliation tests pass with new typed model |
| S1 close-out has Post-Review Fixes section | File inspection |
| S1 review verdict is CONCERNS_RESOLVED | JSON verdict inspection |

## Definition of Done
- [ ] Bracket amendment on slippage implemented and tested
- [ ] Concurrent position limits made optional (0 = disabled)
- [ ] Strategy and system configs updated for paper trading
- [ ] Zero-R signal guard added
- [ ] S1 CONCERNS resolved: shutdown ordering test, typed reconciliation, close-out/review updated
- [ ] All existing tests pass
- [ ] 12+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
Write close-out to: `docs/sprints/sprint-27.65/S2-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After close-out, invoke @reviewer with:
1. Review context: `docs/sprints/sprint-27.65/review-context.md`
2. Close-out path: `docs/sprints/sprint-27.65/S2-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/execution/ tests/core/test_risk_manager* tests/strategies/ -x -q`
5. Files NOT to modify: `argus/core/event_bus.py`, `argus/analytics/`, `argus/ai/`

Write review to: `docs/sprints/sprint-27.65/S2-review.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify bracket amendment never leaves a position without stop protection
2. Verify amendment uses delta-based approach (not absolute replacement)
3. Verify max_concurrent=0 truly skips the check, doesn't treat 0 as "allow 0"
4. Verify zero-R guard uses absolute value and handles both long and short sides
5. Verify existing backtest configs are not affected by config changes
6. Check for race condition between entry fill and bracket amendment
7. Verify shutdown ordering test actually asserts call sequence (R4.1)
8. Verify `type: ignore` removed from reconciliation endpoint (R4.2)
9. Verify S1 close-out and review report updated per Post-Review Fix protocol (R4.3)
10. Confirm S1 review verdict changed to CONCERNS_RESOLVED with post_review_fixes array