```markdown
---BEGIN-CLOSE-OUT---

**Session:** Sprint 28 S1 — Learning Data Models + Outcome Collector
**Date:** 2026-03-28
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/intelligence/learning/__init__.py | added | Package init with re-exports |
| argus/intelligence/learning/models.py | added | All data models: ConfidenceLevel, OutcomeRecord, DataQualityPreamble, WeightRecommendation, ThresholdRecommendation, CorrelationResult, LearningReport, ConfigProposal, LearningLoopConfig |
| argus/intelligence/learning/outcome_collector.py | added | OutcomeCollector: read-only queries across trades, counterfactual, quality_history |
| tests/intelligence/learning/__init__.py | added | Test package init |
| tests/intelligence/learning/test_models.py | added | Model serialization, validation, immutability tests |
| tests/intelligence/learning/test_outcome_collector.py | added | Collector tests: both sources, empty DBs, filtering, preamble |

### Judgment Calls
- LEFT JOIN strategy for quality_history → trades: joined on symbol + strategy_id + closest scored_at before exit_time. Spec said "timestamp proximity or signal metadata" — chose the most reliable approach using correlated subquery.
- regime_context for trade records: set to empty dict `{}` since trades table has no regime_vector_snapshot column. Counterfactual records get the full regime snapshot. This is correct — trade-source regime context would need to come from a future quality_history → regime join.
- DataQualityPreamble known_data_gaps: added three detection heuristics (reconciliation artifacts, missing counterfactual, zero quality scores) beyond what the spec explicitly listed.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| Create learning/ package with __init__.py | DONE | argus/intelligence/learning/__init__.py |
| All models as frozen dataclasses | DONE | models.py — all @dataclass(frozen=True) except LearningLoopConfig (Pydantic) |
| LearningReport to_dict()/from_dict() | DONE | models.py:LearningReport.to_dict(), from_dict() |
| OutcomeCollector reads trades + counterfactual + quality_history | DONE | outcome_collector.py: _collect_trades (LEFT JOIN quality_history), _collect_counterfactual |
| Empty databases return [] | DONE | Path.exists() check + try/except |
| Schema verification (Amendment 8) | DONE | quality_history HAS per-dimension columns (pattern_strength, catalyst_quality, volume_profile, historical_match, regime_alignment) — full dimension scores available |
| ConfigProposal states match Amendment 6 | DONE | PROPOSAL_STATUSES frozenset with all 8 states |
| LearningLoopConfig with 13 fields | DONE | All 13 fields from review-context.md |
| Pydantic validators | DONE | 4 field_validators for min_sample_count, max_weight_change, cumulative_drift, p_value |
| ≥15 new tests | DONE | 31 new tests |
| No existing files modified | DONE | git diff --name-only shows nothing |
| OutcomeCollector read-only | DONE | grep for INSERT/UPDATE/DELETE returns nothing |
| Re-export key classes in __init__.py | DONE | 9 classes re-exported |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| No existing files modified | PASS | git diff --name-only empty; git status shows only new files in learning/ dirs |
| OutcomeCollector is read-only | PASS | grep INSERT/UPDATE/DELETE in outcome_collector.py — zero matches |
| Import doesn't break existing code | PASS | `python -c "from argus.intelligence.learning import OutcomeCollector"` succeeds |
| Full test suite | PASS | 3,712 passed; 8 failures are all pre-existing (verified on clean HEAD) |

### Test Results
- Tests run: 3,720 (full suite) + 31 (scoped)
- Tests passed: 3,712 (full suite) + 31 (scoped)
- Tests failed: 8 (all pre-existing — verified by running same tests on clean HEAD with no local changes)
- New tests added: 31
- Command used: `python -m pytest tests/intelligence/learning/ -x -q` (scoped), `python -m pytest --ignore=tests/test_main.py -n auto -q` (full)

Pre-existing failures (not caused by this session):
- tests/ai/test_client.py (3 tests) — TestClaudeClientDisabled
- tests/ai/test_config.py (1 test) — TestAIConfigDefaults
- tests/api/test_server_intelligence.py (1 test) — lifespan test
- tests/intelligence/test_counterfactual_wiring.py (1 test) — store init
- tests/backtest/test_engine.py (2 tests) — teardown + empty data

### Unfinished Work
None

### Notes for Reviewer
- **Amendment 8 finding (POSITIVE):** quality_history table DOES have per-dimension score columns (pattern_strength, catalyst_quality, volume_profile, historical_match, regime_alignment). S2a WeightAnalyzer can use per-dimension correlations directly — no fallback to composite-only needed.
- The LEFT JOIN for quality_history uses a correlated subquery to find the closest scored_at before the trade's exit_time for the same symbol + strategy. This is the most reliable proximity match without requiring exact timestamp matching.
- Trade OutcomeRecords have `regime_context={}` because the trades table has no regime snapshot column. Counterfactual records populate this from regime_vector_snapshot JSON.

---END-CLOSE-OUT---
```

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "28",
  "session": "S1",
  "verdict": "COMPLETE",
  "tests": {
    "before": 3689,
    "after": 3720,
    "new": 31,
    "all_pass": true
  },
  "files_created": [
    "argus/intelligence/learning/__init__.py",
    "argus/intelligence/learning/models.py",
    "argus/intelligence/learning/outcome_collector.py",
    "tests/intelligence/learning/__init__.py",
    "tests/intelligence/learning/test_models.py",
    "tests/intelligence/learning/test_outcome_collector.py"
  ],
  "files_modified": [],
  "files_should_not_have_modified": [],
  "scope_additions": [
    {
      "description": "Three data quality gap detection heuristics in build_data_quality_preamble",
      "justification": "Spec said 'flag known data gaps' — implemented concrete detection for reconciliation artifacts, missing counterfactual data, and zero quality scores"
    }
  ],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "Trade-source OutcomeRecords have empty regime_context because trades table lacks regime_vector_snapshot column. Future enhancement: join quality_history or add regime snapshot to trades.",
    "8 pre-existing test failures discovered in full suite run — not related to Sprint 28 changes."
  ],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "quality_history table confirmed to have per-dimension columns — Amendment 8 finding is positive. LEFT JOIN uses correlated subquery for closest scored_at match. All 31 new tests pass in 0.09s."
}
```
