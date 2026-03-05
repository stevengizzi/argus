# Sprint 21b — Complete Materials Package

---

## Part 1: Claude Code Session Prompts (Copy-Paste Ready)

---

### Session 1 Prompt: API Extensions

```
# Sprint 21b Session 1: API Extensions

Read `docs/sprints/SPRINT_21B_SPEC.md` — the full sprint spec. Focus on **Session 1: API Extensions**.

Read these files for context:
- `CLAUDE.md` — project state, architecture rules
- `argus/api/routes/orchestrator.py` — existing 3 endpoints + response models
- `argus/core/orchestrator.py` — Orchestrator class (need to add `pre_market_complete` property)
- `argus/core/regime.py` — RegimeClassifier, RegimeIndicators
- `argus/core/throttle.py` — PerformanceThrottler, ThrottleAction, StrategyAllocation
- `argus/api/dependencies.py` — AppState for dependency injection
- `argus/api/dev_state.py` — MockOrchestrator (needs to support new fields)
- `argus/analytics/trade_logger.py` — `get_orchestrator_decisions()` method (check if it supports date filtering)
- `tests/api/` — existing API test patterns

## Tasks

### 1. Add `pre_market_complete` property to Orchestrator
In `argus/core/orchestrator.py`, add:
```python
@property
def pre_market_complete(self) -> bool:
    """Whether pre-market routine has completed today."""
    return self._pre_market_done_today
```

And add matching property to MockOrchestrator in `argus/api/dev_state.py`:
```python
@property
def pre_market_complete(self) -> bool:
    return True  # Always complete in dev mode
```

### 2. Add session phase helper
In `argus/api/routes/orchestrator.py`, add:
```python
def _compute_session_phase() -> str:
    """Compute current session phase from ET time."""
    from zoneinfo import ZoneInfo
    now_et = datetime.now(ZoneInfo("America/New_York"))
    t = now_et.time()
    weekday = now_et.weekday()
    
    if weekday >= 5:  # Weekend
        return "market_closed"
    if t < time(9, 30):
        return "pre_market"
    if t < time(11, 30):
        return "market_open"
    if t < time(14, 0):
        return "midday"
    if t < time(16, 0):
        return "power_hour"
    if t < time(20, 0):
        return "after_hours"
    return "market_closed"
```

### 3. Add OperatingWindow model and extend AllocationInfo
Add to `argus/api/routes/orchestrator.py`:
```python
class OperatingWindow(BaseModel):
    earliest_entry: str
    latest_entry: str
    force_close: str
```

Extend AllocationInfo with these new fields:
- `operating_window: OperatingWindow | None`
- `consecutive_losses: int`
- `rolling_sharpe: float | None`
- `drawdown_pct: float`
- `is_active: bool`
- `health_status: str`
- `trade_count_today: int`
- `daily_pnl: float`
- `open_position_count: int`
- `override_active: bool`  (default False for now — Session 2 adds the backend)
- `override_until: str | None`  (default None for now)

### 4. Extend OrchestratorStatusResponse
Add:
- `session_phase: str`
- `pre_market_complete: bool`
- `pre_market_completed_at: str | None`

### 5. Populate new fields in get_orchestrator_status()
For each strategy allocation:
- `operating_window`: Read from strategy config if available. Strategy objects have `._config` with operating_window settings. Check if strategies in `state.strategies` expose these — if not, hardcode a lookup dict for the 4 known strategies.
- `consecutive_losses`: Call `state.trade_logger.get_trades_by_strategy(sid, limit=20)` and count consecutive losses from most recent
- `rolling_sharpe`: Call `state.trade_logger.get_daily_pnl(strategy_id=sid)` and compute via PerformanceThrottler helper or inline
- `drawdown_pct`: Same data, compute drawdown from peak
- `is_active`: `state.strategies[sid].is_active`
- `health_status`: Check `state.health_monitor` if available, else "healthy"
- `trade_count_today`: `state.strategies[sid]._trade_count_today` (or equivalent)
- `daily_pnl`: `state.strategies[sid]._daily_pnl` (or equivalent)
- `open_position_count`: Count from order_manager positions matching strategy
- `pre_market_completed_at`: Query decisions for today's first regime_classification, use its created_at

### 6. Add date filter to GET /orchestrator/decisions
Add `date: str | None = None` query param. Check if `trade_logger.get_orchestrator_decisions()` supports date filtering. If not, add a `date` parameter to that method. Default to today's date if no date provided.

### 7. Write tests
Create or extend `tests/api/test_orchestrator_extended.py`:
- Test `_compute_session_phase()` with mocked times for each phase
- Test extended status response has all new fields
- Test decisions date filter returns only matching date
- Test decisions without date filter returns all
- Test operating_window populated for known strategies
- Test throttle metrics (consecutive_losses, rolling_sharpe, drawdown_pct) present
Target: ~12 new tests.

## Constraints
- Don't break existing tests (1558 pytest + 70 Vitest baseline)
- Follow existing code patterns in orchestrator.py routes
- Use Pydantic models for all response types
- Handle gracefully when data is unavailable (return defaults/None)
```

---

### Session 2 Prompt: Throttle Override Backend

```
# Sprint 21b Session 2: Throttle Override Backend

Read `docs/sprints/SPRINT_21B_SPEC.md` — focus on **Session 2**.

Read these files:
- `argus/core/orchestrator.py` — full Orchestrator (add override logic)
- `argus/core/throttle.py` — ThrottleAction, PerformanceThrottler
- `argus/api/routes/orchestrator.py` — add new endpoint (check Session 1 changes already in place)
- `argus/api/routes/controls.py` — existing control endpoint patterns (ControlResponse model)
- `argus/api/dev_state.py` — MockOrchestrator (add override support)
- `tests/core/test_orchestrator.py` — existing orchestrator tests

## Tasks

### 1. Add override tracking to Orchestrator
In `argus/core/orchestrator.py`:

In `__init__`:
```python
self._override_until: dict[str, datetime] = {}  # strategy_id → expiry
```

Add methods:
```python
async def override_throttle(self, strategy_id: str, duration_minutes: int, reason: str) -> None:
    """Temporarily override throttle for a strategy."""
    # If duration >= 999, set to 4:00 PM ET today (rest of day)
    # Otherwise, set to now + duration_minutes
    # Reactivate the strategy (is_active = True)
    # Log decision via _log_decision("throttle_override", ...)
    # Publish StrategyActivatedEvent

def _is_override_active(self, strategy_id: str) -> bool:
    """Check if a throttle override is currently active."""
    # Return False if not in dict
    # Clean up expired overrides
    # Return True if still active

@property
def override_until(self) -> dict[str, datetime]:
    """Get active override expiry times."""
    return self._override_until.copy()
```

### 2. Modify _calculate_allocations to respect overrides
In the throttle checking loop, before applying the result:
```python
for sid in eligible_ids:
    trades = await self._trade_logger.get_trades_by_strategy(sid, limit=200)
    daily_pnl = await self._trade_logger.get_daily_pnl(strategy_id=sid)
    action = self._throttler.check(sid, trades, daily_pnl)
    # Override check
    if self._is_override_active(sid) and action in (ThrottleAction.REDUCE, ThrottleAction.SUSPEND):
        action = ThrottleAction.NONE  # Override in effect
    throttle_results[sid] = action
```

### 3. Add API endpoint
In `argus/api/routes/orchestrator.py`:
```python
class ThrottleOverrideRequest(BaseModel):
    duration_minutes: int  # 30, 60, or 999 (rest of day)
    reason: str

@router.post("/strategies/{strategy_id}/override-throttle")
async def override_strategy_throttle(strategy_id, request, auth, state):
    # Validate strategy exists
    # Call orchestrator.override_throttle()
    # Return ControlResponse (reuse from controls.py — import it)
```

### 4. Update AllocationInfo population
In `get_orchestrator_status()`, populate the override fields added in Session 1:
- `override_active`: `orchestrator._is_override_active(strategy_id)`
- `override_until`: format the datetime if active, else None

### 5. Update MockOrchestrator
Add `_override_until` field and `override_throttle` / `_is_override_active` methods to the mock.

### 6. Write tests
- Test `override_throttle()` sets flag and reactivates strategy
- Test `_is_override_active()` returns True within duration, False after expiry
- Test `_calculate_allocations` skips throttle when override active
- Test override with duration=999 sets to 4:00 PM ET
- Test API endpoint returns 200 and logs decision
- Test API endpoint with unknown strategy returns 404
- Test override expires correctly (mock clock forward)
Target: ~8 new tests.

## Constraints
- Override must be transient — stored in memory, not DB (lost on restart is acceptable)
- Decision logging for override is mandatory (audit trail)
- Don't modify PerformanceThrottler itself — override logic lives in Orchestrator
```

---

### Session 3 Prompt: Dev Mode Enhancement

```
# Sprint 21b Session 3: Dev Mode Enhancement

Read `docs/sprints/SPRINT_21B_SPEC.md` — focus on **Session 3**.

Read these files:
- `argus/api/dev_state.py` — current mock data (study all of it carefully — it's ~1250 lines)
- `argus/api/routes/orchestrator.py` — the extended response models from Sessions 1-2
- `config/strategies/*.yaml` — operating window configs for all 4 strategies
- `argus/core/regime.py` — MarketRegime enum values
- `argus/core/throttle.py` — ThrottleAction enum values

## Goal
Make dev mode exercise all Orchestrator page features: regime classification, throttled strategy, rich decision timeline, operating windows, session phase.

## Tasks

### 1. Update _create_mock_orchestrator()
Change from "all strategies healthy" to a realistic mid-session state:
- **ORB Breakout:** Active, ThrottleAction.NONE, 20% allocation ($20,000)
- **ORB Scalp:** ThrottleAction.REDUCE, 10% allocation ($8,000), reason: "Throttled to minimum (10%): 3 consecutive losses"
- **VWAP Reclaim:** Active, ThrottleAction.NONE, 25% allocation ($20,000) — gets extra from ORB Scalp reduction
- **Afternoon Momentum:** Active, ThrottleAction.NONE, 25% allocation ($20,000)

Total: 80% deployed + 20% reserve = 100%.

### 2. Enrich _seed_orchestrator_decisions()
Replace the current sparse decisions with a realistic trading day timeline. Add decisions with timestamps spread across the day:

```
9:25 AM — regime_classification: SPY above both SMAs, bullish momentum, 12.5% vol → bullish_trending
9:25 AM — allocation: ORB Breakout 20% ($20,000)
9:25 AM — allocation: ORB Scalp 20% ($20,000)
9:25 AM — allocation: VWAP Reclaim 20% ($20,000)
9:25 AM — allocation: Afternoon Momentum 20% ($20,000)
9:25 AM — activation: ORB Breakout activated
9:25 AM — activation: ORB Scalp activated
9:25 AM — activation: VWAP Reclaim activated (will begin scanning at 10:00 AM)
10:00 AM — regime_recheck: bullish_trending unchanged, SPY +0.3%
10:30 AM — regime_recheck: bullish_trending → range_bound (SPY dropped below SMA-20)
10:30 AM — allocation: Rebalance — regime change, allocations unchanged (all strategies eligible in range_bound)
10:45 AM — throttle: ORB Scalp suspended — 3 consecutive losses (REDUCE)
10:45 AM — allocation: ORB Scalp reduced to 10% ($8,000), excess redistributed
11:00 AM — regime_recheck: range_bound → bullish_trending (SPY reclaimed SMA-20)
2:00 PM — activation: Afternoon Momentum scanning started
```

That's ~15 decisions. Make sure the timestamps are realistic `created_at` values (ISO format).

### 3. Add operating windows to mock strategy state
Either read from YAML configs or hardcode:
```python
STRATEGY_OPERATING_WINDOWS = {
    "orb_breakout": {"earliest_entry": "09:35", "latest_entry": "11:30", "force_close": "15:50"},
    "orb_scalp": {"earliest_entry": "09:45", "latest_entry": "11:30", "force_close": "15:50"},
    "vwap_reclaim": {"earliest_entry": "10:00", "latest_entry": "12:00", "force_close": "15:50"},
    "afternoon_momentum": {"earliest_entry": "14:00", "latest_entry": "15:30", "force_close": "15:45"},
}
```

Make this accessible to the orchestrator status route. The route needs to populate `operating_window` per strategy — check how the mock strategies expose config. You may need to add the operating window to MockStrategy's config object.

### 4. Enrich mock strategy metrics for throttle display
The MockStrategy objects need realistic values for the new AllocationInfo fields:
- `orb_scalp`: consecutive_losses=3, rolling_sharpe=-0.12, drawdown_pct=0.042
- Others: consecutive_losses=0-1, rolling_sharpe=0.8-1.5, drawdown_pct=0.01-0.02

### 5. Verify dev mode works
Run `python -m argus.api --dev` and test:
- `GET /api/v1/orchestrator/status` returns all extended fields
- `GET /api/v1/orchestrator/decisions` returns ~15 decisions
- ORB Scalp shows as throttled with metrics
- All strategies have operating_window

## Constraints
- Don't add new test files — this is mock data only
- Keep mock data realistic and internally consistent
- Timestamps should be for "today" so the frontend sees them as current
```

---

### Session 4 Prompt: Frontend Types + Hooks + API Client

```
# Sprint 21b Session 4: Frontend Data Layer

Read `docs/sprints/SPRINT_21B_SPEC.md` — focus on **Session 4**.

Read these files:
- `argus/ui/src/api/types.ts` — existing type definitions
- `argus/ui/src/api/client.ts` — existing API functions
- `argus/ui/src/api/ws.ts` — WebSocket client (if exists, or check stores/live.ts)
- `argus/ui/src/hooks/useOrchestratorStatus.ts` — existing hook
- `argus/ui/src/hooks/useControls.ts` — existing control mutations
- `argus/ui/src/hooks/index.ts` — barrel exports
- `argus/ui/src/stores/live.ts` — WebSocket state store
- `argus/ui/src/stores/patternLibraryUI.ts` — example Zustand store pattern
- `argus/ui/src/stores/orchestratorUI.ts` — if exists from earlier sprint, or create new

## Tasks

### 1. Extend types in api/types.ts
Add `OperatingWindow` interface. Extend `AllocationInfo` with all new fields from the sprint spec. Extend `OrchestratorStatusResponse` with session_phase, pre_market_complete, pre_market_completed_at. Add `DecisionInfo`, `DecisionsResponse`, `ThrottleOverrideRequest` interfaces.

### 2. Add API functions in api/client.ts
- `getOrchestratorDecisions(date?: string)` → `DecisionsResponse`
- `triggerRebalance()` → `{ success: boolean; message: string }`
- `overrideThrottle(strategyId: string, body: ThrottleOverrideRequest)` → `{ success: boolean; message: string }`

Follow existing patterns in client.ts for auth headers and error handling.

### 3. Create useOrchestratorDecisions hook
File: `argus/ui/src/hooks/useOrchestratorDecisions.ts`
- TanStack Query with key `['orchestrator-decisions', date]`
- 30s refetch interval
- Default date to today (YYYY-MM-DD format in ET timezone)

### 4. Create useOrchestratorMutations hook
File: `argus/ui/src/hooks/useOrchestratorMutations.ts`
Export:
- `useRebalanceMutation()` — calls triggerRebalance, invalidates ['orchestrator-status'] on success
- `useThrottleOverrideMutation()` — calls overrideThrottle, invalidates ['orchestrator-status'] on success

Use the mutation pattern from useControls.ts as reference.

### 5. Create orchestratorUI Zustand store
File: `argus/ui/src/stores/orchestratorUI.ts`
```typescript
interface OrchestratorUIState {
  overrideDialogOpen: boolean;
  overrideTargetStrategy: string | null;
  openOverrideDialog: (strategyId: string) => void;
  closeOverrideDialog: () => void;
}
```

### 6. Wire WebSocket events to query invalidation
In `stores/live.ts`, find where WebSocket messages are processed. Add handling for messages where `type` starts with `orchestrator.`:
```typescript
if (data.type?.startsWith('orchestrator.')) {
  // Import queryClient and invalidate
  queryClient.invalidateQueries({ queryKey: ['orchestrator-status'] });
  queryClient.invalidateQueries({ queryKey: ['orchestrator-decisions'] });
}
```

Check how the store accesses queryClient — it may need to be passed in or imported from a shared module. Follow whatever pattern is already established.

### 7. Update hooks/index.ts barrel exports
Export all new hooks.

## Constraints
- No visual components in this session — data layer only
- All types must match the backend response models exactly
- Test by checking TypeScript compilation: `cd argus/ui && npx tsc --noEmit`
```

---

### Session 5 Prompt: Page Shell + RegimePanel + Coverage Timeline

```
# Sprint 21b Session 5: OrchestratorPage + RegimePanel + StrategyCoverageTimeline

Read `docs/sprints/SPRINT_21B_SPEC.md` — focus on **Session 5**.

Read these files for UI patterns:
- `argus/ui/src/pages/PatternLibraryPage.tsx` — latest page pattern (Sprint 21a)
- `argus/ui/src/pages/DashboardPage.tsx` — stagger animation pattern
- `argus/ui/src/features/dashboard/MarketRegimeCard.tsx` — existing regime display
- `argus/ui/src/components/Badge.tsx` — RegimeBadge, StrategyBadge (colors, variants)
- `argus/ui/src/components/Card.tsx` — Card component
- `argus/ui/src/components/CardHeader.tsx` — CardHeader component
- `argus/ui/src/components/CapitalAllocation.tsx` — component we'll reuse
- `argus/ui/src/utils/motion.ts` — animation variants
- `argus/ui/src/hooks/useOrchestratorStatus.ts` — data hook

## Tasks

### 1. Create feature folder
```
argus/ui/src/features/orchestrator/
├── index.ts
├── RegimePanel.tsx
├── RegimeInputBreakdown.tsx
└── StrategyCoverageTimeline.tsx
```

### 2. Build OrchestratorPage.tsx
File: `argus/ui/src/pages/OrchestratorPage.tsx`

Structure:
```tsx
<AnimatedPage>
  <div className="space-y-6">
    <h1 className="text-xl font-semibold text-argus-text">Orchestrator</h1>
    {/* Section 1: Regime & Session */}
    <RegimePanel />
    {/* Section 2: Coverage Timeline */}
    <StrategyCoverageTimeline allocations={orchestratorData?.allocations ?? []} />
    {/* Section 3: Capital Allocation (reuse) */}
    <Card><CardHeader title="Capital Allocation" /><CapitalAllocation /></Card>
    {/* Section 4: Strategy Operations — placeholder for Session 6 */}
    {/* Section 5: Decision Timeline — placeholder for Session 7 */}
    {/* Section 6: Global Controls — placeholder for Session 7 */}
  </div>
</AnimatedPage>
```

Use stagger animation pattern from DashboardPage. Add placeholder divs for sections built in later sessions.

### 3. Build RegimePanel.tsx
Full-width Card with two zones:

**Left/top (stacked on mobile):**
- Session phase pill badge: color-coded by phase (pre_market=blue, market_open=green, midday=yellow, power_hour=orange, after_hours/closed=gray)
- Market regime: RegimeBadge (existing component, scaled up)
- Next regime check: countdown text "Next check in Xm" computed from `next_regime_check` timestamp
- Last updated: "Updated 10:30 AM"

**Right/bottom:**
- RegimeInputBreakdown component

Desktop: flex-row justify-between. Mobile: stacked.

### 4. Build RegimeInputBreakdown.tsx
Three-row compact display using orchestrator indicator values.

Each row shows an assessment factor:
```
Row 1 — Trend:
  "SPY $525.50" then show comparison to SMA-20 and SMA-50
  Compute trend score client-side: above both = "+2 Strong Bull" (green)
  Show checkmarks: "> SMA-20 $520.30 ✓" "> SMA-50 $515.80 ✓"

Row 2 — Volatility:
  "12.5% annualized" then bucket label
  Thresholds: <8% = Low, <16% = Normal, <25% = High, ≥35% = Crisis
  Color: green for Low/Normal, yellow for High, red for Crisis

Row 3 — Momentum:
  "+1.25% 5d ROC" then direction
  Thresholds: >+1% = "Bullish ✓" (green), <-1% = "Bearish ✗" (red), else "Neutral —"
```

Use tabular-nums for all numbers. Muted labels, colored values.

If indicator data is missing (null/undefined), show "—" with dim styling.

### 5. Build StrategyCoverageTimeline.tsx
Custom SVG component showing strategy operating windows.

Props: `{ allocations: AllocationInfo[] }`

Structure:
- SVG element, width="100%", viewBox computed from container width
- Use a ResizeObserver or hard-code reasonable aspect ratio
- Actually, simplest approach: use percentages within the SVG

Time mapping:
```typescript
const MARKET_START_MIN = 570;  // 9:30 = 9*60+30
const MARKET_END_MIN = 960;    // 16:00 = 16*60
const TOTAL_MIN = 390;
const timeToPercent = (timeStr: string) => {
  const [h, m] = timeStr.split(':').map(Number);
  return ((h * 60 + m) - MARKET_START_MIN) / TOTAL_MIN * 100;
};
```

SVG elements:
- Time axis labels: text elements at major hours (9:30, 10, 11, 12, 1, 2, 3, 4)
- Vertical grid lines at each hour (stroke-dasharray, very light)
- Per-strategy row: rect from earliest_entry% to latest_entry%, colored per strategy
- Strategy colors: orb_breakout=#60a5fa, orb_scalp=#c084fc, vwap_reclaim=#2dd4bf, afternoon_momentum=#fbbf24
- Throttled/paused: opacity=0.3 + diagonal stripe SVG pattern
- "Now" marker: vertical line at current ET time position, red (#ef4444), dashed
- Strategy labels: text on left side of each row

Dimensions:
- Row height: 28px
- Top axis: 24px for labels
- Left margin: 80px for strategy names (desktop), 32px for abbreviations (mobile)
- Total height: 24 + (numStrategies × 28) + 8 padding

Responsive:
- Desktop (≥1024px): full labels ("ORB Breakout"), time labels every 30min
- Tablet (640–1023px): medium labels ("ORB"), time labels every hour
- Mobile (<640px): single-letter labels ("O","S","V","A"), time labels every 2 hours

### 6. Add route to App.tsx
Import OrchestratorPage and add:
```tsx
<Route path="/orchestrator" element={<OrchestratorPage />} />
```

Do NOT update nav items yet — that's Session 8. For now, access via direct URL.

## Design notes
- Use the existing dark theme colors throughout
- Don't over-animate — the coverage timeline is static SVG, no transitions needed
- The CapitalAllocation reuse should work directly since it reads from useOrchestratorStatus()
- Follow the exact Card/CardHeader patterns from other pages
```

---

### Session 6 Prompt: Strategy Operations Grid

```
# Sprint 21b Session 6: StrategyOperationsGrid + StrategyOperationsCard

Read `docs/sprints/SPRINT_21B_SPEC.md` — focus on **Session 6**.

Read these files:
- `argus/ui/src/features/system/StrategyCards.tsx` — existing strategy cards on System page (similar concept, simpler)
- `argus/ui/src/components/Badge.tsx` — StrategyBadge, ThrottleBadge
- `argus/ui/src/components/AnimatedNumber.tsx` — animated number display
- `argus/ui/src/components/StatusDot.tsx` — health status indicator
- `argus/ui/src/components/PnlValue.tsx` — P&L colored display
- `argus/ui/src/hooks/useControls.ts` — existing pause/resume mutations
- `argus/ui/src/stores/orchestratorUI.ts` — override dialog state (from Session 4)
- `argus/ui/src/features/orchestrator/` — files created in Session 5

## Tasks

### 1. Create StrategyOperationsGrid.tsx
File: `argus/ui/src/features/orchestrator/StrategyOperationsGrid.tsx`

Responsive grid:
- Desktop (≥1024px): 2 columns
- Mobile: 1 column

Maps `allocations` from useOrchestratorStatus to StrategyOperationsCard.

### 2. Create StrategyOperationsCard.tsx
File: `argus/ui/src/features/orchestrator/StrategyOperationsCard.tsx`

Props: `{ allocation: AllocationInfo }` (the extended version with all fields)

Card sections:

**Header row** (flex justify-between):
- Left: Strategy name (from allocation.strategy_id, formatted), StrategyBadge
- Right: StatusDot (green=active, yellow=paused, red=error) + Pause/Resume button

Pause/Resume: icon button (Play/Pause icons from lucide). Uses existing pause/resume API calls. Show current state. Instant toggle, no confirmation.

**Allocation section:**
- "Allocated: $20,000 (20%)" — use AnimatedNumber for dollar amount
- "Deployed: $13,500 (68%)" — smaller text
- Thin progress bar: deployed/allocated ratio, strategy-colored

**Throttle section** (only render if throttle_action !== "none"):
- ThrottleBadge (REDUCED or SUSPENDED)
- Reason text from allocation.reason
- Metric row: "Losses: 3 | Sharpe: -0.12 | DD: 4.2%"
  - consecutive_losses, rolling_sharpe (format ±X.XX), drawdown_pct (format X.X%)
  - Color-code: losses >= 3 red, sharpe < 0 red, drawdown > 10% red
- "Override Throttle" button (amber/orange) → calls orchestratorUI.openOverrideDialog(strategyId)

**Performance today:**
- Row: "Trades: 5 (3W / 2L) | P&L: +$234.50 | Open: 2"
- Use PnlValue for the P&L display

**Operating window:**
- Text: "9:35 – 11:30 AM ET"
- Status indicator: "● Active" (green) if current ET time is within earliest_entry–latest_entry, "○ Inactive" otherwise

Format operating window times: "09:35" → "9:35 AM", "14:00" → "2:00 PM"

### 3. Wire into OrchestratorPage
Replace the Session 6 placeholder in OrchestratorPage.tsx with:
```tsx
<StrategyOperationsGrid />
```

The grid component fetches its own data via useOrchestratorStatus.

### 4. Strategy name formatting
Create a utility or inline map for pretty-printing strategy IDs:
```typescript
const STRATEGY_NAMES: Record<string, string> = {
  orb_breakout: 'ORB Breakout',
  orb_scalp: 'ORB Scalp',
  vwap_reclaim: 'VWAP Reclaim',
  afternoon_momentum: 'Afternoon Momentum',
};
```

Check if this already exists elsewhere (it likely does in Badge.tsx or a shared util).

## Design notes
- Cards should have subtle left border in strategy color (like PatternCard selected state pattern)
- Use the same Card component and padding as other cards in the system
- Throttle section should feel visually distinct — maybe a subtle amber/red background tint
- The "Override Throttle" button should feel weighty: amber bg, bold text, ShieldAlert icon
```

---

### Session 7 Prompt: DecisionTimeline + Controls + Override Dialog

```
# Sprint 21b Session 7: DecisionTimeline + GlobalControls + ThrottleOverrideDialog

Read `docs/sprints/SPRINT_21B_SPEC.md` — focus on **Session 7**.

Read these files:
- `argus/ui/src/features/system/EmergencyControls.tsx` — existing emergency control pattern with confirmation modals
- `argus/ui/src/features/system/EventsLog.tsx` — existing event timeline (similar concept)
- `argus/ui/src/hooks/useOrchestratorDecisions.ts` — data hook (from Session 4)
- `argus/ui/src/hooks/useOrchestratorMutations.ts` — rebalance + override mutations (from Session 4)
- `argus/ui/src/stores/orchestratorUI.ts` — override dialog state (from Session 4)
- `argus/ui/src/api/types.ts` — DecisionInfo type

## Tasks

### 1. Create DecisionTimeline.tsx
File: `argus/ui/src/features/orchestrator/DecisionTimeline.tsx`

Card with CardHeader "Decision Log" and scrollable content (max-h-[400px] overflow-y-auto).

Uses useOrchestratorDecisions() hook. Maps decisions to DecisionTimelineItem components.

If no decisions: show EmptyState "No decisions logged today."

Decisions rendered in chronological order (oldest first). The API returns them in creation order — verify and sort if needed.

### 2. Create DecisionTimelineItem.tsx
File: `argus/ui/src/features/orchestrator/DecisionTimelineItem.tsx`

Props: `{ decision: DecisionInfo }`

Layout: horizontal row with vertical connecting line on left.

```
[timestamp] [icon] [content]
   9:25 AM    🧭    Regime classified: bullish_trending
                    SPY above both SMAs with positive momentum
   9:25 AM    📊    ORB Breakout allocated 20% ($20,000)
  10:45 AM    ⚠️    ORB Scalp throttled: 3 consecutive losses → REDUCE
```

Components of each item:
- **Timestamp** (w-16, shrink-0): formatted time "9:25 AM" in text-argus-text-dim
- **Icon** (w-8, shrink-0): lucide icon by decision_type:
  - regime_classification / regime_recheck → Compass (blue)
  - allocation → PieChart (argus-accent)
  - activation / strategy_activated → Play (green)
  - suspension / strategy_suspended / throttle → Pause (orange) or ShieldAlert (red for suspend)
  - throttle_override → ShieldAlert (amber)
  - eod_review → Moon (gray)
  - default → Clock (gray)
- **Content** (flex-1):
  - Primary text: decision rationale (from `decision.rationale`)
  - Secondary: strategy badge if `decision.strategy_id` is present (use StrategyBadge)

Connecting line: vertical border-l on the icon column, connecting items visually. First and last items have half-height connectors.

Decision severity color (dot or icon tint):
- Green: activation, allocation (positive)
- Yellow/amber: throttle, regime_recheck
- Red: suspension
- Blue: regime_classification
- Gray: eod_review, default

### 3. Create GlobalControls.tsx
File: `argus/ui/src/features/orchestrator/GlobalControls.tsx`

Card with CardHeader "Controls" containing a row of action buttons:

**Force Rebalance** (blue button):
- Icon: RefreshCcw from lucide
- On click: show confirmation dialog "Recalculate all strategy allocations based on current account state and performance metrics?"
- Confirm → call useRebalanceMutation
- Show loading state while executing

**Emergency Pause All** (orange button):
- Reuse the same pattern from EmergencyControls.tsx
- Or extract a ConfirmButton pattern if cleaner

**Emergency Flatten All** (red button):
- Reuse the same pattern from EmergencyControls.tsx

Desktop: horizontal flex with gap-3. Mobile: stacked full-width buttons.

For confirmation dialogs, study EmergencyControls.tsx and reuse the same dialog/modal pattern. If it uses a custom modal, reuse it. If it uses window.confirm(), upgrade to a proper dialog.

### 4. Create ThrottleOverrideDialog.tsx
File: `argus/ui/src/features/orchestrator/ThrottleOverrideDialog.tsx`

Modal dialog driven by orchestratorUI Zustand store.

When `overrideDialogOpen === true`:
- Overlay backdrop (fixed inset-0, bg-black/50, z-50)
- Centered dialog panel (max-w-md)
- Amber/warning-themed border or accent

Contents:
- Title: "Override Throttle" with ShieldAlert icon
- Subtitle: strategy name from overrideTargetStrategy (formatted)
- Warning text: "⚠️ This temporarily overrides performance-based risk controls. The strategy will resume accepting new trades."
- Duration select: dropdown or radio buttons — "30 minutes" | "1 hour" | "Rest of day"
- Reason textarea: required, placeholder "Why are you overriding? (required)", min-length validation (10 chars)
- Button row: Cancel (ghost) | Confirm Override (amber, disabled until reason meets min length)
- On confirm: call useThrottleOverrideMutation with { duration_minutes, reason }
- On success: close dialog, invalidate queries (mutation handles this)

Mount this component in OrchestratorPage.tsx (at the bottom, outside the scroll flow).

### 5. Wire into OrchestratorPage
Replace remaining placeholders:
```tsx
<DecisionTimeline />
<GlobalControls />
<ThrottleOverrideDialog />
```

## Design notes
- Decision timeline should feel like a calm, readable log — not flashy
- Emergency controls should reuse the existing severity pattern: red bg for flatten, orange for pause
- The ThrottleOverrideDialog should feel appropriately serious — this is overriding risk controls
- Keep all confirmation text concise but clear about consequences
```

---

### Session 8 Prompt: Nav + Polish + Vitest + Skeleton

```
# Sprint 21b Session 8: Nav Update + Polish + Vitest + Skeleton

Read `docs/sprints/SPRINT_21B_SPEC.md` — focus on **Session 8**.

Read these files:
- `argus/ui/src/layouts/Sidebar.tsx` — desktop nav (add 6th item)
- `argus/ui/src/layouts/MobileNav.tsx` — mobile nav (add 6th item)
- `argus/ui/src/App.tsx` — router config (verify route is added from Session 5)
- `argus/ui/src/components/Skeleton.tsx` — skeleton component
- `argus/ui/src/features/patterns/IncubatorPipeline.test.tsx` — example Vitest test
- `argus/ui/src/features/symbol/SymbolDetailPanel.test.tsx` — example Vitest test
- All files in `argus/ui/src/features/orchestrator/` — the components we built

## Tasks

### 1. Update Sidebar.tsx
Add Orchestrator as 5th item (before System):
```typescript
import { Gauge } from 'lucide-react';

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/trades', icon: ScrollText, label: 'Trades' },
  { to: '/performance', icon: TrendingUp, label: 'Performance' },
  { to: '/patterns', icon: BookOpen, label: 'Pattern Library' },
  { to: '/orchestrator', icon: Gauge, label: 'Orchestrator' },
  { to: '/system', icon: Activity, label: 'System' },
];
```

Keyboard shortcuts already auto-map from NAV_ITEMS.length — verify 1-6 works.

### 2. Update MobileNav.tsx
Add Orchestrator. With 6 items, shrink labels:
```typescript
import { Gauge } from 'lucide-react';

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dash' },
  { to: '/trades', icon: ScrollText, label: 'Trades' },
  { to: '/performance', icon: TrendingUp, label: 'Perf' },
  { to: '/patterns', icon: BookOpen, label: 'Patterns' },
  { to: '/orchestrator', icon: Gauge, label: 'Orch' },
  { to: '/system', icon: Activity, label: 'System', showStatusDot: true },
];
```

Change the label text size from `text-[10px]` to `text-[9px]` to accommodate 6 items.

### 3. Create OrchestratorSkeleton.tsx
File: `argus/ui/src/features/orchestrator/OrchestratorSkeleton.tsx`

Skeleton matching page layout:
- RegimePanel skeleton: badge placeholder (h-6 w-24 rounded-full), indicator row placeholders
- CoverageTimeline skeleton: gray rect bars mimicking the timeline
- 4 strategy card skeletons: header + 3 content rows each
- Decision timeline skeleton: 5 list item placeholders

Use in OrchestratorPage when orchestrator data is loading.

### 4. Write Vitest tests
Create test files in `argus/ui/src/features/orchestrator/__tests__/` or co-located as `.test.tsx`:

**StrategyCoverageTimeline.test.tsx:**
- Renders SVG element
- Renders one rect per strategy with operating_window
- Shows "now" marker (vertical line)
- Throttled strategy has reduced opacity

**RegimeInputBreakdown.test.tsx:**
- Renders with indicator values
- Shows "Bullish" for positive trend
- Shows "Normal" for mid-range volatility
- Handles missing indicator data gracefully

**StrategyOperationsCard.test.tsx:**
- Renders strategy name and badge
- Shows throttle section when throttle_action is "reduce"
- Hides throttle section when throttle_action is "none"
- Shows "Override" button for throttled strategy

**ThrottleOverrideDialog.test.tsx:**
- Renders when store.overrideDialogOpen is true
- Does not render when false
- Confirm button disabled when reason is empty
- Confirm button enabled when reason has 10+ chars

Target: 8 new Vitest tests across these files.

### 5. Responsive polish
Verify at all breakpoints by running dev mode and checking:
- 393px (iPhone): sections stacked, mobile nav fits 6 items, timeline readable
- 834px (iPad portrait): comfortable layout
- 1194px (iPad landscape): 2-col strategy grid, coverage timeline full labels
- 1512px (MacBook): full desktop layout

Fix any overflow, truncation, or alignment issues.

### 6. Final checks
- Run `cd argus/ui && npx tsc --noEmit` — zero type errors
- Run `cd argus/ui && npx vitest run` — all tests pass (70 existing + 8 new = 78)
- Run `cd argus && python -m pytest` — all tests pass (1558 existing + ~20 new ≈ 1578)
- Run dev mode: `python -m argus.api --dev` and verify page works end-to-end
- Check that all existing pages still work (regression test)

## Constraints
- Mobile nav must remain usable with 6 items — if labels overlap, use shorter abbreviations
- All skeleton states must match the actual content layout dimensions
- Vitest tests should use the existing test patterns (check imports, render utilities, mocks)
```

---

## Part 2: Code Review Plan

### Review Schedule

**Two review checkpoints for Sprint 21b:**

| Review | After Sessions | Focus |
|--------|---------------|-------|
| **Review A** | Sessions 1-4 (backend + data layer) | API correctness, type safety, mock data quality, architectural consistency |
| **Review B** | Sessions 5-8 (frontend + polish) | Visual fidelity, responsiveness, component architecture, test coverage, final sign-off |

### Review A: After Sessions 1-4

**When:** After Session 4 is committed and pushed to `main`.

**Materials needed:**
- Git log of Sessions 1-4 commits
- Screenshot of `GET /orchestrator/status` response in dev mode (curl or browser)
- Screenshot of `GET /orchestrator/decisions` response in dev mode
- Test count confirmation (pytest count)
- TypeScript compilation status (`npx tsc --noEmit`)

**What to check:**
1. API response schema matches the sprint spec
2. All new fields populated correctly in dev mode
3. Mock data is realistic and internally consistent
4. Throttle override endpoint works
5. Frontend types match backend response exactly
6. Hooks follow established patterns
7. No regressions in existing tests

**Procedure:**
1. Push all Session 1-4 work to `main`
2. Open new Claude.ai conversation with review handoff brief (below)
3. Claude reviews the code via GitHub repo access
4. Issues categorized as: fix-now (blocks Sessions 5-8) vs fix-later (polish in Session 8)
5. Fix-now items addressed before starting Session 5

### Review B: After Sessions 5-8

**When:** After Session 8 is committed and pushed to `main`.

**Materials needed:**
- Git log of Sessions 5-8 commits
- Screenshots at all 4 breakpoints (393px, 834px, 1194px, 1512px) showing the Orchestrator page
- Screenshot of the coverage timeline
- Screenshot of throttled strategy card
- Screenshot of decision timeline
- Screenshot of throttle override dialog
- Test count confirmation (pytest + Vitest)
- Dev mode running confirmation

**What to check:**
1. Page layout matches spec across all breakpoints
2. Coverage timeline correct positioning and colors
3. Throttled strategy visual treatment
4. Decision timeline renders all mock entries
5. Controls work (pause/resume, rebalance, override)
6. Navigation updated correctly
7. Skeleton loading states
8. Vitest tests meaningful
9. No regressions

**Procedure:**
1. Push all Session 5-8 work to `main`
2. Open new Claude.ai conversation with review handoff brief (below)
3. Claude reviews code + screenshots
4. Issues addressed in fix session if needed
5. Sprint declared complete

### Doc Updates

**After Review B passes**, draft and commit doc updates:
- Decision Log entries (drafted in Part 6 below)
- Project Knowledge (02) current state update
- Sprint Plan (10) — move 21b to completed
- CLAUDE.md — update current state

---

## Part 3: Code Review Handoff Briefs

---

### Review A Handoff Brief (paste into new Claude.ai conversation)

```
# Sprint 21b Code Review A — Backend + Data Layer (Sessions 1-4)

I'm building ARGUS, an automated multi-strategy day trading ecosystem. Sprint 21b (Orchestrator Page) is in progress. Sessions 1-4 are complete and pushed to `main`. I need a code review of the backend API extensions, throttle override implementation, dev mode mock data, and frontend data layer.

**Repo:** https://github.com/stevengizzi/argus.git

**Sprint spec:** `docs/sprints/SPRINT_21B_SPEC.md`

**What was built in Sessions 1-4:**
1. Extended `GET /orchestrator/status` with session_phase, pre_market_complete, per-strategy operating_window, throttle detail metrics (consecutive_losses, rolling_sharpe, drawdown_pct), is_active, health_status, trade_count_today, daily_pnl, open_position_count
2. Added date filter to `GET /orchestrator/decisions`
3. Added `POST /orchestrator/strategies/{id}/override-throttle` with duration + reason
4. Added `_override_until` tracking to Orchestrator with `_is_override_active()` check in allocation calculation
5. Enhanced dev mode mock data: ORB Scalp throttled (REDUCE), ~15 decision timeline entries, operating windows for all strategies
6. Frontend: extended types, new hooks (useOrchestratorDecisions, useOrchestratorMutations), orchestratorUI Zustand store, WebSocket event → query invalidation wiring

**Review these files (changed/created in Sessions 1-4):**
- `argus/core/orchestrator.py` — override_throttle, _is_override_active, pre_market_complete property
- `argus/api/routes/orchestrator.py` — extended response models, new endpoint, session phase helper
- `argus/api/dev_state.py` — enhanced mock orchestrator + decisions
- `argus/ui/src/api/types.ts` — extended interfaces
- `argus/ui/src/api/client.ts` — new API functions
- `argus/ui/src/hooks/useOrchestratorDecisions.ts`
- `argus/ui/src/hooks/useOrchestratorMutations.ts`
- `argus/ui/src/stores/orchestratorUI.ts`
- `argus/ui/src/stores/live.ts` — WS event wiring
- New test files in `tests/api/`

**Check for:**
1. **Spec compliance:** Do the API responses match what the sprint spec defines?
2. **Architectural consistency:** Do the new patterns match existing patterns (route structure, Pydantic models, hook patterns, store patterns)?
3. **Mock data quality:** Is the dev mode data realistic and internally consistent? Does it exercise throttle, regime, and all decision types?
4. **Type safety:** Do frontend types match backend responses exactly?
5. **Edge cases:** What happens when orchestrator is unavailable? When strategies dict is empty? When trade_logger has no data?
6. **Test coverage:** Are the new tests meaningful? Any gaps?
7. **Regressions:** Any changes that could break existing functionality?

**Categorize issues as:**
- 🔴 Fix-now (blocks frontend sessions 5-8)
- 🟡 Fix-in-session-8 (polish/cleanup, can wait)
- 🟢 Note (observation, no action needed now)

Provide specific file paths and line numbers for all issues.
```

---

### Review B Handoff Brief (paste into new Claude.ai conversation)

```
# Sprint 21b Code Review B — Frontend + Final (Sessions 5-8)

I'm building ARGUS, an automated multi-strategy day trading ecosystem. Sprint 21b (Orchestrator Page) Sessions 5-8 are complete and pushed to `main`. This is the final review before declaring the sprint complete.

**Repo:** https://github.com/stevengizzi/argus.git

**Sprint spec:** `docs/sprints/SPRINT_21B_SPEC.md`

**What was built in Sessions 5-8:**
1. OrchestratorPage.tsx — full page with 6 sections in vertical flow
2. RegimePanel + RegimeInputBreakdown — session phase, regime badge, indicator scoring breakdown
3. StrategyCoverageTimeline — custom SVG timeline with strategy bars, "now" marker, throttled state
4. StrategyOperationsGrid + StrategyOperationsCard — per-strategy cards with allocation, throttle detail, controls
5. DecisionTimeline + DecisionTimelineItem — chronological decision log with type icons
6. GlobalControls — force rebalance + emergency flatten/pause
7. ThrottleOverrideDialog — duration + reason confirmation modal
8. OrchestratorSkeleton — loading state
9. Nav update — Sidebar + MobileNav now have 6 items (Orchestrator = 5th)
10. 8 new Vitest tests

**Review these files:**
- `argus/ui/src/pages/OrchestratorPage.tsx`
- `argus/ui/src/features/orchestrator/` — all files
- `argus/ui/src/layouts/Sidebar.tsx` — nav update
- `argus/ui/src/layouts/MobileNav.tsx` — nav update + label abbreviation
- `argus/ui/src/App.tsx` — route addition
- Vitest test files

**Screenshots I should provide:** [attach screenshots at 393px, 834px, 1194px, 1512px breakpoints]

**Check for:**
1. **Visual quality:** Does the page look polished and consistent with existing pages?
2. **Responsive fidelity:** All 4 breakpoints working correctly? Mobile nav not cramped?
3. **Coverage timeline:** Bars positioned correctly? Strategy colors match Badge system? "Now" marker works? Throttled strategy visually distinct?
4. **Strategy cards:** Throttle section visible only when throttled? Controls work? Allocation bars correct?
5. **Decision timeline:** Entries in chronological order? Correct icons and colors per type? Strategy badges present?
6. **Controls:** Rebalance confirmation works? Emergency controls match existing pattern? Override dialog validates inputs?
7. **Component architecture:** Proper separation of concerns? Components reusable? Feature folder organized?
8. **Skeleton states:** Match actual content layout?
9. **Test quality:** Vitest tests meaningful? Good coverage of key behaviors?
10. **Regressions:** All existing pages still work? Navigation keyboard shortcuts updated?

**Test counts expected:** ~1578 pytest + ~78 Vitest

**Decision log entries to validate (from design phase):**
- DEC-186: Orchestrator page layout — vertical flow, no master-detail
- DEC-187: Throttle override — duration + reason + confirmation
- DEC-188: Coverage timeline — custom SVG
- DEC-189: Mobile nav with 6 items — abbreviated labels
- DEC-190: Session phase computation
- DEC-191: Regime input display — client-side scoring breakdown

Categorize issues as:
- 🔴 Fix-now (must fix before sprint complete)
- 🟡 Defer to 21d (add to backlog)
- 🟢 Note (observation only)

After review passes, I need:
1. Confirmation the sprint is complete
2. Any items to add to UX Feature Backlog for future improvement
3. List of any new deferred items (DEF-XXX)
```

---

## Part 4: Document Updates (Draft Now)

### Decision Log Entries

Add these to `docs/05_DECISION_LOG.md` (after DEC-185):

```markdown
### DEC-186 | Orchestrator Page Layout — Vertical Flow
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Orchestrator page uses full-width vertical flow layout (no master-detail). Sections top-to-bottom: RegimePanel, StrategyCoverageTimeline, CapitalAllocation, StrategyOperationsGrid, DecisionTimeline, GlobalControls. |
| **Alternatives Considered** | (A) Three-column layout (Capital | Decisions | Risk) — original 21b spec in sprint plan. (B) Master-detail with strategy list + detail panel. (C) Tab-based sections. |
| **Rationale** | Vertical flow matches the "progressive disclosure" principle (DEC-109): ambient summary at top, operational detail in middle, controls at bottom. Master-detail would hide the coverage timeline and decision log behind clicks. Three-column was too dense on tablet. The operator reads this page top-to-bottom during market hours — the layout should match that flow. |
| **Status** | Active |

### DEC-187 | Throttle Override Design
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Throttle override requires duration selection (30 min / 1 hour / rest of day) + written reason + confirmation dialog. Override stored in-memory as `_override_until` dict on Orchestrator. Logged as `throttle_override` decision for audit trail. Override checked in `_calculate_allocations` — active override converts REDUCE/SUSPEND to NONE. |
| **Alternatives Considered** | (A) One-click instant override lasting until next poll cycle. (B) Persistent override stored in DB surviving restarts. (C) No override — only manual resume via pause/resume. |
| **Rationale** | This is overriding risk controls protecting capital. The UI must feel appropriately weighty — not a casual toggle. Duration prevents "forgot to un-override" scenarios. Reason creates accountability in the decision log. In-memory storage is acceptable because overrides are inherently session-scoped (a restart should re-evaluate from scratch). |
| **Status** | Active |

### DEC-188 | Strategy Coverage Timeline — Custom SVG
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Strategy coverage timeline uses custom SVG with fixed 9:30–16:00 time axis. Per-strategy colored bars from earliest_entry to latest_entry. "Now" marker as red dashed vertical line. Throttled/paused strategies at reduced opacity. Strategy colors match Badge system (ORB=blue, Scalp=purple, VWAP=teal, Momentum=amber). |
| **Alternatives Considered** | (A) D3.js time-scale visualization. (B) CSS Grid with percentage widths. (C) Recharts bar chart. |
| **Rationale** | The visualization is simple: fixed time axis, 4–18 bars, one moving marker. D3 adds a large dependency for something achievable in ~100 lines of SVG math. CSS Grid can't easily do the "now" marker overlay. Custom SVG follows the proven pattern from CapitalAllocation donut (DEC-133). Time-to-pixel mapping is trivial: `(minuteOfDay - 570) / 390 * width`. |
| **Status** | Active |

### DEC-189 | Mobile Navigation with 6 Pages
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Mobile bottom nav expanded from 5 to 6 items with abbreviated labels ("Dash", "Trades", "Perf", "Patterns", "Orch", "System") at 9px text. All 6 items visible — no "More" menu. |
| **Alternatives Considered** | (A) 5 items + "More" menu hiding Orchestrator and/or System. (B) Keep full labels and allow horizontal scroll. (C) Context-dependent nav showing different items per page. |
| **Rationale** | All 6 pages are frequently accessed — hiding any behind "More" adds friction during trading hours. Abbreviated labels at 9px fit within the 393px iPhone width. "More" menu restructure deferred to Sprint 21d when the 7th page (The Debrief) is added — at 7 pages, "More" becomes necessary. |
| **Status** | Active |

### DEC-190 | Session Phase Computation
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Session phase computed server-side from current ET time. Six phases: pre_market (before 9:30), market_open (9:30–11:30), midday (11:30–14:00), power_hour (14:00–16:00), after_hours (16:00–20:00), market_closed (after 20:00 or weekends). Included in orchestrator status response. |
| **Alternatives Considered** | (A) Client-side computation. (B) Phase derived from strategy activity. (C) Manual phase selection. |
| **Rationale** | Server-side ensures consistency — all clients see the same phase. Time-based is deterministic and requires no state. Phase boundaries align with trading conventions: market_open covers the highest-activity morning period, power_hour captures the afternoon surge. |
| **Status** | Active |

### DEC-191 | Regime Input Display — Client-Side Scoring
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | RegimeInputBreakdown component computes trend score, volatility bucket, and momentum confirmation client-side from the raw indicator values already in the orchestrator status response. Displays each factor with its directional assessment (bullish/bearish/neutral). |
| **Alternatives Considered** | (A) Backend computes and returns scoring breakdown as separate fields. (B) Display only raw values without interpretation. (C) Full diagnostic with all thresholds and intermediate calculations. |
| **Rationale** | The raw indicator values (spy_price, spy_sma_20, spy_sma_50, spy_roc_5d, spy_realized_vol_20d) are already in the API response. The scoring logic is simple and deterministic (trend: compare price vs SMAs; vol: compare to fixed thresholds; momentum: compare ROC to ±1%). Computing client-side avoids API schema changes and keeps the scoring visible/debuggable in the UI code. Option (B) would show numbers without "so what?" context. Option (C) is too noisy for an at-a-glance display. |
| **Status** | Active |
```

### Sprint Plan Update

Update `docs/10_PHASE3_SPRINT_PLAN.md` — move Sprint 21b to current/in-progress status (don't move to complete until Review B passes):

Replace the existing Sprint 21b entry with:

```markdown
#### Sprint 21b — Orchestrator Page (DEC-169, DEC-171, DEC-186–191)
**Status:** IN PROGRESS
**Target:** ~8 sessions, ~1578 pytest + ~78 Vitest
**Scope:**
- **Orchestrator page** (6th page): Real-time operational nerve center. Vertical flow layout (DEC-186). Sections: RegimePanel (session phase, regime badge, indicator breakdown DEC-190/191), StrategyCoverageTimeline (custom SVG DEC-188), CapitalAllocation (reuse), StrategyOperationsGrid (per-strategy cards with allocation, throttle detail, controls), DecisionTimeline (chronological decision log), GlobalControls (rebalance, emergency flatten/pause).
- Throttle override: duration + reason + confirmation, in-memory _override_until, logged to decision log (DEC-187).
- API extensions: session_phase, pre_market_complete, per-strategy operating_window, throttle metrics (consecutive_losses, rolling_sharpe, drawdown_pct), override status. Date filter on decisions endpoint. New POST override endpoint.
- Dev mode: ORB Scalp throttled (REDUCE), ~15 decision entries, operating windows, session phase.
- Nav: 6 pages, abbreviated mobile labels (DEC-189). Keyboard shortcuts 1–6.
- Tests: ~20 new pytest, ~8 new Vitest.
- **Deferred to 21d:** PreMarketCard/EodSummaryCard as dedicated components, multi-day regime history, decision filtering, "More" menu for mobile nav.
```

### Project Knowledge Update

After sprint completes, add to the Build Track section in `02_PROJECT_KNOWLEDGE.md`:

```markdown
- Sprint 21b (Orchestrator Page): ✅ COMPLETE — ~1578 tests (pytest) + ~78 (Vitest), Feb 27. Backend: extended orchestrator status (session_phase, pre_market_complete, per-strategy operating_window, throttle metrics, override status), decisions date filter, throttle override endpoint (DEC-187). Frontend: OrchestratorPage (6th page) with RegimePanel (session phase + regime input breakdown DEC-190/191), StrategyCoverageTimeline (custom SVG DEC-188), CapitalAllocation (reuse), StrategyOperationsGrid (per-strategy allocation/throttle/controls), DecisionTimeline (chronological log), GlobalControls (rebalance + emergency). ThrottleOverrideDialog (duration + reason + confirmation). OrchestratorSkeleton. Nav updated to 6 pages with abbreviated mobile labels (DEC-189). WS event → query invalidation. Vertical flow layout (DEC-186). X implementation sessions + Y code review checkpoints. Code review passed (DEC-186–191).
```

(Fill in session counts and exact test numbers after completion.)

### CLAUDE.md Update

After sprint completes, update the Current State section and add architectural rules for:
- Orchestrator page route: `/orchestrator`
- Throttle override: `_override_until` dict pattern
- Session phase: server-side computation in API route

### Risk Register

No new risks identified for Sprint 21b. The throttle override feature could theoretically be misused (overriding risk controls during a losing streak), but the audit trail (decision logging) and time-limited duration mitigate this.

### Deferred Items

No new DEF entries needed. The items deferred to 21d are already captured in the sprint spec and will be added to Sprint 21d's scope when it's designed:
- PreMarketCard / EodSummaryCard dedicated components
- Multi-day regime history
- Decision timeline filtering by type/strategy
- Mobile nav "More" menu (needed at 7 pages)
- AI insights placeholder sections on strategy cards
