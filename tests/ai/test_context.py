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


class TestDashboardFullPortfolioContext:
    """Test Dashboard context includes all positions (>5) and portfolio aggregates."""

    @pytest.fixture
    def builder(self) -> SystemContextBuilder:
        """Create a SystemContextBuilder instance."""
        return SystemContextBuilder()

    @pytest.mark.asyncio
    async def test_dashboard_includes_all_positions_when_more_than_five_exist(
        self, builder: SystemContextBuilder
    ) -> None:
        """Test that Dashboard context includes all open positions when there are >5."""
        from datetime import datetime, timezone

        def _make_position(symbol_idx: int, unrealized_sign: float) -> MagicMock:
            pos = MagicMock()
            pos.strategy_id = f"strategy_{symbol_idx % 3}"
            pos.shares_remaining = 100
            pos.entry_price = 100.0
            pos.original_stop_price = 98.0
            pos.realized_pnl = 0.0
            pos.is_fully_closed = False
            pos.entry_time = datetime(2026, 4, 1, 14, 0, 0, tzinfo=timezone.utc)
            return pos

        positions_by_symbol = {
            f"SYM{i}": [_make_position(i, 1.0 if i % 2 == 0 else -1.0)]
            for i in range(8)
        }

        mock_order_manager = MagicMock()
        mock_order_manager.get_managed_positions.return_value = positions_by_symbol

        mock_data_service = MagicMock()
        mock_data_service.get_current_price = AsyncMock(return_value=102.0)

        state = MockAppState()
        state.order_manager = mock_order_manager
        state.data_service = mock_data_service

        context = await builder.build_context(
            page="Dashboard",
            context_data={},
            app_state=state,
        )

        positions = context["page_context"]["positions"]
        assert len(positions) == 8, "All 8 positions should be included (not capped at 5)"

        # Every position should have the enriched fields
        for pos in positions:
            assert "current_price" in pos
            assert "side" in pos
            assert pos["side"] == "long"
            assert "r_multiple" in pos
            assert "hold_duration_seconds" in pos

    @pytest.mark.asyncio
    async def test_dashboard_portfolio_summary_includes_aggregates(
        self, builder: SystemContextBuilder
    ) -> None:
        """Test that portfolio_summary includes aggregated position statistics."""
        from datetime import datetime, timezone

        winning_pos = MagicMock()
        winning_pos.strategy_id = "orb_breakout"
        winning_pos.shares_remaining = 100
        winning_pos.entry_price = 100.0
        winning_pos.original_stop_price = 98.0
        winning_pos.realized_pnl = 0.0
        winning_pos.is_fully_closed = False
        winning_pos.entry_time = datetime(2026, 4, 1, 14, 0, 0, tzinfo=timezone.utc)

        losing_pos = MagicMock()
        losing_pos.strategy_id = "vwap_reclaim"
        losing_pos.shares_remaining = 50
        losing_pos.entry_price = 200.0
        losing_pos.original_stop_price = 198.0
        losing_pos.realized_pnl = 0.0
        losing_pos.is_fully_closed = False
        losing_pos.entry_time = datetime(2026, 4, 1, 14, 0, 0, tzinfo=timezone.utc)

        mock_order_manager = MagicMock()
        mock_order_manager.get_managed_positions.return_value = {
            "AAPL": [winning_pos],   # current_price 102 → unrealized +200
            "TSLA": [losing_pos],    # current_price 198 → unrealized -100
        }

        mock_data_service = MagicMock()
        # AAPL → 102 (winning), TSLA → 198 (losing)
        mock_data_service.get_current_price = AsyncMock(side_effect=[102.0, 198.0])

        state = MockAppState()
        state.order_manager = mock_order_manager
        state.data_service = mock_data_service

        context = await builder.build_context(
            page="Dashboard",
            context_data={},
            app_state=state,
        )

        summary = context["page_context"]["portfolio_summary"]
        assert summary["total_position_count"] == 2
        assert summary["winning_count"] == 1
        assert summary["losing_count"] == 1
        assert "count_by_strategy" in summary
        assert summary["count_by_strategy"]["orb_breakout"] == 1
        assert summary["count_by_strategy"]["vwap_reclaim"] == 1
        assert "total_unrealized_pnl" in summary


class TestSystemPageContextBody:
    """Cover ``_build_system_page_context`` (lines 472-501) — the method body is
    entirely untested; the existing ``test_system_page_context`` only exercises the
    ``health_monitor=None`` fallback + empty connections.
    """

    @pytest.fixture
    def builder(self) -> SystemContextBuilder:
        return SystemContextBuilder()

    @pytest.mark.asyncio
    async def test_system_page_with_all_connections(
        self, builder: SystemContextBuilder
    ) -> None:
        """health_monitor + broker + data_service set with truthy states → fully
        populated health dict + connections dict."""
        health_monitor = MagicMock()
        health_monitor.status = "healthy"
        broker = MagicMock()
        broker.is_connected = True
        data_service = MagicMock()
        data_service.is_connected = True

        state = MockAppState(
            health_monitor=health_monitor,
            broker=broker,
            data_service=data_service,
        )

        context = await builder.build_context(
            page="System",
            context_data={"uptime": "3d 4h"},
            app_state=state,
        )
        page = context["page_context"]

        assert page["health"] == {"status": "healthy", "uptime": "3d 4h"}
        assert page["connections"]["broker"] == "connected"
        assert page["connections"]["data_feed"] == "connected"

    @pytest.mark.asyncio
    async def test_system_page_all_disconnected(
        self, builder: SystemContextBuilder
    ) -> None:
        """broker/data_service with ``is_connected=False`` → 'disconnected'."""
        broker = MagicMock()
        broker.is_connected = False
        data_service = MagicMock()
        data_service.is_connected = False

        state = MockAppState(broker=broker, data_service=data_service)
        context = await builder.build_context(
            page="System", context_data={}, app_state=state
        )

        assert context["page_context"]["connections"]["broker"] == "disconnected"
        assert context["page_context"]["connections"]["data_feed"] == "disconnected"

    @pytest.mark.asyncio
    async def test_system_page_health_monitor_raises(
        self, builder: SystemContextBuilder
    ) -> None:
        """Attribute access on health_monitor.status raises → caught, fallback dict."""

        class _BrokenHealthMonitor:
            @property
            def status(self) -> str:
                raise RuntimeError("status probe failed")

        state = MockAppState(health_monitor=_BrokenHealthMonitor())
        context = await builder.build_context(
            page="System", context_data={}, app_state=state
        )

        assert context["page_context"]["health"] == {
            "status": "unknown",
            "uptime": "N/A",
        }

    @pytest.mark.asyncio
    async def test_system_page_broker_connection_raises(
        self, builder: SystemContextBuilder
    ) -> None:
        """broker.is_connected property raising RuntimeError → 'unknown'."""

        class _BrokenBroker:
            @property
            def is_connected(self) -> bool:
                raise RuntimeError("broker probe failed")

        state = MockAppState(broker=_BrokenBroker())
        context = await builder.build_context(
            page="System", context_data={}, app_state=state
        )

        assert context["page_context"]["connections"]["broker"] == "unknown"

    @pytest.mark.asyncio
    async def test_system_page_data_service_connection_raises(
        self, builder: SystemContextBuilder
    ) -> None:
        """data_service.is_connected raising → 'unknown'."""

        class _BrokenDataService:
            @property
            def is_connected(self) -> bool:
                raise RuntimeError("data probe failed")

        state = MockAppState(data_service=_BrokenDataService())
        context = await builder.build_context(
            page="System", context_data={}, app_state=state
        )

        assert context["page_context"]["connections"]["data_feed"] == "unknown"


class TestBuildSystemStateErrorPaths:
    """Cover ``_build_system_state`` regime/equity/pnl/circuit-breaker branches
    that no existing test exercises (lines 84-85, 91-99, 116-125).
    """

    @pytest.fixture
    def builder(self) -> SystemContextBuilder:
        return SystemContextBuilder()

    @pytest.mark.asyncio
    async def test_regime_from_orchestrator_string(
        self, builder: SystemContextBuilder
    ) -> None:
        """Orchestrator set with a truthy regime → state['regime'] reflects it."""
        orchestrator = MagicMock()
        orchestrator.current_regime = "trending_up"
        state = MockAppState(orchestrator=orchestrator)

        context = await builder.build_context(
            page="Dashboard", context_data={}, app_state=state
        )

        assert context["system"]["regime"] == "trending_up"

    @pytest.mark.asyncio
    async def test_regime_from_orchestrator_none_falls_back_to_unknown(
        self, builder: SystemContextBuilder
    ) -> None:
        """Orchestrator set but current_regime is None → 'unknown'."""
        orchestrator = MagicMock()
        orchestrator.current_regime = None
        state = MockAppState(orchestrator=orchestrator)

        context = await builder.build_context(
            page="Dashboard", context_data={}, app_state=state
        )

        assert context["system"]["regime"] == "unknown"

    @pytest.mark.asyncio
    async def test_broker_account_equity_populated(
        self, builder: SystemContextBuilder
    ) -> None:
        """broker.get_account returns account → account_equity populated from .equity."""
        account = MagicMock()
        account.equity = 125_000.0
        broker = MagicMock()
        broker.get_account = AsyncMock(return_value=account)

        state = MockAppState(broker=broker)
        context = await builder.build_context(
            page="Dashboard", context_data={}, app_state=state
        )

        assert context["system"]["account_equity"] == 125_000.0

    @pytest.mark.asyncio
    async def test_broker_get_account_returns_none_falls_back_to_zero(
        self, builder: SystemContextBuilder
    ) -> None:
        """broker.get_account returns None → fallback 0.0."""
        broker = MagicMock()
        broker.get_account = AsyncMock(return_value=None)

        state = MockAppState(broker=broker)
        context = await builder.build_context(
            page="Dashboard", context_data={}, app_state=state
        )

        assert context["system"]["account_equity"] == 0.0

    @pytest.mark.asyncio
    async def test_broker_get_account_raises_falls_back_to_zero(
        self, builder: SystemContextBuilder
    ) -> None:
        """broker.get_account raises → caught, account_equity = 0.0."""
        broker = MagicMock()
        broker.get_account = AsyncMock(side_effect=RuntimeError("broker dead"))

        state = MockAppState(broker=broker)
        context = await builder.build_context(
            page="Dashboard", context_data={}, app_state=state
        )

        assert context["system"]["account_equity"] == 0.0

    @pytest.mark.asyncio
    async def test_trade_logger_daily_pnl_populated(
        self, builder: SystemContextBuilder
    ) -> None:
        """trade_logger.get_todays_pnl returns value → daily_pnl populated."""
        trade_logger = MagicMock()
        trade_logger.get_todays_pnl = AsyncMock(return_value=250.75)

        state = MockAppState(trade_logger=trade_logger)
        context = await builder.build_context(
            page="Dashboard", context_data={}, app_state=state
        )

        assert context["system"]["daily_pnl"] == 250.75

    @pytest.mark.asyncio
    async def test_trade_logger_get_todays_pnl_raises_falls_back_to_zero(
        self, builder: SystemContextBuilder
    ) -> None:
        """trade_logger.get_todays_pnl raises → caught, daily_pnl = 0.0."""
        trade_logger = MagicMock()
        trade_logger.get_todays_pnl = AsyncMock(side_effect=RuntimeError("db down"))

        state = MockAppState(trade_logger=trade_logger)
        context = await builder.build_context(
            page="Dashboard", context_data={}, app_state=state
        )

        assert context["system"]["daily_pnl"] == 0.0

    @pytest.mark.asyncio
    async def test_circuit_breaker_active_is_appended(
        self, builder: SystemContextBuilder
    ) -> None:
        """Active circuit breaker → appended to state['circuit_breakers']."""
        risk_manager = MagicMock()
        risk_manager.circuit_breaker_active = True

        state = MockAppState(risk_manager=risk_manager)
        context = await builder.build_context(
            page="Dashboard", context_data={}, app_state=state
        )

        breakers = context["system"]["circuit_breakers"]
        assert len(breakers) == 1
        assert breakers[0]["type"] == "risk_manager"

    @pytest.mark.asyncio
    async def test_circuit_breaker_inactive_stays_empty(
        self, builder: SystemContextBuilder
    ) -> None:
        """Inactive circuit breaker → circuit_breakers list stays empty."""
        risk_manager = MagicMock()
        risk_manager.circuit_breaker_active = False

        state = MockAppState(risk_manager=risk_manager)
        context = await builder.build_context(
            page="Dashboard", context_data={}, app_state=state
        )

        assert context["system"]["circuit_breakers"] == []

    @pytest.mark.asyncio
    async def test_risk_manager_attribute_raises_is_caught(
        self, builder: SystemContextBuilder
    ) -> None:
        """risk_manager.circuit_breaker_active raising RuntimeError → caught silently."""

        class _BrokenRiskManager:
            @property
            def circuit_breaker_active(self) -> bool:
                raise RuntimeError("rm probe failed")

        state = MockAppState(risk_manager=_BrokenRiskManager())
        context = await builder.build_context(
            page="Dashboard", context_data={}, app_state=state
        )

        # No breaker appended, no exception propagated.
        assert context["system"]["circuit_breakers"] == []


class TestPageBuilderFallbacks:
    """Cover branches the enumerated gap spec calls out under 'Dashboard edge cases
    and Debrief tail (lines 269-271, 277-278, 405-412)'.
    """

    @pytest.fixture
    def builder(self) -> SystemContextBuilder:
        return SystemContextBuilder()

    @pytest.mark.asyncio
    async def test_dashboard_regime_pulled_from_orchestrator(
        self, builder: SystemContextBuilder
    ) -> None:
        """When orchestrator is set, Dashboard.regime is derived from it (lines 277-278)."""
        orchestrator = MagicMock()
        orchestrator.current_regime = "choppy"

        state = MockAppState(orchestrator=orchestrator)
        context = await builder.build_context(
            page="Dashboard", context_data={}, app_state=state
        )

        assert context["page_context"]["regime"] == "choppy"

    @pytest.mark.asyncio
    async def test_dashboard_order_manager_raises_positions_empty(
        self, builder: SystemContextBuilder
    ) -> None:
        """order_manager.get_managed_positions raising → caught, positions = []."""
        order_manager = MagicMock()
        order_manager.get_managed_positions.side_effect = RuntimeError("om broken")

        state = MockAppState(order_manager=order_manager)
        context = await builder.build_context(
            page="Dashboard", context_data={}, app_state=state
        )

        assert context["page_context"]["positions"] == []

    @pytest.mark.asyncio
    async def test_pattern_library_with_selected_pattern(
        self, builder: SystemContextBuilder
    ) -> None:
        """PatternLibrary page surfaces selected_pattern from context_data (lines 407-408)."""
        state = MockAppState()
        context = await builder.build_context(
            page="PatternLibrary",
            context_data={"selected_pattern": {"name": "Bull Flag"}},
            app_state=state,
        )

        assert context["page_context"]["selected_pattern"] == {"name": "Bull Flag"}

    @pytest.mark.asyncio
    async def test_pattern_library_no_selected_pattern_is_none(
        self, builder: SystemContextBuilder
    ) -> None:
        """PatternLibrary page → selected_pattern None when not provided (lines 409-410)."""
        state = MockAppState()
        context = await builder.build_context(
            page="PatternLibrary", context_data={}, app_state=state
        )

        assert context["page_context"]["selected_pattern"] is None


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
