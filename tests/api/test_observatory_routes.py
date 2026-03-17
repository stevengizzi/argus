"""Tests for Observatory API routes.

Sprint 25, Session 1.
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator
from pathlib import Path

import aiosqlite
import pytest
from httpx import ASGITransport, AsyncClient

from argus.analytics.config import ObservatoryConfig
from argus.analytics.observatory_service import ObservatoryService
from argus.api.auth import create_access_token, set_jwt_secret
from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.core.config import ApiConfig, SystemConfig

TEST_JWT_SECRET = "test-jwt-secret-for-argus-api-testing-minimum-32-chars"
TEST_DATE = "2026-03-17"

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS evaluation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trading_date TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    result TEXT NOT NULL,
    reason TEXT NOT NULL,
    metadata_json TEXT DEFAULT '{}'
)
"""


class FakeStore:
    """Minimal stand-in for EvaluationEventStore with a real SQLite connection."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    @property
    def is_connected(self) -> bool:
        """Return True if the database connection is open."""
        return self._conn is not None

    async def execute_query(
        self, sql: str, params: tuple[object, ...] = ()
    ) -> list[aiosqlite.Row]:
        """Execute a read-only SQL query and return all rows."""
        cursor = await self._conn.execute(sql, params)
        return await cursor.fetchall()


async def _build_observatory_client(
    tmp_path: Path,
    *,
    enabled: bool = True,
    seed_data: bool = True,
) -> tuple[AsyncClient, aiosqlite.Connection, object]:
    """Build an httpx client with Observatory service.

    Returns (client, obs_db_conn, db_manager) for cleanup.
    """
    from argus.analytics.trade_logger import TradeLogger
    from argus.api.auth import hash_password
    from argus.core.clock import FixedClock
    from argus.core.config import HealthConfig, OrderManagerConfig, RiskConfig
    from argus.core.event_bus import EventBus
    from argus.core.health import HealthMonitor
    from argus.core.risk_manager import RiskManager
    from argus.db.manager import DatabaseManager
    from argus.execution.order_manager import OrderManager
    from argus.execution.simulated_broker import SimulatedBroker
    from datetime import datetime, UTC

    # Create eval events DB
    obs_db_path = str(tmp_path / "obs_eval.db")
    obs_conn = await aiosqlite.connect(obs_db_path)
    await obs_conn.execute(_CREATE_TABLE)
    await obs_conn.commit()

    if seed_data:
        for sym in ["AAPL", "NVDA", "TSLA"]:
            await obs_conn.execute(
                "INSERT INTO evaluation_events "
                "(trading_date, timestamp, symbol, strategy_id, event_type, "
                "result, reason, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (TEST_DATE, "2026-03-17T10:30:00", sym, "orb_breakout",
                 "ENTRY_EVALUATION", "FAIL", "conditions not met",
                 json.dumps({"conditions": [
                     {"name": "volume", "passed": True},
                     {"name": "range", "passed": sym == "AAPL"},
                 ]})),
            )
        await obs_conn.execute(
            "INSERT INTO evaluation_events "
            "(trading_date, timestamp, symbol, strategy_id, event_type, "
            "result, reason, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (TEST_DATE, "2026-03-17T10:31:00", "AAPL", "orb_breakout",
             "SIGNAL_GENERATED", "PASS", "signal generated", "{}"),
        )
        await obs_conn.commit()

    # Build minimal AppState
    clock = FixedClock(datetime(2026, 3, 17, 14, 30, 0, tzinfo=UTC))
    event_bus = EventBus()
    broker = SimulatedBroker(initial_cash=100_000.0)
    await broker.connect()
    temp_db = DatabaseManager(tmp_path / "logger.db")
    await temp_db.initialize()
    trade_logger = TradeLogger(temp_db)
    health_monitor = HealthMonitor(
        event_bus=event_bus, clock=clock, config=HealthConfig(),
        broker=broker, trade_logger=trade_logger,
    )
    risk_manager = RiskManager(
        config=RiskConfig(), broker=broker, event_bus=event_bus, clock=clock,
    )
    order_manager = OrderManager(
        event_bus=event_bus, broker=broker, clock=clock,
        config=OrderManagerConfig(), trade_logger=trade_logger,
    )

    config = SystemConfig(
        api=ApiConfig(password_hash=hash_password("testpassword123")),
        observatory=ObservatoryConfig(enabled=enabled),
    )

    store = FakeStore(obs_conn)
    obs_svc = ObservatoryService(
        telemetry_store=store,
        universe_manager=None,
        quality_engine=None,
        strategies={},
    ) if enabled else None

    app_state = AppState(
        event_bus=event_bus,
        trade_logger=trade_logger,
        broker=broker,
        health_monitor=health_monitor,
        risk_manager=risk_manager,
        order_manager=order_manager,
        strategies={},
        clock=clock,
        config=config,
        start_time=time.time(),
        observatory_service=obs_svc,
    )

    app = create_app(app_state)
    app.state.app_state = app_state

    client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )

    return client, obs_conn, temp_db


@pytest.fixture
async def observatory_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx client with Observatory service wired up."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    client, obs_conn, temp_db = await _build_observatory_client(
        tmp_path, enabled=True, seed_data=True,
    )
    async with client:
        yield client
    await obs_conn.close()
    await temp_db.close()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Provide Authorization headers with a valid JWT token."""
    token, _ = create_access_token(TEST_JWT_SECRET, expires_hours=24)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_observatory_endpoints_require_auth(
    observatory_client: AsyncClient,
) -> None:
    """All observatory endpoints return 401 without JWT."""
    endpoints = [
        f"/api/v1/observatory/pipeline?date={TEST_DATE}",
        f"/api/v1/observatory/closest-misses?date={TEST_DATE}",
        f"/api/v1/observatory/symbol/AAPL/journey?date={TEST_DATE}",
        f"/api/v1/observatory/session-summary?date={TEST_DATE}",
    ]
    for url in endpoints:
        resp = await observatory_client.get(url)
        assert resp.status_code == 401, f"{url} returned {resp.status_code}"


# ---------------------------------------------------------------------------
# Pipeline endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_endpoint(
    observatory_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Pipeline endpoint returns correct structure and counts."""
    resp = await observatory_client.get(
        f"/api/v1/observatory/pipeline?date={TEST_DATE}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["evaluating"] == 3
    assert data["signal"] == 1
    assert "timestamp" in data


# ---------------------------------------------------------------------------
# Closest misses endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_closest_misses_endpoint(
    observatory_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Closest misses endpoint returns sorted results."""
    resp = await observatory_client.get(
        f"/api/v1/observatory/closest-misses?tier=evaluating&date={TEST_DATE}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "evaluating"
    assert data["count"] == 3
    # AAPL should be first (2 conditions passed)
    assert data["items"][0]["symbol"] == "AAPL"
    assert data["items"][0]["conditions_passed"] == 2


# ---------------------------------------------------------------------------
# Symbol journey endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_symbol_journey_endpoint(
    observatory_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Symbol journey returns chronological events."""
    resp = await observatory_client.get(
        f"/api/v1/observatory/symbol/AAPL/journey?date={TEST_DATE}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["count"] == 2  # ENTRY_EVALUATION + SIGNAL_GENERATED


@pytest.mark.asyncio
async def test_symbol_journey_unknown_symbol(
    observatory_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Unknown symbol returns empty list, not 404."""
    resp = await observatory_client.get(
        f"/api/v1/observatory/symbol/ZZZZZZ/journey?date={TEST_DATE}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["events"] == []


# ---------------------------------------------------------------------------
# Session summary endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_summary_endpoint(
    observatory_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Session summary returns aggregated metrics."""
    resp = await observatory_client.get(
        f"/api/v1/observatory/session-summary?date={TEST_DATE}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_evaluations"] == 3
    assert data["total_signals"] == 1
    assert data["symbols_evaluated"] == 3
    assert "timestamp" in data


# ---------------------------------------------------------------------------
# Config-gated disabled test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_observatory_disabled_no_routes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When observatory.enabled=false, endpoints return 404."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    client, obs_conn, temp_db = await _build_observatory_client(
        tmp_path, enabled=False, seed_data=False,
    )

    token, _ = create_access_token(TEST_JWT_SECRET, expires_hours=24)
    headers = {"Authorization": f"Bearer {token}"}

    async with client:
        resp = await client.get(
            "/api/v1/observatory/pipeline", headers=headers,
        )
        assert resp.status_code == 404

    await obs_conn.close()
    await temp_db.close()
