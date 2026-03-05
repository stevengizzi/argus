# Sprint 21b — Orchestrator Page Implementation Spec

> **Status:** Ready for implementation
> **Prerequisites:** Sprint 21a complete (1558 pytest + 70 Vitest), repo at `main`
> **Target:** ~1578 pytest + ~78 Vitest (20 new pytest, 8 new Vitest)
> **Sessions:** 8 implementation sessions

---

## Overview

Build the Orchestrator page — the 6th Command Center page. This is the real-time operational nerve center that answers: "What is the Orchestrator doing right now, why is it making these decisions, and how do I intervene?"

The Dashboard shows ambient status. The Orchestrator page shows operational detail and controls. Think engine diagnostic screen vs. car dashboard.

### Page Sections (top to bottom)
1. **RegimePanel** — session phase, regime badge, input breakdown, next check countdown
2. **StrategyCoverageTimeline** — SVG timeline showing strategy operating windows + "now" marker
3. **CapitalAllocation** — reuse existing component (compact)
4. **StrategyOperationsGrid** — per-strategy cards with allocation, throttle status, controls
5. **DecisionTimeline** — today's orchestrator decisions in chronological order
6. **GlobalControls** — force rebalance + emergency flatten/pause

### Key Architecture Decisions
- **No master-detail layout.** Full-width vertical scroll. Information-dense but progressive.
- **Reuse existing components** heavily: CapitalAllocation, Badge system, EmergencyControls pattern, Card/CardHeader/MetricCard.
- **Custom SVG** for the coverage timeline (not D3). Simple time-to-pixel mapping.
- **TanStack Query** for data fetching. WebSocket events invalidate queries for near-instant updates.
- **Minimal new Zustand state.** Most state is server state via TanStack Query.

---

## Session 1: API Extensions

### Goal
Extend `GET /orchestrator/status` with session phase, pre-market status, and richer per-strategy data. Add date filter to `GET /orchestrator/decisions`.

### Files to modify

**`argus/api/routes/orchestrator.py`:**

Add to `OrchestratorStatusResponse`:
```python
session_phase: str  # "pre_market" | "market_open" | "midday" | "power_hour" | "after_hours" | "market_closed"
pre_market_complete: bool
pre_market_completed_at: str | None
```

Add new response model:
```python
class OperatingWindow(BaseModel):
    earliest_entry: str  # "09:35"
    latest_entry: str    # "11:30"
    force_close: str     # "15:50"
```

Extend `AllocationInfo`:
```python
operating_window: OperatingWindow | None
consecutive_losses: int
rolling_sharpe: float | None
drawdown_pct: float
is_active: bool
health_status: str  # "healthy" | "warning" | "error"
trade_count_today: int
daily_pnl: float
open_position_count: int
override_active: bool
override_until: str | None
```

Add helper function for session phase:
```python
def _compute_session_phase(now_et: datetime) -> str:
    """Compute session phase from current ET time.
    
    pre_market: before 9:30
    market_open: 9:30-11:30
    midday: 11:30-14:00
    power_hour: 14:00-16:00
    after_hours: 16:00-20:00
    market_closed: after 20:00 or weekends
    """
```

In `get_orchestrator_status()`, populate the new fields:
- `session_phase`: call `_compute_session_phase()`
- `pre_market_complete`: from `orchestrator._pre_market_done_today`
- `pre_market_completed_at`: derive from decision log (find today's first `regime_classification` decision timestamp)
- Per-strategy fields: query strategies dict for `is_active`, `daily_pnl`, `trade_count_today`, open positions from order_manager, health from health_monitor
- `operating_window`: read from strategy config objects
- Throttle metrics: call `throttler.get_consecutive_losses()`, `get_rolling_sharpe()`, `get_drawdown_from_peak()` with trade data

Note: The Orchestrator needs to expose its `_pre_market_done_today` flag. Add a property:
```python
@property
def pre_market_complete(self) -> bool:
    return self._pre_market_done_today
```

**`argus/api/routes/orchestrator.py` — decisions endpoint:**

Add optional `date` query parameter:
```python
@router.get("/decisions")
async def get_orchestrator_decisions(
    limit: int = 50,
    offset: int = 0,
    date: str | None = None,  # "2026-02-27" format, default today
    ...
)
```

If `date` is provided, filter decisions to that date. The `trade_logger.get_orchestrator_decisions()` may need a date filter added — check the current implementation. If it doesn't support date filtering, add it.

**`argus/core/orchestrator.py`:**

Add property:
```python
@property
def pre_market_complete(self) -> bool:
    """Whether pre-market routine has completed today."""
    return self._pre_market_done_today
```

### Tests
- Test `_compute_session_phase()` with various times (pre-market, open, midday, power hour, after hours, weekend)
- Test extended `/orchestrator/status` response includes new fields
- Test `/orchestrator/decisions?date=2026-02-27` filters correctly
- Target: ~12 new tests in `tests/api/test_orchestrator_routes.py` (create if doesn't exist)

### Acceptance
- `GET /orchestrator/status` returns all new fields
- `GET /orchestrator/decisions?date=today` returns only today's decisions
- All existing orchestrator tests still pass
- New tests pass

---

## Session 2: Throttle Override Backend

### Goal
Add throttle override capability to the Orchestrator backend and expose via API.

### Files to modify

**`argus/core/orchestrator.py`:**

Add override tracking:
```python
# In __init__:
self._override_until: dict[str, datetime] = {}  # strategy_id → expiry datetime

# New method:
async def override_throttle(
    self, strategy_id: str, duration_minutes: int, reason: str
) -> None:
    """Temporarily override throttle for a strategy.
    
    Args:
        strategy_id: Strategy to override.
        duration_minutes: How long the override lasts. Use 999 for rest-of-day.
        reason: Human-readable reason for the override.
    """
    now = self._clock.now()
    if duration_minutes >= 999:
        # Rest of day = 4:00 PM ET today
        et_tz = ZoneInfo("America/New_York")
        now_et = now.astimezone(et_tz)
        eod = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
        self._override_until[strategy_id] = eod
    else:
        self._override_until[strategy_id] = now + timedelta(minutes=duration_minutes)
    
    # Reactivate the strategy
    strategy = self._strategies.get(strategy_id)
    if strategy:
        strategy.is_active = True
    
    # Log the override decision
    await self._log_decision(
        "throttle_override",
        strategy_id,
        {"duration_minutes": duration_minutes, "reason": reason},
        f"Manual throttle override: {reason}",
    )

# In _calculate_allocations, before applying throttle:
# Check if override is active
def _is_override_active(self, strategy_id: str) -> bool:
    if strategy_id not in self._override_until:
        return False
    now = self._clock.now()
    if now >= self._override_until[strategy_id]:
        del self._override_until[strategy_id]
        return False
    return True
```

Modify `_calculate_allocations` to skip throttle when override is active:
```python
# After computing throttle_results:
for sid in eligible_ids:
    if self._is_override_active(sid):
        throttle_results[sid] = ThrottleAction.NONE  # Override in effect
```

**`argus/api/routes/orchestrator.py`:**

New endpoint:
```python
class ThrottleOverrideRequest(BaseModel):
    duration_minutes: int  # 30, 60, or 999 (rest of day)
    reason: str

@router.post("/strategies/{strategy_id}/override-throttle", response_model=ControlResponse)
async def override_strategy_throttle(
    strategy_id: str,
    request: ThrottleOverrideRequest,
    _auth: dict = Depends(require_auth),
    state: AppState = Depends(get_app_state),
) -> ControlResponse:
```

**`argus/api/dev_state.py`:**

Update MockOrchestrator to support override:
```python
_override_until: dict[str, datetime] = field(default_factory=dict)

async def override_throttle(self, strategy_id: str, duration_minutes: int, reason: str) -> None:
    """Mock override — just set the flag."""
    self._override_until[strategy_id] = datetime.now(UTC) + timedelta(minutes=duration_minutes)

def _is_override_active(self, strategy_id: str) -> bool:
    if strategy_id not in self._override_until:
        return False
    return datetime.now(UTC) < self._override_until[strategy_id]
```

### Tests
- Test `override_throttle()` sets override flag, reactivates strategy
- Test `_is_override_active()` returns True within duration, False after
- Test `_calculate_allocations` respects active override
- Test API endpoint returns success, logs decision
- Test API endpoint with invalid strategy_id returns 404
- Target: ~8 new tests

### Acceptance
- Override endpoint works in dev mode
- Overriding a suspended strategy reactivates it
- Override expires after duration_minutes
- Decision logged for audit trail

---

## Session 3: Dev Mode Enhancement

### Goal
Make the dev mode orchestrator state realistic enough to exercise all Orchestrator page features, including a throttled strategy scenario.

### Files to modify

**`argus/api/dev_state.py`:**

Update `_create_mock_orchestrator()`:
- Set ORB Scalp to `ThrottleAction.REDUCE` with reason "Throttled to minimum (10%): 3 consecutive losses"
- Set ORB Scalp allocation to 10% ($8,000) instead of 20% ($20,000)
- Redistribute freed capital to remaining strategies (≈23.3% each)

Update `_seed_orchestrator_decisions()` to include:
1. Pre-market regime classification (9:25 AM) with indicator values
2. Pre-market allocations (one per strategy, 9:25 AM)
3. Strategy activations (9:25 AM)  
4. Mid-morning regime re-check (10:00 AM) — regime unchanged
5. ORB Scalp throttle event (10:45 AM) — "3 consecutive losses → REDUCE"
6. Allocation update reflecting throttle (10:45 AM) — ORB Scalp reduced
7. Mid-day regime re-check (11:00 AM) — still bullish_trending
8. Afternoon strategy activation note (2:00 PM)

This gives the Decision Timeline ~12-15 realistic entries.

Add operating window data to the mock strategy configs by reading from actual YAML files or hardcoding:
```python
STRATEGY_WINDOWS = {
    "orb_breakout": {"earliest_entry": "09:35", "latest_entry": "11:30", "force_close": "15:50"},
    "orb_scalp": {"earliest_entry": "09:45", "latest_entry": "11:30", "force_close": "15:50"},
    "vwap_reclaim": {"earliest_entry": "10:00", "latest_entry": "12:00", "force_close": "15:50"},
    "afternoon_momentum": {"earliest_entry": "14:00", "latest_entry": "15:30", "force_close": "15:45"},
}
```

### Acceptance
- `--dev` mode shows ORB Scalp as throttled (REDUCE)
- Decision timeline has 12+ entries spanning mock trading day
- All four strategies have operating windows in status response
- Session phase reflects mock time appropriately

---

## Session 4: Frontend Types + Hooks + API Client + WS Wiring

### Goal
Wire up the frontend data layer for the Orchestrator page.

### Files to create/modify

**`argus/ui/src/api/types.ts`:**

Extend `AllocationInfo`:
```typescript
export interface OperatingWindow {
  earliest_entry: string;
  latest_entry: string;
  force_close: string;
}

export interface AllocationInfo {
  // existing fields...
  operating_window: OperatingWindow | null;
  consecutive_losses: number;
  rolling_sharpe: number | null;
  drawdown_pct: number;
  is_active: boolean;
  health_status: string;
  trade_count_today: number;
  daily_pnl: number;
  open_position_count: number;
  override_active: boolean;
  override_until: string | null;
}

export interface OrchestratorStatusResponse {
  // existing fields...
  session_phase: string;
  pre_market_complete: boolean;
  pre_market_completed_at: string | null;
}

export interface DecisionInfo {
  id: string;
  date: string;
  decision_type: string;
  strategy_id: string | null;
  details: Record<string, unknown> | null;
  rationale: string | null;
  created_at: string;
}

export interface DecisionsResponse {
  decisions: DecisionInfo[];
  total: number;
  limit: number;
  offset: number;
  timestamp: string;
}

export interface ThrottleOverrideRequest {
  duration_minutes: number;
  reason: string;
}
```

**`argus/ui/src/api/client.ts`:**

Add functions:
```typescript
export function getOrchestratorDecisions(date?: string): Promise<DecisionsResponse> {
  const params = new URLSearchParams();
  params.set('limit', '100');
  if (date) params.set('date', date);
  return fetchWithAuth<DecisionsResponse>(`/orchestrator/decisions?${params}`);
}

export function triggerRebalance(): Promise<{ success: boolean; message: string }> {
  return fetchWithAuth('/orchestrator/rebalance', { method: 'POST' });
}

export function overrideThrottle(
  strategyId: string, body: ThrottleOverrideRequest
): Promise<{ success: boolean; message: string }> {
  return fetchWithAuth(`/orchestrator/strategies/${strategyId}/override-throttle`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}
```

**`argus/ui/src/hooks/useOrchestratorDecisions.ts`:**

```typescript
export function useOrchestratorDecisions(date?: string) {
  return useQuery<DecisionsResponse, Error>({
    queryKey: ['orchestrator-decisions', date ?? 'today'],
    queryFn: () => getOrchestratorDecisions(date),
    refetchInterval: 30_000,
  });
}
```

**`argus/ui/src/hooks/useOrchestratorMutations.ts`:**

```typescript
export function useRebalanceMutation() { ... }
export function useThrottleOverrideMutation() { ... }
```

Both call `queryClient.invalidateQueries(['orchestrator-status'])` on success.

**`argus/ui/src/stores/live.ts`:**

Add WS event handling for orchestrator events:
```typescript
// In the WS message handler, when event type matches orchestrator.*:
if (event.type.startsWith('orchestrator.')) {
  queryClient.invalidateQueries({ queryKey: ['orchestrator-status'] });
  queryClient.invalidateQueries({ queryKey: ['orchestrator-decisions'] });
}
```

Note: Need to access queryClient from the store. Use the pattern already established — check how other WS events trigger refetches.

**`argus/ui/src/stores/orchestratorUI.ts`:**

```typescript
interface OrchestratorUIState {
  overrideDialogOpen: boolean;
  overrideTargetStrategy: string | null;
  openOverrideDialog: (strategyId: string) => void;
  closeOverrideDialog: () => void;
}
```

**`argus/ui/src/hooks/index.ts`:**

Export new hooks.

### Acceptance
- Types compile cleanly
- Hooks return data in dev mode
- WS events trigger query invalidation
- Mutations send requests and invalidate queries

---

## Session 5: OrchestratorPage + RegimePanel + StrategyCoverageTimeline

### Goal
Build the page shell, regime section, and coverage timeline SVG.

### Files to create

**`argus/ui/src/pages/OrchestratorPage.tsx`:**

Vertical layout with sections:
```tsx
<AnimatedPage>
  <div className="space-y-6">
    <RegimePanel />
    <StrategyCoverageTimeline />
    <CapitalAllocation compact />  {/* reuse existing */}
    <StrategyOperationsGrid />
    <DecisionTimeline />
    <GlobalControls />
  </div>
</AnimatedPage>
```

Wrap in stagger animation using `motion.div` with `staggerChildren` variant (existing pattern from other pages).

**`argus/ui/src/features/orchestrator/RegimePanel.tsx`:**

Full-width card containing:
- **Left side:** Session phase badge (pill: "Market Open", "Pre-Market", etc. with appropriate color), Market regime badge (reuse `RegimeBadge`), next regime check countdown ("Next check in 14m")
- **Right side:** RegimeInputBreakdown component

Desktop: flex-row. Mobile: stacked.

Session phase colors:
- pre_market: argus-accent (blue)
- market_open: argus-profit (green)  
- midday: argus-warning (yellow)
- power_hour: orange-400
- after_hours: argus-text-dim (gray)
- market_closed: argus-text-dim

**`argus/ui/src/features/orchestrator/RegimeInputBreakdown.tsx`:**

Three-row compact display showing the regime classification inputs:

```
Trend    SPY $525.50 > SMA-20 $520.30 ✓  > SMA-50 $515.80 ✓  → +2 Strong Bull
Vol      12.5% annualized → Normal (< 16% threshold)
Momentum +1.25% 5d ROC → Bullish ✓ (> +1% threshold)
```

Each row: label, value, directional indicator (✓ green / ✗ red / — neutral), interpretation.

Use the indicator values from `orchestrator.regime_indicators` (spy_price, spy_sma_20, spy_sma_50, spy_roc_5d, spy_realized_vol_20d). Compute trend score and vol bucket client-side using the same thresholds as the backend (from orchestrator config or hardcoded V1 values).

**`argus/ui/src/features/orchestrator/StrategyCoverageTimeline.tsx`:**

Custom SVG component.

Props:
```typescript
interface StrategyCoverageTimelineProps {
  allocations: AllocationInfo[];  // from orchestrator status
}
```

Constants:
```typescript
const MARKET_START = 570;  // 9:30 AM in minutes
const MARKET_END = 960;    // 4:00 PM in minutes  
const TOTAL_MINUTES = MARKET_END - MARKET_START; // 390

// Strategy colors (match Badge system)
const STRATEGY_COLORS: Record<string, string> = {
  orb_breakout: '#60a5fa',    // blue-400
  orb_scalp: '#c084fc',       // purple-400
  vwap_reclaim: '#2dd4bf',    // teal-400
  afternoon_momentum: '#fbbf24', // amber-400
};
```

SVG structure:
- Time axis labels along top (9:30, 10:00, 10:30, ..., 4:00)
- Vertical grid lines at each hour
- Per-strategy row: colored rect from earliest_entry to latest_entry
- Throttled/paused strategies: reduced opacity + diagonal stripe pattern
- "Now" marker: vertical red dashed line with time label
- Strategy labels on left margin
- Row height: 28px, total height: labels + (rows × 28) + axis

Responsive:
- Desktop ≥1024px: full width, time labels every 30 min
- Tablet 640–1023px: full width, time labels every hour
- Mobile <640px: full width, time labels every 2 hours, abbreviated strategy names (O, S, V, A)

### Acceptance
- Page renders at `/orchestrator` route
- RegimePanel shows session phase, regime, indicators breakdown
- Coverage timeline shows 4 strategy bars with correct time positioning
- "Now" marker visible at current ET time
- Throttled strategy (ORB Scalp in dev mode) shows dimmed bar
- Responsive across all breakpoints

---

## Session 6: StrategyOperationsGrid + StrategyOperationsCard

### Goal
Build the per-strategy operational status cards with inline controls.

### Files to create

**`argus/ui/src/features/orchestrator/StrategyOperationsGrid.tsx`:**

2-column grid on desktop, 1-column on mobile. Maps `allocations` array to cards.

**`argus/ui/src/features/orchestrator/StrategyOperationsCard.tsx`:**

Per-strategy card with sections:

**Header row:**
- Strategy name + `StrategyBadge`
- Pipeline stage badge (from strategy config, if available)
- Active/Paused/Suspended status dot
- Pause/Resume toggle button (instant, no confirmation)

**Allocation section:**
- Allocation: "$20,000 (20%)" with `AnimatedNumber`
- Deployed: "$13,500 (68% of allocation)" 
- Mini progress bar showing deployed vs allocated

**Throttle section (only visible when throttled):**
- `ThrottleBadge` (REDUCE or SUSPEND)
- Reason text (e.g., "3 consecutive losses")
- Metric details: "Consecutive Losses: 3 | Rolling Sharpe: -0.12 | Drawdown: 4.2%"
- "Override Throttle" button → opens ThrottleOverrideDialog (from Zustand store)

**Today's performance:**
- Trades: 5 (3W / 2L)
- P&L: +$234.50 (green/red)
- Open positions: 2

**Operating window:**
- Text: "9:35 – 11:30 AM ET"
- Status: "Active" (green) if current time is within window, "Inactive" (gray) otherwise

**Health:**
- StatusDot (green/yellow/red) + label

### Acceptance
- All 4 strategy cards render in dev mode
- ORB Scalp shows throttle section with REDUCE badge and "Override" button
- Pause/resume toggles work (calls existing control endpoints)
- Performance metrics show mock data
- Responsive layout works

---

## Session 7: DecisionTimeline + GlobalControls + ThrottleOverrideDialog

### Goal
Build the decision log viewer, global controls section, and throttle override dialog.

### Files to create

**`argus/ui/src/features/orchestrator/DecisionTimeline.tsx`:**

Scrollable card showing today's orchestrator decisions. Uses `useOrchestratorDecisions()` hook.

Layout: vertical timeline with left-aligned timestamps.

Each entry (`DecisionTimelineItem`):
- **Timestamp** (left column, 60px): "9:25 AM" in muted text
- **Type icon** (middle): use lucide icons by decision_type:
  - `regime_classification` → `Compass`
  - `allocation` → `PieChart`
  - `throttle_override` → `ShieldAlert`
  - `activation` / `strategy_activated` → `Play`
  - `suspension` / `strategy_suspended` → `Pause`
  - `eod_review` → `Moon`
  - default → `Clock`
- **Content** (right): decision rationale text, strategy badge if applicable
- **Severity** color: connecting line color (green for activations, yellow for throttle, red for suspensions, blue for regime, gray for info)

Max height: 400px with overflow-y scroll. Show "No decisions yet" empty state if list is empty.

**`argus/ui/src/features/orchestrator/GlobalControls.tsx`:**

Section at bottom of page with:
- "Force Rebalance" button (blue, confirmation dialog: "Recalculate all allocations based on current state?")
- "Emergency Flatten All" button (red, reuse existing modal pattern from EmergencyControls)
- "Emergency Pause All" button (orange, reuse existing modal pattern)

Desktop: horizontal button row. Mobile: stacked.

For the confirmation dialogs, create a lightweight reusable `ConfirmDialog` component or reuse the pattern from `EmergencyControls.tsx`.

**`argus/ui/src/features/orchestrator/ThrottleOverrideDialog.tsx`:**

Modal/dialog that opens from Zustand store state (`orchestratorUI`).

Contents:
- Title: "Override Throttle — {strategy_name}"
- Warning text: "This temporarily overrides risk controls. The strategy will resume trading."
- Duration dropdown: "30 minutes" | "1 hour" | "Rest of day"
- Reason textarea (required, min 10 chars)
- Cancel / Confirm buttons
- Confirm calls `overrideThrottle` mutation, closes dialog, shows toast or success message

Styled with appropriate severity (orange/amber border, warning icon).

### Acceptance
- Decision timeline shows all mock decisions in chronological order
- Decision types have correct icons and colors
- Force rebalance works (calls API, refreshes data)
- Emergency controls work
- Throttle override dialog opens from strategy card, submits correctly
- Duration + reason are required

---

## Session 8: Nav Update + Polish + Vitest + Skeleton

### Goal
Wire up navigation, add loading states, write tests, final responsive polish.

### Files to modify

**`argus/ui/src/layouts/Sidebar.tsx`:**

Add Orchestrator as 6th nav item:
```typescript
import { Gauge } from 'lucide-react';  // or Settings2 or Sliders

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/trades', icon: ScrollText, label: 'Trades' },
  { to: '/performance', icon: TrendingUp, label: 'Performance' },
  { to: '/patterns', icon: BookOpen, label: 'Pattern Library' },
  { to: '/orchestrator', icon: Gauge, label: 'Orchestrator' },
  { to: '/system', icon: Activity, label: 'System' },
];
```

**`argus/ui/src/layouts/MobileNav.tsx`:**

Add Orchestrator. With 6 items:
- Shrink labels to `text-[9px]` (from `text-[10px]`)
- Use shorter label: "Orch" instead of "Orchestrator"
- Keep all 6 visible — defer "More" menu to 21d

```typescript
const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dash' },
  { to: '/trades', icon: ScrollText, label: 'Trades' },
  { to: '/performance', icon: TrendingUp, label: 'Perf' },
  { to: '/patterns', icon: BookOpen, label: 'Patterns' },
  { to: '/orchestrator', icon: Gauge, label: 'Orch' },
  { to: '/system', icon: Activity, label: 'System', showStatusDot: true },
];
```

**`argus/ui/src/App.tsx`:**

Add route:
```tsx
<Route path="/orchestrator" element={<OrchestratorPage />} />
```

Import `OrchestratorPage` lazily if the pattern is established, otherwise direct import.

**Keyboard shortcuts:** Update to 1–6 (Orchestrator = 6, System = 7 with 7 pages, or keep System at 6 and Orchestrator at 5 — check what makes sense with the nav order). Actually, since Orchestrator is 5th in the list and System is 6th: shortcuts 1–6 map to the 6 pages in order.

**`argus/ui/src/features/orchestrator/OrchestratorSkeleton.tsx`:**

Skeleton matching the page layout:
- Regime panel skeleton (badge placeholder, indicator rows)
- Coverage timeline skeleton (gray bars)
- Strategy cards skeleton (4 cards with placeholder content)
- Decision timeline skeleton (list item placeholders)

**Vitest tests:**

Create `argus/ui/src/features/orchestrator/__tests__/`:

1. `OrchestratorPage.test.tsx` — renders without crash, shows key sections
2. `StrategyCoverageTimeline.test.tsx` — renders SVG bars for each strategy, shows "now" marker
3. `RegimeInputBreakdown.test.tsx` — shows indicator values from mock data
4. `ThrottleOverrideDialog.test.tsx` — opens and closes, validates required fields
5. `StrategyOperationsCard.test.tsx` — shows throttle section when throttled
6-8. Additional as needed

Target: 8 new Vitest tests.

### Final responsive check

Verify at all breakpoints:
- 393px (iPhone): all sections stacked, coverage timeline readable, mobile nav fits 6 items
- 834px (iPad portrait): comfortable layout, coverage timeline full-width
- 1194px (iPad landscape): 2-column strategy grid
- 1512px (MacBook): full desktop layout

### Acceptance
- Orchestrator appears in both Sidebar and MobileNav
- Keyboard shortcut 5 navigates to Orchestrator
- Page has proper skeleton loading state
- All Vitest tests pass
- All existing tests still pass (1558 pytest + 70 Vitest baseline)
- Responsive layout verified at all 4 breakpoints

---

## Component Dependency Graph

```
OrchestratorPage
├── RegimePanel
│   ├── RegimeBadge (existing)
│   └── RegimeInputBreakdown (new)
├── StrategyCoverageTimeline (new, custom SVG)
├── CapitalAllocation (existing, reuse)
├── StrategyOperationsGrid
│   └── StrategyOperationsCard (new)
│       ├── StrategyBadge (existing)
│       ├── ThrottleBadge (existing)
│       ├── AnimatedNumber (existing)
│       ├── StatusDot (existing)
│       └── → ThrottleOverrideDialog (via Zustand)
├── DecisionTimeline (new)
│   └── DecisionTimelineItem (new)
├── GlobalControls (new)
│   └── ConfirmDialog pattern (from EmergencyControls)
└── ThrottleOverrideDialog (new, mounted in page)
```

## Files Created/Modified Summary

### New files
- `argus/ui/src/pages/OrchestratorPage.tsx`
- `argus/ui/src/features/orchestrator/index.ts`
- `argus/ui/src/features/orchestrator/RegimePanel.tsx`
- `argus/ui/src/features/orchestrator/RegimeInputBreakdown.tsx`
- `argus/ui/src/features/orchestrator/StrategyCoverageTimeline.tsx`
- `argus/ui/src/features/orchestrator/StrategyOperationsGrid.tsx`
- `argus/ui/src/features/orchestrator/StrategyOperationsCard.tsx`
- `argus/ui/src/features/orchestrator/DecisionTimeline.tsx`
- `argus/ui/src/features/orchestrator/DecisionTimelineItem.tsx`
- `argus/ui/src/features/orchestrator/GlobalControls.tsx`
- `argus/ui/src/features/orchestrator/ThrottleOverrideDialog.tsx`
- `argus/ui/src/features/orchestrator/OrchestratorSkeleton.tsx`
- `argus/ui/src/hooks/useOrchestratorDecisions.ts`
- `argus/ui/src/hooks/useOrchestratorMutations.ts`
- `argus/ui/src/stores/orchestratorUI.ts`
- `tests/api/test_orchestrator_extended.py` (or extend existing)
- Vitest test files

### Modified files
- `argus/core/orchestrator.py` (add pre_market_complete property, override_until, override_throttle)
- `argus/api/routes/orchestrator.py` (extend status response, decisions date filter, new override endpoint)
- `argus/api/dev_state.py` (richer mock data with throttle scenario)
- `argus/ui/src/api/types.ts` (extended types)
- `argus/ui/src/api/client.ts` (new API functions)
- `argus/ui/src/hooks/index.ts` (exports)
- `argus/ui/src/stores/live.ts` (WS event → query invalidation)
- `argus/ui/src/layouts/Sidebar.tsx` (6th nav item)
- `argus/ui/src/layouts/MobileNav.tsx` (6th nav item)
- `argus/ui/src/App.tsx` (new route)

---

## Design Reference

### Strategy Colors (from Badge.tsx)
- ORB Breakout: `#60a5fa` (blue-400)
- ORB Scalp: `#c084fc` (purple-400)
- VWAP Reclaim: `#2dd4bf` (teal-400)
- Afternoon Momentum: `#fbbf24` (amber-400)

### Session Phase Colors
- pre_market: `bg-argus-accent/15 text-argus-accent`
- market_open: `bg-argus-profit-dim text-argus-profit`
- midday: `bg-argus-warning-dim text-argus-warning`
- power_hour: `bg-orange-400/15 text-orange-400`
- after_hours: `bg-argus-surface-2 text-argus-text-dim`
- market_closed: `bg-argus-surface-2 text-argus-text-dim`

### Decision Type Icons (lucide-react)
- regime_classification: Compass
- allocation: PieChart
- throttle_override: ShieldAlert
- activation: Play
- suspension: Pause
- eod_review: Moon
- default: Clock

### Throttle Status Display
- NONE: No throttle section shown
- REDUCE: Yellow badge "REDUCED", show metrics, "Override" button
- SUSPEND: Red badge "SUSPENDED", show metrics, "Override" button

---

## Deferred to Sprint 21d

1. **PreMarketCard / EodSummaryCard** as dedicated components (info accessible via Decision Timeline)
2. **Multi-day regime history** visualization
3. **Decision timeline filtering** by type or strategy
4. **"More" menu** for mobile nav (if 6 items prove too tight)
5. **AI insights placeholder** sections on strategy cards (for V2)
