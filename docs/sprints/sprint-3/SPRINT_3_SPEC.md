# ARGUS — Sprint 3 Implementation Spec

> **Sprint 3 Scope:** BaseStrategy ABC + Scanner + Data Service + ORB Breakout Strategy
> **Date:** February 15, 2026
> **Prerequisite:** Sprint 2 complete (112 tests passing, ruff clean). Sprint 2 polish committed.

---

## Context

Read these files before starting:
- `CLAUDE.md` — project rules, code style, architectural constraints
- `docs/03_ARCHITECTURE.md` — Sections 3.2 (Data Service), 3.4 (BaseStrategy)
- `docs/01_PROJECT_BIBLE.md` — Section 4 (Strategy Ecosystem), Section 6 (Risk Management)
- `config/strategies/orb_breakout.yaml` — ORB configuration
- `argus/core/events.py` — existing event types
- `argus/models/trading.py` — existing data models
- `argus/core/risk_manager.py` — Risk Manager (Sprint 2)
- `argus/execution/simulated_broker.py` — SimulatedBroker (Sprint 2)

Sprint 3 builds the strategy layer: the base strategy interface, a scanner that feeds watchlists to strategies, a data service that delivers market data, and the first real strategy (ORB Breakout). By the end of this sprint, ORB should be able to receive replayed 1-minute candle data, track an opening range, detect breakouts, and emit `SignalEvent`s — fully testable end-to-end with `SimulatedBroker` and `ReplayDataService`.

---

## Pre-Sprint Fix: DEC-037 (Start-of-Day Equity)

**Do this first as a warm-up.** The Risk Manager's cash reserve currently uses `account.equity` (live equity including unrealized P&L). It should use start-of-day equity.

### Changes:
1. **`argus/core/risk_manager.py`:**
   - Add `_start_of_day_equity: float = 0.0` to `__init__`
   - In `reset_daily_state()`: query the broker for current account info, store `account.equity` into `_start_of_day_equity`
   - In `evaluate_signal()` step 5 (cash reserve check): replace `account.equity` with `self._start_of_day_equity`
   - In `reconstruct_state()`: also snapshot start-of-day equity (query broker)
   - If `_start_of_day_equity` is 0.0 (never initialized — e.g., first call before `reset_daily_state`), fall back to live `account.equity` for safety

2. **Tests:**
   - Test that after `reset_daily_state()`, `_start_of_day_equity` is set
   - Test that cash reserve check uses `_start_of_day_equity` not live equity
   - Test the fallback: if `_start_of_day_equity` is 0, uses live equity

3. **Verify:** All 112+ existing tests still pass. Run ruff.

---

## Step 1: Pydantic Config Models for Sprint 3

Add new config models for Data Service and Scanner. Follow the DEC-032 pattern (Pydantic BaseModel, loaded from YAML).

### File: `argus/core/config.py` (extend existing)

```python
class DataServiceConfig(BaseModel):
    """Configuration for the Data Service."""
    active_timeframes: list[str] = ["1m"]  # Only 1m in Sprint 3
    supported_timeframes: list[str] = ["1s", "5s", "1m", "5m", "15m"]
    indicators: list[str] = ["vwap", "atr_14", "rvol", "sma_9", "sma_20", "sma_50"]
    stale_data_timeout_seconds: int = 30

class ScannerConfig(BaseModel):
    """Configuration for the Scanner."""
    scanner_type: str = "static"  # "static" or "alpaca" (future)
    static_symbols: list[str] = []  # Used by StaticScanner

class OrbBreakoutConfig(StrategyConfig):
    """ORB-specific configuration extending the base StrategyConfig.

    Validates ORB-specific parameters on top of the common strategy config.
    """
    orb_window_minutes: int = Field(default=15, ge=1, le=60)
    stop_placement: str = "midpoint"  # "midpoint" or "bottom"
    volume_threshold_rvol: float = Field(default=2.0, gt=0)
    target_1_r: float = Field(default=1.0, gt=0)
    target_2_r: float = Field(default=2.0, gt=0)
    time_stop_minutes: int = Field(default=30, ge=1)
    min_range_atr_ratio: float = Field(default=0.5, gt=0)
    max_range_atr_ratio: float = Field(default=2.0, gt=0)
    chase_protection_pct: float = Field(default=0.005, ge=0, le=0.05)
    breakout_volume_multiplier: float = Field(default=1.5, gt=0)
```

Add `DataServiceConfig` and `ScannerConfig` fields to the top-level `ArgusConfig` model if it exists, or to wherever the configs are composed.

### Tests:
- Validate `OrbBreakoutConfig` loads correctly from `config/strategies/orb_breakout.yaml`
- Validate defaults and constraint enforcement (e.g., `orb_window_minutes` must be >= 1)
- Validate `DataServiceConfig` defaults

---

## Step 2: BaseStrategy ABC

### File: `argus/strategies/base_strategy.py`

This is the interface all strategies implement. Follow Architecture doc Section 3.4 exactly, with these clarifications from decided micro-decisions:

```python
from abc import ABC, abstractmethod
from argus.core.events import CandleEvent, TickEvent, SignalEvent
from argus.models.trading import Position

class BaseStrategy(ABC):
    """Abstract base class for all trading strategies.

    Strategies follow a daily-stateful, session-stateless model (DEC-028):
    - Within a trading day: accumulate state (opening range, trade count, daily P&L)
    - Between trading days: all state wiped by reset_daily_state()
    - On mid-day restart: reconstruct intraday state from database via reconstruct_state()
    """

    def __init__(self, config: StrategyConfig) -> None:
        """Initialize strategy with validated configuration.

        Args:
            config: Strategy configuration loaded from YAML and validated by Pydantic.
        """

    # --- Identity (from config) ---
    @property
    @abstractmethod
    def strategy_id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def version(self) -> str: ...

    # --- Core Interface ---

    @abstractmethod
    async def on_candle(self, event: CandleEvent) -> SignalEvent | None:
        """Process a new candle. Return a SignalEvent if entry criteria are met.

        This is the primary decision method. Called by the Orchestrator/Event Bus
        for every CandleEvent matching symbols on this strategy's watchlist.

        Args:
            event: The candle event with OHLCV data.

        Returns:
            A SignalEvent if all entry criteria are met, None otherwise.
        """

    @abstractmethod
    async def on_tick(self, event: TickEvent) -> None:
        """Process a tick update. Used for fast strategies and position management.

        Args:
            event: The tick event with current price data.
        """

    @abstractmethod
    def get_scanner_criteria(self) -> ScannerCriteria:
        """Return scanner filter criteria for this strategy's stock selection.

        Returns:
            ScannerCriteria defining the filters for pre-market scanning.
        """

    @abstractmethod
    def calculate_position_size(self, entry_price: float, stop_price: float) -> int:
        """Calculate number of shares for a trade.

        Uses the universal formula: shares = risk_dollars / (entry - stop)
        Risk dollars = allocated_capital * risk_per_trade_pct

        Args:
            entry_price: Expected entry price.
            stop_price: Stop loss price.

        Returns:
            Number of shares (integer, floored).
        """

    @abstractmethod
    def get_exit_rules(self) -> ExitRules:
        """Return the complete exit configuration for this strategy.

        Returns:
            ExitRules containing stop loss, profit targets, time stop,
            and trailing stop configuration.
        """

    @abstractmethod
    def get_market_conditions_filter(self) -> MarketConditionsFilter:
        """Return market regime conditions for strategy activation.

        The Orchestrator checks these conditions daily to decide whether
        this strategy should be active.

        Returns:
            MarketConditionsFilter with required regime, VIX range, etc.
        """

    # --- State Management ---

    def check_internal_risk_limits(self) -> bool:
        """Check strategy-level risk limits.

        Returns:
            True if the strategy is within all its limits and can continue trading.
            False if any limit is hit (max daily loss, max positions, max trades).
        """

    def reset_daily_state(self) -> None:
        """Reset all intraday state. Called at start of each trading day.

        Wipes: daily P&L, trade count, opening range, watchlist,
        any strategy-specific intraday state. Does NOT reset config,
        allocated_capital, or pipeline_stage.
        """

    async def reconstruct_state(self, trade_logger) -> None:
        """Reconstruct intraday state from database after mid-day restart.

        Queries today's trades and open positions from the Trade Logger.

        Args:
            trade_logger: TradeLogger instance for database queries.
        """

    # --- Properties ---
    @property
    def is_active(self) -> bool: ...

    @property
    def allocated_capital(self) -> float: ...

    @allocated_capital.setter
    def allocated_capital(self, value: float) -> None: ...

    @property
    def daily_pnl(self) -> float: ...

    @property
    def trade_count_today(self) -> int: ...
```

### Supporting Models

Create `argus/models/strategy.py` (or add to existing models):

```python
@dataclass
class ScannerCriteria:
    """Defines what stocks a strategy wants to see.

    Used by the Scanner to build a watchlist.
    """
    min_price: float = 10.0
    max_price: float = 200.0
    min_volume_avg_daily: int = 1_000_000  # ADV
    min_relative_volume: float = 2.0       # RVOL
    min_gap_pct: float | None = None       # Gap percentage (e.g., 0.02 = 2%)
    max_gap_pct: float | None = None
    min_market_cap: float | None = None
    max_spread_pct: float | None = None    # Maximum bid-ask spread as %
    excluded_symbols: list[str] = field(default_factory=list)
    max_results: int = 20                  # Max watchlist size

@dataclass
class ExitRules:
    """Complete exit configuration for a strategy."""
    stop_type: str  # "fixed", "trailing", "atr_based"
    stop_price_func: str  # How to calculate stop: "midpoint", "bottom", "atr"
    targets: list[ProfitTarget]
    time_stop_minutes: int | None = None
    trailing_stop_atr_multiplier: float | None = None

@dataclass
class ProfitTarget:
    """A single profit target level."""
    r_multiple: float       # Target as R-multiple (1.0 = 1R)
    position_pct: float     # Percentage of position to close at this target (0.5 = 50%)

@dataclass
class MarketConditionsFilter:
    """Conditions under which a strategy may be activated by the Orchestrator."""
    allowed_regimes: list[str]  # e.g., ["bullish_trending", "range_bound"]
    max_vix: float | None = None
    min_vix: float | None = None
    require_spy_above_sma: int | None = None  # e.g., 20 (20-day SMA)

@dataclass
class WatchlistItem:
    """A single stock on a strategy's watchlist."""
    symbol: str
    gap_pct: float | None = None
    relative_volume: float | None = None
    atr: float | None = None
    # Extensible — strategies can use any fields they need
```

### File: `argus/strategies/__init__.py`

Export `BaseStrategy` and supporting models.

### Tests (`tests/strategies/test_base_strategy.py`):
- Create a minimal `ConcreteTestStrategy` that implements the ABC
- Verify it can be instantiated with a valid config
- Test `reset_daily_state()` clears all intraday state
- Test `check_internal_risk_limits()` returns False when limits are hit
- Test `calculate_position_size()` math: `risk_dollars / (entry - stop)`
- Test that `allocated_capital` setter works and is used in position sizing

---

## Step 3: Scanner ABC + StaticScanner

### File: `argus/data/scanner.py`

Per MD-1 (option c): build the Scanner ABC + a `StaticScanner` implementation.

```python
from abc import ABC, abstractmethod

class Scanner(ABC):
    """Abstract base class for stock scanners.

    The Scanner takes ScannerCriteria from active strategies and produces
    a merged watchlist. Published as a WatchlistEvent on the Event Bus.
    """

    @abstractmethod
    async def scan(self, criteria_list: list[ScannerCriteria]) -> list[WatchlistItem]:
        """Run the scanner with criteria from all active strategies.

        Args:
            criteria_list: Scanner criteria from each active strategy.

        Returns:
            Merged, deduplicated list of WatchlistItems.
        """

    @abstractmethod
    async def start(self) -> None:
        """Initialize scanner resources."""

    @abstractmethod
    async def stop(self) -> None:
        """Clean up scanner resources."""


class StaticScanner(Scanner):
    """Scanner that returns a fixed list of symbols from configuration.

    Used for backtesting, replay, and development. Symbols are defined
    in config/scanner.yaml or injected at construction.

    The StaticScanner ignores ScannerCriteria filters — it always returns
    its configured symbol list. This is intentional: during replay/backtest,
    the watchlist is predetermined from historical data.
    """

    def __init__(self, symbols: list[str]) -> None:
        """Initialize with a fixed symbol list.

        Args:
            symbols: List of ticker symbols to always return.
        """

    async def scan(self, criteria_list: list[ScannerCriteria]) -> list[WatchlistItem]:
        """Return the static symbol list as WatchlistItems.

        Args:
            criteria_list: Ignored by StaticScanner.

        Returns:
            WatchlistItems for each configured symbol.
        """

    async def start(self) -> None:
        """No-op for StaticScanner."""

    async def stop(self) -> None:
        """No-op for StaticScanner."""
```

### Config: `config/scanner.yaml`

```yaml
scanner_type: "static"
static_symbols:
  - "AAPL"
  - "MSFT"
  - "NVDA"
  - "TSLA"
  - "AMD"
```

### Tests (`tests/data/test_scanner.py`):
- `StaticScanner` returns all configured symbols regardless of criteria
- `StaticScanner` returns `WatchlistItem` instances
- `StaticScanner` handles empty symbol list
- `StaticScanner` deduplicates if same symbol appears twice in config

---

## Step 4: Data Service ABC + ReplayDataService

### File: `argus/data/service.py`

Per Architecture doc Section 3.2 and DEC-029 (Event Bus is sole streaming mechanism):

```python
from abc import ABC, abstractmethod

class DataService(ABC):
    """Abstract base class for market data services.

    The Data Service is the single source of market data for the system.
    Streaming data is delivered exclusively via the Event Bus (DEC-029):
    - CandleEvent for completed candles
    - TickEvent for price updates
    - IndicatorEvent for computed indicators

    Synchronous query methods are for point-in-time lookups only.
    """

    @abstractmethod
    async def start(self, symbols: list[str], timeframes: list[str]) -> None:
        """Start streaming data for the given symbols and timeframes.

        Publishes CandleEvent, TickEvent, and IndicatorEvent to the Event Bus.

        Args:
            symbols: List of ticker symbols to stream.
            timeframes: List of timeframe strings (e.g., ["1m"]).
        """

    @abstractmethod
    async def stop(self) -> None:
        """Stop streaming and clean up connections."""

    @abstractmethod
    async def get_current_price(self, symbol: str) -> float | None:
        """Get last known price from in-memory cache.

        Args:
            symbol: Ticker symbol.

        Returns:
            Last known price, or None if no data available.
        """

    @abstractmethod
    async def get_indicator(self, symbol: str, indicator: str) -> float | None:
        """Get current indicator value from in-memory cache.

        Args:
            symbol: Ticker symbol.
            indicator: Indicator name (e.g., "vwap", "atr_14", "sma_20").

        Returns:
            Current indicator value, or None if not yet computed.
        """

    @abstractmethod
    async def get_historical_candles(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """Fetch historical candle data.

        Args:
            symbol: Ticker symbol.
            timeframe: Candle timeframe (e.g., "1m").
            start: Start datetime (inclusive).
            end: End datetime (inclusive).

        Returns:
            DataFrame with columns: open, high, low, close, volume, timestamp.
        """
```

### File: `argus/data/replay_data_service.py`

The ReplayDataService reads Parquet files and drips candle data through the Event Bus.

```python
class ReplayDataService(DataService):
    """Data service that replays historical data from Parquet files.

    Reads 1-minute candle data from Parquet files and publishes CandleEvents
    to the Event Bus. Supports configurable replay speed.

    Multi-timeframe framework (MD-2c): The interface accepts a list of timeframes,
    but Sprint 3 only implements 1m. Other timeframes will be built by aggregating
    1m candles when needed.

    Data format (MD-5a): Parquet only. Expected schema:
        - timestamp: datetime (UTC)
        - open: float
        - high: float
        - low: float
        - close: float
        - volume: int

    Each file represents one symbol's data. File naming: {SYMBOL}.parquet
    (e.g., AAPL.parquet)

    Indicator computation (MD-3a): After publishing each CandleEvent, the
    ReplayDataService computes indicators and publishes IndicatorEvents.
    Indicators computed: VWAP, ATR(14), RVOL, SMA(9), SMA(20), SMA(50).

    Args:
        event_bus: The Event Bus to publish events on.
        data_dir: Path to directory containing Parquet files.
        speed: Replay speed multiplier. 0 = instant (as fast as possible),
               1.0 = real-time, 100.0 = 100x speed.
    """

    def __init__(
        self,
        event_bus: EventBus,
        data_dir: Path,
        speed: float = 0,  # Default: instant replay (for testing)
    ) -> None: ...

    async def start(self, symbols: list[str], timeframes: list[str]) -> None:
        """Load Parquet files for symbols and begin replay.

        For each symbol:
        1. Load the Parquet file from data_dir/{SYMBOL}.parquet
        2. Sort by timestamp
        3. Iterate through candles in chronological order
        4. For each candle: publish CandleEvent, compute & publish IndicatorEvents
        5. If speed > 0, sleep proportionally between candles

        If timeframes contains anything other than "1m", log a warning but continue
        (multi-timeframe not yet implemented).
        """

    async def stop(self) -> None:
        """Stop replay and clean up."""

    async def get_current_price(self, symbol: str) -> float | None:
        """Return the close price of the most recent candle for the symbol."""

    async def get_indicator(self, symbol: str, indicator: str) -> float | None:
        """Return the most recent computed indicator value."""

    async def get_historical_candles(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """Return candles from the loaded Parquet data within the date range."""
```

### Indicator Computation

Indicators are computed incrementally inside the ReplayDataService (MD-3a). After each 1m candle is published, compute and publish IndicatorEvents for:

1. **VWAP** — Running cumulative: `sum(typical_price * volume) / sum(volume)`. Resets daily (on date boundary in the data). Typical price = (high + low + close) / 3.
2. **ATR(14)** — 14-period Average True Range. True Range = max(high-low, |high-prev_close|, |low-prev_close|). Use exponential moving average (Wilder's smoothing). Returns `None` until 14 candles available.
3. **RVOL** — Relative Volume. Requires a baseline. For ReplayDataService V1: use a simple rolling 20-day average volume for the same time-of-day bucket (if historical depth allows), OR just compute cumulative volume vs. a baseline from the data. If insufficient history, return `None`. Keep this simple — a reasonable approximation is fine for Sprint 3.
4. **SMA(9), SMA(20), SMA(50)** — Simple Moving Averages of close prices. Returns `None` until enough candles.

Each indicator is published as an `IndicatorEvent` on the Event Bus immediately after the `CandleEvent` for that candle.

The ReplayDataService maintains an internal `_indicators` dict per symbol for the `get_indicator()` synchronous lookup.

### Parquet Test Data

Create a helper to generate synthetic Parquet test data:

```python
# tests/data/conftest.py or tests/data/test_helpers.py
def generate_test_parquet(
    symbol: str,
    start_date: date,
    num_days: int = 1,
    output_dir: Path,
    base_price: float = 100.0,
    volatility: float = 0.02,
) -> Path:
    """Generate a synthetic 1m Parquet file for testing.

    Creates realistic-ish OHLCV data for market hours (9:30-16:00 ET).
    390 candles per day. Prices follow a random walk with configurable volatility.

    Returns:
        Path to the generated Parquet file.
    """
```

### Tests (`tests/data/test_data_service.py`):
- ReplayDataService loads a Parquet file and publishes CandleEvents
- CandleEvents are published in chronological order
- IndicatorEvents are published after each CandleEvent
- `get_current_price()` returns the latest close
- `get_indicator("AAPL", "vwap")` returns a computed value after candles are published
- `get_indicator()` returns `None` before enough data is available
- VWAP resets on date boundary
- ATR returns `None` before 14 candles, valid value after
- SMA(9) returns `None` before 9 candles, valid value after
- Test with speed=0 (instant replay)
- Test with missing Parquet file raises appropriate error
- Test with unsupported timeframe logs warning but continues

---

## Step 5: ORB Breakout Strategy

### File: `argus/strategies/orb_breakout.py`

The first real strategy. Implements the full ORB lifecycle as defined in Bible Section 4.2 and `config/strategies/orb_breakout.yaml`.

#### ORB Lifecycle (within a single trading day):

**Phase 1: Opening Range Formation (9:30 — 9:30 + orb_window_minutes)**
- Accumulate 1m candles during the opening range window (MD-4a: internal state)
- Track the high and low of all candles in the window
- After the window closes, record the Opening Range: `or_high`, `or_low`, `or_midpoint`
- Validate the range:
  - Range size = `or_high - or_low`
  - Must be >= `min_range_atr_ratio * ATR(14)` (range isn't too tight)
  - Must be <= `max_range_atr_ratio * ATR(14)` (range isn't too wide)
  - If invalid, strategy sits out for the rest of the day (log the reason)

**Phase 2: Watching for Breakout (after OR window — latest_entry time)**
- On each 1m `CandleEvent`:
  - Check if `check_internal_risk_limits()` passes (daily loss, max trades, max positions)
  - Check if current time is within operating window (after OR formation, before `latest_entry`)
  - **Breakout detection** (MD-7 confirmed thresholds):
    1. Candle must **close** above `or_high` (for long). Not just a wick.
    2. Breakout candle volume > `breakout_volume_multiplier` × average volume of candles during OR formation period.
    3. Current price is above VWAP (query DataService `get_indicator(symbol, "vwap")`)
  - **Chase protection** (MD-6a): Skip if close price is already > `or_high * (1 + chase_protection_pct)`. The breakout moved too far without us.
  - If all conditions met: emit `SignalEvent`

**Phase 3: Position active (until exit)**
- Position management is handled by the Order Manager (Sprint 4), not by the strategy
- ORB emits the signal with exit rules; the Order Manager executes them
- The strategy tracks that a position is open (to respect `max_concurrent_positions`)

**Signal Construction:**
```python
SignalEvent(
    strategy_id="strat_orb_breakout",
    symbol=symbol,
    side=OrderSide.BUY,  # Long only (DEC-011)
    entry_price=candle.close,  # Market order at current price (MD-6a)
    stop_price=or_midpoint,  # Midpoint of opening range (DEC-012)
    target_prices=[
        entry_price + (entry_price - stop_price) * target_1_r,  # 1R
        entry_price + (entry_price - stop_price) * target_2_r,  # 2R
    ],
    share_count=self.calculate_position_size(entry_price, stop_price),
    rationale=f"ORB breakout: {symbol} closed above OR high {or_high:.2f}, "
              f"volume {candle.volume} > {threshold}, VWAP {vwap:.2f}",
)
```

**Position Sizing:**
```
risk_per_share = entry_price - stop_price
risk_dollars = allocated_capital * config.risk_limits.max_loss_per_trade_pct
shares = floor(risk_dollars / risk_per_share)
```

#### Strategy-Specific Daily State:
- `_or_high: float | None` — Opening range high
- `_or_low: float | None` — Opening range low
- `_or_candles: list[CandleEvent]` — Candles during OR formation window
- `_or_complete: bool` — Whether the OR window has closed
- `_or_valid: bool` — Whether the OR passed validation
- `_breakout_triggered: bool` — Whether a breakout was already detected today (for this symbol)
- `_daily_pnl: float` — Running P&L for the day
- `_trade_count_today: int` — Trades taken today
- `_active_positions: list` — Currently open positions (tracked by strategy)
- `_watchlist: list[str]` — Today's symbols (set by Scanner)

All of these reset in `reset_daily_state()`.

#### Multi-Symbol Support:
ORB can watch multiple symbols. State is tracked per-symbol. Use a dict keyed by symbol:
```python
_symbol_state: dict[str, OrbSymbolState]
```
Where `OrbSymbolState` is a dataclass holding the per-symbol intraday state.

#### on_candle Implementation Logic:
```
1. If symbol not in watchlist → ignore
2. If OR window not complete for this symbol:
   a. If candle is within OR window time → add to or_candles, update high/low
   b. If candle is first one after OR window → finalize OR, validate
3. If OR complete and valid, and no breakout triggered yet for this symbol:
   a. Check time window (before latest_entry)
   b. Check internal risk limits
   c. Check breakout conditions (close > or_high, volume, VWAP, chase)
   d. If all pass → build and return SignalEvent
4. Return None
```

#### on_tick:
For Sprint 3, `on_tick` is a no-op. ORB uses 1m candles for decisions. Tick-based position management is the Order Manager's job (Sprint 4).

#### get_scanner_criteria:
Return `ScannerCriteria` with ORB's requirements:
```python
ScannerCriteria(
    min_price=10.0,
    max_price=200.0,
    min_volume_avg_daily=1_000_000,
    min_relative_volume=config.volume_threshold_rvol,
    min_gap_pct=0.02,  # 2% gap minimum
    max_results=20,
)
```

#### get_exit_rules:
```python
ExitRules(
    stop_type="fixed",
    stop_price_func="midpoint",
    targets=[
        ProfitTarget(r_multiple=config.target_1_r, position_pct=0.5),
        ProfitTarget(r_multiple=config.target_2_r, position_pct=0.5),
    ],
    time_stop_minutes=config.time_stop_minutes,
)
```

#### get_market_conditions_filter:
```python
MarketConditionsFilter(
    allowed_regimes=["bullish_trending", "range_bound", "high_volatility"],
    max_vix=35.0,
)
```

### Tests (`tests/strategies/test_orb_breakout.py`):

This is the most important test file in Sprint 3. Test every phase of the ORB lifecycle:

**Opening Range Formation:**
- Feed 15 candles (9:30-9:44) → OR high/low/midpoint calculated correctly
- Feed 16th candle (9:45) → OR is finalized
- OR too tight (range < min_range_atr_ratio × ATR) → strategy sits out
- OR too wide (range > max_range_atr_ratio × ATR) → strategy sits out

**Breakout Detection:**
- Candle closes above OR high with volume and VWAP → SignalEvent emitted
- Candle wicks above OR high but closes below → no signal
- Candle closes above OR high but volume too low → no signal
- Candle closes above OR high but below VWAP → no signal
- Candle closes above OR high but past chase protection → no signal

**Signal Correctness:**
- Signal has correct entry_price (candle close)
- Signal has correct stop_price (OR midpoint)
- Signal has correct target_prices (1R and 2R from entry)
- Signal has correct share_count (position sizing formula)

**Risk Limits:**
- After max_trades_per_day reached → no more signals
- After max_daily_loss hit → no more signals
- After max_concurrent_positions reached → no more signals

**Time Window:**
- Candle at 11:31 (after latest_entry) → no signal even if breakout conditions met
- Candle at 9:44 (during OR formation) → never triggers breakout

**State Management:**
- `reset_daily_state()` clears all ORB state
- After reset, strategy can form a new OR on the next day's data

**Multi-Symbol:**
- Feed candles for AAPL and MSFT simultaneously → independent OR tracking
- Breakout in AAPL doesn't affect MSFT's state

**To set up these tests**, you'll need to:
- Create a mock/minimal EventBus (or use the real one from Sprint 1)
- Create synthetic CandleEvent sequences that represent different scenarios
- Use the ReplayDataService or mock `get_indicator()` for VWAP/ATR values

A test helper factory function will be useful:
```python
def make_candle(
    symbol: str = "AAPL",
    timestamp: datetime,
    open: float,
    high: float,
    low: float,
    close: float,
    volume: int = 100_000,
    timeframe: str = "1m",
) -> CandleEvent: ...
```

---

## Step 6: Integration Test

### File: `tests/test_integration_sprint3.py`

A full end-to-end integration test that wires together everything from Sprints 1-3:

```
StaticScanner → provides watchlist
ReplayDataService → reads Parquet, publishes CandleEvents + IndicatorEvents
OrbBreakout → receives candles, forms OR, detects breakout, emits SignalEvent
RiskManager → evaluates signal (should approve)
SimulatedBroker → receives approved order (bracket order: entry + stop + targets)
```

**Test scenario:**
1. Generate a Parquet file with synthetic 1m data for "TEST" stock:
   - 9:30-9:44: Price ranges 99-101 (establishing OR: high=101, low=99, mid=100)
   - 9:45: Breakout candle: open=101, close=102, volume=200,000 (high volume)
   - VWAP should be above 100 (will be computed from the data)
2. Wire up: EventBus → StaticScanner(["TEST"]) → ReplayDataService → OrbBreakout → RiskManager → SimulatedBroker
3. Run the replay
4. Assert:
   - OrbBreakout detected the breakout and emitted a SignalEvent
   - SignalEvent has correct entry (~102), stop (100, midpoint), targets (104, 106)
   - RiskManager approved the signal
   - SimulatedBroker received a bracket order

This is the "everything works together" test. Keep it focused on the happy path. Edge cases are covered in unit tests.

---

## Build Order

1. **DEC-037 fix** (warm-up, ~15 min)
2. **Config models** (OrbBreakoutConfig, DataServiceConfig, ScannerConfig)
3. **Strategy models** (ScannerCriteria, ExitRules, ProfitTarget, MarketConditionsFilter, WatchlistItem)
4. **BaseStrategy ABC** + concrete test strategy + tests
5. **Scanner ABC + StaticScanner** + tests
6. **ReplayDataService** + indicator computation + Parquet test data generator + tests
7. **OrbBreakout strategy** + tests
8. **Integration test**
9. **Full test suite pass + ruff clean**

---

## New Files Created This Sprint

```
argus/strategies/__init__.py
argus/strategies/base_strategy.py
argus/strategies/orb_breakout.py
argus/data/scanner.py
argus/data/service.py
argus/data/replay_data_service.py
argus/models/strategy.py              (or extend existing models/trading.py)
config/scanner.yaml
tests/strategies/__init__.py
tests/strategies/test_base_strategy.py
tests/strategies/test_orb_breakout.py
tests/data/__init__.py (if not existing)
tests/data/test_scanner.py
tests/data/test_data_service.py
tests/test_integration_sprint3.py
```

---

## Decisions In Effect (Do Not Relitigate)

All decisions from DEC-001 through DEC-037 remain active. Key ones for Sprint 3:

| ID | Relevant Rule |
|----|---------------|
| DEC-011 | Long only for V1 |
| DEC-012 | ORB stop at midpoint of opening range |
| DEC-028 | Daily-stateful, session-stateless |
| DEC-029 | Event Bus is sole streaming mechanism. No callbacks on DataService. |
| DEC-032 | Pydantic BaseModel for all config validation |
| DEC-033 | Type-only Event Bus subscription. Filtering in handlers. |
| MD-1 | Scanner ABC + StaticScanner. Real AlpacaScanner in Sprint 4. |
| MD-2 | Multi-timeframe framework, only 1m in Sprint 3. |
| MD-3 | Indicators inside Data Service, published as IndicatorEvent. |
| MD-4 | ORB tracks opening range internally. |
| MD-5 | Parquet only for ReplayDataService. |
| MD-6 | Market order + chase protection filter. |
| MD-7 | Candle close > OR high, volume > 1.5x avg, price > VWAP. |

---

## Documentation Update Protocol

At the END of this sprint, output a "Docs Status" summary per CLAUDE.md rules. Flag any docs that need updating.

---

## Success Criteria

Sprint 3 is done when:
- [ ] DEC-037 implemented and tested
- [ ] BaseStrategy ABC is fully defined with all methods from Architecture doc 3.4
- [ ] StaticScanner returns configured symbols as WatchlistItems
- [ ] ReplayDataService reads Parquet, publishes CandleEvents and IndicatorEvents
- [ ] Indicators (VWAP, ATR, SMA) compute correctly from candle data
- [ ] OrbBreakout forms opening range, detects breakouts, emits correct SignalEvents
- [ ] ORB respects all risk limits, time windows, and chase protection
- [ ] Integration test passes: scanner → data → strategy → risk → broker
- [ ] All tests pass (target: ~150+, up from 112)
- [ ] Ruff clean

*End of Sprint 3 Spec*
