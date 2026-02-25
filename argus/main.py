"""Argus Trading System — Main Entry Point.

Wires all components together and runs the event loop.

Usage:
    python -m argus.main                    # Default: config/ directory
    python -m argus.main --config /path/to  # Custom config directory
    python -m argus.main --paper            # Force paper trading (default)
    python -m argus.main --dry-run          # Start, connect, but don't trade
    python -m argus.main --no-api           # Disable Command Center API server
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import time
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv

# Load .env BEFORE any component imports that read env vars
load_dotenv()

# fmt: off
# ruff: noqa: E402, I001
from argus.analytics.trade_logger import TradeLogger
from argus.core.clock import SystemClock
from argus.core.config import (
    AlpacaScannerConfig,
    BrokerSource,
    DataServiceConfig,
    DataSource,
    OrchestratorConfig,
    load_config,
    load_orb_config,
    load_orb_scalp_config,
    load_vwap_reclaim_config,
    load_yaml_file,
)
from argus.core.event_bus import EventBus
from argus.core.events import CandleEvent
from argus.core.health import ComponentStatus, HealthMonitor
from argus.core.logging_config import setup_logging
from argus.core.orchestrator import Orchestrator
from argus.core.risk_manager import RiskManager
from argus.data.alpaca_data_service import AlpacaDataService
from argus.data.alpaca_scanner import AlpacaScanner
from argus.data.databento_data_service import DatabentoDataService
from argus.data.databento_scanner import DatabentoScanner, DatabentoScannerConfig
from argus.db.manager import DatabaseManager
from argus.execution.alpaca_broker import AlpacaBroker
from argus.execution.order_manager import OrderManager
from argus.strategies.orb_breakout import OrbBreakoutStrategy
from argus.strategies.orb_scalp import OrbScalpStrategy
from argus.strategies.vwap_reclaim import VwapReclaimStrategy
# fmt: on

if TYPE_CHECKING:
    from argus.core.clock import Clock
    from argus.data.scanner import Scanner
    from argus.data.service import DataService
    from argus.execution.broker import Broker

logger = logging.getLogger(__name__)


class ArgusSystem:
    """Top-level system container. Owns all components and their lifecycle."""

    def __init__(self, config_dir: Path, dry_run: bool = False, enable_api: bool = True) -> None:
        """Initialize the Argus system.

        Args:
            config_dir: Path to configuration directory.
            dry_run: If True, connect but don't stream data or trade.
            enable_api: If True, start the Command Center API server.
        """
        self._config_dir = config_dir
        self._dry_run = dry_run
        self._enable_api = enable_api
        self._shutdown_event = asyncio.Event()

        # Components (initialized in start())
        self._clock: Clock | None = None
        self._event_bus: EventBus | None = None
        self._db: DatabaseManager | None = None
        self._trade_logger: TradeLogger | None = None
        self._broker: Broker | None = None
        self._data_service: DataService | None = None
        self._scanner: Scanner | None = None
        self._risk_manager: RiskManager | None = None
        self._order_manager: OrderManager | None = None
        self._health_monitor: HealthMonitor | None = None
        self._orchestrator: Orchestrator | None = None
        self._api_task: asyncio.Task[None] | None = None
        self._config: object | None = None  # Store config for API access

    async def start(self) -> None:
        """Initialize and start all components in dependency order.

        Order matters:
        1. Config + Clock + EventBus (no dependencies)
        2. Database + TradeLogger (needs config)
        3. Broker (needs config, event_bus)
        4. HealthMonitor (needs event_bus, clock, broker)
        5. RiskManager (needs event_bus, clock, config, broker)
        6. DataService (needs config, event_bus, clock)
        7. Scanner (needs config)
        8. Strategy (needs config, clock) — instance created, NOT activated
        9. Orchestrator (needs event_bus, clock, trade_logger, broker, data_service)
        10. OrderManager (needs event_bus, broker, clock, config, trade_logger)
        11. Start data service streaming
        12. API Server (optional, needs all components)
        """
        logger.info("=" * 60)
        logger.info("ARGUS TRADING SYSTEM — STARTING")
        logger.info("=" * 60)

        # --- Phase 1: Foundation ---
        logger.info("[1/12] Loading configuration...")
        config = load_config(self._config_dir)
        self._config = config

        self._clock = SystemClock()
        self._event_bus = EventBus()

        # --- Phase 2: Database ---
        logger.info("[2/12] Initializing database...")
        db_path = Path(config.system.data_dir) / "argus.db"
        self._db = DatabaseManager(db_path)
        await self._db.initialize()
        self._trade_logger = TradeLogger(self._db)

        # --- Phase 3: Broker ---
        logger.info("[3/12] Connecting to broker...")
        if config.system.broker_source == BrokerSource.IBKR:
            from argus.execution.ibkr_broker import IBKRBroker

            logger.info("Using IBKR broker (production execution)")
            self._broker = IBKRBroker(
                config=config.system.ibkr,
                event_bus=self._event_bus,
            )
        elif config.system.broker_source == BrokerSource.ALPACA:
            logger.info("Using Alpaca broker (paper/incubator)")
            self._broker = AlpacaBroker(
                event_bus=self._event_bus,
                config=config.broker.alpaca,
            )
        else:
            # BrokerSource.SIMULATED — default for backtesting
            from argus.execution.simulated_broker import SimulatedBroker

            logger.info("Using Simulated broker (backtesting)")
            self._broker = SimulatedBroker()
        await self._broker.connect()

        account = await self._broker.get_account()
        logger.info("Broker connected. Account equity: %s", account.equity if account else "N/A")

        # --- Phase 4: Health Monitor ---
        logger.info("[4/12] Starting health monitor...")
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
        logger.info("[5/12] Initializing risk manager...")
        self._risk_manager = RiskManager(
            config=config.risk,
            broker=self._broker,
            event_bus=self._event_bus,
            clock=self._clock,
        )
        await self._risk_manager.initialize()
        # Reconstruct state (weekly P&L, daily P&L) from trade log
        if hasattr(self._risk_manager, "reconstruct_state"):
            await self._risk_manager.reconstruct_state(self._trade_logger)
        self._health_monitor.update_component("risk_manager", ComponentStatus.HEALTHY)

        # --- Phase 6: Data Service ---
        logger.info("[6/12] Initializing data service...")
        data_config = DataServiceConfig()  # Use defaults

        if config.system.data_source == DataSource.DATABENTO:
            logger.info("Using Databento data service")
            self._data_service = DatabentoDataService(
                event_bus=self._event_bus,
                config=config.broker.databento,
                clock=self._clock,
                health_monitor=self._health_monitor,
            )
        else:
            logger.info("Using Alpaca data service")
            self._data_service = AlpacaDataService(
                event_bus=self._event_bus,
                config=config.broker.alpaca,
                data_config=data_config,
                clock=self._clock,
                health_monitor=self._health_monitor,
            )
        self._health_monitor.update_component("data_service", ComponentStatus.STARTING)

        # --- Phase 7: Scanner ---
        logger.info("[7/12] Running pre-market scan...")
        scanner_yaml = load_yaml_file(self._config_dir / "scanner.yaml")

        if config.system.data_source == DataSource.DATABENTO:
            logger.info("Using Databento scanner")
            databento_scanner_data = scanner_yaml.get("databento_scanner", {})
            db_scanner_config = DatabentoScannerConfig(**databento_scanner_data)
            self._scanner = DatabentoScanner(
                config=db_scanner_config,
                databento_config=config.broker.databento,
            )
        else:
            logger.info("Using Alpaca scanner")
            alpaca_scanner_data = scanner_yaml.get("alpaca_scanner", {})
            scanner_config = AlpacaScannerConfig(**alpaca_scanner_data)
            self._scanner = AlpacaScanner(
                config=scanner_config,
                alpaca_config=config.broker.alpaca,
            )
        await self._scanner.start()

        # Scan with empty criteria list (use scanner defaults)
        watchlist = await self._scanner.scan([])
        symbols = [item.symbol for item in watchlist]

        if not symbols:
            # Fall back to static symbols if scan returns nothing
            symbols = scanner_yaml.get("static_symbols", [])
            logger.warning("Scanner returned no symbols. Using static list: %s", symbols)
            self._health_monitor.update_component(
                "scanner",
                ComponentStatus.DEGRADED,
                message="No symbols passed filters, using static list",
            )
        else:
            logger.info("Scanner found %d symbols: %s", len(symbols), symbols)
            self._health_monitor.update_component(
                "scanner", ComponentStatus.HEALTHY, message=f"{len(symbols)} symbols"
            )

        # --- Phase 8: Strategy Instances ---
        # Create strategy instances but do NOT activate (Orchestrator handles activation)
        logger.info("[8/12] Creating strategy instances...")
        strategies_created: list[str] = []

        # ORB Breakout
        orb_config = load_orb_config(self._config_dir / "strategies" / "orb_breakout.yaml")
        orb_strategy = OrbBreakoutStrategy(
            config=orb_config,
            data_service=self._data_service,
            clock=self._clock,
        )
        orb_strategy.set_watchlist(symbols)
        strategies_created.append("OrbBreakout")

        # ORB Scalp (optional — only if config file exists)
        scalp_strategy: OrbScalpStrategy | None = None
        scalp_yaml = self._config_dir / "strategies" / "orb_scalp.yaml"
        if scalp_yaml.exists():
            scalp_config = load_orb_scalp_config(scalp_yaml)
            scalp_strategy = OrbScalpStrategy(
                config=scalp_config,
                data_service=self._data_service,
                clock=self._clock,
            )
            scalp_strategy.set_watchlist(symbols)
            strategies_created.append("OrbScalp")

        # VWAP Reclaim (optional — only if config file exists)
        vwap_reclaim_strategy: VwapReclaimStrategy | None = None
        vwap_yaml = self._config_dir / "strategies" / "vwap_reclaim.yaml"
        if vwap_yaml.exists():
            vwap_config = load_vwap_reclaim_config(vwap_yaml)
            vwap_reclaim_strategy = VwapReclaimStrategy(
                config=vwap_config,
                data_service=self._data_service,
                clock=self._clock,
            )
            vwap_reclaim_strategy.set_watchlist(symbols)
            strategies_created.append("VwapReclaim")

        # Note: is_active and allocated_capital set by Orchestrator in Phase 9
        self._health_monitor.update_component(
            "strategy",
            ComponentStatus.STARTING,
            message=f"{len(strategies_created)} strategies created",
        )

        # --- Phase 9: Orchestrator ---
        logger.info("[9/12] Initializing orchestrator...")
        orchestrator_yaml = load_yaml_file(self._config_dir / "orchestrator.yaml")
        orchestrator_config = OrchestratorConfig(**orchestrator_yaml)
        self._orchestrator = Orchestrator(
            config=orchestrator_config,
            event_bus=self._event_bus,
            clock=self._clock,
            trade_logger=self._trade_logger,
            broker=self._broker,
            data_service=self._data_service,
        )

        # Register all strategies
        self._orchestrator.register_strategy(orb_strategy)
        if scalp_strategy is not None:
            self._orchestrator.register_strategy(scalp_strategy)
        if vwap_reclaim_strategy is not None:
            self._orchestrator.register_strategy(vwap_reclaim_strategy)

        await self._orchestrator.start()

        # Run pre-market routine (sets regime, allocations, activates strategies)
        # If mid-day restart, strategies reconstruct their own state
        await self._orchestrator.run_pre_market()
        self._health_monitor.update_component("orchestrator", ComponentStatus.HEALTHY)

        # Update health status based on multi-strategy state
        strategies = self._orchestrator.get_strategies()
        active_count = sum(1 for s in strategies.values() if s.is_active)
        total_count = len(strategies)
        self._health_monitor.update_component(
            "strategy",
            ComponentStatus.HEALTHY if active_count > 0 else ComponentStatus.DEGRADED,
            message=f"{active_count}/{total_count} strategies active",
        )

        # Per-strategy health components
        if vwap_reclaim_strategy is not None:
            self._health_monitor.update_component(
                "strategy_vwap_reclaim", ComponentStatus.HEALTHY, "VWAP Reclaim running"
            )

        # --- Phase 10: Order Manager ---
        logger.info("[10/12] Starting order manager...")
        order_manager_yaml = load_yaml_file(self._config_dir / "order_manager.yaml")
        from argus.core.config import OrderManagerConfig

        order_manager_config = OrderManagerConfig(**order_manager_yaml)

        self._order_manager = OrderManager(
            event_bus=self._event_bus,
            broker=self._broker,
            clock=self._clock,
            config=order_manager_config,
            trade_logger=self._trade_logger,
        )
        await self._order_manager.start()
        # Reconstruct open positions from broker
        await self._order_manager.reconstruct_from_broker()
        self._health_monitor.update_component("order_manager", ComponentStatus.HEALTHY)

        # Wire Risk Manager to Order Manager for cross-strategy checks
        self._risk_manager.set_order_manager(self._order_manager)

        # --- Phase 10.5: CandleEvent Routing ---
        # Subscribe to CandleEvents and route to active strategies (DEC-125)
        self._event_bus.subscribe(CandleEvent, self._on_candle_for_strategies)

        # --- Phase 11: Start streaming ---
        logger.info("[11/12] Starting data streams...")
        if symbols and not self._dry_run:
            await self._data_service.start(symbols=symbols, timeframes=["1m"])
            self._health_monitor.update_component(
                "data_service", ComponentStatus.HEALTHY, message=f"Streaming {len(symbols)} symbols"
            )
        elif self._dry_run:
            logger.info("DRY RUN: Data streams not started.")
            self._health_monitor.update_component(
                "data_service", ComponentStatus.DEGRADED, message="Dry run — no streaming"
            )

        # --- Phase 12: API Server (optional) ---
        logger.info("[12/12] Starting API server...")
        if self._enable_api and config.system.api.enabled:
            # Check for JWT secret
            jwt_secret_env = config.system.api.jwt_secret_env
            if not os.environ.get(jwt_secret_env):
                logger.warning(
                    "API disabled: JWT secret not configured (set %s env var)", jwt_secret_env
                )
                self._health_monitor.update_component(
                    "api_server",
                    ComponentStatus.DEGRADED,
                    message="JWT secret not configured",
                )
            else:
                from argus.api.dependencies import AppState
                from argus.api.server import create_app, run_server
                from argus.api.websocket import get_bridge

                app_state = AppState(
                    event_bus=self._event_bus,
                    trade_logger=self._trade_logger,
                    broker=self._broker,
                    health_monitor=self._health_monitor,
                    risk_manager=self._risk_manager,
                    order_manager=self._order_manager,
                    data_service=self._data_service,
                    orchestrator=self._orchestrator,
                    strategies=self._orchestrator.get_strategies(),
                    clock=self._clock,
                    config=config.system,
                    start_time=time.time(),
                )
                api_app = create_app(app_state)

                # Start WebSocket bridge
                ws_bridge = get_bridge()
                ws_bridge.start(self._event_bus, self._order_manager, config.system.api)

                # Start API server
                self._api_task = await run_server(
                    api_app, config.system.api.host, config.system.api.port
                )
                logger.info(
                    "API server started on %s:%d",
                    config.system.api.host,
                    config.system.api.port,
                )
                self._health_monitor.update_component(
                    "api_server",
                    ComponentStatus.HEALTHY,
                    message=f"http://{config.system.api.host}:{config.system.api.port}",
                )
        else:
            logger.info("API server disabled by configuration or --no-api flag")
            self._health_monitor.update_component(
                "api_server", ComponentStatus.STOPPED, message="Disabled"
            )

        logger.info("=" * 60)
        logger.info("ARGUS TRADING SYSTEM — RUNNING")
        if self._dry_run:
            logger.info("MODE: DRY RUN (no trades will be placed)")
        logger.info("Watching %d symbols", len(symbols))
        if self._api_task:
            logger.info("API: http://%s:%d", config.system.api.host, config.system.api.port)
        logger.info("=" * 60)

        # Send startup alert
        mode = "DRY RUN" if self._dry_run else "PAPER TRADING"
        await self._health_monitor.send_warning_alert(
            title="Argus Started",
            body=f"Watching {len(symbols)} symbols. Mode: {mode}",
        )

    async def _on_candle_for_strategies(self, event: CandleEvent) -> None:
        """Route CandleEvents to active strategies (DEC-125).

        Called for every CandleEvent. Routes to strategies that are:
        1. Active (is_active = True)
        2. Tracking the symbol (symbol in watchlist)

        If a strategy emits a SignalEvent, it's sent through the Risk Manager
        for approval and the result is published to the Event Bus.

        Args:
            event: The candle event to route.
        """
        if self._orchestrator is None or self._risk_manager is None:
            return

        for strategy in self._orchestrator.get_strategies().values():
            if not strategy.is_active:
                continue
            if event.symbol not in strategy.watchlist:
                continue

            signal = await strategy.on_candle(event)
            if signal is not None:
                result = await self._risk_manager.evaluate_signal(signal)
                await self._event_bus.publish(result)

    async def _reconstruct_strategy_state(self, symbols: list[str]) -> None:
        """Reconstruct strategy state if restarting mid-day.

        1. Check if we're within market hours.
        2. If yes, fetch today's historical 1m bars for all symbols.
        3. Replay them through all strategies to rebuild opening ranges.
        4. If fetch fails, log warning and continue.

        Args:
            symbols: List of symbols to reconstruct.
        """
        from datetime import time as dt_time
        from zoneinfo import ZoneInfo

        if not self._clock or not self._data_service or not self._orchestrator:
            return

        strategies = self._orchestrator.get_strategies()
        if not strategies:
            return

        et_tz = ZoneInfo("America/New_York")
        now = self._clock.now()
        now_et = now.replace(tzinfo=et_tz) if now.tzinfo is None else now.astimezone(et_tz)

        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)

        if not (market_open <= now_et.time() <= market_close):
            logger.info("Outside market hours — no strategy reconstruction needed")
            return

        # Only reconstruct if it's past the OR window (9:45+ for 15min window)
        if now_et.time() < dt_time(9, 45):
            logger.info("Before OR window ends — no reconstruction needed")
            return

        logger.info("Mid-day start detected. Reconstructing %d strategies...", len(strategies))

        try:
            if hasattr(self._data_service, "fetch_todays_bars"):
                todays_bars = await self._data_service.fetch_todays_bars(symbols)

                if todays_bars:
                    # Replay bars through all strategies
                    for bar in todays_bars:
                        for strategy in strategies.values():
                            await strategy.on_candle(bar)

                    logger.info(
                        "Strategy state reconstructed from %d historical bars for %d strategies",
                        len(todays_bars),
                        len(strategies),
                    )
                else:
                    logger.warning("No historical bars available — strategies starting fresh")
            else:
                logger.warning("DataService doesn't support fetch_todays_bars — skipping")

        except Exception as e:
            logger.error("Strategy reconstruction failed: %s. Continuing anyway.", e)
            if self._health_monitor:
                self._health_monitor.update_component(
                    "strategy",
                    ComponentStatus.DEGRADED,
                    message=f"Reconstruction failed: {e}",
                )

    async def shutdown(self) -> None:
        """Graceful shutdown sequence.

        Order matters (reverse of startup):
        0. Stop API server
        1. Stop scanner
        2. Stop data streams
        3. Stop order manager
        4. Stop orchestrator
        5. Stop health monitor
        6. Close database
        7. Close broker connection
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

        # 0. Stop API server
        if self._api_task:
            import contextlib

            logger.info("Stopping API server...")
            self._api_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._api_task
            from argus.api.websocket import get_bridge

            get_bridge().stop()
            logger.info("API server stopped")

        # 1. Stop scanner
        if self._scanner:
            logger.info("Stopping scanner...")
            await self._scanner.stop()

        # 2. Stop data streams
        if self._data_service:
            logger.info("Stopping data service...")
            await self._data_service.stop()

        # 3. Stop order manager
        if self._order_manager:
            logger.info("Stopping order manager...")
            await self._order_manager.stop()

        # 4. Stop orchestrator
        if self._orchestrator:
            logger.info("Stopping orchestrator...")
            await self._orchestrator.stop()

        # 5. Stop health monitor
        if self._health_monitor:
            logger.info("Stopping health monitor...")
            await self._health_monitor.stop()

        # 6. Close database
        if self._db:
            logger.info("Closing database...")
            await self._db.close()

        # 7. Close broker
        if self._broker:
            logger.info("Disconnecting broker...")
            if hasattr(self._broker, "disconnect"):
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
        "--config",
        type=Path,
        default=Path("config"),
        help="Path to configuration directory (default: config/)",
    )
    parser.add_argument(
        "--paper",
        action="store_true",
        default=True,
        help="Use paper trading (default: True)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Start and connect but don't stream data or trade",
    )
    parser.add_argument(
        "--no-api",
        action="store_true",
        default=False,
        help="Disable the Command Center API server",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point. Sets up signal handlers and runs the system."""
    args = parse_args()

    # Set up logging first
    setup_logging(log_level="INFO")

    logger.info("Argus starting with config from: %s", args.config)

    system = ArgusSystem(
        config_dir=args.config,
        dry_run=args.dry_run,
        enable_api=not args.no_api,
    )

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
