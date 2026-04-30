# Tier 2 Review: Sprint 31.92, Session S2b

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end,
fenced with ` ```json:structured-verdict `. See the review skill for the full
schema and requirements.

**Write the review report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s2b-path1-emergency-flatten-review.md
```

Create the file, write the full report (including the structured JSON
verdict) to it, and commit it. This is the ONE exception to "do not modify
any files" — the review report file is the sole permitted write.

## Pre-Flight

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this review.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt — particularly **RULE-013** (read-only mode), **RULE-038** (grep-verify factual claims), **RULE-050** (CI green required), **RULE-051** (mechanism-vs-symptom validation), **RULE-053** (architectural-seal verification — DEC-117 atomic-bracket, DEC-372 retry caps + backoff, DEC-385 6-layer reconciliation, DEC-386 4-layer OCA architecture, DEF-158 3-branch side-check all sealed).

## Review Context

Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist (34 invariants), and Sprint-Level Escalation Criteria:

```
docs/sprints/sprint-31.92-def-204-round-2/review-context.md
```

## Tier 1 Close-Out Report

Read the close-out report from:

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s2b-path1-emergency-flatten-closeout.md
```

(Per RULE-038, grep-verify the actual closeout filename if not present at the expected path — the corresponding impl prompt references `session-2b-closeout.md` as a candidate alternative. If neither file exists, flag as CONCERNS — the close-out report is required for review.)

## Review Scope

- **Diff to review:** `git diff HEAD~1` (or specify the correct range if the close-out cites multiple commits).
- **Test command** (non-final session, scoped per DEC-328):
  ```
  python -m pytest tests/execution/order_manager/ -n auto -q
  ```
- **Files that should NOT have been modified:**
  - `argus/execution/order_manager.py::_handle_oca_already_filled` (DEC-386 S1b).
  - `argus/execution/order_manager.py::_trail_flatten` (S2a's surface — preserved at S2b).
  - `argus/execution/order_manager.py::reconstruct_from_broker` (Sprint 31.94 D1 surface).
  - `argus/execution/order_manager.py::reconcile_positions` (DEC-385 L3 + L5).
  - `argus/execution/order_manager.py::_check_flatten_pending_timeouts` (DEF-158 3-branch side-check, lines ~3424–3489).
  - `argus/execution/order_manager.py::_check_sell_ceiling`, `_reserve_pending_or_fail` (S4a-i surfaces).
  - `argus/execution/order_manager.py::_locate_suppressed_until`, `_is_locate_suppressed` (S3a surfaces).
  - `argus/execution/ibkr_broker.py::place_bracket_order`, `_is_oca_already_filled_error`.
  - `argus/main.py` — entire file (Sprint 31.94 D1+D2 surfaces).
  - `argus/models/trading.py::Position` class.
  - `argus/execution/alpaca_broker.py` (Sprint 31.95 retirement scope).
  - `argus/data/alpaca_data_service.py`.
  - `argus/core/health.py` — `HealthMonitor` consumer + `POLICY_TABLE`.
  - `argus/ui/`, `frontend/` (Vitest must remain at 913).
  - `workflow/` submodule (Universal RULE-018).

## Session-Specific Review Focus

1. **AC1.3 — extension to `_resubmit_stop_with_retry` emergency-flatten branch + conditionally `_escalation_update_stop`.** Verify the emergency-flatten branch dispatches via S2a's mechanism (chosen from S1a `selected_mechanism`). Verify the `_escalation_update_stop` applicability decision (Pre-Flight #7) is documented in the close-out's "Applicability Decision" section, citing the actual S1a JSON field value (not a guess); test 3 is either green-and-applied OR skipped-with-reason; the function body change is consistent with the decision.

2. **S2a mechanism reuse, not re-implementation.** Verify `_resubmit_stop_with_retry` emergency-flatten branch reuses S2a's mechanism helper (if S2a introduced `_amend_or_fallback()` for H4) rather than re-implementing the dispatch logic. Cross-session helper reuse keeps the sprint's diff bound under control AND ensures any future fix to the helper propagates to both call sites.

3. **DEC-372 retry-cap + backoff preservation.** Verify test 6 (`test_path1_dec372_backoff_unchanged`) is green AND the canary `test_stop_resubmission_cap` is green. The mechanism dispatch fires ONLY at cap exhaustion; normal retries 1+2+3 do NOT trigger the new mechanism. Inspect the diff line-by-line for any unintended change to retry-loop timing. Per RULE-053, DEC-372 (3 retries; 1s/2s/4s backoff) is sealed.

4. **AC1.6 operator-audit logging extends consistently.** If H1/H4 selected, verify the seventh test fires the SAME structured log line (same keys, same format) that S2a established. The mechanism field discriminates between `"h1_cancel_and_await"` (last-resort) and `"h4_fallback"` (hybrid fallback). Required keys carry over from S2a: `event="amd2_supersede"`, `symbol`, `position_id`, `mechanism`, `cancel_propagation_ms`.

5. **H-R2-2 HALT-ENTRY tests against future S3b/S4a-i field.** Verify test 7 (`test_path1_h1_fallback_locate_reject_halts_entry`) is green under H1/H4 OR SKIPPED with documented reason under H2. The test must drive the locate-rejection through the SELL emission path AND assert `halt_entry_until_operator_ack=True` is set AND `phantom_short_retry_blocked` alert published. If S3b/S4a-i has not yet landed, the test should still be present; either via fixture-time field construction or via skip-with-reason. The cross-session field-shape agreement is load-bearing.

6. **DEC-117 + DEC-386 byte-for-byte preservation on the emergency-flatten surface.** Per A-class halt **A10**, if the chosen mechanism on this surface breaks DEC-117 atomic-bracket invariants, halt. Per RULE-053, DEC-386's 4-layer OCA architecture is sealed. Inspect the diff line-by-line — `_handle_oca_already_filled` short-circuit must continue to fire on the emergency-flatten surface (test 4 + test 5 green).

7. **DEF-158 3-branch side-check verbatim preservation.** Per A-class halt **A5** and regression invariant 8: the BUY → resubmit / SELL → alert+halt / unknown → halt branches in `_check_flatten_pending_timeouts` must remain byte-for-byte. Path #2 detection lands at S3b upstream at `place_order` exception, NOT a 4th branch.

8. **Anti-tautology check on tests 1 + 7.** Verify test 1 (`test_path1_resubmit_stop_emergency_flatten_no_overflatten`) ACTUALLY exercises the emergency-flatten dispatch path (not just the normal-retry path). Verify test 7 ACTUALLY drives the locate-rejection through the SELL emission path AND asserts the `halt_entry_until_operator_ack` field becomes True (not just that no SELL fires for unrelated reasons). Per RULE-051, validate against mechanism signature, not symptom aggregate.

## Additional Context

This is the second implementation session on the Path #1 hot path. S2b extends S2a's mechanism (chosen from S1a's `selected_mechanism`) to the emergency-flatten surface (`_resubmit_stop_with_retry` + conditionally `_escalation_update_stop`). The session also tests the H-R2-2 HALT-ENTRY posture under H1-fallback-locate-reject coupling — the cross-session field-shape on `halt_entry_until_operator_ack` (S3b production code) and `phantom_short_retry_blocked` alert (DEC-388) is verified by test 7. Sprint 31.92 is a **CRITICAL safety** sprint; bias toward CONCERNS over CLEAR when in doubt.

The full Sprint-Level Regression Checklist (34 invariants) is in `docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md`. S2b is ✓-mandatory for invariants **1, 2, 4** (DEC-372 — CRITICAL), **5, 6, 9, 10, 11, 12, 17** and ✓¹-conditional for invariant **22** (MANDATORY only if H1 or H4 selected).

The full Sprint-Level Escalation Criteria are in `docs/sprints/sprint-31.92-def-204-round-2/escalation-criteria.md`. Most relevant to S2b: A-class halts **A4** (DEC-385/386/388 surface modified), **A5** (DEF-158 3-branch side-check modified), **A6** (CONCERNS/ESCALATE verdict), **A10** (DEC-117 atomic-bracket broken on emergency-flatten); B-class halts **B1**, **B3**, **B4**, **B5** (anchor mismatch), **B6** (do-not-modify file in diff), **B8** (frontend modified); C-class halts **C1**, **C5** (do-not-modify boundary uncertainty — especially the conditional `_escalation_update_stop` modification approaches the boundary).
