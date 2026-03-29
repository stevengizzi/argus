"""Tests for BacktestEngine — component assembly, strategy factory, and day loop.

Sprint 27 Session 3: Verifies _setup() wires SyncEventBus (not EventBus),
FixedClock, SimulatedBroker, and _create_strategy() handles all 7 types.

Sprint 27 Session 4: Verifies single-day bar loop, chronological multi-symbol
interleaving, bar-level fill model with worst-case priority, signal routing,
watchlist scoping, and daily state reset.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from argus.backtest.config import BacktestEngineConfig, StrategyType
from argus.backtest.engine import BacktestEngine
from argus.core.clock import FixedClock
from argus.core.events import CandleEvent, OrderFilledEvent, SignalEvent, Side
from argus.core.sync_event_bus import SyncEventBus
from argus.execution.simulated_broker import (
    PendingBracketOrder,
    SimulatedBroker,
)
from argus.models.trading import OrderSide, OrderStatus
from argus.strategies.afternoon_momentum import AfternoonMomentumStrategy
from argus.strategies.orb_breakout import OrbBreakoutStrategy
from argus.strategies.orb_scalp import OrbScalpStrategy
from argus.strategies.pattern_strategy import PatternBasedStrategy
from argus.strategies.patterns.bull_flag import BullFlagPattern
from argus.strategies.patterns.flat_top_breakout import FlatTopBreakoutPattern
from argus.strategies.red_to_green import RedToGreenStrategy
from argus.strategies.vwap_reclaim import VwapReclaimStrategy

ET = ZoneInfo("America/New_York")


@pytest.fixture
def engine_config(tmp_path: Path) -> BacktestEngineConfig:
    """Create a BacktestEngineConfig with a temp output directory."""
    return BacktestEngineConfig(
        start_date=date(2025, 6, 16),
        end_date=date(2025, 6, 20),
        output_dir=tmp_path / "backtest_runs",
        strategy_type=StrategyType.ORB_BREAKOUT,
        strategy_id="strat_orb_breakout",
        log_level="WARNING",
    )


def _make_config(
    tmp_path: Path,
    strategy_type: StrategyType,
    strategy_id: str,
) -> BacktestEngineConfig:
    """Helper to build engine config for a given strategy type."""
    return BacktestEngineConfig(
        start_date=date(2025, 6, 16),
        end_date=date(2025, 6, 20),
        output_dir=tmp_path / "backtest_runs",
        strategy_type=strategy_type,
        strategy_id=strategy_id,
        log_level="WARNING",
    )


@pytest.mark.asyncio
async def test_setup_creates_sync_event_bus(
    engine_config: BacktestEngineConfig,
) -> None:
    """Verify _event_bus is SyncEventBus, not production EventBus."""
    engine = BacktestEngine(engine_config)
    await engine._setup()
    try:
        assert isinstance(engine._event_bus, SyncEventBus)
        # Confirm it is NOT the production EventBus
        from argus.core.event_bus import EventBus

        assert not isinstance(engine._event_bus, EventBus)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_setup_creates_fixed_clock(
    engine_config: BacktestEngineConfig,
) -> None:
    """Verify _clock is FixedClock."""
    engine = BacktestEngine(engine_config)
    await engine._setup()
    try:
        assert isinstance(engine._clock, FixedClock)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_setup_creates_simulated_broker(
    engine_config: BacktestEngineConfig,
) -> None:
    """Verify _broker is SimulatedBroker."""
    engine = BacktestEngine(engine_config)
    await engine._setup()
    try:
        assert isinstance(engine._broker, SimulatedBroker)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_orb_breakout(tmp_path: Path) -> None:
    """strategy_type=ORB_BREAKOUT creates OrbBreakoutStrategy."""
    config = _make_config(tmp_path, StrategyType.ORB_BREAKOUT, "strat_orb_breakout")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, OrbBreakoutStrategy)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_orb_scalp(tmp_path: Path) -> None:
    """strategy_type=ORB_SCALP creates OrbScalpStrategy."""
    config = _make_config(tmp_path, StrategyType.ORB_SCALP, "strat_orb_scalp")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, OrbScalpStrategy)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_vwap_reclaim(tmp_path: Path) -> None:
    """strategy_type=VWAP_RECLAIM creates VwapReclaimStrategy."""
    config = _make_config(tmp_path, StrategyType.VWAP_RECLAIM, "strat_vwap_reclaim")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, VwapReclaimStrategy)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_afternoon_momentum(tmp_path: Path) -> None:
    """strategy_type=AFTERNOON_MOMENTUM creates AfternoonMomentumStrategy."""
    config = _make_config(
        tmp_path, StrategyType.AFTERNOON_MOMENTUM, "strat_afternoon_momentum"
    )
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, AfternoonMomentumStrategy)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_red_to_green(tmp_path: Path) -> None:
    """strategy_type=RED_TO_GREEN creates RedToGreenStrategy."""
    config = _make_config(tmp_path, StrategyType.RED_TO_GREEN, "strat_red_to_green")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, RedToGreenStrategy)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_bull_flag(tmp_path: Path) -> None:
    """strategy_type=BULL_FLAG creates PatternBasedStrategy wrapping BullFlagPattern."""
    config = _make_config(tmp_path, StrategyType.BULL_FLAG, "strat_bull_flag")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, PatternBasedStrategy)
        assert isinstance(engine._strategy._pattern, BullFlagPattern)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_flat_top(tmp_path: Path) -> None:
    """strategy_type=FLAT_TOP_BREAKOUT creates PatternBasedStrategy wrapping FlatTopBreakoutPattern."""
    config = _make_config(
        tmp_path, StrategyType.FLAT_TOP_BREAKOUT, "strat_flat_top_breakout"
    )
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, PatternBasedStrategy)
        assert isinstance(engine._strategy._pattern, FlatTopBreakoutPattern)
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_factory_unknown_raises(tmp_path: Path) -> None:
    """Invalid strategy type raises ValueError."""
    config = _make_config(tmp_path, StrategyType.ORB_BREAKOUT, "strat_test")
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        # Temporarily override to an invalid value
        engine._config.strategy_type = "not_a_strategy"  # type: ignore[assignment]
        with pytest.raises(ValueError, match="Unknown strategy type"):
            engine._create_strategy(Path("config"))
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_teardown_cleans_up(tmp_path: Path) -> None:
    """run() with no data returns empty result (no setup/teardown needed)."""
    empty_cache = tmp_path / "empty_cache"
    empty_cache.mkdir()
    config = BacktestEngineConfig(
        start_date=date(2025, 6, 16),
        end_date=date(2025, 6, 20),
        output_dir=tmp_path / "backtest_runs",
        strategy_type=StrategyType.ORB_BREAKOUT,
        strategy_id="strat_orb_breakout",
        cache_dir=empty_cache,
        log_level="WARNING",
    )
    engine = BacktestEngine(config)
    result = await engine.run()

    # Verify result is returned with empty metrics
    assert result.strategy_id == "strat_orb_breakout"
    assert result.total_trades == 0
    assert result.initial_capital == 100_000.0


@pytest.mark.asyncio
async def test_allocated_capital_set_on_strategy(tmp_path: Path) -> None:
    """Verify allocated_capital is set on the strategy after _setup."""
    config = _make_config(tmp_path, StrategyType.ORB_BREAKOUT, "strat_orb_breakout")
    config.initial_cash = 50_000.0
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert engine._strategy is not None
        assert engine._strategy.allocated_capital == 50_000.0
    finally:
        await engine._teardown()


@pytest.mark.asyncio
async def test_config_overrides_applied(tmp_path: Path) -> None:
    """Verify config_overrides from BacktestEngineConfig are applied to strategy config."""
    config = _make_config(tmp_path, StrategyType.ORB_BREAKOUT, "strat_orb_breakout")
    config.config_overrides = {"orb_window_minutes": 20}
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        assert isinstance(engine._strategy, OrbBreakoutStrategy)
        assert engine._strategy._config.orb_window_minutes == 20
    finally:
        await engine._teardown()


# ---------------------------------------------------------------------------
# Sprint 27 Session 4: Day loop + fill model tests
# ---------------------------------------------------------------------------

TRADING_DAY = date(2025, 6, 16)


def _make_bar_df(
    symbol: str,
    trading_day: date,
    bars: list[tuple[int, int, float, float, float, float, int]],
) -> pd.DataFrame:
    """Build a bar DataFrame from (hour, minute, open, high, low, close, vol).

    Returns DataFrame with columns matching HistoricalDataFeed output:
    timestamp (UTC-aware), open, high, low, close, volume, trading_date.
    """
    rows: list[dict[str, object]] = []
    for h, m, o, hi, lo, c, v in bars:
        ts = datetime(
            trading_day.year, trading_day.month, trading_day.day,
            h, m, 0, tzinfo=ET,
        ).astimezone(UTC)
        rows.append({
            "timestamp": ts,
            "open": o, "high": hi, "low": lo, "close": c,
            "volume": v, "trading_date": trading_day,
        })
    return pd.DataFrame(rows)


async def _setup_engine_with_bars(
    tmp_path: Path,
    bar_data: dict[str, pd.DataFrame],
    slippage: float = 0.0,
) -> BacktestEngine:
    """Create and set up a BacktestEngine with pre-loaded bar data.

    Bypasses HistoricalDataFeed by injecting bar data directly.
    Sets slippage to 0 by default for deterministic fill prices.
    """
    config = _make_config(
        tmp_path, StrategyType.ORB_BREAKOUT, "strat_orb_breakout"
    )
    config.slippage_per_share = slippage
    engine = BacktestEngine(config)
    await engine._setup()

    # Inject bar data directly (bypass HistoricalDataFeed)
    engine._bar_data = bar_data

    # Extract trading days
    all_dates: set[date] = set()
    for df in bar_data.values():
        if not df.empty and "trading_date" in df.columns:
            all_dates.update(df["trading_date"].unique())
    engine._trading_days = sorted(all_dates)

    return engine


# --- Test 1: Bars processed in chronological order across symbols ---

@pytest.mark.asyncio
async def test_single_day_bars_chronological(tmp_path: Path) -> None:
    """Bars are fed in timestamp order across multiple symbols."""
    bars_a = _make_bar_df("AAPL", TRADING_DAY, [
        (9, 30, 150.0, 151.0, 149.0, 150.5, 1000),
        (9, 32, 150.5, 152.0, 150.0, 151.0, 1200),
    ])
    bars_b = _make_bar_df("TSLA", TRADING_DAY, [
        (9, 31, 200.0, 201.0, 199.0, 200.5, 800),
        (9, 33, 200.5, 202.0, 200.0, 201.0, 900),
    ])

    engine = await _setup_engine_with_bars(
        tmp_path, {"AAPL": bars_a, "TSLA": bars_b}
    )

    fed_symbols: list[str] = []
    original_feed_bar = engine._data_service.feed_bar  # type: ignore[union-attr]

    async def tracking_feed_bar(
        symbol: str, **kwargs: object
    ) -> None:
        fed_symbols.append(symbol)
        await original_feed_bar(symbol=symbol, **kwargs)

    engine._data_service.feed_bar = tracking_feed_bar  # type: ignore[union-attr, assignment]

    try:
        await engine._run_trading_day(
            TRADING_DAY, ["AAPL", "TSLA"]
        )
        # Interleaved: AAPL(9:30), TSLA(9:31), AAPL(9:32), TSLA(9:33)
        assert fed_symbols == ["AAPL", "TSLA", "AAPL", "TSLA"]
    finally:
        await engine._teardown()


# --- Test 2: Clock advances per bar ---

@pytest.mark.asyncio
async def test_clock_advances_per_bar(tmp_path: Path) -> None:
    """FixedClock.set() is called with each bar's timestamp."""
    bars = _make_bar_df("AAPL", TRADING_DAY, [
        (9, 30, 150.0, 151.0, 149.0, 150.5, 1000),
        (9, 31, 150.5, 152.0, 150.0, 151.0, 1200),
        (9, 32, 151.0, 153.0, 150.5, 152.0, 1100),
    ])

    engine = await _setup_engine_with_bars(tmp_path, {"AAPL": bars})
    assert engine._clock is not None

    clock_times: list[datetime] = []
    original_set = engine._clock.set

    def tracking_set(t: datetime) -> None:
        clock_times.append(t)
        original_set(t)

    engine._clock.set = tracking_set  # type: ignore[assignment]

    try:
        await engine._run_trading_day(TRADING_DAY, ["AAPL"])
        # Pre-market + 3 bars + EOD = 5 set() calls
        assert len(clock_times) == 5
        # Bars should be 9:30, 9:31, 9:32 ET (converted to UTC)
        bar_times = clock_times[1:4]  # Skip pre-market, before EOD
        for i in range(len(bar_times) - 1):
            assert bar_times[i] < bar_times[i + 1]
    finally:
        await engine._teardown()


# --- Test 3: CandleEvent dispatched to strategy ---

@pytest.mark.asyncio
async def test_candle_event_dispatched(tmp_path: Path) -> None:
    """strategy.on_candle() is called for each bar."""
    bars = _make_bar_df("AAPL", TRADING_DAY, [
        (9, 30, 150.0, 151.0, 149.0, 150.5, 1000),
        (9, 31, 150.5, 152.0, 150.0, 151.0, 1200),
    ])

    engine = await _setup_engine_with_bars(tmp_path, {"AAPL": bars})
    assert engine._strategy is not None

    candle_calls: list[CandleEvent] = []
    original_on_candle = engine._strategy.on_candle

    async def tracking_on_candle(event: CandleEvent) -> object:
        candle_calls.append(event)
        return await original_on_candle(event)

    engine._strategy.on_candle = tracking_on_candle  # type: ignore[assignment]

    try:
        await engine._run_trading_day(TRADING_DAY, ["AAPL"])
        assert len(candle_calls) == 2
        assert all(c.symbol == "AAPL" for c in candle_calls)
    finally:
        await engine._teardown()


# --- Test 4: Indicators computed after sufficient bars ---

@pytest.mark.asyncio
async def test_indicators_computed(tmp_path: Path) -> None:
    """BacktestDataService produces VWAP after feeding bars."""
    # VWAP needs at least 1 bar with volume
    bars = _make_bar_df("AAPL", TRADING_DAY, [
        (9, 30, 150.0, 151.0, 149.0, 150.5, 1000),
        (9, 31, 150.5, 152.0, 150.0, 151.0, 1200),
        (9, 32, 151.0, 153.0, 150.5, 152.0, 1100),
    ])

    engine = await _setup_engine_with_bars(tmp_path, {"AAPL": bars})
    assert engine._data_service is not None

    try:
        await engine._run_trading_day(TRADING_DAY, ["AAPL"])
        vwap = await engine._data_service.get_indicator("AAPL", "vwap")
        assert vwap is not None
        assert vwap > 0.0
    finally:
        await engine._teardown()


# --- Test 5: Fill model — stop priority when both stop and target hit ---

@pytest.mark.asyncio
async def test_fill_model_stop_priority(tmp_path: Path) -> None:
    """Bar hits both stop and target → stop fills (worst case for longs)."""
    engine = await _setup_engine_with_bars(tmp_path, {})
    assert engine._broker is not None and engine._event_bus is not None

    # Register a stop at 95.0 and a target at 110.0
    engine._broker._pending_brackets = [
        PendingBracketOrder(
            order_id="stop_1", symbol="AAPL", side=OrderSide.SELL,
            quantity=100, trigger_price=95.0, order_type="stop",
            parent_position_symbol="AAPL", strategy_id="test",
        ),
        PendingBracketOrder(
            order_id="target_1", symbol="AAPL", side=OrderSide.SELL,
            quantity=50, trigger_price=110.0, order_type="limit",
            parent_position_symbol="AAPL", strategy_id="test",
        ),
    ]

    # Create a position so broker can fill the sell
    from argus.models.trading import Order
    engine._broker.set_price("AAPL", 100.0)
    await engine._broker.place_order(Order(
        strategy_id="test", symbol="AAPL", side=OrderSide.BUY,
        quantity=100, limit_price=100.0,
    ))

    fills: list[OrderFilledEvent] = []

    async def collect_fill(e: OrderFilledEvent) -> None:
        fills.append(e)

    engine._event_bus.subscribe(OrderFilledEvent, collect_fill)

    bar_ts = datetime(2025, 6, 16, 10, 0, tzinfo=UTC)
    # Bar that hits both stop (low=94) and target (high=112)
    await engine._check_bracket_orders(
        symbol="AAPL", bar_high=112.0, bar_low=94.0,
        bar_close=105.0, bar_timestamp=bar_ts,
    )

    try:
        # Stop should win — fill at stop price
        assert len(fills) == 1
        assert fills[0].fill_price == 95.0
    finally:
        await engine._teardown()


# --- Test 6: Fill model — stop only ---

@pytest.mark.asyncio
async def test_fill_model_stop_only(tmp_path: Path) -> None:
    """Bar low reaches stop, high doesn't reach target → stop fills."""
    engine = await _setup_engine_with_bars(tmp_path, {})
    assert engine._broker is not None and engine._event_bus is not None

    engine._broker._pending_brackets = [
        PendingBracketOrder(
            order_id="stop_1", symbol="AAPL", side=OrderSide.SELL,
            quantity=100, trigger_price=95.0, order_type="stop",
            parent_position_symbol="AAPL", strategy_id="test",
        ),
        PendingBracketOrder(
            order_id="target_1", symbol="AAPL", side=OrderSide.SELL,
            quantity=50, trigger_price=110.0, order_type="limit",
            parent_position_symbol="AAPL", strategy_id="test",
        ),
    ]

    from argus.models.trading import Order
    engine._broker.set_price("AAPL", 100.0)
    await engine._broker.place_order(Order(
        strategy_id="test", symbol="AAPL", side=OrderSide.BUY,
        quantity=100, limit_price=100.0,
    ))

    fills: list[OrderFilledEvent] = []

    async def collect_fill(e: OrderFilledEvent) -> None:
        fills.append(e)

    engine._event_bus.subscribe(OrderFilledEvent, collect_fill)

    bar_ts = datetime(2025, 6, 16, 10, 0, tzinfo=UTC)
    # Bar hits stop (low=94) but NOT target (high=108 < 110)
    await engine._check_bracket_orders(
        symbol="AAPL", bar_high=108.0, bar_low=94.0,
        bar_close=96.0, bar_timestamp=bar_ts,
    )

    try:
        assert len(fills) == 1
        assert fills[0].fill_price == 95.0
    finally:
        await engine._teardown()


# --- Test 7: Fill model — target only ---

@pytest.mark.asyncio
async def test_fill_model_target_only(tmp_path: Path) -> None:
    """Bar high reaches target, low doesn't reach stop → target fills."""
    engine = await _setup_engine_with_bars(tmp_path, {})
    assert engine._broker is not None and engine._event_bus is not None

    engine._broker._pending_brackets = [
        PendingBracketOrder(
            order_id="stop_1", symbol="AAPL", side=OrderSide.SELL,
            quantity=100, trigger_price=95.0, order_type="stop",
            parent_position_symbol="AAPL", strategy_id="test",
        ),
        PendingBracketOrder(
            order_id="target_1", symbol="AAPL", side=OrderSide.SELL,
            quantity=50, trigger_price=110.0, order_type="limit",
            parent_position_symbol="AAPL", strategy_id="test",
        ),
    ]

    from argus.models.trading import Order
    engine._broker.set_price("AAPL", 100.0)
    await engine._broker.place_order(Order(
        strategy_id="test", symbol="AAPL", side=OrderSide.BUY,
        quantity=100, limit_price=100.0,
    ))

    fills: list[OrderFilledEvent] = []

    async def collect_fill(e: OrderFilledEvent) -> None:
        fills.append(e)

    engine._event_bus.subscribe(OrderFilledEvent, collect_fill)

    bar_ts = datetime(2025, 6, 16, 10, 0, tzinfo=UTC)
    # Bar hits target (high=112) but NOT stop (low=98 > 95)
    await engine._check_bracket_orders(
        symbol="AAPL", bar_high=112.0, bar_low=98.0,
        bar_close=111.0, bar_timestamp=bar_ts,
    )

    try:
        assert len(fills) == 1
        assert fills[0].fill_price == 110.0
    finally:
        await engine._teardown()


# --- Test 8: Fill model — time stop with stop check ---

@pytest.mark.asyncio
async def test_fill_model_time_stop_with_stop_check(
    tmp_path: Path,
) -> None:
    """Time stop fires on bar where low also hits stop → stop price used."""
    engine = await _setup_engine_with_bars(tmp_path, {})
    assert engine._broker is not None
    assert engine._order_manager is not None

    # Create a position via broker
    from argus.models.trading import Order
    engine._broker.set_price("AAPL", 100.0)
    await engine._broker.place_order(Order(
        strategy_id="test", symbol="AAPL", side=OrderSide.BUY,
        quantity=100, limit_price=100.0,
    ))

    # Register stop bracket
    engine._broker._pending_brackets = [
        PendingBracketOrder(
            order_id="stop_1", symbol="AAPL", side=OrderSide.SELL,
            quantity=100, trigger_price=95.0, order_type="stop",
            parent_position_symbol="AAPL", strategy_id="test",
        ),
    ]

    # Create a managed position with time_stop_seconds
    from argus.execution.order_manager import ManagedPosition
    entry_time = datetime(2025, 6, 16, 9, 35, tzinfo=UTC)
    managed = ManagedPosition(
        symbol="AAPL", strategy_id="test", entry_price=100.0,
        entry_time=entry_time, shares_total=100, shares_remaining=100,
        stop_price=95.0, original_stop_price=95.0, stop_order_id="stop_1",
        t1_price=110.0, t1_order_id=None, t1_shares=50, t1_filled=False,
        t2_price=120.0, high_watermark=100.0, time_stop_seconds=300,
    )
    engine._order_manager._managed_positions["AAPL"] = [managed]
    engine._order_manager._pending_orders["stop_1"] = (
        engine._order_manager._pending_orders.get("stop_1")
        or type("PO", (), {
            "order_id": "stop_1", "symbol": "AAPL",
            "strategy_id": "test", "order_type": "stop", "shares": 100,
        })()
    )

    # Bar timestamp 10 minutes after entry (> 300s time stop)
    bar_ts = entry_time + timedelta(minutes=10)
    # Bar low also hits stop (94 < 95)
    await engine._check_time_stop(
        symbol="AAPL", bar_low=94.0, bar_close=97.0,
        bar_timestamp=bar_ts,
    )

    try:
        # Should have closed at stop price (95.0), not close price (97.0)
        assert engine._broker._current_prices.get("AAPL") == 95.0
    finally:
        await engine._teardown()


# --- Test 9: Fill model — time stop clean (no stop hit) ---

@pytest.mark.asyncio
async def test_fill_model_time_stop_clean(tmp_path: Path) -> None:
    """Time stop fires on bar where low doesn't hit stop → close price."""
    engine = await _setup_engine_with_bars(tmp_path, {})
    assert engine._broker is not None
    assert engine._order_manager is not None

    from argus.models.trading import Order
    engine._broker.set_price("AAPL", 100.0)
    await engine._broker.place_order(Order(
        strategy_id="test", symbol="AAPL", side=OrderSide.BUY,
        quantity=100, limit_price=100.0,
    ))

    engine._broker._pending_brackets = [
        PendingBracketOrder(
            order_id="stop_1", symbol="AAPL", side=OrderSide.SELL,
            quantity=100, trigger_price=95.0, order_type="stop",
            parent_position_symbol="AAPL", strategy_id="test",
        ),
    ]

    from argus.execution.order_manager import ManagedPosition
    entry_time = datetime(2025, 6, 16, 9, 35, tzinfo=UTC)
    managed = ManagedPosition(
        symbol="AAPL", strategy_id="test", entry_price=100.0,
        entry_time=entry_time, shares_total=100, shares_remaining=100,
        stop_price=95.0, original_stop_price=95.0, stop_order_id="stop_1",
        t1_price=110.0, t1_order_id=None, t1_shares=50, t1_filled=False,
        t2_price=120.0, high_watermark=100.0, time_stop_seconds=300,
    )
    engine._order_manager._managed_positions["AAPL"] = [managed]
    engine._order_manager._pending_orders["stop_1"] = (
        engine._order_manager._pending_orders.get("stop_1")
        or type("PO", (), {
            "order_id": "stop_1", "symbol": "AAPL",
            "strategy_id": "test", "order_type": "stop", "shares": 100,
        })()
    )

    bar_ts = entry_time + timedelta(minutes=10)
    # Bar low does NOT hit stop (96 > 95)
    await engine._check_time_stop(
        symbol="AAPL", bar_low=96.0, bar_close=97.0,
        bar_timestamp=bar_ts,
    )

    try:
        # Should have closed at close price (97.0)
        assert engine._broker._current_prices.get("AAPL") == 97.0
    finally:
        await engine._teardown()


# --- Test 10: Fill model — no trigger ---

@pytest.mark.asyncio
async def test_fill_model_no_trigger(tmp_path: Path) -> None:
    """Bar doesn't reach stop or target → no fill."""
    engine = await _setup_engine_with_bars(tmp_path, {})
    assert engine._broker is not None and engine._event_bus is not None

    engine._broker._pending_brackets = [
        PendingBracketOrder(
            order_id="stop_1", symbol="AAPL", side=OrderSide.SELL,
            quantity=100, trigger_price=95.0, order_type="stop",
            parent_position_symbol="AAPL", strategy_id="test",
        ),
        PendingBracketOrder(
            order_id="target_1", symbol="AAPL", side=OrderSide.SELL,
            quantity=50, trigger_price=110.0, order_type="limit",
            parent_position_symbol="AAPL", strategy_id="test",
        ),
    ]

    fills: list[OrderFilledEvent] = []

    async def collect_fill(e: OrderFilledEvent) -> None:
        fills.append(e)

    engine._event_bus.subscribe(OrderFilledEvent, collect_fill)

    bar_ts = datetime(2025, 6, 16, 10, 0, tzinfo=UTC)
    # Bar between stop and target (low=96 > 95, high=108 < 110)
    await engine._check_bracket_orders(
        symbol="AAPL", bar_high=108.0, bar_low=96.0,
        bar_close=102.0, bar_timestamp=bar_ts,
    )

    try:
        assert len(fills) == 0
        # Brackets should still be pending
        assert len(engine._broker._pending_brackets) == 2
    finally:
        await engine._teardown()


# --- Test 11: No trade day ---

@pytest.mark.asyncio
async def test_no_trade_day(tmp_path: Path) -> None:
    """No signals generated → zero fills."""
    bars = _make_bar_df("AAPL", TRADING_DAY, [
        (9, 30, 150.0, 151.0, 149.0, 150.5, 1000),
        (9, 31, 150.5, 152.0, 150.0, 151.0, 1200),
    ])

    engine = await _setup_engine_with_bars(tmp_path, {"AAPL": bars})
    assert engine._broker is not None

    try:
        await engine._run_trading_day(TRADING_DAY, ["AAPL"])
        # No signals → no bracket orders → no fills
        positions = await engine._broker.get_positions()
        assert len(positions) == 0
    finally:
        await engine._teardown()


# --- Test 12: Multi-symbol day ---

@pytest.mark.asyncio
async def test_multi_symbol_day(tmp_path: Path) -> None:
    """3 symbols, bars interleaved correctly, each symbol receives bars."""
    bars_a = _make_bar_df("AAPL", TRADING_DAY, [
        (9, 30, 150.0, 151.0, 149.0, 150.5, 1000),
    ])
    bars_t = _make_bar_df("TSLA", TRADING_DAY, [
        (9, 30, 200.0, 201.0, 199.0, 200.5, 800),
    ])
    bars_n = _make_bar_df("NVDA", TRADING_DAY, [
        (9, 30, 300.0, 301.0, 299.0, 300.5, 600),
    ])

    engine = await _setup_engine_with_bars(
        tmp_path, {"AAPL": bars_a, "TSLA": bars_t, "NVDA": bars_n}
    )
    assert engine._data_service is not None

    fed_symbols: list[str] = []
    original = engine._data_service.feed_bar

    async def track(symbol: str, **kwargs: object) -> None:
        fed_symbols.append(symbol)
        await original(symbol=symbol, **kwargs)

    engine._data_service.feed_bar = track  # type: ignore[assignment]

    try:
        await engine._run_trading_day(
            TRADING_DAY, ["AAPL", "TSLA", "NVDA"]
        )
        assert set(fed_symbols) == {"AAPL", "TSLA", "NVDA"}
        assert len(fed_symbols) == 3
    finally:
        await engine._teardown()


# --- Test 13: Watchlist scoping ---

@pytest.mark.asyncio
async def test_watchlist_scoping(tmp_path: Path) -> None:
    """Strategy only receives candles for watchlist symbols."""
    bars_a = _make_bar_df("AAPL", TRADING_DAY, [
        (9, 30, 150.0, 151.0, 149.0, 150.5, 1000),
    ])
    bars_t = _make_bar_df("TSLA", TRADING_DAY, [
        (9, 31, 200.0, 201.0, 199.0, 200.5, 800),
    ])

    engine = await _setup_engine_with_bars(
        tmp_path, {"AAPL": bars_a, "TSLA": bars_t}
    )
    assert engine._strategy is not None

    candle_symbols: list[str] = []
    original_on_candle = engine._strategy.on_candle

    async def track_candle(event: CandleEvent) -> object:
        candle_symbols.append(event.symbol)
        return await original_on_candle(event)

    engine._strategy.on_candle = track_candle  # type: ignore[assignment]

    try:
        # Only AAPL in watchlist, but both symbols have data
        await engine._run_trading_day(TRADING_DAY, ["AAPL"])
        # Data service feeds only watchlist symbols
        assert candle_symbols == ["AAPL"]
    finally:
        await engine._teardown()


# --- Test 14: Signal to order pipeline ---

@pytest.mark.asyncio
async def test_signal_to_order_pipeline(tmp_path: Path) -> None:
    """Signal → risk eval → order submission end-to-end."""
    bars = _make_bar_df("AAPL", TRADING_DAY, [
        (9, 30, 150.0, 151.0, 149.0, 150.5, 1000),
    ])

    engine = await _setup_engine_with_bars(tmp_path, {"AAPL": bars})
    assert engine._strategy is not None
    assert engine._risk_manager is not None
    assert engine._event_bus is not None

    # Mock the strategy to emit a signal on any candle
    test_signal = SignalEvent(
        strategy_id="strat_orb_breakout",
        symbol="AAPL",
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0, 154.0),
        share_count=50,
        rationale="test signal",
    )

    original_on_candle = engine._strategy.on_candle

    async def signal_on_candle(event: CandleEvent) -> SignalEvent | None:
        await original_on_candle(event)
        if event.symbol == "AAPL":
            return test_signal
        return None

    engine._strategy.on_candle = signal_on_candle  # type: ignore[assignment]

    # Track events published to bus
    published_events: list[object] = []
    original_publish = engine._event_bus.publish

    async def tracking_publish(event: object) -> None:
        published_events.append(event)
        await original_publish(event)

    engine._event_bus.publish = tracking_publish  # type: ignore[assignment]

    try:
        await engine._run_trading_day(TRADING_DAY, ["AAPL"])

        # Should have published at least: CandleEvent + IndicatorEvents +
        # OrderApprovedEvent or OrderRejectedEvent
        from argus.core.events import OrderApprovedEvent, OrderRejectedEvent
        risk_events = [
            e for e in published_events
            if isinstance(e, (OrderApprovedEvent, OrderRejectedEvent))
        ]
        assert len(risk_events) >= 1, (
            "Expected at least one risk decision event"
        )
    finally:
        await engine._teardown()


# --- Test 15: Daily state reset ---

@pytest.mark.asyncio
async def test_daily_state_reset(tmp_path: Path) -> None:
    """strategy.reset_daily_state() called at start of day."""
    bars = _make_bar_df("AAPL", TRADING_DAY, [
        (9, 30, 150.0, 151.0, 149.0, 150.5, 1000),
    ])

    engine = await _setup_engine_with_bars(tmp_path, {"AAPL": bars})
    assert engine._strategy is not None

    reset_called = {"count": 0}
    original_reset = engine._strategy.reset_daily_state

    def tracking_reset() -> None:
        reset_called["count"] += 1
        original_reset()

    engine._strategy.reset_daily_state = tracking_reset  # type: ignore[assignment]

    try:
        await engine._run_trading_day(TRADING_DAY, ["AAPL"])
        assert reset_called["count"] == 1
    finally:
        await engine._teardown()


# ---------------------------------------------------------------------------
# Sprint 27 Session 5: Multi-day orchestration + scanner + results + CLI
# ---------------------------------------------------------------------------


def _make_multi_day_bars(
    symbol: str,
    trading_days: list[date],
) -> pd.DataFrame:
    """Build bar data spanning multiple trading days.

    Creates 3 bars per day at 9:30, 10:00, 10:30 ET with simple price data.
    """
    rows: list[dict[str, object]] = []
    base_price = 100.0
    for day in trading_days:
        for h, m in [(9, 30), (10, 0), (10, 30)]:
            ts = datetime(
                day.year, day.month, day.day, h, m, 0, tzinfo=ET,
            ).astimezone(UTC)
            rows.append({
                "timestamp": ts,
                "open": base_price,
                "high": base_price + 1.0,
                "low": base_price - 1.0,
                "close": base_price + 0.5,
                "volume": 1000,
                "trading_date": day,
            })
        base_price += 1.0
    return pd.DataFrame(rows)


MULTI_DAYS = [
    date(2025, 6, 16),
    date(2025, 6, 17),
    date(2025, 6, 18),
    date(2025, 6, 19),
    date(2025, 6, 20),
]


# --- Test S5-1: Multi-day run ---

@pytest.mark.asyncio
async def test_run_multi_day(tmp_path: Path) -> None:
    """Run processes all 5 trading days."""
    bars = _make_multi_day_bars("AAPL", MULTI_DAYS)
    config = _make_config(
        tmp_path, StrategyType.ORB_BREAKOUT, "strat_orb_breakout"
    )
    engine = BacktestEngine(config)

    # Inject bar data directly
    engine._bar_data = {"AAPL": bars}
    engine._trading_days = MULTI_DAYS

    # Patch _load_data to skip file I/O
    engine._load_data = AsyncMock()  # type: ignore[method-assign]

    result = await engine.run()

    assert result.trading_days == 5
    assert result.strategy_id == "strat_orb_breakout"


# --- Test S5-2: Daily state reset across days ---

@pytest.mark.asyncio
async def test_daily_state_reset_across_days(tmp_path: Path) -> None:
    """Strategy/RM/OM/DS reset between each trading day."""
    days = [date(2025, 6, 16), date(2025, 6, 17), date(2025, 6, 18)]
    bars = _make_multi_day_bars("AAPL", days)

    engine = await _setup_engine_with_bars(tmp_path, {"AAPL": bars})
    assert engine._strategy is not None

    reset_count = {"value": 0}
    original_reset = engine._strategy.reset_daily_state

    def counting_reset() -> None:
        reset_count["value"] += 1
        original_reset()

    engine._strategy.reset_daily_state = counting_reset  # type: ignore[assignment]
    engine._trading_days = days

    try:
        for day in days:
            await engine._run_trading_day(day, ["AAPL"])
        assert reset_count["value"] == 3
    finally:
        await engine._teardown()


# --- Test S5-3: Scanner generates watchlists ---

@pytest.mark.asyncio
async def test_scanner_generates_watchlists(tmp_path: Path) -> None:
    """ScannerSimulator is called and watchlists used per day."""
    days = [date(2025, 6, 16), date(2025, 6, 17)]
    bars_a = _make_multi_day_bars("AAPL", days)
    bars_t = _make_multi_day_bars("TSLA", days)

    config = _make_config(
        tmp_path, StrategyType.ORB_BREAKOUT, "strat_orb_breakout"
    )
    engine = BacktestEngine(config)
    engine._bar_data = {"AAPL": bars_a, "TSLA": bars_t}
    engine._trading_days = days
    engine._load_data = AsyncMock()  # type: ignore[method-assign]

    # Patch ScannerSimulator to track calls
    from argus.backtest.scanner_simulator import ScannerSimulator, DailyWatchlist

    watchlist_calls: list[object] = []
    original_compute = ScannerSimulator.compute_watchlists

    def tracking_compute(
        self: ScannerSimulator,
        bar_data: dict[str, pd.DataFrame],
        trading_days: list[date],
    ) -> dict[date, DailyWatchlist]:
        watchlist_calls.append(True)
        return original_compute(self, bar_data, trading_days)

    with patch.object(
        ScannerSimulator, "compute_watchlists", tracking_compute
    ):
        result = await engine.run()

    assert len(watchlist_calls) == 1  # Called exactly once
    assert result.trading_days == 2


# --- Test S5-4: Results computed ---

@pytest.mark.asyncio
async def test_results_computed(tmp_path: Path) -> None:
    """BacktestResult has valid fields after run."""
    bars = _make_multi_day_bars("AAPL", MULTI_DAYS)
    config = _make_config(
        tmp_path, StrategyType.ORB_BREAKOUT, "strat_orb_breakout"
    )
    config.initial_cash = 50_000.0
    engine = BacktestEngine(config)
    engine._bar_data = {"AAPL": bars}
    engine._trading_days = MULTI_DAYS
    engine._load_data = AsyncMock()  # type: ignore[method-assign]

    result = await engine.run()

    assert result.initial_capital == 50_000.0
    assert result.start_date == date(2025, 6, 16)
    assert result.end_date == date(2025, 6, 20)
    assert result.trading_days == 5
    # No signals emitted by default ORB strategy on this simple data
    assert result.total_trades == 0
    assert result.final_equity == 50_000.0


# --- Test S5-5: Empty data returns empty result ---

@pytest.mark.asyncio
async def test_empty_data_returns_empty_result(tmp_path: Path) -> None:
    """No trading days -> BacktestResult with 0 trades."""
    empty_cache = tmp_path / "empty_cache"
    empty_cache.mkdir()
    config = BacktestEngineConfig(
        start_date=date(2025, 6, 16),
        end_date=date(2025, 6, 20),
        output_dir=tmp_path / "backtest_runs",
        strategy_type=StrategyType.ORB_BREAKOUT,
        strategy_id="strat_orb_breakout",
        cache_dir=empty_cache,
        log_level="WARNING",
    )
    engine = BacktestEngine(config)
    # No bar data, no trading days
    result = await engine.run()

    assert result.total_trades == 0
    assert result.trading_days == 0
    assert result.win_rate == 0.0


# --- Test S5-6: End-to-end ORB breakout (no signals on simple data) ---

@pytest.mark.asyncio
async def test_end_to_end_orb_breakout(tmp_path: Path) -> None:
    """ORB Breakout on mocked data completes without error."""
    bars = _make_multi_day_bars("AAPL", MULTI_DAYS[:3])
    config = _make_config(
        tmp_path, StrategyType.ORB_BREAKOUT, "strat_orb_breakout"
    )
    engine = BacktestEngine(config)
    engine._bar_data = {"AAPL": bars}
    engine._trading_days = MULTI_DAYS[:3]
    engine._load_data = AsyncMock()  # type: ignore[method-assign]

    result = await engine.run()

    # Simple data won't trigger ORB entries — just verify no crash
    assert result.trading_days == 3
    assert result.total_trades >= 0


# --- Test S5-7: End-to-end no signals ---

@pytest.mark.asyncio
async def test_end_to_end_no_signals(tmp_path: Path) -> None:
    """Strategy with no matching setups -> 0 trades, no error."""
    bars = _make_multi_day_bars("AAPL", [date(2025, 6, 16)])
    config = _make_config(
        tmp_path, StrategyType.VWAP_RECLAIM, "strat_vwap_reclaim"
    )
    engine = BacktestEngine(config)
    engine._bar_data = {"AAPL": bars}
    engine._trading_days = [date(2025, 6, 16)]
    engine._load_data = AsyncMock()  # type: ignore[method-assign]

    result = await engine.run()

    assert result.total_trades == 0
    assert result.strategy_id == "strat_vwap_reclaim"


# --- Test S5-8: DB output created ---

@pytest.mark.asyncio
async def test_db_output_created(tmp_path: Path) -> None:
    """SQLite file exists at expected path with DEC-056 naming."""
    bars = _make_multi_day_bars("AAPL", [date(2025, 6, 16)])
    config = _make_config(
        tmp_path, StrategyType.ORB_BREAKOUT, "strat_orb_breakout"
    )
    engine = BacktestEngine(config)
    engine._bar_data = {"AAPL": bars}
    engine._trading_days = [date(2025, 6, 16)]
    engine._load_data = AsyncMock()  # type: ignore[method-assign]

    await engine.run()

    assert engine._db_path is not None
    assert engine._db_path.exists()
    # DEC-056: {strategy_id}_{start}_{end}_{timestamp}.db
    assert engine._db_path.name.startswith("strat_orb_breakout_")
    assert engine._db_path.suffix == ".db"


# --- Test S5-9: Metadata recorded (AR-1) ---

@pytest.mark.asyncio
async def test_metadata_recorded(tmp_path: Path) -> None:
    """engine_type and fill_model present in output (AR-1)."""
    import json as json_mod

    bars = _make_multi_day_bars("AAPL", [date(2025, 6, 16)])
    config = _make_config(
        tmp_path, StrategyType.ORB_BREAKOUT, "strat_orb_breakout"
    )
    engine = BacktestEngine(config)
    engine._bar_data = {"AAPL": bars}
    engine._trading_days = [date(2025, 6, 16)]
    engine._load_data = AsyncMock()  # type: ignore[method-assign]

    await engine.run()

    assert engine._db_path is not None
    meta_path = Path(f"{engine._db_path}.meta.json")
    assert meta_path.exists()

    metadata = json_mod.loads(meta_path.read_text())
    assert metadata["engine_type"] == "backtest_engine"
    assert metadata["fill_model"] == "bar_level_worst_case"
    assert metadata["strategy_type"] == "orb"
    assert metadata["symbol_count"] == 1
    assert "run_timestamp" in metadata


# --- Test S5-10: CLI parse_args ---

def test_cli_parse_args() -> None:
    """parse_args handles all required flags correctly."""
    from argus.backtest.engine import parse_args

    with patch(
        "sys.argv",
        [
            "engine",
            "--strategy", "orb",
            "--start", "2025-01-01",
            "--end", "2025-01-31",
            "--symbols", "AAPL,TSLA",
            "--initial-cash", "50000",
            "--slippage", "0.02",
            "--log-level", "INFO",
            "--no-cost-check",
            "--config-override", "orb_window_minutes=15",
            "-v",
        ],
    ):
        args = parse_args()

    assert args.strategy == "orb"
    assert args.start == date(2025, 1, 1)
    assert args.end == date(2025, 1, 31)
    assert args.symbols == "AAPL,TSLA"
    assert args.initial_cash == 50000.0
    assert args.slippage == 0.02
    assert args.log_level == "INFO"
    assert args.no_cost_check is True
    assert args.verbose is True
    assert args.config_override == ["orb_window_minutes=15"]


# --- Test S5-11: CLI main runs ---

def test_cli_main_runs(tmp_path: Path) -> None:
    """main() builds correct config and calls asyncio.run()."""
    from argus.backtest.engine import main
    from argus.backtest.metrics import BacktestResult

    empty_result = BacktestResult(
        strategy_id="strat_orb", start_date=date(2025, 6, 16),
        end_date=date(2025, 6, 16), initial_capital=100_000.0,
        final_equity=100_000.0, trading_days=0, total_trades=0,
        winning_trades=0, losing_trades=0, breakeven_trades=0,
        win_rate=0.0, profit_factor=0.0, avg_r_multiple=0.0,
        avg_winner_r=0.0, avg_loser_r=0.0, expectancy=0.0,
        max_drawdown_dollars=0.0, max_drawdown_pct=0.0,
        sharpe_ratio=0.0, recovery_factor=0.0, avg_hold_minutes=0.0,
        max_consecutive_wins=0, max_consecutive_losses=0,
        largest_win_dollars=0.0, largest_loss_dollars=0.0,
        largest_win_r=0.0, largest_loss_r=0.0,
    )

    with patch(
        "sys.argv",
        [
            "engine",
            "--strategy", "orb",
            "--start", "2025-06-16",
            "--end", "2025-06-16",
            "--output-dir", str(tmp_path / "output"),
            "--log-level", "ERROR",
        ],
    ), patch(
        "argus.backtest.engine.asyncio.run",
        return_value=empty_result,
    ) as mock_run:
        main()

    # Verify asyncio.run was called with a coroutine
    assert mock_run.called


# --- Test S5-12: Log level config ---

@pytest.mark.asyncio
async def test_log_level_config(tmp_path: Path) -> None:
    """WARNING level applied during _setup(); INFO level applies INFO."""
    config = _make_config(
        tmp_path, StrategyType.ORB_BREAKOUT, "strat_orb_breakout"
    )
    config.log_level = "WARNING"
    engine = BacktestEngine(config)
    await engine._setup()
    try:
        argus_logger = logging.getLogger("argus")
        assert argus_logger.level == logging.WARNING
    finally:
        await engine._teardown()

    # Now test with INFO
    config2 = _make_config(
        tmp_path, StrategyType.ORB_BREAKOUT, "strat_orb_breakout_2"
    )
    config2.log_level = "INFO"
    engine2 = BacktestEngine(config2)
    await engine2._setup()
    try:
        assert logging.getLogger("argus").level == logging.INFO
    finally:
        await engine2._teardown()


# --- Test S5-13: Progress logging ---

@pytest.mark.asyncio
async def test_progress_logging(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Progress logged every 20 days."""
    # Create 25 weekdays (need >20 to trigger progress log)
    base = date(2025, 1, 2)
    all_days = [base + timedelta(days=i) for i in range(40)]
    days = [d for d in all_days if d.weekday() < 5][:25]
    bars = _make_multi_day_bars("AAPL", days)

    config = _make_config(
        tmp_path, StrategyType.ORB_BREAKOUT, "strat_orb_breakout"
    )
    config.log_level = "INFO"
    engine = BacktestEngine(config)
    engine._bar_data = {"AAPL": bars}
    engine._trading_days = days
    engine._load_data = AsyncMock()  # type: ignore[method-assign]

    with caplog.at_level(logging.INFO, logger="argus.backtest.engine"):
        await engine.run()

    progress_msgs = [
        r for r in caplog.records
        if "Progress:" in r.message and "trading days complete" in r.message
    ]
    # With 25 days, day 20 triggers progress log
    assert len(progress_msgs) >= 1


# --- Test S5-14: Config overrides applied ---

@pytest.mark.asyncio
async def test_config_overrides_applied_in_run(tmp_path: Path) -> None:
    """Strategy parameter overrides reflected in strategy config via run()."""
    bars = _make_multi_day_bars("AAPL", [date(2025, 6, 16)])
    config = _make_config(
        tmp_path, StrategyType.ORB_BREAKOUT, "strat_orb_breakout"
    )
    config.config_overrides = {"orb_window_minutes": 20}
    engine = BacktestEngine(config)
    engine._bar_data = {"AAPL": bars}
    engine._trading_days = [date(2025, 6, 16)]
    engine._load_data = AsyncMock()  # type: ignore[method-assign]

    # Run setup only to check strategy config
    await engine._setup()
    try:
        assert isinstance(engine._strategy, OrbBreakoutStrategy)
        assert engine._strategy._config.orb_window_minutes == 20
    finally:
        await engine._teardown()


# --- Test S5-15: Symbols filter ---

@pytest.mark.asyncio
async def test_symbols_filter(tmp_path: Path) -> None:
    """Only specified symbols processed when symbols list provided."""
    days = [date(2025, 6, 16)]
    bars_a = _make_multi_day_bars("AAPL", days)
    bars_t = _make_multi_day_bars("TSLA", days)

    engine = await _setup_engine_with_bars(
        tmp_path, {"AAPL": bars_a, "TSLA": bars_t}
    )
    assert engine._data_service is not None

    fed_symbols: list[str] = []
    original_feed = engine._data_service.feed_bar

    async def track_feed(symbol: str, **kwargs: object) -> None:
        fed_symbols.append(symbol)
        await original_feed(symbol=symbol, **kwargs)

    engine._data_service.feed_bar = track_feed  # type: ignore[assignment]

    try:
        # Only pass AAPL in watchlist
        await engine._run_trading_day(date(2025, 6, 16), ["AAPL"])
        assert all(s == "AAPL" for s in fed_symbols)
        assert "TSLA" not in fed_symbols
    finally:
        await engine._teardown()
