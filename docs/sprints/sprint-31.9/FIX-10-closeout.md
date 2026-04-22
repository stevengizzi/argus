# FIX-10-backtest-legacy-cleanup — Close-Out Report

> Tier 1 self-review produced per `workflow/claude/skills/close-out.md`.
> Paste the fenced block below into the Work Journal on Claude.ai.

```markdown
---BEGIN-CLOSE-OUT---

**Session:** audit-2026-04-21-phase-3 — FIX-10-backtest-legacy-cleanup
**Date:** 2026-04-22
**Self-Assessment:** MINOR_DEVIATIONS

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| CLAUDE.md | modified | Backtesting Commands section split into two sub-headings — "operational wrappers (primary entrypoints)" with `scripts/revalidate_strategy.py`, `scripts/validate_all_strategies.py`, `scripts/run_experiment.py` above "direct module CLIs (invoked internally by wrappers above)" retaining the pre-existing `python -m argus.backtest.*` lines (P1-E2-C01 partial fix). |
| docs/audits/audit-2026-04-21/p1-e2-backtest-legacy.md | modified | Added `## FIX-10 Resolution (2026-04-22)` section enumerating C1/L1/L2 verdicts with one-line justification each. |
| docs/audits/audit-2026-04-21/phase-2-review.csv | modified | Back-annotated 3 rows: P1-E2-L01 → `**RESOLVED-VERIFIED FIX-10-backtest-legacy-cleanup**`; P1-E2-L02 → `**RESOLVED-VERIFIED FIX-10-backtest-legacy-cleanup**`; P1-E2-C01 → `**RESOLVED FIX-10-backtest-legacy-cleanup**`. |

### Judgment Calls
- **C01 partial fix over no-op or full fix.** The suggested fix is conditional on M1/M2 landing ("If M1/M2 land, retune ... and drop the direct vectorbt_*.py invocations"). M1 (delete `vectorbt_pattern.py`) and M2 (delete `report_generator.py`) were NOT routed to this session and both target files still exist. Three options were considered: (a) no-op + RESOLVED-VERIFIED on the precondition-unmet grounds; (b) partial additive fix — add the operational wrappers above the existing direct CLIs without dropping anything; (c) full retune as if M1/M2 had landed. Chose (b): the cosmetic developer-confusion concern ("advertises vectorbt_orb as if it's a primary workflow") is real even without M1/M2, and adding the wrappers is additive and reversible. The "drop direct invocations" half of the suggested fix is deferred to the session that actually lands M1/M2. Self-assessment is MINOR_DEVIATIONS (not CLEAN) because this is a judgment call splitting the suggested fix in two.
- **L01 pure-observation treatment.** Safety is `read-only-no-fix-needed`; suggested fix is literally "No action. Revisit when M5's DEF is closed." Per Required Steps step 3, verified DEC-149 remains `Status = Active` at `docs/decision-log.md:1656` and marked RESOLVED-VERIFIED with no code change.
- **L02 "Otherwise leave alone" path.** The suggested fix is conditional on M2 adoption: "If M2 is adopted, consider deleting these three HTML files... Otherwise leave alone." Verified M2 is NOT adopted — `argus/backtest/report_generator.py` still exists at 37 KB. The explicit "Otherwise leave alone" clause applies. The three HTML files (`orb_baseline_defaults.html`, `orb_baseline_relaxed.html`, `orb_final_validation.html`) in `reports/` are retained, to be revisited when M2 lands. Marked RESOLVED-VERIFIED.
- **Scope-discipline: DEF entries additions by concurrent FIX-18 NOT staged.** FIX-18 was running in a parallel session and added DEF-178/179/180 to CLAUDE.md's Deferred Items table in the shared working tree. Those additions were not part of FIX-10's declared scope. I used `git checkout HEAD -- CLAUDE.md` + re-application of only my Backtesting edit, then `git add CLAUDE.md` with only my hunk staged. After committing, the backup was restored so FIX-18's DEF additions remain as unstaged changes in the working tree for FIX-18's own commit. Git diff on the committed CLAUDE.md shows exactly one hunk (+6/-1) in the Backtesting section.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| **Finding 1 — P1-E2-C01 [COSMETIC]** (Backtesting section advertises direct VectorBT CLIs as primary workflow) | DONE (partial) | CLAUDE.md Commands section split — wrappers above, direct CLIs retained below (M1/M2 pre-conditions for "drop direct invocations" not met). |
| **Finding 2 — P1-E2-L01 [LOW]** (DEC-149 retirement still gated on M5) | RESOLVED-VERIFIED | DEC-149 Status confirmed `Active` at decision-log.md:1656; no code change per `read-only-no-fix-needed`. |
| **Finding 3 — P1-E2-L02 [LOW]** (3 stale HTML artifacts in reports/) | RESOLVED-VERIFIED | M2 confirmed not adopted (report_generator.py still exists); per "Otherwise leave alone" the 3 HTML files retained. |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| pytest net delta >= 0 against baseline 4,985 passed | PASS | Post-change pytest: 4,990 passed / 0 failed / 68.20s. Net +5 is concurrent FIX-18 test additions in the shared working tree (`tests/scripts/test_resolve_sweep_symbols.py` — confirmed unstaged at commit time and NOT included in FIX-10's commit). FIX-10's own edits are strictly docs (CLAUDE.md, audit .md, CSV) and cannot affect pytest count. |
| DEF-150 flake remains the only pre-existing failure (no new regressions) | PASS | 0 failures. DEF-150 did not flake this run; DEF-163 and DEF-171 did not fire either. |
| No file outside this session's declared Scope was modified | PASS | Committed diff is exactly 3 files: CLAUDE.md (6 insertions / 1 deletion in Backtesting section only), docs/audits/audit-2026-04-21/p1-e2-backtest-legacy.md (+17 FIX-10 Resolution section), docs/audits/audit-2026-04-21/phase-2-review.csv (3 rows back-annotated). No runtime code, no workflow/ submodule, no DEF-175 discovery doc, no Stage 1/2/3 campaign trail rows touched. |
| Every resolved finding back-annotated in audit report with `**RESOLVED FIX-10-backtest-legacy-cleanup**` | PASS | 3/3 CSV rows annotated; FIX-10 Resolution section added to `p1-e2-backtest-legacy.md`. |
| Every DEF closure recorded in CLAUDE.md | PASS (N/A) | No DEFs closed this session. |
| Every new DEF/DEC referenced in commit message bullets | PASS (N/A) | No new DEFs or DECs opened. |
| `read-only-no-fix-needed` findings: verification output recorded OR DEF promoted | PASS | L01 verification: `sed -n '1656p' docs/decision-log.md` → `\| **Status** \| Active \|`. L02 verification: `ls -la argus/backtest/report_generator.py` → 37530-byte file exists. Both recorded in FIX-10 Resolution section. |
| `deferred-to-defs` findings: fix applied AND DEF-NNN added to CLAUDE.md | PASS (N/A) | No findings were tagged `deferred-to-defs`. |

### Test Results
- Tests run: 4,990 (full suite via `--ignore=tests/test_main.py -n auto`)
- Tests passed: 4,990
- Tests failed: 0
- New tests added: 0 (docs-only session; +5 count delta attributable to concurrent FIX-18 unstaged additions not included in FIX-10's commit)
- Command used: `python -m pytest --ignore=tests/test_main.py -n auto --tb=no -q`

### Unfinished Work
- M1, M2, M3, M4 remain open as Phase 3 follow-on items (T1/T2 tiers per Deletion Safety Matrix in `p1-e2-backtest-legacy.md`). These are routed to FIX-09-backtest-engine per phase-2-review.csv.
- M5 (walk-forward migration from VectorBT to BacktestEngine, ~12,777 LOC retirement) remains a future-sprint DEF candidate per the DEC-149 Recommendation section; not yet opened as a formal DEF. When M5 lands, DEC-149 becomes retirable.
- C01's "drop direct vectorbt_*.py invocations" second half remains deferred until M1/M2 land (at which point the vectorbt_orb / report_generator lines in CLAUDE.md's direct-CLIs block can be removed).

### Notes for Reviewer

**1. Smallest session in the campaign.** 3 findings, all docs-only, 4 files touched in the repo (3 committed + implicit verification reads). No runtime code modified. No new tests. Pytest delta of +5 is FIX-18's work bleeding into the observation window, not FIX-10's.

**2. Parallel-session hygiene proof.** FIX-18 was running concurrently on the same working tree and added DEF-178/179/180 entries to CLAUDE.md, plus changes to pyproject.toml, .env.example, scripts/resolve_sweep_symbols.py, tests/scripts/test_resolve_sweep_symbols.py, and docs/audits/audit-2026-04-21/p1-i-dependencies.md. None of FIX-18's changes appear in FIX-10's commit (`675bf78`). The clean separation was achieved by: (a) backing up CLAUDE.md containing both sessions' edits; (b) `git checkout HEAD -- CLAUDE.md`; (c) re-applying only the Backtesting edit; (d) staging with explicit file paths (`git add CLAUDE.md docs/audits/...`); (e) committing; (f) restoring CLAUDE.md from backup so FIX-18's unstaged DEF additions are preserved in the working tree for their session to commit. `git stash push --include-untracked` was used to carry FIX-18's unstaged work across the rebase+push.

**3. Suggested-fix conditionality.** All three findings had conditional suggested fixes ("If M1/M2 land...", "No action. Revisit when M5's DEF is closed.", "If M2 is adopted... Otherwise leave alone."). None of the preconditions (M1, M2, M5) were met by this session's scope. C01 received a partial additive fix; L01 and L02 were marked RESOLVED-VERIFIED. No invented fixes were applied.

**4. Campaign-hygiene grep-verified.** Pre-edit and post-edit greps confirmed prior-session resolution entries (DEF-074, DEF-082, DEF-093, DEF-097, DEF-109, DEF-142, DEF-162, DEF-172, DEF-173, DEF-175, DEF-176, DEF-177) untouched. Active-sprint header line on CLAUDE.md line 8 is owned by the running register and was not modified.

---END-CLOSE-OUT---
```

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "audit-2026-04-21-phase-3",
  "session": "FIX-10-backtest-legacy-cleanup",
  "verdict": "COMPLETE",
  "tests": {
    "before": 4985,
    "after": 4990,
    "new": 0,
    "all_pass": true
  },
  "files_created": [],
  "files_modified": [
    "CLAUDE.md",
    "docs/audits/audit-2026-04-21/p1-e2-backtest-legacy.md",
    "docs/audits/audit-2026-04-21/phase-2-review.csv"
  ],
  "files_deleted": [],
  "files_should_not_have_modified": [],
  "scope_additions": [
    {
      "description": "C01 suggested fix was conditional on M1/M2 landing; applied a partial additive fix (add wrappers, retain direct CLIs under sub-heading) rather than either a pure no-op or the full retune.",
      "justification": "The cosmetic developer-confusion concern is real even without M1/M2. Additive edit preserves pre-existing behavior and defers the 'drop vectorbt_*.py invocations' part of the suggested fix until the session that actually lands M1/M2."
    }
  ],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "M1-M4 remain open for Phase 3 follow-on (routed to FIX-09-backtest-engine).",
    "M5 (walk-forward migration to BacktestEngine) is the gate for DEC-149 retirement; no DEF opened yet per the p1-e2 audit's DEC-149 Recommendation section.",
    "C01's 'drop vectorbt_*.py invocations' second half deferred pending M1/M2.",
    "3 stale HTML files in reports/ retained pending M2 per suggested fix's 'Otherwise leave alone' clause."
  ],
  "doc_impacts": [
    {"document": "CLAUDE.md", "change_description": "Backtesting Commands section split into operational wrappers vs direct module CLIs sub-headings."},
    {"document": "docs/audits/audit-2026-04-21/p1-e2-backtest-legacy.md", "change_description": "Appended FIX-10 Resolution section (2026-04-22) enumerating C1/L1/L2 verdicts."},
    {"document": "docs/audits/audit-2026-04-21/phase-2-review.csv", "change_description": "3 rows back-annotated in notes column (C01 RESOLVED; L01 and L02 RESOLVED-VERIFIED)."}
  ],
  "dec_entries_needed": [],
  "warnings": [
    "Concurrent FIX-18 session modified CLAUDE.md + pyproject.toml + scripts/resolve_sweep_symbols.py + tests/scripts/test_resolve_sweep_symbols.py + .env.example + p1-i-dependencies.md in the shared working tree. FIX-10 staged only its own hunks (see close-out Note 2 for the hygiene protocol used). Commit 675bf78 contains only FIX-10 edits."
  ],
  "implementation_notes": "Smallest session of the campaign (3 findings, docs-only). All three suggested fixes had unmet preconditions (M1/M2/M5). C01 received a partial additive fix (add operational wrappers above pre-existing direct CLIs); L01 and L02 marked RESOLVED-VERIFIED with explicit verification commands. Parallel FIX-18 session added concurrent CLAUDE.md changes — staged only the FIX-10 Backtesting hunk via checkout+re-apply+restore protocol. No runtime code touched, no new tests, no DEFs/DECs opened."
}
```
