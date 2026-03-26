# Sprint 27.95, Session 3b: Overflow Routing Logic

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/main.py` (or `server.py`) — find `_process_signal()` method, understand current flow: signal → quality pipeline → risk manager → order placement
   - `argus/execution/order_manager.py` — position tracking, how to get current position count
   - `argus/core/events.py` — SignalRejectedEvent, RejectionStage.BROKER_OVERFLOW (added in 3a)
   - `argus/config/` — OverflowConfig (added in 3a)
   - `argus/intelligence/counterfactual.py` — `_on_signal_rejected()` handler to understand what fields SignalRejectedEvent needs
2. Run scoped test baseline:
   ```bash
   python -m pytest tests/test_main* tests/execution/ tests/core/ -x -q
   ```
   Expected: all passing (full suite confirmed by Session 3a close-out)
3. Verify all prior sessions committed

## Objective
Add the overflow position count check in `_process_signal()`. When real IBKR positions reach `broker_capacity`, route new approved signals to CounterfactualTracker by publishing `SignalRejectedEvent` with `RejectionStage.BROKER_OVERFLOW`.

## Requirements

1. **In `_process_signal()`**, after Risk Manager approval and before order placement, add the overflow check:

   ```python
   # Overflow check — after RM approval, before order placement
   if (self._broker_source != BrokerSource.SIMULATED
       and self._overflow_config.enabled
       and self._order_manager.active_position_count >= self._overflow_config.broker_capacity):
       # Route to counterfactual tracking instead of broker
       self._publish_signal_rejected(
           signal=signal_event,
           stage=RejectionStage.BROKER_OVERFLOW,
           reason=f"Broker capacity reached ({self._order_manager.active_position_count}/{self._overflow_config.broker_capacity})",
           quality_score=quality_score,  # from quality pipeline
           quality_grade=quality_grade,
           regime_vector=current_regime_vector,
       )
       return
   ```

2. **Expose position count from OrderManager:**
   - Add a property or method `active_position_count` (or equivalent) to OrderManager that returns `len(self._positions)` — the count of real (non-counterfactual) positions
   - If such a property already exists, use it. If not, add it.

3. **Wire OverflowConfig into the main application:**
   - Load `OverflowConfig` from SystemConfig during initialization
   - Store as instance variable accessible in `_process_signal()`

4. **Publish SignalRejectedEvent with correct fields:**
   - The event must have all fields that CounterfactualTracker's `_on_signal_rejected()` expects
   - Include: signal data (symbol, entry, stop, target, strategy), rejection stage, reason string, quality metadata, regime vector snapshot
   - Follow the exact same pattern used for QUALITY_FILTER, POSITION_SIZER, and RISK_MANAGER rejections (find existing `_publish_signal_rejected` calls or equivalent)

5. **Add logging:**
   - Log INFO "Signal overflow to counterfactual: {strategy} {symbol} ({count}/{capacity} positions)" — use ThrottledLogger if available to avoid log spam

## Constraints
- Do NOT modify: `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/ai/`, `argus/data/`, `argus/intelligence/counterfactual.py` (core logic)
- Do NOT change: Quality Engine scoring, Risk Manager gating, signal generation, CounterfactualTracker internals
- The overflow check MUST be after Risk Manager approval — the signal is fully qualified, just capacity-limited
- Do NOT move or reorder existing pipeline steps (quality → RM → [NEW: overflow] → order placement)
- BrokerSource.SIMULATED MUST bypass the overflow check entirely (backtest engine must not be affected)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write (~6):
  1. Position count below capacity → signal proceeds to order placement normally
  2. Position count at capacity (==) → signal routed to overflow (SignalRejectedEvent published)
  3. Position count above capacity (>) → signal routed to overflow
  4. BrokerSource.SIMULATED → overflow check skipped, signal proceeds normally even above capacity
  5. overflow.enabled=false → overflow check skipped
  6. SignalRejectedEvent has correct stage=BROKER_OVERFLOW, reason contains count/capacity, signal data populated
- Minimum new test count: 6
- Test command: `python -m pytest tests/test_main* tests/execution/ tests/core/ -x -q`

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass
- [ ] 6+ new tests written and passing
- [ ] Overflow check is demonstrably AFTER RM approval in code flow
- [ ] BrokerSource.SIMULATED bypass confirmed
- [ ] Close-out report written to `docs/sprints/sprint-27.95/session-3b-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| _process_signal() flow order preserved | Read code: quality → RM → overflow → order placement |
| Quality pipeline unchanged | Run quality engine tests |
| Risk Manager gating unchanged | Run risk manager tests |
| Order placement for sub-capacity signals unchanged | Test with position count = 0 |
| BacktestEngine unaffected | Verify SIMULATED bypass |

## Close-Out
Follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.
**Write the close-out report to:** `docs/sprints/sprint-27.95/session-3b-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-27.95/review-context.md`
2. Close-out report: `docs/sprints/sprint-27.95/session-3b-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/test_main* tests/execution/ tests/core/ -x -q`
5. Files NOT modified: `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/intelligence/counterfactual.py`, `argus/data/`

Review report: `docs/sprints/sprint-27.95/session-3b-review.md`

## Post-Review Fix Documentation
If CONCERNS reported and fixed, update both close-out and review files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify overflow check is AFTER Risk Manager approval (not before — signals must be fully qualified)
2. Verify overflow check is BEFORE order placement (not after — no IBKR orders for overflow signals)
3. Verify BrokerSource.SIMULATED bypass is unconditional (no edge cases)
4. Verify SignalRejectedEvent fields match what CounterfactualTracker expects (check _on_signal_rejected signature)
5. Verify position count source is real positions only (not counterfactual shadow positions)
6. Verify no modification to existing rejection paths (quality filter, sizer, RM)

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Signal pipeline flow order preserved (quality → RM → overflow → order)
- [ ] Quality Engine unchanged
- [ ] Risk Manager unchanged
- [ ] BacktestEngine unaffected (SIMULATED bypass)
- [ ] Existing rejection paths unchanged
- [ ] Full test suite passes, no hangs

## Sprint-Level Escalation Criteria (for @reviewer)
1. Overflow routing blocks signals that should reach broker → halt, investigate
2. _process_signal() flow change breaks quality pipeline or RM → halt, escalate
3. Signal count divergence after modification → halt
