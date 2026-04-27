# Sprint 31.91, Session 3: DEF-158 Retry Side-Check + Severity Fix

> **Track:** Single-session track (D6). Independent of the Side-Aware Reconciliation Contract track but consumes its `phantom_short` alert taxonomy.
> **Position in sprint:** First session AFTER Tier 3 #1 + the entire reconciliation contract track lands. By Session 3's start, every reconciliation entry point in ARGUS is already side-aware. Session 3 closes the last side-blind retry path.

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full.** RULE-038, RULE-050, RULE-019, RULE-007 all apply.

2. Read these files:
   - `argus/execution/order_manager.py:2299-2406` — `_check_flatten_pending_timeouts` (verify line range; primary modification target).
   - `argus/execution/order_manager.py:2384` — the specific retry-decision line within that function (per spec D6).
   - `argus/execution/order_manager.py:1670-1750` — IMPROMPTU-04 EOD A1 pattern (do-not-modify but **read for reference** — Session 3's 3-branch logic mirrors this exact pattern; the pattern code shape, log idiom, and alert metadata fields should be parallel).
   - `argus/core/events.py:405` — `SystemAlertEvent` definition (verify constructor signature; Session 2b.1 introduced `phantom_short` alert_type, Session 3 adds `phantom_short_retry_blocked`).
   - `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` — D6 acceptance (lines ~590-595).
   - Pre-existing tests on `_check_flatten_pending_timeouts` — locate via `grep -rn "_check_flatten_pending_timeouts\|test_def158" tests/`. Read at least one to learn the test idiom.

3. Run baseline (DEC-328 — Session 6+ of sprint, scoped is fine):

   ```
   python -m pytest tests/execution/ -n auto -q
   ```

   Expected: green (Session 2d's close-out confirmed the entire 2-track is on `main`).

4. Branch: **`main`**.

5. **Verify Session 2b.1 and 2c.1 deliverables on `main`** (Session 3 consumes both):

   ```bash
   grep -n "phantom_short" argus/execution/order_manager.py | head -20
   grep -n "_phantom_short_gated_symbols" argus/execution/order_manager.py
   grep -n "alert_type=\"phantom_short\"" argus/
   ```

   The first two must show 2b.1's `_handle_broker_orphan_short` path and 2c.1's gate state. The third must show at least one existing emission (from 2b.1, 2b.2, 2c.1). If any are missing, halt — the reconciliation track has not landed.

6. **Pre-flight grep for the existing DEF-158 retry pattern at `:2384`:**

   ```bash
   sed -n '2299,2406p' argus/execution/order_manager.py | grep -n "broker_qty\|getattr.*side\|place_order"
   ```

   Confirm the existing function has:
   - A `broker_qty` read (the qty mismatch path that DEF-158 originally fixed).
   - Either no `side` read OR a side-blind read (this is what Session 3 fixes).
   - A `place_order(... side=OrderSide.SELL ...)` somewhere downstream.

   If line numbers have drifted by more than ±5 (RULE-038), reconcile against the current code before applying changes — the spec D6 explicitly named `:2384` as the side-read insertion point but the surrounding function is `:2299-2406`.

## Objective

Apply IMPROMPTU-04's exact 3-branch pattern to `_check_flatten_pending_timeouts`. The function is the retry path for flatten-pending entries that didn't get a fill confirmation within the timeout window. Today, on retry, it queries broker for `qty` (DEF-158 fixed the qty-mismatch case) but does NOT inspect `side`. If the broker side is SELL (i.e., the position is already short — e.g., a phantom from a prior flatten that flipped, or a manual operator action that ARGUS missed), the retry will issue ANOTHER SELL, doubling the short.

The fix mirrors IMPROMPTU-04 exactly. Three branches:

- **BUY + broker_qty > 0** → flatten as today. This is the normal happy path and existing test `test_def158_flatten_qty_mismatch_uses_broker_qty` (or sibling) covers it.
- **SELL** → CRITICAL log, emit `SystemAlertEvent(alert_type="phantom_short_retry_blocked", severity="critical")`, do NOT issue SELL, clear flatten-pending entry.
- **None or unrecognized** → ERROR log, do NOT issue SELL, clear flatten-pending entry.

The existing branches for `broker_qty == 0` (broker reports the position is already closed; ARGUS just missed the close) and qty-mismatch (DEF-158's original fix) are preserved verbatim — they are correct behaviors that Session 3 does not touch.

## Why This Pattern Is Correct (Reference Reasoning)

The IMPROMPTU-04 EOD A1 fix at `:1670-1750` faces the same architectural problem: a flatten path that thought it was placing a SELL on a long but might actually be facing a short. IMPROMPTU-04 chose the 3-branch pattern (BUY=flatten, SELL=alert+halt, None=error+halt) because:

1. **The cost-of-error asymmetry is identical.** Issuing a SELL on a short produces an unbounded short — the same DEF-204 mechanism. Refusing to flatten a long is bounded exposure with a missing automated stop. Bounded loss > unbounded loss; refuse-and-alert is correct.

2. **The "unknown side" branch is structural.** If `side` is `None` because the broker returned a malformed Position or because ARGUS's `Position` model has a bug, the safe action is to refuse the SELL, not to default to "flatten the way we always did." Defaulting to legacy behavior is what produced DEF-204 in the first place.

3. **The taxonomy alignment is intentional.** All "phantom short detected" paths in ARGUS now emit a `phantom_short` or `phantom_short_retry_blocked` alert. Session 5a.2's auto-resolution policy table can consume these uniformly. A reviewer reading the codebase later sees that side-blindness was systematically purged.

Session 3 is the LAST side-blind retry path. After this session lands, the architectural property "every flatten/retry path inspects side before placing SELL" holds across the entire OrderManager.

## Requirements

1. **Modify `_check_flatten_pending_timeouts` in `argus/execution/order_manager.py:~2384`:**

   The exact insertion point is where the current code reads `broker_qty` and decides whether to retry the flatten. Add a `side` read alongside the `broker_qty` read, then apply the 3-branch logic. Pseudocode (adapt to the actual existing function structure):

   ```python
   # Existing pattern (approximately):
   broker_pos = await self._broker.get_position(symbol)
   broker_qty = broker_pos.shares if broker_pos else 0

   # Sprint 31.91 Session 3: side-aware retry. Mirror of IMPROMPTU-04 EOD A1.
   broker_side = getattr(broker_pos, "side", None) if broker_pos else None

   # Existing branch — broker reports zero shares (position already closed)
   if broker_qty == 0:
       # ... existing handling: clear pending, log INFO ...
       return

   # NEW (Session 3): 3-branch side check before retry.
   if broker_side == OrderSide.BUY and broker_qty > 0:
       # Branch 1: BUY + non-zero qty → flatten as today (existing logic).
       # ... existing flatten-retry path with broker_qty as the SELL qty ...
       pass  # placeholder for existing code
   elif broker_side == OrderSide.SELL:
       # Branch 2: SELL → phantom short. Refuse retry. Alert critical.
       self._logger.critical(
           "Flatten retry refused for %s: broker reports SHORT position "
           "(shares=%d) but ARGUS expected long. Will NOT issue SELL "
           "(would double the short). Investigate via "
           "scripts/ibkr_close_all_positions.py.",
           symbol, broker_qty,
       )
       alert = SystemAlertEvent(
           severity="critical",
           source="order_manager._check_flatten_pending_timeouts",
           alert_type="phantom_short_retry_blocked",
           message=(
               f"DEF-158 retry refused for {symbol}: broker reports SHORT "
               f"position (shares={broker_qty}) but ARGUS expected long. "
               f"SELL was NOT issued. Operator must investigate via "
               f"scripts/ibkr_close_all_positions.py."
           ),
           metadata={
               "symbol": symbol,
               "broker_shares": broker_qty,
               "broker_side": "SELL",
               "expected_side": "BUY",
               "detection_source": "def158_retry",
           },
       )
       self._event_bus.publish(alert)
       # CRITICAL: clear flatten-pending so we don't loop forever
       self._flatten_pending.pop(symbol, None)
       return
   else:
       # Branch 3: side is None / unrecognized.
       self._logger.error(
           "Flatten retry refused for %s: broker side is %r (expected "
           "OrderSide.BUY or OrderSide.SELL); broker_qty=%d. Will NOT "
           "issue SELL. Investigate broker integration; check Position "
           "model for malformed `side` field.",
           symbol, broker_side, broker_qty,
       )
       # No alert — this is a defensive code path that should not occur
       # in normal operation. ERROR log is sufficient observability;
       # alert flooding on a structural bug is not useful.
       self._flatten_pending.pop(symbol, None)
       return
   ```

   **Adaptation notes:**
   - The exact location of "the existing flatten-retry path" (the body of branch 1) depends on how the current function is structured. If the existing code does the flatten unconditionally after the qty-zero branch, your job is to wrap the existing flatten code in `if broker_side == OrderSide.BUY and broker_qty > 0: ...` and add the two new branches.
   - The `flatten-pending` clearance in branches 2 and 3 is critical. Without it, the function will retry on the next timeout cycle, looping the alert/error log forever. Branch 1's flatten path may already clear pending on success; verify it does. If not, add the clearance.
   - The `side` field on `Position` may be an `OrderSide` enum or a string. Verify by reading `argus/models/trading.py`'s `Position` definition. If it's a string, the comparison should be `broker_side == OrderSide.BUY.value` or normalized via a helper. Use whatever idiom the existing code uses elsewhere (e.g., `:1670-1750` IMPROMPTU-04 pattern).

2. **Preserve the qty-mismatch path (DEF-158's original fix).** The existing test `test_def158_flatten_qty_mismatch_uses_broker_qty` (or whatever the actual test name is — verify via grep) must continue passing. The qty-mismatch logic is independent of side; on broker_qty=BUY with mismatched qty, the path uses broker_qty for the SELL placement, which is correct.

3. **Mirror IMPROMPTU-04's idiom precisely.** The log strings, error messages, and alert metadata fields should be parallel to `:1670-1750` IMPROMPTU-04. A reviewer comparing the two should be able to say "this is the same pattern applied to a different code site." Specifically:
   - Same `severity="critical"` for the SELL branch.
   - Same `metadata` shape (symbol + side + shares + detection source).
   - Same INFO/ERROR/CRITICAL log levels.
   - Same investigate-via-script callout in the alert message.

4. **No edits to do-not-modify regions.** Specifically:
   - `argus/execution/order_manager.py:1670-1750` (IMPROMPTU-04 EOD A1 fix) — zero edits. Read-only reference. Tier 2 will verify via diff.
   - `argus/main.py` — zero edits.
   - `argus/models/trading.py` — zero edits (consume `side` field as-is; do not rename or restructure).
   - Alpaca files — zero edits.
   - `IMPROMPTU-04-closeout.md` — zero edits.
   - `workflow/` — zero edits.

5. **Anti-regression: DEF-158 normal-case test must pass unchanged.** The pre-existing test that validates the qty-mismatch behavior (locating it via `grep -rn "test_def158" tests/`) MUST pass without modification. Session 3 adds the side check upstream of the qty-using flatten; it does not change qty handling.

## Tests (~5 new + ~2 mock updates)

1. **`test_def158_retry_long_position_flattens_normally`** — set up flatten-pending entry for AAPL; mock broker `get_position` to return `Position(symbol="AAPL", side=OrderSide.BUY, shares=100)`; trigger `_check_flatten_pending_timeouts`; assert `place_order` called with `side=OrderSide.SELL, qty=100`; assert flatten-pending entry cleared. This is the happy-path branch 1.

2. **`test_def158_retry_short_position_blocks_and_alerts_critical`** — set up flatten-pending entry for AAPL; mock broker to return `Position(symbol="AAPL", side=OrderSide.SELL, shares=100)`; trigger; assert `place_order` was NOT called; assert exactly one `SystemAlertEvent` emitted with `alert_type="phantom_short_retry_blocked"` and `severity="critical"`; assert flatten-pending cleared (no infinite retry loop); assert CRITICAL log message present.

3. **`test_def158_retry_unknown_side_blocks_and_logs_error`** — set up flatten-pending; mock broker to return `Position(symbol="AAPL", side=None, shares=100)` (or whatever the malformed-side fixture pattern is); trigger; assert `place_order` was NOT called; assert NO alert emitted (this is the structural-bug branch — log only, no alert flooding); assert ERROR log message present; assert flatten-pending cleared.

4. **`test_def158_retry_qty_mismatch_long_uses_broker_qty`** — anti-regression for DEF-158's original case. Set up flatten-pending with `flatten_qty=200` (ARGUS-tracked); mock broker `Position(side=OrderSide.BUY, shares=150)` (mismatch); trigger; assert `place_order` called with `qty=150` (broker's authoritative count, per DEF-158), not `200`. This test may already exist as `test_def158_flatten_qty_mismatch_uses_broker_qty`; if so, verify it still passes after the side-check insertion. If not, add it.

5. **`test_phantom_short_retry_blocked_alert_severity_is_critical`** — focused verification of the alert payload from test 2. Assert `alert_type == "phantom_short_retry_blocked"`, `severity == "critical"`, `metadata["symbol"] == "AAPL"`, `metadata["broker_side"] == "SELL"`, `metadata["expected_side"] == "BUY"`, `metadata["broker_shares"] == 100`, `metadata["detection_source"] == "def158_retry"`.

6. **(MOCK UPDATE)** Update test fixtures that mock `Broker.get_position` to expose a `side` field on the returned Position. The existing fixture may return a Position without `side` (silently `None`); after Session 3, every test that exercises `_check_flatten_pending_timeouts` will hit branch 3 unless `side` is set. This is likely 2 mock files: a shared `conftest.py` Position factory + a specific test-helper file. Per RULE-019, do not delete existing tests; add `side=OrderSide.BUY` defaults to fixtures so existing tests continue passing.

## Definition of Done

- [ ] 3-branch logic at `:~2384` mirrors IMPROMPTU-04 idiom (CRITICAL log + alert + clear-pending for SELL; ERROR log + clear-pending for unknown).
- [ ] BUY + non-zero qty branch preserves existing flatten behavior.
- [ ] All 3 branches clear flatten-pending (no infinite retry).
- [ ] `phantom_short_retry_blocked` alert severity=critical with full metadata payload.
- [ ] DEF-199 A1 fix unchanged (`:1670-1750` zero edits).
- [ ] DEF-158 qty-mismatch normal case anti-regression passes.
- [ ] 5 new tests + 2 mock updates added; all green.
- [ ] CI green; pytest baseline ≥ Session 2d's count + 5.
- [ ] Tier 2 review (backend safety reviewer) verdict CLEAR.
- [ ] Close-out at `docs/sprints/sprint-31.91-reconciliation-drift/session-3-closeout.md`.

## Close-Out Report

Standard structure. The verdict JSON should specifically note:

```json
{
  "session": "3",
  "verdict": "PROPOSED_CLEAR",
  "tests_added": 5,
  "improptu_04_pattern_mirrored": true,
  "all_branches_clear_flatten_pending": true,
  "def158_anti_regression_pass": true
}
```

Add a "Pattern Symmetry Note" section to the close-out: a short paragraph explicitly comparing your branch-2/branch-3 code to IMPROMPTU-04 at `:1670-1750`. State which lines mirror which (e.g., "the CRITICAL log message format mirrors `:1690-1695`; the alert metadata shape mirrors `:1710-1720`"). This makes Tier 2's job dramatically easier and is the durable trace future maintainers need to understand the architectural property.

## Tier 2 Review Invocation

Standard pattern. Provide `review-context.md`, the close-out, `git diff HEAD~1`, scoped test command, and the do-not-modify list.

The reviewer must use the **backend safety reviewer** template (`templates/review-prompt.md`).

Reviewer output path: `docs/sprints/sprint-31.91-reconciliation-drift/session-3-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **IMPROMPTU-04 mirror verification.** Open `:1670-1750` side-by-side with the new code at `:~2384`. Verify:
   - Branch structure is parallel (3 branches in IMPROMPTU-04; 3 branches here).
   - Log levels match (CRITICAL on phantom-short detection; ERROR on unknown side).
   - Alert metadata shape matches (`symbol`, side info, `detection_source`).
   - The `pop(symbol, None)` to clear pending state is present in both.

   The Pattern Symmetry Note in the close-out should make this trivially verifiable. If the close-out lacks it or the symmetry isn't actual, this is a CONCERN.

2. **All 3 branches clear flatten-pending.** Read each branch's exit path. The BUY branch may clear via the existing flatten code's success callback; verify by tracing. The SELL and unknown branches MUST explicitly call `self._flatten_pending.pop(symbol, None)`. Without it, infinite retry loops emit alerts forever.

3. **Alert severity is `critical`, not `warning`.** Per spec D6 acceptance and Sprint 31.91 alert taxonomy. The auto-resolution policy table (Session 5a.2) treats severity as the routing axis; downgrading to warning would silently break the policy.

4. **`broker_side == OrderSide.SELL` comparison shape.** Verify the comparison matches the existing `Position.side` type. If `Position.side` is a string ("BUY" / "SELL"), the comparison must use the string form OR be normalized via a helper. Inconsistency between IMPROMPTU-04's idiom and Session 3's idiom is a CONCERN.

5. **No edits to `:1670-1750`.** `git diff` audit must show the IMPROMPTU-04 region untouched.

6. **DEF-158 normal case unchanged.** Run the original DEF-158 test (whatever name it has — locate via grep). It must pass unchanged.

7. **Mock fixture updates are scoped.** The fixture changes should add `side=OrderSide.BUY` defaults to `Position` factories used in flatten-pending tests; they should NOT broaden to affect tests outside this scope. Per RULE-019.

8. **`phantom_short_retry_blocked` is a NEW alert_type.** Verify Session 2b.1/2b.2 use `phantom_short` (without the `_retry_blocked` suffix). Session 3's alert is taxonomically distinct — same severity (critical), but a different `alert_type` so Session 5a.2's policy table can route them separately if needed. Mixing the two would be a CONCERN.

## Sprint-Level Regression Checklist (for @reviewer)

- **Invariant 1 (DEF-199 A1 fix):** PASS — `:1670-1750` zero edits.
- **Invariant 3 (DEF-158 dup-SELL prevention for ARGUS=N, IBKR=N normal case):** PASS — DEF-158's qty-mismatch path is preserved by Test 4. The new side-check is upstream of (not replacing) the dup-SELL prevention.
- **Invariant 5:** PASS — expected baseline + 5.
- **Invariant 14 (Monotonic-safety):** Row "After Session 3" — DEF-158 retry side-aware = YES.
- **Invariant 15:** PASS.

## Sprint-Level Escalation Criteria (for @reviewer)

- **A2** (Tier 2 CONCERNS or ESCALATE).
- **A6** (regression test 4 fails — would mean the side-check insertion broke DEF-158's qty-mismatch path).
- **B1, B3, B4, B6** — standard halt conditions.
- **C5** (uncertain whether the modification crosses the `:1670-1750` boundary — Session 3's target at `:~2384` is structurally adjacent in the file but architecturally separate; verify by reading the actual function boundaries).
- **C7** (existing flatten-pending tests fail because their `Position` fixtures don't have `side` set; the mock-update step is meant to handle this — escalation only if the mock update doesn't resolve all failures cleanly).

---

*End Sprint 31.91 Session 3 implementation prompt.*
