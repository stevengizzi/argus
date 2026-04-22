# FIX-10-backtest-legacy-cleanup — Tier 2 Review

> Independent review per `workflow/claude/skills/review.md`. Read-only; no source files were modified. Findings below.

```markdown
---BEGIN-REVIEW---

**Reviewing:** audit-2026-04-21-phase-3 — FIX-10-backtest-legacy-cleanup (commit 675bf78)
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-04-22
**Verdict:** CLEAR

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | Committed diff is exactly 3 files: `CLAUDE.md` (one hunk in the Backtesting section, +6/-1), `docs/audits/audit-2026-04-21/p1-e2-backtest-legacy.md` (+14 FIX-10 Resolution section), `docs/audits/audit-2026-04-21/phase-2-review.csv` (3 rows back-annotated). No runtime code, no `workflow/` submodule, no `.claude/` agents, no tests touched. Concurrent FIX-18 working-tree changes (`.env.example`, `pyproject.toml`, `scripts/resolve_sweep_symbols.py`, `tests/scripts/test_resolve_sweep_symbols.py`, `docs/audits/audit-2026-04-21/p1-i-dependencies.md`, plus DEF-178/179/180 rows in CLAUDE.md) are correctly absent from 675bf78 — verified by `git show 675bf78 --name-only`. |
| Close-Out Accuracy | PASS | Change manifest matches the diff exactly. Judgment calls (C01 partial-fix over no-op/full-fix; L01 and L02 purely-observational RESOLVED-VERIFIED per "Otherwise leave alone" clauses) are all traceable to the diff and defensible against the suggested-fix conditionality. Self-assessment MINOR_DEVIATIONS is honest — splitting the C01 suggested fix into "add wrappers now" and "drop direct CLIs when M1/M2 land" is a real judgment call and is correctly flagged rather than labeled CLEAN. |
| Test Health | PASS | Full suite reran locally: `python -m pytest --ignore=tests/test_main.py -n auto --tb=no -q` → **4,990 passed, 0 failed, 105.19s**. Net delta +5 is attributable to concurrent FIX-18's `tests/scripts/test_resolve_sweep_symbols.py` additions in the unstaged working tree — FIX-10's commit itself is docs-only and cannot affect the pytest count. The close-out correctly calls this out. |
| Regression Checklist | PASS | All 8 campaign-level checks pass — see detailed results in JSON appendix. Independently re-verified: net delta positive (+5 working-tree, 0 commit-attributable), zero failures in final run, scope clean (3/3 files inside declared scope), 3/3 CSV rows annotated with correct suffix strings, zero DEF closures required, zero new DEF/DEC opened. |
| Architectural Compliance | PASS | Zero runtime-code changes. The CLAUDE.md edit is a pure documentation restructure that preserves every pre-existing command line and adds three operational-wrapper lines above a newly-introduced sub-heading. The audit-report annotations follow the FIX-NN back-annotation convention used across the Phase 3 campaign. No architectural surface touched. |
| Escalation Criteria | NONE_TRIGGERED | No CRITICAL severity finding (the session contained 1 COSMETIC + 2 LOW); pytest net delta >= 0; no scope boundary violation; no different test failure surfaces (0 failures total); no Rule-4 sensitive path touched; audit back-annotations present on all 3 rows with correct `RESOLVED` / `RESOLVED-VERIFIED` suffixes. |

### Detailed Verification of Findings

1. **P1-E2-C01 [COSMETIC] — CLAUDE.md Backtesting section.** Committed CLAUDE.md hunk at lines 94–98 introduces "Backtesting — operational wrappers (primary entrypoints)" sub-heading with 3 lines (`scripts/revalidate_strategy.py`, `scripts/validate_all_strategies.py`, `scripts/run_experiment.py`), and the pre-existing 5 direct-module-CLI lines (`argus.backtest.data_fetcher`, `replay_harness`, `vectorbt_orb`, `engine`, `report_generator`) are retained under a new "Backtesting — direct module CLIs (invoked internally by wrappers above)" sub-heading. The suggested fix was conditional on M1/M2 landing ("drop the direct vectorbt_*.py invocations"); M1 (delete `vectorbt_pattern.py`) and M2 (delete `report_generator.py`) are both verifiably NOT met — `ls argus/backtest/report_generator.py` returns 37,530 bytes. The partial-additive fix is a defensible middle path: it addresses the cosmetic developer-confusion concern (wrappers are now visually advertised as primary) without overreaching into M1/M2's deletion scope. The close-out explicitly enumerates the three options considered (a/no-op, b/partial additive, c/full retune) and documents why (b) was chosen. CSV annotation uses `**RESOLVED FIX-10-backtest-legacy-cleanup**` (not -VERIFIED) correctly since a code/doc change was made. PASS.

2. **P1-E2-L01 [LOW] — DEC-149 Active status.** Verified `sed -n '1656p' docs/decision-log.md` → `| **Status** | Active |`. This confirms the finding's observation that DEC-149 is still Active because operational revalidation still calls `run_sweep` from the 4 vectorbt_*.py files. Safety tag is `read-only-no-fix-needed`; suggested fix is "No action. Revisit when M5's DEF is closed." The session correctly took the purely-observational path per Required Steps step 3 — no code change, marked `**RESOLVED-VERIFIED FIX-10-backtest-legacy-cleanup**` with verification command recorded. The "Revisit when M5's DEF is closed" clause is not a DEF-promotion request (M5 itself is a future DEF candidate, not yet opened; the DEC-149 Recommendation section in p1-e2-backtest-legacy.md explicitly frames M5 as a gate, not a fix). No DEF promotion required. PASS.

3. **P1-E2-L02 [LOW] — 3 stale HTML artifacts in reports/.** Verified `argus/backtest/report_generator.py` still exists at 37 KB (M2 not adopted), and all 3 HTML files (`orb_baseline_defaults.html` 45,577 B, `orb_baseline_relaxed.html` 59,057 B, `orb_final_validation.html` 72,173 B — dated Feb 16–17, 2026) are still in `reports/`. The suggested fix has an explicit conditional: "If M2 is adopted, consider deleting these three HTML files in the same PR since they reference the retired tool. **Otherwise leave alone.**" M2 is verifiably not adopted, so the "Otherwise leave alone" clause applies and the files are correctly retained. Marked `**RESOLVED-VERIFIED FIX-10-backtest-legacy-cleanup**` with verification recorded in the FIX-10 Resolution section of p1-e2-backtest-legacy.md. PASS.

### Detailed Verification of Scrutiny Items

1. **Scope hygiene vs concurrent FIX-18.** The close-out §Notes-for-Reviewer §2 describes the checkout+re-apply+restore protocol used to isolate FIX-10's commit from FIX-18's concurrent working-tree edits. Independently verified: `git show 675bf78 --name-only` returns exactly 3 files (CLAUDE.md, p1-e2-backtest-legacy.md, phase-2-review.csv). `git status` at review time still shows the 7 FIX-18 files as unstaged (`.env.example`, `CLAUDE.md`, `p1-i-dependencies.md`, `phase-2-review.csv`, `pyproject.toml`, `scripts/resolve_sweep_symbols.py`, `tests/scripts/test_resolve_sweep_symbols.py`) — note that CLAUDE.md and phase-2-review.csv appear in both the commit AND in the unstaged-changes list because FIX-18 has its own subsequent edits to those files (DEF-178/179/180 additions on CLAUDE.md; P1-I-* row annotations on the CSV). The hygiene protocol worked exactly as described: FIX-10's hunks committed, FIX-18's hunks preserved unstaged for that session's own commit. No cross-contamination. PASS.

2. **Audit-report back-annotation correctness.** All 3 CSV rows carry the correct suffix string in the final notes column: row 174 (P1-E2-L01) → `**RESOLVED-VERIFIED FIX-10-backtest-legacy-cleanup**` + parenthetical verification; row 175 (P1-E2-L02) → `**RESOLVED-VERIFIED FIX-10-backtest-legacy-cleanup**` + parenthetical; row 177 (P1-E2-C01) → `**RESOLVED FIX-10-backtest-legacy-cleanup**` (not -VERIFIED because a doc change was made) + parenthetical. The `/-VERIFIED` vs `/` distinction is applied correctly per the prompt's convention. PASS.

3. **FIX-10 Resolution section in p1-e2-backtest-legacy.md.** The +14-line section appended at the end of the audit report (after line 163's "T3 tier effort" line) enumerates C1/L1/L2 verdicts in a 3-row table with one-line justification each, and explicitly calls out that M1–M5, L3, C2 remain routed to FIX-09-backtest-engine or tracked as Phase 3 follow-on. This matches the convention used in prior FIX sessions' resolution sections (e.g., FIX-16's resolution section in p1-h2-config-consistency.md). PASS.

4. **Test count consistency.** Close-out reports 4,990 post-run passed. Independent re-run: 4,990 passed, 0 failed. Baseline was 4,985. The +5 delta is attributable to concurrent FIX-18 test additions (`tests/scripts/test_resolve_sweep_symbols.py`, added but unstaged) — verified by inspecting the working-tree diff of that file. FIX-10's commit itself contains 0 test changes; the commit-attributable delta is 0. The commit message's body even explicitly notes this ("Test delta: 4,985 -> 4,985 ... +5 concurrent FIX-18 tests observed in working tree but not included in this commit"). PASS.

5. **Pre-existing flake posture.** The run produced 0 failures — no DEF-150 (sprint_runner time-of-day arithmetic), no DEF-163 (date-decay/timezone boundary), no DEF-171 (ibkr_broker xdist). All 3 pre-existing flakes are known and the expected-failure window did not fire during this review run. Zero new failure surfaces introduced. PASS.

### Findings

**None.**

The session is a near-textbook small-cleanup close-out. All three findings had conditional suggested fixes ("If M1/M2 land...", "No action. Revisit when M5...", "If M2 adopted... Otherwise leave alone.") and the session honored every conditional: C01 got the additive-half of its suggested fix with the deletion-half correctly deferred; L01 and L02 got the "leave alone" treatment with explicit verification evidence. The MINOR_DEVIATIONS self-assessment is honest — the C01 split is a real judgment call, not a pretense of CLEAN.

Parallel-session hygiene is notable: FIX-18 was actively editing CLAUDE.md and phase-2-review.csv in the same working tree, and the session used a checkout+re-apply+restore protocol to stage only its own hunks. The commit is verifiably clean (3 files, no FIX-18 bleed), and the working-tree still carries FIX-18's unstaged work for its own commit. This is exactly the scope-discipline posture the Phase 3 campaign was designed to enforce, working under unusually contentious concurrent-session conditions.

### Recommendation

**Proceed to next session (CLEAR).**

All three findings resolved with defensible verdicts. Commit 675bf78 contains exactly 3 files — all within the declared scope. Test suite net-positive (+5 working-tree, 0 commit-attributable), zero failures. Audit back-annotations correct on all 3 rows. No new DEFs/DECs required; no DEF closures missed. The M1/M2/M5 preconditions remain open and are explicitly tracked in the FIX-10 Resolution section of p1-e2-backtest-legacy.md as future-session follow-on, which is the correct disposition.

No action items.

---END-REVIEW---
```

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "audit-2026-04-21-phase-3",
  "session": "FIX-10-backtest-legacy-cleanup",
  "verdict": "CLEAR",
  "findings": [],
  "spec_conformance": {
    "status": "MINOR_DEVIATION",
    "notes": "Self-assessment of MINOR_DEVIATIONS is correct and honest. The one deviation — splitting P1-E2-C01's suggested fix into an additive-half (add operational wrappers above existing direct CLIs) applied this session and a deletion-half (drop the vectorbt_*.py invocations) deferred pending M1/M2 — is well-justified: M1 (delete vectorbt_pattern.py) and M2 (delete report_generator.py) are verifiably unmet (report_generator.py still exists at 37 KB), and the partial-additive fix addresses the cosmetic developer-confusion concern without overreaching into M1/M2's scope. Options (a/no-op, b/partial-additive, c/full-retune) were enumerated in the close-out and (b) was chosen on documented grounds. L01 and L02 correctly took the purely-observational RESOLVED-VERIFIED path with explicit verification commands.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "CLAUDE.md",
    "docs/audits/audit-2026-04-21/p1-e2-backtest-legacy.md",
    "docs/audits/audit-2026-04-21/phase-2-review.csv",
    "docs/sprints/sprint-31.9/FIX-10-closeout.md",
    "docs/audits/audit-2026-04-21/phase-3-prompts/FIX-10-backtest-legacy-cleanup.md",
    "docs/decision-log.md (line 1656 verification only)",
    "argus/backtest/report_generator.py (existence verification only)",
    "reports/orb_baseline_defaults.html (existence verification only)",
    "reports/orb_baseline_relaxed.html (existence verification only)",
    "reports/orb_final_validation.html (existence verification only)"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 4990,
    "new_tests_adequate": true,
    "test_quality_notes": "No new tests were added this session (docs-only scope, correctly zero-test delta attributable to FIX-10's commit). The +5 delta between baseline (4,985) and post-run (4,990) is attributable to concurrent FIX-18's tests/scripts/test_resolve_sweep_symbols.py additions in the unstaged working tree — verified by inspecting git status and the commit file list. FIX-10's commit itself contains 0 test changes and cannot affect the pytest count. The commit message body explicitly notes this. 0 failures in the final run; no DEF-150/163/171 flakes fired."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "pytest net delta >= 0 against baseline 4,985 passed", "passed": true, "notes": "Post-run: 4,990 passed, 0 failed, 105.19s. Net +5 is FIX-18's unstaged test additions (test_resolve_sweep_symbols.py). FIX-10's commit-attributable delta is 0 (docs only)."},
      {"check": "DEF-150 flake remains the only pre-existing failure (no new regressions)", "passed": true, "notes": "Final run produced 0 failures. No DEF-150, DEF-163, or DEF-171 flakes fired this run. No new failure surfaces."},
      {"check": "No file outside declared scope was modified", "passed": true, "notes": "git show 675bf78 --name-only returns exactly 3 files: CLAUDE.md, docs/audits/audit-2026-04-21/p1-e2-backtest-legacy.md, docs/audits/audit-2026-04-21/phase-2-review.csv — all inside the declared scope. Concurrent FIX-18 edits (7 other files) are unstaged in working tree, NOT in the commit."},
      {"check": "Every resolved finding back-annotated in audit report with **RESOLVED FIX-10-backtest-legacy-cleanup**", "passed": true, "notes": "All 3 CSV rows carry correct suffix: P1-E2-C01 → **RESOLVED FIX-10-backtest-legacy-cleanup** (code/doc change applied); P1-E2-L01 → **RESOLVED-VERIFIED FIX-10-backtest-legacy-cleanup** (read-only verification); P1-E2-L02 → **RESOLVED-VERIFIED FIX-10-backtest-legacy-cleanup** (read-only verification). Each annotation includes a parenthetical with the verification evidence. Additionally, a FIX-10 Resolution section (+14 lines) is appended to p1-e2-backtest-legacy.md enumerating C1/L1/L2 verdicts in a 3-row table."},
      {"check": "Every DEF closure recorded in CLAUDE.md", "passed": true, "notes": "N/A — no DEFs were closed this session (all 3 findings were audit-level, not DEF-tracked)."},
      {"check": "Every new DEF/DEC referenced in commit message bullets", "passed": true, "notes": "N/A — zero new DEFs or DECs opened this session. Commit message correctly omits DEF/DEC references."},
      {"check": "read-only-no-fix-needed findings: verification output recorded OR DEF promoted", "passed": true, "notes": "P1-E2-L01 (read-only-no-fix-needed): verification command `sed -n '1656p' docs/decision-log.md` → `| **Status** | Active |` recorded in FIX-10 Resolution section. Suggested fix ('No action. Revisit when M5 DEF lands.') does not require DEF promotion — M5 itself is a future-sprint gate candidate per the DEC-149 Recommendation section in p1-e2-backtest-legacy.md, not a deferred-to-DEF fix. Correctly no DEF opened."},
      {"check": "deferred-to-defs findings: fix applied AND DEF-NNN added to CLAUDE.md", "passed": true, "notes": "N/A — no findings were tagged deferred-to-defs in this session."}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Proceed to next session. No blockers.",
    "Informational: the C01 'drop direct vectorbt_*.py invocations' deferred-half remains pending M1/M2 adoption. When the session that lands M1/M2 runs, the direct-CLI lines for `argus.backtest.vectorbt_orb` and `argus.backtest.report_generator` in CLAUDE.md's Backtesting section can be removed at that time.",
    "Informational: M5 (walk-forward migration from VectorBT to BacktestEngine) remains the gate for DEC-149 retirement. Per the DEC-149 Recommendation section in p1-e2-backtest-legacy.md, this is tracked as a future-sprint DEF candidate — no DEF opened yet."
  ]
}
```
