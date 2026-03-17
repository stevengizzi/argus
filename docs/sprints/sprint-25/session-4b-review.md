# Sprint 25, Session 4b — Tier 2 Review Report

---BEGIN-REVIEW---

## Review Summary

**Session:** Sprint 25, Session 4b — Candlestick Chart + Data Hooks
**Reviewer:** Tier 2 Automated (Claude Opus 4.6)
**Date:** 2026-03-17
**Verdict:** CLEAR

## Spec Compliance

All Definition of Done items verified:

| Requirement | Status | Notes |
|-------------|--------|-------|
| Candlestick chart renders with candle data | PASS | SymbolCandlestickChart uses createChart + CandlestickSeries, data mapped from BarData |
| Chart reinitializes on symbol change | PASS | useEffect dependency on `symbol` triggers full dispose/recreate cycle |
| Chart disposes on unmount | PASS | Cleanup function calls chart.remove(), nulls refs |
| useSymbolDetail fetches and combines data | PASS | 4 TanStack queries: journey (5s), quality (30s), catalysts (60s), candles (15s) |
| All detail panel sections populated | PASS | Quality grade badge, market data from bars, catalysts, chart, conditions, strategy history |
| Loading and empty states handled | PASS | "No quality data", "No catalysts available", "No chart data available", "Loading..." states present |
| 5+ new tests | PASS | 6 new tests (3 chart + 3 hook) |
| All existing tests pass | PASS | 554 Vitest tests pass, 0 failures |

## Review Focus Items

### 1. Chart disposal on unmount (no memory leaks)

**PASS.** The useEffect cleanup at line 97-102 of SymbolCandlestickChart.tsx calls:
- `resizeObserver.disconnect()` — stops the ResizeObserver
- `chart.remove()` — disposes the Lightweight Charts instance
- Nulls both `chartRef.current` and `seriesRef.current`

Test `disposes chart on unmount` confirms `mockRemove` is called exactly once on unmount.

### 2. Chart reinitializes (not just updates) on symbol change

**PASS.** The useEffect at line 51 has `[symbol, height]` as dependencies. When symbol changes, React runs the cleanup (disposing old chart) then re-runs the effect (creating a new chart). This is a full reinit, not a data swap. Test `reinitializes chart on symbol change` confirms old chart is removed and addSeries is called twice.

### 3. TanStack Query keys include symbol -- automatic refetch on change

**PASS.** All four queries include symbol in their key arrays:
- `['observatory', 'journey', symbol, date]`
- `['observatory', 'quality', symbol]`
- `['observatory', 'catalysts', symbol]`
- `['observatory', 'candles', symbol]`

TanStack Query will automatically refetch when symbol changes.

### 4. Polling disabled in debrief mode

**PASS.** Each query has `refetchInterval: isDebrief ? false : <interval>` where `isDebrief = date !== undefined`. When a date prop is provided, all polling stops. Test `disables polling in debrief mode` verifies the date is passed to the journey query.

**Note:** The debrief mode test only verifies that the date argument is passed to the journey query function. It does not directly assert that `refetchInterval` is `false`. This is a minor test coverage gap -- the polling disable behavior is verified by code inspection rather than runtime assertion. This is acceptable for TanStack Query behavior since testing internal query options requires reaching into query client internals.

### 5. Lightweight Charts uses 2D canvas (no WebGL context conflict risk)

**PASS.** Lightweight Charts uses HTML5 2D Canvas, not WebGL. The createChart call produces a standard canvas element. No WebGL context is created. Three.js (used elsewhere in Observatory) uses a separate WebGL context. No conflict risk.

## Code Quality Assessment

- **No `any` types** anywhere in new or modified files.
- **TypeScript compiles cleanly** (`tsc --noEmit` passes with no errors).
- **No backend files modified** -- pure frontend session as specified.
- **Proper type imports** from `lightweight-charts` (IChartApi, ISeriesApi, CandlestickData, UTCTimestamp).
- **Shared chart theme** reused from `utils/chartTheme.ts` (chartColors, lwcDefaultOptions).
- **New API types** (CatalystItem, CatalystsBySymbolResponse) are well-typed with specific fields, no `any`.
- **getCatalystsBySymbol** properly uses URLSearchParams and fetchWithAuth.
- **Responsive width** handled via ResizeObserver on the container div.

## Minor Observations (Non-Blocking)

1. **Market data "High" and "Low" show last bar values, not session high/low.** The implementation shows `lastBar.high` and `lastBar.low` (last candle's high/low), not the session-wide high and low. The close-out acknowledges this as a judgment call -- deriving ATR/VWAP/RelVol would need a new endpoint. The current approach is pragmatically useful and clearly labeled.

2. **Candle polling at 15s vs spec's unspecified interval.** The spec said "candle data from appropriate existing endpoint" but didn't specify a polling interval. 15s is reasonable for 1-minute bars.

3. **QualityScoreResponse accessed as `quality.score.toFixed(1)` without null guard on score field.** If the API returns a response where `score` is somehow null or undefined, this would throw. However, the quality section is gated by `quality ?` truthiness check, and the QualityScoreResponse type defines `score: number`, so this is type-safe.

## Regression Checklist

| Check | Result |
|-------|--------|
| No backend files modified | PASS -- only `argus/ui/src/` and `docs/` changed |
| All Vitest tests pass (554) | PASS -- 554 passed, 0 failed |
| TypeScript strict mode | PASS -- `tsc --noEmit` clean |
| Test count increased | PASS -- 523 baseline to 554 (31 net new across S4a+S4b) |

## Escalation Criteria Check

| Criterion | Triggered? |
|-----------|-----------|
| Three.js performance below 30fps | N/A (no Three.js work this session) |
| Bundle size increase > 500KB gzipped | N/A (no new dependencies added) |
| WebSocket degradation | N/A (no WS changes this session) |
| Modification to strategy/pipeline logic | NO -- pure frontend |
| Non-Observatory page load increase > 100ms | N/A (no shared code changes) |
| Lightweight Charts conflicts with Three.js | NO -- 2D canvas, no conflict |

No escalation criteria triggered.

## Verdict

**CLEAR** -- Implementation matches spec across all Definition of Done items and all five review focus areas. Tests pass, types are clean, chart lifecycle is correctly managed, and no regressions detected.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "session": "sprint-25-S4b",
  "reviewer": "tier-2-automated",
  "date": "2026-03-17",
  "spec_compliance": "full",
  "tests_pass": true,
  "test_count": { "observatory": 31, "full_suite": 554 },
  "typescript_clean": true,
  "review_focus_results": {
    "chart_disposal_on_unmount": "PASS",
    "chart_reinitializes_on_symbol_change": "PASS",
    "query_keys_include_symbol": "PASS",
    "polling_disabled_in_debrief": "PASS",
    "lightweight_charts_2d_canvas": "PASS"
  },
  "escalation_triggers": [],
  "concerns": [],
  "notes": [
    "Market data High/Low show last bar values, not session high/low -- acknowledged judgment call",
    "Debrief mode test verifies date passthrough but not refetchInterval=false directly -- acceptable coverage gap"
  ]
}
```
