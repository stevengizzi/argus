# FIX-01-catalyst-db-quality-pipeline — Tier 2 Review

> Tier 2 review produced per `workflow/claude/skills/review.md` by the
> `reviewer` subagent. Read-only — no source files modified. Paste the
> fenced block below into the Work Journal on Claude.ai.

```markdown
---BEGIN-REVIEW---

**Session:** audit-2026-04-21-phase-3 — FIX-01-catalyst-db-quality-pipeline
**Commit:** `59bb100` on `main`
**Reviewer:** Tier 2 automated review (read-only)
**Date:** 2026-04-21
**Verdict:** CLEAR

### Summary

FIX-01 lands cleanly. The catalyst DB path is corrected, the quality pipeline now has a structural fix for the `quality_engine.yaml` drift via Option B (DEC-384 `_STANDALONE_SYSTEM_OVERLAYS`), the scoring-context fingerprint infrastructure is wired end-to-end, and the historical_match stub is hardened. All 11 new regression tests pass; the two adjusted `test_quality_engine` assertions reflect the new stub contract correctly. The A→B pivot is documented in the closeout, codified in DEC-384, and does not introduce a new class of config drift — keys are preserved by `deep_update()` in both directions, and validation still flows through Pydantic `ArgusConfig(**raw)`. The pivot is architecturally sound and narrower-blast-radius than Option A would have been (no config YAML churn).

### Scope & File Audit

Commit touched 18 files (857 insertions, 36 deletions), all within declared FIX-01 scope:

- Source: `argus/core/config.py`, `argus/main.py`, `argus/intelligence/{scoring_fingerprint.py, counterfactual.py, counterfactual_store.py, startup.py, quality_engine.py, experiments/promotion.py}`.
- Tests: `tests/intelligence/{test_scoring_fingerprint.py, test_quality_engine.py}`, `tests/test_fix01_catalyst_db_path.py`, `tests/test_fix01_load_config_merge.py`.
- Docs: `CLAUDE.md`, `docs/{decision-log.md, dec-index.md}`, `docs/audits/audit-2026-04-21/{phase-2-review.csv, p1-d1-catalyst-quality.md, p1-h2-config-consistency.md}`.

No `config/*.yaml` files modified (`git diff HEAD~1 HEAD -- config/` empty). No execution/broker code touched. No `workflow/` submodule pointer touched. Sibling FIX-00/15/17/20 closeout/review reports correctly remain untracked and were NOT staged into this commit.

### Regression Checklist Results

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | pytest net delta ≥ +8 vs baseline 4,933 | PASS | Closeout reports 4,947/0. My re-run at 20:15 ET reports 4,944/3 — the 3 failures are two pre-existing DEF-163 time-of-day bugs (20:00–00:00 ET window, CLAUDE.md-documented) + one xdist flake on `test_all_ulids_mapped_bidirectionally` that passes in isolation. Net delta still +11 against baseline. |
| 2 | Only DEF-150 flake or no pre-existing failures | PASS (with annotation) | Closeout run hit neither DEF-150 nor DEF-163 boundaries. My 20:15 ET re-run surfaced DEF-163 (a) + (b) per their documented time-boundary root cause. DEF-150 did not surface (not in minute 0/1). The `test_ibkr_broker` xdist flake is not FIX-01-attributable (FIX-01 does not touch execution code). |
| 3 | No file outside scope modified | PASS | All 18 files in declared scope. |
| 4 | Audit report back-annotations applied | PASS | phase-2-review.csv has 9 rows carrying `**RESOLVED FIX-01-catalyst-db-quality-pipeline**` (P1-D1-C01/C02/L01, DEF-082, DEF-142, H2-D01/D02/D03/DEAD05). `p1-d1-catalyst-quality.md` and `p1-h2-config-consistency.md` both carry `## FIX-01 Resolution` footers covering C1/C2/L1 and D-01/D-02/D-03/DEAD05 respectively. Footer style matches the sibling FIX-17 pattern and is cleaner than per-row edits. |
| 5 | DEF-082 + DEF-142 struck through in CLAUDE.md | PASS | Both rows flipped to `~~DEF-0XX~~ \| ~~…~~ \| — \| **RESOLVED** (audit 2026-04-21 FIX-01-catalyst-db-quality-pipeline)` per doc-sync convention. |
| 6 | DEC-384 added with full fields + dec-index count bump | PASS | DEC-384 present in `decision-log.md` with Context/Decision/Alternatives/Rationale/Impact/Cross-References/Status. `dec-index.md` header bumped 383 → 384. Footer updated: `Next DEC: 385`. Single-line entry present under Sprint 31.75 block of the index. |
| 7 | `_STANDALONE_SYSTEM_OVERLAYS` + `load_config` deep-merge + INFO log | PASS | Module-scope tuple `(("quality_engine", "quality_engine.yaml"),)` at `argus/core/config.py:1339`. `load_config()` extension at lines 1399–1421 reuses `deep_update()`, validates overlay is a dict before merging (silent skip otherwise — consistent with `load_yaml_file` empty-file posture), logs INFO enumerating merged sections. |
| 8 | Scoring-context fingerprint end-to-end | PASS | New `argus/intelligence/scoring_fingerprint.py` (SHA-256 canonical JSON, first 16 hex). `CounterfactualStore.scoring_fingerprint` column added via idempotent `pragma_table_info` check + conditional `ALTER TABLE ... ADD COLUMN`. `CounterfactualTracker.__init__` accepts `quality_config: QualityEngineConfig \| None = None`, emits INFO log with the fingerprint at construction, and recomputes per-call in `track()`. `startup.py` wires with `isinstance(raw_qe, QualityEngineConfig)` narrowing — MagicMock configs cleanly no-op. `PromotionEvaluator.evaluate_all_variants` + `_evaluate_for_promotion` + `_build_result_from_shadow` + `_count_shadow_trading_days` all accept `scoring_fingerprint: str \| None = None` with default-None preserving legacy behavior. |
| 9 | `_score_historical_match()` returns 0.0 | PASS | `quality_engine.py:155` returns `0.0` with a dormancy comment explaining why and what happens if someone bumps the weight without replacing the stub. |
| 10 | main.py Phase 10.25 uses `catalyst.db` | PASS | `argus/main.py:1119` reads `db_path = Path(config.system.data_dir) / "catalyst.db"`. Preceding comment block cites the audit finding and root cause. |
| 11 | 11 new FIX-01 regression tests + 2 adjusted assertions | PASS | 4 fingerprint tests (stability, sensitivity, round-trip, promotion filter) + 1 catalyst DB path grep-guard + 6 load_config merge tests (baseline, override, fallback, standalone-only key, live-only key, registry sanity). All 36 targeted tests pass locally in 0.07s. `test_historical_match_returns_50` renamed to `test_historical_match_returns_dormant_zero`; `test_score_setup_full_pipeline` updated for new composite (69.0 → 59.0, B+ → B). |
| 12 | Option A artifact `tests/test_fix01_quality_yaml_parity.py` absent | PASS | File not present on disk (`ls` returns No such file). Never tracked in a commit. |
| 13 | Sibling FIX-00/15/17 reports not staged | PASS | `git show --name-only 59bb100` shows none of `docs/sprints/sprint-31.9/*.md` staged. Working-tree `git status` confirms they remain untracked. |
| 14 | Config YAML files unchanged | PASS | `git diff HEAD~1 HEAD -- config/` empty. `config/system.yaml`, `config/system_live.yaml`, `config/quality_engine.yaml`, `config/overflow.yaml` all at their pre-commit contents. |
| 15 | FIX-02 left as a one-tuple extension point | PASS | No overflow-specific shim code in this commit. Only a doc-comment at `argus/core/config.py:1335` referring to FIX-02's future extension. FIX-02 becomes a single tuple-entry addition to `_STANDALONE_SYSTEM_OVERLAYS`. |

### Escalation Criteria Evaluation

| Trigger | Fired? | Notes |
|---------|--------|-------|
| CRITICAL finding unresolved or mis-implemented | NO | All 5 CRITICAL findings (P1-D1-C01, P1-D1-C02, DEF-082, DEF-142, H2-D01/D02/D03) verified resolved. |
| pytest net delta < 0 | NO | +11 to +14 depending on time-of-day DEF-163 boundary. |
| Scope boundary violation | NO | All 18 files within scope. |
| Rule-4 sensitive file touched without authorization | NO | No rule-4-tagged file in the diff. |
| Regression check (1)–(15) fails | NO | All pass. |
| Pivot architecturally unsound | NO | `deep_update()` merge semantics preserve all keys in both directions; Pydantic validation runs post-merge; standalone overlays are explicit and registered via a module-scope tuple (not implicit auto-discovery); backwards-compatible (absent overlay → legacy behavior). The Option A → Option B pivot reduces blast radius (zero YAML churn) and produces a single source of truth per subsystem. |

### Architectural Assessment of DEC-384

The Option B merge is well-formed:

1. **Merge direction is correct.** `deep_update(existing, overlay)` — `existing` is the live-merged system block's section, `overlay` is the standalone file. The helper's docstring says "override value wins" and the test `test_key_only_in_system_survives_partial_overlay` empirically verifies the "live-only key survives" direction. Precedence is consistently `standalone > live > base`.
2. **No silent key loss.** The deep merge recurses on matching dict keys and unions non-conflicting keys; neither side's keys are dropped. `test_key_only_in_standalone_appears_in_merged_result` + the mirror test cover both directions.
3. **Validation posture preserved.** The merged dict still flows through `ArgusConfig(**raw)` → Pydantic. Invalid overlay contents (bad types, out-of-range values) surface as Pydantic ValidationErrors at load time, not silently. `QualityEngineConfig` validators (e.g., weights sum-to-1) still run.
4. **Registry is explicit, not auto-discovery.** `_STANDALONE_SYSTEM_OVERLAYS` is a module-scope tuple; new overlays require a code edit, not a config-dir scan. This is the correct posture for a security- and correctness-sensitive config-loading path.
5. **Extension discipline for FIX-02.** The single-tuple-entry extension point is clean. No pre-emptive overflow shim code was landed; only a doc comment.

One minor judgment call flagged in the closeout deserves a nod: the implementation silently skips a non-dict overlay (e.g., YAML list, scalar, or malformed file) rather than raising. This is consistent with the existing `load_yaml_file()` behavior of returning `{}` for empty files, but it *could* mask a misconfigured overlay. Not a review-blocker — the existing pattern is well-established — but worth noting that if DEF-082-style silent-empty-table bugs recur, this is a candidate hardening site.

### Findings

None. Everything in the spec and regression checklist is cleanly implemented.

### Test Run Note

At review time (20:15 ET on 2026-04-21), my fresh full-suite run returned:

- 4,944 passed / 3 failed in 150.31s
- Failures: `test_get_todays_pnl_excludes_unrecoverable` (DEF-163 item (a), time-of-day bug 20:00–00:00 ET), `test_history_store_migration` (DEF-163 item (b), hardcoded default at line 36), `test_all_ulids_mapped_bidirectionally` (xdist flake, passes in isolation, unrelated to FIX-01 scope).
- The closeout captured 4,947 passed / 0 failed earlier in the day (~19:56 ET commit time) before the DEF-163 time boundary and DEF-150 boundary were crossed.
- The +11 net delta (my run) vs +14 (closeout) both clear the +8 threshold. Neither the DEF-163 pair nor the xdist flake is attributable to FIX-01 — DEF-163 is pre-existing and CLAUDE.md-documented; FIX-01 touches no execution/broker code.

### Verdict

**CLEAR.** FIX-01 resolves 9 audit findings (2 critical DEF closures, 4 audit-level CRITICAL findings, 1 MEDIUM, 2 LOW) with a clean Option B pivot codified as DEC-384. Scope discipline held; no spill-over to execution, data, strategy, or UI layers. Back-annotation complete. New regression guards are targeted and pass cleanly. The A→B pivot is architecturally sound and narrower-blast-radius than Option A would have been. Pre-existing DEF-163 surfacing at review time reflects real-time tests and is not a FIX-01 regression.

---END-REVIEW---
```

```json:structured-verdict
{
  "session_id": "FIX-01-catalyst-db-quality-pipeline",
  "sprint": "audit-2026-04-21-phase-3",
  "commit_sha": "59bb100",
  "branch": "main",
  "verdict": "CLEAR",
  "reviewer_tier": 2,
  "review_date": "2026-04-21",
  "closeout_self_assessment": "MINOR_DEVIATIONS",
  "regression_checks": {
    "pytest_net_delta_at_least_8": "PASS",
    "only_expected_preexisting_failures": "PASS_WITH_ANNOTATION",
    "no_out_of_scope_file_modified": "PASS",
    "audit_report_back_annotations_applied": "PASS",
    "claudemd_def_closures_recorded": "PASS",
    "dec_384_added_with_full_fields": "PASS",
    "dec_index_count_bumped_383_to_384": "PASS",
    "standalone_system_overlays_tuple_present": "PASS",
    "load_config_deep_merge_with_info_log": "PASS",
    "scoring_fingerprint_module_present": "PASS",
    "counterfactual_store_migration_idempotent": "PASS",
    "counterfactual_tracker_wires_fingerprint": "PASS",
    "promotion_evaluator_optional_filter": "PASS",
    "score_historical_match_returns_zero": "PASS",
    "main_py_phase_10_25_uses_catalyst_db": "PASS",
    "regression_tests_11_added_plus_2_adjusted": "PASS",
    "option_a_parity_test_absent": "PASS",
    "sibling_fix_reports_not_staged": "PASS",
    "config_yamls_unchanged": "PASS",
    "fix_02_one_tuple_extension_point_preserved": "PASS"
  },
  "escalation_triggers_fired": [],
  "findings_verified_resolved": [
    "P1-D1-C01",
    "P1-D1-C02",
    "P1-D1-L01",
    "H2-D01",
    "H2-D02",
    "H2-D03",
    "H2-DEAD05",
    "DEF-082",
    "DEF-142"
  ],
  "new_decs_verified": ["DEC-384"],
  "new_defs_opened": [],
  "pivot_assessment": {
    "option_selected": "B",
    "architecturally_sound": true,
    "merge_preserves_keys_both_directions": true,
    "pydantic_validation_still_runs": true,
    "registry_is_explicit_not_auto_discovery": true,
    "backwards_compatible": true,
    "no_silent_key_loss": true
  },
  "test_run_at_review_time": {
    "passed": 4944,
    "failed": 3,
    "failures": [
      "tests/analytics/test_def159_entry_price_known.py::test_get_todays_pnl_excludes_unrecoverable (DEF-163 (a), time-of-day 20:00-00:00 ET, pre-existing)",
      "tests/core/test_regime_vector_expansion.py::TestHistoryStoreMigration::test_history_store_migration (DEF-163 (b), hardcoded date, pre-existing)",
      "tests/execution/test_ibkr_broker.py::TestIBKRBrokerBracketOrders::test_all_ulids_mapped_bidirectionally (xdist flake, passes in isolation, unrelated to FIX-01)"
    ],
    "net_delta_vs_baseline_4933": 11,
    "above_min_threshold_plus_8": true,
    "all_failures_attributable_to_fix_01": false
  },
  "closeout_test_run": {
    "passed": 4947,
    "failed": 0,
    "net_delta_vs_baseline_4933": 14
  }
}
```
