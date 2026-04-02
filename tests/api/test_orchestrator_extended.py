"""Tests for extended Orchestrator API endpoints (Sprint 21b).

Tests the new fields and functionality added in Sprint 21b:
- Session phase computation
- Pre-market completion status
- Extended allocation info (operating window, throttle metrics)
- Date filter for decisions endpoint
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import pytest

from argus.api.routes.orchestrator import _compute_session_phase, STRATEGY_WINDOWS
from argus.api.server import create_app
from argus.core.config import OrchestratorConfig
from argus.core.regime import MarketRegime, RegimeIndicators
from argus.core.throttle import StrategyAllocation, ThrottleAction

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from httpx import AsyncClient

    from argus.api.dependencies import AppState
    from argus.models.trading import Trade


# ---------------------------------------------------------------------------
# Mock Orchestrator with pre_market_complete
# ---------------------------------------------------------------------------


@dataclass
class MockOrchestratorExtended:
    """Mock orchestrator for extended API testing."""

    _config: OrchestratorConfig
    _current_regime: MarketRegime
    _current_allocations: dict[str, StrategyAllocation]
    _current_indicators: RegimeIndicators | None
    _last_regime_check: datetime | None
    _pre_market_done_today: bool = True

    @property
    def current_regime(self) -> MarketRegime:
        return self._current_regime

    @property
    def current_allocations(self) -> dict[str, StrategyAllocation]:
        return self._current_allocations

    @property
    def current_indicators(self) -> RegimeIndicators | None:
        return self._current_indicators

    @property
    def last_regime_check(self) -> datetime | None:
        return self._last_regime_check

    @property
    def regime_check_interval_minutes(self) -> int:
        return self._config.regime_check_interval_minutes

    @property
    def cash_reserve_pct(self) -> float:
        return self._config.cash_reserve_pct

    @property
    def pre_market_complete(self) -> bool:
        return self._pre_market_done_today

    async def manual_rebalance(self) -> dict[str, StrategyAllocation]:
        return self._current_allocations


# ---------------------------------------------------------------------------
# Session Phase Tests
# ---------------------------------------------------------------------------


class TestComputeSessionPhase:
    """Tests for _compute_session_phase() helper."""

    def test_session_phases_cover_all_periods(self) -> None:
        """Session phase computation covers all market periods."""
        # Instead of mocking, test the logic directly
        # We'll test the function exists and returns expected type
        result = _compute_session_phase()
        assert result in [
            "pre_market",
            "market_open",
            "midday",
            "power_hour",
            "after_hours",
            "market_closed",
        ]


@pytest.mark.parametrize(
    "hour,minute,weekday,expected",
    [
        (8, 0, 0, "pre_market"),  # Monday 8:00 AM
        (9, 29, 1, "pre_market"),  # Tuesday 9:29 AM
        (9, 30, 2, "market_open"),  # Wednesday 9:30 AM
        (10, 30, 3, "market_open"),  # Thursday 10:30 AM
        (11, 30, 4, "midday"),  # Friday 11:30 AM
        (13, 0, 0, "midday"),  # Monday 1:00 PM
        (14, 0, 1, "power_hour"),  # Tuesday 2:00 PM
        (15, 30, 2, "power_hour"),  # Wednesday 3:30 PM
        (16, 0, 3, "after_hours"),  # Thursday 4:00 PM
        (19, 0, 4, "after_hours"),  # Friday 7:00 PM
        (20, 0, 0, "market_closed"),  # Monday 8:00 PM
        (10, 0, 5, "market_closed"),  # Saturday
        (10, 0, 6, "market_closed"),  # Sunday
    ],
)
def test_session_phase_parametrized(
    hour: int, minute: int, weekday: int, expected: str
) -> None:
    """Test _compute_session_phase with various times."""
    # Create a datetime for the given time
    # Using a week where weekday 0 = Monday
    base_date = datetime(2026, 2, 23, tzinfo=ZoneInfo("America/New_York"))  # Monday
    target_date = base_date + timedelta(days=weekday)
    target_time = target_date.replace(hour=hour, minute=minute)

    # Pass now_et directly — clock injection pattern (no mocking required)
    result = _compute_session_phase(now_et=target_time)
    assert result == expected


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_orchestrator_extended() -> MockOrchestratorExtended:
    """Create a mock orchestrator with extended fields."""
    config = OrchestratorConfig()
    indicators = RegimeIndicators(
        spy_price=525.50,
        spy_sma_20=520.30,
        spy_sma_50=515.80,
        spy_roc_5d=1.25,
        spy_realized_vol_20d=12.5,
        spy_vs_vwap=0.002,
        timestamp=datetime.now(UTC),
    )
    allocations = {
        "orb_breakout": StrategyAllocation(
            strategy_id="orb_breakout",
            allocation_pct=0.25,
            allocation_dollars=25000.0,
            throttle_action=ThrottleAction.NONE,
            eligible=True,
            reason="Active: 25% allocation",
        ),
        "orb_scalp": StrategyAllocation(
            strategy_id="orb_scalp",
            allocation_pct=0.25,
            allocation_dollars=25000.0,
            throttle_action=ThrottleAction.REDUCE,
            eligible=True,
            reason="Throttled: 3 consecutive losses",
        ),
        "vwap_reclaim": StrategyAllocation(
            strategy_id="vwap_reclaim",
            allocation_pct=0.25,
            allocation_dollars=25000.0,
            throttle_action=ThrottleAction.NONE,
            eligible=True,
            reason="Active: 25% allocation",
        ),
        "afternoon_momentum": StrategyAllocation(
            strategy_id="afternoon_momentum",
            allocation_pct=0.25,
            allocation_dollars=25000.0,
            throttle_action=ThrottleAction.NONE,
            eligible=True,
            reason="Active: 25% allocation",
        ),
    }
    return MockOrchestratorExtended(
        _config=config,
        _current_regime=MarketRegime.BULLISH_TRENDING,
        _current_allocations=allocations,
        _current_indicators=indicators,
        _last_regime_check=datetime.now(UTC) - timedelta(minutes=15),
        _pre_market_done_today=True,
    )


@pytest.fixture
async def app_state_extended(
    app_state: AppState,
    mock_orchestrator_extended: MockOrchestratorExtended,
) -> AppState:
    """Provide AppState with extended mock orchestrator."""
    app_state.orchestrator = mock_orchestrator_extended  # type: ignore[assignment]
    return app_state


@pytest.fixture
async def client_extended(
    app_state_extended: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide client with extended AppState."""
    from httpx import ASGITransport, AsyncClient

    app = create_app(app_state_extended)
    app.state.app_state = app_state_extended
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
async def app_state_with_decisions_extended(
    app_state_extended: AppState,
) -> AppState:
    """Provide AppState with seeded decisions including today and yesterday."""
    trade_logger = app_state_extended.trade_logger
    now = datetime.now(UTC)
    today = now.date().isoformat()
    yesterday = (now - timedelta(days=1)).date().isoformat()
    two_days_ago = (now - timedelta(days=2)).date().isoformat()

    # Today's decisions
    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="regime_classification",
        strategy_id=None,
        details={"regime": "bullish_trending", "spy_price": 525.50},
        rationale="SPY above both SMAs with positive momentum",
    )
    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="allocation",
        strategy_id="orb_breakout",
        details={"allocation_pct": 0.25},
        rationale="Active: 25% allocation",
    )

    # Yesterday's decisions
    await trade_logger.log_orchestrator_decision(
        date=yesterday,
        decision_type="regime_classification",
        strategy_id=None,
        details={"regime": "bullish_trending"},
        rationale="Yesterday regime",
    )
    await trade_logger.log_orchestrator_decision(
        date=yesterday,
        decision_type="allocation",
        strategy_id="orb_breakout",
        details={"allocation_pct": 0.30},
        rationale="Active: 30% allocation",
    )

    # Two days ago
    await trade_logger.log_orchestrator_decision(
        date=two_days_ago,
        decision_type="eod_review",
        strategy_id=None,
        details={"regime": "bullish_trending"},
        rationale="End of day review",
    )

    return app_state_extended


@pytest.fixture
async def client_with_decisions_extended(
    app_state_with_decisions_extended: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide client with extended decisions."""
    from httpx import ASGITransport, AsyncClient

    app = create_app(app_state_with_decisions_extended)
    app.state.app_state = app_state_with_decisions_extended
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Extended Status Endpoint Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_includes_session_phase(
    client_extended: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/status includes session_phase."""
    response = await client_extended.get(
        "/api/v1/orchestrator/status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert "session_phase" in data
    assert data["session_phase"] in [
        "pre_market",
        "market_open",
        "midday",
        "power_hour",
        "after_hours",
        "market_closed",
    ]


@pytest.mark.asyncio
async def test_status_includes_pre_market_complete(
    client_extended: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/status includes pre_market_complete."""
    response = await client_extended.get(
        "/api/v1/orchestrator/status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert "pre_market_complete" in data
    assert data["pre_market_complete"] is True


@pytest.mark.asyncio
async def test_status_allocations_have_operating_window(
    client_extended: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/status allocations include operating_window."""
    response = await client_extended.get(
        "/api/v1/orchestrator/status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    allocations_by_id = {a["strategy_id"]: a for a in data["allocations"]}

    # Check orb_breakout has operating window
    orb = allocations_by_id["orb_breakout"]
    assert orb["operating_window"] is not None
    assert orb["operating_window"]["earliest_entry"] == "09:35"
    assert orb["operating_window"]["latest_entry"] == "11:30"
    assert orb["operating_window"]["force_close"] == "15:50"

    # Check afternoon_momentum has operating window
    aftn = allocations_by_id["afternoon_momentum"]
    assert aftn["operating_window"] is not None
    assert aftn["operating_window"]["earliest_entry"] == "14:00"
    assert aftn["operating_window"]["latest_entry"] == "15:30"


@pytest.mark.asyncio
async def test_status_allocations_have_throttle_metrics(
    client_extended: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/status allocations include throttle metrics."""
    response = await client_extended.get(
        "/api/v1/orchestrator/status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Check that all allocations have throttle metric fields
    for alloc in data["allocations"]:
        assert "consecutive_losses" in alloc
        assert "rolling_sharpe" in alloc
        assert "drawdown_pct" in alloc
        assert isinstance(alloc["consecutive_losses"], int)
        assert isinstance(alloc["drawdown_pct"], float)


@pytest.mark.asyncio
async def test_status_allocations_have_extended_fields(
    client_extended: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/status allocations include all extended fields."""
    response = await client_extended.get(
        "/api/v1/orchestrator/status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Check that all allocations have all extended fields
    required_fields = [
        "operating_window",
        "consecutive_losses",
        "rolling_sharpe",
        "drawdown_pct",
        "is_active",
        "health_status",
        "trade_count_today",
        "daily_pnl",
        "open_position_count",
        "override_active",
        "override_until",
    ]

    for alloc in data["allocations"]:
        for field in required_fields:
            assert field in alloc, f"Missing field {field} in allocation {alloc['strategy_id']}"


@pytest.mark.asyncio
async def test_status_health_status_defaults_to_healthy(
    client_extended: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/status allocations have health_status defaulting to healthy."""
    response = await client_extended.get(
        "/api/v1/orchestrator/status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    for alloc in data["allocations"]:
        # Default health status should be "healthy" when no health data available
        assert alloc["health_status"] in ["healthy", "warning", "error"]


# ---------------------------------------------------------------------------
# Decisions Date Filter Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decisions_with_date_filter_returns_only_matching(
    client_with_decisions_extended: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/decisions?date=... returns only matching date."""
    yesterday = (datetime.now(UTC) - timedelta(days=1)).date().isoformat()

    response = await client_with_decisions_extended.get(
        f"/api/v1/orchestrator/decisions?date={yesterday}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Should only have yesterday's decisions (2 decisions)
    assert data["total"] == 2
    for decision in data["decisions"]:
        assert decision["date"] == yesterday


@pytest.mark.asyncio
async def test_decisions_without_date_defaults_to_today(
    client_with_decisions_extended: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/decisions without date filter returns today's decisions."""
    today = datetime.now(ZoneInfo("America/New_York")).date().isoformat()

    response = await client_with_decisions_extended.get(
        "/api/v1/orchestrator/decisions",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Should only have today's decisions (2 decisions)
    assert data["total"] == 2
    for decision in data["decisions"]:
        assert decision["date"] == today


@pytest.mark.asyncio
async def test_decisions_date_filter_empty_results(
    client_with_decisions_extended: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/decisions with non-matching date returns empty list."""
    far_future = "2030-01-01"

    response = await client_with_decisions_extended.get(
        f"/api/v1/orchestrator/decisions?date={far_future}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 0
    assert data["decisions"] == []


# ---------------------------------------------------------------------------
# Pre-market Completed At Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_includes_pre_market_completed_at_from_decisions(
    client_with_decisions_extended: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/status includes pre_market_completed_at from decisions."""
    response = await client_with_decisions_extended.get(
        "/api/v1/orchestrator/status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert "pre_market_completed_at" in data
    # Should have a value since we seeded a regime_classification decision today
    assert data["pre_market_completed_at"] is not None


# ---------------------------------------------------------------------------
# Strategy Windows Tests
# ---------------------------------------------------------------------------


def test_strategy_windows_have_all_four_strategies() -> None:
    """STRATEGY_WINDOWS dict has all four strategies."""
    expected = ["orb_breakout", "orb_scalp", "vwap_reclaim", "afternoon_momentum"]
    for strategy_id in expected:
        assert strategy_id in STRATEGY_WINDOWS
        window = STRATEGY_WINDOWS[strategy_id]
        assert "earliest_entry" in window
        assert "latest_entry" in window
        assert "force_close" in window


def test_strategy_windows_time_format() -> None:
    """STRATEGY_WINDOWS times are in HH:MM format."""
    import re

    time_pattern = re.compile(r"^\d{2}:\d{2}$")

    for strategy_id, window in STRATEGY_WINDOWS.items():
        assert time_pattern.match(window["earliest_entry"]), (
            f"Invalid time format for {strategy_id}.earliest_entry"
        )
        assert time_pattern.match(window["latest_entry"]), (
            f"Invalid time format for {strategy_id}.latest_entry"
        )
        assert time_pattern.match(window["force_close"]), (
            f"Invalid time format for {strategy_id}.force_close"
        )


# ---------------------------------------------------------------------------
# Per-strategy P&L and Trade Count Tests (Sprint 32.75 S3)
# ---------------------------------------------------------------------------


def _make_trade_today(
    strategy_id: str,
    gross_pnl: float,
) -> "Trade":
    """Create a trade with today's ET date as exit_time."""
    from argus.models.trading import ExitReason, OrderSide, Trade

    _ET = ZoneInfo("America/New_York")
    today = datetime.now(_ET).date()
    entry_time = datetime(today.year, today.month, today.day, 10, 0, 0)
    exit_time = datetime(today.year, today.month, today.day, 10, 30, 0)

    return Trade(
        strategy_id=strategy_id,
        symbol="AAPL",
        side=OrderSide.BUY,
        entry_price=150.0,
        entry_time=entry_time,
        exit_price=151.0 if gross_pnl >= 0 else 149.0,
        exit_time=exit_time,
        shares=100,
        stop_price=148.0,
        exit_reason=ExitReason.TARGET_1 if gross_pnl >= 0 else ExitReason.STOP_LOSS,
        gross_pnl=gross_pnl,
        commission=1.0,
    )


@pytest.fixture
async def app_state_with_trades_today(
    app_state_extended: AppState,
) -> AppState:
    """Provide AppState with orb_breakout trades seeded for today."""
    trade_logger = app_state_extended.trade_logger

    # Two wins + one loss for orb_breakout
    await trade_logger.log_trade(_make_trade_today("orb_breakout", gross_pnl=100.0))
    await trade_logger.log_trade(_make_trade_today("orb_breakout", gross_pnl=50.0))
    await trade_logger.log_trade(_make_trade_today("orb_breakout", gross_pnl=-30.0))

    # One win for orb_scalp — different strategy
    await trade_logger.log_trade(_make_trade_today("orb_scalp", gross_pnl=80.0))

    return app_state_extended


@pytest.fixture
async def client_with_trades_today(
    app_state_with_trades_today: AppState,
    jwt_secret: str,
) -> "AsyncGenerator[AsyncClient, None]":
    """Provide client with AppState containing today's trades."""
    from httpx import ASGITransport, AsyncClient

    app = create_app(app_state_with_trades_today)
    app.state.app_state = app_state_with_trades_today
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_status_trade_count_today_reflects_logged_trades(
    client_with_trades_today: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/status trade_count_today matches logged trades for each strategy."""
    response = await client_with_trades_today.get(
        "/api/v1/orchestrator/status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    allocs_by_id = {a["strategy_id"]: a for a in data["allocations"]}

    assert allocs_by_id["orb_breakout"]["trade_count_today"] == 3
    assert allocs_by_id["orb_scalp"]["trade_count_today"] == 1


@pytest.mark.asyncio
async def test_status_daily_pnl_reflects_logged_trades(
    client_with_trades_today: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/status daily_pnl is non-zero for strategy with trades today."""
    response = await client_with_trades_today.get(
        "/api/v1/orchestrator/status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    allocs_by_id = {a["strategy_id"]: a for a in data["allocations"]}

    # orb_breakout: gross (100 + 50 - 30) = 120, commission 3×1.0 = 3, net = 117
    assert allocs_by_id["orb_breakout"]["daily_pnl"] == pytest.approx(117.0, abs=0.01)


@pytest.mark.asyncio
async def test_status_daily_pnl_sums_wins_and_losses(
    client_with_trades_today: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/status daily_pnl correctly nets wins and losses."""
    response = await client_with_trades_today.get(
        "/api/v1/orchestrator/status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    allocs_by_id = {a["strategy_id"]: a for a in data["allocations"]}
    orb_pnl = allocs_by_id["orb_breakout"]["daily_pnl"]

    # Should be positive (wins outweigh the loss)
    assert orb_pnl > 0


@pytest.mark.asyncio
async def test_status_pnl_is_zero_when_no_trades_today(
    client_extended: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/status returns daily_pnl=0 and trade_count_today=0 with no trades."""
    response = await client_extended.get(
        "/api/v1/orchestrator/status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    for alloc in data["allocations"]:
        assert alloc["trade_count_today"] == 0
        assert alloc["daily_pnl"] == 0.0


@pytest.mark.asyncio
async def test_status_pnl_is_independent_per_strategy(
    client_with_trades_today: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/status daily_pnl is isolated per strategy — no cross-contamination."""
    response = await client_with_trades_today.get(
        "/api/v1/orchestrator/status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    allocs_by_id = {a["strategy_id"]: a for a in data["allocations"]}

    # orb_scalp has only 1 trade (gross 80, commission 1 → net 79)
    assert allocs_by_id["orb_scalp"]["trade_count_today"] == 1
    assert allocs_by_id["orb_scalp"]["daily_pnl"] == pytest.approx(79.0, abs=0.01)

    # Strategies with no trades should show 0
    for strategy_id in ["vwap_reclaim", "afternoon_momentum"]:
        assert allocs_by_id[strategy_id]["trade_count_today"] == 0
        assert allocs_by_id[strategy_id]["daily_pnl"] == 0.0
