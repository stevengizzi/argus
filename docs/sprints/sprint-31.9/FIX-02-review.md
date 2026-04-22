# FIX-02-config-drift-critical — Tier 2 Review

> Independent review produced per `workflow/claude/skills/review.md`.
> Paste the fenced block below into the Work Journal on Claude.ai.

```markdown
---BEGIN-REVIEW---

**Reviewing:** audit-2026-04-21-phase-3 — FIX-02-config-drift-critical (overflow.yaml via DEC-384 standalone overlay)
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-04-21
**Verdict:** CLEAR

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | `git diff --name-only c987ccd..9454df5` returns exactly the 11 expected files; no out-of-scope modifications. |
| Close-Out Accuracy | PASS | Change manifest matches diff precisely. Judgment calls surfaced honestly (shape-mismatch discovery, non-dict warning wording, `tests/intelligence/test_config.py` intentionally left alone per prompt). Test math (+3 delta = 3 new tests) reconciles exactly. |
| Test Health | PASS | Targeted suite: 48/48 pass. Full suite: 4,946 passed + 2 failed. The 2 failures are exactly the DEF-163 date-decay pair pre-registered in CLAUDE.md (`test_get_todays_pnl_excludes_unrecoverable`, `test_history_store_migration`). No new regressions. New tests are non-trivial (registry membership, end-to-end merge via `tmp_path`, caplog WARNING assertion + fallback behavior). |
| Regression Checklist | PASS | All 5 prompt-specified checks green (see Findings below). |
| Architectural Compliance | PASS | DEC-384 registry extension is exactly the "one-tuple addition" FIX-01 previewed. `load_config()` logic unchanged except for the WARNING log (authorized deferred pickup) and docstring. Shape convention (bare fields at top) now applied consistently across both registered overlays. |
| Escalation Criteria | NONE_TRIGGERED | No CRITICAL finding, no scope boundary violation, no merge-correctness break, no FIX-01 regression, no test failure outside known flake set. |

### Findings

#### Verification Results (prompt-specified correctness checks)

| Check | Expected | Actual | Result |
|-------|----------|--------|--------|
| `config.system.overflow.broker_capacity` | `50` | `50` | PASS |
| `config.system.quality_engine.weights.pattern_strength` (FIX-01 path) | `0.375` | `0.375` | PASS |
| `grep -rn "broker_capacity" config/` | 1 hit in `overflow.yaml` only | `config/overflow.yaml:11:broker_capacity: 50` | PASS |
| Targeted test suite | all pass | 48 passed | PASS |
| Full pytest suite | >= 4,943 baseline; only DEF-163 flakes failing | 4,946 passed + 2 DEF-163 failures | PASS |

#### Shape-Mismatch Verification

- `config/overflow.yaml` has bare top-level fields (`enabled: true`, `broker_capacity: 50`) with no `overflow:` wrapper. Shape matches `quality_engine.yaml` convention. File carries an explicit comment documenting the DEC-384/FIX-02 convention.
- `config/system.yaml` and `config/system_live.yaml` no longer carry an `overflow:` block. Both files now have a clear pointer comment directing readers to `config/overflow.yaml` with a "Do NOT re-add an `overflow:` block here" warning. This matches the quality_engine precedent.

#### Registry / Merge Code

- `_STANDALONE_SYSTEM_OVERLAYS` at `argus/core/config.py:1350-1353` contains exactly two tuples: `("quality_engine", "quality_engine.yaml")` and `("overflow", "overflow.yaml")`.
- `load_config()` merge body (lines 1415-1443) is semantically unchanged. The only functional addition is the `logger.warning(...)` call inside the `if not isinstance(overlay, dict):` branch (lines 1424-1430), which replaces a silent `continue` — exactly the Stage 1 deferred pickup FIX-01's review flagged. Docstring updated to reference FIX-02 extension.

#### Test Integrity

- **Rename integrity**: `test_overflow_yaml_broker_capacity_is_60` → `test_overflow_yaml_broker_capacity_is_50` (correct — the body asserts 50). `test_overflow_config_loads_with_capacity_60` NOT renamed (correct — its body uses `_build_overflow_system(...broker_capacity=60)` programmatically and asserts 60; the "60" in the name refers to the programmatic input, not the YAML).
- **`tests/intelligence/test_config.py::TestOverflowConfigYamlAlignment::test_yaml_overflow_loads_into_config`** (line 146-152): close-out flagged this as trivially passing since `system.yaml` no longer has an `overflow:` block; `raw.get("overflow", {})` returns `{}`, `OverflowConfig(**{})` defaults `broker_capacity=30`, and the test asserts 30. **Independently verified: observation is correct.** The prompt explicitly directed "do not touch this test" in §3, so this is an acknowledged cosmetic brittleness, not a review concern. Close-out surfaced it in "deferred_observations" honestly.
- **New tests**: All 3 exercise real behavior — not tautologies:
  - `test_registry_includes_overflow_after_fix02`: asserts registry membership (would fail if FIX-02 were reverted).
  - `test_overflow_broker_capacity_loaded_from_standalone`: end-to-end with `tmp_path` + synthetic YAML files, asserts `config.system.overflow.broker_capacity == 50` (would fail if `load_config()` or the registry were broken).
  - `test_non_dict_standalone_overlay_emits_warning`: writes a YAML list, asserts WARNING caplogged AND config still loads with defaults. Non-trivial — covers both the WARNING path (new behavior) and the graceful-fallback path.

#### Audit Back-Annotation Completeness

- `docs/audits/audit-2026-04-21/p1-d1-catalyst-quality.md`: new "FIX-02 Resolution" section annotates **C3** as RESOLVED. The pre-existing closing prose `"C3 ... is deferred to FIX-02..."` was correctly replaced with the new Resolution section. PASS.
- `docs/audits/audit-2026-04-21/p1-h2-config-consistency.md`: new "FIX-02 Resolution" section annotates **D-05** AND **DEAD-04** as RESOLVED. The FIX-01-era "deferred to FIX-02" sentence was updated to reference the new Resolution section. Bonus: Stage 1 deferred pickup (non-dict warning) is documented. PASS — and notably the close-out over-delivered by including DEAD-04 (same root cause as D-05).
- `docs/audits/audit-2026-04-21/phase-2-review.csv`: P1-D1-C03 row (line 106) and H2-D05 row (line 347) both carry `**RESOLVED FIX-02-config-drift-critical** (DEC-384 registry extension)` in their notes column. PASS.

#### CLAUDE.md Update Coherence

- "Last updated" line refreshed to reference FIX-02.
- Active Sprint status line updated: `FIX-00/15/17/20/01/11 landed; FIX-02 just landed`.
- FIX-01 entry's trailing sentence softened from forward-looking `"FIX-02 (overflow.yaml) becomes a one-tuple addition..."` to past-tense cross-reference: `"FIX-02 (overflow.yaml) subsequently landed as the first extension of _STANDALONE_SYSTEM_OVERLAYS — see next entry."` Correct.
- New FIX-02 follow-on block added directly below the FIX-01 entry. Dense and accurate — enumerates the finding pair, the registry extension, the shape flattening, the system-YAML block removal, the runtime effect (broker_capacity=50 closing the 20-position drift window), the Stage 1 deferred pickup, and the test delta.
- No new DEF-NNN or DEC-NNN entries introduced. Verified by diff inspection of CLAUDE.md and confirmed against close-out assertion.

#### No HIGH or CRITICAL findings.

### Recommendation

**Proceed to next session.** FIX-02 is a clean, surgical execution of the FIX-01 preview: exactly the "one-tuple addition" DEC-384 anticipated, plus the load-bearing shape-flattening discovery the operator override in the prompt specifically called out. The Stage 1 deferred pickup (non-dict overlay WARNING) was folded in transparently with a +7-line footprint, well within the prompt's stated threshold. All 11 scope files map 1:1 to the spec. The full-suite delta (+3 passing = 3 new regression tests) reconciles exactly. The two DEF-163 failures are pre-existing date-decay flakes acknowledged in CLAUDE.md.

One observation worth carrying forward (not blocking): `tests/intelligence/test_config.py::TestOverflowConfigYamlAlignment` tests are now effectively no-ops (they assert against an empty dict). The close-out correctly flagged this in `deferred_observations` and correctly declined to fix it per prompt §3. Future cleanup (likely FIX-13 test-hygiene or a dedicated follow-up) could either retarget those tests at `config/overflow.yaml` directly or delete them since the new tests in `test_fix01_load_config_merge.py` cover the real merge behavior.

---END-REVIEW---
```

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "audit-2026-04-21-phase-3",
  "session": "FIX-02-config-drift-critical",
  "verdict": "CLEAR",
  "findings": [
    {
      "description": "tests/intelligence/test_config.py::TestOverflowConfigYamlAlignment tests are now no-ops since system.yaml has no overflow: block. raw.get('overflow', {}) returns {}, OverflowConfig(**{}) defaults broker_capacity=30, and the test asserts 30 — passes trivially without exercising real behavior. The prompt §3 explicitly directed not to touch this file; close-out surfaced this honestly in deferred_observations. Not a regression of FIX-02 (it was equally meaningless before); only the shape changed.",
      "severity": "INFO",
      "category": "TEST_COVERAGE_GAP",
      "file": "tests/intelligence/test_config.py",
      "recommendation": "Retarget at config/overflow.yaml directly, or delete since test_fix01_load_config_merge.py now covers real merge behavior. Candidate for FIX-13 test-hygiene batch."
    }
  ],
  "spec_conformance": {
    "status": "CONFORMANT",
    "notes": "All 12 scope requirements from close-out's Scope Verification table verified. All 5 prompt-specified correctness checks green. All back-annotations present and correctly worded. CLAUDE.md updates coherent. No new DEFs or DECs introduced (prompt §1 explicit: DEC-384 covers the registry extension).",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "CLAUDE.md",
    "argus/core/config.py",
    "config/overflow.yaml",
    "config/system.yaml",
    "config/system_live.yaml",
    "docs/audits/audit-2026-04-21/p1-d1-catalyst-quality.md",
    "docs/audits/audit-2026-04-21/p1-h2-config-consistency.md",
    "docs/audits/audit-2026-04-21/phase-2-review.csv",
    "tests/core/test_signal_cutoff.py",
    "tests/test_fix01_load_config_merge.py",
    "tests/test_overflow_routing.py"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": false,
    "count": 4946,
    "new_tests_adequate": true,
    "test_quality_notes": "Full suite: 4,946 passed + 2 failed. Both failures are DEF-163 date-decay pre-existing flakes (test_get_todays_pnl_excludes_unrecoverable, test_history_store_migration) acknowledged in CLAUDE.md's Known Issues. Targeted suite: 48/48 passed. 3 new regression tests are non-trivial: registry membership, end-to-end merge via tmp_path, caplog WARNING + fallback behavior. +3 delta reconciles exactly with 3 new tests. No test deletions, no test skips added."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "Live load_config produces config.system.overflow.broker_capacity == 50", "passed": true, "notes": "Direct Python invocation confirmed; also covered by new test_overflow_broker_capacity_loaded_from_standalone"},
      {"check": "FIX-01 path unbroken: quality_engine.weights.pattern_strength == 0.375", "passed": true, "notes": "Direct Python invocation confirmed"},
      {"check": "grep -rn 'broker_capacity' config/ returns only overflow.yaml", "passed": true, "notes": "Single hit at config/overflow.yaml:11"},
      {"check": "pytest net delta >= 0 against baseline 4,943", "passed": true, "notes": "4,946 passed (+3, matches 3 new tests)"},
      {"check": "Pre-existing failures match known flake set (DEF-150, DEF-163)", "passed": true, "notes": "2 failures this run are both DEF-163 date-decay; DEF-150 did not flake this run"},
      {"check": "No file outside declared 11-file scope was modified", "passed": true, "notes": "git diff --name-only c987ccd..9454df5 returns exactly the 11 expected files"},
      {"check": "Every resolved finding back-annotated with RESOLVED FIX-02-config-drift-critical", "passed": true, "notes": "P1-D1-C03 + H2-D05 both carry the annotation in CSV and markdown. DEAD-04 bonus-annotated (same root cause)."},
      {"check": "No new DEFs opened, no new DECs introduced", "passed": true, "notes": "DEC-384 covers this extension per prompt §1"},
      {"check": "overflow.yaml flattened to bare fields (no 'overflow:' wrapper)", "passed": true, "notes": "Confirmed by direct read of config/overflow.yaml"},
      {"check": "overflow: block removed from system.yaml + system_live.yaml with pointer comment", "passed": true, "notes": "Both files replace the overflow: block with a clear pointer comment referencing config/overflow.yaml"},
      {"check": "_STANDALONE_SYSTEM_OVERLAYS contains both quality_engine and overflow tuples", "passed": true, "notes": "Verified at argus/core/config.py:1350-1353"},
      {"check": "load_config() merge logic unchanged except for authorized WARNING log", "passed": true, "notes": "Diff confirms only the WARNING log addition (lines 1424-1430) and docstring update; deep_update path is semantically identical"}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Proceed to next FIX-NN session per campaign order.",
    "Optional follow-up (not blocking): retarget or retire tests/intelligence/test_config.py::TestOverflowConfigYamlAlignment during FIX-13 test-hygiene. Real behavior coverage now lives in tests/test_fix01_load_config_merge.py."
  ]
}
```
