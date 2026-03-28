# Tier 2 Review: Sprint 28, Session 1 — Learning Data Models + Outcome Collector

---BEGIN-REVIEW---

## Review Summary

**Session:** Sprint 28, Session 1
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-28
**Verdict:** CLEAR

## Scope Verification

All 6 new files created per spec:
- `argus/intelligence/learning/__init__.py`
- `argus/intelligence/learning/models.py`
- `argus/intelligence/learning/outcome_collector.py`
- `tests/intelligence/learning/__init__.py`
- `tests/intelligence/learning/test_models.py`
- `tests/intelligence/learning/test_outcome_collector.py`

No existing tracked files modified (confirmed via `git diff HEAD --name-only` returning empty for `argus/` and `tests/`).

## Test Results

- **Scoped tests:** 31 passed in 0.06s (`python -m pytest tests/intelligence/learning/ -x -q`)
- **Spec minimum:** 15 tests required -- 31 delivered (2x target)
- **Import check:** `from argus.intelligence.learning import OutcomeCollector` succeeds

## Session-Specific Review Focus

### 1. OutcomeCollector queries are read-only
**PASS.** Grep for INSERT/UPDATE/DELETE in `outcome_collector.py` returned zero matches. All SQL statements are SELECT queries with parameterized WHERE clauses. The class does not open any database connections in write mode.

### 2. LearningReport.to_dict()/from_dict() round-trips correctly
**PASS.** Verified independently via Python: constructed a full LearningReport with all nested types (WeightRecommendation, ThresholdRecommendation, CorrelationResult with tuple keys), serialized to dict, passed through `json.dumps`/`json.loads` (simulating real persistence), then deserialized via `from_dict()`. All fields match including correlation_matrix tuple keys (`"orb|vwap"` string key -> `("orb","vwap")` tuple key) and datetime round-trips.

### 3. LearningLoopConfig Pydantic validators reject invalid values
**PASS.** Tests cover:
- `min_sample_count < 5` rejected
- `max_weight_change_per_cycle = 0.0` rejected
- `max_weight_change_per_cycle > 0.50` rejected
- `max_cumulative_drift < 0.05` rejected
- `correlation_p_value_threshold > 0.20` rejected
- Boundary values (exact minimums) accepted

Note: The `field_validator` methods duplicate the `ge`/`le` constraints already on the `Field()` definitions. This is redundant but not harmful -- it provides explicit error messages.

### 4. OutcomeRecord.source field correctly set
**PASS.** Trade records are constructed with `source="trade"` in `_collect_trades()` (line 237). Counterfactual records are constructed with `source="counterfactual"` in `_collect_counterfactual()` (line 329). Tests verify both paths explicitly (`test_collect_trades`, `test_collect_counterfactual`, `test_combined_collection`).

### 5. quality_history schema finding documented (Amendment 8)
**PASS.** The close-out documents the finding clearly under "Notes for Reviewer": quality_history table HAS per-dimension columns (pattern_strength, catalyst_quality, volume_profile, historical_match, regime_alignment). The implementation uses these columns in the LEFT JOIN query. The close-out also notes the positive implication for S2a (WeightAnalyzer).

### 6. ConfigProposal state machine values match Amendment 6
**PASS.** `PROPOSAL_STATUSES` frozenset contains all 8 required values: PENDING, APPROVED, DISMISSED, SUPERSEDED, REJECTED_GUARD, REJECTED_VALIDATION, APPLIED, REVERTED. Test `test_all_statuses_defined` asserts exact equality with the expected set.

## Sprint-Level Regression Checklist (Session-Applicable Items)

| Check | Result |
|-------|--------|
| OutcomeCollector queries are read-only | PASS |
| No existing files modified | PASS |
| All 13 learning_loop.* YAML keys recognized by Pydantic model | PASS (verified: 13 fields, names match review-context.md exactly) |

## Findings

### Minor (Non-Blocking)

1. **Unused import in models.py:** `import json` on line 12 is never used within `models.py`. JSON parsing is only done in `outcome_collector.py`. No functional impact.

2. **Reconciliation gap detection heuristic is unreachable for trade records:** In `build_data_quality_preamble()` (lines 106-114), the reconciliation artifact check looks at `r.rejection_reason` on trade-sourced OutcomeRecords. However, trade records are always constructed with `rejection_reason=None` (the default). To detect reconciliation trades, the heuristic would need to check the trade's exit_reason (e.g., `ExitReason.RECONCILIATION`) which is not currently carried into OutcomeRecord. The heuristic is dead code for the trade source. Counterfactual records could match if their rejection_reason contained "reconciliation", but that is also unlikely given the current rejection pipeline. Not harmful -- just inert.

3. **Redundant Pydantic validators:** All four `@field_validator` methods repeat constraints already expressed via `Field(ge=..., le=...)`. The validators add explicit error messages, which is marginally useful, but the duplication could cause maintenance confusion if someone updates one but not the other. Low priority.

## Escalation Criteria Check

| Criterion | Triggered? |
|-----------|-----------|
| ConfigProposalManager writes invalid YAML | N/A (not in scope) |
| Config application causes scoring regression | N/A (not in scope) |
| Auto trigger blocks/delays shutdown | N/A (not in scope) |
| Mathematically impossible results | N/A (not in scope) |
| OutcomeCollector returns mismatched data | No -- source fields correctly set, data types match |
| LearningStore fails to persist | N/A (not in scope) |
| Config change history gaps | N/A (not in scope) |
| Frontend mutations don't update UI | N/A (not in scope) |

No escalation criteria triggered.

## Assessment

Clean implementation that meets all spec requirements. All 6 files are new (no modifications to existing code). Models are correctly frozen. Serialization round-trips work through JSON. Config validation rejects invalid values at boundaries. OutcomeCollector is strictly read-only. The quality_history schema finding is properly documented. 31 tests provide thorough coverage of both happy paths and edge cases (empty DBs, missing files, filtering, data quality gap detection). The three minor findings are cosmetic and do not affect correctness or safety.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "28",
  "session": "S1",
  "verdict": "CLEAR",
  "findings": [
    {
      "severity": "minor",
      "category": "code-hygiene",
      "description": "Unused `import json` in models.py",
      "file": "argus/intelligence/learning/models.py",
      "line": 12,
      "recommendation": "Remove unused import"
    },
    {
      "severity": "minor",
      "category": "correctness",
      "description": "Reconciliation gap detection heuristic in build_data_quality_preamble() checks rejection_reason on trade records, but trade records always have rejection_reason=None. The heuristic is unreachable dead code for trade-sourced records.",
      "file": "argus/intelligence/learning/outcome_collector.py",
      "line": 106,
      "recommendation": "Consider checking exit_reason (not currently in OutcomeRecord) or remove the heuristic for trade records"
    },
    {
      "severity": "minor",
      "category": "code-hygiene",
      "description": "Four field_validator methods duplicate constraints already expressed via Field(ge=, le=)",
      "file": "argus/intelligence/learning/models.py",
      "line": 348,
      "recommendation": "Keep Field constraints OR validators, not both"
    }
  ],
  "escalation_triggers": [],
  "tests": {
    "scoped_pass": 31,
    "scoped_fail": 0,
    "command": "python -m pytest tests/intelligence/learning/ -x -q"
  },
  "regression_checklist": {
    "outcome_collector_read_only": "PASS",
    "no_existing_files_modified": "PASS",
    "all_13_yaml_keys_recognized": "PASS"
  }
}
```
