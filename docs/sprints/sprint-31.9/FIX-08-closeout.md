---BEGIN-CLOSE-OUT---
```markdown
# Close-Out — FIX-08-intelligence-experiments-learning

- **Sprint:** `audit-2026-04-21-phase-3`
- **Session:** `FIX-08` (full ID: `FIX-08-intelligence-experiments-learning`)
- **Date:** 2026-04-22
- **Commit:** `33ad7da` (audit + tests + docs, pushed to `origin/main`)
- **Baseline HEAD:** `0d8b485` (post-Stage 5 seal — "docs(sprint-31.9): seal Stage 5 complete + barrier update")
- **Test delta:** 5,028 → 5,035 (net +7; +7 new regression tests; 0 removed); Vitest 859 → 859 (no delta)
- **Self-Assessment:** `MINOR_DEVIATIONS`
- **Context State:** GREEN (no compaction)

## Scope

Phase 3 Stage 6 (solo session, weekend-only). Backend Python in `argus/intelligence/experiments/` (runner, promotion, store, config) + `argus/intelligence/learning/` (config_proposal_manager, learning_service, models, threshold_analyzer) + exactly one frontend file (`LearningInsightsPanel.tsx`, Finding 18). **18 findings total:** 3 MEDIUM + 7 LOW + 8 COSMETIC. No CRITICAL.

DEF closures: DEF-107 (Finding 18, raiseRec destructure) + DEF-123 (Finding 6, build_parameter_grid float accumulation, RESOLVED-VERIFIED). No new DEFs/DECs opened.

## Change Manifest

| File | Change Type | Rationale |
|------|-------------|-----------|
| `argus/intelligence/experiments/config.py` | modified | Finding 13: added `VariantConfig` Pydantic model + retyped `ExperimentConfig.variants` as `dict[str, list[VariantConfig]]`. |
| `argus/intelligence/experiments/runner.py` | modified | Findings 1, 2, 3, 4, 5, 6: fingerprint unification with factory; `try/finally` executor cleanup; shared `_make_unsupported_record` + `_make_result_record` helpers; removed local re-import aliasing in `_run_single_backtest`; collapsed `combos` materialisation; documented float-grid mitigation. |
| `argus/intelligence/experiments/promotion.py` | modified | Findings 7, 8: collapsed `_build_result_from_shadow` + `_count_shadow_trading_days` into `_fetch_shadow_positions` + `_build_result_from_positions` + `_count_unique_days` (single counterfactual query); replaced hand-built `VariantDefinition` with `dataclasses.replace`. |
| `argus/intelligence/experiments/store.py` | modified | Finding 10: narrowed bare `except Exception: pass` on the idempotent `ALTER TABLE` to `aiosqlite.OperationalError` with a duplicate-column sanity check. |
| `argus/intelligence/learning/learning_service.py` | modified | Finding 12: defensive correlation formatting in proposal rationale (`(trade_src or cf_src or 0.0)` then `{:+.4f}`). |
| `argus/intelligence/learning/models.py` | modified | Finding 16: widened `_convert_datetimes` from `datetime`-only to `(date, datetime)` to prevent the latent DEF-151-class crash on bare `date` fields. |
| `argus/intelligence/learning/config_proposal_manager.py` | modified | Finding 15: snapshot weights pre/post redistribution and emit per-dim `record_change(source="learning_loop_redistribution", proposal_id=...)` so cumulative drift guard sees redistributed dims. |
| `argus/intelligence/learning/threshold_analyzer.py` | modified | Finding 17: `_analyze_grade` rewritten as `if (correct < 0.50) "raise" elif (missed > 0.40) "lower" else no-rec` — emits at most one recommendation per grade. |
| `argus/ui/src/components/learning/LearningInsightsPanel.tsx` | modified | Finding 18 (DEF-107): removed unused `raise: raiseRec` from `conflictingThresholds.map` destructure. |
| `tests/intelligence/experiments/test_runner.py` | modified | Updated `test_run_single_backtest_passes_fingerprint` to patch runner-local `BacktestEngine` (Finding 4 side-effect); added 4 new regression tests (Findings 1+2). |
| `tests/intelligence/learning/test_config_proposal_manager.py` | modified | Updated `test_apply_pending_records_change_history` to expect 1 explicit + 4 redistribution records (was: 1); added new `test_redistribution_drift_visible_to_cumulative_drift_guard`. |
| `tests/intelligence/learning/test_models.py` | modified | Added `test_convert_datetimes_handles_date` regression. |
| `tests/intelligence/learning/test_threshold_analyzer.py` | modified | Updated `test_high_missed_opportunity_recommends_lower` for new "raise"-precedence semantics; renamed `test_both_conditions_simultaneous` → `test_both_conditions_simultaneous_emit_only_raise`; added `test_no_recommendation_when_neither_threshold_breached`. |
| `tests/intelligence/test_scoring_fingerprint.py` | modified | Migrated FIX-01 scoring-fingerprint test from removed `_build_result_from_shadow` to the new `_fetch_shadow_positions` + `_build_result_from_positions` pair (Finding 7 ripple). |
| `docs/audits/audit-2026-04-21/p1-d2-experiments-learning.md` | modified | Back-annotated all 16 in-doc finding rows (M-02, M-04, M-05, L-01..L-07, C-01..C-06): 13 RESOLVED + 3 RESOLVED-VERIFIED. |
| `CLAUDE.md` | modified | Strikethrough closures for DEF-107 (Finding 18) and DEF-123 (Finding 6, RESOLVED-VERIFIED). |

## Judgment Calls

- **Finding 1 implementation form.** Spec said "delegate to `factory.compute_parameter_fingerprint`" but the factory's signature requires a `StrategyConfig` instance + `pattern_class`, neither of which the runner has at the call sites. Chose the second spec-suggested form: reshape the runner's `{"detection_params": ..., "exit_overrides": ...}` dict into the factory's canonical `{"detection": ..., "exit": ...}` form before hashing inside `_compute_fingerprint`. Produces byte-identical hashes to factory (verified). Did **not** modify `argus/strategies/patterns/factory.py` per Hazard 5.
- **Finding 4 test-patch update.** Removing the local `BacktestEngine` re-import in `_run_single_backtest` broke `test_run_single_backtest_passes_fingerprint`, which patched `argus.backtest.engine.BacktestEngine` (the original module symbol). Updated the test to patch `argus.intelligence.experiments.runner.BacktestEngine` (the runner's bound reference) — this is the established pattern used by every other parallel-path test in the file.
- **Finding 6 (DEF-123) — chose RESOLVED-VERIFIED over the spec's `numpy.arange` migration.** Both float grid generators already use `round(min + i * step, 6)`, which is the integer-multiplied form (no cumulative round-off) — semantically equivalent to what `numpy.arange` would produce. The spec's suggested fix would add a numpy import to a hot grid path for zero behavioural gain. Documented the rationale inline in both helpers' docstrings.
- **Finding 7 method rename touched a downstream test outside scope.** Collapsing `_build_result_from_shadow` + `_count_shadow_trading_days` removed both methods. `tests/intelligence/test_scoring_fingerprint.py` (a FIX-01 test, not in this session's declared scope) called the removed `_build_result_from_shadow` 3 times. Updated those 3 call sites to the new `_fetch_shadow_positions` + `_build_result_from_positions` pair — minimal, mechanical, behaviour-preserving change. Flagged as Files-Outside-Scope-But-Necessary in the structured appendix.
- **Finding 13 (VariantConfig) — kept production read-path unchanged.** Per the audit's own note, `ExperimentConfig` is **never instantiated in production** (`main.py` reads `experiments.yaml` as a raw dict and hands it directly to `VariantSpawner`). Adding `VariantConfig` with `extra="forbid"` only protects future Pydantic-aware consumers (tests, future startup wiring). Spawner not modified — would have required broader scope changes to update its `.get()` access pattern. Verified `config/experiments.yaml` round-trips cleanly through `ExperimentConfig(**yaml)`.
- **Finding 15 cumulative-drift test infrastructure.** New `test_redistribution_drift_visible_to_cumulative_drift_guard` had to raise `LearningLoopConfig.max_cumulative_drift` to its Pydantic-allowed maximum (0.50) so three sequential +0.02 promotions don't trip the guard mid-test; this isolates the assertion to the new redistribution-recording behavior rather than guard skips.
- **Finding 17 — updated 1 existing test that asserted the buggy dual-emission behaviour.** Pre-FIX-08 `test_both_conditions_simultaneous` explicitly asserted both "lower" AND "raise" fired; the spec calls this out as the bug. Updated to assert exactly one "raise" recommendation (raise wins), and added a no-recommendation case. Also updated `test_high_missed_opportunity_recommends_lower` to use data where `missed > 0.40` AND `correct >= 0.50` (so the elif branch fires — the only path that produces "lower" under the new semantics).
- **Spec path drift on Finding 18.** Spec scope header listed `argus/ui/src/features/learning/LearningInsightsPanel.ts` (wrong directory + wrong extension) and Finding 18 body said `features/learning/LearningInsightsPanel.tsx` (wrong directory). Actual path: `argus/ui/src/components/learning/LearningInsightsPanel.tsx:388`. Edited the actual path and documented the drift in CLAUDE.md DEF-107 closure (per kickoff prompt P12 protocol).

## Scope Verification

| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| Finding 1 (P1-D2-M02): unify runner ↔ factory fingerprint | DONE | `runner._compute_fingerprint` reshapes structured-grid dict to factory's canonical `{"detection":...,"exit":...}` form. |
| Finding 2 (P1-D2-L03): ProcessPoolExecutor cleanup on any exception | DONE | `try/except KeyboardInterrupt/finally` with `interrupted` flag driving `shutdown(wait=not interrupted, cancel_futures=interrupted)`. |
| Finding 3 (P1-D2-L06): extract record-construction helper | DONE | New `_make_unsupported_record` + `_make_result_record` static helpers used by both sweep paths. |
| Finding 4 (P1-D2-C01): runner aliasing cleanup | DONE | Removed 6 local `noqa: PLC0415` re-imports; worker now uses module-scope imports. |
| Finding 5 (P1-D2-C05): single materialisation in grid generator | DONE | Single comprehension over `itertools.product(*(...))` generator. Same shape applied to `exit_grid`. |
| Finding 6 (DEF-123): float accumulation | DONE-VERIFIED | Confirmed integer-multiplied form already in place; `numpy.arange` migration deemed cosmetic-only and skipped. Docstrings updated to capture rationale. |
| Finding 7 (P1-D2-L02): single counterfactual query for promotion | DONE | `_fetch_shadow_positions` + `_build_result_from_positions` + `_count_unique_days`. |
| Finding 8 (P1-D2-C04): `dataclasses.replace` in promotion | DONE | One-line replacement of the 7-field hand copy. |
| Finding 9 (P1-D2-L05): shadow_trades int coercion | DONE-VERIFIED | DDL has `NOT NULL DEFAULT 0` on both `experiments` and `promotion_events`. No code change. |
| Finding 10 (P1-D2-C06): narrow ALTER TABLE except | DONE | Catches `aiosqlite.OperationalError` with duplicate-column sanity check; other errors re-raise. |
| Finding 11 (P1-D2-L04): register_auto_trigger lifecycle | DONE-VERIFIED | Process-lifetime singletons; observation holds. |
| Finding 12 (P1-D2-L07): defensive rationale formatting | DONE | `correlation = (trade_src or cf_src or 0.0)` formatted as `{:+.4f}`. |
| Finding 13 (P1-D2-C02): VariantConfig Pydantic | DONE | Added `VariantConfig` with `extra="forbid"`; retyped `ExperimentConfig.variants`. YAML round-trip verified. |
| Finding 14 (P1-D2-C03): learning __init__ analyzers | DONE-VERIFIED | All 8 consumers use direct submodule imports; asymmetry intentional. |
| Finding 15 (P1-D2-M05): record redistribution drift | DONE | Pre/post weight snapshots + per-dim `record_change(source="learning_loop_redistribution")`. |
| Finding 16 (P1-D2-L01): `_convert_datetimes` widen | DONE | `isinstance(val, date)` (matches both `date` and `datetime`); `datetime.isoformat` still produces the richer string. |
| Finding 17 (P1-D2-M04): threshold raise/lower split | DONE | `if/elif/else` with raise precedence per spec option (a). |
| Finding 18 (DEF-107): delete unused raiseRec | DONE | Removed from destructure at the actual path `argus/ui/src/components/learning/LearningInsightsPanel.tsx:388`. |

## Regression Checks

| Check | Result | Notes |
|-------|--------|-------|
| pytest net delta >= 0 against baseline 5,028 passed | PASS | 5,028 → 5,035 (+7). |
| DEF-163 `test_get_todays_pnl_excludes_unrecoverable` remains the only pre-existing failure | PASS | Same 1 failure pre and post; no new regressions. (Note: kickoff prompt mentioned DEF-150 as the expected flake, but actual baseline failure is DEF-163.) |
| No file outside this session's declared Scope was modified | MINOR DEVIATION | `tests/intelligence/test_scoring_fingerprint.py` updated as a downstream consumer of Finding 7's method rename — minimal, mechanical, behaviour-preserving. Documented as judgment call. |
| Every resolved finding back-annotated in audit report with `**RESOLVED FIX-08-intelligence-experiments-learning**` | PASS | All 16 in-doc rows back-annotated (M-02, M-04, M-05, L-01..L-07, C-01..C-06). |
| Every DEF closure recorded in CLAUDE.md | PASS | DEF-107 + DEF-123 strikethrough with FIX-08 attribution. |
| Every new DEF/DEC referenced in commit message bullets | PASS | No new DEFs/DECs opened this session. |
| `read-only-no-fix-needed` findings: verification output recorded OR DEF promoted | PASS | L-04, L-05, C-03 all verified-only with output recorded in the audit doc. |
| `deferred-to-defs` findings: fix applied AND DEF-NNN added to CLAUDE.md | N/A | No findings tagged `deferred-to-defs` in this session. |

## Test Results

- Tests run: 5,036 (5,035 passed + 1 pre-existing DEF-163 failure)
- Tests passed: 5,035
- Tests failed: 1 (pre-existing — `tests/analytics/test_def159_entry_price_known.py::test_get_todays_pnl_excludes_unrecoverable`, DEF-163)
- New tests added: 7 (1 fingerprint pin + 2 fingerprint factory parity + 1 executor shutdown on save exception + 1 redistribution drift cumulative guard + 1 _convert_datetimes date widening + 1 threshold no-recommendation case)
- Vitest: 859 passed → 859 passed (no delta; Finding 18 was a delete with no test dependency)
- Command used: `python -m pytest --ignore=tests/test_main.py -n auto -q` ; `cd argus/ui && npx vitest run`

## Unfinished Work

None. All 18 findings addressed (15 RESOLVED, 3 RESOLVED-VERIFIED).

## Notes for Reviewer

- **Finding 1 is the highest-value fix** — confirm via `tests/intelligence/experiments/test_runner.py::test_compute_fingerprint_with_exit_overrides_matches_factory` that the runner's exit-overrides hash now byte-matches `factory.compute_parameter_fingerprint`. Detection-only is pinned by `test_compute_fingerprint_detection_only_pinned` to the pre-fix hash `ddec1b2a09ee2263` (so existing `experiments.db` rows remain reachable via `get_by_fingerprint`).
- **Finding 15 cumulative-drift test relies on the `LearningLoopConfig` Pydantic max** (0.50) to keep the guard from skipping mid-test. If a future change tightens that ceiling, revisit `test_redistribution_drift_visible_to_cumulative_drift_guard`.
- **Finding 17 changed the public-ish behaviour of `ThresholdAnalyzer.analyze`** — it now emits at most one recommendation per grade (was 0–2). Any operator-facing UI element that assumed pairs (e.g. dual approve/dismiss buttons in `LearningInsightsPanel.tsx`) should be re-checked. Spot check passed: the dual-button conflicting-pair UI block at `LearningInsightsPanel.tsx:387–471` is *guarded* by `lowerProposal?.status === 'PENDING' && raiseProposal?.status === 'PENDING'` — under the new analyzer semantics that condition is false (only one of the two will exist), so the dual-action block self-disables. No breaking UI change.
- **Spec drift on Finding 18 path** — the actual file path is `argus/ui/src/components/learning/LearningInsightsPanel.tsx`, not the spec's `argus/ui/src/features/learning/LearningInsightsPanel.ts` (wrong directory + extension) nor the Finding 18 body's `features/learning/LearningInsightsPanel.tsx` (wrong directory). Documented in CLAUDE.md DEF-107 closure under campaign retrospective P12.
```

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "audit-2026-04-21-phase-3",
  "session": "FIX-08-intelligence-experiments-learning",
  "verdict": "COMPLETE",
  "tests": {
    "before": 5028,
    "after": 5035,
    "new": 7,
    "all_pass": false
  },
  "files_created": [],
  "files_modified": [
    "CLAUDE.md",
    "argus/intelligence/experiments/config.py",
    "argus/intelligence/experiments/promotion.py",
    "argus/intelligence/experiments/runner.py",
    "argus/intelligence/experiments/store.py",
    "argus/intelligence/learning/config_proposal_manager.py",
    "argus/intelligence/learning/learning_service.py",
    "argus/intelligence/learning/models.py",
    "argus/intelligence/learning/threshold_analyzer.py",
    "argus/ui/src/components/learning/LearningInsightsPanel.tsx",
    "docs/audits/audit-2026-04-21/p1-d2-experiments-learning.md",
    "tests/intelligence/experiments/test_runner.py",
    "tests/intelligence/learning/test_config_proposal_manager.py",
    "tests/intelligence/learning/test_models.py",
    "tests/intelligence/learning/test_threshold_analyzer.py",
    "tests/intelligence/test_scoring_fingerprint.py"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [
    {
      "description": "tests/intelligence/test_scoring_fingerprint.py was updated to consume promotion's new _fetch_shadow_positions + _build_result_from_positions API after Finding 7 collapsed _build_result_from_shadow and _count_shadow_trading_days. The test was not in the declared Scope but was a downstream consumer of removed methods; left unchanged it would have broken the suite.",
      "justification": "Behaviour-preserving migration of 3 test call sites to the new API. Alternative would have been keeping a no-op _build_result_from_shadow shim, which the audit identified as the symptom to fix."
    },
    {
      "description": "tests/intelligence/learning/test_threshold_analyzer.py had its test_both_conditions_simultaneous test renamed and its assertion inverted (now asserts ONE 'raise' recommendation, not BOTH). One additional test (test_high_missed_opportunity_recommends_lower) had its data updated to the only data shape that exercises the new 'lower' branch (missed > 0.40 AND correct >= 0.50).",
      "justification": "These tests previously asserted the legacy buggy dual-emission behavior that Finding 17 explicitly fixes. The spec says 'add a test that would fail without the fix' — updating tests that asserted the buggy old behavior is the necessary corollary."
    },
    {
      "description": "tests/intelligence/learning/test_config_proposal_manager.py::test_apply_pending_records_change_history was updated to assert 5 records (1 explicit + 4 redistribution) instead of 1.",
      "justification": "Finding 15's whole point is that redistribution must now emit additional records; the legacy 1-record assertion would have hidden the fix."
    },
    {
      "description": "tests/intelligence/experiments/test_runner.py::test_run_single_backtest_passes_fingerprint patch path updated from argus.backtest.engine.BacktestEngine to argus.intelligence.experiments.runner.BacktestEngine.",
      "justification": "Finding 4 removed the local re-import that made the original module-symbol patch effective. The new patch target matches the established pattern used by all other parallel-path tests in the same file."
    }
  ],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "Finding 13's VariantConfig is purely structural until something instantiates ExperimentConfig from a dict at runtime. Production still consumes experiments.yaml as a raw dict via VariantSpawner. A natural follow-on is to wire ExperimentConfig.from_dict() at startup and remove the spawner's .get()-based access — that change is wider in scope than any single FIX session and was deferred."
  ],
  "doc_impacts": [
    {"document": "docs/audits/audit-2026-04-21/p1-d2-experiments-learning.md", "change_description": "Back-annotated all 16 in-doc findings (M-02/M-04/M-05/L-01..L-07/C-01..C-06)."},
    {"document": "CLAUDE.md", "change_description": "DEF-107 + DEF-123 strikethrough with FIX-08 attribution. Spec path drift on Finding 18 documented in DEF-107 closure."}
  ],
  "dec_entries_needed": [],
  "warnings": [
    "Kickoff prompt's expected baseline failure was DEF-150; actual baseline failure is DEF-163 (test_get_todays_pnl_excludes_unrecoverable). Both are LOW-priority date/timezone hygiene items batched into FIX-13. Net delta verified positive against the actual 5,028 baseline."
  ],
  "implementation_notes": "Finding 1 (the highest-value MEDIUM) implemented via runner-side reshape rather than literal factory delegation, because the runner doesn't have a StrategyConfig instance to pass to factory.compute_parameter_fingerprint. Outcome is byte-identical hashes. Finding 6 (DEF-123) chose RESOLVED-VERIFIED over the spec's numpy.arange migration because the existing round(min + i*step, 6) form is mathematically equivalent to numpy.arange's output and the migration would only add an import dependency. Finding 13 (VariantConfig) is structural / future-proofing only because production never instantiates ExperimentConfig — documented in the audit row. Finding 15 emits 4 additional record_change rows per applied weight proposal (one per non-target weight dim); the new source tag 'learning_loop_redistribution' is distinct from 'learning_loop' so a future drift-guard refinement could weight them differently. Finding 17 changed observable behavior (analyzer now emits at most one rec per grade); UI guard already requires both lower+raise proposals to be PENDING before showing the dual-action block, so the change self-deactivates that block under the new semantics — no separate UI fix needed. Spec scope-header path for Finding 18 was wrong (claimed features/learning/, actual is components/learning/); documented per P12 protocol."
}
```
---END-CLOSE-OUT---
