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
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

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
    load_bull_flag_config,
    load_config,
    load_flat_top_breakout_config,
    load_orb_config,
    load_orb_scalp_config,
    load_red_to_green_config,
    load_vwap_reclaim_config,
    load_yaml_file,
)
from argus.core.event_bus import EventBus
from argus.core.events import (
    CandleEvent,
    OrderApprovedEvent,
    OrderRejectedEvent,
    PositionClosedEvent,
    QualitySignalEvent,
    SessionEndEvent,
    ShutdownRequestedEvent,
    SignalRejectedEvent,
)
from argus.core.health import ComponentStatus, HealthMonitor
from argus.core.logging_config import setup_logging
from argus.core.orchestrator import Orchestrator
from argus.core.risk_manager import RiskManager
from argus.data.alpaca_data_service import AlpacaDataService
from argus.data.alpaca_scanner import AlpacaScanner
from argus.data.databento_data_service import DatabentoDataService
from argus.data.intraday_candle_store import IntradayCandleStore
from argus.data.databento_scanner import DatabentoScanner, DatabentoScannerConfig
from argus.data.fmp_reference import FMPReferenceClient, FMPReferenceConfig
from argus.data.fmp_scanner import FMPScannerConfig, FMPScannerSource
from argus.data.scanner import StaticScanner
from argus.data.universe_manager import UniverseManager
from argus.ai.actions import ActionManager
from argus.ai.conversations import ConversationManager
from argus.ai.usage import UsageTracker
from argus.db.manager import DatabaseManager
from argus.core.regime import MarketRegime
from argus.intelligence.position_sizer import DynamicPositionSizer
from argus.intelligence.quality_engine import SetupQualityEngine
from argus.execution.alpaca_broker import AlpacaBroker
from argus.execution.order_manager import OrderManager
from argus.strategies.afternoon_momentum import AfternoonMomentumStrategy
from argus.strategies.pattern_strategy import PatternBasedStrategy
from argus.strategies.patterns import BullFlagPattern, FlatTopBreakoutPattern
from argus.strategies.red_to_green import RedToGreenStrategy
from argus.strategies.telemetry_store import EvaluationEventStore
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
        # Sprint 24: Quality pipeline components (initialized after DB + config)
        self._quality_engine: SetupQualityEngine | None = None
        self._position_sizer: DynamicPositionSizer | None = None
        self._catalyst_storage: object | None = None  # CatalystStorage, if pipeline active
        self._eval_check_task: asyncio.Task[None] | None = None  # Sprint 25.5: eval health check
        self._eval_store: EvaluationEventStore | None = None  # Sprint 25.6: reused in health check
        self._regime_task: asyncio.Task[None] | None = None  # Sprint 25.6 S2: periodic regime reclass
        self._regime_check_count: int = 0  # Sprint 25.9: counter for INFO logging cadence
        self._bg_refresh_task: asyncio.Task[None] | None = None  # Sprint 25.9: background cache refresh
        self._reconciliation_task: asyncio.Task[None] | None = None  # Sprint 27.65: position recon
        self._candle_store: IntradayCandleStore | None = None  # Sprint 27.65 S4: intraday bar store
        self._counterfactual_enabled: bool = False  # Sprint 27.7 S3b sets True after tracker init
        self._counterfactual_tracker: object | None = None  # Sprint 27.7: CounterfactualTracker
        self._counterfactual_store: object | None = None  # Sprint 27.7: CounterfactualStore
        self._counterfactual_task: asyncio.Task[None] | None = None  # Sprint 27.7: maintenance task

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

        # Track all_symbols for potential background refresh (DEC-362)
        um_all_symbols: list[str] = []

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

                um_all_symbols = all_symbols

                # Build viable universe (trust_cache=True uses cache, no FMP fetch)
                trust_cache = config.system.universe_manager.trust_cache_on_startup
                viable_symbols = await self._universe_manager.build_viable_universe(
                    all_symbols, trust_cache=trust_cache
                )

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

        # Red-to-Green (optional — only if config file exists)
        r2g_strategy: RedToGreenStrategy | None = None
        r2g_yaml = self._config_dir / "strategies" / "red_to_green.yaml"
        if r2g_yaml.exists():
            r2g_config = load_red_to_green_config(r2g_yaml)
            r2g_strategy = RedToGreenStrategy(
                config=r2g_config,
                data_service=self._data_service,
                clock=self._clock,
            )
            if not use_universe_manager:
                r2g_strategy.set_watchlist(symbols)
            strategies_created.append("RedToGreen")

        # Bull Flag (optional — PatternBasedStrategy wrapping BullFlagPattern)
        bull_flag_strategy: PatternBasedStrategy | None = None
        bull_flag_yaml = self._config_dir / "strategies" / "bull_flag.yaml"
        if bull_flag_yaml.exists():
            bull_flag_config = load_bull_flag_config(bull_flag_yaml)
            bull_flag_pattern = BullFlagPattern()
            bull_flag_strategy = PatternBasedStrategy(
                pattern=bull_flag_pattern,
                config=bull_flag_config,
                data_service=self._data_service,
                clock=self._clock,
            )
            if not use_universe_manager:
                bull_flag_strategy.set_watchlist(symbols)
            strategies_created.append("BullFlag")

        # Flat-Top Breakout (optional — PatternBasedStrategy wrapping FlatTopBreakoutPattern)
        flat_top_strategy: PatternBasedStrategy | None = None
        flat_top_yaml = self._config_dir / "strategies" / "flat_top_breakout.yaml"
        if flat_top_yaml.exists():
            flat_top_config = load_flat_top_breakout_config(flat_top_yaml)
            flat_top_pattern = FlatTopBreakoutPattern()
            flat_top_strategy = PatternBasedStrategy(
                pattern=flat_top_pattern,
                config=flat_top_config,
                data_service=self._data_service,
                clock=self._clock,
            )
            if not use_universe_manager:
                flat_top_strategy.set_watchlist(symbols)
            strategies_created.append("FlatTopBreakout")

        # Note: is_active and allocated_capital set by Orchestrator in Phase 9
        self._health_monitor.update_component(
            "strategy",
            ComponentStatus.STARTING,
            message=f"{len(strategies_created)} strategies created",
        )

        # --- Phase 8.5: Regime Intelligence V2 (Sprint 27.6) ---
        regime_v2 = None
        regime_history_store = None
        breadth_calc = None
        intraday_detector = None
        regime_config = config.system.regime_intelligence

        if regime_config.enabled:
            logger.info("[8.5/12] Initializing regime intelligence V2...")
            from argus.core.breadth import BreadthCalculator as BreadthCalcImpl
            from argus.core.intraday_character import IntradayCharacterDetector
            from argus.core.market_correlation import MarketCorrelationTracker
            from argus.core.regime import RegimeClassifierV2
            from argus.core.sector_rotation import SectorRotationAnalyzer

            orchestrator_yaml_pre = load_yaml_file(self._config_dir / "orchestrator.yaml")
            orchestrator_config_pre = OrchestratorConfig(**orchestrator_yaml_pre)

            # Create dimension calculators
            breadth_calc = BreadthCalcImpl(regime_config.breadth) if regime_config.breadth.enabled else None
            correlation_tracker = (
                MarketCorrelationTracker(regime_config.correlation)
                if regime_config.correlation.enabled
                else None
            )

            fmp_api_key = os.environ.get("FMP_API_KEY", "")
            sector_analyzer = (
                SectorRotationAnalyzer(
                    config=regime_config.sector_rotation,
                    fmp_base_url="https://financialmodelingprep.com/api",
                    fmp_api_key=fmp_api_key,
                )
                if regime_config.sector_rotation.enabled
                else None
            )

            intraday_detector = (
                IntradayCharacterDetector(
                    config=regime_config.intraday,
                    spy_symbol=orchestrator_config_pre.spy_symbol,
                )
                if regime_config.intraday.enabled
                else None
            )

            regime_v2 = RegimeClassifierV2(
                config=orchestrator_config_pre,
                regime_config=regime_config,
                breadth=breadth_calc,
                correlation=correlation_tracker,
                sector=sector_analyzer,
                intraday=intraday_detector,
            )

            # Create history store if persistence enabled
            if regime_config.persist_history:
                from argus.core.regime_history import RegimeHistoryStore

                history_db_path = str(Path(config.system.data_dir) / "regime_history.db")
                regime_history_store = RegimeHistoryStore(db_path=history_db_path)
                await regime_history_store.initialize()
                logger.info("RegimeHistoryStore initialized: %s", history_db_path)

            logger.info("Regime intelligence V2 ready")

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
            regime_classifier_v2=regime_v2,
            regime_history=regime_history_store,
        )

        # Register all strategies
        self._orchestrator.register_strategy(orb_strategy)
        if scalp_strategy is not None:
            self._orchestrator.register_strategy(scalp_strategy)
        if vwap_reclaim_strategy is not None:
            self._orchestrator.register_strategy(vwap_reclaim_strategy)
        if afternoon_strategy is not None:
            self._orchestrator.register_strategy(afternoon_strategy)
        if r2g_strategy is not None:
            self._orchestrator.register_strategy(r2g_strategy)
        if bull_flag_strategy is not None:
            self._orchestrator.register_strategy(bull_flag_strategy)
        if flat_top_strategy is not None:
            self._orchestrator.register_strategy(flat_top_strategy)

        await self._orchestrator.start()

        # Run V2 pre-market (correlation + sector rotation, concurrent)
        if regime_v2 is not None:
            try:
                await regime_v2.run_pre_market(
                    fetch_daily_bars_fn=self._data_service.fetch_daily_bars,
                    get_top_symbols_fn=(
                        self._universe_manager.get_top_symbols
                        if self._universe_manager is not None
                        and hasattr(self._universe_manager, "get_top_symbols")
                        else lambda: []
                    ),
                )
            except Exception:
                logger.warning("V2 pre-market failed — V1 will proceed normally", exc_info=True)

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
        for strategy_id, strategy in strategies.items():
            status = ComponentStatus.HEALTHY if strategy.is_active else ComponentStatus.DEGRADED
            label = "active" if strategy.is_active else "regime-filtered"
            self._health_monitor.update_component(
                f"strategy_{strategy_id}",
                status,
                message=f"{strategy.config.name} {label}",
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

            # Populate strategy watchlists from Universe Manager routing
            for strategy_id, strategy in strategies.items():
                um_symbols = self._universe_manager.get_strategy_symbols(strategy_id)
                strategy.set_watchlist(list(um_symbols), source="universe_manager")
            logger.info("Strategy watchlists populated from Universe Manager routing")

            # Initialize R2G prior_close from UM cached reference data (Sprint 27.65 S3)
            if r2g_strategy is not None:
                ref_data = {
                    sym: self._universe_manager.get_reference_data(sym)
                    for sym in r2g_strategy.watchlist
                }
                # Filter out None entries
                valid_ref = {s: r for s, r in ref_data.items() if r is not None}
                r2g_strategy.initialize_prior_closes(valid_ref)

        # --- Phase 10: Order Manager ---
        logger.info("[10/12] Starting order manager...")
        order_manager_yaml = load_yaml_file(self._config_dir / "order_manager.yaml")
        from argus.core.config import ExitManagementConfig, OrderManagerConfig

        order_manager_config = OrderManagerConfig(**order_manager_yaml)

        # AMD-10: Warn if legacy trailing stop fields are active in order_manager.yaml
        if order_manager_yaml.get("enable_trailing_stop") is True or (
            order_manager_yaml.get("trailing_stop_atr_multiplier", 2.0) != 2.0
        ):
            logger.warning(
                "Legacy trailing stop config detected (enable_trailing_stop / "
                "trailing_stop_atr_multiplier). These fields are deprecated — use "
                "config/exit_management.yaml instead. Legacy fields are ignored."
            )

        # Load exit management config (Sprint 28.5)
        exit_mgmt_yaml = load_yaml_file(self._config_dir / "exit_management.yaml")
        exit_config = ExitManagementConfig(**exit_mgmt_yaml)

        # Scan strategy YAMLs for per-strategy exit_management overrides (S4a)
        strategy_exit_overrides: dict[str, dict[str, Any]] = {}
        strategies_dir = self._config_dir / "strategies"
        if strategies_dir.is_dir():
            for yaml_path in sorted(strategies_dir.glob("*.yaml")):
                strat_yaml = load_yaml_file(yaml_path)
                if "exit_management" in strat_yaml and "strategy_id" in strat_yaml:
                    strategy_exit_overrides[strat_yaml["strategy_id"]] = strat_yaml[
                        "exit_management"
                    ]

        # Read reconciliation and startup configs from typed Pydantic models
        reconciliation_config = config.system.reconciliation
        startup_config = config.system.startup

        self._order_manager = OrderManager(
            event_bus=self._event_bus,
            broker=self._broker,
            clock=self._clock,
            config=order_manager_config,
            trade_logger=self._trade_logger,
            db_manager=self._db,
            broker_source=self._config.system.broker_source,
            reconciliation_config=reconciliation_config,
            startup_config=startup_config,
            exit_config=exit_config,
            strategy_exit_overrides=strategy_exit_overrides,
        )
        await self._order_manager.start()
        # Reconstruct open positions from broker
        await self._order_manager.reconstruct_from_broker()
        self._health_monitor.update_component("order_manager", ComponentStatus.HEALTHY)

        # Wire Risk Manager to Order Manager for cross-strategy checks
        self._risk_manager.set_order_manager(self._order_manager)

        # --- Phase 10.25: Quality Pipeline (Sprint 24) ---
        qe_config = config.system.quality_engine
        if qe_config.enabled and config.system.broker_source != BrokerSource.SIMULATED:
            self._quality_engine = SetupQualityEngine(qe_config, db_manager=self._db)
            self._position_sizer = DynamicPositionSizer(qe_config)
            # Create CatalystStorage for quality lookups (catalyst data)
            if self._catalyst_storage is None:
                try:
                    from argus.intelligence.storage import CatalystStorage

                    db_path = Path(config.system.data_dir) / "argus.db"
                    self._catalyst_storage = CatalystStorage(str(db_path))
                    await self._catalyst_storage.initialize()
                except Exception:
                    logger.warning("CatalystStorage not available for quality pipeline")
            logger.info("Quality pipeline initialized (engine + sizer)")
        else:
            logger.info(
                "Quality pipeline disabled (enabled=%s, broker=%s)",
                qe_config.enabled,
                config.system.broker_source,
            )

        # --- Phase 10.3: Telemetry Store (Sprint 25.6) ---
        # Create EvaluationEventStore early so health check + API share one instance
        try:
            eval_db_path = str(Path(config.system.data_dir) / "evaluation.db")
            self._eval_store = EvaluationEventStore(eval_db_path)
            await self._eval_store.initialize()
            await self._eval_store.cleanup_old_events()

            # Wire store into each strategy's evaluation buffer
            for strategy in self._strategies.values():
                strategy.eval_buffer.set_store(self._eval_store)

            logger.info("EvaluationEventStore initialized: %s", eval_db_path)
        except Exception as e:
            logger.error("Failed to initialize EvaluationEventStore: %s", e)
            self._eval_store = None

        # --- Phase 10.5: Event Routing ---
        # IntradayCandleStore — parallel CandleEvent subscriber (Sprint 27.65 S4)
        self._candle_store = IntradayCandleStore()
        self._event_bus.subscribe(CandleEvent, self._candle_store.on_candle)

        # Wire candle store into PatternBasedStrategy instances for auto-backfill
        for strategy in self._strategies.values():
            if isinstance(strategy, PatternBasedStrategy):
                strategy.set_candle_store(self._candle_store)

        # Subscribe to CandleEvents and route to active strategies (DEC-125)
        self._event_bus.subscribe(CandleEvent, self._on_candle_for_strategies)
        # Subscribe to PositionClosedEvents to update strategy position tracking
        self._event_bus.subscribe(PositionClosedEvent, self._on_position_closed_for_strategies)
        # Subscribe to ShutdownRequestedEvent for auto-shutdown after EOD flatten
        self._event_bus.subscribe(ShutdownRequestedEvent, self._on_shutdown_requested)

        # Subscribe regime intelligence calculators to CandleEvent (Sprint 27.6)
        # EventBus requires async handlers; wrap sync on_candle methods
        if breadth_calc is not None:
            _bc = breadth_calc

            async def _breadth_on_candle(event: CandleEvent) -> None:
                _bc.on_candle(event)

            self._event_bus.subscribe(CandleEvent, _breadth_on_candle)
            logger.info("BreadthCalculator subscribed to CandleEvent")
        if intraday_detector is not None:
            _id = intraday_detector

            async def _intraday_on_candle(event: CandleEvent) -> None:
                _id.on_candle(event)

            self._event_bus.subscribe(CandleEvent, _intraday_on_candle)
            logger.info("IntradayCharacterDetector subscribed to CandleEvent")

        # --- Phase 10.7: Counterfactual Engine (Sprint 27.7) ---
        from argus.intelligence.startup import build_counterfactual_tracker

        cf_result = await build_counterfactual_tracker(
            config=config.system,
            candle_store=self._candle_store,
        )
        if cf_result is not None:
            self._counterfactual_tracker, self._counterfactual_store = cf_result
            self._counterfactual_enabled = True
            logger.info("Counterfactual Engine initialized")

            # Subscribe to rejected signals for shadow tracking
            self._event_bus.subscribe(
                SignalRejectedEvent,
                self._on_signal_rejected_for_counterfactual,
            )
            # Subscribe to candle events for monitoring open positions
            self._event_bus.subscribe(
                CandleEvent,
                self._counterfactual_tracker.on_candle,
            )

            # Retention enforcement (once per boot)
            await self._counterfactual_store.enforce_retention(
                config.system.counterfactual.retention_days
            )

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
                    telemetry_store=self._eval_store,
                    candle_store=self._candle_store,
                    counterfactual_store=self._counterfactual_store,
                )

                # Start ActionManager cleanup task if AI is enabled
                if self._action_manager is not None:
                    self._action_manager.start_cleanup_task()
                api_app = create_app(app_state)

                # Start WebSocket bridge
                ws_bridge = get_bridge()
                ws_bridge.start(
                    self._event_bus, self._order_manager, config.system.api,
                    broker=self._broker,
                )

                # Start API server with port-availability guard
                try:
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
                except Exception as e:
                    # Import here to avoid circular import
                    from argus.api.server import PortInUseError

                    if isinstance(e, PortInUseError):
                        # Port already in use — system continues in headless mode
                        logger.warning(
                            "API server not started: %s. System running in headless mode.",
                            e,
                        )
                        self._health_monitor.update_component(
                            "api_server",
                            ComponentStatus.DEGRADED,
                            message=f"Port {config.system.api.port} in use — headless mode",
                        )
                        # Stop the WebSocket bridge since we have no API server
                        ws_bridge.stop()
                    else:
                        raise
        else:
            logger.info("API server disabled by configuration or --no-api flag")
            self._health_monitor.update_component(
                "api_server", ComponentStatus.STOPPED, message="Disabled"
            )

        logger.info("=" * 60)
        logger.info("ARGUS TRADING SYSTEM — RUNNING")
        if self._dry_run:
            logger.info("MODE: DRY RUN (no trades will be placed)")
        if self._universe_manager is not None and self._universe_manager.is_built:
            logger.info(
                "Watching %d symbols (Universe Manager)",
                self._universe_manager.viable_count,
            )
        else:
            logger.info("Watching %d symbols (scanner)", len(symbols))
        if self._api_task:
            logger.info("API: http://%s:%d", config.system.api.host, config.system.api.port)
        logger.info("=" * 60)

        # Start strategy evaluation health check (Sprint 25.5, 25.6: reuse store)
        self._eval_check_task = asyncio.create_task(
            self._evaluation_health_check_loop()
        )

        # Start periodic regime reclassification (Sprint 25.6 S2)
        self._regime_task = asyncio.create_task(
            self._run_regime_reclassification()
        )

        # Start periodic position reconciliation (Sprint 27.65)
        self._reconciliation_task = asyncio.create_task(
            self._run_position_reconciliation()
        )

        # Start counterfactual maintenance task (Sprint 27.7)
        if self._counterfactual_tracker is not None:
            self._counterfactual_task = asyncio.create_task(
                self._run_counterfactual_maintenance()
            )

        # Start background cache refresh if trust_cache_on_startup is enabled (DEC-362)
        if (
            use_universe_manager
            and self._universe_manager is not None
            and config.system.universe_manager.trust_cache_on_startup
            and um_all_symbols
        ):
            self._bg_refresh_task = asyncio.create_task(
                self._background_cache_refresh(um_all_symbols)
            )

        # Send startup alert
        mode = "DRY RUN" if self._dry_run else "PAPER TRADING"
        watch_count = (
            self._universe_manager.viable_count
            if self._universe_manager is not None and self._universe_manager.is_built
            else len(symbols)
        )
        await self._health_monitor.send_warning_alert(
            title="Argus Started",
            body=f"Watching {watch_count} symbols. Mode: {mode}",
        )

    async def _evaluation_health_check_loop(self) -> None:
        """Periodic check for strategies with zero evaluation events.

        Runs every 60 seconds during market hours (9:30–16:00 ET).
        Delegates to HealthMonitor.check_strategy_evaluations().
        """
        from datetime import time as dt_time
        from zoneinfo import ZoneInfo

        et_tz = ZoneInfo("America/New_York")
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)

        while True:
            try:
                now = self._clock.now()
                now_et = (
                    now.replace(tzinfo=et_tz) if now.tzinfo is None
                    else now.astimezone(et_tz)
                )
                current_time = now_et.time()

                if market_open <= current_time <= market_close:
                    if (
                        self._health_monitor is not None
                        and self._eval_store is not None
                        and self._eval_store.is_connected
                        and self._strategies
                    ):
                        await self._health_monitor.check_strategy_evaluations(
                            strategies=self._strategies,
                            eval_store=self._eval_store,
                            clock=self._clock,
                        )
            except Exception as e:
                logger.error("Evaluation health check error: %s", e)

            await asyncio.sleep(60)

    async def _run_regime_reclassification(self) -> None:
        """Periodic regime reclassification during market hours.

        Runs every 5 minutes (300s). Calls the orchestrator's reclassify_regime()
        method and logs the result at appropriate levels.
        """
        from datetime import time as dt_time
        from zoneinfo import ZoneInfo

        et_tz = ZoneInfo("America/New_York")
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)

        while True:
            await asyncio.sleep(300)
            try:
                now = self._clock.now()
                now_et = (
                    now.replace(tzinfo=et_tz) if now.tzinfo is None
                    else now.astimezone(et_tz)
                )
                current_time = now_et.time()

                if market_open <= current_time <= market_close:
                    if self._orchestrator is not None:
                        old, new = await self._orchestrator.reclassify_regime()
                        self._regime_check_count += 1
                        if old != new:
                            logger.info(
                                "Regime reclassified: %s → %s",
                                old.value,
                                new.value,
                            )
                        elif self._regime_check_count % 6 == 0:
                            indicators = self._orchestrator.current_indicators
                            vol = indicators.spy_realized_vol_20d if indicators else None
                            logger.info(
                                "Regime unchanged: %s (check #%d, SPY vol: %s)",
                                new.value,
                                self._regime_check_count,
                                f"{vol:.4f}" if vol is not None else "N/A",
                            )
                        else:
                            logger.debug("Regime unchanged: %s", new.value)
            except Exception as e:
                logger.error("Regime reclassification error: %s", e)

    async def _run_position_reconciliation(self) -> None:
        """Periodic position reconciliation during market hours.

        Runs every 60 seconds. Compares Order Manager internal positions
        against broker-reported positions and logs warnings on mismatch.
        Does NOT auto-correct — warn only.
        """
        from datetime import time as dt_time
        from zoneinfo import ZoneInfo

        et_tz = ZoneInfo("America/New_York")
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)

        while True:
            await asyncio.sleep(60)
            try:
                now = self._clock.now()
                now_et = (
                    now.replace(tzinfo=et_tz) if now.tzinfo is None
                    else now.astimezone(et_tz)
                )
                current_time = now_et.time()

                if market_open <= current_time <= market_close:
                    if self._broker is None or self._order_manager is None:
                        continue

                    # Get broker positions and convert to {symbol: quantity}
                    broker_pos_list = await self._broker.get_positions()
                    broker_positions: dict[str, float] = {}
                    for pos in broker_pos_list:
                        symbol = getattr(pos, "symbol", "")
                        qty = float(getattr(pos, "qty", 0))
                        if symbol and qty != 0:
                            broker_positions[symbol] = qty

                    discrepancies = await self._order_manager.reconcile_positions(
                        broker_positions
                    )
                    if discrepancies:
                        logger.warning(
                            "Position reconciliation: %d mismatch(es) found",
                            len(discrepancies),
                        )
            except Exception as e:
                logger.error("Position reconciliation error: %s", e)

    async def _background_cache_refresh(self, all_symbols: list[str]) -> None:
        """Background task to refresh stale reference cache entries (DEC-362).

        Runs after startup completes. Fetches fresh data for stale symbols,
        then atomically rebuilds the routing table and updates strategy
        watchlists. Failure logs a warning but does not affect trading.

        Args:
            all_symbols: Complete symbol list for staleness checking.
        """
        if self._universe_manager is None:
            return

        ref_client = self._universe_manager._reference_client
        await ref_client.background_refresh(all_symbols)

        # Rebuild routing table with fresh data
        strategy_configs = {
            sid: strat.config
            for sid, strat in self._strategies.items()
            if hasattr(strat, "config")
        }
        self._universe_manager.rebuild_after_refresh(strategy_configs)

        # Update strategy watchlists from new routing table
        for strategy_id, strategy in self._strategies.items():
            um_symbols = self._universe_manager.get_strategy_symbols(strategy_id)
            strategy.set_watchlist(list(um_symbols), source="universe_manager")

        # Re-initialize R2G prior_close after watchlist refresh (Sprint 27.65 S3)
        for strategy in self._strategies.values():
            if isinstance(strategy, RedToGreenStrategy):
                ref_data = {
                    sym: self._universe_manager.get_reference_data(sym)
                    for sym in strategy.watchlist
                }
                valid_ref = {s: r for s, r in ref_data.items() if r is not None}
                strategy.initialize_prior_closes(valid_ref)

        # Update data service viable universe for fast-path discard
        if hasattr(self._data_service, "set_viable_universe"):
            self._data_service.set_viable_universe(
                self._universe_manager.viable_symbols
            )

        logger.info(
            "Background refresh complete — routing table and watchlists updated"
        )

    async def _on_candle_for_strategies(self, event: CandleEvent) -> None:
        """Route CandleEvents to active strategies (DEC-125).

        Called for every CandleEvent. Routes to strategies via one of two paths:

        1. Universe Manager path (Sprint 23): Uses routing table for O(1) lookup
           of which strategies should receive this symbol.
        2. Legacy path: Iterates all strategies, checks watchlist membership.

        If a strategy emits a SignalEvent, it is processed through the quality
        pipeline (if active) or legacy sizing, then sent to the Risk Manager.

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
                        await self._process_signal(signal, strategy)
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
                    await self._process_signal(signal, strategy)

    async def _process_signal(self, signal: "SignalEvent", strategy: object) -> None:
        """Run quality pipeline (or legacy sizing) then evaluate via Risk Manager.

        Bypass conditions (legacy sizing):
        - BrokerSource.SIMULATED (backtesting)
        - quality_engine.enabled = false

        Args:
            signal: The SignalEvent emitted by a strategy.
            strategy: The strategy instance that emitted the signal.
        """
        # Shadow mode routing (Sprint 27.7)
        strategy_mode = getattr(
            getattr(strategy, 'config', None), 'mode', 'live'
        )
        if strategy_mode == "shadow":
            if self._counterfactual_enabled:
                regime_snapshot = self._capture_regime_snapshot()
                await self._event_bus.publish(SignalRejectedEvent(
                    signal=signal,
                    rejection_reason="Shadow mode — signal tracked counterfactually, not executed",
                    rejection_stage="shadow",
                    quality_score=None,
                    quality_grade=None,
                    regime_vector_snapshot=regime_snapshot,
                ))
            return

        config = self._config
        bypass = (
            config.system.broker_source == BrokerSource.SIMULATED
            or not config.system.quality_engine.enabled
            or self._quality_engine is None
        )

        if bypass:
            # Legacy sizing: compute shares from strategy config
            risk_per_share = abs(signal.entry_price - signal.stop_price)
            if risk_per_share > 0:
                shares = int(
                    strategy.allocated_capital
                    * strategy.config.risk_limits.max_loss_per_trade_pct
                    / risk_per_share
                )
            else:
                shares = 0
            signal = replace(signal, share_count=shares)
        else:
            # Quality pipeline: score → grade → size → enrich signal
            catalysts = []
            if self._catalyst_storage is not None:
                try:
                    catalysts = await self._catalyst_storage.get_catalysts_by_symbol(
                        signal.symbol, limit=10
                    )
                except Exception:
                    logger.debug("Catalyst lookup failed for %s", signal.symbol)

            regime = (
                self._orchestrator.current_regime
                if self._orchestrator is not None
                else MarketRegime.RANGE_BOUND
            )

            quality = self._quality_engine.score_setup(
                signal=signal,
                catalysts=catalysts,
                rvol=None,
                regime=regime,
                allowed_regimes=[],
            )

            # Check minimum grade
            min_grade = config.system.quality_engine.min_grade_to_trade
            if not self._grade_meets_minimum(quality.grade, min_grade):
                logger.info(
                    "Signal filtered: %s %s grade=%s below min=%s",
                    signal.symbol,
                    signal.strategy_id,
                    quality.grade,
                    min_grade,
                )
                await self._quality_engine.record_quality_history(signal, quality, shares=0)
                if getattr(self, '_counterfactual_enabled', False):
                    regime_snapshot = self._capture_regime_snapshot()
                    await self._event_bus.publish(SignalRejectedEvent(
                        signal=signal,
                        rejection_reason=f"Quality grade {quality.grade} below minimum {min_grade}",
                        rejection_stage="quality_filter",
                        quality_score=quality.score,
                        quality_grade=quality.grade,
                        regime_vector_snapshot=regime_snapshot,
                    ))
                return

            # Dynamic position sizing
            account = await self._broker.get_account()
            shares = self._position_sizer.calculate_shares(
                quality=quality,
                entry_price=signal.entry_price,
                stop_price=signal.stop_price,
                allocated_capital=strategy.allocated_capital,
                buying_power=account.buying_power if account else 0.0,
            )

            if shares <= 0:
                logger.info(
                    "Signal skipped: %s %s sizer returned 0 shares "
                    "(grade=%s, score=%.0f, allocated_capital=%.2f, "
                    "buying_power=%.2f, entry=%.2f, stop=%.2f, risk_per_share=%.4f)",
                    signal.symbol,
                    signal.strategy_id,
                    quality.grade,
                    quality.score,
                    strategy.allocated_capital,
                    account.buying_power if account else 0.0,
                    signal.entry_price,
                    signal.stop_price,
                    abs(signal.entry_price - signal.stop_price),
                )
                await self._quality_engine.record_quality_history(signal, quality, shares=0)
                if getattr(self, '_counterfactual_enabled', False):
                    regime_snapshot = self._capture_regime_snapshot()
                    await self._event_bus.publish(SignalRejectedEvent(
                        signal=signal,
                        rejection_reason=f"Position sizer returned 0 shares (grade={quality.grade}, score={quality.score:.0f})",
                        rejection_stage="position_sizer",
                        quality_score=quality.score,
                        quality_grade=quality.grade,
                        regime_vector_snapshot=regime_snapshot,
                    ))
                return

            # Record with actual shares
            await self._quality_engine.record_quality_history(signal, quality, shares=shares)

            # Enrich signal with quality data and share count
            signal = replace(
                signal,
                share_count=shares,
                quality_score=quality.score,
                quality_grade=quality.grade,
            )

            # Publish informational QualitySignalEvent for UI consumers
            await self._event_bus.publish(
                QualitySignalEvent(
                    symbol=signal.symbol,
                    strategy_id=signal.strategy_id,
                    score=quality.score,
                    grade=quality.grade,
                    risk_tier=quality.risk_tier,
                    components=quality.components,
                    rationale=quality.rationale,
                )
            )

        result = await self._risk_manager.evaluate_signal(signal)

        # Overflow check — after RM approval, before order placement (Sprint 27.95 S3b)
        if (
            isinstance(result, OrderApprovedEvent)
            and config.system.broker_source != BrokerSource.SIMULATED
            and config.system.overflow.enabled
            and getattr(self, '_order_manager', None) is not None
            and self._order_manager.open_position_count
            >= config.system.overflow.broker_capacity
        ):
            position_count = self._order_manager.open_position_count
            capacity = config.system.overflow.broker_capacity
            logger.info(
                "Signal overflow to counterfactual: %s %s (%d/%d positions)",
                signal.strategy_id,
                signal.symbol,
                position_count,
                capacity,
            )
            if getattr(self, '_counterfactual_enabled', False):
                regime_snapshot = self._capture_regime_snapshot()
                await self._event_bus.publish(SignalRejectedEvent(
                    signal=signal,
                    rejection_reason=(
                        f"Broker capacity reached ({position_count}/{capacity})"
                    ),
                    rejection_stage="broker_overflow",
                    quality_score=getattr(signal, 'quality_score', None),
                    quality_grade=getattr(signal, 'quality_grade', None),
                    regime_vector_snapshot=regime_snapshot,
                ))
            return

        await self._event_bus.publish(result)

        if getattr(self, '_counterfactual_enabled', False) and isinstance(result, OrderRejectedEvent):
            regime_snapshot = self._capture_regime_snapshot()
            await self._event_bus.publish(SignalRejectedEvent(
                signal=signal,
                rejection_reason=result.reason,
                rejection_stage="risk_manager",
                quality_score=getattr(signal, 'quality_score', None),
                quality_grade=getattr(signal, 'quality_grade', None),
                regime_vector_snapshot=regime_snapshot,
            ))

    def _grade_meets_minimum(self, grade: str, min_grade: str) -> bool:
        """Check if a quality grade meets the minimum threshold.

        Args:
            grade: The actual grade (e.g. "B+").
            min_grade: The minimum required grade (e.g. "C+").

        Returns:
            True if grade >= min_grade in the grade ordering.
        """
        from argus.intelligence.config import VALID_GRADES

        grade_order = {g: i for i, g in enumerate(reversed(VALID_GRADES))}
        return grade_order.get(grade, -1) >= grade_order.get(min_grade, 0)

    def _capture_regime_snapshot(self) -> dict[str, Any] | None:
        """Capture the current regime vector as a dict, if available.

        Returns:
            RegimeVector.to_dict() or None if no regime vector is set.
        """
        if self._orchestrator is not None:
            rv = getattr(self._orchestrator, 'latest_regime_vector', None)
            if rv is not None and hasattr(rv, 'to_dict'):
                return rv.to_dict()
        return None

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

    async def _on_signal_rejected_for_counterfactual(
        self, event: SignalRejectedEvent
    ) -> None:
        """Route rejected signals to the Counterfactual Engine for shadow tracking.

        Args:
            event: The SignalRejectedEvent to process.
        """
        if self._counterfactual_tracker is None or event.signal is None:
            return
        try:
            from argus.intelligence.counterfactual import RejectionStage

            self._counterfactual_tracker.track(
                signal=event.signal,
                rejection_reason=event.rejection_reason,
                rejection_stage=RejectionStage(event.rejection_stage),
                metadata={
                    "quality_score": event.quality_score,
                    "quality_grade": event.quality_grade,
                    "regime_vector_snapshot": event.regime_vector_snapshot,
                    **(event.metadata or {}),
                },
            )
        except Exception:
            logger.warning(
                "Counterfactual tracking failed for %s",
                event.signal.symbol,
                exc_info=True,
            )

    async def _run_counterfactual_maintenance(self) -> None:
        """Periodic counterfactual timeout check during market hours (60s).

        Also handles EOD close when market hours end.
        """
        from datetime import time as dt_time
        from zoneinfo import ZoneInfo

        et_tz = ZoneInfo("America/New_York")
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)
        eod_closed_today = False

        while True:
            await asyncio.sleep(60)
            try:
                if self._counterfactual_tracker is None:
                    continue
                now = self._clock.now()
                now_et = (
                    now.replace(tzinfo=et_tz) if now.tzinfo is None
                    else now.astimezone(et_tz)
                )
                current_time = now_et.time()

                if market_open <= current_time < market_close:
                    eod_closed_today = False
                    self._counterfactual_tracker.check_timeouts()
                elif not eod_closed_today:
                    # Market closed — close all remaining counterfactual positions
                    await self._counterfactual_tracker.close_all_eod()
                    eod_closed_today = True
                    logger.info("Counterfactual EOD close completed")
            except Exception:
                logger.warning("Counterfactual maintenance failed", exc_info=True)

    async def _on_shutdown_requested(self, event: ShutdownRequestedEvent) -> None:
        """Handle shutdown request from Order Manager after EOD flatten.

        Publishes SessionEndEvent for Learning Loop auto-trigger, then
        schedules graceful shutdown after the configured delay.

        Args:
            event: The shutdown request event with delay configuration.
        """
        delay = event.delay_seconds
        logger.info(
            "Auto-shutdown requested (reason=%s). Initiating in %ds...",
            event.reason,
            delay,
        )

        # Publish SessionEndEvent for Learning Loop (Amendment 13)
        await self._publish_session_end_event()

        # Schedule the delayed shutdown
        async def delayed_shutdown() -> None:
            await asyncio.sleep(delay)
            logger.info("Auto-shutdown initiated")
            self.request_shutdown()

        asyncio.create_task(delayed_shutdown())

    async def _publish_session_end_event(self) -> None:
        """Publish SessionEndEvent after EOD flatten completes.

        Gathers today's trade count and counterfactual count, then
        publishes SessionEndEvent on the Event Bus. Fire-and-forget.
        """
        from zoneinfo import ZoneInfo

        try:
            et_tz = ZoneInfo("America/New_York")
            trading_day = self._clock.now().astimezone(et_tz).strftime("%Y-%m-%d")

            trades_count = 0
            if self._trade_logger is not None:
                trades_count = await self._trade_logger.get_todays_trade_count()

            counterfactual_count = 0
            if self._counterfactual_tracker is not None:
                counterfactual_count = getattr(
                    self._counterfactual_tracker, "closed_position_count", 0
                )

            await self._event_bus.publish(
                SessionEndEvent(
                    trading_day=trading_day,
                    trades_count=trades_count,
                    counterfactual_count=counterfactual_count,
                )
            )
            logger.info(
                "SessionEndEvent published (day=%s, trades=%d, cf=%d)",
                trading_day,
                trades_count,
                counterfactual_count,
            )
        except Exception:
            logger.warning("Failed to publish SessionEndEvent", exc_info=True)

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

        # --- Counterfactual EOD close (before debrief export) ---
        if self._counterfactual_tracker is not None:
            try:
                await self._counterfactual_tracker.close_all_eod()
                logger.info("Counterfactual positions closed at shutdown")
            except Exception:
                logger.warning("Counterfactual EOD close failed", exc_info=True)

        # --- Debrief Export (before tearing down components) ---
        try:
            from argus.analytics.debrief_export import export_debrief_data
            from zoneinfo import ZoneInfo

            et_tz = ZoneInfo("America/New_York")
            session_date = self._clock.now().astimezone(et_tz).strftime("%Y-%m-%d")

            catalyst_db_path = None
            data_dir_str = getattr(
                getattr(self._config, 'system', self._config), 'data_dir', 'data'
            )
            if self._catalyst_storage is not None:
                catalyst_db_path = str(Path(data_dir_str) / "catalyst.db")

            export_path = await export_debrief_data(
                session_date=session_date,
                db=self._db,
                eval_store=self._eval_store,
                catalyst_db_path=catalyst_db_path,
                broker=self._broker,
                orchestrator=self._orchestrator,
                output_dir="logs",
            )
            if export_path:
                logger.info("Debrief data exported: %s", export_path)
            else:
                logger.warning("Debrief data export failed — see earlier warnings")
        except Exception as e:
            logger.warning("Debrief export error (non-fatal): %s", e)

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

        # 0a. Stop evaluation health check task
        if self._eval_check_task is not None:
            import contextlib as _ctxlib

            self._eval_check_task.cancel()
            with _ctxlib.suppress(asyncio.CancelledError):
                await self._eval_check_task
            logger.info("Evaluation health check task stopped")

        # 0a1. Stop regime reclassification task
        if self._regime_task is not None:
            import contextlib as _ctxlib2

            self._regime_task.cancel()
            with _ctxlib2.suppress(asyncio.CancelledError):
                await self._regime_task
            logger.info("Regime reclassification task stopped")

        # 0a1a. Stop position reconciliation task (Sprint 27.65)
        if self._reconciliation_task is not None:
            import contextlib as _ctxlib_recon

            self._reconciliation_task.cancel()
            with _ctxlib_recon.suppress(asyncio.CancelledError):
                await self._reconciliation_task
            logger.info("Position reconciliation task stopped")

        # 0a1b. Stop background cache refresh task (DEC-362)
        if self._bg_refresh_task is not None:
            import contextlib as _ctxlib3

            self._bg_refresh_task.cancel()
            with _ctxlib3.suppress(asyncio.CancelledError):
                await self._bg_refresh_task
            logger.info("Background cache refresh task stopped")

        # 0a1c. Stop counterfactual maintenance task (Sprint 27.7)
        if self._counterfactual_task is not None:
            import contextlib as _ctxlib_cf

            self._counterfactual_task.cancel()
            with _ctxlib_cf.suppress(asyncio.CancelledError):
                await self._counterfactual_task
            logger.info("Counterfactual maintenance task stopped")

        # 0a1d. Close counterfactual store (Sprint 27.7)
        if self._counterfactual_store is not None:
            await self._counterfactual_store.close()
            self._counterfactual_store = None
            logger.info("CounterfactualStore closed")

        # 0a2. Close evaluation telemetry store
        if self._eval_store is not None:
            await self._eval_store.close()
            self._eval_store = None
            logger.info("EvaluationEventStore closed")

        # 0b. Stop ActionManager cleanup task
        if self._action_manager is not None:
            logger.info("Stopping ActionManager cleanup task...")
            self._action_manager.stop_cleanup_task()

        # 1. Stop scanner
        if self._scanner:
            logger.info("Stopping scanner...")
            await self._scanner.stop()

        # 1a. Stop Universe Manager (saves reference cache)
        if self._universe_manager is not None:
            logger.info("Stopping Universe Manager...")
            ref_client = self._universe_manager._reference_client
            if ref_client is not None:
                await ref_client.stop()

        # 2. Stop data streams
        if self._data_service:
            logger.info("Stopping data service...")
            await self._data_service.stop()

        # 2a. Cancel all open orders at broker BEFORE stopping order manager
        if self._broker:
            try:
                count = await self._broker.cancel_all_orders()
                if count > 0:
                    logger.info("Shutdown: cancelled %d open orders at broker", count)
            except Exception as e:
                logger.warning("Failed to cancel orders during shutdown: %s", e)

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
