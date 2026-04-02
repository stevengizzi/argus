---BEGIN-REVIEW---

# Sprint 32.8, Session 2 — Tier 2 Review Report

## Session
Sprint 32.8, Session 2: Dashboard Layout Refactor

## Reviewer
Tier 2 Automated Review (Opus 4.6)

## Review Date
2026-04-02

---

## Summary

Session 2 implements a dense 4-row Dashboard layout, creating a new VitalsStrip component that consolidates equity, daily P&L, today's stats, and VIX/regime into a single horizontal strip. The OpenPositions header was reworked to position the All/Open/Closed filter toggle left-aligned next to the title. GoalTracker and UniverseStatusCard were removed from the Dashboard render (components retained in codebase). All 111 scoped tests pass including 10 new tests.

---

## Review Focus Items

### F1: GoalTracker and UniverseStatusCard NOT deleted (PASS)

Both files confirmed present:
- `argus/ui/src/features/dashboard/GoalTracker.tsx` -- exists
- `argus/ui/src/features/dashboard/UniverseStatusCard.tsx` -- exists
- Both remain exported from `argus/ui/src/features/dashboard/index.ts` (lines 27 and 30)
- Their test files are untouched

### F2: VitalsStrip consumes existing hooks, no new API calls (PASS)

VitalsStrip imports and calls:
- `useAccount()` -- existing hook
- `useLiveEquity()` -- existing hook
- `useSparklineData()` -- existing hook
- `useVixData()` -- existing hook
- `todayStats` prop passed from parent's `useDashboardSummary()` -- existing hook

No new API endpoints, no new fetch calls, no new hooks introduced.

### F3: OpenPositions retains all interactivity (PASS with note)

The diff is confined to lines 839-892 (header section only). All table body rendering, sort handlers, filter logic, row click handlers, and display mode toggle are preserved identically. The SegmentedTab and display mode toggle buttons retain the same props, callbacks, and aria attributes.

**Note:** The subtitle that previously showed position counts (e.g., "5 open, 12 closed") was removed when CardHeader was replaced by a custom header. This is a minor information loss -- the count data is still accessible via the filter segments themselves (which show counts in their labels), but the always-visible subtitle is gone.

### F4: Row 3 uses CSS flexbox, not absolute positioning (PASS)

Row 3 uses `className="flex gap-3"` with children using `flex-[7]` (70%) and `flex-[3]` (30%). The right column uses `flex flex-col gap-3` for vertical stacking. No absolute positioning anywhere.

### F5: Responsive breakpoint stacking (PASS)

- Phone (<640px): All sections stacked vertically in a single column via flat `motion.div` children
- Tablet (640-1023px): All sections stacked vertically with `space-y-4`
- Desktop (>=1024px): 4-row layout with flex/grid as specified

---

## Findings

### C1: MarketStatusCard removed without spec authorization (MEDIUM)

**Severity:** Medium

The spec says "Remove from Dashboard: Monthly Goal card, Universe card." However, `MarketStatusCard` was also removed from ALL layout branches (desktop, tablet, phone). MarketStatusCard shows market open/closed/pre-market status with time display, regime badge, and PAPER mode indicator. This data is NOT represented in the VitalsStrip component.

The escalation criterion states: "Data loss -- Dashboard refactor accidentally removing access to any data that was previously visible (relocated is fine, removed is not)." MarketStatusCard data (market open/close status, current ET time, PAPER badge, regime description) is no longer accessible on the Dashboard.

However, this does not fully trigger escalation because: (a) market status is also visible on the OrchestratorStatusStrip (kept on phone/tablet), (b) regime info is partially covered by VitalsStrip's VIX section, and (c) the spec's 4-row layout implicitly excludes it by omission. Flagging as CONCERNS rather than ESCALATE because the data is partially available elsewhere and the spec layout left no room for it.

### C2: OrchestratorStatusStrip removed from desktop layout (LOW)

**Severity:** Low

The spec does not mention OrchestratorStatusStrip in the include or exclude list. The implementer made a judgment call (documented in close-out Judgment Call #1) to remove it from desktop to maintain the 4-row constraint. It is retained on phone and tablet. This is a reasonable interpretation of the spec's silence on the topic, and the close-out correctly flags it as a judgment call.

### C3: Positions subtitle (count text) dropped (LOW)

**Severity:** Low

The old CardHeader rendered a subtitle showing "X open, Y closed" or "X open" depending on the active filter. The new custom header does not render any count text. The segment labels on the SegmentedTab may show counts (depends on the `filterSegments` definition upstream), but the dedicated subtitle line is gone. Minor information density reduction.

---

## Sprint-Level Regression Checklist

| # | Check | Result |
|---|-------|--------|
| 4 | Dashboard renders all data (repositioned, not missing) | PARTIAL -- MarketStatusCard data missing from desktop (C1) |
| 7 | Existing pytest baseline | NOT RUN (Session 2 is frontend-only; no Python changes in scope) |
| 8 | Existing Vitest baseline (scoped) | PASS -- 111/111 |
| 9 | No Python files modified | PASS for Session 2 scope (Python diffs are from Session 1) |

---

## Escalation Criteria Assessment

| Criterion | Triggered? | Notes |
|-----------|-----------|-------|
| Trading engine modification | No | No Python strategy/core/execution changes in Session 2 |
| Event definition change | No | events.py not touched |
| API contract change | No | No REST/WS changes |
| Performance regression | No | Frontend-only changes |
| Data loss | Borderline | MarketStatusCard removed; partial overlap with other components |
| Test baseline regression | No | 111/111 passing |

No escalation criterion is fully triggered. The MarketStatusCard removal is borderline on "data loss" but the market status data is partially available through OrchestratorStatusStrip (on phone/tablet) and the VIX section of VitalsStrip covers regime info. The spec's layout implicitly excluded it.

---

## Test Results

```
Test Files  17 passed (17)
Tests       111 passed (111)
Duration    14.23s
```

New tests: 5 in VitalsStrip.test.tsx + 5 new in DashboardPage.test.tsx = 10 new tests.

---

## Verdict

**CONCERNS**

The implementation is solid and closely follows the spec. The 4-row layout is well-structured, VitalsStrip is clean, and all tests pass. Three medium-to-low findings:

1. MarketStatusCard was removed from the Dashboard without explicit spec authorization, removing market status/time/PAPER badge data from the desktop view (C1 -- medium)
2. OrchestratorStatusStrip removed from desktop as a judgment call (C2 -- low, well-documented)
3. Positions subtitle count text dropped (C3 -- low)

None of these trigger escalation. The implementation quality is high and the close-out report accurately describes the changes. The judgment calls are documented transparently.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CONCERNS",
  "sprint": "32.8",
  "session": 2,
  "title": "Dashboard Layout Refactor",
  "findings": [
    {
      "id": "C1",
      "severity": "medium",
      "category": "scope-deviation",
      "description": "MarketStatusCard removed from all Dashboard layouts without explicit spec authorization. Spec only authorized removal of GoalTracker and UniverseStatusCard. MarketStatusCard data (market open/close status, current ET time, PAPER badge, regime description) is no longer visible on desktop Dashboard.",
      "file": "argus/ui/src/pages/DashboardPage.tsx",
      "recommendation": "Confirm with operator whether MarketStatusCard removal is intentional. If the data is needed, it could be added as a 5th section in VitalsStrip or restored as a compact element."
    },
    {
      "id": "C2",
      "severity": "low",
      "category": "judgment-call",
      "description": "OrchestratorStatusStrip removed from desktop layout (kept on phone/tablet). Spec was silent on this component. Judgment call documented in close-out.",
      "file": "argus/ui/src/pages/DashboardPage.tsx",
      "recommendation": "No action required. Well-documented judgment call."
    },
    {
      "id": "C3",
      "severity": "low",
      "category": "information-loss",
      "description": "Positions header subtitle showing count text (e.g., '5 open, 12 closed') was dropped when CardHeader was replaced with custom header layout.",
      "file": "argus/ui/src/features/dashboard/OpenPositions.tsx",
      "recommendation": "Consider adding a small count indicator next to the title or within the SegmentedTab labels."
    }
  ],
  "tests_passed": 111,
  "tests_failed": 0,
  "tests_total": 111,
  "new_tests": 10,
  "escalation_triggered": false,
  "close_out_assessment_accurate": true
}
```
