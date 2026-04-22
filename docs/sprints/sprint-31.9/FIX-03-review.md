# FIX-03-main-py — Tier 2 Review Report

> Tier 2 independent review produced per `workflow/claude/skills/review.md`.
> Paste the fenced block below into the Work Journal on Claude.ai alongside
> the close-out.

```markdown
---BEGIN-REVIEW---

**Reviewing:** audit-2026-04-21-phase-3 — FIX-03-main-py (main.py lifecycle, imports, type hints, dead wiring)
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-04-22
**Verdict:** CONCERNS

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | 16 files touched; all within declared scope (main.py + 3 adjacent argus/ modules + 7 audit docs + 3 tests + CLAUDE.md + architecture.md). `argus/intelligence/experiments/store.py` intentionally not modified — Finding 29's fix is a call site in main.py; explicitly explained in close-out Note 5. `argus/strategies/pattern_strategy.py` gained `set_config_fingerprint()` as an in-scope encapsulation helper required by Finding 4. No Rule-4 sensitive file touched. |
| Close-Out Accuracy | PARTIAL-FAIL | Change manifest, judgment calls, and test results all match reality. However, Regression Checks row "Every DEF closure recorded in CLAUDE.md | PASS | DEF-074 struck through; DEF-093 struck through" is **incorrect** — CLAUDE.md lines 317 and 347 still carry the live (non-strikethrough) entries for DEF-074 and DEF-093. See MEDIUM finding below. |
| Test Health | PASS | Verified 4,944 passed + 2 failed (`test_get_todays_pnl_excludes_unrecoverable`, `test_history_store_migration` — both DEF-163 date-decay, pre-existing). Matches close-out exactly. DEF-150 flake did not fire this run. DEF-171 ibkr xdist flake also did not fire. No new failure surfaces. Net delta -1 fully explained by 2 intentional test deletions (orphan tests for the now-deleted `_run_regime_reclassification` method) + DEF-150 flake recovery (+1); this is legal under Universal RULE-019 since the tested behavior itself was removed. |
| Regression Checklist | PARTIAL-PASS | 7 of 8 campaign-level checks truly pass. Check "Every DEF closure recorded in CLAUDE.md" is marked PASS in the close-out but is actually incorrect — the claimed strikethroughs for DEF-074 and DEF-093 were never applied. |
| Architectural Compliance | PASS | Mid-day reconstruction path correctly preserved via DEC-368 IntradayCandleStore + `PatternBasedStrategy.backfill_candles()` + `strategy.reconstruct_state()` (Phase 9 / orchestrator.run_pre_market). `ThrottledLogger` pattern applied per `.claude/rules/code-style.md` § ThrottledLogger. Close-path symmetry restored per architecture.md § Separate-DB Pattern. Encapsulation-preserving setter `set_config_fingerprint()` on PatternBasedStrategy matches project-rule guidance for callable-not-attribute. Alpaca lazy import matches IBKR/Simulated pattern per Finding 19. Typing tightened on `Orchestrator._latest_regime_vector: RegimeVector \| None` via TYPE_CHECKING (no runtime import cycle). |
| Escalation Criteria | NONE_TRIGGERED | CRITICAL P1-A1-C01 resolved (method deleted, no remaining call sites); pytest net delta -1 is fully and correctly justified (intentional deletion with behaviour coverage preserved); no scope-boundary violation; no different test failure surfaces (only the expected DEF-163 set); no Rule-4 file touched; audit-report back-annotations present (31 rows in phase-2-review.csv, 6 per-domain audit MDs). |

### Findings

#### MEDIUM — Close-out regression-check row misreports CLAUDE.md DEF strikethroughs

**File:** `CLAUDE.md:317,347` and `docs/sprints/sprint-31.9/FIX-03-closeout.md` Regression Checks table
**Category:** DOC / NAMING_CONVENTION

The close-out's Regression Checks table claims:
> `| Every DEF closure recorded in CLAUDE.md | PASS | DEF-074 struck through; DEF-093 struck through; ...`

Verification with `grep -n "DEF-074\|DEF-093" CLAUDE.md` shows both entries still present as live (non-strikethrough) rows:
- Line 317: `| DEF-074 | Dual regime recheck path consolidation | Natural lull / future cleanup | ...`
- Line 347: `| DEF-093 | main.py duplicate orchestrator YAML load ... | Unscheduled | ...`

This violates `.claude/rules/doc-updates.md` § Numbering Hygiene, which codifies strikethrough as the canonical pattern: `| ~~DEF-NNN~~ | ~~Title~~ | — | **RESOLVED** (context) |`. It also violates Universal RULE-014 (doc updates happen in the same session as code changes).

Impact is doc-only — no production-code regression, no test breakage. But future doc-sync passes will read DEF-074/DEF-093 as still-open when they are in fact resolved by FIX-03 (per commit message, close-out prose, audit back-annotations, and the code itself), creating exactly the kind of stale-reference drift `.claude/rules/doc-updates.md` was written to prevent.

**Recommendation:** Quick follow-up pass (≤5 minutes, doc-only) to apply the canonical strikethrough to both rows in CLAUDE.md. Can be bundled into the next doc-sync pass or the next FIX session's edits — does not block proceeding.

**Post-review resolution note:** The operator applied the strikethroughs in the same FIX-03 commit (a follow-up commit on top of 80af45b); see CLAUDE.md lines 317 and 347 for the canonical `~~…~~ **RESOLVED** (FIX-03, audit 2026-04-21): …` form.

#### LOW — "10 main.py sites migrated" phrasing in close-out is technically correct but easy to misread

**File:** `docs/sprints/sprint-31.9/FIX-03-closeout.md` Scope Verification row "Finding 4 (P1-A1-M04): set_config_fingerprint"
**Category:** DOC / NAMING

Close-out says "10 main.py sites + 1 spawner.py site migrated". Reality: the 10 old direct-attribute assignment blocks were **collapsed into a single loop** (Finding 5 / M5) which now contains **one** `set_config_fingerprint` call at `argus/main.py:604` that fires for all 10 patterns. A fresh reader scanning for "10 call sites" will find only one and may suspect incomplete migration. Cosmetic; close-out Note 3 on the pattern_definitions loop does implicitly cover this, but the Finding 4 row could be clearer.

No action required — flagging for context only.

#### LOW — Three PARTIAL resolutions with DEFs logged, all scope-respecting

Three of the 31 findings received PARTIAL resolutions:

1. **Finding 23 (P1-D1-M13)** — close-path symmetry restored via M3; DEF-172 opened to track the full dedup (requires `argus/api/server.py` lifespan edit, FIX-11 territory, already closed).
2. **Finding 29 (P1-D2-M03)** — ExperimentStore retention wired into main.py boot; LearningStore retention deferred as DEF-173 (same api/server.py lifespan dependency).
3. **Finding 31 (DEF-048+049)** — env-leak autouse fixture `_scrub_anthropic_env` added (DEF-046 pattern, as the finding requested); DEF-049's stale-mock isolation failure of `test_orchestrator_uses_strategies_from_registry` is acknowledged as pre-existing and out of the "apply DEF-046 pattern" scope.

All three partials are consistent with the kickoff prompt's explicit exclusion of `argus/api/*` (FIX-11 territory) and with close-out.md's guidance on scope-respecting partials + DEF logging. DEF-172 and DEF-173 are both present in CLAUDE.md at lines 427–428 with full context, trigger, and priority. Good scope discipline.

#### LOW — Judgment call on `_counterfactual_enabled` convention (all-getattr) is well-reasoned

Close-out Judgment Call #2 documents that the initial direct-access implementation (matching the audit's nominal preference) broke ~20 integration tests that construct `ArgusSystem.__new__(ArgusSystem)` without running `__init__`, relying on `getattr`'s default. Revert to all-getattr preserves the test-construction contract. Verified in code: line 181 declares the attribute, line 1092 does the direct write (guaranteed-post-init), and all 5 read sites (1573, 1653, 1691, 1747, 1763) use `getattr(self, '_counterfactual_enabled', False)`. Consistent.

If the project ever wants the direct-access convention, the ~20 integration tests would need `.set_counterfactual_enabled(False)` (or similar) in their `__new__`-construction helpers — out of FIX-03 scope.

### Recommendation

**Verdict: CONCERNS.** All critical functions work, all 31 findings are addressed (28 fully, 3 partials with DEFs logged), all tests pass as expected, and scope compliance is clean. The CONCERNS verdict is driven by a single MEDIUM doc-hygiene gap: the close-out's Regression Checks row claims DEF-074 and DEF-093 were struck through in CLAUDE.md, but they are still live (non-strikethrough) rows. This is a doc-drift issue, not a code regression — no blocker for the sprint to proceed, but it should be cleaned up on the next doc touch.

Proceed to the next session. The MEDIUM finding can be folded into the next doc-sync pass or caught by a follow-up 5-minute touch. No Tier 3 architectural escalation needed.

---END-REVIEW---
```

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "audit-2026-04-21-phase-3",
  "session": "FIX-03-main-py",
  "verdict": "CONCERNS",
  "findings": [
    {
      "description": "Close-out's Regression Checks row claims DEF-074 and DEF-093 were struck through in CLAUDE.md, but grep -n on CLAUDE.md shows both entries still live (non-strikethrough) at lines 317 and 347. Violates .claude/rules/doc-updates.md Numbering Hygiene and Universal RULE-014.",
      "severity": "MEDIUM",
      "category": "OTHER",
      "file": "CLAUDE.md",
      "recommendation": "Apply canonical strikethrough to DEF-074 and DEF-093 rows with RESOLVED (FIX-03, audit 2026-04-21) annotations. 5-minute doc-only follow-up; can fold into next doc-sync pass. (Operator resolved in-session as part of the FIX-03 commit set — see post-review resolution note.)"
    },
    {
      "description": "Close-out's Finding 4 scope-verification row says '10 main.py sites + 1 spawner.py site migrated' but reality is that the 10 blocks were collapsed (Finding 5) into a single loop with one set_config_fingerprint call. Technically correct but easy to misread as incomplete migration.",
      "severity": "LOW",
      "category": "OTHER",
      "file": "docs/sprints/sprint-31.9/FIX-03-closeout.md",
      "recommendation": "No action required. Flagging for context only."
    },
    {
      "description": "Three PARTIAL resolutions (Finding 23 P1-D1-M13, Finding 29 P1-D2-M03, Finding 31 DEF-048+049) are all scope-respecting with DEFs logged (DEF-172, DEF-173) or documented pre-existing conditions. Partials are consistent with kickoff prompt's explicit exclusion of argus/api/*.",
      "severity": "LOW",
      "category": "OTHER",
      "recommendation": "No action required. Good scope discipline."
    },
    {
      "description": "Judgment call on _counterfactual_enabled convention reverted from direct access (audit's nominal preference) to all-getattr after initial direct-access broke ~20 integration tests that construct ArgusSystem via __new__. Well-reasoned; preserves test-construction contract.",
      "severity": "LOW",
      "category": "OTHER",
      "file": "argus/main.py",
      "recommendation": "No action required. If future work wants direct access, ~20 integration tests need __new__-construction helpers updated — out of FIX-03 scope."
    }
  ],
  "spec_conformance": {
    "status": "MINOR_DEVIATION",
    "notes": "All 31 findings addressed (28 fully RESOLVED, 3 PARTIAL with DEFs logged). 3 PARTIAL resolutions are scope-respecting per kickoff prompt's argus/api/* exclusion. Self-assessment of MINOR_DEVIATIONS is accurate. The one MEDIUM review finding is a doc-hygiene regression-check misreport, not a spec deviation.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/main.py",
    "argus/core/orchestrator.py",
    "argus/intelligence/experiments/spawner.py",
    "argus/strategies/pattern_strategy.py",
    "docs/architecture.md",
    "docs/audits/audit-2026-04-21/phase-2-review.csv",
    "docs/audits/audit-2026-04-21/p1-a1-main-py.md",
    "docs/audits/audit-2026-04-21/p1-a2-core-rest.md",
    "docs/audits/audit-2026-04-21/p1-c1-execution.md",
    "docs/audits/audit-2026-04-21/p1-d1-catalyst-quality.md",
    "docs/audits/audit-2026-04-21/p1-d2-experiments-learning.md",
    "docs/audits/audit-2026-04-21/p1-g1-test-coverage.md",
    "tests/test_main.py",
    "tests/core/test_orchestrator.py",
    "tests/test_shutdown_tasks.py",
    "CLAUDE.md"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": false,
    "count": 4944,
    "new_tests_adequate": true,
    "test_quality_notes": "4,944 passed + 2 failed (DEF-163 date-decay × 2, pre-existing known-flake set — matches close-out). Net delta -1 from baseline 4,945 is fully explained: 2 intentional test deletions for the now-deleted _run_regime_reclassification method (Finding 10 / DEF-074) + DEF-150 flake recovery (+1). Intentional deletions are legal under Universal RULE-019 since the tested behavior itself was removed; intent is covered by existing Orchestrator._run_regime_recheck + _poll_loop tests in the same file. Verified via python -m pytest --ignore=tests/test_main.py -n auto --tb=no -q."
  },
  "regression_checklist": {
    "all_passed": false,
    "results": [
      {"check": "pytest net delta >= 0 against baseline 4,945 passed", "passed": true, "notes": "Delta -1 but fully justified by intentional test deletions paired with deleted production code (Finding 10 / DEF-074). No passing test became failing. Legal under RULE-019."},
      {"check": "Failures match known flake set (DEF-150, DEF-163)", "passed": true, "notes": "2 failures are both DEF-163 date-decay. DEF-150 and DEF-171 ibkr flake did not fire."},
      {"check": "No file outside declared Scope modified", "passed": true, "notes": "16 files, all within declared scope. argus/intelligence/experiments/store.py intentionally not modified (close-out Note 5). argus/strategies/pattern_strategy.py addition justified as Finding 4 encapsulation helper."},
      {"check": "Every resolved finding back-annotated in audit report", "passed": true, "notes": "31 back-annotations in phase-2-review.csv (28 RESOLVED + 2 PARTIALLY RESOLVED + 1 RESOLVED-VERIFIED). 6 per-domain audit MDs each carry 'FIX-03 Resolution' sections."},
      {"check": "Every DEF closure recorded in CLAUDE.md", "passed": false, "notes": "FAIL at initial review. Close-out claimed DEF-074 and DEF-093 struck through in CLAUDE.md, but grep confirmed both still live non-strikethrough rows at lines 317 and 347. Operator applied canonical strikethrough in the same FIX-03 commit set post-review. See MEDIUM finding."},
      {"check": "Every new DEF/DEC referenced in commit message bullets", "passed": true, "notes": "DEF-172 and DEF-173 both present in commit message 80af45b; both also present in CLAUDE.md Deferred Items table at lines 427–428."},
      {"check": "read-only-no-fix-needed findings verification recorded OR DEF promoted", "passed": true, "notes": "P1-G1-M02 back-annotated as RESOLVED-VERIFIED FIX-03-main-py."},
      {"check": "deferred-to-defs findings: fix applied AND DEF-NNN added to CLAUDE.md", "passed": true, "notes": "P1-D1-M13 fix-path symmetry applied + DEF-172 logged; P1-D2-M03 ExperimentStore retention wired + DEF-173 for LearningStore half. Both DEFs present in CLAUDE.md."}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "[Resolved in-session] Apply canonical ~~strikethrough~~ to DEF-074 and DEF-093 rows in CLAUDE.md's Deferred Items table (lines 317 and 347). Operator landed this as a follow-up commit on top of 80af45b.",
    "Optional: tighten the close-out's Finding 4 scope-verification wording to acknowledge that the 10 old call sites were collapsed into a single loop, not individually migrated. Cosmetic."
  ]
}
```
