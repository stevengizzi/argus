# Tier 2 Review: Sprint 31.92, Session S1b

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end,
fenced with ` ```json:structured-verdict `. See the review skill for the full
schema and requirements.

**Write the review report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s1b-spike-path2-review.md
```

Create the file, write the full report (including the structured JSON
verdict) to it, and commit it. This is the ONE exception to "do not modify
any files" — the review report file is the sole permitted write.

## Pre-Flight

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this review.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt — particularly **RULE-013** (read-only mode), **RULE-038** (grep-verify factual claims), **RULE-040** (small-sample sweep conclusions are directional), **RULE-050** (CI green required), **RULE-053** (architectural-seal verification — DEF-158 3-branch side-check sealed; DEC-386's 4-layer OCA architecture sealed).

## Review Context

Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist (34 invariants), and Sprint-Level Escalation Criteria:

```
docs/sprints/sprint-31.92-def-204-round-2/review-context.md
```

## Tier 1 Close-Out Report

Read the close-out report from:

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s1b-spike-path2-closeout.md
```

(Per RULE-038, grep-verify the actual closeout filename if not present at the expected path — sibling impl prompts in this sprint reference `session-1b-closeout.md` as a candidate alternative. If neither file exists, flag as CONCERNS — the close-out report is required for review.)

## Review Scope

- **Diff to review:** `git diff HEAD~1` (or specify the correct range if the close-out cites multiple commits).
- **Test command** (non-final session, scoped per DEC-328):
  ```
  python -m pytest tests/execution/ -n auto -q
  ```
  Note: the spike script itself is NOT a pytest unit test. The reviewer additionally verifies the JSON artifact's required-keys schema against `scripts/spike-results/spike-def204-round2-path2-results.json`.
- **Files that should NOT have been modified:**
  - All `argus/**/*` (entire production tree — spike is read-only with respect to production code; specifically `_LOCATE_REJECTED_FINGERPRINT` and `_is_locate_rejection` land at S3a, NOT S1b).
  - `tests/` (spike adds zero new pytest tests).
  - `frontend/` (Vitest count must remain at 913 — B-class halt B8).
  - `workflow/` submodule (Universal RULE-018).
  - Any sealed/frozen artifact in `docs/sprints/sprint-31.91-reconciliation-drift/` or `docs/sprints/sprint-31.915-evaluation-db-retention/`.

## Session-Specific Review Focus

1. **Spike does not modify production code.** `git diff HEAD~1 -- argus/` must return empty. If any `argus/**/*` file appears in the diff, A-class halt **A4** fires regardless of close-out claims. Specifically, DEF-158's 3-branch side-check structure in `_check_flatten_pending_timeouts` MUST remain unchanged (A-class halt **A5**).

2. **JSON artifact required-keys schema.** Run the inspection command from the regression checklist; assert all 16 required keys are present (`status`, `fingerprint_string`, `fingerprint_stable`, `case_a_observed`, `case_a_count`, `case_b_count`, `case_a_max_age_seconds`, `release_events_observed`, `release_p50_seconds`, `release_p95_seconds`, `release_p99_seconds`, `release_max_seconds`, `recommended_locate_suppression_seconds`, `symbols_tested`, `trials_per_symbol`, `spike_run_date`) and `status: "PROCEED"`. If `status: "INCONCLUSIVE"`, A-class halt **A2** fires.

3. **Fingerprint stability across symbols.** Verify `fingerprint_stable: bool` is True iff every observed locate-rejection trial across all symbols produced the canonical exact substring `"contract is not available for short sale"`. If `fingerprint_stable: false`, the close-out MUST surface the variant strings observed AND recommend substring-list broadening for S3a's `_LOCATE_REJECTED_FINGERPRINT` constant. `fingerprint_string` must be non-empty when `case_b_count > 0` — empty fingerprint with non-zero case-B count indicates the substring extraction logic failed; halt and re-run.

4. **Case-A vs case-B differentiation (FAI #6 / M-R2-1 disposition).** Per the Round-1 disposition, the spike actively probes for case A (held order pending borrow) — the breaking condition for the H5 substring assumption. If `case_a_count == 0 AND case_b_count == 0`, halt; the curated symbols did not actually trigger any locate-related broker behavior. If `case_a_observed: true`, the AC2.7 watchdog auto-activation per Decision 4 is operationally meaningful and the close-out should call this out.

5. **PCT in `symbols_tested`.** PCT is the canonical reference symbol from the Apr 28 paper-session debrief. Absence indicates the operator's curated list missed the canonical anchor, and the spike's case-B fingerprint may not generalize. Verify via:
   ```
   python -c "import json; d = json.load(open('scripts/spike-results/spike-def204-round2-path2-results.json')); assert 'PCT' in d['symbols_tested'], d['symbols_tested']"
   ```

6. **`recommended_locate_suppression_seconds` formula.**
   - If `release_events_observed > 0`: `min(86400, max(18000, p99 × 1.2))`.
   - If `release_events_observed == 0` (H6 RULES-OUT): exactly **18000** with documented H6 rules-out rationale.
   Mis-derivation silently mis-tunes the S3a Pydantic field default. Verify the value falls in `[18000, 86400]` (matches Pydantic field validator bounds for S3a).

7. **H6 rules-out path documentation (if applicable).** When `release_events_observed == 0`, the close-out's "Judgment Calls" section MUST surface (a) the fallback to 18000s AND (b) the AC2.5 Branch 4 broker-verification-at-timeout fallback as the structural mitigation. Absence of this documentation creates a stale-rationale risk for S3a/S3b sessions.

8. **Operator-curated symbol-list rationale.** Per RULE-038, the operator's symbol curation IS load-bearing context for the spike's empirical reach. Verify the close-out's "Operator Notes" section documents the curation rationale — future reviewers (Round 3 + sprint-close + post-merge debriefs) audit whether the symbol list adequately represents the production hard-to-borrow microcap surface.

9. **Spike artifact freshness.** `scripts/spike-results/spike-def204-round2-path2-results.json` mtime should be within the session window (per operational regression invariant 18). Stale artifacts indicate a previous run was committed without re-execution.

## Additional Context

This is the Phase A Path #2 fingerprint-capture spike for Sprint 31.92. The spike's `fingerprint_string` and `recommended_locate_suppression_seconds` fields are consumed at S3a (the substring constant `_LOCATE_REJECTED_FINGERPRINT` and the Pydantic field default `OrderManagerConfig.locate_suppression_seconds`). Sprint 31.92 is a **CRITICAL safety** sprint; bias toward CONCERNS over CLEAR when in doubt. Per RULE-053, DEF-158's 3-branch side-check structure and DEC-386's 4-layer OCA architecture are sealed — verify no diff touches the seal boundary, even via the spike's read-only consumption of `place_order` / `cancel_order`.

The full Sprint-Level Regression Checklist (34 invariants) is in `docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md`. S1b is ✓-mandatory for invariants **10, 11, 12, 14, 18** per the Per-Session Verification Matrix.

The full Sprint-Level Escalation Criteria are in `docs/sprints/sprint-31.92-def-204-round-2/escalation-criteria.md`. Most relevant to S1b: A-class halts **A2** (INCONCLUSIVE), **A4** (DEC-385/386/388 surface modified), **A5** (DEF-158 3-branch side-check modified), **A6** (CONCERNS/ESCALATE verdict), **A13** (artifact >30 days old at first paper session); B-class halts **B1** (flake count increases), **B3** (pytest below 5,269), **B4** (CI red), **B5** (anchor mismatch), **B6** (do-not-modify file in diff), **B8** (frontend modified), **B9** (`release_p99_seconds > 86400`); C-class halts **C1** (out-of-scope improvements), **C8** (JSON schema deviation), **C10** (curated list <5 symbols OR no rejections triggered — H6 RULES-OUT path; NOT a halt).
