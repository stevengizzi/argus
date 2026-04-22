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
    """Verify deque doesn't exceed 720 per symbol."""
    store = IntradayCandleStore()

    # Add 395 bars (9:30 to 16:05 — but market close filter will drop some)
    for m in range(395):
        hour = 9 + (30 + m) // 60
        minute = (30 + m) % 60
        if hour < 16:
            await store.on_candle(_make_candle("AAPL", hour, minute))

    assert store.bar_count("AAPL") <= 720


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
    """Bars from 4:00 AM ET onward are stored; overnight bars are filtered."""
    store = IntradayCandleStore()
    await store.on_candle(_make_candle("AAPL", 3, 59))  # Overnight — filtered
    await store.on_candle(_make_candle("AAPL", 4, 0))   # Pre-market open — stored
    await store.on_candle(_make_candle("AAPL", 8, 30))  # Pre-market — stored
    await store.on_candle(_make_candle("AAPL", 9, 30))  # Regular session — stored

    assert store.bar_count("AAPL") == 3


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


# ---------------------------------------------------------------------------
# Sprint 32.8 S1: Pre-market widening tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_candle_store_accepts_premarket_bars() -> None:
    """CandleEvent at 8:00 AM ET is stored after widening to 4:00 AM ET."""
    store = IntradayCandleStore()
    await store.on_candle(_make_candle("AAPL", 8, 0))   # Pre-market — now stored
    await store.on_candle(_make_candle("AAPL", 4, 0))   # Pre-market open — stored
    await store.on_candle(_make_candle("AAPL", 6, 30))  # Pre-market — stored

    assert store.bar_count("AAPL") == 3


@pytest.mark.asyncio
async def test_candle_store_rejects_overnight_bars() -> None:
    """CandleEvent at 3:00 AM ET is still rejected (before 4:00 AM boundary)."""
    store = IntradayCandleStore()
    await store.on_candle(_make_candle("AAPL", 3, 0))   # Overnight — rejected
    await store.on_candle(_make_candle("AAPL", 3, 59))  # Overnight — rejected
    await store.on_candle(_make_candle("AAPL", 4, 0))   # Pre-market open — stored

    assert store.bar_count("AAPL") == 1


@pytest.mark.asyncio
async def test_candle_store_max_bars_increased() -> None:
    """Verify max bars per symbol is 720 (12-hour session)."""
    from argus.data.intraday_candle_store import _MAX_BARS_PER_SYMBOL

    assert _MAX_BARS_PER_SYMBOL == 720

    store = IntradayCandleStore()
    # Fill 720 bars across 4 AM to 4 PM (12 hours × 60 bars)
    count = 0
    for h in range(4, 16):
        for m in range(60):
            await store.on_candle(_make_candle("AAPL", h, m))
            count += 1

    # All bars within the 4 AM–4 PM window should be stored (up to 720)
    assert store.bar_count("AAPL") == 720


@pytest.mark.asyncio
async def test_candle_store_rejects_naive_timestamp() -> None:
    """FIX-06 audit 2026-04-21 (P1-C2-8): naive timestamps are a test-fixture
    smell — production always carries tzinfo. Fail-fast with ValueError so
    a silent ET-misinterpretation never slips through."""
    store = IntradayCandleStore()
    naive_event = CandleEvent(
        symbol="AAPL",
        timeframe="1m",
        open=150.0,
        high=150.5,
        low=149.5,
        close=150.1,
        volume=1000,
        timestamp=datetime(2026, 3, 25, 10, 0, 0),  # naive — no tzinfo
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        await store.on_candle(naive_event)
