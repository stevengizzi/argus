---BEGIN-REVIEW---

# Tier 2 Review: Sprint 28, Session S6cf-1

**Reviewer:** Automated Tier 2
**Session:** S6cf-1 (Batch Findings + Visual Review Fixes)
**Date:** 2026-03-29
**Spec:** `docs/sprints/sprint-28/sprint-28-session-s6cf-1-impl.md`
**Close-out:** `docs/sprints/sprint-28/session-6cf-1-closeout.md`

---

## 1. Spec Compliance

All 14 Definition of Done items were completed as specified.

| DoD Item | Verdict | Notes |
|----------|---------|-------|
| A1: Unused `import json` removed from models.py | PASS | Also removed unused `field` import (not in spec, justified in close-out) |
| A2: `import yaml` in correct position in quality_engine.py | PASS | Moved to stdlib/third-party section, before local imports |
| A3: All 5 `assert` replacements | PASS | 2 in config_proposal_manager.py (ValueError), 3 in learning.py (HTTPException 500) |
| A4: Test assumption documented | PASS | Comment added at line 322 |
| A5: Stale current_value behavior documented | PASS | 3-line comment added at line 168 |
| B1: pairKey delimiter fix | PASS | `:` changed to `|` matching backend serialization |
| C1: shortenName + label dimensions | PASS | Strips `strat_` prefix, labelWidth=120, labelHeight=80 |
| C2: Conflicting threshold combined card | PASS | proposalsByFieldMulti, conflict detection, amber badge, both Approve buttons |
| C2: No duplicate React keys | PASS | Keys are `conflict-{grade}` and `{grade}-{direction}` |
| C3: Empty weight recommendations placeholder | PASS | Shows header + descriptive message when weight_recommendations empty |
| C4: Strategy Health context-aware empty state | PASS | Ternary distinguishes no-report vs no-data |
| Tests pass (133 pytest) | PASS | 133 passed |
| Tests pass (680 Vitest) | PASS | 680 passed |
| Close-out report | PASS | Complete and accurate |

## 2. Session-Specific Review Focus Items

### Focus 1: pairKey uses `|` delimiter
**PASS.** Line 41 of CorrelationMatrix.tsx now returns `` `${a}|${b}` `` matching the backend `f"{k[0]}|{k[1]}"` serialization in models.py line 199. Matrix cells will now resolve to actual correlation values instead of all falling through to dark grey.

### Focus 2: All 5 assert replacements use correct exception types
**PASS.** The two replacements in config_proposal_manager.py (lines 105-106 and 258-259) raise `ValueError`, appropriate for data validation. The three replacements in learning.py (lines 285-286, 336-337, 399-400) raise `HTTPException(status_code=500)`, appropriate for unexpected server-side failures in API routes.

### Focus 3: Correlation matrix labels fully readable
**PASS.** `shortenName` now strips `strat_` prefix (the actual ID pattern) instead of `_strategy` suffix (wrong pattern). labelWidth increased from 80 to 120, labelHeight from 60 to 80. Longest resulting label "Afternoon Momentum" (18 chars) should fit within 120px at font-size 9.

### Focus 4: Conflicting threshold card shows both Approve buttons with correct proposal IDs
**PASS.** Lines 427-441 render "Approve Lower" and "Approve Raise" buttons. Each calls `handleApprove(lowerProposal.proposal_id)` and `handleApprove(raiseProposal.proposal_id)` respectively. The proposals are matched via `proposalsByFieldMulti` using `proposed_value < current_value` (lower) and `proposed_value > current_value` (raise).

### Focus 5: "Dismiss Both" calls handleDismiss for both proposals
**PASS.** Lines 446-451: the onClick handler calls `handleDismiss(lowerProposal.proposal_id)` then `handleDismiss(raiseProposal.proposal_id)`, each guarded by null checks.

### Focus 6: Empty weight placeholder appears only when report exists but recommendations are empty
**PASS.** The empty weight placeholder (lines 347-358) is inside the main content section, which only renders after the `!activeReport` early return at line 201. Therefore it can only appear when a report exists and `weight_recommendations.length === 0`.

### Focus 7: ruff check on modified Python files -- zero new warnings
**PASS.** Ruff reports exactly 3 warnings, all pre-existing: 2x B904 in learning.py (pre-existing `raise HTTPException` without `from` in except blocks at lines 139 and 390) and 1x F841 in config_proposal_manager.py (pre-existing unused `old_value` at line 186). Zero new warnings introduced by this session.

### Focus 8: No duplicate React keys in threshold section
**PASS.** Normal threshold cards use `key={rec.grade}-{rec.recommended_direction}` (unique per direction). Conflicting cards use `key={conflict-{grade}}` (unique per grade). No overlap possible between the two key namespaces.

## 3. Regression Checklist (Sprint-Level)

| Check | Status |
|-------|--------|
| quality_engine.yaml weights sum to 1.0 | NOT AFFECTED (no config changes) |
| Config safety / Pydantic validation | NOT AFFECTED (assert replacements preserve behavior) |
| Existing API endpoints | NOT AFFECTED (only assert→raise in existing endpoints) |
| Frontend existing content | NOT AFFECTED (only additive changes to Learning components) |
| Test suite passes | PASS (133 learning pytest, 680 Vitest) |

## 4. Escalation Criteria Check

No escalation criteria triggered. This session made no changes to:
- ConfigProposalManager write logic (only assert replacements and comments)
- Analysis computation logic
- Shutdown behavior
- Data access patterns

## 5. Findings

### F1 (Informational): Changes not committed
The close-out report is written but all changes remain unstaged/uncommitted in the working tree. The close-out report references itself as complete, but there is no git commit yet. This is typical for sessions where the reviewer is invoked before the final commit.

### F2 (Informational): Remaining assert statements in models.py `from_dict()`
`models.py` contains ~8 `assert` statements in its `from_dict()` classmethod (lines 222-260). These were NOT in scope for this session (spec only targeted config_proposal_manager.py and learning.py), but they represent the same pattern (assert in non-test production code). Worth noting for a future cleanup pass.

### F3 (Informational): pendingCount semantics changed slightly
The `pendingCount` calculation changed from `weight_recommendations.length + threshold_recommendations.length` to `weight_recommendations.length + normalThresholds.length + conflictingThresholds.length`. For conflicting scenarios (2 threshold recs for the same grade), each conflict group counts as 1 instead of 2. This is a reasonable change matching the visual representation (1 combined card per conflict), but the semantic shift is worth noting.

### F4 (Informational): Unused `raiseRec` destructured variable
In `LearningInsightsPanel.tsx` line 388, the conflicting threshold map destructures `raise: raiseRec` but `raiseRec` is never used in the template. The `raise` property (aliased because `raise` is not a valid JS identifier for destructuring) is only accessed through its child properties in the destructured `lowerProposal`/`raiseProposal`. The `raiseRec` alias is harmless but unused. Not a functional issue.

## 6. Close-Out Report Accuracy

The close-out report is accurate:
- Change manifest matches the actual diff (8 files, correct descriptions)
- Judgment calls are reasonable (removing `field` import to avoid lint warning)
- Scope verification matches actual implementation
- Test counts confirmed (133 pytest, 14 API pytest, 680 Vitest)
- Self-assessment of CLEAN is appropriate
- Context state GREEN is accurate

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "summary": "All 14 Definition of Done items completed exactly as specified. The critical B1 delimiter fix restores correlation matrix functionality. All 5 assert replacements use correct exception types. Frontend conflict card logic is correctly wired with unique React keys. Tests pass (133 pytest, 680 Vitest). Ruff reports zero new warnings. No escalation criteria triggered.",
  "findings": [
    {
      "id": "F1",
      "severity": "informational",
      "description": "Changes not yet committed to git -- unstaged in working tree",
      "recommendation": "Commit with standard session commit message before next session"
    },
    {
      "id": "F2",
      "severity": "informational",
      "description": "models.py from_dict() contains ~8 assert statements (same pattern as fixed ones, but out of scope)",
      "recommendation": "Consider addressing in a future cleanup pass"
    },
    {
      "id": "F3",
      "severity": "informational",
      "description": "pendingCount semantics changed: conflicting threshold groups count as 1 instead of 2",
      "recommendation": "No action needed -- matches visual representation"
    },
    {
      "id": "F4",
      "severity": "informational",
      "description": "Unused raiseRec destructured variable in LearningInsightsPanel.tsx line 388",
      "recommendation": "Harmless; can remove the alias in a future cleanup"
    }
  ],
  "tests_passed": true,
  "test_counts": {
    "learning_pytest": 133,
    "vitest": 680,
    "ruff_new_warnings": 0
  },
  "escalation_triggers": [],
  "close_out_accurate": true,
  "spec_compliance": "full"
}
```
