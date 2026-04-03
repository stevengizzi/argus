---BEGIN-REVIEW---

**Reviewing:** Sprint 31.5, Session 1 — Parallel Sweep Infrastructure
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-04-03
**Verdict:** CONCERNS

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | Deliverables 1 and 5 implemented per session prompt. Unfinished items (DEF-146, CLI, filter YAMLs) correctly deferred to later sessions. |
| Close-Out Accuracy | PASS | Change manifest matches diff. Self-assessment MINOR_DEVIATIONS is justified — session-3 impl file was modified (not in scope but harmless). Judgment calls documented. |
| Test Health | PASS | 93 experiment tests pass; 4,831 full suite pass. +8 new tests. |
| Regression Checklist | PASS | All applicable checklist items verified (see details below). |
| Architectural Compliance | PASS | Module-level worker, no SQLite in subprocess, main-process store writes. Follows project patterns. |
| Escalation Criteria | NONE_TRIGGERED | No pickling issues, no SQLite corruption risk, no memory concerns. |

### Findings

**F1 (MEDIUM): `_run_single_backtest` calls `_backtest_result_to_dict` which is defined at module level in the same file — works only because ProcessPoolExecutor uses `fork` on macOS/Linux**

File: `argus/intelligence/experiments/runner.py:112`

The worker function `_run_single_backtest` (line 57) calls `_backtest_result_to_dict` (defined at line 727) from within its nested `_execute()` async function. This works because on Unix-like systems, `ProcessPoolExecutor` uses `fork` by default, so the subprocess inherits the parent's module state. However, on systems where the start method is `spawn` (Windows, or if `mp.set_start_method("spawn")` is called), the worker function must be importable and all its dependencies resolvable via import. Since `_backtest_result_to_dict` is in the same module and the module is importable, this would work with `spawn` too — but it differs from the local-import pattern used for `BacktestEngine`, `BacktestEngineConfig`, etc. inside `_execute()`. The inconsistency is worth noting: either all module-level helpers should be locally imported inside the worker (consistent defensive pattern) or none should be (consistent trust-the-module pattern). No functional bug today, but a consistency concern.

**F2 (LOW): Modification of `docs/sprints/sprint-31.5/sprint-31.5-session-3-impl.md` outside session scope**

File: `docs/sprints/sprint-31.5/sprint-31.5-session-3-impl.md`

The session modified a future session's implementation prompt to fix a Python falsy-value bug (`args.workers or config.max_workers` changed to `args.workers if args.workers is not None else config.max_workers`) and add an explanatory note. The fix itself is correct and helpful — it prevents `--workers 0` from silently falling through. However, modifying a future session's prompt from within the current session is a minor scope boundary deviation. The close-out report documents this as MINOR_DEVIATIONS, which is appropriate.

**F3 (LOW): `_run_single_backtest` uses bare `dict` return type annotation**

File: `argus/intelligence/experiments/runner.py:57`

The function signature is `def _run_single_backtest(args: dict) -> dict:`. Per project code-style rules (CLAUDE.md: "Use parameterized generics: `dict[str, Any]`, not bare `dict`"), this should be `def _run_single_backtest(args: dict[str, Any]) -> dict[str, Any]:`. The inner `_execute()` at line 79 also uses bare `dict`. Minor style issue.

**F4 (INFO): Progress logging in parallel path reports completion order, not grid order**

File: `argus/intelligence/experiments/runner.py:452-459`

The parallel path uses `asyncio.as_completed()` which yields results in completion order. The progress log shows `[completed_count/total_pending]` which is accurate for throughput tracking but means log lines are not in grid-point order. This is expected and acceptable behavior for parallel execution — noted for operator awareness only.

### Regression Checklist Results

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | Sequential identical to current | PASS | `workers=1` falls through to unchanged sequential loop (line 478+). Test `test_run_sweep_sequential_identical` confirms. |
| 2 | Store writes main-process only | PASS | No `ExperimentStore` in `_run_single_backtest`. `save_experiment()` called only after `await coro` in main process. |
| 3 | Fingerprint dedup works | PASS | `test_run_sweep_parallel_skips_existing_fingerprints` confirms all duplicates skipped. |
| 4 | CLI unchanged without new flags | PASS | No CLI changes in this session. |
| 5 | `ExperimentConfig(extra="forbid")` valid | PASS | `test_config_max_workers_field` + `test_experiments_yaml_loads_without_parse_error` both pass. |
| 9 | 4,831 pytest pass | PASS | 4,831 passed in full suite run (was 4,823 pre-sprint; +8 new). |
| 11 | Existing experiment tests pass | PASS | 93 passed in `tests/intelligence/experiments/` (was 85; +8 new). |

### Session-Specific Focus Verification

| # | Focus Item | Verified |
|---|-----------|----------|
| 1 | `_run_single_backtest()` is module-level | YES — `runner.py:57`, standalone function, not a method or nested function. |
| 2 | No `ExperimentStore` import or usage in worker | YES — function body (lines 57-137) contains no ExperimentStore reference. |
| 3 | `asyncio.run()` used inside worker | YES — `runner.py:126`: `return _asyncio.run(_execute())`. |
| 4 | Fingerprint dedup BEFORE ProcessPoolExecutor dispatch | YES — dedup loop (lines 349-416) completes before `ProcessPoolExecutor` created at line 421. |
| 5 | KeyboardInterrupt calls `shutdown(wait=False, cancel_futures=True)` | YES — `runner.py:468`. |
| 6 | `workers=1` uses existing sequential loop | YES — `if workers > 1:` guard at line 347; `workers=1` falls through to sequential path at line 478. |

### Recommendation

CONCERNS: Two minor findings worth noting for future sessions.

F1 (inconsistent import pattern in worker function) is not a bug but represents a design inconsistency that could matter if the multiprocessing start method changes. Consider standardizing in a future cleanup pass.

F3 (bare `dict` type annotations) is a minor style violation. Can be addressed in S2 or S3 if those sessions touch the worker function.

Both findings are non-blocking. Proceed to Session 2.

### Post-Review Fixes Applied (2026-04-03)

F1 and F3 addressed in same session:
- **F3 fixed:** `_run_single_backtest` signature updated to `dict[str, Any]` for both `args` and return type. `_execute()` return type updated to `dict[str, Any]`.
- **F1 addressed:** Added explanatory comment at the `_backtest_result_to_dict(result)` call site documenting why it is called directly (pure helper, no side effects, no heavy imports — intentionally not locally imported). Local import pattern is reserved for heavy dependencies like `BacktestEngine`.

Tests: 93 passed after fixes (unchanged).

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "31.5",
  "session": "S1",
  "verdict": "CONCERNS",
  "findings": [
    {
      "description": "_run_single_backtest calls module-level _backtest_result_to_dict without local import, inconsistent with the defensive local-import pattern used for BacktestEngine et al. inside the nested _execute(). No functional bug, but inconsistent defensive pattern.",
      "severity": "MEDIUM",
      "category": "ARCHITECTURE",
      "file": "argus/intelligence/experiments/runner.py:112",
      "recommendation": "Either locally import _backtest_result_to_dict inside _execute() for consistency, or document that module-level helpers are intentionally trusted. Low urgency."
    },
    {
      "description": "Session modified docs/sprints/sprint-31.5/sprint-31.5-session-3-impl.md (a future session prompt) to fix a falsy-value bug. Correct fix but minor scope boundary deviation.",
      "severity": "LOW",
      "category": "SCOPE_BOUNDARY_VIOLATION",
      "file": "docs/sprints/sprint-31.5/sprint-31.5-session-3-impl.md",
      "recommendation": "No action needed — the fix is correct and the close-out documented it."
    },
    {
      "description": "_run_single_backtest uses bare dict type annotations instead of dict[str, Any] per project style rules.",
      "severity": "LOW",
      "category": "NAMING_CONVENTION",
      "file": "argus/intelligence/experiments/runner.py:57",
      "recommendation": "Update to dict[str, Any] in next session touching this function."
    },
    {
      "description": "Parallel progress logging reports completion order, not grid order (expected behavior with asyncio.as_completed).",
      "severity": "INFO",
      "category": "OTHER",
      "file": "argus/intelligence/experiments/runner.py:452",
      "recommendation": "No action needed — expected parallel execution behavior."
    }
  ],
  "spec_conformance": {
    "status": "CONFORMANT",
    "notes": "Session 1 scope (deliverables 1 and 5) fully implemented. Remaining deliverables correctly deferred to sessions 2-3.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/intelligence/experiments/config.py",
    "argus/intelligence/experiments/runner.py",
    "tests/intelligence/experiments/test_runner.py",
    "docs/sprints/sprint-31.5/sprint-31.5-session-3-impl.md"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 4831,
    "new_tests_adequate": true,
    "test_quality_notes": "8 new tests cover parallel distribution, worker error isolation, sequential identity, fingerprint dedup, dry-run guard, main-process store writes, config validation, and worker return structure. Good coverage of the parallel path contract."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "Sequential identical to current", "passed": true, "notes": "workers=1 falls through to unchanged sequential loop"},
      {"check": "Store writes main-process only", "passed": true, "notes": "No ExperimentStore in worker; save_experiment after await only"},
      {"check": "Fingerprint dedup works", "passed": true, "notes": "Test confirms all duplicates skipped before dispatch"},
      {"check": "CLI unchanged without new flags", "passed": true, "notes": "No CLI changes in S1"},
      {"check": "ExperimentConfig extra=forbid valid", "passed": true, "notes": "max_workers accepted; unknown fields still rejected"},
      {"check": "4831 pytest pass", "passed": true, "notes": "4831 passed, 0 failed"},
      {"check": "Existing experiment tests pass", "passed": true, "notes": "93 passed (85 existing + 8 new)"}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Consider standardizing import pattern in _run_single_backtest in a future session",
    "Fix bare dict type annotations to dict[str, Any] when next touching the worker function"
  ]
}
```
