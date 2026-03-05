# Sprint 12.5 — IndicatorEngine Extraction (DEF-013)

> **Type:** Pure refactor (no behavioral changes)
> **Target:** ~0.5 day
> **Prerequisite:** Sprint 12 ✅ COMPLETE
> **Unblocks:** Clean foundation for IQFeedDataService (DEF-011) and any future DataService implementations
> **Test baseline:** 658 tests (all must pass unchanged after refactor)

---

## 1. Problem Statement

Indicator computation (VWAP, ATR-14, SMA-9/20/50, RVOL) is duplicated across four DataService implementations:

| DataService | Location | Usage |
|---|---|---|
| `ReplayDataService` | `argus/data/replay_data_service.py` | Autonomous replay from Parquet |
| `BacktestDataService` | `argus/data/backtest_data_service.py` | Step-driven harness replay |
| `AlpacaDataService` | `argus/data/alpaca_data_service.py` | Live Alpaca WebSocket + warm-up |
| `DatabentoDataService` | `argus/data/databento_data_service.py` | Live Databento TCP + warm-up |

DEC-055 mandated shared logic. Sprint 12 deduplicated the warm-up path *within* DatabentoDataService, but cross-service extraction remains. Each implementation currently maintains its own:
- Per-symbol indicator state (cumulative VWAP accumulators, rolling windows for ATR/SMA, RVOL baselines)
- Indicator computation logic (identical math, copy-pasted)
- Daily reset logic (VWAP and RVOL reset at day boundary; ATR/SMA carry over)
- IndicatorEvent construction and publication

This triplication (quadruplication, now) creates maintenance burden and risks divergence.

---

## 2. Solution: `IndicatorEngine`

Create `argus/data/indicator_engine.py` — a stateful, per-symbol indicator computation engine that all DataService implementations delegate to.

### 2.1 Design Principles

1. **No Event Bus dependency.** The engine computes values and returns them. The DataService is responsible for publishing IndicatorEvents. This keeps the engine testable in isolation and usable in contexts that don't have an Event Bus (e.g., future CLI tools).

2. **One engine instance per symbol.** Each DataService creates `IndicatorEngine` instances keyed by symbol. The engine maintains all rolling state internally.

3. **Identical math.** The extraction must preserve the exact computation from the existing implementations. Any divergence is a bug. Existing tests are the safety net.

4. **Daily lifecycle awareness.** The engine exposes `reset_daily()` for VWAP/RVOL resets. ATR and SMA state carries over across days (rolling windows). The *caller* decides when to call reset — the engine doesn't know about market hours or calendars.

### 2.2 Class Interface

```python
# argus/data/indicator_engine.py

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class IndicatorValues:
    """Computed indicator values for a single bar update.
    
    None means the indicator doesn't have enough data yet
    (e.g., SMA-50 before 50 bars).
    """
    vwap: float | None = None
    atr_14: float | None = None
    sma_9: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    rvol: float | None = None

    def as_dict(self) -> dict[str, float | None]:
        """Return as {indicator_name: value} dict for cache/event iteration."""
        return {
            "vwap": self.vwap,
            "atr_14": self.atr_14,
            "sma_9": self.sma_9,
            "sma_20": self.sma_20,
            "sma_50": self.sma_50,
            "rvol": self.rvol,
        }


class IndicatorEngine:
    """Stateful indicator computation engine for a single symbol.
    
    Maintains rolling state for all V1 indicators:
    - VWAP: Cumulative typical_price * volume / cumulative volume (daily reset)
    - ATR(14): Wilder's smoothing (exponential) of True Range
    - SMA(9/20/50): Simple moving averages of close prices
    - RVOL: Relative volume vs. rolling baseline (daily reset)
    
    Usage:
        engine = IndicatorEngine(symbol="AAPL")
        values = engine.update(open, high, low, close, volume, timestamp)
        # values.vwap, values.atr_14, etc.
        
        # At day boundary:
        engine.reset_daily()
    
    Thread safety: NOT thread-safe. Each DataService should own its
    own engine instances and call them from a single thread/task.
    """
    
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        
        # --- VWAP state (daily reset) ---
        self._vwap_cum_tp_vol: float = 0.0  # cumulative(typical_price * volume)
        self._vwap_cum_vol: float = 0.0     # cumulative(volume)
        
        # --- ATR(14) state (carries across days) ---
        self._atr_period: int = 14
        self._atr_value: float | None = None
        self._atr_tr_history: deque[float] = deque(maxlen=14)
        self._prev_close: float | None = None
        
        # --- SMA state (carries across days) ---
        self._close_history: deque[float] = deque(maxlen=50)  # longest SMA window
        
        # --- RVOL state (daily reset) ---
        self._rvol_cum_volume: int = 0
        self._rvol_bar_count: int = 0
        self._rvol_baseline_avg_volume: float | None = None
        # Rolling daily volume history for baseline computation
        self._rvol_daily_volumes: deque[float] = deque(maxlen=20)
        self._current_date: date | None = None
        
        # --- Bar count (for diagnostics) ---
        self._total_bars: int = 0
    
    def update(
        self,
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        timestamp_date: date | None = None,
    ) -> IndicatorValues:
        """Process a new 1-minute bar and return updated indicator values.
        
        Args:
            open_: Bar open price
            high: Bar high price
            low: Bar low price
            close: Bar close price
            volume: Bar volume
            timestamp_date: Date of this bar. Used for automatic daily reset
                detection. If None, caller must manage reset_daily() manually.
        
        Returns:
            IndicatorValues with current values (None if insufficient data).
        """
        # Auto-detect day boundary if timestamp_date provided
        if timestamp_date is not None and self._current_date is not None:
            if timestamp_date != self._current_date:
                self._do_daily_reset()
        if timestamp_date is not None:
            self._current_date = timestamp_date
        
        self._total_bars += 1
        
        # --- VWAP ---
        vwap = self._update_vwap(high, low, close, volume)
        
        # --- ATR(14) ---
        atr_14 = self._update_atr(high, low, close)
        
        # --- SMAs ---
        self._close_history.append(close)
        sma_9 = self._compute_sma(9)
        sma_20 = self._compute_sma(20)
        sma_50 = self._compute_sma(50)
        
        # --- RVOL ---
        rvol = self._update_rvol(volume)
        
        # Update prev_close for next bar's TR calculation
        self._prev_close = close
        
        return IndicatorValues(
            vwap=vwap,
            atr_14=atr_14,
            sma_9=sma_9,
            sma_20=sma_20,
            sma_50=sma_50,
            rvol=rvol,
        )
    
    def reset_daily(self) -> None:
        """Reset daily-scoped indicators. Call at market open / day boundary.
        
        Resets: VWAP accumulators, RVOL baseline + cumulative
        Preserves: ATR (rolling), SMA (rolling), prev_close
        """
        self._do_daily_reset()
    
    def _do_daily_reset(self) -> None:
        """Internal daily reset implementation."""
        # Archive today's average volume for RVOL baseline
        if self._rvol_bar_count > 0:
            avg_vol = self._rvol_cum_volume / self._rvol_bar_count
            self._rvol_daily_volumes.append(avg_vol)
            if len(self._rvol_daily_volumes) >= 5:
                self._rvol_baseline_avg_volume = (
                    sum(self._rvol_daily_volumes) / len(self._rvol_daily_volumes)
                )
        
        # Reset VWAP
        self._vwap_cum_tp_vol = 0.0
        self._vwap_cum_vol = 0.0
        
        # Reset RVOL cumulative counters
        self._rvol_cum_volume = 0
        self._rvol_bar_count = 0
    
    def _update_vwap(
        self, high: float, low: float, close: float, volume: int
    ) -> float | None:
        """Cumulative VWAP: sum(TP * vol) / sum(vol). TP = (H+L+C)/3."""
        if volume <= 0:
            # Zero-volume bar — return current VWAP without updating
            if self._vwap_cum_vol > 0:
                return self._vwap_cum_tp_vol / self._vwap_cum_vol
            return None
        
        typical_price = (high + low + close) / 3.0
        self._vwap_cum_tp_vol += typical_price * volume
        self._vwap_cum_vol += volume
        return self._vwap_cum_tp_vol / self._vwap_cum_vol
    
    def _update_atr(self, high: float, low: float, close: float) -> float | None:
        """ATR(14) using Wilder's smoothing.
        
        True Range = max(H-L, |H-prevC|, |L-prevC|).
        First ATR = simple average of first 14 TRs.
        Subsequent: ATR = (prev_ATR * 13 + TR) / 14 (Wilder's smoothing).
        """
        if self._prev_close is not None:
            tr = max(
                high - low,
                abs(high - self._prev_close),
                abs(low - self._prev_close),
            )
        else:
            tr = high - low
        
        self._atr_tr_history.append(tr)
        
        if len(self._atr_tr_history) < self._atr_period:
            return None
        
        if self._atr_value is None:
            # First ATR: simple average
            self._atr_value = sum(self._atr_tr_history) / self._atr_period
        else:
            # Wilder's smoothing
            self._atr_value = (
                self._atr_value * (self._atr_period - 1) + tr
            ) / self._atr_period
        
        return self._atr_value
    
    def _compute_sma(self, period: int) -> float | None:
        """SMA of close prices over `period` bars."""
        if len(self._close_history) < period:
            return None
        # Use the last `period` values from the deque
        recent = list(self._close_history)[-period:]
        return sum(recent) / period
    
    def _update_rvol(self, volume: int) -> float | None:
        """Relative Volume: cumulative avg volume today / baseline avg volume."""
        self._rvol_cum_volume += volume
        self._rvol_bar_count += 1
        
        if self._rvol_baseline_avg_volume is None or self._rvol_baseline_avg_volume <= 0:
            return None
        
        avg_vol_today = self._rvol_cum_volume / self._rvol_bar_count
        return avg_vol_today / self._rvol_baseline_avg_volume
    
    @property
    def bar_count(self) -> int:
        """Total bars processed by this engine."""
        return self._total_bars
    
    def get_current_values(self) -> IndicatorValues:
        """Return the most recently computed indicator values.
        
        Useful for warm-up — after feeding historical bars, the caller
        can read the current state without needing to process another bar.
        """
        vwap = None
        if self._vwap_cum_vol > 0:
            vwap = self._vwap_cum_tp_vol / self._vwap_cum_vol
        
        return IndicatorValues(
            vwap=vwap,
            atr_14=self._atr_value,
            sma_9=self._compute_sma(9),
            sma_20=self._compute_sma(20),
            sma_50=self._compute_sma(50),
            rvol=(
                (self._rvol_cum_volume / self._rvol_bar_count / self._rvol_baseline_avg_volume)
                if self._rvol_bar_count > 0 and self._rvol_baseline_avg_volume and self._rvol_baseline_avg_volume > 0
                else None
            ),
        )
```

### 2.3 Indicator Computation Details

These must match the existing implementations exactly. Claude Code should verify against the current code.

| Indicator | Formula | Window | Daily Reset? | Returns None Until |
|---|---|---|---|---|
| VWAP | `cum(TP * vol) / cum(vol)`, TP = (H+L+C)/3 | Cumulative within day | ✅ Yes | First bar with volume > 0 |
| ATR(14) | Wilder's smoothing: `(prev * 13 + TR) / 14` | Rolling 14 bars | ❌ No (carries over) | 14 bars processed |
| SMA(9) | Simple average of last 9 closes | Rolling 9 bars | ❌ No (carries over) | 9 bars processed |
| SMA(20) | Simple average of last 20 closes | Rolling 20 bars | ❌ No (carries over) | 20 bars processed |
| SMA(50) | Simple average of last 50 closes | Rolling 50 bars | ❌ No (carries over) | 50 bars processed |
| RVOL | `avg_vol_today / baseline_avg_vol` | Cumulative today / 20-day baseline | ✅ Yes (cumulative) | 5+ days of data for baseline |

**Critical: ATR uses Wilder's smoothing, NOT a simple moving average of TR.** This was documented in DEC-074 as a known divergence point between VectorBT (daily-bar ATR) and production (1-minute-bar ATR with Wilder smoothing). The IndicatorEngine preserves the production behavior.

---

## 3. Refactor Plan

### 3.1 Step 1: Create `IndicatorEngine` and `IndicatorValues`

**File:** `argus/data/indicator_engine.py`

Create the `IndicatorEngine` class as specified above. Before writing new code, read the existing indicator logic in `ReplayDataService` to ensure the IndicatorEngine's math matches exactly.

### 3.2 Step 2: Create comprehensive unit tests

**File:** `tests/data/test_indicator_engine.py`

Test the engine in isolation:

```
test_vwap_basic_computation
test_vwap_zero_volume_bar_preserves_value
test_vwap_resets_on_daily_reset
test_atr_returns_none_until_14_bars
test_atr_wilder_smoothing_correctness
test_atr_carries_across_daily_reset
test_sma_9_basic
test_sma_20_basic
test_sma_50_returns_none_until_50_bars
test_sma_carries_across_daily_reset
test_rvol_returns_none_without_baseline
test_rvol_builds_baseline_after_5_days
test_rvol_resets_cumulative_on_daily_reset
test_update_returns_indicator_values
test_as_dict_format
test_auto_daily_reset_on_date_change
test_get_current_values_after_warmup
test_prev_close_used_for_true_range
```

These tests verify the engine independently of any DataService. They form the canonical specification for indicator behavior.

### 3.3 Step 3: Refactor `BacktestDataService`

**Why first:** BacktestDataService is the simplest consumer — `feed_bar()` calls indicator logic directly. Lowest risk.

**Changes:**
- Import `IndicatorEngine`
- Replace `self._indicator_state` dict with `dict[str, IndicatorEngine]`
- In `feed_bar()`: call `engine.update(...)` instead of inline computation
- In `reset_daily_state()`: call `engine.reset_daily()` for all engines
- In `get_indicator()`: read from engine's cached values (or keep the existing `_indicator_cache` pattern, populated from `IndicatorValues.as_dict()`)
- Remove all inline indicator computation code

**Validation:** Run all backtest-related tests. No changes to test code — only internal refactoring.

### 3.4 Step 4: Refactor `ReplayDataService`

**Changes:**
- Same pattern as BacktestDataService
- The `_update_indicators()` / `_compute_indicators()` method becomes a thin wrapper that calls `engine.update()` and publishes the resulting IndicatorEvents
- Day-boundary detection (date change in Parquet data) triggers `engine.reset_daily()`

**Validation:** Run all replay/harness tests. Cross-validation tests must still pass.

### 3.5 Step 5: Refactor `AlpacaDataService`

**Changes:**
- Replace inline indicator state with `dict[str, IndicatorEngine]`
- `_on_bar()` handler: call `engine.update()`, publish IndicatorEvents from result
- Warm-up path: feed historical bars through `engine.update()` without publishing events (same behavior as today, just delegated)
- VWAP daily reset: already triggered by clock/market-open detection — delegate to `engine.reset_daily()`

**Validation:** Run all Alpaca-related tests.

### 3.6 Step 6: Refactor `DatabentoDataService`

**Changes:**
- Replace inline indicator state with `dict[str, IndicatorEngine]`
- `_process_ohlcv_bar()` (or equivalent): call `engine.update()`, publish IndicatorEvents
- Warm-up path: same delegation pattern as AlpacaDataService
- Day-boundary detection: delegate to `engine.reset_daily()`

**Validation:** Run all Databento-related tests.

### 3.7 Step 7: Remove dead indicator code

After all four DataServices are refactored:
- Delete any standalone indicator helper functions that are now unused
- Verify no imports reference the old code
- Final `ruff` clean

---

## 4. What This Sprint Does NOT Include

- **New indicators.** This is extraction only. No new indicators are added.
- **IndicatorEvent changes.** The event format and publishing behavior remain identical.
- **DataService ABC changes.** The `get_indicator()` interface is unchanged.
- **Performance optimization.** The SMA computation uses list slicing from a deque, which is fine for 50-element windows at 1-bar-per-minute throughput. Optimization deferred.
- **IndicatorEngine as a standalone "service."** It's a utility class owned by DataServices, not an Event Bus participant. This keeps the architecture clean per DEC-038 ("indicators computed inside Data Service").

---

## 5. Implementation Notes for Claude Code

### 5.1 Read Before Writing

Before implementing `IndicatorEngine`, Claude Code MUST read the existing indicator logic in **all four** DataService implementations to understand:
1. Exact state variables used (naming may differ across implementations)
2. Edge cases already handled (zero-volume bars, None returns, first-bar behavior)
3. How daily reset is currently triggered in each implementation
4. Any implementation-specific quirks that developed over sprints

The goal is to extract what exists, not reinvent.

### 5.2 Validation Strategy

**The existing 658 tests are the safety net.** This refactor should produce zero test changes and zero behavioral changes. If any test breaks, the IndicatorEngine has diverged from the existing logic.

Run the full test suite after each DataService refactor step (not just at the end). This catches divergence early and makes debugging trivial.

### 5.3 Common Pitfalls

| Pitfall | Mitigation |
|---|---|
| VWAP doesn't reset on day boundary | Ensure the DataService calls `engine.reset_daily()` at the same point it currently resets VWAP state |
| ATR uses wrong smoothing | Verify Wilder's: `(prev * 13 + TR) / 14`, NOT SMA of TR window |
| SMA returns value too early | Check `len(history) < period` guard matches existing code |
| RVOL baseline never builds | Ensure `_rvol_daily_volumes` is populated during daily reset, not cleared |
| Warm-up feeds bars but triggers day-reset | The auto-reset on date change is helpful but may fire during warm-up when feeding multiple days of historical data. This is correct behavior — warm-up data spans multiple days and VWAP should reset between them |
| `get_indicator()` returns stale values | Ensure `_indicator_cache` is updated from `IndicatorValues.as_dict()` after every `engine.update()` call |

### 5.4 `timestamp_date` Parameter

The `update()` method accepts an optional `timestamp_date` for automatic day-boundary detection. This is a convenience:
- **BacktestDataService / ReplayDataService:** Pass the bar's date. The engine auto-resets.
- **AlpacaDataService / DatabentoDataService:** Can either pass the date OR continue using their existing market-open detection and call `reset_daily()` manually. Either approach is fine.

The important thing is that the reset happens at the same moment it does today.

---

## 6. Decision Needed: Warm-up Helper

**Question:** Should `IndicatorEngine` include a convenience method for warm-up?

```python
def warm_up(self, bars: pd.DataFrame) -> None:
    """Feed historical bars to seed indicator state.
    
    Iterates through DataFrame rows (expected columns: open, high, low, 
    close, volume, timestamp) and calls update() for each.
    """
    for _, row in bars.iterrows():
        self.update(
            open_=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=int(row["volume"]),
            timestamp_date=row["timestamp"].date() if "timestamp" in row else None,
        )
```

**Recommendation: Yes.** Both AlpacaDataService and DatabentoDataService have warm-up paths that fetch historical bars as a DataFrame and loop through them. A `warm_up(df)` convenience method eliminates that boilerplate too. It's a trivial wrapper over `update()` but improves readability in the DataService implementations.

---

## 7. Success Criteria

- [ ] `argus/data/indicator_engine.py` exists with `IndicatorEngine` and `IndicatorValues` classes
- [ ] `tests/data/test_indicator_engine.py` with 15+ focused unit tests
- [ ] All four DataServices refactored to delegate to `IndicatorEngine`
- [ ] All inline indicator computation code removed from DataServices
- [ ] All 658 existing tests pass with zero modifications
- [ ] Ruff fully clean
- [ ] No behavioral changes to any DataService's external behavior

---

## 8. Docs Update Targets

After sprint completion, update:

| Document | Change |
|---|---|
| `05_DECISION_LOG.md` | DEC-092: IndicatorEngine extraction (reference DEF-013 resolution) |
| `02_PROJECT_KNOWLEDGE.md` | Update Sprint 12.5 status to COMPLETE. Update test count. Strike DEF-013 from deferred items. |
| `03_ARCHITECTURE.md` | Add note to DataService section: "Indicator computation delegated to `IndicatorEngine` (Sprint 12.5, DEF-013 resolved)." |
| `10_PHASE3_SPRINT_PLAN.md` | Move Sprint 12.5 to completed table with deliverables. |
| `CLAUDE.md` | Update current state. Add IndicatorEngine to components list. Strike DEF-013. |

---

*End of Sprint 12.5 Spec*
