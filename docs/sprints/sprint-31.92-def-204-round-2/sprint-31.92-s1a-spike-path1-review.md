# Tier 2 Review: Sprint 31.92, Session S1a

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end,
fenced with ` ```json:structured-verdict `. See the review skill for the full
schema and requirements.

**Write the review report to a file** (DEC-330):

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s1a-spike-path1-review.md
```

Create the file, write the full report (including the structured JSON
verdict) to it, and commit it. This is the ONE exception to "do not modify
any files" — the review report file is the sole permitted write.

## Pre-Flight

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this review.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt — particularly **RULE-013** (read-only mode), **RULE-038** (grep-verify factual claims), **RULE-040** (small-sample sweep conclusions are directional, but the spike's HARD GATE on N=100 + worst-axis Wilson UB is decision-by-construction), **RULE-050** (CI green required), **RULE-051** (mechanism-vs-symptom validation), **RULE-053** (architectural-seal verification — DEC-386's 4-layer OCA architecture is sealed).

## Review Context

Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist (34 invariants), and Sprint-Level Escalation Criteria:

```
docs/sprints/sprint-31.92-def-204-round-2/review-context.md
```

## Tier 1 Close-Out Report

Read the close-out report from:

```
docs/sprints/sprint-31.92-def-204-round-2/sprint-31.92-s1a-spike-path1-closeout.md
```

(Per RULE-038, grep-verify the actual closeout filename if not present at the expected path — sibling impl prompts in this sprint reference `session-1a-closeout.md` as a candidate alternative. If neither file exists, flag as CONCERNS — the close-out report is required for review.)

## Review Scope

- **Diff to review:** `git diff HEAD~1` (or specify the correct range if the close-out cites multiple commits).
- **Test command** (non-final session, scoped per DEC-328):
  ```
  python -m pytest tests/execution/ -n auto -q
  ```
  Note: the spike script itself is NOT a pytest unit test. The reviewer additionally verifies the JSON artifact's required-keys schema by inspecting `scripts/spike-results/spike-def204-round2-path1-results.json` against the required-keys list documented in the close-out report and reproduced in S1a's regression checklist.
- **Files that should NOT have been modified:**
  - All `argus/**/*` (entire production tree — spike is read-only with respect to production code).
  - `tests/` (spike adds zero new pytest tests).
  - `frontend/` (Vitest count must remain at 913 — B-class halt B8).
  - `workflow/` submodule (Universal RULE-018).
  - Any sealed/frozen artifact in `docs/sprints/sprint-31.91-reconciliation-drift/` or `docs/sprints/sprint-31.915-evaluation-db-retention/`.

## Session-Specific Review Focus

1. **Spike does not modify production code.** `git diff HEAD~1 -- argus/` must return empty. If any `argus/**/*` file appears in the diff, A-class halt **A4** fires regardless of close-out claims.

2. **JSON artifact required-keys schema.** Run the inspection command from the regression checklist; assert all 14 required keys are present (`status`, `selected_mechanism`, `h2_modify_order_p50_ms`, `h2_modify_order_p95_ms`, `h2_rejection_rate_pct`, `h2_deterministic_propagation`, `adversarial_axes_results`, `worst_axis_wilson_ub`, `h1_cancel_all_orders_p50_ms`, `h1_cancel_all_orders_p95_ms`, `h1_propagation_n_trials`, `h1_propagation_zero_conflict_in_100`, `trial_count`, `spike_run_date`) and `status: "PROCEED"`. If `status: "INCONCLUSIVE"`, A-class halt **A1** fires.

3. **Mechanism-selection consistency with H-R2-2-tightened gate language.** The `selected_mechanism` field must derive deterministically from the gate rule:
   - `worst_axis_wilson_ub < 5%` AND `h1_propagation_zero_conflict_in_100 == true` → `h2_amend`
   - `5% ≤ worst_axis_wilson_ub < 20%` AND `h1_propagation_zero_conflict_in_100 == true` → `h4_hybrid`
   - `worst_axis_wilson_ub ≥ 20%` AND `h1_propagation_zero_conflict_in_100 == true` AND operator written confirmation → `h1_cancel_and_await`
   - `h1_propagation_zero_conflict_in_100 == false` (any 1 conflict in 100) → H1 NOT eligible regardless of Wilson UB; if Wilson UB ≥ 20%, `status: INCONCLUSIVE`.

   Verify the close-out's mechanism rationale matches the JSON values; mis-derivation silently mis-routes downstream S2a/S2b implementation.

4. **`h1_propagation_n_trials == 100` (HARD GATE per Decision 2).** Reducing N silently weakens the gate (Wilson UB on 0/30 ≈ [0%, 11.6%]; on 0/100 it tightens substantially). C-class halt **C8** (JSON schema deviation) escalates if N < 100.

5. **`worst_axis_wilson_ub` is the maximum across 4 adversarial axes,** not the average or median. The decision rule is worst-case-driven; misreading the JSON aggregator silently misroutes mechanism selection. Inspect the script's aggregation function.

6. **FAI #3 + FAI #5 falsification evidence (per RULE-038 + RULE-051).** The spike actively PROBES for the breaking condition (FAI #3 — worst-axis amend rejection rate; FAI #5 — H1 propagation conflict in N=100). Inspect the script's axis (i) — concurrent amends across N≥3 positions — to confirm the timing actually overlaps (≤10ms separation between fire times) rather than serializing accidentally. If the script serializes the amends, the adversarial axis is degenerate and `worst_axis_wilson_ub` is meaningless; halt and request re-spike. The mechanism signature is the falsifiable part per RULE-051.

7. **Operator-confirmation reference if H1 selected.** If `selected_mechanism == "h1_cancel_and_await"`, the close-out's "Judgment Calls" section MUST cite the operator's written confirmation per the existing tightened gate language. Absence escalates to operator before any S2a/S2b prompt generation.

8. **Spike artifact freshness.** `scripts/spike-results/spike-def204-round2-path1-results.json` mtime should be within the session window (per operational regression invariant 18). Stale artifacts indicate a previous run was committed without re-execution.

## Additional Context

This is the Phase A Path #1 mechanism-selection spike for Sprint 31.92. The spike's `selected_mechanism` field deterministically gates the implementation prompts at S2a + S2b. Sprint 31.92 is a **CRITICAL safety** sprint; bias toward CONCERNS over CLEAR when in doubt. Per RULE-053, DEC-386's 4-layer OCA architecture is architecturally sealed — verify no diff touches the seal boundary, even via the spike's read-only consumption of `place_bracket_order` / `cancel_all_orders` / `modify_order`.

The full Sprint-Level Regression Checklist (34 invariants) is in `docs/sprints/sprint-31.92-def-204-round-2/regression-checklist.md`. S1a is ✓-mandatory for invariants **10, 11, 12, 18** per the Per-Session Verification Matrix.

The full Sprint-Level Escalation Criteria are in `docs/sprints/sprint-31.92-def-204-round-2/escalation-criteria.md`. Most relevant to S1a: A-class halts **A1** (INCONCLUSIVE), **A4** (DEC-385/386/388 surface modified), **A6** (CONCERNS/ESCALATE verdict), **A9** (worst-axis Wilson UB ≥ 20%), **A13** (artifact >30 days old at first paper session); B-class halts **B1** (flake count increases), **B3** (pytest below 5,269), **B4** (CI red), **B5** (anchor mismatch), **B6** (do-not-modify file in diff), **B8** (frontend modified); C-class halts **C1** (out-of-scope improvements), **C8** (JSON schema deviation).
