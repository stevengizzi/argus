"""Tests for the counterfactual API endpoints.

Covers the accuracy endpoint (Sprint 27.7 S4) and the positions
endpoint (Sprint 32.5 S5).
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
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


def _seed_anchor() -> datetime:
    """Return an anchor 5 days in the past, second-precision (DEF-205).

    Within compute_filter_accuracy's rolling 30-day default window so the
    accuracy endpoint includes seeded positions regardless of wall-clock date.
    """
    return (datetime.now() - timedelta(days=5)).replace(microsecond=0)


async def _seed_cf_position(
    store: CounterfactualStore,
    position_id: str,
    theoretical_pnl: float = -2.0,
    opened_at: str | None = None,
    closed_at: str | None = None,
) -> None:
    """Insert a closed counterfactual position for API testing."""
    if opened_at is None or closed_at is None:
        anchor = _seed_anchor()
        if opened_at is None:
            opened_at = anchor.isoformat()
        if closed_at is None:
            closed_at = (anchor + timedelta(minutes=30)).isoformat()
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
            opened_at, closed_at,
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

        # Date range that includes the seeded position (anchor = 5 days ago).
        seed_day = _seed_anchor().date()
        next_day = seed_day + timedelta(days=1)
        resp = await client_with_cf.get(
            "/api/v1/counterfactual/positions",
            headers=auth_headers,
            params={
                "date_from": f"{seed_day.isoformat()}T00:00:00",
                "date_to": f"{seed_day.isoformat()}T23:59:59",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["total_count"] == 1

        # Date range that excludes the position (starts the day after the seed).
        resp2 = await client_with_cf.get(
            "/api/v1/counterfactual/positions",
            headers=auth_headers,
            params={"date_from": f"{next_day.isoformat()}T00:00:00"},
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


class TestF06MfeMaeRMultiples:
    """Apr 21 debrief F-06 (IMPROMPTU-07, 2026-04-23): the positions
    endpoint now serializes ``mfe_r`` / ``mae_r`` R-multiple fields
    alongside the original dollar-valued ``max_favorable_excursion`` /
    ``max_adverse_excursion`` fields. The UI renders MFE/MAE via
    RMultipleCell which expects R-multiples — feeding it the dollar
    values produced "$0.00R"-style labels.

    The fix is additive: the dollar fields are preserved for
    backward-compat; the R fields are computed at serialization time
    from ``(excursion_dollars) / |entry_price - stop_price|``.
    MAE is stored as a positive dollar drawdown, so ``mae_r`` is
    flipped to a negative R-multiple for UI rendering.
    """

    @pytest.mark.asyncio
    async def test_response_includes_mfe_r_and_mae_r_fields(
        self,
        client_with_cf: AsyncClient,
        auth_headers: dict[str, str],
        cf_store: CounterfactualStore,
    ) -> None:
        """New mfe_r/mae_r fields present alongside dollar fields."""
        await _seed_cf_position(cf_store, "pos_mfe_1", theoretical_pnl=-2.0)

        resp = await client_with_cf.get(
            "/api/v1/counterfactual/positions",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        pos = resp.json()["positions"][0]
        assert "mfe_r" in pos, "F-06 regression: mfe_r field missing from response"
        assert "mae_r" in pos, "F-06 regression: mae_r field missing from response"
        # Backward-compat: dollar fields still present.
        assert "max_favorable_excursion" in pos
        assert "max_adverse_excursion" in pos

    @pytest.mark.asyncio
    async def test_mfe_r_matches_known_r_multiple(
        self,
        client_with_cf: AsyncClient,
        auth_headers: dict[str, str],
        cf_store: CounterfactualStore,
    ) -> None:
        """Seeded fixture: entry=100, stop=95 (risk_per_share=5),
        max_favorable_excursion=3.0 → mfe_r = 3.0 / 5 = 0.6.
        max_adverse_excursion=2.0 stored as positive dollars →
        mae_r = -2.0 / 5 = -0.4 (flipped by the enrichment helper).
        """
        await _seed_cf_position(cf_store, "pos_mfe_math", theoretical_pnl=-2.0)

        resp = await client_with_cf.get(
            "/api/v1/counterfactual/positions",
            headers=auth_headers,
        )
        pos = resp.json()["positions"][0]
        assert pos["mfe_r"] == pytest.approx(0.6, abs=1e-9)
        assert pos["mae_r"] == pytest.approx(-0.4, abs=1e-9)
        # Dollar fields unchanged by the enrichment step.
        assert pos["max_favorable_excursion"] == pytest.approx(3.0)
        assert pos["max_adverse_excursion"] == pytest.approx(2.0)
