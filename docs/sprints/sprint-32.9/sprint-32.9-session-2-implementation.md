# Sprint 32.9, Session 2: Margin Circuit Breaker + Intelligence Fix + Reconciliation Fix (DEF-141, DEF-142)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md`
   - `argus/execution/order_manager.py` (focus on: order rejection callbacks, `_on_order_rejected()` or equivalent, signal processing flow for new entries)
   - `argus/intelligence/startup.py` (focus on the polling loop — search for variable `symbols`)
   - `argus/main.py` (~line 1399 — reconciliation loop with `getattr(pos, "qty", 0)`)
   - `config/system_live.yaml`
   - Session 1 close-out: `docs/sprints/sprint-32.9/session-1-closeout.md`
   - Session 3 close-out: `docs/sprints/sprint-32.9/session-3-closeout.md`
   (S2 runs after S1 and S3 have been merged.)
2. Run the scoped test baseline:
   `python -m pytest tests/execution/ tests/intelligence/ -x -q`
   Expected: all passing (full suite confirmed by S1 and S3 close-outs)
3. Verify you are on branch `main` with Sessions 1 and 3 committed

## Objective
Add a permanent margin rejection circuit breaker that halts new entries when IBKR rejects too many orders for insufficient margin. Fix the intelligence polling crash from an unbound variable. Fix the last remaining `"qty"` → `"shares"` attribute mismatch in the reconciliation loop.

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

Add corresponding keys to `config/order_manager.yaml` (this is where OrderManagerConfig fields live — NOT system_live.yaml, per S1's judgment call #2).

### 6. DEF-141: Intelligence polling crash

In `argus/intelligence/startup.py`:
- Find the polling loop function (the crash message was: "cannot access local variable 'symbols' where it is not associated with a value" at 17:14:09 UTC)
- The variable `symbols` is used without guaranteed assignment — likely in a conditional path where an exception or early return skips the assignment
- Fix: initialize `symbols` to `[]` (or `None`) at the top of the loop body, before any conditional branches
- Wrap the main polling loop body in a try/except that:
  - Logs ERROR with exc_info=True
  - Continues to the next polling cycle (do NOT re-raise)
  - This prevents a single bad cycle from killing the entire polling task

### 7. S1 deferred item: main.py reconciliation `qty` → `shares` fix

In `argus/main.py` (~line 1399), the reconciliation loop reads:
```python
qty = float(getattr(pos, "qty", 0))
```

This has the same root cause as the S1 fixes — `Position` model uses `shares`, not `qty`. The result is that `broker_positions` dict is always empty (every position has qty=0, fails the `qty != 0` check), meaning `reconcile_positions()` receives no broker data.

Fix: change to `float(getattr(pos, "shares", 0))`.

This is the last known instance of the `qty` attribute mismatch in the entire codebase. After this fix, grep the full `argus/` directory to confirm zero remaining `getattr(.*"qty"` reads from Position objects (note: `getattr(order, "qty"` in order_manager.py line ~1909 reads from an Order object and is correct — leave it).

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
9. `test_reconciliation_reads_shares_not_qty` — verify main.py reconciliation loop reads `shares` attribute and builds non-empty broker_positions dict

Minimum new test count: 8
Test command (FINAL SESSION — full suite): `python -m pytest --ignore=tests/test_main.py -n auto -q`

## Config Validation
Write a test that loads `config/order_manager.yaml` and verifies:
- `margin_rejection_threshold` → OrderManagerConfig field
- `margin_circuit_reset_positions` → OrderManagerConfig field

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| EOD flatten from S1 still works | `python -m pytest tests/execution/test_*sprint329* -x -q` |
| Signal cutoff from S3 still works | `python -m pytest tests/core/test_signal_cutoff.py -x -q` |
| Quality engine from S3 still works | `python -m pytest tests/intelligence/test_quality_config.py -x -q` |
| Normal entry order flow (circuit closed) | Existing order tests pass |
| Bracket orders never blocked by circuit | New test |
| Flatten orders never blocked by circuit | New test |
| Overflow routing still works | Existing overflow tests |
| Intelligence polling loop starts and runs | New test |
| No `getattr(pos/bp, "qty"` remaining for Position objects | `grep -rn '"qty"' argus/` and verify only Order reads remain |

## Definition of Done
- [ ] Margin rejection counter tracking implemented
- [ ] Circuit breaker opens at threshold
- [ ] New entries blocked when circuit open
- [ ] Flatten/bracket orders bypass circuit
- [ ] Auto-reset when positions drop below threshold
- [ ] Daily reset implemented
- [ ] Intelligence polling crash fixed
- [ ] Polling loop wrapped in try/except
- [ ] main.py reconciliation `qty` → `shares` fixed
- [ ] No remaining Position-object `qty` reads in codebase
- [ ] Config fields added and validated
- [ ] All 8+ new tests passing
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
4. Test command (FINAL SESSION — full suite): `python -m pytest --ignore=tests/test_main.py -n auto -q`
5. Files that should NOT have been modified: anything in `argus/strategies/`, `argus/ui/`, `argus/api/routes/`, `argus/backtest/`

## Session-Specific Review Focus (for @reviewer)
1. **CRITICAL:** Verify circuit breaker ONLY blocks new entry orders — not flattens, brackets, stop resubmissions, or amendments
2. Verify the rejection callback correctly identifies margin-specific Error 201s (not all 201s are margin — check for "Available Funds" or "insufficient" in the message)
3. Verify SignalRejectedEvent from circuit breaker has correct rejection_stage for counterfactual tracking
4. Verify auto-reset actually queries broker positions (not just checking internal state)
5. Verify the `symbols` fix in startup.py doesn't change semantics — just ensures variable is always defined
6. Verify try/except in polling loop logs the actual exception (not silently swallowing)
7. Verify no changes to EOD flatten (Session 1's domain)
8. Verify main.py reconciliation now reads `shares` and grep confirms no remaining Position-object `qty` reads
9. Verify all S1 and S3 changes still work (full suite pass as final session)

## Sprint-Level Escalation Criteria
- Any change to bracket order logic (stops, targets, amendments)
- Any change to how existing positions are managed mid-session
- Any modification to the broker abstraction interface
- Test count drops by more than 5 from baseline