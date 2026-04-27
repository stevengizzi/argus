# Sprint 31.91, Session 1b: Standalone-SELL OCA Threading + Error 201 Graceful Handling

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** RULE-038 (grep-verify discipline), RULE-050 (CI green), and RULE-007 (out-of-scope discoveries) apply.

2. Read these files to load context:
   - `argus/execution/order_manager.py:2451` — `_trail_flatten` method (verify line number; may have drifted)
   - `argus/execution/order_manager.py:2552` — `_escalation_update_stop` method (verify)
   - `argus/execution/order_manager.py:778` — `_resubmit_stop_with_retry` method (verify)
   - `argus/execution/order_manager.py:2620` — `_flatten_position` method (verify)
   - `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` — D3 acceptance criteria
   - `docs/sprints/sprint-31.91-reconciliation-drift/spec-by-contradiction.md` — Do NOT refactor list

3. Run the test baseline (DEC-328 — Session 2+ of sprint, scoped):

   ```
   python -m pytest tests/execution/ -n auto -q
   ```

   Expected: all passing (full suite was confirmed by Session 1a's close-out).

4. Verify you are on the correct branch: **`main`**.

5. Verify Session 1a's deliverables are present on `main`:

   ```bash
   grep -n "oca_group_id" argus/execution/order_manager.py
   grep -n "bracket_oca_type" argus/core/config.py
   ```

   Both must match. If not, halt — Session 1a has not landed yet.

6. **Pre-flight grep — verify exactly 4 SELL placement paths are in scope:**

   ```bash
   grep -n "_broker.place_order" argus/execution/order_manager.py
   ```

   Inspect each match. There should be at least 4 sites where a SELL order is placed for a symbol that may have a `ManagedPosition`. If you find MORE than 4 (e.g., a path was added in a recent sprint that isn't in this prompt's list), halt and escalate — the spec needs updating.

## Objective

Thread `oca_group_id` from `ManagedPosition` into every standalone SELL order placed by `_trail_flatten`, `_escalation_update_stop`, `_resubmit_stop_with_retry`, AND `_flatten_position`. When `oca_group_id is None` (covers `reconstruct_from_broker`-derived positions), fall through to legacy no-OCA behavior. Add graceful Error 201 / "OCA group is already filled" handling — this means the position is already exiting via another OCA member (e.g., the bracket stop already fired); log INFO, mark the ManagedPosition as a redundant exit, and do NOT trigger DEF-158 retry. Add a grep-test regression guard preventing future SELL placements from skipping the threading.

## Requirements

1. **Thread `oca_group_id` into `_trail_flatten`** at `argus/execution/order_manager.py:2451`:

   - Before placing the SELL Order, set:

     ```python
     sell_order.ocaGroup = managed_position.oca_group_id  # may be None
     sell_order.ocaType = self._config.ibkr.bracket_oca_type if managed_position.oca_group_id else 0
     ```

   - When `managed_position.oca_group_id is None`, the SELL order has no `ocaGroup`; this preserves legacy behavior for `reconstruct_from_broker`-derived positions. Log INFO once per position via the existing throttled-logger pattern (do not log per-call).

2. **Thread `oca_group_id` into `_escalation_update_stop`** at `argus/execution/order_manager.py:2552`:

   Same pattern as `_trail_flatten`. The escalation path may place a stop replacement order; that replacement Order also carries the OCA group.

3. **Thread `oca_group_id` into `_resubmit_stop_with_retry`** at `argus/execution/order_manager.py:778`:

   Same pattern. Important: only the new SELL Order placement gets OCA threading. The retry-cap logic (DEC-372: `stop_cancel_retry_max`, exponential-backoff schedule) is unchanged in structure.

4. **Thread `oca_group_id` into `_flatten_position`** at `argus/execution/order_manager.py:2620`:

   `_flatten_position` is the central exit path used by:
   - EOD Pass 1 (the daily-flatten loop)
   - `close_position()` API
   - `emergency_flatten()`
   - Time-stop exits

   Same OCA-threading pattern. This is the highest-leverage path of the four because it closes positions through the largest number of upstream callers.

5. **Graceful Error 201 / "OCA group is already filled" handling** on all 4 SELL placements:

   When `_broker.place_order(sell_order)` raises Error 201 with reason "OCA group is already filled":

   - Log INFO not ERROR (this is the SAFE signature confirmed by the Phase A spike).
   - Mark the `ManagedPosition` as a redundant exit. Add a field if needed:

     ```python
     @dataclass
     class ManagedPosition:
         # ... existing fields ...
         redundant_exit_observed: bool = False
     ```

     Or use an existing state field if a suitable one exists (verify during pre-flight). The semantic is: "we tried to exit but another OCA member beat us to it; the position is exiting via that other member's fill callback."

   - Do NOT trigger DEF-158 retry path. The `_check_flatten_pending_timeouts` Session 3 side-check would catch the resulting zero-broker-position anyway, but the short-circuit here is cleaner. Concretely: do NOT add the order_id to `_flatten_pending`.

   - Reuse the `_is_oca_already_filled_error` helper from Session 1a (in `argus/execution/ibkr_broker.py`), or import it if it lives elsewhere. Do NOT duplicate the parsing logic.

   Distinguishing test (existing in Session 1a, must still pass): generic Error 201 (margin, price-protection) is logged ERROR, retry path engages.

6. **Grep regression guard** — add to a regression-tests file (e.g., `tests/_regression_guards/test_oca_threading_completeness.py`):

   ```python
   def test_no_sell_without_oca_when_managed_position_has_oca():
       """Sprint 31.91 Session 1b: every SELL placement in
       order_manager.py must thread oca_group_id when the position has
       one, OR be in the explicit exempt list (broker-only paths
       handled by Session 1c).

       This guard catches future SELL paths added without OCA threading.
       """
       import re
       with open("argus/execution/order_manager.py") as fh:
           src = fh.read()

       # Find every SELL order placement
       # Pattern: _broker.place_order(... side=...SELL... )
       placements = re.findall(
           r"_broker\.place_order\([^)]*side\s*=\s*[^,)]*SELL[^)]*\)",
           src,
           re.DOTALL,
       )

       # Each placement must either:
       # (a) reference oca_group_id near it (threading present), OR
       # (b) be marked with `# OCA-EXEMPT: <reason>` comment on the line above
       #     (broker-only paths — Session 1c handles separately)

       for placement in placements:
           # Look for OCA threading within the same call expression
           if "oca_group_id" in placement or "ocaGroup" in placement:
               continue
           # Check for OCA-EXEMPT comment in the surrounding code
           idx = src.find(placement)
           preamble = src[max(0, idx - 200):idx]
           if "# OCA-EXEMPT:" in preamble:
               continue
           assert False, (
               f"SELL placement without OCA threading found:\n{placement}\n"
               f"Either thread oca_group_id, or mark with "
               f"`# OCA-EXEMPT: <reason>` comment if intentional."
           )
   ```

   This test is intentionally strict. If a Session 1b implementation site needs to be exempt (e.g., a path that legitimately has no `ManagedPosition` access), mark it with `# OCA-EXEMPT: <reason>` per soft-halt criterion C7.

## Constraints

- Do NOT modify:
  - `argus/execution/order_manager.py:1670-1750` — DEF-199 A1 fix.
  - `argus/main.py` — startup invariant region.
  - `argus/models/trading.py` — `Position` class.
  - `argus/execution/alpaca_broker.py` — Alpaca is out of scope post-Session 0.
  - `argus/data/alpaca_data_service.py:593` — out of scope.
  - `argus/execution/ibkr_broker.py` — Session 1b touches `order_manager.py` only. The IBKR broker code is the same as it was post-Session 1a; only the Error 201 helper is REUSED, not duplicated, in `order_manager.py`.
  - DEC-372 stop-retry-cap logic in `_resubmit_stop_with_retry`. Only `ocaGroup` / `ocaType` are added to the placed Order.
  - The `workflow/` submodule.

- Do NOT change:
  - The `_check_flatten_pending_timeouts` general structure (Session 3 modifies its branch logic; Session 1b only adds the SAFE-outcome short-circuit on Error 201 at the place-order site, not in the retry function).
  - `_flatten_pending` dict shape.
  - Any throttled-logger interval.
  - The OCA-threading pattern: ONLY `ocaGroup` and `ocaType` are added to the SELL Order. No new OrderType enum values, no new ExitReason enum values, no new event classes.

- Do NOT add:
  - A new `OrderType` enum value (per SbC §"Do NOT add").
  - A new circuit breaker.
  - A new event class — `SystemAlertEvent` covers everything.

- Do NOT cross-reference other session prompts.

## Risky Batch Edit — Staged Flow (recommended)

This session modifies 4 functions in a single file. To prevent overlap mistakes, use the staged flow:

1. Read-only exploration: enumerate every `_broker.place_order` call in `order_manager.py` (pre-flight grep step 6 already does this).
2. Produce a structured findings report with: exact line number per site, existing call-expression text, planned edit (the OCA threading), and any sites that look eligible but should be skipped (with reasoning — these become `# OCA-EXEMPT:` candidates).
3. Write the report to `docs/sprints/sprint-31.91-reconciliation-drift/session-1b-staged-flow-report.md`.
4. **Halt.** Surface the report to the operator and wait for confirmation.
5. Apply edits exactly as listed in the confirmed report.

See RULE-039 in `.claude/rules/universal.md`.

## Test Targets

After implementation:

- Existing tests: all 5,080+ must still pass.
- New tests (~8 new pytest in `tests/execution/test_standalone_sell_oca_threading.py` or appended):

  1. `test_trail_flatten_threads_oca_group`
     - Set up a `ManagedPosition` with `oca_group_id = "oca_test"`. Trigger trail-flatten. Assert the placed SELL Order has `ocaGroup == "oca_test"` and `ocaType == 1`.
  2. `test_escalation_update_stop_threads_oca_group`
     - Same shape for the escalation path.
  3. `test_resubmit_stop_with_retry_threads_oca_group`
     - Same shape for the retry path. DEC-372 retry-cap logic still functional (existing test must pass alongside).
  4. `test_flatten_position_threads_oca_group`
     - Same shape for the central flatten path.
  5. `test_oca_threading_falls_through_when_oca_group_id_none`
     - Set up a `ManagedPosition` with `oca_group_id = None`. Trigger any of the 4 paths. Assert the placed SELL Order has NO `ocaGroup` set (or it's None / empty). Assert legacy behavior preserved.
  6. `test_race_window_two_paths_same_oca_group`
     - Set up a position with `oca_group_id = "oca_test"`. Race two of the 4 paths firing simultaneously (e.g., trail_flatten and escalation). Assert both place SELL Orders with the same `ocaGroup`. (The IBKR side will then atomically cancel one — verify this via the spike script's behavior, not in this unit test.)
  7. `test_no_sell_without_oca_when_managed_position_has_oca` (the grep regression guard from requirement 6)
  8. `test_standalone_sell_error_201_oca_filled_logged_info_not_error`
     - Mock IBKR to raise Error 201 "OCA group is already filled" on the SELL placement. Assert:
       - Log severity INFO not ERROR.
       - `ManagedPosition.redundant_exit_observed` (or equivalent state) becomes True.
       - DEF-158 retry path NOT triggered (`_flatten_pending` does NOT gain the order_id).
     - Distinguishing case: Error 201 with reason "Margin requirement not met" — assert ERROR severity, retry path engages (existing behavior).

- Test command (scoped per DEC-328):

  ```
  python -m pytest tests/execution/ tests/_regression_guards/ -n auto -q
  ```

## Config Validation (N/A this session)

Session 1b adds no config fields.

## Marker Validation (N/A this session)

Session 1b adds no pytest markers.

## Definition of Done

- [ ] All 4 SELL paths thread `oca_group_id`: `_trail_flatten`, `_escalation_update_stop`, `_resubmit_stop_with_retry`, `_flatten_position`.
- [ ] When `oca_group_id is None`, all 4 paths fall through to legacy no-OCA behavior.
- [ ] Error 201 / "OCA group is already filled" handled gracefully on all 4 paths: INFO severity; ManagedPosition marked redundant exit; DEF-158 retry NOT triggered.
- [ ] Generic Error 201 (margin, price-protection) still treated as ERROR with retry (Session 1a's distinguishing test must still pass).
- [ ] Grep regression guard (`test_no_sell_without_oca_when_managed_position_has_oca`) lands and passes.
- [ ] DEF-199 A1 fix still detects phantom shorts (anti-regression — invariant 1).
- [ ] DEF-158 dup-SELL prevention works for the ARGUS=N, IBKR=N normal case (invariant 3).
- [ ] All 5,080+ existing pytest still passing.
- [ ] CI green.
- [ ] Tier 2 review CLEAR.

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| `git diff HEAD~1 -- argus/execution/order_manager.py:1670-1750` shows zero edits | DEF-199 A1 fix protected (invariant 1) |
| `git diff HEAD~1 -- argus/main.py` shows zero edits | invariant 9 |
| `git diff HEAD~1 -- argus/models/trading.py` shows zero edits | invariant 15 |
| `git diff HEAD~1 -- argus/execution/alpaca_broker.py` shows zero edits | post-Session-0 Alpaca is out of scope |
| `git diff HEAD~1 -- argus/data/alpaca_data_service.py` shows zero edits | invariant 15 |
| `git diff HEAD~1 -- argus/execution/ibkr_broker.py` shows zero edits | Session 1b touches order_manager.py only |
| `_check_flatten_pending_timeouts` general structure unchanged | grep + diff inspection; Session 3 modifies its branch logic, not Session 1b |
| `_flatten_pending` dict shape unchanged | grep for `_flatten_pending[` to verify no shape change |
| DEC-372 retry-cap logic in `_resubmit_stop_with_retry` unchanged | git diff inspection of the retry-loop body |
| Pre-existing flake count unchanged | CI run |
| 4 SELL placement paths all thread OCA when present | Tests 1-4 + grep regression guard |
| `_broker.place_order` calls outside the 4 paths are exempt or threaded | Grep regression guard catches this |

## Close-Out

After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

**Write the close-out report to a file** (DEC-330):

```
docs/sprints/sprint-31.91-reconciliation-drift/session-1b-closeout.md
```

If you used the staged-flow pattern, the staged-flow report
(`session-1b-staged-flow-report.md`) lives alongside the close-out and
is referenced from it.

## Tier 2 Review (Mandatory — @reviewer Subagent)

After the close-out is written to file and committed, invoke the @reviewer subagent.

Provide the @reviewer with:

1. The review context file: `docs/sprints/sprint-31.91-reconciliation-drift/review-context.md`
2. The close-out report path: `docs/sprints/sprint-31.91-reconciliation-drift/session-1b-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/execution/ tests/_regression_guards/ -n auto -q` (scoped — DEC-328; non-final session)
5. Files that should NOT have been modified:
   - `argus/execution/order_manager.py:1670-1750` (DEF-199 A1 fix)
   - `argus/execution/ibkr_broker.py` (Session 1a was the IBKR-broker-touching session; Session 1b touches order_manager.py)
   - `argus/main.py`
   - `argus/models/trading.py`
   - `argus/execution/alpaca_broker.py`
   - `argus/data/alpaca_data_service.py`
   - `docs/sprints/sprint-31.9/IMPROMPTU-04-closeout.md`
   - `workflow/` submodule

The @reviewer must use the **backend safety reviewer** template (`templates/review-prompt.md`).

The @reviewer will produce its review report at:

```
docs/sprints/sprint-31.91-reconciliation-drift/session-1b-review.md
```

## Post-Review Fix Documentation

Same pattern as Session 0/1a. If @reviewer reports CONCERNS and you fix within session, append "Post-Review Fixes" / "Post-Review Resolution" sections and update verdict JSON to `CONCERNS_RESOLVED`.

## Session-Specific Review Focus (for @reviewer)

1. **All 4 paths thread correctly.** Run the four threading tests (1–4 above) and verify each fires. Verify grep finds OCA references near each `_broker.place_order` call inside the 4 paths.

2. **Error 201 distinguishing logic.** Inspect the call site where the SELL placement is wrapped in error handling. Verify:
   - The OCA-filled check uses the `_is_oca_already_filled_error` helper from Session 1a (NOT a duplicated parser).
   - The OCA-filled path: INFO log, mark redundant exit, NO retry path entry.
   - The generic Error 201 path: ERROR log, retry path engages.

3. **DEF-199 A1 fix still detects phantom shorts** (anti-regression). The Tier 2 reviewer must run `test_short_position_is_not_flattened_by_pass2` (or sibling) and verify it still passes. The test is on the do-not-modify line range (1670-1750), but its behavior should still be exercisable.

4. **DEF-158 dup-SELL prevention preserved for the normal case.** Run `test_def158_flatten_qty_mismatch_uses_broker_qty` (or sibling). Session 3 will modify `_check_flatten_pending_timeouts` later; Session 1b must not regress its current behavior.

5. **Grep regression guard correctness.** The guard test `test_no_sell_without_oca_when_managed_position_has_oca` is added in this session. Verify:
   - The regex correctly identifies `_broker.place_order(... side=...SELL...)` calls.
   - The exemption mechanism (`# OCA-EXEMPT: <reason>`) works for legitimate cases (Session 1c will use this for broker-only paths).
   - The test fails when a SELL placement is added without OCA or exemption (negative-case verification).

6. **Race window correctness.** Test 6 (`test_race_window_two_paths_same_oca_group`) — verify two paths can fire simultaneously and both thread the same `ocaGroup`. The unit test is bounded; the IBKR-side atomic cancellation is verified by the spike script, not by this unit test.

7. **`_flatten_position` is the central flatten path.** Verify Session 1b's change to `_flatten_position` propagates through:
   - EOD Pass 1 callers
   - `close_position()` API caller
   - `emergency_flatten()` caller
   - Time-stop exit caller

   Each upstream caller should see the OCA threading "for free" via the `_flatten_position` change.

## Sprint-Level Regression Checklist (for @reviewer)

The full Sprint-Level Regression Checklist is in
`docs/sprints/sprint-31.91-reconciliation-drift/review-context.md`.

Of particular relevance to Session 1b:

- **Invariant 1 (DEF-199 A1 fix detects + refuses 100% of phantom shorts at EOD):** PASS — verify zero edits to `order_manager.py:1670-1750`.
- **Invariant 3 (DEF-158 dup-SELL prevention works for the ARGUS=N, IBKR=N normal case):** PASS — Session 1b's Error 201 graceful handling must NOT regress this. The dup-SELL prevention runs in `_check_flatten_pending_timeouts`, which Session 3 modifies; Session 1b only changes the upstream `_flatten_pending` queueing on Error 201.
- **Invariant 5 (5,080 pytest baseline holds):** PASS.
- **Invariant 14 (Monotonic-safety property):** Row "After Session 1b" — OCA bracket = YES, OCA standalone (4) = YES, all others = NO.
- **Invariant 15 (do-not-modify list untouched):** PASS — verify the explicit list above.
- **Invariant 21 (SimulatedBroker OCA-assertion tautology guard):** Lands at Session 0 close-out; verify still passing.

## Sprint-Level Escalation Criteria (for @reviewer)

Of particular relevance to Session 1b:

- **A2** (Tier 2 CONCERNS or ESCALATE).
- **A4** (OCA-group ID lifecycle interacts with re-entry in a way the lifecycle tests didn't model — Session 1b touches the lifecycle's exit side).
- **B1, B3, B4, B6** — standard halt conditions.
- **C7** (grep regression guard false-positives on a legitimate exempt site) — add `# OCA-EXEMPT: <reason>` comment; do NOT remove the guard.

---

*End Sprint 31.91 Session 1b implementation prompt.*
