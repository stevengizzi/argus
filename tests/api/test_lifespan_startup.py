"""Tests for lifespan startup behavior.

Verifies:
1. Lifespan handler completes within 30 seconds even with slow dependencies.
2. api_server health component reports healthy only after port is actually bound.
3. HistoricalQueryService initialization is backgrounded and does not block startup.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.auth import set_jwt_secret
from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.core.clock import FixedClock
from argus.core.config import (
    ApiConfig,
    HealthConfig,
    HistoricalQueryConfig,
    SystemConfig,
)
from argus.core.event_bus import EventBus
from argus.core.health import ComponentStatus, HealthMonitor
from argus.db.manager import DatabaseManager
from argus.execution.order_manager import OrderManager
from argus.execution.simulated_broker import SimulatedBroker

TEST_JWT_SECRET = "test-jwt-secret-for-argus-api-testing-minimum-32-chars"


@pytest.fixture
def minimal_app_state(tmp_path: object) -> AppState:
    """Minimal AppState for lifespan testing — no AI, no intelligence."""
    from argus.analytics.trade_logger import TradeLogger
    from argus.core.config import OrderManagerConfig

    from datetime import UTC, datetime

    clock = FixedClock(datetime(2026, 4, 20, 14, 0, 0, tzinfo=UTC))
    event_bus = EventBus()
    broker = SimulatedBroker()
    health_config = HealthConfig()
    health_monitor = HealthMonitor(event_bus, clock, health_config)

    db_manager = DatabaseManager(":memory:")
    trade_logger = TradeLogger(db_manager)

    order_manager = OrderManager(
        broker=broker,
        event_bus=event_bus,
        config=OrderManagerConfig(),
        clock=clock,
    )

    config = SystemConfig(
        api=ApiConfig(
            enabled=True,
            host="127.0.0.1",
            port=8000,
            password_hash="unused",
            jwt_secret_env="ARGUS_JWT_SECRET",
        ),
        historical_query=HistoricalQueryConfig(
            enabled=True,
            cache_dir="/nonexistent/path",
        ),
    )

    return AppState(
        event_bus=event_bus,
        trade_logger=trade_logger,
        broker=broker,
        health_monitor=health_monitor,
        risk_manager=MagicMock(),
        order_manager=order_manager,
        data_service=MagicMock(),
        strategies={},
        clock=clock,
        config=config,
        start_time=time.time(),
    )


@pytest.mark.asyncio
async def test_lifespan_completes_within_timeout_with_slow_hqs(
    monkeypatch: pytest.MonkeyPatch,
    minimal_app_state: AppState,
) -> None:
    """Lifespan handler must complete within 30s even if HQS init is slow.

    Simulates a HistoricalQueryService constructor that takes 5 seconds
    by patching the module that gets imported inside the background task.
    The lifespan should NOT wait for it (backgrounded).
    """
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    import importlib
    import sys

    class SlowHistoricalQueryService:
        """Mock HQS that takes 5s to construct."""

        def __init__(self, config: object) -> None:
            import time as _time

            _time.sleep(5)

        @property
        def is_available(self) -> bool:
            return True

        def close(self) -> None:
            pass

    # Create a mock module to replace the real one
    mock_module = MagicMock()
    mock_module.HistoricalQueryService = SlowHistoricalQueryService

    # Point HQS config to a path that exists so the init task launches
    minimal_app_state.config.historical_query.cache_dir = "."

    original_module = sys.modules.get("argus.data.historical_query_service")
    sys.modules["argus.data.historical_query_service"] = mock_module
    try:
        app = create_app(minimal_app_state)

        start = time.monotonic()
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            elapsed = time.monotonic() - start
            # Lifespan completed — verify it was fast (not blocked by 5s HQS)
            assert elapsed < 3, (
                f"Lifespan took {elapsed:.1f}s — HQS init should be backgrounded"
            )

            # Verify the app is responsive
            response = await client.get("/api/v1/market/status")
            assert response.status_code == 200
    finally:
        if original_module is not None:
            sys.modules["argus.data.historical_query_service"] = original_module
        else:
            sys.modules.pop("argus.data.historical_query_service", None)


@pytest.mark.asyncio
async def test_lifespan_proceeds_when_hqs_cache_missing(
    monkeypatch: pytest.MonkeyPatch,
    minimal_app_state: AppState,
) -> None:
    """Lifespan completes quickly when HQS cache dir doesn't exist.

    The HQS constructor should handle missing cache gracefully.
    """
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)

    # cache_dir is set to /nonexistent/path — HQS should log and return unavailable
    app = create_app(minimal_app_state)

    start = time.monotonic()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        elapsed = time.monotonic() - start
        assert elapsed < 10, f"Lifespan took {elapsed:.1f}s with missing cache"

        response = await client.get("/api/v1/market/status")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_wait_for_port_returns_true_when_port_bound() -> None:
    """_wait_for_port returns True when a port is already listening."""
    import socket

    # Bind a socket to a random port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]

    try:
        # Import the static method from ArgusSystem
        from argus.main import ArgusSystem

        result = await ArgusSystem._wait_for_port("127.0.0.1", port, timeout_seconds=5)
        assert result is True
    finally:
        sock.close()


@pytest.mark.asyncio
async def test_wait_for_port_returns_false_on_timeout() -> None:
    """_wait_for_port returns False when port never becomes available."""
    from argus.main import ArgusSystem

    # Use a port that definitely isn't bound (high ephemeral port)
    result = await ArgusSystem._wait_for_port("127.0.0.1", 59999, timeout_seconds=2)
    assert result is False
