"""Tests for extended strategy fields (Sprint 21a).

Tests the new fields added to GET /api/v1/strategies:
- time_window, family, description_short
- performance_summary
- backtest_summary
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.core.config import BacktestSummaryConfig, OrbBreakoutConfig


@pytest.fixture
def test_orb_config_with_extended_fields() -> OrbBreakoutConfig:
    """Provide an OrbBreakoutConfig with all new Sprint 21a fields."""
    return OrbBreakoutConfig(
        strategy_id="strat_orb_breakout",
        name="ORB Breakout",
        version="1.0.0",
        enabled=True,
        orb_window_minutes=15,
        target_1_r=1.0,
        target_2_r=2.0,
        time_stop_minutes=30,
        # New Sprint 21a fields
        pipeline_stage="paper_trading",
        family="orb_family",
        description_short="Test ORB breakout strategy.",
        time_window_display="9:35–11:30 AM",
        backtest_summary=BacktestSummaryConfig(
            status="walk_forward_complete",
            wfe_pnl=0.56,
            oos_sharpe=0.34,
            total_trades=137,
            data_months=35,
            last_run="2026-02-17",
        ),
    )


@pytest.fixture
def test_strategy_extended(test_orb_config_with_extended_fields, test_clock):
    """Provide an OrbBreakoutStrategy with extended config fields."""
    from argus.strategies.orb_breakout import OrbBreakoutStrategy

    strategy = OrbBreakoutStrategy(
        config=test_orb_config_with_extended_fields,
        data_service=None,
        clock=test_clock,
    )
    strategy.is_active = True
    strategy.allocated_capital = 25000.0
    strategy._daily_pnl = 150.0
    strategy._trade_count_today = 2
    return strategy


@pytest.fixture
async def app_state_with_extended_strategy(
    app_state: AppState,
    test_strategy_extended,
) -> AppState:
    """Provide AppState with a strategy having extended config fields."""
    app_state.strategies = {
        test_strategy_extended.strategy_id: test_strategy_extended,
    }
    return app_state


@pytest.fixture
async def client_with_extended_strategy(
    app_state_with_extended_strategy: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide client with AppState containing extended strategy."""
    app = create_app(app_state_with_extended_strategy)
    app.state.app_state = app_state_with_extended_strategy
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_strategies_returns_extended_fields(
    client_with_extended_strategy: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /strategies returns time_window, family, description_short."""
    response = await client_with_extended_strategy.get(
        "/api/v1/strategies",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data["strategies"]) == 1
    strategy = data["strategies"][0]

    # Check new Sprint 21a fields
    assert strategy["time_window"] == "9:35–11:30 AM"
    assert strategy["family"] == "orb_family"
    assert strategy["description_short"] == "Test ORB breakout strategy."


@pytest.mark.asyncio
async def test_strategies_returns_backtest_summary(
    client_with_extended_strategy: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /strategies returns backtest_summary with correct values."""
    response = await client_with_extended_strategy.get(
        "/api/v1/strategies",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    strategy = data["strategies"][0]

    # Check backtest_summary is present and has correct values
    assert strategy["backtest_summary"] is not None
    bs = strategy["backtest_summary"]
    assert bs["status"] == "walk_forward_complete"
    assert bs["wfe_pnl"] == 0.56
    assert bs["oos_sharpe"] == 0.34
    assert bs["total_trades"] == 137
    assert bs["data_months"] == 35
    assert bs["last_run"] == "2026-02-17"


@pytest.mark.asyncio
async def test_strategies_performance_summary_null_when_no_trades(
    client_with_extended_strategy: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /strategies returns null performance_summary when no trades exist."""
    response = await client_with_extended_strategy.get(
        "/api/v1/strategies",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    strategy = data["strategies"][0]

    # No trades in database, so performance_summary should be null
    assert strategy["performance_summary"] is None


@pytest.mark.asyncio
async def test_config_model_parses_backtest_summary() -> None:
    """BacktestSummaryConfig parses from YAML-like dict correctly."""
    config_data = {
        "strategy_id": "strat_test",
        "name": "Test Strategy",
        "orb_window_minutes": 5,
        "backtest_summary": {
            "status": "sweep_complete",
            "wfe_pnl": None,
            "oos_sharpe": 1.49,
            "total_trades": 59556,
            "data_months": 35,
            "last_run": "2026-02-26",
        },
    }

    config = OrbBreakoutConfig(**config_data)

    assert config.backtest_summary.status == "sweep_complete"
    assert config.backtest_summary.wfe_pnl is None
    assert config.backtest_summary.oos_sharpe == 1.49
    assert config.backtest_summary.total_trades == 59556
    assert config.backtest_summary.data_months == 35
    assert config.backtest_summary.last_run == "2026-02-26"
