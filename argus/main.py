"""Argus Trading System — Main Entry Point.

Wires all components together and runs the event loop.

Usage:
    python -m argus.main                    # Default: config/ directory
    python -m argus.main --config /path/to  # Custom config directory
    python -m argus.main --paper            # Force paper trading (default)
    python -m argus.main --dry-run          # Start, connect, but don't trade
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
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
    DataServiceConfig,
    DataSource,
    load_config,
    load_orb_config,
    load_yaml_file,
)
from argus.core.event_bus import EventBus
from argus.core.health import ComponentStatus, HealthMonitor
from argus.core.logging_config import setup_logging
from argus.core.risk_manager import RiskManager
from argus.data.alpaca_data_service import AlpacaDataService
from argus.data.alpaca_scanner import AlpacaScanner
from argus.data.databento_data_service import DatabentoDataService
from argus.data.databento_scanner import DatabentoScanner, DatabentoScannerConfig
from argus.db.manager import DatabaseManager
from argus.execution.alpaca_broker import AlpacaBroker
from argus.execution.order_manager import OrderManager
from argus.strategies.orb_breakout import OrbBreakoutStrategy
# fmt: on

if TYPE_CHECKING:
    from argus.core.clock import Clock
    from argus.data.scanner import Scanner
    from argus.data.service import DataService

logger = logging.getLogger(__name__)


class ArgusSystem:
    """Top-level system container. Owns all components and their lifecycle."""

    def __init__(self, config_dir: Path, dry_run: bool = False) -> None:
        """Initialize the Argus system.

        Args:
            config_dir: Path to configuration directory.
            dry_run: If True, connect but don't stream data or trade.
        """
        self._config_dir = config_dir
        self._dry_run = dry_run
        self._shutdown_event = asyncio.Event()

        # Components (initialized in start())
        self._clock: Clock | None = None
        self._event_bus: EventBus | None = None
        self._db: DatabaseManager | None = None
        self._trade_logger: TradeLogger | None = None
        self._broker: AlpacaBroker | None = None
        self._data_service: DataService | None = None
        self._scanner: Scanner | None = None
        self._risk_manager: RiskManager | None = None
        self._strategy: OrbBreakoutStrategy | None = None
        self._order_manager: OrderManager | None = None
        self._health_monitor: HealthMonitor | None = None

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
        8. Strategy (needs config, clock)
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
        db_path = Path(config.system.data_dir) / "argus.db"
        self._db = DatabaseManager(db_path)
        await self._db.initialize()
        self._trade_logger = TradeLogger(self._db)

        # --- Phase 3: Broker ---
        logger.info("[3/10] Connecting to broker...")
        self._broker = AlpacaBroker(
            event_bus=self._event_bus,
            config=config.broker.alpaca,
        )
        await self._broker.connect()

        account = await self._broker.get_account()
        logger.info("Broker connected. Account equity: %s", account.equity if account else "N/A")

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
        logger.info("[6/10] Initializing data service...")
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
        logger.info("[7/10] Running pre-market scan...")
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
                "scanner", ComponentStatus.DEGRADED,
                message="No symbols passed filters, using static list"
            )
        else:
            logger.info("Scanner found %d symbols: %s", len(symbols), symbols)
            self._health_monitor.update_component(
                "scanner", ComponentStatus.HEALTHY,
                message=f"{len(symbols)} symbols"
            )

        # --- Phase 8: Strategy ---
        logger.info("[8/10] Initializing strategy...")
        strategy_config = load_orb_config(
            self._config_dir / "strategies" / "orb_breakout.yaml"
        )
        self._strategy = OrbBreakoutStrategy(
            config=strategy_config,
            data_service=self._data_service,
            clock=self._clock,
        )

        # Subscribe strategy to candle events
        # (Strategy handles its own event subscriptions via data_service)

        # If mid-day restart, attempt state reconstruction
        await self._reconstruct_strategy_state(symbols)
        self._health_monitor.update_component(
            "strategy", ComponentStatus.HEALTHY,
            message="OrbBreakout active"
        )

        # --- Phase 9: Order Manager ---
        logger.info("[9/10] Starting order manager...")
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

        # --- Phase 10: Start streaming ---
        logger.info("[10/10] Starting data streams...")
        if symbols and not self._dry_run:
            await self._data_service.start(symbols=symbols, timeframes=["1m"])
            self._health_monitor.update_component(
                "data_service", ComponentStatus.HEALTHY,
                message=f"Streaming {len(symbols)} symbols"
            )
        elif self._dry_run:
            logger.info("DRY RUN: Data streams not started.")
            self._health_monitor.update_component(
                "data_service", ComponentStatus.DEGRADED,
                message="Dry run — no streaming"
            )

        logger.info("=" * 60)
        logger.info("ARGUS TRADING SYSTEM — RUNNING")
        if self._dry_run:
            logger.info("MODE: DRY RUN (no trades will be placed)")
        logger.info("Watching %d symbols", len(symbols))
        logger.info("=" * 60)

        # Send startup alert
        mode = "DRY RUN" if self._dry_run else "PAPER TRADING"
        await self._health_monitor.send_warning_alert(
            title="Argus Started",
            body=f"Watching {len(symbols)} symbols. Mode: {mode}",
        )

    async def _reconstruct_strategy_state(self, symbols: list[str]) -> None:
        """Reconstruct strategy state if restarting mid-day.

        1. Check if we're within market hours.
        2. If yes, fetch today's historical 1m bars for all symbols.
        3. Replay them through the strategy to rebuild opening range.
        4. If fetch fails, log warning and continue.

        Args:
            symbols: List of symbols to reconstruct.
        """
        from datetime import time as dt_time
        from zoneinfo import ZoneInfo

        if not self._clock or not self._data_service or not self._strategy:
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

        logger.info("Mid-day start detected. Reconstructing strategy state...")

        try:
            if hasattr(self._data_service, "fetch_todays_bars"):
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
                logger.warning(
                    "DataService doesn't support fetch_todays_bars — skipping"
                )

        except Exception as e:
            logger.error("Strategy reconstruction failed: %s. Continuing anyway.", e)
            if self._health_monitor:
                self._health_monitor.update_component(
                    "strategy", ComponentStatus.DEGRADED,
                    message=f"Reconstruction failed: {e}",
                )

    async def shutdown(self) -> None:
        """Graceful shutdown sequence.

        Order matters (reverse of startup):
        1. Stop accepting new signals (deactivate strategy)
        2. Stop data streams
        3. Stop order manager
        4. Stop health monitor
        5. Close database
        6. Close broker connection
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

        # 4. Stop health monitor
        if self._health_monitor:
            logger.info("Stopping health monitor...")
            await self._health_monitor.stop()

        # 5. Close database
        if self._db:
            logger.info("Closing database...")
            await self._db.close()

        # 6. Close broker
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
