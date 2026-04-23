---BEGIN-REVIEW---
```markdown
# Tier 2 Review — FIX-08-intelligence-experiments-learning

- **Reviewing:** `audit-2026-04-21-phase-3` — FIX-08-intelligence-experiments-learning (Sprint 31.9, Stage 6 solo)
- **Reviewer:** Tier 2 Automated Review (fresh read-only subagent)
- **Date:** 2026-04-22
- **Verdict:** `CLEAR`
- **Commit reviewed:** `33ad7da` (diff range `0d8b485..33ad7da`)
- **Campaign HEAD at session start:** `0d8b485`
- **Baseline pytest:** 5,028 passed (1 pre-existing DEF-163 failure)
- **Post-session pytest (reviewer's fresh run):** 5,035 passed, 1 failed (DEF-163 — `test_get_todays_pnl_excludes_unrecoverable`, pre-existing date/timezone hygiene). Net delta vs baseline: **+7**.
- **Vitest:** 859 passed → 859 passed (no delta)

## Assessment Summary

| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | All 16 declared files modified within scope. No Hazard 5 file (`argus/strategies/patterns/factory.py`) touched. Two out-of-scope file edits (`tests/intelligence/test_scoring_fingerprint.py` + `argus/ui/src/components/learning/LearningInsightsPanel.tsx` vs spec's `features/learning/LearningInsightsPanel.ts`) are both explicitly justified in the close-out: the test file is a downstream consumer of renamed promotion methods (behavior-preserving migration); the .tsx path drift is documented P12 verification of an incorrect spec scope header — actual file edited. |
| Close-Out Accuracy | PASS | Manifest matches `git diff --stat HEAD~1`. Self-assessed MINOR_DEVIATIONS is justified by the documented spec path drift on Finding 18 + the test-file ripple from Finding 7. |
| Test Health | PASS | pytest 5,028 → 5,035 (net **+7**). Vitest 859 → 859 (no delta). Single failure is `tests/analytics/test_def159_entry_price_known.py::test_get_todays_pnl_excludes_unrecoverable` — exactly the expected DEF-163 pre-existing failure. New tests (8 added across test_runner.py + test_config_proposal_manager.py + test_threshold_analyzer.py + test_models.py) are meaningful: hash parity, executor cleanup, redistribution drift visibility, threshold conflict resolution, date serialization. Pinned hash `ddec1b2a09ee2263` independently verified by re-derivation. |
| Regression Checklist | PASS | All 8 campaign-level checks pass. (1) net delta +7 ≥ 0; (2) DEF-163 is the only failure (kickoff prompt expected DEF-150 but DEF-163 is the actual baseline failure — both are LOW pre-existing date/timezone hygiene items batched into FIX-13); (3) no out-of-scope sensitive files touched; (4) 16 audit-doc rows correctly back-annotated (3× RESOLVED-VERIFIED, 13× RESOLVED); (5) DEF-107 + DEF-123 strikethrough'd in CLAUDE.md DEF table at lines 337 + 353; (6) no new DEFs/DECs (correct); (7) L-04/L-05/C-03 + DEF-123 verifications recorded in audit doc with grep evidence; (8) no `deferred-to-defs` findings in scope. |
| Architectural Compliance | PASS | Pydantic `VariantConfig` follows existing config-gating pattern (`extra="forbid"`, `default_factory`). `dataclasses.replace` usage on frozen `VariantDefinition` is idiomatic. ProcessPoolExecutor `try/finally` cleanup matches the architecture rule for executor lifetime. `_make_unsupported_record` + `_make_result_record` are clean static helpers — no shared mutable state. Narrowing `except Exception` → `except aiosqlite.OperationalError` with sanity check on error message is consistent with project error-handling rules. Date-vs-datetime widening uses `isinstance(val, date)` with documented subclass dispatch — order-correct. |
| Escalation Criteria | NONE_TRIGGERED | No CRITICAL findings, pytest delta positive, no scope boundary violation, only DEF-163 pre-existing failure (not a new regression), no Rule-4 sensitive file touched, all audit back-annotations present and well-formed. |

## Findings

**No HIGH or CRITICAL findings.** Selected verification observations:

1. **Finding 1 (M-02 fingerprint parity) — CONFIRMED CORRECT.** Independent re-derivation: with `detection={"pole_min_move_pct":0.03,"flag_max_bars":20}` + `exit={"trailing_stop.atr_multiplier":2.5}`, both runner reshape and factory `compute_parameter_fingerprint` produce `f34adc8d4460b65b`. Detection-only path also pinned to `ddec1b2a09ee2263` (byte-identical to pre-FIX-08 implementation, preserving any existing `data/experiments.db` rows). The new test `test_compute_fingerprint_with_exit_overrides_matches_factory` correctly exercises the runner-side reshape against the factory's canonical form. Hazard 5 honored — no factory.py modification.

2. **Finding 7 (test_scoring_fingerprint.py) — CONFIRMED BEHAVIOR-PRESERVING.** The test was updated from a single `await evaluator._build_result_from_shadow(...)` call to the new `_fetch_shadow_positions(...)` + `_build_result_from_positions(...)` pair. The assertion semantics (expectancy sign flips between fingerprints, results comparable across A/B/all) are unchanged. The change is mechanically equivalent to the pre-FIX-08 path; this is a routine downstream-consumer migration, not a scope violation.

3. **Finding 17 (M-04 threshold contradictions) — CORRECT SEMANTIC CHANGE.** Spec-recommended option (a) cleanly applied: `if (correct < 0.50) raise; elif (missed > 0.40) lower; else no-rec`. The renamed test `test_both_conditions_simultaneous_emit_only_raise` documents the new behavior; the legacy assertion intentionally captured the bug (both directions emitted). `test_high_missed_opportunity_recommends_lower` data shape was updated to use a 9p+11n sample (missed=0.45, correct=0.55) to exercise the elif branch in isolation — this is necessary precisely because the new semantics make the elif unreachable when `correct < 0.50`. The test data update is spec-aligned, not a regression. Note: the `LearningInsightsPanel.tsx` "conflicting threshold" card is now unreachable in normal operation (no new conflicts generated), but is preserved for any pre-FIX-08 conflicting proposals already persisted — appropriate defensive carry-forward.

4. **Finding 6 (DEF-123) — RESOLVED-VERIFIED is JUSTIFIED.** The existing implementation `round(min + i*step, 6)` for `i in range(n_steps + 1)` is mathematically equivalent to `numpy.arange(min, max+step, step)` modulo float representation, and `round(_, 6)` already collapses any residual drift. Adding numpy to a hot grid path purely for cosmetic API symmetry would be over-engineering; the rationale is captured in inline docstrings on both `_generate_param_values` and `_generate_exit_values`. I agree with the RESOLVED-VERIFIED verdict.

5. **Finding 13 (C-02 VariantConfig) — Hazard 4 NOT BREACHED.** `config/experiments.yaml` round-trips cleanly through `ExperimentConfig(**yaml)` per the close-out (all 22 variants parse). Production path still consumes the YAML as raw dicts via `VariantSpawner` (verified by reading the unchanged spawner code path), so the typed shape is purely additive — Pydantic-aware consumers (tests, future startup wiring) get type safety, in-flight shadow trading config remains untouched.

6. **Finding 18 (DEF-107 path drift) — CORRECT P12 BEHAVIOR.** Spec scope header listed `argus/ui/src/features/learning/LearningInsightsPanel.ts` (wrong subdirectory + wrong extension). Actual file is `argus/ui/src/components/learning/LearningInsightsPanel.tsx`. Implementation correctly edited the existing file rather than creating a phantom one matching the spec path. The CLAUDE.md DEF-107 closure documents the path drift explicitly. This is the textbook P12 verification protocol response.

7. **L-03 ProcessPoolExecutor cleanup — VERIFIED THROUGH NEW TEST.** `test_parallel_executor_shutdown_on_save_exception` uses a recording `ThreadPoolExecutor` subclass to assert `shutdown(wait=True, cancel_futures=False)` fires exactly once on a `RuntimeError` from `save_experiment`. The `try/except KeyboardInterrupt/finally` structure is correct: the `interrupted` flag drives `wait=not interrupted, cancel_futures=interrupted`, so KeyboardInterrupt → cancel-and-don't-wait, any other exception → wait-for-cleanup-then-propagate.

8. **L-02 promotion query collapse — BEHAVIOR-PRESERVING.** The refactor splits the old `_build_result_from_shadow` (which fetched + computed) into `_fetch_shadow_positions` (fetch only) + `_build_result_from_positions` (pure compute) + `_count_unique_days` (pure compute). Callers in `_evaluate_for_promotion` fetch once and feed both. Limit + scoping_fingerprint semantics preserved.

9. **M-05 redistribution drift recording — VERIFIED THROUGH INTEGRATION-LEVEL TEST.** `test_redistribution_drift_visible_to_cumulative_drift_guard` exercises 3 sequential proposals each promoting a different dim, then asserts `get_cumulative_drift("historical_match")` (which is never explicitly targeted) equals the sum of recorded redistribution deltas. Pre-FIX-08 this would be 0.0; post-fix it matches recorded sum. The `_snapshot_weights` helper iterates `_WEIGHT_DIMENSIONS` consistently, and the per-proposal `redistribution_deltas` map is keyed by `proposal_id` so concurrent application order is preserved. The legacy `test_apply_pending_records_change_history` was correctly updated from "1 record" to "1 explicit + 4 redistributed" to reflect the new accounting.

10. **L-01 date/datetime widening — CORRECT SUBCLASS-DISPATCH ORDER.** `isinstance(val, date)` matches both `date` and `datetime` (datetime is a subclass of date), and Python dispatches to the subclass's overridden `isoformat()` first, so `datetime` still produces the richer "YYYY-MM-DDTHH:MM:SS+TZ" form. The new `test_convert_datetimes_handles_date` exercises both types in nested + list positions.

## Recommendation

Proceed to next session. All 18 findings resolved (13 RESOLVED + 3 RESOLVED-VERIFIED in audit doc + 2 closures in CLAUDE.md DEF table). MINOR_DEVIATIONS self-assessment is the correct rating — the deviations (test-file ripple from Finding 7, spec path drift on Finding 18) are well-documented and reviewer-confirmed as appropriate. No follow-up action needed.

**Verification commands run:**
- `python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -5` → `1 failed, 5035 passed, 43 warnings in 59.67s` (only failure = expected DEF-163)
- `cd argus/ui && npx vitest run` → `Test Files 115 passed (115) | Tests 859 passed (859)`
- Independent fingerprint hash re-derivation: detection-only `ddec1b2a09ee2263` matches pinned test value; exit-overrides `f34adc8d4460b65b` matches between runner reshape and factory canonical form
- `git diff HEAD~1 HEAD --name-only | grep -E "factory|patterns/__|argus/main\.py|api/server"` → empty (Hazard 5 honored, no sensitive file touched)
- Audit doc back-annotation count: 13 RESOLVED + 3 RESOLVED-VERIFIED = 16 (matches the 16 rows in P1-D2 audit doc)
- CLAUDE.md DEF closures: DEF-107 (L337) + DEF-123 (L353) both strikethrough'd
```

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "audit-2026-04-21-phase-3",
  "session": "FIX-08-intelligence-experiments-learning",
  "verdict": "CLEAR",
  "findings": [
    {
      "description": "Finding 7 ripple: tests/intelligence/test_scoring_fingerprint.py modified outside declared 'Files touched' as downstream consumer of removed _build_result_from_shadow method. Migration is mechanically behavior-preserving (single fetch + pure compute pair replaces old fetch+compute method). Documented in close-out.",
      "severity": "INFO",
      "category": "SCOPE_BOUNDARY_VIOLATION",
      "file": "tests/intelligence/test_scoring_fingerprint.py",
      "recommendation": "Acceptable — informational only. Future spec scope sections should pre-enumerate downstream test consumers when refactoring public method signatures."
    },
    {
      "description": "Finding 18 spec path drift: spec listed argus/ui/src/features/learning/LearningInsightsPanel.ts but actual file is argus/ui/src/components/learning/LearningInsightsPanel.tsx. Implementation correctly edited the actual file. CLAUDE.md DEF-107 row notes the drift explicitly.",
      "severity": "INFO",
      "category": "OTHER",
      "file": "argus/ui/src/components/learning/LearningInsightsPanel.tsx",
      "recommendation": "P12 protocol working as designed. No action."
    },
    {
      "description": "Finding 17 secondary effect: LearningInsightsPanel.tsx 'conflictingThresholds' card is now unreachable in normal operation (M-04 fix prevents new conflicts), but card is preserved for any pre-FIX-08 conflicting proposals already in DB. Cosmetic dead UI for new state, defensible carry-forward for in-flight DB.",
      "severity": "INFO",
      "category": "OTHER",
      "file": "argus/ui/src/components/learning/LearningInsightsPanel.tsx",
      "recommendation": "Re-evaluate in a future UI cleanup sprint — once any pre-FIX-08 conflicting proposals have aged out via retention, the entire conflictingThresholds map block can be deleted."
    }
  ],
  "spec_conformance": {
    "status": "MINOR_DEVIATION",
    "notes": "All 18 findings addressed. Two minor deviations from spec letter — both well-documented and reviewer-validated: (a) test_scoring_fingerprint.py ripple from Finding 7's promotion method rename, behavior-preserving; (b) Finding 18 path drift in spec scope header, edit went to actual existing file (P12 verification working correctly).",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/intelligence/experiments/config.py",
    "argus/intelligence/experiments/promotion.py",
    "argus/intelligence/experiments/runner.py",
    "argus/intelligence/experiments/store.py",
    "argus/intelligence/learning/config_proposal_manager.py",
    "argus/intelligence/learning/learning_service.py",
    "argus/intelligence/learning/models.py",
    "argus/intelligence/learning/threshold_analyzer.py",
    "argus/ui/src/components/learning/LearningInsightsPanel.tsx",
    "tests/intelligence/experiments/test_runner.py",
    "tests/intelligence/learning/test_config_proposal_manager.py",
    "tests/intelligence/learning/test_models.py",
    "tests/intelligence/learning/test_threshold_analyzer.py",
    "tests/intelligence/test_scoring_fingerprint.py",
    "docs/audits/audit-2026-04-21/p1-d2-experiments-learning.md",
    "CLAUDE.md"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 5035,
    "new_tests_adequate": true,
    "test_quality_notes": "8 new tests added, all meaningful: (1) test_compute_fingerprint_detection_only_pinned anchors backward-compat to pinned hash ddec1b2a09ee2263 (independently verified); (2) test_compute_fingerprint_with_exit_overrides_matches_factory + test_compute_fingerprint_detection_only_factory_parity verify cross-surface dedup invariant; (3) test_parallel_executor_shutdown_on_save_exception uses recording ThreadPoolExecutor subclass to assert shutdown(wait=True, cancel_futures=False) fires once on save failure; (4) test_apply_pending_records_change_history updated 1->5 records to reflect redistribution accounting; (5) test_redistribution_drift_visible_to_cumulative_drift_guard exercises 3 sequential proposals with end-to-end drift assertion; (6) test_both_conditions_simultaneous_emit_only_raise + test_no_recommendation_when_neither_threshold_breached document new threshold semantics; (7) test_convert_datetimes_handles_date exercises date + datetime in nested + list positions. The vitest suite (859 tests) was unchanged because no test referenced the deleted raiseRec destructure."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "pytest net delta >= 0 against baseline 5,028", "passed": true, "notes": "5028 -> 5035 (net +7), matches close-out"},
      {"check": "Pre-existing failure remains the only failure (DEF-163 was the actual baseline failure; kickoff prompt mentioned DEF-150 in error)", "passed": true, "notes": "Single failure: tests/analytics/test_def159_entry_price_known.py::test_get_todays_pnl_excludes_unrecoverable (DEF-163). No new regressions."},
      {"check": "No file outside Scope was modified", "passed": true, "notes": "Two out-of-scope edits both documented as ripple/path-drift, both behavior-preserving and reviewer-validated."},
      {"check": "Every resolved finding back-annotated in audit doc", "passed": true, "notes": "16 audit-doc rows annotated (13 RESOLVED + 3 RESOLVED-VERIFIED). DEF-107 + DEF-123 are tracked in CLAUDE.md, not audit doc — also correctly closed."},
      {"check": "Every DEF closure recorded in CLAUDE.md", "passed": true, "notes": "DEF-107 and DEF-123 both strikethrough'd at CLAUDE.md L337 and L353."},
      {"check": "Every new DEF/DEC referenced in commit-message bullets", "passed": true, "notes": "No new DEFs/DECs (correct — close-out claims 'No new DEFs/DECs')."},
      {"check": "read-only-no-fix-needed findings: verification recorded OR DEF promoted", "passed": true, "notes": "L-04 (re-grep evidence), L-05 (DDL grep evidence), C-03 (consumer grep evidence), DEF-123 (mathematical equivalence reasoning). All four verification rationales appear in the back-annotation text."},
      {"check": "deferred-to-defs findings: fix applied AND DEF-NNN added to CLAUDE.md", "passed": true, "notes": "No deferred-to-defs findings in this session's scope."}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "None. Proceed to next FIX-NN session."
  ]
}
```
---END-REVIEW---
