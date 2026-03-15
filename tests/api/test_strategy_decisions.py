"""Tests for the GET /{strategy_id}/decisions endpoint."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.core.config import OrbBreakoutConfig
from argus.strategies.orb_breakout import OrbBreakoutStrategy
from argus.strategies.telemetry import (
    EvaluationEvent,
    EvaluationEventType,
    EvaluationResult,
)

_NOW = datetime(2026, 3, 15, 9, 30, 0)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_orb_config() -> OrbBreakoutConfig:
    return OrbBreakoutConfig(
        strategy_id="strat_orb_breakout",
        name="ORB Breakout",
        version="1.0.0",
        enabled=True,
    )


@pytest.fixture
def test_strategy(
    test_orb_config: OrbBreakoutConfig,
    test_clock,
) -> OrbBreakoutStrategy:
    return OrbBreakoutStrategy(
        config=test_orb_config,
        data_service=None,
        clock=test_clock,
    )


@pytest.fixture
def strategy_with_events(test_strategy: OrbBreakoutStrategy) -> OrbBreakoutStrategy:
    """Strategy pre-populated with evaluation events in the buffer."""
    events = [
        EvaluationEvent(
            timestamp=_NOW,
            symbol="AAPL",
            strategy_id=test_strategy.strategy_id,
            event_type=EvaluationEventType.CONDITION_CHECK,
            result=EvaluationResult.PASS,
            reason="volume above threshold",
        ),
        EvaluationEvent(
            timestamp=_NOW,
            symbol="TSLA",
            strategy_id=test_strategy.strategy_id,
            event_type=EvaluationEventType.SIGNAL_REJECTED,
            result=EvaluationResult.FAIL,
            reason="outside time window",
        ),
        EvaluationEvent(
            timestamp=_NOW,
            symbol="AAPL",
            strategy_id=test_strategy.strategy_id,
            event_type=EvaluationEventType.SIGNAL_GENERATED,
            result=EvaluationResult.PASS,
            reason="entry signal emitted",
            metadata={"rvol": 3.5},
        ),
    ]
    for e in events:
        test_strategy.eval_buffer.record(e)
    return test_strategy


@pytest.fixture
async def app_state_with_strategy(
    app_state: AppState,
    strategy_with_events: OrbBreakoutStrategy,
) -> AppState:
    app_state.strategies = {strategy_with_events.strategy_id: strategy_with_events}
    return app_state


@pytest.fixture
async def client_with_strategy(
    app_state_with_strategy: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    app = create_app(app_state_with_strategy)
    app.state.app_state = app_state_with_strategy
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_decisions_returns_events(
    client_with_strategy: AsyncClient,
    auth_headers: dict[str, str],
    strategy_with_events: OrbBreakoutStrategy,
) -> None:
    """GET /decisions returns buffered evaluation events for known strategy."""
    strategy_id = strategy_with_events.strategy_id
    response = await client_with_strategy.get(
        f"/api/v1/strategies/{strategy_id}/decisions",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3
    # Newest first — SIGNAL_GENERATED was recorded last
    assert data[0]["event_type"] == EvaluationEventType.SIGNAL_GENERATED
    assert data[0]["symbol"] == "AAPL"
    assert "timestamp" in data[0]


@pytest.mark.asyncio
async def test_get_decisions_symbol_filter(
    client_with_strategy: AsyncClient,
    auth_headers: dict[str, str],
    strategy_with_events: OrbBreakoutStrategy,
) -> None:
    """GET /decisions?symbol=AAPL returns only AAPL events."""
    strategy_id = strategy_with_events.strategy_id
    response = await client_with_strategy.get(
        f"/api/v1/strategies/{strategy_id}/decisions?symbol=AAPL",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(e["symbol"] == "AAPL" for e in data)


@pytest.mark.asyncio
async def test_get_decisions_unknown_strategy_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /decisions for an unknown strategy_id returns 404."""
    response = await client.get(
        "/api/v1/strategies/does_not_exist/decisions",
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert "does_not_exist" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_decisions_requires_auth(
    client_with_strategy: AsyncClient,
    strategy_with_events: OrbBreakoutStrategy,
) -> None:
    """GET /decisions without a JWT returns 401."""
    strategy_id = strategy_with_events.strategy_id
    response = await client_with_strategy.get(
        f"/api/v1/strategies/{strategy_id}/decisions",
    )
    assert response.status_code == 401
