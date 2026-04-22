# FIX-16-config-consistency — Tier 2 Review

> Independent review per `workflow/claude/skills/review.md`. Read-only; no source files were modified. Findings below.

```markdown
---BEGIN-REVIEW---

**Reviewing:** audit-2026-04-21-phase-3 — FIX-16-config-consistency (commit 563ae13)
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-04-22
**Verdict:** CLEAR

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | 36 files modified + 1 deleted — every path inside the declared scope (`argus/core/config.py`, `argus/intelligence/experiments/spawner.py`, `argus/data/fmp_scanner.py`, `argus/main.py`, `config/**`, audit docs, touched test modules, DEF-109 row only in CLAUDE.md). No workflow/ or .claude/agents/ touches. |
| Close-Out Accuracy | PASS | Change manifest mirrors the diff exactly. Judgment calls (wire-vs-delete, runtime check not model_validator, model_fields not PatternParam, prior_baseline typing) are all traceable to the diff. Self-assessment MINOR_DEVIATIONS is honest — the scope additions (api.enabled=false in 4 test fixture sites + prior_baseline re-typing mid-session) were forced by the H2-H10 and H2-S03 choices and are documented. |
| Test Health | PASS | Full suite reran locally: `python -m pytest --ignore=tests/test_main.py -n auto --tb=no -q` → 4,984 passed, 0 failed, 152.94s. Baseline 4,965 + net 19 matches. New tests are substantive (the H2-S02 typo test loads a real typo into the spawner and asserts a real ERROR log naming the bad key; the 22-variant fleet test loads live experiments.yaml and would fail on any future typo). |
| Regression Checklist | PASS | All 8 campaign-level checks pass — see table in close-out §Regression Checks. Verified independently: net delta +19, zero failures, scope-clean, 19/19 CSV annotations, DEF-109 struck through in CLAUDE.md, zero new DEF/DEC opened, H2-H11 + H2-DEAD03 RESOLVED-VERIFIED with justification, no deferred-to-DEF findings. |
| Architectural Compliance | PASS | DEC-384 extension follows FIX-02 precedent exactly (registry-based, logic untouched). Runtime `validate_password_hash_set()` is the correct posture for a fail-loud check that must not trip on default `ApiConfig()` construction. `_resolve_pattern_name` fallback chain still holds up (ABCDConfig no longer carries `pattern_class`; class-name inference returns `ABCDPattern` as verified by runtime probe). `extra="forbid"` is NOT added to strategy configs — H2-S02 guarded at the spawner layer, consistent with existing PatternModule discipline. |
| Escalation Criteria | NONE_TRIGGERED | No CRITICAL finding remains incomplete; pytest delta positive (+19); no scope boundary violation; no new regressions; no Rule-4 sensitive path touched; audit back-annotations present on all 19 rows. |

### Detailed Verification of Scrutiny Items

1. **H2-S02 (CRITICAL) — VariantSpawner key validation.** `_apply_variant_params` at `argus/intelligence/experiments/spawner.py:334-367` raises `ValueError` when `variant_params` keys are not in `type(base_config).model_fields`. The test `test_unknown_param_key_typo_is_rejected_not_silently_dropped` uses the real misspelling `flag_retrace_pct` (vs correct `flag_max_retrace_pct`) inside a real `BullFlagConfig`, confirms the bad variant is skipped, AND confirms a sibling valid variant still spawns — this actually exercises the validation path, not a tautology. The fleet-sanity test `test_existing_experiments_yaml_has_no_typos_in_variant_params` reads `config/experiments.yaml` at runtime against the 10 pattern config classes and would fail loudly on any typo introduced there. Caller's exception block widened to `(ValueError, ValidationError)` and log level escalated `warning→error`. PASS.

2. **H2-S01 (CRITICAL) — min_sharpe rename.** `grep -rn "min_sharpe" config/strategies/` → all 15 strategies now spell `min_sharpe_ratio`. Confirmed via secondary check: `grep -rn "^\s*min_sharpe:\s" config/` → zero matches. The 12 YAMLs listed in the close-out (bull_flag, vwap_bounce, narrow_range_breakout, dip_and_rip, micro_pullback, afternoon_momentum, abcd, hod_break, flat_top_breakout, premarket_high_break, vwap_reclaim, gap_and_go) match the 12 modified in the diff; orb_breakout / orb_scalp / red_to_green were already correct (verified in diff — those YAMLs have no `benchmarks:` block change related to min_sharpe). The parametrized regression test covers all 15 YAMLs with skip-when-absent, and the grep-guard test fails loudly on any future regression. PASS.

3. **H2-H10 — runtime password_hash check.** `ApiConfig.validate_password_hash_set()` is an instance method (not a Pydantic `model_validator`) and is invoked exactly once from `load_config()` at `argus/core/config.py:1525`. `ApiConfig()` with no args still constructs cleanly (confirmed by the sixth regression test `test_ApiConfig_can_still_be_constructed_with_defaults`). Dev hash in `config/system.yaml` is byte-identical to `config/system_live.yaml`'s hash (`$2b$12$Qs2VsacIbZZhDwtA50vQ8eqnJtihmK8AOisBqpwPRPxXMH2MiCsdC`). All 6 regression cases present: raises-on-enabled-empty, passes-on-enabled-with-hash, passes-on-disabled-empty, load_config-rejects, load_config-accepts-disabled, bare-ApiConfig-constructs. PASS.

4. **DEC-384 registry extension.** Read `argus/core/config.py:1413-1428`: original 2 entries (quality_engine, overflow) retained; 4 new entries appended (learning_loop, regime_intelligence, vix_regime, historical_query). The merge loop, `deep_update` helper, and standalone-overlay-non-dict WARNING logic (introduced by FIX-02 stage-1 pickup) are unchanged. Runtime probe via live `load_config(Path("config"))`: `system.learning_loop.report_retention_days == 90`, `system.regime_intelligence.breadth.ma_period == 20`, `system.vix_regime.enabled == True`, `system.historical_query.cache_dir == "data/databento_cache"`. All four overlay values land as expected. PASS.

5. **counterfactual.yaml deletion.** `ls config/counterfactual.yaml` → "No such file or directory". No Python code or test in the repo references `Path("config/counterfactual.yaml")` (only historical sprint docs and the audit report mention it by name). The redirected test `test_config_yaml_keys_match_pydantic_fields` now reads `config/system_live.yaml`, asserts `raw["counterfactual"].keys()` matches `CounterfactualConfig.model_fields.keys()` — still semantically equivalent, just sourced from the living YAML. PASS.

6. **H2-S08 pattern_class removal.** `ABCDConfig` at `argus/core/config.py:1262-1285` no longer declares `pattern_class`. The factory's `_resolve_pattern_name` (`argus/strategies/patterns/factory.py:267-292`) still keeps `hasattr(config, "pattern_class")` as step 2 of its resolution chain — now inert for ABCDConfig (which falls through to step 3, class-name inference). Runtime probe: `hasattr(ABCDConfig(strategy_id='abcd', name='abcd'), 'pattern_class')` returns `False`; `_resolve_pattern_name(c, None)` returns `"ABCDPattern"`. Updated tests in `tests/strategies/patterns/test_abcd_integration.py` and `test_factory.py` now assert the new posture (`not hasattr(config, "pattern_class")` + factory still resolves to `ABCDPattern`). PASS.

7. **DEF-109 cleanup completeness.** (a) `enable_trailing_stop` + `trailing_stop_atr_multiplier` absent from `OrderManagerConfig` (verified — only in a comment block). (b) AMD-10 warning block removed from `argus/main.py:927-931` (now a comment explaining the removal). (c) `config/order_manager.yaml` legacy fields removed, replaced by a pointer comment. (d) `TestDeprecatedConfigWarning` class (3 tests) deleted from `tests/unit/strategies/test_atr_emission.py`. (e) CLAUDE.md DEF-109 row struck through with full RESOLVED annotation at line 334. A surviving `trailing_stop_atr_multiplier` field in `argus/models/strategy.py:57` is on a separate `StrategyRules` model (not `OrderManagerConfig`) and was explicitly called out in the close-out as out-of-scope — that judgment is correct: that field feeds a different code path. PASS.

8. **CLAUDE.md scope discipline.** `git diff` on CLAUDE.md shows exactly one changed row — the DEF-109 row on line 334 converted to strikethrough + RESOLVED. No other lines modified (including the "Active sprint" header line, which is owned by the running register). PASS.

### Findings

**INFO-1 (doc-drift, LOW).** The `load_config()` docstring at `argus/core/config.py:1443-1449` still says _"Files listed in `_STANDALONE_SYSTEM_OVERLAYS` — currently `quality_engine.yaml` and `overflow.yaml` — are deep-merged..."_ This was accurate pre-FIX-16 but is now out-of-date: the registry has 6 entries post-FIX-16. The registry tuple itself at `:1413-1428` has an updated comment block enumerating the new entries, so the source of truth is correct — only the function docstring is stale. No functional impact; trivially fixed by adding the 4 new filenames or genericizing to "Files listed in `_STANDALONE_SYSTEM_OVERLAYS`" without enumeration. Not a blocker and not worth opening a DEF for — fold into the next config-module touch. **Severity: INFO.**

No other findings. CRITICAL items H2-S01 + H2-S02 both landed with meaningful regression guards that exercise real code paths. H2-H10's choice to run the check at `load_config()` (not `model_validator`) is the correct call and is defended by a test that explicitly confirms `ApiConfig()` still constructs at defaults. H2-DEAD04's delete-over-wire call is well-justified (pure duplicate values, no operator knob). The scope additions (4 test fixtures gaining `api.enabled: false`) are necessary consequences of the runtime validator and are documented.

### Recommendation

**Proceed to next session (CLEAR).**

The two CRITICAL findings closed cleanly. All 19 findings verified (17 fixed this session + 2 RESOLVED-VERIFIED with justified deferral to prior FIX sessions). Audit documents + CSV fully back-annotated. Test suite net-positive (+19, 0 failures). Scope discipline held across 36 files + 1 deletion. The DEC-384 registry pattern — two sessions into its life (FIX-02 → FIX-16) — is now carrying 6 subsystems without modification to `load_config()` logic, which is exactly what DEC-384 was designed for; that's the right architectural signal.

Single INFO-severity doc-drift noted (load_config docstring enumeration is stale) — fold into next config-module touch; no action required now.

---END-REVIEW---
```

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "audit-2026-04-21-phase-3",
  "session": "FIX-16-config-consistency",
  "verdict": "CLEAR",
  "findings": [
    {
      "description": "load_config() docstring at argus/core/config.py:1443-1449 still enumerates only 'quality_engine.yaml and overflow.yaml' as the registered standalone overlays. Post-FIX-16 the registry has 6 entries; the tuple's inline comment block is current but the function docstring is stale. No functional impact.",
      "severity": "INFO",
      "category": "NAMING_CONVENTION",
      "file": "argus/core/config.py",
      "recommendation": "Next time the config module is touched, either enumerate all 6 registered overlays or genericize the docstring to 'Files listed in _STANDALONE_SYSTEM_OVERLAYS' without naming specific files."
    }
  ],
  "spec_conformance": {
    "status": "CONFORMANT",
    "notes": "All 19 findings resolved (17 fixed this session + 2 RESOLVED-VERIFIED with verification evidence in audit resolution section). CRITICAL findings H2-S01 + H2-S02 closed with regression tests that exercise real validation paths (typo test loads live experiments.yaml; min_sharpe_ratio test loads every strategy YAML). Judgment calls (wire vs delete for 6 dead YAMLs; runtime check vs model_validator for H2-H10; model_fields vs PatternParam for H2-S02; prior_baseline dict typing for H2-S03) all traceable and defensible. Scope additions (4 test fixture sites gaining api.enabled:false; prior_baseline re-typing mid-session) are necessary consequences of the chosen approach and are documented in the close-out.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "CLAUDE.md",
    "argus/core/config.py",
    "argus/data/fmp_scanner.py",
    "argus/intelligence/experiments/spawner.py",
    "argus/main.py",
    "argus/strategies/patterns/factory.py",
    "config/counterfactual.yaml (deleted)",
    "config/historical_query.yaml",
    "config/order_manager.yaml",
    "config/scanner.yaml",
    "config/strategies/*.yaml (15 files)",
    "config/system.yaml",
    "config/system_live.yaml",
    "docs/audits/audit-2026-04-21/p1-h2-config-consistency.md",
    "docs/audits/audit-2026-04-21/phase-2-review.csv",
    "docs/sprints/sprint-31.9/FIX-16-closeout.md",
    "tests/core/test_config.py",
    "tests/data/test_historical_query_config.py",
    "tests/fixtures/test_system.yaml",
    "tests/intelligence/experiments/test_spawner.py",
    "tests/intelligence/test_counterfactual_store.py",
    "tests/strategies/patterns/test_abcd_integration.py",
    "tests/strategies/patterns/test_factory.py",
    "tests/test_fix01_load_config_merge.py",
    "tests/unit/strategies/test_atr_emission.py"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 4984,
    "new_tests_adequate": true,
    "test_quality_notes": "19 net new tests. H2-S02 typo test exercises real validation path (BullFlag typo + sibling valid variant confirms bad-skipped + good-spawned behavior with the actual ERROR log asserted). Fleet-sanity test parses live config/experiments.yaml against 10 pattern config classes and would fail on any future typo. H2-S01 parametrized test covers all 15 YAMLs + grep-guard regression. H2-H10 covers all 6 logically distinct cases (raises on enabled+empty; passes on enabled+hash; passes on disabled+empty; load_config rejects; load_config accepts disabled; bare ApiConfig() constructs). H2-S04 non-dict entry test asserts correct skip + real ERROR log. No tautological tests."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "pytest net delta >= 0 against baseline 4,965", "passed": true, "notes": "Verified locally: 4,984 passed, 0 failed (+19)."},
      {"check": "DEF-150 flake remains the only pre-existing failure (no new regressions)", "passed": true, "notes": "Final run produced 0 failures. DEF-150 did not flake this run; DEF-163 date-decay tests passed (UTC clock outside 20:00-00:00 ET danger window)."},
      {"check": "No file outside declared scope was modified", "passed": true, "notes": "36 files modified + 1 deleted, all inside the declared scope. No workflow/ or .claude/agents/ touches."},
      {"check": "Every resolved finding back-annotated in audit report", "passed": true, "notes": "19/19 finding rows in phase-2-review.csv carry '**RESOLVED [-VERIFIED] FIX-16-config-consistency**'. New 'FIX-16 Resolution (2026-04-22)' section in p1-h2-config-consistency.md enumerates each with one-line verdict + implementation note."},
      {"check": "Every DEF closure recorded in CLAUDE.md", "passed": true, "notes": "DEF-109 row at CLAUDE.md:334 strikethrough + full RESOLVED annotation citing audit 2026-04-21 FIX-16-config-consistency."},
      {"check": "Every new DEF/DEC referenced in commit message", "passed": true, "notes": "None opened. DEC-384 registry extension follows FIX-02 precedent (no new DEC needed per DEC-384's own extensibility clause)."},
      {"check": "read-only-no-fix-needed findings: verification recorded OR DEF promoted", "passed": true, "notes": "H2-H11 + H2-DEAD03 marked RESOLVED-VERIFIED with explicit justification (H2-H11 → FIX-19 StrategyMode StrEnum; H2-DEAD03 → FIX-02 overflow.yaml wiring). Verification evidence cited in p1-h2 resolution section."},
      {"check": "deferred-to-defs findings: fix applied AND DEF added to CLAUDE.md", "passed": true, "notes": "N/A — all 19 findings resolved this session; no deferral."}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Proceed to next session. No blockers.",
    "Optional: sync the load_config() docstring enumeration with the expanded _STANDALONE_SYSTEM_OVERLAYS registry at the next config-module touch (INFO-1, not required now)."
  ]
}
```
