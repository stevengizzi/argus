---BEGIN-REVIEW---
```markdown
# Tier 2 Review — FIX-09-backtest-engine

- **Reviewing:** `audit-2026-04-21-phase-3` — FIX-09-backtest-engine (Sprint 31.9, Stage 7 solo)
- **Reviewer:** Tier 2 Automated Review (fresh read-only subagent)
- **Date:** 2026-04-22
- **Verdict:** `CLEAR`
- **Commit reviewed:** `f639a98` (diff range `449b7df..f639a98`)
- **Campaign HEAD at session start:** `449b7df`

## Assessment Summary

| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | **PASS** | Exactly the 22 files in the close-out manifest (15 M + 6 D + 1 A); 2 scope expansions (`test_walk_forward.py` + `test_runtime_wiring.py`) pre-documented and tightly coupled to in-scope deletions. No Rule-4 file touched. |
| Close-Out Accuracy | **PASS** | Manifest matches `git diff HEAD~1 --name-status` exactly. Test delta 5,035 → 4,979 (−56) matches the Hazard-9-sanctioned accounting (−36 vectorbt_pattern, −13 vectorbt_red_to_green, −14 report_generator, +7 FIX-09 regression tests). MINOR_DEVIATIONS self-rating is justified by the per-file-summary-header back-annotation format and the two documented expansions — neither is an ESCALATE trigger. |
| Test Health | **PASS** | Second-run: 4,979 passed + 1 failed (DEF-163 `test_get_todays_pnl_excludes_unrecoverable`, as expected inside the 20:00–24:00 ET window; reviewer wall-clock was 22:13 ET 2026-04-22, inside the window). Vitest: 859 passed / 0 failed. New tests are meaningful: `TestEventBusProtocolConformance`, `test_load_data_drops_holiday_dates`, `test_itertuples_parity_against_iterrows`, plus 2 in `test_engine.py` covering the dot-path fix. |
| Regression Checklist | **PASS** | All 8 campaign-level checks pass. `EventBusProtocol` exported from `argus/core/protocols.py` (line 56 + `__all__` at 107); `_apply_config_overrides` emits WARNING on unresolvable dot-path and no longer has flat-key fallback (`engine.py:1644-1650`); bar dispatch uses `itertuples(index=False)` at `engine.py:640`; walk_forward.py has zero executable R2G code (only one comment mention at line 127); CLAUDE.md `python -m argus.backtest.report_generator` line removed; DEF-186 + DEF-187 present in the DEF table; `tests/test_runtime_wiring.py` imports from `argus.strategies.patterns.factory`, not from deleted `argus.backtest.vectorbt_pattern`. |
| Architectural Compliance | **PASS** | Protocol pattern matches FIX-07 precedent; fire-and-forget WARNING log on dot-path no-op matches project pattern; NYSE holiday filter aligns with `core/market_calendar.py`; operator approval for F23 documented per universal RULE-005. |
| Escalation Criteria | **NONE_TRIGGERED** | No CRITICAL findings; net delta exactly −56 (expected); no Rule-4 violations; two documented scope expansions are sanctioned; operator approval evidence present; DEF-163 is the only persistent failure and it matches the expected window. |

## Findings

### LOW — transient pyarrow/xdist race surfaced on first review run (INFO severity)
The first full-suite run after checkout produced 3 failures: the expected DEF-163 plus `tests/test_integration_sprint3.py::test_full_pipeline_scanner_to_signal` and `::test_full_pipeline_with_risk_manager`, both on `gw5`, both with `pyarrow.lib.ArrowKeyError: A type extension with name pandas.period already defined`. Re-running the full suite produced the expected 4,979 passed + 1 DEF-163 failure. Both failing tests pass in isolation. Root cause is a concurrent `register_extension_type` call on a single xdist worker during pyarrow/pandas import — a known class of xdist flake (family: DEF-048, DEF-171) and not a code regression. FIX-09 did not introduce pyarrow imports or change test startup ordering, so the flake is attributable to the existing xdist/pyarrow-init race, not this session's code. Worth noting alongside DEF-150/163/171 in the FIX-13 batch but is not an ESCALATE trigger.

### INFO — P1-E1-L03 hardcoded fallback retained for empty-trade case
The `_weighted_avg_entry_price` helper replaces the literal `50.0` with a volume-weighted average, but retains `$50` as a fallback when the trade log is empty for the filtered subset (documented in the audit back-annotation). This is a reasonable and well-scoped retention — flagged for visibility, not a concern.

### INFO — DEF-186 remainder (partial L5 + F3 + F4)
Three `# type: ignore[arg-type]` comments remain in `engine.py` at lines 401, 408 (RiskManager + OrderManager constructor sites) because those classes haven't been retyped against `EventBusProtocol`. Consolidated into DEF-186 as documented. Not a regression — the FIX-09 spec explicitly scoped only `BacktestDataService.__init__` for the retype.

### INFO — audit back-annotation format
Spec templates in the audit-remediation campaign typically use per-row strikethrough to mark `RESOLVED` findings. FIX-09 used a per-file summary header at the top of each audit file instead. Close-out explicitly notes this as MINOR_DEVIATIONS. Both formats preserve audit history and both are machine-parseable by a future doc-sync pass; the deviation is presentational.

## Recommendation

Proceed to the next session. All 27 in-scope findings are resolved or documented. 4,979 passed + 1 expected DEF-163 failure (timezone window) matches the Hazard-9-sanctioned delta exactly. Operator approval for `report_generator` deletion is captured in both the commit body and the audit back-annotation. The two remainders (DEF-186, DEF-187) are correctly catalogued with clear cross-references and owners.

Minor follow-up suggestion for the Sprint 31.9 seal: consider adding the observed pyarrow xdist race to DEF-171's cluster note (or opening a new DEF-188 if the xdist-pytest audit prefers a separate entry). This is housekeeping, not a FIX-09 deliverable.

```

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "audit-2026-04-21",
  "session": "FIX-09-backtest-engine",
  "verdict": "CLEAR",
  "findings": [
    {
      "description": "First-run pyarrow/xdist race produced 2 transient failures in tests/test_integration_sprint3.py on gw5 (pyarrow.lib.ArrowKeyError 'pandas.period already defined'). Second full-suite run produced exactly the expected 4,979 passed + 1 DEF-163. Both tests pass in isolation. Attributable to the existing xdist/pyarrow-init race (same family as DEF-048/DEF-171), not FIX-09 code changes.",
      "severity": "LOW",
      "category": "TEST_COVERAGE_GAP",
      "file": "tests/test_integration_sprint3.py",
      "recommendation": "Note alongside DEF-150/163/171 in the FIX-13 xdist-flake batch; consider a new DEF-188 entry if the next audit seal prefers per-race tracking. Not a FIX-09 deliverable."
    },
    {
      "description": "Audit back-annotation uses per-file summary header instead of per-row strikethrough used by other FIX-NN sessions in this campaign. Close-out self-flagged this as MINOR_DEVIATIONS.",
      "severity": "INFO",
      "category": "OTHER",
      "file": "docs/audits/audit-2026-04-21/p1-e1-backtest-engine.md",
      "recommendation": "Acceptable format deviation; both formats preserve audit history. No action required."
    },
    {
      "description": "DEF-186 correctly documents the three remaining F20/F3/F4 reach-in sites (RiskManager/OrderManager event_bus type: ignore + SimulatedBroker._pending_brackets + PatternBasedStrategy._pattern). Partial resolution is sanctioned by the spec.",
      "severity": "INFO",
      "category": "ARCHITECTURE",
      "file": "argus/backtest/engine.py",
      "recommendation": "Resolve in the next execution-layer or backtest cleanup session per DEF-186."
    }
  ],
  "spec_conformance": {
    "status": "MINOR_DEVIATION",
    "notes": "27 in-scope findings resolved. Two pre-documented scope expansions (test_walk_forward.py patch-target + test_runtime_wiring.py factory migration) are tight consequences of in-scope deletions. Audit back-annotation uses a per-file summary header rather than per-row strikethrough — the format difference is presentational, and both formats preserve audit history.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/backtest/engine.py",
    "argus/backtest/walk_forward.py",
    "argus/backtest/scanner_simulator.py",
    "argus/backtest/backtest_data_service.py",
    "argus/core/protocols.py",
    "tests/backtest/test_fix09_audit.py",
    "tests/backtest/test_engine.py",
    "tests/backtest/test_walk_forward.py",
    "tests/backtest/test_walk_forward_engine.py",
    "tests/test_runtime_wiring.py",
    "CLAUDE.md",
    "docs/audits/audit-2026-04-21/p1-e1-backtest-engine.md",
    "docs/audits/audit-2026-04-21/p1-e2-backtest-legacy.md",
    "docs/audits/audit-2026-04-21/p1-g1-test-coverage.md",
    "docs/audits/audit-2026-04-21/p1-g2-test-quality.md"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 4979,
    "new_tests_adequate": true,
    "test_quality_notes": "tests/backtest/test_fix09_audit.py adds EventBusProtocol conformance (3 tests), holiday filter regression (1 test), itertuples vs iterrows parity (1 test). tests/backtest/test_engine.py adds 2 tests for the dot-path fix. Total +7 meaningful regression tests. DEF-163 is the only persistent failure and is expected inside the 20:00-24:00 ET window (reviewer wall-clock was 22:13 ET). Second-run confirms Hazard-9-sanctioned -56 delta. Vitest 859/859 pass."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "Deleted files absent (3 prod + 3 test = 6 deletions)", "passed": true, "notes": "Confirmed via ls: vectorbt_pattern.py, vectorbt_red_to_green.py, report_generator.py + their test modules all absent."},
      {"check": "tests/backtest/test_fix09_audit.py exists with required coverage", "passed": true, "notes": "EventBusProtocol conformance (3 tests), holiday filter (1 test), itertuples parity (1 test) all present."},
      {"check": "argus/core/protocols.py exports EventBusProtocol", "passed": true, "notes": "Line 56 class definition + line 107 __all__ export."},
      {"check": "_apply_config_overrides no flat-key fallback + WARNING log", "passed": true, "notes": "engine.py:1644-1650 confirmed; comment 'Do NOT fall back to a flat key' explicit."},
      {"check": "_run_trading_day uses itertuples(index=False)", "passed": true, "notes": "engine.py:640 confirmed."},
      {"check": "walk_forward.py has no executable R2G code", "passed": true, "notes": "Grep for R2GSweepConfig/run_r2g_sweep/_optimize_in_sample_r2g/_validate_oos_r2g/r2g_ returns nothing executable; line 127 is a harmless comment."},
      {"check": "CLAUDE.md lacks report_generator command + has DEF-186/187", "passed": true, "notes": "git diff confirms command removal; DEF-186 + DEF-187 rows present at lines 413-414."},
      {"check": "tests/test_runtime_wiring.py uses factory instead of vectorbt_pattern", "passed": true, "notes": "Imports build_pattern_from_config from argus.strategies.patterns.factory; remaining vectorbt_pattern mentions are historical comments documenting the migration."}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Proceed to next session in the audit-2026-04-21 Phase 3 remediation campaign.",
    "Consider adding the observed pyarrow/xdist race to DEF-171's cluster note or opening DEF-188 during the Sprint 31.9 seal; not blocking.",
    "DEF-186 + DEF-187 cleanly catalogued — carry forward per their triggers (next execution-layer cleanup session / Sprint 33+ validation-tooling sprint)."
  ]
}
```
---END-REVIEW---
