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
        assert "taipei" in system["current_time"]

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
