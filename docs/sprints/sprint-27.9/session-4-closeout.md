# Sprint 27.9, Session 4: Dashboard VIX Widget (Frontend) — Close-Out

## Change Manifest

| File | Action | Description |
|------|--------|-------------|
| `argus/ui/src/api/types.ts` | Modified | Added `VixRegimeData` and `VixCurrentResponse` TypeScript interfaces |
| `argus/ui/src/api/client.ts` | Modified | Added `getVixCurrent()` API function + VixCurrentResponse import |
| `argus/ui/src/hooks/useVixData.ts` | Created | TanStack Query hook with 60s refetchInterval |
| `argus/ui/src/hooks/index.ts` | Modified | Added `useVixData` export |
| `argus/ui/src/features/dashboard/VixRegimeCard.tsx` | Created | Card component: VIX close, VRP tier badge, vol phase label, momentum arrow |
| `argus/ui/src/features/dashboard/index.ts` | Modified | Added `VixRegimeCard` export |
| `argus/ui/src/pages/DashboardPage.tsx` | Modified | Added VixRegimeCard to all 3 layouts (phone, tablet, desktop) |
| `argus/ui/src/pages/DashboardPage.test.tsx` | Modified | Added VixRegimeCard mock (returns null) to existing dashboard mock |
| `argus/ui/src/features/dashboard/__tests__/VixRegimeCard.test.tsx` | Created | 6 Vitest tests |

## Judgment Calls

1. **No `endpoints.ts` file exists** — The prompt spec asked to add endpoint constants to `argus/ui/src/api/endpoints.ts`, but this file doesn't exist. The project stores API functions directly in `client.ts`. Added `getVixCurrent()` there instead, following the established pattern.

2. **VixRegimeCard placement** — Placed after StrategyDeploymentBar in all layouts (phone/tablet/desktop). The component returns `null` when VIX is unavailable/disabled, so no layout shift occurs. Placed at the top per spec suggestion ("top row alongside existing summary widgets") rather than embedding in an existing grid row, which would disrupt the existing 3-col/2-col grid patterns.

3. **DashboardPage.test.tsx mock** — The existing test mocks all dashboard components. Added `VixRegimeCard: () => null` to the mock, matching the real component's default behavior (returns null when no VIX data). This preserves existing test assertions about card ordering.

## Scope Verification

- [x] useVixData hook implemented with 60s polling
- [x] VixRegimeCard renders correctly in all states (data, loading, stale, disabled, unavailable)
- [x] Dashboard shows VixRegimeCard when VIX enabled and data available
- [x] Dashboard hides VixRegimeCard when VIX disabled or unavailable
- [x] 6 Vitest tests passing
- [x] All existing Vitest tests passing (645 total, 0 failures)
- [x] Backend pytest: 4 pre-existing failures (AI client, server intelligence, 2x backtest engine) — all confirmed on clean HEAD, unrelated to frontend changes
- [x] No Canvas 2D, Three.js, or animation library usage
- [x] No WebSocket connections added
- [x] No existing Dashboard widgets modified

## Regression Checklist

| Check | Result |
|-------|--------|
| R14: Dashboard loads when VIX disabled | PASS — VixRegimeCard returns null, test_hidden_when_disabled passes |
| Existing Dashboard widgets unchanged | PASS — All 639 existing Vitest tests pass |
| No other pages modified | PASS — `git diff --name-only` shows only DashboardPage.tsx (no other pages) |

## Test Results

**Vitest:** 645 passed, 0 failed (94 test files)
- 6 new VixRegimeCard tests
- All 639 existing tests pass

**Backend pytest:** 4 pre-existing failures, 1779 passed
- `test_send_message_returns_graceful_response` — AI client test (pre-existing)
- `test_lifespan_ai_disabled_catalyst_enabled` — server intelligence test (pre-existing)
- `test_teardown_cleans_up` — backtest engine test (confirmed pre-existing on clean HEAD)
- `test_empty_data_returns_empty_result` — backtest engine test (pre-existing)

## Self-Assessment

**Verdict:** CLEAN

All spec items implemented. No scope deviation. No regressions. 4 backend failures confirmed pre-existing on clean HEAD.

## Context State

GREEN — session completed well within context limits.
