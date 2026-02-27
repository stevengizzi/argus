"""Tests for trades API endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestTradesBatchEndpoint:
    """Tests for GET /api/v1/trades/batch endpoint."""

    @pytest.mark.asyncio
    async def test_batch_valid_ids(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Returns trades for valid IDs."""
        # First get some actual trade IDs
        response = await client_with_trades.get(
            "/api/v1/trades?limit=3",
            headers=auth_headers,
        )
        assert response.status_code == 200
        trade_ids = [t["id"] for t in response.json()["trades"]]
        assert len(trade_ids) == 3

        # Now batch fetch them
        ids_param = ",".join(trade_ids)
        response = await client_with_trades.get(
            f"/api/v1/trades/batch?ids={ids_param}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "trades" in data
        assert "count" in data
        assert "timestamp" in data
        assert data["count"] == 3
        assert len(data["trades"]) == 3

        # All requested IDs should be returned
        returned_ids = {t["id"] for t in data["trades"]}
        assert returned_ids == set(trade_ids)

    @pytest.mark.asyncio
    async def test_batch_empty_ids(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Empty ID string returns empty list."""
        response = await client_with_trades.get(
            "/api/v1/trades/batch?ids=",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["trades"] == []
        assert data["count"] == 0

    @pytest.mark.asyncio
    async def test_batch_nonexistent_ids(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Nonexistent IDs are silently omitted."""
        response = await client_with_trades.get(
            "/api/v1/trades/batch?ids=nonexistent1,nonexistent2",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["trades"] == []
        assert data["count"] == 0

    @pytest.mark.asyncio
    async def test_batch_too_many_ids(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Returns 400 if more than 50 IDs are requested."""
        # Generate 51 fake IDs
        ids = [f"id_{i}" for i in range(51)]
        ids_param = ",".join(ids)

        response = await client_with_trades.get(
            f"/api/v1/trades/batch?ids={ids_param}",
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "50" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_batch_unauthenticated(
        self,
        client_with_trades: AsyncClient,
    ) -> None:
        """Returns 401 without valid auth."""
        response = await client_with_trades.get("/api/v1/trades/batch?ids=test")

        assert response.status_code == 401
        assert "detail" in response.json()


class TestTradesEndpoint:
    """Tests for GET /api/v1/trades endpoint."""

    @pytest.mark.asyncio
    async def test_trades_default(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Returns up to 50 most recent trades by default."""
        response = await client_with_trades.get("/api/v1/trades", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "trades" in data
        assert "total_count" in data
        assert "limit" in data
        assert "offset" in data
        assert "timestamp" in data

        # We seeded 15 trades
        assert data["total_count"] == 15
        assert len(data["trades"]) == 15
        assert data["limit"] == 50
        assert data["offset"] == 0

        # Check trade fields
        for trade in data["trades"]:
            assert "id" in trade
            assert "strategy_id" in trade
            assert "symbol" in trade
            assert "side" in trade
            assert "entry_price" in trade
            assert "entry_time" in trade
            assert "pnl_dollars" in trade
            assert "commission" in trade

    @pytest.mark.asyncio
    async def test_trades_pagination(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Pagination with limit and offset works correctly."""
        # First page: 5 trades
        response = await client_with_trades.get(
            "/api/v1/trades?limit=5&offset=0",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["trades"]) == 5
        assert data["total_count"] == 15
        assert data["limit"] == 5
        assert data["offset"] == 0

        first_page_ids = [t["id"] for t in data["trades"]]

        # Second page: next 5 trades
        response = await client_with_trades.get(
            "/api/v1/trades?limit=5&offset=5",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["trades"]) == 5
        assert data["total_count"] == 15
        assert data["offset"] == 5

        second_page_ids = [t["id"] for t in data["trades"]]

        # Pages should not overlap
        assert set(first_page_ids).isdisjoint(set(second_page_ids))

    @pytest.mark.asyncio
    async def test_trades_filter_strategy(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Filter trades by strategy_id works correctly."""
        response = await client_with_trades.get(
            "/api/v1/trades?strategy_id=orb_breakout",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # orb_breakout trades: AAPL, NVDA, MSFT, GOOG, META, AMZN, CRM, ORCL, INTC = 9
        assert data["total_count"] == 9
        for trade in data["trades"]:
            assert trade["strategy_id"] == "orb_breakout"

    @pytest.mark.asyncio
    async def test_trades_filter_date_range(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Filter trades by date_from and date_to works correctly."""
        # Get trades from last 7 days (should exclude very old ones)
        response = await client_with_trades.get(
            "/api/v1/trades?date_from=2026-02-16&date_to=2026-02-23",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Trades within 7 days: today (3) + yesterday (2) + 5-7 days ago (3) = 8
        assert data["total_count"] == 8
        for trade in data["trades"]:
            # All entry_times should be within range
            entry_date = trade["entry_time"][:10]  # Extract YYYY-MM-DD
            assert entry_date >= "2026-02-16"
            assert entry_date <= "2026-02-23"

    @pytest.mark.asyncio
    async def test_trades_filter_outcome_win(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Filter outcome=win returns only profitable trades."""
        response = await client_with_trades.get(
            "/api/v1/trades?outcome=win",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Count wins: trades with net_pnl > 0 (gross - commission)
        # AAPL (350-2=348), TSLA (300-1.5=298.5), MSFT (200-1=199), GOOG (250-1=249),
        # NFLX (200-0.8=199.2), COST (100-0.5=99.5), ORCL (250-1=249),
        # ADBE (250-1.25=248.75), PYPL (150-0.75=149.25) = 9 wins
        # Note: META has gross_pnl=0 so it's not a win (net_pnl=-1)
        assert data["total_count"] == 9
        for trade in data["trades"]:
            assert trade["pnl_dollars"] is not None
            assert trade["pnl_dollars"] > 0

    @pytest.mark.asyncio
    async def test_trades_filter_outcome_loss(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Filter outcome=loss returns only losing trades."""
        response = await client_with_trades.get(
            "/api/v1/trades?outcome=loss",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Losses: NVDA (-252), AMD (-202), AMZN (-121.2), CRM (-201), INTC (-200.5), META (-1) = 6
        # Note: META has gross_pnl=0 but commission=1, so net_pnl=-1 (loss)
        assert data["total_count"] == 6
        for trade in data["trades"]:
            assert trade["pnl_dollars"] is not None
            assert trade["pnl_dollars"] < 0

    @pytest.mark.asyncio
    async def test_trades_combined_filters(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Multiple filters work together."""
        response = await client_with_trades.get(
            "/api/v1/trades?strategy_id=orb_breakout&outcome=win",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # orb_breakout wins: AAPL, MSFT, GOOG, ORCL = 4
        assert data["total_count"] == 4
        for trade in data["trades"]:
            assert trade["strategy_id"] == "orb_breakout"
            assert trade["pnl_dollars"] > 0

    @pytest.mark.asyncio
    async def test_trades_empty_result(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """No matches returns empty list with total_count=0."""
        response = await client_with_trades.get(
            "/api/v1/trades?strategy_id=nonexistent_strategy",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["trades"] == []
        assert data["total_count"] == 0
        assert data["limit"] == 50
        assert data["offset"] == 0

    @pytest.mark.asyncio
    async def test_trades_total_count_for_pagination(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """total_count reflects filtered total, not returned count."""
        response = await client_with_trades.get(
            "/api/v1/trades?strategy_id=orb_scalp&limit=2",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # orb_scalp has 6 trades total, but only 2 returned
        assert len(data["trades"]) == 2
        assert data["total_count"] == 6

    @pytest.mark.asyncio
    async def test_trades_unauthenticated(
        self,
        client_with_trades: AsyncClient,
    ) -> None:
        """Returns 401 without valid auth."""
        response = await client_with_trades.get("/api/v1/trades")

        assert response.status_code == 401
        assert "detail" in response.json()

    @pytest.mark.asyncio
    async def test_trades_limit_bounds(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Limit parameter respects bounds (1-250)."""
        # Valid limit
        response = await client_with_trades.get(
            "/api/v1/trades?limit=100",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["limit"] == 100

        # Limit too high should be rejected
        response = await client_with_trades.get(
            "/api/v1/trades?limit=500",
            headers=auth_headers,
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_trades_filter_symbol(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Filter trades by symbol returns only matching trades."""
        response = await client_with_trades.get(
            "/api/v1/trades?symbol=AAPL",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # AAPL appears once in the seeded data
        assert data["total_count"] == 1
        assert len(data["trades"]) == 1
        for trade in data["trades"]:
            assert trade["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_trades_filter_symbol_combined(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Symbol filter works with other filters (strategy_id)."""
        # NVDA is in orb_breakout
        response = await client_with_trades.get(
            "/api/v1/trades?symbol=NVDA&strategy_id=orb_breakout",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should find the NVDA trade from orb_breakout
        assert data["total_count"] == 1
        for trade in data["trades"]:
            assert trade["symbol"] == "NVDA"
            assert trade["strategy_id"] == "orb_breakout"
