"""Tests for the counterfactual accuracy API endpoint.

Verifies JWT protection, 200 response with data, and empty report
when counterfactual store is not available.

Sprint 27.7, Session 4.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.intelligence.counterfactual_store import CounterfactualStore


@pytest.fixture
async def cf_store(tmp_path: Path) -> AsyncGenerator[CounterfactualStore, None]:
    """Provide an initialized CounterfactualStore with temp database."""
    store = CounterfactualStore(str(tmp_path / "cf_api_test.db"))
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
async def app_state_with_cf(
    app_state: AppState,
    cf_store: CounterfactualStore,
) -> AppState:
    """Provide AppState with a counterfactual store attached."""
    app_state.counterfactual_store = cf_store
    return app_state


@pytest.fixture
async def client_with_cf(
    app_state_with_cf: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx client with counterfactual store."""
    app = create_app(app_state_with_cf)
    app.state.app_state = app_state_with_cf
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


async def _seed_cf_position(
    store: CounterfactualStore,
    position_id: str,
    theoretical_pnl: float = -2.0,
) -> None:
    """Insert a closed counterfactual position for API testing."""
    assert store._conn is not None
    await store._conn.execute(
        """INSERT INTO counterfactual_positions (
            position_id, symbol, strategy_id, entry_price, stop_price,
            target_price, time_stop_seconds, rejection_stage, rejection_reason,
            quality_score, quality_grade, regime_vector_snapshot, signal_metadata,
            opened_at, closed_at, exit_price, exit_reason,
            theoretical_pnl, theoretical_r_multiple, duration_seconds,
            max_adverse_excursion, max_favorable_excursion, bars_monitored
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            position_id, "AAPL", "orb_breakout", 100.0, 95.0,
            110.0, None, "quality_filter", "grade too low",
            72.5, "B", None, "{}",
            "2026-03-25T10:00:00", "2026-03-25T10:30:00",
            98.0, "stopped_out",
            theoretical_pnl, theoretical_pnl / 5.0, 1800.0,
            2.0, 3.0, 10,
        ),
    )
    await store._conn.commit()


class TestCounterfactualAccuracyEndpoint:
    """Tests for GET /api/v1/counterfactual/accuracy."""

    @pytest.mark.asyncio
    async def test_returns_200_with_data(
        self,
        client_with_cf: AsyncClient,
        auth_headers: dict[str, str],
        cf_store: CounterfactualStore,
    ) -> None:
        """Valid request with data returns 200 and a populated report."""
        await _seed_cf_position(cf_store, "pos_1", theoretical_pnl=-3.0)
        await _seed_cf_position(cf_store, "pos_2", theoretical_pnl=5.0)

        resp = await client_with_cf.get(
            "/api/v1/counterfactual/accuracy",
            headers=auth_headers,
            params={"min_sample_count": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_positions"] == 2
        assert len(data["by_stage"]) >= 1
        assert data["by_stage"][0]["total_rejections"] == 2

    @pytest.mark.asyncio
    async def test_returns_401_without_auth(
        self, client_with_cf: AsyncClient,
    ) -> None:
        """Request without JWT returns 401."""
        resp = await client_with_cf.get("/api/v1/counterfactual/accuracy")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_200_empty_when_no_store(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """When counterfactual store is None, return 200 with empty report."""
        resp = await client.get(
            "/api/v1/counterfactual/accuracy",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_positions"] == 0
        assert data["by_stage"] == []

    @pytest.mark.asyncio
    async def test_returns_200_empty_when_no_data(
        self,
        client_with_cf: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Empty store returns 200 with total_positions=0."""
        resp = await client_with_cf.get(
            "/api/v1/counterfactual/accuracy",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_positions"] == 0

    @pytest.mark.asyncio
    async def test_strategy_filter_param(
        self,
        client_with_cf: AsyncClient,
        auth_headers: dict[str, str],
        cf_store: CounterfactualStore,
    ) -> None:
        """strategy_id query param filters results."""
        await _seed_cf_position(cf_store, "pos_1", theoretical_pnl=-1.0)

        resp = await client_with_cf.get(
            "/api/v1/counterfactual/accuracy",
            headers=auth_headers,
            params={"strategy_id": "nonexistent", "min_sample_count": 1},
        )
        assert resp.status_code == 200
        assert resp.json()["total_positions"] == 0

    @pytest.mark.asyncio
    async def test_invalid_date_returns_400(
        self,
        client_with_cf: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Invalid date format returns 400."""
        resp = await client_with_cf.get(
            "/api/v1/counterfactual/accuracy",
            headers=auth_headers,
            params={"start_date": "not-a-date"},
        )
        assert resp.status_code == 400
