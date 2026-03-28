---BEGIN-REVIEW---

# Sprint 28, Session 3b: Tier 2 Review

**Reviewer:** Automated (Tier 2)
**Date:** 2026-03-28
**Session:** Sprint 28, Session 3b — LearningService + CLI
**Verdict:** CLEAR

## Summary

Session 3b implements the LearningService orchestrator and CLI entry point as specified. The LearningService correctly wires OutcomeCollector, WeightAnalyzer, ThresholdAnalyzer, CorrelationAnalyzer, and LearningStore into a pipeline that collects outcomes, runs analysis, assembles a LearningReport, persists it, supersedes prior proposals, and generates new ConfigProposals. The CLI script provides `--window-days`, `--strategy-id`, and `--dry-run` flags. All 16 tests pass. No regressions introduced.

## Review Focus Items

### 1. Concurrent guard (`_running` flag) with proper try/finally

**PASS.** The `_running` flag is set to `True` at line 124, before entering the try block. The `finally` clause at line 128-131 unconditionally resets `_running = False`. The actual work is delegated to `_execute_analysis()` inside the try block. If `_execute_analysis()` raises, the finally block still fires. Test `test_concurrent_guard_resets_on_error` validates this path by injecting an exception in the collector and confirming `_running` resets to `False`.

### 2. Proposal supersession called BEFORE new proposals are created

**PASS.** In `_execute_analysis()`, `store.supersede_proposals(report.report_id)` is called at line 199, before `_generate_proposals()` at line 204 and the `save_proposal()` loop at lines 205-206. The test `test_supersede_called_before_new_proposals` uses call-order tracking to verify supersede occurs before any save_proposal call.

### 3. Config-gated behavior (enabled=false produces no analysis, no error)

**PASS.** Lines 117-119 check `self._config.enabled` and return `None` with an INFO log if disabled. The check occurs before the `_running` guard, so it does not set the running flag. Test `test_config_disabled_returns_none` validates that no collector or store methods are called when disabled.

### 4. CLI --dry-run doesn't persist to DB

**PASS with note.** The CLI script skips `store.initialize()` when `args.dry_run` is True (line 156-157), so the SQLite tables are never created. However, the service still calls `store.save_report()` and `store.save_proposal()` during `run_analysis()`. Since the LearningStore uses fire-and-forget exception handling (try/except with warning log), these calls will silently fail when the DB has no tables. The close-out report acknowledges this design honestly. The report object is still constructed and returned in full, and the CLI prints it to stdout. This is acceptable for a diagnostic tool but is not a clean separation. If a future session needs a cleaner pattern, a `dry_run` parameter on `run_analysis()` that skips persistence calls would be preferable.

### 5. LearningReport.version is set (forward-compat for Sprint 32.5)

**PASS.** The LearningReport dataclass has `version: int = 1` as a field default. The LearningService explicitly sets `version=1` at line 192. Test `test_report_version_is_set` validates this.

## Scope Compliance

- Only files within `argus/intelligence/learning/`, `scripts/`, `tests/intelligence/learning/`, and `docs/sprints/sprint-28/` were created or modified.
- No modifications to `server.py` or `main.py`.
- No config file `config/learning_loop.yaml` was created (that is S4's responsibility).
- The `__init__.py` modification adds only the LearningService import and `__all__` entry.

## Test Results

- **Learning module tests:** 126 passed (110 existing + 16 new) in 1.27s.
- **Full suite:** 3807 passed, 8 failed in 194.80s. All 8 failures are pre-existing (AI config race + backtest engine teardown), consistent with the close-out report and MEMORY.md.
- **No regressions introduced.**

## Code Quality Observations

- Type hints present on all function signatures.
- Google-style docstrings on all public methods and the class.
- Clean separation between the concurrent guard (`run_analysis`) and the pipeline logic (`_execute_analysis`).
- ULID generation for report and proposal IDs follows project convention (DEC-026).
- The `_enrich_with_regime` method correctly creates new WeightRecommendation instances rather than mutating frozen dataclass fields.
- Grade-to-YAML-key conversion is tested independently.
- The `# type: ignore[arg-type]` on line 79 of the test file (for the `source` field) is acceptable since the test helper creates OutcomeRecords with string literals rather than the Literal type.

## Minor Observations (Non-Blocking)

1. **Threshold proposal delta hardcoded at +/-5:** The `_generate_proposals` method uses a fixed delta of 5 points for threshold proposals (lines 360-363). This is documented as a judgment call in the close-out report. It is reasonable for an advisory-only V1 system but should be revisited if threshold proposals are ever auto-applied.

2. **CLI dry-run silent persistence failures:** As noted in focus item 4, the dry-run mode relies on fire-and-forget exception handling in LearningStore to silently swallow persistence failures. This works but produces warning logs that could confuse operators. A `dry_run` flag on the service would be cleaner.

## Escalation Criteria Check

None of the 11 escalation criteria are triggered:
- No invalid YAML writes (no YAML writing in this session).
- No config reload behavior (not wired in yet).
- No shutdown concerns (not wired in yet).
- No mathematically impossible results observed.

## Verdict

**CLEAR** -- All Definition of Done items verified. All 5 review focus items pass. No regressions. No escalation criteria triggered. The implementation is clean, well-tested (16 new tests, 126 total in module), and correctly scoped.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "session": "Sprint 28, Session 3b",
  "reviewer": "Tier 2 Automated",
  "date": "2026-03-28",
  "tests_passed": 3807,
  "tests_failed": 8,
  "tests_failed_preexisting": true,
  "new_tests": 16,
  "regressions": false,
  "scope_violation": false,
  "escalation_triggered": false,
  "focus_items": {
    "concurrent_guard_try_finally": "PASS",
    "proposal_supersession_before_create": "PASS",
    "config_gated_no_error": "PASS",
    "cli_dry_run_no_persist": "PASS_WITH_NOTE",
    "report_version_set": "PASS"
  },
  "notes": "Dry-run relies on fire-and-forget exception handling for silent no-persist behavior rather than explicit skip. Functional but not the cleanest pattern."
}
```
