"""Tests for SystemContextBuilder."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.ai.context import SystemContextBuilder


@dataclass
class MockAppState:
    """Mock AppState for testing."""

    strategies: dict[str, Any] = field(default_factory=dict)
    orchestrator: Any = None
    broker: Any = None
    trade_logger: Any = None
    risk_manager: Any = None
    order_manager: Any = None
    health_monitor: Any = None
    data_service: Any = None


class TestSystemContextBuilder:
    """Test SystemContextBuilder."""

    @pytest.fixture
    def builder(self) -> SystemContextBuilder:
        """Create a SystemContextBuilder instance."""
        return SystemContextBuilder()

    @pytest.fixture
    def mock_app_state(self) -> MockAppState:
        """Create a mock AppState with basic components."""
        state = MockAppState()
        state.strategies = {"orb_breakout": MagicMock(), "vwap_reclaim": MagicMock()}
        return state

    @pytest.mark.asyncio
    async def test_build_context_returns_system_and_page(
        self, builder: SystemContextBuilder, mock_app_state: MockAppState
    ) -> None:
        """Test that build_context returns system and page context."""
        context = await builder.build_context(
            page="Dashboard",
            context_data={},
            app_state=mock_app_state,
        )

        assert "system" in context
        assert "page" in context
        assert "page_context" in context
        assert context["page"] == "Dashboard"

    @pytest.mark.asyncio
    async def test_system_state_includes_time_info(
        self, builder: SystemContextBuilder, mock_app_state: MockAppState
    ) -> None:
        """Test that system state includes time information."""
        context = await builder.build_context(
            page="Dashboard",
            context_data={},
            app_state=mock_app_state,
        )

        system = context["system"]
        assert "current_time" in system
        assert "utc" in system["current_time"]
        assert "et" in system["current_time"]
        assert "cape_town" in system["current_time"]

    @pytest.mark.asyncio
    async def test_system_state_includes_strategy_count(
        self, builder: SystemContextBuilder, mock_app_state: MockAppState
    ) -> None:
        """Test that system state includes active strategy count."""
        context = await builder.build_context(
            page="Dashboard",
            context_data={},
            app_state=mock_app_state,
        )

        assert context["system"]["active_strategy_count"] == 2


class TestPageSpecificContext:
    """Test page-specific context building."""

    @pytest.fixture
    def builder(self) -> SystemContextBuilder:
        """Create a SystemContextBuilder instance."""
        return SystemContextBuilder()

    @pytest.fixture
    def mock_app_state(self) -> MockAppState:
        """Create a mock AppState."""
        return MockAppState()

    @pytest.mark.asyncio
    async def test_dashboard_context(
        self, builder: SystemContextBuilder, mock_app_state: MockAppState
    ) -> None:
        """Test Dashboard page context building."""
        context_data = {
            "equity": 100000.0,
            "daily_pnl": 250.0,
            "open_positions_count": 3,
            "positions": [{"symbol": "AAPL", "shares": 100}],
        }

        context = await builder.build_context(
            page="Dashboard",
            context_data=context_data,
            app_state=mock_app_state,
        )

        page_context = context["page_context"]
        assert "portfolio_summary" in page_context
        assert page_context["portfolio_summary"]["equity"] == 100000.0

    @pytest.mark.asyncio
    async def test_trades_context(
        self, builder: SystemContextBuilder, mock_app_state: MockAppState
    ) -> None:
        """Test Trades page context building."""
        context_data = {
            "recent_trades": [
                {"symbol": "TSLA", "pnl": 150.0, "outcome": "win"},
            ],
            "filters": {"strategy": "orb_breakout"},
        }

        context = await builder.build_context(
            page="Trades",
            context_data=context_data,
            app_state=mock_app_state,
        )

        page_context = context["page_context"]
        assert "recent_trades" in page_context
        assert page_context["filters"]["strategy"] == "orb_breakout"

    @pytest.mark.asyncio
    async def test_performance_context(
        self, builder: SystemContextBuilder, mock_app_state: MockAppState
    ) -> None:
        """Test Performance page context building."""
        context_data = {
            "metrics": {
                "win_rate": 0.65,
                "profit_factor": 2.1,
                "sharpe_ratio": 1.5,
                "net_pnl": 5000.0,
            },
            "timeframe": "30d",
        }

        context = await builder.build_context(
            page="Performance",
            context_data=context_data,
            app_state=mock_app_state,
        )

        page_context = context["page_context"]
        assert page_context["metrics"]["win_rate"] == 0.65
        assert page_context["timeframe"] == "30d"

    @pytest.mark.asyncio
    async def test_orchestrator_context(
        self, builder: SystemContextBuilder, mock_app_state: MockAppState
    ) -> None:
        """Test Orchestrator page context building."""
        context_data = {
            "allocations": [
                {"strategy_id": "orb_breakout", "pct": 40.0},
                {"strategy_id": "vwap_reclaim", "pct": 30.0},
            ],
            "schedule_state": "active",
        }

        context = await builder.build_context(
            page="Orchestrator",
            context_data=context_data,
            app_state=mock_app_state,
        )

        page_context = context["page_context"]
        assert len(page_context["allocations"]) == 2
        assert page_context["schedule_state"] == "active"

    @pytest.mark.asyncio
    async def test_system_page_context(
        self, builder: SystemContextBuilder, mock_app_state: MockAppState
    ) -> None:
        """Test System page context building."""
        context_data = {
            "health": {"status": "healthy", "uptime": "2d 4h"},
        }

        context = await builder.build_context(
            page="System",
            context_data=context_data,
            app_state=mock_app_state,
        )

        page_context = context["page_context"]
        assert "health" in page_context
        assert "connections" in page_context

    @pytest.mark.asyncio
    async def test_unknown_page_returns_context_data(
        self, builder: SystemContextBuilder, mock_app_state: MockAppState
    ) -> None:
        """Test that unknown pages return context_data as-is."""
        context_data = {"custom_field": "custom_value"}

        context = await builder.build_context(
            page="UnknownPage",
            context_data=context_data,
            app_state=mock_app_state,
        )

        assert context["page_context"] == context_data


class TestTradesContextNetPnl:
    """Test that Trades context uses net_pnl column from trade dicts."""

    @pytest.fixture
    def builder(self) -> SystemContextBuilder:
        """Create a SystemContextBuilder instance."""
        return SystemContextBuilder()

    @pytest.mark.asyncio
    async def test_trades_context_uses_net_pnl_key(self, builder: SystemContextBuilder) -> None:
        """Test that _build_trades_context uses net_pnl key from trade dicts."""
        mock_trade_logger = MagicMock()
        mock_trade_logger.query_trades = AsyncMock(return_value=[
            {"symbol": "AAPL", "net_pnl": 125.50, "outcome": "win", "strategy_id": "orb_breakout"},
            {"symbol": "TSLA", "net_pnl": -75.25, "outcome": "loss", "strategy_id": "vwap_reclaim"},
        ])

        state = MockAppState()
        state.trade_logger = mock_trade_logger

        context = await builder.build_context(
            page="Trades",
            context_data={},
            app_state=state,
        )

        recent_trades = context["page_context"]["recent_trades"]
        assert len(recent_trades) == 2
        assert recent_trades[0]["pnl"] == 125.50
        assert recent_trades[1]["pnl"] == -75.25


class TestDashboardPositionsIteration:
    """Test Dashboard context correctly iterates managed positions."""

    @pytest.fixture
    def builder(self) -> SystemContextBuilder:
        """Create a SystemContextBuilder instance."""
        return SystemContextBuilder()

    @pytest.mark.asyncio
    async def test_dashboard_positions_iterates_dict_items(
        self, builder: SystemContextBuilder
    ) -> None:
        """Test that Dashboard context correctly iterates get_managed_positions() dict."""
        mock_position = MagicMock()
        mock_position.strategy_id = "orb_breakout"
        mock_position.shares_remaining = 100
        mock_position.entry_price = 150.0
        mock_position.realized_pnl = 50.0
        mock_position.is_fully_closed = False

        mock_order_manager = MagicMock()
        mock_order_manager.get_managed_positions.return_value = {
            "AAPL": [mock_position],
        }

        state = MockAppState()
        state.order_manager = mock_order_manager

        context = await builder.build_context(
            page="Dashboard",
            context_data={},
            app_state=state,
        )

        positions = context["page_context"]["positions"]
        assert len(positions) == 1
        assert positions[0]["symbol"] == "AAPL"
        assert positions[0]["shares"] == 100
        assert positions[0]["entry_price"] == 150.0
        assert positions[0]["strategy_id"] == "orb_breakout"
        assert positions[0]["realized_pnl"] == 50.0

    @pytest.mark.asyncio
    async def test_dashboard_positions_computes_unrealized_pnl(
        self, builder: SystemContextBuilder
    ) -> None:
        """Test that Dashboard context computes unrealized P&L from data service."""
        mock_position = MagicMock()
        mock_position.strategy_id = "orb_breakout"
        mock_position.shares_remaining = 100
        mock_position.entry_price = 150.0
        mock_position.realized_pnl = 0.0
        mock_position.is_fully_closed = False

        mock_order_manager = MagicMock()
        mock_order_manager.get_managed_positions.return_value = {
            "AAPL": [mock_position],
        }

        mock_data_service = MagicMock()
        mock_data_service.get_current_price = AsyncMock(return_value=155.0)

        state = MockAppState()
        state.order_manager = mock_order_manager
        state.data_service = mock_data_service

        context = await builder.build_context(
            page="Dashboard",
            context_data={},
            app_state=state,
        )

        positions = context["page_context"]["positions"]
        assert len(positions) == 1
        # Unrealized P&L: (155 - 150) * 100 = 500
        assert positions[0]["unrealized_pnl"] == 500.0

    @pytest.mark.asyncio
    async def test_dashboard_positions_handles_none_current_price(
        self, builder: SystemContextBuilder
    ) -> None:
        """Test that Dashboard context handles get_current_price returning None."""
        mock_position = MagicMock()
        mock_position.strategy_id = "orb_breakout"
        mock_position.shares_remaining = 100
        mock_position.entry_price = 150.0
        mock_position.realized_pnl = 0.0
        mock_position.is_fully_closed = False

        mock_order_manager = MagicMock()
        mock_order_manager.get_managed_positions.return_value = {
            "AAPL": [mock_position],
        }

        mock_data_service = MagicMock()
        mock_data_service.get_current_price = AsyncMock(return_value=None)

        state = MockAppState()
        state.order_manager = mock_order_manager
        state.data_service = mock_data_service

        context = await builder.build_context(
            page="Dashboard",
            context_data={},
            app_state=state,
        )

        positions = context["page_context"]["positions"]
        assert len(positions) == 1
        # Unrealized P&L should be 0.0 when price is None
        assert positions[0]["unrealized_pnl"] == 0.0

    @pytest.mark.asyncio
    async def test_dashboard_positions_excludes_fully_closed(
        self, builder: SystemContextBuilder
    ) -> None:
        """Test that Dashboard context excludes fully closed positions."""
        open_position = MagicMock()
        open_position.strategy_id = "orb_breakout"
        open_position.shares_remaining = 100
        open_position.entry_price = 150.0
        open_position.realized_pnl = 0.0
        open_position.is_fully_closed = False

        closed_position = MagicMock()
        closed_position.is_fully_closed = True

        mock_order_manager = MagicMock()
        mock_order_manager.get_managed_positions.return_value = {
            "AAPL": [open_position, closed_position],
        }

        state = MockAppState()
        state.order_manager = mock_order_manager

        context = await builder.build_context(
            page="Dashboard",
            context_data={},
            app_state=state,
        )

        positions = context["page_context"]["positions"]
        assert len(positions) == 1


class TestDebriefDateFilter:
    """Test Debrief context uses ET timezone for date filtering."""

    @pytest.fixture
    def builder(self) -> SystemContextBuilder:
        """Create a SystemContextBuilder instance."""
        return SystemContextBuilder()

    @pytest.mark.asyncio
    async def test_debrief_uses_et_timezone_for_date_filter(
        self, builder: SystemContextBuilder
    ) -> None:
        """Test that Debrief context uses ET timezone for date filtering."""
        from datetime import datetime
        from unittest.mock import patch
        from zoneinfo import ZoneInfo

        # Mock a time where Cape Town date (UTC+2) differs from ET date (UTC-5)
        # At 1:00 AM Cape Town (March 7), it's 6:00 PM ET (March 6)
        mock_time = datetime(2026, 3, 7, 1, 0, 0, tzinfo=ZoneInfo("Africa/Johannesburg"))
        et_date = mock_time.astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
        assert et_date == "2026-03-06"  # Confirm it's previous day in ET

        mock_trade_logger = MagicMock()
        mock_trade_logger.get_todays_pnl = AsyncMock(return_value=100.0)
        # Trade that matches ET date (March 6), not Cape Town date (March 7)
        mock_trade_logger.query_trades = AsyncMock(return_value=[
            {"symbol": "AAPL", "exit_time": "2026-03-06T14:30:00"},  # ET date
            {"symbol": "TSLA", "exit_time": "2026-03-07T10:00:00"},  # Cape Town date
        ])

        state = MockAppState()
        state.trade_logger = mock_trade_logger

        with patch("argus.ai.context.datetime") as mock_datetime:
            # Make datetime.now(ZoneInfo("America/New_York")) return the ET time
            et_time = mock_time.astimezone(ZoneInfo("America/New_York"))
            mock_datetime.now.return_value = et_time
            # Preserve the ZoneInfo for the constructor
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            context = await builder.build_context(
                page="Debrief",
                context_data={},
                app_state=state,
            )

        # Only the trade matching ET date should be counted
        assert context["page_context"]["today_summary"]["total_trades"] == 1
