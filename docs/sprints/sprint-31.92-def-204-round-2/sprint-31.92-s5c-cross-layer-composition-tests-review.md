<!-- workflow-version: 1.2.0 -->
# Tier 2 Review: Sprint 31.92, Session S5c — Cross-Layer Composition Tests (CL-1..CL-5 + CL-7) + `SimulatedBrokerWithRefreshTimeout` Fixture — FINAL SESSION OF SPRINT 31.92

## Instructions

You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

**Write the review report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s5c-review.md
```

Create the file, write the full report (including the structured JSON
verdict) to it, and commit it. This is the ONE exception to "do not
modify any files" — the review report file is the sole permitted write.

## Pre-Flight

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this review.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt — particularly RULE-013 (read-only mode), RULE-038 (grep-verify factual claims), RULE-040 (small-sample sweep / spike-artifact directional vs. authoritative), RULE-050 (CI green precondition — sprint-seal-gating; this is the FINAL session and CI green is a sprint-seal precondition), and RULE-053 (architectural-seal verification — DEC-117 / DEC-385 / DEC-386 / DEC-388 are sealed defenses; AC5.6 cross-layer composition tests assert composition holds, NOT that any layer is modified).

## Review Context

Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-31.92-def-204-round-2/review-context.md`

## Tier 1 Close-Out Report

Read the close-out report from:

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s5c-closeout.md
```

If the close-out file does not exist, flag this as CONCERNS — the close-out report is required for review per DEC-330.

## Review Scope

- **Diff to review:** `git diff HEAD~1`
- **Test command** (DEC-328 — **FINAL session — full suite per final-review tier**):
  ```
  python -m pytest --ignore=tests/test_main.py -n auto -q
  ```
  Expected pass count target: **5,357–5,403 pytest** (5,269 baseline + 88–134 new logical / 95–145 effective per Round 3 disposition aggregate). Vitest unchanged at 913 (frontend immutability invariant 12).

- **Files that should NOT have been modified (S5c is TEST-ONLY — production code shows ZERO edits):**
  - `argus/execution/order_manager.py`
  - `argus/execution/simulated_broker.py` (the `SimulatedBrokerWithRefreshTimeout` fixture variant subclasses in test code only — production `simulated_broker.py` is unchanged per SbC §"Do NOT modify" #2)
  - `argus/execution/ibkr_broker.py`
  - `argus/main.py`
  - `argus/core/config.py`
  - `argus/core/health.py`, `argus/api/routes/alerts.py`, `argus/api/websocket/alerts_ws.py`
  - `argus/models/trading.py`
  - `argus/execution/alpaca_broker.py`
  - `argus/data/alpaca_data_service.py`
  - `frontend/`, `argus/ui/` (regression invariant 12 / B-class halt B8)
  - DB schemas
  - DEC-385 / DEC-386 / DEC-388 entries in `docs/decision-log.md`
  - `workflow/` submodule (RULE-018)
  - **The 13 prior S5a/S5b tests in `tests/integration/test_def204_round2_validation.py`** (4 from S5a + 9 from S5b) — append-only.

  **Permitted modifications:** new fixture file `tests/integration/conftest_refresh_timeout.py` (≤80 LOC) + 7 new tests appended to `tests/integration/test_def204_round2_validation.py` (6 cross-layer composition tests + 1 Branch 4 unit test).

## Session-Specific Review Focus

1. **Production code untouched.** S5c is a test/validation-only session. `git diff HEAD~1 -- argus/` MUST return empty (or only touch test directories). Verify via diff inspection. Any production-code edit is a B-class halt B6 candidate; on the FINAL session this is sprint-seal-gating.

2. **Append-only to S5a/S5b test file.** The 13 prior tests must remain byte-for-byte unchanged. Verify via `git diff HEAD~1 -- tests/integration/test_def204_round2_validation.py` showing only end-of-file additions. Use `grep -c "^def test_\|^async def test_" tests/integration/test_def204_round2_validation.py` — expect exactly 20 hits post-S5c (4 from S5a + 9 from S5b + 7 from S5c).

3. **Fixture LOC budget ≤80.** `wc -l tests/integration/conftest_refresh_timeout.py` MUST return ≤80. Exceeding triggers the large-file penalty per S5c compaction-risk score. The fixture is focused single-purpose per Tier 3 item E / DEF-SIM-BROKER-TIMEOUT-FIXTURE — do NOT add other test helpers to this file.

4. **Production `simulated_broker.py` untouched (SbC §"Do NOT modify" #2).** The `SimulatedBrokerWithRefreshTimeout` subclass lives in `tests/integration/conftest_refresh_timeout.py` ONLY. Verify via `git diff HEAD~1 -- argus/execution/simulated_broker.py` returning empty.

5. **All 6 CL tests + 1 Branch 4 unit test pass.** Run the scoped command:
   ```
   pytest tests/integration/test_def204_round2_validation.py -k "cl_\|branch_4" -v
   ```
   Confirm 7 tests pass:
   - `test_cl_1_l1_fails_l3_catches_pending_reservation_false_positive` (CL-1)
   - `test_cl_2_l4_fails_l2_catches_emergency_flatten_under_rollback` (CL-2)
   - `test_cl_3_l3_l5_cross_falsification_h1_active_refresh_timeout_halts_entry` (CL-3 — uses fixture)
   - `test_cl_4_l1_l2_misclassified_stop_replacement_l3_catches` (CL-4)
   - `test_cl_5_l2_l3_stop_replacement_with_active_suppression_no_false_fire` (CL-5)
   - `test_cl_7_concurrent_callers_no_stale_branch_2_classification` (CL-7 — NEW per Round 3 C-R3-1)
   - `test_branch_4_verification_stale_metadata_emitted_on_refresh_timeout_in_process` (Branch 4 — uses fixture)

6. **CL-3 uses the `SimulatedBrokerWithRefreshTimeout` fixture.** Verify CL-3's signature includes `simulated_broker_with_refresh_timeout` parameter. The Branch 4 unit test (test 7) similarly uses the fixture.

7. **CL-7 falsification logic correct (regression invariant 28).** CL-7 must assert BOTH branches:
   - (a) the race IS observable WITHOUT the single-flight + coalesce mitigation (counter-test).
   - (b) the race is NOT observable WITH the mitigation enabled.
   If only (b) is asserted, CL-7 cannot prove the fix is load-bearing — it would pass even if the mitigation were absent. This is the structural defense per RULE-051 (mechanism-signature vs. symptom-aggregate).

8. **Branch 4 metadata exhaustive (regression invariant 25 + DEF-SIM-BROKER-TIMEOUT-FIXTURE).** The Branch 4 unit test must assert ALL FOUR metadata keys:
   - `verification_stale=True`
   - `verification_failure_reason="TimeoutError"`
   - `position_id` (specific value matching the test's ManagedPosition)
   - `symbol` (specific value matching the test's symbol)
   AND assert `_locate_suppressed_until[position.id]` is NOT cleared on refresh failure (operator-triage signal).

9. **CL-6 NOT in the test list (Decision 5).** Verify there is no `test_cl_6_*` test in S5c's diff — CL-6 (rollback + locate-suppression interaction) is explicitly OUT per Decision 5. Rationale to be documented in `docs/process-evolution.md` at sprint-close per `doc-update-checklist.md` C10. If CL-6 is present, this is a scope-creep CONCERNS finding.

10. **No real wall-clock sleeps >100ms (B10).** Reviewer scans new test code AND fixture for `asyncio.sleep(<positive_real>)` or `time.sleep(<positive_real>)`; the only allowed `asyncio.sleep` is the very small (≤1ms typical, ≤100ms max) sleep inside the fixture's `refresh_positions()` override that triggers the synthetic timeout.

11. **AC5.6 in-process scope qualifier preserved.** Cross-layer test docstrings AND the close-out must explicitly state the in-process scope qualifier ("validates IN-PROCESS LOGIC against SimulatedBroker; does NOT validate IBKR-API timing"). The close-out must NOT claim S5c closes cessation criterion #5.

12. **Per-test runtime ≤ 5s (B10).** Run `pytest --durations=10 tests/integration/test_def204_round2_validation.py` and confirm each new test is below 5s. Cross-layer tests are slow + ugly by design (per `templates/sprint-spec.md` v1.2.0) — they MUST still finish in <5s via `SimulatedBrokerWithRefreshTimeout` fixture mocking; reduce fixture scope OR mock the slow path; do NOT carry slow tests into the final suite.

13. **FULL-suite green at S5c close-out — sprint-seal precondition.** Run `python -m pytest --ignore=tests/test_main.py -n auto -q` and confirm pass count is in target range **5,357–5,403**. Failure to reach target (or full-suite red) is **B-class halt B3 / B4 — sprint cannot seal**. The close-out must cite the exact post-S5c pass count.

14. **Vitest baseline 913.** Run `cd argus/ui && npx vitest run` and confirm pass count is exactly 913 (frontend immutability invariant 12). Any change is a B-class halt B8.

15. **All 5 validation artifacts committed to `main`.** Verify presence:
    - `scripts/spike-results/spike-def204-round2-path1-results.json` (S1a)
    - `scripts/spike-results/spike-def204-round2-path2-results.json` (S1b)
    - `scripts/spike-results/sprint-31.92-validation-path1.json` (S5a)
    - `scripts/spike-results/sprint-31.92-validation-path2.json` (S5b)
    - `scripts/spike-results/sprint-31.92-validation-composite.json` (S5b)

16. **FAI table at 11 entries.** Verify FAI #10 (S3b close-out) AND FAI #11 (S4a-ii close-out) materialized in `docs/sprints/sprint-31.92-def-204-round-2/falsifiable-assumption-inventory.md`. Inventory preamble line should read `## Inventory (11 entries)`. Both pending-extension subsection entries should have been removed.

17. **Sprint-seal precondition checklist completeness.** Verify the close-out's sprint-seal precondition checklist enumerates ALL items per `escalation-criteria.md` § Closing the Sprint:
    - All 13 sessions Tier 2 verdict CLEAR.
    - M-R2-5 verdict received and dispositioned.
    - All 5 validation artifacts on `main`.
    - All 6 CL tests + 1 Branch 4 unit test green; CL-6 confirmed OUT per Decision 5.
    - `tests/integration/conftest_refresh_timeout.py` (`SimulatedBrokerWithRefreshTimeout` fixture) committed.
    - FULL suite green at S5c close-out (target 5,357–5,403 pytest).
    - DEC-390 written below in `docs/decision-log.md` per AC6 (likely deferred to D14 sprint-close doc-sync; flag in close-out).
    - DEF-204 row in `CLAUDE.md` to be marked **RESOLVED-PENDING-PAPER-VALIDATION** at D14 (NOT RESOLVED).
    - DEF-212 row in `CLAUDE.md` to be marked **RESOLVED** at D14.
    - 6 NEW DEFs from Tier 3 to be added to `CLAUDE.md` DEF table at D14: DEF-FAI-CALLBACK-ATOMICITY, DEF-CROSS-LAYER-EXPANSION, DEF-FAI-N-INCREASE, DEF-FAI-2-SCOPE, DEF-FAI-8-OPTION-A, DEF-SIM-BROKER-TIMEOUT-FIXTURE.
    - 7 new RSKs to be filed at D14.
    - Cessation criterion #5 counter explicitly RESET to 0/5.
    - Daily CI workflow added at sprint-close (operator-manual edit per `doc-update-checklist.md` C9; not in S5c diff).
    - Process-evolution lesson F.5 reaffirmation + FAI completeness pattern lesson + CL-6 deferral rationale.
    Items typically deferred to D14 (DEC-390, DEF row markings, RSK filings, daily CI workflow) MUST be flagged as such — not silently skipped.

18. **S5c compaction-risk score drift disclosure (RULE-038).** The session-breakdown.md line 1584 manifest cites the post-amendment expected score for S5c as 11.5 with pre-amendment baseline 11. The actual session-breakdown scoring table at line 1574–1583 lands at 13.5 (Medium) post-amendment with 13 pre-amendment baseline. Per session-breakdown.md note (lines 1586–1598), this discrepancy is logged for the close-out manifest per RULE-038 — the disposition's amendment intent (add CL-7; keep within Medium tier) is preserved; the absolute baseline number is reconciled to the actual scoring table. **Reviewer should note this disclosure in the verdict; the Medium-tier classification is the load-bearing fact, not the absolute score.**

## Sprint-Level Regression Checklist (for @reviewer)

The full Sprint-Level Regression Checklist is in `docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md` (34 invariants total).

✓-mandatory at S5c per the Per-Session Verification Matrix (S5c is the final-session sweep; nearly all invariants are validated in composition):

- **Invariant 1 (DEC-117 atomic bracket):** ✓ — preserved.
- **Invariant 5 (DEC-385 6-layer side-aware reconciliation):** ✓ — preserved.
- **Invariant 6 (DEC-386 4-layer OCA architecture):** ✓ — preserved; CL-2 stresses lock-step under rollback.
- **Invariant 7 (DEC-388 alert observability):** ✓ — preserved; Branch 4 unit test exercises `phantom_short_retry_blocked` alert path with `verification_stale=True` metadata.
- **Invariant 9 (`# OCA-EXEMPT:` mechanism):** ✓ — preserved.
- **Invariant 10 (test count baseline ≥ 5,269; target +7 at S5c, +88–134 sprint-total):** ✓ — full-suite count required at close-out.
- **Invariant 11 (pre-existing flake count):** ✓ — preserved.
- **Invariant 12 (frontend immutability):** ✓ — preserved (Vitest at 913).
- **Invariant 13 (SELL-volume ceiling pending+sold pattern):** ✓ — composite cross-layer via CL-1 + CL-4.
- **Invariant 14 (Path #2 fingerprint + position-keyed dict + broker-verification):** ✓ — composite via CL-3 + CL-5.
- **Invariant 15 (`_OCA_TYPE_BRACKET` constant deleted; S4b precondition):** ✓ — preserved.
- **Invariant 16 (AC4.4 OCA-type lock-step):** ✓ — composite via CL-2.
- **Invariant 18 (spike artifacts fresh + committed):** ✓ — S5a + S5b artifacts on `main`.
- **Invariant 21 (broker-verification three-branch coverage):** ✓ — composite via CL-3 + Branch 4 unit test.
- **Invariant 23 (synchronous-update invariant + reflective-pattern AST):** ✓ — composite via CL-1 (forces L1 false-positive; L3 catches).
- **Invariant 24 (HALT-ENTRY posture under H1 + refresh fail):** ✓ — composite via CL-3.
- **Invariant 25 (Branch 4 + `SimulatedBrokerWithRefreshTimeout` fixture):** ✓ — ESTABLISHES fixture + Branch 4 unit test.
- **Invariant 27 (5 cross-layer composition tests CL-1..CL-5):** ✓ — ESTABLISHES all 5 + CL-7.
- **Invariant 28 (single-flight serialization + 250ms coalesce window):** ✓ — composite via CL-7.

## Visual Review (N/A — backend-only)

S5c is backend-only. No frontend changes per regression invariant 12.

## Additional Context

**S5c IS THE FINAL SESSION OF SPRINT 31.92 — THIS REVIEW IS THE SPRINT-SEAL PRECONDITION GATE.**

Per DEC-328 final-review tier:
- Use full suite with `-n auto`: `python -m pytest --ignore=tests/test_main.py -n auto -q`
- Verify final test count is **5,357–5,403 pytest** (baseline 5,269 + 88–134 new logical / 95–145 effective with parametrize)
- Vitest count must remain **913** (frontend immutability invariant)
- Verify all 5 validation artifacts committed to `main`:
  - `scripts/spike-results/spike-def204-round2-path1-results.json` (S1a)
  - `scripts/spike-results/spike-def204-round2-path2-results.json` (S1b)
  - `scripts/spike-results/sprint-31.92-validation-path1.json` (S5a)
  - `scripts/spike-results/sprint-31.92-validation-path2.json` (S5b)
  - `scripts/spike-results/sprint-31.92-validation-composite.json` (S5b)
- Verify all CL-1..CL-5 + CL-7 tests green; CL-6 confirmed OUT per Decision 5 with deferral rationale documented.
- Verify FAI #10 (S3b close-out) + FAI #11 (S4a-ii close-out) materialized — FAI table at 11 entries.
- Composite cross-layer scenarios are by definition slow + ugly + span multiple modules per `templates/sprint-spec.md` v1.2.0 — they MUST still finish in <5s each via fixture mocking.
- ZERO production-code changes (test-only session). `git diff HEAD~1 -- argus/` returns empty (or test dirs only).

**Sprint cannot seal if:**
- A3 fires (composite validation produces phantom_shorts > 0 OR `total_sold_le_total_bought: false` OR S5c CL-1/CL-2/CL-4/CL-5 fails) — DO NOT seal the sprint.
- A17 fires (CL-3 specifically — Branch 4 + H1 active without HALT-ENTRY firing) — DO NOT seal.
- B3 fires (pytest baseline ends below 5,269) — DO NOT seal.
- B4 fires (CI fails on S5c's final commit AND failure is NOT a documented pre-existing flake) — DO NOT seal per RULE-050.
- B10 fires (any new pytest test > 5s individual runtime) — halt and investigate.

ESCALATE on the FINAL session is particularly serious — operator decides whether to revert or fix-forward. CONCERNS findings can be fixed within this session via the post-review fix protocol (close-out → "Post-Review Fixes" section; review → "Resolved" annotation + verdict update to `CONCERNS_RESOLVED`).
