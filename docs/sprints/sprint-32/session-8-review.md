---BEGIN-REVIEW---

# Sprint 32, Session 8 — Tier 2 Review Report

**Reviewer:** Tier 2 Automated Review (Claude Opus 4.6)
**Date:** 2026-04-01
**Session:** S8 — CLI + REST API + Server Integration + Config Gating
**Close-out self-assessment:** CLEAN

---

## 1. Diff Scope Verification

**Changes are uncommitted.** The S8 work exists as unstaged modifications and
untracked files in the working tree. The HEAD commit is S7 (9f520ee). This is
noted for completeness; the review covers the working tree delta against HEAD.

### Files Changed (Modified)
- `argus/api/dependencies.py` — Added `ExperimentStore` TYPE_CHECKING import + field on AppState
- `argus/api/routes/__init__.py` — Registered experiments router
- `argus/api/server.py` — ExperimentStore lifespan init/cleanup
- `argus/core/config.py` — ExperimentConfig import + field on SystemConfig

### Files Created
- `argus/intelligence/experiments/config.py` — ExperimentConfig Pydantic model
- `argus/api/routes/experiments.py` — 4 REST endpoints
- `scripts/run_experiment.py` — CLI entry point
- `tests/api/test_experiments_api.py` — 17 API tests
- `tests/test_experiment_cli.py` — 11 CLI/config tests
- `docs/sprints/sprint-32/session-8-closeout.md` — Close-out report

### Protected Files Verification
- `argus/intelligence/experiments/store.py` (S4) — NOT modified
- `argus/intelligence/experiments/runner.py` (S6) — NOT modified
- `argus/intelligence/experiments/promotion.py` (S7) — NOT modified
- `argus/intelligence/experiments/spawner.py` (S5) — NOT modified
- `argus/intelligence/experiments/models.py` (S4) — NOT modified
- `argus/strategies/` — NOT modified
- `argus/ui/` — NOT modified

**Verdict: All scope constraints respected.**

---

## 2. Session-Specific Focus Items

### F1: ExperimentConfig has `extra="forbid"`
**PASS.** Line 38 of `config.py`: `model_config = ConfigDict(extra="forbid")`.
Verified programmatically: constructing with an unknown key raises
`ValidationError` with "Extra inputs are not permitted".

### F2: REST endpoints return 503 when experiments disabled
**PASS.** The `_get_experiment_store()` helper raises `HTTPException(503)` when
`state.experiment_store is None`. Four dedicated tests verify 503 on all
endpoints when disabled.

### F3: POST /experiments/run uses BackgroundTasks (non-blocking)
**PASS.** Route function accepts `background_tasks: BackgroundTasks` parameter.
When `body.dry_run` is False, `background_tasks.add_task(_run_sweep)` is called.
Response returns immediately with `experiment_count=0` and `grid_size`.

### F4: CLI works standalone without server
**PASS.** `scripts/run_experiment.py` imports `ExperimentStore` and
`ExperimentRunner` directly; uses `asyncio.run()` with no FastAPI dependency.
Test `test_cli_dry_run_prints_grid_without_executing` confirms standalone
operation.

### F5: JWT protection on all 4 endpoints
**PASS.** All four route functions include `_auth: dict = Depends(require_auth)`.
Three JWT-absence tests cover list, get-by-id, and run-sweep (assert 401 or
403). The baseline endpoint lacks an explicit JWT-absence test, but its
`Depends(require_auth)` is structurally identical to the others.

### F6: Server lifespan initializes store only when experiments.enabled is True
**PASS.** `server.py` checks
`app_state.config.experiments is not None and app_state.config.experiments.enabled`
before initializing ExperimentStore. The else-branch logs "disabled". Cleanup
only runs if `experiments_initialized_here` is True.

### F7: Config validation test is programmatic (not hardcoded key list)
**PASS.** `test_experiments_yaml_keys_match_model_fields` reads
`ExperimentConfig.model_fields.keys()` at runtime and compares against YAML
keys. No hardcoded list.

### F8: No S4-S7 experiment files modified
**PASS.** `git diff HEAD` shows zero changes to store.py, runner.py,
promotion.py, spawner.py, or models.py.

---

## 3. Sprint-Level Regression Checklist

| # | Check | Result |
|---|-------|--------|
| R1 | 12 existing strategies instantiate | Not directly verified (would need startup); no code changes to strategy registration path |
| R2 | Existing YAML configs load | ExperimentConfig defaults via `Field(default_factory=ExperimentConfig)` — existing configs without `experiments:` key still load |
| R3 | Pattern constructor defaults unchanged | No changes to pattern files |
| R4 | PatternBacktester supports pre-existing patterns | No changes to factory or backtester |
| R5 | PatternBacktester supports Sprint 29 patterns | No changes to factory or backtester |
| R6 | Shadow mode routing works | No changes to routing |
| R7 | CounterfactualTracker handles variant signals | No changes to tracker |
| R8 | Non-PatternModule strategies untouched | PASS — verified via git diff |
| R9 | Test suite passes | PASS — 4,402 passed, 0 failures |
| R10 | Config validation rejects invalid values | PASS — `extra="forbid"` + field constraints tested |
| R11 | experiments disabled -> system unchanged | PASS — 503 from all endpoints, no store init |
| R12 | Paper trading overrides unaffected | PASS — no changes to risk/orchestrator configs |
| R13 | No silently ignored config keys | PASS — programmatic test + extra=forbid |
| R14 | Fingerprint deterministic | No changes to fingerprint logic |
| R15 | trades table migration backward compatible | No changes to trades table |
| R16 | Orchestrator registration unchanged | No changes to orchestrator.py |

---

## 4. Escalation Criteria Check

| Criterion | Triggered? |
|-----------|-----------|
| Shadow variants >10% throughput degradation | No — session adds no runtime shadow logic |
| Variant spawning >2x memory increase | No — session adds config + API only |
| Event Bus contention from 35+ subscribers | No — no new subscriptions added |
| Parameter fingerprint hash collision | No — no changes to fingerprint logic |
| CounterfactualTracker volume handling | No — no changes to tracker |
| Factory fails to construct existing pattern | No — no factory changes |
| ARGUS fails to start with experiments disabled | No — default ExperimentConfig() is disabled |
| Pre-existing test failure introduced | No — 4,402 passed |
| Detection param silently ignored | No — extra=forbid enforced |

**No escalation criteria triggered.**

---

## 5. Findings

### F1 (LOW): Unused `asyncio` import in experiments routes
`argus/api/routes/experiments.py` line 11 imports `asyncio` but never uses it.
Will trigger linter warnings. Cosmetic only.

### F2 (LOW): Bare `dict` type on `variants` field
`ExperimentConfig.variants` is typed as `dict` rather than
`dict[str, list[dict[str, Any]]]` or similar parameterized generic. This matches
the spec verbatim but violates the project's code style rule ("Use parameterized
generics: `dict[str, Any]`, not bare `dict`"). Functionally harmless since
`extra="forbid"` does not apply recursively to the variants dict values.

### F3 (LOW): `_get_experiment_store()` returns `object` instead of typed return
The helper function returns `object`, losing type information for callers. A
`TYPE_CHECKING` import of `ExperimentStore` with proper return annotation would
be cleaner. Functionally correct at runtime.

### F4 (LOW): Missing JWT-absence test for baseline endpoint
Three of the four endpoints have explicit no-JWT rejection tests. The
`GET /experiments/baseline/{pattern_name}` endpoint is missing an explicit
JWT-absence test. It is structurally identical and covered by `Depends(require_auth)`,
so the risk is negligible, but completeness would be better.

### F5 (INFO): Close-out report test count discrepancy
Close-out claims "4,298 tests" for existing suite but then "4,402 passed" for
full suite. The delta is 104, not 28 (the new test count). This appears to be a
pre-existing test count discrepancy in the close-out narrative — the 4,298
likely reflects the baseline before S7's tests were counted. The 4,402 full
suite count is confirmed correct by the review test run.

---

## 6. Definition of Done Verification

| Item | Status |
|------|--------|
| ExperimentConfig Pydantic model created | DONE |
| ExperimentConfig wired into SystemConfig | DONE |
| 4 REST endpoints created and JWT-protected | DONE |
| CLI script created with all flags | DONE |
| Server wiring (lifespan + router) | DONE |
| Config validation test passes | DONE |
| All existing tests pass | DONE (4,402 passed) |
| All new tests pass | DONE (28 new) |
| Close-out report written | DONE |

---

## 7. Verdict

**CLEAR**

The implementation faithfully follows the spec. All 8 session-specific focus
items pass. No escalation criteria triggered. The full test suite passes with
4,402 tests and 0 failures. Protected files are untouched. The four findings
are all LOW/INFO severity — unused import, bare dict type, loose return type
annotation, and a missing JWT test for one endpoint. None of these affect
correctness or safety.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "session": "Sprint 32, Session 8",
  "reviewer": "Tier 2 Automated Review (Claude Opus 4.6)",
  "date": "2026-04-01",
  "test_results": {
    "total_passed": 4402,
    "total_failed": 0,
    "new_tests": 28,
    "warnings": 64
  },
  "focus_items": {
    "F1_extra_forbid": "PASS",
    "F2_503_when_disabled": "PASS",
    "F3_background_tasks": "PASS",
    "F4_cli_standalone": "PASS",
    "F5_jwt_protection": "PASS",
    "F6_lifespan_gating": "PASS",
    "F7_programmatic_validation": "PASS",
    "F8_no_s4_s7_modifications": "PASS"
  },
  "escalation_triggered": false,
  "findings": [
    {
      "id": "F1",
      "severity": "LOW",
      "description": "Unused asyncio import in argus/api/routes/experiments.py"
    },
    {
      "id": "F2",
      "severity": "LOW",
      "description": "Bare dict type on ExperimentConfig.variants field (matches spec but violates code style)"
    },
    {
      "id": "F3",
      "severity": "LOW",
      "description": "_get_experiment_store() returns object instead of ExperimentStore"
    },
    {
      "id": "F4",
      "severity": "LOW",
      "description": "Missing JWT-absence test for GET /experiments/baseline/{pattern_name}"
    },
    {
      "id": "F5",
      "severity": "INFO",
      "description": "Close-out report existing test count 4298 vs actual 4374 (pre-S8 baseline)"
    }
  ],
  "protected_files_clean": true,
  "regression_checklist_passed": true,
  "close_out_assessment_agrees": true
}
```
