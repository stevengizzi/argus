---BEGIN-REVIEW---

# Sprint 25, Session 5a — Tier 2 Review Report

**Session:** Matrix View Core
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-17
**Diff Scope:** Unstaged working-tree changes on `sprint-25` branch (7 files)

## Summary

Session 5a implements the Matrix view -- a full-screen condition heatmap for the
Observatory page. The implementation creates MatrixRow.tsx and MatrixView.tsx,
adds Observatory types and API client function, wires the view into
ObservatoryPage.tsx, and includes 7 new tests (all passing, 38 total observatory
tests passing).

## Review Focus Items

### 1. Cell Color Mapping (green=pass, red=fail, gray=inactive)

**PASS.** The `ConditionCell` component in MatrixRow.tsx (lines 66-70) correctly
maps:
- `actual_value === null` --> gray background (`bg-[var(--color-background-secondary,...)]`)
- `passed === true` --> green (`bg-[#1D9E75]`)
- `passed === false` --> red (`bg-[#E24B4A]`)

This matches the spec precisely. Gray is NOT used for failed conditions -- only
for inactive/not-applicable conditions where `actual_value` is null. Test
coverage confirms this distinction (test at line 84 verifies pass/fail/inactive
independently, and test at line 169 verifies null actual_value produces inactive
data attribute).

### 2. Sort Order (descending by conditions_passed)

**PASS.** MatrixView.tsx line 68-69:
```typescript
const sorted = [...items].sort(
  (a, b) => b.conditions_passed - a.conditions_passed
);
```
Descending sort confirmed. Test at line 142-167 verifies HIGH (3/3) appears
before MID (2/3) before LOW (1/3).

### 3. Strategy Grouping

**PASS.** The `groupByStrategy()` function (lines 40-53) correctly groups items
by strategy field. When `strategyGroups.size > 1`, separate tables render with
sticky strategy header divs (line 110-115). Each strategy group gets its own
`MatrixTable` with its own column headers, which is the right approach since
different strategies may have different condition sets. Test at line 218-244
verifies headers and rows render for two strategies.

### 4. Row Simplicity for S5b Virtualization

**PASS with note.** MatrixRow itself is clean -- props in, JSX out, no internal
state, no side effects. However, the `ConditionCell` sub-component (rendered
inline in the same file) uses `useState` for tooltip hover. This is acceptable
for S5b virtualization because: (a) the state is trivially re-mountable (boolean
only), (b) React handles per-cell state efficiently, and (c) S5b can optimize to
event delegation on the row/table level if needed. No complex internal state or
refs that would interfere with virtual list recycling.

## Additional Findings

### F-1: Inline import in client.ts (LOW)

`getObservatoryClosestMisses()` uses `import('./types').ObservatoryClosestMissesResponse`
inline (lines 727, 732) instead of adding the type to the import block at the
top of the file. Every other function in client.ts uses top-level imports. This
is a minor style inconsistency. The type `ObservatoryClosestMissesResponse` is
not in the import block at line 7-50.

### F-2: Imperative loop in groupByStrategy (LOW)

The `groupByStrategy()` function uses a `for...of` loop with mutation
(`existing.push(item)`). The project CLAUDE.md specifies "Prefer map/reduce/filter
over imperative iteration." This is a minor style point -- the imperative version
is arguably more readable for Map construction, and the function is small.

### F-3: Spec references outdated view key numbering (INFORMATIONAL)

The impl spec says "Register MatrixView as the component for view key `2`" and
"press `2` to switch to Matrix view." The implementation correctly uses `m` key
per the S3 keyboard remap (f/m/r/t). The spec had stale references. No code
issue -- just noting the spec-implementation gap was correctly resolved.

## Regression Checklist Verification

| Check | Result |
|-------|--------|
| No trading pipeline files modified | PASS -- only UI files changed |
| No new Event Bus subscribers | PASS -- frontend only |
| Existing Observatory tests pass | PASS -- 31 pre-existing + 7 new = 38 total |
| TypeScript types well-formed | PASS -- types use proper union types, no `any` |

## Escalation Criteria Check

| Criterion | Triggered? |
|-----------|-----------|
| Three.js < 30fps | N/A (no Three.js in this session) |
| Bundle size > 500KB gzipped | N/A (no build verification needed for this session) |
| Observatory WS degrades Copilot | N/A (no WS changes) |
| Trading pipeline modification | NO -- frontend only |
| Non-Observatory page load increase | N/A (no shared code changes beyond types) |

## Test Results

```
Test Files  4 passed (4)
     Tests  38 passed (38)
```

All 38 observatory tests pass (31 existing + 7 new).

## Verdict

**CLEAR** -- All four review focus items pass. Implementation matches spec.
No escalation criteria triggered. Two low-severity style findings (F-1, F-2)
noted but non-blocking. The session delivers a clean Matrix view implementation
ready for S5b virtualization.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "findings_count": {
    "critical": 0,
    "medium": 0,
    "low": 2,
    "informational": 1
  },
  "escalation_triggered": false,
  "tests_pass": true,
  "test_count": {
    "total": 38,
    "new": 7,
    "existing": 31
  },
  "spec_compliance": "FULL",
  "regression_risk": "NONE",
  "review_focus_results": {
    "cell_color_mapping": "PASS",
    "sort_order_descending": "PASS",
    "strategy_grouping": "PASS",
    "row_simplicity_for_virtualization": "PASS"
  },
  "notes": [
    "F-1: getObservatoryClosestMisses uses inline import() instead of top-level import (style inconsistency)",
    "F-2: groupByStrategy uses imperative for-loop instead of functional pattern",
    "F-3: Impl spec references stale view key numbering (2 vs m); code correctly uses m"
  ]
}
```
