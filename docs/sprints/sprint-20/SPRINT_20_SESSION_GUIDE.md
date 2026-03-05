# Sprint 20 — Session Guide & Materials

> All materials needed to execute Sprint 20 across Claude Code sessions and code review checkpoints.
> Generated: February 26, 2026.

---

## Table of Contents

1. [Session Breakdown & Compaction Strategy](#1-session-breakdown--compaction-strategy)
2. [Claude Code Session Prompts](#2-claude-code-session-prompts)
3. [Code Review Plan](#3-code-review-plan)
4. [Code Review Handoff Briefs](#4-code-review-handoff-briefs)
5. [Doc Updates to Make Now](#5-doc-updates-to-make-now)

---

## 1. Session Breakdown & Compaction Strategy

### Principles

- **Each session has a single clear objective** — one pillar or sub-pillar per session
- **Sessions that create new files are safer** than sessions that modify many existing files (less context needed)
- **Test files are created in the same session as the code they test** — ensures the author has full context
- **Integration work (main.py, dev_state.py) is separate from core logic** — different cognitive load
- **Code review happens at natural seams** — after core strategy + backtesting, and after integration + UX

### Session Map

```
Session 0:  Plotly test fixes (housekeeping, quick)
Session 1:  Config + Strategy class + core state machine
Session 2:  Strategy unit tests (comprehensive)
Session 3:  VectorBT sweep — precompute architecture + exit detection
Session 4:  VectorBT sweep — run_sweep + heatmaps + sweep tests
Session 5:  Walk-forward + Replay Harness + backtest config integration

────── CODE REVIEW A (after Session 5) ──────
        Review: strategy logic, backtesting, state machine correctness

Session 6:  main.py + Orchestrator integration + config exports
Session 7:  Integration tests (four-strategy scenarios)
Session 8:  Dev mode mock data + UI badge additions
Session 9:  Strategy spec sheet (docs/strategies/STRATEGY_AFTERNOON_MOMENTUM.md)

────── CODE REVIEW B (after Session 9) ──────
        Review: integration, dev mode, full-system correctness, docs

Session 10: Code review fixes from Review A + B
Session 11: Final doc updates (decision log, sprint plan, project knowledge)
```

### Context Management Notes

- **Sessions 1–2** are the highest-risk for compaction. The strategy file is ~300-400 lines and the test file is ~500+ lines. If Claude Code starts losing context in Session 2, split tests into two sub-sessions (2a: state machine tests, 2b: entry/edge case tests).
- **Sessions 3–4** are split because VectorBT sweeps are ~800+ lines. Session 3 does the hard architecture (precompute + exit detection). Session 4 does the aggregation layer (run_sweep, metrics, heatmaps, CLI).
- **Session 8** (dev_state.py) requires understanding the existing mock data structure. The prompt includes the specific patterns to follow.
- **Session 10** is intentionally after BOTH reviews so fixes can be batched.

---

## 2. Claude Code Session Prompts

### Session 0 — Plotly Test Fixes

```
# Sprint 20 Session 0: Fix Plotly Test Environment Failures

Read CLAUDE.md for current project state. Then read `tests/backtest/test_vectorbt_orb_scalp.py`.

There are 11 test failures in this file caused by `plotly` not being installed in the test environment. The `generate_heatmap()` function imports plotly at runtime, but the test file imports it at module level via the function import.

**Fix:** Add `pytest.importorskip("plotly")` at the beginning of every test function that directly or indirectly calls `generate_heatmap()`. Do NOT add it at module level — that would skip the entire file. Only guard the specific tests that need plotly.

Check if the same issue exists in:
- `tests/backtest/test_vectorbt_orb.py`
- `tests/backtest/test_vectorbt_vwap_reclaim.py`

If so, apply the same fix pattern.

After fixing, run `pytest tests/backtest/` to verify all tests pass (excluding any that legitimately need plotly, which should be skipped cleanly).

Commit: `fix: add plotly importorskip guards to vectorbt test files`
```

---

### Session 1 — Config + Strategy Class + State Machine

```
# Sprint 20 Session 1: Afternoon Momentum Config + Strategy + State Machine

Read CLAUDE.md first, then read the Sprint 20 implementation spec at the end of this prompt.

## Context Files to Read
1. `argus/strategies/vwap_reclaim.py` — Pattern to follow (most recent strategy)
2. `argus/strategies/base_strategy.py` — Interface to implement
3. `argus/core/config.py` — Where to add AfternoonMomentumConfig (find VwapReclaimConfig and add after it)
4. `config/strategies/vwap_reclaim.yaml` — Pattern for YAML config
5. `argus/data/indicator_engine.py` — Available indicators (need ATR-14)

## Deliverables

### 1. AfternoonMomentumConfig in argus/core/config.py

Add after VwapReclaimConfig. Fields:

```python
class AfternoonMomentumConfig(StrategyConfig):
    """Afternoon Momentum strategy configuration (DEC-152).

    Consolidation breakout strategy that identifies stocks consolidating
    during midday (12:00–2:00 PM) and entering on breakouts after 2:00 PM.
    """
    consolidation_start_time: str = "12:00"
    consolidation_atr_ratio: float = Field(default=0.75, gt=0, le=5.0)
    max_consolidation_atr_ratio: float = Field(default=2.0, gt=0, le=10.0)
    min_consolidation_bars: int = Field(default=30, ge=5, le=120)
    volume_multiplier: float = Field(default=1.2, gt=0, le=5.0)
    max_chase_pct: float = Field(default=0.005, ge=0, le=0.03)
    target_1_r: float = Field(default=1.0, gt=0)
    target_2_r: float = Field(default=2.0, gt=0)
    max_hold_minutes: int = Field(default=60, ge=5, le=120)
    stop_buffer_pct: float = Field(default=0.001, ge=0, le=0.05)
    force_close_time: str = "15:45"

    @model_validator(mode="after")
    def validate_atr_ratios(self) -> AfternoonMomentumConfig:
        if self.consolidation_atr_ratio >= self.max_consolidation_atr_ratio:
            raise ValueError(...)
        return self
```

Also add `load_afternoon_momentum_config()` following the `load_vwap_reclaim_config()` pattern.

### 2. config/strategies/afternoon_momentum.yaml

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

### 3. argus/strategies/afternoon_momentum.py

Full strategy class. Follow vwap_reclaim.py structure exactly. Key differences:

**State machine (5 states):**
- WATCHING: Before consolidation_start_time (12:00 PM). Ignore all candles.
- ACCUMULATING: 12:00 PM onward. Track midday_high/midday_low. Check consolidation criteria each bar.
- CONSOLIDATED: Range confirmed tight (midday_range/ATR < consolidation_atr_ratio, bars >= min). Watch for breakout.
- ENTERED: Position taken. Terminal.
- REJECTED: Midday range too wide (> max_consolidation_atr_ratio). Terminal.

**Consolidation detection (in _process_accumulating):**
```
midday_range = midday_high - midday_low
consolidation_ratio = midday_range / atr_14
if consolidation_ratio > max_consolidation_atr_ratio → REJECTED
if consolidation_ratio < consolidation_atr_ratio AND bars >= min → CONSOLIDATED
else: stay ACCUMULATING, update range
```

**Important: CONSOLIDATED continues updating the range.** Bars arriving while CONSOLIDATED still update midday_high/midday_low. This means the range can widen, and if it exceeds max_consolidation_atr_ratio, the state transitions to REJECTED. Breakout is checked against the CURRENT consolidation_high (which may have shifted).

**Breakout entry (in _process_consolidated):**
Must check time >= 2:00 PM (earliest_entry) before checking breakout. 8 conditions:
1. State is CONSOLIDATED
2. Time 2:00–3:30 PM
3. Candle close > consolidation_high
4. Volume >= multiplier × avg
5. Chase protection
6. Risk > 0
7. Internal risk limits
8. Position count limit

**Dynamic time stop:**
```python
def _compute_effective_time_stop(self, candle: CandleEvent) -> int:
    configured_seconds = self._pm_config.max_hold_minutes * 60
    fc_h, fc_m = map(int, self._pm_config.force_close_time.split(":"))
    candle_dt = candle.timestamp.astimezone(ET)
    force_close_dt = candle_dt.replace(hour=fc_h, minute=fc_m, second=0, microsecond=0)
    seconds_until_close = max(0, int((force_close_dt - candle_dt).total_seconds()))
    return min(configured_seconds, seconds_until_close)
```

**Position sizing:** Same as VWAP Reclaim — includes 0.3% minimum risk floor.

**get_market_conditions_filter():** allowed_regimes=["bullish_trending", "high_volatility"], max_vix=30.0

**set_data_service():** Same pattern as VWAP Reclaim (for ATR queries).

### 4. Update argus/strategies/__init__.py

Export AfternoonMomentumStrategy.

### 5. Update argus/core/__init__.py (if needed)

Export AfternoonMomentumConfig and load_afternoon_momentum_config.

After creating all files, run `pytest tests/strategies/ -x` to catch any import errors. Don't write tests yet — that's Session 2.

Commit: `feat(sprint20): add AfternoonMomentumConfig and AfternoonMomentumStrategy`
```

---

### Session 2 — Strategy Unit Tests

```
# Sprint 20 Session 2: Afternoon Momentum Unit Tests

Read CLAUDE.md, then read:
1. `argus/strategies/afternoon_momentum.py` (created in Session 1)
2. `argus/core/config.py` (AfternoonMomentumConfig)
3. `tests/strategies/test_vwap_reclaim.py` — Test pattern to follow

## Deliverable

Create `tests/strategies/test_afternoon_momentum.py` with comprehensive tests.

### Test Structure

Follow the test_vwap_reclaim.py pattern: config factory at top, helper to create CandleEvents at specific times, group tests by category.

**Helper needed:**
```python
def make_candle(symbol, timestamp_et, open_, high, low, close, volume):
    """Create a CandleEvent at a specific ET time."""
    # Convert ET to UTC for the event
    ...
```

**Config factory:**
```python
def make_config(**overrides) -> AfternoonMomentumConfig:
    defaults = {
        "strategy_id": "strat_afternoon_momentum",
        "name": "Afternoon Momentum",
        "consolidation_start_time": "12:00",
        "consolidation_atr_ratio": 0.75,
        "max_consolidation_atr_ratio": 2.0,
        "min_consolidation_bars": 30,
        "volume_multiplier": 1.2,
        "max_chase_pct": 0.005,
        "target_1_r": 1.0,
        "target_2_r": 2.0,
        "max_hold_minutes": 60,
        "stop_buffer_pct": 0.001,
        "force_close_time": "15:45",
        "operating_window": {"earliest_entry": "14:00", "latest_entry": "15:30", "force_close": "15:45"},
        "risk_limits": {"max_loss_per_trade_pct": 0.01, "max_daily_loss_pct": 0.03, "max_trades_per_day": 6, "max_concurrent_positions": 3},
    }
    defaults.update(overrides)
    return AfternoonMomentumConfig(**defaults)
```

### Required Tests (~35 tests)

**State Machine Transitions (8 tests):**
1. test_initial_state_is_watching — new symbol starts in WATCHING
2. test_watching_to_accumulating_at_noon — first candle at 12:00 PM transitions
3. test_watching_ignores_morning_candles — candles before 12:00 PM stay WATCHING
4. test_accumulating_tracks_range — midday_high and midday_low update correctly
5. test_accumulating_to_consolidated — range/ATR < threshold after enough bars
6. test_accumulating_to_rejected — range/ATR > max threshold
7. test_consolidated_breakout_to_entered — valid breakout triggers entry
8. test_consolidated_range_widening_to_rejected — range expands beyond max while consolidated

**Consolidation Detection (5 tests):**
9. test_tight_range_confirms_consolidation — small midday_range relative to ATR
10. test_wide_range_rejects — large midday_range relative to ATR → REJECTED
11. test_min_bars_required — consolidation_ratio passes but bars < min → stays ACCUMULATING
12. test_consolidation_with_zero_atr — ATR is None or 0, consolidation cannot confirm
13. test_consolidation_ratio_calculation — verify exact math: (high-low)/ATR

**Entry Conditions (8 tests):**
14. test_breakout_with_volume_confirmation — close > high, volume OK → signal
15. test_breakout_without_volume — close > high, volume too low → no signal, stays CONSOLIDATED
16. test_breakout_before_2pm — close > high but before entry window → no signal
17. test_breakout_after_330pm — close > high but after latest entry → no signal
18. test_chase_protection_blocks — close too far above consolidation_high → no signal
19. test_entry_with_zero_risk — stop >= entry → no signal (shares = 0)
20. test_max_concurrent_positions — at limit → no new entry, stays CONSOLIDATED
21. test_max_trades_per_day — at limit → no new entry

**Signal Building (5 tests):**
22. test_signal_prices_correct — entry, stop, T1, T2 computed correctly
23. test_signal_share_count — position sizing with risk formula
24. test_signal_min_risk_floor — shallow stop triggers 0.3% floor
25. test_signal_time_stop_seconds — normal case, 60 min time stop
26. test_signal_rationale_string — contains key info (symbol, consolidation, etc.)

**EOD Time Stop (4 tests):**
27. test_time_stop_normal — entry at 2:15 PM → 60 min (well before 3:45)
28. test_time_stop_compressed — entry at 3:25 PM → 20 min (3:45 - 3:25)
29. test_time_stop_very_late — entry at 3:29 PM → 16 min
30. test_time_stop_exact_boundary — entry at 2:45 PM → 60 min (2:45 + 60 = 3:45 exactly)

**State Management (5 tests):**
31. test_daily_state_reset — clears all symbol states
32. test_mark_position_closed — updates position_active flag
33. test_not_in_watchlist_ignored — candle for unknown symbol returns None
34. test_terminal_state_entered_no_more_signals — after ENTERED, subsequent candles return None
35. test_terminal_state_rejected_no_more_signals — after REJECTED, no more processing

Run `pytest tests/strategies/test_afternoon_momentum.py -v` after writing all tests.

Commit: `test(sprint20): comprehensive AfternoonMomentumStrategy unit tests`
```

---

### Session 3 — VectorBT Sweep: Precompute Architecture

```
# Sprint 20 Session 3: VectorBT Afternoon Momentum Sweep — Precompute Architecture

Read CLAUDE.md and `.claude/rules/backtesting.md` (MANDATORY — the precompute+vectorize rule).

Then read:
1. `argus/backtest/vectorbt_vwap_reclaim.py` — Architecture to follow
2. `argus/backtest/vectorbt_orb.py` — Original sweep pattern (for reference)

## Deliverable

Create `argus/backtest/vectorbt_afternoon_momentum.py` — the first half: config, data loading, precompute, and exit detection.

### Architecture (DEC-149 mandatory compliance)

**Precompute once per day, filter per parameter combination.**

1. `load_symbol_data()` — Reuse the same function from vectorbt_vwap_reclaim.py OR import it. If the function is identical, consider extracting to a shared utility (your call — if it's simpler to duplicate, that's fine for now).

2. `compute_qualifying_days()` — Same gap filter logic. Can reuse/import.

3. `_compute_atr_for_day(day_df)` → float — Compute ATR-14 from morning+midday bars (9:30 AM–2:00 PM). Use true range calculation on 1-min bars. Return the ATR value at 2:00 PM (the value that would be available when breakout checking starts).

4. `_precompute_afternoon_entries_for_day(day_df, atr_value, max_chase_pct, stop_buffer_pct)` → list[AfternoonEntryInfo]
   - Extract midday bars (12:00 PM–2:00 PM): compute midday_high, midday_low
   - midday_range = midday_high - midday_low
   - consolidation_ratio = midday_range / atr_value (store with entry for filtering)
   - consolidation_bar_count = number of midday bars (store for filtering)
   - Extract afternoon bars (2:00 PM–3:30 PM)
   - Find FIRST bar where close > midday_high (the breakout candidate)
   - Compute volume_ratio = breakout_bar_volume / avg_volume_up_to_that_point
   - Check chase protection: close <= midday_high * (1 + max_chase_pct)
   - Check risk > 0: close - (midday_low * (1 - stop_buffer_pct)) > 0
   - If passes basic filters: store AfternoonEntryInfo with post-entry NumPy arrays
   - Return list (typically 0 or 1 entries per day)

5. `_find_exit_vectorized(...)` — Same as VWAP Reclaim's exit detection. NumPy boolean masks for stop/target/time_stop/EOD. Worst-case-for-longs priority. Can reuse the same function if the signature matches.

### Data Structures

```python
@dataclass
class AfternoonSweepConfig:
    data_dir: Path
    symbols: list[str]
    start_date: date
    end_date: date
    output_dir: Path
    # Swept parameters
    consolidation_atr_ratio_list: list[float] = field(default_factory=lambda: [0.5, 0.75, 1.0, 1.5])
    min_consolidation_bars_list: list[int] = field(default_factory=lambda: [15, 30, 45, 60])
    volume_multiplier_list: list[float] = field(default_factory=lambda: [1.0, 1.2, 1.5])
    target_r_list: list[float] = field(default_factory=lambda: [1.0, 1.5, 2.0, 3.0])
    time_stop_bars_list: list[int] = field(default_factory=lambda: [15, 30, 45, 60])
    # Fixed parameters
    max_chase_pct: float = 0.005
    stop_buffer_pct: float = 0.001
    min_gap_pct: float = 2.0
    min_price: float = 5.0
    max_price: float = 10000.0

class AfternoonEntryInfo(TypedDict):
    entry_bar_idx: int
    entry_price: float
    entry_minutes: int
    consolidation_high: float
    consolidation_low: float
    consolidation_ratio: float  # midday_range / ATR
    consolidation_bars: int
    volume_ratio: float
    highs: np.ndarray  # post-entry
    lows: np.ndarray
    closes: np.ndarray
    minutes: np.ndarray

@dataclass
class AfternoonSweepResult:
    symbol: str
    consolidation_atr_ratio: float
    min_consolidation_bars: int
    volume_multiplier: float
    target_r: float
    time_stop_bars: int
    total_trades: int
    win_rate: float
    total_return_pct: float
    avg_r_multiple: float
    max_drawdown_pct: float
    sharpe_ratio: float
    profit_factor: float
    avg_hold_bars: float
    qualifying_days: int
```

### Time Constants

```python
CONSOLIDATION_START_MINUTES = 12 * 60  # 12:00 PM = 720
CONSOLIDATION_END_MINUTES = 14 * 60    # 2:00 PM = 840
EARLIEST_ENTRY_MINUTES = 14 * 60       # 2:00 PM = 840
LATEST_ENTRY_MINUTES = 15 * 60 + 30    # 3:30 PM = 930
EOD_FLATTEN_MINUTES = 15 * 60 + 45     # 3:45 PM = 945
```

Write the functions listed above. Do NOT write run_single_symbol_sweep, run_sweep, generate_heatmaps, or main() yet — that's Session 4.

Run a quick sanity check: import the module, verify no syntax errors.

Commit: `feat(sprint20): VectorBT afternoon momentum precompute + exit detection`
```

---

### Session 4 — VectorBT Sweep: Completion + Tests

```
# Sprint 20 Session 4: VectorBT Afternoon Momentum Sweep — Completion + Tests

Read CLAUDE.md, then read:
1. `argus/backtest/vectorbt_afternoon_momentum.py` (Session 3 output)
2. `argus/backtest/vectorbt_vwap_reclaim.py` — `run_single_symbol_sweep()`, `run_sweep()`, `generate_heatmaps()`, `main()` patterns

## Deliverables

### 1. Complete vectorbt_afternoon_momentum.py

Add these functions following the VWAP Reclaim pattern:

**`run_single_symbol_sweep(symbol, df, qualifying_days, config)`** — The main per-symbol sweep:
- For each qualifying day: call _precompute_afternoon_entries_for_day()
- For each parameter combination (768 total): filter precomputed entries by consolidation_ratio < param, bars >= param, volume_ratio >= param. For each passing entry: _find_exit_vectorized() with stop/target/time_stop.
- Aggregate results per combination into AfternoonSweepResult

**Metrics computation functions:** _empty_afternoon_result(), _compute_afternoon_result(), _compute_max_drawdown_pct(), _compute_sharpe_from_r_multiples() — same pattern as VWAP.

**`run_sweep(config)`** → pd.DataFrame — Orchestrate across all symbols. Same pattern.

**`generate_heatmaps(results_df, output_dir)`** — HTML + PNG heatmaps. Use `plotly` import inside the function (not at module level) to avoid test environment issues.

**`main()`** — CLI with argparse. Same interface as VWAP sweep.

### 2. Create tests/backtest/test_vectorbt_afternoon_momentum.py

~15 tests:

1. test_compute_qualifying_days — gap filter works
2. test_compute_atr_for_day — ATR calculation on synthetic bars
3. test_precompute_finds_consolidation — tight midday range produces entry candidate
4. test_precompute_rejects_wide_range — wide midday range produces no candidates
5. test_precompute_captures_consolidation_ratio — verify stored ratio
6. test_precompute_no_breakout — tight consolidation but price never breaks high
7. test_precompute_chase_protection — breakout too far above high filtered out
8. test_exit_vectorized_stop — stop hit first
9. test_exit_vectorized_target — target hit first
10. test_exit_vectorized_time_stop — time stop hit, check if stop also hit
11. test_exit_vectorized_eod — EOD flatten
12. test_run_single_symbol_sweep — synthetic data produces results
13. test_run_sweep — multiple symbols
14. test_generate_heatmaps_creates_html — pytest.importorskip("plotly")
15. test_empty_results_heatmap — no trades, no crash

Run `pytest tests/backtest/test_vectorbt_afternoon_momentum.py -v`.

Commit: `feat(sprint20): complete VectorBT afternoon momentum sweep + tests`
```

---

### Session 5 — Walk-Forward + Replay Harness Integration

```
# Sprint 20 Session 5: Walk-Forward + Replay Harness + Backtest Config Integration

Read CLAUDE.md, then read:
1. `argus/backtest/config.py` — StrategyType enum, BacktestConfig
2. `argus/backtest/walk_forward.py` — how VWAP Reclaim dispatch was added
3. `argus/backtest/replay_harness.py` — strategy factory (_create_strategy)

## Deliverables

### 1. argus/backtest/config.py

Add to StrategyType enum:
```python
AFTERNOON_MOMENTUM = "afternoon_momentum"
```

Add afternoon momentum params to BacktestConfig (find the VWAP Reclaim section and add after):
```python
# Afternoon Momentum params (used when strategy_type=AFTERNOON_MOMENTUM)
consolidation_atr_ratio: float = 0.75
min_consolidation_bars: int = 30
afternoon_volume_multiplier: float = 1.2
afternoon_max_hold_minutes: int = 60
afternoon_target_1_r: float = 1.0
afternoon_target_2_r: float = 2.0
```

### 2. argus/backtest/walk_forward.py

Add afternoon momentum dispatch. Find the VWAP Reclaim block and add a parallel block for AFTERNOON_MOMENTUM. The dispatch should:
- Import and call run_single_symbol_sweep from vectorbt_afternoon_momentum
- Map BacktestConfig fields to AfternoonSweepConfig
- Return results in the standard format

### 3. argus/backtest/replay_harness.py

Add to `_create_strategy()`:
```python
elif self._config.strategy_type == StrategyType.AFTERNOON_MOMENTUM:
    from argus.core.config import AfternoonMomentumConfig
    from argus.strategies.afternoon_momentum import AfternoonMomentumStrategy
    config = AfternoonMomentumConfig(
        strategy_id="strat_afternoon_momentum",
        name="Afternoon Momentum",
        consolidation_atr_ratio=self._config.consolidation_atr_ratio,
        min_consolidation_bars=self._config.min_consolidation_bars,
        volume_multiplier=self._config.afternoon_volume_multiplier,
        max_hold_minutes=self._config.afternoon_max_hold_minutes,
        target_1_r=self._config.afternoon_target_1_r,
        target_2_r=self._config.afternoon_target_2_r,
        operating_window=OperatingWindow(
            earliest_entry="14:00",
            latest_entry="15:30",
            force_close="15:45",
        ),
    )
    return AfternoonMomentumStrategy(config=config, clock=self._clock)
```

### 4. Tests

Add ~5 tests to verify:
- StrategyType.AFTERNOON_MOMENTUM exists and has correct value
- BacktestConfig with afternoon params validates
- Walk-forward dispatch selects correct strategy (unit test with mock)
- Replay harness creates AfternoonMomentumStrategy (integration test)

Run `pytest tests/backtest/ -v`.

Commit: `feat(sprint20): walk-forward + replay harness afternoon momentum integration`
```

---

### Session 6 — main.py + Orchestrator Integration

```
# Sprint 20 Session 6: System Integration — main.py, Config Exports, Orchestrator

Read CLAUDE.md, then read:
1. `argus/main.py` — Strategy creation (find VWAP Reclaim block), registration, health
2. `argus/core/config.py` — load_afternoon_momentum_config (verify it exists from Session 1)
3. `argus/core/__init__.py` — Check current exports

## Deliverables

### 1. argus/main.py

**Phase 8 (Strategy Creation):** Add Afternoon Momentum block after VWAP Reclaim:
```python
# Afternoon Momentum (optional — only if config file exists)
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

**Phase 9 (Orchestrator Registration):**
```python
if afternoon_strategy is not None:
    self._orchestrator.register_strategy(afternoon_strategy)
```

**Phase 10 (Health Monitoring):**
```python
if afternoon_strategy is not None:
    self._health_monitor.update_component(
        "strategy_afternoon_momentum", ComponentStatus.HEALTHY, "Afternoon Momentum running"
    )
```

**Imports:** Add at top:
```python
from argus.core.config import load_afternoon_momentum_config
from argus.strategies.afternoon_momentum import AfternoonMomentumStrategy
```

### 2. Export updates

Ensure `argus/strategies/__init__.py` exports `AfternoonMomentumStrategy`.
Ensure `argus/core/__init__.py` exports `AfternoonMomentumConfig` and `load_afternoon_momentum_config` (if other configs are exported there — check existing pattern).

### 3. Quick smoke test

Run `pytest tests/ -x --ignore=tests/backtest -q` to verify no import cycles or missing exports.

Commit: `feat(sprint20): integrate afternoon momentum into main.py and orchestrator`
```

---

### Session 7 — Integration Tests

```
# Sprint 20 Session 7: Four-Strategy Integration Tests

Read CLAUDE.md, then read:
1. `tests/test_integration_sprint19.py` — Three-strategy integration test patterns
2. `argus/strategies/afternoon_momentum.py` — Strategy under test
3. `argus/core/orchestrator.py` — Strategy registration, allocation
4. `argus/core/risk_manager.py` — Cross-strategy risk checks
5. `argus/execution/order_manager.py` — EOD flatten, time stops

## Deliverable

Create `tests/test_integration_sprint20.py` — Four-strategy integration tests.

Follow the pattern from test_integration_sprint19.py exactly: config factories at top, fixture helpers, grouped test functions.

### Required Config Factory

```python
def make_afternoon_momentum_config(
    strategy_id: str = "strat_afternoon_momentum",
    **overrides,
) -> AfternoonMomentumConfig:
    defaults = dict(
        strategy_id=strategy_id,
        name="Afternoon Momentum",
        consolidation_start_time="12:00",
        consolidation_atr_ratio=0.75,
        max_consolidation_atr_ratio=2.0,
        min_consolidation_bars=3,  # Low for testing
        volume_multiplier=1.0,      # Low for testing
        max_chase_pct=0.01,
        target_1_r=1.0,
        target_2_r=2.0,
        max_hold_minutes=60,
        stop_buffer_pct=0.001,
        force_close_time="15:45",
        operating_window=OperatingWindow(
            earliest_entry="14:00", latest_entry="15:30", force_close="15:45"
        ),
        risk_limits=StrategyRiskLimits(
            max_trades_per_day=6,
            max_daily_loss_pct=0.03,
            max_loss_per_trade_pct=0.01,
            max_concurrent_positions=3,
        ),
    )
    defaults.update(overrides)
    return AfternoonMomentumConfig(**defaults)
```

### Tests (~15 tests)

1. **test_four_strategy_registration** — Register all four, verify orchestrator.get_strategies() has 4
2. **test_four_strategy_equal_allocation** — 80% / 4 = 20% each, 20% cash reserve
3. **test_full_day_sequential_flow** — ORB signal at 9:40 AM, VWAP signal at 10:30, Afternoon signal at 2:15 PM. All approved by Risk Manager.
4. **test_cross_strategy_stock_exposure** — All four try to enter AAPL. Aggregate exposure capped at 5%.
5. **test_afternoon_regime_active** — Bullish trending regime → afternoon momentum active
6. **test_afternoon_regime_suspended** — Crisis regime → afternoon momentum suspended (not active, no signals processed)
7. **test_eod_flatten_afternoon_position** — Position open at 3:44 PM, simulate EOD flatten
8. **test_late_entry_compressed_time_stop** — Entry at 3:28 PM → time_stop_seconds reflects 17 minutes
9. **test_no_consolidation_no_entry** — Feed midday candles with wide range → REJECTED, no afternoon signal
10. **test_consolidation_confirmed_breakout_triggers** — Feed tight midday candles → CONSOLIDATED, then breakout candle → signal
11. **test_volume_filter_blocks** — Breakout candle with low volume → no signal
12. **test_allow_all_same_symbol_different_times** — ORB trades TSLA at 9:40, afternoon momentum trades TSLA at 2:15
13. **test_orchestrator_throttle_blocks_afternoon** — Afternoon momentum suspended by throttler → candle processed but no signal accepted
14. **test_four_strategy_daily_reset** — After reset, all strategies have clean state
15. **test_afternoon_momentum_allocation_with_four_strategies** — Verify no single strategy exceeds 40% cap (trivially true at 20%)

Use FixedClock to control time. Use mock DataService that returns specific ATR-14 values.

Run `pytest tests/test_integration_sprint20.py -v`.

Commit: `test(sprint20): four-strategy integration tests`
```

---

### Session 8 — Dev Mode Mock Data + UI Updates

```
# Sprint 20 Session 8: Dev Mode Mock Data — Fourth Strategy

Read CLAUDE.md, then read:
1. `argus/api/dev_state.py` — Current mock data (search for "vwap_reclaim" to see the pattern)
2. `argus/ui/src/` — Search for "VWAP" or "vwap" to find where strategy names/badges appear

## Deliverables

### 1. argus/api/dev_state.py

Add Afternoon Momentum as the fourth strategy. Search for every occurrence of "vwap_reclaim" and add a parallel "afternoon_momentum" entry. Key additions:

**Trade generation:**
- Add `afternoon_momentum_count: int = 6` parameter
- Add `afternoon_symbols = ["MSFT", "GOOG", "META", "AMZN"]`
- Generate trades with entry times 14:00–15:30 ET, exit times 14:15–15:45 ET
- Exit reasons: mix of TARGET_1, TARGET_2, STOP_LOSS, TIME_STOP, EOD_FLATTEN

**Open positions:**
- Add 1-2 afternoon momentum positions (entered ~14:10, still open)
- Entry prices in $150-400 range (large-cap names)

**Strategy allocations:**
- Change from 3-way to 4-way: orb=20%, scalp=20%, vwap_reclaim=20%, afternoon_momentum=20%
- Update StrategyAllocation entries

**Strategy cards (system status):**
- Add afternoon_momentum strategy card
- Add "strategy_afternoon_momentum" health component

**Orchestrator decisions:**
- Include afternoon_momentum in decision log entries
- Include in "strategies" lists

**Session summary:**
- Include afternoon_momentum trades in session recap

**Watchlist sidebar:**
- Afternoon Momentum badge: letter "A", appropriate color (suggest blue/indigo to differentiate from existing badges)

### 2. UI Badge Updates

Search the React codebase for where strategy badge letters and colors are defined. Add "afternoon_momentum" → { letter: "A", color: appropriate }. This is likely in a constants file or a badge component.

### 3. Frontend Tests

Add ~7 Vitest tests verifying:
- Afternoon Momentum appears in strategy list
- CapitalAllocation shows 4 segments
- Badge renders with correct letter "A"
- Strategy card renders on System page

Run `cd argus/ui && npx vitest run`.

Commit: `feat(sprint20): dev mode mock data + UI badges for afternoon momentum`
```

---

### Session 9 — Strategy Spec Sheet

```
# Sprint 20 Session 9: Afternoon Momentum Strategy Spec Sheet

Read CLAUDE.md, then read:
1. `docs/strategies/STRATEGY_VWAP_RECLAIM.md` — Pattern to follow exactly
2. `docs/04_STRATEGY_TEMPLATE.md` — Template structure
3. `argus/strategies/afternoon_momentum.py` — Implementation details
4. `config/strategies/afternoon_momentum.yaml` — Config values

## Deliverable

Create `docs/strategies/STRATEGY_AFTERNOON_MOMENTUM.md`

Fill in every section of the template. NO TBD fields. Key content:

**Strategy Identity:**
- Name: Afternoon Momentum
- ID: strat_afternoon_momentum
- Version: 1.0.0
- Pipeline Stage: Concept → Exploration (Sprint 20)

**Description:** Consolidation breakout strategy. Identifies stocks from the morning gap watchlist that traded in a tight range during the midday lull (12:00–2:00 PM), then enter on breakout above the consolidation range during the afternoon session (2:00–3:30 PM). Thesis: institutional rebalancing and mutual fund flows during "power hour" drive strong moves in stocks that have consolidated after strong mornings.

**Market Conditions Filter:**
- Regime: Bullish Trending, High Volatility
- VIX: < 30
- SPY: Not in Crisis

**Operating Window:**
- Earliest entry: 2:00 PM ET
- Latest entry: 3:30 PM ET
- Force close: 3:45 PM ET
- Consolidation tracking: starts 12:00 PM ET

**Scanner Criteria:** Same as ORB (gap ≥ 2%, price $10-$200, volume ≥ 1M, RVOL ≥ 2.0)

**Entry Criteria:** All 8 conditions from DEC-156

**State Machine:** Full diagram of 5 states with transitions

**Exit Rules:**
- Stop: consolidation_low × (1 - 0.1%)
- T1: entry + risk × 1.0R (50% of position)
- T2: entry + risk × 2.0R (remaining 50%)
- Time stop: min(60 min, seconds until 3:45 PM)

**Parameter Table:** All config parameters with defaults, min/max, rationale

**VectorBT Sweep:** 768 combinations, parameter grid

**Risk Profile:** Max loss per trade 1%, max daily loss 3%, max concurrent 3

**Complementary Strategies:** Fills the 2:00–3:30 PM gap. ORB covers opening, VWAP Reclaim covers mid-morning, Afternoon Momentum covers late day.

Commit: `docs(sprint20): afternoon momentum strategy spec sheet`
```

---

### Session 10 — Code Review Fixes

```
# Sprint 20 Session 10: Code Review Fixes

Read CLAUDE.md. I'm providing code review feedback from two review checkpoints. Fix all issues listed below.

[PASTE CODE REVIEW FEEDBACK HERE — from Review A and Review B]

After fixing all issues, run the full test suite:
```
pytest tests/ -v --tb=short
cd argus/ui && npx vitest run
```

Commit: `fix(sprint20): code review fixes`
```

---

### Session 11 — Final Doc Updates

```
# Sprint 20 Session 11: Final Documentation Updates

Read CLAUDE.md, then update the following files.

## 1. CLAUDE.md

Update "Current State" section:
- Build Track: Sprint 20 (Afternoon Momentum) COMPLETE
- Test count: [final count] pytest + [final count] Vitest
- Add Sprint 20 Results paragraph (same format as Sprint 19 Results)
- Update Build Track queue: Afternoon Momentum (20) → done, next is CC Analytics & Strategy Lab (21)
- Add new components to the "Components implemented" list

## 2. docs/05_DECISION_LOG.md

Add DEC-152 through DEC-161. Check the current highest DEC number first!

[Use the exact decision entries from the sprint spec — I'll provide the final versions after code review]

## 3. docs/10_PHASE3_SPRINT_PLAN.md

Move Sprint 20 from "queue" to "completed" table. Record:
- Test counts (final)
- Session count
- Key outcomes
- DEC references

## 4. docs/06_RISK_REGISTER.md

Add RSK-030 and RSK-031. Check current highest RSK number first.

## 5. docs/03_ARCHITECTURE.md

Add AfternoonMomentumStrategy to strategy list. Add AfternoonMomentumConfig to config section.

Commit: `docs: update all docs for Sprint 20 completion`
```

---

## 3. Code Review Plan

### Review A — After Session 5 (Core Strategy + Backtesting)

**Timing:** After Sessions 0–5 are complete and committed.

**What to review:**
- `argus/strategies/afternoon_momentum.py` — State machine correctness, all 5 state transitions, consolidation detection math, EOD time stop calculation, edge cases
- `argus/core/config.py` — AfternoonMomentumConfig validation, field ranges
- `tests/strategies/test_afternoon_momentum.py` — Test coverage gaps
- `argus/backtest/vectorbt_afternoon_momentum.py` — Precompute architecture compliance with DEC-149, exit priority correctness
- `tests/backtest/test_vectorbt_afternoon_momentum.py` — Test coverage
- `argus/backtest/config.py` and `walk_forward.py` and `replay_harness.py` — Integration correctness

**Materials needed for review:**
- The Session 5 commit hash
- `git diff main..HEAD --stat` (to see all changed files)
- Run `pytest tests/ -v --tb=short 2>&1 | tail -30` to capture test summary
- Strategy file and test file in full

**Procedure:**
1. Start a new Claude.ai conversation in the ARGUS project
2. Paste the Review A handoff brief (Section 4 below)
3. Claude reviews all files, provides feedback organized by severity (Critical/Major/Minor)
4. Steven captures feedback, pastes into Session 10

### Review B — After Session 9 (Integration + UX + Docs)

**Timing:** After Sessions 6–9 are complete and committed.

**What to review:**
- `argus/main.py` — Correct registration, import paths, health component
- `tests/test_integration_sprint20.py` — Scenario coverage, four-strategy flows
- `argus/api/dev_state.py` — Four-strategy mock data completeness
- UI changes — Badge additions, strategy list
- `docs/strategies/STRATEGY_AFTERNOON_MOMENTUM.md` — Completeness, accuracy vs implementation
- `config/strategies/afternoon_momentum.yaml` — Matches config class

**Materials needed:**
- The Session 9 commit hash
- Full test suite output
- Dev mode screenshot check: `python -m argus.api --dev` and check /api/v1/strategies, /api/v1/orchestrator/status

**Procedure:**
1. Start a new Claude.ai conversation in the ARGUS project
2. Paste the Review B handoff brief
3. Claude reviews all files
4. Steven captures feedback → Session 10

### When to Update Docs

**During Sprint:** Don't update docs until after both code reviews pass. Doc updates happen in Session 11 after all fixes.

**Exception:** If a design decision changes during implementation (e.g., Claude Code discovers consolidation detection needs a different approach), flag it immediately so I can update the decision log.

---

## 4. Code Review Handoff Briefs

### Review A Handoff Brief

```
# Sprint 20 Code Review A — Core Strategy + Backtesting

I'm building ARGUS, an automated multi-strategy day trading ecosystem. Sprint 20 adds the fourth strategy: Afternoon Momentum (consolidation breakout, 2:00–3:30 PM ET). Sessions 0–5 are complete. I need a thorough code review before proceeding to integration.

**Repo:** https://github.com/stevengizzi/argus.git

**Before reviewing, read these files for context:**
1. `CLAUDE.md` — Current project state
2. `docs/strategies/STRATEGY_VWAP_RECLAIM.md` — The pattern Afternoon Momentum follows

**Files to review (the Sprint 20 work):**
1. `argus/strategies/afternoon_momentum.py` — The strategy class (PRIORITY — this is the core deliverable)
2. `argus/core/config.py` — AfternoonMomentumConfig (search for "AfternoonMomentum")
3. `config/strategies/afternoon_momentum.yaml` — Default config
4. `tests/strategies/test_afternoon_momentum.py` — Unit tests
5. `argus/backtest/vectorbt_afternoon_momentum.py` — VectorBT parameter sweep
6. `tests/backtest/test_vectorbt_afternoon_momentum.py` — Sweep tests
7. `argus/backtest/config.py` — StrategyType addition
8. `argus/backtest/walk_forward.py` — Afternoon momentum dispatch
9. `argus/backtest/replay_harness.py` — Strategy factory addition

**Design decisions guiding this review (from sprint spec):**
- DEC-152: Standalone from BaseStrategy (like VWAP Reclaim, DEC-136)
- DEC-153: Consolidation = high/low channel of 12:00–2:00 PM bars + ATR filter
- DEC-155: 5-state machine — WATCHING → ACCUMULATING → CONSOLIDATED → ENTERED/REJECTED
- DEC-156: 8 simultaneous entry conditions
- DEC-157: Stop below consolidation low. T1=1.0R, T2=2.0R. Dynamic time stop: min(60min, seconds until 3:45 PM)
- DEC-159: EOD handling — force close 3:45 PM, time stop compressed for late entries

**Review checklist:**
1. State machine: Are all 5 state transitions correct? Any unreachable states? Any missing transitions?
2. Consolidation detection: Is the midday_range / ATR calculation correct? Does CONSOLIDATED continue updating the range? Does widening past max_consolidation_atr_ratio transition to REJECTED?
3. EOD time stop: Is `_compute_effective_time_stop()` correct for entries at 2:00, 3:00, 3:25 PM?
4. VectorBT architecture: Does it follow the precompute+vectorize mandate (DEC-149)? Is the precompute truly parameter-independent? Does the exit priority match worst-case-for-longs?
5. Test coverage: Are there gaps? Untested edge cases?
6. Config validation: Do Pydantic validators catch invalid parameter combinations?
7. Code quality: Consistent with VWAP Reclaim style? Type hints? Logging? Docstrings?

Please organize feedback as:
- **Critical** (must fix before proceeding): Logic bugs, incorrect math, missing safety checks
- **Major** (should fix this sprint): Missing tests, unclear logic, inconsistencies with other strategies
- **Minor** (fix if time permits): Style, naming, documentation gaps

Current test count before this sprint: 1410 pytest + 40 Vitest.
```

---

### Review B Handoff Brief

```
# Sprint 20 Code Review B — Integration + UX + Docs

Continuing Sprint 20 review. Sessions 6–9 complete. This review covers system integration, dev mode mock data, and documentation.

**Repo:** https://github.com/stevengizzi/argus.git

**Files to review:**
1. `argus/main.py` — Strategy creation, registration, health monitoring (search for "afternoon")
2. `tests/test_integration_sprint20.py` — Four-strategy integration tests
3. `argus/api/dev_state.py` — Mock data for fourth strategy (search for "afternoon")
4. `argus/ui/src/` — Any files with "afternoon" or badge updates
5. `docs/strategies/STRATEGY_AFTERNOON_MOMENTUM.md` — Strategy spec sheet
6. `config/strategies/afternoon_momentum.yaml` — Config file

**Context files (from Review A, already reviewed):**
- `argus/strategies/afternoon_momentum.py`
- `argus/core/config.py`

**Review checklist:**
1. main.py integration: Correct import paths? Strategy created only if YAML exists? Registered with Orchestrator? Health component added? Same pattern as VWAP Reclaim?
2. Integration tests: Do they cover the full-day sequential flow? EOD edge cases? Four-strategy allocation? Regime-based activation? Cross-strategy risk?
3. Dev mode: Does mock data include afternoon momentum in ALL relevant sections? (positions, trades, allocations, strategy cards, orchestrator decisions, session summary, watchlist)? Are the 4 allocation percentages correct (20/20/20/20)?
4. Strategy spec sheet: Every field filled in? No TBD? Accurate to the implementation? State machine diagram present?
5. Config YAML: Validates with AfternoonMomentumConfig? All fields present? Defaults match code?
6. Consistency: Does the spec sheet match the code? Does the config YAML match the config class? Do the mock data strategy IDs match?

Review A feedback was addressed in Session 10 (or will be after this review).

Please organize feedback as Critical/Major/Minor.
```

---

## 5. Doc Updates to Make Now

These are updates to make in the repo BEFORE starting implementation sessions, to keep docs accurate.

### 5a. Decision Log (docs/05_DECISION_LOG.md)

Check the current highest DEC number first. Based on Sprint 19, it should be DEC-151. Add:

```markdown
### DEC-152 | Afternoon Momentum — Standalone from BaseStrategy
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | AfternoonMomentumStrategy inherits from BaseStrategy directly, not from OrbBaseStrategy or any shared consolidation base. |
| **Rationale** | Despite structural similarity to ORB (range → breakout), the range formation is fundamentally different. ORB: predefined time window. Afternoon Momentum: organically formed midday consolidation. Follows VWAP Reclaim precedent (DEC-136). Shared base extracted later if needed (DEF-022 pattern). |
| **Status** | Active |

### DEC-153 | Consolidation Detection — High/Low Channel + ATR Filter
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Consolidation identified by tracking high/low of midday bars (12:00–2:00 PM), confirmed by midday_range / ATR-14 < threshold (default 0.75). |
| **Rationale** | Simple, testable, vectorizable. ATR filter confirms range is genuinely tight vs. just a low-volatility stock. Bollinger Bands require new indicator computation. Moving average convergence too indirect. |
| **Status** | Active |

### DEC-154 | Afternoon Momentum Scanner — Gap Watchlist Reuse
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Afternoon Momentum reuses the same gap scanner criteria as ORB and VWAP Reclaim (min_gap=2%, min_price=$10, max_price=$200, min_volume=1M, min_rvol=2.0). |
| **Rationale** | Gap watchlist identifies institutional-quality stocks with catalysts — natural candidates for midday consolidation and afternoon breakout. Consolidation detection is the second filter. Matches DEC-137 scanner reuse pattern. |
| **Status** | Active |

### DEC-155 | Afternoon Momentum State Machine — 5 States
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | 5-state machine: WATCHING (before 12:00 PM), ACCUMULATING (tracking midday range), CONSOLIDATED (range confirmed tight), ENTERED (position taken, terminal), REJECTED (range too wide, terminal). |
| **Rationale** | ACCUMULATING → CONSOLIDATED split prevents false entries on insufficient data. min_consolidation_bars gate ensures meaningful range measurement. CONSOLIDATED continues updating range, so widening can still reject. Parallels VWAP Reclaim 5-state pattern (DEC-138). |
| **Status** | Active |

### DEC-156 | Afternoon Momentum Entry Conditions — 8 Simultaneous Requirements
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Entry requires ALL: (1) CONSOLIDATED state, (2) time 2:00–3:30 PM, (3) candle close > consolidation_high, (4) volume ≥ multiplier × avg, (5) chase protection, (6) risk > 0, (7) internal risk limits pass, (8) position count limit. |
| **Rationale** | Same comprehensive gating pattern as ORB and VWAP Reclaim. Close-based confirmation (not intra-bar) is consistent across all strategies. |
| **Status** | Active |

### DEC-157 | Afternoon Momentum Stop and Target Design
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Stop below consolidation_low with buffer (0.1%). T1=1.0R (50%), T2=2.0R (50%). Dynamic time stop: min(max_hold_minutes, seconds_until_3:45_PM). |
| **Rationale** | Same T1/T2 pattern proven across three strategies. Dynamic time stop handles EOD proximity — a 3:25 PM entry gets 20-min time stop, not 60-min. Trailing stop deferred (DEC-158). |
| **Status** | Active |

### DEC-158 | Trailing Stop — Deferred to V2
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | No trailing stop mechanism in V1 of Afternoon Momentum. |
| **Rationale** | Trailing stops touch Order Manager, Risk Manager, backtesting, and VectorBT sweep architecture — cross-cutting complexity. T1/T2 fixed targets are proven. If walk-forward shows afternoon moves routinely exceed T2, trailing stop becomes a future sprint item. |
| **Status** | Active |

### DEC-159 | Afternoon Momentum EOD Handling
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Last entry 3:30 PM. Force close 3:45 PM. Time stop at signal creation = min(max_hold_minutes × 60, seconds_until_3:45_PM). Order Manager EOD flatten is safety net. |
| **Rationale** | Dynamic time stop calculation ensures no position is targeted for closure after the hard cutoff. Earliest-exit-wins logic in Order Manager already handles overlap between time stop and EOD flatten. |
| **Status** | Active |

### DEC-160 | Cross-Strategy Interaction — ALLOW_ALL, Time-Separated
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Same ALLOW_ALL duplicate stock policy (DEC-121) for Afternoon Momentum. No additional cross-strategy restrictions. |
| **Rationale** | Time windows are well-separated: ORB/Scalp done by ~10:15 AM, VWAP Reclaim done by ~12:30 PM, Afternoon Momentum starts at 2:00 PM. Cross-strategy collisions effectively impossible. 5% max_single_stock_pct cap remains as safety net. |
| **Status** | Active |

### DEC-161 | Databento Activation — Deferred to Sprint 21
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Databento subscription not activated for Sprint 20. Defer to Sprint 21 (analytics sprint). |
| **Rationale** | Saves $199/month. Sprint 20 uses Alpaca Parquet data like all other strategies. All results provisional per DEC-132. Databento most valuable when four strategies are built AND analytics toolkit is ready for serious validation. Amends DEC-143. |
| **Status** | Active |
```

### 5b. Risk Register (docs/06_RISK_REGISTER.md)

Check current highest RSK number. Add:

```markdown
### RSK-030 | Low Afternoon Trade Counts in Alpaca IEX Data
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-02-26 |
| **Category** | Data Quality |
| **Description** | Afternoon Momentum consolidation detection and breakout confirmation are volume-sensitive. Alpaca's IEX data captures only ~2-3% of market volume (DEC-081). VectorBT sweep may produce very few qualifying trades, making statistical analysis unreliable. |
| **Likelihood** | High |
| **Impact** | Medium — sweep results are directional guidance only, not statistically validated. |
| **Mitigation** | All results provisional per DEC-132. True validation requires Databento exchange-direct data. Low trade counts don't invalidate the strategy thesis — they indicate data limitations. |
| **Status** | Open |
| **Owner** | Steven |

### RSK-031 | EOD Time Stop Compression for Late Afternoon Entries
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-02-26 |
| **Category** | Strategy Risk |
| **Description** | Entries after 3:15 PM have ≤30 minutes effective hold time due to 3:45 PM force close. If the strategy consistently enters late, most exits will be time stops rather than targets, degrading profitability. |
| **Likelihood** | Medium |
| **Impact** | Low — time stop exits at close price, not stop price. Late entries still capture the power hour move direction. |
| **Mitigation** | Monitor time-of-entry distribution in sweep results. If >60% of entries occur after 3:15 PM, consider tightening latest_entry to 3:15 PM. |
| **Status** | Open |
| **Owner** | Steven |
```

### 5c. Sprint Plan (docs/10_PHASE3_SPRINT_PLAN.md)

No changes needed now — Sprint 20 is already in the queue. It gets moved to "completed" in Session 11 after all work is done.

### 5d. Project Knowledge (02_PROJECT_KNOWLEDGE.md)

No changes needed now — updated in Session 11 after sprint completes. But after Sprint 20, you'll need to sync this file to the Claude.ai project instructions.

### 5e. Deferred Items

Add to CLAUDE.md under "Deferred Items" (or create the section if it doesn't exist):

```markdown
### DEF-023 | Trailing Stop Mechanism (DEC-158)
- **Trigger:** Walk-forward shows afternoon moves routinely exceed T2 targets
- **Scope:** Order Manager trailing stop logic, Risk Manager awareness, VectorBT sweep support, backtesting infrastructure
- **Earliest Sprint:** Sprint 23+
- **Filed:** Sprint 20

### DEF-024 | Shared Consolidation Base Class
- **Trigger:** A second consolidation-based strategy is designed (e.g., "Midday Range Breakout")
- **Scope:** Extract shared consolidation detection from AfternoonMomentumStrategy into a base class (following OrbBaseStrategy DEC-120 pattern)
- **Earliest Sprint:** When second consolidation strategy is designed
- **Filed:** Sprint 20
```
