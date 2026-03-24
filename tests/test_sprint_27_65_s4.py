"""Tests for Sprint 27.65 S4: Market bars endpoint + Position P&L updates."""

from __future__ import annotations

import asyncio
import time as _time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from argus.core.events import CandleEvent, PositionUpdatedEvent, TickEvent
from argus.data.intraday_candle_store import IntradayCandleStore
from argus.strategies.patterns.base import CandleBar

ET = ZoneInfo("America/New_York")


# ---------------------------------------------------------------------------
# Market Bars Endpoint Tests
# ---------------------------------------------------------------------------


def _make_store_with_bars(symbol: str = "AAPL", count: int = 5) -> IntradayCandleStore:
    """Create a candle store pre-populated with bars (sync helper)."""
    import asyncio

    store = IntradayCandleStore()

    async def _fill() -> None:
        for m in range(count):
            ts = datetime(2026, 3, 25, 10, m, 0, tzinfo=ET)
            event = CandleEvent(
                symbol=symbol,
                timeframe="1m",
                open=150.0 + m,
                high=151.0 + m,
                low=149.0 + m,
                close=150.5 + m,
                volume=1000 + m,
                timestamp=ts,
            )
            await store.on_candle(event)

    asyncio.get_event_loop().run_until_complete(_fill())
    return store


@pytest.mark.asyncio
async def test_market_bars_endpoint_uses_candle_store() -> None:
    """API returns real bars from candle store when available."""
    from argus.api.routes.market import BarData, BarsResponse, get_symbol_bars

    store = IntradayCandleStore()
    ts = datetime(2026, 3, 25, 10, 0, 0, tzinfo=ET)
    await store.on_candle(CandleEvent(
        symbol="AAPL", timeframe="1m",
        open=150.0, high=151.0, low=149.0, close=150.5, volume=1000,
        timestamp=ts,
    ))

    # Mock state with candle store
    state = MagicMock()
    state.candle_store = store
    state.data_service = None

    # Call the endpoint logic directly
    with patch("argus.api.routes.market.get_app_state", return_value=state):
        result = await get_symbol_bars(
            symbol="AAPL",
            timeframe="1m",
            limit=390,
            start_time=None,
            end_time=None,
            _auth={},
            state=state,
        )

    assert result.count == 1
    assert result.symbol == "AAPL"
    assert result.bars[0].open == 150.0


@pytest.mark.asyncio
async def test_market_bars_endpoint_fallback() -> None:
    """API falls back to synthetic when store has no data for symbol."""
    from argus.api.routes.market import get_symbol_bars

    store = IntradayCandleStore()  # Empty store

    state = MagicMock()
    state.candle_store = store
    state.data_service = None

    result = await get_symbol_bars(
        symbol="MSFT",
        timeframe="1m",
        limit=10,
        start_time=None,
        end_time=None,
        _auth={},
        state=state,
    )

    # Should get synthetic data (10 bars)
    assert result.count == 10
    assert result.symbol == "MSFT"


# ---------------------------------------------------------------------------
# Position P&L Update Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_position_update_event_published() -> None:
    """Tick event for open position triggers PositionUpdatedEvent."""
    from argus.core.event_bus import EventBus
    from argus.execution.order_manager import ManagedPosition, OrderManager

    event_bus = EventBus()
    clock = MagicMock()
    clock.now.return_value = datetime(2026, 3, 25, 10, 0, 0, tzinfo=UTC)
    config = MagicMock()
    config.enable_trailing_stop = False
    config.t1_position_pct = 0.5
    config.eod_flatten_time = "15:55"
    config.time_stop_check_interval_seconds = 5
    config.flatten_guard_seconds = 10

    broker = MagicMock()
    om = OrderManager(
        event_bus=event_bus,
        broker=broker,
        clock=clock,
        config=config,
    )

    # Add a managed position directly
    position = ManagedPosition(
        symbol="AAPL",
        strategy_id="orb_breakout",
        entry_price=150.0,
        entry_time=datetime(2026, 3, 25, 10, 0, 0, tzinfo=UTC),
        shares_total=100,
        shares_remaining=100,
        stop_price=148.0,
        original_stop_price=148.0,
        stop_order_id="stop1",
        t1_price=153.0,
        t1_order_id="t1_1",
        t1_shares=50,
        t1_filled=False,
        t2_price=156.0,
        high_watermark=150.0,
    )
    om._managed_positions["AAPL"] = [position]

    # Subscribe to catch PositionUpdatedEvent
    received: list[PositionUpdatedEvent] = []

    async def on_update(event: PositionUpdatedEvent) -> None:
        received.append(event)

    event_bus.subscribe(PositionUpdatedEvent, on_update)

    # Send a tick
    tick = TickEvent(symbol="AAPL", price=152.0, volume=500)
    await om.on_tick(tick)
    await asyncio.sleep(0)  # Let event bus dispatch handlers

    assert len(received) == 1
    assert received[0].symbol == "AAPL"
    assert received[0].current_price == 152.0
    assert received[0].unrealized_pnl == pytest.approx(200.0)  # (152-150) * 100
    assert received[0].strategy_id == "orb_breakout"
    assert received[0].shares == 100


@pytest.mark.asyncio
async def test_position_update_throttle() -> None:
    """Multiple ticks within 1s produce only 1 P&L update."""
    from argus.core.event_bus import EventBus
    from argus.execution.order_manager import ManagedPosition, OrderManager

    event_bus = EventBus()
    clock = MagicMock()
    clock.now.return_value = datetime(2026, 3, 25, 10, 0, 0, tzinfo=UTC)
    config = MagicMock()
    config.enable_trailing_stop = False
    config.eod_flatten_time = "15:55"
    config.time_stop_check_interval_seconds = 5
    config.flatten_guard_seconds = 10

    broker = MagicMock()
    om = OrderManager(
        event_bus=event_bus,
        broker=broker,
        clock=clock,
        config=config,
    )

    position = ManagedPosition(
        symbol="AAPL",
        strategy_id="test",
        entry_price=150.0,
        entry_time=datetime(2026, 3, 25, 10, 0, 0, tzinfo=UTC),
        shares_total=100,
        shares_remaining=100,
        stop_price=148.0,
        original_stop_price=148.0,
        stop_order_id="stop1",
        t1_price=153.0,
        t1_order_id="t1_1",
        t1_shares=50,
        t1_filled=False,
        t2_price=156.0,
        high_watermark=150.0,
    )
    om._managed_positions["AAPL"] = [position]

    received: list[PositionUpdatedEvent] = []

    async def on_update(event: PositionUpdatedEvent) -> None:
        received.append(event)

    event_bus.subscribe(PositionUpdatedEvent, on_update)

    # Send 3 rapid ticks
    for price in [151.0, 152.0, 153.0]:
        await om.on_tick(TickEvent(symbol="AAPL", price=price, volume=100))
        await asyncio.sleep(0)  # Let event bus dispatch

    # Only 1 should have been published (throttled at 1/sec)
    assert len(received) == 1


@pytest.mark.asyncio
async def test_position_update_r_multiple_calculation() -> None:
    """Verify R-multiple math: unrealized_pnl / risk_amount."""
    from argus.core.event_bus import EventBus
    from argus.execution.order_manager import ManagedPosition, OrderManager

    event_bus = EventBus()
    clock = MagicMock()
    clock.now.return_value = datetime(2026, 3, 25, 10, 0, 0, tzinfo=UTC)
    config = MagicMock()
    config.enable_trailing_stop = False
    config.eod_flatten_time = "15:55"
    config.time_stop_check_interval_seconds = 5
    config.flatten_guard_seconds = 10

    broker = MagicMock()
    om = OrderManager(
        event_bus=event_bus,
        broker=broker,
        clock=clock,
        config=config,
    )

    # Entry=100, Stop=98 => risk_per_share=2, risk_amount=200 (100 shares)
    position = ManagedPosition(
        symbol="TEST",
        strategy_id="test",
        entry_price=100.0,
        entry_time=datetime(2026, 3, 25, 10, 0, 0, tzinfo=UTC),
        shares_total=100,
        shares_remaining=100,
        stop_price=98.0,
        original_stop_price=98.0,
        stop_order_id="stop1",
        t1_price=104.0,
        t1_order_id="t1_1",
        t1_shares=50,
        t1_filled=False,
        t2_price=108.0,
        high_watermark=100.0,
    )
    om._managed_positions["TEST"] = [position]

    received: list[PositionUpdatedEvent] = []

    async def on_update(event: PositionUpdatedEvent) -> None:
        received.append(event)

    event_bus.subscribe(PositionUpdatedEvent, on_update)

    # Price at 103 => unrealized = 300, risk_amount = 200, R = 1.5
    await om.on_tick(TickEvent(symbol="TEST", price=103.0, volume=100))
    await asyncio.sleep(0)  # Let event bus dispatch

    assert len(received) == 1
    assert received[0].unrealized_pnl == pytest.approx(300.0)
    assert received[0].r_multiple == pytest.approx(1.5)
