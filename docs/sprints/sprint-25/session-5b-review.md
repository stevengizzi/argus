# Session 5b Tier 2 Review: Matrix Virtual Scrolling + Live Sort + Interaction

**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-17
**Sprint:** 25 — The Observatory
**Session:** 5b
**Diff scope:** Uncommitted changes on branch `sprint-25` (6 files)

---BEGIN-REVIEW---

## 1. Spec Compliance

| Requirement | Verdict | Notes |
|-------------|---------|-------|
| `useMatrixData` hook with TanStack Query + WS + sort | PASS | Created at `hooks/useMatrixData.ts`. Fetches via TanStack, subscribes to WS, sorts with `sortEntries()`. |
| Virtual scrolling for 500+ rows | PASS | Spacer-row technique in `VirtualMatrixTable` for 100+ rows. Sub-100 rendered directly. |
| Tab/Shift+Tab keyboard navigation | PASS | `handleKeyDown` on `window` in MatrixView. Wraps at list boundaries. |
| Enter selects highlighted symbol | PASS | Calls `onSelectSymbol(highlightedSymbol)` on Enter. |
| Highlight tracks by symbol across re-sort | PASS | State is `highlightedSymbol: string`, not an index. Test `highlight tracks symbol across re-sort` validates this. |
| Debrief mode: fetch once, no WS | PASS | `isDebrief = date !== undefined` disables `refetchInterval` and exits WS `useEffect` early. |
| Stable sort (same-score symbols don't jump) | PASS | `sortEntries()` uses `a.symbol.localeCompare(b.symbol)` as tiebreaker. Test validates alphabetical order for equal scores. |
| No new npm packages | PASS | `package.json` and `package-lock.json` unchanged (verified via `git diff`). |
| 4+ new tests | PASS | 4 new tests added (alpha tiebreaker, Tab advances, highlight tracks, Enter selects). Total: 42 observatory. |

## 2. Session-Specific Focus Items

### Focus 1: Virtual scroll does not install new packages
**PASS.** No changes to `package.json` or `package-lock.json`. Virtual scrolling implemented with native `onScroll`, `useMemo` for visible range, and spacer `<tr>` elements.

### Focus 2: Highlight tracks by symbol, not array index
**PASS.** `highlightedSymbol` is `string | null` state in `useMatrixData`. MatrixView uses `sorted.findIndex(r => r.symbol === highlightedSymbol)` to locate the current position after re-sorts. The test `highlight tracks symbol across re-sort` confirms this by changing sort order and verifying TSLA stays highlighted.

### Focus 3: Stable sort (same-score symbols don't jump)
**PASS.** `sortEntries()` in `useMatrixData.ts` lines 23-31 sorts by `conditions_passed` descending, then `symbol.localeCompare(symbol)` ascending. This is deterministic. Test at line 313 validates three symbols with equal scores sort alphabetically.

### Focus 4: Debrief mode disables WS subscription
**PASS.** In `useMatrixData.ts` line 81: `if (isDebrief) return;` exits the WS effect before creating the WebSocket. Line 63: `refetchInterval: isDebrief ? false : 5_000` disables polling.

## 3. Code Quality Findings

### 3a. Unused variable `totalHeight` (LOW)
`MatrixView.tsx` line 237: `const totalHeight = items.length * ROW_HEIGHT;` is computed but never referenced. This is dead code. It was likely intended for the virtual scroll container's inner height but is not used since spacer rows handle the total height implicitly.

### 3b. Potential Tab key handler conflict (MEDIUM)
Both `useObservatoryKeyboard` (page-level hook, line 130-132) and `MatrixView.handleKeyDown` (lines 81-113) register `window.addEventListener('keydown')` handlers that intercept the Tab key. When the Matrix view is active:

- The page-level hook calls `handleSymbolCycle()` which updates `selectedSymbol` (opens detail panel).
- The MatrixView handler calls `setHighlightedSymbol()` which updates visual highlight.

Both fire on the same keypress. This means Tab in Matrix view simultaneously: (a) cycles `selectedSymbol` in the page keyboard hook, and (b) cycles `highlightedSymbol` in the Matrix. These are separate state values tracked independently. If they drift out of sync (e.g., one starts null, the other doesn't), the highlighted row and the selected row (detail panel) could diverge.

The close-out acknowledges this in Judgment Call #4 and states they don't conflict. In practice the two lists iterate the same sorted data, so they likely stay in sync when both start from null. However, if `selectedSymbol` is set by clicking a row (which doesn't update `highlightedSymbol`), or `highlightedSymbol` is set by Tab (which doesn't call page-level `setSelectedSymbol` directly), the two can diverge. This is not a blocking issue but is worth revisiting if users report confusing behavior.

### 3c. Virtual scroll container maxHeight bootstrap (LOW)
`VirtualMatrixTable` initializes `containerHeight` to 600 and sets `style={{ maxHeight: containerHeight }}` on the scroll container. The `ResizeObserver` then measures this container -- but the container's own height is constrained by the `maxHeight` it just set. This creates a circular dependency where the container measures at most 600px initially. In practice, the outer `MatrixView` div has `h-full overflow-auto` which sizes the layout, and the VirtualMatrixTable only kicks in at 100+ rows where the 600px default is reasonable. Not blocking.

## 4. Test Verification

| Suite | Result |
|-------|--------|
| Observatory tests (`src/features/observatory/`) | 42/42 passed |
| Full Vitest suite | 565/565 passed |
| TypeScript strict check (`tsc --noEmit`) | 0 errors |

Test count: 565 (up from 523 baseline mentioned in CLAUDE.md -- growth is from earlier Sprint 25 sessions, not just this one).

## 5. Regression Checklist

| Check | Status |
|-------|--------|
| No trading pipeline files modified | PASS -- all changes in `argus/ui/src/features/observatory/` |
| No strategy/core/execution/data files modified | PASS |
| All existing Vitest tests pass | PASS (565/565) |
| TypeScript strict mode passes | PASS (0 errors) |
| No new npm packages added | PASS |

## 6. Escalation Criteria Check

| Criterion | Triggered? |
|-----------|-----------|
| #4: Modification to strategy logic / Event Bus / pipeline | No |
| #6: Matrix virtual scrolling jank with 200+ rows | Cannot verify visually in automated review; spacer-row approach is sound |
| #8: Keyboard shortcut conflicts | Tab conflict noted in 3b; not a browser/OS conflict but internal handler overlap |

No escalation criteria triggered.

## 7. Summary

The session delivers all spec requirements cleanly. Virtual scrolling is implemented without new dependencies using spacer rows and scroll position tracking. Highlight state correctly tracks by symbol string rather than array index, confirmed by test. Stable sort uses alphabetical tiebreaker. Debrief mode properly disables both WS and polling.

Two minor findings: an unused `totalHeight` variable (dead code) and a Tab key handler overlap between the page-level keyboard hook and MatrixView's own handler. Neither is blocking. The Tab overlap is a design consideration that could cause highlight/selection divergence in edge cases but is acceptable for the current implementation.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CONCERNS",
  "confidence": 0.90,
  "findings": [
    {
      "severity": "medium",
      "category": "behavior",
      "description": "Tab key handler overlap: both useObservatoryKeyboard and MatrixView register window keydown handlers for Tab. They update separate state (selectedSymbol vs highlightedSymbol) which can drift out of sync if one is set by click and the other by keyboard.",
      "file": "argus/ui/src/features/observatory/views/MatrixView.tsx",
      "lines": "81-113"
    },
    {
      "severity": "low",
      "category": "code-quality",
      "description": "Unused variable: const totalHeight = items.length * ROW_HEIGHT is computed but never referenced.",
      "file": "argus/ui/src/features/observatory/views/MatrixView.tsx",
      "lines": "237"
    },
    {
      "severity": "low",
      "category": "code-quality",
      "description": "Virtual scroll container maxHeight bootstrap: containerHeight state initializes to 600 and is used as maxHeight on the container that ResizeObserver measures, creating a circular constraint. Works in practice but is fragile.",
      "file": "argus/ui/src/features/observatory/views/MatrixView.tsx",
      "lines": "216-229"
    }
  ],
  "tests_pass": true,
  "test_count": {
    "observatory": 42,
    "full_vitest": 565,
    "typescript_errors": 0
  },
  "spec_compliance": "full",
  "focus_items_verified": [
    "No new packages installed",
    "Highlight tracks by symbol string not index",
    "Stable sort with alphabetical tiebreaker",
    "Debrief mode disables WS and polling"
  ],
  "escalation_triggers_fired": false,
  "recommendation": "Proceed to next session. Consider resolving Tab handler overlap in a future polish pass -- either disable the page-level Tab handler when Matrix view is active, or unify highlight and selection state in the Matrix."
}
```
