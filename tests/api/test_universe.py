"""Tests for universe API endpoints.

Sprint 23: NLP Catalyst + Universe Manager
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.data.fmp_reference import SymbolReferenceData


@dataclass
class MockUniverseManager:
    """Mock UniverseManager for testing universe endpoints."""

    _viable_symbols: set[str]
    _reference_cache: dict[str, SymbolReferenceData]
    _routing_table: dict[str, set[str]]
    _last_build_time: datetime

    @property
    def viable_symbols(self) -> set[str]:
        """Get viable symbols."""
        return self._viable_symbols.copy()

    @property
    def reference_cache(self) -> dict[str, SymbolReferenceData]:
        """Get reference cache."""
        return self._reference_cache.copy()

    def get_universe_stats(self) -> dict:
        """Get universe statistics."""
        strategy_counts: dict[str, int] = {}
        for strategies in self._routing_table.values():
            for strategy_id in strategies:
                strategy_counts[strategy_id] = strategy_counts.get(strategy_id, 0) + 1

        delta = datetime.now(UTC) - self._last_build_time
        cache_age_minutes = delta.total_seconds() / 60.0

        return {
            "total_viable": len(self._viable_symbols),
            "per_strategy_counts": strategy_counts,
            "last_build_time": self._last_build_time.isoformat(),
            "last_routing_build_time": self._last_build_time.isoformat(),
            "cache_age_minutes": cache_age_minutes,
        }

    def get_strategy_symbols(self, strategy_id: str) -> set[str]:
        """Get symbols for a specific strategy."""
        return {
            symbol
            for symbol, strategies in self._routing_table.items()
            if strategy_id in strategies
        }

    def get_reference_data(self, symbol: str) -> SymbolReferenceData | None:
        """Get reference data for a symbol."""
        return self._reference_cache.get(symbol)

    def route_candle(self, symbol: str) -> set[str]:
        """Get strategies that match this symbol."""
        return self._routing_table.get(symbol, set())


@pytest.fixture
def mock_universe_manager() -> MockUniverseManager:
    """Provide a mock UniverseManager with test data."""
    # Create reference data for 10 symbols
    ref_data: dict[str, SymbolReferenceData] = {}
    viable_symbols: set[str] = set()
    routing_table: dict[str, set[str]] = {}

    symbols = [
        "AAPL", "NVDA", "TSLA", "MSFT", "GOOG", "META", "AMZN", "AMD", "CRM", "ORCL"
    ]
    sectors = [
        "Technology", "Technology", "Consumer Cyclical", "Technology",
        "Communication Services", "Communication Services", "Consumer Cyclical",
        "Technology", "Technology", "Technology"
    ]
    market_caps = [
        3.2e12, 2.5e12, 800e9, 2.8e12, 2.0e12, 1.2e12, 1.9e12, 300e9, 320e9, 280e9
    ]

    for i, symbol in enumerate(symbols):
        ref_data[symbol] = SymbolReferenceData(
            symbol=symbol,
            sector=sectors[i],
            market_cap=market_caps[i],
            float_shares=15e9 if i < 5 else 8e9,
            avg_volume=60e6 if i < 7 else 30e6,
        )
        viable_symbols.add(symbol)

        # Build routing table - first 5 symbols match orb_breakout, all match vwap_reclaim
        strategies: set[str] = {"strat_vwap_reclaim"}
        if i < 5:
            strategies.add("strat_orb_breakout")
        if i < 3:
            strategies.add("strat_orb_scalp")
        routing_table[symbol] = strategies

    return MockUniverseManager(
        _viable_symbols=viable_symbols,
        _reference_cache=ref_data,
        _routing_table=routing_table,
        _last_build_time=datetime.now(UTC) - timedelta(minutes=45),
    )


@pytest.fixture
async def app_state_with_universe(
    app_state: AppState,
    mock_universe_manager: MockUniverseManager,
) -> AppState:
    """Provide AppState with a mock UniverseManager."""
    app_state.universe_manager = mock_universe_manager  # type: ignore[assignment]
    return app_state


@pytest.fixture
async def client_with_universe(
    app_state_with_universe: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide client with AppState containing mock universe manager."""
    app = create_app(app_state_with_universe)
    app.state.app_state = app_state_with_universe
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Test: Universe Status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_universe_status_enabled(
    client_with_universe: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Test universe status endpoint returns correct data when enabled."""
    response = await client_with_universe.get(
        "/api/v1/universe/status",
        headers=auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["enabled"] is True
    assert data["total_symbols"] == 10
    assert data["viable_count"] == 10
    assert "per_strategy_counts" in data
    assert "last_refresh" in data
    assert "reference_data_age_minutes" in data

    # Verify per_strategy_counts
    counts = data["per_strategy_counts"]
    assert counts["strat_orb_breakout"] == 5
    assert counts["strat_orb_scalp"] == 3
    assert counts["strat_vwap_reclaim"] == 10


@pytest.mark.asyncio
async def test_universe_status_disabled(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Test universe status endpoint returns enabled=false when UM not available."""
    response = await client.get(
        "/api/v1/universe/status",
        headers=auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["enabled"] is False
    assert data.get("total_symbols") is None
    assert data.get("viable_count") is None


# ---------------------------------------------------------------------------
# Test: Universe Symbols
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_universe_symbols_paginated(
    client_with_universe: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Test universe symbols endpoint returns paginated results."""
    # First page with 5 items
    response = await client_with_universe.get(
        "/api/v1/universe/symbols?page=1&per_page=5",
        headers=auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["enabled"] is True
    assert len(data["symbols"]) == 5
    assert data["total"] == 10
    assert data["page"] == 1
    assert data["per_page"] == 5
    assert data["pages"] == 2

    # Verify symbol structure
    symbol_data = data["symbols"][0]
    assert "symbol" in symbol_data
    assert "sector" in symbol_data
    assert "market_cap" in symbol_data
    assert "float_shares" in symbol_data
    assert "avg_volume" in symbol_data
    assert "matching_strategies" in symbol_data

    # Second page
    response = await client_with_universe.get(
        "/api/v1/universe/symbols?page=2&per_page=5",
        headers=auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["symbols"]) == 5
    assert data["page"] == 2


@pytest.mark.asyncio
async def test_universe_symbols_strategy_filter(
    client_with_universe: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Test universe symbols endpoint filters by strategy_id."""
    # Filter by strat_orb_breakout (only 5 symbols match)
    response = await client_with_universe.get(
        "/api/v1/universe/symbols?strategy_id=strat_orb_breakout",
        headers=auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["enabled"] is True
    assert data["total"] == 5
    assert len(data["symbols"]) == 5

    # Verify all returned symbols include strat_orb_breakout in matching_strategies
    for symbol in data["symbols"]:
        assert "strat_orb_breakout" in symbol["matching_strategies"]

    # Filter by strat_orb_scalp (only 3 symbols match)
    response = await client_with_universe.get(
        "/api/v1/universe/symbols?strategy_id=strat_orb_scalp",
        headers=auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 3


@pytest.mark.asyncio
async def test_universe_symbols_disabled(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Test universe symbols endpoint returns empty when UM not available."""
    response = await client.get(
        "/api/v1/universe/symbols",
        headers=auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["enabled"] is False
    assert data["symbols"] == []
    assert data["total"] == 0


# ---------------------------------------------------------------------------
# Test: Authentication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_universe_endpoints_require_auth(
    client_with_universe: AsyncClient,
) -> None:
    """Test that universe endpoints require authentication."""
    # Status endpoint without auth
    response = await client_with_universe.get("/api/v1/universe/status")
    assert response.status_code == 401

    # Symbols endpoint without auth
    response = await client_with_universe.get("/api/v1/universe/symbols")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Test: Counts Accuracy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_universe_status_counts_accurate(
    client_with_universe: AsyncClient,
    auth_headers: dict[str, str],
    mock_universe_manager: MockUniverseManager,
) -> None:
    """Test that per_strategy_counts match the routing table exactly."""
    response = await client_with_universe.get(
        "/api/v1/universe/status",
        headers=auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    api_counts = data["per_strategy_counts"]

    # Manually count from the routing table
    expected_counts: dict[str, int] = {}
    for strategies in mock_universe_manager._routing_table.values():
        for strategy_id in strategies:
            expected_counts[strategy_id] = expected_counts.get(strategy_id, 0) + 1

    # Verify they match
    assert api_counts == expected_counts
