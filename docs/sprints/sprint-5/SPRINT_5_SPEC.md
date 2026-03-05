# ARGUS — Sprint 5 Implementation Spec

> **Date:** February 16, 2026
> **Author:** Claude (claude.ai strategic session)
> **Purpose:** Complete implementation guide for Claude Code. Everything needed to build Sprint 5 without ambiguity.
> **Starting state:** 320 tests, 0 flaky, ruff clean. Sprint 4b complete.

---

## Sprint 5 Objective

Wire all existing components into a running system, add operational hardening (health monitoring, recovery, integrity checks), and validate on Alpaca paper trading. After this sprint, Argus runs autonomously during market hours on paper trading.

**Phase 1 exit criteria (from Sprint Plan):** Minimum 3 trading days of unattended paper trading with no crashes, no missed events, all trades logged correctly, stops managed properly, EOD flatten works, daily performance recorded.

---

## Micro-Decisions (All Resolved)

### MD-5-1: External Monitoring — Generic Webhook ✅

**Decision:** HealthMonitor sends HTTP POST to a configured webhook URL every 60 seconds. Default config points to Healthchecks.io. Dead man's switch is handled by the external service (alert if no ping for 5 minutes). The webhook URL is configurable in `config/system.yaml`.

### MD-5-2: Alerting Channel — Webhook-Based ✅

**Decision:** Critical events (circuit breaker, crash, data stall, integrity check failure) send an HTTP POST to a configured alert webhook URL. Separate from the heartbeat URL. Point it at a Discord webhook for instant push notifications during paper trading.

### MD-5-3: Strategy State Reconstruction — Full with Skip-Day Fallback ✅

**Decision:** On mid-day restart, AlpacaDataService fetches the current day's historical 1m bars from Alpaca REST API and replays them through the indicator engine and strategy. If the historical fetch fails, the strategy marks itself inactive for the remainder of the day. This gives the best chance of resuming without adding much complexity.

### MD-5-4: Order Manager Reconstruction — Query Broker on Startup ✅

**Decision:** On startup, the Order Manager queries the broker for all open positions and standing orders. It reconstructs ManagedPosition objects for anything it finds and resumes management (tick subscription, time stops, EOD flatten). The broker is the source of truth for what positions exist.

### MD-5-5: System Health Storage — In-Memory Only ✅

**Decision:** Health status is a dict of `{component_name: ComponentHealth}` in the HealthMonitor. Lost on restart, which is fine — health is a live concern. Status changes are logged to structured log for post-hoc analysis.

### MD-5-6: Main Entry Point — Procedural ✅

**Decision:** A single `async def main()` that instantiates components in order, wires them, and runs the event loop. Reads like a recipe. No dependency injection container.

---

## Component Overview

| # | Component | File | Purpose | New/Modified |
|---|-----------|------|---------|--------------|
| 1 | HealthMonitor | `argus/core/health.py` | Component health tracking, heartbeat, alerts | NEW |
| 2 | System Entry Point | `argus/main.py` | Wires everything, runs the event loop | NEW |
| 3 | Graceful Shutdown | `argus/main.py` | SIGINT/SIGTERM handling, clean exit | NEW (in main.py) |
| 4 | Stale Data Market Hours Fix | `argus/data/alpaca_data_service.py` | RSK-015: Only trigger stale alerts during market hours | MODIFIED |
| 5 | Strategy Reconstruction | `argus/strategies/orb_breakout.py` | Rebuild opening range from historical data on restart | MODIFIED |
| 6 | Order Manager Reconstruction | `argus/execution/order_manager.py` | Recover open positions from broker on startup | MODIFIED |
| 7 | Integrity Checks | `argus/core/health.py` | Daily stop verification, weekly reconciliation | NEW (in health.py) |
| 8 | Structured Logging | `argus/core/logging_config.py` | JSON structured logging setup | NEW |
| 9 | HealthMonitor Config | `config/system.yaml` + `argus/core/config.py` | Config for webhooks, intervals | MODIFIED |

---

## Component 1: HealthMonitor (`argus/core/health.py`)

### Purpose

Central health tracking for all system components. Provides three functions:
1. **Component status registry** — each component reports its health; HealthMonitor aggregates.
2. **Heartbeat** — HTTP POST to configured URL every 60 seconds (dead man's switch).
3. **Alert dispatch** — HTTP POST to configured URL on critical events.
4. **Integrity checks** — scheduled verification of system consistency.

### Data Models

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ComponentStatus(str, Enum):
    """Health status of a system component."""
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"     # Working but with issues (e.g., reconnecting)
    UNHEALTHY = "unhealthy"   # Not functioning
    STOPPED = "stopped"


@dataclass
class ComponentHealth:
    """Health snapshot for a single component."""
    name: str
    status: ComponentStatus
    last_updated: datetime
    message: str = ""
    details: dict = field(default_factory=dict)
```

### Interface

```python
import asyncio
import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

import aiohttp

from argus.core.config import HealthConfig
from argus.core.event_bus import EventBus
from argus.core.events import CircuitBreakerEvent, HeartbeatEvent

logger = logging.getLogger(__name__)


class HealthMonitor:
    """System health monitoring, heartbeat, and alerting.
    
    Tracks component health status in-memory. Sends periodic heartbeat
    pings to an external monitoring service (e.g., Healthchecks.io).
    Dispatches critical alerts via webhook.
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        clock,                    # Clock protocol
        config: HealthConfig,
        broker=None,              # Optional: for integrity checks
        trade_logger=None,        # Optional: for reconciliation
    ) -> None:
        self._event_bus = event_bus
        self._clock = clock
        self._config = config
        self._broker = broker
        self._trade_logger = trade_logger
        
        # Component health registry
        self._components: dict[str, ComponentHealth] = {}
        
        # Tasks
        self._heartbeat_task: asyncio.Task | None = None
        self._integrity_task: asyncio.Task | None = None
        self._running: bool = False
        
        # Tracking
        self._last_daily_check: datetime | None = None
        self._last_weekly_check: datetime | None = None
    
    async def start(self) -> None:
        """Start health monitoring.
        
        1. Subscribe to CircuitBreakerEvent for alert dispatch
        2. Start heartbeat loop
        3. Start integrity check loop
        """
        await self._event_bus.subscribe(CircuitBreakerEvent, self._on_circuit_breaker)
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._integrity_task = asyncio.create_task(self._integrity_loop())
        logger.info("HealthMonitor started")
    
    async def stop(self) -> None:
        """Stop health monitoring. Cancel all tasks."""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._integrity_task:
            self._integrity_task.cancel()
        logger.info("HealthMonitor stopped")

    # --- Component Registry ---
    
    def update_component(
        self, name: str, status: ComponentStatus, message: str = "", details: dict | None = None
    ) -> None:
        """Update a component's health status.
        
        Called by each component when its status changes.
        If status transitions to UNHEALTHY, send an alert.
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
        if status == ComponentStatus.UNHEALTHY:
            if previous is None or previous.status != ComponentStatus.UNHEALTHY:
                asyncio.create_task(self._send_alert(
                    title=f"Component UNHEALTHY: {name}",
                    body=message,
                    severity="critical",
                ))
        
        logger.info("Component %s → %s: %s", name, status.value, message)
    
    def get_status(self) -> dict[str, ComponentHealth]:
        """Return all component health statuses."""
        return dict(self._components)
    
    def get_overall_status(self) -> ComponentStatus:
        """Return overall system status.
        
        UNHEALTHY if any component is UNHEALTHY.
        DEGRADED if any component is DEGRADED.
        HEALTHY if all components are HEALTHY.
        STARTING if any component is STARTING and none are UNHEALTHY.
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
                
                # Publish HeartbeatEvent to Event Bus
                await self._event_bus.publish(HeartbeatEvent(
                    timestamp=self._clock.now(),
                    system_status=overall.value,
                ))
                
                # Send to external monitoring
                if self._config.heartbeat_url:
                    await self._send_heartbeat(overall)
                
            except Exception as e:
                logger.error("Heartbeat failed: %s", e)
            
            await asyncio.sleep(self._config.heartbeat_interval_seconds)
    
    async def _send_heartbeat(self, status: ComponentStatus) -> None:
        """HTTP POST to heartbeat URL.
        
        For Healthchecks.io: a simple GET/POST to the ping URL.
        Include system status in the body for context.
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "status": status.value,
                    "timestamp": self._clock.now().isoformat(),
                    "components": {
                        name: health.status.value
                        for name, health in self._components.items()
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
            {"content": "🚨 **title**\nbody"}
        
        Generic format:
            {"title": ..., "body": ..., "severity": ..., "timestamp": ...}
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
        """Circuit breaker fired — send critical alert."""
        await self._send_alert(
            title="Circuit Breaker Triggered",
            body=f"Level: {event.level}, Reason: {event.reason}",
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
        ET = ZoneInfo("America/New_York")
        daily_check_time = time(16, 15)      # 4:15 PM ET
        weekly_check_day = 5                  # Saturday (0=Monday in weekday())
        weekly_check_time = time(9, 0)        # 9:00 AM ET
        
        while self._running:
            try:
                now = self._clock.now()
                # Ensure we're working in ET
                if now.tzinfo is None:
                    now_et = now.replace(tzinfo=ET)
                else:
                    now_et = now.astimezone(ET)
                
                current_time = now_et.time()
                current_date = now_et.date()
                
                # Daily check: 4:15 PM ET, once per day
                if (current_time >= daily_check_time
                    and (self._last_daily_check is None 
                         or self._last_daily_check.date() < current_date)):
                    await self._run_daily_integrity_check()
                    self._last_daily_check = now_et
                
                # Weekly check: Saturday 9 AM ET
                if (now_et.weekday() == weekly_check_day
                    and current_time >= weekly_check_time
                    and (self._last_weekly_check is None
                         or (now_et - self._last_weekly_check).days >= 6)):
                    await self._run_weekly_reconciliation()
                    self._last_weekly_check = now_et
            
            except Exception as e:
                logger.error("Integrity check loop error: %s", e)
            
            # Check every 60 seconds
            await asyncio.sleep(60)
    
    async def _run_daily_integrity_check(self) -> None:
        """Verify all open positions have broker-side stop orders.
        
        1. Get all open positions from broker
        2. Get all open orders from broker
        3. For each position, verify there's a corresponding stop order
        4. If any position lacks a stop → ALERT
        
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
            symbols_with_stops = set()
            for order in orders:
                if hasattr(order, 'order_type') and 'stop' in str(order.order_type).lower():
                    symbols_with_stops.add(order.symbol if hasattr(order, 'symbol') else "")
            
            # Check each position
            unprotected = []
            for pos in positions:
                symbol = pos.symbol if hasattr(pos, 'symbol') else str(pos)
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
        
        1. Fetch this week's closed orders from broker
        2. Fetch this week's logged trades from TradeLogger
        3. Compare: every broker fill should have a corresponding trade log entry
        4. Report discrepancies
        
        Requires self._broker and self._trade_logger to be set.
        """
        if not self._broker or not self._trade_logger:
            logger.warning("Weekly reconciliation skipped — broker or trade_logger not configured")
            return
        
        logger.info("Running weekly reconciliation...")
        try:
            # Implementation depends on broker's get_closed_orders() method.
            # For Sprint 5, this is a placeholder that logs a reminder.
            # Full reconciliation requires:
            #   broker_trades = await self._broker.get_order_history(days=7)
            #   logged_trades = await self._trade_logger.get_trades(days=7)
            #   Compare and report discrepancies.
            #
            # The Alpaca API provides get_orders(status="closed") for this.
            # Implementing the full comparison is the task here.
            
            logger.info("Weekly reconciliation: TODO — implement full comparison")
            # For now, just verify broker is accessible
            account = await self._broker.get_account()
            logger.info("Weekly reconciliation: Broker accessible. Account equity: %s", account)
        
        except Exception as e:
            logger.error("Weekly reconciliation failed: %s", e)
            await self._send_alert(
                title="Weekly Reconciliation Error",
                body=str(e),
                severity="critical",
            )
    
    # --- Public alert method for other components ---
    
    async def send_critical_alert(self, title: str, body: str) -> None:
        """Public method for other components to send critical alerts."""
        await self._send_alert(title, body, severity="critical")
    
    async def send_warning_alert(self, title: str, body: str) -> None:
        """Public method for other components to send warning alerts."""
        await self._send_alert(title, body, severity="warning")
```

### Dependencies

Add `aiohttp` to project dependencies. This is a lightweight HTTP client for the webhook calls. It's already a transitive dependency of alpaca-py, so it's likely already installed, but make it explicit.

---

## Component 2: System Entry Point (`argus/main.py`)

### Purpose

The single entry point that wires all components together and runs the system. This is the most critical new file in Sprint 5 — it makes Argus a runnable program rather than a collection of tested components.

### Implementation

```python
"""Argus Trading System — Main Entry Point.

Wires all components together and runs the event loop.

Usage:
    python -m argus.main                    # Default: config/ directory
    python -m argus.main --config /path/to  # Custom config directory
    python -m argus.main --paper            # Force paper trading (default)
    python -m argus.main --dry-run          # Start, connect, but don't trade
"""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env BEFORE any component imports that read env vars
load_dotenv()

from argus.core.clock import SystemClock
from argus.core.config import load_config, load_strategy_config
from argus.core.event_bus import EventBus
from argus.core.events import CircuitBreakerEvent
from argus.core.health import ComponentStatus, HealthMonitor
from argus.core.logging_config import setup_logging
from argus.analytics.trade_logger import TradeLogger
from argus.core.risk_manager import RiskManager
from argus.data.alpaca_data_service import AlpacaDataService
from argus.data.alpaca_scanner import AlpacaScanner
from argus.db.manager import DatabaseManager
from argus.execution.alpaca_broker import AlpacaBroker
from argus.execution.order_manager import OrderManager
from argus.strategies.orb_breakout import OrbBreakoutStrategy

logger = logging.getLogger(__name__)


class ArgusSystem:
    """Top-level system container. Owns all components and their lifecycle."""
    
    def __init__(self, config_dir: Path, dry_run: bool = False) -> None:
        self._config_dir = config_dir
        self._dry_run = dry_run
        self._shutdown_event = asyncio.Event()
        
        # Components (initialized in start())
        self._clock = None
        self._event_bus = None
        self._db = None
        self._trade_logger = None
        self._broker = None
        self._data_service = None
        self._scanner = None
        self._risk_manager = None
        self._strategy = None
        self._order_manager = None
        self._health_monitor = None
    
    async def start(self) -> None:
        """Initialize and start all components in dependency order.
        
        Order matters:
        1. Config + Clock + EventBus (no dependencies)
        2. Database + TradeLogger (needs config)
        3. Broker (needs config, event_bus)
        4. HealthMonitor (needs event_bus, clock, broker)
        5. RiskManager (needs event_bus, clock, config, trade_logger)
        6. DataService (needs config, event_bus, clock)
        7. Scanner (needs config)
        8. Strategy (needs config, event_bus, clock)
        9. OrderManager (needs event_bus, broker, clock, config, trade_logger)
        10. Subscribe strategy to events
        11. Start data service streaming
        """
        logger.info("=" * 60)
        logger.info("ARGUS TRADING SYSTEM — STARTING")
        logger.info("=" * 60)
        
        # --- Phase 1: Foundation ---
        logger.info("[1/10] Loading configuration...")
        config = load_config(self._config_dir)
        
        self._clock = SystemClock()
        self._event_bus = EventBus()
        
        # --- Phase 2: Database ---
        logger.info("[2/10] Initializing database...")
        self._db = DatabaseManager()
        await self._db.initialize()
        self._trade_logger = TradeLogger(self._db)
        
        # --- Phase 3: Broker ---
        logger.info("[3/10] Connecting to broker...")
        self._broker = AlpacaBroker(
            config=config.broker.alpaca,
            event_bus=self._event_bus,
        )
        await self._broker.connect()
        
        account = await self._broker.get_account()
        logger.info("Broker connected. Account equity: %s", account)
        
        # --- Phase 4: Health Monitor ---
        logger.info("[4/10] Starting health monitor...")
        self._health_monitor = HealthMonitor(
            event_bus=self._event_bus,
            clock=self._clock,
            config=config.system.health,
            broker=self._broker,
            trade_logger=self._trade_logger,
        )
        await self._health_monitor.start()
        self._health_monitor.update_component("event_bus", ComponentStatus.HEALTHY)
        self._health_monitor.update_component("database", ComponentStatus.HEALTHY)
        self._health_monitor.update_component("broker", ComponentStatus.HEALTHY)
        
        # --- Phase 5: Risk Manager ---
        logger.info("[5/10] Initializing risk manager...")
        self._risk_manager = RiskManager(
            event_bus=self._event_bus,
            config=config.risk,
            clock=self._clock,
        )
        await self._risk_manager.start(broker=self._broker)
        # Reconstruct state (weekly P&L, daily P&L) from trade log
        await self._risk_manager.reconstruct_state(self._trade_logger)
        self._health_monitor.update_component("risk_manager", ComponentStatus.HEALTHY)
        
        # --- Phase 6: Data Service ---
        logger.info("[6/10] Starting data service...")
        self._data_service = AlpacaDataService(
            config=config.broker.alpaca,
            event_bus=self._event_bus,
            clock=self._clock,
            health_monitor=self._health_monitor,
        )
        self._health_monitor.update_component("data_service", ComponentStatus.STARTING)
        
        # --- Phase 7: Scanner ---
        logger.info("[7/10] Running pre-market scan...")
        self._scanner = AlpacaScanner(
            config=config.scanner.alpaca,
        )
        watchlist = await self._scanner.scan()
        symbols = [item.symbol for item in watchlist]
        
        if not symbols:
            logger.warning("Scanner returned no symbols. System will idle.")
            self._health_monitor.update_component("scanner", ComponentStatus.DEGRADED,
                                                   message="No symbols passed filters")
        else:
            logger.info("Scanner found %d symbols: %s", len(symbols), symbols)
            self._health_monitor.update_component("scanner", ComponentStatus.HEALTHY,
                                                   message=f"{len(symbols)} symbols")
        
        # --- Phase 8: Strategy ---
        logger.info("[8/10] Initializing strategy...")
        strategy_config = load_strategy_config(
            self._config_dir / "strategies" / "orb_breakout.yaml"
        )
        self._strategy = OrbBreakoutStrategy(
            config=strategy_config,
            event_bus=self._event_bus,
            clock=self._clock,
        )
        # If mid-day restart, attempt state reconstruction
        await self._reconstruct_strategy_state(symbols)
        self._health_monitor.update_component("strategy", ComponentStatus.HEALTHY,
                                               message="OrbBreakout active")
        
        # --- Phase 9: Order Manager ---
        logger.info("[9/10] Starting order manager...")
        self._order_manager = OrderManager(
            event_bus=self._event_bus,
            broker=self._broker,
            clock=self._clock,
            config=config.order_manager,
            trade_logger=self._trade_logger,
        )
        await self._order_manager.start()
        # Reconstruct open positions from broker
        await self._order_manager.reconstruct_from_broker()
        self._health_monitor.update_component("order_manager", ComponentStatus.HEALTHY)
        
        # --- Phase 10: Start streaming ---
        logger.info("[10/10] Starting data streams...")
        if symbols and not self._dry_run:
            await self._data_service.start(symbols=symbols, timeframes=["1m"])
            self._health_monitor.update_component("data_service", ComponentStatus.HEALTHY,
                                                   message=f"Streaming {len(symbols)} symbols")
        elif self._dry_run:
            logger.info("DRY RUN: Data streams not started.")
            self._health_monitor.update_component("data_service", ComponentStatus.DEGRADED,
                                                   message="Dry run — no streaming")
        
        logger.info("=" * 60)
        logger.info("ARGUS TRADING SYSTEM — RUNNING")
        if self._dry_run:
            logger.info("MODE: DRY RUN (no trades will be placed)")
        logger.info("Watching %d symbols", len(symbols))
        logger.info("=" * 60)
        
        # Send startup alert
        await self._health_monitor.send_warning_alert(
            title="Argus Started",
            body=f"Watching {len(symbols)} symbols. Mode: {'DRY RUN' if self._dry_run else 'PAPER TRADING'}",
        )
    
    async def _reconstruct_strategy_state(self, symbols: list[str]) -> None:
        """Reconstruct strategy state if restarting mid-day.
        
        1. Check if we're within market hours
        2. If yes, fetch today's historical 1m bars for all symbols
        3. Replay them through the strategy to rebuild opening range
        4. If fetch fails, mark strategy as inactive for today
        """
        from datetime import time as dt_time
        from zoneinfo import ZoneInfo
        
        ET = ZoneInfo("America/New_York")
        now = self._clock.now()
        if now.tzinfo is None:
            now_et = now.replace(tzinfo=ET)
        else:
            now_et = now.astimezone(ET)
        
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)
        
        if not (market_open <= now_et.time() <= market_close):
            logger.info("Outside market hours — no strategy reconstruction needed")
            return
        
        logger.info("Mid-day start detected. Reconstructing strategy state...")
        
        try:
            # Use AlpacaDataService's historical fetch capability
            # to get today's 1m bars from market open to now
            if hasattr(self._data_service, 'fetch_todays_bars'):
                todays_bars = await self._data_service.fetch_todays_bars(symbols)
                
                if todays_bars:
                    # Replay bars through strategy
                    for bar in todays_bars:
                        await self._strategy.on_candle(bar)
                    
                    logger.info(
                        "Strategy state reconstructed from %d historical bars",
                        len(todays_bars),
                    )
                else:
                    logger.warning("No historical bars available — strategy starting fresh")
            else:
                logger.warning("DataService doesn't support fetch_todays_bars — skipping reconstruction")
        
        except Exception as e:
            logger.error("Strategy reconstruction failed: %s. Strategy will sit out today.", e)
            # Deactivate strategy for the day
            if hasattr(self._strategy, 'deactivate'):
                self._strategy.deactivate("Reconstruction failed")
            self._health_monitor.update_component(
                "strategy", ComponentStatus.DEGRADED,
                message=f"Reconstruction failed: {e}",
            )
    
    async def shutdown(self) -> None:
        """Graceful shutdown sequence.
        
        Order matters (reverse of startup):
        1. Stop accepting new signals (deactivate strategy)
        2. Flatten positions if configured (EOD flatten)
        3. Stop data streams
        4. Stop order manager
        5. Stop risk manager
        6. Stop health monitor
        7. Close database
        8. Close broker connection
        """
        logger.info("=" * 60)
        logger.info("ARGUS TRADING SYSTEM — SHUTTING DOWN")
        logger.info("=" * 60)
        
        # Send shutdown alert
        if self._health_monitor:
            await self._health_monitor.send_warning_alert(
                title="Argus Shutting Down",
                body="Graceful shutdown initiated",
            )
        
        # 1. Stop strategy
        if self._strategy:
            logger.info("Stopping strategy...")
            if hasattr(self._strategy, 'deactivate'):
                self._strategy.deactivate("System shutdown")
        
        # 2. Flatten positions (optional — configurable)
        # For paper trading, we leave positions open.
        # For live trading, this would be configurable.
        
        # 3. Stop data streams
        if self._data_service:
            logger.info("Stopping data service...")
            await self._data_service.stop()
        
        # 4. Stop order manager
        if self._order_manager:
            logger.info("Stopping order manager...")
            await self._order_manager.stop()
        
        # 5. Stop risk manager
        # (Risk Manager doesn't have a stop() in current impl — just unsubscribes)
        
        # 6. Stop health monitor
        if self._health_monitor:
            logger.info("Stopping health monitor...")
            await self._health_monitor.stop()
        
        # 7. Close database
        if self._db:
            logger.info("Closing database...")
            await self._db.close()
        
        # 8. Close broker
        if self._broker:
            logger.info("Disconnecting broker...")
            if hasattr(self._broker, 'disconnect'):
                await self._broker.disconnect()
        
        logger.info("=" * 60)
        logger.info("ARGUS TRADING SYSTEM — STOPPED")
        logger.info("=" * 60)
    
    async def run(self) -> None:
        """Start the system and wait for shutdown signal."""
        try:
            await self.start()
            # Wait until shutdown is requested
            await self._shutdown_event.wait()
        except Exception as e:
            logger.critical("Fatal error during startup: %s", e, exc_info=True)
            if self._health_monitor:
                await self._health_monitor.send_critical_alert(
                    title="Argus FATAL ERROR",
                    body=str(e),
                )
        finally:
            await self.shutdown()
    
    def request_shutdown(self) -> None:
        """Signal the system to shut down. Called by signal handlers."""
        logger.info("Shutdown requested")
        self._shutdown_event.set()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Argus Trading System")
    parser.add_argument(
        "--config", type=Path, default=Path("config"),
        help="Path to configuration directory (default: config/)",
    )
    parser.add_argument(
        "--paper", action="store_true", default=True,
        help="Use paper trading (default: True)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Start and connect but don't stream data or trade",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point. Sets up signal handlers and runs the system."""
    args = parse_args()
    
    # Set up logging first
    setup_logging(log_level="INFO")
    
    logger.info("Argus starting with config from: %s", args.config)
    
    system = ArgusSystem(config_dir=args.config, dry_run=args.dry_run)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Signal handlers for graceful shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, system.request_shutdown)
    
    try:
        loop.run_until_complete(system.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
```

### Adaptation Notes for Claude Code

The above is the **target architecture**. During implementation, you'll need to adapt to the actual interfaces of existing components. Specifically:

1. **`AlpacaBroker.connect()`** — Check if this method exists. If not, the broker may connect lazily on first API call. Adjust accordingly.
2. **`RiskManager.start(broker=...)`** — Check how RiskManager currently gets broker reference. It may already be set in constructor.
3. **`RiskManager.reconstruct_state(trade_logger)`** — This exists from Sprint 2. Verify the signature.
4. **`AlpacaDataService` constructor** — Check what arguments it currently takes. It may not accept `health_monitor` yet — add it as an optional parameter.
5. **`AlpacaScanner` constructor** — Check its current interface and adapt.
6. **`OrbBreakoutStrategy.on_candle()`** — Verify this method exists for reconstruction replay.

**The goal is to wire existing components, not rewrite them.** If an interface doesn't quite fit, add a thin adapter method rather than restructuring the existing component.

---

## Component 3: Graceful Shutdown

Already integrated into `ArgusSystem` above. Key behaviors:

1. **SIGINT (Ctrl+C)** and **SIGTERM** both trigger `request_shutdown()`.
2. Shutdown stops components in reverse order of startup.
3. Each component's `stop()` method is called, which should:
   - Cancel async tasks
   - Close WebSocket connections
   - Flush pending database writes
4. **No position flattening on shutdown by default** for paper trading. Add a `--flatten-on-exit` flag for live trading later.

---

## Component 4: Stale Data Market Hours Fix (`argus/data/alpaca_data_service.py`)

### Purpose

Fix RSK-015: The stale data monitor currently runs 24/7 but only market-hours data is expected. Outside market hours, lack of data is normal and should not trigger alerts.

### Changes

Modify the `_stale_data_monitor()` method in AlpacaDataService to check whether the current time is within market hours before triggering a stale data alert.

```python
# Add to AlpacaDataService._stale_data_monitor():

from datetime import time as dt_time
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

async def _stale_data_monitor(self) -> None:
    """Monitor for stale data. Only alert during market hours."""
    while self._running:
        await asyncio.sleep(self._stale_check_interval)
        
        now = self._clock.now()
        if now.tzinfo is None:
            now_et = now.replace(tzinfo=ET)
        else:
            now_et = now.astimezone(ET)
        
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)
        
        # Only check for stale data during market hours on weekdays
        if now_et.weekday() >= 5:  # Saturday=5, Sunday=6
            continue
        if not (market_open <= now_et.time() <= market_close):
            continue
        
        # Existing stale data check logic continues here...
        # (Check last_data_timestamp against now - stale_threshold)
```

Also add an optional `health_monitor` parameter to AlpacaDataService constructor. When stale data IS detected during market hours, call `health_monitor.update_component("data_service", ComponentStatus.DEGRADED, ...)`. When data resumes, update back to HEALTHY.

---

## Component 5: Strategy State Reconstruction

### Purpose

If Argus restarts mid-day, OrbBreakout needs to reconstruct its opening range from historical data.

### Approach

Add a method to AlpacaDataService that fetches today's 1m bars:

```python
# Add to AlpacaDataService:

async def fetch_todays_bars(self, symbols: list[str]) -> list[CandleEvent]:
    """Fetch today's 1m bars from Alpaca REST API for reconstruction.
    
    Returns CandleEvent objects in chronological order, suitable for
    replaying through strategies.
    
    Uses StockHistoricalDataClient.get_stock_bars() with:
    - timeframe: 1Min
    - start: today at 9:30 AM ET
    - end: now
    """
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    
    ET = ZoneInfo("America/New_York")
    now = self._clock.now()
    if now.tzinfo is None:
        now_et = now.replace(tzinfo=ET)
    else:
        now_et = now.astimezone(ET)
    
    today_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    
    events = []
    
    for symbol in symbols:
        try:
            # Use the existing historical data client
            bars = await self._fetch_historical_bars(
                symbol=symbol,
                timeframe="1Min",
                start=today_open,
                end=now_et,
            )
            
            for bar in bars:
                events.append(CandleEvent(
                    symbol=symbol,
                    timeframe="1m",
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                    timestamp=bar.timestamp,
                ))
        
        except Exception as e:
            logger.error("Failed to fetch today's bars for %s: %s", symbol, e)
    
    # Sort by timestamp
    events.sort(key=lambda e: e.timestamp)
    return events
```

**Implementation note:** The `_fetch_historical_bars` method likely already exists in AlpacaDataService (used for indicator warm-up). Reuse it. If it doesn't exist as a standalone method, extract it from the warm-up logic.

The reconstruction replay happens in `ArgusSystem._reconstruct_strategy_state()` (defined in Component 2 above).

---

## Component 6: Order Manager Reconstruction

### Purpose

If Argus restarts with open positions at the broker, the Order Manager needs to resume managing them.

### Changes to `argus/execution/order_manager.py`

Add a `reconstruct_from_broker()` method:

```python
async def reconstruct_from_broker(self) -> None:
    """Reconstruct managed positions from broker state.
    
    Called at startup to recover any open positions that existed
    before a restart.
    
    1. Query broker for all open positions
    2. Query broker for all open orders
    3. For each position, create a ManagedPosition with:
       - Entry price from broker position data
       - Stop price from any matching stop order
       - T1/T2 inferred from stop orders and limit orders
    4. Subscribe to TickEvents for these symbols
    
    Limitations:
    - Cannot reconstruct exact entry_time (not available from broker)
    - Cannot reconstruct original strategy_id (uses "reconstructed")
    - T1/T2 status is inferred from order types, not exact
    
    These limitations are acceptable because:
    - Time stops use conservative defaults
    - The position will still be managed (stops moved, EOD flattened)
    - Full accuracy requires the system to not crash, which is the goal
    """
    try:
        positions = await self._broker.get_positions()
        
        if not positions:
            logger.info("Order Manager reconstruction: No open positions at broker.")
            return
        
        orders = await self._broker.get_open_orders()
        
        logger.info(
            "Reconstructing %d positions and %d open orders from broker",
            len(positions), len(orders),
        )
        
        # Build order lookup by symbol
        orders_by_symbol: dict[str, list] = {}
        for order in orders:
            symbol = order.symbol if hasattr(order, 'symbol') else ""
            if symbol not in orders_by_symbol:
                orders_by_symbol[symbol] = []
            orders_by_symbol[symbol].append(order)
        
        for pos in positions:
            symbol = pos.symbol if hasattr(pos, 'symbol') else str(pos)
            qty = int(pos.qty) if hasattr(pos, 'qty') else 0
            avg_entry = float(pos.avg_entry_price) if hasattr(pos, 'avg_entry_price') else 0.0
            
            # Find matching stop order
            stop_price = 0.0
            stop_order_id = None
            symbol_orders = orders_by_symbol.get(symbol, [])
            for order in symbol_orders:
                order_type = str(getattr(order, 'type', '')).lower()
                if 'stop' in order_type:
                    stop_price = float(getattr(order, 'stop_price', 0))
                    stop_order_id = str(getattr(order, 'id', ''))
                    break
            
            # Find matching limit order (T1)
            t1_price = 0.0
            t1_order_id = None
            t1_shares = 0
            for order in symbol_orders:
                order_type = str(getattr(order, 'type', '')).lower()
                if 'limit' in order_type:
                    t1_price = float(getattr(order, 'limit_price', 0))
                    t1_order_id = str(getattr(order, 'id', ''))
                    t1_shares = int(getattr(order, 'qty', 0))
                    break
            
            managed = ManagedPosition(
                symbol=symbol,
                strategy_id="reconstructed",
                entry_price=avg_entry,
                entry_time=self._clock.now(),  # Approximation
                shares_total=qty,
                shares_remaining=qty,
                stop_price=stop_price,
                stop_order_id=stop_order_id,
                t1_price=t1_price,
                t1_order_id=t1_order_id,
                t1_shares=t1_shares,
                t1_filled=(t1_order_id is None and t1_shares == 0),
                t2_price=0.0,  # Unknown — position rides to stop or EOD
                high_watermark=avg_entry,
            )
            
            if symbol not in self._managed_positions:
                self._managed_positions[symbol] = []
            self._managed_positions[symbol].append(managed)
            
            logger.info(
                "Reconstructed position: %s %d shares @ %.2f (stop=%.2f)",
                symbol, qty, avg_entry, stop_price,
            )
        
        logger.info("Order Manager reconstruction complete: %d positions recovered",
                     len(positions))
    
    except Exception as e:
        logger.error("Order Manager reconstruction failed: %s", e)
        # Don't crash — system can still manage new positions
```

**Adaptation note:** The attribute access patterns above (e.g., `pos.symbol`, `pos.qty`) depend on what `AlpacaBroker.get_positions()` returns. Check the actual return type and adjust.

---

## Component 7: Structured Logging (`argus/core/logging_config.py`)

### Purpose

Set up structured JSON logging for machine-parseable log analysis during paper trading.

```python
"""Logging configuration for Argus.

Sets up structured JSON logging to file and human-readable logging to console.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path


class JsonFormatter(logging.Formatter):
    """JSON log formatter for machine-parseable logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Include extra fields if present
        for key in ("component", "symbol", "order_id", "position_id", "trade_id"):
            if hasattr(record, key):
                log_data[key] = getattr(record, key)
        
        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter with colors."""
    
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[1;31m", # Bold Red
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET if color else ""
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        return (
            f"{color}{timestamp} [{record.levelname:>8}]{reset} "
            f"{record.name}: {record.getMessage()}"
        )


def setup_logging(
    log_level: str = "INFO",
    log_dir: Path | None = None,
) -> None:
    """Configure logging for the Argus system.
    
    Console: human-readable format, colored.
    File: JSON format, one line per entry.
    
    Args:
        log_level: Root log level (DEBUG, INFO, WARNING, ERROR).
        log_dir: Directory for log files. Default: logs/
    """
    if log_dir is None:
        log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Clear existing handlers
    root.handlers.clear()
    
    # Console handler — human-readable
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(ConsoleFormatter())
    console.setLevel(logging.INFO)
    root.addHandler(console)
    
    # File handler — JSON structured
    log_file = log_dir / f"argus_{datetime.now().strftime('%Y%m%d')}.jsonl"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(JsonFormatter())
    file_handler.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("alpaca").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    
    logging.info("Logging initialized. File: %s", log_file)
```

---

## Component 8: Configuration Updates

### Add `HealthConfig` to `argus/core/config.py`

```python
class HealthConfig(BaseModel):
    """Health monitoring configuration."""
    heartbeat_interval_seconds: int = Field(default=60, ge=10, le=300)
    heartbeat_url: str = ""           # Healthchecks.io ping URL or similar
    alert_webhook_url: str = ""       # Discord webhook, Slack webhook, etc.
    daily_check_enabled: bool = True
    weekly_reconciliation_enabled: bool = True
```

### Update `SystemConfig`

```python
class SystemConfig(BaseModel):
    """Global system settings."""
    timezone: str = "America/New_York"
    market_open: str = "09:30"
    market_close: str = "16:00"
    log_level: LogLevel = LogLevel.INFO
    heartbeat_interval_seconds: int = 60    # KEEP for backward compatibility
    data_dir: str = "data"
    health: HealthConfig = Field(default_factory=HealthConfig)
```

### Update `config/system.yaml`

```yaml
timezone: "America/New_York"
market_open: "09:30"
market_close: "16:00"
log_level: "INFO"
heartbeat_interval_seconds: 60
data_dir: "data"

health:
  heartbeat_interval_seconds: 60
  heartbeat_url: ""           # Set to Healthchecks.io URL when ready
  alert_webhook_url: ""       # Set to Discord webhook URL when ready
  daily_check_enabled: true
  weekly_reconciliation_enabled: true
```

---

## New Files Created This Sprint

```
argus/core/health.py                    # NEW — HealthMonitor
argus/core/logging_config.py            # NEW — Structured logging setup
argus/main.py                           # NEW — System entry point
tests/core/test_health.py              # NEW — HealthMonitor tests
tests/test_main.py                     # NEW — System startup/shutdown tests
tests/test_integration_sprint5.py      # NEW — Full system integration tests
```

**Modified files:**
```
argus/core/config.py                   # ADD HealthConfig, update SystemConfig
argus/data/alpaca_data_service.py      # ADD market hours check to stale monitor, 
                                       #     fetch_todays_bars(), health_monitor param
argus/execution/order_manager.py       # ADD reconstruct_from_broker()
config/system.yaml                     # ADD health section
```

---

## Test Plan

### Test File: `tests/core/test_health.py`

Target: ~20 tests.

**Component registry (5):**
1. `test_update_component_stores_health` — Update → retrieve → correct
2. `test_overall_status_healthy_when_all_healthy` — All components healthy → HEALTHY
3. `test_overall_status_degraded_when_any_degraded` — One degraded → DEGRADED
4. `test_overall_status_unhealthy_when_any_unhealthy` — One unhealthy → UNHEALTHY
5. `test_overall_status_starting_when_empty` — No components → STARTING

**Heartbeat (4):**
6. `test_heartbeat_publishes_event` — HeartbeatEvent published to event bus
7. `test_heartbeat_sends_http_post` — Webhook called with correct payload (mock aiohttp)
8. `test_heartbeat_handles_http_failure` — HTTP error → logged, no crash
9. `test_heartbeat_skips_when_no_url` — Empty URL → no HTTP call

**Alerts (4):**
10. `test_alert_sends_discord_format` — Discord webhook URL → Discord payload format
11. `test_alert_sends_generic_format` — Non-Discord URL → generic JSON payload
12. `test_unhealthy_transition_triggers_alert` — HEALTHY → UNHEALTHY → alert sent
13. `test_circuit_breaker_triggers_alert` — CircuitBreakerEvent → critical alert

**Integrity checks (4):**
14. `test_daily_check_finds_unprotected_position` — Position without stop → alert
15. `test_daily_check_all_positions_have_stops` — All covered → OK logged
16. `test_daily_check_no_positions_is_ok` — No positions → OK logged
17. `test_daily_check_skipped_without_broker` — No broker → warning logged

**Edge cases (3):**
18. `test_start_and_stop_lifecycle` — Start → tasks created. Stop → tasks cancelled.
19. `test_multiple_unhealthy_only_one_alert_each` — Same component UNHEALTHY twice → only one alert
20. `test_component_recovery_clears_status` — UNHEALTHY → HEALTHY → status updated

### Test File: `tests/test_main.py`

Target: ~8 tests. These test the ArgusSystem wiring, NOT the individual components.

**All components are mocked — no real broker connections, no real data.**

1. `test_system_starts_in_correct_order` — Verify start() calls components in dependency order (use mocks with call order tracking)
2. `test_system_shuts_down_in_reverse_order` — Verify shutdown() calls components in reverse order
3. `test_system_handles_startup_failure_gracefully` — Broker connect fails → error logged, shutdown called
4. `test_signal_handlers_request_shutdown` — SIGINT simulation → shutdown_event set
5. `test_dry_run_skips_data_streams` — --dry-run → data_service.start() not called
6. `test_no_symbols_logs_warning` — Scanner returns empty → warning logged, system runs
7. `test_config_loaded_from_directory` — Config dir → load_config called with correct path
8. `test_dotenv_loaded_before_components` — Verify dotenv loaded before broker instantiation

### Test File: `tests/test_integration_sprint5.py`

Target: ~5 integration tests. All external services mocked.

1. `test_full_system_startup_shutdown` — Create ArgusSystem with all mocked deps → start → verify all healthy → shutdown → verify all stopped
2. `test_heartbeat_fires_during_runtime` — Start system → advance time → verify HeartbeatEvent published
3. `test_circuit_breaker_triggers_alert_and_flatten` — Publish CircuitBreakerEvent → verify alert sent AND emergency flatten called
4. `test_stale_data_during_market_hours_triggers_degraded` — Simulate no data for 30+ seconds during market hours → DataService status DEGRADED
5. `test_stale_data_outside_market_hours_no_alert` — Simulate no data outside market hours → no alert triggered

### Test File: Additions to existing test files

**`tests/execution/test_order_manager.py`** — Add 3 tests:
26. `test_reconstruct_from_broker_recovers_positions` — Mock broker with 2 open positions + orders → ManagedPositions created
27. `test_reconstruct_from_broker_no_positions` — Empty broker → no positions, no crash
28. `test_reconstruct_from_broker_handles_error` — Broker raises → error logged, no crash

**`tests/data/test_data_service.py`** — Add 2 tests:
(numbering continues from existing tests)
- `test_stale_data_monitor_ignores_outside_market_hours` — Clock set to 8:00 AM ET → no stale alert
- `test_stale_data_monitor_alerts_during_market_hours` — Clock set to 10:00 AM ET, no data → alert fires

Total new tests: ~38 (20 health + 8 main + 5 integration + 3 order manager + 2 data service)
**Target end state: ~358 tests (320 + 38)**

---

## Build Order

1. **Structured logging** (`argus/core/logging_config.py`) — No dependencies, needed by everything
2. **HealthConfig** in `argus/core/config.py` + update `config/system.yaml`
3. **HealthMonitor** (`argus/core/health.py`) + tests
4. **Stale data market hours fix** in `argus/data/alpaca_data_service.py` + tests
5. **`fetch_todays_bars()`** in `argus/data/alpaca_data_service.py`
6. **`reconstruct_from_broker()`** in `argus/execution/order_manager.py` + tests
7. **System entry point** (`argus/main.py`) + tests
8. **Integration tests** (`tests/test_integration_sprint5.py`)
9. **Full test suite pass + ruff clean**
10. **Commit and push**

---

## Decisions In Effect (Do Not Relitigate)

| ID | Rule |
|----|------|
| DEC-011 | Long only for V1 |
| DEC-025 | Event Bus: FIFO per subscriber, monotonic sequence numbers |
| DEC-027 | Approve-with-modification (reduce shares, tighten targets, never widen stops) |
| DEC-028 | Daily-stateful, session-stateless |
| DEC-029 | Event Bus is sole streaming mechanism |
| DEC-030 | Order Manager: tick-driven + 5s poll + EOD flatten |
| DEC-032 | Pydantic BaseModel for all config |
| DEC-033 | Type-only Event Bus subscription |
| DEC-034 | aiosqlite, DatabaseManager owns connection, TradeLogger sole persistence |
| DEC-039/MD-4a-3 | alpaca-py, not alpaca-trade-api |
| DEC-039/MD-4a-5 | Clock protocol: SystemClock + FixedClock |
| DEC-040 | Stop management: cancel and resubmit |
| DEC-041 | EOD flatten in fallback poll loop |
| DEC-042 | TradeLogger called directly by Order Manager |
| DEC-043 | AlpacaScanner: static universe from config |

---

## Success Criteria

Sprint 5 is done when:
- [ ] `argus/main.py` starts the full system and connects all components
- [ ] `python -m argus.main --dry-run` starts, connects to broker, runs scanner, reports status, and exits cleanly on Ctrl+C
- [ ] HealthMonitor tracks component status and sends heartbeat pings
- [ ] Alert webhook fires on circuit breaker and unhealthy transitions
- [ ] Stale data monitor only alerts during market hours (RSK-015 fixed)
- [ ] Order Manager reconstructs open positions from broker on startup
- [ ] Strategy state reconstruction fetches today's bars and replays them
- [ ] Graceful shutdown stops all components in correct order
- [ ] Structured logging writes JSON to file and human-readable to console
- [ ] All tests pass (target: ~358, up from 320)
- [ ] Ruff clean
- [ ] Committed and pushed

### Paper Trading Validation (Post-Sprint, Done by User)

After the code is complete and committed:
1. Set up Healthchecks.io account and configure heartbeat URL
2. Set up Discord webhook and configure alert URL
3. Run `python -m argus.main` during market hours on 3+ different trading days
4. Monitor logs and Discord for any issues
5. After each day, verify:
   - Trades logged to database match what appeared in Alpaca dashboard
   - EOD flatten fired at the right time
   - No crashes or unhandled exceptions in logs
   - Heartbeat pings were consistent (check Healthchecks.io dashboard)

---

## What This Sprint Does NOT Include

- Real notifications (Telegram, email, push) — Phase 6
- Orchestrator — Phase 4
- Multiple strategies — Phase 4+
- Shadow system — Phase 3+
- UI / Command Center — Phase 5
- Live (real money) trading — Phase 3
- APScheduler integration — deferred, fallback poll is sufficient
- Full weekly reconciliation logic — placeholder in Sprint 5, full implementation when broker API response format is better understood from paper trading

---

## Documentation Update Protocol

At the END of this sprint, output a "Docs Status" summary per CLAUDE.md rules. Expect these updates:

- **CLAUDE.md:** Update Current State to "Sprint 5 complete / Phase 1 complete". Add aiohttp to dependencies. Add HealthMonitor to components list.
- **07_PHASE1_SPRINT_PLAN.md:** Mark Sprint 5 ✅ Complete with test count. Add Phase 1 completion date.
- **05_DECISION_LOG.md:** Add DEC-044 (Sprint 5 micro-decisions: MD-5-1 through MD-5-6).
- **02_PROJECT_KNOWLEDGE.md (project instructions):** Update phase status to "Phase 1 COMPLETE."
- **06_RISK_REGISTER.md:** Close RSK-015 (stale data false positives). Note any new risks discovered.
- **03_ARCHITECTURE.md:** Add HealthMonitor to Module Specifications. Add `main.py` startup sequence.

---

*End of Sprint 5 Implementation Spec*
