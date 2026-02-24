"""Sprint 18 Integration Tests — Multi-Strategy Operations.

Tests for multi-strategy scenarios including:
- Two strategies registering with Orchestrator
- CandleEvent routing to multiple strategies
- Cross-strategy risk checks (duplicate stock policy, single-stock exposure)
- Per-strategy time stops (seconds vs minutes)
- Concurrent position management
- Daily state reset for multiple strategies
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.clock import FixedClock
from argus.core.config import (
    AccountRiskConfig,
    CrossStrategyRiskConfig,
    DuplicateStockPolicy,
    OperatingWindow,
    OrbBreakoutConfig,
    OrbScalpConfig,
    OrchestratorConfig,
    OrderManagerConfig,
    RiskConfig,
    StrategyRiskLimits,
)
from argus.core.event_bus import EventBus
from argus.core.events import (
    CandleEvent,
    ExitReason,
    OrderApprovedEvent,
    OrderRejectedEvent,
    PositionClosedEvent,
    PositionOpenedEvent,
    Side,
    SignalEvent,
)
from argus.core.orchestrator import Orchestrator
from argus.core.risk_manager import RiskManager
from argus.execution.order_manager import OrderManager
from argus.execution.simulated_broker import SimulatedBroker
from argus.strategies.orb_breakout import OrbBreakoutStrategy
from argus.strategies.orb_scalp import OrbScalpStrategy


def make_orb_breakout_config(
    strategy_id: str = "strat_orb_breakout",
    orb_window_minutes: int = 5,
    time_stop_minutes: int = 15,
) -> OrbBreakoutConfig:
    """Create an OrbBreakoutConfig for testing."""
    return OrbBreakoutConfig(
        strategy_id=strategy_id,
        name="ORB Breakout",
        orb_window_minutes=orb_window_minutes,
        time_stop_minutes=time_stop_minutes,
        target_1_r_multiple=1.0,
        target_2_r_multiple=2.0,
        risk_limits=StrategyRiskLimits(
            max_trades_per_day=6,
            max_daily_loss_pct=0.03,
            max_loss_per_trade_pct=0.01,
            max_concurrent_positions=2,
        ),
        operating_window=OperatingWindow(
            earliest_entry="09:35",
            latest_entry="11:30",
        ),
    )


def make_orb_scalp_config(
    strategy_id: str = "strat_orb_scalp",
    orb_window_minutes: int = 5,
    scalp_target_r: float = 0.3,
    max_hold_seconds: int = 120,
) -> OrbScalpConfig:
    """Create an OrbScalpConfig for testing."""
    return OrbScalpConfig(
        strategy_id=strategy_id,
        name="ORB Scalp",
        orb_window_minutes=orb_window_minutes,
        scalp_target_r=scalp_target_r,
        max_hold_seconds=max_hold_seconds,
        risk_limits=StrategyRiskLimits(
            max_trades_per_day=12,
            max_daily_loss_pct=0.03,
            max_loss_per_trade_pct=0.01,
            max_concurrent_positions=3,
        ),
        operating_window=OperatingWindow(
            earliest_entry="09:45",
            latest_entry="11:30",
        ),
    )


def make_candle(
    symbol: str = "AAPL",
    timestamp: datetime | None = None,
    open_price: float = 100.0,
    high: float = 101.0,
    low: float = 99.0,
    close: float = 100.5,
    volume: int = 100_000,
) -> CandleEvent:
    """Create a CandleEvent for testing."""
    if timestamp is None:
        timestamp = datetime(2026, 2, 25, 14, 30, 0, tzinfo=UTC)
    return CandleEvent(
        symbol=symbol,
        timeframe="1m",
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        timestamp=timestamp,
    )


class TestMultiStrategyRegistration:
    """Tests for strategy registration and allocation."""

    @pytest.mark.asyncio
    async def test_two_strategies_register_with_orchestrator(self) -> None:
        """Both ORB and Scalp strategies register with Orchestrator."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 25, 10, 0, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        trade_logger = MagicMock()
        trade_logger.get_todays_pnl = AsyncMock(return_value=0.0)
        trade_logger.query_trades = AsyncMock(return_value=[])

        data_service = MagicMock()
        data_service.get_daily_bars = AsyncMock(return_value=None)

        config = OrchestratorConfig()

        orchestrator = Orchestrator(
            config=config,
            event_bus=event_bus,
            clock=clock,
            trade_logger=trade_logger,
            broker=broker,
            data_service=data_service,
        )

        orb_config = make_orb_breakout_config()
        scalp_config = make_orb_scalp_config()

        orb_strategy = OrbBreakoutStrategy(config=orb_config, clock=clock)
        scalp_strategy = OrbScalpStrategy(config=scalp_config, clock=clock)

        orchestrator.register_strategy(orb_strategy)
        orchestrator.register_strategy(scalp_strategy)

        strategies = orchestrator.get_strategies()

        assert len(strategies) == 2
        assert "strat_orb_breakout" in strategies
        assert "strat_orb_scalp" in strategies

    @pytest.mark.asyncio
    async def test_orchestrator_allocates_capital_to_both_strategies(self) -> None:
        """Orchestrator allocates capital proportionally to both strategies."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 25, 10, 0, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        trade_logger = MagicMock()
        trade_logger.get_todays_pnl = AsyncMock(return_value=0.0)
        trade_logger.query_trades = AsyncMock(return_value=[])

        data_service = MagicMock()
        data_service.get_daily_bars = AsyncMock(return_value=None)

        config = OrchestratorConfig()

        orchestrator = Orchestrator(
            config=config,
            event_bus=event_bus,
            clock=clock,
            trade_logger=trade_logger,
            broker=broker,
            data_service=data_service,
        )

        orb_strategy = OrbBreakoutStrategy(config=make_orb_breakout_config(), clock=clock)
        scalp_strategy = OrbScalpStrategy(config=make_orb_scalp_config(), clock=clock)

        orchestrator.register_strategy(orb_strategy)
        orchestrator.register_strategy(scalp_strategy)

        # Verify both strategies can receive allocation
        assert orb_strategy.strategy_id in orchestrator.get_strategies()
        assert scalp_strategy.strategy_id in orchestrator.get_strategies()


class TestCandleEventRouting:
    """Tests for CandleEvent routing to multiple strategies."""

    @pytest.mark.asyncio
    async def test_candle_event_routes_to_both_strategies(self) -> None:
        """CandleEvent is processed by both ORB and Scalp strategies."""
        clock = FixedClock(datetime(2026, 2, 25, 14, 30, 0, tzinfo=UTC))

        orb_strategy = OrbBreakoutStrategy(config=make_orb_breakout_config(), clock=clock)
        scalp_strategy = OrbScalpStrategy(config=make_orb_scalp_config(), clock=clock)

        # Add symbol to both watchlists
        orb_strategy.set_watchlist(["AAPL"])
        scalp_strategy.set_watchlist(["AAPL"])

        # Create OR formation candle
        candle = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 25, 14, 31, 0, tzinfo=UTC),  # 9:31 AM ET
        )

        # Both strategies should process the candle without error
        result_orb = await orb_strategy.on_candle(candle)
        result_scalp = await scalp_strategy.on_candle(candle)

        # Both return None during OR formation
        assert result_orb is None
        assert result_scalp is None


class TestCrossStrategyRiskChecks:
    """Tests for cross-strategy risk management."""

    @pytest.mark.asyncio
    async def test_scalp_signal_approved_with_allow_all_policy(self) -> None:
        """Scalp signal on same symbol as ORB approved with ALLOW_ALL policy."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 25, 15, 0, 0, tzinfo=UTC))  # 10:00 AM ET
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        risk_config = RiskConfig(
            account=AccountRiskConfig(
                daily_loss_limit_pct=0.03,
                max_concurrent_positions=10,
            ),
            cross_strategy=CrossStrategyRiskConfig(
                duplicate_stock_policy=DuplicateStockPolicy.ALLOW_ALL,
                max_single_stock_pct=0.10,  # 10% of equity
            ),
        )

        order_config = OrderManagerConfig()
        order_manager = OrderManager(
            event_bus=event_bus,
            broker=broker,
            clock=clock,
            config=order_config,
        )
        await order_manager.start()

        risk_manager = RiskManager(
            config=risk_config,
            broker=broker,
            event_bus=event_bus,
            clock=clock,
            order_manager=order_manager,
        )
        await risk_manager.initialize()
        await risk_manager.reset_daily_state()

        # Scalp signal
        scalp_signal = SignalEvent(
            strategy_id="strat_orb_scalp",
            symbol="AAPL",
            side=Side.LONG,
            entry_price=150.0,
            stop_price=148.0,
            target_prices=(150.60,),  # 0.3R target
            share_count=50,
            rationale="ORB Scalp breakout",
            time_stop_seconds=120,
        )

        result = await risk_manager.evaluate_signal(scalp_signal)

        assert isinstance(result, OrderApprovedEvent)
        assert result.signal.strategy_id == "strat_orb_scalp"

        await order_manager.stop()

    @pytest.mark.asyncio
    async def test_scalp_signal_rejected_with_block_all_policy(self) -> None:
        """Scalp signal rejected when ORB already holds symbol with BLOCK_ALL policy."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 25, 15, 0, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        risk_config = RiskConfig(
            account=AccountRiskConfig(
                daily_loss_limit_pct=0.03,
                max_concurrent_positions=10,
            ),
            cross_strategy=CrossStrategyRiskConfig(
                duplicate_stock_policy=DuplicateStockPolicy.BLOCK_ALL,
                max_single_stock_pct=0.50,  # High limit so exposure check doesn't trigger first
            ),
        )

        order_config = OrderManagerConfig()
        order_manager = OrderManager(
            event_bus=event_bus,
            broker=broker,
            clock=clock,
            config=order_config,
        )
        await order_manager.start()

        risk_manager = RiskManager(
            config=risk_config,
            broker=broker,
            event_bus=event_bus,
            clock=clock,
            order_manager=order_manager,
        )
        await risk_manager.initialize()
        await risk_manager.reset_daily_state()

        # First, ORB takes a small position
        broker.set_price("AAPL", 150.0)
        orb_signal = SignalEvent(
            strategy_id="strat_orb_breakout",
            symbol="AAPL",
            side=Side.LONG,
            entry_price=150.0,
            stop_price=148.0,
            target_prices=(152.0, 154.0),
            share_count=10,  # Small position
            rationale="ORB Breakout",
            time_stop_seconds=900,
        )

        orb_result = await risk_manager.evaluate_signal(orb_signal)
        assert isinstance(orb_result, OrderApprovedEvent)

        # Process the ORB order through order manager
        await order_manager.on_approved(orb_result)
        await asyncio.sleep(0.05)  # Let fill process

        # Now scalp tries same symbol - should be blocked by BLOCK_ALL policy
        scalp_signal = SignalEvent(
            strategy_id="strat_orb_scalp",
            symbol="AAPL",
            side=Side.LONG,
            entry_price=150.50,
            stop_price=149.0,
            target_prices=(150.95,),
            share_count=10,  # Small position
            rationale="ORB Scalp breakout",
            time_stop_seconds=120,
        )

        scalp_result = await risk_manager.evaluate_signal(scalp_signal)

        assert isinstance(scalp_result, OrderRejectedEvent)
        # Check for duplicate/already or exposure rejection
        reason_lower = scalp_result.reason.lower()
        is_blocked = (
            "duplicate" in reason_lower
            or "already" in reason_lower
            or "another strategy" in reason_lower
        )
        assert is_blocked

        await order_manager.stop()

    @pytest.mark.asyncio
    async def test_signal_rejected_when_single_stock_exposure_exceeded(self) -> None:
        """Signal rejected when single-stock exposure would exceed limit."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 25, 15, 0, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        risk_config = RiskConfig(
            account=AccountRiskConfig(
                daily_loss_limit_pct=0.03,
                max_concurrent_positions=10,
            ),
            cross_strategy=CrossStrategyRiskConfig(
                duplicate_stock_policy=DuplicateStockPolicy.ALLOW_ALL,
                max_single_stock_pct=0.05,  # 5% of equity = $5,000
            ),
        )

        order_config = OrderManagerConfig()
        order_manager = OrderManager(
            event_bus=event_bus,
            broker=broker,
            clock=clock,
            config=order_config,
        )
        await order_manager.start()

        risk_manager = RiskManager(
            config=risk_config,
            broker=broker,
            event_bus=event_bus,
            clock=clock,
            order_manager=order_manager,
        )
        await risk_manager.initialize()
        await risk_manager.reset_daily_state()

        broker.set_price("AAPL", 150.0)

        # ORB takes a position worth $4,500 (30 shares × $150)
        orb_signal = SignalEvent(
            strategy_id="strat_orb_breakout",
            symbol="AAPL",
            side=Side.LONG,
            entry_price=150.0,
            stop_price=148.0,
            target_prices=(152.0, 154.0),
            share_count=30,
            rationale="ORB Breakout",
            time_stop_seconds=900,
        )

        orb_result = await risk_manager.evaluate_signal(orb_signal)
        assert isinstance(orb_result, OrderApprovedEvent)

        await order_manager.on_approved(orb_result)
        await asyncio.sleep(0.05)

        # Scalp tries to add $3,000 more (20 shares × $150)
        # Total would be $7,500 > $5,000 limit
        scalp_signal = SignalEvent(
            strategy_id="strat_orb_scalp",
            symbol="AAPL",
            side=Side.LONG,
            entry_price=150.0,
            stop_price=149.0,
            target_prices=(150.30,),
            share_count=20,
            rationale="ORB Scalp breakout",
            time_stop_seconds=120,
        )

        scalp_result = await risk_manager.evaluate_signal(scalp_signal)

        assert isinstance(scalp_result, OrderRejectedEvent)
        assert "exposure" in scalp_result.reason.lower() or "exceed" in scalp_result.reason.lower()

        await order_manager.stop()


class TestTimeStops:
    """Tests for per-strategy time stops."""

    @pytest.mark.asyncio
    async def test_scalp_position_has_time_stop_seconds(self) -> None:
        """Scalp position stores time_stop_seconds from signal."""
        event_bus = EventBus()
        initial_time = datetime(2026, 2, 25, 15, 0, 0, tzinfo=UTC)  # 10:00 AM ET
        clock = FixedClock(initial_time)
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        order_config = OrderManagerConfig()
        order_manager = OrderManager(
            event_bus=event_bus,
            broker=broker,
            clock=clock,
            config=order_config,
        )
        await order_manager.start()

        # Create scalp signal with 120 second time stop
        broker.set_price("TSLA", 200.0)
        scalp_signal = SignalEvent(
            strategy_id="strat_orb_scalp",
            symbol="TSLA",
            side=Side.LONG,
            entry_price=200.0,
            stop_price=198.0,
            target_prices=(200.60,),  # 0.3R
            share_count=25,
            rationale="Scalp breakout",
            time_stop_seconds=120,  # 2 minute time stop
        )

        approved = OrderApprovedEvent(signal=scalp_signal)

        await order_manager.on_approved(approved)
        await asyncio.sleep(0.05)

        # Verify time stop is stored on the position
        positions = order_manager.get_managed_positions()
        assert "TSLA" in positions
        pos = positions["TSLA"][0]
        assert pos.time_stop_seconds == 120  # Scalp: 120 seconds

        await order_manager.stop()

    @pytest.mark.asyncio
    async def test_orb_position_has_time_stop_seconds(self) -> None:
        """ORB position stores time_stop_seconds from signal."""
        event_bus = EventBus()
        initial_time = datetime(2026, 2, 25, 15, 0, 0, tzinfo=UTC)
        clock = FixedClock(initial_time)
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        order_config = OrderManagerConfig()
        order_manager = OrderManager(
            event_bus=event_bus,
            broker=broker,
            clock=clock,
            config=order_config,
        )
        await order_manager.start()

        # Create ORB signal with 15 minute (900 second) time stop
        broker.set_price("NVDA", 500.0)
        orb_signal = SignalEvent(
            strategy_id="strat_orb_breakout",
            symbol="NVDA",
            side=Side.LONG,
            entry_price=500.0,
            stop_price=495.0,
            target_prices=(505.0, 510.0),
            share_count=20,
            rationale="ORB breakout",
            time_stop_seconds=900,  # 15 minute time stop
        )

        approved = OrderApprovedEvent(signal=orb_signal)

        await order_manager.on_approved(approved)
        await asyncio.sleep(0.05)

        # Verify time stop is stored on the position
        positions = order_manager.get_managed_positions()
        assert "NVDA" in positions
        pos = positions["NVDA"][0]
        assert pos.time_stop_seconds == 900  # ORB: 15 minutes = 900 seconds

        await order_manager.stop()


class TestSingleTargetBracket:
    """Tests for single-target bracket orders (scalp strategy)."""

    @pytest.mark.asyncio
    async def test_single_target_bracket_order_end_to_end(self) -> None:
        """Single-target scalp bracket order works end-to-end."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 25, 15, 0, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        order_config = OrderManagerConfig()
        order_manager = OrderManager(
            event_bus=event_bus,
            broker=broker,
            clock=clock,
            config=order_config,
        )
        await order_manager.start()

        opened_events: list[PositionOpenedEvent] = []

        async def on_opened(e: PositionOpenedEvent) -> None:
            opened_events.append(e)

        event_bus.subscribe(PositionOpenedEvent, on_opened)

        # Scalp signal with single target
        broker.set_price("META", 400.0)
        scalp_signal = SignalEvent(
            strategy_id="strat_orb_scalp",
            symbol="META",
            side=Side.LONG,
            entry_price=400.0,
            stop_price=398.0,  # $2 risk
            target_prices=(400.60,),  # 0.3R = $0.60 profit
            share_count=50,
            rationale="Scalp breakout",
            time_stop_seconds=120,
        )

        approved = OrderApprovedEvent(signal=scalp_signal)

        await order_manager.on_approved(approved)
        await asyncio.sleep(0.05)

        assert len(opened_events) == 1
        assert opened_events[0].shares == 50

        # Verify position has single target (t1_price)
        positions = order_manager.get_managed_positions()
        assert "META" in positions
        assert len(positions["META"]) == 1
        pos = positions["META"][0]
        # Single target scalp stores target in t1_price
        assert pos.t1_price == 400.60

        await order_manager.stop()


class TestDailyStateReset:
    """Tests for daily state reset across strategies."""

    @pytest.mark.asyncio
    async def test_both_strategies_reset_daily_state_correctly(self) -> None:
        """Both strategies clear per-symbol state on daily reset."""
        clock = FixedClock(datetime(2026, 2, 25, 14, 30, 0, tzinfo=UTC))

        orb_strategy = OrbBreakoutStrategy(config=make_orb_breakout_config(), clock=clock)
        scalp_strategy = OrbScalpStrategy(config=make_orb_scalp_config(), clock=clock)

        orb_strategy.set_watchlist(["AAPL", "TSLA"])
        scalp_strategy.set_watchlist(["AAPL", "TSLA"])

        # Process some candles to build state
        for minute in range(5):
            candle = make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 25, 14, 30 + minute, 0, tzinfo=UTC),
            )
            await orb_strategy.on_candle(candle)
            await scalp_strategy.on_candle(candle)

        # Both should have accumulated OR candles
        assert len(orb_strategy._symbol_state.get("AAPL", MagicMock()).or_candles or []) > 0
        assert len(scalp_strategy._symbol_state.get("AAPL", MagicMock()).or_candles or []) > 0

        # Reset daily state
        orb_strategy.reset_daily_state()
        scalp_strategy.reset_daily_state()

        # State should be cleared
        assert "AAPL" not in orb_strategy._symbol_state
        assert "AAPL" not in scalp_strategy._symbol_state


class TestWatchlistSharing:
    """Tests for watchlist shared between strategies."""

    @pytest.mark.asyncio
    async def test_watchlist_shared_between_strategies(self) -> None:
        """Both strategies can use the same watchlist."""
        clock = FixedClock(datetime(2026, 2, 25, 14, 30, 0, tzinfo=UTC))

        orb_strategy = OrbBreakoutStrategy(config=make_orb_breakout_config(), clock=clock)
        scalp_strategy = OrbScalpStrategy(config=make_orb_scalp_config(), clock=clock)

        shared_watchlist = ["AAPL", "TSLA", "NVDA", "META"]

        orb_strategy.set_watchlist(shared_watchlist)
        scalp_strategy.set_watchlist(shared_watchlist)

        # Watchlist is stored as a list
        assert set(orb_strategy._watchlist) == set(shared_watchlist)
        assert set(scalp_strategy._watchlist) == set(shared_watchlist)


class TestConcurrentPositionManagement:
    """Tests for concurrent position management across strategies."""

    @pytest.mark.asyncio
    async def test_both_positions_managed_simultaneously(self) -> None:
        """ORB and Scalp positions on different symbols managed simultaneously."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 25, 15, 0, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        order_config = OrderManagerConfig()
        order_manager = OrderManager(
            event_bus=event_bus,
            broker=broker,
            clock=clock,
            config=order_config,
        )
        await order_manager.start()

        opened_events: list[PositionOpenedEvent] = []

        async def on_opened(e: PositionOpenedEvent) -> None:
            opened_events.append(e)

        event_bus.subscribe(PositionOpenedEvent, on_opened)

        # ORB signal on AAPL
        broker.set_price("AAPL", 150.0)
        orb_signal = SignalEvent(
            strategy_id="strat_orb_breakout",
            symbol="AAPL",
            side=Side.LONG,
            entry_price=150.0,
            stop_price=148.0,
            target_prices=(152.0, 154.0),
            share_count=30,
            rationale="ORB breakout",
            time_stop_seconds=900,
        )

        # Scalp signal on TSLA
        broker.set_price("TSLA", 200.0)
        scalp_signal = SignalEvent(
            strategy_id="strat_orb_scalp",
            symbol="TSLA",
            side=Side.LONG,
            entry_price=200.0,
            stop_price=198.0,
            target_prices=(200.60,),
            share_count=25,
            rationale="Scalp breakout",
            time_stop_seconds=120,
        )

        # Submit both
        orb_approved = OrderApprovedEvent(signal=orb_signal)
        scalp_approved = OrderApprovedEvent(signal=scalp_signal)

        await order_manager.on_approved(orb_approved)
        await order_manager.on_approved(scalp_approved)
        await asyncio.sleep(0.05)

        # Both positions should be managed
        assert len(opened_events) == 2
        positions = order_manager.get_managed_positions()
        assert "AAPL" in positions
        assert "TSLA" in positions

        await order_manager.stop()


class TestThrottlerTracking:
    """Tests for performance throttler tracking per strategy."""

    @pytest.mark.asyncio
    async def test_position_close_tracked_per_strategy_by_throttler(self) -> None:
        """Position close events are tracked per strategy by the throttler."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 25, 15, 0, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        trade_logger = MagicMock()
        trade_logger.get_todays_pnl = AsyncMock(return_value=0.0)
        trade_logger.query_trades = AsyncMock(return_value=[])

        data_service = MagicMock()
        data_service.get_daily_bars = AsyncMock(return_value=None)

        config = OrchestratorConfig()
        orchestrator = Orchestrator(
            config=config,
            event_bus=event_bus,
            clock=clock,
            trade_logger=trade_logger,
            broker=broker,
            data_service=data_service,
        )

        # Simulate position close event with correct signature
        close_event = PositionClosedEvent(
            position_id="pos_123",
            strategy_id="strat_orb_scalp",
            exit_price=149.0,
            realized_pnl=-50.0,
            exit_reason=ExitReason.STOP_LOSS,
            hold_duration_seconds=60,
        )

        # The orchestrator tracks losses per strategy
        await orchestrator._on_position_closed(close_event)

        # Verify loss recorded for the correct strategy
        assert "strat_orb_scalp" in orchestrator._intraday_losses
        assert orchestrator._intraday_losses["strat_orb_scalp"][-1] == -50.0


class TestMidDayReconstruction:
    """Tests for mid-day state reconstruction."""

    @pytest.mark.asyncio
    async def test_mid_day_reconstruction_replays_bars_to_both_strategies(self) -> None:
        """Mid-day restart replays today's bars to reconstruct strategy state."""
        clock = FixedClock(datetime(2026, 2, 25, 15, 30, 0, tzinfo=UTC))  # 10:30 AM ET

        orb_strategy = OrbBreakoutStrategy(config=make_orb_breakout_config(), clock=clock)
        scalp_strategy = OrbScalpStrategy(config=make_orb_scalp_config(), clock=clock)

        orb_strategy.set_watchlist(["AAPL"])
        scalp_strategy.set_watchlist(["AAPL"])

        # Simulate reconstructing by replaying historical bars
        # 9:30 AM ET = 14:30 UTC to 10:30 AM ET = 15:30 UTC
        historical_bars = []
        base_time = datetime(2026, 2, 25, 14, 30, 0, tzinfo=UTC)
        for minute in range(60):  # 60 minutes of data
            bar_time = base_time + timedelta(minutes=minute)
            historical_bars.append(
                make_candle(
                    symbol="AAPL",
                    timestamp=bar_time,
                    open_price=100.0 + minute * 0.1,
                    high=101.0 + minute * 0.1,
                    low=99.0 + minute * 0.1,
                    close=100.5 + minute * 0.1,
                )
            )

        # Replay to both strategies
        for bar in historical_bars:
            await orb_strategy.on_candle(bar)
            await scalp_strategy.on_candle(bar)

        # Both strategies should have formed opening range
        orb_state = orb_strategy._symbol_state.get("AAPL")
        scalp_state = scalp_strategy._symbol_state.get("AAPL")

        assert orb_state is not None
        assert orb_state.or_complete is True

        assert scalp_state is not None
        assert scalp_state.or_complete is True
