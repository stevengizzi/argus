# Sprint 32.9, Session 1: EOD Flatten + Startup Zombie Fix (DEF-139, DEF-140)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md`
   - `docs/project-knowledge.md` (search for "eod_flatten", "flatten_pending", "DEF-140", "DEF-139")
   - `argus/execution/order_manager.py` (focus on: `eod_flatten()` at ~line 1466, reconstruction at ~line 1615, `_flatten_unknown_position()` at ~line 1665, `_drain_startup_flatten_queue()` at ~line 1720, `_flatten_position()`)
   - `argus/models/trading.py` (confirm `Position` model uses `shares: int`, NOT `qty`)
   - `argus/execution/ibkr_broker.py` (confirm `get_positions()` returns `Position` objects with `shares` attribute)
   - `config/system_live.yaml`
2. Run the test baseline:
   Full suite: `python -m pytest --ignore=tests/test_main.py -n auto -q`
   Expected: ~4,539 tests, all passing
3. Verify you are on branch `main`

## Objective
Fix the `"qty"` → `"shares"` attribute mismatch that silently breaks both startup zombie cleanup (DEF-139) and EOD Pass 2 broker-only cleanup (DEF-140). Then make `eod_flatten()` wait for fill verification before declaring completion.

## Background — Root Cause Analysis

The `Position` model (`argus/models/trading.py`) defines `shares: int = Field(ge=1)`. IBKRBroker's `get_positions()` returns `Position` objects with `shares` as the quantity attribute.

Two code paths in `order_manager.py` read `getattr(pos, "qty", 0)` instead of `getattr(pos, "shares", 0)`. Since `Position` has no `qty` attribute, `getattr` always returns the default `0`.

**Impact on DEF-139 (startup zombie flatten):**
In `_reconstruct_from_broker()` (~line 1627), `qty` is always 0. Every zombie hits the `abs(qty) <= 0` guard → "Skipping flatten for zero-quantity position" (DEBUG log) → zombie is counted as "handled" but never flattened or queued. The startup flatten queue receives 0 entries. The "44 zombies handled" log is misleading — zero were actually processed.

**Impact on DEF-140 (EOD Pass 2):**
In `eod_flatten()` Pass 2 (~line 1499), `qty` is always 0. Every broker-only position fails `if qty > 0` → silently skipped. Pass 2 has been broken since Sprint 29.5 when it was added.

## Requirements

### 1. Fix `"qty"` → `"shares"` attribute mismatch (ROOT CAUSE)

a) In `_reconstruct_from_broker()` (~line 1627):
   - Change: `qty = int(getattr(pos, "qty", 0))`
   - To: `qty = int(getattr(pos, "shares", 0))`

b) In `eod_flatten()` Pass 2 (~line 1499):
   - Change: `qty = int(getattr(pos, "qty", 0))`
   - To: `qty = int(getattr(pos, "shares", 0))`

c) Search the ENTIRE `order_manager.py` file for any other occurrences of `getattr(pos, "qty"` or `getattr(pos, 'qty'` and fix them all.

### 2. Synchronous EOD flatten with fill verification

Refactor `eod_flatten()` to wait for results:

a) **Pass 1 — Managed positions** (existing scope with verification):
   - Before submitting flatten orders, create an `asyncio.Event` per symbol being flattened.
   - After submitting all flatten orders, wait for fill/reject/cancel callbacks with timeout (`eod_flatten_timeout_seconds`, default 30s).
   - Implementation: collect all symbols being flattened into a dict `{symbol: asyncio.Event()}`. In the fill/reject/cancel callback paths (wherever `_flatten_pending` is cleared for a symbol), set the corresponding event. Use `asyncio.wait_for(asyncio.gather(*[event.wait() for event in events.values()]), timeout=timeout)`.
   - For rejected orders: if `eod_flatten_retry_rejected` is True, retry ONCE with re-queried IBKR position qty.
   - Track results: `{filled: list[str], rejected: list[str], timed_out: list[str]}`
   - Log: `"EOD flatten Pass 1: {n_filled} filled, {n_rejected} rejected, {n_timed_out} timed out"`

b) **Pass 2 — Broker-only cleanup** (now functional with `"shares"` fix):
   - After Pass 1 verification, call `broker.get_positions()`
   - Identify symbols at IBKR not in `_managed_positions` and not in Pass 1 filled list
   - Submit MARKET SELL for each orphan
   - Wait for callbacks with same timeout
   - Log: `"EOD flatten Pass 2: {n_orphans} broker-only positions, {n_filled} filled, {n_rejected} rejected"`

c) **Post-flatten verification:**
   - After both passes, query `broker.get_positions()` one final time
   - If positions remain: log CRITICAL with count and symbol list
   - Move auto-shutdown timer start to AFTER verification completes

### 3. Config additions
Add to `OrderManagerConfig`:
- `eod_flatten_timeout_seconds: int = 30`
- `eod_flatten_retry_rejected: bool = True`

Add corresponding keys to `config/system_live.yaml` under the order_manager section.

### 4. Startup flatten queue drain verification
With the `"shares"` fix in reconstruction, zombies will now be properly queued in `_startup_flatten_queue` when ARGUS boots pre-market. Verify:
- The queue is populated with (symbol, shares) tuples during reconstruction
- The poll loop drain check at `now_et2.time() >= time(9, 30)` fires correctly
- `_drain_startup_flatten_queue()` submits SELL orders for each queued position

Add a log message in reconstruction when a zombie IS queued: change the existing "Queued startup flatten for..." message to INFO level (it may currently be at DEBUG).

## Constraints
- Do NOT modify: strategy files, data service, UI code, API routes, broker abstraction interface
- Do NOT change: order placement logic for non-EOD orders, bracket management, mid-session flatten logic (`_flatten_pending`)
- Preserve: `_flatten_abandoned` set behavior, flatten circuit breaker, DEC-369 broker-confirmed immunity
- The `"shares"` fix must be backward-compatible: `getattr` with default 0 handles any edge case where the attribute doesn't exist

## Test Targets
New tests to write:
1. `test_reconstruction_reads_shares_attribute` — create Position with shares=100, pass to reconstruction, verify qty is read as 100 (not 0)
2. `test_eod_pass2_reads_shares_attribute` — create Position with shares=50, pass to EOD Pass 2, verify SELL order placed for 50 shares
3. `test_reconstruction_queues_zombies_premarket` — boot at 9:15 AM with zombie positions, verify `_startup_flatten_queue` populated
4. `test_startup_queue_drains_at_market_open` — populate queue, advance clock past 9:30, verify SELL orders submitted
5. `test_eod_flatten_waits_for_fills` — submit flatten orders, mock broker fills, verify function waits for callbacks before returning
6. `test_eod_pass2_discovers_orphans` — mock broker.get_positions() returns positions not in _managed_positions, verify SELL orders placed
7. `test_eod_flatten_retries_rejected` — mock first attempt rejected, verify retry
8. `test_eod_flatten_timeout` — mock order that never resolves, verify function returns after timeout
9. `test_auto_shutdown_after_verification` — verify shutdown timer starts after verification

Minimum new test count: 8
Test command: `python -m pytest tests/execution/ -x -q`

## Config Validation
Write a test that loads `config/system_live.yaml` and verifies:
- `eod_flatten_timeout_seconds` → OrderManagerConfig field
- `eod_flatten_retry_rejected` → OrderManagerConfig field

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Non-EOD flatten still works (time_stop, trail) | Existing flatten tests pass |
| `_flatten_pending` mechanism unchanged for mid-session | Existing tests |
| Bracket management unchanged | Existing bracket tests |
| SimulatedBroker path still works | Existing backtest tests |
| No other uses of `getattr(pos, "qty"` remain in codebase | `grep -rn '"qty"' argus/execution/` |

## Definition of Done
- [ ] `"qty"` → `"shares"` fixed in reconstruction AND eod_flatten Pass 2
- [ ] No other `getattr(pos, "qty"` occurrences in codebase
- [ ] eod_flatten waits for fill verification before declaring complete
- [ ] Pass 2 discovers and flattens broker-only positions
- [ ] Auto-shutdown timer starts after verification
- [ ] Config fields added and validated
- [ ] All 8+ new tests passing
- [ ] All existing tests passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.
**Write the close-out report to:** docs/sprints/sprint-32.9/session-1-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: Sprint 32.9 scope (this implementation prompt)
2. Close-out report: docs/sprints/sprint-32.9/session-1-closeout.md
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/execution/ -x -q`
5. Files that should NOT have been modified: anything in `argus/strategies/`, `argus/ui/`, `argus/api/routes/`, `argus/data/`

## Session-Specific Review Focus (for @reviewer)
1. **CRITICAL:** Verify ALL occurrences of `getattr(pos, "qty"` are changed to `getattr(pos, "shares"` — grep the entire codebase
2. Verify eod_flatten() awaits fill/reject callbacks before publishing ShutdownRequestedEvent
3. Verify Pass 2 queries broker positions AFTER Pass 1 verification completes
4. Verify retry logic re-queries IBKR position qty before resubmitting
5. Verify timeout path returns cleanly (no orphaned asyncio tasks)
6. Verify startup flatten queue is populated during reconstruction when `"shares"` fix is in place
7. Verify no changes to mid-session flatten logic

## Sprint-Level Escalation Criteria
- Any change to bracket order logic (stops, targets, amendments)
- Any change to how existing positions are managed mid-session
- Any modification to the broker abstraction interface
- Test count drops by more than 5 from baseline
