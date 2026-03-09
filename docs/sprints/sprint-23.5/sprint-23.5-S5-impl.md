# Sprint 23.5, Session 5: Frontend — Dashboard Catalyst Badges + Orchestrator Alert Panel

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/src/pages/DashboardPage.tsx` (current Dashboard layout — find watchlist area)
   - `argus/ui/src/pages/OrchestratorPage.tsx` (current Orchestrator layout — find where to add panel)
   - `argus/ui/src/hooks/useAccount.ts` or similar existing hooks (pattern for TanStack Query hooks)
   - `argus/ui/src/components/Badge.tsx` (existing Badge component — reuse or extend)
   - `argus/api/intelligence_routes.py` (S4 output — API response shapes)
2. Run the frontend test suite: `cd argus/ui && npx vitest run`
   Expected: 392+ tests, all passing
3. Run the backend test suite: `cd argus && python -m pytest tests/ -x -q`
   Expected: all passing (including S1–S4 tests)
4. Verify S4 API routes exist: `grep "catalysts" argus/api/intelligence_routes.py`

## Objective
Surface catalyst data on two Command Center pages: catalyst count badges on Dashboard watchlist entries, and a scrolling catalyst alert feed on the Orchestrator page. This session creates the shared `useCatalysts` hook and two new components.

## Requirements

1. **Create `argus/ui/src/hooks/useCatalysts.ts`**: TanStack Query hooks for catalyst data.
   - **`useCatalystsBySymbol(symbol: string)`**: Fetches `GET /api/v1/catalysts/{symbol}`. Returns `{ data, isLoading, error }`. Refetch interval: 60 seconds during market hours, disabled otherwise.
   - **`useRecentCatalysts(limit?: number)`**: Fetches `GET /api/v1/catalysts/recent?limit={limit}`. Returns `{ data, isLoading, error }`. Refetch interval: 30 seconds during market hours. Default limit: 50.
   - **Type definitions**: Define TypeScript interfaces matching the API response:
     ```typescript
     interface CatalystItem {
       symbol: string;
       catalyst_type: string;
       quality_score: number;
       headline: string;
       summary: string;
       source: string;
       source_url: string | null;
       filing_type: string | null;
       published_at: string;
       classified_at: string;
     }
     interface CatalystsResponse {
       catalysts: CatalystItem[];
       count: number;
       symbol?: string;
       total?: number;
     }
     ```
   - Use existing auth token from the auth store (follow existing hook patterns).

2. **Create `argus/ui/src/components/CatalystBadge.tsx`**: Small badge showing catalyst info.
   - Props: `catalysts: CatalystItem[]` (catalysts for this symbol).
   - If `catalysts.length === 0`: render nothing (null).
   - If catalysts exist: render a small pill/badge showing:
     - Catalyst count (e.g., "3")
     - Color coded by highest-priority catalyst type: earnings=blue, insider_trade=amber, analyst_action=purple, sec_filing=gray, corporate_event=teal, regulatory=red, news_sentiment=green, other=gray.
     - Tooltip on hover showing top catalyst headline.
   - Keep it compact — this sits next to symbol names in the watchlist.
   - Use Tailwind utility classes only (no custom CSS).

3. **Integrate CatalystBadge into Dashboard**: Modify `DashboardPage.tsx`.
   - Find the watchlist/symbol display area (likely in or near the Pre-Market Watchlist panel or the positions display).
   - For each symbol shown, call `useCatalystsBySymbol(symbol)` and render `<CatalystBadge catalysts={data?.catalysts ?? []} />` next to the symbol name.
   - Handle loading state: don't show badge while loading (avoid flickering).
   - Handle error state: don't show badge on error (silent degradation).
   - IMPORTANT: Do NOT restructure the existing Dashboard layout. Add the badge as a sibling/child element within existing containers. Do NOT use conditional rendering that creates different React element trees.

4. **Create `argus/ui/src/components/CatalystAlertPanel.tsx`**: Scrolling catalyst alert feed.
   - Uses `useRecentCatalysts(30)` hook.
   - Renders as a panel/card (follow existing card patterns — likely uses `Card` component).
   - Title: "Catalyst Alerts" with a small indicator showing live/stale status.
   - Each alert entry shows:
     - Symbol (bold, colored by catalyst type)
     - Quality score (small badge, colored: ≥70 green, 40–69 amber, <40 gray)
     - Headline (truncated to ~80 chars with ellipsis)
     - Source icon/label (SEC, FMP, Finnhub)
     - Time (relative — "2m ago", "1h ago")
   - Scrollable container with max height (~300px), newest at top.
   - Empty state: "No recent catalysts" with a subtle icon.
   - Auto-refreshes via the hook's refetch interval (30 seconds).

5. **Integrate CatalystAlertPanel into Orchestrator**: Modify `OrchestratorPage.tsx`.
   - Add `<CatalystAlertPanel />` as a new section/card on the page.
   - Place it logically — likely after the strategy status section or alongside the decision history.
   - Do NOT restructure existing Orchestrator layout.

## Constraints
- Do NOT modify any backend files
- Do NOT modify pages other than DashboardPage.tsx and OrchestratorPage.tsx
- Do NOT use conditional rendering that creates different React element trees (anti-pattern per project rules)
- Use only Tailwind utility classes for styling
- Use existing component patterns (Card, Badge, etc.) where available
- Do NOT create new API endpoints or modify existing ones

## Visual Review
The developer should visually verify the following after this session:
1. **Dashboard**: Catalyst badges appear next to watchlist entries that have catalysts. Symbols without catalysts show no badge. Badge colors are distinguishable and not clashing with existing UI.
2. **Orchestrator**: Catalyst alert panel renders with recent events (or empty state). Quality scores are color-coded. Panel scrolls when content exceeds max height.
3. **Both pages**: No layout shifts or visual regressions on existing panels. Loading states don't cause flickering.

Verification conditions:
- Backend running with mock catalyst data (or run `POST /api/v1/premarket/briefing/generate` to populate some data)
- API accessible at localhost:8000

## Test Targets
After implementation:
- Existing Vitest tests: all 392+ must still pass
- New tests in `argus/ui/src/`:
  1. useCatalysts hook: returns loading state initially
  2. useCatalysts hook: returns data on success
  3. useCatalysts hook: handles error gracefully
  4. useCatalysts hook: returns empty catalysts array
  5. CatalystBadge: renders nothing when no catalysts
  6. CatalystBadge: renders badge with count when catalysts exist
  7. CatalystBadge: uses correct color for catalyst type
  8. CatalystAlertPanel: renders alerts when data available
  9. CatalystAlertPanel: renders empty state
  10. CatalystAlertPanel: truncates long headlines
- Minimum new test count: 10 Vitest
- Test command: `cd argus/ui && npx vitest run`

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing Vitest tests pass (392+)
- [ ] All existing pytest tests pass
- [ ] New Vitest tests written and passing (≥10)
- [ ] Visual review items ready for inspection
- [ ] No conditional rendering anti-pattern
- [ ] Ruff linting passes (backend unchanged)

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No backend files modified | `git diff --name-only` shows only UI files |
| Dashboard existing panels intact | Existing Dashboard tests pass, visual inspection |
| Orchestrator existing panels intact | Existing Orchestrator tests pass, visual inspection |
| Only DashboardPage and OrchestratorPage modified | `git diff --name-only argus/ui/src/pages/` shows only these two |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema and requirements.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
R1–R25 from `docs/sprints/sprint-23.5/sprint-23.5-review-context.md`

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
Items 1–15 from `docs/sprints/sprint-23.5/sprint-23.5-review-context.md`
