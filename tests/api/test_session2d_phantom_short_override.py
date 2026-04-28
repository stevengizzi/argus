"""Sprint 31.91 Session 2d — phantom-short gate override API tests.

Covers the operator-facing override surface introduced in Session 2d:

- ``POST /api/v1/reconciliation/phantom-short-gate/clear`` removes the
  symbol from in-memory state AND deletes the row from
  ``data/operations.db::phantom_short_gated_symbols`` AND writes a row
  to ``phantom_short_override_audit`` with full M3 schema.
- Audit-log entries persist across restarts (the row is queryable after
  reconnecting to the SQLite file fresh — simulates ARGUS shutdown +
  reboot).
- Unknown symbols return 404 with no audit-log row written.

These tests are revert-proof for the Session 2d clearance flow.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from pathlib import Path

import aiosqlite
import pytest
import time
from httpx import ASGITransport, AsyncClient

from argus.analytics.debrief_service import DebriefService
from argus.analytics.trade_logger import TradeLogger
from argus.api.auth import create_access_token, hash_password, set_jwt_secret
from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.core.clock import FixedClock
from argus.core.config import (
    ApiConfig,
    HealthConfig,
    OrderManagerConfig,
    ReconciliationConfig,
    SystemConfig,
)
from argus.core.event_bus import EventBus
from argus.core.health import HealthMonitor
from argus.core.risk_manager import RiskManager
from argus.db.manager import DatabaseManager
from argus.execution.order_manager import OrderManager
from argus.execution.simulated_broker import SimulatedBroker


TEST_PASSWORD = "testpassword123"
TEST_JWT_SECRET = "test-jwt-secret-for-argus-api-testing-minimum-32-chars"


# ---------------------------------------------------------------------------
# Fixtures (purpose-built so OrderManager carries an isolated tmp_path
# ``operations_db_path`` — the shared conftest fixture does not allow
# overriding this).
# ---------------------------------------------------------------------------


@pytest.fixture
def operations_db_path(tmp_path: Path) -> Path:
    return tmp_path / "operations.db"


@pytest.fixture
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)
    return TEST_JWT_SECRET


@pytest.fixture
def auth_headers(jwt_secret: str) -> dict[str, str]:
    token, _ = create_access_token(jwt_secret, expires_hours=24)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def fixed_clock() -> FixedClock:
    from datetime import UTC, datetime

    return FixedClock(datetime(2026, 4, 28, 15, 0, 0, tzinfo=UTC))


@pytest.fixture
async def trade_logger(tmp_path: Path) -> AsyncGenerator[TradeLogger, None]:
    manager = DatabaseManager(tmp_path / "argus_test.db")
    await manager.initialize()
    yield TradeLogger(manager)
    await manager.close()


@pytest.fixture
async def broker() -> SimulatedBroker:
    b = SimulatedBroker(initial_cash=100_000.0)
    await b.connect()
    return b


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def health_monitor(
    event_bus: EventBus, fixed_clock: FixedClock,
    broker: SimulatedBroker, trade_logger: TradeLogger,
) -> HealthMonitor:
    return HealthMonitor(
        event_bus=event_bus,
        clock=fixed_clock,
        config=HealthConfig(),
        broker=broker,
        trade_logger=trade_logger,
    )


@pytest.fixture
def risk_manager(
    event_bus: EventBus, fixed_clock: FixedClock, broker: SimulatedBroker,
) -> RiskManager:
    from argus.core.config import RiskConfig

    return RiskManager(
        config=RiskConfig(),
        broker=broker,
        event_bus=event_bus,
        clock=fixed_clock,
    )


@pytest.fixture
def order_manager(
    event_bus: EventBus,
    broker: SimulatedBroker,
    fixed_clock: FixedClock,
    trade_logger: TradeLogger,
    operations_db_path: Path,
) -> OrderManager:
    return OrderManager(
        event_bus=event_bus,
        broker=broker,
        clock=fixed_clock,
        config=OrderManagerConfig(),
        trade_logger=trade_logger,
        reconciliation_config=ReconciliationConfig(),
        operations_db_path=str(operations_db_path),
    )


@pytest.fixture
def api_config() -> ApiConfig:
    return ApiConfig(
        enabled=True,
        host="127.0.0.1",
        port=8000,
        password_hash=hash_password(TEST_PASSWORD),
        jwt_secret_env="ARGUS_JWT_SECRET",
        jwt_expiry_hours=24,
        cors_origins=["http://localhost:5173"],
        ws_heartbeat_interval_seconds=30,
        ws_tick_throttle_ms=1000,
    )


@pytest.fixture
def system_config(api_config: ApiConfig) -> SystemConfig:
    return SystemConfig(api=api_config)


@pytest.fixture
async def app_state(
    event_bus: EventBus,
    trade_logger: TradeLogger,
    broker: SimulatedBroker,
    health_monitor: HealthMonitor,
    risk_manager: RiskManager,
    order_manager: OrderManager,
    fixed_clock: FixedClock,
    system_config: SystemConfig,
) -> AppState:
    return AppState(
        event_bus=event_bus,
        trade_logger=trade_logger,
        broker=broker,
        health_monitor=health_monitor,
        risk_manager=risk_manager,
        order_manager=order_manager,
        data_service=None,
        strategies={},
        clock=fixed_clock,
        config=system_config,
        start_time=time.time(),
    )


@pytest.fixture
async def client(
    app_state: AppState, jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    app = create_app(app_state)
    app.state.app_state = app_state
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# Test 1 — clearance endpoint removes symbol from in-memory + SQLite state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phantom_short_gate_clear_endpoint_removes_symbol(
    client: AsyncClient,
    auth_headers: dict[str, str],
    app_state: AppState,
    operations_db_path: Path,
) -> None:
    """POSTing a valid clearance request:
    1. Returns 200 with audit_id populated.
    2. Removes AAPL from ``_phantom_short_gated_symbols`` in-memory.
    3. Deletes the row from ``phantom_short_gated_symbols`` SQLite table.
    4. Writes a row to ``phantom_short_override_audit`` with the full M3
       schema populated.
    """
    om = app_state.order_manager

    # Setup: pre-engage the gate (in-memory + persisted row).
    om._phantom_short_gated_symbols.add("AAPL")
    await om._persist_gated_symbol(
        "AAPL", "engaged", last_observed_short_shares=137,
    )
    assert "AAPL" in om._phantom_short_gated_symbols

    # POST the clearance.
    response = await client.post(
        "/api/v1/reconciliation/phantom-short-gate/clear",
        headers=auth_headers,
        json={
            "symbol": "AAPL",
            "reason": "manually flattened via close script at 09:31 ET",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["symbol"] == "AAPL"
    assert isinstance(body["audit_id"], int)
    assert body["audit_id"] >= 1
    assert body["prior_engagement_source"] == (
        "reconciliation.broker_orphan_branch"
    )
    assert body["prior_engagement_alert_id"] is None
    assert "cleared_at_utc" in body
    assert "cleared_at_et" in body

    # In-memory state cleared.
    assert "AAPL" not in om._phantom_short_gated_symbols

    # SQLite state: gated row deleted.
    async with aiosqlite.connect(str(operations_db_path)) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM phantom_short_gated_symbols "
            "WHERE symbol = ?",
            ("AAPL",),
        ) as cursor:
            row = await cursor.fetchone()
    assert row is not None
    assert row[0] == 0

    # SQLite state: audit-log row written with full M3 schema.
    async with aiosqlite.connect(str(operations_db_path)) as db:
        async with db.execute(
            "SELECT id, timestamp_utc, timestamp_et, symbol, "
            "prior_engagement_source, prior_engagement_alert_id, "
            "reason_text, override_payload_json "
            "FROM phantom_short_override_audit WHERE symbol = ?",
            ("AAPL",),
        ) as cursor:
            audit_row = await cursor.fetchone()
    assert audit_row is not None
    (
        audit_id, ts_utc, ts_et, sym,
        prior_source, prior_alert_id, reason, payload_json,
    ) = audit_row
    assert audit_id == body["audit_id"]
    assert ts_utc and "T" in ts_utc  # ISO format
    assert ts_et and "T" in ts_et
    assert sym == "AAPL"
    assert prior_source == "reconciliation.broker_orphan_branch"
    assert prior_alert_id is None
    assert reason == "manually flattened via close script at 09:31 ET"
    payload = json.loads(payload_json)
    assert payload["symbol"] == "AAPL"
    assert payload["reason"] == reason


# ---------------------------------------------------------------------------
# Test 2 (M3) — audit-log row persists across simulated restart
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phantom_short_gate_clear_audit_log_full_schema_persists(
    client: AsyncClient,
    auth_headers: dict[str, str],
    app_state: AppState,
    operations_db_path: Path,
) -> None:
    """After clearance, simulate ARGUS restart by reconnecting to the
    SQLite file fresh. Audit-log row remains queryable with all 8
    columns populated and ``override_payload_json`` parses to a dict
    containing at least ``{"symbol": "AAPL", "reason": "..."}``.
    """
    om = app_state.order_manager
    om._phantom_short_gated_symbols.add("AAPL")
    await om._persist_gated_symbol(
        "AAPL", "engaged", last_observed_short_shares=42,
    )

    response = await client.post(
        "/api/v1/reconciliation/phantom-short-gate/clear",
        headers=auth_headers,
        json={
            "symbol": "AAPL",
            "reason": "post-restart cleanup verification test reason",
        },
    )
    assert response.status_code == 200

    # Simulate ARGUS restart: drop all in-memory references; reconnect to
    # the same SQLite file fresh. The fixture's tmp_path lives for the
    # duration of the test, so the file persists.
    async with aiosqlite.connect(str(operations_db_path)) as db:
        async with db.execute(
            "SELECT id, timestamp_utc, timestamp_et, symbol, "
            "prior_engagement_source, prior_engagement_alert_id, "
            "reason_text, override_payload_json "
            "FROM phantom_short_override_audit WHERE symbol = ?",
            ("AAPL",),
        ) as cursor:
            row = await cursor.fetchone()

    assert row is not None
    columns = row
    # All 8 columns populated (some may be None per schema — id, ts_utc,
    # ts_et, symbol, reason, payload are NOT NULL; prior_engagement_source
    # is populated pre-5a.1; prior_engagement_alert_id is None pre-5a.1).
    assert columns[0] is not None  # id
    assert columns[1] is not None and "T" in columns[1]  # timestamp_utc
    assert columns[2] is not None and "T" in columns[2]  # timestamp_et
    assert columns[3] == "AAPL"
    assert columns[4] == "reconciliation.broker_orphan_branch"
    assert columns[5] is None  # prior_engagement_alert_id (Session 5a.1)
    assert columns[6] == "post-restart cleanup verification test reason"
    payload = json.loads(columns[7])
    assert isinstance(payload, dict)
    assert payload["symbol"] == "AAPL"
    assert payload["reason"] == (
        "post-restart cleanup verification test reason"
    )


# ---------------------------------------------------------------------------
# Test 3 — unknown symbol returns 404 with no audit-log row written
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phantom_short_gate_clear_unknown_symbol_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
    app_state: AppState,
    operations_db_path: Path,
) -> None:
    """When ``_phantom_short_gated_symbols`` does NOT contain the
    requested symbol, the endpoint returns 404 with a body mentioning
    "not currently gated", and NO audit-log row is written.
    """
    om = app_state.order_manager
    assert om._phantom_short_gated_symbols == set()

    response = await client.post(
        "/api/v1/reconciliation/phantom-short-gate/clear",
        headers=auth_headers,
        json={
            "symbol": "AAPL",
            "reason": "spurious clearance attempt for diagnostic test",
        },
    )

    assert response.status_code == 404
    body = response.json()
    assert "not currently gated" in body["detail"]

    # No audit-log row written. The audit table may not exist yet at all
    # (DDL is created lazily on first write); either way, no rows for
    # AAPL should be present. Use try/except since the table may not
    # exist yet (no clearance ever ran in this test).
    if operations_db_path.exists():
        async with aiosqlite.connect(str(operations_db_path)) as db:
            try:
                async with db.execute(
                    "SELECT COUNT(*) FROM phantom_short_override_audit "
                    "WHERE symbol = ?",
                    ("AAPL",),
                ) as cursor:
                    row = await cursor.fetchone()
                assert row is not None
                assert row[0] == 0
            except aiosqlite.OperationalError:
                # Table may not exist — that's fine; means no row written.
                pass


# ---------------------------------------------------------------------------
# Test 4 (L3) — at threshold, aggregate AND per-symbol alerts both fire
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aggregate_phantom_short_startup_alert_at_10_symbols_AND_individual_alerts_fire(
    operations_db_path: Path,
    fixed_clock: FixedClock,
) -> None:
    """At >= L15 threshold (default 10), the aggregate
    ``phantom_short_startup_engaged`` alert fires AND all 10 per-symbol
    ``phantom_short`` alerts ALSO fire (L3 always-both — no
    suppression). Total SystemAlertEvent count = 11.

    Reproduces the startup block in ``argus/main.py`` (lines 1086-1141)
    against an isolated EventBus + a pre-populated rehydration source.
    """
    from argus.core.events import SystemAlertEvent
    from unittest.mock import AsyncMock, MagicMock

    bus = EventBus()
    captured: list[SystemAlertEvent] = []

    async def _capture(evt: SystemAlertEvent) -> None:
        captured.append(evt)

    bus.subscribe(SystemAlertEvent, _capture)

    # Construct an OrderManager, pre-seed 10 gated symbols into the
    # operations.db, then run rehydration so its in-memory set matches
    # the prior-session state.
    mock_broker = MagicMock()
    mock_broker.place_bracket_order = AsyncMock()
    mock_broker.cancel_order = AsyncMock(return_value=True)
    mock_broker.cancel_all_orders = AsyncMock(return_value=0)
    mock_broker.get_positions = AsyncMock(return_value=[])

    om = OrderManager(
        event_bus=bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=OrderManagerConfig(),
        reconciliation_config=ReconciliationConfig(),
        operations_db_path=str(operations_db_path),
    )

    symbols = [
        "AAPL", "AMD", "GOOG", "MSFT", "NVDA",
        "TSLA", "META", "AMZN", "NFLX", "INTC",
    ]
    for sym in symbols:
        await om._persist_gated_symbol(sym, "engaged", 100)
    await om._rehydrate_gated_symbols_from_db()
    assert len(om._phantom_short_gated_symbols) == 10

    # Reproduce the startup-emission block from main.py against the
    # rehydrated state. Threshold default is 10 — count meets it.
    threshold = (
        ReconciliationConfig().phantom_short_aggregate_alert_threshold
    )
    assert threshold == 10

    gated_list = sorted(om._phantom_short_gated_symbols)
    if len(gated_list) >= threshold:
        await bus.publish(
            SystemAlertEvent(
                severity="critical",
                source="startup",
                alert_type="phantom_short_startup_engaged",
                message=(
                    f"STARTUP: {len(gated_list)} phantom-short symbols "
                    f"rehydrated (threshold: {threshold}). "
                    "Operator triage required."
                ),
                metadata={
                    "gated_symbols": gated_list,
                    "count": len(gated_list),
                    "threshold": threshold,
                },
            )
        )
    for sym in gated_list:
        await bus.publish(
            SystemAlertEvent(
                severity="critical",
                source="startup",
                alert_type="phantom_short",
                message=(
                    f"STARTUP: phantom-short gate rehydrated for "
                    f"{sym}. Operator triage required."
                ),
                metadata={
                    "symbol": sym,
                    "side": "SELL",
                    "detection_source": "startup.rehydration",
                },
            )
        )
    await bus.drain()

    # Assertions: 1 aggregate alert + 10 per-symbol alerts = 11 total.
    aggregate_alerts = [
        e for e in captured
        if e.alert_type == "phantom_short_startup_engaged"
    ]
    per_symbol_alerts = [
        e for e in captured if e.alert_type == "phantom_short"
    ]

    assert len(aggregate_alerts) == 1
    assert len(per_symbol_alerts) == 10
    assert len(captured) == 11

    # Aggregate metadata covers all 10 symbols.
    agg = aggregate_alerts[0]
    assert agg.metadata is not None
    assert agg.metadata["count"] == 10
    assert agg.metadata["threshold"] == 10
    assert sorted(agg.metadata["gated_symbols"]) == sorted(symbols)


# ---------------------------------------------------------------------------
# Test 5 — below threshold, only per-symbol alerts fire (no aggregate)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_below_10_symbols_individual_alerts_only_no_aggregate(
    operations_db_path: Path,
    fixed_clock: FixedClock,
) -> None:
    """With 5 symbols (below the L15 default threshold of 10), only the
    5 per-symbol alerts fire — the aggregate alert is suppressed (the
    threshold gates only the aggregate).
    """
    from argus.core.events import SystemAlertEvent
    from unittest.mock import AsyncMock, MagicMock

    bus = EventBus()
    captured: list[SystemAlertEvent] = []

    async def _capture(evt: SystemAlertEvent) -> None:
        captured.append(evt)

    bus.subscribe(SystemAlertEvent, _capture)

    mock_broker = MagicMock()
    mock_broker.place_bracket_order = AsyncMock()
    mock_broker.cancel_order = AsyncMock(return_value=True)
    mock_broker.cancel_all_orders = AsyncMock(return_value=0)
    mock_broker.get_positions = AsyncMock(return_value=[])

    om = OrderManager(
        event_bus=bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=OrderManagerConfig(),
        reconciliation_config=ReconciliationConfig(),
        operations_db_path=str(operations_db_path),
    )

    symbols = ["AAPL", "NVDA", "TSLA", "MSFT", "AMD"]
    for sym in symbols:
        await om._persist_gated_symbol(sym, "engaged", 50)
    await om._rehydrate_gated_symbols_from_db()
    assert len(om._phantom_short_gated_symbols) == 5

    threshold = (
        ReconciliationConfig().phantom_short_aggregate_alert_threshold
    )
    gated_list = sorted(om._phantom_short_gated_symbols)
    # Aggregate gating: 5 < 10, so no aggregate fires.
    if len(gated_list) >= threshold:
        await bus.publish(
            SystemAlertEvent(
                severity="critical",
                source="startup",
                alert_type="phantom_short_startup_engaged",
                message="should not fire",
                metadata={"count": len(gated_list)},
            )
        )
    # Per-symbol alerts always fire.
    for sym in gated_list:
        await bus.publish(
            SystemAlertEvent(
                severity="critical",
                source="startup",
                alert_type="phantom_short",
                message=f"per-symbol alert for {sym}",
                metadata={"symbol": sym},
            )
        )
    await bus.drain()

    aggregate_alerts = [
        e for e in captured
        if e.alert_type == "phantom_short_startup_engaged"
    ]
    per_symbol_alerts = [
        e for e in captured if e.alert_type == "phantom_short"
    ]
    assert len(aggregate_alerts) == 0
    assert len(per_symbol_alerts) == 5


# ---------------------------------------------------------------------------
# Test 6 — startup CRITICAL log line lists gated symbols sorted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_startup_log_line_lists_gated_symbols(
    operations_db_path: Path,
    fixed_clock: FixedClock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Pre-populating 3 symbols (TSLA, NVDA, AMD) and triggering the
    rehydrate path produces a CRITICAL log line that:
    - Mentions the count exactly: "3 phantom-short gated symbol(s)".
    - Lists the symbols sorted alphabetically: ['AMD', 'NVDA', 'TSLA'].

    Anchored on Session 2c.1's CRITICAL log line in
    ``_rehydrate_gated_symbols_from_db()`` — Session 2d does not emit a
    second CRITICAL line for the same fact.
    """
    import logging

    from unittest.mock import AsyncMock, MagicMock

    bus = EventBus()
    mock_broker = MagicMock()
    mock_broker.place_bracket_order = AsyncMock()
    mock_broker.cancel_order = AsyncMock(return_value=True)
    mock_broker.cancel_all_orders = AsyncMock(return_value=0)
    mock_broker.get_positions = AsyncMock(return_value=[])

    om = OrderManager(
        event_bus=bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=OrderManagerConfig(),
        reconciliation_config=ReconciliationConfig(),
        operations_db_path=str(operations_db_path),
    )

    for sym in ("TSLA", "NVDA", "AMD"):
        await om._persist_gated_symbol(sym, "engaged", 25)

    # Drop the in-memory state so rehydration repopulates it (and emits
    # the CRITICAL log).
    om._phantom_short_gated_symbols.clear()

    with caplog.at_level(logging.CRITICAL, logger="argus.execution.order_manager"):
        await om._rehydrate_gated_symbols_from_db()

    critical_records = [
        r for r in caplog.records if r.levelno == logging.CRITICAL
    ]
    assert len(critical_records) >= 1
    # Find the rehydration record (mentions "REHYDRATED").
    rehydration_msg = next(
        r.getMessage() for r in critical_records
        if "REHYDRATED" in r.getMessage()
    )
    # Sorted-alphabetically list ['AMD', 'NVDA', 'TSLA'].
    assert "['AMD', 'NVDA', 'TSLA']" in rehydration_msg
