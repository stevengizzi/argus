# Sprint 18 — ORB Scalp Strategy: Complete Implementation Package

> **Last Updated:** Feb 25, 2026
> **Sprint 17 Test Count:** 1146
> **Target Test Count:** ~1,341+
> **Estimated Sessions:** 12 Claude Code + 2 Code Reviews

---

# PART 1: IMPLEMENTATION SPECIFICATION

## Sprint 18 Overview

Sprint 18 adds the second strategy to ARGUS — ORB Scalp — and builds the multi-strategy infrastructure that all future strategies depend on. Four pillars:

1. **ORBBase Extraction + ORB Scalp Strategy** — Shared base class, new strategy implementation
2. **Cross-Strategy Risk Integration** — Duplicate stock policy, single-stock exposure cap, Risk Manager → Order Manager reference
3. **Multi-Strategy Wiring** — CandleEvent routing, main.py generalization, per-signal time stops
4. **Backtesting Validation** — VectorBT sweep, walk-forward, Replay Harness cross-validation
5. **UX Add-ons** — Session Summary Card, Position Timeline (~7h)

### Key Decisions (to be logged as DEC-120 through DEC-125)

| ID | Decision |
|----|----------|
| DEC-120 | ORBBase extraction: shared opening range + breakout detection base class for all ORB variants |
| DEC-121 | `ALLOW_ALL` duplicate stock policy added: ORB + Scalp trade same symbol simultaneously, gated by `max_single_stock_pct` (5%). Default changed from `PRIORITY_BY_WIN_RATE` to `ALLOW_ALL`. |
| DEC-122 | Per-signal time stop: `time_stop_seconds` field on SignalEvent, carried to ManagedPosition, checked per-position by Order Manager |
| DEC-123 | ORB Scalp: single target exit (no T1/T2 split), 0.3R default, 120s default hold, OR midpoint stop |
| DEC-124 | Cross-strategy risk: Risk Manager receives Order Manager reference for position-aware cross-strategy checks |
| DEC-125 | CandleEvent routing in main.py: EventBus subscription routes candles to all active strategies through Orchestrator registry. Replaces single-strategy `self._strategy` singleton. |
| DEC-126 | Sector exposure check (`max_single_sector_pct`) deferred — no sector classification data available. Logged as DEF-020. |

### New Deferred Items

| ID | Description | Trigger |
|----|-------------|---------|
| DEF-020 | Cross-strategy sector exposure check (`max_single_sector_pct`). Requires sector classification data (SIC codes or similar). | When sector data source is integrated (IQFeed or similar). |
| DEF-021 | Sub-bar backtesting precision for Scalp. Synthetic ticks give 15s granularity per 1m bar. Sub-15s time stops resolve at next tick. | If Scalp backtesting results look unreliable or Databento tick data is available for backtesting. |

---

## Detailed Technical Specification

### 1. ORBBase Extraction (DEC-120)

**New file:** `argus/strategies/orb_base.py`

```
BaseStrategy (ABC)
    └── OrbBaseStrategy (opening range + breakout detection)
            ├── OrbBreakoutStrategy (T1/T2, minutes time stop)
            └── OrbScalpStrategy (single target, seconds time stop)
```

**OrbBaseStrategy** contains:
- `OrbSymbolState` dataclass (moved from `orb_breakout.py`)
- `__init__` accepting a union config type with shared fields
- `_get_symbol_state()`, `_get_candle_time()`, `_is_in_or_window()`, `_is_past_or_window()`, `_is_before_latest_entry()`
- `_finalize_opening_range()` — unchanged
- `_check_breakout_conditions()` — returns a "breakout context" dict (symbol, candle, state, volume_threshold, vwap_str) instead of building the signal directly
- `on_candle()` — full flow: OR formation → finalization → breakout detection → calls abstract `_build_signal()`
- `calculate_position_size()` — unchanged formula
- `get_scanner_criteria()` — unchanged
- `reset_daily_state()` — unchanged
- `mark_position_closed()` — unchanged
- `set_data_service()` — unchanged

**Abstract methods on OrbBaseStrategy** (subclasses implement):
- `_build_signal(symbol, candle, state, volume_threshold, vwap_str) → SignalEvent | None`
- `get_exit_rules() → ExitRules`
- `get_market_conditions_filter() → MarketConditionsFilter`

**OrbBaseStrategy needs these shared config fields** (accessed via properties):
- `orb_window_minutes: int`
- `min_range_atr_ratio: float`
- `max_range_atr_ratio: float`
- `chase_protection_pct: float`
- `breakout_volume_multiplier: float`
- `volume_threshold_rvol: float`
- `operating_window.latest_entry: str`

**Approach**: Define a `Protocol` or just use `getattr` on `self._config` for these fields since both `OrbBreakoutConfig` and `OrbScalpConfig` define them. Alternatively, define an `OrbSharedMixin` protocol. The cleanest approach: access via `self._config.orb_window_minutes` etc. — Pydantic configs on both subclasses have these fields.

**Critical rule**: `OrbBreakoutStrategy` must produce byte-identical signals after refactor. All 962 ORB tests pass with zero modifications (only import paths may change if `OrbSymbolState` moves).

### 2. ORB Scalp Strategy (DEC-123)

**New file:** `argus/strategies/orb_scalp.py`

```python
class OrbScalpStrategy(OrbBaseStrategy):
    """ORB Scalp — fast variant targeting quick 0.3–0.5R exits."""
    
    def __init__(self, config: OrbScalpConfig, data_service=None, clock=None):
        super().__init__(config, clock=clock)
        self._scalp_config = config
        self._data_service = data_service
    
    def _build_signal(self, symbol, candle, state, volume_threshold, vwap_str):
        """Build a single-target scalp signal with time stop in seconds."""
        entry_price = candle.close
        stop_price = state.or_midpoint
        risk_per_share = entry_price - stop_price
        
        # Single target: scalp_target_r * risk
        target = entry_price + risk_per_share * self._scalp_config.scalp_target_r
        
        shares = self.calculate_position_size(entry_price, stop_price)
        if shares <= 0:
            return None
        
        return SignalEvent(
            strategy_id=self.strategy_id,
            symbol=symbol,
            side=Side.LONG,
            entry_price=entry_price,
            stop_price=stop_price,
            target_prices=(target,),  # Single target — no T1/T2 split
            share_count=shares,
            rationale=f"ORB Scalp: {symbol} breakout...",
            time_stop_seconds=self._scalp_config.max_hold_seconds,  # NEW field
        )
    
    def get_exit_rules(self):
        return ExitRules(
            stop_type="fixed",
            stop_price_func="midpoint",
            targets=[ProfitTarget(r_multiple=self._scalp_config.scalp_target_r, position_pct=1.0)],
            time_stop_minutes=self._scalp_config.max_hold_seconds // 60 or 1,
        )
    
    def get_market_conditions_filter(self):
        return MarketConditionsFilter(
            allowed_regimes=["bullish_trending", "range_bound", "high_volatility"],
            max_vix=35.0,
        )
```

**New config:** `OrbScalpConfig` in `argus/core/config.py`

```python
class OrbScalpConfig(StrategyConfig):
    """ORB Scalp strategy configuration."""
    orb_window_minutes: int = Field(default=5, ge=1, le=60)
    scalp_target_r: float = Field(default=0.3, gt=0, le=2.0)
    max_hold_seconds: int = Field(default=120, ge=10, le=600)
    stop_placement: str = "midpoint"
    min_range_atr_ratio: float = Field(default=0.5, gt=0)
    max_range_atr_ratio: float = Field(default=999.0, gt=0)  # disabled per DEC-075
    chase_protection_pct: float = Field(default=0.005, ge=0, le=0.05)
    breakout_volume_multiplier: float = Field(default=1.5, gt=0)
    volume_threshold_rvol: float = Field(default=2.0, gt=0)
```

Add `load_orb_scalp_config()` function.

**New YAML:** `config/strategies/orb_scalp.yaml`

```yaml
strategy_id: "strat_orb_scalp"
name: "ORB Scalp"
version: "1.0.0"
enabled: true
asset_class: "us_stocks"

risk_limits:
  max_loss_per_trade_pct: 0.008   # Slightly less than ORB since faster turnover
  max_daily_loss_pct: 0.03
  max_consecutive_losses_pause: 5
  max_trades_per_day: 12           # More trades than ORB
  max_concurrent_positions: 3      # Can overlap more since exits are fast

operating_window:
  earliest_entry: "09:45"          # 10 min after ORB earliest (09:35)
  latest_entry: "11:30"
  force_close: "15:50"
  active_days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

benchmarks:
  min_win_rate: 0.55               # Higher win rate expected (smaller targets)
  min_avg_r_multiple: 0.25
  min_profit_factor: 1.2
  min_sharpe_ratio: 0.3
  max_drawdown_pct: 0.12

orb_window_minutes: 5
scalp_target_r: 0.3
max_hold_seconds: 120
stop_placement: "midpoint"
min_range_atr_ratio: 0.5
max_range_atr_ratio: 999.0
chase_protection_pct: 0.005
breakout_volume_multiplier: 1.5
volume_threshold_rvol: 2.0
```

### 3. Per-Signal Time Stop (DEC-122)

**Modify `SignalEvent`** in `argus/core/events.py`:

```python
class SignalEvent(Event):
    strategy_id: str = ""
    symbol: str = ""
    side: Side = Side.LONG
    entry_price: float = 0.0
    stop_price: float = 0.0
    target_prices: tuple[float, ...] = ()
    share_count: int = 0
    rationale: str = ""
    time_stop_seconds: int | None = None  # NEW — per-signal time stop override
```

**Modify `ManagedPosition`** in `argus/execution/order_manager.py`:

```python
@dataclass
class ManagedPosition:
    # ... existing fields ...
    time_stop_seconds: int | None = None  # NEW — from SignalEvent
```

**Modify `_handle_entry_fill()`** to copy `signal.time_stop_seconds` → `position.time_stop_seconds`.

**Modify tick-based time stop check** in Order Manager's `_check_time_stops()` or equivalent poll loop:

```python
# Current: uses global max_position_duration_minutes
# New: per-position time_stop_seconds takes priority
if position.time_stop_seconds is not None:
    elapsed = (now - position.entry_time).total_seconds()
    if elapsed >= position.time_stop_seconds:
        await self._flatten_position(position, reason="time_stop")
elif elapsed_minutes >= self._config.max_position_duration_minutes:
    await self._flatten_position(position, reason="time_stop")
```

**Backport to ORB**: `OrbBreakoutStrategy._build_signal()` should set `time_stop_seconds = self._orb_config.time_stop_minutes * 60`. This makes both strategies use the per-signal mechanism consistently. The global `max_position_duration_minutes` becomes a safety backstop only.

### 4. Single-Target Bracket Orders

The Order Manager's `_handle_entry_fill()` currently assumes `len(target_prices) >= 2` for T1/T2 bracket construction. For Scalp's single target:

**When `len(target_prices) == 1`**:
- Submit bracket with: entry + stop + single limit target
- `t1_shares = shares_total` (100%)
- `t2_price = target_prices[0]` (or 0.0 — no T2)
- `t1_price = target_prices[0]`
- Skip T2 limit order placement
- `t2_order_id = None`
- On T1 fill → position fully closed (no T2 monitoring needed)
- Stop-to-breakeven still applies after T1 would be illogical (position gone), so skip breakeven for single-target

**When `len(target_prices) >= 2`**: Existing behavior unchanged.

### 5. Cross-Strategy Risk (DEC-121, DEC-124)

**Add `ALLOW_ALL` to `DuplicateStockPolicy`:**

```python
class DuplicateStockPolicy(StrEnum):
    PRIORITY_BY_WIN_RATE = "priority_by_win_rate"
    FIRST_SIGNAL = "first_signal"
    BLOCK_ALL = "block_all"
    ALLOW_ALL = "allow_all"
```

**Change default** in `CrossStrategyRiskConfig`:

```python
class CrossStrategyRiskConfig(BaseModel):
    max_single_stock_pct: float = Field(default=0.05, gt=0, le=0.5)
    max_single_sector_pct: float = Field(default=0.15, gt=0, le=0.5)
    duplicate_stock_policy: DuplicateStockPolicy = DuplicateStockPolicy.ALLOW_ALL  # changed
```

**Risk Manager receives Order Manager reference:**

```python
class RiskManager:
    def __init__(self, config, broker, event_bus, clock=None, order_manager=None):
        # ... existing ...
        self._order_manager = order_manager  # NEW — for cross-strategy position checks
```

**New method: `_check_cross_strategy_risk()`** inserted in `evaluate_signal()` between step 4 (max concurrent) and step 5 (cash reserve):

```python
async def _check_cross_strategy_risk(self, signal: SignalEvent, account) -> str | None:
    """Check cross-strategy constraints. Returns rejection reason or None."""
    cross_config = self._config.cross_strategy
    
    # 4.5a: Single-stock exposure check
    if self._order_manager is not None:
        existing_exposure = 0.0
        managed = self._order_manager.get_managed_positions()  # new public method
        for positions_list in managed.values():
            for pos in positions_list:
                if pos.symbol == signal.symbol and not pos.is_fully_closed:
                    # Use entry_price as proxy for current price
                    existing_exposure += pos.shares_remaining * pos.entry_price
        
        proposed_exposure = signal.share_count * signal.entry_price
        total_exposure = existing_exposure + proposed_exposure
        max_exposure = account.equity * cross_config.max_single_stock_pct
        
        if total_exposure > max_exposure:
            return (
                f"Single-stock exposure would exceed {cross_config.max_single_stock_pct:.0%}: "
                f"${total_exposure:.0f} > ${max_exposure:.0f}"
            )
        
        # 4.5b: Duplicate stock policy
        if cross_config.duplicate_stock_policy != DuplicateStockPolicy.ALLOW_ALL:
            # Check if another strategy holds this symbol
            other_strategy_holding = False
            for positions_list in managed.values():
                for pos in positions_list:
                    if (pos.symbol == signal.symbol 
                        and pos.strategy_id != signal.strategy_id 
                        and not pos.is_fully_closed):
                        other_strategy_holding = True
                        break
            
            if other_strategy_holding:
                policy = cross_config.duplicate_stock_policy
                if policy == DuplicateStockPolicy.BLOCK_ALL:
                    return f"Duplicate stock blocked: {signal.symbol} held by another strategy"
                elif policy == DuplicateStockPolicy.FIRST_SIGNAL:
                    return f"First-signal policy: {signal.symbol} already held"
                elif policy == DuplicateStockPolicy.PRIORITY_BY_WIN_RATE:
                    # For V1: reject — would need win rate data to prioritize
                    return f"Priority policy: {signal.symbol} held by another strategy"
    
    return None  # All checks passed
```

**Add `get_managed_positions()` to Order Manager:**

```python
def get_managed_positions(self) -> dict[str, list[ManagedPosition]]:
    """Return a copy of managed positions for cross-strategy queries."""
    return {k: list(v) for k, v in self._managed_positions.items()}
```

### 6. CandleEvent Routing in main.py (DEC-125)

**Remove** `self._strategy: OrbBreakoutStrategy | None = None` singleton.

**Add** multi-strategy setup in Phase 8:

```python
# --- Phase 8: Strategy Instances ---
logger.info("[8/12] Creating strategy instances...")

# ORB Breakout
orb_config = load_orb_config(self._config_dir / "strategies" / "orb_breakout.yaml")
orb_strategy = OrbBreakoutStrategy(
    config=orb_config, data_service=self._data_service, clock=self._clock,
)

# ORB Scalp
scalp_config = load_orb_scalp_config(self._config_dir / "strategies" / "orb_scalp.yaml")
scalp_strategy = OrbScalpStrategy(
    config=scalp_config, data_service=self._data_service, clock=self._clock,
)

# Store for reference
self._strategies = [orb_strategy, scalp_strategy]
```

**Phase 9:** Register both strategies:

```python
for strategy in self._strategies:
    self._orchestrator.register_strategy(strategy)
```

**Phase 10:** Pass Order Manager to Risk Manager:

```python
self._risk_manager._order_manager = self._order_manager
# Or better: add to constructor. But this requires reordering init.
# Safest: setter method self._risk_manager.set_order_manager(self._order_manager)
```

**Phase 10.5 (NEW):** Wire CandleEvent routing:

```python
# --- Phase 10.5: Event Routing ---
logger.info("Wiring CandleEvent routing to strategies...")
self._event_bus.subscribe(CandleEvent, self._on_candle_for_strategies)
```

**New method on ArgusSystem:**

```python
async def _on_candle_for_strategies(self, event: CandleEvent) -> None:
    """Route CandleEvents to all active strategies."""
    for strategy in self._orchestrator.get_strategies().values():
        if not strategy.is_active:
            continue
        if event.symbol not in strategy.watchlist:
            continue
        signal = await strategy.on_candle(event)
        if signal is not None and self._risk_manager is not None:
            result = await self._risk_manager.evaluate_signal(signal)
            await self._event_bus.publish(result)
```

**Update `_reconstruct_strategy_state()`:** Loop over all strategies instead of `self._strategy`:

```python
async def _reconstruct_strategy_state(self, symbols):
    # ... time checks ...
    for strategy in self._orchestrator.get_strategies().values():
        for bar in todays_bars:
            await strategy.on_candle(bar)
```

**Update health monitor status:** Report per-strategy health instead of single strategy.

### 7. VectorBT ORB Scalp Sweep

**New file:** `argus/backtest/vectorbt_orb_scalp.py`

Simplified variant of `vectorbt_orb.py`. Key differences:
- Parameter grid: `scalp_target_r` × `max_hold_bars` (since 1m bars, max_hold_seconds / 60)
- Single target exit (no T1/T2 split) — exit 100% at target
- Time stop in bars: `max_hold_bars = max_hold_seconds // 60` (minimum 1 bar)
- Same entry detection: close > OR high, volume, VWAP, chase protection
- Same stop: OR midpoint

**SweepConfig for Scalp:**

```python
@dataclass
class ScalpSweepConfig:
    data_dir: Path
    symbols: list[str]
    start_date: date
    end_date: date
    output_dir: Path
    
    # Scalp-specific sweep ranges
    scalp_target_r_list: list[float] = field(default_factory=lambda: [0.2, 0.3, 0.4, 0.5])
    max_hold_bars_list: list[int] = field(default_factory=lambda: [1, 2, 3, 5])  # 1m bars
    
    # Fixed parameters (proven from ORB validation)
    or_minutes: int = 5
    min_gap_pct: float = 2.0
    stop_buffer_pct: float = 0.0
    
    # Scanner filters
    min_price: float = 5.0
    max_price: float = 10000.0
```

Total combos: 4 × 4 = 16 per symbol. 16 × 28 = 448 total. Runs in seconds.

### 8. Walk-Forward Validation

Use existing `walk_forward.py` with Scalp parameters. Same 35-month dataset.

**Run command:**
```bash
python -m argus.backtest.walk_forward \
    --mode fixed-params \
    --data-dir data/historical/1m \
    --config-dir config \
    --start 2023-03-01 --end 2026-01-31 \
    --strategy orb_scalp \
    --output-dir data/backtest_runs/orb_scalp_wf
```

This requires `walk_forward.py` to accept a `--strategy` flag and load the appropriate config + strategy class. Currently hardcoded to ORB. **Sprint 18 must generalize this.**

### 9. UX: Session Summary Card (18-D)

**API endpoint:** `GET /api/session-summary?date=YYYY-MM-DD`

Returns:
```json
{
    "date": "2026-02-25",
    "trade_count": 5,
    "wins": 3,
    "losses": 2,
    "net_pnl": 1847.23,
    "best_trade": {"symbol": "AMD", "r_multiple": 2.0, "pnl": 892.50},
    "worst_trade": {"symbol": "TSLA", "r_multiple": -1.0, "pnl": -445.00},
    "fill_rate": "4/4",
    "regime": "bullish_trending",
    "strategies_active": ["strat_orb_breakout", "strat_orb_scalp"]
}
```

**React component:** `SessionSummaryCard` — rendered at top of Dashboard when `now > 16:00 ET` and there are trades today. Dismissable (local state, not persisted). Shows key metrics with appropriate colors (green P&L, red losses). Strategy badges.

### 10. UX: Position Timeline (18-B)

**React component:** `PositionTimeline` — horizontal bar chart showing position durations.

- X-axis: time (9:30 AM to now or 4:00 PM)
- Y-axis: stacked horizontal bars, one per position
- Bar start: entry time. Bar end: exit time (or "now" if still open).
- Color: green (profitable), red (losing), gray (flat)
- Strategy badge on each bar
- Time stop indicator: vertical line showing when time stop would trigger
- Tooltip on hover: symbol, strategy, entry price, current P&L, R-multiple, hold duration

Critical for Scalp: tiny bars (30s–5min) visible alongside ORB's longer bars (5–15min).

---

# PART 2: SESSION BREAKDOWN

## Session Architecture

12 implementation sessions + 2 code review sessions. Organized into 3 phases with reviews after each.

### Phase A: Core Infrastructure (Sessions 1–6, Review after Session 6)
Sessions 1–3: ORBBase + Scalp strategy + tests
Sessions 4–5: Cross-strategy risk + per-signal time stops
Session 6: main.py multi-strategy wiring

### Phase B: Backtesting (Sessions 7–9, Review after Session 9)
Session 7: VectorBT Scalp sweep
Session 8: Walk-forward generalization + validation run
Session 9: Replay Harness integration + strategy spec + integration tests

### Phase C: UX + Polish (Sessions 10–12, Review after Session 12)
Session 10: Session Summary Card (API + React)
Session 11: Position Timeline (React)
Session 12: Final polish + lint + full test suite run

### Test Count Targets

| Session | New Tests | Running Total |
|---------|-----------|---------------|
| 1 (ORBBase extraction) | 0 (existing pass) | 1146 |
| 2 (OrbScalpStrategy) | ~15 | ~1161 |
| 3 (Scalp test suite) | ~55 | ~1216 |
| 4 (Cross-strategy risk) | ~30 | ~1246 |
| 5 (Per-signal time stop) | ~15 | ~1261 |
| 6 (main.py wiring) | ~15 | ~1276 |
| 7 (VectorBT Scalp) | ~10 | ~1286 |
| 8 (Walk-forward) | ~5 | ~1291 |
| 9 (Integration + spec) | ~15 | ~1306 |
| 10 (Session Summary API) | ~10 | ~1316 |
| 11 (Position Timeline) | ~5 | ~1321 |
| 12 (Polish) | ~5 | ~1326+ |

---

# PART 3: CLAUDE CODE SESSION PROMPTS

## Session 1: ORBBase Extraction

```
# Sprint 18, Session 1: ORBBase Extraction

Read CLAUDE.md first for project state.

## Context
Sprint 18 adds ORB Scalp (second strategy). This session extracts shared
opening-range logic into a base class so both ORB and Scalp inherit it.

## Decisions
- DEC-120: ORBBase extraction for shared OR formation + breakout detection
- Zero behavior changes to OrbBreakoutStrategy — all 962 ORB tests must pass

## Task

### Step 1: Create `argus/strategies/orb_base.py`

Extract from `argus/strategies/orb_breakout.py`:

1. Move `OrbSymbolState` dataclass to `orb_base.py`
2. Create `OrbBaseStrategy(BaseStrategy)` abstract class containing:
   - `__init__` that accepts any StrategyConfig with shared ORB fields
   - `_symbol_state` dict management (`_get_symbol_state`)
   - Market time calculation: `_market_open`, `_or_end_time`, `_latest_entry_time`
   - All time check methods: `_get_candle_time`, `_is_in_or_window`, `_is_past_or_window`, `_is_before_latest_entry`
   - `_finalize_opening_range()` — unchanged
   - `_check_breakout_conditions()` — but instead of building a SignalEvent directly, it should return the "breakout context" needed by subclasses. Approach: check all conditions (close > OR high, volume, VWAP, chase), and if all pass, call `self._build_breakout_signal(symbol, candle, state)` which is abstract.
   - `on_candle()` — the complete flow (OR formation → finalization → breakout check → signal)
   - `calculate_position_size()` — unchanged formula
   - `get_scanner_criteria()` — unchanged
   - `reset_daily_state()` — clears `_symbol_state`
   - `mark_position_closed()` — unchanged
   - `set_data_service()` — unchanged
3. Add abstract method: `_build_breakout_signal(symbol, candle, state) -> SignalEvent | None`
4. Keep `get_exit_rules()` and `get_market_conditions_filter()` abstract (from BaseStrategy)

### Step 2: Refactor `argus/strategies/orb_breakout.py`

1. Change to: `class OrbBreakoutStrategy(OrbBaseStrategy)`
2. Remove all code that moved to OrbBaseStrategy
3. Implement `_build_breakout_signal()` — this builds the T1/T2 signal exactly as the old `_check_breakout_conditions()` did
4. Keep `get_exit_rules()` and `get_market_conditions_filter()` implementations
5. Keep `on_tick()` (no-op)

### Step 3: Update imports

1. `argus/strategies/__init__.py` — export OrbBaseStrategy
2. Any file importing `OrbSymbolState` from `orb_breakout` → import from `orb_base`

### Step 4: Verify

Run the FULL test suite: `python -m pytest tests/ -x -q`
Every single existing test must pass. Zero modifications to test files.
If any test fails, the extraction is wrong — fix the base class, not the tests.

## Shared Config Field Access

OrbBaseStrategy needs to access: `orb_window_minutes`, `min_range_atr_ratio`,
`max_range_atr_ratio`, `chase_protection_pct`, `breakout_volume_multiplier`,
`operating_window.latest_entry`. Both OrbBreakoutConfig and OrbScalpConfig
(coming in Session 2) define these fields. Access them via `self._config.field`
— Pydantic guarantees they exist on both config types.

To make this type-safe, you can use a Protocol:

```python
class OrbConfigProtocol(Protocol):
    orb_window_minutes: int
    min_range_atr_ratio: float
    max_range_atr_ratio: float
    chase_protection_pct: float
    breakout_volume_multiplier: float
    volume_threshold_rvol: float
    operating_window: OperatingWindow
    risk_limits: StrategyRiskLimits
```

Or just use the concrete config types with `Union[OrbBreakoutConfig, OrbScalpConfig]`.
Your call on which approach is cleaner — the Protocol is more extensible for future
ORB variants.

## Acceptance Criteria
- [ ] `orb_base.py` created with OrbBaseStrategy + OrbSymbolState
- [ ] `orb_breakout.py` refactored to inherit from OrbBaseStrategy
- [ ] ALL existing tests pass: `python -m pytest tests/ -x -q` (1146 tests)
- [ ] Zero test file modifications
- [ ] `ruff check argus/ tests/` passes clean
```

## Session 2: OrbScalpStrategy + Config

```
# Sprint 18, Session 2: OrbScalpStrategy + Config

Read CLAUDE.md first.

## Context
Session 1 extracted OrbBaseStrategy. This session creates the ORB Scalp
strategy class and its configuration.

## Decisions
- DEC-123: Single target exit (no T1/T2), 0.3R default, 120s hold, midpoint stop

## Important: Timezone Pattern (RSK-017)
OrbBaseStrategy inherits the DEC-061 ET conversion pattern from the ORB fix.
Verify this works correctly for Scalp's time windows (09:45–11:30 ET) with
explicit regression tests. The ORB timezone bug was silent — zero trades, no
errors. Don't assume inheritance handles it; test it.

## Task

### Step 1: Add OrbScalpConfig to `argus/core/config.py`

```python
class OrbScalpConfig(StrategyConfig):
    """ORB Scalp strategy configuration."""
    orb_window_minutes: int = Field(default=5, ge=1, le=60)
    scalp_target_r: float = Field(default=0.3, gt=0, le=2.0)
    max_hold_seconds: int = Field(default=120, ge=10, le=600)
    stop_placement: str = "midpoint"
    min_range_atr_ratio: float = Field(default=0.5, gt=0)
    max_range_atr_ratio: float = Field(default=999.0, gt=0)
    chase_protection_pct: float = Field(default=0.005, ge=0, le=0.05)
    breakout_volume_multiplier: float = Field(default=1.5, gt=0)
    volume_threshold_rvol: float = Field(default=2.0, gt=0)
```

Add `load_orb_scalp_config(path: Path) -> OrbScalpConfig` function.

### Step 2: Create `config/strategies/orb_scalp.yaml`

Use values from the implementation spec:
- strategy_id: "strat_orb_scalp"
- name: "ORB Scalp"
- earliest_entry: "09:45" (10 min after ORB)
- max_trades_per_day: 12
- max_concurrent_positions: 3
- scalp_target_r: 0.3
- max_hold_seconds: 120
- benchmarks: higher win_rate (0.55), lower avg_r (0.25)

### Step 3: Create `argus/strategies/orb_scalp.py`

```python
class OrbScalpStrategy(OrbBaseStrategy):
```

Implement:
- `__init__`: store `self._scalp_config`
- `_build_breakout_signal()`: single target at `scalp_target_r * risk_per_share`,
  single element `target_prices=(target,)`, set `time_stop_seconds=self._scalp_config.max_hold_seconds`
- `get_exit_rules()`: single ProfitTarget at 100% position
- `get_market_conditions_filter()`: same regimes as ORB (bullish_trending, range_bound, high_volatility)
- `on_tick()`: no-op (same as ORB)

### Step 4: Add `time_stop_seconds` to SignalEvent

In `argus/core/events.py`, add to `SignalEvent`:
```python
time_stop_seconds: int | None = None
```

Also update OrbBreakoutStrategy's `_build_breakout_signal()` to set
`time_stop_seconds = self._orb_config.time_stop_minutes * 60`.

### Step 5: Update exports

- `argus/strategies/__init__.py` — export OrbScalpStrategy
- `argus/core/config.py` — ensure OrbScalpConfig is importable
- `argus/__init__.py` — add if needed

### Step 6: Basic smoke tests

Write ~15 tests in `tests/strategies/test_orb_scalp.py`:
- Config validation (OrbScalpConfig, load from YAML)
- Strategy initialization
- Opening range formation (reuse patterns from test_orb_breakout.py)
- Single breakout signal: verify target_prices has 1 element
- Verify time_stop_seconds is set on signal
- Verify strategy_id is "strat_orb_scalp"

### Step 7: Verify

`python -m pytest tests/ -x -q` — all tests pass
`ruff check argus/ tests/` — clean

## Acceptance Criteria
- [ ] OrbScalpConfig in config.py with validation
- [ ] orb_scalp.yaml with tuned defaults
- [ ] OrbScalpStrategy inheriting OrbBaseStrategy
- [ ] time_stop_seconds field on SignalEvent
- [ ] ORB also sets time_stop_seconds (backported)
- [ ] ~15 new tests passing
- [ ] All 1146 + new tests pass
- [ ] Ruff clean
```

## Session 3: ORB Scalp Comprehensive Test Suite

```
# Sprint 18, Session 3: ORB Scalp Comprehensive Tests

Read CLAUDE.md first.

## Context
Sessions 1–2 created OrbBaseStrategy and OrbScalpStrategy. This session
builds the full test suite mirroring test_orb_breakout.py patterns.

## Task

### Create comprehensive tests in `tests/strategies/test_orb_scalp.py`

Follow the exact patterns from `tests/strategies/test_orb_breakout.py` (962 lines).
Use the same helper functions pattern: `make_scalp_config()`, `make_candle()`, `make_or_candles()`.

#### Test Categories (~55 tests):

**Config Tests (~8):**
- Default config values
- YAML loading with `load_orb_scalp_config`
- Validation: scalp_target_r bounds, max_hold_seconds bounds
- Config with custom values

**Opening Range Formation (~10):**
- OR forms correctly with 5-min window
- OR high/low/midpoint calculated correctly
- OR validates against ATR bounds
- OR rejected: range too tight
- OR rejected: range too wide
- OR rejected: no candles
- Multiple symbols track independently
- Pre-OR candles ignored after OR complete

**Breakout Detection (~12):**
- Breakout signal generated: close > OR high + volume + VWAP
- No signal: close below OR high
- No signal: insufficient volume
- No signal: below VWAP
- No signal: chase protection triggered
- No signal: past latest entry time
- No signal: max trades reached
- No signal: max daily loss reached
- No signal: max concurrent positions reached
- Only one breakout per symbol
- Breakout with no ATR available (accepted)
- Breakout with no VWAP available (skips check)

**Scalp-Specific Signal Properties (~10):**
- Signal has single target_prices element (not two)
- Signal target_prices[0] = entry + scalp_target_r * risk
- Signal time_stop_seconds matches config.max_hold_seconds
- Position size uses allocated_capital * max_loss_per_trade_pct / risk
- Rationale string contains "ORB Scalp"
- strategy_id is "strat_orb_scalp"
- Different scalp_target_r values (0.2, 0.3, 0.4, 0.5)
- Different max_hold_seconds values
- Signal with custom config parameters

**State Management (~8):**
- reset_daily_state clears symbol states
- mark_position_closed updates state
- set_watchlist works correctly
- record_trade_result updates P&L and count
- is_active property
- allocated_capital property
- Multiple symbols can fire independently
- Reconstruct state from trade logger

**Timezone Regression (RSK-017, ~4 tests):**
- Candle with UTC timestamp: OR window detection uses ET conversion (DEC-061 pattern)
- Entry at 09:45 ET boundary: signal generated (not rejected)
- Entry at 11:31 ET: signal rejected (past latest_entry)
- OR formation with mixed UTC timestamps: correct ET grouping

**Exit Rules + Market Conditions (~5):**
- get_exit_rules returns single target at 100%
- get_exit_rules time_stop reflects seconds
- get_market_conditions_filter matches ORB's regimes
- get_scanner_criteria returns expected values

**Edge Cases (~5):**
- Very short max_hold_seconds (10s)
- Very high scalp_target_r (0.5)
- Zero allocated capital → 0 shares
- Stop price >= entry price → 0 shares
- Multiple strategies with same symbol (state isolation)

### Verify

`python -m pytest tests/strategies/test_orb_scalp.py -v` — all pass
`python -m pytest tests/ -x -q` — full suite passes
`ruff check argus/ tests/` — clean

## Acceptance Criteria
- [ ] ~55 new tests in test_orb_scalp.py
- [ ] All follow existing test patterns
- [ ] Full test suite passes
- [ ] Ruff clean
```

## Session 4: Cross-Strategy Risk

```
# Sprint 18, Session 4: Cross-Strategy Risk Integration

Read CLAUDE.md first.

## Context
ORB Scalp exists but the Risk Manager doesn't enforce cross-strategy limits.
This session implements the infrastructure for multi-strategy risk management.

## Decisions
- DEC-121: ALLOW_ALL duplicate stock policy as default
- DEC-124: Risk Manager receives Order Manager reference
- DEC-126: Sector exposure deferred (DEF-020)

## Task

### Step 1: Add ALLOW_ALL to DuplicateStockPolicy

In `argus/core/config.py`:
```python
class DuplicateStockPolicy(StrEnum):
    PRIORITY_BY_WIN_RATE = "priority_by_win_rate"
    FIRST_SIGNAL = "first_signal"
    BLOCK_ALL = "block_all"
    ALLOW_ALL = "allow_all"
```

Change default in CrossStrategyRiskConfig to `DuplicateStockPolicy.ALLOW_ALL`.

### Step 2: Add Order Manager reference to Risk Manager

In `argus/core/risk_manager.py`:
- Add `order_manager` parameter to `__init__` (optional, default None)
- Store as `self._order_manager`
- Add `set_order_manager(om)` setter for cases where init order prevents constructor injection

### Step 3: Add `get_managed_positions()` to Order Manager

In `argus/execution/order_manager.py`:
```python
def get_managed_positions(self) -> dict[str, list[ManagedPosition]]:
    """Return a copy of managed positions for cross-strategy queries."""
    return {k: list(v) for k, v in self._managed_positions.items()}
```

### Step 4: Implement cross-strategy checks in evaluate_signal()

Add `_check_cross_strategy_risk(signal, account)` method. Insert call between
step 4 (max concurrent) and step 5 (cash reserve) in evaluate_signal():

```python
# 4.5: Cross-strategy risk checks
cross_reason = await self._check_cross_strategy_risk(signal, account)
if cross_reason:
    return OrderRejectedEvent(signal=signal, reason=cross_reason)
```

The method checks:
1. Single-stock exposure: sum all open positions in signal.symbol across strategies,
   add proposed exposure, reject if > max_single_stock_pct * equity
2. Duplicate stock policy (only if not ALLOW_ALL):
   - BLOCK_ALL: reject if any other strategy holds this symbol
   - FIRST_SIGNAL: reject if any other strategy holds this symbol
   - PRIORITY_BY_WIN_RATE: reject (V1 simplified — need win rate data for proper impl)

### Step 5: Write tests (~30)

In `tests/core/test_risk_manager.py` (extend existing file or new file
`tests/core/test_cross_strategy_risk.py`):

**Cross-strategy exposure tests:**
- Signal approved: no existing positions in symbol
- Signal approved: existing positions under max_single_stock_pct
- Signal rejected: exposure would exceed max_single_stock_pct
- Signal approved: existing positions from SAME strategy (not cross-strategy issue)
- Multiple strategies holding same stock: combined exposure check

**Duplicate stock policy tests:**
- ALLOW_ALL: both strategies can trade same symbol
- BLOCK_ALL: second strategy rejected
- FIRST_SIGNAL: second strategy rejected
- PRIORITY_BY_WIN_RATE: second strategy rejected (V1)
- No conflict: different symbols

**Edge cases:**
- Order Manager not set (skip cross-strategy checks gracefully)
- Empty managed positions
- Fully closed positions not counted
- Signal for symbol with partially closed position (correct remaining shares calc)

### Step 6: Verify

`python -m pytest tests/ -x -q` — all pass
`ruff check argus/ tests/` — clean

## Acceptance Criteria
- [ ] ALLOW_ALL added to DuplicateStockPolicy, set as default
- [ ] Risk Manager accepts Order Manager reference
- [ ] get_managed_positions() on Order Manager
- [ ] _check_cross_strategy_risk() implemented and wired into evaluate_signal()
- [ ] ~30 new tests
- [ ] All tests pass
- [ ] Ruff clean
```

## Session 5: Per-Signal Time Stops

```
# Sprint 18, Session 5: Per-Signal Time Stops in Order Manager

Read CLAUDE.md first.

## Context
SignalEvent now has time_stop_seconds (Session 2). This session makes the
Order Manager respect it, and handles single-target bracket orders for Scalp.

## Decisions
- DEC-122: Per-position time stop from SignalEvent

## Task

### Step 1: Add time_stop_seconds to ManagedPosition

In `argus/execution/order_manager.py`:
```python
@dataclass
class ManagedPosition:
    # ... existing fields ...
    time_stop_seconds: int | None = None
```

### Step 2: Populate in _handle_entry_fill()

When creating ManagedPosition from an entry fill, copy time_stop_seconds
from the original signal:

```python
# In _handle_entry_fill, find where ManagedPosition is created:
position = ManagedPosition(
    # ... existing fields ...
    time_stop_seconds=pending.signal.signal.time_stop_seconds if pending.signal else None,
)
```

Check the actual code path — the signal is accessible via `pending.signal.signal`
(OrderApprovedEvent.signal is a SignalEvent). Verify this chain.

### Step 3: Modify time stop check

Find the existing time stop check (uses max_position_duration_minutes).
Change to per-position check:

```python
# Per-position time stop (from strategy signal)
if position.time_stop_seconds is not None:
    elapsed_seconds = (now - position.entry_time).total_seconds()
    if elapsed_seconds >= position.time_stop_seconds:
        await self._flatten_position(position, reason="time_stop")
        continue
# Fallback: global max_position_duration_minutes
elif elapsed_minutes >= self._config.max_position_duration_minutes:
    await self._flatten_position(position, reason="time_stop")
    continue
```

### Step 4: Handle single-target bracket orders

In `_handle_entry_fill()`, handle `len(target_prices) == 1`:

When the signal has only one target:
- t1_shares = shares_total (100% exit at target)
- t1_price = target_prices[0]
- t2_price = 0.0 (or target_prices[0] as fallback)
- Do NOT place a T2 limit order
- t2_order_id = None
- Skip stop-to-breakeven logic (position will be fully closed at T1)

Bracket order: entry + stop + single limit order (no T2).

Check if the bracket order methods (place_bracket_order on IBKR/Alpaca/Simulated)
handle a bracket with only stop + 1 target. May need to conditionally skip T2
in the bracket construction.

Also check `on_tick()` — the T2 monitoring logic should skip when t2_order_id
is None and t1_shares == shares_total. After T1 fills all shares, position is
fully closed.

### Step 5: Write tests (~15)

**Per-signal time stop tests:**
- Position with time_stop_seconds=120: flattened after 120s
- Position with time_stop_seconds=30: flattened after 30s
- Position without time_stop_seconds: uses global max_position_duration_minutes
- Time stop fires before T1 hit
- T1 hit before time stop

**Single-target bracket tests:**
- Signal with 1 target: bracket has stop + 1 limit
- T1 fill closes 100% of position
- No T2 monitoring for single-target positions
- No stop-to-breakeven for single-target positions

### Step 6: Verify

`python -m pytest tests/ -x -q`
`ruff check argus/ tests/`

## Acceptance Criteria
- [ ] ManagedPosition.time_stop_seconds populated from signal
- [ ] Per-position time stop check in Order Manager
- [ ] Global max_position_duration_minutes as fallback only
- [ ] Single-target bracket orders work (1 target)
- [ ] T1 fill on single-target = fully closed
- [ ] ~15 new tests
- [ ] All tests pass
- [ ] Ruff clean
```

## Session 6: main.py Multi-Strategy Wiring

```
# Sprint 18, Session 6: main.py Multi-Strategy Wiring

Read CLAUDE.md first.

## Context
Strategy and risk infrastructure is ready. This session generalizes main.py
from single-strategy to multi-strategy and wires CandleEvent routing.

## Decisions
- DEC-125: CandleEvent routing via EventBus to all active strategies

## Task

### Step 1: Remove single-strategy singleton

In `argus/main.py`:
- Remove `self._strategy: OrbBreakoutStrategy | None = None`
- Add `self._strategies: list[BaseStrategy] = []` (or access via orchestrator)

### Step 2: Update Phase 8 (Strategy Instances)

Create both strategies:
```python
from argus.strategies.orb_scalp import OrbScalpStrategy
from argus.core.config import load_orb_scalp_config

# ORB Breakout
orb_config = load_orb_config(self._config_dir / "strategies" / "orb_breakout.yaml")
orb_strategy = OrbBreakoutStrategy(
    config=orb_config, data_service=self._data_service, clock=self._clock,
)

# ORB Scalp
scalp_yaml = self._config_dir / "strategies" / "orb_scalp.yaml"
if scalp_yaml.exists():
    scalp_config = load_orb_scalp_config(scalp_yaml)
    scalp_strategy = OrbScalpStrategy(
        config=scalp_config, data_service=self._data_service, clock=self._clock,
    )
```

### Step 3: Update Phase 9 (Orchestrator)

Register all strategies:
```python
self._orchestrator.register_strategy(orb_strategy)
if scalp_strategy:
    self._orchestrator.register_strategy(scalp_strategy)
```

Update health monitor to report per-strategy status.

### Step 4: Update Phase 10 (Order Manager + Risk Manager wiring)

After Order Manager is created, wire it to Risk Manager:
```python
self._risk_manager.set_order_manager(self._order_manager)
```

### Step 5: Add CandleEvent routing (Phase 10.5)

```python
self._event_bus.subscribe(CandleEvent, self._on_candle_for_strategies)
```

New method:
```python
async def _on_candle_for_strategies(self, event: CandleEvent) -> None:
    for strategy in self._orchestrator.get_strategies().values():
        if not strategy.is_active:
            continue
        if event.symbol not in strategy.watchlist:
            continue
        signal = await strategy.on_candle(event)
        if signal is not None and self._risk_manager is not None:
            result = await self._risk_manager.evaluate_signal(signal)
            await self._event_bus.publish(result)
```

### Step 6: Update _reconstruct_strategy_state()

Loop over all strategies:
```python
for strategy in self._orchestrator.get_strategies().values():
    for bar in todays_bars:
        await strategy.on_candle(bar)
```

### Step 7: Update Phase 12 (API AppState)

The `strategies` field in AppState already comes from `self._orchestrator.get_strategies()`.
Verify this still works with multiple strategies.

### Step 8: Update health monitor status

Report multi-strategy health:
```python
strategies = self._orchestrator.get_strategies()
active = sum(1 for s in strategies.values() if s.is_active)
total = len(strategies)
self._health_monitor.update_component(
    "strategy",
    ComponentStatus.HEALTHY if active > 0 else ComponentStatus.DEGRADED,
    message=f"{active}/{total} strategies active",
)
```

### Step 9: Update tests/test_main.py

Update main.py tests to account for multi-strategy setup:
- Startup creates two strategy instances
- Both registered with Orchestrator
- CandleEvent routing subscription exists
- Shutdown handles multiple strategies

### Step 10: Verify

`python -m pytest tests/ -x -q`
`ruff check argus/ tests/`

## Acceptance Criteria
- [ ] Single-strategy singleton removed
- [ ] Both ORB + Scalp created and registered
- [ ] CandleEvent routing via EventBus subscription
- [ ] Risk Manager wired to Order Manager
- [ ] _reconstruct_strategy_state loops all strategies
- [ ] Health monitor reports multi-strategy status
- [ ] ~15 new/updated tests
- [ ] All tests pass
- [ ] Ruff clean
```

## Session 7: VectorBT ORB Scalp Sweep

```
# Sprint 18, Session 7: VectorBT ORB Scalp Parameter Sweep

Read CLAUDE.md first.

## Context
Strategy implementation complete. This session creates the VectorBT
parameter sweep module for ORB Scalp.

## Task

### Step 1: Create `argus/backtest/vectorbt_orb_scalp.py`

Simplified variant of `vectorbt_orb.py`. Key differences from ORB sweep:

1. **Parameter grid:** Only sweep `scalp_target_r` and `max_hold_bars`:
   - scalp_target_r_list: [0.2, 0.3, 0.4, 0.5]
   - max_hold_bars_list: [1, 2, 3, 5] (1m bars → 60s, 120s, 180s, 300s)
   - Fixed: or_minutes=5, min_gap_pct=2.0, stop_buffer_pct=0.0

2. **Single target exit:** Exit 100% at target. No T1/T2 split.
   The vectorized exit logic checks for `close >= target` on each bar.
   First bar where target is hit → exit at target price.

3. **Time stop in bars:** If `max_hold_bars` reached without hitting target or stop,
   exit at the close of that bar.

4. **Stop:** OR midpoint (same as ORB).

5. **Entry:** Same as ORB — close > OR high, volume > threshold, VWAP check.

### Step 2: Reuse infrastructure from vectorbt_orb.py

Copy the data loading, bar processing, and metric calculation functions.
Only the trade simulation loop changes.

The vectorized exit for each day/symbol:
```python
# For each entry bar (first bar with close > OR high + volume + VWAP):
entry_price = close[entry_bar]
stop_price = or_midpoint
risk = entry_price - stop_price
target_price = entry_price + scalp_target_r * risk

# Scan forward from entry_bar:
for i in range(entry_bar + 1, min(entry_bar + max_hold_bars + 1, len(close))):
    if low[i] <= stop_price:
        exit_price = stop_price  # Stopped out
        break
    if high[i] >= target_price:
        exit_price = target_price  # Target hit
        break
else:
    exit_price = close[entry_bar + max_hold_bars]  # Time stop
```

### Step 3: CLI interface

```bash
python -m argus.backtest.vectorbt_orb_scalp \
    --data-dir data/historical/1m \
    --start 2023-03-01 --end 2026-01-31 \
    --output-dir data/backtest_runs/scalp_sweeps
```

### Step 4: Generate heatmap

2D heatmap: scalp_target_r (x) × max_hold_bars (y), color = Sharpe ratio.
Save as HTML (Plotly) in output directory.

### Step 5: Tests (~10)

- ScalpSweepConfig validation
- Single-symbol single-combo simulation produces correct trade count
- Target hit → exit at target price
- Stop hit → exit at stop price
- Time stop → exit at close
- Multi-symbol aggregation
- Output file generation

### Step 6: Run the sweep

Execute on full 35-month dataset with all 28 symbols.
Record results in session notes for code review.

### Verify

`python -m pytest tests/ -x -q`
`ruff check argus/ tests/`
```

## Session 8: Walk-Forward Generalization + Validation

```
# Sprint 18, Session 8: Walk-Forward Validation for ORB Scalp

Read CLAUDE.md first.

## Context
VectorBT sweep complete. This session generalizes walk_forward.py to support
multiple strategies and runs validation for ORB Scalp.

## Task

### Step 1: Generalize walk_forward.py

Currently hardcoded to ORB. Add `--strategy` CLI flag:
- `orb` → use OrbBreakoutConfig, OrbBreakoutStrategy, vectorbt_orb sweep
- `orb_scalp` → use OrbScalpConfig, OrbScalpStrategy, vectorbt_orb_scalp sweep

This is the minimum change — a strategy factory function:

```python
def get_strategy_factory(strategy_name: str):
    if strategy_name == "orb":
        return orb_factory  # existing
    elif strategy_name == "orb_scalp":
        return scalp_factory
    raise ValueError(f"Unknown strategy: {strategy_name}")
```

### Step 2: Scalp-specific walk-forward config

- Fixed-params mode with Scalp defaults (scalp_target_r=0.3, max_hold_bars=2)
- 15 windows on 35-month data (same as Sprint 11)
- WFE threshold: > 0.3

### Step 3: Run fixed-params walk-forward

```bash
python -m argus.backtest.walk_forward \
    --mode fixed-params \
    --strategy orb_scalp \
    --data-dir data/historical/1m \
    --start 2023-03-01 --end 2026-01-31 \
    --output-dir data/backtest_runs/orb_scalp_wf
```

### Step 4: Run Replay Harness cross-validation

Verify ORB Scalp works through the production code path:
- Feed historical data through ReplayHarness
- Compare trade counts: VectorBT vs Replay Harness
- Document any discrepancies (expected: VectorBT >= Replay, same as ORB)

The ReplayHarness currently creates OrbBreakoutStrategy internally.
Generalize to accept a strategy factory parameter.

### Step 5: Record results

Save walk-forward results + heatmaps in `data/backtest_runs/orb_scalp_wf/`.
Note WFE, OOS Sharpe, trade counts for the strategy spec sheet (Session 9).

### Step 6: Tests (~5)

- Walk-forward accepts --strategy orb_scalp
- ReplayHarness works with OrbScalpStrategy
- Cross-validation comparison runs

### Verify

`python -m pytest tests/ -x -q`
`ruff check argus/ tests/`
```

## Session 9: Strategy Spec + Integration Tests

```
# Sprint 18, Session 9: Strategy Spec Sheet + Integration Tests

Read CLAUDE.md first.

## Context
All implementation and backtesting complete. This session creates the
strategy documentation and multi-strategy integration tests.

## Task

### Step 1: Create `docs/strategies/STRATEGY_ORB_SCALP.md`

Fill in the strategy template (docs/04_STRATEGY_TEMPLATE.md) for ORB Scalp.
Use backtesting results from Sessions 7-8. Include:
- Strategy identity (strat_orb_scalp, v1.0.0, US Stocks)
- Description of the scalping thesis
- Market conditions filter (same regimes as ORB)
- Operating window (09:45–11:30)
- Scanner criteria (same as ORB — gap stocks)
- Entry criteria (close > OR high, volume, VWAP, chase protection)
- Exit rules (single target at scalp_target_r, time stop at max_hold_seconds)
- Position sizing formula
- Holding duration (10s–5min)
- Risk limits (from orb_scalp.yaml)
- Performance benchmarks
- Backtest results (from walk-forward)
- Version history

### Step 2: Multi-strategy integration tests

Create `tests/test_integration_sprint18.py`:

**Integration scenarios (~15 tests):**
- Two strategies register with Orchestrator, both get allocation
- CandleEvent routes to both strategies
- ORB fires breakout signal → Risk Manager approves
- Scalp fires breakout signal on same symbol → Risk Manager approves (ALLOW_ALL)
- Scalp fires signal, single-stock exposure exceeds 5% → rejected
- Scalp fires signal with BLOCK_ALL policy → rejected
- Scalp position exits after max_hold_seconds (time stop)
- ORB position exits after time_stop_minutes (time stop)
- Single-target bracket order works end-to-end
- Both strategies reset daily state correctly
- Orchestrator allocates capital to both strategies
- Watchlist shared between strategies
- ORB breakout + Scalp breakout → both positions managed simultaneously
- Position close event tracked per strategy by throttler
- Mid-day reconstruction replays bars to both strategies

### Step 3: Verify full suite

`python -m pytest tests/ -x -q` — all pass
`ruff check argus/ tests/` — clean

Count total tests. Target: ~1306.

## Acceptance Criteria
- [ ] STRATEGY_ORB_SCALP.md complete with backtest results
- [ ] ~15 integration tests
- [ ] Full suite passes
- [ ] Ruff clean
```

## Session 10: Session Summary Card (API + React)

```
# Sprint 18, Session 10: Session Summary Card

Read CLAUDE.md first.

## Context
UX add-on from UX_FEATURE_BACKLOG.md item 18-D. Post-market debrief card.

## Task

### Step 1: API endpoint

Add to `argus/api/routes/` (or extend existing routes):

`GET /api/session-summary?date=YYYY-MM-DD`

Implementation:
- Query TradeLogger for trades on the given date
- Calculate: trade count, wins, losses, net P&L
- Find best/worst trade by R-multiple
- Get fill rate (signals generated vs orders filled — may need to estimate)
- Get regime from Orchestrator's last classification
- Get active strategy list

Return JSON matching the schema in the implementation spec.

Default date = today if not provided.

### Step 2: React component

Create `argus/ui/src/components/SessionSummaryCard.tsx`:

- Shows when now > 16:00 ET and there are trades today
- Dismissable (local state via useState)
- Cards layout: net P&L (large, colored), trade count, wins/losses, best trade, worst trade
- Strategy badges for each active strategy
- Regime badge with color coding
- Framer Motion entrance animation (slide down, stagger children)
- Skeleton loading state while fetching

### Step 3: Add to Dashboard

Import SessionSummaryCard at top of Dashboard page.
Render above the existing dashboard content.

### Step 4: Tests (~10)

API tests:
- Session summary returns correct structure
- Correct trade count and P&L calculation
- Best/worst trade identification
- Empty day returns zeros
- Specific date parameter works

React: No unit tests (Sprint 15 pattern — visual verification in code review).

### Verify

`python -m pytest tests/ -x -q`
`ruff check argus/ tests/`
Build React: `cd argus/ui && npm run build`
```

## Session 11: Position Timeline

```
# Sprint 18, Session 11: Position Timeline

Read CLAUDE.md first.

## Context
UX add-on from UX_FEATURE_BACKLOG.md item 18-B. Horizontal timeline of
position durations. Critical for visualizing Scalp (30s–5min) alongside
ORB (5–15min) holds.

## Task

### Step 1: Data preparation

The existing WebSocket already streams position data with entry_time.
The React PositionsPanel has access to this data. No new API needed — use
existing position data from the WebSocket + REST position endpoints.

### Step 2: React component

Create `argus/ui/src/components/PositionTimeline.tsx`:

Layout:
- Horizontal bars on a time axis (9:30 AM to current time or 4:00 PM)
- One bar per position (open or recently closed)
- Bar color: green (profitable), red (losing), amber (flat/new)
- Bar width: proportional to hold duration
- Strategy badge on each bar (small pill: "ORB" or "SCALP")
- Time stop indicator: subtle vertical dashed line at projected time stop
- Responsive: full-width on all breakpoints

Interaction:
- Hover shows tooltip: symbol, strategy, entry price, P&L, hold duration, R-multiple
- Click opens trade detail panel (existing slide-in from Sprint 16)

Animation:
- Open positions: bar grows in real-time (Framer Motion layout animation)
- New positions: slide-in from left
- Closed positions: fade to 50% opacity over 2 seconds

Technical:
- Time axis scale: SVG or div-based (not canvas) for hover targets
- Auto-scroll to "now" marker
- Stack overlapping positions vertically

### Step 3: Add to Dashboard

Add PositionTimeline below the open positions section.
Toggle between table view and timeline view (or show both on desktop).

On mobile: timeline is horizontally scrollable.

### Step 4: Tests (~5)

- Component renders with empty positions
- Component renders with mock positions
- Timeline scale calculation (start/end times)
- Position bar width proportional to duration

### Verify

`cd argus/ui && npm run build` — builds clean
No new backend tests needed.
```

## Session 12: Final Polish + Lint + Full Test Run

```
# Sprint 18, Session 12: Final Polish

Read CLAUDE.md first.

## Context
All implementation complete. This session is cleanup, polish, and final verification.

## Task

### Step 1: Full test suite

```bash
python -m pytest tests/ -x -q --tb=short
```

Fix any failures. Count total tests.

### Step 2: Ruff

```bash
ruff check argus/ tests/
ruff format --check argus/ tests/
```

Fix any issues.

### Step 3: React build

```bash
cd argus/ui && npm run build
```

Fix any TypeScript errors.

### Step 4: Update exports

Verify all new modules are properly exported:
- `argus/strategies/__init__.py` — OrbBaseStrategy, OrbScalpStrategy
- `argus/core/config.py` — OrbScalpConfig, load_orb_scalp_config, ALLOW_ALL in DuplicateStockPolicy
- `argus/core/events.py` — time_stop_seconds on SignalEvent
- `argus/backtest/__init__.py` — vectorbt_orb_scalp

### Step 5: Verify dev mode

```bash
python -m argus.api --dev
```

Confirm the dev server starts with mock data showing both strategies.

### Step 6: Check for TODO/FIXME

```bash
grep -rn "TODO\|FIXME\|HACK\|XXX" argus/ --include="*.py" | head -20
```

Address or log as deferred items.

### Step 7: Record final metrics

- Total test count
- Files changed
- Files created
- Lines of code added (approximate)

## Acceptance Criteria
- [ ] All tests pass
- [ ] Ruff clean
- [ ] React builds clean
- [ ] Dev mode works with both strategies
- [ ] No unaddressed TODOs
```

---

# PART 4: CODE REVIEW PLAN

## Review Schedule

| Review | After Session | Scope | Duration |
|--------|---------------|-------|----------|
| **Review A** | Session 6 | Core infrastructure: ORBBase, Scalp strategy, cross-strategy risk, time stops, main.py wiring | ~1 hour |
| **Review B** | Session 12 | Backtesting, UX, integration tests, final polish | ~45 min |

## Review A Procedure (After Session 6)

### Materials Needed
1. Git diff: `git diff sprint-17-complete..HEAD` (or equivalent range)
2. Test results: `python -m pytest tests/ -x -q --tb=short 2>&1 | tail -20`
3. Ruff results: `ruff check argus/ tests/ 2>&1 | tail -10`
4. Screenshots of new tests passing (optional but helpful)

### Review Checklist

**Architecture:**
- [ ] OrbBaseStrategy correctly extracts shared logic
- [ ] OrbBreakoutStrategy produces identical signals post-refactor
- [ ] OrbScalpStrategy signals have correct properties (single target, time_stop_seconds)
- [ ] Cross-strategy risk check properly inserted in evaluate_signal() flow
- [ ] CandleEvent routing handles all edge cases (inactive strategy, symbol not in watchlist)
- [ ] main.py multi-strategy wiring is clean

**Correctness:**
- [ ] Time stop per-position logic correct (seconds vs minutes)
- [ ] Single-target bracket orders work (no T2 monitoring)
- [ ] Duplicate stock policy enforced correctly per mode
- [ ] Position sizing unchanged (same formula)
- [ ] OR formation unchanged (same logic in base class)

**Safety:**
- [ ] Cross-strategy exposure cap enforced (5% single stock)
- [ ] Global max_position_duration_minutes still works as fallback
- [ ] Circuit breaker still works with multiple strategies
- [ ] Risk Manager gracefully handles missing Order Manager reference

**Code Quality:**
- [ ] All new code has docstrings
- [ ] Type hints on all new functions
- [ ] No circular imports
- [ ] Consistent naming conventions
- [ ] Ruff clean

### Decisions to Confirm
- DEC-120 through DEC-126

### Output
- Approve or request changes
- Draft any doc updates needed
- Flag issues for remaining sessions

## Review B Procedure (After Session 12)

### Materials Needed
1. Full git diff from sprint start
2. Final test count + full test output
3. VectorBT sweep results (heatmaps, best parameters)
4. Walk-forward results (WFE, OOS metrics)
5. Screenshots: Session Summary Card (desktop + mobile), Position Timeline (desktop + mobile)
6. Strategy spec sheet (STRATEGY_ORB_SCALP.md)
7. React build output

### Review Checklist

**Backtesting:**
- [ ] VectorBT sweep covers correct parameter space
- [ ] Walk-forward WFE > 0.3 (or documented if not)
- [ ] Replay Harness cross-validation passed
- [ ] Results documented in strategy spec sheet

**UX:**
- [ ] Session Summary Card renders correctly on all breakpoints
- [ ] Position Timeline shows correct durations
- [ ] Animations follow Sprint 17.5 principles (animation-once, stable DOM)
- [ ] Skeleton loading on new components
- [ ] Dark theme consistent

**Integration:**
- [ ] Integration tests cover multi-strategy scenarios
- [ ] Dev mode works with both strategies
- [ ] No regression in existing functionality

**Documentation:**
- [ ] STRATEGY_ORB_SCALP.md complete
- [ ] Decision log entries drafted
- [ ] CLAUDE.md updated
- [ ] Sprint plan updated

### Output
- Final approval
- Complete doc sync package
- Sprint 18 marked complete

---

# PART 5: CODE REVIEW HANDOFF BRIEFS

## Review A Handoff (After Session 6)

```
# Sprint 18 Code Review A — Core Infrastructure

Sprint 18 adds ORB Scalp (second strategy) to ARGUS. Sessions 1–6 are
complete. This review covers the core infrastructure changes before
proceeding to backtesting (Sessions 7–9) and UX (Sessions 10–12).

**Before anything else:** Pull the latest from the repo:
https://github.com/stevengizzi/argus.git

Read these files to understand what changed:

1. `CLAUDE.md` — updated project state
2. `argus/strategies/orb_base.py` — NEW: shared ORB base class (DEC-120)
3. `argus/strategies/orb_scalp.py` — NEW: ORB Scalp strategy (DEC-123)
4. `argus/strategies/orb_breakout.py` — MODIFIED: now inherits OrbBaseStrategy
5. `argus/core/config.py` — MODIFIED: OrbScalpConfig, ALLOW_ALL policy, load_orb_scalp_config
6. `argus/core/events.py` — MODIFIED: time_stop_seconds on SignalEvent (DEC-122)
7. `argus/core/risk_manager.py` — MODIFIED: cross-strategy risk checks (DEC-121, DEC-124)
8. `argus/execution/order_manager.py` — MODIFIED: per-position time stops, single-target brackets, get_managed_positions()
9. `argus/main.py` — MODIFIED: multi-strategy wiring, CandleEvent routing (DEC-125)
10. `config/strategies/orb_scalp.yaml` — NEW
11. `tests/strategies/test_orb_scalp.py` — NEW: ~70 tests
12. `tests/core/test_cross_strategy_risk.py` — NEW: ~30 tests

**What I need from you:**

1. Review the ORBBase extraction:
   - Does the shared/separate boundary make sense?
   - Is OrbBreakoutStrategy behavior preserved? (All 962 ORB tests should pass unchanged)
   - Is the Protocol/typing approach for shared config fields clean?

2. Review cross-strategy risk:
   - Is the insertion point in evaluate_signal() correct?
   - Does the ALLOW_ALL default make sense?
   - Is the exposure calculation correct (using entry_price as proxy)?

3. Review CandleEvent routing in main.py:
   - Is the _on_candle_for_strategies method correct?
   - Are there race conditions with multiple strategies processing the same candle?
   - Is error handling adequate?

4. Review per-signal time stops:
   - Is the per-position override clean?
   - Does the single-target bracket flow work?

5. Check for any regressions or architectural issues.

6. Confirm decisions DEC-120 through DEC-126.

**Test results should be available in the repo.** If not, ask me to run:
```
python -m pytest tests/ -x -q --tb=short
ruff check argus/ tests/
```

After review, tell me:
- Approved / Changes needed
- Any issues to fix in Sessions 7–12
- Draft doc updates if needed
```

## Review B Handoff (After Session 12)

```
# Sprint 18 Code Review B — Final Review

Sprint 18 is complete. All 12 implementation sessions done. This is the
final review before marking Sprint 18 complete and doing the doc sync.

**Pull latest:** https://github.com/stevengizzi/argus.git

**Review scope (Sessions 7–12):**

1. `argus/backtest/vectorbt_orb_scalp.py` — NEW: VectorBT Scalp sweep
2. `argus/backtest/walk_forward.py` — MODIFIED: --strategy flag for multi-strategy
3. `argus/backtest/replay_harness.py` — MODIFIED: strategy factory for Scalp
4. `docs/strategies/STRATEGY_ORB_SCALP.md` — NEW: strategy spec sheet
5. `tests/test_integration_sprint18.py` — NEW: multi-strategy integration tests
6. `argus/api/routes/` — MODIFIED: session-summary endpoint
7. `argus/ui/src/components/SessionSummaryCard.tsx` — NEW
8. `argus/ui/src/components/PositionTimeline.tsx` — NEW

**What I need from you:**

1. Review backtesting:
   - VectorBT Scalp sweep: correct parameter space? Exit logic sound?
   - Walk-forward results: WFE acceptable? Parameters generalize?
   - Replay Harness cross-validation: any concerning discrepancies?

2. Review UX components:
   - I'll provide screenshots of both components on desktop + mobile
   - Check animation patterns (Framer Motion, animation-once refs)
   - Check responsive behavior at all breakpoints
   - Verify stable DOM structure (Sprint 17.5 principle)

3. Review integration tests:
   - Do they cover the critical multi-strategy scenarios?
   - Any gaps in coverage?

4. Review strategy spec sheet:
   - Complete? All fields filled in?
   - Backtest results match actual run outputs?

5. Final test count and overall health check.

**After review, produce the complete doc sync:**
- Decision Log entries (DEC-120 through DEC-126+)
- Project Knowledge update
- Sprint Plan update (Sprint 18 → completed)
- CLAUDE.md update
- Risk Register if needed
- Architecture doc if needed

I'll copy-paste all doc updates after your review.
```

---

# PART 6: DOC UPDATES TO MAKE NOW

These should be added to the docs before starting Claude Code sessions.

## 6A. Decision Log Entries (add to `05_DECISION_LOG.md`)

```markdown
### DEC-120 | ORBBase Strategy Extraction
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Extract shared opening range formation and breakout detection logic into `OrbBaseStrategy` base class. Both `OrbBreakoutStrategy` and `OrbScalpStrategy` inherit from it. |
| **Rationale** | ORB Scalp shares ~70% of ORB's code (OR formation, breakout detection, position sizing, scanner criteria). Extracting to a base class eliminates duplication and ensures future ORB variants slot in cleanly. Subclasses override only signal construction and exit rules. |
| **Alternatives** | (A) Subclass ORB directly — messy override of trade management. (B) Copy code — duplication risk. |
| **Status** | Active |

### DEC-121 | ALLOW_ALL Duplicate Stock Policy
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Add `ALLOW_ALL` to `DuplicateStockPolicy` enum and set it as the default. ORB and ORB Scalp can trade the same symbol simultaneously, subject to `max_single_stock_pct` (5%) exposure cap. |
| **Rationale** | ORB targets 2R over 15 minutes. Scalp targets 0.3R over 30–120 seconds. They exploit different phases of the same momentum event and have independent risk profiles. Combined exposure is already gated by the single-stock cap. Blocking same-stock trades across strategies would eliminate valid diversified signals. |
| **Alternatives** | BLOCK_ALL — too restrictive. FIRST_SIGNAL — arbitrary winner. PRIORITY_BY_WIN_RATE — requires win rate data not yet available in real-time. |
| **Status** | Active |

### DEC-122 | Per-Signal Time Stop
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Add `time_stop_seconds: int | None` field to `SignalEvent`. Carried to `ManagedPosition`. Order Manager checks per-position time stop before falling back to global `max_position_duration_minutes`. |
| **Rationale** | ORB Scalp needs time stops in seconds (30–300s), not minutes. Different strategies have fundamentally different hold durations. A per-signal mechanism is cleaner than per-strategy config on the Order Manager. The global config becomes a safety backstop. |
| **Alternatives** | Per-strategy config on Order Manager — breaks encapsulation, requires OM to know about strategies. |
| **Status** | Active |

### DEC-123 | ORB Scalp Trade Management
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | ORB Scalp uses single-target exit (no T1/T2 split), defaulting to 0.3R target, 120s max hold, OR midpoint stop. Sends `target_prices=(target,)` with one element. |
| **Rationale** | Scalp trades are too fast for partial exits. The entire position exits at the single target or gets stopped/timed out. 0.3R keeps the expected win rate high (>55%) while generating enough P&L per trade. 120s hold aligns with the "capture initial momentum burst" thesis. |
| **Alternatives** | T1/T2 split like ORB — unnecessary complexity for sub-5-minute trades. Higher R target — would reduce win rate below the scalp thesis. |
| **Status** | Active |

### DEC-124 | Risk Manager ↔ Order Manager Reference
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Risk Manager receives an Order Manager reference (via setter) for cross-strategy position queries. `get_managed_positions()` public method added to Order Manager. |
| **Rationale** | Cross-strategy risk checks need to know what positions are currently open *per strategy*. `broker.get_positions()` returns raw broker positions without strategy attribution. The Order Manager's `ManagedPosition` objects have `strategy_id`, making them the correct source for cross-strategy queries. |
| **Alternatives** | Query broker + match by symbol — loses strategy attribution. Shared position tracker — unnecessary abstraction for V1. |
| **Status** | Active |

### DEC-125 | CandleEvent Routing via EventBus
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | main.py subscribes to CandleEvent on the EventBus and routes candles to all active strategies via `_on_candle_for_strategies()`. Replaces the single-strategy `self._strategy` singleton. Strategies are accessed through `orchestrator.get_strategies()`. |
| **Rationale** | The live system had no CandleEvent → strategy routing (only existed in Replay Harness). With multiple strategies, a centralized router that checks `is_active` and watchlist membership before calling `on_candle()` is the cleanest pattern. Using the Orchestrator's registry as the source of truth keeps strategy lifecycle management in one place. |
| **Alternatives** | Each strategy subscribes to CandleEvent directly — would bypass active/watchlist checks and require strategies to self-filter. |
| **Status** | Active |

### DEC-126 | Sector Exposure Check Deferred
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Cross-strategy sector exposure check (`max_single_sector_pct`) deferred. No sector classification data available. Logged as DEF-020. |
| **Rationale** | Implementing the exposure cap requires mapping symbols to sectors (SIC codes, GICS, or similar). No data source currently provides this. Building a static mapping is fragile. IQFeed or Databento fundamentals could provide this when integrated. The single-stock cap (5%) provides sufficient concentration protection for V1. |
| **Status** | Active |
```

## 6B. Risk Register Entry (add to `06_RISK_REGISTER.md`)

```markdown
### RSK-025 | Multi-Strategy Same-Symbol Execution Risk
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-02-25 |
| **Category** | Execution |
| **Description** | With ALLOW_ALL duplicate stock policy, ORB and ORB Scalp can hold simultaneous positions in the same stock. If both are active and the stock gaps against both positions, the combined loss from one symbol could be significant even if individual positions are within risk limits. |
| **Likelihood** | Medium |
| **Impact** | Medium |
| **Mitigation** | `max_single_stock_pct` (5% of account) caps combined exposure. Circuit breaker triggers on total daily loss regardless of per-stock allocation. Monitor correlation between ORB and Scalp P&L during paper trading. |
| **Status** | Open — monitoring during paper trading |

### RSK-026 | Sub-Bar Backtesting Precision for Scalp
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-02-25 |
| **Category** | Validation |
| **Description** | ORB Scalp targets 30–120 second holds, but backtesting uses 1-minute bars. Synthetic ticks give ~15s granularity (4 per bar). Time stops shorter than 60s resolve at the nearest bar boundary, and intra-bar price dynamics (which determine whether the target or stop is hit first) are approximated by O→L→H→C ordering. |
| **Likelihood** | High (guaranteed imprecision) |
| **Impact** | Low-Medium (backtesting results are approximations, not exact) |
| **Mitigation** | Document limitation. Use backtesting for directional guidance, not exact P&L projection. Validate with live paper trading where actual tick data is available. Consider Databento tick-level replay in future if precision needed. |
| **Status** | Accepted — DEF-021 logged |
```

## 6C. Deferred Items (add to CLAUDE.md under "Deferred Items")

```markdown
- **DEF-020** (Sprint 18): Cross-strategy sector exposure check. Requires sector classification data. Trigger: IQFeed or fundamentals data integration.
- **DEF-021** (Sprint 18): Sub-bar backtesting precision for Scalp. Synthetic ticks give ~15s granularity. Trigger: If Scalp paper trading results diverge significantly from backtests.
```

## 6D. Sprint Plan Update (add to `10_PHASE3_SPRINT_PLAN.md`)

Update the Sprint 18 entry to reflect the finalized scope:

```markdown
#### Sprint 18 — ORB Scalp Strategy ← ACTIVE
**Target:** ~3 days (12 implementation sessions + 2 code reviews)
**Scope:**
- OrbBaseStrategy extraction (DEC-120) — shared OR formation + breakout detection
- OrbScalpStrategy (DEC-123) — single-target exit, 0.3R, 120s hold, per-signal time stop (DEC-122)
- OrbScalpConfig + orb_scalp.yaml
- Cross-strategy risk integration (DEC-121, DEC-124): ALLOW_ALL policy, single-stock exposure cap, Risk Manager ↔ Order Manager reference
- CandleEvent routing in main.py (DEC-125) — multi-strategy generalization
- Per-signal time stops in Order Manager (DEC-122)
- Single-target bracket orders (len(target_prices)==1)
- VectorBT parameter sweep (scalp_target_r × max_hold_bars)
- Walk-forward validation (35-month dataset, generalized pipeline)
- Replay Harness cross-validation
- Strategy spec sheet (STRATEGY_ORB_SCALP.md)
- Multi-strategy integration tests
- **UX add-ons:** Session Summary Card (18-D, ~3h), Position Timeline (18-B, ~4h)
- Deferred: sector exposure check (DEF-020), sub-bar precision (DEF-021)

**Session Plan:**
- Sessions 1–6: Core infrastructure (ORBBase, Scalp, cross-strategy risk, time stops, main.py)
- Code Review A after Session 6
- Sessions 7–9: Backtesting (VectorBT, walk-forward, Replay Harness, integration tests)
- Sessions 10–11: UX (Session Summary Card, Position Timeline)
- Session 12: Polish
- Code Review B after Session 12
```

## 6E. Project Knowledge Update

After Sprint 18 completes, update `02_PROJECT_KNOWLEDGE.md`:

**Under "Key Decisions Made":**
Add DEC-120 through DEC-126 summaries (one-liners matching the existing format).

**Under "Current Project State — Build Track":**
Add Sprint 18 entry:
```
- Sprint 18 (ORB Scalp + Multi-Strategy): ✅ COMPLETE — [test count] tests, Feb [date]. OrbBaseStrategy extraction (DEC-120), OrbScalpStrategy (0.3R, 120s, single-target — DEC-123), cross-strategy risk (ALLOW_ALL, exposure cap — DEC-121/124), per-signal time stops (DEC-122), CandleEvent routing (DEC-125), VectorBT sweep + walk-forward validation. Session Summary Card + Position Timeline. [X] implementation sessions.
```

**Under "Strategy Roster":**
Note that ORB Scalp is now implemented.

*(These updates are drafted at code review B, not now — wait for actual test counts and results.)*
