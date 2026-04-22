"""Health monitoring for Argus.

Provides component health tracking, heartbeat pings, alert dispatch, and
scheduled integrity checks.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

import aiohttp

from argus.core.config import HealthConfig
from argus.core.event_bus import EventBus
from argus.core.events import CircuitBreakerEvent, HeartbeatEvent, SystemStatus

if TYPE_CHECKING:
    from argus.analytics.trade_logger import TradeLogger
    from argus.core.clock import Clock
    from argus.execution.broker import Broker
    from argus.strategies.base_strategy import BaseStrategy
    from argus.strategies.telemetry_store import EvaluationEventStore

logger = logging.getLogger(__name__)


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
    ) -> None:
        """Initialize the HealthMonitor.

        Args:
            event_bus: Event bus for publishing health events.
            clock: Clock protocol for time operations.
            config: Health monitoring configuration.
            broker: Optional broker for integrity checks.
            trade_logger: Optional trade logger for reconciliation.
        """
        self._event_bus = event_bus
        self._clock = clock
        self._config = config
        self._broker = broker
        self._trade_logger = trade_logger

        # Component health registry
        self._components: dict[str, ComponentHealth] = {}

        # Tasks
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._integrity_task: asyncio.Task[None] | None = None
        self._running: bool = False

        # Tracking
        self._last_daily_check: datetime | None = None
        self._last_weekly_check: datetime | None = None

    async def start(self) -> None:
        """Start health monitoring.

        1. Subscribe to CircuitBreakerEvent for alert dispatch.
        2. Start heartbeat loop.
        3. Start integrity check loop.
        """
        self._event_bus.subscribe(CircuitBreakerEvent, self._on_circuit_breaker)
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._integrity_task = asyncio.create_task(self._integrity_loop())
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

    async def _run_daily_integrity_check(self) -> None:
        """Verify all open positions have broker-side stop orders.

        1. Get all open positions from broker.
        2. Get all open orders from broker.
        3. For each position, verify there's a corresponding stop order.
        4. If any position lacks a stop → ALERT.

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

            # Check each position
            unprotected = []
            for pos in positions:
                symbol = getattr(pos, "symbol", str(pos))
                if symbol not in symbols_with_stops:
                    unprotected.append(symbol)

            if unprotected:
                msg = f"Positions WITHOUT stop orders: {', '.join(unprotected)}"
                logger.error(msg)
                await self._send_alert(
                    title="Integrity Check FAILED",
                    body=msg,
                    severity="critical",
                )
            else:
                logger.info(
                    "Daily integrity check: All %d positions have stops. OK.",
                    len(positions),
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
