"""Tests for the counterfactual API endpoints.

Covers the accuracy endpoint (Sprint 27.7 S4) and the positions
endpoint (Sprint 32.5 S5).
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


class TestCounterfactualPositionsEndpoint:
    """Tests for GET /api/v1/counterfactual/positions (Sprint 32.5 S5)."""

    @pytest.mark.asyncio
    async def test_happy_path_returns_positions(
        self,
        client_with_cf: AsyncClient,
        auth_headers: dict[str, str],
        cf_store: CounterfactualStore,
    ) -> None:
        """Seeded positions are returned with expected shape."""
        await _seed_cf_position(cf_store, "pos_happy_1", theoretical_pnl=-2.0)
        await _seed_cf_position(cf_store, "pos_happy_2", theoretical_pnl=4.0)

        resp = await client_with_cf.get(
            "/api/v1/counterfactual/positions",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 2
        assert len(data["positions"]) == 2
        assert "limit" in data
        assert "offset" in data
        assert "timestamp" in data
        # Verify all expected fields present in first position
        pos = data["positions"][0]
        assert "symbol" in pos
        assert "strategy_id" in pos
        assert "entry_price" in pos
        assert "rejection_stage" in pos

    @pytest.mark.asyncio
    async def test_strategy_id_filter(
        self,
        client_with_cf: AsyncClient,
        auth_headers: dict[str, str],
        cf_store: CounterfactualStore,
    ) -> None:
        """strategy_id query param filters results correctly."""
        await _seed_cf_position(cf_store, "pos_filter_1", theoretical_pnl=-1.0)

        resp = await client_with_cf.get(
            "/api/v1/counterfactual/positions",
            headers=auth_headers,
            params={"strategy_id": "orb_breakout"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 1
        assert data["positions"][0]["strategy_id"] == "orb_breakout"

        # Non-matching strategy returns empty
        resp2 = await client_with_cf.get(
            "/api/v1/counterfactual/positions",
            headers=auth_headers,
            params={"strategy_id": "nonexistent_strategy"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["total_count"] == 0

    @pytest.mark.asyncio
    async def test_date_range_filter(
        self,
        client_with_cf: AsyncClient,
        auth_headers: dict[str, str],
        cf_store: CounterfactualStore,
    ) -> None:
        """date_from and date_to query params filter by opened_at."""
        await _seed_cf_position(cf_store, "pos_date_1", theoretical_pnl=-1.0)

        # Date range that includes the seeded position (opened_at = 2026-03-25)
        resp = await client_with_cf.get(
            "/api/v1/counterfactual/positions",
            headers=auth_headers,
            params={"date_from": "2026-03-25T00:00:00", "date_to": "2026-03-25T23:59:59"},
        )
        assert resp.status_code == 200
        assert resp.json()["total_count"] == 1

        # Date range that excludes the position
        resp2 = await client_with_cf.get(
            "/api/v1/counterfactual/positions",
            headers=auth_headers,
            params={"date_from": "2026-03-26T00:00:00"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["total_count"] == 0

    @pytest.mark.asyncio
    async def test_rejection_stage_filter(
        self,
        client_with_cf: AsyncClient,
        auth_headers: dict[str, str],
        cf_store: CounterfactualStore,
    ) -> None:
        """rejection_stage query param filters results correctly."""
        await _seed_cf_position(cf_store, "pos_stage_1", theoretical_pnl=-2.0)

        resp = await client_with_cf.get(
            "/api/v1/counterfactual/positions",
            headers=auth_headers,
            params={"rejection_stage": "quality_filter"},
        )
        assert resp.status_code == 200
        assert resp.json()["total_count"] == 1

        resp2 = await client_with_cf.get(
            "/api/v1/counterfactual/positions",
            headers=auth_headers,
            params={"rejection_stage": "risk_manager"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["total_count"] == 0

    @pytest.mark.asyncio
    async def test_pagination_limit_offset(
        self,
        client_with_cf: AsyncClient,
        auth_headers: dict[str, str],
        cf_store: CounterfactualStore,
    ) -> None:
        """limit and offset pagination works correctly."""
        for i in range(5):
            await _seed_cf_position(cf_store, f"pos_page_{i}", theoretical_pnl=float(i))

        resp_first = await client_with_cf.get(
            "/api/v1/counterfactual/positions",
            headers=auth_headers,
            params={"limit": 2, "offset": 0},
        )
        assert resp_first.status_code == 200
        data_first = resp_first.json()
        assert data_first["total_count"] == 5
        assert len(data_first["positions"]) == 2

        resp_second = await client_with_cf.get(
            "/api/v1/counterfactual/positions",
            headers=auth_headers,
            params={"limit": 2, "offset": 2},
        )
        assert resp_second.status_code == 200
        data_second = resp_second.json()
        assert data_second["total_count"] == 5
        assert len(data_second["positions"]) == 2
        # Pages must not overlap
        first_ids = {p["position_id"] for p in data_first["positions"]}
        second_ids = {p["position_id"] for p in data_second["positions"]}
        assert first_ids.isdisjoint(second_ids)

    @pytest.mark.asyncio
    async def test_empty_store_returns_empty_list(
        self,
        client_with_cf: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Empty store returns 200 with positions=[] and total_count=0."""
        resp = await client_with_cf.get(
            "/api/v1/counterfactual/positions",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 0
        assert data["positions"] == []

    @pytest.mark.asyncio
    async def test_no_store_returns_empty_list(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """When counterfactual store is None, returns 200 with empty list."""
        resp = await client.get(
            "/api/v1/counterfactual/positions",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 0
        assert data["positions"] == []

    @pytest.mark.asyncio
    async def test_requires_auth(
        self,
        client_with_cf: AsyncClient,
    ) -> None:
        """Request without JWT returns 401."""
        resp = await client_with_cf.get("/api/v1/counterfactual/positions")
        assert resp.status_code == 401
