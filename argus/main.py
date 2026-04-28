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
from collections.abc import Callable
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
    ArgusConfig,
    BrokerSource,
    DataServiceConfig,
    DataSource,
    load_afternoon_momentum_config,
    load_bull_flag_config,
    load_config,
    load_abcd_config,
    load_dip_and_rip_config,
    load_flat_top_breakout_config,
    load_gap_and_go_config,
    load_hod_break_config,
    load_micro_pullback_config,
    load_narrow_range_breakout_config,
    load_vwap_bounce_config,
    load_orb_config,
    load_premarket_high_break_config,
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
    SystemAlertEvent,
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
from argus.execution.order_manager import OrderManager, ReconciliationPosition
from argus.strategies.afternoon_momentum import AfternoonMomentumStrategy
from argus.strategies.pattern_strategy import PatternBasedStrategy
from argus.strategies.patterns.factory import (
    build_pattern_from_config,
    compute_parameter_fingerprint,
    get_pattern_class,
)
from argus.strategies.red_to_green import RedToGreenStrategy
from argus.strategies.telemetry_store import EvaluationEventStore
from argus.strategies.orb_base import OrbBaseStrategy
from argus.strategies.orb_breakout import OrbBreakoutStrategy
from argus.strategies.orb_scalp import OrbScalpStrategy
from argus.strategies.vwap_reclaim import VwapReclaimStrategy
from argus.utils.log_throttle import ThrottledLogger
# fmt: on

if TYPE_CHECKING:
    from argus.core.clock import Clock
    from argus.core.regime_history import RegimeHistoryStore
    from argus.data.scanner import Scanner
    from argus.data.service import DataService
    from argus.execution.broker import Broker

logger = logging.getLogger(__name__)
_throttled = ThrottledLogger(logger)


def check_startup_position_invariant(
    positions: list[Any],
) -> tuple[bool, list[str]]:
    """Long-only startup invariant for broker-reported positions (DEF-199 defense).

    ARGUS is long-only today. If the broker returns any position whose
    ``side`` is not ``OrderSide.BUY``, the invariant is violated and caller
    MUST disable auto startup-cleanup — a blind SELL of a short doubles it
    (the DEF-199 mechanism, now blocked at the EOD filter level too).

    Fails closed: a position object that is missing a ``side`` attribute
    entirely (novel broker adapter drift) is treated as a violation rather
    than silently passed through.

    Args:
        positions: Output of ``broker.get_positions()`` — list of Position
            or Position-shaped duck objects.

    Returns:
        ``(ok, violations)`` where ``ok`` is True iff every position has
        ``side == OrderSide.BUY``, and ``violations`` is a list of short
        descriptor strings suitable for logging.
    """
    from argus.models.trading import OrderSide

    violations: list[str] = []
    for pos in positions:
        symbol = getattr(pos, "symbol", "?")
        shares = getattr(pos, "shares", "?")
        # Use a sentinel that is definitely not OrderSide.BUY so missing-attr
        # cases fail closed (below).
        _sentinel = object()
        side = getattr(pos, "side", _sentinel)
        if side is _sentinel:
            violations.append(f"{symbol}(shares={shares}, side=MISSING)")
            continue
        if side != OrderSide.BUY:
            violations.append(f"{symbol}({shares} shares, side={side!r})")
    return (len(violations) == 0, violations)


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
        # DEF-199 defense: set True in startup() when check_startup_position_invariant
        # detects any non-long broker position at connect time. Gates the
        # reconstruct_from_broker auto-cleanup call to prevent the DEF-199
        # double-short scenario (blind SELL against an existing short).
        self._startup_flatten_disabled: bool = False
        self._data_service: DataService | None = None
        self._scanner: Scanner | None = None
        self._risk_manager: RiskManager | None = None
        self._order_manager: OrderManager | None = None
        self._health_monitor: HealthMonitor | None = None
        self._orchestrator: Orchestrator | None = None
        self._api_task: asyncio.Task[None] | None = None
        self._config: ArgusConfig | None = None  # Store config for API access
        self._cached_watchlist: list[Any] = []  # Scanner results for API watchlist endpoint
        self._universe_manager: UniverseManager | None = None
        # Strategy dict for candle routing (BaseStrategy per value via isinstance narrowing)
        self._strategies: dict[str, Any] = {}
        # Sprint 24: Quality pipeline components (initialized after DB + config)
        self._quality_engine: SetupQualityEngine | None = None
        self._position_sizer: DynamicPositionSizer | None = None
        self._catalyst_storage: object | None = None  # CatalystStorage, if pipeline active
        self._regime_history_store: RegimeHistoryStore | None = None  # Sprint 27.6, closed on shutdown
        self._eval_check_task: asyncio.Task[None] | None = None
        self._eval_store: EvaluationEventStore | None = None  # Sprint 25.6: reused in health check
        # _run_regime_reclassification task removed FIX-03 P1-A1-M10 / DEF-074 —
        # Orchestrator._poll_loop already runs the same reclassify cadence.
        self._regime_check_count: int = 0  # Sprint 25.9: counter for INFO logging cadence
        self._bg_refresh_task: asyncio.Task[None] | None = None
        self._reconciliation_task: asyncio.Task[None] | None = None  # Sprint 27.65: position recon
        self._candle_store: IntradayCandleStore | None = None  # Sprint 27.65 S4: intraday bar store
        self._counterfactual_enabled: bool = False  # Sprint 27.7 S3b sets True after tracker init
        self._counterfactual_tracker: object | None = None
        self._counterfactual_store: object | None = None
        self._counterfactual_task: asyncio.Task[None] | None = None  # Sprint 27.7: maintenance task
        self._promotion_evaluator: object | None = None
        self._experiments_auto_promote: bool = False  # Sprint 32 S7: auto_promote config flag
        # Sprint 32.9 / FIX-03 P1-A1-L05: one-shot log per session for signal
        # cutoff, keyed on the ET session date so multi-day runs re-log.
        self._cutoff_logged_date: str | None = None
        # Closure-captured CandleEvent handlers (FIX-03 P1-A1-L01).
        self._breadth_candle_handler: Callable[[CandleEvent], Any] | None = None
        self._intraday_candle_handler: Callable[[CandleEvent], Any] | None = None
        # Variant exit overrides collected during spawning (FIX-03 P1-D2-M01).
        self._variant_exit_overrides: dict[str, dict[str, Any]] = {}
        # DEF-164 (IMPROMPTU-07, 2026-04-23): monotonic boot timestamp used
        # by _on_shutdown_requested to suppress auto-shutdown during the
        # post-boot grace window. Set at the top of start(); None pre-start
        # so early shutdown requests (shouldn't happen) don't pass the
        # "0s elapsed" suppression test by accident.
        self._boot_monotonic: float | None = None

    async def start(self) -> None:
        """Initialize and start all components in dependency order.

        Live phase sequence (see ``docs/architecture.md`` §3.9 for the full
        per-phase breakdown). Twelve primary phases plus seven sub-phases
        (7.5, 8.5, 9.5, 10.25, 10.3, 10.4, 10.7) bolted on as features landed
        — 19 phases total. (IMPROMPTU-07 DEF-198, 2026-04-23: the "five
        config-gated sub-phases" language in the original FIX-03 docstring
        miscounted 9.5 and 10.4.):

        1. Config + Clock + EventBus (no dependencies)
        2. Database + TradeLogger + AI persistence (needs config)
        3. Broker connection (IBKR / Alpaca / Simulated — lazy-imported)
        4. HealthMonitor
        5. RiskManager (+ state reconstruction from trade log)
        6. DataService (Databento or Alpaca)
        7. Scanner (pre-market scan)
        7.5. Universe Manager (config-gated, non-simulated only)
        8. Strategies (ORB + ORB Scalp + VWAP Reclaim + Afternoon Momentum +
           Red-to-Green + table-driven PatternBasedStrategy roster)
        8.5. Regime Intelligence V2 (config-gated)
        9. Orchestrator (+ experiment-variant spawning + telemetry-store
           wiring + run_pre_market). Mid-day restart state rehydrates via
           PatternBasedStrategy.backfill_candles() from IntradayCandleStore
           and strategy.reconstruct_state(trade_logger); the prior separate
           _reconstruct_strategy_state replay path was removed (audit
           2026-04-21 FIX-03 P1-A1-C01).
        9.5. Build routing table (UM-gated)
        10. OrderManager (+ per-strategy exit overrides, including any
            experiment-variant overrides collected during spawning)
        10.25. Quality Pipeline (config-gated)
        10.3. Telemetry Store — initialized in phase 9 (see P1-A1-M08);
              retained as a numbering anchor for architecture.md
        10.4. Event Routing (renumbered from 10.5 per audit)
        10.7. Counterfactual Engine (config-gated)
        11. Start data streaming + background loops
        12. API Server (optional, in-process FastAPI)

        Regime reclassification cadence is owned by Orchestrator._poll_loop.
        """
        logger.info("=" * 60)
        logger.info("ARGUS TRADING SYSTEM — STARTING")
        logger.info("=" * 60)

        # DEF-164: capture boot time before any phase begins so the
        # shutdown-grace computation in _on_shutdown_requested covers the
        # full init window (including the long HistoricalQueryService
        # Parquet-view build during Phase 11).
        self._boot_monotonic = time.monotonic()

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

        # Initialize AI persistence tables.
        # NOTE: AI writes (conversations, messages, proposals, usage) share the
        # argus.db SQLite write lock with TradeLogger. If latency spikes during
        # active trading + chat, consider WAL mode or a separate ai.db file.
        # (FIX-03 P1-A1-L08: dangling "RSK-NEW-5" reference removed.)
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

        # --- Holiday Check (between Phase 1 and Phase 3) ---
        from argus.core.market_calendar import get_next_trading_day, is_market_holiday

        _is_holiday, _holiday_name = is_market_holiday()
        if _is_holiday:
            logger.info("Market holiday today: %s — US equity markets are closed", _holiday_name)
            logger.info("Next trading day: %s", get_next_trading_day())

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
            # FIX-03 P1-C1-M03: lazy-import to match IBKR/Simulated pattern so
            # alpaca-py is only required on Alpaca incubator deployments.
            from argus.execution.alpaca_broker import AlpacaBroker

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

        # DEF-199 defense: post-connect long-only invariant check.
        # ARGUS is long-only today. If the broker returns any short position at
        # connect, something has gone wrong upstream (prior session zombie,
        # manual short, DEF-199 residue) and auto startup-cleanup must NOT run —
        # a blind SELL against a short doubles it. Fail-closed on any exception.
        try:
            startup_positions = await self._broker.get_positions()
            ok, violations = check_startup_position_invariant(startup_positions)
            if ok:
                self._startup_flatten_disabled = False
                if startup_positions:
                    logger.info(
                        "Startup invariant: %d broker positions at connect, "
                        "all long — auto-cleanup enabled.",
                        len(startup_positions),
                    )
            else:
                self._startup_flatten_disabled = True
                logger.error(
                    "STARTUP INVARIANT VIOLATED: broker returned %d non-long "
                    "position(s) at connect: %s. ARGUS is long-only; auto "
                    "startup-cleanup DISABLED for this session. Investigate "
                    "and cover manually before next startup.",
                    len(violations),
                    ", ".join(violations),
                )
        except Exception as e:
            # Fail-closed: if we can't verify, disable auto-cleanup.
            self._startup_flatten_disabled = True
            logger.error(
                "STARTUP INVARIANT check failed (%s). Disabling auto "
                "startup-cleanup for this session.", e,
            )

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
            # FIX-03 P1-A1-M09: surface subsystem state to /health.
            if self._universe_manager is not None:
                self._health_monitor.update_component(
                    "universe_manager", ComponentStatus.HEALTHY
                )
            else:
                self._health_monitor.update_component(
                    "universe_manager",
                    ComponentStatus.DEGRADED,
                    message="build failed — scanner fallback",
                )
        else:
            logger.info("Universe Manager disabled or simulated broker mode")
            self._health_monitor.update_component(
                "universe_manager", ComponentStatus.DEGRADED, message="disabled"
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

        # PatternBasedStrategy roster (DEC-275 collapse, FIX-03 P1-A1-M04/M05).
        # Adding a new pattern = one row here. The prior code cloned this 18-line
        # block ten times and again in the register cascade + variant spawner.
        pattern_definitions: list[tuple[str, str, Callable[[Path], Any]]] = [
            ("bull_flag", "BullFlag", load_bull_flag_config),
            ("flat_top_breakout", "FlatTopBreakout", load_flat_top_breakout_config),
            ("dip_and_rip", "DipAndRip", load_dip_and_rip_config),
            ("hod_break", "HODBreak", load_hod_break_config),
            ("abcd", "ABCD", load_abcd_config),
            ("gap_and_go", "GapAndGo", load_gap_and_go_config),
            ("premarket_high_break", "PreMarketHighBreak", load_premarket_high_break_config),
            ("micro_pullback", "MicroPullback", load_micro_pullback_config),
            ("vwap_bounce", "VwapBounce", load_vwap_bounce_config),
            ("narrow_range_breakout", "NarrowRangeBreakout", load_narrow_range_breakout_config),
        ]

        pattern_strategies: dict[str, PatternBasedStrategy] = {}
        for pattern_name, display_name, loader in pattern_definitions:
            yaml_path = self._config_dir / "strategies" / f"{pattern_name}.yaml"
            if not yaml_path.exists():
                continue
            pattern_config = loader(yaml_path)
            pattern = build_pattern_from_config(pattern_config, pattern_name)
            strategy = PatternBasedStrategy(
                pattern=pattern,
                config=pattern_config,
                data_service=self._data_service,
                clock=self._clock,
            )
            strategy.set_config_fingerprint(
                compute_parameter_fingerprint(pattern_config, get_pattern_class(pattern_name))
            )
            if not use_universe_manager:
                strategy.set_watchlist(symbols)
            pattern_strategies[pattern_name] = strategy
            strategies_created.append(display_name)

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

            orchestrator_config_pre = config.orchestrator

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
                self._regime_history_store = regime_history_store
                logger.info("RegimeHistoryStore initialized: %s", history_db_path)

            logger.info("Regime intelligence V2 ready")
            self._health_monitor.update_component(
                "regime_classifier_v2", ComponentStatus.HEALTHY
            )
        else:
            # FIX-03 P1-A1-M09: report disabled subsystems explicitly.
            self._health_monitor.update_component(
                "regime_classifier_v2", ComponentStatus.DEGRADED, message="disabled"
            )

        # --- Phase 9: Orchestrator ---
        logger.info("[9/12] Initializing orchestrator...")
        orchestrator_config = config.orchestrator
        OrbBaseStrategy.mutual_exclusion_enabled = orchestrator_config.orb_family_mutual_exclusion
        logger.info(
            "[9/12] ORB family mutual exclusion: %s",
            orchestrator_config.orb_family_mutual_exclusion,
        )
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
        for pattern_strategy in pattern_strategies.values():
            self._orchestrator.register_strategy(pattern_strategy)

        # --- Experiment Variant Spawning (Sprint 32, Session 5) ---
        # Config-gated: skipped entirely when experiments.enabled is false (default).
        # Failure is non-fatal — base system startup continues regardless.
        _experiments_yaml_path = self._config_dir / "experiments.yaml"
        if _experiments_yaml_path.exists():
            _experiments_yaml = load_yaml_file(_experiments_yaml_path)
            if _experiments_yaml.get("enabled", False):
                try:
                    from argus.intelligence.experiments import ExperimentStore
                    from argus.intelligence.experiments.spawner import VariantSpawner

                    # Map pattern snake_case name → (config, strategy) for each
                    # registered base PatternBasedStrategy.
                    _base_pattern_strategies: dict[
                        str, tuple[Any, PatternBasedStrategy]
                    ] = {
                        name: (strat.config, strat)
                        for name, strat in pattern_strategies.items()
                    }

                    _experiment_db_path = str(
                        Path(config.system.data_dir) / "experiments.db"
                    )
                    _experiment_store = ExperimentStore(db_path=_experiment_db_path)
                    await _experiment_store.initialize()
                    # FIX-03 P1-D2-M03: mirror the counterfactual retention
                    # pattern so experiments.db doesn't grow unbounded.
                    try:
                        await _experiment_store.enforce_retention(max_age_days=90)
                    except Exception:
                        logger.warning(
                            "ExperimentStore retention enforcement failed",
                            exc_info=True,
                        )
                    self._experiments_auto_promote = bool(
                        _experiments_yaml.get("auto_promote", False)
                    )

                    _variant_spawner = VariantSpawner(
                        _experiment_store, _experiments_yaml
                    )
                    _variant_strategies = await _variant_spawner.spawn_variants(
                        _base_pattern_strategies,
                        data_service=self._data_service,
                        clock=self._clock,
                    )

                    # FIX-03 P1-D2-M01: collect variant exit overrides so they
                    # flow into OrderManager's strategy_exit_overrides when it
                    # is built in Phase 10. Otherwise a variant with
                    # `exit_overrides:` in experiments.yaml silently gets the
                    # base pattern's exit config.
                    for _variant_strategy in _variant_strategies:
                        self._orchestrator.register_strategy(_variant_strategy)
                        _var_exit = getattr(_variant_strategy, "_exit_overrides", None)
                        if _var_exit:
                            self._variant_exit_overrides[
                                _variant_strategy.strategy_id
                            ] = _var_exit

                    # Wire promotion evaluator (Sprint 32 S7).
                    # Counterfactual store and trade logger may be None if
                    # their subsystems are disabled; PromotionEvaluator accepts
                    # duck-typed dependencies and handles missing data gracefully.
                    from argus.intelligence.experiments.promotion import (
                        PromotionEvaluator,
                    )

                    self._promotion_evaluator = PromotionEvaluator(
                        store=_experiment_store,
                        counterfactual_store=self._counterfactual_store,
                        trade_logger=self._trade_logger,
                        config=_experiments_yaml,
                    )

                    logger.info(
                        "[9/12] Experiment variants spawned: %d",
                        len(_variant_strategies),
                    )
                except Exception:
                    logger.error(
                        "Experiment variant spawning failed — "
                        "base system startup continues",
                        exc_info=True,
                    )

        await self._orchestrator.start()

        # --- Phase 10.3: Telemetry store (moved earlier, FIX-03 P1-A1-M08) ---
        # Used to live after run_pre_market(), which meant any ENTRY_EVALUATION
        # emitted during mid-day reconstruction replay hit an in-memory ring
        # buffer with no store attached and was lost on the next buffer wrap.
        # Init the store and wire it into every registered strategy before
        # pre-market can emit anything.
        logger.info("[10.3/12] Initializing telemetry store...")
        try:
            eval_db_path = str(Path(config.system.data_dir) / "evaluation.db")
            self._eval_store = EvaluationEventStore(eval_db_path)
            await self._eval_store.initialize()
            await self._eval_store.cleanup_old_events()
            for strategy in self._orchestrator.get_strategies().values():
                strategy.eval_buffer.set_store(self._eval_store)
            logger.info("EvaluationEventStore initialized: %s", eval_db_path)
            self._health_monitor.update_component(
                "evaluation_store", ComponentStatus.HEALTHY
            )
        except Exception as e:
            logger.error("Failed to initialize EvaluationEventStore: %s", e)
            self._eval_store = None
            self._health_monitor.update_component(
                "evaluation_store", ComponentStatus.DEGRADED, message=str(e)
            )

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

        # Run pre-market routine (sets regime, allocations, activates strategies).
        # Mid-day restart: PatternBasedStrategy.backfill_candles() rehydrates from
        # IntradayCandleStore on first candle per symbol (DEC-368). Trade counts /
        # daily P&L rehydrated by strategy.reconstruct_state(trade_logger) inside
        # orchestrator.run_pre_market() step 0.
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

            # Initialize reference data (prior_closes) for PatternBasedStrategy
            # patterns that use set_reference_data() — PMH and GapAndGo (Sprint 31A S2)
            for strategy in strategies.values():
                if isinstance(strategy, PatternBasedStrategy):
                    ref_data_pattern = {
                        sym: self._universe_manager.get_reference_data(sym)
                        for sym in strategy.watchlist
                    }
                    valid_ref_pattern = {
                        s: r for s, r in ref_data_pattern.items() if r is not None
                    }
                    strategy.initialize_reference_data(valid_ref_pattern)

        # --- Phase 10: Order Manager ---
        logger.info("[10/12] Starting order manager...")
        order_manager_yaml = load_yaml_file(self._config_dir / "order_manager.yaml")
        from argus.core.config import ExitManagementConfig, OrderManagerConfig

        # Legacy trailing stop fields (enable_trailing_stop,
        # trailing_stop_atr_multiplier) removed from OrderManagerConfig in
        # FIX-16 (audit 2026-04-21, DEF-109). Trailing stops now live entirely
        # in config/exit_management.yaml via ExitManagementConfig (Sprint 28.5).
        order_manager_config = OrderManagerConfig(**order_manager_yaml)

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

        # Merge in experiment-variant exit overrides collected during spawning
        # (FIX-03 P1-D2-M01). Variant overrides take precedence over any YAML
        # override sharing the same strategy_id since a variant is intentionally
        # configured to differ from its base.
        strategy_exit_overrides.update(self._variant_exit_overrides)

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
            operations_db_path=str(
                Path(config.system.data_dir) / "operations.db"
            ),
        )
        # Sprint 31.91 Session 2c.1: M5 — rehydrate phantom-short gate
        # state BEFORE the OrderManager subscribes to OrderApprovedEvent.
        # Without this ordering, ~60s of unsafe entries on restart could
        # land before the next reconciliation re-detects the phantom
        # short and re-engages the gate. ``order_manager.start()`` is
        # what subscribes to OrderApprovedEvent, so the rehydration must
        # precede it.
        await self._order_manager._rehydrate_gated_symbols_from_db()
        # Sprint 31.91 Session 2d (D5, L3 + L15): emit startup alerts
        # for any gated symbols that survived the prior session. The
        # rehydration call above already logs CRITICAL when symbols are
        # loaded; this block adds the explicit "operator triage required"
        # log line + L3 always-both-alerts emission (per-symbol alerts
        # ALWAYS fire; aggregate alert fires only if count >= L15
        # threshold). Threshold is configurable via
        # ``reconciliation.phantom_short_aggregate_alert_threshold``.
        if self._order_manager._phantom_short_gated_symbols:
            gated_list = sorted(
                self._order_manager._phantom_short_gated_symbols
            )
            logger.critical(
                "STARTUP: %d phantom-short gated symbol(s) rehydrated from "
                "prior session: %s. These symbols will reject new entries. "
                "See docs/live-operations.md 'Phantom-Short Gate Diagnosis "
                "and Clearance' for operator triage steps.",
                len(gated_list),
                gated_list,
            )
            agg_threshold = (
                config.system.reconciliation
                .phantom_short_aggregate_alert_threshold
            )
            # L15 configurable threshold gates the aggregate alert.
            if len(gated_list) >= agg_threshold:
                await self._event_bus.publish(
                    SystemAlertEvent(
                        severity="critical",
                        source="startup",
                        alert_type="phantom_short_startup_engaged",
                        message=(
                            f"STARTUP: {len(gated_list)} phantom-short "
                            f"symbols rehydrated (threshold: "
                            f"{agg_threshold}). Operator triage required."
                        ),
                        metadata={
                            "gated_symbols": gated_list,
                            "count": len(gated_list),
                            "threshold": agg_threshold,
                        },
                    )
                )
            # L3 always-both-alerts: per-symbol alerts ALWAYS fire,
            # regardless of whether the aggregate fired. Operator needs
            # both signals — aggregate to know "many symbols gated";
            # per-symbol to triage each one.
            for symbol in gated_list:
                await self._event_bus.publish(
                    SystemAlertEvent(
                        severity="critical",
                        source="startup",
                        alert_type="phantom_short",
                        message=(
                            f"STARTUP: phantom-short gate rehydrated "
                            f"for {symbol}. Operator triage required."
                        ),
                        metadata={
                            "symbol": symbol,
                            "side": "SELL",
                            "detection_source": "startup.rehydration",
                        },
                    )
                )
        await self._order_manager.start()
        # Reconstruct open positions from broker — gated by the startup
        # invariant (DEF-199 defense). If any short was detected at connect
        # time, skip the entire reconstruction path. This is conservative:
        # legit bracket-equipped long positions also won't be reconstructed,
        # but the operator must investigate manually anyway (any short is a
        # red flag), and the alternative — per-position flatten-decision
        # plumbing through the Order Manager — has broader blast radius.
        if self._startup_flatten_disabled:
            logger.warning(
                "Skipping Order Manager reconstruct_from_broker — startup "
                "invariant violated. Reconstruct manually after investigating "
                "the short positions flagged above."
            )
        else:
            await self._order_manager.reconstruct_from_broker()
        self._health_monitor.update_component("order_manager", ComponentStatus.HEALTHY)

        # Wire strategy fingerprints into Order Manager (Sprint 32 scope gap fix)
        for strategy in self._orchestrator.get_strategies().values():
            fingerprint = getattr(strategy, "config_fingerprint", None)
            self._order_manager.register_strategy_fingerprint(
                strategy.strategy_id, fingerprint
            )

        # Wire Risk Manager to Order Manager for cross-strategy checks
        self._risk_manager.set_order_manager(self._order_manager)

        # --- Phase 10.25: Quality Pipeline (Sprint 24) ---
        logger.info("[10.25/12] Initializing quality pipeline...")
        qe_config = config.system.quality_engine
        if qe_config.enabled and config.system.broker_source != BrokerSource.SIMULATED:
            self._quality_engine = SetupQualityEngine(qe_config, db_manager=self._db)
            self._position_sizer = DynamicPositionSizer(qe_config)
            # Create CatalystStorage for quality lookups (catalyst data).
            # FIX-01 (audit 2026-04-21 DEF-082 / P1-D1 C1): path is catalyst.db
            # — the same DB the intelligence pipeline writes into via
            # argus/intelligence/startup.py. Previously this pointed at
            # argus.db, which CatalystStorage.initialize() would populate
            # with an empty catalyst_events table, causing the quality
            # engine's _score_catalyst_quality() to return the neutral
            # default (50.0) for every signal.
            if self._catalyst_storage is None:
                db_path = Path(config.system.data_dir) / "catalyst.db"
                try:
                    from argus.intelligence.storage import CatalystStorage

                    self._catalyst_storage = CatalystStorage(str(db_path))
                    await self._catalyst_storage.initialize()
                except Exception:
                    # FIX-03 P1-A1-M07 / P1-D1-M02: include exception + db_path
                    # so a misconfigured/locked/missing catalyst DB is diagnosable.
                    logger.warning(
                        "CatalystStorage not available for quality pipeline "
                        "(db_path=%s); catalyst_quality scoring will default.",
                        db_path,
                        exc_info=True,
                    )
            logger.info("Quality pipeline initialized (engine + sizer)")
            # FIX-03 P1-A1-M09: health visibility for optional subsystem.
            self._health_monitor.update_component(
                "quality_engine", ComponentStatus.HEALTHY
            )
        else:
            logger.info(
                "Quality pipeline disabled (enabled=%s, broker=%s)",
                qe_config.enabled,
                config.system.broker_source,
            )

        # --- Phase 10.4: Event Routing ---
        # FIX-03 P1-A1-L07: renumbered from 10.5 to free the 10.5 slot for
        # architecture.md §3.9's "Set viable universe on DataService" (now
        # lives in Phase 11 streaming prep).
        logger.info("[10.4/12] Wiring event routing...")
        # IntradayCandleStore — parallel CandleEvent subscriber (Sprint 27.65 S4)
        self._candle_store = IntradayCandleStore()
        self._event_bus.subscribe(CandleEvent, self._candle_store.on_candle)
        # FIX-03 P1-A1-M09: health visibility.
        self._health_monitor.update_component(
            "candle_store", ComponentStatus.HEALTHY
        )

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
        # FIX-03 P1-A1-L01: retain handler refs on self so a future restart-in-place
        # path can unsubscribe them from the event bus.
        if breadth_calc is not None:
            _bc = breadth_calc

            async def _breadth_on_candle(event: CandleEvent) -> None:
                _bc.on_candle(event)

            self._breadth_candle_handler = _breadth_on_candle
            self._event_bus.subscribe(CandleEvent, _breadth_on_candle)
            logger.info("BreadthCalculator subscribed to CandleEvent")
        if intraday_detector is not None:
            _id = intraday_detector

            async def _intraday_on_candle(event: CandleEvent) -> None:
                _id.on_candle(event)

            self._intraday_candle_handler = _intraday_on_candle
            self._event_bus.subscribe(CandleEvent, _intraday_on_candle)
            logger.info("IntradayCharacterDetector subscribed to CandleEvent")

        # --- Phase 10.7: Counterfactual Engine (Sprint 27.7) ---
        logger.info("[10.7/12] Initializing counterfactual engine...")
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
            # FIX-03 P1-A1-M09: health visibility.
            self._health_monitor.update_component(
                "counterfactual_tracker", ComponentStatus.HEALTHY
            )
        else:
            self._health_monitor.update_component(
                "counterfactual_tracker", ComponentStatus.DEGRADED, message="disabled"
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
                    # Wait for the port to actually be bound before marking healthy.
                    # run_server() returns a task immediately; the lifespan handler
                    # may still be executing. Probe the port with a timeout.
                    api_host = config.system.api.host
                    api_port = config.system.api.port
                    api_ready = await self._wait_for_port(
                        api_host if api_host != "0.0.0.0" else "127.0.0.1",
                        api_port,
                        timeout_seconds=60,
                    )
                    if api_ready:
                        logger.info(
                            "API server started on %s:%d",
                            api_host,
                            api_port,
                        )
                        self._health_monitor.update_component(
                            "api_server",
                            ComponentStatus.HEALTHY,
                            message=f"http://{api_host}:{api_port}",
                        )
                    else:
                        logger.error(
                            "API server task started but port %d never became "
                            "reachable within 60s — marking DEGRADED",
                            api_port,
                        )
                        self._health_monitor.update_component(
                            "api_server",
                            ComponentStatus.DEGRADED,
                            message=f"Port {api_port} not reachable after 60s",
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

        # Regime reclassification cadence is owned by Orchestrator._poll_loop
        # (FIX-03 P1-A1-M10 / DEF-074). The main.py 300s task that used to run
        # here duplicated _poll_loop's work verbatim — same reclassify_regime()
        # call, same DB write path, same RegimeChangeEvent emission.

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

    @staticmethod
    async def _wait_for_port(
        host: str, port: int, timeout_seconds: int = 60
    ) -> bool:
        """Poll a TCP port until it accepts connections or timeout.

        Args:
            host: Host to probe.
            port: Port number to probe.
            timeout_seconds: Maximum seconds to wait.

        Returns:
            True if the port became reachable, False on timeout.
        """
        import socket

        deadline = asyncio.get_event_loop().time() + timeout_seconds
        while asyncio.get_event_loop().time() < deadline:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            try:
                sock.connect((host, port))
                sock.close()
                return True
            except (ConnectionRefusedError, OSError):
                sock.close()
            await asyncio.sleep(0.5)
        return False

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
            # FIX-03 P1-A1-L06: sleep-first (aligned with other loops), avoids
            # a boot-time burst before dependencies are fully warm.
            await asyncio.sleep(60)
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

                    # Get broker positions and convert to typed dict.
                    # Sprint 31.91 Session 2a (DEC-385 reserved): the
                    # contract is now ``dict[str, ReconciliationPosition]``
                    # so the broker's side travels end-to-end and downstream
                    # reconciliation reads cannot be silently long-only-blind
                    # (the structural cause of DEF-204).
                    broker_pos_list = await self._broker.get_positions()
                    broker_positions: dict[str, ReconciliationPosition] = {}
                    for pos in broker_pos_list:
                        symbol = getattr(pos, "symbol", "")
                        # ``Position.shares`` is the broker's absolute size
                        # (IBKR may report negative for shorts; `abs` is
                        # defensive against either signing convention).
                        shares = int(abs(getattr(pos, "shares", 0)))
                        side = getattr(pos, "side", None)
                        if not symbol or shares == 0:
                            continue
                        if side is None:
                            # Fail-closed: a position without a side cannot
                            # be safely reconciled. Skip and log CRITICAL;
                            # the orphan loop's broker-orphan branch
                            # (Session 2b.1) will detect via separate
                            # mechanisms.
                            logger.critical(
                                "Reconciliation skipped %s: broker Position missing "
                                "side attribute. This indicates a broker-layer bug "
                                "or a Position object constructed without side. "
                                "Sprint 31.91 (DEF-204 mechanism) hardens against "
                                "this.",
                                symbol,
                            )
                            continue
                        broker_positions[symbol] = ReconciliationPosition(
                            symbol=symbol, side=side, shares=shares
                        )

                    # Order Manager logs consolidated mismatch summary at WARNING
                    await self._order_manager.reconcile_positions(
                        broker_positions
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

        # Re-initialize reference data for PatternBasedStrategy patterns (Sprint 31A S2)
        for strategy in self._strategies.values():
            if isinstance(strategy, PatternBasedStrategy):
                ref_data_pattern = {
                    sym: self._universe_manager.get_reference_data(sym)
                    for sym in strategy.watchlist
                }
                valid_ref_pattern = {
                    s: r for s, r in ref_data_pattern.items() if r is not None
                }
                strategy.initialize_reference_data(valid_ref_pattern)

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
        # Pre-EOD signal cutoff (Sprint 32.9) — no new entries after cutoff time
        orchestrator_cfg = getattr(self._config, "orchestrator", None)
        _clock = getattr(self, "_clock", None)
        if orchestrator_cfg is not None and _clock is not None and getattr(orchestrator_cfg, "signal_cutoff_enabled", False):
            from datetime import time as dt_time
            from zoneinfo import ZoneInfo
            et_tz = ZoneInfo("America/New_York")
            now_et = _clock.now().astimezone(et_tz)
            cutoff = dt_time.fromisoformat(orchestrator_cfg.signal_cutoff_time)
            if now_et.time() >= cutoff:
                session_date = now_et.strftime("%Y-%m-%d")
                if self._cutoff_logged_date != session_date:
                    logger.info(
                        "Pre-EOD signal cutoff active at %s ET — "
                        "no new entries until next session",
                        now_et.time().isoformat()[:5],
                    )
                    self._cutoff_logged_date = session_date
                if self._order_manager is not None:
                    self._order_manager.increment_signal_cutoff()
                return

        # Shadow mode routing (Sprint 27.7)
        strategy_mode = getattr(
            getattr(strategy, 'config', None), 'mode', 'live'
        )
        if strategy_mode == "shadow":
            if getattr(self, '_counterfactual_enabled', False):
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
                    # FIX-03 P1-A1-M06: downgraded from debug to throttled
                    # warning so a DB outage is visible without flooding logs.
                    _throttled.warn_throttled(
                        key=f"catalyst_lookup:{signal.symbol}",
                        message=(
                            f"Catalyst lookup failed for {signal.symbol} — "
                            f"quality scoring will default catalyst_quality"
                        ),
                    )
                    logger.debug(
                        "Catalyst lookup traceback for %s",
                        signal.symbol,
                        exc_info=True,
                    )

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

        DEF-164 (IMPROMPTU-07, 2026-04-23): when a late-night boot fires
        after EOD — or when an EOD flatten queues a ShutdownRequested event
        immediately after a reboot — honour the boot grace window so the
        shutdown doesn't tear down HistoricalQueryService (or any other
        slow phase-11 component) mid-init. See CLAUDE.md DEF-164 + DEF-165
        for the interrupt-close interaction.

        Args:
            event: The shutdown request event with delay configuration.
        """
        if (
            self._config is not None
            and self._boot_monotonic is not None
            and self._config.order_manager.auto_shutdown_boot_grace_minutes > 0
        ):
            grace_seconds = (
                self._config.order_manager.auto_shutdown_boot_grace_minutes * 60
            )
            elapsed = time.monotonic() - self._boot_monotonic
            if elapsed < grace_seconds:
                logger.info(
                    "Auto-shutdown deferred (reason=%s): boot grace window "
                    "active (elapsed=%.1fs / grace=%ds). Per DEF-164, a "
                    "shutdown fired during boot can tear down slow-init "
                    "components (HistoricalQueryService CREATE VIEW) "
                    "mid-flight. Boot will continue; no shutdown scheduled.",
                    event.reason,
                    elapsed,
                    grace_seconds,
                )
                return

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

        # --- Autonomous promotion evaluator (Sprint 32 S7) ---
        # Runs after SessionEndEvent is published so the Learning Loop (which
        # subscribes to that event) has been triggered first.
        # Gated by experiments.enabled (self._promotion_evaluator is only set
        # when experiments are enabled) AND experiments.auto_promote.
        # Wrapped in try/except — promotion failure must NOT prevent shutdown.
        if self._promotion_evaluator is not None and self._experiments_auto_promote:
            try:
                from argus.intelligence.experiments.promotion import PromotionEvaluator

                evaluator: PromotionEvaluator = self._promotion_evaluator  # type: ignore[assignment]
                promotion_events = await evaluator.evaluate_all_variants()
                for promo_event in promotion_events:
                    if promo_event.action == "promote":
                        logger.info(
                            "Promoted variant %s from shadow to live",
                            promo_event.variant_id,
                        )
                    else:
                        logger.info(
                            "Demoted variant %s from live to shadow",
                            promo_event.variant_id,
                        )
                    # Apply mode change to in-memory strategy so subsequent signals
                    # are routed correctly without restart.
                    # _process_signal() reads strategy.config.mode at signal time,
                    # making this the first intraday mode adaptation in ARGUS.
                    if self._orchestrator is not None:
                        strategies = self._orchestrator.get_strategies()
                        matching = strategies.get(promo_event.variant_id)
                        if matching is not None and hasattr(matching, "config"):
                            matching.config.mode = promo_event.new_mode
                            logger.debug(
                                "In-memory mode updated: %s → %s",
                                promo_event.variant_id,
                                promo_event.new_mode,
                            )
            except Exception:
                logger.warning(
                    "Promotion evaluator failed — session cleanup continues",
                    exc_info=True,
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

            counterfactual_db_path = str(Path(data_dir_str) / "counterfactual.db")
            experiment_db_path = str(Path(data_dir_str) / "experiments.db")

            export_path = await export_debrief_data(
                session_date=session_date,
                db=self._db,
                eval_store=self._eval_store,
                catalyst_db_path=catalyst_db_path,
                broker=self._broker,
                orchestrator=self._orchestrator,
                output_dir="logs",
                counterfactual_db_path=counterfactual_db_path,
                experiment_db_path=experiment_db_path,
                order_manager=self._order_manager,
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

        # 0a. Cancel all background tasks in batch
        background_tasks: list[asyncio.Task[None]] = []
        task_names: list[str] = []
        for task, name in [
            (self._eval_check_task, "evaluation health check"),
            (self._reconciliation_task, "position reconciliation"),
            (self._bg_refresh_task, "background cache refresh"),
            (self._counterfactual_task, "counterfactual maintenance"),
        ]:
            if task is not None:
                task.cancel()
                background_tasks.append(task)
                task_names.append(name)

        if background_tasks:
            await asyncio.gather(*background_tasks, return_exceptions=True)
            logger.info(
                "Background tasks stopped: %s", ", ".join(task_names)
            )

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

        # 5a. Close analytical SQLite stores (symmetric with counterfactual/eval).
        # FIX-03 P1-A1-M03 / P1-D1-M01: previously relied on process teardown.
        if self._catalyst_storage is not None:
            try:
                await self._catalyst_storage.close()
                logger.info("CatalystStorage closed")
            except Exception:
                logger.warning("CatalystStorage close failed", exc_info=True)
            self._catalyst_storage = None
        if self._regime_history_store is not None:
            try:
                await self._regime_history_store.close()
                logger.info("RegimeHistoryStore closed")
            except Exception:
                logger.warning("RegimeHistoryStore close failed", exc_info=True)
            self._regime_history_store = None

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
