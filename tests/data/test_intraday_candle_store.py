"""Tests for IntradayCandleStore (Sprint 27.65 S4)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from argus.core.events import CandleEvent
from argus.data.intraday_candle_store import IntradayCandleStore


def _make_candle(
    symbol: str = "AAPL",
    hour: int = 10,
    minute: int = 0,
    timeframe: str = "1m",
    price: float = 150.0,
    volume: int = 1000,
) -> CandleEvent:
    """Create a CandleEvent with ET-aware timestamp during market hours."""
    from zoneinfo import ZoneInfo

    et = ZoneInfo("America/New_York")
    ts = datetime(2026, 3, 25, hour, minute, 0, tzinfo=et)
    return CandleEvent(
        symbol=symbol,
        timeframe=timeframe,
        open=price,
        high=price + 0.5,
        low=price - 0.5,
        close=price + 0.1,
        volume=volume,
        timestamp=ts,
    )


@pytest.mark.asyncio
async def test_candle_store_accumulates_bars() -> None:
    """Publish CandleEvents, verify they are stored."""
    store = IntradayCandleStore()
    await store.on_candle(_make_candle("AAPL", 10, 0))
    await store.on_candle(_make_candle("AAPL", 10, 1))
    await store.on_candle(_make_candle("TSLA", 10, 0))

    assert store.bar_count("AAPL") == 2
    assert store.bar_count("TSLA") == 1
    assert store.has_bars("AAPL")
    assert not store.has_bars("MSFT")


@pytest.mark.asyncio
async def test_candle_store_get_bars_time_range() -> None:
    """Filter bars by start and end time."""
    from zoneinfo import ZoneInfo

    et = ZoneInfo("America/New_York")
    store = IntradayCandleStore()

    for m in range(5):
        await store.on_candle(_make_candle("AAPL", 10, m))

    start = datetime(2026, 3, 25, 10, 1, 0, tzinfo=et)
    end = datetime(2026, 3, 25, 10, 3, 0, tzinfo=et)
    bars = store.get_bars("AAPL", start_time=start, end_time=end)

    assert len(bars) == 3  # minutes 1, 2, 3


@pytest.mark.asyncio
async def test_candle_store_max_length() -> None:
    """Verify deque doesn't exceed 390 per symbol."""
    store = IntradayCandleStore()

    # Add 395 bars (9:30 to 16:05 — but market close filter will drop some)
    for m in range(395):
        hour = 9 + (30 + m) // 60
        minute = (30 + m) % 60
        if hour < 16:
            await store.on_candle(_make_candle("AAPL", hour, minute))

    assert store.bar_count("AAPL") <= 390


@pytest.mark.asyncio
async def test_candle_store_get_latest() -> None:
    """Returns N most recent bars."""
    store = IntradayCandleStore()
    for m in range(10):
        await store.on_candle(_make_candle("AAPL", 10, m, price=100.0 + m))

    latest = store.get_latest("AAPL", count=3)
    assert len(latest) == 3
    # Should be the last 3 bars (prices 107, 108, 109)
    assert latest[0].open == pytest.approx(107.0)
    assert latest[2].open == pytest.approx(109.0)


@pytest.mark.asyncio
async def test_candle_store_reset() -> None:
    """Clears all data."""
    store = IntradayCandleStore()
    await store.on_candle(_make_candle("AAPL", 10, 0))
    await store.on_candle(_make_candle("TSLA", 10, 0))

    assert store.symbols_with_bars() == ["AAPL", "TSLA"]

    store.reset()
    assert store.symbols_with_bars() == []
    assert store.bar_count("AAPL") == 0


@pytest.mark.asyncio
async def test_candle_store_filters_pre_market() -> None:
    """Pre-market bars (before 9:30 ET) should not be stored."""
    store = IntradayCandleStore()
    await store.on_candle(_make_candle("AAPL", 8, 30))  # Pre-market
    await store.on_candle(_make_candle("AAPL", 9, 0))   # Pre-market
    await store.on_candle(_make_candle("AAPL", 9, 30))  # Market open — stored

    assert store.bar_count("AAPL") == 1


@pytest.mark.asyncio
async def test_candle_store_filters_post_market() -> None:
    """Post-market bars (at or after 16:00 ET) should not be stored."""
    store = IntradayCandleStore()
    await store.on_candle(_make_candle("AAPL", 15, 59))  # Last minute — stored
    await store.on_candle(_make_candle("AAPL", 16, 0))   # Post-market — filtered

    assert store.bar_count("AAPL") == 1


@pytest.mark.asyncio
async def test_candle_store_filters_non_1m() -> None:
    """Only 1m bars should be stored."""
    store = IntradayCandleStore()
    await store.on_candle(_make_candle("AAPL", 10, 0, timeframe="5m"))
    await store.on_candle(_make_candle("AAPL", 10, 0, timeframe="1s"))
    await store.on_candle(_make_candle("AAPL", 10, 1, timeframe="1m"))

    assert store.bar_count("AAPL") == 1


@pytest.mark.asyncio
async def test_candle_store_symbols_with_bars() -> None:
    """Returns sorted list of symbols with bars."""
    store = IntradayCandleStore()
    await store.on_candle(_make_candle("TSLA", 10, 0))
    await store.on_candle(_make_candle("AAPL", 10, 0))
    await store.on_candle(_make_candle("NVDA", 10, 0))

    assert store.symbols_with_bars() == ["AAPL", "NVDA", "TSLA"]


@pytest.mark.asyncio
async def test_candle_store_get_latest_empty() -> None:
    """get_latest on empty symbol returns empty list."""
    store = IntradayCandleStore()
    assert store.get_latest("AAPL", 5) == []


@pytest.mark.asyncio
async def test_candle_store_get_bars_no_filter() -> None:
    """get_bars with no time filter returns all bars."""
    store = IntradayCandleStore()
    for m in range(5):
        await store.on_candle(_make_candle("AAPL", 10, m))

    bars = store.get_bars("AAPL")
    assert len(bars) == 5
