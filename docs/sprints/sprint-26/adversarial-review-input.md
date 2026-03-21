# Sprint 26: Adversarial Review Input Package

> This document provides all context needed for the adversarial review.
> Paste this + the Sprint Spec + the Specification by Contradiction into the adversarial review conversation.

---

## What to Stress-Test

The adversarial reviewer should focus on:

1. **PatternModule ABC interface completeness** — Does the detect()/score()/get_default_params() interface support all planned use cases? Can the BacktestEngine (Sprint 27) consume these cleanly? Is the interface too narrow (missing critical methods) or too broad (unnecessary complexity)?

2. **PatternBasedStrategy composition model** — Is wrapping PatternModule inside BaseStrategy the right approach? Does the delegation model handle all BaseStrategy contract requirements? Are there edge cases where the wrapper breaks the strategy lifecycle?

3. **Detection vs. execution separation** — Is the boundary between pattern detection (PatternModule) and trade execution (PatternBasedStrategy/BaseStrategy) correct? Should exit rules live in the pattern or the strategy wrapper?

4. **R2G state machine design** — Are 5 states sufficient? Does the state machine handle all gap-down reversal scenarios? Is the level-testing logic (VWAP/premarket low/prior close) well-defined?

5. **BacktestEngine forward compatibility** — Sprint 27 will build a BacktestEngine that runs actual strategy code against Databento OHLCV-1m data. Will PatternModule's detect(candles, indicators) interface work with both live CandleEvent streams and historical bar arrays?

6. **Quality Engine integration** — Does the pattern_strength flow (PatternModule.score() → PatternBasedStrategy._calculate_pattern_strength() → SignalEvent.pattern_strength → Quality Engine) work correctly? Any loss of information in the delegation chain?

---

## Architecture Context: BaseStrategy Interface

Every strategy in ARGUS implements `BaseStrategy(ABC)`. The interface has been stable since Sprint 1 and is NOT changing in Sprint 26. Key abstract methods:

```python
class BaseStrategy(ABC):
    @abstractmethod
    async def on_candle(self, event: CandleEvent) -> SignalEvent | None:
        """Process a candle. Return signal if entry criteria met."""

    @abstractmethod
    async def on_tick(self, event: TickEvent) -> None:
        """Process tick updates for position management."""

    @abstractmethod
    def get_scanner_criteria(self) -> ScannerCriteria:
        """Pre-market scanner filters."""

    @abstractmethod
    def calculate_position_size(self, entry_price: float, stop_price: float) -> int:
        """Share count from allocated capital and risk."""

    @abstractmethod
    def get_exit_rules(self) -> ExitRules:
        """Stop, targets, time stop, trailing stop."""

    @abstractmethod
    def get_market_conditions_filter(self) -> MarketConditionsFilter:
        """Regime conditions for activation."""
```

Non-abstract but important:
- `set_watchlist(symbols: list[str], source: str)` — sets `_watchlist: set[str]`
- `reset_daily_state()` — wipes intraday state, clears watchlist
- `reconstruct_state(trade_logger)` — rebuilds from DB after restart
- `record_evaluation(event_type, symbol, result, message, metadata)` — telemetry
- `_calculate_pattern_strength(...)` — convention (not abstract), returns (float 0–100, signal_context dict)

**StrategyConfig** (Pydantic BaseModel):
```python
class StrategyConfig(BaseModel):
    strategy_id: str
    name: str
    version: str = "1.0.0"
    enabled: bool = True
    asset_class: str = "us_stocks"
    pipeline_stage: str = "concept"
    family: str = "uncategorized"
    description_short: str = ""
    time_window_display: str = ""
    backtest_summary: BacktestSummaryConfig = Field(default_factory=BacktestSummaryConfig)
    risk_limits: StrategyRiskLimits = StrategyRiskLimits()
    operating_window: OperatingWindow = OperatingWindow()
    benchmarks: PerformanceBenchmarks = PerformanceBenchmarks()
    universe_filter: UniverseFilterConfig | None = None
```

Each strategy extends StrategyConfig with its own parameters (e.g., VwapReclaimConfig adds min_pullback_pct, max_pullback_pct, etc.).

---

## Architecture Context: SignalEvent

```python
@dataclass(frozen=True)
class SignalEvent(Event):
    strategy_id: str = ""
    symbol: str = ""
    side: Side = Side.LONG
    entry_price: float = 0.0
    stop_price: float = 0.0
    target_prices: tuple[float, ...] = ()
    share_count: int = 0  # Always 0 — Quality Engine + Sizer populate
    rationale: str = ""
    time_stop_seconds: int | None = None
    pattern_strength: float = 50.0  # 0-100, strategy-assessed
    signal_context: dict[str, object] = field(default_factory=dict)
    quality_score: float = 0.0  # Populated by Quality Engine
    quality_grade: str = ""  # Populated by Quality Engine
```

All strategies emit `share_count=0`. The Quality Engine scores the signal, then the Dynamic Position Sizer calculates actual share count. Risk Manager performs final gating (check 0 rejects share_count ≤ 0 before circuit breaker evaluation).

---

## Architecture Context: Quality Engine Pipeline

```
Strategy.on_candle()
  → emits SignalEvent(share_count=0, pattern_strength=X)
  → main.py _process_signal()
    → SetupQualityEngine.score_setup(pattern_strength=X, ...)
      → Returns SetupQuality(score=Y, grade="A", components={...})
    → Filter by minimum_grade
    → DynamicPositionSizer.calculate_shares(quality, entry, stop, capital, power)
      → Returns share_count (or 0 if SKIP grade)
    → Enrich SignalEvent with quality_score, quality_grade, share_count
  → EventBus.publish(enriched SignalEvent)
  → Risk Manager evaluates
```

Quality Engine's `score_setup()` takes `pattern_strength` (0-100) as one input. It doesn't know or care how that value was computed — whether by a custom `_calculate_pattern_strength()` or by `PatternModule.score()`.

---

## Architecture Context: Strategy Registration (main.py Phase 8)

Strategies are created and registered in `main.py` during startup:

```python
# Phase 8: Strategy Instances
# Each strategy is optional — only created if config YAML exists
vwap_yaml = self._config_dir / "strategies" / "vwap_reclaim.yaml"
if vwap_yaml.exists():
    vwap_config = load_vwap_reclaim_config(vwap_yaml)
    vwap_reclaim_strategy = VwapReclaimStrategy(
        config=vwap_config,
        data_service=self._data_service,
        clock=self._clock,
    )
    if not use_universe_manager:
        vwap_reclaim_strategy.set_watchlist(symbols)
    strategies_created.append("VwapReclaim")

# Phase 9: Register with Orchestrator
self._orchestrator.register_strategy(vwap_reclaim_strategy)
```

New strategies follow this exact pattern. No changes to Orchestrator or registration logic needed.

---

## Architecture Context: State Machine Pattern (VWAP Reclaim Reference)

VWAP Reclaim uses a 5-state machine as the model for R2G:

```python
class VwapState(StrEnum):
    WATCHING = "watching"          # Initial — waiting for price vs VWAP
    ABOVE_VWAP = "above_vwap"     # Price above VWAP (prerequisite)
    BELOW_VWAP = "below_vwap"     # Pullback below VWAP, tracking
    ENTERED = "entered"           # Position taken (terminal)
    EXHAUSTED = "exhausted"       # Gave up (max attempts, window expired)

@dataclass
class VwapSymbolState:
    state: VwapState = VwapState.WATCHING
    pullback_low: float = 0.0
    pullback_bars: int = 0
    # ... additional tracking fields
```

Each symbol gets independent state. on_candle() routes to per-state handler methods. State transitions are logged via evaluation telemetry.

---

## Architecture Context: Universe Manager + Strategy Routing

Universe Manager builds a routing table mapping symbols → qualifying strategies. After `build_routing_table()`, it populates each strategy's watchlist via `set_watchlist(symbols, source="universe_manager")`.

**Routing is based on static reference data filters** (UniverseFilterConfig): min_price, max_price, min_market_cap, min_avg_volume, etc. Dynamic conditions (gap direction, VWAP position, consolidation) are checked by the strategy's own `on_candle()` logic.

R2G's universe_filter would include:
```yaml
universe_filter:
  min_price: 5.0
  max_price: 200.0
  min_avg_volume: 500000
```

Gap-down detection is NOT part of the universe filter — it's a dynamic check in R2G's on_candle().

---

## Architecture Context: VectorBT Backtesting Pattern

Existing VectorBT modules follow this structure:
1. Strategy-specific signal generation function (vectorized)
2. Parameter grid definition
3. Walk-forward engine integration
4. Report generation (backtest summary with WFE, Sharpe, trade count)

Walk-forward validation (DEC-047): WFE > 0.3 required. Walk-forward uses the engine in `backtest/walk_forward.py`. Results are provisional until re-validated with Databento data via BacktestEngine (Sprint 27, DEC-132).

---

## Relevant DEC Entries

- **DEC-028:** Strategies are daily-stateful, session-stateless
- **DEC-047:** Walk-forward validation mandatory, WFE > 0.3
- **DEC-120:** OrbBaseStrategy ABC established the family ABC pattern
- **DEC-132:** All pre-Databento backtests provisional
- **DEC-163:** 15+ artisanal patterns vision
- **DEC-239:** Quality Engine 0–100 scoring with pattern_strength input
- **DEC-277:** Fail-closed on missing reference data
- **DEC-300:** Config-gated features (default enabled, gated in YAML)
- **DEC-330/331:** Strategies emit share_count=0 with pattern_strength for Quality Engine pipeline
- **DEC-342:** Strategy evaluation telemetry via record_evaluation()
- **DEC-343:** Watchlist from UM via set_watchlist(symbols, source="universe_manager")
- **DEC-354:** Sprint 26 is last sprint using VectorBT before BacktestEngine

---

## Proposed PatternModule ABC Design

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

@dataclass
class PatternDetection:
    """Result of a successful pattern detection."""
    pattern_type: str          # e.g., "bull_flag", "flat_top_breakout"
    confidence: float          # 0-100, how strong the pattern match is
    entry_price: float         # Suggested entry price
    stop_price: float          # Suggested stop price
    metadata: dict = field(default_factory=dict)  # Pattern-specific context

class PatternModule(ABC):
    """Abstract base class for pattern detection modules.

    Patterns are pure detection logic — they identify chart patterns
    in candle data and score them. They do NOT handle:
    - Operating windows (PatternBasedStrategy handles)
    - Position sizing (Quality Engine + Sizer handles)
    - State management (PatternBasedStrategy handles)
    - Signal generation (PatternBasedStrategy handles)
    """

    @abstractmethod
    def detect(
        self,
        candles: list[dict],   # List of OHLCV candle dicts
        indicators: dict,      # Indicator values (vwap, atr, rvol, etc.)
    ) -> PatternDetection | None:
        """Detect a pattern in the given candle sequence.

        Args:
            candles: Recent candle history (most recent last).
                     Each candle: {open, high, low, close, volume, timestamp}
            indicators: Current indicator values from IndicatorEngine.

        Returns:
            PatternDetection if pattern found, None otherwise.
        """

    @abstractmethod
    def score(self, detection: PatternDetection) -> float:
        """Score the quality of a detected pattern (0-100).

        Used as pattern_strength input to Quality Engine.
        """

    @abstractmethod
    def get_default_params(self) -> dict:
        """Return default parameter values for this pattern.

        Used by BacktestEngine for parameter sweep configuration
        and by the Pattern Library UI for parameter display.
        """
```

**Key design question for adversarial review:** Is `candles: list[dict]` the right type? It's flexible (works with both live CandleEvent streams converted to dicts and historical bar arrays from BacktestEngine), but it loses type safety. Alternative: define a `CandleBar` dataclass and use `list[CandleBar]`.

**Key design question:** Should `detect()` receive the full candle history (potentially thousands of bars) or a windowed subset? The caller (PatternBasedStrategy or BacktestEngine) would need to manage the window size. This affects memory usage and detection semantics.
