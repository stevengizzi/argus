"""Tests for the strategy spec endpoint (Sprint 21a).

Tests GET /api/v1/strategies/{strategy_id}/spec endpoint.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestStrategySpecEndpoint:
    """Tests for GET /strategies/{strategy_id}/spec."""

    async def test_returns_markdown_for_valid_strategy(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """GET /strategies/{strategy_id}/spec returns markdown for valid strategy."""
        response = await client.get(
            "/api/v1/strategies/strat_orb_breakout/spec",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["strategy_id"] == "strat_orb_breakout"
        assert data["format"] == "markdown"
        assert "content" in data
        assert len(data["content"]) > 0

    async def test_returns_404_for_unknown_strategy(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """GET /strategies/{strategy_id}/spec returns 404 for unknown strategy."""
        response = await client.get(
            "/api/v1/strategies/unknown_strategy/spec",
            headers=auth_headers,
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "No spec sheet" in data["detail"]

    async def test_content_contains_expected_heading(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Spec content contains the expected strategy name heading."""
        response = await client.get(
            "/api/v1/strategies/strat_orb_breakout/spec",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # The ORB Breakout spec should contain the strategy name
        assert "ORB" in data["content"]
        # Should be a markdown document
        assert "#" in data["content"]  # Contains headings


class TestOtherStrategySpecs:
    """Tests for other strategy spec files."""

    async def test_orb_scalp_spec_exists(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """GET /strategies/strat_orb_scalp/spec returns content."""
        response = await client.get(
            "/api/v1/strategies/strat_orb_scalp/spec",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["strategy_id"] == "strat_orb_scalp"
        assert len(data["content"]) > 0

    async def test_vwap_reclaim_spec_exists(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """GET /strategies/strat_vwap_reclaim/spec returns content."""
        response = await client.get(
            "/api/v1/strategies/strat_vwap_reclaim/spec",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["strategy_id"] == "strat_vwap_reclaim"
        assert len(data["content"]) > 0

    async def test_afternoon_momentum_spec_exists(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """GET /strategies/strat_afternoon_momentum/spec returns content."""
        response = await client.get(
            "/api/v1/strategies/strat_afternoon_momentum/spec",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["strategy_id"] == "strat_afternoon_momentum"
        assert len(data["content"]) > 0


class TestUnauthenticated:
    """Tests for unauthenticated access."""

    async def test_returns_401_without_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """GET /strategies/{strategy_id}/spec returns 401 without auth."""
        response = await client.get("/api/v1/strategies/strat_orb_breakout/spec")

        assert response.status_code == 401
