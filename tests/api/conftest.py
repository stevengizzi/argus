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
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from argus.analytics.debrief_service import DebriefService
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
from argus.execution.order_manager import ManagedPosition, OrderManager
from argus.execution.simulated_broker import SimulatedBroker
from argus.models.trading import (
    ExitReason,
    OrderSide,
    Trade,
)

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
def test_debrief_service(test_db: DatabaseManager) -> DebriefService:
    """Provide a DebriefService backed by a temp database."""
    return DebriefService(test_db)


@pytest.fixture
async def test_broker() -> SimulatedBroker:
    """Provide a connected SimulatedBroker with test settings."""
    broker = SimulatedBroker(initial_cash=100_000.0)
    await broker.connect()
    return broker


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
    test_debrief_service: DebriefService,
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
        debrief_service=test_debrief_service,
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


@pytest.fixture
async def seeded_trade_logger(test_trade_logger: TradeLogger) -> TradeLogger:
    """Provide a TradeLogger seeded with diverse test trades.

    Creates 15+ trades across different:
    - Dates (last 30 days, including today)
    - Strategies (orb_breakout, orb_scalp)
    - Outcomes (wins, losses, breakevens)
    - Exit reasons (target_1, target_2, stop_loss, eod)
    """
    # Base time: Feb 23, 2026 (matches test_clock)
    base_time = datetime(2026, 2, 23, 10, 30, 0, tzinfo=UTC)

    trades = [
        # Today's trades (for daily_pnl tests)
        Trade(
            strategy_id="orb_breakout",
            symbol="AAPL",
            side=OrderSide.BUY,
            entry_price=185.00,
            entry_time=base_time - timedelta(hours=2),
            exit_price=188.50,
            exit_time=base_time - timedelta(hours=1),
            shares=100,
            stop_price=183.00,
            target_prices=[187.00, 189.00],
            exit_reason=ExitReason.TARGET_1,
            gross_pnl=350.00,
            commission=2.00,
        ),
        Trade(
            strategy_id="orb_breakout",
            symbol="NVDA",
            side=OrderSide.BUY,
            entry_price=750.00,
            entry_time=base_time - timedelta(hours=3),
            exit_price=745.00,
            exit_time=base_time - timedelta(hours=2),
            shares=50,
            stop_price=740.00,
            target_prices=[760.00, 770.00],
            exit_reason=ExitReason.STOP_LOSS,
            gross_pnl=-250.00,
            commission=2.00,
        ),
        Trade(
            strategy_id="orb_scalp",
            symbol="TSLA",
            side=OrderSide.BUY,
            entry_price=200.00,
            entry_time=base_time - timedelta(hours=4),
            exit_price=204.00,
            exit_time=base_time - timedelta(hours=3, minutes=30),
            shares=75,
            stop_price=198.00,
            target_prices=[202.00, 206.00],
            exit_reason=ExitReason.TARGET_2,
            gross_pnl=300.00,
            commission=1.50,
        ),
        # Yesterday's trades
        Trade(
            strategy_id="orb_breakout",
            symbol="MSFT",
            side=OrderSide.BUY,
            entry_price=420.00,
            entry_time=base_time - timedelta(days=1, hours=3),
            exit_price=425.00,
            exit_time=base_time - timedelta(days=1, hours=1),
            shares=40,
            stop_price=415.00,
            target_prices=[425.00, 430.00],
            exit_reason=ExitReason.TARGET_1,
            gross_pnl=200.00,
            commission=1.00,
        ),
        Trade(
            strategy_id="orb_scalp",
            symbol="AMD",
            side=OrderSide.BUY,
            entry_price=150.00,
            entry_time=base_time - timedelta(days=1, hours=4),
            exit_price=148.00,
            exit_time=base_time - timedelta(days=1, hours=3),
            shares=100,
            stop_price=147.00,
            target_prices=[152.00, 154.00],
            exit_reason=ExitReason.STOP_LOSS,
            gross_pnl=-200.00,
            commission=2.00,
        ),
        # Older trades (5-7 days ago)
        Trade(
            strategy_id="orb_breakout",
            symbol="GOOG",
            side=OrderSide.BUY,
            entry_price=175.00,
            entry_time=base_time - timedelta(days=5, hours=2),
            exit_price=180.00,
            exit_time=base_time - timedelta(days=5, hours=1),
            shares=50,
            stop_price=172.00,
            target_prices=[178.00, 182.00],
            exit_reason=ExitReason.TARGET_2,
            gross_pnl=250.00,
            commission=1.00,
        ),
        Trade(
            strategy_id="orb_breakout",
            symbol="META",
            side=OrderSide.BUY,
            entry_price=550.00,
            entry_time=base_time - timedelta(days=6, hours=3),
            exit_price=550.00,
            exit_time=base_time - timedelta(days=6, hours=1),
            shares=30,
            stop_price=545.00,
            target_prices=[555.00, 560.00],
            exit_reason=ExitReason.EOD_FLATTEN,
            gross_pnl=0.00,
            commission=1.00,
        ),
        Trade(
            strategy_id="orb_scalp",
            symbol="NFLX",
            side=OrderSide.BUY,
            entry_price=650.00,
            entry_time=base_time - timedelta(days=7, hours=2),
            exit_price=660.00,
            exit_time=base_time - timedelta(days=7, hours=1),
            shares=20,
            stop_price=645.00,
            target_prices=[655.00, 665.00],
            exit_reason=ExitReason.TARGET_1,
            gross_pnl=200.00,
            commission=0.80,
        ),
        # Older trades (10-15 days ago)
        Trade(
            strategy_id="orb_breakout",
            symbol="AMZN",
            side=OrderSide.BUY,
            entry_price=190.00,
            entry_time=base_time - timedelta(days=10, hours=3),
            exit_price=188.00,
            exit_time=base_time - timedelta(days=10, hours=2),
            shares=60,
            stop_price=186.00,
            target_prices=[194.00, 198.00],
            exit_reason=ExitReason.STOP_LOSS,
            gross_pnl=-120.00,
            commission=1.20,
        ),
        Trade(
            strategy_id="orb_scalp",
            symbol="COST",
            side=OrderSide.BUY,
            entry_price=900.00,
            entry_time=base_time - timedelta(days=12, hours=2),
            exit_price=910.00,
            exit_time=base_time - timedelta(days=12, hours=1),
            shares=10,
            stop_price=895.00,
            target_prices=[905.00, 915.00],
            exit_reason=ExitReason.TARGET_2,
            gross_pnl=100.00,
            commission=0.50,
        ),
        Trade(
            strategy_id="orb_breakout",
            symbol="CRM",
            side=OrderSide.BUY,
            entry_price=300.00,
            entry_time=base_time - timedelta(days=14, hours=3),
            exit_price=295.00,
            exit_time=base_time - timedelta(days=14, hours=2),
            shares=40,
            stop_price=292.00,
            target_prices=[305.00, 310.00],
            exit_reason=ExitReason.STOP_LOSS,
            gross_pnl=-200.00,
            commission=1.00,
        ),
        # Very old trades (20-30 days ago)
        Trade(
            strategy_id="orb_breakout",
            symbol="ORCL",
            side=OrderSide.BUY,
            entry_price=180.00,
            entry_time=base_time - timedelta(days=20, hours=2),
            exit_price=185.00,
            exit_time=base_time - timedelta(days=20, hours=1),
            shares=50,
            stop_price=177.00,
            target_prices=[183.00, 187.00],
            exit_reason=ExitReason.TARGET_1,
            gross_pnl=250.00,
            commission=1.00,
        ),
        Trade(
            strategy_id="orb_scalp",
            symbol="ADBE",
            side=OrderSide.BUY,
            entry_price=480.00,
            entry_time=base_time - timedelta(days=25, hours=3),
            exit_price=490.00,
            exit_time=base_time - timedelta(days=25, hours=1),
            shares=25,
            stop_price=475.00,
            target_prices=[485.00, 495.00],
            exit_reason=ExitReason.TARGET_2,
            gross_pnl=250.00,
            commission=1.25,
        ),
        Trade(
            strategy_id="orb_breakout",
            symbol="INTC",
            side=OrderSide.BUY,
            entry_price=25.00,
            entry_time=base_time - timedelta(days=28, hours=2),
            exit_price=24.00,
            exit_time=base_time - timedelta(days=28, hours=1),
            shares=200,
            stop_price=23.50,
            target_prices=[26.00, 27.00],
            exit_reason=ExitReason.STOP_LOSS,
            gross_pnl=-200.00,
            commission=0.50,
        ),
        Trade(
            strategy_id="orb_scalp",
            symbol="PYPL",
            side=OrderSide.BUY,
            entry_price=70.00,
            entry_time=base_time - timedelta(days=30, hours=3),
            exit_price=72.00,
            exit_time=base_time - timedelta(days=30, hours=2),
            shares=75,
            stop_price=68.00,
            target_prices=[71.50, 73.00],
            exit_reason=ExitReason.TARGET_1,
            gross_pnl=150.00,
            commission=0.75,
        ),
    ]

    for trade in trades:
        await test_trade_logger.log_trade(trade)

    return test_trade_logger


@pytest.fixture
def sample_managed_positions(test_clock: FixedClock) -> list[ManagedPosition]:
    """Provide sample ManagedPositions for position tests.

    Creates 3 positions with different characteristics:
    - One profitable (price above entry)
    - One losing (price below entry)
    - One at breakeven (price at entry)
    """
    now = test_clock.now()
    return [
        ManagedPosition(
            symbol="AAPL",
            strategy_id="orb_breakout",
            entry_price=185.00,
            entry_time=now - timedelta(minutes=45),
            shares_total=100,
            shares_remaining=50,  # T1 already hit
            stop_price=183.50,  # Moved to breakeven
            original_stop_price=183.00,
            stop_order_id="stop_001",
            t1_price=187.00,
            t1_order_id=None,  # T1 already filled
            t1_shares=50,
            t1_filled=True,
            t2_price=189.00,
            high_watermark=187.50,
        ),
        ManagedPosition(
            symbol="NVDA",
            strategy_id="orb_breakout",
            entry_price=750.00,
            entry_time=now - timedelta(minutes=30),
            shares_total=50,
            shares_remaining=50,  # Full position
            stop_price=740.00,
            original_stop_price=740.00,
            stop_order_id="stop_002",
            t1_price=760.00,
            t1_order_id="t1_002",
            t1_shares=25,
            t1_filled=False,
            t2_price=770.00,
            high_watermark=752.00,
        ),
        ManagedPosition(
            symbol="TSLA",
            strategy_id="orb_scalp",
            entry_price=200.00,
            entry_time=now - timedelta(minutes=15),
            shares_total=75,
            shares_remaining=75,
            stop_price=198.00,
            original_stop_price=198.00,
            stop_order_id="stop_003",
            t1_price=202.00,
            t1_order_id="t1_003",
            t1_shares=37,
            t1_filled=False,
            t2_price=206.00,
            high_watermark=200.50,
        ),
    ]


@pytest.fixture
async def app_state_with_positions(
    app_state: AppState,
    sample_managed_positions: list[ManagedPosition],
) -> AppState:
    """Provide AppState with pre-injected managed positions."""
    # Inject positions directly into OrderManager's internal dict
    # _managed_positions is dict[str, list[ManagedPosition]]
    for pos in sample_managed_positions:
        if pos.symbol not in app_state.order_manager._managed_positions:
            app_state.order_manager._managed_positions[pos.symbol] = []
        app_state.order_manager._managed_positions[pos.symbol].append(pos)
    return app_state


@pytest.fixture
async def client_with_positions(
    app_state_with_positions: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide client with AppState containing managed positions."""
    app = create_app(app_state_with_positions)
    app.state.app_state = app_state_with_positions
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
async def app_state_with_trades(
    test_event_bus: EventBus,
    seeded_trade_logger: TradeLogger,
    test_broker: SimulatedBroker,
    test_health_monitor: HealthMonitor,
    test_risk_manager: RiskManager,
    test_order_manager: OrderManager,
    test_clock: FixedClock,
    test_system_config: SystemConfig,
) -> AppState:
    """Provide AppState with seeded trades for trade query tests."""
    return AppState(
        event_bus=test_event_bus,
        trade_logger=seeded_trade_logger,
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
async def client_with_trades(
    app_state_with_trades: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide client with AppState containing seeded trades."""
    app = create_app(app_state_with_trades)
    app.state.app_state = app_state_with_trades
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
async def seeded_debrief_service(test_debrief_service: DebriefService) -> DebriefService:
    """Provide a DebriefService pre-populated with test data.

    Creates:
    - 3 briefings (2 pre_market, 1 eod)
    - 5 journal entries (various types)
    - 2 documents (research category)
    """
    # Create briefings
    await test_debrief_service.create_briefing(
        date="2026-02-20",
        briefing_type="pre_market",
        title="Pre-Market Test Briefing",
        content="Test pre-market content with analysis.",
    )
    await test_debrief_service.create_briefing(
        date="2026-02-20",
        briefing_type="eod",
        title="EOD Test Briefing",
        content="Test end of day review content.",
    )
    await test_debrief_service.create_briefing(
        date="2026-02-21",
        briefing_type="pre_market",
        title="Second Pre-Market Briefing",
        content="Another pre-market briefing for testing pagination.",
    )

    # Create journal entries
    await test_debrief_service.create_journal_entry(
        entry_type="observation",
        title="Test Observation",
        content="Observing market patterns for testing.",
        tags=["test", "observation"],
    )
    await test_debrief_service.create_journal_entry(
        entry_type="trade_annotation",
        title="Test Trade Note",
        content="Annotation about a specific trade.",
        linked_trade_ids=["trade_001"],
        tags=["trade", "annotation"],
    )
    await test_debrief_service.create_journal_entry(
        entry_type="pattern_note",
        title="Test Pattern",
        content="Notes about a pattern observed.",
        tags=["pattern", "test"],
    )
    await test_debrief_service.create_journal_entry(
        entry_type="system_note",
        title="System Configuration Note",
        content="Notes about system behavior.",
        tags=["system", "config"],
    )
    await test_debrief_service.create_journal_entry(
        entry_type="observation",
        title="Searchable Entry",
        content="This entry contains the word FINDME for search tests.",
        tags=["search", "test"],
    )

    # Create documents
    await test_debrief_service.create_document(
        category="research",
        title="Test Research Document",
        content="Research content for testing the debrief service.",
        tags=["test", "research"],
    )
    await test_debrief_service.create_document(
        category="research",
        title="Another Research Doc",
        content="More research content with FINDME keyword.",
        tags=["test", "research", "search"],
    )

    return test_debrief_service


@pytest.fixture
async def app_state_with_debrief(
    test_event_bus: EventBus,
    test_trade_logger: TradeLogger,
    seeded_debrief_service: DebriefService,
    test_broker: SimulatedBroker,
    test_health_monitor: HealthMonitor,
    test_risk_manager: RiskManager,
    test_order_manager: OrderManager,
    test_clock: FixedClock,
    test_system_config: SystemConfig,
) -> AppState:
    """Provide AppState with seeded debrief content for API testing."""
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
        debrief_service=seeded_debrief_service,
    )


@pytest.fixture
async def client_with_debrief(
    app_state_with_debrief: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide client with AppState containing seeded debrief data."""
    app = create_app(app_state_with_debrief)
    app.state.app_state = app_state_with_debrief
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
