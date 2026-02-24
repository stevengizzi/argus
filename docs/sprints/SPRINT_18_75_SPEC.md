# Sprint 18.75 — CapitalAllocation Enhancement

> **Scope:** Rename AllocationDonut → CapitalAllocation. Add nested two-ring donut (allocation policy + deployment state) and horizontal stacked bars view with SegmentedTab toggle. ~3 sessions.
> **Prerequisite:** Read this entire spec before starting any session.

---

Session 1: API Enrichment + TypeScript Types

# ARGUS Sprint 18.75 — Session 1: Deployment State API + Types

## Context
We're enhancing the capital allocation visualization on the Dashboard. The current 
AllocationDonut shows allocation policy only (what % each strategy is *allowed*). 
We need to also show deployment state (what % each strategy *currently has in open 
positions*) and throttle status.

Read CLAUDE.md for project state. This is a small pre-Sprint 19 polish task (3 sessions total).

## This Session's Scope

### 1. Enrich the orchestrator status endpoint

The existing `GET /api/v1/orchestrator/status` endpoint (added in Sprint 17) returns 
allocation data. Enrich the response to include per-strategy deployment state.

For each strategy in the allocations response, add:
- `deployed_capital: float` — sum of (entry_price × shares_remaining) for all open 
  positions belonging to this strategy. Computed from `state.order_manager.get_managed_positions()`.
- `deployed_pct: float` — deployed_capital / total_equity (or 0 if no equity).
- `is_throttled: bool` — whether the PerformanceThrottler has this strategy suspended.
  Check via `state.orchestrator.throttler.is_throttled(strategy_id)` or equivalent 
  (inspect the actual Orchestrator/PerformanceThrottler API and use whatever accessor exists).

Also add a top-level field:
- `total_deployed_capital: float` — sum of all strategies' deployed_capital.
- `total_equity: float` — total account equity (from broker or account state).

**Implementation approach:**
- Look at the existing orchestrator routes file (`argus/api/routes/orchestrator.py` or 
  wherever Sprint 17 put them). Find the status endpoint and its response model.
- Read the Orchestrator class to understand its public API — especially how it exposes 
  allocation data and throttle state. Sprint 17.5 added encapsulation properties for 
  route access.
- Read `argus/execution/order_manager.py` — `get_managed_positions()` returns all 
  ManagedPosition objects. Each has `strategy_id`, `entry_price`, `shares_remaining`, 
  `is_fully_closed`.
- Compute deployed capital by iterating positions, filtering to open (!is_fully_closed), 
  grouping by strategy_id, summing entry_price * shares_remaining.

### 2. Update dev mode mock data

In `argus/api/dev_state.py`, ensure the mock Orchestrator (or mock orchestrator status) 
includes realistic deployment data. The existing mock positions (NVDA, TSLA, AMD) from 
Sprint 14+ should naturally produce deployed capital when the endpoint computes from 
order_manager positions.

If the orchestrator status endpoint in dev mode returns mock data directly (rather than 
computing from real components), update the mock to include the new fields. Check how 
Sprint 17 wired the orchestrator endpoints in dev mode — it may use a mock orchestrator 
or compute from the real mock order_manager.

### 3. Update TypeScript types

In `argus/ui/src/api/types.ts`, find or create the `OrchestratorStatus` type (or whatever 
Sprint 17 named it). Add the new fields:
- Per-strategy: `deployed_capital`, `deployed_pct`, `is_throttled`
- Top-level: `total_deployed_capital`, `total_equity`

### 4. Add tests

Add pytest tests for the new computation:
- Test that deployed_capital correctly sums open positions per strategy
- Test that strategies with no open positions show deployed_capital = 0
- Test that is_throttled reflects throttler state
- Test dev mode returns the enriched response

## Verification
- `pytest tests/api/ -x` — all pass including new tests
- `cd argus/ui && npx tsc --noEmit` — TypeScript compiles clean
- `python -m argus.api --dev` then `curl localhost:8000/api/v1/orchestrator/status` — 
  response includes new deployment fields with realistic values

## Do NOT do in this session
- Any frontend component changes
- Renaming AllocationDonut
- Any chart/visualization work

---

Session 2: CapitalAllocation Component — Nested Donut + Toggle

# ARGUS Sprint 18.75 — Session 2: Nested Donut + SegmentedTab Toggle

## Context
Session 1 enriched the API with per-strategy deployment state. This session renames 
AllocationDonut → CapitalAllocation and implements the nested two-ring donut view with 
a toggle for the bars view (built in Session 3).

Read CLAUDE.md for project state. Read `argus/ui/src/utils/motion.ts` for animation constants.

## This Session's Scope

### 1. Rename AllocationDonut → CapitalAllocation

- Rename the file: `AllocationDonut.tsx` → `CapitalAllocation.tsx`
- Rename the component export: `AllocationDonut` → `CapitalAllocation`
- Update all imports (Dashboard page, any skeleton references, etc.)
- Update the parent card — if the card title says "Allocation" or similar, keep it or 
  rename to "Capital Allocation"

### 2. Add SegmentedTab toggle

- Import the existing `SegmentedTab` component (created in Sprint 17)
- Add a `Donut | Bars` toggle at the top of the CapitalAllocation card, below the 
  CardHeader
- Use compact sizing — this is inside a dashboard card, not a full page
- The "Bars" tab renders a placeholder `<div>` with text "Bars view — Session 3" for now

### 3. Add Zustand view persistence

- Follow the DEC-129 pattern (positions view toggle). Find how the positions view mode 
  is stored in the Zustand store (likely in `argus/ui/src/store/` or similar).
- Add a `capitalAllocationView: 'donut' | 'bars'` field to the appropriate store
- Wire the SegmentedTab to read/write from this store
- View preference persists across page navigations (session-level, not localStorage)

### 4. Implement nested two-ring donut

Replace the current single-ring donut with a two-ring design:

**Outer ring — Allocation Policy:**
- Each strategy gets a segment proportional to its allocated_pct
- Reserve capital gets its own segment (cash_reserve_pct)
- Unallocated remainder (if any) gets a subtle segment
- Colors: use existing strategy color mapping (Sprint 17 established per-strategy colors — 
  ORB = blue, Scalp = purple, etc.). Reserve = neutral gray.

**Inner ring — Deployment State:**
- Same angular segments as outer ring (aligned to each strategy's allocation)
- Within each segment, fill proportionally to deployed_pct / allocated_pct
- Deployed portion: strategy's accent color (solid)
- Available portion: strategy's accent color (very desaturated/transparent, ~20% opacity)
- Throttled: gray fill (only shown when strategy.is_throttled is true — replaces the 
  available portion)
- Reserve segment inner ring: always empty (reserves aren't deployed)

**Center label:**
- Show total deployed % in the donut hole (e.g., "34% Deployed")
- Or total deployed capital as dollar amount
- Use the existing pattern from the Sprint 17 donut (it likely has a center label already)

**Implementation approach:**
- The current AllocationDonut likely uses SVG arcs or a charting library. Inspect the 
  actual implementation to understand the rendering approach.
- If it uses SVG directly: add a second set of arcs at a smaller radius for the inner ring
- If it uses Recharts PieChart: use two nested Pie components with different innerRadius/outerRadius
- Match the Framer Motion animation-once pattern from Sprint 17.5 (animate on first mount only)

### 5. Wire to API data

- Find the existing hook that fetches orchestrator status (Sprint 17 created this)
- Use the enriched response fields from Session 1 (deployed_capital, deployed_pct, is_throttled)
- Handle loading state: show the existing skeleton or shimmer pattern
- Handle empty state: no strategies registered → show contextual empty state

### 6. Update the dashboard card sizing

- The CapitalAllocation card may need slightly more vertical space to accommodate the 
  SegmentedTab + the nested donut
- Check the RiskBudget card — Steven noted it's "much bigger than it needs to be for just 
  the two small radials." You can redistribute some of that vertical space if they share a 
  grid row. Don't change the RiskBudget card itself — just allow CapitalAllocation to grow 
  if the grid layout permits.

## Design Rules
- Animations: <500ms, 60fps, Framer Motion for mount animations
- Colors: use existing strategy color constants (don't invent new ones)
- Responsive: must work at 393px (phone) — the donut should scale down gracefully
- The two rings should have enough visual separation to read as two distinct layers
- Outer ring: slightly thicker stroke/width. Inner ring: slightly thinner.

## Verification
- `cd argus/ui && npm run build && npm run lint` — clean
- `python -m argus.api --dev` → open dashboard → CapitalAllocation card shows nested donut
- Toggle between Donut and Bars — Bars shows placeholder
- Navigate away and back — toggle preference preserved
- Check at 393px width — donut scales appropriately
- Check at 1512px width — donut looks correct in desktop layout
- Outer ring shows allocation policy (ORB + Scalp + Reserve segments)
- Inner ring shows deployment state (filled portions for strategies with open positions)

## Do NOT do in this session
- The Bars view (Session 3)
- Any backend changes
- RiskBudget card changes

---

Session 3: Horizontal Stacked Bars View + Polish

# ARGUS Sprint 18.75 — Session 3: Stacked Bars View + Final Polish

## Context
Session 1 enriched the API. Session 2 built the nested donut and SegmentedTab toggle.
This session implements the horizontal stacked bars view and polishes both views.

Read CLAUDE.md for project state.

## This Session's Scope

### 1. Implement horizontal stacked bars view

Replace the Session 2 placeholder in the "Bars" tab with a proper visualization.

**Layout — one bar per strategy + reserve:**
ORB Breakout    [████████░░░░░░░░░░] $8,200 / $25,000   33%
ORB Scalp       [██░░░░░░░░░░░░░░░░] $2,100 / $25,000    8%
Reserve         [░░░░░░░░░░░░░░░░░░] $0     / $20,000    0%
▲deployed  ▲available  ▲throttled(if any)

Each bar is a horizontal stacked bar where:
- Total bar width = that strategy's allocated capital (as proportion of total)
- **Deployed segment** (left, solid strategy color): capital in open positions
- **Available segment** (middle, desaturated strategy color ~20% opacity): allocated but not deployed
- **Throttled segment** (replaces Available when is_throttled=true, gray): allocated but strategy suspended

**Bar label layout:**
- Left side: strategy name (with strategy badge/color dot for quick identification)
- Right side: deployed amount / allocated amount, and deployed percentage
- If throttled: show a small "Paused" badge or icon next to the strategy name

**Reserve bar:**
- Always at the bottom
- Neutral gray color
- Shows reserve amount (never has deployed or throttled segments)

### 2. Responsive behavior

- **Desktop (≥1024px):** Bars at full width within card. Labels on both sides.
- **Tablet (640–1023px):** Same as desktop.
- **Phone (<640px):** Strategy name above the bar (stacked layout). Amount/percentage 
  below the bar. Bars still horizontal and full-width. This avoids squeezing labels 
  into tiny space.

### 3. Animation

- Bars animate in on first mount: width grows from 0 to final value, staggered per bar 
  (use the existing `staggerContainer`/`staggerItem` pattern from `motion.ts`)
- Deployed segment within each bar can also animate its fill width
- On data update (WebSocket position changes), bars smoothly transition to new widths 
  (CSS transition or Framer Motion layout animation)
- Match the animation-once pattern from Sprint 17.5 (useRef to track first mount)

### 4. Interaction

- Hover on a bar segment: show tooltip with exact dollar amount and percentage
  (desktop only — use `@media (hover: hover)` pattern from Sprint 16)
- No click-to-filter behavior yet (that's Sprint 21 scope per UX Feature Backlog)

### 5. Edge cases

- **Zero strategies:** Show contextual empty state ("No strategies registered")
- **One strategy:** Single bar + reserve. Still useful — shows how much of the allocation is deployed.
- **Strategy with 0 deployed:** Full bar is Available color (desaturated)
- **Strategy at 100% deployed:** Full bar is solid strategy color
- **All strategies throttled:** All bars show gray throttled segments — visually distinct warning state

### 6. Polish both views

Review both Donut and Bars views for consistency:
- Both should use the same strategy colors
- Both should show the same data (they're just different representations)
- Legend (if any) should be consistent — or remove explicit legend if the bars self-label
- Transition between views: use Framer Motion AnimatePresence for a subtle crossfade 
  between donut and bars when toggling

### 7. Vitest test (optional if time permits)

Add 1-2 Vitest component tests following the DEC-130 pattern:
- CapitalAllocation renders without crashing with mock data
- Toggle switches between donut and bars views

## Verification
- `cd argus/ui && npm run build && npm run lint` — clean
- `python -m argus.api --dev` → Dashboard → CapitalAllocation card
- **Donut tab:** Nested two-ring donut with allocation + deployment
- **Bars tab:** Horizontal stacked bars with deployed/available/throttled segments
- Toggle between views — smooth crossfade transition
- Navigate away and back — preference persisted
- Check at 393px: bars stack labels vertically, still readable
- Check at 1512px: bars with side-by-side labels
- Hover on bar segments (desktop): tooltip with details
- Data consistency: same numbers in both donut and bars views
- Overall dashboard: CapitalAllocation card fits well alongside other cards

## Final checks (end of Sprint 18.75)
- `cd argus/ui && npm run build && npm run lint` — clean
- `npx tsc --noEmit` — clean
- `pytest tests/api/ -x` — all pass
- `npx vitest run` — all pass (if tests added)
- Dev mode walkthrough: login → dashboard → verify both views → toggle → navigate → return