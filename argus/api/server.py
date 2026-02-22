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
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from argus.api.auth import set_jwt_secret
from argus.api.dependencies import AppState

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


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

        # Start WebSocket bridge for event streaming
        from argus.api.websocket import get_bridge

        bridge = get_bridge()
        if app_state.config and app_state.config.api:
            bridge.start(app_state.event_bus, app_state.order_manager, app_state.config.api)

        yield

        # Cleanup on shutdown
        bridge.stop()

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
    from argus.api.websocket import ws_router

    app.include_router(ws_router)

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
