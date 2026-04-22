"""Tests for the strategies endpoint."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.core.config import OrbBreakoutConfig
from argus.execution.order_manager import ManagedPosition
from argus.strategies.orb_breakout import OrbBreakoutStrategy


@pytest.fixture
def test_orb_config() -> OrbBreakoutConfig:
    """Provide an OrbBreakoutConfig for testing."""
    return OrbBreakoutConfig(
        strategy_id="orb_breakout",
        name="ORB Breakout",
        version="1.0.0",
        enabled=True,
        orb_window_minutes=15,
        target_1_r=1.0,
        target_2_r=2.0,
        time_stop_minutes=30,
    )


@pytest.fixture
def test_strategy(test_orb_config: OrbBreakoutConfig, test_clock) -> OrbBreakoutStrategy:
    """Provide a test OrbBreakoutStrategy instance."""
    strategy = OrbBreakoutStrategy(
        config=test_orb_config,
        data_service=None,
        clock=test_clock,
    )
    strategy.is_active = True
    strategy.allocated_capital = 25000.0
    # Simulate some daily activity
    strategy._daily_pnl = 150.0
    strategy._trade_count_today = 2
    return strategy


@pytest.fixture
async def app_state_with_strategies(
    app_state: AppState,
    test_strategy: OrbBreakoutStrategy,
) -> AppState:
    """Provide AppState with registered strategies."""
    app_state.strategies = {
        test_strategy.strategy_id: test_strategy,
    }
    return app_state


@pytest.fixture
async def client_with_strategies(
    app_state_with_strategies: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide client with AppState containing strategies."""
    app = create_app(app_state_with_strategies)
    app.state.app_state = app_state_with_strategies
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_strategies_list(client_with_strategies, auth_headers):
    """GET /strategies returns all strategies."""
    response = await client_with_strategies.get("/api/v1/strategies", headers=auth_headers)

    assert response.status_code == 200

    data = response.json()

    assert "strategies" in data
    assert "count" in data
    assert "timestamp" in data
    assert data["count"] == 1
    assert len(data["strategies"]) == 1


@pytest.mark.asyncio
async def test_strategies_fields(client_with_strategies, auth_headers):
    """Each strategy has all required fields."""
    response = await client_with_strategies.get("/api/v1/strategies", headers=auth_headers)

    assert response.status_code == 200

    data = response.json()
    strategy = data["strategies"][0]

    # Check all expected fields are present
    assert "strategy_id" in strategy
    assert "name" in strategy
    assert "version" in strategy
    assert "is_active" in strategy
    assert "pipeline_stage" in strategy
    assert "allocated_capital" in strategy
    assert "daily_pnl" in strategy
    assert "trade_count_today" in strategy
    assert "open_positions" in strategy
    assert "config_summary" in strategy

    # Check values match the fixture
    assert strategy["strategy_id"] == "orb_breakout"
    assert strategy["name"] == "ORB Breakout"
    assert strategy["version"] == "1.0.0"
    assert strategy["is_active"] is True
    assert strategy["allocated_capital"] == 25000.0
    assert strategy["daily_pnl"] == 150.0
    assert strategy["trade_count_today"] == 2


@pytest.mark.asyncio
async def test_strategies_config_summary(client_with_strategies, auth_headers):
    """Config_summary has content from strategy config."""
    response = await client_with_strategies.get("/api/v1/strategies", headers=auth_headers)

    assert response.status_code == 200

    data = response.json()
    strategy = data["strategies"][0]

    config_summary = strategy["config_summary"]

    # Check ORB-specific config fields are extracted
    assert isinstance(config_summary, dict)
    assert len(config_summary) > 0

    # These should be extracted from OrbBreakoutConfig
    assert config_summary.get("orb_window_minutes") == 15
    assert config_summary.get("target_1_r") == 1.0
    assert config_summary.get("target_2_r") == 2.0
    assert config_summary.get("time_stop_minutes") == 30


@pytest.mark.asyncio
async def test_strategies_open_positions_count(
    app_state_with_strategies,
    test_clock,
    jwt_secret: str,
):
    """Open_positions count matches actual positions from order manager."""
    # Add managed positions to order manager
    now = test_clock.now()
    positions = [
        ManagedPosition(
            symbol="AAPL",
            strategy_id="orb_breakout",
            entry_price=185.00,
            entry_time=now - timedelta(minutes=30),
            shares_total=100,
            shares_remaining=100,
            stop_price=183.00,
            original_stop_price=183.00,
            stop_order_id="stop_001",
            t1_price=187.00,
            t1_order_id="t1_001",
            t1_shares=50,
            t1_filled=False,
            t2_price=189.00,
            high_watermark=185.50,
        ),
        ManagedPosition(
            symbol="NVDA",
            strategy_id="orb_breakout",
            entry_price=750.00,
            entry_time=now - timedelta(minutes=15),
            shares_total=50,
            shares_remaining=50,
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
    ]

    # Inject positions into order manager
    order_manager = app_state_with_strategies.order_manager
    for pos in positions:
        if pos.symbol not in order_manager._managed_positions:
            order_manager._managed_positions[pos.symbol] = []
        order_manager._managed_positions[pos.symbol].append(pos)

    app = create_app(app_state_with_strategies)
    app.state.app_state = app_state_with_strategies

    from argus.api.auth import create_access_token

    token, _ = create_access_token(jwt_secret, expires_hours=24)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        response = await test_client.get("/api/v1/strategies", headers=headers)

    assert response.status_code == 200

    data = response.json()
    strategy = data["strategies"][0]

    # Should have 2 open positions for orb_breakout
    assert strategy["open_positions"] == 2


@pytest.mark.asyncio
async def test_strategies_unauthenticated(client):
    """GET /strategies without token returns 401."""
    response = await client.get("/api/v1/strategies")

    assert response.status_code == 401


# --- Strategy Spec Sheet Auto-Discovery Tests ---


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "strategy_id,expected_filename",
    [
        ("strat_orb_breakout", "STRATEGY_ORB_BREAKOUT.md"),
        ("strat_orb_scalp", "STRATEGY_ORB_SCALP.md"),
        ("strat_vwap_reclaim", "STRATEGY_VWAP_RECLAIM.md"),
        ("strat_afternoon_momentum", "STRATEGY_AFTERNOON_MOMENTUM.md"),
    ],
)
async def test_strategy_spec_auto_discovery(
    client_with_strategies,
    auth_headers,
    strategy_id: str,
    expected_filename: str,
):
    """GET /strategies/{id}/spec resolves all 4 current strategies correctly."""
    response = await client_with_strategies.get(
        f"/api/v1/strategies/{strategy_id}/spec",
        headers=auth_headers,
    )

    # All 4 strategy spec files should exist and resolve
    assert response.status_code == 200
    data = response.json()
    assert data["strategy_id"] == strategy_id
    # Response has documents list with metadata
    assert "documents" in data
    assert len(data["documents"]) > 0
    # Primary document should have expected fields
    doc = data["documents"][0]
    assert doc["doc_id"] == "strategy_spec"
    assert doc["filename"] == expected_filename
    assert len(doc["content"]) > 0
    assert doc["word_count"] > 0
    assert doc["reading_time_min"] >= 1


@pytest.mark.asyncio
async def test_strategy_spec_returns_404_for_nonexistent_strategy(
    client_with_strategies,
    auth_headers,
):
    """GET /strategies/{id}/spec returns 404 for non-existent strategy."""
    response = await client_with_strategies.get(
        "/api/v1/strategies/strat_does_not_exist/spec",
        headers=auth_headers,
    )

    assert response.status_code == 404
    data = response.json()
    assert "No documents found" in data["detail"]
