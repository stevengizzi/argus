# Sprint 19 — VWAP Reclaim Strategy — Implementation Spec

> Paste into Claude Code Session 1. Read CLAUDE.md first. 1317 pytest + 7 Vitest tests must pass before and after every session.

---

## Sprint Overview

**Goal:** Add VWAP Reclaim as ARGUS's third strategy — the first mean-reversion strategy, operating 10:00 AM–12:00 PM ET on stocks that pulled back below VWAP and are reclaiming it.

**Test target:** ~1460+ tests (pytest) + ~10+ Vitest after sprint completion.

**Key principle:** VWAP Reclaim inherits directly from `BaseStrategy`, NOT from `OrbBaseStrategy`. No shared logic with ORB. VWAP is already computed by `IndicatorEngine` — no new indicator infrastructure needed.

---

## Session 1: Config + Models (~30 min)

### 1.1 Add `VwapReclaimConfig` to `argus/core/config.py`

Add after `OrbScalpConfig`:

```python
class VwapReclaimConfig(StrategyConfig):
    """VWAP Reclaim strategy configuration.

    Mean-reversion strategy that buys stocks reclaiming VWAP after
    a pullback. Operates 10:00 AM – 12:00 PM ET.

    State machine: WATCHING → ABOVE_VWAP → BELOW_VWAP → entry (or EXHAUSTED)
    """

    # Pullback parameters
    min_pullback_pct: float = Field(default=0.002, ge=0, le=0.05)       # 0.2% minimum pullback depth
    max_pullback_pct: float = Field(default=0.02, ge=0, le=0.10)        # 2.0% maximum (beyond = sell-off, not pullback)
    min_pullback_bars: int = Field(default=3, ge=1, le=30)              # Minimum bars below VWAP (3 min)

    # Reclaim confirmation
    volume_confirmation_multiplier: float = Field(default=1.2, gt=0, le=5.0)  # Reclaim bar volume vs avg
    max_chase_above_vwap_pct: float = Field(default=0.003, ge=0, le=0.02)     # 0.3% max chase above VWAP

    # Targets and stops
    target_1_r: float = Field(default=1.0, gt=0)
    target_2_r: float = Field(default=2.0, gt=0)
    time_stop_minutes: int = Field(default=30, ge=1)
    stop_buffer_pct: float = Field(default=0.001, ge=0, le=0.05)  # 0.1% buffer below swing low
```

### 1.2 Add config loader function

```python
def load_vwap_reclaim_config(path: Path) -> VwapReclaimConfig:
    """Load VWAP Reclaim strategy config from YAML."""
    data = load_yaml_file(path)
    return VwapReclaimConfig(**data)
```

### 1.3 Create `config/strategies/vwap_reclaim.yaml`

```yaml
strategy_id: "strat_vwap_reclaim"
name: "VWAP Reclaim"
version: "1.0.0"
enabled: true
asset_class: "us_stocks"

# Operating window
operating_window:
  earliest_entry: "10:00"
  latest_entry: "12:00"
  force_close: "15:50"

# Pullback parameters
min_pullback_pct: 0.002      # 0.2% minimum pullback depth
max_pullback_pct: 0.02       # 2.0% maximum pullback depth
min_pullback_bars: 3         # 3 minutes minimum below VWAP

# Reclaim confirmation
volume_confirmation_multiplier: 1.2  # Reclaim volume vs average
max_chase_above_vwap_pct: 0.003     # 0.3% max chase

# Targets
target_1_r: 1.0
target_2_r: 2.0
time_stop_minutes: 30
stop_buffer_pct: 0.001       # 0.1% buffer below swing low

# Risk limits
risk_limits:
  max_loss_per_trade_pct: 0.01       # 1% of allocated capital
  max_daily_loss_pct: 0.03           # 3% daily loss limit
  max_trades_per_day: 8
  max_concurrent_positions: 3

# Performance benchmarks
benchmarks:
  min_win_rate: 0.45
  min_profit_factor: 1.1
  min_sharpe: 0.3
  max_drawdown_pct: 0.12
```

### 1.4 Add `StrategyType.VWAP_RECLAIM` to `argus/backtest/config.py`

```python
class StrategyType(StrEnum):
    ORB_BREAKOUT = "orb"
    ORB_SCALP = "orb_scalp"
    VWAP_RECLAIM = "vwap_reclaim"  # NEW
```

### 1.5 Update `__init__.py` exports

Add VwapReclaimConfig and load_vwap_reclaim_config to appropriate `__init__.py` exports.

**Checkpoint:** All 1317 tests pass. New config loads from YAML without error.

---

## Session 2: Strategy Core (~90 min)

### 2.1 Create `argus/strategies/vwap_reclaim.py`

This is the core implementation. Key design:

**Per-symbol state machine:**

```
WATCHING → ABOVE_VWAP → BELOW_VWAP → (entry signal) → ENTERED
                ↑            |
                +--- (back above VWAP without entry conditions) ---+
         Also: BELOW_VWAP → EXHAUSTED (pullback too deep)
```

**State dataclass:**

```python
from enum import StrEnum

class VwapState(StrEnum):
    WATCHING = "watching"           # Initial — waiting for first above-VWAP observation
    ABOVE_VWAP = "above_vwap"      # Stock confirmed above VWAP
    BELOW_VWAP = "below_vwap"      # Stock pulled back below VWAP
    ENTERED = "entered"            # Entry taken, position active
    EXHAUSTED = "exhausted"        # Pullback too deep or entry already taken

@dataclass
class VwapSymbolState:
    state: VwapState = VwapState.WATCHING
    pullback_low: float | None = None
    pullback_start_bar: int = 0        # Bar count when pullback started
    bars_below_vwap: int = 0           # How many consecutive bars below VWAP
    position_active: bool = False
    recent_volumes: list[int] = field(default_factory=list)  # For avg volume calc
```

**`on_candle()` logic:**

```python
async def on_candle(self, event: CandleEvent) -> SignalEvent | None:
    symbol = event.symbol
    if symbol not in self._watchlist:
        return None

    state = self._get_symbol_state(symbol)

    # Get current VWAP
    vwap = await self._data_service.get_indicator(symbol, "vwap") if self._data_service else None
    if vwap is None:
        return None  # No VWAP yet (early bars)

    # Track volume for averaging
    state.recent_volumes.append(event.volume)

    # State machine transitions
    match state.state:
        case VwapState.WATCHING:
            if event.close > vwap:
                state.state = VwapState.ABOVE_VWAP
            return None

        case VwapState.ABOVE_VWAP:
            if event.close < vwap:
                state.state = VwapState.BELOW_VWAP
                state.pullback_low = event.low
                state.pullback_start_bar = len(state.recent_volumes)
                state.bars_below_vwap = 1
            return None

        case VwapState.BELOW_VWAP:
            if event.close < vwap:
                # Still below — update pullback tracking
                state.bars_below_vwap += 1
                if event.low < (state.pullback_low or event.low):
                    state.pullback_low = event.low

                # Check if pullback too deep → exhausted
                pullback_depth = (vwap - state.pullback_low) / vwap if state.pullback_low else 0
                if pullback_depth > self._vwap_config.max_pullback_pct:
                    state.state = VwapState.EXHAUSTED
                return None

            # Candle CLOSED above VWAP → potential reclaim
            if event.close > vwap:
                return await self._check_reclaim_entry(symbol, event, state, vwap)

        case VwapState.ENTERED | VwapState.EXHAUSTED:
            return None

    return None
```

**`_check_reclaim_entry()` — entry condition checks:**

1. Time window: >= earliest_entry AND < latest_entry (10:00–12:00)
2. Internal risk limits pass
3. Concurrent positions under limit
4. Pullback depth >= min_pullback_pct (0.2%)
5. Bars below VWAP >= min_pullback_bars (3)
6. Volume confirmation: reclaim bar volume >= avg_volume × multiplier
7. Chase protection: close < VWAP × (1 + max_chase_above_vwap_pct)
8. Position size > 0

**Stop and targets:**
- `stop_price = pullback_low - (pullback_low × stop_buffer_pct)`
- `t1 = entry_price + risk_per_share × target_1_r`
- `t2 = entry_price + risk_per_share × target_2_r`
- `time_stop_seconds = time_stop_minutes × 60`

**Position size safety:** If `risk_per_share < entry_price * 0.001` (less than 0.1%), cap position size to prevent enormous positions from shallow pullbacks. Use `max(risk_per_share, entry_price * 0.003)` as minimum effective risk for sizing.

**Other required methods:**

- `get_scanner_criteria()` → Same as ORB: min_gap_pct=2%, min_price=10, max_price=200, min_volume=1M, RVOL >= 2.0
- `get_exit_rules()` → T1 at target_1_r (50%), T2 at target_2_r (50%), time stop, fixed stop type
- `get_market_conditions_filter()` → allowed_regimes=["bullish_trending", "range_bound", "high_volatility"], max_vix=35.0
- `calculate_position_size()` → Standard risk formula with minimum risk floor
- `reset_daily_state()` → Clear symbol states + call super()
- `mark_position_closed()` → Reset symbol's position_active flag
- `set_data_service()` → Store DataService reference (same pattern as OrbBase)

**Checkpoint:** Strategy class compiles cleanly. No tests yet.

---

## Session 3: Strategy Unit Tests (~90 min)

### Create `tests/strategies/test_vwap_reclaim.py`

**Test categories (target: ~50-60 tests):**

**State machine transitions:**
- WATCHING → ABOVE_VWAP on close > VWAP
- ABOVE_VWAP → BELOW_VWAP on close < VWAP
- BELOW_VWAP → entry signal on reclaim with all conditions met
- BELOW_VWAP → ABOVE_VWAP on reclaim without conditions (e.g., volume too low)
- BELOW_VWAP → EXHAUSTED on pullback too deep
- Multiple pullback attempts (above → below → above → below → reclaim)

**Entry condition rejections:**
- Pullback too shallow (below min_pullback_pct)
- Pullback duration too short (below min_pullback_bars)
- Volume not confirmed
- Chase protection triggered (close too far above VWAP)
- Before earliest entry time (10:00 AM)
- After latest entry time (12:00 PM)
- Max trades per day reached
- Max concurrent positions reached
- Insufficient capital (position size = 0)

**Signal construction:**
- Correct stop_price (pullback_low - buffer)
- Correct target_prices (T1 at 1.0R, T2 at 2.0R)
- Correct time_stop_seconds (30 min = 1800s)
- Correct share_count from position sizing
- Minimum risk floor prevents enormous positions

**Edge cases:**
- VWAP not available (early bars, no data service)
- Symbol not in watchlist → ignored
- Zero/negative allocated capital → no signal
- Candle exactly at VWAP (boundary conditions)

**Other method tests:**
- get_scanner_criteria() returns correct values
- get_exit_rules() returns T1/T2 with correct R-multiples
- get_market_conditions_filter() allows correct regimes
- reset_daily_state() clears symbol states
- mark_position_closed() resets position_active flag
- reconstruct_state() from TradeLogger

**Mock setup pattern:** Follow existing test patterns in `tests/strategies/test_orb_scalp.py`:
- Mock DataService with `get_indicator()` returning controlled VWAP values
- Use `FixedClock` for time control
- Create CandleEvents with specific OHLCV to trigger state transitions

**Checkpoint:** All new tests pass. All 1317 existing tests still pass.

---

## Session 4: System Integration (~45 min)

### 4.1 Wire VWAP Reclaim into `argus/main.py`

In the strategy creation phase (Phase 8/12):

```python
from argus.core.config import load_vwap_reclaim_config
from argus.strategies.vwap_reclaim import VwapReclaimStrategy

# After ORB Scalp creation:
vwap_reclaim_strategy: VwapReclaimStrategy | None = None
vwap_yaml = self._config_dir / "strategies" / "vwap_reclaim.yaml"
if vwap_yaml.exists():
    vwap_config = load_vwap_reclaim_config(vwap_yaml)
    vwap_reclaim_strategy = VwapReclaimStrategy(
        config=vwap_config, data_service=data_service, clock=self._clock
    )
    vwap_reclaim_strategy.set_watchlist(symbols)
    strategies_created.append("VwapReclaim")

# Register with Orchestrator:
if vwap_reclaim_strategy is not None:
    self._orchestrator.register_strategy(vwap_reclaim_strategy)
```

Add health monitor component:
```python
health_monitor.update_component(
    "strategy_vwap_reclaim", ComponentStatus.HEALTHY, "VWAP Reclaim running"
)
```

### 4.2 Update CandleEvent routing

The existing `_route_candle_to_strategies()` in main.py already iterates over all registered strategies. VWAP Reclaim just needs to be registered with the Orchestrator (done above). Verify the routing works for 3 strategies.

### 4.3 Update strategy reconstruction

In `_reconstruct_strategy_state()`, ensure VWAP Reclaim is included in the strategy loop. This should already work since it iterates over `self._orchestrator.get_strategies()`.

**Checkpoint:** System starts in dev mode with three strategies registered. All tests pass.

---

## Session 5: Integration Tests (~90 min)

### Create `tests/test_integration_sprint19.py`

**Test scenarios (target: ~15-18 tests):**

1. **Three-strategy allocation**
   - Orchestrator allocates equally: (1 - 0.20) / 3 = 26.7% each
   - No strategy exceeds 40% cap
   - Total allocation = 80% (20% cash reserve)

2. **ORB → VWAP Reclaim sequential trade (the intended flow)**
   - ORB trades breakout on AAPL at 9:40 AM
   - ORB exits at time stop (9:55 AM)
   - AAPL pulls back below VWAP at 10:15 AM
   - AAPL reclaims VWAP at 10:25 AM
   - VWAP Reclaim enters AAPL
   - Verify both trades have correct strategy IDs

3. **Three-strategy concurrent positions**
   - ORB holding AAPL, Scalp holding TSLA, VWAP Reclaim holding NVDA
   - All three risk-checked and approved
   - Cross-strategy position counts correct

4. **Same-symbol ALLOW_ALL**
   - ORB still holding AAPL when VWAP Reclaim triggers on AAPL
   - Both allowed under max_single_stock_pct (5%)

5. **VWAP Reclaim state machine complete cycle**
   - Feed candle sequence: above VWAP → below VWAP (3+ bars) → reclaim
   - Verify correct signal emission

6. **VWAP Reclaim rejection: pullback too shallow**
7. **VWAP Reclaim rejection: pullback too deep → EXHAUSTED**
8. **VWAP Reclaim rejection: volume not confirmed**
9. **VWAP Reclaim rejection: outside operating window**
10. **VWAP Reclaim rejection: max trades reached**

11. **Throttle isolation**
    - VWAP Reclaim throttled while ORB continues
    - Verify independent throttling per strategy

12. **Three-strategy allocation exhaustion**
    - All strategies at max positions
    - New signal rejected by Risk Manager

13. **Regime filtering**
    - Crisis regime → ORB active, VWAP Reclaim suspended
    - Verify per-strategy regime checks

14. **Three-strategy daily reset**
    - All strategies reset daily state
    - Symbol states cleared across all three

**Checkpoint:** All integration tests pass. Total pytest count target: ~1380+.

---

## Session 6: VectorBT Sweep (~90 min)

### Create `argus/backtest/vectorbt_vwap_reclaim.py`

**Design:** Follows the pattern in `vectorbt_orb_scalp.py` — iterative simulation per symbol-day, not fully vectorized (state machine is inherently sequential per-day).

**Parameter grid:**

```python
@dataclass
class VwapReclaimSweepConfig:
    data_dir: Path
    symbols: list[str]
    start_date: date
    end_date: date
    output_dir: Path

    # Swept parameters
    min_pullback_pct_list: list[float] = field(
        default_factory=lambda: [0.001, 0.002, 0.003, 0.005]
    )
    min_pullback_bars_list: list[int] = field(
        default_factory=lambda: [2, 3, 5, 8]
    )
    volume_multiplier_list: list[float] = field(
        default_factory=lambda: [1.0, 1.2, 1.5, 2.0]
    )
    target_r_list: list[float] = field(
        default_factory=lambda: [0.5, 1.0, 1.5]
    )
    time_stop_bars_list: list[int] = field(
        default_factory=lambda: [10, 15, 20, 30]
    )

    # Fixed parameters
    max_pullback_pct: float = 0.02
    max_chase_above_vwap_pct: float = 0.003
    stop_buffer_pct: float = 0.001
    min_gap_pct: float = 0.02
    min_price: float = 5.0
    max_price: float = 10000.0

    # Note: target_r is swept as a single target (T1 only) for sweep simplicity.
    # T1/T2 split is tested via Replay Harness.
```

**Total combos:** 4 × 4 × 4 × 3 × 4 = 768 (reduced from 2304 by dropping T2 from sweep — T2 is tested in Replay Harness)

**VWAP computation in sweep:**
```python
def compute_vwap(df: pd.DataFrame) -> pd.Series:
    """Cumulative VWAP from 1-minute bars."""
    tp = (df["high"] + df["low"] + df["close"]) / 3
    cum_tp_vol = (tp * df["volume"]).cumsum()
    cum_vol = df["volume"].cumsum()
    return cum_tp_vol / cum_vol.replace(0, np.nan)
```

**Per-day simulation logic:**
1. Compute VWAP for each bar
2. Apply gap filter (gap >= min_gap_pct from prev close to day open)
3. Run state machine: track above/below VWAP transitions
4. On reclaim: check pullback depth, duration, volume, chase
5. If entry: compute stop (pullback low - buffer), target, time stop
6. Track P&L

**Output:** Same format as ORB sweeps — per-combo metrics (total_trades, win_rate, avg_r, profit_factor, sharpe, max_dd) + heatmaps.

**CLI:**
```bash
python -m argus.backtest.vectorbt_vwap_reclaim \
    --data-dir data/historical/1m \
    --start 2023-03-01 --end 2026-01-31 \
    --output-dir data/backtest_runs/vwap_reclaim_sweeps
```

**Checkpoint:** Sweep runs without error. Results saved.

---

## Session 7: Walk-Forward Integration (~60 min)

### 7.1 Extend `argus/backtest/walk_forward.py`

Add VWAP Reclaim dispatch alongside existing ORB and ORB Scalp dispatches:

**In `WalkForwardConfig`:**
```python
# VWAP Reclaim parameter grid
vwap_min_pullback_pct_list: list[float] = field(...)
vwap_min_pullback_bars_list: list[int] = field(...)
vwap_volume_multiplier_list: list[float] = field(...)
vwap_target_r_list: list[float] = field(...)
vwap_time_stop_bars_list: list[int] = field(...)
```

**In `_run_in_sample_optimization()`:**
```python
if config.strategy == "vwap_reclaim":
    # Build VwapReclaimSweepConfig from WalkForwardConfig fields
    # Call run_vwap_reclaim_sweep()
    # Return best params
```

**In `_run_out_of_sample_validation()`:**
```python
if config.strategy == "vwap_reclaim":
    # Map best params to Replay Harness config
    # Run replay with VwapReclaimStrategy
```

**CLI update:**
```python
parser.add_argument("--strategy", choices=["orb", "orb_scalp", "vwap_reclaim"])
```

### 7.2 Update Replay Harness strategy factory

In `argus/backtest/replay_harness.py`, add VWAP Reclaim to `_create_strategy()`:

```python
if self._config.strategy_type == StrategyType.VWAP_RECLAIM:
    from argus.strategies.vwap_reclaim import VwapReclaimStrategy
    config = VwapReclaimConfig(
        strategy_id=self._config.strategy_id or "strat_vwap_reclaim",
        name="VWAP Reclaim",
        # ... map params from BacktestConfig
    )
    return VwapReclaimStrategy(config=config, data_service=self._data_service, clock=self._clock)
```

### 7.3 Add `BacktestConfig` fields for VWAP Reclaim params

Add fields to `BacktestConfig` in `argus/backtest/config.py` for VWAP Reclaim parameters that the Replay Harness needs.

**Checkpoint:** Walk-forward pipeline accepts `--strategy vwap_reclaim`. Replay Harness creates VwapReclaimStrategy.

---

## Session 8: Run Backtests (~45 min)

1. Run VectorBT sweep on 35-month data
2. Analyze results — identify best parameter regions
3. Run walk-forward with 15 windows
4. Record WFE, OOS Sharpe
5. If WFE > 0.3: good. If not: note as provisional (DEC-132 re-validation needed)

**No code changes — this is an execution + analysis session.**

---

## Session 9: Dev Mock Data (~45 min)

### Update `argus/api/dev_state.py`

Following Sprint 18.5 pattern:

1. **Add VWAP Reclaim mock positions** — mid-morning entries (10:15 AM, 10:45 AM), 5–30 min holds
2. **Add VWAP Reclaim mock trades** — mix of wins/losses with exit reasons: TARGET_1, TARGET_2, STOP_LOSS, TIME_STOP
3. **Add strategy to system health** — `strategy_vwap_reclaim: HEALTHY`
4. **Add VWAP Reclaim strategy card** — strategy_id, allocatedPct, daily P&L, trade count
5. **Update allocation donut** — three-strategy split (33.3% each after cash reserve)
6. **Update performance breakdown** — three strategies in the breakdown

### Update `SessionSummaryCard` data

Include VWAP Reclaim trades in the after-hours summary.

**Checkpoint:** Dev mode (`python -m argus.api --dev`) shows three strategies everywhere.

---

## Session 10: Watchlist Sidebar (18-C, ~90 min)

### UX Feature 18-C from `docs/ui/UX_FEATURE_BACKLOG.md`

**Component:** `WatchlistSidebar` — collapsible sidebar showing scanner candidates

**Layout:**
- Desktop: 280px right sidebar on Dashboard page, collapsible
- Tablet: Slide-out panel from right edge
- Mobile: Full-screen overlay (accessed via toolbar button)

**Content per symbol:**
- Symbol name + current price
- Gap % badge
- Mini sparkline (SVG, 50×20px, last 30 bars)
- Strategy badges: which strategies are watching this symbol (ORB ▪ Scalp ▪ VWAP)
- VWAP Reclaim state indicator: colored dot (gray=watching, blue=above, amber=below, green=entered)

**Data source:** New WebSocket event type `WatchlistUpdateEvent` or extend existing system events. Alternatively, poll via REST endpoint.

**New API endpoint:**
```
GET /api/watchlist
→ [{symbol, price, gap_pct, strategies: ["orb", "scalp", "vwap_reclaim"], vwap_state: "below_vwap"}]
```

**Checkpoint:** Sidebar renders with mock data in dev mode. Responsive at all breakpoints.

---

## Session 11: Strategy Spec + Polish (~45 min)

### Create `docs/strategies/STRATEGY_VWAP_RECLAIM.md`

Fill in strategy template (04_STRATEGY_TEMPLATE.md) with all VWAP Reclaim parameters. Include backtest results from Session 8.

### Code review checklist:
- [ ] ruff lint clean
- [ ] All tests pass (pytest + Vitest)
- [ ] Type hints complete
- [ ] Docstrings on all public methods
- [ ] Config loads correctly from YAML
- [ ] Dev mode shows three strategies
- [ ] No regressions in existing strategies

---

## Session 12: Docs Update (~30 min)

Update these docs:
1. **05_DECISION_LOG.md** — New DEC entries for Sprint 19 decisions
2. **02_PROJECT_KNOWLEDGE.md** — Sprint 19 in completed work, update Build Track queue
3. **10_PHASE3_SPRINT_PLAN.md** — Move Sprint 19 to completed table
4. **03_ARCHITECTURE.md** — Add VwapReclaimStrategy to strategy section
5. **CLAUDE.md** — Update current state, test count

---

## Decisions to Log (DEC-NNN)

Check current highest DEC number before adding. Expected new entries:

| Decision | Summary |
|----------|---------|
| VwapReclaimStrategy standalone | Inherits from BaseStrategy, not OrbBase. No shared logic. |
| Scanner reuse | VWAP Reclaim uses same gap watchlist as ORB family. No separate scanner. |
| State machine design | 5-state: WATCHING → ABOVE_VWAP → BELOW_VWAP → ENTERED / EXHAUSTED |
| Stop at pullback swing low | Stop = pullback_low − buffer. Not VWAP-based (VWAP moves intraday). |
| T1/T2 targets | T1=1.0R (50%), T2=2.0R (50%). Configurable. |
| Position size minimum risk floor | Min effective risk = max(risk_per_share, entry × 0.003) to prevent oversizing on shallow pullbacks. |
| ALLOW_ALL for VWAP Reclaim | Same duplicate stock policy as ORB family (DEC-121 applies). |
| Watchlist sidebar (18-C) | Added in Sprint 19. Shows scanner candidates + strategy badges + VWAP state. |

---

## Architecture Notes for Claude Code

- **DataService access pattern:** `self._data_service.get_indicator(symbol, "vwap")` returns `float | None`. This is an in-memory cache lookup — no I/O. Safe to call on every candle.
- **Time handling:** All candle timestamps are UTC (DEC-049). Convert to ET for market hours comparisons: `candle.timestamp.astimezone(ET).time()`.
- **SignalEvent construction:** Use `time_stop_seconds` field (not minutes). T1/T2 as `target_prices=(t1, t2)` tuple.
- **Position active tracking:** Strategy must expose `mark_position_closed(symbol)` for Order Manager callback. See OrbBase pattern.
- **Config protocol:** VWAP Reclaim doesn't use a Protocol like OrbBase — it's a simple config class. Direct attribute access.

## Files to Create
- `argus/strategies/vwap_reclaim.py`
- `config/strategies/vwap_reclaim.yaml`
- `tests/strategies/test_vwap_reclaim.py`
- `tests/test_integration_sprint19.py`
- `argus/backtest/vectorbt_vwap_reclaim.py`
- `docs/strategies/STRATEGY_VWAP_RECLAIM.md`
- `argus/ui/src/components/WatchlistSidebar.tsx` (and sub-components)

## Files to Modify
- `argus/core/config.py` — add VwapReclaimConfig + loader
- `argus/backtest/config.py` — add StrategyType.VWAP_RECLAIM + BacktestConfig fields
- `argus/backtest/walk_forward.py` — add vwap_reclaim dispatch
- `argus/backtest/replay_harness.py` — add VwapReclaim to strategy factory
- `argus/main.py` — wire VwapReclaimStrategy
- `argus/api/dev_state.py` — add VWAP Reclaim mock data
- `argus/__init__.py` — update exports
