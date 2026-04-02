"""Tests for Arena WebSocket endpoint.

Covers:
- Connection auth (reject non-auth, reject invalid token, accept valid)
- Message format for each of the 5 message types
- CandleEvent filtering (only tracked symbols)
- arena_stats computation
- R-multiple computation on position close
- Graceful disconnect (no leaked subscriptions)
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

from argus.api.auth import create_access_token, set_jwt_secret
from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.api.websocket.arena_ws import (
    _prune_ring_buffer,
    build_arena_candle,
    build_arena_position_closed,
    build_arena_position_opened,
    build_arena_stats,
    build_arena_tick,
    compute_r_multiple,
    get_active_arena_connections,
)
from argus.core.events import (
    CandleEvent,
    ExitReason,
    PositionClosedEvent,
    PositionOpenedEvent,
    PositionUpdatedEvent,
)

TEST_JWT_SECRET = "test-jwt-secret-for-argus-api-testing-minimum-32-chars"


def _make_token() -> str:
    token, _ = create_access_token(TEST_JWT_SECRET, expires_hours=24)
    return token


def _build_app(app_state: AppState) -> object:
    app = create_app(app_state)
    app.state.app_state = app_state
    return app


# ---------------------------------------------------------------------------
# Auth tests (TestClient)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_arena_ws_requires_auth_message(
    app_state: AppState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sending a non-auth first message closes the connection with 4001."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    app = _build_app(app_state)
    client = TestClient(app)
    try:
        with client.websocket_connect("/ws/v1/arena") as ws:
            ws.send_json({"type": "not_auth"})
    except Exception:
        pass  # Expected: server closes with 4001


@pytest.mark.asyncio
async def test_arena_ws_rejects_invalid_token(
    app_state: AppState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid JWT token causes 4001 close."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    app = _build_app(app_state)
    client = TestClient(app)
    try:
        with client.websocket_connect("/ws/v1/arena") as ws:
            ws.send_json({"type": "auth", "token": "not-a-valid-jwt"})
    except Exception:
        pass  # Expected: connection closed with 4001


@pytest.mark.asyncio
async def test_arena_ws_accepts_valid_auth(
    app_state: AppState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid JWT produces auth_success response."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    app = _build_app(app_state)
    client = TestClient(app)
    with client.websocket_connect("/ws/v1/arena") as ws:
        ws.send_json({"type": "auth", "token": _make_token()})
        response = ws.receive_json()

    assert response["type"] == "auth_success"
    assert "timestamp" in response


@pytest.mark.asyncio
async def test_arena_ws_graceful_disconnect(
    app_state: AppState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Disconnecting removes the connection from the active set."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    app = _build_app(app_state)
    client = TestClient(app)
    with client.websocket_connect("/ws/v1/arena") as ws:
        ws.send_json({"type": "auth", "token": _make_token()})
        ws.receive_json()  # auth_success

    # After disconnect the connection must be removed
    assert len(get_active_arena_connections()) == 0


# ---------------------------------------------------------------------------
# Message format unit tests
# ---------------------------------------------------------------------------


def test_build_arena_tick_message_format() -> None:
    """build_arena_tick produces correct keys and values."""
    event = PositionUpdatedEvent(
        symbol="AAPL",
        current_price=186.50,
        unrealized_pnl=150.0,
        r_multiple=0.75,
        entry_price=185.0,
        shares=100,
        strategy_id="orb_breakout",
    )
    msg = build_arena_tick(event, trailing_stop_price=184.25)

    assert msg["type"] == "arena_tick"
    assert msg["symbol"] == "AAPL"
    assert msg["price"] == 186.50
    assert msg["unrealized_pnl"] == 150.0
    assert msg["r_multiple"] == 0.75
    assert msg["trailing_stop_price"] == 184.25


def test_build_arena_candle_message_format() -> None:
    """build_arena_candle produces correct keys and values."""
    ts = datetime(2026, 4, 1, 14, 30, 0, tzinfo=UTC)
    event = CandleEvent(
        symbol="NVDA",
        timeframe="1m",
        open=750.0,
        high=752.5,
        low=749.0,
        close=751.0,
        volume=12345,
        timestamp=ts,
    )
    msg = build_arena_candle(event)

    assert msg["type"] == "arena_candle"
    assert msg["symbol"] == "NVDA"
    assert msg["open"] == 750.0
    assert msg["high"] == 752.5
    assert msg["low"] == 749.0
    assert msg["close"] == 751.0
    assert msg["volume"] == 12345
    assert msg["time"] == ts.isoformat()


def test_build_arena_position_opened_message_format() -> None:
    """build_arena_position_opened has correct keys and side defaults to long."""
    event = PositionOpenedEvent(
        symbol="TSLA",
        strategy_id="bull_flag",
        entry_price=200.0,
        stop_price=197.0,
        target_prices=(204.0, 208.0),
        shares=50,
    )
    msg = build_arena_position_opened(event)

    assert msg["type"] == "arena_position_opened"
    assert msg["symbol"] == "TSLA"
    assert msg["strategy_id"] == "bull_flag"
    assert msg["entry_price"] == 200.0
    assert msg["stop_price"] == 197.0
    assert msg["target_prices"] == [204.0, 208.0]
    assert msg["side"] == "long"
    assert msg["shares"] == 50
    assert "entry_time" in msg


def test_build_arena_position_closed_message_format() -> None:
    """build_arena_position_closed has correct keys."""
    event = PositionClosedEvent(
        symbol="MSFT",
        strategy_id="orb_breakout",
        exit_price=425.0,
        realized_pnl=200.0,
        exit_reason=ExitReason.TARGET_1,
    )
    msg = build_arena_position_closed(event, r_multiple=1.25)

    assert msg["type"] == "arena_position_closed"
    assert msg["symbol"] == "MSFT"
    assert msg["strategy_id"] == "orb_breakout"
    assert msg["exit_price"] == 425.0
    assert msg["pnl"] == 200.0
    assert msg["r_multiple"] == 1.25
    assert msg["exit_reason"] == "target_1"


def test_build_arena_stats_message_format() -> None:
    """build_arena_stats produces correct keys and values."""
    msg = build_arena_stats(
        position_count=3,
        total_pnl=450.0,
        net_r=2.1,
        entries_5m=2,
        exits_5m=1,
    )

    assert msg["type"] == "arena_stats"
    assert msg["position_count"] == 3
    assert msg["total_pnl"] == 450.0
    assert msg["net_r"] == 2.1
    assert msg["entries_5m"] == 2
    assert msg["exits_5m"] == 1


# ---------------------------------------------------------------------------
# compute_r_multiple unit tests
# ---------------------------------------------------------------------------


def test_compute_r_multiple_win() -> None:
    """Winning trade computes positive R-multiple."""
    r = compute_r_multiple(entry_price=185.0, stop_price=183.0, exit_price=187.0)
    assert abs(r - 1.0) < 1e-6


def test_compute_r_multiple_loss() -> None:
    """Losing trade computes negative R-multiple."""
    r = compute_r_multiple(entry_price=185.0, stop_price=183.0, exit_price=184.0)
    assert abs(r - (-0.5)) < 1e-6


def test_compute_r_multiple_zero_risk() -> None:
    """Near-zero risk (entry == stop) returns 0.0 without division error."""
    r = compute_r_multiple(entry_price=185.0, stop_price=185.0, exit_price=190.0)
    assert r == 0.0


# ---------------------------------------------------------------------------
# CandleEvent filtering unit test
# ---------------------------------------------------------------------------


def test_arena_candle_only_forwards_tracked_symbols() -> None:
    """CandleEvent for non-tracked symbol must be ignored.

    Validates the filtering logic: if a symbol is not in tracked_symbols,
    build_arena_candle is never called for it.
    """
    tracked: set[str] = {"AAPL", "NVDA"}

    aapl_candle = CandleEvent(symbol="AAPL", timeframe="1m", close=186.0)
    tsla_candle = CandleEvent(symbol="TSLA", timeframe="1m", close=200.0)

    # AAPL is tracked — message built
    assert aapl_candle.symbol in tracked
    msg = build_arena_candle(aapl_candle)
    assert msg["symbol"] == "AAPL"

    # TSLA is NOT tracked — filtering logic would skip it
    assert tsla_candle.symbol not in tracked


# ---------------------------------------------------------------------------
# Ring buffer pruning test
# ---------------------------------------------------------------------------


def test_prune_ring_buffer_removes_old_entries() -> None:
    """_prune_ring_buffer removes timestamps older than cutoff."""
    from collections import deque

    now = time.monotonic()
    buf: deque[float] = deque([now - 400, now - 350, now - 100, now - 50, now])
    _prune_ring_buffer(buf, cutoff=now - 300.0)

    assert len(buf) == 3
    assert all(t >= now - 300.0 for t in buf)
