# ARGUS — Sprint 7 Implementation Spec

> **Sprint 7 Scope:** Replay Harness + Backtest Metrics (Phase 2, Backtesting Validation)
> **Date:** February 16, 2026
> **Prerequisite:** Sprint 6 complete (417 tests passing, ruff clean). Historical data in `data/historical/1m/`.
> **Estimated tests:** ~25–30 new tests
> **Target total:** ~445–450 tests

---

## Context

Read these files before starting:
- `CLAUDE.md` — project rules, code style, architectural constraints
- `docs/09_PHASE2_SPRINT_PLAN.md` — Phase 2 plan with Sprint 7 scope
- `argus/data/replay_data_service.py` — existing ReplayDataService (indicator computation logic to reference)
- `argus/strategies/orb_breakout.py` — production ORB strategy
- `argus/execution/simulated_broker.py` — SimulatedBroker with `simulate_price_update()`
- `argus/execution/order_manager.py` — production Order Manager (tick-driven exits)
- `argus/core/risk_manager.py` — production Risk Manager
- `argus/core/clock.py` — FixedClock with `set()` and `advance()`
- `argus/core/event_bus.py` — production EventBus
- `argus/analytics/trade_logger.py` — TradeLogger for persistence
- `argus/backtest/data_fetcher.py` — Sprint 6 DataFetcher (for Parquet file paths)
- `argus/backtest/manifest.py` — Manifest for data inventory
- `config/order_manager.yaml` — Order Manager config
- `config/risk_limits.yaml` — Risk Manager config
- `config/strategies/orb_breakout.yaml` — ORB config

Sprint 7 builds the Replay Harness — the highest-fidelity backtesting tool in Argus. It feeds historical Parquet data through the **actual production pipeline**: real EventBus, real OrbBreakout strategy, real RiskManager, real OrderManager, and real SimulatedBroker — all with FixedClock injection so components see simulated time.

This is the sprint where we prove that the code we wrote in Phase 1 actually works on historical data.

---

## Micro-Decisions (All Resolved)

| ID | Decision | Choice |
|----|----------|--------|
| MD-7-1 | Scanner simulation | **(a) Compute gap from prev close → current day's 9:30 open.** Apply same gap/price criteria from scanner config. Fall back to feeding all symbols if gap filter produces zero candidates for a day. Log which mode was used. |
| MD-7-2 | Order Manager in replay | **(a) Synthetic ticks from bars.** 4 ticks per bar: Open → Low → High → Close (bullish) or Open → High → Low → Close (bearish). Tests actual Order Manager code. |
| MD-7-3 | Opening range in replay | **No special handling.** Strategy's `on_candle()` accumulates OR bars naturally when fed in timestamp order. |
| MD-7-4 | Slippage model | **(a) Fixed $0.01/share.** Configured via `BacktestConfig.slippage_per_share`. Simple, conservative, configurable. |
| MD-7-5 | Backtest database naming | **(b) `data/backtest_runs/{strategy}_{start}_{end}_{timestamp}.db`.** Example: `orb_20250601_20251231_20260216_143022.db`. Directory gitignored. |

### Additional Micro-Decisions (Emerged During Spec Writing)

| ID | Decision | Choice |
|----|----------|--------|
| MD-7-6 | DataService for harness | **New `BacktestDataService`** that implements the DataService ABC but is driven step-by-step by the harness (see design below). Reuses indicator computation logic from ReplayDataService. Does NOT reuse ReplayDataService directly — harness needs fine-grained control over clock advancement and event ordering. |
| MD-7-7 | SimulatedBroker ↔ EventBus bridge | **Harness publishes OrderFilledEvents** after calling `simulate_price_update()`. SimulatedBroker itself is not modified. The harness is the glue layer. See "Event Flow in Replay" section. |
| MD-7-8 | Pre-market data gap | **Deferred.** IEX feed (free tier) only provides regular hours data. Gap computed from prev day close → current day open bar. Pre-market volume filter not replicated. Acceptable for V1 — our 28-symbol universe is already curated for liquidity. Track as DEF-007. |

---

## Adaptation Notes for Claude Code

The code in this spec is a **detailed guide**, not copy-paste-ready. Claude Code must:

1. **Check actual imports, class names, and method signatures** in the repo. The spec references components from Sprints 1-6 — verify exact signatures before coding.
2. **Verify Order Manager's fill handling.** The spec assumes the Order Manager can handle both synchronous fills (from `place_order()` returning FILLED) and asynchronous fills (via `OrderFilledEvent`). Check the actual implementation and adapt the harness bridge accordingly. See "Critical Integration Point" below.
3. **Verify SimulatedBroker's `simulate_price_update()` return type.** The spec assumes it returns `list[OrderResult]`. Confirm.
4. **Check indicator computation in ReplayDataService.** The BacktestDataService reuses the same indicator logic. Extract or reference the existing implementation — do NOT reimplement from scratch.
5. **Match existing code patterns** for logging, error handling, type hints, and docstrings (Google style).
6. **Run `ruff check`** after implementation and fix any linting issues.
7. **Run the full test suite** (`pytest`) to ensure no regressions against the existing 417 tests.

---

## Architecture Overview

### Event Flow in Replay Mode

```
For each trading day:
  1. Reset all components (strategy, risk manager, order manager daily state)
  2. Run scanner simulation → compute watchlist from gap data
  3. Set strategy's watchlist

  For each 1-minute bar (chronological across all symbols):
    4. Advance FixedClock to bar's timestamp
    5. BacktestDataService.feed_bar(symbol, bar)
       → Updates indicator state
       → Publishes CandleEvent to EventBus
       → Publishes IndicatorEvents to EventBus
    6. Strategy's on_candle() fires (subscribed to CandleEvent)
       → May emit SignalEvent
    7. Risk Manager's on_signal() evaluates
       → May emit OrderApprovedEvent
    8. Order Manager's on_approved() places orders on SimulatedBroker
       → SimulatedBroker fills entry immediately (market order)
       → Order Manager handles fill, places stop + T1 orders as PendingBracketOrders
    9. Synthesize 4 ticks from bar OHLC
       For each synthetic tick:
         a. BacktestDataService publishes TickEvent
         b. Harness calls broker.simulate_price_update(symbol, tick_price)
            → SimulatedBroker checks pending brackets (stops, targets)
            → Returns list of OrderResults for triggered fills
         c. Harness publishes OrderFilledEvent for each triggered fill
         d. Order Manager's on_fill() processes (stop-to-breakeven, position close, etc.)
    10. Allow EventBus to drain (asyncio.sleep(0) or event loop yield)

  After last bar of day:
    11. Advance clock to EOD flatten time (15:50 ET)
    12. Trigger Order Manager's eod_flatten()
    13. Log daily summary (trades, P&L, positions closed)

After all trading days:
  14. Compute backtest metrics from trade log database
  15. Print summary to console
```

### Critical Integration Point: Order Manager + SimulatedBroker

The production Order Manager was designed for AlpacaBroker (async fills via WebSocket). With SimulatedBroker (sync fills), there's a potential mismatch. **Claude Code must verify the actual implementation handles these cases:**

1. **Entry orders:** When `on_approved()` calls `broker.place_order()`, SimulatedBroker returns `OrderResult(status=FILLED)` immediately. The Order Manager must detect this and process the fill inline (create ManagedPosition, place stop + T1 orders) rather than waiting for an `OrderFilledEvent`. Check if the current implementation does this, or if the harness needs to publish an `OrderFilledEvent` to trigger `on_fill()`.

2. **Stop/target orders:** These are registered as `PendingBracketOrder` in SimulatedBroker. They trigger when `simulate_price_update()` is called. The harness calls this during tick synthesis and publishes `OrderFilledEvent` for each triggered fill. The Order Manager's `on_fill()` then processes the fill (stop-to-breakeven, position close, etc.).

3. **Event ordering:** After publishing events, yield to the event loop (`await asyncio.sleep(0)`) to ensure subscribers process them before the next bar. This is critical — if events queue up without being processed, the strategy might see stale state.

**If the Order Manager's `on_approved()` does NOT handle inline fills from place_order():** The harness needs to publish an `OrderFilledEvent` for entry fills too. Add this to the bridge logic.

---

## Components to Implement

### Component 1: BacktestConfig (`argus/backtest/config.py`)

Add to the existing `argus/backtest/config.py` (which already has `DataFetcherConfig` from Sprint 6).

```python
class BacktestConfig(BaseModel):
    """Configuration for the Replay Harness."""
    
    # Data
    data_dir: Path = Path("data/historical/1m")
    output_dir: Path = Path("data/backtest_runs")
    
    # Date range
    start_date: date  # First trading day to include
    end_date: date    # Last trading day to include
    
    # Strategy
    strategy_id: str = "orb_breakout"
    
    # Slippage
    slippage_per_share: float = 0.01  # Fixed $0.01/share (MD-7-4)
    
    # SimulatedBroker
    initial_cash: float = 100_000.0
    
    # Scanner simulation
    scanner_min_gap_pct: float = 0.02      # 2% minimum gap
    scanner_min_price: float = 10.0
    scanner_max_price: float = 500.0
    scanner_fallback_all_symbols: bool = True  # Feed all if gap filter finds none
    
    # EOD
    eod_flatten_time: str = "15:50"         # HH:MM in ET
    eod_flatten_timezone: str = "America/New_York"
    
    # Config overrides (applied on top of YAML config)
    # Keys are dot-separated paths: {"orb_breakout.opening_range_minutes": 15}
    config_overrides: dict[str, Any] = {}
```

---

### Component 2: BacktestDataService (`argus/backtest/backtest_data_service.py`)

A DataService implementation that is driven step-by-step by the ReplayHarness. Unlike ReplayDataService (which runs autonomously through all data in `start()`), BacktestDataService exposes a `feed_bar()` method for the harness to push one bar at a time.

**Why not reuse ReplayDataService?** The harness needs fine-grained control over:
- When the clock advances (before each bar)
- The order of events (CandleEvent → IndicatorEvents → synthetic TickEvents)
- Daily lifecycle (reset indicators at day boundary)
- Interleaving bars across multiple symbols in timestamp order

ReplayDataService's `start()` runs through all data at once — it can't be paused for clock advancement or tick synthesis between bars.

```python
"""Backtest data service for the Replay Harness.

Step-by-step DataService that the ReplayHarness controls directly.
Implements the DataService ABC so strategies can call get_indicator()
and get_current_price() as normal.

Indicator computation reuses the same logic as ReplayDataService
(VWAP, ATR(14), SMA(9), SMA(20), SMA(50), RVOL).
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from argus.core.event_bus import EventBus
from argus.core.events import CandleEvent, IndicatorEvent, TickEvent
from argus.data.service import DataService

logger = logging.getLogger(__name__)


class BacktestDataService(DataService):
    """DataService for the Replay Harness. Driven step-by-step.
    
    The harness calls feed_bar() for each 1m bar. This updates indicators,
    publishes CandleEvent and IndicatorEvents to the EventBus, and updates
    the price/indicator caches that strategies query via get_current_price()
    and get_indicator().
    
    The harness calls publish_tick() for each synthetic tick. This publishes
    a TickEvent and updates the price cache.
    
    Args:
        event_bus: EventBus for publishing events.
    """
    
    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        
        # Price cache: symbol → last known price
        self._price_cache: dict[str, float] = {}
        
        # Indicator state per symbol — reuse the same structure as 
        # ReplayDataService's indicator computation.
        # Claude Code: check how ReplayDataService stores indicator state
        # (likely an _indicators dict or IndicatorState dataclass per symbol).
        # Mirror that structure here.
        self._indicator_state: dict[str, ...] = {}  # Exact type TBD — match existing code
        
        # Indicator cache: (symbol, indicator_name) → value
        self._indicator_cache: dict[tuple[str, str], float] = {}
    
    # --- DataService ABC implementation ---
    
    async def start(self, symbols: list[str], timeframes: list[str]) -> None:
        """No-op. The harness drives data through feed_bar()."""
        logger.info(
            "BacktestDataService initialized for %d symbols", len(symbols)
        )
    
    async def stop(self) -> None:
        """No-op. Nothing to clean up."""
        pass
    
    async def get_current_price(self, symbol: str) -> float | None:
        """Return last known price from feed_bar() or publish_tick()."""
        return self._price_cache.get(symbol)
    
    async def get_indicator(self, symbol: str, indicator: str) -> float | None:
        """Return latest indicator value computed during feed_bar()."""
        return self._indicator_cache.get((symbol, indicator))
    
    async def get_historical_candles(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """Not used in backtest mode. Raise NotImplementedError."""
        raise NotImplementedError(
            "BacktestDataService does not support historical candle queries. "
            "Use Parquet files directly."
        )
    
    # --- Harness-controlled methods ---
    
    async def feed_bar(
        self,
        symbol: str,
        timestamp: datetime,
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        timeframe: str = "1m",
    ) -> None:
        """Feed a single bar into the system.
        
        1. Update indicator state for this symbol (VWAP, ATR, SMA, RVOL)
        2. Update price cache
        3. Publish CandleEvent to EventBus
        4. Publish IndicatorEvents for all updated indicators
        
        Claude Code: Extract the indicator computation logic from 
        ReplayDataService (the _update_indicators / _compute_indicators 
        method) and reuse it here. Do NOT reimplement from scratch — 
        the indicators must compute identically to what ReplayDataService
        and AlpacaDataService produce.
        """
        # Update price cache
        self._price_cache[symbol] = close
        
        # Update indicators (reuse existing logic)
        # ... compute VWAP, ATR, SMA(9), SMA(20), SMA(50), RVOL ...
        # ... update self._indicator_cache ...
        
        # Publish CandleEvent
        candle_event = CandleEvent(
            symbol=symbol,
            timeframe=timeframe,
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=volume,
            timestamp=timestamp,
        )
        await self._event_bus.publish(candle_event)
        
        # Publish IndicatorEvents for each updated indicator
        # ... for each indicator in [vwap, atr_14, sma_9, sma_20, sma_50, rvol] ...
        # ... if value is not None, publish IndicatorEvent ...
    
    async def publish_tick(
        self, symbol: str, price: float, volume: int, timestamp: datetime
    ) -> None:
        """Publish a synthetic tick to the EventBus.
        
        Called by the harness during tick synthesis. Updates price cache
        and publishes TickEvent.
        """
        self._price_cache[symbol] = price
        tick_event = TickEvent(
            symbol=symbol,
            price=price,
            volume=volume,
            timestamp=timestamp,
        )
        await self._event_bus.publish(tick_event)
    
    def reset_daily_state(self) -> None:
        """Reset indicator state that is daily-scoped.
        
        Called by the harness at the start of each trading day.
        - VWAP resets (cumulative within day)
        - ATR, SMA carry over (rolling windows)
        - RVOL resets (relative to today's baseline)
        
        Claude Code: Check how ReplayDataService handles day boundaries
        for indicator resets and mirror the logic.
        """
        # Reset VWAP accumulators per symbol
        # Reset RVOL baseline per symbol
        # ATR and SMA carry over — do not reset
        pass
```

**Key implementation note:** The indicator computation MUST be extracted from or shared with ReplayDataService. If the existing ReplayDataService has indicator logic inline (not in a shared utility), Claude Code should refactor it into a shared module (e.g., `argus/data/indicators.py`) that both ReplayDataService and BacktestDataService import. This prevents duplicate logic and ensures identical computation. If refactoring is too invasive, at minimum copy the logic and add a `# TODO: extract to shared module` comment.

---

### Component 3: TickSynthesizer (`argus/backtest/tick_synthesizer.py`)

Small utility that generates synthetic tick sequences from a bar's OHLC data.

```python
"""Synthesize tick sequences from 1-minute bar OHLC data.

Generates 4 synthetic ticks per bar to drive the Order Manager's
tick-based exit evaluation. The tick order depends on bar direction
to simulate a conservative intra-bar price path for longs:

- Bullish bar (close >= open): O → L → H → C
  (dip before rally — stop gets tested before target)
- Bearish bar (close < open): O → H → L → C
  (rally before dip — target gets tested before stop)

This is the "worst-case for longs" ordering, which produces
conservative backtest results. Real intra-bar paths are more complex,
but this 4-tick model exercises the actual Order Manager code and is
sufficient for strategy validation.

Limitations (documented, accepted):
- Real ticks within a 1m bar can number in the hundreds/thousands.
- True intra-bar path may hit stop AND target — we can only detect one.
- Volume per tick is approximated as bar_volume / 4.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class SyntheticTick:
    """A single synthetic tick derived from bar OHLC."""
    symbol: str
    price: float
    volume: int
    timestamp: datetime


def synthesize_ticks(
    symbol: str,
    timestamp: datetime,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: int,
) -> list[SyntheticTick]:
    """Generate 4 synthetic ticks from a bar's OHLC.
    
    Args:
        symbol: Ticker symbol.
        timestamp: Bar timestamp (start of the 1-minute bar).
        open_: Bar open price.
        high: Bar high price.
        low: Bar low price.
        close: Bar close price.
        volume: Bar volume.
    
    Returns:
        List of 4 SyntheticTick objects in the appropriate order.
    """
    tick_volume = max(1, volume // 4)
    
    # Determine tick order based on bar direction
    if close >= open_:
        # Bullish: O → L → H → C (dip first, conservative for longs)
        prices = [open_, low, high, close]
    else:
        # Bearish: O → H → L → C (rally first, conservative for longs)
        prices = [open_, high, low, close]
    
    # Space ticks ~15 seconds apart within the 1-minute bar
    ticks = []
    for i, price in enumerate(prices):
        tick_time = timestamp + timedelta(seconds=i * 15)
        ticks.append(SyntheticTick(
            symbol=symbol,
            price=price,
            volume=tick_volume,
            timestamp=tick_time,
        ))
    
    return ticks
```

---

### Component 4: ScannerSimulator (`argus/backtest/scanner_simulator.py`)

Simulates the pre-market scanner for backtest mode. Computes daily watchlists from gap data.

```python
"""Scanner simulation for backtesting.

In live trading, AlpacaScanner fetches pre-market snapshots to find
gapping stocks. In backtest mode, we don't have pre-market data
(IEX feed covers regular hours only — see DEF-007).

Instead, we compute the gap as:
    gap_pct = (day_open - prev_close) / prev_close

Where:
    day_open = first 1m bar's open price on the current day
    prev_close = last 1m bar's close price on the previous trading day

We then apply the same filter criteria as the live scanner:
    - min_gap_pct (default 2%)
    - min_price / max_price range
    
If the filter produces zero symbols for a day, optionally fall back
to feeding all symbols (configurable).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class DailyWatchlist:
    """Watchlist for a single trading day."""
    trading_date: date
    symbols: list[str]
    mode: str  # "gap_filter" or "all_symbols"
    gap_data: dict[str, float]  # symbol → gap_pct


class ScannerSimulator:
    """Simulates pre-market scanning for backtesting.
    
    Pre-computes watchlists for all trading days by analyzing gap data
    from the historical bar data.
    
    Args:
        min_gap_pct: Minimum gap percentage to qualify (default 0.02 = 2%).
        min_price: Minimum stock price filter.
        max_price: Maximum stock price filter.
        fallback_all_symbols: If True, use all symbols when gap filter
            finds no candidates.
    """
    
    def __init__(
        self,
        min_gap_pct: float = 0.02,
        min_price: float = 10.0,
        max_price: float = 500.0,
        fallback_all_symbols: bool = True,
    ) -> None:
        self._min_gap_pct = min_gap_pct
        self._min_price = min_price
        self._max_price = max_price
        self._fallback_all_symbols = fallback_all_symbols
    
    def compute_watchlists(
        self,
        bar_data: dict[str, pd.DataFrame],
        trading_days: list[date],
    ) -> dict[date, DailyWatchlist]:
        """Pre-compute watchlists for all trading days.
        
        Args:
            bar_data: Dict of symbol → DataFrame with columns 
                [timestamp, open, high, low, close, volume].
                Timestamps in UTC.
            trading_days: Ordered list of trading days to compute for.
        
        Returns:
            Dict of date → DailyWatchlist.
        
        Algorithm:
        1. For each symbol, extract the last close of each trading day
           and the first open of the next trading day.
        2. Compute gap_pct = (next_open - prev_close) / prev_close.
        3. Filter by min_gap_pct, min_price, max_price.
        4. If no symbols pass, fall back to all symbols (if enabled).
        
        Note: The first trading day in the range has no "previous close"
        available (it's the start of our data). Use fallback for day 1.
        """
        watchlists: dict[date, DailyWatchlist] = {}
        all_symbols = list(bar_data.keys())
        
        # Build lookup: symbol → {date → (first_open, last_close)}
        # Claude Code: Extract trading day boundaries from timestamps.
        # Convert UTC timestamps to ET to determine trading day boundaries.
        # Market hours: 9:30-16:00 ET.
        
        # For each trading day (starting from day 2):
        #   For each symbol:
        #     prev_close = last bar's close on previous trading day
        #     day_open = first bar's open on current trading day
        #     gap_pct = (day_open - prev_close) / prev_close
        #   Filter by criteria
        #   Build DailyWatchlist
        
        # Day 1: fallback (no previous close available)
        if trading_days:
            watchlists[trading_days[0]] = DailyWatchlist(
                trading_date=trading_days[0],
                symbols=all_symbols,
                mode="all_symbols",
                gap_data={},
            )
        
        # ... implementation for remaining days ...
        
        return watchlists
```

---

### Component 5: BacktestMetrics (`argus/backtest/metrics.py`)

Computes standard backtest performance metrics from the trade log database.

```python
"""Backtest performance metrics.

Computes standard trading metrics from a trade log database (SQLite).
The trade log uses the same schema as the production database, so all
metrics work on both backtest and live trade data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Complete results from a backtest run."""
    
    # Run metadata
    strategy_id: str
    start_date: date
    end_date: date
    initial_capital: float
    final_equity: float
    trading_days: int
    
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int  # P&L within ±$0.50
    
    # Performance
    win_rate: float              # winning_trades / total_trades
    profit_factor: float         # gross_wins / gross_losses (inf if no losses)
    avg_r_multiple: float        # average R per trade
    avg_winner_r: float          # average R of winning trades
    avg_loser_r: float           # average R of losing trades (negative)
    expectancy: float            # (win_rate * avg_winner_r) + ((1 - win_rate) * avg_loser_r)
    
    # Drawdown
    max_drawdown_dollars: float  # largest peak-to-trough decline
    max_drawdown_pct: float      # as percentage of peak equity
    
    # Risk-adjusted
    sharpe_ratio: float          # annualized, using daily returns
    recovery_factor: float       # net_profit / max_drawdown
    
    # Duration
    avg_hold_minutes: float      # average position hold duration
    
    # Streaks
    max_consecutive_wins: int
    max_consecutive_losses: int
    
    # Extremes
    largest_win_dollars: float
    largest_loss_dollars: float
    largest_win_r: float
    largest_loss_r: float
    
    # Time analysis
    pnl_by_hour: dict[int, float]       # hour (ET) → total P&L
    pnl_by_weekday: dict[int, float]    # 0=Mon → total P&L
    trades_by_hour: dict[int, int]      # hour (ET) → trade count
    trades_by_weekday: dict[int, int]   # 0=Mon → trade count
    
    # Daily equity curve
    daily_equity: list[tuple[date, float]]  # (date, end_of_day_equity)
    
    # Monthly P&L
    monthly_pnl: dict[str, float]  # "YYYY-MM" → net P&L


def compute_metrics(
    trade_logger,  # TradeLogger instance connected to backtest DB
    strategy_id: str,
    start_date: date,
    end_date: date,
    initial_capital: float,
) -> BacktestResult:
    """Compute all backtest metrics from the trade log.
    
    Args:
        trade_logger: TradeLogger connected to the backtest database.
        strategy_id: Strategy that was run.
        start_date: First trading day in the backtest.
        end_date: Last trading day in the backtest.
        initial_capital: Starting capital.
    
    Returns:
        BacktestResult with all computed metrics.
    
    Implementation notes:
    - Query all trades from the trade log for the date range.
    - Each trade record should have: entry_price, exit_price, shares,
      pnl_dollars, entry_time, exit_time, strategy_id, symbol.
    - R-multiple = pnl_dollars / risk_dollars, where 
      risk_dollars = (entry_price - stop_price) * shares.
    - If stop_price is not in the trade record, use the signal's stop_price
      (may require joining with signal log, or storing R on trade record).
    
    Claude Code: Check the TradeLogger's trade record schema. The
    compute_metrics function needs to know what fields are available.
    If R-multiple can't be computed from the trade record alone,
    either: (a) store risk_per_share on the trade record (preferred),
    or (b) compute from entry_price and the strategy's stop rule.
    """
    pass  # Implementation TBD by Claude Code


def compute_sharpe_ratio(
    daily_returns: list[float],
    risk_free_rate: float = 0.05,  # 5% annual
    trading_days_per_year: int = 252,
) -> float:
    """Compute annualized Sharpe ratio from daily returns.
    
    Sharpe = (mean_daily_return - daily_risk_free) / std_daily_return * sqrt(252)
    
    Returns 0.0 if fewer than 2 data points or zero standard deviation.
    """
    if len(daily_returns) < 2:
        return 0.0
    
    daily_rf = risk_free_rate / trading_days_per_year
    excess_returns = [r - daily_rf for r in daily_returns]
    
    mean_excess = sum(excess_returns) / len(excess_returns)
    variance = sum((r - mean_excess) ** 2 for r in excess_returns) / (len(excess_returns) - 1)
    std_dev = variance ** 0.5
    
    if std_dev == 0:
        return 0.0
    
    return (mean_excess / std_dev) * (trading_days_per_year ** 0.5)


def compute_max_drawdown(
    equity_curve: list[float],
) -> tuple[float, float]:
    """Compute maximum drawdown from an equity curve.
    
    Args:
        equity_curve: List of equity values (e.g., end-of-day equity).
    
    Returns:
        Tuple of (max_drawdown_dollars, max_drawdown_pct).
    """
    if not equity_curve:
        return 0.0, 0.0
    
    peak = equity_curve[0]
    max_dd_dollars = 0.0
    max_dd_pct = 0.0
    
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        drawdown = peak - equity
        drawdown_pct = drawdown / peak if peak > 0 else 0.0
        if drawdown > max_dd_dollars:
            max_dd_dollars = drawdown
            max_dd_pct = drawdown_pct
    
    return max_dd_dollars, max_dd_pct
```

---

### Component 6: ReplayHarness (`argus/backtest/replay_harness.py`)

The main orchestrator. This is the most important file in Sprint 7.

```python
"""Replay Harness — highest-fidelity backtesting for Argus.

Feeds historical Parquet data through the production trading pipeline:
  EventBus → BacktestDataService → OrbBreakout → RiskManager → OrderManager → SimulatedBroker

All components are REAL production code. The only differences from live:
  1. FixedClock instead of SystemClock (simulated time)
  2. BacktestDataService instead of AlpacaDataService (step-by-step bar feed)
  3. SimulatedBroker instead of AlpacaBroker (deterministic fills)
  4. ScannerSimulator instead of AlpacaScanner (gap-based watchlist)

Output: A SQLite database per run with the same schema as production.
All existing SQL queries work on backtest output.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from argus.backtest.backtest_data_service import BacktestDataService
from argus.backtest.config import BacktestConfig
from argus.backtest.metrics import BacktestResult, compute_metrics
from argus.backtest.scanner_simulator import ScannerSimulator
from argus.backtest.tick_synthesizer import synthesize_ticks
from argus.core.clock import FixedClock
from argus.core.config import ArgusConfig  # or however config is loaded
from argus.core.event_bus import EventBus
from argus.core.events import OrderFilledEvent, OrderStatus
from argus.core.risk_manager import RiskManager
from argus.execution.order_manager import OrderManager
from argus.execution.simulated_broker import SimulatedBroker, SimulatedSlippage
from argus.strategies.orb_breakout import OrbBreakout

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")


class ReplayHarness:
    """Orchestrates a complete backtest run using production components.
    
    Usage:
        config = BacktestConfig(start_date=date(2025, 6, 1), end_date=date(2025, 12, 31))
        harness = ReplayHarness(config)
        result = await harness.run()
        print(result)
    """
    
    def __init__(self, config: BacktestConfig) -> None:
        self._config = config
        
        # Components — initialized in _setup()
        self._event_bus: EventBus | None = None
        self._clock: FixedClock | None = None
        self._broker: SimulatedBroker | None = None
        self._risk_manager: RiskManager | None = None
        self._order_manager: OrderManager | None = None
        self._strategy: OrbBreakout | None = None
        self._data_service: BacktestDataService | None = None
        self._trade_logger = None  # TradeLogger type — check actual import
        self._db_manager = None    # DatabaseManager type — check actual import
        
        # Run state
        self._bar_data: dict[str, pd.DataFrame] = {}
        self._trading_days: list[date] = []
        self._daily_summaries: list[dict] = []
    
    async def run(self) -> BacktestResult:
        """Execute the complete backtest.
        
        Returns:
            BacktestResult with all performance metrics.
        """
        logger.info(
            "Starting backtest: strategy=%s, period=%s to %s",
            self._config.strategy_id,
            self._config.start_date,
            self._config.end_date,
        )
        
        # 1. Load historical data
        self._load_data()
        
        # 2. Initialize all components
        await self._setup()
        
        # 3. Pre-compute watchlists
        scanner = ScannerSimulator(
            min_gap_pct=self._config.scanner_min_gap_pct,
            min_price=self._config.scanner_min_price,
            max_price=self._config.scanner_max_price,
            fallback_all_symbols=self._config.scanner_fallback_all_symbols,
        )
        watchlists = scanner.compute_watchlists(self._bar_data, self._trading_days)
        
        # 4. Run each trading day
        for day_num, trading_day in enumerate(self._trading_days, 1):
            await self._run_trading_day(trading_day, watchlists.get(trading_day))
            
            if day_num % 20 == 0:
                logger.info(
                    "Progress: %d/%d trading days complete",
                    day_num, len(self._trading_days),
                )
        
        # 5. Compute metrics
        result = await self._compute_results()
        
        # 6. Teardown
        await self._teardown()
        
        logger.info(
            "Backtest complete: %d trading days, %d trades, PF=%.2f, WR=%.1f%%",
            result.trading_days,
            result.total_trades,
            result.profit_factor,
            result.win_rate * 100,
        )
        
        return result
    
    def _load_data(self) -> None:
        """Load Parquet files for all symbols in the data directory.
        
        Loads all .parquet files from self._config.data_dir.
        Filters to the configured date range.
        Builds self._bar_data (dict[symbol, DataFrame]) and 
        self._trading_days (sorted list of unique dates).
        
        Claude Code: The Sprint 6 Parquet files are stored as
        data/historical/1m/{SYMBOL}/{SYMBOL}_{YYYY}-{MM}.parquet.
        Load all month files that overlap with the date range.
        Concatenate per symbol. Filter rows to [start_date, end_date].
        
        Convert UTC timestamps to ET for trading day extraction.
        Trading days = unique dates when bars exist.
        Sort trading_days chronologically.
        """
        pass
    
    async def _setup(self) -> None:
        """Initialize all production components for the backtest.
        
        1. Create output directory and backtest database
        2. Initialize EventBus
        3. Initialize FixedClock (set to first trading day, pre-market)
        4. Initialize DatabaseManager + TradeLogger (writing to backtest DB)
        5. Initialize SimulatedBroker (with configured slippage and initial cash)
        6. Initialize BacktestDataService
        7. Initialize RiskManager (with SimulatedBroker + FixedClock)
        8. Initialize OrderManager (with SimulatedBroker + FixedClock)
        9. Initialize OrbBreakout strategy (with BacktestDataService + FixedClock)
        10. Start all components (subscribe to events, etc.)
        
        Apply config_overrides from BacktestConfig before creating strategy.
        
        Database path: {output_dir}/{strategy}_{start}_{end}_{timestamp}.db
        Example: data/backtest_runs/orb_20250601_20251231_20260216_143022.db
        """
        pass
    
    async def _run_trading_day(
        self, trading_day: date, watchlist: "DailyWatchlist | None"
    ) -> None:
        """Run a single trading day through the pipeline.
        
        Sequence:
        1. Set FixedClock to 09:25 ET on trading_day (pre-market)
        2. Reset daily state:
           - strategy.reset_daily_state()
           - risk_manager.reset_daily_state()
           - order_manager._flattened_today = False (check actual field name)
           - data_service.reset_daily_state()
           - broker: reset daily tracking if any
        3. Set strategy's watchlist from ScannerSimulator output
        4. Get today's bars for watchlist symbols, sorted by timestamp
        5. For each bar:
           a. Advance FixedClock to bar's timestamp
           b. Call data_service.feed_bar(...)
              → Publishes CandleEvent + IndicatorEvents
              → Strategy's on_candle() fires
              → May cascade: Signal → Risk → Order → Broker fill
           c. Yield to event loop: await asyncio.sleep(0)
           d. Synthesize ticks from bar OHLC
           e. For each synthetic tick:
              - Call data_service.publish_tick(...)
                → Publishes TickEvent
                → Order Manager's on_tick() fires
              - Call broker.simulate_price_update(symbol, tick_price)
                → Triggers pending bracket orders (stops/targets)
                → Returns list of triggered OrderResults
              - For each triggered fill: publish OrderFilledEvent
                → Order Manager's on_fill() processes
              - Yield to event loop
        6. After last bar: check if EOD flatten needed
           - Advance clock to eod_flatten_time
           - Call order_manager.eod_flatten()
           - Yield to event loop
        7. Log daily summary
        """
        pass
    
    def _get_daily_bars(
        self, trading_day: date, symbols: list[str]
    ) -> pd.DataFrame:
        """Get all bars for the given symbols on the given trading day.
        
        Returns a single DataFrame with all symbols' bars for the day,
        sorted by timestamp. Includes a 'symbol' column.
        
        Claude Code: Convert timestamps from UTC to ET to filter by
        trading day. Market hours: 9:30-16:00 ET.
        """
        pass
    
    async def _process_bracket_triggers(
        self, symbol: str, price: float
    ) -> None:
        """Call simulate_price_update and publish fill events.
        
        This is the bridge between SimulatedBroker's synchronous bracket
        triggers and the Order Manager's event-driven fill handling.
        
        1. Call self._broker.simulate_price_update(symbol, price)
        2. For each OrderResult returned:
           - If status == FILLED:
             Publish OrderFilledEvent to EventBus with:
               order_id, fill_price, fill_quantity, symbol
        3. Yield to event loop
        
        Claude Code: Check the actual OrderResult fields and OrderFilledEvent
        constructor. The OrderFilledEvent may need symbol added if not present
        (see Sprint 4b spec note about missing symbol field).
        """
        pass
    
    async def _compute_results(self) -> BacktestResult:
        """Compute all metrics after the backtest completes.
        
        Uses compute_metrics() from metrics.py, passing the TradeLogger
        connected to the backtest database.
        """
        pass
    
    async def _teardown(self) -> None:
        """Clean up all components.
        
        1. Stop Order Manager
        2. Stop Risk Manager (if has stop method)
        3. Close database connection
        4. Log final database path
        """
        pass
```

---

### Component 7: CLI Entry Point (`argus/backtest/replay_harness.py` — `__main__` block)

Add a CLI interface at the bottom of replay_harness.py (or as `argus/backtest/__main__.py`).

```python
"""CLI for the Replay Harness.

Usage:
    python -m argus.backtest.replay_harness \
        --start 2025-06-01 \
        --end 2025-12-31 \
        --data-dir data/historical/1m \
        --initial-cash 100000 \
        --slippage 0.01

    # With config overrides:
    python -m argus.backtest.replay_harness \
        --start 2025-06-01 \
        --end 2025-12-31 \
        --config-override orb_breakout.opening_range_minutes=15 \
        --config-override orb_breakout.target_1_r=1.5
"""

import argparse
import asyncio
import logging
import sys
from datetime import date

from argus.backtest.config import BacktestConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Argus Replay Harness — backtest ORB strategy on historical data"
    )
    parser.add_argument("--start", type=date.fromisoformat, required=True,
                        help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=date.fromisoformat, required=True,
                        help="End date (YYYY-MM-DD)")
    parser.add_argument("--data-dir", default="data/historical/1m",
                        help="Path to historical data directory")
    parser.add_argument("--output-dir", default="data/backtest_runs",
                        help="Path to store backtest results")
    parser.add_argument("--initial-cash", type=float, default=100_000.0,
                        help="Starting capital")
    parser.add_argument("--slippage", type=float, default=0.01,
                        help="Fixed slippage per share in dollars")
    parser.add_argument("--config-override", action="append", default=[],
                        help="Config override in key=value format (repeatable)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable debug logging")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    
    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Parse config overrides
    overrides = {}
    for override in args.config_override:
        key, _, value = override.partition("=")
        # Try to parse as number
        try:
            value = float(value)
            if value == int(value):
                value = int(value)
        except ValueError:
            pass
        overrides[key.strip()] = value
    
    config = BacktestConfig(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        start_date=args.start,
        end_date=args.end,
        initial_cash=args.initial_cash,
        slippage_per_share=args.slippage,
        config_overrides=overrides,
    )
    
    harness = ReplayHarness(config)
    result = asyncio.run(harness.run())
    
    # Print summary
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)
    print(f"Strategy:        {result.strategy_id}")
    print(f"Period:          {result.start_date} to {result.end_date}")
    print(f"Trading Days:    {result.trading_days}")
    print(f"Total Trades:    {result.total_trades}")
    print(f"Win Rate:        {result.win_rate:.1%}")
    print(f"Profit Factor:   {result.profit_factor:.2f}")
    print(f"Avg R-Multiple:  {result.avg_r_multiple:.2f}")
    print(f"Expectancy:      {result.expectancy:.3f}R")
    print(f"Max Drawdown:    ${result.max_drawdown_dollars:,.2f} ({result.max_drawdown_pct:.1%})")
    print(f"Sharpe Ratio:    {result.sharpe_ratio:.2f}")
    print(f"Recovery Factor: {result.recovery_factor:.2f}")
    print(f"Net P&L:         ${result.final_equity - config.initial_cash:,.2f}")
    print(f"Final Equity:    ${result.final_equity:,.2f}")
    print(f"Avg Hold:        {result.avg_hold_minutes:.0f} min")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

---

## Tests

### File: `tests/backtest/test_tick_synthesizer.py`

~5 tests:

```
test_bullish_bar_order
    # close >= open → O, L, H, C
    ticks = synthesize_ticks("AAPL", ts, open_=100, high=105, low=98, close=104, volume=1000)
    assert [t.price for t in ticks] == [100, 98, 105, 104]
    assert len(ticks) == 4

test_bearish_bar_order
    # close < open → O, H, L, C
    ticks = synthesize_ticks("AAPL", ts, open_=100, high=102, low=95, close=96, volume=1000)
    assert [t.price for t in ticks] == [100, 102, 95, 96]

test_doji_bar_treated_as_bullish
    # close == open → bullish path (O, L, H, C)
    ticks = synthesize_ticks("AAPL", ts, open_=100, high=101, low=99, close=100, volume=400)
    assert [t.price for t in ticks] == [100, 99, 101, 100]

test_volume_distributed_evenly
    ticks = synthesize_ticks("AAPL", ts, open_=100, high=105, low=98, close=104, volume=1000)
    assert all(t.volume == 250 for t in ticks)

test_timestamps_spaced_15_seconds
    ticks = synthesize_ticks("AAPL", base_ts, open_=100, high=105, low=98, close=104, volume=1000)
    for i, tick in enumerate(ticks):
        expected = base_ts + timedelta(seconds=i * 15)
        assert tick.timestamp == expected
```

### File: `tests/backtest/test_scanner_simulator.py`

~6 tests:

```
test_gap_filter_selects_gapping_stocks
    # Symbol A: prev_close=100, day_open=103 → 3% gap → selected
    # Symbol B: prev_close=100, day_open=100.50 → 0.5% gap → filtered out
    scanner = ScannerSimulator(min_gap_pct=0.02)
    watchlists = scanner.compute_watchlists(bar_data, trading_days)
    assert "A" in watchlists[day2].symbols
    assert "B" not in watchlists[day2].symbols

test_price_filter_applied
    # Symbol C: gapping 5% but price=$5 (below min_price=10) → filtered
    scanner = ScannerSimulator(min_price=10.0)
    watchlists = scanner.compute_watchlists(bar_data, trading_days)
    assert "C" not in watchlists[day2].symbols

test_first_day_uses_all_symbols
    # No previous close for day 1 → fallback to all
    watchlists = scanner.compute_watchlists(bar_data, [day1, day2])
    assert watchlists[day1].mode == "all_symbols"

test_fallback_when_no_gaps
    # All symbols gap < 2% → if fallback enabled, use all
    scanner = ScannerSimulator(min_gap_pct=0.10, fallback_all_symbols=True)
    watchlists = scanner.compute_watchlists(bar_data, trading_days)
    assert watchlists[day2].mode == "all_symbols"

test_no_fallback_returns_empty
    scanner = ScannerSimulator(min_gap_pct=0.10, fallback_all_symbols=False)
    watchlists = scanner.compute_watchlists(bar_data, trading_days)
    assert watchlists[day2].symbols == []

test_gap_data_recorded
    watchlists = scanner.compute_watchlists(bar_data, trading_days)
    assert "A" in watchlists[day2].gap_data
    assert abs(watchlists[day2].gap_data["A"] - 0.03) < 0.001
```

### File: `tests/backtest/test_backtest_data_service.py`

~6 tests:

```
test_feed_bar_publishes_candle_event
    # Feed a bar → CandleEvent received by subscriber
    ds = BacktestDataService(event_bus)
    received = []
    await event_bus.subscribe(CandleEvent, received.append)
    await ds.feed_bar("AAPL", ts, 100, 105, 98, 104, 50000)
    assert len(received) == 1
    assert received[0].symbol == "AAPL"
    assert received[0].close == 104

test_feed_bar_publishes_indicator_events
    # Feed enough bars for indicators to compute → IndicatorEvents published
    ds = BacktestDataService(event_bus)
    indicator_events = []
    await event_bus.subscribe(IndicatorEvent, indicator_events.append)
    # Feed 15+ bars to get VWAP and ATR
    for i in range(15):
        await ds.feed_bar("AAPL", ts + timedelta(minutes=i), ...)
    # At least VWAP should be published
    vwap_events = [e for e in indicator_events if e.indicator_name == "vwap"]
    assert len(vwap_events) > 0

test_get_current_price_after_feed
    ds = BacktestDataService(event_bus)
    await ds.feed_bar("AAPL", ts, 100, 105, 98, 104, 50000)
    price = await ds.get_current_price("AAPL")
    assert price == 104.0

test_get_indicator_returns_vwap
    ds = BacktestDataService(event_bus)
    # Feed several bars
    for i in range(5):
        await ds.feed_bar("AAPL", ts + timedelta(minutes=i), 100, 101, 99, 100, 10000)
    vwap = await ds.get_indicator("AAPL", "vwap")
    assert vwap is not None
    assert vwap > 0

test_publish_tick_updates_price_cache
    ds = BacktestDataService(event_bus)
    await ds.publish_tick("AAPL", 105.50, 100, ts)
    price = await ds.get_current_price("AAPL")
    assert price == 105.50

test_reset_daily_state_resets_vwap
    ds = BacktestDataService(event_bus)
    # Feed bars for day 1
    for i in range(10):
        await ds.feed_bar("AAPL", day1_ts + timedelta(minutes=i), ...)
    vwap_before = await ds.get_indicator("AAPL", "vwap")
    # Reset
    ds.reset_daily_state()
    # Feed first bar of day 2 — VWAP should restart
    await ds.feed_bar("AAPL", day2_ts, 200, 201, 199, 200, 10000)
    vwap_after = await ds.get_indicator("AAPL", "vwap")
    # VWAP should reflect only day 2's bar
    assert vwap_after != vwap_before
```

### File: `tests/backtest/test_metrics.py`

~5 tests:

```
test_sharpe_ratio_positive_returns
    daily_returns = [0.01, 0.005, 0.008, -0.002, 0.012] * 50  # 250 days
    sharpe = compute_sharpe_ratio(daily_returns)
    assert sharpe > 0

test_sharpe_ratio_zero_std_returns_zero
    daily_returns = [0.01] * 100  # No variance
    sharpe = compute_sharpe_ratio(daily_returns)
    assert sharpe == 0.0

test_sharpe_ratio_insufficient_data
    sharpe = compute_sharpe_ratio([0.01])
    assert sharpe == 0.0

test_max_drawdown_simple
    equity = [100, 110, 105, 95, 100, 90, 115]
    dd_dollars, dd_pct = compute_max_drawdown(equity)
    # Peak was 110, trough was 90 → DD = 20, 18.18%
    assert dd_dollars == 20.0
    assert abs(dd_pct - 0.1818) < 0.01

test_max_drawdown_no_drawdown
    equity = [100, 105, 110, 115]
    dd_dollars, dd_pct = compute_max_drawdown(equity)
    assert dd_dollars == 0.0
```

### File: `tests/backtest/test_replay_harness.py`

~8 tests. These are integration-level tests using synthetic data.

```
test_harness_runs_single_day_no_crash
    # Minimal test: 1 symbol, 1 day of synthetic bars, harness completes
    config = BacktestConfig(
        start_date=test_day, end_date=test_day,
        data_dir=tmp_parquet_dir, initial_cash=100000,
    )
    harness = ReplayHarness(config)
    result = await harness.run()
    assert result.trading_days == 1
    assert result.total_trades >= 0  # May or may not trade

test_harness_creates_output_database
    # Run harness → output .db file exists in output_dir
    config = BacktestConfig(...)
    harness = ReplayHarness(config)
    await harness.run()
    db_files = list(Path(config.output_dir).glob("*.db"))
    assert len(db_files) == 1

test_harness_clock_advances_with_bars
    # Verify FixedClock time matches bar timestamps during replay
    # (Instrument the harness or check via a clock-reading spy)
    pass  # Design depends on whether we can hook into the harness internals

test_harness_eod_flatten_closes_positions
    # Generate data that triggers a trade, then verify EOD flatten
    # closes it. Check that the trade record has exit_reason containing
    # "eod" or "flatten".
    pass  # Requires synthetic data that triggers ORB signal

test_harness_respects_config_overrides
    # Pass config_overrides changing opening_range_minutes
    # Verify the strategy uses the overridden value
    config = BacktestConfig(
        ...,
        config_overrides={"orb_breakout.opening_range_minutes": 10},
    )
    # ... run and verify behavior changes (fewer OR candles)

test_harness_multi_day_resets_strategy_state
    # Run 2 days. Verify strategy's OR state resets between days.
    # Day 2 should form a fresh opening range, not carry over day 1's.
    pass  # Check trade log for signals on both days

test_harness_scanner_filters_symbols
    # Generate data where Symbol A has a 5% gap and Symbol B has 0.5% gap
    # Verify only Symbol A appears in the watchlist / generates trades
    pass

test_harness_slippage_applied
    # Run with slippage=0.01. Check that fills in trade log show
    # entry price slightly worse than the bar's price.
    # Compare to a run with slippage=0.00.
    pass
```

**Test data generation:** Create a `tests/backtest/conftest.py` with fixtures that generate synthetic Parquet files for testing. Reuse the `generate_test_parquet()` helper from Sprint 3 tests if it exists, or create a new one. The synthetic data should:
- Cover 1-3 trading days
- Include bars for 9:30-16:00 ET only
- Have configurable price action (e.g., create a gap + breakout scenario for trigger testing)
- Be in the same format as Sprint 6 Parquet files (per-symbol-per-month layout)

---

## New Files Created This Sprint

```
argus/backtest/config.py             (EXTEND — add BacktestConfig)
argus/backtest/backtest_data_service.py
argus/backtest/tick_synthesizer.py
argus/backtest/scanner_simulator.py
argus/backtest/metrics.py
argus/backtest/replay_harness.py     (includes CLI)
data/backtest_runs/.gitkeep          (gitignored directory for output)
tests/backtest/test_tick_synthesizer.py
tests/backtest/test_scanner_simulator.py
tests/backtest/test_backtest_data_service.py
tests/backtest/test_metrics.py
tests/backtest/test_replay_harness.py
tests/backtest/conftest.py           (synthetic data fixtures)
```

**Possibly modified:**
- `argus/data/replay_data_service.py` — if indicator logic is extracted to a shared module
- `argus/data/indicators.py` (NEW) — shared indicator computation if extracted
- `.gitignore` — add `data/backtest_runs/` if not already ignored

---

## Build Order

1. **BacktestConfig** — extend existing config.py (quick, foundation for everything)
2. **TickSynthesizer** + tests (standalone utility, no dependencies)
3. **ScannerSimulator** + tests (standalone, only needs pandas)
4. **BacktestDataService** + tests (needs EventBus, indicator logic)
   - If extracting indicators to shared module: do the refactor here
5. **BacktestMetrics** + tests (standalone math, no component dependencies)
6. **ReplayHarness** + tests (wires everything together)
7. **CLI** (thin wrapper around ReplayHarness)
8. **Full test suite pass + ruff clean**

---

## Deferred Items

### DEF-007 | Pre-Market Data for Scanner Accuracy
| Field | Value |
|-------|-------|
| **Description** | IEX feed (free tier) only provides regular market hours data. Scanner simulation computes gap from prev close → day open, which captures overnight moves but misses pre-market volume patterns. |
| **Trigger** | When backtest results look promising and scanner accuracy becomes the bottleneck for live-vs-backtest correlation. |
| **Resolution** | Download 1 month of SIP data (Alpaca paid plan) to validate scanner accuracy. If significant, consider switching to SIP for all historical data. |
| **Status** | Open |

---

## Decision Log Entries (to be committed with this sprint)

### DEC-052 | Scanner Simulation via Gap Computation
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Replay Harness simulates pre-market scanning by computing gap_pct from previous day's close to current day's 9:30 open. Applies same min_gap_pct and price filters as live scanner config. Falls back to all symbols if gap filter produces zero candidates. |
| **Rationale** | No pre-market data available in IEX feed (DEF-007). Gap computation from regular hours data captures overnight moves including pre-market activity reflected in the open. Fallback prevents wasting trading days on zero-candidate scenarios. The 28-symbol universe is already curated for liquidity, reducing the importance of volume-based filtering. |
| **Alternatives** | (a) Static watchlist every day — unrealistic. (b) Feed all symbols always — doesn't test scanner interaction. (c) Download pre-market data — costs money, deferred. |
| **Status** | Active |

### DEC-053 | Synthetic Tick Generation from Bar OHLC
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Generate 4 synthetic ticks per 1m bar: Open, Low, High, Close for bullish bars; Open, High, Low, Close for bearish bars. This "worst-case for longs" ordering tests stops before targets on bullish bars, producing conservative results. |
| **Rationale** | The Replay Harness must run the actual Order Manager code (tick-driven exits), which requires TickEvents. Synthetic ticks are an approximation but exercise the real code path. Option (b) — a simplified bar-close evaluator — would create a parallel implementation that could diverge from production. Known limitation: real intra-bar paths are more complex, and the 4-tick model may miss scenarios where both stop and target are hit within one bar. |
| **Alternatives** | (b) Simplified replay-mode Order Manager evaluating on bar close only. (c) Random walk simulation within OHLC bounds — more complex, marginal benefit. |
| **Status** | Active |

### DEC-054 | Fixed Slippage Model for V1 Backtesting
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | $0.01/share fixed slippage for all backtest fills. Configured via `BacktestConfig.slippage_per_share`. |
| **Rationale** | Simple, conservative, configurable. At 100 shares per trade and 2 fills per round trip, this adds $2 drag per trade — meaningful over hundreds of trades. Can be refined in Sprint 9 after comparing backtest to paper trading results. Volume-dependent slippage adds complexity with no calibration data yet. |
| **Alternatives** | (b) Percentage-based (0.05%). (c) Volume-dependent. (d) No slippage. |
| **Status** | Active |

### DEC-055 | BacktestDataService (Step-Driven DataService)
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | New BacktestDataService implements DataService ABC but is driven step-by-step via `feed_bar()` and `publish_tick()` methods. Does not reuse ReplayDataService's `start()` method (which runs autonomously). Shares indicator computation logic with ReplayDataService. |
| **Rationale** | The Replay Harness needs fine-grained control over clock advancement, event ordering, and daily lifecycle that ReplayDataService's autonomous iteration doesn't provide. The strategy needs a DataService for `get_indicator()` / `get_current_price()` lookups. BacktestDataService satisfies both requirements. Indicator logic is shared (not duplicated) to ensure identical computation across all DataService implementations. |
| **Alternatives** | (a) Modify ReplayDataService to support step mode — invasive, breaks existing tests. (b) Harness publishes events directly without a DataService — strategy can't call `get_indicator()`. |
| **Status** | Active |

### DEC-056 | Backtest Database Naming Convention
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Backtest output databases stored at `data/backtest_runs/{strategy}_{start}_{end}_{timestamp}.db`. Example: `orb_20250601_20251231_20260216_143022.db`. Directory is gitignored. |
| **Rationale** | Strategy name and date range in filename enables easy identification and filtering. Run timestamp ensures uniqueness across repeated runs. Same schema as production database allows reuse of all SQL queries and TradeLogger methods. |
| **Alternatives** | (a) `run_YYYYMMDD_HHMMSS.db` — less informative filename. |
| **Status** | Active |

---

*End of Sprint 7 Implementation Spec*
