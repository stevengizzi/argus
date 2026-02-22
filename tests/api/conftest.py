"""Shared test fixtures for Command Center API tests.

These fixtures provide everything needed to test API routes:
- api_config: ApiConfig with test password hash
- jwt_secret: Monkeypatched env var for JWT signing
- app_state: Full AppState with real EventBus, in-memory TradeLogger, SimulatedBroker
- client: httpx.AsyncClient wrapping the FastAPI app
- auth_headers: Pre-built Authorization header with valid JWT
"""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from argus.analytics.trade_logger import TradeLogger
from argus.api.auth import create_access_token, hash_password, set_jwt_secret
from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.core.clock import FixedClock
from argus.core.config import ApiConfig, HealthConfig, OrderManagerConfig, SystemConfig
from argus.core.event_bus import EventBus
from argus.core.health import HealthMonitor
from argus.core.risk_manager import RiskManager
from argus.db.manager import DatabaseManager
from argus.execution.order_manager import OrderManager
from argus.execution.simulated_broker import SimulatedBroker

# Test password - the hash is generated from this
TEST_PASSWORD = "testpassword123"
TEST_JWT_SECRET = "test-jwt-secret-for-argus-api-testing-minimum-32-chars"


@pytest.fixture
def api_config() -> ApiConfig:
    """Provide an ApiConfig with a pre-computed password hash for testing.

    The password hash is for "testpassword123".
    """
    return ApiConfig(
        enabled=True,
        host="127.0.0.1",
        port=8000,
        password_hash=hash_password(TEST_PASSWORD),
        jwt_secret_env="ARGUS_JWT_SECRET",
        jwt_expiry_hours=24,
        cors_origins=["http://localhost:5173"],
        ws_heartbeat_interval_seconds=30,
        ws_tick_throttle_ms=1000,
    )


@pytest.fixture
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    """Monkeypatch the ARGUS_JWT_SECRET env var and return the secret.

    Also sets the module-level JWT secret in auth.py.
    """
    monkeypatch.setenv("ARGUS_JWT_SECRET", TEST_JWT_SECRET)
    set_jwt_secret(TEST_JWT_SECRET)
    return TEST_JWT_SECRET


@pytest.fixture
def test_clock() -> FixedClock:
    """Provide a fixed clock for testing."""
    # Market hours: 10:30 AM ET on a Monday
    return FixedClock(datetime(2026, 2, 23, 15, 30, 0, tzinfo=UTC))


@pytest.fixture
async def test_db(tmp_path: Path) -> AsyncGenerator[DatabaseManager, None]:
    """Provide an initialized DatabaseManager with a temp database."""
    manager = DatabaseManager(tmp_path / "argus_test_api.db")
    await manager.initialize()
    yield manager
    await manager.close()


@pytest.fixture
def test_trade_logger(test_db: DatabaseManager) -> TradeLogger:
    """Provide a TradeLogger backed by a temp database."""
    return TradeLogger(test_db)


@pytest.fixture
def test_broker() -> SimulatedBroker:
    """Provide a SimulatedBroker with test settings."""
    return SimulatedBroker(initial_cash=100_000.0)


@pytest.fixture
def test_event_bus() -> EventBus:
    """Provide a fresh EventBus for testing."""
    return EventBus()


@pytest.fixture
def test_health_monitor(
    test_event_bus: EventBus,
    test_clock: FixedClock,
    test_broker: SimulatedBroker,
    test_trade_logger: TradeLogger,
) -> HealthMonitor:
    """Provide a HealthMonitor for testing."""
    return HealthMonitor(
        event_bus=test_event_bus,
        clock=test_clock,
        config=HealthConfig(),
        broker=test_broker,
        trade_logger=test_trade_logger,
    )


@pytest.fixture
def test_risk_manager(
    test_event_bus: EventBus,
    test_broker: SimulatedBroker,
    test_clock: FixedClock,
) -> RiskManager:
    """Provide a RiskManager for testing."""
    from argus.core.config import RiskConfig

    return RiskManager(
        config=RiskConfig(),
        broker=test_broker,
        event_bus=test_event_bus,
        clock=test_clock,
    )


@pytest.fixture
def test_order_manager(
    test_event_bus: EventBus,
    test_broker: SimulatedBroker,
    test_clock: FixedClock,
    test_trade_logger: TradeLogger,
) -> OrderManager:
    """Provide an OrderManager for testing."""
    return OrderManager(
        event_bus=test_event_bus,
        broker=test_broker,
        clock=test_clock,
        config=OrderManagerConfig(),
        trade_logger=test_trade_logger,
    )


@pytest.fixture
def test_system_config(api_config: ApiConfig) -> SystemConfig:
    """Provide a SystemConfig with the test ApiConfig."""
    return SystemConfig(api=api_config)


@pytest.fixture
async def app_state(
    test_event_bus: EventBus,
    test_trade_logger: TradeLogger,
    test_broker: SimulatedBroker,
    test_health_monitor: HealthMonitor,
    test_risk_manager: RiskManager,
    test_order_manager: OrderManager,
    test_clock: FixedClock,
    test_system_config: SystemConfig,
) -> AppState:
    """Provide a complete AppState for API testing.

    Uses real EventBus, in-memory TradeLogger, and SimulatedBroker.
    """
    return AppState(
        event_bus=test_event_bus,
        trade_logger=test_trade_logger,
        broker=test_broker,
        health_monitor=test_health_monitor,
        risk_manager=test_risk_manager,
        order_manager=test_order_manager,
        data_service=None,
        strategies={},
        clock=test_clock,
        config=test_system_config,
        start_time=time.time(),
    )


@pytest.fixture
async def client(
    app_state: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx.AsyncClient wrapping the FastAPI app.

    The JWT secret is set up before the client is created.
    Manually attaches app_state since httpx ASGITransport doesn't
    trigger FastAPI lifespan events.
    """
    app = create_app(app_state)
    # Manually attach app_state since ASGITransport doesn't trigger lifespan
    app.state.app_state = app_state
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def auth_headers(jwt_secret: str) -> dict[str, str]:
    """Provide Authorization headers with a valid JWT token.

    The token is created using the test JWT secret.
    """
    token, _ = create_access_token(jwt_secret, expires_hours=24)
    return {"Authorization": f"Bearer {token}"}
