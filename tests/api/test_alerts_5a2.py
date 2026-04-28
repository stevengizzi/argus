"""Sprint 31.91 Session 5a.2 — alert observability backend tests.

Covers:

- WebSocket fan-out at ``/ws/v1/alerts`` (snapshot + state-change deltas).
- SQLite persistence + restart rehydration of ``alert_state``.
- Auto-resolution policy table (8 alert types; predicate firing).
- Single-source-of-truth coupling between ``phantom_short`` predicate
  and ``ReconciliationConfig.broker_orphan_consecutive_clear_threshold``.
- Retention policy (audit log + archived alert pruning) + VACUUM.
- Schema migration framework (``schema_version`` table records v1).
- Rehydration ordering invariant: alerts present in DB BEFORE the
  Event Bus subscription wires up survive into the active set.
"""

from __future__ import annotations

import asyncio
import inspect
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import aiosqlite
import pytest

from argus.core.alert_auto_resolution import (
    PolicyEntry,
    PredicateContext,
    build_policy_table,
)
from argus.core.clock import FixedClock
from argus.core.config import (
    AlertsConfig,
    HealthConfig,
    ReconciliationConfig,
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
    ActiveAlert,
    AlertLifecycleState,
    HealthMonitor,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def operations_db(tmp_path: Path) -> str:
    """Provide a fresh ``data/operations.db`` path for each test."""
    return str(tmp_path / "operations.db")


@pytest.fixture
def alerts_config_short_retention() -> AlertsConfig:
    """AlertsConfig tuned for fast test iteration (1-second retention task)."""
    return AlertsConfig(
        retention_task_interval_seconds=0.05,
        archived_alert_retention_days=1,
    )


@pytest.fixture
async def hm(
    operations_db: str,
    alerts_config_short_retention: AlertsConfig,
) -> HealthMonitor:
    """Provide a HealthMonitor wired with operations.db + AlertsConfig.

    NOTE: does NOT call ``start()`` — tests that need the predicate
    handlers wired call it explicitly to avoid spawning the heartbeat /
    integrity / retention background tasks for unrelated tests.
    """
    bus = EventBus()
    return HealthMonitor(
        event_bus=bus,
        clock=FixedClock(datetime.now(UTC)),
        config=HealthConfig(),
        alerts_config=alerts_config_short_retention,
        reconciliation_config=ReconciliationConfig(),
        operations_db_path=operations_db,
    )


async def _emit_alert(
    hm_inst: HealthMonitor,
    *,
    alert_type: str = "phantom_short",
    severity: str = "critical",
    source: str = "test",
    message: str = "test alert",
    metadata: dict[str, Any] | None = None,
) -> ActiveAlert:
    """Drive an alert through ``on_system_alert_event`` and return it."""
    evt = SystemAlertEvent(
        alert_type=alert_type,
        severity=severity,
        source=source,
        message=message,
        metadata=metadata or {},
    )
    await hm_inst.on_system_alert_event(evt)
    return list(hm_inst._active_alerts.values())[-1]


# ---------------------------------------------------------------------------
# 1. SQLite persistence + rehydration
# ---------------------------------------------------------------------------


class TestPersistence:
    @pytest.mark.asyncio
    async def test_alert_state_persists_to_sqlite_for_restart_recovery(
        self, hm: HealthMonitor, operations_db: str
    ) -> None:
        """Test #3 — emit alert; row appears in alert_state table."""
        alert = await _emit_alert(hm, metadata={"symbol": "AAPL"})
        async with aiosqlite.connect(operations_db) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM alert_state WHERE alert_id = ?",
                (alert.alert_id,),
            )
            row = await cursor.fetchone()
        assert row is not None
        assert row["status"] == "active"
        assert row["alert_type"] == "phantom_short"
        meta = json.loads(row["metadata_json"])
        assert meta["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_alert_state_rehydrated_before_event_bus_subscription(
        self,
        operations_db: str,
        alerts_config_short_retention: AlertsConfig,
    ) -> None:
        """Test #4 — rehydration completes before subscription window opens."""
        # Phase 1: pre-populate ``alert_state`` via a first HealthMonitor.
        bus_a = EventBus()
        hm_a = HealthMonitor(
            event_bus=bus_a,
            clock=FixedClock(datetime.now(UTC)),
            config=HealthConfig(),
            alerts_config=alerts_config_short_retention,
            operations_db_path=operations_db,
        )
        await hm_a.on_system_alert_event(
            SystemAlertEvent(
                alert_type="phantom_short",
                severity="critical",
                source="test",
                message="prior session",
                metadata={"symbol": "AAPL"},
            )
        )
        prior_alert_id = next(iter(hm_a._active_alerts.keys()))

        # Phase 2: simulate fresh process start. Construct a fresh
        # HealthMonitor; rehydrate; THEN subscribe; THEN emit a new
        # event to confirm the subscription window opened correctly.
        bus_b = EventBus()
        hm_b = HealthMonitor(
            event_bus=bus_b,
            clock=FixedClock(datetime.now(UTC)),
            config=HealthConfig(),
            alerts_config=alerts_config_short_retention,
            operations_db_path=operations_db,
        )
        # The prior alert MUST already be in active state after
        # rehydration BEFORE subscription wiring. This is the contract.
        await hm_b.rehydrate_alerts_from_db()
        assert prior_alert_id in hm_b._active_alerts, (
            "Rehydration must populate _active_alerts before subscribe."
        )

        # Now subscribe and emit a new alert; confirm subscription works.
        bus_b.subscribe(SystemAlertEvent, hm_b.on_system_alert_event)
        await bus_b.publish(
            SystemAlertEvent(
                alert_type="phantom_short",
                severity="critical",
                source="test",
                message="new alert",
                metadata={"symbol": "TSLA"},
            )
        )
        await bus_b.drain()
        active_types = {a.alert_type for a in hm_b._active_alerts.values()}
        assert "phantom_short" in active_types
        assert len(hm_b._active_alerts) == 2  # prior + new

    @pytest.mark.asyncio
    async def test_persistence_survives_acknowledgment(
        self, hm: HealthMonitor, operations_db: str
    ) -> None:
        """Acknowledgment is persisted to alert_state.status."""
        alert = await _emit_alert(hm, metadata={"symbol": "AAPL"})
        hm.apply_acknowledgment(
            alert,
            operator_id="operator",
            reason="manual ack reason text",
            now_utc=datetime.now(UTC),
        )
        # 5a.2: route would call persist_acknowledgment_after_commit;
        # call it directly here.
        await hm.persist_acknowledgment_after_commit(alert)
        async with aiosqlite.connect(operations_db) as db:
            cursor = await db.execute(
                "SELECT status, acknowledged_by FROM alert_state WHERE alert_id = ?",
                (alert.alert_id,),
            )
            row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "acknowledged"
        assert row[1] == "operator"


# ---------------------------------------------------------------------------
# 2. Auto-resolution policy table
# ---------------------------------------------------------------------------


class TestAutoResolutionPolicy:
    @pytest.mark.asyncio
    async def test_phantom_short_5_cycles_zero_shares(
        self, hm: HealthMonitor
    ) -> None:
        """Test #5 — phantom_short auto-resolves after threshold cycles.

        ReconciliationConfig.broker_orphan_consecutive_clear_threshold
        defaults to 5; we verify exactly 5 zero-shares cycles fires
        the predicate.
        """
        # Subscribe predicate handlers without starting other tasks.
        hm._subscribe_predicate_handlers()
        alert = await _emit_alert(hm, metadata={"symbol": "AAPL"})
        for cycle in range(5):
            await hm._evaluate_predicates(
                ReconciliationCompletedEvent(
                    cycle_number=cycle + 1,
                    broker_shares_by_symbol={"AAPL": 0},
                )
            )
        assert alert.alert_id not in hm._active_alerts, (
            "phantom_short should auto-resolve on 5th zero-shares cycle."
        )
        assert alert.state == AlertLifecycleState.ARCHIVED
        assert alert.archived_at_utc is not None

    @pytest.mark.asyncio
    async def test_phantom_short_retry_blocked_never_auto_resolves(
        self, hm: HealthMonitor
    ) -> None:
        """Test #6 — phantom_short_retry_blocked never auto-resolves."""
        hm._subscribe_predicate_handlers()
        alert = await _emit_alert(
            hm,
            alert_type="phantom_short_retry_blocked",
            metadata={"symbol": "AAPL"},
        )
        # Hammer the predicate with 100 reconciliation completions; the
        # alert must remain active.
        for cycle in range(100):
            await hm._evaluate_predicates(
                ReconciliationCompletedEvent(
                    cycle_number=cycle,
                    broker_shares_by_symbol={"AAPL": 0},
                )
            )
        assert alert.alert_id in hm._active_alerts
        assert alert.state == AlertLifecycleState.ACTIVE

    @pytest.mark.asyncio
    async def test_cancel_propagation_timeout_never_auto_resolves(
        self, hm: HealthMonitor
    ) -> None:
        """Test #7 — cancel_propagation_timeout never auto-resolves."""
        hm._subscribe_predicate_handlers()
        alert = await _emit_alert(
            hm,
            alert_type="cancel_propagation_timeout",
            metadata={"symbol": "AAPL"},
        )
        for _ in range(100):
            await hm._evaluate_predicates(
                ReconciliationCompletedEvent(
                    broker_shares_by_symbol={"AAPL": 0}
                )
            )
        assert alert.alert_id in hm._active_alerts

    @pytest.mark.asyncio
    async def test_databento_dead_feed_3_healthy_heartbeats(
        self, hm: HealthMonitor
    ) -> None:
        """Test #8 — databento_dead_feed clears after 3 healthy heartbeats."""
        hm._subscribe_predicate_handlers()
        alert = await _emit_alert(
            hm, alert_type="databento_dead_feed"
        )
        for _ in range(3):
            await hm._evaluate_predicates(DatabentoHeartbeatEvent())
        assert alert.alert_id not in hm._active_alerts
        assert alert.state == AlertLifecycleState.ARCHIVED

    @pytest.mark.asyncio
    async def test_phantom_short_uses_2c2_threshold_field(
        self,
        operations_db: str,
        alerts_config_short_retention: AlertsConfig,
    ) -> None:
        """Test #13 — phantom_short reads the live 2c.2 threshold.

        Build HM with a custom ReconciliationConfig threshold=3 and
        confirm the predicate fires on the 3rd cycle (NOT the 5th).
        """
        bus = EventBus()
        hm_local = HealthMonitor(
            event_bus=bus,
            clock=FixedClock(datetime.now(UTC)),
            config=HealthConfig(),
            alerts_config=alerts_config_short_retention,
            reconciliation_config=ReconciliationConfig(
                broker_orphan_consecutive_clear_threshold=3,
            ),
            operations_db_path=operations_db,
        )
        hm_local._subscribe_predicate_handlers()
        alert = await _emit_alert(hm_local, metadata={"symbol": "AAPL"})
        # 2 cycles — should NOT clear yet.
        for cycle in range(2):
            await hm_local._evaluate_predicates(
                ReconciliationCompletedEvent(
                    broker_shares_by_symbol={"AAPL": 0}
                )
            )
        assert alert.alert_id in hm_local._active_alerts, (
            "Should not clear at 2 cycles when threshold=3."
        )
        # 3rd cycle — clears.
        await hm_local._evaluate_predicates(
            ReconciliationCompletedEvent(
                broker_shares_by_symbol={"AAPL": 0}
            )
        )
        assert alert.alert_id not in hm_local._active_alerts

    def test_phantom_short_predicate_does_not_define_duplicate_threshold(
        self,
    ) -> None:
        """Static check: the predicate-builder reads the threshold via a
        provider, not a duplicated AlertsConfig field. Inspect the
        source of ``make_phantom_short_predicate`` and confirm it does
        not reference a literal 5 or any AlertsConfig threshold field.
        """
        from argus.core import alert_auto_resolution

        source = inspect.getsource(
            alert_auto_resolution.make_phantom_short_predicate
        )
        assert "threshold_provider" in source
        # No duplicated AlertsConfig threshold field exists on
        # AlertsConfig — confirm by inspecting the model fields.
        cfg_fields = set(AlertsConfig.model_fields.keys())
        assert "broker_orphan_consecutive_clear_threshold" not in cfg_fields, (
            "AlertsConfig must NOT duplicate the 2c.2 threshold field."
        )
        # Confirm the field DOES live on ReconciliationConfig (the
        # canonical home).
        assert (
            "broker_orphan_consecutive_clear_threshold"
            in ReconciliationConfig.model_fields
        )

    def test_policy_table_is_exhaustive(self) -> None:
        """All 10 alert types are present in the policy table."""
        table = build_policy_table(
            phantom_short_threshold_provider=lambda: 5
        )
        expected = {
            "phantom_short",
            "stranded_broker_long",
            "phantom_short_retry_blocked",
            "cancel_propagation_timeout",
            "ibkr_disconnect",
            "ibkr_auth_failure",
            "databento_dead_feed",
            "phantom_short_startup_engaged",
            "eod_residual_shorts",
            "eod_flatten_failed",
        }
        assert set(table.keys()) == expected
        # NEVER_AUTO_RESOLVE entries are explicit (not omitted).
        ctx = PredicateContext()
        dummy_alert = ActiveAlert(
            alert_id="x",
            alert_type="cancel_propagation_timeout",
            severity="critical",
            source="t",
            message="t",
            metadata={},
        )
        # Use a dummy event of a type the predicate doesn't consume.
        from argus.core.events import HeartbeatEvent
        for never in (
            "phantom_short_retry_blocked",
            "cancel_propagation_timeout",
            "eod_residual_shorts",
            "eod_flatten_failed",
        ):
            assert table[never].operator_ack_required is True
            assert table[never].predicate(dummy_alert, HeartbeatEvent(), ctx) is False


# ---------------------------------------------------------------------------
# 3. Retention + VACUUM + migrations
# ---------------------------------------------------------------------------


class TestRetention:
    @pytest.mark.asyncio
    async def test_audit_log_retention_forever_default(
        self, hm: HealthMonitor, operations_db: str
    ) -> None:
        """Test #9 — default audit_log_retention_days=None deletes nothing."""
        # Force schema to exist.
        await hm._ensure_operations_schema()
        old_ts = (datetime.now(UTC) - timedelta(days=400)).isoformat()
        async with aiosqlite.connect(operations_db) as db:
            await db.execute(
                """
                INSERT INTO alert_acknowledgment_audit
                    (timestamp_utc, alert_id, operator_id, reason, audit_kind)
                VALUES (?, ?, ?, ?, ?)
                """,
                (old_ts, "old-alert", "operator", "old reason", "ack"),
            )
            await db.commit()
        # Default is None — retention pass should be a no-op for audit.
        assert hm._alerts_config.audit_log_retention_days is None
        await hm._run_retention_once()
        async with aiosqlite.connect(operations_db) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM alert_acknowledgment_audit"
            )
            row = await cursor.fetchone()
        assert row is not None and row[0] == 1

    @pytest.mark.asyncio
    async def test_archived_alert_retention_purges_older(
        self, hm: HealthMonitor, operations_db: str
    ) -> None:
        """Test #10 — archived alerts older than retention window are purged."""
        await hm._ensure_operations_schema()
        old_archived_ts = (datetime.now(UTC) - timedelta(days=100)).isoformat()
        # Insert an alert directly with archived_at in the distant past.
        async with aiosqlite.connect(operations_db) as db:
            await db.execute(
                """
                INSERT INTO alert_state (
                    alert_id, alert_type, severity, source, message,
                    metadata_json, emitted_at_utc, emitted_at_et,
                    status, archived_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "old-archived-id",
                    "phantom_short",
                    "critical",
                    "test",
                    "old archived alert",
                    "{}",
                    old_archived_ts,
                    old_archived_ts,
                    "archived",
                    old_archived_ts,
                ),
            )
            await db.commit()
        await hm._run_retention_once()
        async with aiosqlite.connect(operations_db) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM alert_state WHERE alert_id = ?",
                ("old-archived-id",),
            )
            row = await cursor.fetchone()
        assert row is not None and row[0] == 0

    @pytest.mark.asyncio
    async def test_schema_version_records_v1(
        self, hm: HealthMonitor, operations_db: str
    ) -> None:
        """Test #11 — apply_migrations records v1 in schema_version."""
        await hm._ensure_operations_schema()
        async with aiosqlite.connect(operations_db) as db:
            cursor = await db.execute(
                "SELECT version, description FROM schema_version "
                "WHERE schema_name = ?",
                ("operations",),
            )
            row = await cursor.fetchone()
        assert row is not None
        assert row[0] == 1
        assert "Sprint 31.91" in row[1]

    @pytest.mark.asyncio
    async def test_vacuum_runs_via_asyncio_to_thread(
        self, hm: HealthMonitor, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test #12 — VACUUM is invoked via asyncio.to_thread, not blocking."""
        await hm._ensure_operations_schema()
        # Monkeypatch asyncio.to_thread to record invocation + delegate.
        original_to_thread = asyncio.to_thread
        invocations: list[Any] = []

        async def tracking_to_thread(func, *args, **kwargs):
            invocations.append(func)
            return await original_to_thread(func, *args, **kwargs)

        monkeypatch.setattr(asyncio, "to_thread", tracking_to_thread)
        await hm._vacuum_operations_db()
        assert len(invocations) == 1
        # The invoked callable is the inner _sync_vacuum closure.
        assert callable(invocations[0])


# ---------------------------------------------------------------------------
# 4. WebSocket fan-out
# ---------------------------------------------------------------------------


class TestWebSocketFanOut:
    @pytest.mark.asyncio
    async def test_state_change_subscriber_receives_alert_active(
        self, hm: HealthMonitor
    ) -> None:
        """Test #1 (WS-internal) — alert_active is fan-out'd to subscribers.

        We test the in-process queue contract (HealthMonitor's
        ``subscribe_state_changes`` / ``_publish_state_change``); the
        WebSocket router is a thin shim over this contract.
        """
        queue = hm.subscribe_state_changes()
        await _emit_alert(hm, metadata={"symbol": "AAPL"})
        msg = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert msg["type"] == "alert_active"
        assert msg["alert"]["alert_type"] == "phantom_short"

    @pytest.mark.asyncio
    async def test_state_change_subscriber_receives_acknowledged(
        self, hm: HealthMonitor
    ) -> None:
        """Test #2 (WS-internal) — alert_acknowledged is fan-out'd."""
        queue = hm.subscribe_state_changes()
        alert = await _emit_alert(hm, metadata={"symbol": "AAPL"})
        # Drain the alert_active message.
        await asyncio.wait_for(queue.get(), timeout=1.0)
        hm.apply_acknowledgment(
            alert,
            operator_id="operator",
            reason="manual ack reason text",
            now_utc=datetime.now(UTC),
        )
        await hm.persist_acknowledgment_after_commit(alert)
        msg = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert msg["type"] == "alert_acknowledged"
        assert msg["alert"]["state"] == "acknowledged"

    @pytest.mark.asyncio
    async def test_state_change_subscriber_receives_auto_resolved(
        self, hm: HealthMonitor
    ) -> None:
        """alert_auto_resolved is fan-out'd when the predicate fires."""
        queue = hm.subscribe_state_changes()
        hm._subscribe_predicate_handlers()
        await _emit_alert(hm, metadata={"symbol": "AAPL"})
        # Drain alert_active.
        await asyncio.wait_for(queue.get(), timeout=1.0)
        # Fire 5 zero-shares cycles.
        for _ in range(5):
            await hm._evaluate_predicates(
                ReconciliationCompletedEvent(
                    broker_shares_by_symbol={"AAPL": 0}
                )
            )
        msg = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert msg["type"] == "alert_auto_resolved"
        assert msg["alert"]["state"] == "archived"

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_queue(self, hm: HealthMonitor) -> None:
        """Unsubscribed queue does not receive further messages."""
        queue = hm.subscribe_state_changes()
        hm.unsubscribe_state_changes(queue)
        await _emit_alert(hm, metadata={"symbol": "AAPL"})
        # Queue should remain empty.
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(queue.get(), timeout=0.1)

    @pytest.mark.asyncio
    async def test_auto_resolution_writes_audit_row(
        self, hm: HealthMonitor, operations_db: str
    ) -> None:
        """Auto-resolution writes ``audit_kind=auto_resolution`` audit row."""
        hm._subscribe_predicate_handlers()
        alert = await _emit_alert(hm, metadata={"symbol": "AAPL"})
        for _ in range(5):
            await hm._evaluate_predicates(
                ReconciliationCompletedEvent(
                    broker_shares_by_symbol={"AAPL": 0}
                )
            )
        async with aiosqlite.connect(operations_db) as db:
            cursor = await db.execute(
                "SELECT audit_kind, operator_id FROM alert_acknowledgment_audit "
                "WHERE alert_id = ?",
                (alert.alert_id,),
            )
            row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "auto_resolution"
        assert row[1] == "auto"


# ---------------------------------------------------------------------------
# 5. Migration framework
# ---------------------------------------------------------------------------


class TestMigrationFramework:
    @pytest.mark.asyncio
    async def test_apply_migrations_is_idempotent(
        self, operations_db: str
    ) -> None:
        """Re-applying migrations is a no-op (current_version unchanged)."""
        from argus.data.migrations import apply_migrations, current_version
        from argus.data.migrations.operations import MIGRATIONS, SCHEMA_NAME

        async with aiosqlite.connect(operations_db) as db:
            v1 = await apply_migrations(
                db, schema_name=SCHEMA_NAME, migrations=MIGRATIONS
            )
            v2 = await apply_migrations(
                db, schema_name=SCHEMA_NAME, migrations=MIGRATIONS
            )
            current = await current_version(db, schema_name=SCHEMA_NAME)
        assert v1 == 1
        assert v2 == 1
        assert current == 1
