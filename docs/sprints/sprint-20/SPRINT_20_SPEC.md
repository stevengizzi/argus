# Sprint 20 — Afternoon Momentum Strategy: Implementation Spec

> Sprint 20 design document. Paste into Claude Code for the first implementation session.
> Designed by Steven + Claude (claude.ai). February 26, 2026.

---

## Overview

Sprint 20 adds the fourth and final V1 strategy: **Afternoon Momentum** — a consolidation breakout strategy operating 2:00–3:30 PM ET. After this sprint, ARGUS covers the full trading day with four uncorrelated signal types across four distinct time windows.

**Starting state:** 1410 pytest + 40 Vitest tests. Sprints 1–19 complete.

**Target state:** ~1560+ pytest + ~47+ Vitest tests. Four strategies registered, full-day coverage, VectorBT sweep + walk-forward validation, dev mode mock data, strategy spec sheet.

---

## Pre-Sprint Housekeeping

### Fix Plotly Test Environment Failures (11 tests)

In `tests/backtest/test_vectorbt_orb_scalp.py`, tests that call `generate_heatmap()` fail because `plotly` is not installed in the test environment. Fix with `pytest.importorskip("plotly")` at the top of any test function that calls `generate_heatmap()`.

Pattern:
```python
def test_generate_heatmap_creates_html(tmp_path):
    """Run sweep → call generate_heatmap → HTML file exists."""
    pytest.importorskip("plotly")
    # ... rest of test
```

Apply to all tests in the file that invoke plotly-dependent functions.

---

## Design Decisions

### DEC-152: Afternoon Momentum — Standalone from BaseStrategy

**Decision:** `AfternoonMomentumStrategy` inherits directly from `BaseStrategy`, not from `OrbBaseStrategy` or any shared base.

**Rationale:** Despite structural similarity (range → breakout), the range formation is fundamentally different. ORB uses a predefined time window (first N minutes). Afternoon Momentum detects an organically-formed consolidation during midday. The consolidation detection logic, the two-phase tracking (accumulation then breakout watching), and the EOD proximity handling are all unique. If a "Midday Range Breakout" variant is later needed, a shared base can be extracted then (following DEF-022 precedent). This matches the VWAP Reclaim precedent (DEC-136).

### DEC-153: Consolidation Detection — High/Low Channel + ATR Filter

**Decision:** Consolidation is identified by tracking the high/low of midday bars (12:00–2:00 PM), then checking if the range is tight relative to ATR-14.

**Algorithm:**
1. Starting at 12:00 PM ET, accumulate the high and low of each 1-minute bar
2. `midday_range = midday_high - midday_low`
3. `consolidation_ratio = midday_range / ATR-14` (from IndicatorEngine)
4. Consolidation is confirmed when `consolidation_ratio < consolidation_atr_ratio` threshold (default: 0.75)
5. Additionally require `min_consolidation_bars` (default: 30) bars tracked before confirming

**Rationale:** Simple, testable, vectorizable. The ATR filter confirms the range is genuinely tight (not just a low-volatility stock that always has narrow ranges). The min_consolidation_bars prevents false positives from early readings. Bollinger Bands (option B) require adding new indicator computation. Moving average convergence (option D) is too indirect. This is option C + A from the design questions.

### DEC-154: Scanner Reuse — Gap Watchlist

**Decision:** Afternoon Momentum reuses the same gap scanner as ORB and VWAP Reclaim. Same `ScannerCriteria` (min_gap=2%, min_price=$10, max_price=$200, min_volume=1M, min_rvol=2.0).

**Rationale:** The gap watchlist already identifies institutional-quality stocks with catalysts. These are the stocks most likely to consolidate midday and break out in the afternoon. Consolidation detection itself serves as the second filter — not all gap stocks consolidate. This is the simplest approach and matches the scanner reuse pattern from VWAP Reclaim (DEC-137).

### DEC-155: Afternoon Momentum State Machine (5 States)

**States:**
- `WATCHING` — Before 12:00 PM. Ignoring candles (waiting for midday period).
- `ACCUMULATING` — 12:00 PM onward. Tracking midday high/low. Not yet ready for breakout.
- `CONSOLIDATED` — Consolidation confirmed (range/ATR < threshold, enough bars). Watching for breakout after 2:00 PM.
- `ENTERED` — Position taken. Terminal state for this symbol today.
- `REJECTED` — Midday range too wide (range/ATR exceeds `max_consolidation_atr_ratio`). Terminal.

**Transitions:**
```
WATCHING ──[12:00 PM bar arrives]──→ ACCUMULATING
ACCUMULATING ──[range/ATR < threshold & bars >= min]──→ CONSOLIDATED
ACCUMULATING ──[range/ATR > max_threshold]──→ REJECTED
CONSOLIDATED ──[close > consolidation_high & volume OK & time 2:00–3:30]──→ ENTERED
```

**Key details:**
- Transition from WATCHING to ACCUMULATING happens on the first candle at or after 12:00 PM
- ACCUMULATING continuously updates midday_high/midday_low and checks consolidation criteria on each bar
- Once CONSOLIDATED, the strategy watches for breakout but continues updating the consolidation range (the range can tighten further, which is good)
- A bar that breaches consolidation_high but fails volume confirmation resets expectation (stays CONSOLIDATED, waits for next breakout attempt)
- If the range widens beyond `max_consolidation_atr_ratio` while still in ACCUMULATING, transition to REJECTED

### DEC-156: Breakout Entry Conditions

ALL must be TRUE simultaneously:

1. **State is CONSOLIDATED** — midday range confirmed as tight
2. **Time window:** 2:00 PM ≤ candle time < 3:30 PM ET
3. **Candle CLOSE > consolidation_high** — close-based confirmation (not intra-bar)
4. **Volume confirmation:** candle volume ≥ `volume_multiplier` × average bar volume (accumulated across the day)
5. **Chase protection:** close ≤ consolidation_high × (1 + `max_chase_pct`) — not too far above the range
6. **Risk > 0:** entry_price - stop_price > 0
7. **Internal risk limits pass** (max trades, daily loss, concurrent positions)
8. **Position count limit** not exceeded

### DEC-157: Stop and Target Design

- **Stop:** Below consolidation range low, with buffer: `stop = consolidation_low × (1 - stop_buffer_pct)`
- **T1:** `entry + risk × target_1_r` (default 1.0R, exit 50%)
- **T2:** `entry + risk × target_2_r` (default 2.0R, exit remaining 50%)
- **Time stop:** `min(max_hold_minutes, minutes_until_force_close)` — dynamic calculation accounting for EOD proximity
- **`time_stop_seconds` on SignalEvent:** Calculated at signal creation time based on current time and force_close time

**Rationale:** Same proven T1/T2 pattern as ORB and VWAP Reclaim. Trailing stops deferred to V2 (see DEC-158).

### DEC-158: Trailing Stop — Deferred to V2

**Decision:** No trailing stop in V1 of Afternoon Momentum.

**Rationale:** A trailing stop mechanism would touch Order Manager, Risk Manager, backtesting, and the VectorBT sweep architecture. The T1/T2 fixed target pattern is proven across three strategies and well-tested. If walk-forward validation shows afternoon moves routinely exceed T2, adding a trailing stop becomes a future sprint item. Premature complexity.

### DEC-159: EOD Handling

- **Last entry:** 3:30 PM ET (`latest_entry` in config)
- **Force close:** 3:45 PM ET (`force_close` in config)
- **Time stop calculation at entry:** `effective_seconds = min(max_hold_minutes × 60, seconds_until_3:45_PM)`
- **Edge case — late entry (e.g., 3:25 PM):** Time stop = 20 minutes (3:45 - 3:25), not the configured 60 minutes. The `time_stop_seconds` on SignalEvent reflects this dynamic calculation.
- **Integration with Order Manager:** Order Manager's existing EOD flatten logic handles the 3:45 PM hard cutoff. The strategy's time_stop_seconds calculation ensures positions are targeted for closure before the hard cutoff. If time stop and EOD flatten both trigger, the earliest one wins (already handled by Order Manager priority logic).

### DEC-160: Cross-Strategy Interaction

Same ALLOW_ALL duplicate stock policy (DEC-121). Time windows are well-separated:
- ORB: 9:35–10:00 AM (positions closed by ~10:15 AM)
- ORB Scalp: 9:45–10:00 AM (positions closed by ~10:02 AM)
- VWAP Reclaim: 10:00 AM–12:00 PM (positions closed by ~12:30 PM)
- Afternoon Momentum: 2:00–3:30 PM (positions closed by 3:45 PM)

By 2:00 PM when Afternoon Momentum activates, all other strategies' positions are closed. Cross-strategy collisions are effectively impossible. The 5% max_single_stock_pct cap still applies as a safety net.

### DEC-161: Databento Activation — Defer to Sprint 21

**Decision:** Databento subscription not activated for Sprint 20. Defer to Sprint 21 (analytics sprint) where quality data matters more for conviction-building.

**Rationale:** Another month of $199 saved. Sprint 20 uses the same Alpaca Parquet historical data as all other strategies. All backtest results remain provisional per DEC-132. Databento activation is most valuable when all four strategies are built AND the analytics toolkit (Sprint 21) is ready for serious validation.

---

## Architecture: AfternoonMomentumStrategy

### File: `argus/strategies/afternoon_momentum.py`

```
AfternoonMomentumStrategy(BaseStrategy)
├── __init__(config, data_service, clock)
├── State management
│   ├── _symbol_state: dict[str, AfternoonSymbolState]
│   ├── _get_symbol_state(symbol) → AfternoonSymbolState
│   ├── reset_daily_state()
│   └── mark_position_closed(symbol)
├── Core interface
│   ├── on_candle(event) → SignalEvent | None
│   ├── on_tick(event) → None (no-op, uses candles)
│   ├── get_scanner_criteria() → ScannerCriteria
│   ├── calculate_position_size(entry, stop) → int
│   ├── get_exit_rules() → ExitRules
│   └── get_market_conditions_filter() → MarketConditionsFilter
├── State machine
│   ├── _process_state_machine(symbol, candle, state) → SignalEvent | None
│   ├── _process_watching(symbol, candle, state) → None
│   ├── _process_accumulating(symbol, candle, state) → None
│   ├── _process_consolidated(symbol, candle, state) → SignalEvent | None
│   └── _check_breakout_entry(symbol, candle, state) → SignalEvent | None
├── Signal building
│   ├── _build_signal(symbol, candle, state) → SignalEvent | None
│   └── _compute_effective_time_stop(candle) → int (seconds)
└── Data service
    └── set_data_service(data_service)
```

### State Dataclass

```python
@dataclass
class AfternoonSymbolState:
    state: AfternoonState = AfternoonState.WATCHING
    # Consolidation tracking
    midday_high: float | None = None
    midday_low: float | None = None
    consolidation_bars: int = 0
    consolidation_confirmed: bool = False
    # Volume tracking
    recent_volumes: list[int] = field(default_factory=list)
    # Position tracking
    position_active: bool = False
```

### Config: `AfternoonMomentumConfig(StrategyConfig)`

```python
class AfternoonMomentumConfig(StrategyConfig):
    # Consolidation parameters
    consolidation_start_time: str = "12:00"  # When to start tracking midday range
    consolidation_atr_ratio: float = 0.75    # Max midday_range/ATR for consolidation
    max_consolidation_atr_ratio: float = 2.0 # If exceeded, reject (not consolidating)
    min_consolidation_bars: int = 30         # Min bars tracked before confirming

    # Breakout confirmation
    volume_multiplier: float = 1.2           # Breakout bar volume vs avg
    max_chase_pct: float = 0.005             # Max distance above consolidation high

    # Targets and stops
    target_1_r: float = 1.0
    target_2_r: float = 2.0
    max_hold_minutes: int = 60
    stop_buffer_pct: float = 0.001

    # Force close (EOD safety)
    force_close_time: str = "15:45"          # 3:45 PM ET hard cutoff
```

### YAML Config: `config/strategies/afternoon_momentum.yaml`

```yaml
strategy_id: "strat_afternoon_momentum"
name: "Afternoon Momentum"
version: "1.0.0"
enabled: true
asset_class: "us_stocks"

operating_window:
  earliest_entry: "14:00"
  latest_entry: "15:30"
  force_close: "15:45"

consolidation_start_time: "12:00"
consolidation_atr_ratio: 0.75
max_consolidation_atr_ratio: 2.0
min_consolidation_bars: 30
volume_multiplier: 1.2
max_chase_pct: 0.005
target_1_r: 1.0
target_2_r: 2.0
max_hold_minutes: 60
stop_buffer_pct: 0.001
force_close_time: "15:45"

risk_limits:
  max_loss_per_trade_pct: 0.01
  max_daily_loss_pct: 0.03
  max_trades_per_day: 6
  max_concurrent_positions: 3

benchmarks:
  min_win_rate: 0.45
  min_profit_factor: 1.1
  min_sharpe: 0.3
  max_drawdown_pct: 0.12
```

---

## Pillar 1: Strategy Implementation

### Session 1: Config + Strategy Scaffold + State Machine

**Files to create/modify:**
- `argus/core/config.py` — Add `AfternoonMomentumConfig`, `load_afternoon_momentum_config()`
- `argus/backtest/config.py` — Add `AFTERNOON_MOMENTUM` to `StrategyType` enum
- `argus/strategies/afternoon_momentum.py` — Full strategy class
- `config/strategies/afternoon_momentum.yaml` — Default config
- `tests/strategies/test_afternoon_momentum.py` — Comprehensive unit tests

**Config additions to `argus/core/config.py`:**

```python
class AfternoonMomentumConfig(StrategyConfig):
    """Afternoon Momentum strategy configuration (DEC-152).

    Consolidation breakout strategy that identifies stocks consolidating
    during midday (12:00–2:00 PM) and entering on breakouts after 2:00 PM.
    """

    # Consolidation detection
    consolidation_start_time: str = "12:00"
    consolidation_atr_ratio: float = Field(default=0.75, gt=0, le=5.0)
    max_consolidation_atr_ratio: float = Field(default=2.0, gt=0, le=10.0)
    min_consolidation_bars: int = Field(default=30, ge=5, le=120)

    # Breakout confirmation
    volume_multiplier: float = Field(default=1.2, gt=0, le=5.0)
    max_chase_pct: float = Field(default=0.005, ge=0, le=0.03)

    # Targets and stops
    target_1_r: float = Field(default=1.0, gt=0)
    target_2_r: float = Field(default=2.0, gt=0)
    max_hold_minutes: int = Field(default=60, ge=5, le=120)
    stop_buffer_pct: float = Field(default=0.001, ge=0, le=0.05)

    # EOD
    force_close_time: str = "15:45"

    @model_validator(mode="after")
    def validate_atr_ratios(self) -> AfternoonMomentumConfig:
        """Ensure consolidation_atr_ratio < max_consolidation_atr_ratio."""
        if self.consolidation_atr_ratio >= self.max_consolidation_atr_ratio:
            raise ValueError(
                f"consolidation_atr_ratio ({self.consolidation_atr_ratio}) must be less than "
                f"max_consolidation_atr_ratio ({self.max_consolidation_atr_ratio})"
            )
        return self
```

Also add `load_afternoon_momentum_config()` following the same pattern as `load_vwap_reclaim_config()`.

**Strategy implementation pattern:** Follow `vwap_reclaim.py` exactly for structure:
- Same import pattern, same BaseStrategy inheritance
- Same `_get_candle_time()` and `_is_in_entry_window()` helpers
- Same position sizing with min risk floor (0.3%)
- Same `get_scanner_criteria()` returning shared gap criteria
- Unique: `_compute_effective_time_stop()` for EOD proximity handling
- Unique: two-phase state machine (ACCUMULATING → CONSOLIDATED → entry)

**Key implementation detail — effective time stop:**
```python
def _compute_effective_time_stop(self, candle: CandleEvent) -> int:
    """Compute time stop in seconds, accounting for EOD proximity."""
    configured_seconds = self._pm_config.max_hold_minutes * 60

    # Parse force close time
    fc_h, fc_m = map(int, self._pm_config.force_close_time.split(":"))
    force_close = time(fc_h, fc_m)

    candle_dt = candle.timestamp.astimezone(ET)
    force_close_dt = candle_dt.replace(
        hour=fc_h, minute=fc_m, second=0, microsecond=0
    )
    seconds_until_close = max(0, int((force_close_dt - candle_dt).total_seconds()))

    return min(configured_seconds, seconds_until_close)
```

**Unit tests (~30+ tests):**
- State machine transitions: WATCHING→ACCUMULATING, ACCUMULATING→CONSOLIDATED, ACCUMULATING→REJECTED
- Consolidation detection: tight range confirms, wide range rejects, minimum bars required
- Breakout entry: close above consolidation high with volume, chase protection blocks
- Time window enforcement: before 2:00 PM (no entry), after 3:30 PM (no entry)
- EOD time stop: entry at 3:25 PM gets 20-min effective time stop, not 60-min
- Position sizing with min risk floor
- Signal building: correct prices, targets, time_stop_seconds
- Daily state reset
- Position closed tracking
- ATR integration (via data service mock)
- Volume confirmation: average volume calculation, multiplier threshold
- Edge cases: no ATR available, zero volume, consolidation_high == consolidation_low

### Session 2: Strategy Tests + Edge Cases

Complete the test suite. Ensure at least 30 unit tests covering every state transition and edge case. Pattern: follow `tests/strategies/test_vwap_reclaim.py` structure.

---

## Pillar 2: Backtesting

### Session 3–4: VectorBT Parameter Sweep

**File:** `argus/backtest/vectorbt_afternoon_momentum.py`

**MANDATORY: Follow precompute+vectorize architecture (DEC-149).**

**Architecture:**

1. **Precompute consolidation data per day (ONCE):**
   - For each qualifying day (gap filter passes):
     - Extract bars from 12:00 PM onward
     - Compute midday high/low from 12:00–2:00 PM bars
     - Compute VWAP vectorized
     - Compute ATR (from all morning + midday bars)
     - For each bar after 2:00 PM where close > midday_high: record as potential entry candidate
     - Store: entry_bar_idx, entry_price, consolidation_high, consolidation_low, consolidation_range, atr_at_entry, consolidation_bar_count, volume_ratio, post-entry NumPy arrays (highs, lows, closes, minutes)

2. **Per-parameter filtering (fast inner loop):**
   - Filter precomputed entries by: consolidation_ratio < consolidation_atr_ratio, bars >= min_consolidation_bars, volume_ratio >= volume_multiplier
   - For each passing entry: call `_find_exit_vectorized()` with stop/target/time_stop/EOD

3. **Vectorized exit detection:** Same pattern as VWAP Reclaim — NumPy boolean masks for stop/target/time_stop/EOD.

**Parameter space:**

| Parameter | Values | Count |
|-----------|--------|-------|
| `consolidation_atr_ratio` | 0.5, 0.75, 1.0, 1.5 | 4 |
| `min_consolidation_bars` | 15, 30, 45, 60 | 4 |
| `volume_multiplier` | 1.0, 1.2, 1.5 | 3 |
| `target_r` | 1.0, 1.5, 2.0, 3.0 | 4 |
| `time_stop_bars` | 15, 30, 45, 60 | 4 |

**Total combinations:** 4 × 4 × 3 × 4 × 4 = **768 combinations**

**Performance target:** 29 symbols × 35 months × 768 combos in **< 30 seconds**.

**Consolidation precomputation detail:**

For each qualifying day:
1. Find bars where `minutes_from_midnight >= 720` (12:00 PM) and `< 840` (2:00 PM) → these are the midday bars
2. `midday_high = max(midday_bars.high)`, `midday_low = min(midday_bars.low)`
3. `midday_range = midday_high - midday_low`
4. Compute ATR-14 from morning bars (9:30 AM through end of midday)
5. `consolidation_ratio = midday_range / atr` (save for filtering)
6. `consolidation_bar_count = len(midday_bars)` (save for filtering)
7. Find bars where `minutes_from_midnight >= 840` (2:00 PM) and `< 930` (3:30 PM) → afternoon bars
8. For afternoon bars where `close > midday_high`: potential entry candidates
9. Take FIRST such bar (one entry per day for sweep), capture post-entry arrays

**Important:** The precompute step records ALL potential entries regardless of parameter values. The midday_range, atr, consolidation_bar_count, and volume_ratio are stored with each entry. The per-parameter loop just filters: `entry.consolidation_ratio < param.consolidation_atr_ratio AND entry.bars >= param.min_consolidation_bars AND entry.volume_ratio >= param.volume_multiplier`.

**Output:** Same as VWAP Reclaim sweep — results DataFrame, heatmaps (HTML + PNG).

**Tests:** `tests/backtest/test_vectorbt_afternoon_momentum.py` (~15 tests):
- Consolidation precomputation: tight range detected, wide range excluded
- Entry candidate identification: breakout after 2:00 PM captured
- Vectorized exit: stop, target, time stop, EOD priority
- Run sweep on synthetic data
- Heatmap generation (with `pytest.importorskip("plotly")`)

### Session 5: Walk-Forward + Replay Harness Integration

**Walk-forward (`argus/backtest/walk_forward.py`):**
- Add `StrategyType.AFTERNOON_MOMENTUM = "afternoon_momentum"` to enum in `argus/backtest/config.py`
- Add `afternoon_momentum` dispatch block in `walk_forward.py` (parallel to the `vwap_reclaim` block)
- Add afternoon momentum parameters to `BacktestConfig`

**Replay Harness (`argus/backtest/replay_harness.py`):**
- Add `AfternoonMomentumStrategy` to the strategy factory `_create_strategy()`
- Import and instantiate with `AfternoonMomentumConfig`

**BacktestConfig (`argus/backtest/config.py`):**
- Add afternoon momentum fields (consolidation_atr_ratio, min_consolidation_bars, volume_multiplier, max_hold_minutes, target_r)

---

## Pillar 3: Integration

### Session 6: Orchestrator + main.py Integration

**`argus/main.py`:**
- Import `AfternoonMomentumStrategy` and `load_afternoon_momentum_config`
- Add afternoon momentum creation block (same pattern as VWAP Reclaim):
  ```python
  afternoon_strategy: AfternoonMomentumStrategy | None = None
  afternoon_yaml = self._config_dir / "strategies" / "afternoon_momentum.yaml"
  if afternoon_yaml.exists():
      afternoon_config = load_afternoon_momentum_config(afternoon_yaml)
      afternoon_strategy = AfternoonMomentumStrategy(
          config=afternoon_config,
          data_service=self._data_service,
          clock=self._clock,
      )
      afternoon_strategy.set_watchlist(symbols)
      strategies_created.append("AfternoonMomentum")
  ```
- Register with Orchestrator
- Add health monitor component `"strategy_afternoon_momentum"`

**`argus/core/config.py`:**
- Ensure `__init__.py` exports the new config class and loader

### Session 7: Integration Tests

**File:** `tests/test_integration_sprint20.py`

**Test scenarios (~15 tests):**

1. **Four-strategy allocation split** — Orchestrator with 4 strategies gets 20/20/20/20/20 (with 20% cash reserve)
2. **Full-day sequential flow** — ORB entry 9:40 AM → close 9:55 AM → VWAP Reclaim entry 10:30 AM → close 11:00 AM → [midday quiet, consolidation forms] → Afternoon Momentum entry 2:15 PM → close 2:45 PM
3. **Four-strategy concurrent risk** — max_single_stock_pct (5%) checked across all four strategies
4. **Afternoon Momentum regime preferences** — Bullish Trending + High Volatility = active. Crisis = suspended. Verify via Orchestrator.
5. **EOD flatten coordination** — Afternoon Momentum has open position at 3:44 PM → Order Manager EOD flatten at 3:45 PM closes it
6. **Late entry time stop** — Entry at 3:28 PM with 60-min max hold → effective time stop = 17 minutes (3:45 - 3:28)
7. **No-consolidation day** — Midday range too wide → REJECTED state → no afternoon trades
8. **Consolidation but no breakout** — Range is tight but price never exceeds consolidation_high → no entry
9. **Volume filter blocks breakout** — Price breaks out but volume below threshold → stays CONSOLIDATED
10. **Same-symbol ALLOW_ALL** — ORB trades AAPL at 9:40, Afternoon Momentum trades AAPL at 2:15 (different positions, both allowed)
11. **Orchestrator throttle applied** — Afternoon Momentum suspended due to consecutive losses → no entries even with valid consolidation
12. **Daily state reset** — End of day → all symbol states cleared, next day starts fresh in WATCHING
13. **Allocation rebalance with four strategies** — Orchestrator rebalance distributes to all four
14. **Chase protection blocks late breakout** — Price gaps far above consolidation high → entry blocked
15. **Consolidation tracking start time** — Bars before 12:00 PM don't contribute to consolidation range

---

## Pillar 4: UX & Dev Mode

### Session 8: Dev Mode Mock Data

**File:** `argus/api/dev_state.py`

Add Afternoon Momentum as the fourth strategy in all mock data:

1. **Open positions:** 1-2 afternoon momentum positions (entered ~2:10 PM, holding)
2. **Closed trades:** 6 afternoon momentum trades (mix: T1, T2, SL, TIME, EOD)
3. **Strategy cards:** `strategy_afternoon_momentum` in system health
4. **Allocation:** Four-strategy split in StrategyAllocation (orb=20%, scalp=20%, vwap_reclaim=20%, afternoon_momentum=20%)
5. **CapitalAllocation component:** Four segments in donut + bars
6. **Performance page:** Four-strategy breakdown
7. **Watchlist sidebar:** Afternoon Momentum badge letter = **"A"** (for Afternoon)
8. **Session summary:** Include afternoon momentum trades
9. **Orchestrator decisions:** Include afternoon momentum entries in decision log mock

**Pattern:** Follow exactly how `vwap_reclaim` was added in Sprint 19 dev_state.py. Search for `"vwap_reclaim"` and add parallel `"afternoon_momentum"` entries.

**Afternoon momentum symbols for mock data:** `["MSFT", "GOOG", "META", "AMZN"]` — large-cap names that could plausibly consolidate midday.

### Session 9: Strategy Spec Sheet

**File:** `docs/strategies/STRATEGY_AFTERNOON_MOMENTUM.md`

Fill in the strategy template (04_STRATEGY_TEMPLATE.md) with all resolved design parameters. See the VWAP Reclaim spec sheet for the pattern. Key sections:

- **Market Conditions Filter:** Bullish Trending, High Volatility, Low Volatility. Not Range-Bound (consolidation breakouts need directional momentum). Not Crisis. VIX < 30.
- **Operating Window:** Earliest 2:00 PM, Latest 3:30 PM, Force Close 3:45 PM
- **Scanner Criteria:** Same gap scanner as ORB/VWAP
- **Entry Criteria:** All 8 conditions from DEC-156
- **Exit Rules:** Stop below consolidation low, T1 1.0R (50%), T2 2.0R (50%), time stop min(60min, until 3:45 PM)
- **State Machine Diagram:** The 5 states and transitions
- **Parameter Table:** All config parameters with defaults, ranges, rationale
- **VectorBT Sweep Parameters:** The 768-combination grid

---

## Session Breakdown

| Session | Scope | Est. Tests |
|---------|-------|-----------|
| 0 | Fix plotly test failures (11 tests) | +0 (fixes existing) |
| 1 | Config + strategy scaffold + state machine | +20 |
| 2 | Strategy tests + edge cases | +15 |
| 3 | VectorBT sweep precompute architecture | +10 |
| 4 | VectorBT sweep completion + heatmaps | +5 |
| 5 | Walk-forward + Replay Harness integration | +5 |
| 6 | main.py + Orchestrator integration | +5 |
| 7 | Integration tests (four-strategy) | +15 |
| 8 | Dev mode mock data + UI updates | +7 Vitest |
| 9 | Strategy spec sheet + YAML config | +0 (docs) |
| 10 | Code review checkpoint | +0 (review) |
| 11 | Code review fixes | +5 |

**Estimated total:** ~80 new pytest tests + ~7 new Vitest tests = ~1490 pytest + ~47 Vitest

---

## Files Changed/Created Summary

### New Files
- `argus/strategies/afternoon_momentum.py` — Strategy class
- `argus/backtest/vectorbt_afternoon_momentum.py` — VectorBT sweep
- `config/strategies/afternoon_momentum.yaml` — Default config
- `docs/strategies/STRATEGY_AFTERNOON_MOMENTUM.md` — Strategy spec sheet
- `tests/strategies/test_afternoon_momentum.py` — Unit tests
- `tests/backtest/test_vectorbt_afternoon_momentum.py` — Sweep tests
- `tests/test_integration_sprint20.py` — Integration tests

### Modified Files
- `argus/core/config.py` — AfternoonMomentumConfig, load_afternoon_momentum_config()
- `argus/backtest/config.py` — StrategyType.AFTERNOON_MOMENTUM, BacktestConfig fields
- `argus/backtest/walk_forward.py` — Afternoon momentum dispatch
- `argus/backtest/replay_harness.py` — Strategy factory addition
- `argus/main.py` — Strategy creation + registration + health
- `argus/api/dev_state.py` — Fourth strategy mock data
- `tests/backtest/test_vectorbt_orb_scalp.py` — Fix plotly importorskip guards

### Export Updates
- `argus/strategies/__init__.py` — Export AfternoonMomentumStrategy
- `argus/core/__init__.py` — Export AfternoonMomentumConfig if not already handled

---

## Market Regime Preferences

From the Project Bible section 5.3:

| Regime | Afternoon Momentum | Rationale |
|--------|-------------------|-----------|
| Bullish Trending + High Vol | **FAVORED** | Strong directional moves after consolidation |
| Bullish Trending + Low Vol | **ACTIVE** | Sustained trends, quieter breakouts |
| Range-Bound + High Vol | REDUCED | Breakouts may fail in range-bound conditions |
| Range-Bound + Low Vol | REDUCED | Insufficient momentum for follow-through |
| Crisis | SUSPENDED | All strategies suspended |

Implemented via `get_market_conditions_filter()`:
```python
def get_market_conditions_filter(self) -> MarketConditionsFilter:
    return MarketConditionsFilter(
        allowed_regimes=["bullish_trending", "high_volatility"],
        max_vix=30.0,
    )
```

---

## Time Window Coverage After Sprint 20

| Time Window | Strategy | Type | Hold |
|---|---|---|---|
| 9:35–10:00 AM | ORB Breakout | Opening momentum | 1–15 min |
| 9:45–10:00 AM | ORB Scalp | Fast momentum | 10s–2 min |
| 10:00 AM–12:00 PM | VWAP Reclaim | Mean-reversion | 5–30 min |
| 12:00–2:00 PM | *Midday quiet* | Consolidation forms | — |
| 2:00–3:30 PM | Afternoon Momentum | Consolidation breakout | 15–60 min |

Full-day coverage: 9:35 AM – 3:45 PM with intentional midday quiet period.

---

## Decisions to Log (DEC-152 through DEC-161)

After sprint completion, add these to the Decision Log:

- DEC-152: Afternoon Momentum standalone from BaseStrategy
- DEC-153: Consolidation detection — high/low channel + ATR filter
- DEC-154: Scanner reuse — gap watchlist
- DEC-155: Afternoon Momentum state machine (5 states)
- DEC-156: Breakout entry conditions (8 simultaneous requirements)
- DEC-157: Stop and target design (T1/T2, dynamic time stop)
- DEC-158: Trailing stop deferred to V2
- DEC-159: EOD handling (3:45 PM force close, dynamic time stop calculation)
- DEC-160: Cross-strategy interaction (ALLOW_ALL, time-separated)
- DEC-161: Databento activation deferred to Sprint 21

---

## Risk Items to Log

- **RSK-030:** Afternoon Momentum consolidation detection may produce few trades in the existing 35-month Parquet dataset (Alpaca IEX data captures ~2-3% of volume). Low trade counts in sweep are expected and not necessarily indicative of strategy viability. True validation requires Databento data (DEC-132).
- **RSK-031:** EOD time stop compression — entries after 3:15 PM have ≤30 minutes effective hold time. If the strategy consistently enters late, most exits will be time stops rather than targets. Monitor time-of-entry distribution in sweep results.

---

## Code Review Checklist

At the end of Sprint 20, verify:

1. [ ] All 5 state transitions tested with unit tests
2. [ ] EOD time stop calculation correct for entries at 2:00, 2:30, 3:00, 3:15, 3:25 PM
3. [ ] VectorBT sweep completes in < 30 seconds for 29 symbols × 35 months
4. [ ] Walk-forward pipeline runs with `--strategy afternoon_momentum`
5. [ ] Replay harness creates `AfternoonMomentumStrategy` correctly
6. [ ] main.py registers fourth strategy with Orchestrator
7. [ ] Dev mode shows four strategies in all relevant views
8. [ ] Four-strategy allocation = 20/20/20/20/20 with cash reserve
9. [ ] Integration tests pass for full-day sequential flow
10. [ ] Strategy spec sheet complete (no TBD fields)
11. [ ] Config YAML validates with Pydantic
12. [ ] No ruff lint errors
13. [ ] All plotly test failures fixed (importorskip guards)
14. [ ] `AfternoonMomentumStrategy` exported from `argus/strategies/__init__.py`
