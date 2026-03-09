"""Argus Trading System — Main Entry Point.

Wires all components together and runs the event loop.

Usage:
    python -m argus.main                              # Default: config/ directory
    python -m argus.main --config /path/to/           # Custom config directory
    python -m argus.main --config config/system_live.yaml  # Specific system config
    python -m argus.main --paper                      # Force paper trading (default)
    python -m argus.main --dry-run                    # Start, connect, but don't trade
    python -m argus.main --no-api                     # Disable Command Center API server

System profiles:
    - config/system.yaml      — Alpaca/simulated (development/incubator)
    - config/system_live.yaml — Databento + IBKR (live integration)
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
    load_afternoon_momentum_config,
    load_config,
    load_orb_config,
    load_orb_scalp_config,
    load_vwap_reclaim_config,
    load_yaml_file,
)
from argus.core.event_bus import EventBus
from argus.core.events import CandleEvent, PositionClosedEvent, ShutdownRequestedEvent
from argus.core.health import ComponentStatus, HealthMonitor
from argus.core.logging_config import setup_logging
from argus.core.orchestrator import Orchestrator
from argus.core.risk_manager import RiskManager
from argus.data.alpaca_data_service import AlpacaDataService
from argus.data.alpaca_scanner import AlpacaScanner
from argus.data.databento_data_service import DatabentoDataService
from argus.data.databento_scanner import DatabentoScanner, DatabentoScannerConfig
from argus.data.fmp_reference import FMPReferenceClient, FMPReferenceConfig
from argus.data.fmp_scanner import FMPScannerConfig, FMPScannerSource
from argus.data.scanner import StaticScanner
from argus.data.universe_manager import UniverseManager
from argus.ai.actions import ActionManager
from argus.ai.conversations import ConversationManager
from argus.ai.usage import UsageTracker
from argus.db.manager import DatabaseManager
from argus.execution.alpaca_broker import AlpacaBroker
from argus.execution.order_manager import OrderManager
from argus.strategies.afternoon_momentum import AfternoonMomentumStrategy
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

    def __init__(
        self,
        config_dir: Path,
        dry_run: bool = False,
        enable_api: bool = True,
        system_config_file: Path | None = None,
    ) -> None:
        """Initialize the Argus system.

        Args:
            config_dir: Path to configuration directory.
            dry_run: If True, connect but don't stream data or trade.
            enable_api: If True, start the Command Center API server.
            system_config_file: Optional path to a specific system config file.
                If provided, this file is used instead of config_dir/system.yaml.
        """
        self._config_dir = config_dir
        self._dry_run = dry_run
        self._enable_api = enable_api
        self._system_config_file = system_config_file
        self._shutdown_event = asyncio.Event()

        # Components (initialized in start())
        self._clock: Clock | None = None
        self._event_bus: EventBus | None = None
        self._db: DatabaseManager | None = None
        self._trade_logger: TradeLogger | None = None
        self._conversation_manager: ConversationManager | None = None
        self._usage_tracker: UsageTracker | None = None
        self._broker: Broker | None = None
        self._data_service: DataService | None = None
        self._scanner: Scanner | None = None
        self._risk_manager: RiskManager | None = None
        self._order_manager: OrderManager | None = None
        self._health_monitor: HealthMonitor | None = None
        self._orchestrator: Orchestrator | None = None
        self._api_task: asyncio.Task[None] | None = None
        self._config: object | None = None  # Store config for API access
        self._cached_watchlist: list = []  # Scanner results for API watchlist endpoint
        self._universe_manager: UniverseManager | None = None  # Sprint 23: Universe Manager
        self._strategies: dict = {}  # Strategy dict for candle routing

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
        config = load_config(self._config_dir, self._system_config_file)
        self._config = config

        self._clock = SystemClock()
        self._event_bus = EventBus()

        # --- Phase 2: Database ---
        logger.info("[2/12] Initializing database...")
        db_path = Path(config.system.data_dir) / "argus.db"
        self._db = DatabaseManager(db_path)
        await self._db.initialize()
        self._trade_logger = TradeLogger(self._db)

        # Initialize AI persistence tables
        # NOTE: Shares SQLite write lock with Trade Logger. Monitor latency during
        # active trading + chat. See RSK-NEW-5.
        self._conversation_manager = ConversationManager(self._db)
        await self._conversation_manager.initialize()
        self._usage_tracker = UsageTracker(self._db)
        await self._usage_tracker.initialize()

        # Initialize ActionManager if AI is enabled
        self._action_manager: ActionManager | None = None
        if config.system.ai.enabled:
            self._action_manager = ActionManager(self._db, self._event_bus, config.system.ai)
            await self._action_manager.initialize()
            logger.info("ActionManager initialized")

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
                data_config=data_config,
                clock=self._clock,
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

        scanner_type = scanner_yaml.get("scanner_type", "static")

        if scanner_type == "fmp":
            logger.info("Using FMP scanner")
            fmp_scanner_data = scanner_yaml.get("fmp_scanner", {})
            fmp_config = FMPScannerConfig(**fmp_scanner_data)
            self._scanner = FMPScannerSource(config=fmp_config)
        elif scanner_type == "databento":
            logger.info("Using Databento scanner")
            databento_scanner_data = scanner_yaml.get("databento_scanner", {})
            db_scanner_config = DatabentoScannerConfig(**databento_scanner_data)
            self._scanner = DatabentoScanner(
                config=db_scanner_config,
                databento_config=config.broker.databento,
            )
        elif scanner_type == "alpaca":
            logger.info("Using Alpaca scanner")
            alpaca_scanner_data = scanner_yaml.get("alpaca_scanner", {})
            scanner_config = AlpacaScannerConfig(**alpaca_scanner_data)
            self._scanner = AlpacaScanner(
                config=scanner_config,
                alpaca_config=config.broker.alpaca,
            )
        else:
            logger.info("Using static scanner (type=%s)", scanner_type)
            static_symbols = scanner_yaml.get("static_symbols", [])
            self._scanner = StaticScanner(symbols=static_symbols)
        await self._scanner.start()

        # Scan with empty criteria list (use scanner defaults)
        watchlist = await self._scanner.scan([])
        self._cached_watchlist = watchlist
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

        # --- Phase 7.5: Universe Manager (Sprint 23) ---
        # Only enabled when universe_manager.enabled=True AND not simulated broker
        use_universe_manager = (
            config.system.universe_manager.enabled
            and config.system.broker_source != BrokerSource.SIMULATED
        )

        # Track symbols for warm-up (may be scanner symbols or viable symbols)
        warmup_symbols: list[str] = symbols

        if use_universe_manager:
            logger.info("[7.5/12] Building Universe Manager...")
            try:
                # Create FMP reference client
                fmp_ref_config = FMPReferenceConfig(
                    batch_size=config.system.universe_manager.fmp_batch_size,
                    cache_ttl_hours=config.system.universe_manager.reference_cache_ttl_hours,
                )
                fmp_client = FMPReferenceClient(fmp_ref_config)
                await fmp_client.start()

                # Create Universe Manager
                self._universe_manager = UniverseManager(
                    reference_client=fmp_client,
                    config=config.system.universe_manager,
                    scanner=self._scanner,
                )

                # Fetch full stock list from FMP (Sprint 23.3 — wide pipe)
                all_symbols = await fmp_client.fetch_stock_list()

                # Fall back to scanner symbols if stock-list fetch failed
                if not all_symbols:
                    logger.warning(
                        "FMP stock-list fetch failed — falling back to scanner symbols "
                        "(%d symbols). Universe Manager will operate with reduced universe.",
                        len(symbols),
                    )
                    all_symbols = symbols

                # Build viable universe from full stock list (or fallback)
                viable_symbols = await self._universe_manager.build_viable_universe(all_symbols)

                # Handle empty viable set (all symbols filtered out)
                if not viable_symbols:
                    logger.error(
                        "Viable universe is empty after filtering %d symbols. "
                        "Falling back to scanner symbols for warm-up.",
                        len(all_symbols),
                    )
                    warmup_symbols = symbols
                else:
                    # Use viable symbols for warm-up
                    warmup_symbols = list(viable_symbols)
                    logger.info(
                        "Universe Manager built: %d viable symbols from %d total",
                        len(viable_symbols),
                        len(all_symbols),
                    )

            except Exception as e:
                logger.error("Failed to build Universe Manager: %s. Falling back to scanner.", e)
                # Graceful degradation — continue without Universe Manager
                self._universe_manager = None
                use_universe_manager = False
                warmup_symbols = symbols
        else:
            logger.info("Universe Manager disabled or simulated broker mode")

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
        if not use_universe_manager:
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
            if not use_universe_manager:
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
            if not use_universe_manager:
                vwap_reclaim_strategy.set_watchlist(symbols)
            strategies_created.append("VwapReclaim")

        # Afternoon Momentum (optional — only if config file exists)
        afternoon_strategy: AfternoonMomentumStrategy | None = None
        afternoon_yaml = self._config_dir / "strategies" / "afternoon_momentum.yaml"
        if afternoon_yaml.exists():
            afternoon_config = load_afternoon_momentum_config(afternoon_yaml)
            afternoon_strategy = AfternoonMomentumStrategy(
                config=afternoon_config,
                data_service=self._data_service,
                clock=self._clock,
            )
            if not use_universe_manager:
                afternoon_strategy.set_watchlist(symbols)
            strategies_created.append("AfternoonMomentum")

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
        if afternoon_strategy is not None:
            self._orchestrator.register_strategy(afternoon_strategy)

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
        self._health_monitor.update_component(
            "strategy_orb_breakout", ComponentStatus.HEALTHY, "ORB Breakout running"
        )
        if scalp_strategy is not None:
            self._health_monitor.update_component(
                "strategy_orb_scalp", ComponentStatus.HEALTHY, "ORB Scalp running"
            )
        if vwap_reclaim_strategy is not None:
            self._health_monitor.update_component(
                "strategy_vwap_reclaim", ComponentStatus.HEALTHY, "VWAP Reclaim running"
            )
        if afternoon_strategy is not None:
            self._health_monitor.update_component(
                "strategy_afternoon_momentum", ComponentStatus.HEALTHY, "Afternoon Momentum running"
            )

        # Store strategies reference for candle routing
        self._strategies = strategies

        # --- Phase 9.5: Build Routing Table (Sprint 23) ---
        if use_universe_manager and self._universe_manager is not None:
            logger.info("[9.5/12] Building routing table...")
            # Build strategy configs dict for routing table
            strategy_configs = {
                sid: strat.config for sid, strat in strategies.items() if hasattr(strat, "config")
            }
            self._universe_manager.build_routing_table(strategy_configs)

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

        # --- Phase 10.5: Event Routing ---
        # Subscribe to CandleEvents and route to active strategies (DEC-125)
        self._event_bus.subscribe(CandleEvent, self._on_candle_for_strategies)
        # Subscribe to PositionClosedEvents to update strategy position tracking
        self._event_bus.subscribe(PositionClosedEvent, self._on_position_closed_for_strategies)
        # Subscribe to ShutdownRequestedEvent for auto-shutdown after EOD flatten
        self._event_bus.subscribe(ShutdownRequestedEvent, self._on_shutdown_requested)

        # --- Phase 11: Start streaming ---
        logger.info("[11/12] Starting data streams...")

        # When Universe Manager is active, set viable universe on data service
        # for fast-path discard (Sprint 23)
        if use_universe_manager and self._universe_manager is not None:
            if hasattr(self._data_service, "set_viable_universe"):
                self._data_service.set_viable_universe(self._universe_manager.viable_symbols)
                logger.info(
                    "Viable universe set on data service: %d symbols",
                    self._universe_manager.viable_count,
                )

        # Start data service with appropriate symbols for warm-up
        # When UM enabled: uses viable symbols; when disabled: uses scanner symbols
        if warmup_symbols and not self._dry_run:
            await self._data_service.start(symbols=warmup_symbols, timeframes=["1m"])
            self._health_monitor.update_component(
                "data_service", ComponentStatus.HEALTHY, message=f"Streaming {len(warmup_symbols)} symbols"
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
                    cached_watchlist=self._cached_watchlist,
                    conversation_manager=self._conversation_manager,
                    usage_tracker=self._usage_tracker,
                    action_manager=self._action_manager,
                    universe_manager=self._universe_manager,
                )

                # Start ActionManager cleanup task if AI is enabled
                if self._action_manager is not None:
                    self._action_manager.start_cleanup_task()
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

        Called for every CandleEvent. Routes to strategies via one of two paths:

        1. Universe Manager path (Sprint 23): Uses routing table for O(1) lookup
           of which strategies should receive this symbol.
        2. Legacy path: Iterates all strategies, checks watchlist membership.

        If a strategy emits a SignalEvent, it's sent through the Risk Manager
        for approval and the result is published to the Event Bus.

        Args:
            event: The candle event to route.
        """
        if self._risk_manager is None:
            return

        if self._universe_manager is not None and self._universe_manager.is_built:
            # Sprint 23: Universe Manager routing path
            matching_strategy_ids = self._universe_manager.route_candle(event.symbol)
            for strategy_id in matching_strategy_ids:
                strategy = self._strategies.get(strategy_id)
                if strategy is not None and strategy.is_active:
                    signal = await strategy.on_candle(event)
                    if signal is not None:
                        result = await self._risk_manager.evaluate_signal(signal)
                        await self._event_bus.publish(result)
        else:
            # Legacy path: iterate all strategies, check watchlist
            if self._orchestrator is None:
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

    async def _on_position_closed_for_strategies(self, event: PositionClosedEvent) -> None:
        """Route PositionClosedEvents to originating strategy.

        Updates strategy position tracking so concurrent position counters
        are decremented when positions close.

        Args:
            event: The position closed event to route.
        """
        if self._orchestrator is None:
            return

        strategies = self._orchestrator.get_strategies()
        strategy = strategies.get(event.strategy_id)
        if strategy is not None and hasattr(strategy, "mark_position_closed"):
            strategy.mark_position_closed(event.symbol)
            logger.debug(
                "Position closed for %s on %s, notified strategy",
                event.symbol,
                event.strategy_id,
            )

    async def _on_shutdown_requested(self, event: ShutdownRequestedEvent) -> None:
        """Handle shutdown request from Order Manager after EOD flatten.

        Schedules graceful shutdown after the configured delay to allow
        any final operations (trade logging, API responses) to complete.

        Args:
            event: The shutdown request event with delay configuration.
        """
        delay = event.delay_seconds
        logger.info(
            "Auto-shutdown requested (reason=%s). Initiating in %ds...",
            event.reason,
            delay,
        )

        # Schedule the delayed shutdown
        async def delayed_shutdown() -> None:
            await asyncio.sleep(delay)
            logger.info("Auto-shutdown initiated")
            self.request_shutdown()

        asyncio.create_task(delayed_shutdown())

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

        # 0a. Stop ActionManager cleanup task
        if self._action_manager is not None:
            logger.info("Stopping ActionManager cleanup task...")
            self._action_manager.stop_cleanup_task()

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
        help=(
            "Path to configuration directory OR a specific system config file. "
            "If a .yaml file is provided (e.g., config/system_live.yaml), "
            "that file is used as the system config and the parent directory "
            "is used for other config files. (default: config/)"
        ),
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

    # Detect if --config is a file or directory
    config_path = args.config
    system_config_file: Path | None = None

    if config_path.suffix in (".yaml", ".yml"):
        # --config points to a specific system config file
        system_config_file = config_path
        config_dir = config_path.parent
        logger.info(
            "Argus starting with system config: %s (dir: %s)", system_config_file, config_dir
        )
    else:
        # --config points to a directory
        config_dir = config_path
        logger.info("Argus starting with config from: %s", config_dir)

    system = ArgusSystem(
        config_dir=config_dir,
        dry_run=args.dry_run,
        enable_api=not args.no_api,
        system_config_file=system_config_file,
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
