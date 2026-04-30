# Tier 2 Review: Sprint 31.92, Session S2a

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end,
fenced with ` ```json:structured-verdict `. See the review skill for the full
schema and requirements.

**Write the review report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s2a-path1-trail-flatten-review.md
```

Create the file, write the full report (including the structured JSON
verdict) to it, and commit it. This is the ONE exception to "do not modify
any files" — the review report file is the sole permitted write.

## Pre-Flight

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this review.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt — particularly **RULE-013** (read-only mode), **RULE-038** (grep-verify factual claims), **RULE-050** (CI green required), **RULE-051** (mechanism-vs-symptom validation), **RULE-053** (architectural-seal verification — DEC-117 atomic-bracket invariants, DEC-385 6-layer reconciliation, DEC-386 4-layer OCA architecture all sealed).

## Review Context

Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist (34 invariants), and Sprint-Level Escalation Criteria:

```
docs/sprints/sprint-31.92-def-204-round-2/review-context.md
```

## Tier 1 Close-Out Report

Read the close-out report from:

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s2a-path1-trail-flatten-closeout.md
```

(Per RULE-038, grep-verify the actual closeout filename if not present at the expected path — the corresponding impl prompt references `session-2a-closeout.md` as a candidate alternative. If neither file exists, flag as CONCERNS — the close-out report is required for review.)

## Review Scope

- **Diff to review:** `git diff HEAD~1` (or specify the correct range if the close-out cites multiple commits).
- **Test command** (non-final session, scoped per DEC-328):
  ```
  python -m pytest tests/execution/order_manager/ -n auto -q
  ```
- **Files that should NOT have been modified:**
  - `argus/execution/order_manager.py::_handle_oca_already_filled` (DEC-386 S1b SAFE-marker path).
  - `argus/execution/order_manager.py::reconstruct_from_broker` (entire body — Sprint 31.94 D1 surface).
  - `argus/execution/order_manager.py::reconcile_positions` (Pass 1 + Pass 2 — DEC-385 L3 + L5).
  - `argus/execution/order_manager.py::_check_flatten_pending_timeouts` (DEF-158 3-branch side-check).
  - `argus/execution/order_manager.py::_resubmit_stop_with_retry` (S2b's surface).
  - `argus/execution/order_manager.py::_escalation_update_stop` (S2b's surface).
  - `argus/execution/order_manager.py::_check_sell_ceiling`, `_reserve_pending_or_fail` (S4a-i surfaces).
  - `argus/execution/ibkr_broker.py::place_bracket_order` (DEC-386 S1a OCA threading).
  - `argus/execution/ibkr_broker.py::_is_oca_already_filled_error` / `_OCA_ALREADY_FILLED_FINGERPRINT`.
  - `argus/main.py` — entire file (Sprint 31.94 D1+D2 surfaces).
  - `argus/models/trading.py::Position` class.
  - `argus/execution/alpaca_broker.py` (Sprint 31.95 retirement scope).
  - `argus/data/alpaca_data_service.py`.
  - `argus/core/health.py` — `HealthMonitor` consumer + `POLICY_TABLE`.
  - `argus/ui/`, `frontend/` (Vitest must remain at 913).
  - `workflow/` submodule (Universal RULE-018).

## Session-Specific Review Focus

1. **AC1.1 + AC1.2 — mechanism-conditional H2/H4/H1 implementation correctness.** Verify the implemented mechanism in `_trail_flatten` matches S1a's `selected_mechanism` field from `scripts/spike-results/spike-def204-round2-path1-results.json`. If H2 was selected, confirm `IBKRBroker.modify_order` is called BEFORE any `place_order(SELL)` invocation; if H4, confirm `cancel_all_orders(symbol, await_propagation=True)` is the rejection-fallback before SELL; if H1, confirm `cancel_all_orders` is called BEFORE SELL unconditionally. **The mechanism's correctness is the entire sprint's CRITICAL safety property.** Per RULE-051, validate against the mechanism signature (mechanism dispatch ordering) not the symptom aggregate (no overflatten in synthetic trace).

2. **AC1.4 — AMD-8 + AMD-4 + `_handle_oca_already_filled` byte-for-byte preservation.** Inspect the diff line-by-line:
   - AMD-8 guard (complete no-op if `_flatten_pending` already set) preserved.
   - AMD-4 guard (no-op if `shares_remaining ≤ 0`) preserved.
   - `_handle_oca_already_filled` short-circuit (DEC-386 S1b SAFE-marker path) preserved verbatim.
   The mechanism dispatch should be a clean replacement of the cancel/SELL block; surrounding guards untouched.

3. **AC1.5 — AMD-2 mechanism-conditional framing.** Verify the framing (preserved / mixed / superseded) matches the chosen mechanism in the close-out's "Mechanism Selected" section AND in the test 6 (`test_path1_amd2_invariant_per_mechanism`) docstring:
   - H2 → AMD-2 preserved (no SELL emission at all because the stop is amended, not replaced).
   - H4 → success branch preserves AMD-2 (no SELL); fallback branch asserts AMD-2-prime (cancel propagates BEFORE SELL).
   - H1 → AMD-2 superseded; assert cancel-and-await BEFORE SELL ordering.

4. **AC1.6 (conditional) — operator-audit logging conditionality.** If H1 or H4 selected, confirm test 7 is present + green AND the structured log line emits `mechanism="h1_cancel_and_await"` (under H1) or `mechanism="h4_fallback"` (under H4 fallback path). Required keys: `event="amd2_supersede"`, `symbol`, `position_id`, `mechanism`, `cancel_propagation_ms`. If H2 selected, confirm test 7 is skipped with reason and no logging code was added (preserves H2's no-AMD-2-supersede property).

5. **M-R3-3 precondition check disposition.** Verify the close-out documents either:
   - An existing serialization site found at `<file>:<func>`, OR
   - A documented in-session mitigation applied at `<site>` (per-position `asyncio.Lock` keyed by `position.id`, ≤10 LOC), OR
   - A halted-and-resumed-with-operator-approval outcome.
   If the operator approved an in-session lock addition, verify the lock is keyed by `position.id` and the LOC count is ≤10.

6. **Cross-session field-shape agreement on `halt_entry_until_operator_ack`.** S2a's tests may reference the field even though production-side addition is S3b's surface. Verify the close-out documents the field-shape approach (test fixture creates the field at test time vs. assumed-from-S3b). Cross-session field-shape agreement is load-bearing for S2b's seventh test.

7. **DEC-117 + DEC-386 byte-for-byte preservation.** Per A-class halt **A10**, if the chosen mechanism breaks DEC-117 atomic-bracket invariants, halt. Per RULE-053, DEC-386's 4-layer OCA architecture is sealed — `_handle_oca_already_filled`, `place_bracket_order`, `_is_oca_already_filled_error` must remain byte-for-byte. The reviewer's most critical structural check.

8. **Anti-tautology check on test 1 (`test_path1_canonical_bitu_race_no_overflatten`).** Verify the test uses an IBKR mock or SimulatedBroker fixture that ACTUALLY exercises the trail-flatten dispatch path; assert `total_sold ≤ position.shares_total` as a measurement of the mechanism's effect, not just as a tautology against `total_sold = 0` because no SELL ever fired (which would be a false-pass).

## Additional Context

This is the first implementation session on the Path #1 hot path (`_trail_flatten`). The session establishes the AMD-2 mechanism-conditional framing for the entire sprint per AC1.5, and (under H1/H4) the AC1.6 operator-audit logging contract that S2b extends to the emergency-flatten surface. Sprint 31.92 is a **CRITICAL safety** sprint; bias toward CONCERNS over CLEAR when in doubt. Per RULE-053, DEC-117 / DEC-385 / DEC-386 are architecturally sealed — verify no diff touches the seal boundary.

The full Sprint-Level Regression Checklist (34 invariants) is in `docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md`. S2a is ✓-mandatory for invariants **1, 2, 5, 6, 9, 10, 11, 12, 17** (ESTABLISHES) and ✓¹-conditional for invariant **22** (MANDATORY only if H1 or H4 selected).

The full Sprint-Level Escalation Criteria are in `docs/sprints/sprint-31.92-def-204-round-2/escalation-criteria.md`. Most relevant to S2a: A-class halts **A4** (DEC-385/386/388 surface modified), **A5** (DEF-158 side-check modified), **A6** (CONCERNS/ESCALATE verdict), **A9** (Path #1 spike measures ≥20% Wilson UB — pre-empted by Pre-Flight #6, defensive), **A10** (DEC-117 atomic-bracket broken); B-class halts **B1**, **B3**, **B4**, **B5** (anchor mismatch), **B6** (do-not-modify file in diff), **B8** (frontend modified); C-class halts **C1**, **C5** (do-not-modify boundary uncertainty).
