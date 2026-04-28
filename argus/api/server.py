"""FastAPI application factory for the Command Center API.

Creates and configures the FastAPI app with all routes, middleware, and
lifecycle handlers.

Usage:
    from argus.api.server import create_app
    from argus.api.dependencies import AppState

    app_state = AppState(event_bus=..., trade_logger=..., broker=..., ...)
    app = create_app(app_state)

    # Run with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

Lifespan structure (FIX-11 refactor):
    The ``lifespan`` handler used to be a single ~550-line block with
    nested try/except blocks for each of 10 optional subsystems. That was
    hard to audit and hard to extend. It's now a flat sequence of
    ``_init_<phase>()`` helpers that each return a teardown callable (or
    ``None``). The lifespan collects teardowns, yields, and runs them in
    reverse order on shutdown. Adding a new optional service is a new
    ``_init_<phase>`` helper plus one call in the lifespan body.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from argus.api.auth import set_jwt_secret
from argus.api.dependencies import AppState

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)

# A teardown returned by a phase initializer. Returning ``None`` means
# the phase has nothing to clean up (either because it was disabled, or
# because ownership of the resources lives elsewhere — e.g., main.py
# pre-created the telemetry store).
Teardown = Callable[[], Awaitable[None]]


# ---------------------------------------------------------------------------
# Lifespan phase initializers
# ---------------------------------------------------------------------------


def _set_jwt_secret(app_state: AppState) -> None:
    """Resolve and set the JWT secret from config (no teardown)."""
    if app_state.config and app_state.config.api:
        from argus.api.auth import resolve_jwt_secret

        try:
            jwt_secret = resolve_jwt_secret(app_state.config.api)
            set_jwt_secret(jwt_secret)
        except Exception:
            # In tests, the secret may be set directly
            pass


async def _init_ai_services(app_state: AppState) -> Teardown | None:
    """Initialize AI services (ClaudeClient, ConversationManager, etc.).

    Skips init when AI is disabled in config or when ``ai_client`` was
    already wired by main.py.
    """
    if not (app_state.config and app_state.config.ai):
        return None
    if not app_state.config.ai.enabled:
        logger.info("AI services disabled — no API key")
        return None
    if app_state.ai_client is not None:
        # Already initialized (e.g., by main.py)
        return None

    try:
        from argus.ai.actions import ActionManager
        from argus.ai.cache import ResponseCache
        from argus.ai.client import ClaudeClient
        from argus.ai.context import SystemContextBuilder
        from argus.ai.conversations import ConversationManager
        from argus.ai.prompts import PromptManager
        from argus.ai.summary import DailySummaryGenerator
        from argus.ai.usage import UsageTracker

        app_state.ai_client = ClaudeClient(app_state.config.ai)
        app_state.prompt_manager = PromptManager(app_state.config.ai)
        app_state.context_builder = SystemContextBuilder()

        db = app_state.trade_logger.db_manager
        app_state.conversation_manager = ConversationManager(db)
        await app_state.conversation_manager.initialize()

        app_state.usage_tracker = UsageTracker(db)
        await app_state.usage_tracker.initialize()

        app_state.action_manager = ActionManager(
            db, app_state.event_bus, app_state.config.ai
        )
        await app_state.action_manager.initialize()
        app_state.action_manager.start_cleanup_task()

        app_state.ai_cache = ResponseCache(
            default_ttl=app_state.config.ai.cache_ttl_seconds
        )
        app_state.ai_summary_generator = DailySummaryGenerator(
            client=app_state.ai_client,
            usage_tracker=app_state.usage_tracker,
            cache=app_state.ai_cache,
        )

        logger.info(
            "AI services initialized (ClaudeClient, PromptManager, "
            "SystemContextBuilder, ConversationManager, UsageTracker, "
            "ActionManager, DailySummaryGenerator, ResponseCache)"
        )
    except Exception as e:
        logger.error(f"Failed to initialize AI services: {e}")
        return None

    async def _teardown() -> None:
        if app_state.action_manager is not None:
            app_state.action_manager.stop_cleanup_task()
        app_state.ai_client = None
        app_state.prompt_manager = None
        app_state.context_builder = None
        app_state.conversation_manager = None
        app_state.usage_tracker = None
        app_state.action_manager = None
        app_state.ai_summary_generator = None
        app_state.ai_cache = None
        logger.info("AI services cleaned up")

    return _teardown


async def _init_debrief_service(app_state: AppState) -> Teardown | None:
    """Initialize DebriefService (uses same DB as trade_logger)."""
    if app_state.debrief_service is not None or app_state.trade_logger is None:
        return None
    try:
        from argus.analytics.debrief_service import DebriefService

        db = app_state.trade_logger.db_manager
        app_state.debrief_service = DebriefService(db)
        logger.info("DebriefService initialized")
    except Exception as e:
        logger.error(f"Failed to initialize DebriefService: {e}")
    # DebriefService has no explicit teardown (DB handle is owned by
    # TradeLogger).
    return None


async def _init_intelligence_pipeline(app_state: AppState) -> Teardown | None:
    """Initialize Intelligence Pipeline + polling task."""
    if not (app_state.config and app_state.config.catalyst):
        return None
    if not app_state.config.catalyst.enabled:
        logger.info("Intelligence pipeline disabled")
        return None

    try:
        from argus.intelligence.startup import (
            create_intelligence_components,
            run_polling_loop,
        )

        intelligence_components = await create_intelligence_components(
            config=app_state.config.catalyst,
            event_bus=app_state.event_bus,
            ai_client=app_state.ai_client,
            usage_tracker=app_state.usage_tracker,
            data_dir=app_state.config.data_dir,
        )

        if intelligence_components is None:
            return None

        await intelligence_components.pipeline.start()
        app_state.catalyst_storage = intelligence_components.storage
        app_state.briefing_generator = intelligence_components.briefing_generator

        if app_state.health_monitor is not None:
            from argus.core.health import ComponentStatus

            app_state.health_monitor.update_component(
                "catalyst_pipeline",
                ComponentStatus.HEALTHY,
                message=f"{len(intelligence_components.sources)} sources active",
            )

        logger.info(
            "Intelligence pipeline initialized (%d sources)",
            len(intelligence_components.sources),
        )

        catalyst_max = app_state.config.catalyst.max_batch_size

        def get_symbols() -> list[str]:
            if app_state.cached_watchlist:
                symbols = [item.symbol for item in app_state.cached_watchlist]
                if symbols:
                    return symbols
            if (
                app_state.universe_manager is not None
                and app_state.universe_manager.viable_count > 0
            ):
                all_viable = list(app_state.universe_manager.viable_symbols)
                return all_viable[:catalyst_max]
            return []

        def _poll_task_done(task: asyncio.Task[None]) -> None:
            if task.cancelled():
                logger.info("Intelligence polling task was cancelled")
            elif task.exception():
                logger.critical(
                    "Intelligence polling task CRASHED: %s",
                    task.exception(),
                    exc_info=task.exception(),
                )
            else:
                logger.warning("Intelligence polling task exited cleanly (unexpected)")

        polling_task: asyncio.Task[None] = asyncio.create_task(
            run_polling_loop(
                pipeline=intelligence_components.pipeline,
                config=app_state.config.catalyst,
                get_symbols=get_symbols,
                firehose=True,
            )
        )
        polling_task.add_done_callback(_poll_task_done)
        app_state.intelligence_polling_task = polling_task
        logger.info("Intelligence polling loop started")
    except Exception as e:
        logger.error(f"Failed to initialize intelligence pipeline: {e}")
        return None

    async def _teardown() -> None:
        polling_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await polling_task
        logger.info("Intelligence polling loop stopped")

        try:
            from argus.intelligence.startup import shutdown_intelligence

            await shutdown_intelligence(intelligence_components)
        except Exception as e:
            logger.error(f"Failed to shutdown intelligence pipeline: {e}")
        app_state.catalyst_storage = None
        app_state.briefing_generator = None
        logger.info("Intelligence pipeline cleaned up")

    return _teardown


async def _init_quality_engine(app_state: AppState) -> Teardown | None:
    """Initialize quality engine + position sizer."""
    if not (app_state.config and app_state.config.quality_engine):
        return None

    try:
        from argus.intelligence.startup import create_quality_components

        db_manager = None
        if app_state.trade_logger is not None:
            db_manager = app_state.trade_logger.db_manager

        quality_result = create_quality_components(
            config=app_state.config.quality_engine,
            db_manager=db_manager,
        )

        if quality_result is None:
            logger.info("Quality engine disabled in config")
            return None

        app_state.quality_engine, app_state.position_sizer = quality_result

        if app_state.health_monitor is not None:
            from argus.core.health import ComponentStatus

            app_state.health_monitor.update_component(
                "quality_engine",
                ComponentStatus.HEALTHY,
                message="Quality engine + sizer active",
            )

        logger.info("Quality engine + position sizer initialized")
    except Exception as e:
        logger.error(f"Failed to initialize quality components: {e}")

    # Quality engine has no explicit teardown — DB is owned by TradeLogger.
    return None


async def _init_telemetry_store(app_state: AppState) -> Teardown | None:
    """Initialize EvaluationEventStore for telemetry persistence.

    When launched from main.py, the store is pre-created and passed via
    app_state. When launched standalone, create it here and wire into
    each strategy's buffer.
    """
    pre_initialized = app_state.telemetry_store
    if pre_initialized is not None:
        logger.info("EvaluationEventStore pre-initialized by main.py")
        return None

    if app_state.trade_logger is None:
        return None

    try:
        from argus.strategies.telemetry_store import EvaluationEventStore

        data_dir = app_state.config.data_dir if app_state.config else "data"
        db_path = str(Path(data_dir) / "evaluation.db")
        telemetry_store = EvaluationEventStore(db_path)
        await telemetry_store.initialize()
        await telemetry_store.cleanup_old_events()
        app_state.telemetry_store = telemetry_store

        for strategy in app_state.strategies.values():
            strategy.eval_buffer.set_store(telemetry_store)

        logger.info("EvaluationEventStore initialized and wired to strategy buffers")
    except Exception as e:
        logger.error(f"Failed to initialize EvaluationEventStore: {e}")
        return None

    async def _teardown() -> None:
        # Guard: only close if still the same instance we created.
        if app_state.telemetry_store is not None and app_state.telemetry_store is not pre_initialized:
            await app_state.telemetry_store.close()
            app_state.telemetry_store = None
            logger.info("EvaluationEventStore closed")

    return _teardown


async def _init_observatory_service(app_state: AppState) -> Teardown | None:
    """Initialize ObservatoryService (Sprint 25)."""
    if not (
        app_state.config is not None
        and app_state.config.observatory is not None
        and app_state.config.observatory.enabled
    ):
        return None

    try:
        from argus.analytics.observatory_service import ObservatoryService

        app_state.observatory_service = ObservatoryService(
            telemetry_store=app_state.telemetry_store,
            universe_manager=app_state.universe_manager,
            quality_engine=app_state.quality_engine,
            strategies=app_state.strategies,
        )
        logger.info("ObservatoryService initialized")
    except Exception as e:
        logger.error(f"Failed to initialize ObservatoryService: {e}")
    return None


async def _init_vix_data_service(app_state: AppState) -> Teardown | None:
    """Initialize VIXDataService (Sprint 27.9) and wire into Orchestrator."""
    if not (app_state.config is not None and app_state.config.vix_regime is not None):
        return None
    if not app_state.config.vix_regime.enabled:
        logger.info("VIXDataService disabled")
        return None

    try:
        from argus.data.vix_data_service import VIXDataService

        vix_service = VIXDataService(config=app_state.config.vix_regime)
        try:
            await vix_service.initialize()
        except Exception as e:
            logger.warning(
                "VIXDataService initialization failed (degraded mode): %s", e
            )

        app_state.vix_data_service = vix_service

        # Public setter wiring (DEF-091) — forwards to RegimeClassifierV2.
        if app_state.orchestrator is not None:
            app_state.orchestrator.attach_vix_service(vix_service)
            logger.info(
                "VIXDataService wired into Orchestrator "
                "(forwarded to RegimeClassifierV2 if present)"
            )

        logger.info(
            "VIXDataService initialized (ready=%s, stale=%s)",
            vix_service.is_ready,
            vix_service.is_stale,
        )
    except Exception as e:
        logger.warning("Failed to initialize VIXDataService: %s", e)
        return None

    async def _teardown() -> None:
        if app_state.vix_data_service is not None:
            await app_state.vix_data_service.shutdown()
            logger.info("VIXDataService update task cancelled")
            app_state.vix_data_service = None

    return _teardown


async def _init_learning_loop(app_state: AppState) -> Teardown | None:
    """Initialize Learning Loop (Sprint 28)."""
    if not (
        app_state.config is not None
        and app_state.config.learning_loop is not None
    ):
        return None
    if not app_state.config.learning_loop.enabled:
        logger.info("Learning Loop disabled")
        return None

    try:
        from argus.intelligence.learning.config_proposal_manager import (
            ConfigProposalManager,
        )
        from argus.intelligence.learning.correlation_analyzer import (
            CorrelationAnalyzer,
        )
        from argus.intelligence.learning.learning_service import LearningService
        from argus.intelligence.learning.learning_store import LearningStore
        from argus.intelligence.learning.outcome_collector import OutcomeCollector
        from argus.intelligence.learning.threshold_analyzer import (
            ThresholdAnalyzer,
        )
        from argus.intelligence.learning.weight_analyzer import WeightAnalyzer

        ll_config = app_state.config.learning_loop
        data_dir = app_state.config.data_dir

        learning_store = LearningStore(db_path=str(Path(data_dir) / "learning.db"))
        await learning_store.initialize()
        # DEF-173: mirror the experiment-store retention pattern so learning.db
        # doesn't grow unbounded. Protected APPLIED/REVERTED proposal reports
        # are skipped by enforce_retention's SQL (Amendment 11). See
        # docs/sprints/post-31.9-component-ownership/DISCOVERY.md for why
        # this component will move out of api/server.py lifespan into main.py
        # in the post-31.9 sprint (DEF-175).
        try:
            await learning_store.enforce_retention(ll_config.report_retention_days)
        except Exception:
            logger.warning(
                "LearningStore retention enforcement failed", exc_info=True
            )

        outcome_collector = OutcomeCollector(
            argus_db_path=str(Path(data_dir) / "argus.db"),
            counterfactual_db_path=str(Path(data_dir) / "counterfactual.db"),
        )

        weight_analyzer = WeightAnalyzer()
        threshold_analyzer = ThresholdAnalyzer()
        correlation_analyzer = CorrelationAnalyzer()

        learning_service = LearningService(
            config=ll_config,
            outcome_collector=outcome_collector,
            weight_analyzer=weight_analyzer,
            threshold_analyzer=threshold_analyzer,
            correlation_analyzer=correlation_analyzer,
            store=learning_store,
        )

        config_proposal_manager = ConfigProposalManager(
            config=ll_config,
            store=learning_store,
        )

        # Apply pending proposals at startup (Amendment 1)
        applied_ids = await config_proposal_manager.apply_pending()
        if applied_ids:
            logger.info(
                "Applied %d pending config proposals at startup",
                len(applied_ids),
            )

        # Wire auto-trigger via Event Bus (Amendment 13)
        learning_service.register_auto_trigger(app_state.event_bus)

        app_state.learning_service = learning_service
        app_state.learning_store = learning_store
        app_state.config_proposal_manager = config_proposal_manager

        logger.info("Learning Loop initialized")
    except Exception as e:
        logger.error("Failed to initialize Learning Loop: %s", e)
        return None

    async def _teardown() -> None:
        app_state.learning_service = None
        app_state.learning_store = None
        app_state.config_proposal_manager = None
        logger.info("Learning Loop cleaned up")

    return _teardown


async def _init_experiments(app_state: AppState) -> Teardown | None:
    """Initialize Experiment pipeline (Sprint 32)."""
    if not (
        app_state.config is not None
        and app_state.config.experiments is not None
    ):
        return None
    if not app_state.config.experiments.enabled:
        logger.info("Experiment pipeline disabled")
        return None

    try:
        from argus.intelligence.experiments.store import ExperimentStore

        data_dir = app_state.config.data_dir
        experiment_store = ExperimentStore(
            db_path=str(Path(data_dir) / "experiments.db")
        )
        await experiment_store.initialize()
        app_state.experiment_store = experiment_store
        logger.info("ExperimentStore initialized")
    except Exception as e:
        logger.error("Failed to initialize ExperimentStore: %s", e)
        return None

    async def _teardown() -> None:
        app_state.experiment_store = None
        logger.info("ExperimentStore cleaned up")

    return _teardown


async def _init_historical_query_service(app_state: AppState) -> Teardown | None:
    """Initialize Historical Query Service (Sprint 31A.5).

    The HQS constructor scans the entire Parquet cache directory (potentially
    hundreds of thousands of files), which can take minutes. To avoid
    blocking the lifespan handler, we run it in a background task.
    """
    if not (
        app_state.config is not None
        and app_state.config.historical_query is not None
    ):
        return None
    if not app_state.config.historical_query.enabled:
        logger.info("Historical Query Service disabled")
        return None

    hqs_config = app_state.config.historical_query

    async def _init_in_background() -> None:
        try:
            from argus.data.historical_query_service import HistoricalQueryService

            service = await asyncio.to_thread(HistoricalQueryService, hqs_config)
            app_state.historical_query_service = service
            if service.is_available:
                logger.info("Historical Query Service initialized (DuckDB)")
            else:
                logger.warning(
                    "Historical Query Service enabled but cache unavailable"
                )
        except Exception as e:
            logger.error("Failed to initialize Historical Query Service: %s", e)

    hqs_init_task: asyncio.Task[None] = asyncio.create_task(_init_in_background())
    logger.info("Historical Query Service initialization started (background)")

    async def _teardown() -> None:
        if not hqs_init_task.done():
            hqs_init_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await hqs_init_task
            logger.info("Historical Query Service init task cancelled")
        if app_state.historical_query_service is not None:
            app_state.historical_query_service.close()
            app_state.historical_query_service = None
            logger.info("Historical Query Service closed")

    return _teardown


# Registry of lifespan phase initializers, run in order.
# Each returns an optional async teardown callable. Teardowns run in
# reverse order on shutdown.
_LIFESPAN_PHASES: tuple[tuple[str, Callable[[AppState], Awaitable[Teardown | None]]], ...] = (
    ("ai_services", _init_ai_services),
    ("debrief_service", _init_debrief_service),
    ("intelligence_pipeline", _init_intelligence_pipeline),
    ("quality_engine", _init_quality_engine),
    ("telemetry_store", _init_telemetry_store),
    ("observatory_service", _init_observatory_service),
    ("vix_data_service", _init_vix_data_service),
    ("learning_loop", _init_learning_loop),
    ("experiments", _init_experiments),
    ("historical_query_service", _init_historical_query_service),
)


def create_app(app_state: AppState) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        app_state: The shared application state with all system components.

    Returns:
        Configured FastAPI application instance.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """App lifespan handler for startup/shutdown.

        Attaches AppState to app.state, runs each registered lifespan phase
        in order, then tears them down in reverse order on shutdown. Each
        phase handles its own exceptions — a failure in one phase does not
        abort the others, but is logged at ERROR/WARNING.
        """
        app.state.app_state = app_state
        _set_jwt_secret(app_state)

        teardowns: list[tuple[str, Teardown]] = []
        for name, init_fn in _LIFESPAN_PHASES:
            try:
                teardown = await init_fn(app_state)
            except Exception as e:
                logger.error("Lifespan phase %s raised: %s", name, e)
                teardown = None
            if teardown is not None:
                teardowns.append((name, teardown))

        # Reference to the WebSocket bridge (started by main.py before
        # run_server()); we only need it for shutdown.
        from argus.api.websocket import get_bridge

        bridge = get_bridge()

        yield

        # Cleanup on shutdown
        bridge.stop()

        # Run teardowns in reverse order so later phases clean up first.
        for name, teardown in reversed(teardowns):
            try:
                await teardown()
            except Exception as e:
                logger.error("Lifespan phase %s teardown raised: %s", name, e)

    app = FastAPI(
        title="Argus Command Center API",
        description="REST and WebSocket API for the Argus trading system",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Configure CORS — default is Vite dev origin (see ApiConfig docstring
    # for the override note for Tauri / PWA deployments).
    cors_origins = ["http://localhost:5173"]
    if app_state.config and app_state.config.api:
        cors_origins = app_state.config.api.cors_origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API routes
    from argus.api.routes import api_router

    app.include_router(api_router, prefix="/api/v1")

    # Mount Observatory routes (config-gated — Sprint 25)
    observatory_enabled = (
        app_state.config is not None
        and app_state.config.observatory is not None
        and app_state.config.observatory.enabled
    )
    if observatory_enabled:
        from argus.api.routes.observatory import router as observatory_router

        app.include_router(
            observatory_router,
            prefix="/api/v1/observatory",
            tags=["observatory"],
        )

    # Mount WebSocket routes (no prefix)
    from argus.api.websocket import ai_ws_router, ws_router
    from argus.api.websocket.alerts_ws import alerts_ws_router
    from argus.api.websocket.arena_ws import arena_ws_router

    app.include_router(ws_router)
    app.include_router(ai_ws_router)
    app.include_router(arena_ws_router)
    app.include_router(alerts_ws_router)

    # Mount Observatory WebSocket (config-gated — Sprint 25 S2)
    if observatory_enabled:
        from argus.api.websocket.observatory_ws import observatory_ws_router

        app.include_router(observatory_ws_router)

    # Mount static files if configured
    if app_state.config and app_state.config.api and app_state.config.api.static_dir:
        static_path = Path(app_state.config.api.static_dir)
        if static_path.exists() and static_path.is_dir():
            from fastapi.staticfiles import StaticFiles

            app.mount("/", StaticFiles(directory=static_path, html=True), name="static")

    return app


class PortInUseError(Exception):
    """Raised when the requested port is already in use."""

    pass


def check_port_available(host: str, port: int) -> bool:
    """Check if a port is available for binding.

    Attempts to bind a socket to the specified host:port. If successful,
    the port is available. The socket is closed immediately after the check.

    Args:
        host: Host address to check.
        port: Port number to check.

    Returns:
        True if port is available, False if already in use.
    """
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
        sock.close()
        return True
    except OSError:
        return False


async def run_server(app: FastAPI, host: str, port: int) -> asyncio.Task[None]:
    """Start uvicorn programmatically in the existing event loop.

    Checks port availability before starting to provide a clear error message
    if another instance is already running on the same port.

    Args:
        app: The FastAPI application instance.
        host: Host address to bind to.
        port: Port number to bind to.

    Returns:
        The asyncio.Task running the server, so caller can cancel on shutdown.

    Raises:
        PortInUseError: If the port is already in use.
    """
    import uvicorn

    # Defense in depth: check port availability before starting uvicorn
    if not check_port_available(host, port):
        logger.critical(
            "Port %d already in use — cannot start API server. "
            "Is another ARGUS instance running?",
            port,
        )
        raise PortInUseError(
            f"Port {port} already in use. Is another ARGUS instance running?"
        )

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    # Disable uvicorn's signal handlers to avoid conflict with main.py
    server.install_signal_handlers = lambda: None  # type: ignore[method-assign]

    # Create and return the task
    return asyncio.create_task(server.serve())


if __name__ == "__main__":
    print("Start the API via 'python -m argus.main' for full system startup.")
