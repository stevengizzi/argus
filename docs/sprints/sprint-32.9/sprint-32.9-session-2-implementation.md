# Sprint 32.9, Session 2: Margin Circuit Breaker + Intelligence Fix (DEF-141, DEF-142)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md`
   - `argus/execution/order_manager.py` (focus on: order rejection callbacks, `_on_order_rejected()` or equivalent, signal processing flow for new entries)
   - `argus/intelligence/startup.py` (focus on the polling loop — search for variable `symbols`)
   - `config/system_live.yaml`
   - Session 1 close-out: `docs/sprints/sprint-32.9/session-1-closeout.md`
2. Run the scoped test baseline:
   `python -m pytest tests/execution/ tests/intelligence/ -x -q`
   Expected: all passing (full suite confirmed by S1 close-out)
3. Verify you are on branch `main` with Session 1 committed

## Objective
Add a permanent margin rejection circuit breaker that halts new entries when IBKR rejects too many orders for insufficient margin. Fix the intelligence polling crash from an unbound variable.

## Background
On April 2, IBKR rejected 718 orders for "insufficient margin" during the session. Each rejected bracket leg left an orphaned position at IBKR consuming margin, creating a positive feedback loop: more orphaned positions → less margin → more rejections. By 1:24 PM ET, reconciliation showed 200 position mismatches. The system had no awareness it was hitting margin limits.

## Requirements

### 1. Margin rejection tracking

In `order_manager.py`, add instance variables:
```python
self._margin_rejection_count: int = 0
self._margin_circuit_open: bool = False
```

In the order rejection callback (wherever IBKR Error 201 with "Available Funds" or "insufficient" in the message text is handled):
- Increment `_margin_rejection_count`
- If count exceeds `margin_rejection_threshold` (config, default 10) AND `_margin_circuit_open` is False:
  - Set `_margin_circuit_open = True`
  - Log WARNING: `"Margin circuit breaker OPEN — {count} margin rejections this session. New entries blocked until positions clear."`

### 2. Entry gate

Find the code path where new entry orders are submitted to the broker. This is the initial BUY order for a new position — NOT flatten orders, NOT bracket legs (stop/target), NOT amendments.

Before submitting the entry order to IBKR, check `_margin_circuit_open`. If True:
- Do NOT submit to IBKR
- Publish a `SignalRejectedEvent` with:
  - `rejection_stage = "RISK_MANAGER"` (or whichever RejectionStage enum value is appropriate)
  - `rejection_reason = "Margin circuit breaker open — {self._margin_rejection_count} rejections this session"`
- Log INFO: `"Entry blocked by margin circuit breaker: {symbol} for {strategy_id}"`
- Return early — the signal routes to CounterfactualTracker via existing overflow mechanics

**CRITICAL:** The gate must ONLY apply to new entry orders. Flatten orders, bracket leg orders, stop resubmissions, and emergency flattens must ALWAYS bypass the circuit breaker. Verify this by checking the order flow paths.

### 3. Auto-reset

In the poll loop (or reconciliation check), add a periodic check:
- If `_margin_circuit_open` is True:
  - Query current IBKR position count via `broker.get_positions()`
  - If `len(positions) < margin_circuit_reset_positions` (config, default 20):
    - Set `_margin_circuit_open = False`
    - Reset `_margin_rejection_count = 0`
    - Log INFO: `"Margin circuit breaker RESET — position count {n} below threshold {threshold}"`

### 4. Daily reset

At the point where daily state resets (start of new trading day, or wherever `_flattened_today` resets):
- Reset `_margin_rejection_count = 0`
- Reset `_margin_circuit_open = False`

### 5. Config

Add to `OrderManagerConfig`:
- `margin_rejection_threshold: int = 10`
- `margin_circuit_reset_positions: int = 20`

Add corresponding keys to `config/system_live.yaml`.

### 6. DEF-141: Intelligence polling crash

In `argus/intelligence/startup.py`:
- Find the polling loop function (the crash message was: "cannot access local variable 'symbols' where it is not associated with a value" at 17:14:09 UTC)
- The variable `symbols` is used without guaranteed assignment — likely in a conditional path where an exception or early return skips the assignment
- Fix: initialize `symbols` to `[]` (or `None`) at the top of the loop body, before any conditional branches
- Wrap the main polling loop body in a try/except that:
  - Logs ERROR with exc_info=True
  - Continues to the next polling cycle (do NOT re-raise)
  - This prevents a single bad cycle from killing the entire polling task

## Constraints
- Do NOT modify: `eod_flatten()` (Session 1 owns this), strategy files, UI, API routes
- Do NOT change: existing Risk Manager evaluate_signal flow (the margin circuit breaker is in Order Manager, not Risk Manager)
- Do NOT change: bracket leg placement, stop resubmission, flatten order paths
- Preserve: DEC-369 broker-confirmed immunity, existing overflow routing, all existing rejection reasons and stages

## Test Targets
New tests to write:
1. `test_margin_circuit_opens_after_threshold` — simulate 10 margin rejections via mock callbacks, verify `_margin_circuit_open` is True
2. `test_margin_circuit_does_not_open_below_threshold` — simulate 9 rejections, verify circuit stays closed
3. `test_margin_circuit_blocks_new_entries` — set circuit open, attempt new entry order, verify SignalRejectedEvent published and order NOT sent to broker
4. `test_margin_circuit_allows_flatten_orders` — set circuit open, attempt flatten order, verify it goes through to broker
5. `test_margin_circuit_allows_bracket_legs` — set circuit open, attempt stop/target placement, verify it goes through
6. `test_margin_circuit_resets_on_position_drop` — set circuit open with count=15, mock broker.get_positions() returning 10 positions, trigger check, verify circuit resets
7. `test_margin_circuit_daily_reset` — set circuit open, trigger daily reset, verify circuit closed and count zeroed
8. `test_polling_loop_survives_exception` — mock a source that raises, verify polling loop continues

Minimum new test count: 7
Test command: `python -m pytest tests/execution/ tests/intelligence/ -x -q`

## Config Validation
Write a test that loads `config/system_live.yaml` and verifies:
- `margin_rejection_threshold` → OrderManagerConfig field
- `margin_circuit_reset_positions` → OrderManagerConfig field

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| EOD flatten from S1 still works | `python -m pytest tests/execution/test_*eod* tests/execution/test_*flatten* -x -q` |
| Normal entry order flow (circuit closed) | Existing order tests pass |
| Bracket orders never blocked by circuit | New test |
| Flatten orders never blocked by circuit | New test |
| Overflow routing still works | Existing overflow tests |
| Intelligence polling loop starts and runs | New test |

## Definition of Done
- [ ] Margin rejection counter tracking implemented
- [ ] Circuit breaker opens at threshold
- [ ] New entries blocked when circuit open
- [ ] Flatten/bracket orders bypass circuit
- [ ] Auto-reset when positions drop below threshold
- [ ] Daily reset implemented
- [ ] Intelligence polling crash fixed
- [ ] Polling loop wrapped in try/except
- [ ] Config fields added and validated
- [ ] All 7+ new tests passing
- [ ] All existing tests passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.
**Write the close-out report to:** docs/sprints/sprint-32.9/session-2-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: Sprint 32.9 scope
2. Close-out report: docs/sprints/sprint-32.9/session-2-closeout.md
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/execution/ tests/intelligence/ -x -q`
5. Files that should NOT have been modified: anything in `argus/strategies/`, `argus/ui/`, `argus/api/routes/`, `argus/backtest/`

## Session-Specific Review Focus (for @reviewer)
1. **CRITICAL:** Verify circuit breaker ONLY blocks new entry orders — not flattens, brackets, stop resubmissions, or amendments
2. Verify the rejection callback correctly identifies margin-specific Error 201s (not all 201s are margin — check for "Available Funds" or "insufficient" in the message)
3. Verify SignalRejectedEvent from circuit breaker has correct rejection_stage for counterfactual tracking
4. Verify auto-reset actually queries broker positions (not just checking internal state)
5. Verify the `symbols` fix in startup.py doesn't change semantics — just ensures variable is always defined
6. Verify try/except in polling loop logs the actual exception (not silently swallowing)
7. Verify no changes to EOD flatten (Session 1's domain)

## Sprint-Level Escalation Criteria
- Any change to bracket order logic (stops, targets, amendments)
- Any change to how existing positions are managed mid-session
- Any modification to the broker abstraction interface
- Test count drops by more than 5 from baseline
