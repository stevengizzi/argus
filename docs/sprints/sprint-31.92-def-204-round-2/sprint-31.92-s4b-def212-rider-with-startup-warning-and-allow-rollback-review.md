<!-- workflow-version: 1.2.0 -->
# Tier 2 Review: Sprint 31.92, Session S4b — DEF-212 Rider + AC4.6 Dual-Channel Startup Warning + AC4.7 `--allow-rollback` CLI Gate per H-R2-4 + Interactive Ack + Periodic Re-Ack + CI-Override Flag per Round 3 H-R3-4

## Instructions

You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

**Write the review report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s4b-review.md
```

Create the file, write the full report (including the structured JSON
verdict) to it, and commit it. This is the ONE exception to "do not
modify any files" — the review report file is the sole permitted write.

## Pre-Flight

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this review.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt — particularly RULE-013 (read-only mode), RULE-038 (grep-verify factual claims), RULE-039 (staged risky-edit flow — load-bearing for the multi-site `_OCA_TYPE_BRACKET` substitution), RULE-050 (CI green precondition), and RULE-053 (architectural-seal verification — DEC-117 atomic-bracket + DEC-386 4-layer OCA architecture are sealed defenses; AC4.5 byte-for-byte preservation is the seal).

## Review Context

Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-31.92-def-204-round-2/review-context.md`

## Tier 1 Close-Out Report

Read the close-out report from:

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s4b-closeout.md
```

If the close-out file does not exist, flag this as CONCERNS — the close-out report is required for review per DEC-330.

## Review Scope

- **Diff to review:** `git diff HEAD~1`
- **Test command** (DEC-328 — non-final session, scoped):
  ```
  python -m pytest tests/execution/order_manager/ tests/test_main.py -n auto -q
  ```
- **Files that should NOT have been modified:**
  - `argus/execution/ibkr_broker.py` (DEC-386 S1a/S1b OCA threading + `_is_oca_already_filled_error` helper preservation — AC4.5 byte-for-byte SEAL)
  - `argus/execution/order_manager.py::_handle_oca_already_filled` (DEC-386 S1b SAFE-marker path)
  - `argus/execution/order_manager.py::reconstruct_from_broker` body (Sprint 31.94 D1 surface)
  - `argus/execution/order_manager.py::reconcile_positions` Pass 1 / Pass 2 (DEC-385 L3 + L5)
  - `argus/execution/order_manager.py::_check_flatten_pending_timeouts` 3-branch side-check (DEF-158)
  - `argus/main.py::check_startup_position_invariant` (Sprint 31.94 D2)
  - `argus/main.py::_startup_flatten_disabled` (Sprint 31.94 D2)
  - `argus/core/config.py::IBKRConfig.bracket_oca_type` Pydantic validator (runtime-flippability preserved per DEC-386 design intent)
  - `argus/core/health.py`, `argus/api/routes/alerts.py`, `argus/api/websocket/alerts_ws.py`
  - `argus/frontend/...`, `argus/ui/` (frontend immutability — invariant 12)
  - DB schemas (`data/operations.db`, `data/argus.db`)
  - DEC-385 / DEC-386 / DEC-388 entries in `docs/decision-log.md`
  - `workflow/` submodule (RULE-018)

  **Modifiable surfaces are ONLY:** `argus/main.py` (with byte-preserved `check_startup_position_invariant` / `_startup_flatten_disabled`) and `argus/execution/order_manager.py` (with byte-preserved `_handle_oca_already_filled`, `reconstruct_from_broker` body, `reconcile_positions`, `_check_flatten_pending_timeouts`, and DEF-199 A1 region).

## Session-Specific Review Focus

1. **Constant deletion completeness (AC4.3 / regression invariant 15).** `grep -c "_OCA_TYPE_BRACKET" argus/execution/order_manager.py` MUST return 0 post-S4b. Any docstring or comment that historically referenced the constant must use `# OCA-EXEMPT: <reason>` per protocol if retained for context. The grep-regression-guard test (`test_no_oca_type_bracket_constant_remains_in_module`) is the structural defense.

2. **4-site migration consistency (AC4.3).** All 4 OCA-thread sites must use `self._bracket_oca_type`. Verify via `grep -c "ocaType = self._bracket_oca_type" argus/execution/order_manager.py` returns exactly 4. The lock-step test (test 4) parametrized over 4 sites × {0, 1} = 8 effective cases is the structural assertion; verify it covers all 4 sites enumerated by the pre-S4b grep.

3. **DEC-386 byte-for-byte preservation (AC4.5).** `argus/execution/ibkr_broker.py::place_bracket_order` MUST show ZERO edits. Verify via `git diff HEAD~1 -- argus/execution/ibkr_broker.py` returning empty. The OCA-threading SEMANTICS flow through `OrderManager` only; `ibkr_broker.py`'s bracket-placement contract is untouched. A-class halt A4 (DEC-385/386/388 do-not-modify violation) and A10 (DEC-117 atomic-bracket invariants broken) fire on regression.

4. **AC4.4 lock-step is a CONSISTENCY assertion, NOT operational validity.** The test docstring for `test_bracket_oca_type_lockstep_preserved_under_rollback` MUST explicitly state: "ocaType=0 disables OCA enforcement and reopens DEF-204; this test asserts the rollback path is consistent, not that the rollback is operationally safe." The test asserts that flipping from 1 to 0 produces consistent `ocaType=0` on bracket children AND on standalone-SELL OCA threading (NO divergence). The lock-step gate is a reviewer guardrail against silently mis-framing the test as proving "rollback is safe."

5. **`OrderManager.__init__` keyword-only argument (AC4.1).** The new `bracket_oca_type` parameter MUST be keyword-only (no default). This forces call-site auditability — verify the construction site in `argus/main.py` passes the value explicitly. A `bracket_oca_type: int = 1` default would silently mask a missing call-site update.

6. **Dual-channel emission BOTH fire under rollback (AC4.6 / H-R2-4).** Test 6 asserts both channels fire. Verify the implementation calls BOTH:
   - Canonical-logger CRITICAL with phrase exactly `"DEC-386 ROLLBACK ACTIVE"`.
   - ntfy.sh `system_warning` urgent emission with topic `argus_system_warnings`.
   A logging-only implementation is the C11 failure mode. If the close-out's Judgment Calls section documents an alternative ntfy.sh implementation (e.g., `urlopen` shim vs. existing helper), verify the dual-channel contract is preserved regardless.

7. **Exit code precision (AC4.7 + H-R3-4).** Three distinct exit codes:
   - `0`: success / `bracket_oca_type=1` no-op (the `--allow-rollback` flag is a no-op when `bracket_oca_type=1` — verify).
   - `2`: no `--allow-rollback` flag AND `bracket_oca_type != 1` → stderr FATAL banner with exact phrase `"DEC-386 ROLLBACK REQUESTED WITHOUT --allow-rollback FLAG. Refusing to start."`.
   - `3`: interactive ack wrong phrase (when TTY detected and ack required).
   Verify each test asserts the exact integer.

8. **Interactive ack TTY detection (H-R3-4 / regression invariant 33).** The interactive prompt MUST only fire when `sys.stdin.isatty()` returns True AND `--allow-rollback-skip-confirm` is absent. The skip-confirm flag is the CI escape hatch; production startup MUST NOT use it (SbC §19). Verify:
   - Test 9 mocks `isatty()` returning True + correct phrase → ARGUS proceeds.
   - Test 10 mocks `isatty()` returning True + wrong phrase → exit 3.
   - Test 11 sets `--allow-rollback-skip-confirm` + `isatty()` returning True → ARGUS proceeds without prompt + canonical-logger CRITICAL emission STILL fires (CI evidence trail preserved).

9. **Periodic re-ack runtime task survival (H-R3-4).** The 4-hour periodic re-ack task MUST be held on `ArgusSystem` (or the equivalent owning surface) so it is not garbage-collected mid-runtime. Verify the task is not left as a dangling local. Test 12's mocked-asyncio.sleep advancement is the structural test; verify it asserts dual-channel emission at each 4-hour boundary with phrase `"DEC-386 ROLLBACK ACTIVE — STILL IN ROLLBACK STATE — N hours since startup"`.

10. **`argus/main.py` exception-clause respect.** SbC §"Do NOT modify" allows S4b to modify the `OrderManager(...)` construction call site to add `bracket_oca_type=...`. Verify the modification is SCOPED to:
    - The single kwarg insertion at the construction site.
    - The new gate-logic block (post-config-load, pre-OrderManager-construction).
    - The new CLI flag parsing (alongside existing argparse).
    - The dual-channel helper + periodic re-ack scheduling.
    NO surrounding logic is touched. `check_startup_position_invariant` and `_startup_flatten_disabled` byte-for-byte unchanged.

11. **Edit manifest exists and was confirmed (RULE-039).** Per the staged-flow Halt step, an edit manifest must exist at `docs/sprints/sprint-31.92-def-204-round-2/s4b-edit-manifest.md`. Verify the manifest exists and that the actual diff matches the manifest's planned edits. Mismatches between manifest and diff are CONCERNS-level findings.

12. **`--allow-rollback-skip-confirm` separation from production startup (SbC §19).** The skip-confirm flag is for CI ONLY. Verify no production startup script (e.g., `scripts/start_live.sh` or equivalent) is modified to pass `--allow-rollback-skip-confirm` — that would silently bypass the operator-acknowledgment requirement.

## Sprint-Level Regression Checklist (for @reviewer)

The full Sprint-Level Regression Checklist is in `docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md` (34 invariants total).

✓-mandatory at S4b per the Per-Session Verification Matrix:

- **Invariant 1 (DEC-117 atomic bracket):** PASS — AC4.5 byte-for-byte preservation.
- **Invariant 5 (DEC-385 6-layer side-aware reconciliation):** PASS — preserved.
- **Invariant 6 (DEC-386 4-layer OCA architecture):** PASS — OCA-threading semantics preserved; only the source of `ocaType` value changes from module constant to instance attribute.
- **Invariant 9 (`# OCA-EXEMPT:` mechanism):** PASS — preserved.
- **Invariant 10 (test count baseline ≥ 5,269):** PASS — target at S4b: 5,332–5,357.
- **Invariant 11 (pre-existing flake count):** PASS — DEF-150/167/171/190/192 unchanged.
- **Invariant 12 (frontend immutability):** PASS — zero `argus/ui/` edits.
- **Invariant 15 (`_OCA_TYPE_BRACKET` constant deleted):** ESTABLISHES — grep-guard test 2 enforces.
- **Invariant 16 (AC4.4 OCA-type lock-step):** ESTABLISHES — parametrized test 4 enforces.
- **Invariant 33 (interactive ack + CI-override flag separation per H-R3-4):** ESTABLISHES — tests 9, 10, 11, 12 enforce.

## Visual Review (N/A — backend-only)

S4b is backend-only. No frontend changes per regression invariant 12.

## Additional Context

- S4b is the dependency-rider session — DEF-212 (constant drift wiring) was originally scoped for Sprint 31.93 (component-ownership), but folded into Sprint 31.92 because both sprints touch `OrderManager.__init__` and the new sprint's Path #1/#2 fixes consume the same `IBKRConfig` plumbing this rider establishes.
- The rider lands AFTER M-R2-5 mid-sprint Tier 3 verdict (which fires post-S4a-ii). S4b proceeds only if M-R2-5 verdict is PROCEED or CLEAR; verify via `ls docs/sprints/sprint-31.92-def-204-round-2/tier-3-review-2-verdict.md` + `grep "PROCEED" docs/sprints/sprint-31.92-def-204-round-2/tier-3-review-2-verdict.md`.
- Round 3 H-R3-4 mandated three additions to AC4.7's original `--allow-rollback` design: (a) interactive ack at startup (when TTY); (b) periodic re-ack every 4h; (c) `--allow-rollback-skip-confirm` CI override flag with strict scope (CI only, not production). All three must land together — partial implementation is a CONCERNS-level finding.
- The cumulative-diff line count for `argus/execution/order_manager.py` across Sprint 31.92 sessions S2a → S4b should remain well below the ~1200–1350 cumulative bound (per round-3-disposition.md recalibration). Verify the close-out's cumulative-diff disclosure section reports the measured count.
