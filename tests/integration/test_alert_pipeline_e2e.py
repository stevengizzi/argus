"""Sprint 31.91 Session 5b — alert observability end-to-end pipeline tests.

Drives every alert through the full backend pipeline:
    emit → HealthMonitor consume → SQLite persist → REST `/active`
    → WebSocket fan-out → operator ack via REST → audit-log row
    → auto-resolution predicate fires → archive.

Layered with the two IBKR emitter resolutions (DEF-014):

- ``test_ibkr_disconnect_reconnect_failure_emits_system_alert`` — covers
  the `_reconnect()` exhaustion path now wired by 5b.
- ``test_ibkr_auth_permission_failure_emits_system_alert`` — covers the
  CRITICAL non-connection branch in ``_on_error`` now wired by 5b.

Plus the behavioral Alpaca anti-regression test that pins the
deferred-by-deletion boundary (DEF-178/183, Sprint 31.94).

The WebSocket fan-out is verified through HealthMonitor's
``subscribe_state_changes`` queue — the WS handler in
``argus/api/websocket/alerts_ws.py`` is a thin shim over that queue and
is independently tested in ``tests/api/test_alerts_5a2.py::TestWebSocketFanOut``
+ ``tests/api/test_alerts.py``.
"""

from __future__ import annotations

import asyncio
import inspect
import time as time_module
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
import pytest
from httpx import ASGITransport, AsyncClient

from argus.analytics.trade_logger import TradeLogger
from argus.api.auth import create_access_token, hash_password, set_jwt_secret
from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.core.clock import FixedClock
from argus.core.config import (
    AlertsConfig,
    ApiConfig,
    HealthConfig,
    IBKRConfig,
    OrderManagerConfig,
    ReconciliationConfig,
    SystemConfig,
)
from argus.core.event_bus import EventBus
from argus.core.events import (
    DatabentoHeartbeatEvent,
    IBKRReconnectedEvent,
    OrderFilledEvent,
    ReconciliationCompletedEvent,
    SystemAlertEvent,
)
from argus.core.health import (
    AlertLifecycleState,
    HealthMonitor,
)
from argus.core.risk_manager import RiskManager
from argus.db.manager import DatabaseManager
from argus.execution.ibkr_broker import IBKRBroker
from argus.execution.order_manager import OrderManager
from argus.execution.simulated_broker import SimulatedBroker

TEST_PASSWORD = "testpassword123"
TEST_JWT_SECRET = "test-jwt-secret-for-argus-api-testing-minimum-32-chars"


# ---------------------------------------------------------------------------
# Fixtures (self-contained — these tests need a HealthMonitor with
# operations_db_path wired so audit/persistence rows actually land in
# SQLite, which the shared tests/api/conftest.py fixture does not provide.)
# ---------------------------------------------------------------------------


@pytest.fixture
def operations_db(tmp_path: Path) -> str:
    """Provide a fresh ``data/operations.db`` path for each test."""
    return str(tmp_path / "operations.db")


@pytest.fixture
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    """Monkeypatch ARGUS_JWT_SECRET and return the secret."""
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)
    return TEST_JWT_SECRET


@pytest.fixture
def auth_headers(jwt_secret: str) -> dict[str, str]:
    """Authorization headers with a valid JWT."""
    token, _ = create_access_token(jwt_secret, expires_hours=24)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def system_config(operations_db: str) -> SystemConfig:
    """SystemConfig pointing data_dir at the temp operations DB parent."""
    return SystemConfig(
        api=ApiConfig(
            enabled=True,
            host="127.0.0.1",
            port=8000,
            password_hash=hash_password(TEST_PASSWORD),
            jwt_secret_env="ARGUS_JWT_SECRET",
            jwt_expiry_hours=24,
        ),
        data_dir=str(Path(operations_db).parent),
    )


@pytest.fixture
async def event_bus() -> EventBus:
    """Fresh EventBus for each test."""
    return EventBus()


@pytest.fixture
def alerts_config_short_retention() -> AlertsConfig:
    """AlertsConfig tuned for fast test iteration."""
    return AlertsConfig(
        retention_task_interval_seconds=0.05,
        archived_alert_retention_days=1,
    )


@pytest.fixture
async def health_monitor(
    event_bus: EventBus,
    operations_db: str,
    alerts_config_short_retention: AlertsConfig,
) -> HealthMonitor:
    """HealthMonitor wired with bus + operations.db.

    Subscribes ``on_system_alert_event`` to the bus AND the predicate
    handlers — exactly what ``main.py`` does at startup.
    """
    hm = HealthMonitor(
        event_bus=event_bus,
        clock=FixedClock(datetime.now(UTC)),
        config=HealthConfig(),
        alerts_config=alerts_config_short_retention,
        reconciliation_config=ReconciliationConfig(),
        operations_db_path=operations_db,
    )
    event_bus.subscribe(SystemAlertEvent, hm.on_system_alert_event)
    hm._subscribe_predicate_handlers()
    return hm


@pytest.fixture
async def database_manager(tmp_path: Path) -> AsyncGenerator[DatabaseManager, None]:
    """In-memory database for the TradeLogger."""
    manager = DatabaseManager(tmp_path / "argus_e2e.db")
    await manager.initialize()
    yield manager
    await manager.close()


@pytest.fixture
async def app_state(
    event_bus: EventBus,
    database_manager: DatabaseManager,
    health_monitor: HealthMonitor,
    system_config: SystemConfig,
) -> AppState:
    """Full AppState with our HealthMonitor (operations.db wired)."""
    trade_logger = TradeLogger(database_manager)
    broker = SimulatedBroker(initial_cash=100_000.0)
    await broker.connect()
    clock = FixedClock(datetime.now(UTC))
    from argus.core.config import RiskConfig

    risk_manager = RiskManager(
        config=RiskConfig(),
        broker=broker,
        event_bus=event_bus,
        clock=clock,
    )
    order_manager = OrderManager(
        event_bus=event_bus,
        broker=broker,
        clock=clock,
        config=OrderManagerConfig(),
        trade_logger=trade_logger,
    )
    return AppState(
        event_bus=event_bus,
        trade_logger=trade_logger,
        broker=broker,
        health_monitor=health_monitor,
        risk_manager=risk_manager,
        order_manager=order_manager,
        data_service=None,
        strategies={},
        clock=clock,
        config=system_config,
        start_time=time_module.time(),
    )


@pytest.fixture
async def client(
    app_state: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """httpx AsyncClient wrapping the FastAPI app."""
    app = create_app(app_state)
    app.state.app_state = app_state
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# IBKR broker emitter fixtures (mock ib_async)
# ---------------------------------------------------------------------------


class _MockEvent:
    """Mock for ib_async event objects (supports +=)."""

    def __init__(self) -> None:
        self.handlers: list = []

    def __iadd__(self, handler):  # type: ignore[no-untyped-def]
        self.handlers.append(handler)
        return self


@pytest.fixture
def mock_ib_for_emitter() -> MagicMock:
    """Minimal mock ib_async.IB for the emitter tests.

    Just enough to construct an IBKRBroker without raising.
    """
    ib = MagicMock()
    ib.isConnected.return_value = True
    ib.managedAccounts.return_value = ["U24619949"]
    ib.positions.return_value = []
    ib.openTrades.return_value = []
    ib.trades.return_value = []
    ib.accountValues.return_value = []
    ib.orderStatusEvent = _MockEvent()
    ib.errorEvent = _MockEvent()
    ib.disconnectedEvent = _MockEvent()
    ib.connectedEvent = _MockEvent()
    ib.newOrderEvent = _MockEvent()
    ib.connectAsync = AsyncMock()
    return ib


@pytest.fixture
def ibkr_config_for_emitter() -> IBKRConfig:
    """IBKRConfig with low retry count + base delay for fast tests."""
    return IBKRConfig(
        host="127.0.0.1",
        port=4002,
        client_id=1,
        account="U24619949",
        timeout_seconds=10.0,
        readonly=False,
        reconnect_max_retries=2,
        reconnect_base_delay_seconds=0.01,
    )


# ---------------------------------------------------------------------------
# 1. IBKR emitter unit tests
# ---------------------------------------------------------------------------


class TestIBKRDisconnectEmitter:
    """``ibkr_disconnect`` SystemAlertEvent emitted on reconnect exhaustion."""

    @pytest.mark.asyncio
    async def test_ibkr_disconnect_reconnect_failure_emits_system_alert(
        self,
        mock_ib_for_emitter: MagicMock,
        ibkr_config_for_emitter: IBKRConfig,
        event_bus: EventBus,
    ) -> None:
        """Sprint 31.91 5b: exhausted reconnect retries publishes
        ``SystemAlertEvent(alert_type="ibkr_disconnect", severity="critical")``.

        DEF-014 emitter resolution at the previously-TODO site in
        ``_reconnect``.
        """
        published: list[SystemAlertEvent] = []

        async def capture(evt: SystemAlertEvent) -> None:
            published.append(evt)

        event_bus.subscribe(SystemAlertEvent, capture)

        # connectAsync always raises ConnectionError -> retries exhausted.
        mock_ib_for_emitter.connectAsync = AsyncMock(
            side_effect=ConnectionError("Connection refused")
        )

        with (
            patch("argus.execution.ibkr_broker.IB", return_value=mock_ib_for_emitter),
            patch("argus.execution.ibkr_broker.asyncio.sleep", new_callable=AsyncMock),
        ):
            broker = IBKRBroker(ibkr_config_for_emitter, event_bus)
            broker._connected = False
            await broker._reconnect()

        # Drain any pending publish tasks queued by the broker.
        await event_bus.drain()

        assert len(published) == 1, (
            f"Expected exactly one SystemAlertEvent; got {len(published)}"
        )
        alert = published[0]
        assert alert.alert_type == "ibkr_disconnect"
        assert alert.severity == "critical"
        assert alert.source == "ibkr_broker.disconnect_handler"
        assert alert.metadata is not None
        assert alert.metadata["max_retries"] == (
            ibkr_config_for_emitter.reconnect_max_retries
        )
        assert (
            alert.metadata["client_id"]
            == ibkr_config_for_emitter.client_id
        )
        assert alert.metadata["detection_source"] == (
            "ibkr_broker.disconnect_handler"
        )

    @pytest.mark.asyncio
    async def test_ibkr_disconnect_emit_does_not_raise_on_publish_failure(
        self,
        mock_ib_for_emitter: MagicMock,
        ibkr_config_for_emitter: IBKRConfig,
        event_bus: EventBus,
    ) -> None:
        """Defensive: a publish failure must not propagate out of _reconnect."""
        mock_ib_for_emitter.connectAsync = AsyncMock(
            side_effect=ConnectionError("Connection refused")
        )

        async def boom(_evt: SystemAlertEvent) -> None:
            raise RuntimeError("simulated publish failure")

        event_bus.subscribe(SystemAlertEvent, boom)

        with (
            patch("argus.execution.ibkr_broker.IB", return_value=mock_ib_for_emitter),
            patch("argus.execution.ibkr_broker.asyncio.sleep", new_callable=AsyncMock),
        ):
            broker = IBKRBroker(ibkr_config_for_emitter, event_bus)
            broker._connected = False
            # Must not raise.
            await broker._reconnect()


class TestIBKRAuthFailureEmitter:
    """``ibkr_auth_failure`` SystemAlertEvent emitted on CRITICAL non-connection error."""

    @pytest.mark.asyncio
    async def test_ibkr_auth_permission_failure_emits_system_alert(
        self,
        mock_ib_for_emitter: MagicMock,
        ibkr_config_for_emitter: IBKRConfig,
        event_bus: EventBus,
    ) -> None:
        """Sprint 31.91 5b: a CRITICAL non-connection IBKR error
        (e.g., 203 ``security not available for this account``)
        publishes ``SystemAlertEvent(alert_type="ibkr_auth_failure", severity="critical")``.

        DEF-014 emitter resolution at the auth/permission branch of
        ``_on_error``.
        """
        published: list[SystemAlertEvent] = []

        async def capture(evt: SystemAlertEvent) -> None:
            published.append(evt)

        event_bus.subscribe(SystemAlertEvent, capture)

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib_for_emitter):
            broker = IBKRBroker(ibkr_config_for_emitter, event_bus)
            await broker.connect()
            # Trigger a CRITICAL non-connection error: 203 (account
            # permission). Use a contract mock so metadata.symbol is
            # populated.
            contract = MagicMock()
            contract.symbol = "TSLA"
            broker._on_error(
                req_id=42,
                error_code=203,
                error_string="The security is not available or allowed for this account",
                contract=contract,
            )
            # _on_error schedules publish via asyncio.ensure_future; let
            # it run to completion.
            await asyncio.sleep(0)
            await event_bus.drain()

        assert len(published) == 1, (
            f"Expected exactly one SystemAlertEvent; got {len(published)}"
        )
        alert = published[0]
        assert alert.alert_type == "ibkr_auth_failure"
        assert alert.severity == "critical"
        assert alert.source == "ibkr_broker.auth_handler"
        assert alert.metadata is not None
        assert alert.metadata["error_code"] == 203
        assert alert.metadata["symbol"] == "TSLA"
        assert (
            alert.metadata["client_id"]
            == ibkr_config_for_emitter.client_id
        )
        assert alert.metadata["detection_source"] == "ibkr_broker.auth_handler"

    @pytest.mark.asyncio
    async def test_ibkr_connection_critical_does_not_emit_auth_alert(
        self,
        mock_ib_for_emitter: MagicMock,
        ibkr_config_for_emitter: IBKRConfig,
        event_bus: EventBus,
    ) -> None:
        """A CRITICAL connection error (502/504/1100) does NOT emit
        ``ibkr_auth_failure`` — the existing reconnection path owns
        recovery for those.
        """
        published: list[SystemAlertEvent] = []

        async def capture(evt: SystemAlertEvent) -> None:
            published.append(evt)

        event_bus.subscribe(SystemAlertEvent, capture)

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib_for_emitter):
            broker = IBKRBroker(ibkr_config_for_emitter, event_bus)
            await broker.connect()
            broker._on_error(
                req_id=0,
                error_code=502,
                error_string="Couldn't connect to TWS",
                contract=None,
            )
            await asyncio.sleep(0)
            await event_bus.drain()

        assert published == [], (
            f"Connection error 502 must not emit ibkr_auth_failure; "
            f"got {published}"
        )


# ---------------------------------------------------------------------------
# 2. End-to-end pipeline tests
# ---------------------------------------------------------------------------


class TestE2EDatabentoDeadFeed:
    """Databento dead-feed alert through the full pipeline."""

    @pytest.mark.asyncio
    async def test_e2e_databento_dead_feed_emit_consume_rest_ws_ack(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        event_bus: EventBus,
        health_monitor: HealthMonitor,
        operations_db: str,
    ) -> None:
        """E2E: emit → consume → REST `/active` → WS push → ack → audit.

        WebSocket fan-out is asserted via HealthMonitor's
        ``subscribe_state_changes`` queue — the wire-level WS handler is
        a thin shim over this contract (independently tested in
        ``test_alerts_5a2.py::TestWebSocketFanOut`` + the E2E ack flow
        below).
        """
        # Subscribe a state-change consumer to act as a WS client.
        ws_queue = health_monitor.subscribe_state_changes()

        # Emit via the Event Bus (the real path).
        await event_bus.publish(
            SystemAlertEvent(
                source="databento_feed",
                alert_type="databento_dead_feed",
                message="Databento feed dead",
                severity="critical",
                metadata={"detection_source": "test"},
            )
        )
        await event_bus.drain()

        # WS push received.
        ws_msg = await asyncio.wait_for(ws_queue.get(), timeout=1.0)
        assert ws_msg["type"] == "alert_active"
        assert ws_msg["alert"]["alert_type"] == "databento_dead_feed"
        alert_id = ws_msg["alert"]["alert_id"]

        # REST `/active` returns it.
        resp = await client.get("/api/v1/alerts/active", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert any(a["alert_id"] == alert_id for a in body)

        # Acknowledge via REST.
        ack_resp = await client.post(
            f"/api/v1/alerts/{alert_id}/acknowledge",
            json={
                "reason": "operator confirmed databento offline",
                "operator_id": "operator",
            },
            headers=auth_headers,
        )
        assert ack_resp.status_code == 200
        ack_body = ack_resp.json()
        assert ack_body["state"] == "acknowledged"

        # WS push received for the ack.
        ws_ack_msg = await asyncio.wait_for(ws_queue.get(), timeout=1.0)
        assert ws_ack_msg["type"] == "alert_acknowledged"
        assert ws_ack_msg["alert"]["alert_id"] == alert_id

        # Audit-log row persisted.
        async with aiosqlite.connect(operations_db) as db:
            cursor = await db.execute(
                "SELECT audit_kind, operator_id "
                "FROM alert_acknowledgment_audit WHERE alert_id = ?",
                (alert_id,),
            )
            row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "ack"
        assert row[1] == "operator"


class TestE2EIBKRDisconnectAutoResolution:
    """IBKR disconnect alert auto-resolves on reconnect."""

    @pytest.mark.asyncio
    async def test_e2e_ibkr_disconnect_emit_consume_rest_ws_ack_auto_resolution(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        event_bus: EventBus,
        health_monitor: HealthMonitor,
        operations_db: str,
    ) -> None:
        """E2E: emit ibkr_disconnect → consume → REST → WS → auto-resolve
        on subsequent ``IBKRReconnectedEvent`` → audit row with
        ``audit_kind=auto_resolution``.
        """
        ws_queue = health_monitor.subscribe_state_changes()

        # Emit ibkr_disconnect via the Event Bus.
        await event_bus.publish(
            SystemAlertEvent(
                source="ibkr_broker.disconnect_handler",
                alert_type="ibkr_disconnect",
                message="reconnect retries exhausted",
                severity="critical",
                metadata={"client_id": 1},
            )
        )
        await event_bus.drain()
        ws_msg = await asyncio.wait_for(ws_queue.get(), timeout=1.0)
        assert ws_msg["type"] == "alert_active"
        alert_id = ws_msg["alert"]["alert_id"]

        # REST sees it.
        resp = await client.get("/api/v1/alerts/active", headers=auth_headers)
        assert any(a["alert_id"] == alert_id for a in resp.json())

        # Auto-resolution: publish IBKRReconnectedEvent.
        await event_bus.publish(IBKRReconnectedEvent(client_id=1))
        await event_bus.drain()

        # WS push received for auto-resolve.
        ws_resolve_msg = await asyncio.wait_for(ws_queue.get(), timeout=1.0)
        assert ws_resolve_msg["type"] == "alert_auto_resolved"
        assert ws_resolve_msg["alert"]["alert_id"] == alert_id
        assert ws_resolve_msg["alert"]["state"] == "archived"

        # REST `/active` no longer lists it.
        resp_after = await client.get("/api/v1/alerts/active", headers=auth_headers)
        assert all(a["alert_id"] != alert_id for a in resp_after.json())

        # Audit row written with audit_kind=auto_resolution.
        async with aiosqlite.connect(operations_db) as db:
            cursor = await db.execute(
                "SELECT audit_kind, operator_id "
                "FROM alert_acknowledgment_audit WHERE alert_id = ?",
                (alert_id,),
            )
            row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "auto_resolution"
        assert row[1] == "auto"


class TestE2EIBKRAuthFailureAutoResolution:
    """E2E test for ibkr_auth_failure auto-resolution via OrderFilledEvent.

    Closes the symmetry gap noted in S5b closeout — Test 4 covered
    the IBKRReconnectedEvent leg; this test covers the OrderFilledEvent
    leg of the same predicate. Surfaced as DEF-225 by Tier 3 #2.
    """

    @pytest.mark.asyncio
    async def test_ibkr_auth_failure_clears_on_order_filled(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        event_bus: EventBus,
        health_monitor: HealthMonitor,
        operations_db: str,
    ) -> None:
        """E2E: emit ibkr_auth_failure → consume → REST → WS →
        auto-resolve on subsequent ``OrderFilledEvent`` → audit row
        with ``audit_kind=auto_resolution``.

        OrderFilledEvent's existence implies a successful authenticated
        round-trip with the broker, so the predicate
        ``_ibkr_auth_success_predicate`` clears the alert. This test
        covers the OrderFilledEvent leg specifically — distinct from
        Test 4's IBKRReconnectedEvent leg.
        """
        ws_queue = health_monitor.subscribe_state_changes()

        # Emit ibkr_auth_failure via the Event Bus.
        await event_bus.publish(
            SystemAlertEvent(
                source="ibkr_broker.auth_handler",
                alert_type="ibkr_auth_failure",
                message="account permission error 203",
                severity="critical",
                metadata={
                    "error_code": 203,
                    "symbol": "TSLA",
                    "client_id": 1,
                    "detection_source": "ibkr_broker.auth_handler",
                },
            )
        )
        await event_bus.drain()
        ws_msg = await asyncio.wait_for(ws_queue.get(), timeout=1.0)
        assert ws_msg["type"] == "alert_active"
        assert ws_msg["alert"]["alert_type"] == "ibkr_auth_failure"
        alert_id = ws_msg["alert"]["alert_id"]

        # REST sees it.
        resp = await client.get("/api/v1/alerts/active", headers=auth_headers)
        assert any(a["alert_id"] == alert_id for a in resp.json())

        # Auto-resolution: publish OrderFilledEvent (the
        # OrderFilledEvent leg, NOT the IBKRReconnectedEvent leg
        # exercised by Test 4 — that distinction is the point of this
        # test).
        await event_bus.publish(
            OrderFilledEvent(
                order_id="test-order-1",
                fill_price=100.0,
                fill_quantity=10,
            )
        )
        await event_bus.drain()

        # WS push received for auto-resolve.
        ws_resolve_msg = await asyncio.wait_for(ws_queue.get(), timeout=1.0)
        assert ws_resolve_msg["type"] == "alert_auto_resolved"
        assert ws_resolve_msg["alert"]["alert_id"] == alert_id
        assert ws_resolve_msg["alert"]["state"] == "archived"

        # REST `/active` no longer lists it.
        resp_after = await client.get(
            "/api/v1/alerts/active", headers=auth_headers
        )
        assert all(a["alert_id"] != alert_id for a in resp_after.json())

        # Audit row written with audit_kind=auto_resolution.
        async with aiosqlite.connect(operations_db) as db:
            cursor = await db.execute(
                "SELECT audit_kind, operator_id "
                "FROM alert_acknowledgment_audit WHERE alert_id = ?",
                (alert_id,),
            )
            row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "auto_resolution"
        assert row[1] == "auto"


class TestE2EPhantomShortAutoResolution:
    """phantom_short auto-resolves after the 2c.2 threshold of zero-shares cycles."""

    @pytest.mark.asyncio
    async def test_e2e_phantom_short_emit_consume_rest_ws_ack_5_cycle_auto_resolution(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        event_bus: EventBus,
        health_monitor: HealthMonitor,
        operations_db: str,
    ) -> None:
        """E2E phantom_short: N consecutive zero-shares cycles auto-resolve.

        Pins the threshold = ``ReconciliationConfig.broker_orphan_consecutive_clear_threshold``
        — the SAME field that Session 2c.2's entry-gate clear reads.
        Hardcoding ``5`` here would make the threshold drift undetectable.
        """
        # Read the live threshold from the same config field that drives
        # Session 2c.2 — single source of truth.
        threshold = (
            health_monitor._reconciliation_config
            .broker_orphan_consecutive_clear_threshold
        )
        assert threshold >= 1, (
            "broker_orphan_consecutive_clear_threshold must be ≥ 1"
        )

        ws_queue = health_monitor.subscribe_state_changes()

        await event_bus.publish(
            SystemAlertEvent(
                source="reconciliation",
                alert_type="phantom_short",
                message="phantom short for AAPL",
                severity="critical",
                metadata={"symbol": "AAPL", "shares": -100},
            )
        )
        await event_bus.drain()
        ws_msg = await asyncio.wait_for(ws_queue.get(), timeout=1.0)
        alert_id = ws_msg["alert"]["alert_id"]

        # REST sees it.
        resp = await client.get("/api/v1/alerts/active", headers=auth_headers)
        assert any(a["alert_id"] == alert_id for a in resp.json())

        # Drive exactly ``threshold`` zero-shares cycles via the bus.
        for cycle in range(threshold):
            await event_bus.publish(
                ReconciliationCompletedEvent(
                    cycle_number=cycle + 1,
                    broker_shares_by_symbol={"AAPL": 0},
                )
            )
            await event_bus.drain()

        # WS push received for auto-resolve.
        ws_resolve_msg = await asyncio.wait_for(ws_queue.get(), timeout=1.0)
        assert ws_resolve_msg["type"] == "alert_auto_resolved"
        assert ws_resolve_msg["alert"]["alert_id"] == alert_id

        # REST `/history` includes it as archived.
        resp_hist = await client.get(
            "/api/v1/alerts/history", headers=auth_headers
        )
        archived = [
            a for a in resp_hist.json() if a["alert_id"] == alert_id
        ]
        assert len(archived) == 1
        assert archived[0]["state"] == "archived"

        # Audit row mirrors the auto-resolution.
        async with aiosqlite.connect(operations_db) as db:
            cursor = await db.execute(
                "SELECT audit_kind FROM alert_acknowledgment_audit "
                "WHERE alert_id = ?",
                (alert_id,),
            )
            row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "auto_resolution"


class TestE2EAcknowledgmentPersistsRestart:
    """Acknowledgment writes audit + survives a process restart."""

    @pytest.mark.asyncio
    async def test_e2e_acknowledgment_writes_audit_persists_restart(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        event_bus: EventBus,
        health_monitor: HealthMonitor,
        operations_db: str,
        alerts_config_short_retention: AlertsConfig,
    ) -> None:
        """Emit + ack; build a fresh HealthMonitor; rehydrate; assert
        the acknowledged state and the audit row both survive.
        """
        await event_bus.publish(
            SystemAlertEvent(
                source="reconciliation",
                alert_type="phantom_short",
                message="phantom short for AAPL",
                severity="critical",
                metadata={"symbol": "AAPL", "shares": -100},
            )
        )
        await event_bus.drain()
        active = health_monitor.get_active_alerts()
        assert len(active) == 1
        alert_id = active[0].alert_id

        # Acknowledge via REST.
        resp = await client.post(
            f"/api/v1/alerts/{alert_id}/acknowledge",
            json={
                "reason": "operator manually flattened position",
                "operator_id": "operator",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200

        # Simulate process restart: build a fresh HealthMonitor against
        # the same operations.db.
        fresh_bus = EventBus()
        fresh_hm = HealthMonitor(
            event_bus=fresh_bus,
            clock=FixedClock(datetime.now(UTC)),
            config=HealthConfig(),
            alerts_config=alerts_config_short_retention,
            reconciliation_config=ReconciliationConfig(),
            operations_db_path=operations_db,
        )
        await fresh_hm.rehydrate_alerts_from_db()

        # Acknowledged state survived rehydration.
        recovered = fresh_hm.get_alert_by_id(alert_id)
        assert recovered is not None
        assert recovered.state == AlertLifecycleState.ACKNOWLEDGED
        assert recovered.acknowledged_by == "operator"

        # Audit row queryable directly.
        async with aiosqlite.connect(operations_db) as db:
            cursor = await db.execute(
                "SELECT audit_kind, operator_id, reason "
                "FROM alert_acknowledgment_audit WHERE alert_id = ?",
                (alert_id,),
            )
            row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "ack"
        assert row[1] == "operator"
        assert row[2] == "operator manually flattened position"


class TestE2EPhantomShortRetryBlockedNeverAutoResolves:
    """``phantom_short_retry_blocked`` (Session 3) is policy-table NEVER."""

    @pytest.mark.asyncio
    async def test_e2e_phantom_short_retry_blocked_never_auto_resolves(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        event_bus: EventBus,
        health_monitor: HealthMonitor,
    ) -> None:
        """Emit phantom_short_retry_blocked → fire 100 ReconciliationCompletedEvents
        with zero shares → alert STAYS active → operator-ack via REST clears it.

        Pins the policy-table NEVER row introduced by Session 3 for the
        retry-blocked variant. The 100-cycle count is intentional: it
        exercises the predicate enough to prove "across many cycles, no
        resolution," and is unmistakably not a 1-iteration typo.
        """
        await event_bus.publish(
            SystemAlertEvent(
                source="order_manager",
                alert_type="phantom_short_retry_blocked",
                message="retry blocked for AAPL",
                severity="critical",
                metadata={"symbol": "AAPL"},
            )
        )
        await event_bus.drain()
        active = health_monitor.get_active_alerts()
        assert len(active) == 1
        alert_id = active[0].alert_id

        # Hammer the predicate. With NEVER_AUTO_RESOLVE the count must
        # be observably large; 100 iterations × the predicate evaluating
        # = 100 attempts that all return False.
        for cycle in range(100):
            await event_bus.publish(
                ReconciliationCompletedEvent(
                    cycle_number=cycle + 1,
                    broker_shares_by_symbol={"AAPL": 0},
                )
            )
            await event_bus.drain()

        still_active = health_monitor.get_alert_by_id(alert_id)
        assert still_active is not None
        assert still_active.state == AlertLifecycleState.ACTIVE, (
            "phantom_short_retry_blocked must NEVER auto-resolve."
        )

        # Operator ack via REST works as expected.
        resp = await client.post(
            f"/api/v1/alerts/{alert_id}/acknowledge",
            json={
                "reason": "operator manually unblocked retry path",
                "operator_id": "operator",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["state"] == "acknowledged"


# ---------------------------------------------------------------------------
# 3. Behavioral Alpaca anti-regression
# ---------------------------------------------------------------------------


class TestAlpacaBoundary:
    """Sprint 31.91 boundary: Alpaca emitter site stays unwired."""

    def test_alpaca_data_service_does_not_emit_system_alert_events(self) -> None:
        """Sprint 31.91 boundary: Alpaca emitter site stays unwired
        until Sprint 31.94 retires the broker by deletion (DEF-178/183).

        Behavioral check (replaces line-number-based textual check from
        earlier sprint drafts): inspects the actual module source for
        any reference to SystemAlertEvent in *executable* code. Robust
        to refactors; enforces the architectural constraint at semantic
        level.

        The pre-existing ``# TODO: Publish SystemAlertEvent ...`` comment
        in the source is intentionally NOT a violation — comments are
        semantically inert at runtime, and editing the comment to
        remove the literal substring would have required modifying
        ``alpaca_data_service.py``, which the Sprint 31.91 5b
        do-not-modify list explicitly forbids (the file is queued for
        deletion in Sprint 31.94).

        Implementation: tokenize the source and reject ``COMMENT`` and
        ``STRING`` tokens before searching, so a future ``import
        SystemAlertEvent`` or ``SystemAlertEvent(...)`` call is caught,
        but a TODO/docstring mention is not.
        """
        import io
        import tokenize

        import argus.data.alpaca_data_service as mod

        src = inspect.getsource(mod)
        tokens = tokenize.generate_tokens(io.StringIO(src).readline)
        executable_text_chunks: list[str] = []
        for tok in tokens:
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            executable_text_chunks.append(tok.string)
        executable_src = " ".join(executable_text_chunks)

        assert "SystemAlertEvent" not in executable_src, (
            "Alpaca data service should not emit SystemAlertEvent in "
            "executable code — queued for retirement in Sprint 31.94 "
            "(DEF-178/183). If the emitter was added intentionally, "
            "this test must be removed AS PART OF the retirement "
            "sprint, not separately."
        )


# ---------------------------------------------------------------------------
# 4. Sprint 31.91 Impromptu B (DEF-221) — real Databento producer chain
# ---------------------------------------------------------------------------


class TestE2EDatabentoDeadFeedAutoResolveWithRealProducer:
    """Drives the production Databento emitter chain end-to-end.

    Distinct from ``TestE2EDatabentoDeadFeed`` (above), which fabricates
    the ``SystemAlertEvent``: this test exercises the actual
    ``_run_with_reconnection`` exhaustion path AND the actual
    ``_heartbeat_publish_loop`` task, validating that DEF-217 (correct
    ``alert_type`` literal at the producer site) and DEF-221
    (DatabentoHeartbeatEvent producer wiring) together deliver a working
    auto-resolution pipeline.
    """

    @pytest.mark.asyncio
    async def test_databento_dead_feed_auto_resolves_via_real_heartbeats(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        event_bus: EventBus,
        health_monitor: HealthMonitor,
        operations_db: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Real producer → consume → REST → suppress while dead → 3 real
        heartbeats → auto-resolve.

        Pinned assertions (load-bearing):
        - The dead-feed alert reaches HealthMonitor with
          ``alert_type='databento_dead_feed'`` (validates DEF-217 fix in
          production code path — a regressed literal here would surface
          as ``alert_type='max_retries_exceeded'`` and the auto-resolution
          policy entry would silently never apply).
        - Zero ``DatabentoHeartbeatEvent`` instances are published while
          ``self._stale_published`` is True (validates suppression
          contract during reconnect / dead-feed state).
        - At least three ``DatabentoHeartbeatEvent`` instances are
          published once the feed recovers (sufficient to satisfy the
          predicate at
          ``alert_auto_resolution._databento_heartbeat_predicate``).
        - The alert ends up archived via ``audit_kind=auto_resolution``.
        """
        import sys

        from argus.core.config import DatabentoConfig, DataServiceConfig
        from argus.data.databento_data_service import DatabentoDataService
        from tests.mocks.mock_databento import (
            MockErrorMsg,
            MockHistoricalClient,
            MockLiveClient,
            MockOHLCVMsg,
            MockSymbolMappingMsg,
            MockTradeMsg,
        )

        class _MockDatabentoModule:
            Live = MockLiveClient
            Historical = MockHistoricalClient
            OHLCVMsg = MockOHLCVMsg
            TradeMsg = MockTradeMsg
            SymbolMappingMsg = MockSymbolMappingMsg
            ErrorMsg = MockErrorMsg

        monkeypatch.setitem(sys.modules, "databento", _MockDatabentoModule())
        monkeypatch.setenv("DATABENTO_API_KEY", "test-key")

        # Capture every DatabentoHeartbeatEvent on the bus so we can
        # count and time-correlate them against state transitions.
        heartbeats: list[DatabentoHeartbeatEvent] = []

        async def _capture_heartbeat(event: DatabentoHeartbeatEvent) -> None:
            heartbeats.append(event)

        event_bus.subscribe(DatabentoHeartbeatEvent, _capture_heartbeat)

        ws_queue = health_monitor.subscribe_state_changes()

        # Tiny intervals so the test completes in well under a second.
        databento_config = DatabentoConfig(
            api_key_env_var="DATABENTO_API_KEY",
            dataset="XNAS.ITCH",
            symbols=["AAPL"],
            reconnect_max_retries=1,
            reconnect_base_delay_seconds=0.01,
            reconnect_max_delay_seconds=0.05,
            stale_data_timeout_seconds=10.0,
            heartbeat_publish_interval_seconds=0.05,
        )
        data_config = DataServiceConfig()

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        # Skip the historical warm-up — irrelevant to this test.
        service._warm_up_indicators = AsyncMock()  # type: ignore[method-assign]

        # First call to _connect_live_session succeeds (so start() returns
        # cleanly and the heartbeat task spawns); subsequent calls inside
        # the reconnect loop fail until retries are exhausted.
        connect_calls: list[int] = []
        original_connect = service._connect_live_session

        async def _connect_succeeds_then_fails() -> None:
            connect_calls.append(1)
            if len(connect_calls) == 1:
                await original_connect()
            else:
                raise ConnectionError("mock reconnect failure")

        service._connect_live_session = _connect_succeeds_then_fails  # type: ignore[method-assign]

        # Engage the suppression invariant from t=0 so we can prove
        # heartbeats stay quiet across the entire reconnect window.
        service._stale_published = True

        await service.start(["AAPL"], ["1m"])
        try:
            # Drive the reconnect loop to exhaustion. retries=1 +
            # base_delay=0.01s + cap=0.05s → the production
            # SystemAlertEvent fires within ~50ms; budget generously
            # for asyncio scheduling under xdist load.
            await asyncio.sleep(0.3)
            await event_bus.drain()

            # WS push for the real-producer dead-feed alert.
            ws_msg = await asyncio.wait_for(ws_queue.get(), timeout=2.0)
            assert ws_msg["type"] == "alert_active"
            # Load-bearing: the literal must round-trip exactly. A
            # regressed DEF-217 fix would surface here as
            # ``max_retries_exceeded`` and the assertion would fire.
            assert (
                ws_msg["alert"]["alert_type"] == "databento_dead_feed"
            ), (
                "Production emitter must publish "
                "alert_type='databento_dead_feed' (validates DEF-217 in "
                "the real reconnect-exhaustion code path; a drift to "
                "'max_retries_exceeded' would silently break the "
                "auto-resolution policy lookup)."
            )
            alert_id = ws_msg["alert"]["alert_id"]

            # REST `/active` lists the alert.
            resp = await client.get(
                "/api/v1/alerts/active", headers=auth_headers
            )
            assert resp.status_code == 200
            assert any(a["alert_id"] == alert_id for a in resp.json())

            # Suppression contract: zero heartbeats published while the
            # feed is in dead state. Wait several intervals to confirm.
            heartbeats_before_recovery = len(heartbeats)
            await asyncio.sleep(0.25)  # ~5 intervals at 0.05s
            assert len(heartbeats) == heartbeats_before_recovery, (
                "Heartbeats must not publish while _stale_published is "
                "True (suppression contract for the reconnect / "
                "dead-feed state)."
            )

            # Mock recovery: clear the staleness flag and freshen the
            # last-message marker, mirroring what the stale_data_monitor
            # does on a DataResumed transition.
            service._stale_published = False
            service._last_message_time = time_module.monotonic()

            # Wait for the auto-resolution WS push. Each iteration is
            # ~one heartbeat interval; cap the total wait at ~2s.
            ws_resolve_msg: dict | None = None
            for _ in range(40):
                try:
                    msg = await asyncio.wait_for(
                        ws_queue.get(), timeout=0.1
                    )
                except asyncio.TimeoutError:
                    continue
                if (
                    msg.get("type") == "alert_auto_resolved"
                    and msg.get("alert", {}).get("alert_id") == alert_id
                ):
                    ws_resolve_msg = msg
                    break

            assert ws_resolve_msg is not None, (
                "Expected alert_auto_resolved WS push within the "
                "heartbeat-driven auto-resolution window."
            )
            assert ws_resolve_msg["alert"]["state"] == "archived"

            # The predicate requires three healthy heartbeats; verify
            # the producer actually delivered ≥3.
            assert len(heartbeats) >= 3, (
                f"Expected ≥3 DatabentoHeartbeatEvents during recovery, "
                f"got {len(heartbeats)}."
            )

            # REST `/active` no longer lists the alert.
            resp_after = await client.get(
                "/api/v1/alerts/active", headers=auth_headers
            )
            assert all(
                a["alert_id"] != alert_id for a in resp_after.json()
            )

            # Audit row confirms the auto_resolution path (vs operator
            # ack).
            async with aiosqlite.connect(operations_db) as db:
                cursor = await db.execute(
                    "SELECT audit_kind, operator_id "
                    "FROM alert_acknowledgment_audit WHERE alert_id = ?",
                    (alert_id,),
                )
                row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "auto_resolution"
            assert row[1] == "auto"
        finally:
            await service.stop()
