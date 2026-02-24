"""Tests for the Orchestrator class.

The Orchestrator manages strategy lifecycle, capital allocation, and market
regime classification. These tests verify all major functionality.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from argus.core.clock import FixedClock
from argus.core.config import OrchestratorConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    AllocationUpdateEvent,
    PositionClosedEvent,
    RegimeChangeEvent,
    StrategyActivatedEvent,
    StrategySuspendedEvent,
)
from argus.core.orchestrator import Orchestrator
from argus.core.regime import MarketRegime
from argus.core.throttle import ThrottleAction
from argus.models.strategy import MarketConditionsFilter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def orchestrator_config() -> OrchestratorConfig:
    """Create default orchestrator config for testing."""
    return OrchestratorConfig(
        allocation_method="equal_weight",
        max_allocation_pct=0.40,
        min_allocation_pct=0.10,
        cash_reserve_pct=0.20,
        performance_lookback_days=20,
        consecutive_loss_throttle=5,
        suspension_sharpe_threshold=0.0,
        suspension_drawdown_pct=0.15,
        regime_check_interval_minutes=30,
        spy_symbol="SPY",
        pre_market_time="09:25",
        eod_review_time="16:05",
        poll_interval_seconds=30,
    )


@pytest.fixture
def event_bus() -> EventBus:
    """Create event bus for testing."""
    return EventBus()


@pytest.fixture
def fixed_clock() -> FixedClock:
    """Create fixed clock at 9:30 AM ET on a Monday."""
    # February 24, 2026 at 9:30 AM EST (14:30 UTC)
    return FixedClock(datetime(2026, 2, 24, 14, 30, tzinfo=UTC))


@pytest.fixture
def mock_trade_logger() -> AsyncMock:
    """Create mock trade logger."""
    mock = AsyncMock()
    mock.get_trades_by_strategy = AsyncMock(return_value=[])
    mock.get_daily_pnl = AsyncMock(return_value=[])
    mock.get_trades_by_date = AsyncMock(return_value=[])
    mock._db = AsyncMock()
    mock._db.execute = AsyncMock()
    mock._db.commit = AsyncMock()
    return mock


@pytest.fixture
def mock_broker() -> AsyncMock:
    """Create mock broker."""
    mock = AsyncMock()
    account = MagicMock()
    account.equity = 100000.0
    mock.get_account = AsyncMock(return_value=account)
    return mock


@pytest.fixture
def mock_data_service() -> AsyncMock:
    """Create mock data service."""
    mock = AsyncMock()
    mock.fetch_daily_bars = AsyncMock(return_value=None)
    return mock


def create_spy_bars_bullish(days: int = 60) -> pd.DataFrame:
    """Create mock SPY daily bars for a bullish regime."""
    data = []
    base_price = 500.0

    for i in range(days):
        price = base_price + i * 0.5  # Uptrend
        data.append({
            "timestamp": datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=i),
            "open": price - 1,
            "high": price + 1,
            "low": price - 2,
            "close": price,
            "volume": 100000000,
        })

    return pd.DataFrame(data)


def create_spy_bars_crisis(days: int = 60) -> pd.DataFrame:
    """Create mock SPY daily bars for a crisis regime (high volatility)."""
    data = []
    base_price = 500.0

    for i in range(days):
        # High daily swings for high realized volatility
        swing = 20 if i % 2 == 0 else -20
        price = base_price + swing
        data.append({
            "timestamp": datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=i),
            "open": price - 10,
            "high": price + 15,
            "low": price - 15,
            "close": price,
            "volume": 200000000,
        })

    return pd.DataFrame(data)


class MockStrategy:
    """Mock strategy for testing."""

    def __init__(
        self,
        strategy_id: str,
        allowed_regimes: list[str] | None = None,
    ) -> None:
        self._strategy_id = strategy_id
        self._allowed_regimes = allowed_regimes or [
            "bullish_trending",
            "bearish_trending",
            "range_bound",
        ]
        self.is_active = False
        self.allocated_capital = 0.0

    @property
    def strategy_id(self) -> str:
        return self._strategy_id

    def get_market_conditions_filter(self) -> MarketConditionsFilter:
        return MarketConditionsFilter(allowed_regimes=self._allowed_regimes)


@pytest.fixture
def orchestrator(
    orchestrator_config: OrchestratorConfig,
    event_bus: EventBus,
    fixed_clock: FixedClock,
    mock_trade_logger: AsyncMock,
    mock_broker: AsyncMock,
    mock_data_service: AsyncMock,
) -> Orchestrator:
    """Create orchestrator for testing."""
    return Orchestrator(
        config=orchestrator_config,
        event_bus=event_bus,
        clock=fixed_clock,
        trade_logger=mock_trade_logger,
        broker=mock_broker,
        data_service=mock_data_service,
    )


# ---------------------------------------------------------------------------
# Strategy Registration Tests
# ---------------------------------------------------------------------------


def test_register_strategy(orchestrator: Orchestrator) -> None:
    """Test registering a single strategy."""
    strategy = MockStrategy("orb_breakout")
    orchestrator.register_strategy(strategy)

    assert "orb_breakout" in orchestrator.get_strategies()
    assert orchestrator.get_strategy("orb_breakout") is strategy


def test_register_multiple_strategies(orchestrator: Orchestrator) -> None:
    """Test registering multiple strategies."""
    strategy1 = MockStrategy("orb_breakout")
    strategy2 = MockStrategy("orb_scalp")
    strategy3 = MockStrategy("vwap_reclaim")

    orchestrator.register_strategy(strategy1)
    orchestrator.register_strategy(strategy2)
    orchestrator.register_strategy(strategy3)

    strategies = orchestrator.get_strategies()
    assert len(strategies) == 3
    assert "orb_breakout" in strategies
    assert "orb_scalp" in strategies
    assert "vwap_reclaim" in strategies


def test_get_strategy_not_found(orchestrator: Orchestrator) -> None:
    """Test getting a strategy that doesn't exist."""
    assert orchestrator.get_strategy("nonexistent") is None


# ---------------------------------------------------------------------------
# Pre-Market Routine Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pre_market_single_strategy_bullish(
    orchestrator: Orchestrator,
    mock_data_service: AsyncMock,
    event_bus: EventBus,
) -> None:
    """Test pre-market routine with single strategy in bullish regime."""
    # Setup
    mock_data_service.fetch_daily_bars.return_value = create_spy_bars_bullish()
    strategy = MockStrategy("orb_breakout")
    orchestrator.register_strategy(strategy)

    # Track published events
    events: list = []
    event_bus.subscribe(AllocationUpdateEvent, lambda e: events.append(e))
    event_bus.subscribe(StrategyActivatedEvent, lambda e: events.append(e))
    event_bus.subscribe(RegimeChangeEvent, lambda e: events.append(e))

    # Run pre-market
    await orchestrator.run_pre_market()
    await event_bus.drain()

    # Verify
    assert orchestrator.current_regime == MarketRegime.BULLISH_TRENDING
    assert strategy.is_active is True
    assert strategy.allocated_capital > 0

    # Check events (regime change from RANGE_BOUND to BULLISH_TRENDING)
    regime_events = [e for e in events if isinstance(e, RegimeChangeEvent)]
    assert len(regime_events) == 1
    assert regime_events[0].new_regime == "bullish_trending"


@pytest.mark.asyncio
async def test_pre_market_strategy_excluded_by_regime(
    orchestrator: Orchestrator,
    mock_data_service: AsyncMock,
) -> None:
    """Test pre-market excludes strategy when regime doesn't match allowed_regimes."""
    # Setup bullish regime
    mock_data_service.fetch_daily_bars.return_value = create_spy_bars_bullish()

    # Strategy only allows bearish
    strategy = MockStrategy("bearish_only", allowed_regimes=["bearish_trending"])
    orchestrator.register_strategy(strategy)

    # Run pre-market
    await orchestrator.run_pre_market()

    # Verify strategy is not active
    assert orchestrator.current_regime == MarketRegime.BULLISH_TRENDING
    assert strategy.is_active is False
    assert strategy.allocated_capital == 0.0

    # Check allocation
    alloc = orchestrator.current_allocations.get("bearish_only")
    assert alloc is not None
    assert alloc.eligible is False


@pytest.mark.asyncio
async def test_pre_market_strategy_throttled(
    orchestrator: Orchestrator,
    mock_data_service: AsyncMock,
    mock_trade_logger: AsyncMock,
) -> None:
    """Test pre-market throttles strategy with consecutive losses."""
    # Setup
    mock_data_service.fetch_daily_bars.return_value = create_spy_bars_bullish()

    # Create mock trades with 5 consecutive losses
    mock_trades = [MagicMock(net_pnl=-100) for _ in range(5)]
    mock_trade_logger.get_trades_by_strategy.return_value = mock_trades

    strategy = MockStrategy("orb_breakout")
    orchestrator.register_strategy(strategy)

    # Run pre-market
    await orchestrator.run_pre_market()

    # Verify strategy is throttled (REDUCE means minimum allocation)
    alloc = orchestrator.current_allocations.get("orb_breakout")
    assert alloc is not None
    assert alloc.throttle_action == ThrottleAction.REDUCE
    assert alloc.allocation_pct == orchestrator._config.min_allocation_pct
    assert strategy.is_active is True  # REDUCE doesn't suspend


@pytest.mark.asyncio
async def test_pre_market_strategy_suspended(
    orchestrator: Orchestrator,
    mock_data_service: AsyncMock,
    mock_trade_logger: AsyncMock,
) -> None:
    """Test pre-market suspends strategy with negative Sharpe."""
    # Setup
    mock_data_service.fetch_daily_bars.return_value = create_spy_bars_bullish()

    # Create daily P&L data with negative Sharpe
    # Need at least 5 days of data
    daily_pnl = [
        {"date": "2026-02-20", "pnl": -100},
        {"date": "2026-02-21", "pnl": -150},
        {"date": "2026-02-22", "pnl": -50},
        {"date": "2026-02-23", "pnl": -200},
        {"date": "2026-02-24", "pnl": -100},
        {"date": "2026-02-19", "pnl": -80},
    ]
    mock_trade_logger.get_daily_pnl.return_value = daily_pnl

    strategy = MockStrategy("orb_breakout")
    orchestrator.register_strategy(strategy)

    # Run pre-market
    await orchestrator.run_pre_market()

    # Verify strategy is suspended
    alloc = orchestrator.current_allocations.get("orb_breakout")
    assert alloc is not None
    assert alloc.throttle_action == ThrottleAction.SUSPEND
    assert alloc.allocation_pct == 0.0
    assert strategy.is_active is False


@pytest.mark.asyncio
async def test_pre_market_spy_data_unavailable(
    orchestrator: Orchestrator,
    mock_data_service: AsyncMock,
) -> None:
    """Test pre-market falls back to previous regime when SPY data unavailable."""
    # No SPY data
    mock_data_service.fetch_daily_bars.return_value = None

    strategy = MockStrategy("orb_breakout")
    orchestrator.register_strategy(strategy)

    # Run pre-market
    await orchestrator.run_pre_market()

    # Should use default regime (RANGE_BOUND)
    assert orchestrator.current_regime == MarketRegime.RANGE_BOUND


# ---------------------------------------------------------------------------
# Allocation Math Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_allocation_math_equal_weight_single(
    orchestrator: Orchestrator,
    mock_data_service: AsyncMock,
) -> None:
    """Test allocation math for single strategy."""
    mock_data_service.fetch_daily_bars.return_value = create_spy_bars_bullish()

    strategy = MockStrategy("orb_breakout")
    orchestrator.register_strategy(strategy)

    await orchestrator.run_pre_market()

    # With 100k equity and 20% reserve, deployable = 80k
    # Single strategy should get min(1.0, max_allocation_pct) = 40%
    alloc = orchestrator.current_allocations.get("orb_breakout")
    assert alloc is not None
    assert alloc.allocation_pct == 0.40  # max cap
    assert alloc.allocation_dollars == pytest.approx(100000 * 0.80 * 0.40, rel=0.01)


@pytest.mark.asyncio
async def test_allocation_math_equal_weight_two(
    orchestrator: Orchestrator,
    mock_data_service: AsyncMock,
) -> None:
    """Test allocation math for two strategies."""
    mock_data_service.fetch_daily_bars.return_value = create_spy_bars_bullish()

    orchestrator.register_strategy(MockStrategy("orb_breakout"))
    orchestrator.register_strategy(MockStrategy("orb_scalp"))

    await orchestrator.run_pre_market()

    # Two strategies: each gets min(1/2, 0.40) = 0.40
    for sid in ["orb_breakout", "orb_scalp"]:
        alloc = orchestrator.current_allocations.get(sid)
        assert alloc is not None
        assert alloc.allocation_pct == 0.40


@pytest.mark.asyncio
async def test_allocation_math_equal_weight_three(
    orchestrator: Orchestrator,
    mock_data_service: AsyncMock,
) -> None:
    """Test allocation math for three strategies."""
    mock_data_service.fetch_daily_bars.return_value = create_spy_bars_bullish()

    orchestrator.register_strategy(MockStrategy("orb_breakout"))
    orchestrator.register_strategy(MockStrategy("orb_scalp"))
    orchestrator.register_strategy(MockStrategy("vwap_reclaim"))

    await orchestrator.run_pre_market()

    # Three strategies: each gets min(1/3, 0.40) = ~0.333
    for sid in ["orb_breakout", "orb_scalp", "vwap_reclaim"]:
        alloc = orchestrator.current_allocations.get(sid)
        assert alloc is not None
        assert alloc.allocation_pct == pytest.approx(1 / 3, rel=0.01)


@pytest.mark.asyncio
async def test_allocation_respects_max_cap(
    orchestrator: Orchestrator,
    orchestrator_config: OrchestratorConfig,
    mock_data_service: AsyncMock,
) -> None:
    """Test that single strategy can't exceed max_allocation_pct."""
    mock_data_service.fetch_daily_bars.return_value = create_spy_bars_bullish()

    # Update config to have lower max
    orchestrator._config = OrchestratorConfig(
        max_allocation_pct=0.30,
        min_allocation_pct=0.10,
        cash_reserve_pct=0.20,
    )

    strategy = MockStrategy("orb_breakout")
    orchestrator.register_strategy(strategy)

    await orchestrator.run_pre_market()

    alloc = orchestrator.current_allocations.get("orb_breakout")
    assert alloc is not None
    assert alloc.allocation_pct == 0.30


@pytest.mark.asyncio
async def test_allocation_cash_reserve(
    orchestrator: Orchestrator,
    mock_data_service: AsyncMock,
    mock_broker: AsyncMock,
) -> None:
    """Test that total deployed doesn't exceed (1 - cash_reserve_pct)."""
    mock_data_service.fetch_daily_bars.return_value = create_spy_bars_bullish()

    # Set account equity
    account = MagicMock()
    account.equity = 100000.0
    mock_broker.get_account.return_value = account

    orchestrator.register_strategy(MockStrategy("orb_breakout"))
    orchestrator.register_strategy(MockStrategy("orb_scalp"))

    await orchestrator.run_pre_market()

    # Total allocated should be at most 80% of equity (80% deployable * allocations)
    total_dollars = sum(
        a.allocation_dollars for a in orchestrator.current_allocations.values()
    )
    max_deployable = 100000 * (1 - 0.20)  # 80k
    assert total_dollars <= max_deployable


# ---------------------------------------------------------------------------
# Event Publishing Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_publishing_regime_change(
    orchestrator: Orchestrator,
    mock_data_service: AsyncMock,
    event_bus: EventBus,
) -> None:
    """Test RegimeChangeEvent is published when regime changes."""
    mock_data_service.fetch_daily_bars.return_value = create_spy_bars_bullish()
    orchestrator.register_strategy(MockStrategy("orb_breakout"))

    events: list = []
    event_bus.subscribe(RegimeChangeEvent, lambda e: events.append(e))

    await orchestrator.run_pre_market()
    await event_bus.drain()

    assert len(events) == 1
    assert events[0].old_regime == "range_bound"
    assert events[0].new_regime == "bullish_trending"


@pytest.mark.asyncio
async def test_event_publishing_allocation_update(
    orchestrator: Orchestrator,
    mock_data_service: AsyncMock,
    event_bus: EventBus,
) -> None:
    """Test AllocationUpdateEvent is published for each strategy."""
    mock_data_service.fetch_daily_bars.return_value = create_spy_bars_bullish()
    orchestrator.register_strategy(MockStrategy("orb_breakout"))
    orchestrator.register_strategy(MockStrategy("orb_scalp"))

    events: list = []
    event_bus.subscribe(AllocationUpdateEvent, lambda e: events.append(e))

    await orchestrator.run_pre_market()
    await event_bus.drain()

    assert len(events) == 2
    strategy_ids = {e.strategy_id for e in events}
    assert strategy_ids == {"orb_breakout", "orb_scalp"}


@pytest.mark.asyncio
async def test_event_publishing_strategy_activated(
    orchestrator: Orchestrator,
    mock_data_service: AsyncMock,
    event_bus: EventBus,
) -> None:
    """Test StrategyActivatedEvent is published when strategy becomes active."""
    mock_data_service.fetch_daily_bars.return_value = create_spy_bars_bullish()

    strategy = MockStrategy("orb_breakout")
    strategy.is_active = False  # Start inactive
    orchestrator.register_strategy(strategy)

    events: list = []
    event_bus.subscribe(StrategyActivatedEvent, lambda e: events.append(e))

    await orchestrator.run_pre_market()
    await event_bus.drain()

    assert len(events) == 1
    assert events[0].strategy_id == "orb_breakout"


@pytest.mark.asyncio
async def test_event_publishing_strategy_suspended(
    orchestrator: Orchestrator,
    mock_data_service: AsyncMock,
    mock_trade_logger: AsyncMock,
    event_bus: EventBus,
) -> None:
    """Test StrategySuspendedEvent is published when strategy is suspended."""
    mock_data_service.fetch_daily_bars.return_value = create_spy_bars_bullish()

    # Setup for suspension (negative Sharpe with variance)
    # Need variance in P&L for Sharpe calculation to work
    daily_pnl = [
        {"date": "2026-02-15", "pnl": -100},
        {"date": "2026-02-16", "pnl": -150},
        {"date": "2026-02-17", "pnl": -50},
        {"date": "2026-02-18", "pnl": -200},
        {"date": "2026-02-19", "pnl": -80},
        {"date": "2026-02-20", "pnl": -120},
        {"date": "2026-02-21", "pnl": -90},
    ]
    mock_trade_logger.get_daily_pnl.return_value = daily_pnl

    strategy = MockStrategy("orb_breakout")
    strategy.is_active = True  # Start active
    orchestrator.register_strategy(strategy)

    events: list = []
    event_bus.subscribe(StrategySuspendedEvent, lambda e: events.append(e))

    await orchestrator.run_pre_market()
    await event_bus.drain()

    # Verify strategy got suspended
    assert strategy.is_active is False
    assert len(events) == 1
    assert events[0].strategy_id == "orb_breakout"


# ---------------------------------------------------------------------------
# Decision Logging Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decision_logging(
    orchestrator: Orchestrator,
    mock_data_service: AsyncMock,
    mock_trade_logger: AsyncMock,
) -> None:
    """Test decisions are logged to database."""
    mock_data_service.fetch_daily_bars.return_value = create_spy_bars_bullish()
    orchestrator.register_strategy(MockStrategy("orb_breakout"))

    await orchestrator.run_pre_market()

    # Verify database insert was called
    assert mock_trade_logger._db.execute.called
    assert mock_trade_logger._db.commit.called


# ---------------------------------------------------------------------------
# Intraday Throttle Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_intraday_throttle_on_consecutive_losses(
    orchestrator: Orchestrator,
    event_bus: EventBus,
) -> None:
    """Test strategy is suspended intraday after consecutive losses."""
    strategy = MockStrategy("orb_breakout")
    strategy.is_active = True
    orchestrator.register_strategy(strategy)

    events: list = []
    event_bus.subscribe(StrategySuspendedEvent, lambda e: events.append(e))

    # Simulate 5 consecutive losing position closes
    for i in range(5):
        await orchestrator._on_position_closed(
            PositionClosedEvent(
                position_id=f"pos_{i}",
                strategy_id="orb_breakout",
                realized_pnl=-100,
            )
        )
    await event_bus.drain()

    # Strategy should be suspended
    assert strategy.is_active is False
    assert len(events) == 1
    assert events[0].strategy_id == "orb_breakout"
    assert "consecutive losses" in events[0].reason


@pytest.mark.asyncio
async def test_intraday_no_throttle_with_wins(
    orchestrator: Orchestrator,
) -> None:
    """Test no throttle when losses are interrupted by wins."""
    strategy = MockStrategy("orb_breakout")
    strategy.is_active = True
    orchestrator.register_strategy(strategy)

    # Simulate losses interrupted by win
    await orchestrator._on_position_closed(
        PositionClosedEvent(
            position_id="pos_1", strategy_id="orb_breakout", realized_pnl=-100
        )
    )
    await orchestrator._on_position_closed(
        PositionClosedEvent(
            position_id="pos_2", strategy_id="orb_breakout", realized_pnl=-100
        )
    )
    await orchestrator._on_position_closed(
        PositionClosedEvent(
            position_id="pos_3", strategy_id="orb_breakout", realized_pnl=200
        )
    )  # WIN
    await orchestrator._on_position_closed(
        PositionClosedEvent(
            position_id="pos_4", strategy_id="orb_breakout", realized_pnl=-100
        )
    )
    await orchestrator._on_position_closed(
        PositionClosedEvent(
            position_id="pos_5", strategy_id="orb_breakout", realized_pnl=-100
        )
    )

    # Strategy should still be active (only 2 consecutive at end)
    assert strategy.is_active is True


# ---------------------------------------------------------------------------
# Regime Recheck Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_regime_recheck_triggers_deactivation(
    orchestrator: Orchestrator,
    mock_data_service: AsyncMock,
    event_bus: EventBus,
) -> None:
    """Test intraday regime change deactivates ineligible strategies."""
    # Start with bullish regime
    mock_data_service.fetch_daily_bars.return_value = create_spy_bars_bullish()

    # Strategy only allows bullish
    strategy = MockStrategy("bullish_only", allowed_regimes=["bullish_trending"])
    orchestrator.register_strategy(strategy)

    await orchestrator.run_pre_market()
    assert strategy.is_active is True

    events: list = []
    event_bus.subscribe(StrategySuspendedEvent, lambda e: events.append(e))

    # Now regime changes to range-bound
    # Create 60 days of flat price action across Jan-Feb 2026
    mock_data_service.fetch_daily_bars.return_value = pd.DataFrame({
        "timestamp": [
            datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=i) for i in range(60)
        ],
        "open": [500.0] * 60,
        "high": [501.0] * 60,
        "low": [499.0] * 60,
        "close": [500.0] * 60,  # Flat - range bound
        "volume": [100000000] * 60,
    })

    await orchestrator._run_regime_recheck()
    await event_bus.drain()

    # Strategy should be deactivated
    assert strategy.is_active is False
    assert len(events) == 1


# ---------------------------------------------------------------------------
# Manual Rebalance Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manual_rebalance(
    orchestrator: Orchestrator,
    mock_data_service: AsyncMock,
) -> None:
    """Test manual rebalance recalculates allocations."""
    mock_data_service.fetch_daily_bars.return_value = create_spy_bars_bullish()

    orchestrator.register_strategy(MockStrategy("orb_breakout"))
    await orchestrator.run_pre_market()

    # Add another strategy
    orchestrator.register_strategy(MockStrategy("orb_scalp"))

    # Rebalance
    allocations = await orchestrator.manual_rebalance()

    # Should have both strategies
    assert "orb_breakout" in allocations
    assert "orb_scalp" in allocations


# ---------------------------------------------------------------------------
# End of Day Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_eod_review_records_correlation(
    orchestrator: Orchestrator,
    mock_trade_logger: AsyncMock,
) -> None:
    """Test EOD review records daily P&L to correlation tracker."""
    # Setup strategy
    strategy = MockStrategy("orb_breakout")
    orchestrator.register_strategy(strategy)

    # Mock trades for today
    mock_trade = MagicMock()
    mock_trade.net_pnl = 250.0
    mock_trade_logger.get_trades_by_date.return_value = [mock_trade]

    await orchestrator.run_end_of_day()

    # Verify correlation tracker has data
    assert orchestrator._correlation_tracker.get_date_count("orb_breakout") == 1


# ---------------------------------------------------------------------------
# Start/Stop Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_start_stop(
    orchestrator: Orchestrator,
    event_bus: EventBus,
) -> None:
    """Test orchestrator start and stop lifecycle."""
    await orchestrator.start()

    # Verify subscription
    assert event_bus.subscriber_count(PositionClosedEvent) == 1

    # Verify poll task is running
    assert orchestrator._poll_task is not None
    assert not orchestrator._poll_task.done()

    await orchestrator.stop()

    # Verify unsubscription
    assert event_bus.subscriber_count(PositionClosedEvent) == 0

    # Verify poll task is cancelled
    assert orchestrator._poll_task.done()


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------


def test_current_regime_property(orchestrator: Orchestrator) -> None:
    """Test current_regime property returns regime."""
    assert orchestrator.current_regime == MarketRegime.RANGE_BOUND  # default


def test_current_allocations_property(orchestrator: Orchestrator) -> None:
    """Test current_allocations returns a copy."""
    allocs1 = orchestrator.current_allocations
    allocs2 = orchestrator.current_allocations
    assert allocs1 is not allocs2


def test_correlation_tracker_property(orchestrator: Orchestrator) -> None:
    """Test correlation_tracker property."""
    tracker = orchestrator.correlation_tracker
    assert tracker is orchestrator._correlation_tracker
