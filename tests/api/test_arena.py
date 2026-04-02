"""Tests for the Arena REST API endpoints.

Covers:
- GET /api/v1/arena/positions — structure, empty case, stats computation
- GET /api/v1/arena/candles/{symbol} — candle format, empty case, missing symbol
- JWT auth required on both endpoints
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.server import create_app
from argus.api.dependencies import AppState
from argus.data.intraday_candle_store import IntradayCandleStore
from argus.execution.order_manager import ManagedPosition
from argus.strategies.patterns.base import CandleBar


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_position(
    symbol: str = "AAPL",
    strategy_id: str = "orb_breakout",
    entry_price: float = 150.00,
    original_stop_price: float = 148.00,
    trail_active: bool = False,
    trail_stop_price: float = 0.0,
    quality_grade: str = "B+",
    entry_time: datetime | None = None,
) -> ManagedPosition:
    now = entry_time or datetime(2026, 4, 1, 14, 0, 0, tzinfo=UTC)
    return ManagedPosition(
        symbol=symbol,
        strategy_id=strategy_id,
        entry_price=entry_price,
        entry_time=now,
        shares_total=100,
        shares_remaining=100,
        stop_price=original_stop_price,
        original_stop_price=original_stop_price,
        stop_order_id="stop_001",
        t1_price=entry_price + 2.0,
        t1_order_id="t1_001",
        t1_shares=50,
        t1_filled=False,
        t2_price=entry_price + 4.0,
        high_watermark=entry_price,
        trail_active=trail_active,
        trail_stop_price=trail_stop_price,
        quality_grade=quality_grade,
    )


def _make_candle_bar(
    ts: datetime,
    open_: float = 150.0,
    high: float = 151.0,
    low: float = 149.5,
    close: float = 150.5,
    volume: float = 10000,
) -> CandleBar:
    return CandleBar(
        timestamp=ts,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def arena_client(
    app_state: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Client with clean app state (no positions, no candle store)."""
    app = create_app(app_state)
    app.state.app_state = app_state
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def arena_client_with_positions(
    app_state: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Client with two managed positions injected into OrderManager."""
    pos1 = _make_position(
        symbol="AAPL",
        entry_price=150.0,
        original_stop_price=148.0,
        entry_time=datetime(2026, 4, 1, 13, 30, 0, tzinfo=UTC),
    )
    pos2 = _make_position(
        symbol="NVDA",
        entry_price=900.0,
        original_stop_price=890.0,
        trail_active=True,
        trail_stop_price=895.0,
        quality_grade="A",
        entry_time=datetime(2026, 4, 1, 13, 45, 0, tzinfo=UTC),
    )
    for pos in [pos1, pos2]:
        sym = pos.symbol
        if sym not in app_state.order_manager._managed_positions:
            app_state.order_manager._managed_positions[sym] = []
        app_state.order_manager._managed_positions[sym].append(pos)

    app = create_app(app_state)
    app.state.app_state = app_state
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def arena_client_with_candles(
    app_state: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Client with a populated IntradayCandleStore."""
    store = IntradayCandleStore()
    base_ts = datetime(2026, 4, 1, 9, 30, 0, tzinfo=UTC)
    for i in range(35):
        bar_ts = base_ts + timedelta(minutes=i)
        # Directly populate internal store to skip CandleEvent routing
        from collections import deque
        from argus.data.intraday_candle_store import _MAX_BARS_PER_SYMBOL

        if "AAPL" not in store._bars:
            store._bars["AAPL"] = deque(maxlen=_MAX_BARS_PER_SYMBOL)
        store._bars["AAPL"].append(
            _make_candle_bar(bar_ts, open_=150.0 + i * 0.1, close=150.05 + i * 0.1)
        )

    app_state.candle_store = store

    app = create_app(app_state)
    app.state.app_state = app_state
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Tests: JWT auth required
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_positions_requires_auth(arena_client: AsyncClient) -> None:
    """GET /arena/positions without auth returns 401."""
    response = await arena_client.get("/api/v1/arena/positions")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_candles_requires_auth(arena_client: AsyncClient) -> None:
    """GET /arena/candles/{symbol} without auth returns 401."""
    response = await arena_client.get("/api/v1/arena/candles/AAPL")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: GET /arena/positions — empty case
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_positions_empty_returns_correct_structure(
    arena_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /arena/positions with no open positions returns empty list with stats."""
    response = await arena_client.get("/api/v1/arena/positions", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["positions"] == []
    assert body["stats"]["position_count"] == 0
    assert body["stats"]["total_pnl"] == 0.0
    assert body["stats"]["net_r"] == 0.0
    assert "timestamp" in body


# ---------------------------------------------------------------------------
# Tests: GET /arena/positions — with positions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_positions_returns_correct_count(
    arena_client_with_positions: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /arena/positions returns one entry per open position."""
    response = await arena_client_with_positions.get(
        "/api/v1/arena/positions", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["positions"]) == 2
    assert body["stats"]["position_count"] == 2


@pytest.mark.asyncio
async def test_positions_response_schema(
    arena_client_with_positions: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Each position contains all required schema fields."""
    response = await arena_client_with_positions.get(
        "/api/v1/arena/positions", headers=auth_headers
    )
    assert response.status_code == 200
    positions = response.json()["positions"]
    required_fields = {
        "symbol", "strategy_id", "side", "shares", "entry_price",
        "current_price", "stop_price", "target_prices", "trailing_stop_price",
        "unrealized_pnl", "r_multiple", "hold_duration_seconds", "quality_grade",
        "entry_time",
    }
    for pos in positions:
        assert required_fields.issubset(pos.keys()), f"Missing fields in {pos}"


@pytest.mark.asyncio
async def test_positions_trailing_stop_null_when_not_active(
    arena_client_with_positions: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """trailing_stop_price is null when trail is not active."""
    response = await arena_client_with_positions.get(
        "/api/v1/arena/positions", headers=auth_headers
    )
    positions = response.json()["positions"]
    aapl = next(p for p in positions if p["symbol"] == "AAPL")
    assert aapl["trailing_stop_price"] is None


@pytest.mark.asyncio
async def test_positions_trailing_stop_populated_when_active(
    arena_client_with_positions: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """trailing_stop_price is a float when trail_active=True."""
    response = await arena_client_with_positions.get(
        "/api/v1/arena/positions", headers=auth_headers
    )
    positions = response.json()["positions"]
    nvda = next(p for p in positions if p["symbol"] == "NVDA")
    assert nvda["trailing_stop_price"] == 895.0


@pytest.mark.asyncio
async def test_positions_target_prices_list(
    arena_client_with_positions: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """target_prices is a list with t1 and t2."""
    response = await arena_client_with_positions.get(
        "/api/v1/arena/positions", headers=auth_headers
    )
    positions = response.json()["positions"]
    for pos in positions:
        assert isinstance(pos["target_prices"], list)
        assert len(pos["target_prices"]) == 2


# ---------------------------------------------------------------------------
# Tests: GET /arena/candles/{symbol}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_candles_unknown_symbol_returns_empty(
    arena_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /arena/candles for unknown symbol returns empty candles list."""
    response = await arena_client.get("/api/v1/arena/candles/UNKNOWN", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "UNKNOWN"
    assert body["candles"] == []


@pytest.mark.asyncio
async def test_candles_no_store_returns_empty(
    arena_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /arena/candles when candle_store is None returns empty list."""
    # Default app_state has candle_store=None
    response = await arena_client.get("/api/v1/arena/candles/AAPL", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["candles"] == []


@pytest.mark.asyncio
async def test_candles_returns_correct_structure(
    arena_client_with_candles: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /arena/candles returns OHLCV bars with Unix timestamps."""
    response = await arena_client_with_candles.get(
        "/api/v1/arena/candles/AAPL", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "AAPL"
    assert len(body["candles"]) > 0

    candle = body["candles"][0]
    for field in ("time", "open", "high", "low", "close", "volume"):
        assert field in candle, f"Missing field: {field}"
    # time must be an integer Unix timestamp
    assert isinstance(candle["time"], int)


@pytest.mark.asyncio
async def test_candles_minutes_param_limits_count(
    arena_client_with_candles: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """minutes query param limits number of bars returned."""
    response = await arena_client_with_candles.get(
        "/api/v1/arena/candles/AAPL?minutes=10", headers=auth_headers
    )
    assert response.status_code == 200
    # 35 bars stored, requesting 10 — should get at most 10
    assert len(response.json()["candles"]) <= 10
