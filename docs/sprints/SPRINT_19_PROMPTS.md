# Sprint 19 — Claude Code Session Plan

> **Purpose:** Break Sprint 19 into Claude Code sessions sized to avoid context compaction while maintaining maximum implementation fidelity. Each session includes an exact copy-paste prompt.
>
> **Total sessions:** 12 implementation + 2 code review checkpoints = 14 interactions
>
> **Compaction strategy:** Each session targets 45–90 minutes of Claude Code work. Sessions are split at natural boundaries where the codebase is in a green state (all tests pass). No session creates more than ~3 files or modifies more than ~5 files.

---

## Session Sizing Rationale

| Risk Factor | Mitigation |
|------------|------------|
| Large file creation (>300 lines) | Split strategy core (Session 2) from tests (Session 3) |
| Multi-file coordination | Config + models first (Session 1), then strategy consumes them (Session 2) |
| Integration wiring touches many files | Dedicated session (Session 4) with small scope |
| Backtesting is complex + independent | Three sessions (6, 7, 8) isolated from strategy code |
| UX work is independent of backend | Sessions 9–10 can't regress backend tests |
| Walk-forward modification is surgical | Session 7 alone — the existing file is large and changes need precision |

---

## Session Map

```
Session 1: Config + Models ──┐
Session 2: Strategy Core ────┤
Session 3: Strategy Tests ───┤── CODE REVIEW CHECKPOINT 1 (after Session 5)
Session 4: System Integration┤
Session 5: Integration Tests ┘

Session 6: VectorBT Sweep ────┐
Session 7: Walk-Forward ──────┤
Session 8: Run Backtests ─────┤── CODE REVIEW CHECKPOINT 2 (after Session 10)
Session 9: Dev Mock Data ─────┤   (backtests analyzed in review)
Session 10: Watchlist Sidebar ┘

Session 11: Strategy Spec + Polish ──── (incorporates review feedback)
Session 12: Docs Update ──────────────── (final)
```

---

## Code Review Checkpoints

### Checkpoint 1: After Session 5 (Strategy + Integration Complete)

**When:** After all strategy code, system wiring, and integration tests pass.

**What to review:**
- `argus/strategies/vwap_reclaim.py` — state machine logic, edge cases, signal construction
- `argus/core/config.py` — VwapReclaimConfig correctness
- `config/strategies/vwap_reclaim.yaml` — parameter values
- `argus/main.py` — wiring changes
- `tests/strategies/test_vwap_reclaim.py` — test coverage completeness
- `tests/test_integration_sprint19.py` — scenario coverage
- Test count delta (should be ~65-75 new tests)

**Materials needed:** Git diff from sprint start, test output, list of new files.

**Procedure:** Steven opens new Claude.ai conversation, pastes Checkpoint 1 handoff brief (see below), provides git diff. Claude reviews strategy design, test coverage gaps, architectural concerns. Any issues become Session 11 fixes.

### Checkpoint 2: After Session 10 (All Implementation Complete)

**When:** After backtesting, dev mock data, and watchlist sidebar are done.

**What to review:**
- `argus/backtest/vectorbt_vwap_reclaim.py` — sweep logic, VWAP computation
- `argus/backtest/walk_forward.py` — dispatch changes
- `argus/backtest/replay_harness.py` — strategy factory addition
- `argus/api/dev_state.py` — mock data completeness
- Watchlist sidebar component(s)
- VectorBT sweep results + walk-forward analysis
- Full test count (target: ~1460+ pytest, ~10+ Vitest)

**Materials needed:** Git diff from Checkpoint 1, backtest output/results, screenshots of dev mode UI.

**Procedure:** Steven opens new Claude.ai conversation, pastes Checkpoint 2 handoff brief (see below). Claude reviews backtesting methodology, UI implementation, and flags any issues for Session 11. Also drafts decision log entries based on actual implementation choices.

---

## Copy-Paste Prompts

### Session 1: Config + Models

```
# Sprint 19, Session 1: Config + Models

Read CLAUDE.md first. Current state: 1317 pytest + 7 Vitest tests passing. Sprint 18.5 complete.

## Context
Sprint 19 adds VWAP Reclaim — ARGUS's first mean-reversion strategy. This session creates the configuration infrastructure only. No strategy logic yet.

## Tasks

### 1. Add VwapReclaimConfig to argus/core/config.py

Add after OrbScalpConfig class (~line 547):

```python
class VwapReclaimConfig(StrategyConfig):
    """VWAP Reclaim strategy configuration.

    Mean-reversion strategy that buys stocks reclaiming VWAP after
    a pullback. Operates 10:00 AM – 12:00 PM ET.

    State machine: WATCHING → ABOVE_VWAP → BELOW_VWAP → entry (or EXHAUSTED)
    """

    # Pullback parameters
    min_pullback_pct: float = Field(default=0.002, ge=0, le=0.05)
    max_pullback_pct: float = Field(default=0.02, ge=0, le=0.10)
    min_pullback_bars: int = Field(default=3, ge=1, le=30)

    # Reclaim confirmation
    volume_confirmation_multiplier: float = Field(default=1.2, gt=0, le=5.0)
    max_chase_above_vwap_pct: float = Field(default=0.003, ge=0, le=0.02)

    # Targets and stops
    target_1_r: float = Field(default=1.0, gt=0)
    target_2_r: float = Field(default=2.0, gt=0)
    time_stop_minutes: int = Field(default=30, ge=1)
    stop_buffer_pct: float = Field(default=0.001, ge=0, le=0.05)
```

### 2. Add config loader function

After load_orb_scalp_config (~line 668):

```python
def load_vwap_reclaim_config(path: Path) -> VwapReclaimConfig:
    """Load VWAP Reclaim strategy config from YAML."""
    data = load_yaml_file(path)
    return VwapReclaimConfig(**data)
```

### 3. Create config/strategies/vwap_reclaim.yaml

```yaml
strategy_id: "strat_vwap_reclaim"
name: "VWAP Reclaim"
version: "1.0.0"
enabled: true
asset_class: "us_stocks"

operating_window:
  earliest_entry: "10:00"
  latest_entry: "12:00"
  force_close: "15:50"

min_pullback_pct: 0.002
max_pullback_pct: 0.02
min_pullback_bars: 3
volume_confirmation_multiplier: 1.2
max_chase_above_vwap_pct: 0.003
target_1_r: 1.0
target_2_r: 2.0
time_stop_minutes: 30
stop_buffer_pct: 0.001

risk_limits:
  max_loss_per_trade_pct: 0.01
  max_daily_loss_pct: 0.03
  max_trades_per_day: 8
  max_concurrent_positions: 3

benchmarks:
  min_win_rate: 0.45
  min_profit_factor: 1.1
  min_sharpe: 0.3
  max_drawdown_pct: 0.12
```

### 4. Add StrategyType.VWAP_RECLAIM to argus/backtest/config.py

In the StrategyType enum:
```python
VWAP_RECLAIM = "vwap_reclaim"
```

### 5. Update argus/__init__.py exports

Add VwapReclaimConfig and load_vwap_reclaim_config to the config exports.

## Verification
- All 1317 existing tests pass
- New config loads: `python -c "from argus.core.config import load_vwap_reclaim_config; print('OK')"`
- YAML loads without error: `python -c "from argus.core.config import load_vwap_reclaim_config; from pathlib import Path; c = load_vwap_reclaim_config(Path('config/strategies/vwap_reclaim.yaml')); print(c.strategy_id, c.min_pullback_pct)"`

Commit message: `feat: add VwapReclaimConfig and strategy YAML (Sprint 19, Session 1)`
```

---

### Session 2: Strategy Core

```
# Sprint 19, Session 2: VWAP Reclaim Strategy Core

Read CLAUDE.md first. Session 1 complete — VwapReclaimConfig exists in config.py, YAML created, StrategyType added.

## Context
This session creates the VwapReclaimStrategy class. This is ARGUS's first mean-reversion strategy. It inherits directly from BaseStrategy (NOT OrbBaseStrategy). VWAP is already computed by IndicatorEngine and available via DataService.get_indicator(symbol, "vwap").

## Task: Create argus/strategies/vwap_reclaim.py

### Architecture
- Inherits from `BaseStrategy` directly
- Per-symbol state machine with 5 states: WATCHING, ABOVE_VWAP, BELOW_VWAP, ENTERED, EXHAUSTED
- Queries VWAP from DataService on every candle (in-memory cache lookup, no I/O)
- Entry on candle CLOSE above VWAP (not intra-bar cross) — consistent with ORB breakout confirmation pattern

### State Machine

```
WATCHING → ABOVE_VWAP (close > VWAP)
ABOVE_VWAP → BELOW_VWAP (close < VWAP) — start tracking pullback
BELOW_VWAP → entry signal (close > VWAP + all conditions met) → ENTERED
BELOW_VWAP → ABOVE_VWAP (close > VWAP but conditions NOT met, e.g., volume) — allows retry
BELOW_VWAP → EXHAUSTED (pullback depth > max_pullback_pct)
ENTERED / EXHAUSTED → terminal (no more entries for this symbol today)
```

### Key Design Decisions

1. **State enum:** Use StrEnum for serialization/logging readability
2. **VwapSymbolState dataclass:** tracks state, pullback_low, bars_below_vwap, recent_volumes, position_active
3. **Time handling:** Candle timestamps are UTC (DEC-049). Convert to ET: `candle.timestamp.astimezone(ET).time()`
4. **Volume averaging:** Use all bars seen so far for the symbol (state.recent_volumes). Average = sum/len.
5. **Minimum risk floor in position sizing:** `effective_risk = max(risk_per_share, entry_price * 0.003)` to prevent enormous positions on shallow pullbacks where the stop is very close to entry.

### Entry Conditions (all must be true)

1. Symbol in watchlist
2. State is BELOW_VWAP
3. Candle closes above VWAP (the reclaim)
4. Time >= earliest_entry (10:00) and < latest_entry (12:00)
5. check_internal_risk_limits() passes
6. Concurrent positions < max_concurrent_positions
7. Pullback depth >= min_pullback_pct (0.2%)
8. bars_below_vwap >= min_pullback_bars (3)
9. Reclaim candle volume >= avg_volume × volume_confirmation_multiplier (1.2×)
10. Chase protection: close < VWAP × (1 + max_chase_above_vwap_pct) (0.3%)
11. Position size > 0

### Signal Construction

```python
stop_price = pullback_low - (pullback_low * stop_buffer_pct)
risk_per_share = entry_price - stop_price
t1 = entry_price + risk_per_share * target_1_r
t2 = entry_price + risk_per_share * target_2_r

SignalEvent(
    strategy_id=self.strategy_id,
    symbol=symbol,
    side=Side.LONG,
    entry_price=candle.close,
    stop_price=stop_price,
    target_prices=(t1, t2),
    share_count=shares,
    rationale=f"VWAP Reclaim: {symbol} reclaimed VWAP {vwap:.2f} after pullback to {pullback_low:.2f}...",
    time_stop_seconds=self._vwap_config.time_stop_minutes * 60,
)
```

### Required Methods (BaseStrategy interface)

- `on_candle(event)` — state machine + entry logic
- `on_tick(event)` — no-op (position management via Order Manager)
- `get_scanner_criteria()` — same as ORB: min_gap_pct=0.02, min_price=10, max_price=200, min_volume=1M, rvol=2.0
- `calculate_position_size(entry, stop)` — universal formula with minimum risk floor
- `get_exit_rules()` — T1=target_1_r (50%), T2=target_2_r (50%), time_stop, fixed stop
- `get_market_conditions_filter()` — bullish_trending, range_bound, high_volatility; max_vix=35
- `reset_daily_state()` — clear _symbol_state dict + super()
- `mark_position_closed(symbol)` — set state.position_active = False
- `set_data_service(data_service)` — store reference (same pattern as OrbBase)
- `reconstruct_state(trade_logger)` — call super() (base class handles trade count/P&L)

### Reference Files
- `argus/strategies/base_strategy.py` — interface to implement
- `argus/strategies/orb_scalp.py` — recent strategy implementation pattern (but don't inherit from OrbBase)
- `argus/strategies/orb_base.py` — time handling patterns (_get_candle_time, ET timezone)
- `argus/data/indicator_engine.py` — VWAP is computed here, available via DataService
- `argus/core/events.py` — SignalEvent, CandleEvent, TickEvent, Side

## Verification
- All 1317 existing tests pass
- Strategy class imports cleanly: `python -c "from argus.strategies.vwap_reclaim import VwapReclaimStrategy; print('OK')"`
- No new tests in this session (Session 3 handles tests)

Commit message: `feat: add VwapReclaimStrategy core implementation (Sprint 19, Session 2)`
```

---

### Session 3: Strategy Unit Tests

```
# Sprint 19, Session 3: VWAP Reclaim Unit Tests

Read CLAUDE.md first. Sessions 1-2 complete — VwapReclaimConfig and VwapReclaimStrategy exist.

## Context
Create comprehensive unit tests for VwapReclaimStrategy. Target: ~50-60 new tests. Follow the patterns in tests/strategies/test_orb_scalp.py for mock setup.

## Task: Create tests/strategies/test_vwap_reclaim.py

### Mock Setup Pattern

```python
# Use FixedClock for time control
from argus.core.clock import FixedClock

# Mock DataService for controlled VWAP values
class MockDataService:
    async def get_indicator(self, symbol, indicator):
        if indicator == "vwap":
            return self._vwap_values.get(symbol)
        return None
    # ... other required methods

# Helper to create CandleEvents at specific times with specific OHLCV
def make_candle(symbol, timestamp, open_, high, low, close, volume):
    return CandleEvent(symbol=symbol, timestamp=timestamp, ...)
```

### Test Categories

**1. State Machine Transitions (~12 tests)**
- test_initial_state_is_watching
- test_watching_to_above_vwap_on_close_above
- test_watching_stays_watching_on_close_below (never been above)
- test_above_vwap_to_below_vwap_on_close_below
- test_above_vwap_stays_above_on_close_above
- test_below_vwap_reclaim_triggers_entry (all conditions met)
- test_below_vwap_to_above_without_entry (e.g., volume not confirmed — allows retry)
- test_below_vwap_to_exhausted_on_deep_pullback
- test_exhausted_ignores_further_candles
- test_entered_ignores_further_candles
- test_multiple_pullback_attempts (above → below → above(no entry) → below → reclaim(entry))
- test_pullback_low_tracks_lowest_low_across_bars

**2. Entry Condition Rejections (~10 tests)**
- test_reject_pullback_too_shallow
- test_reject_pullback_too_few_bars
- test_reject_volume_not_confirmed
- test_reject_chase_protection_triggered
- test_reject_before_earliest_entry_time
- test_reject_after_latest_entry_time
- test_reject_max_trades_per_day_reached
- test_reject_max_concurrent_positions_reached
- test_reject_zero_allocated_capital
- test_reject_internal_risk_limits_hit

**3. Signal Construction (~6 tests)**
- test_signal_stop_at_pullback_low_minus_buffer
- test_signal_targets_at_correct_r_multiples
- test_signal_time_stop_seconds_matches_config
- test_signal_share_count_from_position_sizing
- test_signal_rationale_includes_key_values
- test_minimum_risk_floor_prevents_oversizing

**4. Edge Cases (~8 tests)**
- test_vwap_not_available_returns_none
- test_symbol_not_in_watchlist_ignored
- test_candle_exactly_at_vwap_treated_as_below (close == vwap → not above)
- test_zero_volume_candle_handled
- test_no_data_service_returns_none
- test_negative_allocated_capital_prevented
- test_single_bar_below_vwap_not_enough (min_pullback_bars=3)
- test_pullback_low_updates_on_each_bar_below

**5. Other Methods (~8 tests)**
- test_get_scanner_criteria_matches_orb
- test_get_exit_rules_has_two_targets
- test_get_exit_rules_time_stop
- test_get_market_conditions_filter_allows_correct_regimes
- test_get_market_conditions_filter_max_vix
- test_reset_daily_state_clears_symbol_states
- test_mark_position_closed_resets_flag
- test_calculate_position_size_standard_formula

**6. Volume Averaging (~4 tests)**
- test_volume_average_includes_all_bars
- test_volume_average_with_single_bar
- test_reclaim_volume_vs_average_threshold
- test_high_volume_reclaim_passes

### Important Notes
- All candle timestamps must be timezone-aware UTC
- Use ET times between 10:00-12:00 for entry tests, outside for rejection tests
- VwapReclaimConfig with known values for deterministic testing
- Mock DataService.get_indicator("vwap") to return controlled float values
- Set allocated_capital on the strategy before testing signals

## Verification
- All new tests pass
- All 1317 existing tests still pass
- Run: `python -m pytest tests/strategies/test_vwap_reclaim.py -v`

Commit message: `test: add VwapReclaimStrategy unit tests (Sprint 19, Session 3)`
```

---

### Session 4: System Integration

```
# Sprint 19, Session 4: System Integration

Read CLAUDE.md first. Sessions 1-3 complete — VwapReclaimStrategy exists with full unit test coverage.

## Context
Wire VwapReclaimStrategy into the ARGUS system: main.py startup, Orchestrator registration, health monitoring. This is a small, surgical session.

## Task 1: Update argus/main.py

### Add imports (top of file)
```python
from argus.core.config import load_vwap_reclaim_config
from argus.strategies.vwap_reclaim import VwapReclaimStrategy
```

### Add strategy creation in Phase 8 (after ORB Scalp creation)

Find the section where scalp_strategy is created and registered. Add after it:

```python
# VWAP Reclaim strategy
vwap_reclaim_strategy: VwapReclaimStrategy | None = None
vwap_yaml = self._config_dir / "strategies" / "vwap_reclaim.yaml"
if vwap_yaml.exists():
    vwap_config = load_vwap_reclaim_config(vwap_yaml)
    vwap_reclaim_strategy = VwapReclaimStrategy(
        config=vwap_config, data_service=data_service, clock=self._clock
    )
    vwap_reclaim_strategy.set_watchlist(symbols)
    strategies_created.append("VwapReclaim")
```

### Register with Orchestrator (in Phase 9, after scalp registration)
```python
if vwap_reclaim_strategy is not None:
    self._orchestrator.register_strategy(vwap_reclaim_strategy)
```

### Add health component (after scalp health update)
```python
if vwap_reclaim_strategy is not None:
    health_monitor.update_component(
        "strategy_vwap_reclaim", ComponentStatus.HEALTHY, "VWAP Reclaim running"
    )
```

### Update strategy reconstruction
Verify that `_reconstruct_strategy_state()` iterates over `self._orchestrator.get_strategies()` — if so, VWAP Reclaim is automatically included. No changes needed if the loop is generic.

## Task 2: Update argus/__init__.py
Ensure VwapReclaimStrategy is exported from the strategies module.

## Task 3: Verify CandleEvent routing
The existing `_route_candle_to_strategies()` should already iterate over all Orchestrator strategies. Verify by reading the code — no changes should be needed.

## Verification
- All existing tests pass (1317 + new strategy tests)
- New integration: `python -c "from argus.main import ArgusSystem; print('imports OK')"`
- Quick smoke test of main.py structure (no runtime test needed — integration tests in Session 5)

Commit message: `feat: wire VwapReclaimStrategy into main.py startup (Sprint 19, Session 4)`
```

---

### Session 5: Integration Tests

```
# Sprint 19, Session 5: Integration Tests

Read CLAUDE.md first. Sessions 1-4 complete — VwapReclaimStrategy is fully implemented, tested, and wired into the system.

## Context
Create multi-strategy integration tests exercising three concurrent strategies. Follow patterns from tests/test_integration_sprint18.py but focus on three-strategy scenarios and VWAP-specific flows.

## Task: Create tests/test_integration_sprint19.py

Target: ~15-18 new tests.

### Test Infrastructure
Reuse fixtures and patterns from test_integration_sprint18.py:
- MockBroker, MockDataService, MockScanner
- EventBus wiring
- Orchestrator with three registered strategies
- Risk Manager with cross-strategy config

### Test Scenarios

**Three-Strategy Allocation (2 tests)**
1. test_three_strategy_equal_allocation
   - Register ORB, Scalp, VWAP Reclaim with Orchestrator
   - Run pre-market allocation with 100K account
   - Verify: each gets ~26.7K (80K / 3), total = 80K, cash reserve = 20K
   - Verify: no strategy exceeds 40% cap

2. test_three_strategy_allocation_with_throttled_strategy
   - Throttle VWAP Reclaim
   - Verify: remaining capital split between ORB and Scalp

**Sequential Flow — ORB → VWAP Reclaim (2 tests)**
3. test_orb_then_vwap_reclaim_on_same_symbol
   - ORB enters AAPL breakout at 9:40 AM
   - ORB exits at time stop (9:55 AM)
   - Feed candles: AAPL above VWAP, then below VWAP (3+ bars), then reclaim at 10:20 AM
   - VWAP Reclaim enters AAPL
   - Verify: both trades have correct strategy_ids, correct signal construction

4. test_orb_scalp_then_vwap_reclaim_sequential
   - Scalp enters/exits quickly, then VWAP Reclaim enters later
   - Verify all three strategies can trade the same symbol sequentially

**Concurrent Positions (2 tests)**
5. test_three_strategies_concurrent_positions
   - ORB holding AAPL, Scalp holding TSLA, VWAP Reclaim holding NVDA
   - Verify: Risk Manager approves all three
   - Verify: cross-strategy position counts correct

6. test_same_symbol_allow_all_orb_and_vwap
   - ORB still holding AAPL when VWAP Reclaim triggers on AAPL
   - Verify: both allowed under ALLOW_ALL policy
   - Verify: max_single_stock_pct (5%) checked

**VWAP Reclaim State Machine in Integration Context (3 tests)**
7. test_vwap_reclaim_full_state_machine_cycle
   - Feed realistic candle sequence through full system (EventBus → Strategy → Risk → Order)
   - Candles: gap up → run above VWAP → pullback below → reclaim with volume
   - Verify: signal emitted, risk approved, order placed

8. test_vwap_reclaim_rejection_flows
   - Pullback too shallow → no signal
   - Volume not confirmed → state returns to ABOVE_VWAP (retry possible)
   - Pullback too deep → EXHAUSTED state

9. test_vwap_reclaim_multiple_pullback_attempts
   - First pullback: reclaim without volume → back to ABOVE_VWAP
   - Second pullback: all conditions met → entry

**Risk and Throttling (3 tests)**
10. test_throttle_isolation_vwap_vs_orb
    - VWAP Reclaim throttled by PerformanceThrottler
    - ORB continues trading normally
    - Verify independent throttling

11. test_allocation_exhaustion_three_strategies
    - All strategies at max concurrent positions
    - New signal from any strategy → rejected by Risk Manager

12. test_cross_strategy_stock_limit
    - ORB holds 4% in AAPL, VWAP Reclaim tries to add 2% in AAPL
    - Total would exceed 5% → Risk Manager rejects or modifies

**Regime and Daily Reset (3 tests)**
13. test_crisis_regime_suspends_vwap_reclaim
    - Orchestrator detects crisis regime
    - VWAP Reclaim suspended (max_vix exceeded)
    - ORB and Scalp may continue (different regime preferences)

14. test_three_strategy_daily_reset
    - All strategies have accumulated state
    - reset_daily_state() called on each
    - Verify: all symbol states cleared, counters reset

15. test_vwap_reclaim_outside_operating_window
    - Feed VWAP reclaim pattern at 9:30 AM (before 10:00 earliest entry)
    - Verify: no signal emitted despite pattern being valid

### Important Notes
- Use FixedClock to control time precisely
- Mock DataService must return VWAP values that create the desired state transitions
- Create candle sequences that are realistic: OHLCV should be internally consistent
- Use the cross-strategy risk infrastructure from Sprint 18 (it's already built)

## Verification
- All new integration tests pass
- All existing tests still pass (strategy unit tests + all prior integration tests)
- Run: `python -m pytest tests/test_integration_sprint19.py -v`

Commit message: `test: add three-strategy integration tests (Sprint 19, Session 5)`
```

---

### Session 6: VectorBT Sweep

```
# Sprint 19, Session 6: VectorBT VWAP Reclaim Parameter Sweep

Read CLAUDE.md first. Sessions 1-5 complete. Code review checkpoint 1 passed (or issues noted for Session 11).

## Context
Create VectorBT-style parameter sweep for VWAP Reclaim. This is a NEW file — no modifications to existing backtest files. Follows the pattern in argus/backtest/vectorbt_orb_scalp.py but with VWAP Reclaim's state machine logic.

Key difference from ORB sweeps: The state machine (above → below → reclaim) is inherently sequential per symbol-day, so we iterate per day rather than trying to fully vectorize. With 768 parameter combinations, this is computationally tractable.

## Task: Create argus/backtest/vectorbt_vwap_reclaim.py

### Data Flow
1. Load Parquet files from data_dir (same format as ORB sweeps)
2. For each symbol, for each day:
   a. Compute VWAP: cumulative(TP × vol) / cumulative(vol) where TP = (H+L+C)/3
   b. Apply gap filter (gap >= min_gap_pct from prev_close to day_open)
   c. Run state machine to find reclaim entries
   d. For each entry, simulate stop/target/time-stop exit
3. Aggregate results across all symbols and days per parameter combination
4. Output metrics: total_trades, win_rate, avg_r, profit_factor, sharpe, max_dd

### VWAP Computation (vectorized per day)
```python
def compute_day_vwap(day_df: pd.DataFrame) -> pd.Series:
    tp = (day_df["high"] + day_df["low"] + day_df["close"]) / 3
    cum_tp_vol = (tp * day_df["volume"]).cumsum()
    cum_vol = day_df["volume"].cumsum()
    return cum_tp_vol / cum_vol.replace(0, np.nan)
```

### State Machine Simulation (per symbol-day, iterative)
```python
def simulate_vwap_reclaim_day(
    day_df: pd.DataFrame,
    vwap: pd.Series,
    params: VwapReclaimParams,
) -> list[TradeResult]:
    state = "watching"
    pullback_low = None
    bars_below = 0
    volumes = []
    trades = []

    for idx, row in day_df.iterrows():
        bar_time = row["timestamp"].time()  # Already in ET from Parquet
        volumes.append(row["volume"])

        if state == "watching":
            if row["close"] > vwap[idx]:
                state = "above_vwap"

        elif state == "above_vwap":
            if row["close"] < vwap[idx]:
                state = "below_vwap"
                pullback_low = row["low"]
                bars_below = 1

        elif state == "below_vwap":
            if row["close"] < vwap[idx]:
                bars_below += 1
                pullback_low = min(pullback_low, row["low"])
                # Check exhaustion
                depth = (vwap[idx] - pullback_low) / vwap[idx]
                if depth > params.max_pullback_pct:
                    state = "exhausted"
            elif row["close"] > vwap[idx]:
                # Potential reclaim — check all conditions
                # (time, depth, bars, volume, chase)
                if all_conditions_met(...):
                    trade = simulate_trade(row, pullback_low, params, day_df, idx)
                    trades.append(trade)
                    state = "entered"
                else:
                    state = "above_vwap"  # Retry

    return trades
```

### Parameter Grid
```python
@dataclass
class VwapReclaimSweepConfig:
    data_dir: Path
    symbols: list[str]
    start_date: date
    end_date: date
    output_dir: Path

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

    # Fixed
    max_pullback_pct: float = 0.02
    max_chase_above_vwap_pct: float = 0.003
    stop_buffer_pct: float = 0.001
    min_gap_pct: float = 0.02
    min_price: float = 5.0
    max_price: float = 10000.0
```

Total: 4 × 4 × 4 × 3 × 4 = 768 combinations

### Trade Simulation
For each entry, simulate exit:
- Stop: entry_price - risk (pullback_low - buffer)
- Target: entry_price + risk × target_r
- Time stop: close at bar N after entry (N = time_stop_bars)
- EOD flatten: close at 15:45 bar if still open
- Walk forward through subsequent bars checking stop/target/time

### CLI
```python
if __name__ == "__main__":
    # argparse: --data-dir, --start, --end, --output-dir, --symbols (optional)
```

### Output
- CSV with per-combo aggregate metrics
- Heatmaps (matplotlib) for key parameter pairs
- Summary statistics to stdout

### Tests
Add a few unit tests for the VWAP computation and state machine simulation in the same file or a separate test file. At minimum:
- test_compute_day_vwap_correctness
- test_state_machine_basic_reclaim
- test_gap_filter

## Reference
- argus/backtest/vectorbt_orb_scalp.py — follow this file's structure closely
- argus/backtest/vectorbt_orb.py — more complex version with more parameters

## Verification
- All existing tests pass
- Sweep runs on a small test: `python -m argus.backtest.vectorbt_vwap_reclaim --data-dir data/historical/1m --start 2025-01-01 --end 2025-01-31 --output-dir /tmp/vwap_test`

Commit message: `feat: add VectorBT VWAP Reclaim parameter sweep (Sprint 19, Session 6)`
```

---

### Session 7: Walk-Forward Integration

```
# Sprint 19, Session 7: Walk-Forward Pipeline Integration

Read CLAUDE.md first. Session 6 complete — vectorbt_vwap_reclaim.py exists.

## Context
Extend the walk-forward validation pipeline to support --strategy vwap_reclaim. This requires surgical changes to three existing files. Be precise — these files are large and complex.

## Task 1: Extend argus/backtest/walk_forward.py

### 1a. Add imports (top of file)
```python
from argus.backtest.vectorbt_vwap_reclaim import VwapReclaimSweepConfig
from argus.backtest.vectorbt_vwap_reclaim import run_sweep as run_vwap_reclaim_sweep
```

### 1b. Add VWAP Reclaim parameter fields to WalkForwardConfig
After the ORB Scalp fields, add:
```python
# VWAP Reclaim parameter grid (used when strategy="vwap_reclaim")
vwap_min_pullback_pct_list: list[float] = field(
    default_factory=lambda: [0.001, 0.002, 0.003, 0.005]
)
vwap_min_pullback_bars_list: list[int] = field(
    default_factory=lambda: [2, 3, 5, 8]
)
vwap_volume_multiplier_list: list[float] = field(
    default_factory=lambda: [1.0, 1.2, 1.5, 2.0]
)
vwap_target_r_list: list[float] = field(
    default_factory=lambda: [0.5, 1.0, 1.5]
)
vwap_time_stop_bars_list: list[int] = field(
    default_factory=lambda: [10, 15, 20, 30]
)
```

### 1c. Add dispatch in _run_in_sample_optimization()
Find the existing if/elif chain for strategy dispatch. Add:
```python
elif config.strategy == "vwap_reclaim":
    sweep_config = VwapReclaimSweepConfig(
        data_dir=config.data_dir,
        symbols=config.symbols,
        start_date=window_start,
        end_date=window_end,
        output_dir=config.output_dir / f"window_{window_idx}_is",
        min_pullback_pct_list=config.vwap_min_pullback_pct_list,
        min_pullback_bars_list=config.vwap_min_pullback_bars_list,
        volume_multiplier_list=config.vwap_volume_multiplier_list,
        target_r_list=config.vwap_target_r_list,
        time_stop_bars_list=config.vwap_time_stop_bars_list,
    )
    results = run_vwap_reclaim_sweep(sweep_config)
    # Extract best params by Sharpe with min_trades floor
    # Return best_params dict
```

### 1d. Add dispatch in _run_out_of_sample_validation()
```python
elif config.strategy == "vwap_reclaim":
    # Map best params to BacktestConfig for Replay Harness
    backtest_config_overrides = {
        "vwap_reclaim.min_pullback_pct": float(best_params["min_pullback_pct"]),
        "vwap_reclaim.min_pullback_bars": int(best_params["min_pullback_bars"]),
        "vwap_reclaim.volume_confirmation_multiplier": float(best_params["volume_multiplier"]),
        "vwap_reclaim.target_1_r": float(best_params["target_r"]),
        "vwap_reclaim.time_stop_minutes": int(best_params["time_stop_bars"]),
    }
    # Create BacktestConfig with strategy_type=StrategyType.VWAP_RECLAIM
    # Run Replay Harness
```

### 1e. Update CLI
Add "vwap_reclaim" to the --strategy choices list.

## Task 2: Extend argus/backtest/replay_harness.py

In the _create_strategy() method, add VWAP Reclaim case:
```python
elif self._config.strategy_type == StrategyType.VWAP_RECLAIM:
    from argus.core.config import VwapReclaimConfig
    from argus.strategies.vwap_reclaim import VwapReclaimStrategy

    config = VwapReclaimConfig(
        strategy_id=self._config.strategy_id or "strat_vwap_reclaim",
        name="VWAP Reclaim",
        min_pullback_pct=self._config.vwap_min_pullback_pct or 0.002,
        min_pullback_bars=self._config.vwap_min_pullback_bars or 3,
        volume_confirmation_multiplier=self._config.vwap_volume_multiplier or 1.2,
        target_1_r=self._config.vwap_target_1_r or 1.0,
        target_2_r=self._config.vwap_target_2_r or 2.0,
        time_stop_minutes=self._config.vwap_time_stop_minutes or 30,
        stop_buffer_pct=self._config.vwap_stop_buffer_pct or 0.001,
        max_pullback_pct=self._config.vwap_max_pullback_pct or 0.02,
        max_chase_above_vwap_pct=self._config.vwap_max_chase_pct or 0.003,
        operating_window=OperatingWindow(earliest_entry="10:00", latest_entry="12:00"),
        risk_limits=StrategyRiskLimits(max_loss_per_trade_pct=0.01, max_trades_per_day=8, max_concurrent_positions=3),
    )
    return VwapReclaimStrategy(config=config, data_service=self._data_service, clock=self._clock)
```

## Task 3: Extend argus/backtest/config.py

Add VWAP Reclaim parameter fields to BacktestConfig for the Replay Harness:
```python
# VWAP Reclaim params (used when strategy_type=VWAP_RECLAIM)
vwap_min_pullback_pct: float | None = None
vwap_min_pullback_bars: int | None = None
vwap_volume_multiplier: float | None = None
vwap_target_1_r: float | None = None
vwap_target_2_r: float | None = None
vwap_time_stop_minutes: int | None = None
vwap_stop_buffer_pct: float | None = None
vwap_max_pullback_pct: float | None = None
vwap_max_chase_pct: float | None = None
```

## Verification
- All existing tests pass
- Walk-forward CLI accepts: `python -m argus.backtest.walk_forward --strategy vwap_reclaim --help`
- Replay Harness creates VwapReclaimStrategy without error

Commit message: `feat: extend walk-forward + replay harness for VWAP Reclaim (Sprint 19, Session 7)`
```

---

### Session 8: Run Backtests

```
# Sprint 19, Session 8: Run Backtests

This is an EXECUTION session — no code changes. Run the VectorBT sweep and walk-forward analysis on the 35-month dataset.

## Step 1: VectorBT Sweep
```bash
python -m argus.backtest.vectorbt_vwap_reclaim \
    --data-dir data/historical/1m \
    --start 2023-03-01 --end 2026-01-31 \
    --output-dir data/backtest_runs/vwap_reclaim_sweeps
```

Record:
- Runtime
- Total trades across all parameter combos
- Best parameter combo by Sharpe (with min 20 trades)
- Top 5 combos
- Any red flags (all negative Sharpes? Very few trades?)

## Step 2: Walk-Forward Analysis
```bash
python -m argus.backtest.walk_forward \
    --strategy vwap_reclaim \
    --data-dir data/historical/1m \
    --start 2023-03-01 --end 2026-01-31 \
    --output-dir data/backtest_runs/vwap_reclaim_wf \
    --windows 15 --is-ratio 0.7
```

Record:
- WFE (Walk-Forward Efficiency)
- OOS Sharpe
- OOS total P&L
- Number of OOS trades
- Best parameters from each window

## Step 3: Analysis

If sweep shows all negative Sharpes: Note this as a data limitation issue (like ORB Scalp, DEC-127). Record the finding. Strategy parameters will be thesis-driven.

If sweep shows positive results: Record best params and whether they're stable across windows. This is the most meaningful backtest data we'll get pre-Databento.

Either way: Record results for the strategy spec sheet and decision log.

Note: Results are provisional — re-validation with Databento data required (DEC-132).

No commit for this session — results are recorded in docs/strategies/STRATEGY_VWAP_RECLAIM.md (Session 11).
```

---

### Session 9: Dev Mock Data

```
# Sprint 19, Session 9: Dev Mode Mock Data

Read CLAUDE.md first. Sessions 1-8 complete.

## Context
Update dev mode to include VWAP Reclaim as a third strategy everywhere. Follow the patterns established in Sprint 18.5 (which added ORB Scalp mock data).

## Task: Update argus/api/dev_state.py

### 1. Add VWAP Reclaim mock positions

Add 2-3 VWAP Reclaim positions (mid-morning entries):
- Open position: entered NVDA at 10:22 AM, stop at pullback low, T1 at +1R, T2 at +2R
- Recently closed: MSFT entered 10:45 AM, exited T1 at 10:58 AM (+1.0R win)

Key differences from ORB positions:
- Entry times between 10:00-12:00 (not 9:35-10:00)
- strategy_id = "vwap_reclaim" (not "orb_breakout" or "orb_scalp")
- Hold durations 5-30 minutes
- Entry rationale mentions VWAP reclaim, pullback, etc.

### 2. Add VWAP Reclaim mock trades

Add 4-5 historical trades with mix of exits:
- TARGET_1 win (most common expected outcome)
- TARGET_2 win (runner hit)
- STOP_LOSS (pullback resumed after entry)
- TIME_STOP (trade didn't reach target in 30 min)

### 3. Update strategy allocation

Change from 2-strategy to 3-strategy split:
```python
"vwap_reclaim": StrategyAllocation(
    strategy_id="vwap_reclaim",
    name="VWAP Reclaim",
    allocated_pct=0.267,  # (1 - 0.20) / 3
    allocated_amount=26700.0,
    is_active=True,
),
```

Update existing ORB and Scalp allocations to 26.7% each (from ~40% and ~40%).

### 4. Add strategy to system health
```python
health_monitor.update_component(
    "strategy_vwap_reclaim", ComponentStatus.HEALTHY, "VWAP Reclaim active — 2 trades today"
)
```

### 5. Add VWAP Reclaim to strategy cards
In the strategy status section, add a VWAP Reclaim card with:
- strategy_id, name, version
- allocated capital, daily P&L, trade count
- Pipeline stage: "Exploration"

### 6. Update SessionSummaryCard data
Include VWAP Reclaim trades in the after-hours summary.

### 7. Update performance breakdown
Three strategies in the daily performance metrics.

## Verification
- All tests pass (dev_state.py changes don't break anything)
- Dev mode runs: `python -m argus.api --dev`
- Dashboard shows three strategies in donut chart
- System page shows VWAP Reclaim strategy card
- Trade log shows VWAP Reclaim trades
- Performance page shows three-strategy breakdown

Commit message: `feat: add VWAP Reclaim mock data to dev mode (Sprint 19, Session 9)`
```

---

### Session 10: Watchlist Sidebar

```
# Sprint 19, Session 10: Watchlist Sidebar (UX Feature 18-C)

Read CLAUDE.md first. Session 9 complete — dev mode shows three strategies.

## Context
Add a watchlist sidebar to the Dashboard page showing scanner candidates with strategy badges. This is UX Feature 18-C from docs/ui/UX_FEATURE_BACKLOG.md.

## Design

### Layout
- Desktop (≥1024px): 280px right sidebar on Dashboard, collapsible via toggle button
- Tablet (640-1023px): Slide-out panel from right edge, triggered by button
- Mobile (<640px): Full-screen overlay, triggered by toolbar button

### Content per watchlist item
- Symbol + current price (from WebSocket or mock)
- Gap % badge (color-coded: green > 5%, amber 2-5%)
- Mini sparkline (SVG, 60×20px, intraday price path)
- Strategy badges: small colored pills showing which strategies are watching
  - ORB = blue pill, "ORB"
  - Scalp = purple pill, "SCP"
  - VWAP = teal pill, "VWP"
- For VWAP Reclaim symbols: state indicator dot
  - Gray = WATCHING
  - Blue = ABOVE_VWAP
  - Amber = BELOW_VWAP
  - Green = ENTERED
  - Red = EXHAUSTED

### New API endpoint
```
GET /api/watchlist
Response: [{
    symbol: string,
    price: number,
    gap_pct: number,
    change_pct: number,
    strategies: string[],  // ["orb_breakout", "orb_scalp", "vwap_reclaim"]
    vwap_state: string | null,  // "watching" | "above_vwap" | "below_vwap" | "entered" | "exhausted"
    sparkline_data: number[]  // Last 30 close prices
}]
```

### API implementation (argus/api/)
Add watchlist route. In dev mode, return mock watchlist data (8-10 symbols). In live mode, query the Orchestrator for registered strategy watchlists and VWAP Reclaim symbol states.

### Frontend components
- `WatchlistSidebar.tsx` — main container with collapse/expand
- `WatchlistItem.tsx` — individual symbol row
- `StrategyBadge.tsx` — small colored pill (reuse/extend existing Badge component)
- `VwapStateDot.tsx` — colored status indicator
- `MiniSparkline.tsx` — tiny SVG sparkline (reuse pattern from dashboard sparklines)

### Integration
- Add to Dashboard page layout (adjust grid to accommodate sidebar)
- Add toggle button to the dashboard header area
- Collapse state persisted in Zustand store (session-level, like DEC-129)

### Animation
- Sidebar slide-in: Framer Motion, 200ms ease-out
- Follow Sprint 17.5 principle: always render same DOM structure, don't swap skeleton/content conditionally

### Vitest tests
Add 3-4 tests for WatchlistItem rendering, strategy badge display, and VWAP state dot colors.

## Reference
- docs/ui/UX_FEATURE_BACKLOG.md — 18-C spec
- argus/ui/src/components/ — existing component patterns
- argus/ui/src/components/PositionTimeline.tsx — sparkline SVG pattern from Sprint 18

## Verification
- All pytest tests pass (unchanged)
- Vitest tests pass (new + existing)
- Dev mode dashboard shows watchlist sidebar
- Sidebar collapses/expands smoothly
- Responsive at all three breakpoints
- VWAP state dots show correct colors for different states

Commit message: `feat: add Watchlist Sidebar with strategy badges (Sprint 19, Session 10)`
```

---

### Session 11: Strategy Spec + Polish

```
# Sprint 19, Session 11: Strategy Spec + Polish

Read CLAUDE.md first. Sessions 1-10 complete. Code review checkpoint 2 feedback incorporated.

## Task 1: Create docs/strategies/STRATEGY_VWAP_RECLAIM.md
Use the strategy template (docs/04_STRATEGY_TEMPLATE.md). Fill in all fields with actual values from implementation. Include backtest results from Session 8 in the appropriate tables.

A draft is available — Steven will provide it. Update with actual implementation details and backtest numbers.

## Task 2: Address Code Review Feedback
Fix any issues identified in code review checkpoints 1 and 2. Common items:
- Missing edge case tests
- Docstring improvements
- Config validation gaps
- Lint issues

## Task 3: Final Verification Checklist
- [ ] ruff check passes (zero warnings)
- [ ] ruff format passes (zero changes)
- [ ] All pytest tests pass (target: ~1460+)
- [ ] All Vitest tests pass (target: ~10+)
- [ ] Dev mode shows three strategies on all pages
- [ ] Watchlist sidebar functional
- [ ] VectorBT sweep results recorded in strategy spec
- [ ] Walk-forward results recorded in strategy spec
- [ ] No regressions in ORB or ORB Scalp tests

Commit message: `docs: add VWAP Reclaim strategy spec + polish (Sprint 19, Session 11)`
```

---

### Session 12: Docs Update

```
# Sprint 19, Session 12: Documentation Updates

Read CLAUDE.md first. Sprint 19 implementation complete. This session updates all project documentation.

## Documents to Update

### 1. CLAUDE.md
- Update "Current State" section: Sprint 19 complete, test count
- Add VwapReclaimStrategy to architectural notes
- Update strategy list

### 2. docs/05_DECISION_LOG.md
Check current highest DEC number first! Add new entries for Sprint 19 decisions. Steven will provide the exact entries from the code review session.

### 3. docs/02_PROJECT_KNOWLEDGE.md
- Add Sprint 19 to "Completed Work" under Build Track
- Update Build Track queue (Sprint 20 is NEXT)
- Add any new decisions to "Key Decisions Made" section
- Update test count

### 4. docs/10_PHASE3_SPRINT_PLAN.md
- Move Sprint 19 to completed table with test count, date, outcomes
- Update "Next sprint" pointer to Sprint 20

### 5. docs/03_ARCHITECTURE.md
- Add VwapReclaimStrategy to Section 3.4 (Strategy Architecture)
- Add watchlist API endpoint to Section 3.7 (API)
- Note the standalone-from-BaseStrategy pattern (vs OrbBase)

### 6. docs/01_PROJECT_BIBLE.md
- Update Strategy 3 (VWAP Reclaim) description with actual parameters
- Add pipeline stage update

## Verification
- All docs are internally consistent
- DEC numbers are sequential with no gaps or duplicates
- Test counts match actual

Commit message: `docs: update all project docs for Sprint 19 completion`
```

---
