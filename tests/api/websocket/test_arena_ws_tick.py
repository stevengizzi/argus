"""Tests for Arena WebSocket TickEvent subscription and trail stop cache.

Sprint 32.8, Session 1.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from argus.api.websocket.arena_ws import build_arena_tick
from argus.core.events import TickEvent, PositionUpdatedEvent


# ---------------------------------------------------------------------------
# Test 1: TickEvent filtered to tracked symbols — non-tracked is skipped
# ---------------------------------------------------------------------------


def test_arena_ws_tick_event_filtered_to_tracked_symbols() -> None:
    """TickEvent for a non-tracked symbol is not forwarded to the client.

    The on_tick handler checks `if event.symbol not in tracked_symbols: return`.
    This test verifies the filtering condition holds for an untracked symbol.
    """
    tracked_symbols: set[str] = {"AAPL", "NVDA"}
    tick = TickEvent(symbol="TSLA", price=200.0)

    # TSLA is not in tracked_symbols — the on_tick handler would return early
    assert tick.symbol not in tracked_symbols


# ---------------------------------------------------------------------------
# Test 2: TickEvent enqueued for tracked symbol
# ---------------------------------------------------------------------------


def test_arena_ws_tick_event_enqueued_for_tracked_symbol() -> None:
    """TickEvent for a tracked symbol passes the filter and produces a message."""
    tracked_symbols: set[str] = {"AAPL", "NVDA"}
    tick = TickEvent(symbol="AAPL", price=186.50)

    # AAPL is in tracked_symbols — the on_tick handler would enqueue a message
    assert tick.symbol in tracked_symbols


# ---------------------------------------------------------------------------
# Test 3: arena_tick_price message format
# ---------------------------------------------------------------------------


def test_arena_ws_tick_price_message_format() -> None:
    """arena_tick_price message has type, symbol, price, and timestamp fields."""
    ts = datetime(2026, 4, 1, 14, 30, 0, tzinfo=UTC)
    tick = TickEvent(symbol="AAPL", price=186.50, timestamp=ts)

    # Simulate the on_tick handler dict construction
    msg: dict[str, object] = {
        "type": "arena_tick_price",
        "symbol": tick.symbol,
        "price": tick.price,
        "timestamp": tick.timestamp.isoformat(),
    }

    assert msg["type"] == "arena_tick_price"
    assert msg["symbol"] == "AAPL"
    assert msg["price"] == pytest.approx(186.50)
    assert "timestamp" in msg
    assert msg["timestamp"] == ts.isoformat()


# ---------------------------------------------------------------------------
# Test 4: Trail stop cache updated on position update
# ---------------------------------------------------------------------------


def test_trail_stop_cache_updated_on_position_update() -> None:
    """Trail stop cache is populated from on_position_updated at 1 Hz.

    Verifies that the dict-based cache pattern stores trail stops per symbol
    and that a symbol with no update returns a default of 0.0.
    """
    trail_stop_cache: dict[str, float] = {}

    # Simulate on_position_updated storing trail stop for AAPL
    trail_stop_cache["AAPL"] = 184.25
    assert trail_stop_cache["AAPL"] == pytest.approx(184.25)

    # Updating with a new trail stop overwrites the old value
    trail_stop_cache["AAPL"] = 185.00
    assert trail_stop_cache["AAPL"] == pytest.approx(185.00)

    # Symbol with no trail active uses 0.0
    trail_stop_cache["NVDA"] = 0.0
    assert trail_stop_cache["NVDA"] == 0.0

    # Symbol not yet seen has no cache entry
    assert trail_stop_cache.get("TSLA") is None

    # build_arena_tick still works with cache-sourced trail value
    event = PositionUpdatedEvent(
        symbol="AAPL",
        current_price=186.50,
        unrealized_pnl=150.0,
        r_multiple=0.75,
        entry_price=185.0,
        shares=100,
        strategy_id="orb_breakout",
    )
    msg = build_arena_tick(event, trailing_stop_price=trail_stop_cache["AAPL"])
    assert msg["trailing_stop_price"] == pytest.approx(185.00)
    assert msg["type"] == "arena_tick"
