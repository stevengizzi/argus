"""Health monitoring for Argus.

Provides component health tracking, heartbeat pings, alert dispatch, and
scheduled integrity checks.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

import aiohttp
import aiosqlite

from argus.core.alert_auto_resolution import (
    PolicyEntry,
    PredicateContext,
    all_consumed_event_types,
    build_policy_table,
)
from argus.core.config import AlertsConfig, HealthConfig, ReconciliationConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    CircuitBreakerEvent,
    Event,
    HeartbeatEvent,
    SystemAlertEvent,
    SystemStatus,
)
from argus.models.trading import OrderSide

if TYPE_CHECKING:
    from argus.analytics.trade_logger import TradeLogger
    from argus.core.clock import Clock
    from argus.execution.broker import Broker
    from argus.execution.order_manager import OrderManager
    from argus.strategies.base_strategy import BaseStrategy
    from argus.strategies.telemetry_store import EvaluationEventStore

logger = logging.getLogger(__name__)


_ET_TZ = ZoneInfo("America/New_York")


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class ComponentStatus(StrEnum):
    """Health status of a system component."""

    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"  # Working but with issues (e.g., reconnecting)
    UNHEALTHY = "unhealthy"  # Not functioning
    STOPPED = "stopped"


@dataclass
class ComponentHealth:
    """Health snapshot for a single component."""

    name: str
    status: ComponentStatus
    last_updated: datetime
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Alert Lifecycle (Sprint 31.91 D9a, DEF-014)
# ---------------------------------------------------------------------------


class AlertLifecycleState(StrEnum):
    """Lifecycle state of an alert tracked by HealthMonitor.

    Sprint 31.91 D9a (DEF-014). Session 5a.1 supports
    ``ACTIVE → ACKNOWLEDGED`` and ``ACTIVE → ARCHIVED`` (auto-resolved or
    manually closed). Session 5a.2 will add transitions driven by
    auto-resolution policy.
    """

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    ARCHIVED = "archived"


@dataclass
class ActiveAlert:
    """Alert lifecycle record tracked in HealthMonitor.

    Sprint 31.91 D9a (DEF-014). In-memory only in Session 5a.1; SQLite-
    backed pruning + retention land in Session 5a.2.
    """

    alert_id: str
    alert_type: str
    severity: str
    source: str
    message: str
    metadata: dict[str, Any]
    state: AlertLifecycleState = AlertLifecycleState.ACTIVE
    created_at_utc: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    acknowledged_at_utc: datetime | None = None
    acknowledged_by: str | None = None
    archived_at_utc: datetime | None = None
    acknowledgment_reason: str | None = None


def _alert_to_payload(alert: ActiveAlert) -> dict[str, Any]:
    """Project an ``ActiveAlert`` to its JSON-serializable wire form.

    Sprint 31.91 5a.2 — used by both the WebSocket fan-out and the
    rehydration-from-DB path. Mirrors the REST ``AlertResponse`` shape
    so a WS client and a REST client see identical fields per alert.
    """
    return {
        "alert_id": alert.alert_id,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "source": alert.source,
        "message": alert.message,
        "metadata": dict(alert.metadata) if alert.metadata else {},
        "state": alert.state.value,
        "created_at_utc": alert.created_at_utc.isoformat(),
        "acknowledged_at_utc": (
            alert.acknowledged_at_utc.isoformat()
            if alert.acknowledged_at_utc
            else None
        ),
        "acknowledged_by": alert.acknowledged_by,
        "archived_at_utc": (
            alert.archived_at_utc.isoformat()
            if alert.archived_at_utc
            else None
        ),
        "acknowledgment_reason": alert.acknowledgment_reason,
    }


# ---------------------------------------------------------------------------
# HealthMonitor
# ---------------------------------------------------------------------------


class HealthMonitor:
    """System health monitoring, heartbeat, and alerting.

    Tracks component health status in-memory. Sends periodic heartbeat
    pings to an external monitoring service (e.g., Healthchecks.io).
    Dispatches critical alerts via webhook.
    """

    def __init__(
        self,
        event_bus: EventBus,
        clock: Clock,
        config: HealthConfig,
        broker: Broker | None = None,
        trade_logger: TradeLogger | None = None,
        *,
        alerts_config: AlertsConfig | None = None,
        reconciliation_config: ReconciliationConfig | None = None,
        operations_db_path: str | None = None,
    ) -> None:
        """Initialize the HealthMonitor.

        Args:
            event_bus: Event bus for publishing health events.
            clock: Clock protocol for time operations.
            config: Health monitoring configuration.
            broker: Optional broker for integrity checks.
            trade_logger: Optional trade logger for reconciliation.
            alerts_config: Optional Sprint 31.91 5a.2 alerts config —
                controls auto-resolution + retention. Falls back to
                ``AlertsConfig()`` defaults.
            reconciliation_config: Optional Sprint 31.91 5a.2 — phantom
                short auto-resolution reads
                ``broker_orphan_consecutive_clear_threshold`` from this
                config (single source of truth with Session 2c.2).
            operations_db_path: Path to ``data/operations.db`` for
                Sprint 31.91 5a.2 alert-state persistence. ``None`` =
                persistence disabled (in-memory-only mode for tests).
        """
        self._event_bus = event_bus
        self._clock = clock
        self._config = config
        self._broker = broker
        self._trade_logger = trade_logger
        self._alerts_config: AlertsConfig = alerts_config or AlertsConfig()
        self._reconciliation_config: ReconciliationConfig = (
            reconciliation_config or ReconciliationConfig()
        )
        self._operations_db_path: str | None = operations_db_path
        # Sprint 31.91 S2b.2 (Pattern A.4 — Option C cross-reference, MEDIUM #8):
        # Optional OrderManager handle so the daily integrity-check alert can
        # cite an active ``stranded_broker_long`` alert (2b.1) for the same
        # symbol. Wired via ``set_order_manager()``; unset → no cross-reference.
        # TODO (Session 5a.1+): replace with HealthMonitor's queryable
        # active-alert state once the consumer surface lands; main.py is on
        # this session's do-not-modify list, so production wiring is deferred.
        self._order_manager: OrderManager | None = None

        # Sprint 31.915 (DEF-233): EvaluationEventStore handle for the
        # /health endpoint's ``evaluation_db`` subfield. Wired via
        # ``register_evaluation_store()`` from main.py / api/server.py.
        # ``None`` → /health renders the subfield with all-null defaults.
        self._evaluation_store: EvaluationEventStore | None = None

        # Component health registry
        self._components: dict[str, ComponentHealth] = {}

        # Tasks
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._integrity_task: asyncio.Task[None] | None = None
        self._running: bool = False

        # Tracking
        self._last_daily_check: datetime | None = None
        self._last_weekly_check: datetime | None = None

        # Sprint 31.91 D9a (DEF-014): SystemAlertEvent consumer state.
        # ``_active_alerts`` indexes alerts currently in ACTIVE or
        # ACKNOWLEDGED state; ``_alert_history`` is an append-only window
        # of all alerts (ACTIVE + ACKNOWLEDGED + ARCHIVED). Session 5a.2
        # backs both with SQLite via ``rehydrate_alerts_from_db()`` (load)
        # and ``_persist_alert()`` (write-on-every-mutation).
        self._active_alerts: dict[str, ActiveAlert] = {}
        self._alert_history: list[ActiveAlert] = []
        self._alert_history_max_size: int = 1000

        # Sprint 31.91 5a.2: per-alert auto-resolution context (cycle
        # counters, engaged-symbol sets). Indexed by ``alert_id``;
        # populated lazily on first event delivery.
        self._predicate_contexts: dict[str, PredicateContext] = {}

        # Sprint 31.91 5a.2: policy table + state-change subscriber list.
        # Built lazily so tests can construct HealthMonitor without
        # importing the policy module ahead of time.
        self._policy_table: dict[str, PolicyEntry] = build_policy_table(
            phantom_short_threshold_provider=(
                lambda: self._reconciliation_config
                .broker_orphan_consecutive_clear_threshold
            ),
        )
        self._state_change_subscribers: list[
            asyncio.Queue[dict[str, Any]]
        ] = []
        self._predicate_handlers_subscribed: bool = False
        self._retention_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start health monitoring.

        1. Subscribe to CircuitBreakerEvent for alert dispatch.
        2. Sprint 31.91 5a.2: subscribe to every event type referenced by
           the auto-resolution policy table.
        3. Start heartbeat loop.
        4. Start integrity check loop.
        5. Sprint 31.91 5a.2: start the retention background task.
        """
        self._event_bus.subscribe(CircuitBreakerEvent, self._on_circuit_breaker)
        self._subscribe_predicate_handlers()
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._integrity_task = asyncio.create_task(self._integrity_loop())
        self._retention_task = asyncio.create_task(self._retention_loop())
        logger.info("HealthMonitor started")

    async def stop(self) -> None:
        """Stop health monitoring. Cancel all tasks."""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task
        if self._integrity_task:
            self._integrity_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._integrity_task
        if self._retention_task:
            self._retention_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._retention_task
            self._retention_task = None
        logger.info("HealthMonitor stopped")

    # --- Component Registry ---

    def update_component(
        self,
        name: str,
        status: ComponentStatus,
        message: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Update a component's health status.

        Called by each component when its status changes.
        If status transitions to UNHEALTHY, send an alert.

        Args:
            name: Component name (e.g., "broker", "data_service").
            status: New health status.
            message: Optional message describing the status.
            details: Optional additional details.
        """
        previous = self._components.get(name)
        health = ComponentHealth(
            name=name,
            status=status,
            last_updated=self._clock.now(),
            message=message,
            details=details or {},
        )
        self._components[name] = health

        # Alert on transition to UNHEALTHY
        if status == ComponentStatus.UNHEALTHY and (
            previous is None or previous.status != ComponentStatus.UNHEALTHY
        ):
            asyncio.create_task(
                self._send_alert(
                    title=f"Component UNHEALTHY: {name}",
                    body=message,
                    severity="critical",
                )
            )

        logger.info("Component %s → %s: %s", name, status.value, message)

    def get_status(self) -> dict[str, ComponentHealth]:
        """Return all component health statuses.

        Returns:
            Dict mapping component name to ComponentHealth.
        """
        return dict(self._components)

    def get_overall_status(self) -> ComponentStatus:
        """Return overall system status.

        UNHEALTHY if any component is UNHEALTHY.
        DEGRADED if any component is DEGRADED.
        HEALTHY if all components are HEALTHY.
        STARTING if any component is STARTING and none are UNHEALTHY.

        Returns:
            The overall system status.
        """
        if not self._components:
            return ComponentStatus.STARTING

        statuses = [c.status for c in self._components.values()]
        if ComponentStatus.UNHEALTHY in statuses:
            return ComponentStatus.UNHEALTHY
        if ComponentStatus.DEGRADED in statuses:
            return ComponentStatus.DEGRADED
        if ComponentStatus.STARTING in statuses:
            return ComponentStatus.STARTING
        return ComponentStatus.HEALTHY

    # --- Heartbeat ---

    async def _heartbeat_loop(self) -> None:
        """Send heartbeat ping every config.heartbeat_interval_seconds.

        Publishes HeartbeatEvent to Event Bus and sends HTTP POST
        to config.heartbeat_url (if configured).
        """
        while self._running:
            try:
                overall = self.get_overall_status()

                # Map ComponentStatus to SystemStatus for event
                system_status = self._map_to_system_status(overall)

                # Publish HeartbeatEvent to Event Bus
                await self._event_bus.publish(
                    HeartbeatEvent(
                        system_status=system_status,
                    )
                )

                # Send to external monitoring
                if self._config.heartbeat_url:
                    await self._send_heartbeat(overall)

            except Exception as e:
                logger.error("Heartbeat failed: %s", e)

            await asyncio.sleep(self._config.heartbeat_interval_seconds)

    def _map_to_system_status(self, status: ComponentStatus) -> SystemStatus:
        """Map ComponentStatus to SystemStatus enum.

        Args:
            status: The component status to map.

        Returns:
            Corresponding SystemStatus.
        """
        mapping = {
            ComponentStatus.STARTING: SystemStatus.DEGRADED,
            ComponentStatus.HEALTHY: SystemStatus.HEALTHY,
            ComponentStatus.DEGRADED: SystemStatus.DEGRADED,
            ComponentStatus.UNHEALTHY: SystemStatus.DOWN,
            ComponentStatus.STOPPED: SystemStatus.DOWN,
        }
        return mapping.get(status, SystemStatus.DEGRADED)

    async def _send_heartbeat(self, status: ComponentStatus) -> None:
        """HTTP POST to heartbeat URL.

        For Healthchecks.io: a simple GET/POST to the ping URL.
        Include system status in the body for context.

        Args:
            status: Current overall system status.
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "status": status.value,
                    "timestamp": self._clock.now().isoformat(),
                    "components": {
                        name: health.status.value for name, health in self._components.items()
                    },
                }
                async with session.post(
                    self._config.heartbeat_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status >= 400:
                        logger.warning("Heartbeat POST returned %d", resp.status)
        except Exception as e:
            logger.warning("Heartbeat POST failed: %s", e)

    # --- Alert Dispatch ---

    async def _send_alert(self, title: str, body: str, severity: str = "critical") -> None:
        """Send alert via webhook.

        If alert_webhook_url is configured, POST a JSON payload.
        This works with Discord webhooks, Healthchecks.io, Slack, etc.

        Discord webhook format:
            {"content": "🚨 **title**\\nbody"}

        Generic format:
            {"title": ..., "body": ..., "severity": ..., "timestamp": ...}

        Args:
            title: Alert title.
            body: Alert body/message.
            severity: Alert severity ("critical" or "warning").
        """
        if not self._config.alert_webhook_url:
            logger.warning("Alert triggered but no webhook URL configured: %s", title)
            return

        try:
            async with aiohttp.ClientSession() as session:
                # Detect Discord webhook format
                if "discord.com/api/webhooks" in self._config.alert_webhook_url:
                    emoji = "🚨" if severity == "critical" else "⚠️"
                    payload = {"content": f"{emoji} **{title}**\n{body}"}
                else:
                    payload = {
                        "title": title,
                        "body": body,
                        "severity": severity,
                        "timestamp": self._clock.now().isoformat(),
                    }

                async with session.post(
                    self._config.alert_webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status >= 400:
                        logger.error("Alert POST returned %d", resp.status)
        except Exception as e:
            logger.error("Alert POST failed: %s", e)

        logger.critical("ALERT [%s]: %s — %s", severity, title, body)

    async def _on_circuit_breaker(self, event: CircuitBreakerEvent) -> None:
        """Circuit breaker fired — send critical alert.

        Args:
            event: The circuit breaker event.
        """
        await self._send_alert(
            title="Circuit Breaker Triggered",
            body=f"Level: {event.level.value}, Reason: {event.reason}",
            severity="critical",
        )

    # --- SystemAlertEvent consumer (Sprint 31.91 D9a, DEF-014) ---

    async def on_system_alert_event(self, event: SystemAlertEvent) -> None:
        """Subscribe-handler for ``SystemAlertEvent`` (Sprint 31.91 D9a).

        Captures every alert into the in-memory active-alert state machine
        and the bounded history window. Session 5a.2 layered on:

        - SQLite persistence (``_persist_alert``) so alerts survive restart.
        - WebSocket fan-out via ``_publish_state_change`` so connected
          ``/ws/v1/alerts`` clients see the new alert in real time.
        - Predicate-context bookkeeping so the auto-resolution policy
          table can fire for this alert's ``alert_type``.

        Args:
            event: The system alert event consumed from the Event Bus.
        """
        alert_id = str(uuid.uuid4())
        alert = ActiveAlert(
            alert_id=alert_id,
            alert_type=event.alert_type,
            severity=event.severity,
            source=event.source,
            message=event.message,
            metadata=dict(event.metadata) if event.metadata else {},
        )
        self._active_alerts[alert_id] = alert
        self._alert_history.append(alert)
        if len(self._alert_history) > self._alert_history_max_size:
            # Cap in-memory history; SQLite retention task is the durable
            # bound (see _retention_loop).
            self._alert_history = self._alert_history[
                -self._alert_history_max_size:
            ]
        # Predicate context — created here so it exists before any
        # subsequent event delivery.
        self._predicate_contexts[alert_id] = PredicateContext(
            engaged_at_utc=alert.created_at_utc,
        )
        await self._persist_alert(alert)
        await self._publish_state_change(
            kind="alert_active",
            alert=alert,
        )
        logger.info(
            "HealthMonitor consumed alert %s (type=%s severity=%s source=%s).",
            alert_id,
            event.alert_type,
            event.severity,
            event.source,
        )

    # --- Active-alert query surface (used by REST endpoints) ---

    def get_active_alerts(self) -> list[ActiveAlert]:
        """Return alerts currently in ACTIVE or ACKNOWLEDGED state.

        Sprint 31.91 D9a — used by ``GET /api/v1/alerts/active``.
        """
        return [
            a
            for a in self._active_alerts.values()
            if a.state
            in (
                AlertLifecycleState.ACTIVE,
                AlertLifecycleState.ACKNOWLEDGED,
            )
        ]

    def get_alert_history(
        self, since: datetime | None = None
    ) -> list[ActiveAlert]:
        """Return historical alerts within an optional ``since`` window.

        Sprint 31.91 D9a — used by ``GET /api/v1/alerts/history``.
        """
        if since is None:
            return list(self._alert_history)
        return [a for a in self._alert_history if a.created_at_utc >= since]

    def get_alert_by_id(self, alert_id: str) -> ActiveAlert | None:
        """Return an alert by id from active-alert state, or None.

        Sprint 31.91 D9a — used by acknowledgment route to determine
        404-vs-409-vs-200.
        """
        return self._active_alerts.get(alert_id)

    def get_archived_alert_by_id(
        self, alert_id: str
    ) -> ActiveAlert | None:
        """Return an alert by id from archived history, or None.

        Sprint 31.91 D9a — late-ack 409 lookup.
        """
        for a in self._alert_history:
            if (
                a.alert_id == alert_id
                and a.state == AlertLifecycleState.ARCHIVED
            ):
                return a
        return None

    def apply_acknowledgment(
        self,
        alert: ActiveAlert,
        operator_id: str,
        reason: str,
        now_utc: datetime,
    ) -> None:
        """Apply an acknowledgment transition in-place (in-memory).

        Sprint 31.91 D9a — invoked from inside the SQLite transaction in
        the acknowledgment route. If the audit-log INSERT fails the route
        rolls back the transaction; this method's mutation is reverted by
        the caller via the "first take a snapshot" pattern (the route
        captures the alert's pre-mutation state).

        Sprint 31.91 5a.2 — pure in-memory mutation. SQLite persistence
        and WebSocket fan-out are the route handler's responsibility,
        invoked AFTER the atomic-transaction COMMIT succeeds via
        ``persist_acknowledgment_after_commit``. This avoids racing the
        persist task against the route's own rollback path.
        """
        alert.state = AlertLifecycleState.ACKNOWLEDGED
        alert.acknowledged_at_utc = now_utc
        alert.acknowledged_by = operator_id
        alert.acknowledgment_reason = reason

    async def persist_acknowledgment_after_commit(
        self,
        alert: ActiveAlert,
    ) -> None:
        """Post-commit: persist alert_state + fan out to WS subscribers.

        Sprint 31.91 5a.2 — invoked by the acknowledgment route once
        the audit-log transaction has committed. Splitting this from
        ``apply_acknowledgment`` keeps the in-memory mutation
        synchronous (so the route can hold an open aiosqlite txn) and
        avoids races with the route's rollback path.
        """
        await self._persist_alert(alert)
        await self._publish_state_change(
            kind="alert_acknowledged",
            alert=alert,
        )

    # --- Sprint 31.91 5a.2: SQLite persistence + rehydration ---

    async def _persist_alert(self, alert: ActiveAlert) -> None:
        """Write or update one alert row in ``alert_state`` (5a.2).

        Best-effort: persistence failures are logged but do not raise,
        so a transient SQLite error cannot disrupt alert flow. The
        ``alert_state`` table grows by one row per emitted alert; the
        retention background task bounds it.
        """
        if self._operations_db_path is None:
            return
        try:
            await self._ensure_operations_schema()
            now_utc = datetime.now(UTC)
            now_et = now_utc.astimezone(_ET_TZ)
            async with aiosqlite.connect(self._operations_db_path) as db:
                await db.execute(
                    """
                    INSERT INTO alert_state (
                        alert_id, alert_type, severity, source, message,
                        metadata_json, emitted_at_utc, emitted_at_et,
                        status, acknowledged_by, acknowledged_at_utc,
                        acknowledgment_reason, auto_resolved_at_utc,
                        archived_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(alert_id) DO UPDATE SET
                        status=excluded.status,
                        acknowledged_by=excluded.acknowledged_by,
                        acknowledged_at_utc=excluded.acknowledged_at_utc,
                        acknowledgment_reason=excluded.acknowledgment_reason,
                        auto_resolved_at_utc=excluded.auto_resolved_at_utc,
                        archived_at_utc=excluded.archived_at_utc,
                        message=excluded.message,
                        metadata_json=excluded.metadata_json
                    """,
                    (
                        alert.alert_id,
                        alert.alert_type,
                        alert.severity,
                        alert.source,
                        alert.message,
                        json.dumps(alert.metadata or {}, default=str),
                        alert.created_at_utc.isoformat(),
                        now_et.isoformat(),
                        alert.state.value,
                        alert.acknowledged_by,
                        (
                            alert.acknowledged_at_utc.isoformat()
                            if alert.acknowledged_at_utc
                            else None
                        ),
                        alert.acknowledgment_reason,
                        alert.metadata.get("auto_resolved_at_utc")
                        if alert.metadata
                        else None,
                        (
                            alert.archived_at_utc.isoformat()
                            if alert.archived_at_utc
                            else None
                        ),
                    ),
                )
                await db.commit()
        except Exception as exc:
            logger.warning("alert_state persistence failed for %s: %s", alert.alert_id, exc)

    async def _ensure_operations_schema(self) -> None:
        """Apply pending migrations to ``data/operations.db`` (5a.2)."""
        if self._operations_db_path is None:
            return
        # Lazy import — keeps the migration framework optional for
        # in-memory tests that pass operations_db_path=None.
        from argus.data.migrations import apply_migrations
        from argus.data.migrations.operations import MIGRATIONS, SCHEMA_NAME

        # Ensure parent dir exists.
        Path(self._operations_db_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._operations_db_path) as db:
            await apply_migrations(db, schema_name=SCHEMA_NAME, migrations=MIGRATIONS)

    async def rehydrate_alerts_from_db(self) -> None:
        """Repopulate in-memory alert state from ``alert_state`` (5a.2).

        MUST be invoked from ``main.py`` BEFORE the
        ``event_bus.subscribe(SystemAlertEvent, ...)`` call. Without that
        ordering, alerts emitted between rehydration and subscription
        slip through the gap. ``main.py`` documents the line ordering
        explicitly per sprint invariant 15's scoped exception.
        """
        if self._operations_db_path is None:
            return
        try:
            await self._ensure_operations_schema()
            async with aiosqlite.connect(self._operations_db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM alert_state ORDER BY emitted_at_utc ASC"
                )
                rows = await cursor.fetchall()
        except Exception as exc:
            logger.error("alert_state rehydration failed: %s", exc)
            return
        for row in rows:
            alert = self._row_to_alert(row)
            if alert is None:
                continue
            self._alert_history.append(alert)
            if alert.state in (
                AlertLifecycleState.ACTIVE,
                AlertLifecycleState.ACKNOWLEDGED,
            ):
                self._active_alerts[alert.alert_id] = alert
                # Predicate context — allow auto-resolution to keep
                # working post-restart.
                self._predicate_contexts[alert.alert_id] = PredicateContext(
                    engaged_at_utc=alert.created_at_utc,
                )
        logger.info(
            "Rehydrated alert state from %s: %d active, %d total in history.",
            self._operations_db_path,
            len(self._active_alerts),
            len(self._alert_history),
        )

    @staticmethod
    def _row_to_alert(row: aiosqlite.Row) -> ActiveAlert | None:
        """Project an ``alert_state`` row back to an ``ActiveAlert``."""
        try:
            metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        except json.JSONDecodeError:
            metadata = {}
        try:
            state = AlertLifecycleState(row["status"])
        except ValueError:
            return None
        created_at = datetime.fromisoformat(row["emitted_at_utc"])
        ack_at = (
            datetime.fromisoformat(row["acknowledged_at_utc"])
            if row["acknowledged_at_utc"]
            else None
        )
        archived_at = (
            datetime.fromisoformat(row["archived_at_utc"])
            if row["archived_at_utc"]
            else None
        )
        return ActiveAlert(
            alert_id=row["alert_id"],
            alert_type=row["alert_type"],
            severity=row["severity"],
            source=row["source"],
            message=row["message"],
            metadata=metadata,
            state=state,
            created_at_utc=created_at,
            acknowledged_at_utc=ack_at,
            acknowledged_by=row["acknowledged_by"],
            archived_at_utc=archived_at,
            acknowledgment_reason=row["acknowledgment_reason"],
        )

    # --- Sprint 31.91 5a.2: WebSocket fan-out ---

    def subscribe_state_changes(self) -> asyncio.Queue[dict[str, Any]]:
        """Register a WS client for state-change deltas (5a.2).

        Returns a queue the caller awaits. ``unsubscribe_state_changes``
        removes the queue when the client disconnects.
        """
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._state_change_subscribers.append(queue)
        return queue

    def unsubscribe_state_changes(
        self, queue: asyncio.Queue[dict[str, Any]]
    ) -> None:
        """Remove a previously-subscribed queue (5a.2)."""
        try:
            self._state_change_subscribers.remove(queue)
        except ValueError:
            pass

    async def _publish_state_change(
        self,
        *,
        kind: str,
        alert: ActiveAlert,
    ) -> None:
        """Broadcast a state-change message to every subscribed queue."""
        if not self._state_change_subscribers:
            return
        message = {
            "type": kind,
            "alert": _alert_to_payload(alert),
        }
        # Snapshot the subscriber list so a concurrent unsubscribe
        # during iteration doesn't raise RuntimeError.
        for queue in list(self._state_change_subscribers):
            try:
                queue.put_nowait(message)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("State-change publish failed: %s", exc)

    # --- Sprint 31.91 5a.2: auto-resolution ---

    def _subscribe_predicate_handlers(self) -> None:
        """Subscribe ``_evaluate_predicates`` to every consumed event type."""
        if self._predicate_handlers_subscribed:
            return
        for event_type in all_consumed_event_types(self._policy_table):
            self._event_bus.subscribe(event_type, self._evaluate_predicates)
        self._predicate_handlers_subscribed = True

    async def _evaluate_predicates(self, event: Event) -> None:
        """Run every active alert's predicate against ``event``."""
        if not self._alerts_config.auto_resolve_on_condition_cleared:
            return
        # list() to allow _auto_resolve to mutate _active_alerts.
        for alert_id, alert in list(self._active_alerts.items()):
            entry = self._policy_table.get(alert.alert_type)
            if entry is None:
                continue
            if not isinstance(event, entry.consumes_event_types):
                continue
            context = self._predicate_contexts.setdefault(
                alert_id, PredicateContext(engaged_at_utc=alert.created_at_utc)
            )
            try:
                cleared = entry.predicate(alert, event, context)
            except Exception as exc:
                logger.warning(
                    "Auto-resolution predicate raised for alert %s (%s): %s",
                    alert_id,
                    alert.alert_type,
                    exc,
                )
                continue
            if cleared:
                await self._auto_resolve(alert_id)

    async def _auto_resolve(self, alert_id: str) -> None:
        """Transition an alert to ARCHIVED via the auto-resolution path."""
        alert = self._active_alerts.pop(alert_id, None)
        if alert is None:
            return
        now_utc = datetime.now(UTC)
        alert.state = AlertLifecycleState.ARCHIVED
        alert.archived_at_utc = now_utc
        if alert.metadata is None:
            alert.metadata = {}
        alert.metadata["auto_resolved_at_utc"] = now_utc.isoformat()
        # Drop the predicate context — alert is no longer active.
        self._predicate_contexts.pop(alert_id, None)
        # Persist the new ARCHIVED state.
        await self._persist_alert(alert)
        # Audit-log row mirroring the 5a.1 ack-audit shape — outcome
        # ``auto_resolution`` per spec D9a line 342.
        await self._write_auto_resolution_audit(alert_id, now_utc)
        # Fan out.
        await self._publish_state_change(
            kind="alert_auto_resolved",
            alert=alert,
        )
        logger.info(
            "Alert %s auto-resolved (type=%s).",
            alert_id,
            alert.alert_type,
        )

    async def _write_auto_resolution_audit(
        self,
        alert_id: str,
        now_utc: datetime,
    ) -> None:
        """Write a ``audit_kind=auto_resolution`` row to the audit log."""
        if self._operations_db_path is None:
            return
        try:
            await self._ensure_operations_schema()
            async with aiosqlite.connect(self._operations_db_path) as db:
                await db.execute(
                    """
                    INSERT INTO alert_acknowledgment_audit
                        (timestamp_utc, alert_id, operator_id, reason, audit_kind)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        now_utc.isoformat(),
                        alert_id,
                        "auto",
                        "policy-table predicate fired",
                        "auto_resolution",
                    ),
                )
                await db.commit()
        except Exception as exc:
            logger.warning(
                "auto_resolution audit-log write failed for %s: %s",
                alert_id,
                exc,
            )

    # --- Sprint 31.91 5a.2: retention task + VACUUM ---

    async def _retention_loop(self) -> None:
        """Daily retention pass (5a.2, MEDIUM #9)."""
        interval = self._alerts_config.retention_task_interval_seconds
        # First pass on a short delay — gives test harnesses a chance to
        # observe a single iteration without waiting a full day.
        await asyncio.sleep(min(interval, 1.0))
        while self._running:
            try:
                await self._run_retention_once()
            except Exception as exc:
                logger.warning("Alert retention pass failed: %s", exc)
            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                raise

    async def _run_retention_once(self) -> None:
        """One retention pass: prune archived alerts + (optional) audit rows."""
        if self._operations_db_path is None:
            return
        await self._ensure_operations_schema()
        archived_cutoff = (
            datetime.now(UTC)
            - timedelta(days=self._alerts_config.archived_alert_retention_days)
        ).isoformat()
        async with aiosqlite.connect(self._operations_db_path) as db:
            await db.execute(
                """
                DELETE FROM alert_state
                WHERE status = 'archived'
                  AND archived_at_utc IS NOT NULL
                  AND archived_at_utc < ?
                """,
                (archived_cutoff,),
            )
            if self._alerts_config.audit_log_retention_days is not None:
                audit_cutoff = (
                    datetime.now(UTC)
                    - timedelta(
                        days=self._alerts_config.audit_log_retention_days
                    )
                ).isoformat()
                await db.execute(
                    """
                    DELETE FROM alert_acknowledgment_audit
                    WHERE timestamp_utc < ?
                    """,
                    (audit_cutoff,),
                )
            await db.commit()
        await self._vacuum_operations_db()

    async def _vacuum_operations_db(self) -> None:
        """VACUUM via Sprint 31.8 S2 idiom: close → to_thread → reopen.

        HealthMonitor does NOT keep an open ``aiosqlite`` connection
        (every persistence call opens-then-closes its own connection),
        so the ``close → VACUUM → reopen`` dance reduces to "VACUUM via
        a synchronous sqlite3 connection on a worker thread." The
        idiom is preserved end-to-end for consistency with the 31.8
        reference implementation.
        """
        if self._operations_db_path is None:
            return

        db_path = self._operations_db_path

        def _sync_vacuum() -> None:
            conn = sqlite3.connect(db_path, isolation_level=None)
            try:
                conn.execute("VACUUM")
            finally:
                conn.close()

        await asyncio.to_thread(_sync_vacuum)

    # --- Integrity Checks ---

    async def _integrity_loop(self) -> None:
        """Run integrity checks on schedule.

        Daily (after market close): Verify all open positions have broker-side stops.
        Weekly (Saturday): Reconcile trade log with broker records.

        Checks run at 4:15 PM ET (15 min after close) daily.
        Weekly check runs on Saturday at 9:00 AM ET.
        """
        et_tz = ZoneInfo("America/New_York")
        daily_check_time = time(16, 15)  # 4:15 PM ET
        weekly_check_day = 5  # Saturday (0=Monday in weekday())
        weekly_check_time = time(9, 0)  # 9:00 AM ET

        while self._running:
            try:
                now = self._clock.now()
                # Ensure we're working in ET
                now_et = now.replace(tzinfo=et_tz) if now.tzinfo is None else now.astimezone(et_tz)

                current_time = now_et.time()
                current_date = now_et.date()

                # Daily check: 4:15 PM ET, once per day
                daily_due = (
                    self._last_daily_check is None or self._last_daily_check.date() < current_date
                )
                if (
                    self._config.daily_check_enabled
                    and current_time >= daily_check_time
                    and daily_due
                ):
                    await self._run_daily_integrity_check()
                    self._last_daily_check = now_et

                # Weekly check: Saturday 9 AM ET
                weekly_due = (
                    self._last_weekly_check is None or (now_et - self._last_weekly_check).days >= 6
                )
                if (
                    self._config.weekly_reconciliation_enabled
                    and now_et.weekday() == weekly_check_day
                    and current_time >= weekly_check_time
                    and weekly_due
                ):
                    await self._run_weekly_reconciliation()
                    self._last_weekly_check = now_et

            except Exception as e:
                logger.error("Integrity check loop error: %s", e)

            # Check every 60 seconds
            await asyncio.sleep(60)

    def register_evaluation_store(self, store: EvaluationEventStore) -> None:
        """Register the EvaluationEventStore handle for /health rendering.

        Sprint 31.915 (DEF-233): /health surfaces the evaluation_db
        subfield by reading observability state from the store. Wired
        once at boot by main.py's lifespan phase 10.3 and by
        api/server.py's standalone telemetry-store init path.
        """
        self._evaluation_store = store

    async def get_evaluation_db_health(self) -> dict[str, Any]:
        """Return the evaluation_db subfield payload for /health.

        Sprint 31.915 (DEF-233). Combines the synchronous snapshot
        (size_mb, last_retention_run_at_et, last_retention_deleted_count)
        with the async freelist_pct read. Returns all-null defaults when
        the store has not been registered (e.g. test fixtures, or boot
        race before phase 10.3).
        """
        if self._evaluation_store is None:
            return {
                "size_mb": None,
                "last_retention_run_at_et": None,
                "last_retention_deleted_count": None,
                "freelist_pct": None,
            }
        snapshot = self._evaluation_store.get_health_snapshot()
        freelist_pct = await self._evaluation_store.get_freelist_pct()
        return {
            **snapshot,
            "freelist_pct": round(freelist_pct, 3),
        }

    def set_order_manager(self, order_manager: OrderManager) -> None:
        """Wire the OrderManager handle for Pattern A.4 cross-reference.

        Sprint 31.91 S2b.2 (Option C, MEDIUM #8): the daily integrity-check
        alert appends a ``see also: stranded_broker_long ...`` line for any
        long-orphan symbol with an active ``stranded_broker_long`` alert
        already firing from 2b.1. This setter exists because main.py is on
        S2b.2's do-not-modify list; tests wire this directly. Production
        wiring is deferred to a future session (Session 5a.1+ migrates the
        cross-reference to HealthMonitor's queryable active-alert state).
        """
        self._order_manager = order_manager

    async def _run_daily_integrity_check(self) -> None:
        """Verify all open positions have broker-side stop orders.

        1. Get all open positions from broker.
        2. Get all open orders from broker.
        3. For each position, verify there's a corresponding stop order.
        4. If any LONG position lacks a stop → ALERT (with Option C
           cross-reference if a ``stranded_broker_long`` alert is already
           firing for the same symbol).
        5. Any SHORT position is by-construction phantom (ARGUS is long-only,
           DEC-011) → emit ``phantom_short`` SystemAlertEvent (2b.1 taxonomy).

        Sprint 31.91 S2b.2 (Pattern A.4 hybrid + Pattern B coverage at
        Health): side-aware count filter + alert-routing decision.

        Requires self._broker to be set.
        """
        if not self._broker:
            logger.warning("Daily integrity check skipped — no broker configured")
            return

        logger.info("Running daily integrity check...")
        try:
            positions = await self._broker.get_positions()

            if not positions:
                logger.info("Daily integrity check: No open positions. OK.")
                return

            orders = await self._broker.get_open_orders()

            # Build set of symbols with active stop orders
            symbols_with_stops: set[str] = set()
            for order in orders:
                order_type = str(getattr(order, "order_type", "")).lower()
                if "stop" in order_type:
                    symbol = getattr(order, "symbol", "")
                    if symbol:
                        symbols_with_stops.add(symbol)

            # Sprint 31.91 S2b.2 Pattern A.4: side-aware partition.
            long_positions = [
                p for p in positions if getattr(p, "side", None) == OrderSide.BUY
            ]
            short_positions = [
                p for p in positions if getattr(p, "side", None) == OrderSide.SELL
            ]

            longs_without_stop = [
                p for p in long_positions
                if getattr(p, "symbol", str(p)) not in symbols_with_stops
            ]

            logger.info(
                "Health integrity check: longs=%d (without_stop=%d), shorts=%d "
                "(all phantom by long-only design), total_broker=%d",
                len(long_positions),
                len(longs_without_stop),
                len(short_positions),
                len(positions),
            )

            # Long-orphan branch: existing alert path + Option C cross-reference.
            if longs_without_stop:
                unprotected_symbols = [
                    getattr(p, "symbol", str(p)) for p in longs_without_stop
                ]
                msg = f"Positions WITHOUT stop orders: {', '.join(unprotected_symbols)}"
                logger.error(msg)

                # Option C cross-reference (PHASE-D-OPEN-ITEMS Item 3):
                # if 2b.1 has an active stranded_broker_long alert for this
                # symbol, cite it so the operator sees the duplication intent.
                cross_ref_lines: list[str] = []
                if self._order_manager is not None:
                    cycle_map = getattr(
                        self._order_manager,
                        "_broker_orphan_last_alerted_cycle",
                        None,
                    )
                    if isinstance(cycle_map, dict):
                        for symbol in unprotected_symbols:
                            last_alerted_cycle = cycle_map.get(symbol)
                            if last_alerted_cycle:
                                cross_ref_lines.append(
                                    f"  - {symbol}: see also stranded_broker_long "
                                    f"alert (last alerted at cycle {last_alerted_cycle})"
                                )

                if cross_ref_lines:
                    msg = (
                        msg
                        + "\n\nCross-reference (active stranded_broker_long alerts):\n"
                        + "\n".join(cross_ref_lines)
                    )

                await self._send_alert(
                    title="Integrity Check FAILED",
                    body=msg,
                    severity="critical",
                )
            elif not short_positions:
                logger.info(
                    "Daily integrity check: All %d positions have stops. OK.",
                    len(positions),
                )

            # Phantom-short branch: ARGUS is long-only, so every broker-side
            # SHORT is a phantom (DEF-204). Emit phantom_short alert per the
            # 2b.1 taxonomy so Session 5a.2 auto-resolution can consume
            # uniformly across all detection sites.
            for pos in short_positions:
                symbol = getattr(pos, "symbol", str(pos))
                shares = int(getattr(pos, "shares", 0))
                alert = SystemAlertEvent(
                    severity="critical",
                    source="health.integrity_check",
                    alert_type="phantom_short",
                    message=(
                        f"Health integrity check found broker-side short position "
                        f"for {symbol}: shares={shares}. ARGUS is long-only by design."
                    ),
                    metadata={
                        "symbol": symbol,
                        "shares": shares,
                        "side": "SELL",
                        "detection_source": "health.integrity_check",
                    },
                )
                try:
                    await self._event_bus.publish(alert)
                except Exception:
                    logger.exception(
                        "Failed to publish phantom_short SystemAlertEvent for %s "
                        "from Health integrity check",
                        symbol,
                    )

        except Exception as e:
            logger.error("Daily integrity check failed: %s", e)
            await self._send_alert(
                title="Integrity Check Error",
                body=str(e),
                severity="critical",
            )

    async def _run_weekly_reconciliation(self) -> None:
        """Reconcile system trade log with broker's official records.

        1. Fetch this week's closed orders from broker.
        2. Fetch this week's logged trades from TradeLogger.
        3. Compare: every broker fill should have a corresponding trade log entry.
        4. Report discrepancies.

        Requires self._broker and self._trade_logger to be set.
        """
        if not self._broker or not self._trade_logger:
            logger.warning("Weekly reconciliation skipped — broker or trade_logger not configured")
            return

        logger.info("Running weekly reconciliation...")
        try:
            # FIX-05 (P1-A2-L11): the full broker/trade-log comparison is
            # tracked under DEF-182 — Weekly reconciliation implementation.
            # The Sprint-5-era stub here has been firing a weekly WARNING
            # since Sprint 5 without actually comparing trades. Until
            # DEF-182 lands, this call is explicitly a liveness probe only
            # (the broker accessibility check still has operational value).
            logger.warning(
                "Weekly reconciliation: liveness probe only "
                "(full trade comparison tracked under DEF-182)"
            )
            account = await self._broker.get_account()
            logger.info(
                "Weekly reconciliation: broker accessible. Account equity: %s",
                account,
            )

        except Exception as e:
            logger.error("Weekly reconciliation failed: %s", e)
            await self._send_alert(
                title="Weekly Reconciliation Error",
                body=str(e),
                severity="critical",
            )

    # --- Public alert methods for other components ---

    async def send_critical_alert(self, title: str, body: str) -> None:
        """Public method for other components to send critical alerts.

        Args:
            title: Alert title.
            body: Alert body/message.
        """
        await self._send_alert(title, body, severity="critical")

    async def send_warning_alert(self, title: str, body: str) -> None:
        """Public method for other components to send warning alerts.

        Args:
            title: Alert title.
            body: Alert body/message.
        """
        await self._send_alert(title, body, severity="warning")

    # --- Strategy Evaluation Health Check ---

    async def check_strategy_evaluations(
        self,
        strategies: dict[str, BaseStrategy],
        eval_store: EvaluationEventStore,
        clock: Clock,
    ) -> None:
        """Check for active strategies with zero evaluation events after window opens.

        Detects when an active strategy has a populated watchlist but no
        evaluation events after its operating window start + 5 minutes,
        indicating a possible pipeline issue.

        This method is idempotent — safe to call repeatedly. When evaluations
        appear, the warning stops and the component status returns to HEALTHY.

        On market holidays the check is skipped entirely — zero evaluations are
        expected and setting strategies to DEGRADED would be a false alarm.

        Args:
            strategies: Dict mapping strategy_id to BaseStrategy instances.
            eval_store: The EvaluationEventStore for querying today's events.
            clock: Clock for current time.
        """
        from argus.core.market_calendar import is_market_holiday

        is_holiday, holiday_name = is_market_holiday()
        if is_holiday:
            logger.debug("Skipping evaluation check — market holiday (%s)", holiday_name)
            return

        et_tz = ZoneInfo("America/New_York")
        now = clock.now()
        now_et = now.replace(tzinfo=et_tz) if now.tzinfo is None else now.astimezone(et_tz)
        current_time = now_et.time()
        today_str = now_et.strftime("%Y-%m-%d")

        for strategy_id, strategy in strategies.items():
            component_name = f"strategy_{strategy_id}"

            if not strategy.is_active:
                continue

            if len(strategy.watchlist) == 0:
                continue

            # Parse the strategy's earliest_entry time and add 5 minutes
            earliest_entry_str = strategy.config.operating_window.earliest_entry
            parts = earliest_entry_str.split(":")
            entry_hour = int(parts[0])
            entry_minute = int(parts[1])
            grace_minute = entry_minute + 5
            grace_hour = entry_hour + grace_minute // 60
            grace_minute = grace_minute % 60
            window_threshold = time(grace_hour, grace_minute)

            if current_time < window_threshold:
                continue

            # Query today's evaluation count for this strategy
            events = await eval_store.query_events(
                strategy_id=strategy_id, date=today_str, limit=1
            )
            minutes_past = (
                (current_time.hour * 60 + current_time.minute)
                - (entry_hour * 60 + entry_minute)
            )

            if len(events) == 0:
                logger.warning(
                    "Strategy %s has 0 evaluation events %dmin after window "
                    "opened (watchlist: %d symbols) — possible pipeline issue",
                    strategy_id,
                    minutes_past,
                    len(strategy.watchlist),
                )
                self.update_component(
                    component_name,
                    ComponentStatus.DEGRADED,
                    message=(
                        f"0 evaluations {minutes_past}min after window "
                        f"(watchlist: {len(strategy.watchlist)} symbols)"
                    ),
                )
            else:
                # Evaluations present — ensure component is HEALTHY
                current = self._components.get(component_name)
                if current is not None and current.status == ComponentStatus.DEGRADED:
                    self.update_component(
                        component_name,
                        ComponentStatus.HEALTHY,
                        message="Evaluations resumed",
                    )
