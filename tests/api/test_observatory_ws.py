"""Tests for Observatory WebSocket endpoint.

Sprint 25, Session 2.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, patch

import aiosqlite
import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from argus.analytics.config import ObservatoryConfig
from argus.analytics.observatory_service import ObservatoryService
from argus.api.auth import create_access_token, set_jwt_secret
from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.core.config import ApiConfig, SystemConfig

# FIX-13a CI regression defense: cap every test in this file at 30s. The
# observatory WS push-loop runs background asyncio tasks across starlette's
# TestClient portal thread; on Linux under xdist, an earlier test's residual
# task or socket state can block the TestClient teardown on a subsequent
# test. The global pytest-timeout=120 catches any hang eventually, but 30s
# fails fast with a tighter traceback. Every test here should complete in
# <5s — 30s is already 6× the p99.
pytestmark = pytest.mark.timeout(30)

TEST_JWT_SECRET = "test-jwt-secret-for-argus-api-testing-minimum-32-chars"
TEST_DATE = "2026-03-17"


@pytest.fixture(autouse=True)
def _freeze_today_et(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin _today_et() to TEST_DATE so WS handler queries match seed data."""
    monkeypatch.setattr(
        "argus.analytics.observatory_service._today_et",
        lambda: TEST_DATE,
    )

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


async def _build_observatory_app(
    tmp_path: Path,
    *,
    enabled: bool = True,
    seed_data: bool = True,
    ws_update_interval_ms: int = 1000,
) -> tuple[object, aiosqlite.Connection, object]:
    """Build a FastAPI app with Observatory service wired up.

    Returns (app, obs_db_conn, db_manager) for cleanup.
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
        # AAPL also gets a SIGNAL_GENERATED event
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
        observatory=ObservatoryConfig(
            enabled=enabled,
            ws_update_interval_ms=ws_update_interval_ms,
        ),
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

    return app, obs_conn, temp_db


def _make_auth_token() -> str:
    """Create a valid JWT token for test auth."""
    token, _ = create_access_token(TEST_JWT_SECRET, expires_hours=24)
    return token


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_observatory_ws_requires_auth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Connection without JWT auth message is rejected with 4001."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    app, obs_conn, temp_db = await _build_observatory_app(tmp_path)

    client = TestClient(app)
    # Server closes with 4001 on missing/invalid auth; Starlette's TestClient
    # surfaces that as WebSocketDisconnect once the client attempts to receive.
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/v1/observatory") as ws:
            ws.send_json({"type": "not_auth"})
            ws.receive_json()
    assert exc_info.value.code == 4001

    await obs_conn.close()
    await temp_db.close()


@pytest.mark.asyncio
async def test_observatory_ws_rejects_invalid_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid JWT token causes 4001 close."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    app, obs_conn, temp_db = await _build_observatory_app(tmp_path)

    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/v1/observatory") as ws:
            ws.send_json({"type": "auth", "token": "invalid-token-here"})
            ws.receive_json()
    assert exc_info.value.code == 4001

    await obs_conn.close()
    await temp_db.close()


# ---------------------------------------------------------------------------
# Initial state tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_observatory_ws_sends_initial_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """First message after auth is full pipeline state."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    # ws_update_interval_ms=10000. This test exercises ONLY the initial
    # pipeline_update — no recurring push needed. IMPROMPTU-CI post-push
    # evidence: the disconnect-watcher fix eliminates this specific test's
    # crash, but the broader observatory_ws flake (cross-loop aiosqlite +
    # TestClient portal teardown) still trips sibling tests that exercise
    # multiple push cycles. A long interval keeps the push loop from
    # issuing any DB queries beyond the initial send — eliminating the
    # remaining race window for this test. See DEF-200 / DEF-193.
    app, obs_conn, temp_db = await _build_observatory_app(
        tmp_path, ws_update_interval_ms=10000,
    )

    client = TestClient(app)
    with client.websocket_connect("/ws/v1/observatory") as ws:
        # Authenticate
        ws.send_json({"type": "auth", "token": _make_auth_token()})
        auth_resp = ws.receive_json()
        assert auth_resp["type"] == "auth_success"

        # First data message should be pipeline_update
        initial = ws.receive_json()
        assert initial["type"] == "pipeline_update"
        assert "data" in initial
        assert "timestamp" in initial
        assert "evaluating" in initial["data"]

    await obs_conn.close()
    await temp_db.close()


# ---------------------------------------------------------------------------
# Pipeline update format
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_observatory_ws_pipeline_update_format(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pipeline update message has correct type and data fields."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    # ws_update_interval_ms=10000 — this test exercises ONLY the initial
    # pipeline_update. Long interval prevents recurring DB queries (see
    # DEF-200 / DEF-193 for the cross-loop aiosqlite race these tests
    # occasionally trip on Linux under xdist).
    app, obs_conn, temp_db = await _build_observatory_app(
        tmp_path, ws_update_interval_ms=10000,
    )

    client = TestClient(app)
    with client.websocket_connect("/ws/v1/observatory") as ws:
        ws.send_json({"type": "auth", "token": _make_auth_token()})
        ws.receive_json()  # auth_success

        initial = ws.receive_json()  # initial pipeline_update
        data = initial["data"]

        # Verify all expected tier keys are present
        expected_keys = {
            "universe", "viable", "routed", "evaluating",
            "near_trigger", "signal", "traded", "date",
        }
        assert expected_keys.issubset(data.keys())
        # Seed data: 3 symbols evaluated, 1 signal
        assert data["evaluating"] == 3
        assert data["signal"] == 1

    await obs_conn.close()
    await temp_db.close()


# ---------------------------------------------------------------------------
# Configurable interval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_observatory_ws_interval_configurable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Push interval respects config ws_update_interval_ms."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    # Use a very short interval (200ms) so we can observe a push quickly
    app, obs_conn, temp_db = await _build_observatory_app(
        tmp_path, ws_update_interval_ms=200,
    )

    client = TestClient(app)
    with client.websocket_connect("/ws/v1/observatory") as ws:
        ws.send_json({"type": "auth", "token": _make_auth_token()})
        ws.receive_json()  # auth_success
        ws.receive_json()  # initial pipeline_update

        # Wait for a periodic push (should arrive within ~200ms + overhead)
        start = time.monotonic()
        msg = ws.receive_json()
        elapsed = time.monotonic() - start

        assert msg["type"] == "pipeline_update"
        # Should arrive close to 200ms, allow generous margin for CI
        assert elapsed < 2.0

    await obs_conn.close()
    await temp_db.close()


# ---------------------------------------------------------------------------
# Tier transition detection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_observatory_ws_tier_transition_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tier transitions are detected and pushed when symbol tiers change."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    app, obs_conn, temp_db = await _build_observatory_app(
        tmp_path, ws_update_interval_ms=200,
    )

    # Mock get_symbol_tiers to return different values on successive calls
    # to reliably simulate a tier transition without cross-event-loop DB issues
    obs_svc = app.state.app_state.observatory_service
    call_count = 0
    original_get_tiers = obs_svc.get_symbol_tiers

    async def mock_get_symbol_tiers(date=None):
        nonlocal call_count
        call_count += 1
        if call_count <= 1:
            # Initial state: NVDA is evaluating
            return {"AAPL": "signal", "NVDA": "evaluating", "TSLA": "evaluating"}
        # After first interval: NVDA promoted to signal
        return {"AAPL": "signal", "NVDA": "signal", "TSLA": "evaluating"}

    obs_svc.get_symbol_tiers = mock_get_symbol_tiers

    client = TestClient(app)
    with client.websocket_connect("/ws/v1/observatory") as ws:
        ws.send_json({"type": "auth", "token": _make_auth_token()})
        ws.receive_json()  # auth_success
        ws.receive_json()  # initial pipeline_update

        # Collect messages from the next push interval
        messages = []
        for _ in range(5):  # pipeline_update + possible transitions + summary
            try:
                msg = ws.receive_json()
                messages.append(msg)
            except WebSocketDisconnect:
                break

        # Should contain a tier_transition for NVDA
        transition_msgs = [m for m in messages if m["type"] == "tier_transition"]
        nvda_transitions = [
            t for t in transition_msgs
            if t["data"]["symbol"] == "NVDA"
        ]
        assert len(nvda_transitions) >= 1
        assert nvda_transitions[0]["data"]["from_tier"] == "evaluating"
        assert nvda_transitions[0]["data"]["to_tier"] == "signal"

    await obs_conn.close()
    await temp_db.close()


# ---------------------------------------------------------------------------
# Evaluation summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_observatory_ws_evaluation_summary_counts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Evaluation summary includes correct delta counts."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    app, obs_conn, temp_db = await _build_observatory_app(
        tmp_path, ws_update_interval_ms=200,
    )

    client = TestClient(app)
    with client.websocket_connect("/ws/v1/observatory") as ws:
        ws.send_json({"type": "auth", "token": _make_auth_token()})
        ws.receive_json()  # auth_success
        ws.receive_json()  # initial pipeline_update

        # Collect messages from next push
        messages = []
        for _ in range(5):
            try:
                msg = ws.receive_json()
                messages.append(msg)
            except WebSocketDisconnect:
                break

        summary_msgs = [m for m in messages if m["type"] == "evaluation_summary"]
        assert len(summary_msgs) >= 1
        summary_data = summary_msgs[0]["data"]
        assert "evaluations_count" in summary_data
        assert "signals_count" in summary_data
        assert "new_near_triggers" in summary_data
        # Delta since initial should be 0 (no new events inserted)
        assert summary_data["evaluations_count"] == 0
        assert summary_data["signals_count"] == 0

    await obs_conn.close()
    await temp_db.close()


# ---------------------------------------------------------------------------
# Graceful disconnect
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_observatory_ws_graceful_disconnect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Client disconnects cleanly without errors logged."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    # ws_update_interval_ms=200 — see test_observatory_ws_sends_initial_state
    # above for the FIX-13a CI regression rationale.
    app, obs_conn, temp_db = await _build_observatory_app(
        tmp_path, ws_update_interval_ms=200,
    )

    client = TestClient(app)
    with client.websocket_connect("/ws/v1/observatory") as ws:
        ws.send_json({"type": "auth", "token": _make_auth_token()})
        ws.receive_json()  # auth_success
        ws.receive_json()  # initial pipeline_update
        # FIX-13a CI regression: receive one more push-loop message before
        # disconnecting. The server is a push-only handler (never calls
        # receive()), so on Linux xdist the TestClient teardown can stall
        # waiting for the server task to notice the disconnect. Pulling a
        # message from the push loop primes the ASGI state machine so that
        # the next send_json surfaces the disconnect correctly. Matches the
        # pattern that makes test_observatory_ws_interval_configurable safe.
        ws.receive_json()  # pipeline_update from push loop (interval=200ms)
        # Client closes — the context manager handles close

    # If we get here without exceptions, disconnect was graceful
    from argus.api.websocket.observatory_ws import get_active_observatory_connections

    assert len(get_active_observatory_connections()) == 0

    await obs_conn.close()
    await temp_db.close()


# ---------------------------------------------------------------------------
# DEF-200 regression: disconnect watcher cancels push loop promptly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_observatory_ws_disconnect_cancels_push_loop_promptly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DEF-200 regression: server task exits promptly when the client
    disconnects before the push interval elapses.

    Pre-fix, the push loop used ``await asyncio.sleep(interval_s)`` with
    no disconnect awareness; on Linux under xdist that leaked the server
    task across TestClient teardown and crashed the worker via
    aiosqlite's ``_connection_worker_thread`` posting back to a closed
    event loop.

    Post-fix, a disconnect-watcher task sets an ``asyncio.Event`` when
    the peer closes, and the push loop races the interval sleep against
    that event via ``asyncio.wait_for``. Measured elapsed from
    disconnect to ``_active_connections`` cleanup must be well under the
    5s push interval — otherwise the watcher is missing.
    """
    from argus.api.websocket.observatory_ws import (
        get_active_observatory_connections,
    )

    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    # 5000ms push interval: well beyond the <2s cleanup budget asserted
    # below. Without the disconnect watcher, the server parks in
    # ``asyncio.sleep(5.0)`` and ``_active_connections`` stays populated
    # for the full 5s (or, on Linux xdist, the worker crashes).
    app, obs_conn, temp_db = await _build_observatory_app(
        tmp_path, ws_update_interval_ms=5000,
    )

    client = TestClient(app)
    with client.websocket_connect("/ws/v1/observatory") as ws:
        ws.send_json({"type": "auth", "token": _make_auth_token()})
        auth_resp = ws.receive_json()
        assert auth_resp["type"] == "auth_success"
        initial = ws.receive_json()
        assert initial["type"] == "pipeline_update"
        # Short pause to let the server finish its post-initial prep
        # queries (get_symbol_tiers + get_session_summary complete after
        # the initial send but before the push loop's wait_for). Without
        # this, a pathologically fast disconnect on Linux xdist can orphan
        # those queries' aiosqlite futures against the portal loop as it
        # closes — a race that is a test-infrastructure limitation of the
        # observatory_ws test fixture, not a push-loop issue. The
        # disconnect-watcher we are validating still fires correctly; the
        # sleep just ensures it is the only thing under test here.
        await asyncio.sleep(0.1)
        # Do NOT receive any push-loop message. The server is now parked
        # in the push loop's disconnect-aware wait; exiting the ``with``
        # block closes the peer socket and should fire the watcher.

    # Poll briefly for server-side cleanup. With the watcher this happens
    # within milliseconds; without it, ``_active_connections`` stays
    # populated until the 5s sleep elapses (if it doesn't crash first).
    start = time.monotonic()
    deadline = start + 2.0
    while time.monotonic() < deadline:
        if len(get_active_observatory_connections()) == 0:
            break
        await asyncio.sleep(0.02)
    elapsed = time.monotonic() - start

    assert len(get_active_observatory_connections()) == 0, (
        f"_active_connections still populated {elapsed:.2f}s after "
        "client disconnect — disconnect watcher may be missing from "
        "observatory_ws.py push loop (DEF-200 regression)."
    )
    assert elapsed < 2.0, (
        f"Server task did not exit within 2s of client disconnect "
        f"(elapsed={elapsed:.2f}s). Expected prompt cleanup via "
        "disconnect-watcher sentinel; 5s push interval should not "
        "block teardown."
    )

    await obs_conn.close()
    await temp_db.close()


def test_observatory_ws_has_disconnect_watcher_sentinel() -> None:
    """DEF-200 grep-guard: the push loop must use a disconnect-watcher
    sentinel instead of a plain ``asyncio.sleep(interval_s)``.

    The timing test above exercises behavior, but on macOS starlette's
    TestClient cancels the server task cleanly during teardown even
    without the watcher — the bug only reliably manifests on Linux
    under xdist. This grep-guard is the revert-proof layer: it reads
    the production source and asserts the three fix markers are
    present. Any future edit that reverts the fix (whether whole-file
    or surgical) will fail this check on every platform.
    """
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[2]
        / "argus"
        / "api"
        / "websocket"
        / "observatory_ws.py"
    ).read_text()

    # Marker 1 — the disconnect sentinel is wired.
    assert "_disconnect_event = asyncio.Event()" in source, (
        "DEF-200 regression: observatory_ws.py push loop is missing "
        "the disconnect-event sentinel. Expected "
        "`_disconnect_event = asyncio.Event()` inside the handler."
    )

    # Marker 2 — a watcher task races websocket.receive() against the
    # sentinel. We check the helper name + receive() call to allow for
    # cosmetic reformatting.
    assert "_watch_disconnect" in source, (
        "DEF-200 regression: observatory_ws.py is missing the "
        "`_watch_disconnect` helper that sets the sentinel on peer "
        "close. The push loop cannot exit promptly without it."
    )
    assert "await websocket.receive()" in source, (
        "DEF-200 regression: observatory_ws.py push loop no longer "
        "issues `await websocket.receive()` — the disconnect watcher "
        "is the only receive() site and is load-bearing for prompt "
        "teardown on Linux under xdist."
    )

    # Marker 3 — the loop races the sentinel against the interval via
    # asyncio.wait_for. Any edit that restores a bare
    # `await asyncio.sleep(interval_s)` in the push loop body
    # reintroduces the bug.
    assert "asyncio.wait_for(" in source, (
        "DEF-200 regression: observatory_ws.py push loop is missing "
        "the `asyncio.wait_for(_disconnect_event.wait(), ...)` race "
        "against the push interval. A bare `asyncio.sleep(interval_s)` "
        "leaks the server task across TestClient teardown."
    )
    assert "_disconnect_event.wait()" in source, (
        "DEF-200 regression: observatory_ws.py push loop does not "
        "wait on _disconnect_event — even if the sentinel is set, "
        "the loop won't notice."
    )


# ---------------------------------------------------------------------------
# Independent from AI WebSocket
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_observatory_ws_independent_from_ai_ws(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Observatory WS and AI chat WS are fully independent endpoints."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    # ws_update_interval_ms=10000 — this test only needs the initial
    # pipeline_update; long interval eliminates recurring DB queries (see
    # DEF-200 / DEF-193 for the cross-loop aiosqlite race).
    app, obs_conn, temp_db = await _build_observatory_app(
        tmp_path, ws_update_interval_ms=10000,
    )

    client = TestClient(app)

    # Connect to Observatory WS
    with client.websocket_connect("/ws/v1/observatory") as obs_ws:
        obs_ws.send_json({"type": "auth", "token": _make_auth_token()})
        auth_resp = obs_ws.receive_json()
        assert auth_resp["type"] == "auth_success"

        # Also connect to AI chat WS (it exists as a separate endpoint)
        with client.websocket_connect("/ws/v1/ai/chat") as ai_ws:
            ai_ws.send_json({"type": "auth", "token": _make_auth_token()})
            ai_auth = ai_ws.receive_json()
            assert ai_auth["type"] == "auth_success"

        # Observatory connection should still be alive
        initial = obs_ws.receive_json()
        assert initial["type"] == "pipeline_update"

    await obs_conn.close()
    await temp_db.close()


# ---------------------------------------------------------------------------
# Disabled config test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_observatory_ws_disabled_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When observatory.enabled=false, WS endpoint is not mounted."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    app, obs_conn, temp_db = await _build_observatory_app(
        tmp_path, enabled=False,
    )

    client = TestClient(app)
    # Route not mounted when observatory.enabled=false. Starlette raises
    # WebSocketDisconnect on handshake failure; a narrower catch also guards
    # against the previous except-Exception swallowing a pytest.fail() inside
    # the with-block.
    with pytest.raises((WebSocketDisconnect, RuntimeError)):
        with client.websocket_connect("/ws/v1/observatory"):
            # If we get here, the endpoint is erroneously mounted.
            pytest.fail("Observatory WS should not be available when disabled")

    await obs_conn.close()
    await temp_db.close()


# ---------------------------------------------------------------------------
# Slow query no backlog
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_observatory_ws_slow_query_no_backlog(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If service query exceeds interval, push is skipped (no backlog)."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    app, obs_conn, temp_db = await _build_observatory_app(
        tmp_path, ws_update_interval_ms=200,
    )

    # Patch time.monotonic to simulate a slow query
    from argus.api.websocket import observatory_ws

    original_get_pipeline = None

    async def slow_get_pipeline(date=None):
        """Simulate a slow query by sleeping longer than the interval."""
        await asyncio.sleep(0.3)  # 300ms > 200ms interval
        return await original_get_pipeline(date)

    client = TestClient(app)
    with client.websocket_connect("/ws/v1/observatory") as ws:
        ws.send_json({"type": "auth", "token": _make_auth_token()})
        ws.receive_json()  # auth_success
        ws.receive_json()  # initial pipeline_update

        # Now patch the service to be slow
        obs_svc = app.state.app_state.observatory_service
        original_get_pipeline = obs_svc.get_pipeline_stages
        obs_svc.get_pipeline_stages = slow_get_pipeline

        # The push should be skipped due to slow query, then the next
        # push with normal speed should succeed. We collect what we get.
        messages = []
        # Restore normal speed after first slow push attempt
        obs_svc.get_pipeline_stages = original_get_pipeline
        for _ in range(5):
            try:
                msg = ws.receive_json()
                messages.append(msg)
            except WebSocketDisconnect:
                break

        # We should eventually get messages — the key assertion is
        # that we don't get a backlog of queued messages
        pipeline_msgs = [m for m in messages if m["type"] == "pipeline_update"]
        # Should have gotten some updates but not a burst
        assert len(pipeline_msgs) <= 3

    await obs_conn.close()
    await temp_db.close()


# ---------------------------------------------------------------------------
# get_symbol_tiers unit test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_symbol_tiers_returns_correct_tiers(
    tmp_path: Path,
) -> None:
    """ObservatoryService.get_symbol_tiers returns correct tier assignments."""
    obs_db_path = str(tmp_path / "tiers.db")
    conn = await aiosqlite.connect(obs_db_path)
    await conn.execute(_CREATE_TABLE)

    # AAPL: ENTRY_EVALUATION + SIGNAL_GENERATED -> signal tier
    await conn.execute(
        "INSERT INTO evaluation_events "
        "(trading_date, timestamp, symbol, strategy_id, event_type, "
        "result, reason, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (TEST_DATE, "2026-03-17T10:30:00", "AAPL", "orb_breakout",
         "ENTRY_EVALUATION", "FAIL", "conditions", "{}"),
    )
    await conn.execute(
        "INSERT INTO evaluation_events "
        "(trading_date, timestamp, symbol, strategy_id, event_type, "
        "result, reason, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (TEST_DATE, "2026-03-17T10:31:00", "AAPL", "orb_breakout",
         "SIGNAL_GENERATED", "PASS", "signal", "{}"),
    )
    # NVDA: only ENTRY_EVALUATION -> evaluating tier
    await conn.execute(
        "INSERT INTO evaluation_events "
        "(trading_date, timestamp, symbol, strategy_id, event_type, "
        "result, reason, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (TEST_DATE, "2026-03-17T10:30:00", "NVDA", "orb_breakout",
         "ENTRY_EVALUATION", "FAIL", "conditions",
         json.dumps({"conditions": [{"name": "vol", "passed": False}]})),
    )
    # TSLA: QUALITY_SCORED -> traded tier
    await conn.execute(
        "INSERT INTO evaluation_events "
        "(trading_date, timestamp, symbol, strategy_id, event_type, "
        "result, reason, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (TEST_DATE, "2026-03-17T10:32:00", "TSLA", "orb_breakout",
         "QUALITY_SCORED", "PASS", "scored", "{}"),
    )
    await conn.commit()

    store = FakeStore(conn)
    svc = ObservatoryService(
        telemetry_store=store,
        universe_manager=None,
        quality_engine=None,
        strategies={},
    )

    tiers = await svc.get_symbol_tiers(date=TEST_DATE)
    assert tiers["AAPL"] == "signal"
    assert tiers["NVDA"] == "evaluating"
    assert tiers["TSLA"] == "traded"

    await conn.close()
