<!-- workflow-version: 1.2.0 -->
# Tier 2 Review: Sprint 31.92, Session S4a-ii — Synchronous-Update Invariant on All Bookkeeping Paths + FAI #8 Reflective-Call AST + FAI #11 Callsite-Enumeration Exhaustiveness

## Instructions

You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

**Write the review report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s4a-ii-review.md
```

Create the file, write the full report (including the structured JSON
verdict) to it, and commit it. This is the ONE exception to "do not
modify any files" — the review report file is the sole permitted write.

## Pre-Flight

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this review.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt — particularly RULE-013 (read-only mode), RULE-038 (grep-verify factual claims), RULE-043 (`except Exception:` swallowing test signals — load-bearing when scrutinizing AST guards that catch exceptions), RULE-046 (no `Test*`-prefixed non-test classes — load-bearing if AST helpers are organized into classes), RULE-048 (verify library-behavior side-effects empirically — load-bearing for AST-walk semantics), and RULE-050 (CI green precondition).

## Review Context

Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-31.92-def-204-round-2/review-context.md`

## Tier 1 Close-Out Report

Read the close-out report from:

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s4a-ii-closeout.md
```

If the close-out file does not exist, flag this as CONCERNS — the close-out report is required for review per DEC-330.

## Review Scope

- **Diff to review:** `git diff HEAD~1` (or `git diff HEAD~2..HEAD` if the FAI #11 materialization commit is separate from the implementation commit; confirm the actual range during review).
- **Test command** (DEC-328 — non-final session, scoped):
  ```
  python -m pytest tests/execution/order_manager/ -n auto -q
  ```
- **Files that should NOT have been modified:**
  - `argus/execution/order_manager.py` UNLESS static-analysis surfaced a synchronous-update invariant violation in a callback path; in which case ≤30 LOC surgical fix only, in the specific failing callback path. Preferred outcome is ZERO production-code change.
  - `argus/main.py` (A-class halt A12)
  - `argus/execution/ibkr_broker.py`
  - `argus/execution/simulated_broker.py`
  - `argus/core/risk_manager.py` (S3b owned this surface)
  - `argus/api/routes/positions.py`, `scripts/clear_position_halt.py` (S3b owned)
  - `argus/core/alert_auto_resolution.py` (S4a-i owned the POLICY_TABLE 14th entry; S4a-ii must NOT touch)
  - `argus/models/trading.py`
  - `argus/execution/alpaca_broker.py`
  - `argus/data/alpaca_data_service.py`
  - `frontend/`, `argus/ui/` (regression invariant 12 / B-class halt B8)
  - `workflow/` submodule (RULE-018)

## Session-Specific Review Focus

1. **AST guard soundness — the pair-wise pattern.** Each synchronous-update invariant test pairs an AST-no-await scan with a mocked-await injection check. The pair is what makes the guard SOUND: without injection, the AST scan could be passing because the function body is shaped differently than expected. Verify each of tests 1–5 has BOTH parts (AST scan AND injection assertion); a test with only one part is suspect. Tier 3 items A + B / FAI entry #9 are the binding scope.

2. **Reflective-call AST coverage scope (Decision 3 / FAI #8 option (a)).** Verify tests 6–8 use synthetic SOURCE STRINGS fed into `ast.parse`, NOT attempts to instrument production code. The reflective-call sub-tests are checking the AST SCANNER'S coverage, not asserting that production code uses these patterns (production code should NOT use them; the test is the structural defense against future drift). Three sub-tests required:
   - Test 6: `**kw` unpacking pattern.
   - Test 7: computed-value flag assignment pattern.
   - Test 8: `getattr` reflective access pattern.
   Operator decided option (a) detection-with-flag over option (b) accept-and-document; verify all 3 sub-tests assert the AST scanner FLAGS the synthetic call (not silently accepts).

3. **FAI #11 exhaustiveness scope (Round 3 H-R3-5 / regression invariant 29).** Verify `test_bookkeeping_callsite_enumeration_exhaustive` walks `OrderManager`'s ENTIRE source (`inspect.getsource(OrderManager)`), not just specific functions. The point is to catch a NEW mutation site added in a future sprint without updating the FAI #9 protected list. Verify the `PROTECTED_CALLSITES` set in the test matches FAI #9's enumerated list exactly (`_reserve_pending_or_fail`, `on_fill`, `on_cancel`, `on_reject`, `_on_order_status`, `_check_sell_ceiling`, `reconstruct_from_broker`).

4. **M-R3-4 helper-AST test correctness (regression invariant 30).** Verify `test_no_await_between_refresh_and_read_in_read_positions_post_refresh` asserts EXACTLY 1 `ast.Await` in `_read_positions_post_refresh`. If the helper has been refactored to inline the refresh-then-read sequence at multiple call sites, the helper itself may have been removed — in which case the test should be removed or refactored to scan the inlined call sites. Document such drift in close-out's RULE-038 section.

5. **Static-analysis findings disclosure.** The close-out's "Static-Analysis Findings" section is the structural defense against silent production-code drift. Verify the close-out documents:
   - Each callback path inspected (`on_fill` partial-fill, `on_fill` full-fill, `on_cancel`, `on_reject`, `_on_order_status` if it qualifies, `_check_sell_ceiling` multi-attribute read, `_read_positions_post_refresh`).
   - Pass/fail for each.
   - If any failure: the surgical fix landed in this session (≤30 LOC, single function).
   - The total production-code LOC change (target: 0; max: ≤30 — anything more is scope creep, RULE-007).

6. **`except Exception:` pattern check (RULE-043).** AST guard tests can be subtle — verify NO test catches `Exception` broadly in a way that could mask `pytest.fail` or assertion errors. Each test's exception handling should be narrow (specific exception types only).

7. **`Test*` class collection check (RULE-046).** If the AST helpers are organized into classes (e.g., a `TestASTVisitor`-style visitor), verify they have `__test__ = False` so pytest doesn't try to collect them as test classes. The synchronous-update invariant tests themselves are functions, not classes, per the existing `tests/execution/order_manager/` style — verify alignment.

8. **FAI #11 materialization timing (close-out doc-side commit).** Verify the doc commit (`falsifiable-assumption-inventory.md` 10 → 11 entries) happened AFTER the implementation commit AND only when the regression test was green. Verify the FAI inventory's preamble line was updated `## Inventory (10 entries)` → `## Inventory (11 entries)`. Verify the pending-FAI-#11 subsection had FAI #11 removed (FAI #10 should also have been removed at S3b close); if both pending entries are now materialized, the subsection should either be empty or removed entirely per operator preference.

9. **M-R2-5 mid-sprint Tier 3 trigger metadata in structured close-out JSON.** Verify the structured close-out JSON includes the M-R2-5 trigger metadata (or a prose-form fallback if the schema doesn't accommodate the key). The runner / work-journal needs this signal to pause for M-R2-5 BEFORE S4b begins. Suggested key shape: `"mid_sprint_tier_3_required": true`, `"mid_sprint_tier_3_id": "M-R2-5"`. Absence is a CONCERNS-level finding; it gates whether S4b/S5a/S5b/S5c proceed.

10. **Production-code change conditional ≤30 LOC.** If static-analysis surfaced a synchronous-update violation, verify the surgical fix is:
    - In ONE specific failing callback path only (no drive-by improvements per RULE-007).
    - Net ≤30 LOC.
    - Disclosed in close-out's "Static-Analysis Findings" section.
    - Not touching `reconstruct_from_broker` body, DEF-199 A1 region, DEF-158 3-branch side-check, or any A-class halt boundary.

## Sprint-Level Regression Checklist (for @reviewer)

The full Sprint-Level Regression Checklist is in `docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md`.

✓-mandatory at S4a-ii per the Per-Session Verification Matrix:

- **Invariant 10 (test count baseline holds):** PASS — test count ≥ S4a-i baseline; +7 effective new tests.
- **Invariant 11 (pre-existing flake count):** PASS — DEF-150/167/171/190/192.
- **Invariant 12 (frontend immutability):** PASS — zero UI scope.
- **Invariant 13 (SELL-volume ceiling pending+sold pattern):** EXTENDED — synchronous-update invariant scope now covers all 5 bookkeeping callback paths.
- **Invariant 20 (Pending-reservation state transitions):** EXTENDED — AST regression infrastructure validates all 5 transitions structurally.
- **Invariant 23 (synchronous-update invariant on all bookkeeping callback paths + reflective-pattern AST):** ESTABLISHES — primary deliverable. Verify 5 synchronous-update invariant tests + 3 reflective-call sub-tests + DEF-FAI-CALLBACK-ATOMICITY closure path + DEF-FAI-8-OPTION-A closure path.
- **Invariant 29 (bookkeeping callsite-enumeration AST exhaustiveness):** ESTABLISHES — `test_bookkeeping_callsite_enumeration_exhaustive` walks `ast.AugAssign` and asserts subset of FAI #9 protected list.
- **Invariant 30 (`_read_positions_post_refresh` helper AST scan):** ESTABLISHES — `test_no_await_between_refresh_and_read_in_read_positions_post_refresh` confirms exactly 1 `ast.Await` in helper body.

## Visual Review (N/A — backend-only)

S4a-ii is backend-only. No frontend changes per regression invariant 12.

## Additional Context

**M-R2-5 MID-SPRINT TIER 3 ARCHITECTURAL REVIEW IS THE NEXT EVENT AFTER THIS TIER 2 REVIEW.** S4a-ii is the trigger session for M-R2-5.

After this Tier 2 review verdict is rendered (CLEAR / CONCERNS_RESOLVED), the M-R2-5 mid-sprint Tier 3 architectural review is invoked in a SEPARATE Claude.ai conversation BEFORE S4b begins. The Tier 3 review is distinct from this Tier 2 review:

- **Tier 2 (this review):** code-level + spec-conformance.
- **Tier 3 (mid-sprint, separate):** architectural-closure cross-validation of:
  - Pending-reservation pattern (H-R2-1 atomic method).
  - Ceiling guards at 5 standalone-SELL emit sites (S4a-i lands canonical at `_trail_flatten`; remaining 4 deferred to S5b composite).
  - `is_reconstructed` refusal posture (AC3.7) field + short-circuit landed at S4a-i.
  - Callback-path atomicity invariant (Tier 3 items A + B / FAI entry #9) — primary S4a-ii deliverable.
  - Reflective-call AST coverage (Decision 3 / FAI #8 option (a)) — primary S4a-ii deliverable.
  - AC2.7 watchdog auto-activation (Decision 4) landed at S4a-i.
  - C-R3-1 Fix A serialization closure (proportional re-review per round-3-disposition § 1.4).

The Tier 3 verdict (PROCEED / REVISE_PLAN / PAUSE_AND_INVESTIGATE) gates whether S4b proceeds.

The Tier 2 reviewer's task (this review) is to flag whether the close-out provides sufficient material for the Tier 3 reviewer. Specifically: cumulative diff at this checkpoint should be ~600–800 LOC on `argus/execution/order_manager.py`, well below the recalibrated ~1200–1350 cumulative bound. Disclose the actual measured cumulative-diff LOC count in the verdict so the Tier 3 reviewer can plan their session scope. If the close-out's structured JSON does NOT signal `mid_sprint_tier_3_required: true`, this is a procedure-gate finding that must be raised under CONCERNS.
