"""Sprint 31.91 Session 5a.1 (DEF-014) — alert observability tests.

Covers:
- HealthMonitor consumption of SystemAlertEvent (subscription + state).
- REST GET /api/v1/alerts/active and /history.
- REST POST /api/v1/alerts/{id}/acknowledge — atomic + idempotent paths
  (200 / 200-duplicate / 200-late-ack / 404).

The atomic-transition acceptance criterion (MEDIUM #10) is exercised via
``test_post_alert_acknowledge_atomic_transition_writes_audit`` which
forces an aiosqlite COMMIT failure mid-transaction and asserts that
both the audit row AND the in-memory state revert.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import aiosqlite
import pytest
from httpx import AsyncClient

from argus.api.dependencies import AppState
from argus.core.event_bus import EventBus
from argus.core.events import SystemAlertEvent
from argus.core.health import (
    ActiveAlert,
    AlertLifecycleState,
    HealthMonitor,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _migrate_operations_db(db_path: Path) -> None:
    """Apply the operations.db migration framework to ``db_path``.

    Sprint 31.91 Impromptu A (DEF-224) deleted the redundant route-side
    ``_ensure_audit_table`` helper; route tests that bypass the
    HealthMonitor persistence path (via ``_seed_alert``) must pre-create
    the schema explicitly here. Production runs migrations at
    HealthMonitor startup, satisfying the same precondition.
    """
    from argus.data.migrations import apply_migrations
    from argus.data.migrations.operations import MIGRATIONS, SCHEMA_NAME

    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(db_path)) as db:
        await apply_migrations(
            db, schema_name=SCHEMA_NAME, migrations=MIGRATIONS
        )


def _seed_alert(
    health_monitor: HealthMonitor,
    *,
    alert_type: str = "phantom_short",
    severity: str = "critical",
    source: str = "reconciliation",
    message: str = "Test alert",
    metadata: dict | None = None,
    state: AlertLifecycleState = AlertLifecycleState.ACTIVE,
    created_at_utc: datetime | None = None,
) -> ActiveAlert:
    """Inject an alert directly into HealthMonitor state for a test.

    Bypasses Event Bus dispatch — useful for setting up state machine
    states (ACKNOWLEDGED, ARCHIVED) that 5a.1 itself never produces
    automatically.
    """
    import uuid

    alert = ActiveAlert(
        alert_id=str(uuid.uuid4()),
        alert_type=alert_type,
        severity=severity,
        source=source,
        message=message,
        metadata=metadata or {},
        state=state,
        created_at_utc=created_at_utc or datetime.now(UTC),
    )
    if state == AlertLifecycleState.ARCHIVED:
        alert.archived_at_utc = datetime.now(UTC)
    if state == AlertLifecycleState.ACKNOWLEDGED:
        alert.acknowledged_at_utc = datetime.now(UTC)
        alert.acknowledged_by = "operator"
        alert.acknowledgment_reason = "seeded ack reason text"
    health_monitor._alert_history.append(alert)
    if state in (
        AlertLifecycleState.ACTIVE,
        AlertLifecycleState.ACKNOWLEDGED,
    ):
        health_monitor._active_alerts[alert.alert_id] = alert
    return alert


# ---------------------------------------------------------------------------
# 1. HealthMonitor subscription + state-machine tests
# ---------------------------------------------------------------------------


class TestHealthMonitorSubscription:
    """HealthMonitor consumes SystemAlertEvent into in-memory state."""

    @pytest.mark.asyncio
    async def test_health_monitor_subscribes_to_system_alert_event(
        self, test_event_bus: EventBus, test_health_monitor: HealthMonitor
    ) -> None:
        """Test #1: subscription wiring works end-to-end via Event Bus."""
        test_event_bus.subscribe(
            SystemAlertEvent, test_health_monitor.on_system_alert_event
        )
        evt = SystemAlertEvent(
            source="test",
            alert_type="test_alert",
            message="hello",
            severity="critical",
            metadata={"k": "v"},
        )
        await test_event_bus.publish(evt)
        # Event Bus dispatches handlers as background tasks; drain to wait.
        await test_event_bus.drain()

        active = test_health_monitor.get_active_alerts()
        assert len(active) == 1
        assert active[0].alert_type == "test_alert"
        assert active[0].metadata == {"k": "v"}
        assert active[0].state == AlertLifecycleState.ACTIVE

    @pytest.mark.asyncio
    async def test_health_monitor_maintains_active_alert_state_in_memory(
        self, test_health_monitor: HealthMonitor
    ) -> None:
        """Test #2: _active_alerts and _alert_history both populated."""
        evt = SystemAlertEvent(
            source="reconciliation",
            alert_type="phantom_short",
            message="phantom short",
            severity="critical",
            metadata={"symbol": "AAPL", "shares": 100},
        )
        await test_health_monitor.on_system_alert_event(evt)

        assert len(test_health_monitor._active_alerts) == 1
        assert len(test_health_monitor._alert_history) == 1
        only = next(iter(test_health_monitor._active_alerts.values()))
        assert only is test_health_monitor._alert_history[0]
        assert only.metadata == {"symbol": "AAPL", "shares": 100}

    @pytest.mark.asyncio
    async def test_history_caps_at_max_size(
        self, test_health_monitor: HealthMonitor
    ) -> None:
        """History is bounded; oldest evicted when cap exceeded."""
        test_health_monitor._alert_history_max_size = 5
        for i in range(10):
            await test_health_monitor.on_system_alert_event(
                SystemAlertEvent(
                    source="t",
                    alert_type="t",
                    message=f"msg{i}",
                    severity="info",
                    metadata={"i": i},
                )
            )
        assert len(test_health_monitor._alert_history) == 5
        # Newest 5 retained.
        retained = [a.metadata["i"] for a in test_health_monitor._alert_history]
        assert retained == [5, 6, 7, 8, 9]


# ---------------------------------------------------------------------------
# 3, 4. GET routes
# ---------------------------------------------------------------------------


class TestGetActiveAlerts:
    """GET /api/v1/alerts/active."""

    @pytest.mark.asyncio
    async def test_get_alerts_active_returns_current_state(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_health_monitor: HealthMonitor,
    ) -> None:
        """Test #3: returns ACTIVE + ACKNOWLEDGED, excludes ARCHIVED."""
        _seed_alert(test_health_monitor, state=AlertLifecycleState.ACTIVE)
        _seed_alert(test_health_monitor, state=AlertLifecycleState.ACTIVE)
        _seed_alert(test_health_monitor, state=AlertLifecycleState.ACKNOWLEDGED)
        # ARCHIVED entries live only in history, not _active_alerts.
        _seed_alert(test_health_monitor, state=AlertLifecycleState.ARCHIVED)

        resp = await client.get("/api/v1/alerts/active", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 3
        states = {a["state"] for a in body}
        assert states == {"active", "acknowledged"}

    @pytest.mark.asyncio
    async def test_get_alerts_active_requires_auth(
        self, client: AsyncClient
    ) -> None:
        """Auth gate: no token → 401."""
        resp = await client.get("/api/v1/alerts/active")
        assert resp.status_code == 401


class TestGetAlertHistory:
    """GET /api/v1/alerts/history?since=..."""

    @pytest.mark.asyncio
    async def test_get_alerts_history_returns_within_window(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_health_monitor: HealthMonitor,
    ) -> None:
        """Test #4: ``since`` filter excludes pre-window alerts."""
        now = datetime.now(UTC)
        # Seed alerts at increasing timestamps so the dedup is unambiguous.
        for offset_min in (-50, -40, -30, -20, -10):
            _seed_alert(
                test_health_monitor,
                created_at_utc=now + timedelta(minutes=offset_min),
            )
        midpoint = (now + timedelta(minutes=-25)).isoformat()

        resp = await client.get(
            "/api/v1/alerts/history",
            params={"since": midpoint},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        # Three alerts strictly newer than the midpoint (-20, -10) +
        # tied at -30 NOT included since midpoint > -30. Actually
        # midpoint = -25, so -20 and -10 included. = 2 alerts.
        # Plus we want to verify the bound is correct.
        assert len(body) == 2

    @pytest.mark.asyncio
    async def test_get_alerts_history_returns_all_when_no_since(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_health_monitor: HealthMonitor,
    ) -> None:
        """No ``since`` parameter → entire history returned."""
        _seed_alert(test_health_monitor)
        _seed_alert(test_health_monitor, state=AlertLifecycleState.ARCHIVED)

        resp = await client.get("/api/v1/alerts/history", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2


# ---------------------------------------------------------------------------
# 5, 6, 7, 8. POST acknowledge — atomic + idempotent paths
# ---------------------------------------------------------------------------


class TestAcknowledgeAlert:
    """POST /api/v1/alerts/{alert_id}/acknowledge."""

    @pytest.mark.asyncio
    async def test_post_alert_acknowledge_atomic_transition_writes_audit(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_health_monitor: HealthMonitor,
        app_state: AppState,
        tmp_path: Path,
    ) -> None:
        """Test #5: success path writes audit row + applies in-memory ack."""
        # Override config data_dir to tmp_path so the audit DB lives there.
        assert app_state.config is not None
        app_state.config.data_dir = str(tmp_path)
        await _migrate_operations_db(tmp_path / "operations.db")

        alert = _seed_alert(test_health_monitor)
        resp = await client.post(
            f"/api/v1/alerts/{alert.alert_id}/acknowledge",
            json={
                "reason": "operator confirmed manually flattened",
                "operator_id": "operator",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["state"] == "acknowledged"
        assert body["acknowledged_by"] == "operator"
        assert body["audit_id"] >= 1

        # In-memory state mutated.
        assert alert.state == AlertLifecycleState.ACKNOWLEDGED
        assert alert.acknowledged_by == "operator"

        # Audit row persisted.
        db_path = tmp_path / "operations.db"
        async with aiosqlite.connect(str(db_path)) as db:
            cursor = await db.execute(
                "SELECT alert_id, audit_kind, operator_id "
                "FROM alert_acknowledgment_audit"
            )
            rows = await cursor.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == alert.alert_id
        assert rows[0][1] == "ack"

    @pytest.mark.asyncio
    async def test_post_alert_acknowledge_atomicity_rolls_back_on_commit_failure(
        self,
        test_health_monitor: HealthMonitor,
        tmp_path: Path,
    ) -> None:
        """Atomicity: COMMIT failure mid-transaction reverts both
        the audit row AND the in-memory state.

        Calls ``_atomic_acknowledge`` directly (the helper that
        backs the acknowledgment route) so the test can observe the
        rollback contract without going through FastAPI's exception
        handler.
        """
        from argus.api.routes.alerts import _atomic_acknowledge

        await _migrate_operations_db(tmp_path / "operations.db")
        alert = _seed_alert(test_health_monitor)
        db_path = str(tmp_path / "operations.db")

        async def failing_commit(self):  # type: ignore[no-untyped-def]
            raise RuntimeError("simulated commit failure")

        with patch.object(aiosqlite.Connection, "commit", failing_commit):
            with pytest.raises(RuntimeError, match="simulated commit failure"):
                await _atomic_acknowledge(
                    db_path,
                    health_monitor=test_health_monitor,
                    alert=alert,
                    operator_id="operator",
                    reason="operator confirmed manually flattened",
                    now_utc=datetime.now(UTC),
                )

        # In-memory state STILL ACTIVE (rollback worked).
        assert alert.state == AlertLifecycleState.ACTIVE
        assert alert.acknowledged_at_utc is None
        assert alert.acknowledged_by is None
        assert alert.acknowledgment_reason is None

        # No audit row persisted (transaction rolled back).
        if Path(db_path).exists():
            async with aiosqlite.connect(db_path) as db:
                # Table may exist (DDL is autocommit on some sqlite3
                # configurations) but no rows should be inserted.
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND "
                    "name='alert_acknowledgment_audit'"
                )
                if await cursor.fetchone() is not None:
                    cursor = await db.execute(
                        "SELECT COUNT(*) FROM alert_acknowledgment_audit"
                    )
                    row = await cursor.fetchone()
                    assert row is not None and row[0] == 0

    @pytest.mark.asyncio
    async def test_post_alert_acknowledge_idempotent_200_for_already_acknowledged(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_health_monitor: HealthMonitor,
        app_state: AppState,
        tmp_path: Path,
    ) -> None:
        """Test #6: already-acknowledged → 200 with original info preserved.

        Duplicate audit row written with audit_kind="duplicate_ack".
        """
        assert app_state.config is not None
        app_state.config.data_dir = str(tmp_path)
        await _migrate_operations_db(tmp_path / "operations.db")

        alert = _seed_alert(
            test_health_monitor,
            state=AlertLifecycleState.ACKNOWLEDGED,
        )
        original_acker = alert.acknowledged_by
        original_reason = alert.acknowledgment_reason

        resp = await client.post(
            f"/api/v1/alerts/{alert.alert_id}/acknowledge",
            json={
                "reason": "second operator hit ack again later",
                "operator_id": "different_operator",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        # Original acker info preserved in response.
        assert body["acknowledged_by"] == original_acker
        assert body["reason"] == original_reason
        assert body["state"] == "acknowledged"

        # Duplicate audit row written.
        db_path = tmp_path / "operations.db"
        async with aiosqlite.connect(str(db_path)) as db:
            cursor = await db.execute(
                "SELECT audit_kind, operator_id "
                "FROM alert_acknowledgment_audit "
                "WHERE alert_id = ?",
                (alert.alert_id,),
            )
            rows = await cursor.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "duplicate_ack"
        assert rows[0][1] == "different_operator"

    @pytest.mark.asyncio
    async def test_post_alert_acknowledge_404_for_unknown_id(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        app_state: AppState,
        tmp_path: Path,
    ) -> None:
        """Test #7: unknown alert ID → 404 + NO audit row."""
        assert app_state.config is not None
        app_state.config.data_dir = str(tmp_path)

        unknown_id = "00000000-0000-0000-0000-000000000000"
        resp = await client.post(
            f"/api/v1/alerts/{unknown_id}/acknowledge",
            json={
                "reason": "should never be written down",
                "operator_id": "operator",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

        # Audit DB MAY not exist at all (we never opened a connection).
        db_path = tmp_path / "operations.db"
        if db_path.exists():
            async with aiosqlite.connect(str(db_path)) as db:
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND "
                    "name='alert_acknowledgment_audit'"
                )
                row = await cursor.fetchone()
                if row is not None:
                    cursor = await db.execute(
                        "SELECT COUNT(*) FROM alert_acknowledgment_audit"
                    )
                    count_row = await cursor.fetchone()
                    assert count_row is not None and count_row[0] == 0

    @pytest.mark.asyncio
    async def test_post_alert_acknowledge_late_ack_for_archived_writes_audit(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_health_monitor: HealthMonitor,
        app_state: AppState,
        tmp_path: Path,
    ) -> None:
        """Test #8: alert already ARCHIVED → 200 with state="archived"
        + late_ack audit row.
        """
        assert app_state.config is not None
        app_state.config.data_dir = str(tmp_path)
        await _migrate_operations_db(tmp_path / "operations.db")

        alert = _seed_alert(
            test_health_monitor,
            state=AlertLifecycleState.ARCHIVED,
        )
        # ARCHIVED alerts are removed from _active_alerts by 5a.2's
        # auto-resolution; _seed_alert mimics that by NOT inserting
        # them into _active_alerts.
        assert alert.alert_id not in test_health_monitor._active_alerts

        resp = await client.post(
            f"/api/v1/alerts/{alert.alert_id}/acknowledge",
            json={
                "reason": "operator caught the alert just after auto-resolve",
                "operator_id": "operator",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["state"] == "archived"

        # Late-ack audit row written.
        db_path = tmp_path / "operations.db"
        async with aiosqlite.connect(str(db_path)) as db:
            cursor = await db.execute(
                "SELECT audit_kind FROM alert_acknowledgment_audit "
                "WHERE alert_id = ?",
                (alert.alert_id,),
            )
            rows = await cursor.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "late_ack"
