# FIX-16-config-consistency — Close-Out Report

> Tier 1 self-review produced per `workflow/claude/skills/close-out.md`.
> Paste the fenced block below into the Work Journal on Claude.ai.

```markdown
---BEGIN-CLOSE-OUT---

**Session:** audit-2026-04-21-phase-3 — FIX-16-config-consistency
**Date:** 2026-04-22
**Self-Assessment:** MINOR_DEVIATIONS

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/core/config.py | modified | (1) `OrderManagerConfig` — removed `enable_trailing_stop` + `trailing_stop_atr_multiplier` (DEF-109). (2) `ScannerConfig` class + `load_scanner_config()` deleted (H2-S06). (3) `ApiConfig.validate_password_hash_set()` runtime check + load_config() invocation (H2-H10). (4) `BacktestSummaryConfig` extended with 7 documentary fields incl. `prior_baseline: dict` (H2-S03). (5) `ABCDConfig.pattern_class` field removed (H2-S08). (6) `_STANDALONE_SYSTEM_OVERLAYS` extended with 4 entries: learning_loop, regime_intelligence, vix_regime, historical_query (H2-H13/H15/D06/DEAD06). |
| argus/data/fmp_scanner.py | modified | `min_volume` field removed from `FMPScannerConfig` (H2-S10). |
| argus/intelligence/experiments/spawner.py | modified | `_apply_variant_params` now validates variant param keys against `type(base_config).model_fields` and raises ValueError on unknown keys (H2-S02). Outer loop adds non-dict variant entry guard with ERROR log (H2-S04). Caller's exception block widened to `(ValueError, ValidationError)` and re-classed `warning`→`error` for both. |
| argus/main.py | modified | Removed AMD-10 deprecation-warning block for legacy trailing stop fields (DEF-109). |
| config/counterfactual.yaml | deleted | Dead YAML — values already authoritative in `system_live.yaml`'s `counterfactual:` block (H2-DEAD04). |
| config/historical_query.yaml | modified | Flattened — removed top-level `historical_query:` wrapper; bare fields at top level matching DEC-384 / FIX-02 convention. `cache_dir` kept at `data/databento_cache` (no runtime behavior change). Now authoritative via `_STANDALONE_SYSTEM_OVERLAYS` (H2-D06). |
| config/order_manager.yaml | modified | Legacy `enable_trailing_stop` / `trailing_stop_atr_multiplier` lines removed; pointer comment to exit_management.yaml (DEF-109). |
| config/scanner.yaml | modified | `fmp_scanner.min_volume: 500000` line removed; explanatory comment (H2-S10). |
| config/strategies/{12 of 15}.yaml | modified | `benchmarks.min_sharpe: 0.3` → `min_sharpe_ratio: 0.3` (H2-S01). Files: bull_flag, vwap_bounce, narrow_range_breakout, dip_and_rip, micro_pullback, afternoon_momentum, abcd, hod_break, flat_top_breakout, premarket_high_break, vwap_reclaim, gap_and_go. orb_breakout/orb_scalp/red_to_green were already correct. |
| config/strategies/{7 of 15}.yaml | modified | Stale "Activate post-Sprint 28" TODO comment replaced with current-state guidance pointing at FIX-19's `allowed_regimes` (H2-S09). Files carrying the comment: bull_flag, orb_breakout, red_to_green, afternoon_momentum, orb_scalp, flat_top_breakout, vwap_reclaim. |
| config/system.yaml | modified | (1) Dev bcrypt hash added to `api.password_hash` (mirrors system_live.yaml's "argus" dev password) so the Alpaca-incubator profile boots cleanly under H2-H10 validator. (2) `historical_query:` block removed; pointer comment to standalone YAML. (3) `vix_regime:` block removed; pointer comment to standalone YAML. |
| config/system_live.yaml | modified | (1) `historical_query:` block removed; pointer comment. (2) `vix_regime:` block removed; pointer comment. (No api change — already had real hash.) |
| docs/audits/audit-2026-04-21/p1-h2-config-consistency.md | modified | New "FIX-16 Resolution (2026-04-22)" section enumerating all 19 findings with verdict (RESOLVED / RESOLVED-VERIFIED) and one-line implementation note each. |
| docs/audits/audit-2026-04-21/phase-2-review.csv | modified | All 19 finding rows annotated with `**RESOLVED [-VERIFIED] FIX-16-config-consistency** (...)` in the notes column. |
| tests/core/test_config.py | modified | (1) Removed `ScannerConfig` import + `load_scanner_config` import + `TestScannerConfig` class (H2-S06). (2) Added `TestStrategyBenchmarkMinSharpeRatioWires` (15 parametrized + 1 grep-guard, H2-S01). (3) Added `TestApiPasswordHashLoadTimeCheck` (6 cases, H2-H10). (4) Updated `test_missing_optional_files_use_defaults` + 2 universe-manager tests + test_system.yaml to set `api: enabled: false` (H2-H10 fallout). |
| tests/data/test_historical_query_config.py | modified | Updated `TestHistoricalQueryConfigYaml::test_yaml_loads_into_config` + `test_all_yaml_keys_are_recognized` to read bare-field shape (H2-D06 fallout). |
| tests/fixtures/test_system.yaml | modified | Added `api: enabled: false` to avoid H2-H10 validator. |
| tests/intelligence/experiments/test_spawner.py | modified | +3 regression tests: `test_unknown_param_key_typo_is_rejected_not_silently_dropped` (H2-S02 typo case), `test_non_dict_variant_entry_is_rejected` (H2-S04 shape case), `test_existing_experiments_yaml_has_no_typos_in_variant_params` (live 22-variant fleet sanity check). |
| tests/intelligence/test_counterfactual_store.py | modified | `test_config_yaml_keys_match_pydantic_fields` redirected from deleted `config/counterfactual.yaml` to `config/system_live.yaml` (H2-DEAD04 fallout). |
| tests/strategies/patterns/test_abcd_integration.py | modified | `TestABCDConfigYAML::test_abcd_yaml_parses` + `TestABCDConfigModel::test_default_values` updated to assert via `_resolve_pattern_name(config, None) == "ABCDPattern"` instead of removed `config.pattern_class` field (H2-S08 fallout). |
| tests/strategies/patterns/test_factory.py | modified | `test_abcd_config_uses_pattern_class_field` renamed `test_abcd_config_resolves_via_class_name_inference` and rewritten to assert `not hasattr(config, "pattern_class")` + factory still resolves to `ABCDPattern` (H2-S08 fallout). Updated comment in `test_explicit_pattern_name_overrides_inference`. |
| tests/test_fix01_load_config_merge.py | modified | `_BASE_SYSTEM_YAML` constant gains `"api": {"enabled": False}` to avoid H2-H10 validator across the 9 existing merge-regression tests. |
| tests/unit/strategies/test_atr_emission.py | modified | `TestDeprecatedConfigWarning` class (3 tests) deleted — tested removed AMD-10 warning logic (DEF-109). |
| CLAUDE.md | modified | DEF-109 row strikethrough + RESOLVED annotation in the Deferred Items table. |

### Judgment Calls
- **Wire-vs-delete strategy for the 6 dead YAMLs.** Audit offered both options per finding. Chose **wire** for `learning_loop.yaml` / `regime.yaml` / `vix_regime.yaml` / `historical_query.yaml` (via `_STANDALONE_SYSTEM_OVERLAYS`) because they carry operator-tunable knobs and the DEC-384 pattern is the established convention. Chose **delete** for `counterfactual.yaml` because its values are pure duplicates of `system_live.yaml`'s `counterfactual:` block — no operator knob, nothing to preserve. **`overflow.yaml`** is a no-op for FIX-16: already wired by FIX-02 (RESOLVED-VERIFIED).
- **H2-H10 fail-loud as a runtime check, not a Pydantic `model_validator`.** A `model_validator` would fire on every `ApiConfig()` no-arg construction (which test fixtures use freely). The runtime path-only check via `validate_password_hash_set()` called from `load_config()` keeps `ApiConfig()` / `SystemConfig()` usable in tests while still rejecting empty-hash production boots. Required adding a dev bcrypt hash to `system.yaml` (mirroring `system_live.yaml`) and `api: enabled: false` to four test fixtures that bypass `load_config()`.
- **H2-S02 validation against `model_fields`, not against `get_default_params()`.** Audit prompt suggested checking against PatternParam names. That set is strictly narrower than the strategy config's full Pydantic field set — using only it would falsely reject legitimate variant keys like `target_ratio` (which is a config field but not a PatternParam). Validating against `model_fields` catches typos while admitting all real config knobs.
- **H2-S03 extension over removal.** Audit offered both. Chose extension because the 7 fields are operator-visible documentation in 15 strategy YAMLs; removing them across the fleet would be more churn and lose context. `prior_baseline` is `dict[str, Any] | None` rather than a sub-Pydantic model because actual YAML values are free-form (`{source, oos_sharpe, wfe_pnl, total_trades}`).
- **H2-S08 pattern_class removal (over add-to-all).** The factory's class-name inference (`*Config` → `*Pattern`) already covers all 10 patterns. Removing the one outlier field is cleaner than mirroring a no-op field across 9 other configs. Existing tests that asserted `config.pattern_class == "ABCDPattern"` rewritten to assert via `_resolve_pattern_name(config, None)`.
- **H2-D06 cache_dir kept at `data/databento_cache`.** Operator activation of consolidated cache is still pending per CLAUDE.md. Wiring `historical_query.yaml` as the standalone overlay enables the operator-expected workflow ("edit historical_query.yaml to flip cache_dir"), but flipping the value itself is operator-owned and not in this session's scope.
- **CLAUDE.md edit confined to the DEF-109 row.** The audit prompt allowed CLAUDE.md edits "only if a DEF closes" — DEF-109 closed, so the row gets the strikethrough/resolved pattern. The campaign-level "Active sprint" line is owned by the running register and was not touched.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| **Finding 1 — DEF-109** (V1 trailing stop dead code) | DONE | Fields removed from `OrderManagerConfig`; AMD-10 warning removed from `main.py`; legacy fields removed from `order_manager.yaml`; `TestDeprecatedConfigWarning` deleted. |
| **Finding 2 — H2-S06** (ScannerConfig dead Pydantic shim) | DONE | Class + loader deleted; `TestScannerConfig` removed; production code path unchanged. |
| **Finding 3 — H2-H10** (empty password_hash silent JWT break) | DONE | Runtime `validate_password_hash_set()` called by `load_config()`; +6 regression tests; dev hash added to system.yaml. |
| **Finding 4 — H2-H11** (StrategyMode str vs enum) | RESOLVED-VERIFIED | Already resolved by FIX-19 — `StrategyConfig.mode: StrategyMode = StrategyMode.LIVE`. Verified Pydantic rejects misspellings. |
| **Finding 5 — H2-S02 [CRITICAL]** (variant params silent drop) | DONE | `_apply_variant_params` validates `variant_params.keys() ⊆ type(base_config).model_fields`; raises ValueError; +3 regression tests including 22-variant fleet sanity check (zero typos found). |
| **Finding 6 — H2-S04** (variant list shape) | DONE | Non-dict entries rejected with ERROR log; co-fixed with H2-S02; +1 regression test. |
| **Finding 7 — H2-H13** (learning_loop.yaml not wired) | DONE | Registered as `("learning_loop", "learning_loop.yaml")` in `_STANDALONE_SYSTEM_OVERLAYS`. |
| **Finding 8 — H2-DEAD01** (learning_loop.yaml dead) | DONE | Co-fixed with H2-H13. |
| **Finding 9 — H2-H15** (regime.yaml not wired) | DONE | Registered as `("regime_intelligence", "regime.yaml")`. |
| **Finding 10 — H2-DEAD02** (regime.yaml dead) | DONE | Co-fixed with H2-H15. |
| **Finding 11 — H2-DEAD04** (counterfactual.yaml dead) | DONE | File deleted; test redirected to `system_live.yaml`. |
| **Finding 12 — H2-DEAD03** (overflow.yaml dead) | RESOLVED-VERIFIED | Already wired by FIX-02. |
| **Finding 13 — H2-S10** (fmp_scanner.min_volume always ignored) | DONE | Field removed from dataclass + scanner.yaml. |
| **Finding 14 — H2-S01 [CRITICAL]** (12 strategy YAMLs spell `min_sharpe`) | DONE | Renamed to `min_sharpe_ratio` in 12 YAMLs; +parametrized regression test (15 cases + grep-guard). |
| **Finding 15 — H2-S09** (stale "Activate post-Sprint 28" TODO) | DONE | Comment replaced across 7 YAMLs with current-state guidance. |
| **Finding 16 — H2-S08** (pattern_class only on ABCDConfig) | DONE | Field removed from ABCDConfig; class-name inference uniform across 10 patterns. |
| **Finding 17 — H2-S03** (7 silent-drop documentary fields) | DONE | `BacktestSummaryConfig` extended with all 7 (Optional). `prior_baseline: dict[str, Any] \| None` matches actual YAML shape. |
| **Finding 18 — H2-D06** (cache_dir divergence) | DONE | `historical_query.yaml` flattened + registered; system YAMLs blocks removed; `cache_dir` value unchanged (operator-owned activation). |
| **Finding 19 — H2-DEAD06** (vix_regime.yaml dead) | DONE | Registered as `("vix_regime", "vix_regime.yaml")`; `vix_regime: enabled: true` blocks removed from system YAMLs. |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| pytest net delta >= 0 against baseline 4,965 passed | PASS (+19) | 4,984 passed — baseline + 19 new regression tests across 4 files. |
| DEF-150 flake remains the only pre-existing failure (no new regressions) | PASS | Final run produced 0 failures (DEF-150 did not flake this run; 2 DEF-163 date-decay tests passed too — UTC time outside the 20:00–00:00 ET danger window). |
| No file outside this session's declared Scope was modified | PASS | `git diff --name-only` returns exactly the 37 expected files (including 1 deletion). All within the declared scope: `argus/core/config.py`, `argus/intelligence/experiments/spawner.py`, `argus/data/fmp_scanner.py`, `argus/main.py`, `config/**`, audit/CSV docs, regression test files, CLAUDE.md DEF table only. |
| Every resolved finding back-annotated in audit report with `**RESOLVED FIX-16-config-consistency**` | PASS | All 19 finding rows in `phase-2-review.csv` annotated; new "FIX-16 Resolution" section in `p1-h2-config-consistency.md` enumerates each finding's verdict. |
| Every DEF closure recorded in CLAUDE.md | PASS | DEF-109 row strikethrough + RESOLVED annotation. |
| Every new DEF/DEC referenced in commit message bullets | PASS | No new DEFs or DECs opened. The DEC-384 registry extension (4 new entries) follows the FIX-02 precedent and does not require a new DEC. |
| `read-only-no-fix-needed` findings: verification output recorded OR DEF promoted | PASS | Two RESOLVED-VERIFIED: H2-H11 (FIX-19 already fixed) + H2-DEAD03 (FIX-02 already wired). Verification noted in p1-h2 Resolution section + commit message. |
| `deferred-to-defs` findings: fix applied AND DEF-NNN added to CLAUDE.md | PASS (N/A) | All 19 findings resolved this session; no deferral. |

### Test Results
- Tests run: 4,984 (collected, full suite via `--ignore=tests/test_main.py -n auto`)
- Tests passed: 4,984
- Tests failed: 0
- New tests added: 19 (3 in `test_spawner.py`, 16 in `test_config.py`: 15 parametrized H2-S01 + 1 grep-guard, plus 6 H2-H10 cases — minus 3 deleted `TestDeprecatedConfigWarning` tests = net +19)
- Command used: `python -m pytest --ignore=tests/test_main.py -n auto --tb=no -q`

### Unfinished Work
None. All 19 findings resolved.

### Notes for Reviewer

**1. Two CRITICAL findings + the 22-variant fleet sanity check.** H2-S02's
spawner validation closes a silent class of bugs (variant typos disappear
into `model_dump()`-then-`model_validate()`); H2-S01's rename restores
benchmark gating that was at the Pydantic default 0.0 across 12 of 15
strategies. The H2-S02 regression test deliberately includes a parametrized
loader against the live `config/experiments.yaml` confirming zero typos
exist in the current 22-variant shadow fleet at this commit. If a future
operator typo creeps in, that test fails loudly at CI time before the
broken variant ships.

**2. H2-H10 deliberate test fixture changes.** The runtime fail-loud check
forced four test sites to set `api: enabled: false` (or to add a dummy
hash). These are not behavior changes — the runtime guard is what matters.
The dev bcrypt hash added to `system.yaml` matches `system_live.yaml`'s
"argus" password, which has been the documented dev default since Sprint 14.

**3. DEC-384 registry extension scope.** FIX-16 added 4 new entries to
`_STANDALONE_SYSTEM_OVERLAYS`, mirroring FIX-02's single-entry extension.
The merge logic in `load_config()` and the `deep_update` helper are
unchanged. The `_STANDALONE_SYSTEM_OVERLAYS` comment block was extended to
note the FIX-16 extension. The `historical_query.yaml` file was flattened
to bare-field shape to match the convention; its `cache_dir` value was
deliberately kept at `data/databento_cache` so this session does NOT
activate the consolidated Parquet cache (operator decision per CLAUDE.md /
Sprint 31.85 follow-up).

**4. Test fallout from `BacktestSummaryConfig` extension.** Initial run had
14 failures because `prior_baseline` was modelled as `str | None` but the
actual YAML shape is a nested dict. Fixed by re-typing as `dict[str, Any] |
None`. All other 6 added Optional fields validated cleanly first try.

**5. Test-pollution detective work.** Initial full-suite run reported "105
failed" but the output file was truncated by `tail -10` in a shell pipeline
— actual failures were exactly the 5 visible ones (3 ABCD pattern_class +
2 historical_query.yaml shape). All 5 fixed in the same scope as the
findings that introduced them.

---END-CLOSE-OUT---
```

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "audit-2026-04-21-phase-3",
  "session": "FIX-16-config-consistency",
  "verdict": "COMPLETE",
  "tests": {
    "before": 4965,
    "after": 4984,
    "new": 19,
    "all_pass": true
  },
  "files_created": [],
  "files_modified": [
    "CLAUDE.md",
    "argus/core/config.py",
    "argus/data/fmp_scanner.py",
    "argus/intelligence/experiments/spawner.py",
    "argus/main.py",
    "config/historical_query.yaml",
    "config/order_manager.yaml",
    "config/scanner.yaml",
    "config/strategies/abcd.yaml",
    "config/strategies/afternoon_momentum.yaml",
    "config/strategies/bull_flag.yaml",
    "config/strategies/dip_and_rip.yaml",
    "config/strategies/flat_top_breakout.yaml",
    "config/strategies/gap_and_go.yaml",
    "config/strategies/hod_break.yaml",
    "config/strategies/micro_pullback.yaml",
    "config/strategies/narrow_range_breakout.yaml",
    "config/strategies/orb_breakout.yaml",
    "config/strategies/orb_scalp.yaml",
    "config/strategies/premarket_high_break.yaml",
    "config/strategies/red_to_green.yaml",
    "config/strategies/vwap_bounce.yaml",
    "config/strategies/vwap_reclaim.yaml",
    "config/system.yaml",
    "config/system_live.yaml",
    "docs/audits/audit-2026-04-21/p1-h2-config-consistency.md",
    "docs/audits/audit-2026-04-21/phase-2-review.csv",
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
  "files_deleted": ["config/counterfactual.yaml"],
  "files_should_not_have_modified": [],
  "scope_additions": [
    {
      "description": "Extension of `BacktestSummaryConfig` with `prior_baseline: dict[str, Any] | None` (audit only listed it as a `str | None` candidate by implication).",
      "justification": "Initial `str | None` typing failed YAML load — actual values are nested dicts."
    },
    {
      "description": "Test fixture / inline YAML edits in `tests/fixtures/test_system.yaml` + `tests/test_fix01_load_config_merge.py::_BASE_SYSTEM_YAML` + `tests/core/test_config.py` (3 inline writes) to add `api: enabled: false`.",
      "justification": "H2-H10 runtime validator requires a non-empty hash when api.enabled is true. Tests don't exercise JWT login; setting `enabled: false` keeps them runnable without seeding dummy hashes everywhere."
    }
  ],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "operator activation of consolidated Parquet cache: `historical_query.yaml` is now wired and ready, but `cache_dir` was kept at `data/databento_cache` deliberately. Operator can flip to `data/databento_cache_consolidated` post-Sprint-31.85 by editing the standalone YAML.",
    "tests/test_sprint_27_65_s4.py sets `config.enable_trailing_stop = False` on MagicMocks at 3 sites — harmless dead reads on a MagicMock, left untouched for minimal-scope discipline.",
    "argus/models/strategy.py:57 has `trailing_stop_atr_multiplier` on a separate `StrategyRules` model (not OrderManagerConfig) — out of scope for DEF-109."
  ],
  "doc_impacts": [
    {"document": "docs/audits/audit-2026-04-21/p1-h2-config-consistency.md", "change_description": "Added FIX-16 Resolution section enumerating all 19 findings with verdicts."},
    {"document": "docs/audits/audit-2026-04-21/phase-2-review.csv", "change_description": "Annotated all 19 finding rows with **RESOLVED [-VERIFIED] FIX-16-config-consistency** in notes column."},
    {"document": "CLAUDE.md", "change_description": "DEF-109 row strikethrough + RESOLVED annotation in Deferred Items table."}
  ],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Two CRITICAL findings landed first (H2-S02 + H2-S01), then code-grouped fixes by file. H2-H10 fail-loud was implemented as a runtime check (not a Pydantic model_validator) to keep test fixtures usable; required adding a dev bcrypt hash to system.yaml + `api: enabled: false` to four test fixture sites. DEC-384 _STANDALONE_SYSTEM_OVERLAYS registry extended with 4 new entries (learning_loop, regime_intelligence, vix_regime, historical_query), following FIX-02 precedent. config/counterfactual.yaml deleted (duplicate of system_live.yaml). H2-S03 BacktestSummaryConfig extension required prior_baseline as dict not str. Two findings RESOLVED-VERIFIED (already done by prior FIX sessions): H2-H11 (FIX-19 StrategyMode enum) + H2-DEAD03 (FIX-02 overflow.yaml wiring). Self-assessment is MINOR_DEVIATIONS (not CLEAN) because of the prior_baseline typing correction mid-session and the dev-hash injection into system.yaml — both judgment calls necessary to keep the runtime guard honest while avoiding test-suite fallout."
}
```
