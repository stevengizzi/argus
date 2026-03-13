# Sprint 24, Session 9: Frontend — Quality Components + Hooks + Trades Page

## Pre-Flight Checks
1. Read: Existing hook patterns (e.g., `argus/ui/src/hooks/` or similar), Trades page component structure, existing badge/tag component patterns
2. Scoped test: `cd argus/ui && npx vitest run --reporter=verbose 2>&1 | tail -20`
3. Branch: `sprint-24`

## Objective
Create reusable QualityBadge component, TanStack Query hooks for quality API, and add quality grade column to Trades page.

## Requirements

### 1. Create `QualityBadge.tsx` (shared component):
- Grade-colored pill: A+/A/A- = green shades, B+/B/B- = amber shades, C+/C/C- = red/gray
- Props: `grade: string`, `score?: number`, `components?: Record<string, number>`, `compact?: boolean`
- Tooltip on hover: grade, composite score, risk tier (e.g., "A+ (92.3) — 2.5% risk")
- When `compact=false` and components provided: show 5-dimension breakdown (small horizontal bars or simple text list)
- Empty/loading state: gray placeholder

### 2. Create `useQuality.ts` (TanStack Query hooks):
- `useQualityScore(symbol: string)` → GET /api/v1/quality/{symbol}
- `useQualityHistory(filters: QualityHistoryFilters)` → GET /api/v1/quality/history
- `useQualityDistribution()` → GET /api/v1/quality/distribution
- Follow existing hook patterns (staleTime, error handling, etc.)
- Type definitions for API responses

### 3. Trades page modifications:
- Add quality grade column to trades table (using QualityBadge compact mode)
- If quality_grade is empty string (pre-Sprint-24 trades), show "—"
- Trade detail/expanded row: show full QualityBadge with component breakdown

## Constraints
- Do NOT modify: existing table columns (only add new column)
- Follow existing component patterns (Tailwind CSS v4, existing design system)
- Use existing TanStack Query patterns for consistency

## Visual Review
The developer should visually verify:
1. **Trades table**: New "Quality" column visible with grade badges for recent trades
2. **QualityBadge colors**: Grade-appropriate coloring (green for A range, amber for B, gray for no data)
3. **Tooltip**: Hovering QualityBadge shows score and risk tier
4. **Empty state**: Pre-Sprint-24 trades show "—" in quality column
5. **Responsive**: Table doesn't break on mobile viewport

Verification conditions:
- App running in dev mode (`--dev`) with sample data or after paper trading session with quality engine active

## Test Targets
- `test_quality_badge_renders_grade`: Component renders with grade text
- `test_quality_badge_color_mapping`: A+ → green class, B → amber class
- `test_quality_badge_tooltip`: Score and risk tier in tooltip
- `test_quality_badge_empty_state`: No grade → gray placeholder
- `test_quality_badge_compact_mode`: Compact renders smaller
- `test_use_quality_score_hook`: Mock API → correct data
- `test_use_quality_distribution_hook`: Mock API → correct data
- `test_trades_quality_column_present`: Column header exists
- `test_trades_quality_badge_integration`: Badge renders in table cell
- `test_trades_empty_grade_shows_dash`: Empty grade → "—"
- Minimum: 10 Vitest
- Test command: `cd argus/ui && npx vitest run`

## Definition of Done
- [ ] QualityBadge component with grade coloring and tooltip
- [ ] 3 TanStack Query hooks working
- [ ] Trades table has quality column
- [ ] Visual review items verified
- [ ] 10+ Vitest tests

## Close-Out
Write report to `docs/sprints/sprint-24/session-9-closeout.md`.

