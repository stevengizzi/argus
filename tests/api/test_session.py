"""Tests for session summary API endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestSessionSummaryEndpoint:
    """Tests for GET /api/v1/session-summary endpoint."""

    @pytest.mark.asyncio
    async def test_session_summary_returns_correct_structure(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Returns session summary with all required fields."""
        # Use Feb 23, 2026 - the date of seeded trades matching test_clock
        response = await client_with_trades.get(
            "/api/v1/session-summary?date=2026-02-23",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "date" in data
        assert "trade_count" in data
        assert "wins" in data
        assert "losses" in data
        assert "breakeven" in data
        assert "net_pnl" in data
        assert "win_rate" in data
        assert "best_trade" in data
        assert "worst_trade" in data
        assert "fill_rate" in data
        assert "regime" in data
        assert "active_strategies" in data
        assert "timestamp" in data

        # Feb 23 trades: AAPL (win), NVDA (loss), TSLA (win) = 3 trades
        # Based on seeded_trade_logger fixture in conftest.py
        assert data["trade_count"] == 3
        assert data["wins"] == 2  # AAPL, TSLA
        assert data["losses"] == 1  # NVDA

    @pytest.mark.asyncio
    async def test_session_summary_calculates_correct_pnl(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Net P&L is correctly calculated from trades."""
        # Use Feb 23, 2026 - the date of seeded trades
        response = await client_with_trades.get(
            "/api/v1/session-summary?date=2026-02-23",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # AAPL: gross=350, commission=2 -> net=348
        # NVDA: gross=-250, commission=2 -> net=-252
        # TSLA: gross=300, commission=1.5 -> net=298.5
        # Total: 348 - 252 + 298.5 = 394.5
        expected_pnl = 348.0 - 252.0 + 298.5
        assert abs(data["net_pnl"] - expected_pnl) < 0.01

    @pytest.mark.asyncio
    async def test_session_summary_identifies_best_worst_trade(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Best and worst trades are correctly identified by R-multiple."""
        # Use Feb 23, 2026 - the date of seeded trades
        response = await client_with_trades.get(
            "/api/v1/session-summary?date=2026-02-23",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Best trade should have highest R-multiple
        assert data["best_trade"] is not None
        assert "symbol" in data["best_trade"]
        assert "r_multiple" in data["best_trade"]
        assert "pnl_dollars" in data["best_trade"]
        assert "strategy_id" in data["best_trade"]

        # Worst trade should have lowest R-multiple
        assert data["worst_trade"] is not None
        assert "symbol" in data["worst_trade"]
        assert "r_multiple" in data["worst_trade"]
        assert data["worst_trade"]["r_multiple"] <= data["best_trade"]["r_multiple"]

    @pytest.mark.asyncio
    async def test_session_summary_specific_date(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Specific date parameter filters trades correctly."""
        # Query yesterday's trades (Feb 22, 2026 based on test clock Feb 23)
        response = await client_with_trades.get(
            "/api/v1/session-summary?date=2026-02-22",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Yesterday's trades: MSFT (win), AMD (loss) = 2 trades
        assert data["date"] == "2026-02-22"
        assert data["trade_count"] == 2
        assert data["wins"] == 1
        assert data["losses"] == 1

    @pytest.mark.asyncio
    async def test_session_summary_empty_day(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Day with no trades returns zeros."""
        # Query a date with no trades
        response = await client_with_trades.get(
            "/api/v1/session-summary?date=2026-01-01",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["date"] == "2026-01-01"
        assert data["trade_count"] == 0
        assert data["wins"] == 0
        assert data["losses"] == 0
        assert data["net_pnl"] == 0.0
        assert data["win_rate"] == 0.0
        assert data["best_trade"] is None
        assert data["worst_trade"] is None

    @pytest.mark.asyncio
    async def test_session_summary_unauthenticated(
        self,
        client_with_trades: AsyncClient,
    ) -> None:
        """Returns 401 without valid auth."""
        response = await client_with_trades.get("/api/v1/session-summary")

        assert response.status_code == 401
        assert "detail" in response.json()
