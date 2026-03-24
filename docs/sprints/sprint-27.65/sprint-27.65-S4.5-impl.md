# Sprint 27.65, Session S4.5: Final Integration + Carry-Forward Fixes

## Dependency Note
This is the final session of Sprint 27.65. It requires S1–S5 to be complete.
S4 already wired IntradayCandleStore into PatternBasedStrategy (the original
primary scope of S4.5), so this session focuses on carry-forward items from
reviews and final integration verification.

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/project-knowledge.md`
   - `argus/strategies/red_to_green.py`
   - `argus/strategies/pattern_strategy.py` (verify S4 backfill wiring)
   - `argus/data/intraday_candle_store.py` (verify S4 created this)
   - `argus/execution/order_manager.py` (verify S1/S2 changes)
   - `docs/sprints/sprint-27.65/S2-review.md` (CONCERNS to resolve)
   - `docs/sprints/sprint-27.65/S4-review.md` (CONCERNS to resolve)
2. Run the test baseline (DEC-328 — final session, full suite):
   Full suite: `python -m pytest tests/ --ignore=tests/test_main.py -x -q -n auto`
   Expected: ~3,408+ tests, all passing
   Also: `cd argus/ui && npx vitest run`
   Expected: ~633+ Vitest tests, all passing
3. Verify you are on the correct branch
4. Verify S4 backfill is already wired:
   - `PatternBasedStrategy.set_candle_store()` exists
   - `PatternBasedStrategy._try_backfill_from_store()` exists
   - `PatternBasedStrategy._backfilled_symbols` set exists
   - `main.py` passes candle store to pattern strategies

## Objective
Resolve carry-forward items from S2 and S4 reviews, add missing defense-in-depth
guards to Red-to-Green, clean up dead code, log DEF items, and run the final
full-suite integration verification for Sprint 27.65.

## Background — Carry-Forward Items

**From S2 review (CONCERNS):**
- LOW: R2G missing zero-R guard (`_has_zero_r()` added to BaseStrategy but not
  called in R2G's signal construction path)
- LOW: R2G missing strategy-level concurrent position skip-when-zero guard
  (system-level Risk Manager handles it, but other strategies have the guard)
- MEDIUM (informational): Submit-before-cancel bracket amendment pattern for
  live trading hardening → log as DEF item

**From S4 review (CONCERNS):**
- LOW: `AccountUpdateEvent` dead code — defined in events.py, mapped in
  EVENT_TYPE_MAP, but never published through event bus
- LOW: Duck-typed candle store reference → log as DEF item for Protocol type

**From S3 (scaffolding):**
- `reduced_confidence` variable in pattern_strategy.py is dead code scaffolding.
  With S4's backfill wiring complete, evaluate whether to keep or remove.

## Requirements

### R1: Red-to-Green defense-in-depth guards
1. In `red_to_green.py`, in the signal construction path (where entry, stop,
   and target prices are computed):
   - Add zero-R guard: call `self._has_zero_r(entry, target)` before emitting
     the signal. If True, log at DEBUG and return without signaling.
   - This matches the pattern already applied in `orb_base.py` and
     `pattern_strategy.py` (S2).
2. Add strategy-level concurrent position skip-when-zero:
   - If `self._max_concurrent_positions == 0`, skip the strategy-level
     concurrent position check (same pattern as ORB, VWAP, AfMo from S2).
   - This is defense-in-depth only — the Risk Manager already handles it.

### R2: Clean up AccountUpdateEvent dead code
1. The account poll loop in `live.py` constructs WS messages manually via
   `_broadcast()` rather than publishing `AccountUpdateEvent` through the
   event bus. Pick ONE approach and make it consistent:
   - **Option A (preferred):** Publish `AccountUpdateEvent` through the event
     bus and let the standard WS bridge serialization handle it. Remove the
     manual `_broadcast()` call. This is the pattern used by all other events.
   - **Option B:** Remove `AccountUpdateEvent` from `events.py` and its
     `EVENT_TYPE_MAP` entry. Keep the manual broadcast. Simpler but inconsistent.
2. Whichever option: ensure no dead code remains.

### R3: Evaluate reduced_confidence scaffolding
1. In `pattern_strategy.py`, the `reduced_confidence` variable from S3 was
   scaffolding for the case where backfill wasn't available yet.
2. Now that S4 wired the backfill: if `_try_backfill_from_store()` provides
   sufficient history, the reduced-confidence path is no longer needed for
   the backfill case. However, it's still useful for the first few minutes
   of the session when IntradayCandleStore itself doesn't have enough bars.
3. **Keep the warm-up telemetry** (recording "Warming up N/M" and
   "Insufficient history" evaluation events) — this is valuable observability.
4. **Remove the `reduced_confidence` variable** if it's truly unused (no code
   reads it). If it's only used in telemetry metadata, leave it.

### R4: Log DEF items
1. Add to `CLAUDE.md` deferred items:
   - `DEF-095: Submit-before-cancel bracket amendment pattern — currently
     cancel-then-resubmit creates brief sub-second unprotected window. For live
     trading hardening, consider submitting new bracket legs before cancelling
     old ones. Ref: S2 review finding.`
   - `DEF-096: Protocol type for duck-typed candle store reference in
     PatternBasedStrategy — currently uses object + hasattr(). A Protocol type
     would restore type safety without circular imports. Ref: S4 review finding.`

### R5: S2 and S4 review artifact updates
1. Update `docs/sprints/sprint-27.65/S2-review.md`:
   - Append "### Post-Review Resolution" section
   - Mark R2G zero-R guard and concurrent position guard as resolved
   - Mark squashed commit observation as acknowledged (process note)
   - Update verdict to `CONCERNS_RESOLVED` with `post_review_fixes` array
2. Update `docs/sprints/sprint-27.65/S2-closeout.md`:
   - Append "### Post-Review Fixes (S4.5)" section with resolution table
3. Update `docs/sprints/sprint-27.65/S4-review.md`:
   - Append "### Post-Review Resolution" section
   - Mark AccountUpdateEvent dead code as resolved
   - Mark duck-typed reference as DEF-096
   - Update verdict to `CONCERNS_RESOLVED` with `post_review_fixes` array
4. Update `docs/sprints/sprint-27.65/S4-closeout.md`:
   - Append "### Post-Review Fixes (S4.5)" section with resolution table

## Constraints
- Do NOT modify: Order Manager flatten_pending guard, bracket amendment logic,
  Risk Manager circuit breakers, IntradayCandleStore internals
- Do NOT modify: existing WebSocket message types (except AccountUpdateEvent
  cleanup per R2)
- Do NOT modify: PatternModule ABC, BaseStrategy telemetry infrastructure
- R2G guards must follow the exact same pattern used in other strategies (S2)
- DEF items must follow existing CLAUDE.md table format

## Test Targets
After implementation:
- Existing tests: ALL must pass (final session — full suite)
- New tests to write:
  1. `test_r2g_zero_r_guard` — R2G with entry≈target, verify signal not emitted
  2. `test_r2g_concurrent_limit_disabled_when_zero` — max=0, verify check skipped
  3. `test_account_update_event_not_dead_code` — verify AccountUpdateEvent is
     either published via event bus or removed from EVENT_TYPE_MAP (whichever
     approach chosen in R2)
  4. `test_r2g_normal_signal_unaffected_by_guards` — verify valid R2G signals
     still emit normally with guards in place
- Minimum new test count: 4
- Test commands (final session — full suite):
  - `python -m pytest tests/ --ignore=tests/test_main.py -x -q -n auto`
  - `cd argus/ui && npx vitest run`

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| R2G still produces evaluations (S3 fix preserved) | Existing R2G tests pass |
| R2G signal generation still works for valid setups | New test + existing tests |
| Pattern backfill still works (S4 wiring preserved) | Existing S4 backfill tests pass |
| All other strategies unaffected | Full strategy test suite passes |
| WebSocket events still work | Existing WS tests pass |
| No merge conflict residue | `grep -r "<<<<<<" argus/` returns nothing |
| All S1–S5 changes intact | Full test suite passes |

## Definition of Done
- [ ] R2G zero-R guard and concurrent position guard added
- [ ] AccountUpdateEvent dead code resolved (publish via bus or remove)
- [ ] reduced_confidence scaffolding evaluated and cleaned if dead
- [ ] DEF-095 and DEF-096 logged in CLAUDE.md
- [ ] S2 and S4 review artifacts updated (CONCERNS_RESOLVED)
- [ ] Full test suite passes (all S1–S5 + S4.5 tests)
- [ ] Full Vitest suite passes
- [ ] 4+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
Write close-out to: `docs/sprints/sprint-27.65/S4.5-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After close-out, invoke @reviewer with:
1. Review context: `docs/sprints/sprint-27.65/review-context.md`
2. Close-out path: `docs/sprints/sprint-27.65/S4.5-closeout.md`
3. Diff range: full sprint diff from before Sprint 27.65 started
4. Test command (final session — full suite):
   - `python -m pytest tests/ --ignore=tests/test_main.py -x -q -n auto`
   - `cd argus/ui && npx vitest run`
5. Files NOT to modify: `argus/data/intraday_candle_store.py`,
   `argus/execution/order_manager.py` (except if R2 Option A routes
   AccountUpdateEvent through it), `argus/core/risk_manager.py`

Write review to: `docs/sprints/sprint-27.65/S4.5-review.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify R2G zero-R guard follows same pattern as orb_base.py
2. Verify R2G concurrent position guard follows same pattern as other strategies
3. Verify AccountUpdateEvent dead code is fully resolved (no orphaned references)
4. Verify S2 and S4 review artifacts updated per Post-Review Fix protocol
5. Verify DEF items follow CLAUDE.md format
6. Full regression pass — this is the final session of Sprint 27.65
7. Verify no merge conflicts from parallel session execution

## Sprint-Level Escalation Criteria (for @reviewer)
Escalate if:
1. Any change introduces a path where orders can be submitted without risk checks
2. Position reconciliation auto-corrects instead of warning
3. Bracket amendment logic modified (it should NOT be in this session)
4. Changes break SimulatedBroker or backtest paths
5. Any S1–S4 fix was accidentally reverted