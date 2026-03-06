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
                    from argus.ai.client import ClaudeClient
                    from argus.ai.context import SystemContextBuilder
                    from argus.ai.conversations import ConversationManager
                    from argus.ai.prompts import PromptManager
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

                    ai_initialized_here = True
                    logger.info(
                        "AI services initialized (ClaudeClient, PromptManager, "
                        "SystemContextBuilder, ConversationManager, UsageTracker, ActionManager)"
                    )
                except Exception as e:
                    logger.error(f"Failed to initialize AI services: {e}")
        elif app_state.config and app_state.config.ai and not app_state.config.ai.enabled:
            logger.info("AI services disabled — no API key")

        # Start WebSocket bridge for event streaming
        from argus.api.websocket import get_bridge

        bridge = get_bridge()
        if app_state.config and app_state.config.api:
            bridge.start(app_state.event_bus, app_state.order_manager, app_state.config.api)

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
            logger.info("AI services cleaned up")

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

    # Mount WebSocket routes (no prefix)
    from argus.api.websocket import ai_ws_router, ws_router

    app.include_router(ws_router)
    app.include_router(ai_ws_router)

    # Mount static files if configured
    if app_state.config and app_state.config.api and app_state.config.api.static_dir:
        static_path = Path(app_state.config.api.static_dir)
        if static_path.exists() and static_path.is_dir():
            from fastapi.staticfiles import StaticFiles

            app.mount("/", StaticFiles(directory=static_path, html=True), name="static")

    return app


async def run_server(app: FastAPI, host: str, port: int) -> asyncio.Task[None]:
    """Start uvicorn programmatically in the existing event loop.

    Args:
        app: The FastAPI application instance.
        host: Host address to bind to.
        port: Port number to bind to.

    Returns:
        The asyncio.Task running the server, so caller can cancel on shutdown.
    """
    import uvicorn

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    # Disable uvicorn's signal handlers to avoid conflict with main.py
    server.install_signal_handlers = lambda: None  # type: ignore[method-assign]

    # Create and return the task
    return asyncio.create_task(server.serve())


if __name__ == "__main__":
    print("Use --dev flag or run via argus.main for full system startup.")
    print("Example: python -m argus.api.server --dev")
