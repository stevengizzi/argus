---BEGIN-REVIEW---

**Reviewing:** [Sprint 28, Session 6c] — Strategy Health Bands + Correlation Matrix + Dashboard Card
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-28
**Verdict:** CONCERNS

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | All 5 spec requirements implemented. 3 new components, 2 page modifications. |
| Close-Out Accuracy | PASS | Change manifest matches actual diff. Test count accurate (680). Self-assessment CLEAN is mostly justified. |
| Test Health | PASS | Vitest: 100 files, 680 passed, 0 failed. Pytest: 3828 passed, 8 failed (all pre-existing). 10 new Vitest tests (exceeds 6 minimum). |
| Regression Checklist | PASS | Frontend regression items verified: existing Performance content unaffected, Learning components render empty states gracefully, Dashboard card returns null when disabled. |
| Architectural Compliance | PASS | Follows existing patterns: Card/CardHeader usage, TanStack Query hooks, motion.div stagger animations, responsive breakpoint layouts. Import alias avoids CorrelationMatrix name collision. |
| Escalation Criteria | NONE_TRIGGERED | No escalation criteria apply to this frontend-only session. |

### Findings

**[MEDIUM] CorrelationMatrix tooltip missing trade overlap count (spec deviation)**
File: `argus/ui/src/components/learning/CorrelationMatrix.tsx`, lines 276-298
The spec requires "Tooltip: exact correlation value, trade overlap count." The tooltip shows correlation value and flagged status but omits trade overlap count. The `CorrelationResult` API type lacks a trade overlap field, so the data is not available from the backend. This is a data availability limitation rather than an implementation oversight, but it is a spec deviation that should be documented.
Recommendation: Either add `trade_overlap_count` to the backend `CorrelationResult` model and API response in a future session, or formally defer this requirement.

**[LOW] StrategyHealthBands data extraction is a placeholder heuristic**
File: `argus/ui/src/components/learning/StrategyHealthBands.tsx`, lines 70-101
The `extractStrategyMetrics` function maps `correlation_trade_source` to the Sharpe metric and leaves winRate and expectancy as null. The spec calls for "trailing Sharpe, win rate, expectancy" per strategy. The close-out documents this as judgment call #2, noting it will produce meaningful bars once real analysis data flows. The component will render bars for Sharpe only; winRate and expectancy will show "--" and zero-width bars. This is acceptable for V1 but worth noting as the health bands will appear incomplete until the backend provides per-strategy metric breakdowns.

**[LOW] Dashboard grid layout change affects existing card widths**
File: `argus/ui/src/pages/DashboardPage.tsx`, line 246
The desktop "below fold" grid changed from `grid-cols-2` to `grid-cols-3` to accommodate the new LearningDashboardCard. This changes the visual width of UniverseStatusCard and SignalQualityPanel from 50% to 33% of the container. The spec says "Do NOT modify existing Dashboard cards or Performance tab content." The cards themselves are not modified, but their layout context is. This is a reasonable accommodation and does not modify card internals, but it is worth noting as a minor visual change to existing content.

**[INFO] Pre-existing pytest failures (8 tests)**
8 pytest failures confirmed pre-existing on clean HEAD (stash test). All are in `tests/ai/`, `tests/api/`, `tests/backtest/`, and `tests/intelligence/` -- unrelated to S6c frontend changes.

### Recommendation
CONCERNS: Two medium/low findings that do not block progress but should be documented. The missing tooltip trade overlap count is a minor spec deviation bounded by backend data availability. The health bands placeholder heuristic will need revisiting when the backend provides per-strategy metric breakdowns. Neither issue affects production behavior or introduces regressions. Proceed to sprint close-out.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "28",
  "session": "6c",
  "verdict": "CONCERNS",
  "findings": [
    {
      "description": "CorrelationMatrix tooltip missing trade overlap count specified in the implementation spec. Backend CorrelationResult type lacks this field.",
      "severity": "MEDIUM",
      "category": "SPEC_VIOLATION",
      "file": "argus/ui/src/components/learning/CorrelationMatrix.tsx",
      "recommendation": "Add trade_overlap_count to CorrelationResult backend model, or formally defer this spec requirement."
    },
    {
      "description": "StrategyHealthBands extractStrategyMetrics uses correlation_trade_source as Sharpe proxy; winRate and expectancy remain null. Bars will appear incomplete until backend provides per-strategy metric breakdowns.",
      "severity": "LOW",
      "category": "OTHER",
      "file": "argus/ui/src/components/learning/StrategyHealthBands.tsx",
      "recommendation": "Track as known limitation. Revisit when LearningReport includes per-strategy Sharpe/winRate/expectancy fields."
    },
    {
      "description": "Desktop Dashboard grid changed from grid-cols-2 to grid-cols-3, reducing visual width of existing UniverseStatusCard and SignalQualityPanel.",
      "severity": "LOW",
      "category": "SCOPE_BOUNDARY_VIOLATION",
      "file": "argus/ui/src/pages/DashboardPage.tsx",
      "recommendation": "Acceptable accommodation for new card. No action needed unless visual regression reported."
    },
    {
      "description": "8 pre-existing pytest failures confirmed on clean HEAD. Unrelated to S6c changes.",
      "severity": "INFO",
      "category": "OTHER",
      "file": "",
      "recommendation": "No action for this session. Pre-existing failures tracked in DEF items."
    }
  ],
  "spec_conformance": {
    "status": "MINOR_DEVIATION",
    "notes": "Tooltip trade overlap count missing (data not available from backend). Health bands show only Sharpe proxy, not full Sharpe/winRate/expectancy.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/ui/src/components/learning/StrategyHealthBands.tsx",
    "argus/ui/src/components/learning/CorrelationMatrix.tsx",
    "argus/ui/src/components/learning/LearningDashboardCard.tsx",
    "argus/ui/src/components/learning/StrategyHealthBands.test.tsx",
    "argus/ui/src/components/learning/CorrelationMatrix.test.tsx",
    "argus/ui/src/components/learning/LearningDashboardCard.test.tsx",
    "argus/ui/src/pages/PerformancePage.tsx",
    "argus/ui/src/pages/DashboardPage.tsx",
    "argus/ui/src/api/learningApi.ts"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 680,
    "new_tests_adequate": true,
    "test_quality_notes": "10 new Vitest tests across 3 files. Tests cover empty states, mock data rendering, disabled state (returns null), flagged pairs, and navigation link. Meaningful coverage of the three new components."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "Performance page existing content renders with Learning sections", "passed": true, "notes": "Only new imports/components added below LearningInsightsPanel"},
      {"check": "Dashboard existing cards unaffected by Learning card", "passed": true, "notes": "Card internals unchanged; grid-cols-2 to grid-cols-3 changes layout context"},
      {"check": "Learning UI graceful when disabled", "passed": true, "notes": "LearningDashboardCard returns null when enabled=false; tested"},
      {"check": "Learning UI graceful when no reports", "passed": true, "notes": "All 3 components have empty states; tested"},
      {"check": "Full Vitest suite passes", "passed": true, "notes": "100 files, 680 tests, 0 failures"},
      {"check": "Full pytest suite passes", "passed": true, "notes": "3828 passed, 8 failed (all pre-existing on clean HEAD)"},
      {"check": "No test hangs", "passed": true, "notes": "Both suites completed within normal timeouts"}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Document missing tooltip trade overlap count as a known limitation or deferred item",
    "Track health bands data completeness for future backend enhancement"
  ]
}
```
