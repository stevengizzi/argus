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
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
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

        Sets up the JWT secret from config, attaches AppState to app.state,
        and starts the WebSocket bridge.
        """
        # Attach app_state to app.state for dependency injection
        app.state.app_state = app_state

        # Set JWT secret for auth module
        if app_state.config and app_state.config.api:
            from argus.api.auth import resolve_jwt_secret

            try:
                jwt_secret = resolve_jwt_secret(app_state.config.api)
                set_jwt_secret(jwt_secret)
            except Exception:
                # In tests, the secret may be set directly
                pass

        # Initialize AI services if not already done and if enabled
        ai_initialized_here = False
        if app_state.config and app_state.config.ai and app_state.config.ai.enabled:
            # Only initialize if not already set (e.g., by main.py)
            if app_state.ai_client is None:
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

                    # Initialize conversation manager, usage tracker, and action manager
                    # These require the database manager from trade_logger
                    db = app_state.trade_logger._db
                    app_state.conversation_manager = ConversationManager(db)
                    await app_state.conversation_manager.initialize()

                    app_state.usage_tracker = UsageTracker(db)
                    await app_state.usage_tracker.initialize()

                    app_state.action_manager = ActionManager(
                        db, app_state.event_bus, app_state.config.ai
                    )
                    await app_state.action_manager.initialize()
                    app_state.action_manager.start_cleanup_task()

                    # Initialize cache and summary generator for /insight endpoint
                    app_state.ai_cache = ResponseCache(
                        default_ttl=app_state.config.ai.cache_ttl_seconds
                    )
                    app_state.ai_summary_generator = DailySummaryGenerator(
                        client=app_state.ai_client,
                        usage_tracker=app_state.usage_tracker,
                        cache=app_state.ai_cache,
                    )

                    ai_initialized_here = True
                    logger.info(
                        "AI services initialized (ClaudeClient, PromptManager, "
                        "SystemContextBuilder, ConversationManager, UsageTracker, "
                        "ActionManager, DailySummaryGenerator, ResponseCache)"
                    )
                except Exception as e:
                    logger.error(f"Failed to initialize AI services: {e}")
        elif app_state.config and app_state.config.ai and not app_state.config.ai.enabled:
            logger.info("AI services disabled — no API key")

        # Initialize DebriefService (uses same DB as trade_logger)
        if app_state.debrief_service is None and app_state.trade_logger is not None:
            try:
                from argus.analytics.debrief_service import DebriefService

                db = app_state.trade_logger._db
                app_state.debrief_service = DebriefService(db)
                logger.info("DebriefService initialized")
            except Exception as e:
                logger.error(f"Failed to initialize DebriefService: {e}")

        # Initialize intelligence pipeline if enabled
        intelligence_initialized_here = False
        intelligence_components = None
        polling_task: asyncio.Task[None] | None = None
        if app_state.config and app_state.config.catalyst and app_state.config.catalyst.enabled:
            try:
                from argus.intelligence.startup import (
                    create_intelligence_components,
                    run_polling_loop,
                )

                intelligence_components = await create_intelligence_components(
                    config=app_state.config.catalyst,
                    event_bus=app_state.event_bus,
                    ai_client=app_state.ai_client,  # May be None if AI disabled
                    usage_tracker=app_state.usage_tracker,  # May be None
                    data_dir=app_state.config.data_dir,
                )

                if intelligence_components is not None:
                    await intelligence_components.pipeline.start()
                    app_state.catalyst_storage = intelligence_components.storage
                    app_state.briefing_generator = intelligence_components.briefing_generator
                    intelligence_initialized_here = True

                    # Register pipeline component with health monitor for frontend gating
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

                    # Create get_symbols callback for polling
                    catalyst_max = app_state.config.catalyst.max_batch_size

                    def get_symbols() -> list[str]:
                        # Priority 1: Scanner watchlist (15 symbols from FMP pre-market scan)
                        if app_state.cached_watchlist:
                            symbols = [item.symbol for item in app_state.cached_watchlist]
                            if symbols:
                                return symbols
                        # Priority 2: Viable universe capped at max_batch_size
                        if (
                            app_state.universe_manager is not None
                            and app_state.universe_manager.viable_count > 0
                        ):
                            all_viable = list(app_state.universe_manager.viable_symbols)
                            return all_viable[:catalyst_max]
                        return []

                    # Start polling loop task
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

                    polling_task = asyncio.create_task(
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
        elif (
            app_state.config
            and app_state.config.catalyst
            and not app_state.config.catalyst.enabled
        ):
            logger.info("Intelligence pipeline disabled")

        # Initialize quality engine + position sizer if enabled
        if app_state.config and app_state.config.quality_engine:
            try:
                from argus.intelligence.startup import create_quality_components

                db_manager = None
                if app_state.trade_logger is not None:
                    db_manager = app_state.trade_logger._db

                quality_result = create_quality_components(
                    config=app_state.config.quality_engine,
                    db_manager=db_manager,
                )

                if quality_result is not None:
                    app_state.quality_engine, app_state.position_sizer = quality_result

                    if app_state.health_monitor is not None:
                        from argus.core.health import ComponentStatus

                        app_state.health_monitor.update_component(
                            "quality_engine",
                            ComponentStatus.HEALTHY,
                            message="Quality engine + sizer active",
                        )

                    logger.info("Quality engine + position sizer initialized")
                else:
                    logger.info("Quality engine disabled in config")
            except Exception as e:
                logger.error(f"Failed to initialize quality components: {e}")

        # Initialize EvaluationEventStore for telemetry persistence
        # When launched from main.py, the store is pre-created and passed via app_state.
        # When launched standalone (--dev mode), create it here.
        _pre_initialized_store = app_state.telemetry_store
        telemetry_store = _pre_initialized_store
        if telemetry_store is None and app_state.trade_logger is not None:
            try:
                from argus.strategies.telemetry_store import EvaluationEventStore

                data_dir = app_state.config.data_dir if app_state.config else "data"
                db_path = str(Path(data_dir) / "evaluation.db")
                telemetry_store = EvaluationEventStore(db_path)
                await telemetry_store.initialize()
                await telemetry_store.cleanup_old_events()
                app_state.telemetry_store = telemetry_store

                # Wire store into each strategy's evaluation buffer
                for strategy in app_state.strategies.values():
                    strategy.eval_buffer.set_store(telemetry_store)

                logger.info("EvaluationEventStore initialized and wired to strategy buffers")
            except Exception as e:
                logger.error(f"Failed to initialize EvaluationEventStore: {e}")
        elif telemetry_store is not None:
            logger.info("EvaluationEventStore pre-initialized by main.py")

        # Initialize ObservatoryService if enabled (Sprint 25)
        if (
            app_state.config is not None
            and app_state.config.observatory is not None
            and app_state.config.observatory.enabled
        ):
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

        # Initialize VIXDataService if enabled (Sprint 27.9)
        vix_initialized_here = False
        if (
            app_state.config is not None
            and app_state.config.vix_regime is not None
            and app_state.config.vix_regime.enabled
        ):
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
                vix_initialized_here = True

                # Wire into Orchestrator and RegimeClassifierV2 if available
                if app_state.orchestrator is not None:
                    app_state.orchestrator._vix_data_service = vix_service
                    logger.info("VIXDataService wired into Orchestrator")

                    regime_v2 = getattr(
                        app_state.orchestrator, "_regime_classifier_v2", None
                    )
                    if regime_v2 is not None and hasattr(regime_v2, "_vix_data_service"):
                        regime_v2._vix_data_service = vix_service
                        logger.info(
                            "VIXDataService wired into RegimeClassifierV2"
                        )

                logger.info(
                    "VIXDataService initialized (ready=%s, stale=%s)",
                    vix_service.is_ready,
                    vix_service.is_stale,
                )
            except Exception as e:
                logger.warning("Failed to initialize VIXDataService: %s", e)
        elif (
            app_state.config is not None
            and app_state.config.vix_regime is not None
            and not app_state.config.vix_regime.enabled
        ):
            logger.info("VIXDataService disabled")

        # Note: WebSocket bridge is started by main.py before calling run_server().
        # We only need to get a reference to it here for cleanup.
        from argus.api.websocket import get_bridge

        bridge = get_bridge()

        yield

        # Cleanup on shutdown
        bridge.stop()

        # Cleanup AI services if we initialized them here
        if ai_initialized_here:
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

        # Cleanup intelligence pipeline if we initialized it here
        if intelligence_initialized_here and intelligence_components is not None:
            # Cancel polling task first
            if polling_task is not None:
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

        # Cleanup VIXDataService update task if we initialized it here
        if vix_initialized_here and app_state.vix_data_service is not None:
            update_task = app_state.vix_data_service._update_task
            if update_task is not None:
                update_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await update_task
                logger.info("VIXDataService update task cancelled")
            app_state.vix_data_service = None

        # Cleanup telemetry store (only if created by lifespan, not main.py)
        if telemetry_store is not None and telemetry_store is not _pre_initialized_store:
            await telemetry_store.close()
            app_state.telemetry_store = None
            logger.info("EvaluationEventStore closed")

    app = FastAPI(
        title="Argus Command Center API",
        description="REST and WebSocket API for the Argus trading system",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Configure CORS
    cors_origins = ["http://localhost:5173"]  # Default
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

    app.include_router(ws_router)
    app.include_router(ai_ws_router)

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
    print("Use --dev flag or run via argus.main for full system startup.")
    print("Example: python -m argus.api.server --dev")
