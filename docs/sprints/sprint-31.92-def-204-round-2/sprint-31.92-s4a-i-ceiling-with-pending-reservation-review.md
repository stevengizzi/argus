<!-- workflow-version: 1.2.0 -->
# Tier 2 Review: Sprint 31.92, Session S4a-i — Long-Only SELL-Volume Ceiling with Pending Reservation (H-R2-1 Atomic Method) + AC2.7 Watchdog Auto-Activation

## Instructions

You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

**Write the review report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s4a-i-review.md
```

Create the file, write the full report (including the structured JSON
verdict) to it, and commit it. This is the ONE exception to "do not
modify any files" — the review report file is the sole permitted write.

## Pre-Flight

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this review.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt — particularly RULE-013 (read-only mode) which governs the entire review session, RULE-038 (grep-verify factual claims at session start), RULE-042 (`getattr` silent-default anti-pattern — relevant when scrutinizing `_reserve_pending_or_fail`), RULE-050 (CI green precondition), and RULE-053 (architectural-seal verification — DEC-117 / DEC-369 / DEC-385 / DEC-386 / DEC-388 are sealed defenses).

## Review Context

Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-31.92-def-204-round-2/review-context.md`

## Tier 1 Close-Out Report

Read the close-out report from:

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s4a-i-closeout.md
```

If the close-out file does not exist, flag this as CONCERNS — the close-out report is required for review per DEC-330.

## Review Scope

- **Diff to review:** `git diff HEAD~1`
- **Test command** (DEC-328 — non-final session, scoped):
  ```
  python -m pytest tests/execution/order_manager/ tests/api/test_policy_table_exhaustiveness.py -n auto -q
  ```
- **Files that should NOT have been modified:**
  - `argus/main.py`
  - `argus/execution/order_manager.py::reconstruct_from_broker` BODY beyond the single-line `is_reconstructed = True` addition + the AC3.6 zero-counter / `shares_total = abs(broker_position.shares)` initialization fix
  - `argus/execution/order_manager.py` DEF-158 3-branch side-check inside `_check_flatten_pending_timeouts` (regression invariant 8 / A-class halt A5)
  - `argus/execution/order_manager.py` DEF-199 A1 fix region (regression invariant 1)
  - `argus/execution/ibkr_broker.py` (any modification — DEC-386 S1a/S1b OCA threading sealed)
  - `argus/execution/simulated_broker.py` (semantic preservation per SbC §"Do NOT modify" #2)
  - `argus/models/trading.py`
  - `argus/execution/alpaca_broker.py`
  - `argus/data/alpaca_data_service.py`
  - `frontend/`, `argus/ui/` (regression invariant 12 / B-class halt B8)
  - `workflow/` submodule (RULE-018)

## Session-Specific Review Focus

1. **Synchronous-update invariant on the place-time path (AC3.1 state transition #1 / H-R2-1).** Verify `_reserve_pending_or_fail`'s body is synchronous from the read of `cumulative_pending_sell_shares` to the write of the increment. The AST guard test (`test_no_await_in_reserve_pending_or_fail_body`) is the structural defense; verify it walks `ast.parse(textwrap.dedent(inspect.getsource(...)))` on the actual implementation, not a mocked stand-in. The mocked-await injection companion test (`test_reserve_pending_or_fail_race_observable_under_injection`) is what makes the guard SOUND — without injection, the AST scan could be passing because the function body is shaped differently than expected.

2. **Field-ownership clarity (S3b vs S4a-i).** Verify `halt_entry_until_operator_ack` is added EXACTLY ONCE — either at S3b (per S3b's prompt) or at S4a-i (if S3b didn't land it). The S4a-i close-out's "field-ownership disclosure" should explicitly state which session added each of the 4 new fields (`cumulative_pending_sell_shares`, `cumulative_sold_shares`, `is_reconstructed`, `halt_entry_until_operator_ack`). Double-add or missing-add is a CONCERNS-level finding.

3. **AC3.7 `is_reconstructed` refusal short-circuit position.** In `_reserve_pending_or_fail` AND `_check_sell_ceiling`, the `is_reconstructed` check MUST occur BEFORE the counter math. If a reconstructed position with `pending=0, sold=0, total=10, requested=5` reaches the method, it returns False — NOT True (the math would technically allow). This short-circuit is the structural defense per regression invariant 19. Refusal-posture regression test for ALL 4 standalone-SELL paths lives at S5b — at S4a-i verify the field+short-circuit are wired correctly.

4. **AC3.6 broker-confirmed initialization composes additively with DEC-369.** A-class halt A8 is the boundary. Verify `reconstruct_from_broker`-derived positions:
   - Initialize `cumulative_pending_sell_shares = 0` (dataclass default suffices).
   - Initialize `cumulative_sold_shares = 0` (dataclass default suffices).
   - Set `is_reconstructed = True` (the single-line addition).
   - Have `shares_total = abs(broker_position.shares)` (existing initialization preserved).
   - DEC-369 reconciliation immunity is NOT removed — both protections apply additively.
   The single-line addition + the initialization fix are the ONLY permitted edits to `reconstruct_from_broker` BODY at S4a-i; any broader edit fires A12.

5. **AC2.7 watchdog auto-activation atomicity (Decision 4 / H-R3-2).** Verify:
   - `self._watchdog_state_lock` is `asyncio.Lock`, not `threading.Lock`.
   - The flip is guarded by `async with self._watchdog_state_lock:`.
   - Re-entrant flips are no-ops (the inside-lock check `if self._watchdog_enabled_state != "auto": return` covers this).
   - The structured log line uses `extra={"event": "watchdog_auto_to_enabled", "case_a_evidence": {...}}` shape (operator-visible).
   - Restart resets to `"auto"` — the field is in-memory only, not persisted (verify by inspecting `__init__` initialization vs SQLite/file load — the field MUST NOT round-trip through any persistence path).

6. **POLICY_TABLE 14th entry shape (AC3.9 / regression invariant 7).** Verify the `sell_ceiling_violation` entry uses `operator_ack_required=True` and `auto_resolution_predicate=None` (NEVER_AUTO_RESOLVE). The DEF-219 AST exhaustiveness regression guard at `tests/api/test_policy_table_exhaustiveness.py` is the structural defense; verify it's updated 13 → 14 AND additionally asserts the new key's presence (mental-revert sanity: removing the entry from the production table fails the test).

7. **C-1 race test soundness (canonical AC3.5 race coverage).** Test 5 (`test_concurrent_sell_emit_race_blocked_by_pending_reservation`) is the canonical race test for AC3.5. Verify the test:
   - Actually exercises two coroutines on the SAME `ManagedPosition`.
   - The second coroutine's `_reserve_pending_or_fail` call sees the first's reservation (proves the synchronous-update invariant works for the protected path).
   - The mocked broker observes ONLY ONE `place_order` invocation.
   - The second coroutine's path emits `sell_ceiling_violation` with the expected metadata.

8. **Bracket placement is NOT ceiling-checked (AC3.2 + SbC §"Edge Cases to Reject" #15).** Verify that `place_bracket_order` (or the equivalent bracket-placement entry point) does NOT call `_reserve_pending_or_fail` or `_check_sell_ceiling`. Bracket-children placement is governed by DEC-117 atomicity, not by the per-emit ceiling.

9. **H-R2-5 stop-replacement exemption is ONLY at `_resubmit_stop_with_retry` normal-retry path.** Verify the `is_stop_replacement: bool = False` parameter on `_reserve_pending_or_fail` and `_check_sell_ceiling` is NOT being used at S4a-i's canonical site (`_trail_flatten`). The exemption is reserved for `_resubmit_stop_with_retry`'s normal-retry path (NOT the emergency-flatten branch); that wiring lands at S5b composite per session-breakdown. At S4a-i the parameter is plumbed through but used only by tests/diagnostics; production usage is at S5b.

10. **One canonical emit site only at S4a-i.** Per session-breakdown's option-δ-prime mitigation, only `_trail_flatten` carries the ceiling guard at S4a-i. The remaining 4 sites (`_escalation_update_stop`, `_resubmit_stop_with_retry`, `_flatten_position`, `_check_flatten_pending_timeouts`) get the SAME guard at S5b composite. Verify S4a-i's diff includes the guard at exactly ONE site, not all 5.

11. **Watchdog auto-activation idempotency.** Verify Test 7's idempotency check exercises the second `case_a_in_production` event — the flip must NOT re-fire and the structured log line must NOT re-emit. This is the structural defense for H-R3-2.

## Sprint-Level Regression Checklist (for @reviewer)

The full Sprint-Level Regression Checklist is in `docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md`.

✓-mandatory at S4a-i per the Per-Session Verification Matrix:

- **Invariant 1 (DEC-117 atomic bracket):** PASS — bracket placement explicitly excluded from ceiling check (AC3.2).
- **Invariant 3 (DEC-369 broker-confirmed immunity):** PASS — composes additively with `is_reconstructed=True` per AC3.6.
- **Invariant 5 (DEC-385 6-layer side-aware reconciliation):** PASS — `phantom_short_retry_blocked` emitter unchanged.
- **Invariant 6 (DEC-386 4-layer OCA architecture):** PASS — bracket OCA threading unchanged at S4a-i.
- **Invariant 7 (DEC-388 alert observability):** ESTABLISHES — POLICY_TABLE 14th entry + AST exhaustiveness regression guard updated.
- **Invariant 9 (`# OCA-EXEMPT:` mechanism):** PASS — preserved.
- **Invariant 10, 11, 12:** PASS — test count ≥ baseline (S3b + ~7 new); pre-existing flake count unchanged; frontend immutable.
- **Invariant 13 (SELL-volume ceiling pending+sold pattern):** ESTABLISHES — canonical site at `_trail_flatten`.
- **Invariant 19 (`is_reconstructed` refusal posture):** ESTABLISHES — field added; short-circuit on `is_reconstructed=True`.
- **Invariant 20 (Pending-reservation state transitions):** ESTABLISHES — all 5 state transitions wired.
- **Invariant 26 (AC2.7 watchdog auto-activation):** ESTABLISHES — auto-flip from `auto` to `enabled`; in-memory only; asyncio.Lock-guarded; idempotent; logged.

## Visual Review (N/A — backend-only)

S4a-i is backend-only. No frontend changes per regression invariant 12.

## Additional Context

- This is the first of two paired sessions (S4a-i + S4a-ii) implementing the long-only SELL-volume ceiling. S4a-i lays the groundwork (atomic-reserve method + canonical site + watchdog auto-activation); S4a-ii extends the AST regression infrastructure to ALL bookkeeping callback paths and adds the FAI #11 callsite-enumeration exhaustiveness guard.
- M-R2-5 mid-sprint Tier 3 architectural review fires AFTER S4a-ii (NOT after S4a-i). At S4a-i, no Tier 3 trigger is expected.
- Operator daily-flatten mitigation (`scripts/ibkr_close_all_positions.py`) remains in effect throughout Sprint 31.92 until cessation criterion #5 (5 paper sessions clean post-seal) is satisfied.
