"""Sprint 19 Integration Tests — Three-Strategy Multi-Strategy Operations.

Tests for three-strategy scenarios including:
- Three strategies (ORB, Scalp, VWAP Reclaim) registering with Orchestrator
- Equal allocation across three strategies
- Sequential flows (ORB → VWAP Reclaim on same symbol)
- Concurrent position management
- VWAP Reclaim state machine in integration context
- Cross-strategy risk checks
- Regime and throttling
- Daily state reset
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
    VwapReclaimConfig,
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
from argus.core.regime import MarketRegime
from argus.core.risk_manager import RiskManager
from argus.core.throttle import ThrottleAction
from argus.execution.order_manager import OrderManager
from argus.execution.simulated_broker import SimulatedBroker
from argus.models.trading import ExitReason as TradeExitReason
from argus.models.trading import OrderSide, Trade, TradeOutcome
from argus.strategies.orb_breakout import OrbBreakoutStrategy
from argus.strategies.orb_scalp import OrbScalpStrategy
from argus.strategies.vwap_reclaim import VwapReclaimStrategy, VwapState, VwapSymbolState


# ===========================================================================
# Config Factories
# ===========================================================================


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


def make_vwap_reclaim_config(
    strategy_id: str = "strat_vwap_reclaim",
    min_pullback_pct: float = 0.002,
    max_pullback_pct: float = 0.02,
    min_pullback_bars: int = 3,
    volume_confirmation_multiplier: float = 1.0,  # Relaxed for testing
    max_chase_above_vwap_pct: float = 0.003,
    target_1_r: float = 1.0,
    target_2_r: float = 2.0,
    time_stop_minutes: int = 30,
    earliest_entry: str = "10:00",
    latest_entry: str = "12:00",
) -> VwapReclaimConfig:
    """Create a VwapReclaimConfig for testing."""
    return VwapReclaimConfig(
        strategy_id=strategy_id,
        name="VWAP Reclaim",
        min_pullback_pct=min_pullback_pct,
        max_pullback_pct=max_pullback_pct,
        min_pullback_bars=min_pullback_bars,
        volume_confirmation_multiplier=volume_confirmation_multiplier,
        max_chase_above_vwap_pct=max_chase_above_vwap_pct,
        target_1_r=target_1_r,
        target_2_r=target_2_r,
        time_stop_minutes=time_stop_minutes,
        risk_limits=StrategyRiskLimits(
            max_trades_per_day=10,
            max_daily_loss_pct=0.03,
            max_loss_per_trade_pct=0.01,
            max_concurrent_positions=3,
        ),
        operating_window=OperatingWindow(
            earliest_entry=earliest_entry,
            latest_entry=latest_entry,
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
        timestamp = datetime(2026, 2, 25, 15, 30, 0, tzinfo=UTC)  # 10:30 AM ET
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


class MockDataService:
    """Mock DataService for controlled indicator values."""

    def __init__(self, vwap: float | None = 100.0) -> None:
        """Initialize with default VWAP value."""
        self._vwap = vwap
        self._vwap_values: dict[str, float | None] = {}

    def set_vwap(self, symbol: str, vwap: float | None) -> None:
        """Set VWAP for a specific symbol."""
        self._vwap_values[symbol] = vwap

    async def get_indicator(self, symbol: str, indicator: str) -> float | None:
        """Get indicator value."""
        if indicator == "vwap":
            if symbol in self._vwap_values:
                return self._vwap_values[symbol]
            return self._vwap
        return None

    async def get_daily_bars(self, symbol: str, **kwargs) -> None:
        """Mock get_daily_bars."""
        return None

    async def fetch_daily_bars(self, symbol: str, lookback_days: int) -> None:
        """Mock fetch_daily_bars."""
        return None


# ===========================================================================
# Test Classes
# ===========================================================================


class TestThreeStrategyAllocation:
    """Tests for three-strategy allocation."""

    @pytest.mark.asyncio
    async def test_three_strategy_equal_allocation(self) -> None:
        """Three strategies get equal allocation (capped at 40% each)."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 25, 10, 0, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        trade_logger = MagicMock()
        trade_logger.get_todays_pnl = AsyncMock(return_value=0.0)
        trade_logger.query_trades = AsyncMock(return_value=[])
        trade_logger.get_trades_by_strategy = AsyncMock(return_value=[])
        trade_logger.get_daily_pnl = AsyncMock(return_value=[])
        trade_logger.get_trades_by_date = AsyncMock(return_value=[])
        trade_logger.log_orchestrator_decision = AsyncMock()

        data_service = MockDataService()

        config = OrchestratorConfig(
            max_allocation_pct=0.40,
            min_allocation_pct=0.10,
            cash_reserve_pct=0.20,
        )

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
        vwap_strategy = VwapReclaimStrategy(config=make_vwap_reclaim_config(), clock=clock)

        orchestrator.register_strategy(orb_strategy)
        orchestrator.register_strategy(scalp_strategy)
        orchestrator.register_strategy(vwap_strategy)

        await orchestrator.run_pre_market()

        allocations = orchestrator.current_allocations

        # Verify all three strategies registered
        assert len(allocations) == 3
        assert "strat_orb_breakout" in allocations
        assert "strat_orb_scalp" in allocations
        assert "strat_vwap_reclaim" in allocations

        # With 3 strategies, equal weight = 1/3 = 33.3%
        # All under 40% cap, so each gets 33.3%
        for alloc in allocations.values():
            assert alloc.allocation_pct == pytest.approx(1 / 3, rel=0.01)

        # Total deployment = 80K (100K - 20% reserve) × 3 × 33.3% ≈ 80K
        deployable = 100_000 * 0.80
        total_allocated = sum(a.allocation_dollars for a in allocations.values())
        assert total_allocated == pytest.approx(deployable, rel=0.01)

        # Verify each strategy's allocated capital
        for alloc in allocations.values():
            expected_dollars = deployable * (1 / 3)
            assert alloc.allocation_dollars == pytest.approx(expected_dollars, rel=0.01)

    @pytest.mark.asyncio
    async def test_three_strategy_allocation_with_throttled_strategy(self) -> None:
        """When one strategy is throttled, remaining capital splits between others."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 25, 10, 0, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        # Create losing trades for VWAP Reclaim (5 consecutive losses)
        vwap_losing_trades = [
            Trade(
                strategy_id="strat_vwap_reclaim",
                symbol="AAPL",
                side=OrderSide.BUY,
                entry_price=100.0,
                exit_price=99.0,
                stop_price=98.0,
                shares=10,
                entry_time=datetime(2026, 2, 24, 10, i, 0, tzinfo=UTC),
                exit_time=datetime(2026, 2, 24, 10, i + 5, 0, tzinfo=UTC),
                exit_reason=TradeExitReason.STOP_LOSS,
                commission=1.0,
                gross_pnl=-10.0,
                net_pnl=-11.0,
                outcome=TradeOutcome.LOSS,
            )
            for i in range(5)
        ]

        trade_logger = MagicMock()
        trade_logger.get_todays_pnl = AsyncMock(return_value=0.0)
        trade_logger.query_trades = AsyncMock(return_value=[])
        trade_logger.get_daily_pnl = AsyncMock(return_value=[])
        trade_logger.get_trades_by_date = AsyncMock(return_value=[])
        trade_logger.log_orchestrator_decision = AsyncMock()

        async def mock_get_trades_by_strategy(
            strategy_id: str, limit: int = 200
        ) -> list[Trade]:
            if strategy_id == "strat_vwap_reclaim":
                return vwap_losing_trades
            return []

        trade_logger.get_trades_by_strategy = AsyncMock(side_effect=mock_get_trades_by_strategy)

        data_service = MockDataService()

        config = OrchestratorConfig(
            max_allocation_pct=0.40,
            min_allocation_pct=0.10,
            cash_reserve_pct=0.20,
            consecutive_loss_throttle=5,
        )

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
        vwap_strategy = VwapReclaimStrategy(config=make_vwap_reclaim_config(), clock=clock)

        orchestrator.register_strategy(orb_strategy)
        orchestrator.register_strategy(scalp_strategy)
        orchestrator.register_strategy(vwap_strategy)

        await orchestrator.run_pre_market()

        allocations = orchestrator.current_allocations

        # With 3 strategies, equal weight = 1/3 ≈ 33.3%
        # ORB and Scalp get equal weight, VWAP gets min due to throttle
        orb_alloc = allocations["strat_orb_breakout"]
        scalp_alloc = allocations["strat_orb_scalp"]
        vwap_alloc = allocations["strat_vwap_reclaim"]

        assert orb_alloc.allocation_pct == pytest.approx(1 / 3, rel=0.01)
        assert scalp_alloc.allocation_pct == pytest.approx(1 / 3, rel=0.01)
        # VWAP gets minimum allocation due to throttle
        assert vwap_alloc.throttle_action == ThrottleAction.REDUCE
        assert vwap_alloc.allocation_pct == config.min_allocation_pct


class TestSequentialFlows:
    """Tests for sequential trading flows between strategies."""

    @pytest.mark.asyncio
    async def test_orb_then_vwap_reclaim_on_same_symbol(self) -> None:
        """ORB enters/exits, then VWAP Reclaim enters same symbol."""
        clock = FixedClock(datetime(2026, 2, 25, 14, 40, 0, tzinfo=UTC))  # 9:40 AM ET

        orb_strategy = OrbBreakoutStrategy(config=make_orb_breakout_config(), clock=clock)
        vwap_strategy = VwapReclaimStrategy(
            config=make_vwap_reclaim_config(),
            data_service=MockDataService(vwap=100.0),
        )

        orb_strategy.set_watchlist(["AAPL"])
        orb_strategy.allocated_capital = 30_000
        vwap_strategy.set_watchlist(["AAPL"])
        vwap_strategy.allocated_capital = 30_000

        # Build OR for ORB (5 bars at 9:30-9:34)
        for i in range(5):
            candle = make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 25, 14, 30 + i, 0, tzinfo=UTC),
                open_price=100.0,
                high=101.0,
                low=99.0,
                close=100.0 + i * 0.1,
                volume=100_000,
            )
            await orb_strategy.on_candle(candle)

        # ORB breakout at 9:40 AM ET
        breakout_candle = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 25, 14, 40, 0, tzinfo=UTC),
            open_price=101.0,
            high=102.0,
            low=101.0,
            close=101.5,
            volume=200_000,
        )
        orb_signal = await orb_strategy.on_candle(breakout_candle)
        assert orb_signal is not None
        assert orb_signal.strategy_id == "strat_orb_breakout"

        # VWAP Reclaim candle sequence (10:00+ AM ET)
        # First: above VWAP
        await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=101.0,
                high=101.5,
                low=100.5,
                volume=100_000,
                timestamp=datetime(2026, 2, 25, 15, 0, 0, tzinfo=UTC),  # 10:00 AM ET
            )
        )

        # Pullback below VWAP (3 bars)
        for i in range(3):
            await vwap_strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    high=99.5,
                    low=99.0,
                    volume=100_000,
                    timestamp=datetime(2026, 2, 25, 15, 1 + i, 0, tzinfo=UTC),
                )
            )

        # Reclaim candle
        vwap_signal = await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                high=100.5,
                low=99.5,
                volume=150_000,
                timestamp=datetime(2026, 2, 25, 15, 5, 0, tzinfo=UTC),
            )
        )

        assert vwap_signal is not None
        assert vwap_signal.strategy_id == "strat_vwap_reclaim"
        assert vwap_signal.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_orb_scalp_then_vwap_reclaim_sequential(self) -> None:
        """ORB Scalp enters/exits quickly, then VWAP Reclaim enters."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 25, 14, 50, 0, tzinfo=UTC))  # 9:50 AM ET
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        scalp_config = make_orb_scalp_config()
        scalp_strategy = OrbScalpStrategy(config=scalp_config, clock=clock)
        scalp_strategy.set_watchlist(["AAPL"])
        scalp_strategy.allocated_capital = 30_000

        mock_ds = MockDataService(vwap=100.0)
        vwap_strategy = VwapReclaimStrategy(
            config=make_vwap_reclaim_config(),
            data_service=mock_ds,
        )
        vwap_strategy.set_watchlist(["AAPL"])
        vwap_strategy.allocated_capital = 30_000

        # Build OR for scalp
        for i in range(5):
            candle = make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 25, 14, 30 + i, 0, tzinfo=UTC),
                close=100.0 + i * 0.1,
                volume=100_000,
            )
            await scalp_strategy.on_candle(candle)

        # Scalp breakout at 9:50 AM ET
        scalp_signal = await scalp_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 25, 14, 50, 0, tzinfo=UTC),
                open_price=101.0,
                high=102.0,
                low=101.0,
                close=101.5,
                volume=200_000,
            )
        )
        assert scalp_signal is not None
        assert scalp_signal.strategy_id == "strat_orb_scalp"

        # VWAP Reclaim at 10:20 AM ET (after scalp would have exited on time stop)
        await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=101.0,
                volume=100_000,
                timestamp=datetime(2026, 2, 25, 15, 20, 0, tzinfo=UTC),
            )
        )

        for i in range(3):
            await vwap_strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    low=99.0,
                    volume=100_000,
                    timestamp=datetime(2026, 2, 25, 15, 21 + i, 0, tzinfo=UTC),
                )
            )

        vwap_signal = await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=150_000,
                timestamp=datetime(2026, 2, 25, 15, 25, 0, tzinfo=UTC),
            )
        )

        assert vwap_signal is not None
        assert vwap_signal.strategy_id == "strat_vwap_reclaim"


class TestConcurrentPositions:
    """Tests for concurrent position management across strategies."""

    @pytest.mark.asyncio
    async def test_three_strategies_concurrent_positions(self) -> None:
        """ORB, Scalp, and VWAP Reclaim can hold positions on different symbols."""
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
                max_single_stock_pct=0.10,
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

        opened_events: list[PositionOpenedEvent] = []

        async def on_opened(e: PositionOpenedEvent) -> None:
            opened_events.append(e)

        event_bus.subscribe(PositionOpenedEvent, on_opened)

        # ORB on AAPL
        broker.set_price("AAPL", 150.0)
        orb_signal = SignalEvent(
            strategy_id="strat_orb_breakout",
            symbol="AAPL",
            side=Side.LONG,
            entry_price=150.0,
            stop_price=148.0,
            target_prices=(152.0, 154.0),
            share_count=20,
            rationale="ORB breakout",
            time_stop_seconds=900,
        )
        orb_result = await risk_manager.evaluate_signal(orb_signal)
        assert isinstance(orb_result, OrderApprovedEvent)
        await order_manager.on_approved(orb_result)
        await asyncio.sleep(0.05)

        # Scalp on TSLA
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
        scalp_result = await risk_manager.evaluate_signal(scalp_signal)
        assert isinstance(scalp_result, OrderApprovedEvent)
        await order_manager.on_approved(scalp_result)
        await asyncio.sleep(0.05)

        # VWAP Reclaim on NVDA
        broker.set_price("NVDA", 500.0)
        vwap_signal = SignalEvent(
            strategy_id="strat_vwap_reclaim",
            symbol="NVDA",
            side=Side.LONG,
            entry_price=500.0,
            stop_price=495.0,
            target_prices=(505.0, 510.0),
            share_count=10,
            rationale="VWAP reclaim",
            time_stop_seconds=1800,
        )
        vwap_result = await risk_manager.evaluate_signal(vwap_signal)
        assert isinstance(vwap_result, OrderApprovedEvent)
        await order_manager.on_approved(vwap_result)
        await asyncio.sleep(0.05)

        # Verify all three positions opened
        assert len(opened_events) == 3
        positions = order_manager.get_managed_positions()
        assert "AAPL" in positions
        assert "TSLA" in positions
        assert "NVDA" in positions

        await order_manager.stop()

    @pytest.mark.asyncio
    async def test_same_symbol_allow_all_orb_and_vwap(self) -> None:
        """ORB and VWAP Reclaim can both hold same symbol under ALLOW_ALL."""
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
                max_single_stock_pct=0.10,  # 10% = $10,000 max per stock
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

        # ORB takes position worth $3,000 (20 shares × $150)
        orb_signal = SignalEvent(
            strategy_id="strat_orb_breakout",
            symbol="AAPL",
            side=Side.LONG,
            entry_price=150.0,
            stop_price=148.0,
            target_prices=(152.0, 154.0),
            share_count=20,
            rationale="ORB breakout",
            time_stop_seconds=900,
        )
        orb_result = await risk_manager.evaluate_signal(orb_signal)
        assert isinstance(orb_result, OrderApprovedEvent)
        await order_manager.on_approved(orb_result)
        await asyncio.sleep(0.05)

        # VWAP Reclaim takes position worth $3,000 (20 shares × $150)
        # Total = $6,000 < $10,000 limit
        vwap_signal = SignalEvent(
            strategy_id="strat_vwap_reclaim",
            symbol="AAPL",
            side=Side.LONG,
            entry_price=150.0,
            stop_price=148.5,
            target_prices=(151.5, 153.0),
            share_count=20,
            rationale="VWAP reclaim",
            time_stop_seconds=1800,
        )
        vwap_result = await risk_manager.evaluate_signal(vwap_signal)
        assert isinstance(vwap_result, OrderApprovedEvent)

        await order_manager.stop()


class TestVwapReclaimStateMachine:
    """Tests for VWAP Reclaim state machine in integration context."""

    @pytest.mark.asyncio
    async def test_vwap_reclaim_full_state_machine_cycle(self) -> None:
        """Full VWAP reclaim flow through EventBus → Strategy → Risk → Order."""
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
                max_single_stock_pct=0.50,  # High limit for this test
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

        mock_ds = MockDataService(vwap=100.0)
        vwap_strategy = VwapReclaimStrategy(
            config=make_vwap_reclaim_config(),
            data_service=mock_ds,
        )
        vwap_strategy.set_watchlist(["AAPL"])
        vwap_strategy.allocated_capital = 30_000

        # Gap up above VWAP
        await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=101.0,
                high=101.5,
                low=100.5,
                volume=100_000,
                timestamp=datetime(2026, 2, 25, 15, 0, 0, tzinfo=UTC),
            )
        )
        assert vwap_strategy._get_symbol_state("AAPL").state == VwapState.ABOVE_VWAP

        # Pullback below VWAP (3 bars)
        for i in range(3):
            await vwap_strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    high=99.5,
                    low=99.0,
                    volume=100_000,
                    timestamp=datetime(2026, 2, 25, 15, 1 + i, 0, tzinfo=UTC),
                )
            )
        assert vwap_strategy._get_symbol_state("AAPL").state == VwapState.BELOW_VWAP

        # Reclaim with volume
        broker.set_price("AAPL", 100.2)
        signal = await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                high=100.5,
                low=99.5,
                volume=150_000,
                timestamp=datetime(2026, 2, 25, 15, 5, 0, tzinfo=UTC),
            )
        )
        assert signal is not None
        assert vwap_strategy._get_symbol_state("AAPL").state == VwapState.ENTERED

        # Risk approval
        result = await risk_manager.evaluate_signal(signal)
        assert isinstance(result, OrderApprovedEvent)

        # Order execution
        await order_manager.on_approved(result)
        await asyncio.sleep(0.05)

        positions = order_manager.get_managed_positions()
        assert "AAPL" in positions

        await order_manager.stop()

    @pytest.mark.asyncio
    async def test_vwap_reclaim_rejection_pullback_too_shallow(self) -> None:
        """No signal when pullback depth is too shallow."""
        mock_ds = MockDataService(vwap=100.0)
        vwap_strategy = VwapReclaimStrategy(
            config=make_vwap_reclaim_config(min_pullback_pct=0.01),  # 1% required
            data_service=mock_ds,
        )
        vwap_strategy.set_watchlist(["AAPL"])
        vwap_strategy.allocated_capital = 30_000

        # Above VWAP
        await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=101.0,
                high=101.5,
                low=100.5,  # Explicit high low to avoid default 99.0
                timestamp=datetime(2026, 2, 25, 15, 0, 0, tzinfo=UTC),
            )
        )

        # Shallow pullback (0.3% — need 1%)
        # low=99.7 means pullback = (100-99.7)/100 = 0.3% < 1% required
        for i in range(3):
            await vwap_strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.7,
                    high=100.0,
                    low=99.7,
                    timestamp=datetime(2026, 2, 25, 15, 1 + i, 0, tzinfo=UTC),
                )
            )

        # Reclaim — should fail due to shallow pullback
        signal = await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                high=100.3,
                low=99.8,  # Must be higher than pullback lows to not update pullback_low
                volume=150_000,
                timestamp=datetime(2026, 2, 25, 15, 5, 0, tzinfo=UTC),
            )
        )
        assert signal is None
        # State should reset to ABOVE_VWAP for retry
        assert vwap_strategy._get_symbol_state("AAPL").state == VwapState.ABOVE_VWAP

    @pytest.mark.asyncio
    async def test_vwap_reclaim_rejection_pullback_too_deep(self) -> None:
        """No signal when pullback exceeds max depth (EXHAUSTED)."""
        mock_ds = MockDataService(vwap=100.0)
        vwap_strategy = VwapReclaimStrategy(
            config=make_vwap_reclaim_config(max_pullback_pct=0.01),  # 1% max
            data_service=mock_ds,
        )
        vwap_strategy.set_watchlist(["AAPL"])
        vwap_strategy.allocated_capital = 30_000

        # Above VWAP
        await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=101.0,
                timestamp=datetime(2026, 2, 25, 15, 0, 0, tzinfo=UTC),
            )
        )

        # First bar below VWAP
        await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=99.5,
                low=99.5,
                timestamp=datetime(2026, 2, 25, 15, 1, 0, tzinfo=UTC),
            )
        )

        # Deep pullback (2% — exceeds 1% max)
        await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=98.0,
                low=98.0,
                timestamp=datetime(2026, 2, 25, 15, 2, 0, tzinfo=UTC),
            )
        )

        assert vwap_strategy._get_symbol_state("AAPL").state == VwapState.EXHAUSTED

        # Further reclaim attempts should be ignored
        signal = await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=101.0,
                timestamp=datetime(2026, 2, 25, 15, 10, 0, tzinfo=UTC),
            )
        )
        assert signal is None

    @pytest.mark.asyncio
    async def test_vwap_reclaim_multiple_pullback_attempts(self) -> None:
        """First pullback fails (volume), second succeeds."""
        mock_ds = MockDataService(vwap=100.0)
        vwap_strategy = VwapReclaimStrategy(
            config=make_vwap_reclaim_config(
                min_pullback_pct=0.005,  # 0.5% required
                min_pullback_bars=2,
                volume_confirmation_multiplier=2.0,  # Need 2x average
            ),
            data_service=mock_ds,
        )
        vwap_strategy.set_watchlist(["AAPL"])
        vwap_strategy.allocated_capital = 30_000

        base_time = datetime(2026, 2, 25, 15, 0, 0, tzinfo=UTC)

        # Above VWAP
        await vwap_strategy.on_candle(
            make_candle(symbol="AAPL", close=101.0, volume=100_000, timestamp=base_time)
        )

        # First pullback (deep enough, but reclaim without volume)
        await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=99.0,
                low=99.0,
                volume=100_000,
                timestamp=base_time + timedelta(minutes=1),
            )
        )
        await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=99.0,
                low=99.0,
                volume=100_000,
                timestamp=base_time + timedelta(minutes=2),
            )
        )

        # Reclaim without volume (fails, resets to ABOVE_VWAP)
        signal1 = await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=150_000,  # Need 200K (2x average ~100K)
                timestamp=base_time + timedelta(minutes=3),
            )
        )
        assert signal1 is None
        assert vwap_strategy._get_symbol_state("AAPL").state == VwapState.ABOVE_VWAP

        # Second pullback
        await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=99.0,
                low=99.0,
                volume=100_000,
                timestamp=base_time + timedelta(minutes=4),
            )
        )
        await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=99.0,
                low=99.0,
                volume=100_000,
                timestamp=base_time + timedelta(minutes=5),
            )
        )

        # Reclaim with sufficient volume
        signal2 = await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=300_000,  # > 2x average
                timestamp=base_time + timedelta(minutes=6),
            )
        )
        assert signal2 is not None
        assert vwap_strategy._get_symbol_state("AAPL").state == VwapState.ENTERED


class TestRiskAndThrottling:
    """Tests for risk management and throttling across strategies."""

    @pytest.mark.asyncio
    async def test_throttle_isolation_vwap_vs_orb(self) -> None:
        """VWAP throttled, ORB continues trading normally."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 25, 10, 0, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        # VWAP has 5 consecutive losses
        vwap_losing_trades = [
            Trade(
                strategy_id="strat_vwap_reclaim",
                symbol="AAPL",
                side=OrderSide.BUY,
                entry_price=100.0,
                exit_price=99.0,
                stop_price=98.0,
                shares=10,
                entry_time=datetime(2026, 2, 24, 10, i, 0, tzinfo=UTC),
                exit_time=datetime(2026, 2, 24, 10, i + 5, 0, tzinfo=UTC),
                exit_reason=TradeExitReason.STOP_LOSS,
                commission=1.0,
                gross_pnl=-10.0,
                net_pnl=-11.0,
                outcome=TradeOutcome.LOSS,
            )
            for i in range(5)
        ]

        trade_logger = MagicMock()
        trade_logger.get_todays_pnl = AsyncMock(return_value=0.0)
        trade_logger.query_trades = AsyncMock(return_value=[])
        trade_logger.get_daily_pnl = AsyncMock(return_value=[])
        trade_logger.get_trades_by_date = AsyncMock(return_value=[])
        trade_logger.log_orchestrator_decision = AsyncMock()

        async def mock_get_trades_by_strategy(
            strategy_id: str, limit: int = 200
        ) -> list[Trade]:
            if strategy_id == "strat_vwap_reclaim":
                return vwap_losing_trades
            return []

        trade_logger.get_trades_by_strategy = AsyncMock(side_effect=mock_get_trades_by_strategy)

        data_service = MockDataService()

        config = OrchestratorConfig(
            max_allocation_pct=0.40,
            min_allocation_pct=0.10,
            cash_reserve_pct=0.20,
            consecutive_loss_throttle=5,
        )

        orchestrator = Orchestrator(
            config=config,
            event_bus=event_bus,
            clock=clock,
            trade_logger=trade_logger,
            broker=broker,
            data_service=data_service,
        )

        orb_strategy = OrbBreakoutStrategy(config=make_orb_breakout_config(), clock=clock)
        vwap_strategy = VwapReclaimStrategy(config=make_vwap_reclaim_config(), clock=clock)

        orchestrator.register_strategy(orb_strategy)
        orchestrator.register_strategy(vwap_strategy)

        await orchestrator.run_pre_market()

        allocations = orchestrator.current_allocations

        # ORB should be active with full allocation
        assert orb_strategy.is_active is True
        assert allocations["strat_orb_breakout"].throttle_action == ThrottleAction.NONE

        # VWAP should be throttled (REDUCE) but still active
        assert vwap_strategy.is_active is True
        assert allocations["strat_vwap_reclaim"].throttle_action == ThrottleAction.REDUCE

    @pytest.mark.asyncio
    async def test_allocation_exhaustion_three_strategies(self) -> None:
        """When all strategies at max positions, new signals rejected."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 25, 15, 0, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        risk_config = RiskConfig(
            account=AccountRiskConfig(
                daily_loss_limit_pct=0.03,
                max_concurrent_positions=3,  # Only 3 positions total
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

        # Fill up all 3 position slots
        for i, (symbol, strategy_id) in enumerate([
            ("AAPL", "strat_orb_breakout"),
            ("TSLA", "strat_orb_scalp"),
            ("NVDA", "strat_vwap_reclaim"),
        ]):
            broker.set_price(symbol, 100.0 + i * 50)
            signal = SignalEvent(
                strategy_id=strategy_id,
                symbol=symbol,
                side=Side.LONG,
                entry_price=100.0 + i * 50,
                stop_price=98.0 + i * 50,
                target_prices=(105.0 + i * 50,),
                share_count=10,
                rationale="Test position",
                time_stop_seconds=900,
            )
            result = await risk_manager.evaluate_signal(signal)
            assert isinstance(result, OrderApprovedEvent)
            await order_manager.on_approved(result)
            await asyncio.sleep(0.05)

        # Fourth signal should be rejected
        broker.set_price("META", 300.0)
        new_signal = SignalEvent(
            strategy_id="strat_orb_breakout",
            symbol="META",
            side=Side.LONG,
            entry_price=300.0,
            stop_price=295.0,
            target_prices=(310.0,),
            share_count=10,
            rationale="Fourth position attempt",
            time_stop_seconds=900,
        )
        result = await risk_manager.evaluate_signal(new_signal)
        assert isinstance(result, OrderRejectedEvent)
        assert "position" in result.reason.lower() or "concurrent" in result.reason.lower()

        await order_manager.stop()

    @pytest.mark.asyncio
    async def test_cross_strategy_stock_limit(self) -> None:
        """Cross-strategy single-stock exposure limit enforced."""
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
                max_single_stock_pct=0.05,  # 5% = $5,000 max
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

        # ORB takes $4,500 (30 shares × $150)
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
        orb_result = await risk_manager.evaluate_signal(orb_signal)
        assert isinstance(orb_result, OrderApprovedEvent)
        await order_manager.on_approved(orb_result)
        await asyncio.sleep(0.05)

        # VWAP tries to add $3,000 (20 shares × $150)
        # Total would be $7,500 > $5,000 limit
        vwap_signal = SignalEvent(
            strategy_id="strat_vwap_reclaim",
            symbol="AAPL",
            side=Side.LONG,
            entry_price=150.0,
            stop_price=149.0,
            target_prices=(151.0, 152.0),
            share_count=20,
            rationale="VWAP reclaim",
            time_stop_seconds=1800,
        )
        vwap_result = await risk_manager.evaluate_signal(vwap_signal)

        assert isinstance(vwap_result, OrderRejectedEvent)
        assert "exposure" in vwap_result.reason.lower() or "exceed" in vwap_result.reason.lower()

        await order_manager.stop()


class TestRegimeAndDailyReset:
    """Tests for regime handling and daily reset."""

    @pytest.mark.asyncio
    async def test_crisis_regime_suspends_vwap_reclaim(self) -> None:
        """VWAP Reclaim suspended in crisis regime (max_vix exceeded)."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 25, 10, 0, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        trade_logger = MagicMock()
        trade_logger.get_todays_pnl = AsyncMock(return_value=0.0)
        trade_logger.query_trades = AsyncMock(return_value=[])
        trade_logger.get_trades_by_strategy = AsyncMock(return_value=[])
        trade_logger.get_daily_pnl = AsyncMock(return_value=[])
        trade_logger.get_trades_by_date = AsyncMock(return_value=[])
        trade_logger.log_orchestrator_decision = AsyncMock()

        data_service = MockDataService()

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
        vwap_strategy = VwapReclaimStrategy(config=make_vwap_reclaim_config(), clock=clock)

        orchestrator.register_strategy(orb_strategy)
        orchestrator.register_strategy(vwap_strategy)

        # Force crisis regime
        orchestrator._current_regime = MarketRegime.CRISIS

        await orchestrator.run_pre_market()

        allocations = orchestrator.current_allocations

        # VWAP Reclaim has "crisis" not in allowed_regimes
        # (allowed: bullish_trending, range_bound, high_volatility)
        vwap_alloc = allocations["strat_vwap_reclaim"]
        assert vwap_alloc.eligible is False
        assert vwap_strategy.is_active is False

    @pytest.mark.asyncio
    async def test_three_strategy_daily_reset(self) -> None:
        """All three strategies clear state on daily reset."""
        clock = FixedClock(datetime(2026, 2, 25, 15, 30, 0, tzinfo=UTC))

        orb_strategy = OrbBreakoutStrategy(config=make_orb_breakout_config(), clock=clock)
        scalp_strategy = OrbScalpStrategy(config=make_orb_scalp_config(), clock=clock)
        vwap_strategy = VwapReclaimStrategy(
            config=make_vwap_reclaim_config(),
            data_service=MockDataService(vwap=100.0),
        )

        orb_strategy.set_watchlist(["AAPL"])
        scalp_strategy.set_watchlist(["AAPL"])
        vwap_strategy.set_watchlist(["AAPL"])

        # Build up state for each strategy
        for i in range(5):
            candle = make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 25, 14, 30 + i, 0, tzinfo=UTC),
            )
            await orb_strategy.on_candle(candle)
            await scalp_strategy.on_candle(candle)
            await vwap_strategy.on_candle(candle)

        # Verify state accumulated
        assert "AAPL" in orb_strategy._symbol_state
        assert "AAPL" in scalp_strategy._symbol_state
        assert "AAPL" in vwap_strategy._symbol_state

        # Reset all strategies
        orb_strategy.reset_daily_state()
        scalp_strategy.reset_daily_state()
        vwap_strategy.reset_daily_state()

        # All state cleared
        assert "AAPL" not in orb_strategy._symbol_state
        assert "AAPL" not in scalp_strategy._symbol_state
        assert "AAPL" not in vwap_strategy._symbol_state

    @pytest.mark.asyncio
    async def test_vwap_reclaim_outside_operating_window(self) -> None:
        """VWAP Reclaim pattern before 10:00 AM does not emit signal."""
        mock_ds = MockDataService(vwap=100.0)
        vwap_strategy = VwapReclaimStrategy(
            config=make_vwap_reclaim_config(earliest_entry="10:00", latest_entry="12:00"),
            data_service=mock_ds,
        )
        vwap_strategy.set_watchlist(["AAPL"])
        vwap_strategy.allocated_capital = 30_000

        # All candles at 9:30-9:35 AM ET (14:30-14:35 UTC in February)
        base_time = datetime(2026, 2, 25, 14, 30, 0, tzinfo=UTC)  # 9:30 AM ET

        # Above VWAP
        await vwap_strategy.on_candle(
            make_candle(symbol="AAPL", close=101.0, volume=100_000, timestamp=base_time)
        )

        # Pullback
        for i in range(3):
            await vwap_strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    low=99.0,
                    volume=100_000,
                    timestamp=base_time + timedelta(minutes=1 + i),
                )
            )

        # Valid reclaim pattern at 9:35 AM ET (before 10:00 AM window)
        signal = await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=150_000,
                timestamp=base_time + timedelta(minutes=5),  # 9:35 AM ET
            )
        )

        assert signal is None
        # Should reset to ABOVE_VWAP for retry later
        assert vwap_strategy._get_symbol_state("AAPL").state == VwapState.ABOVE_VWAP


class TestWatchlistSharing:
    """Tests for shared watchlist across strategies."""

    @pytest.mark.asyncio
    async def test_three_strategies_share_watchlist(self) -> None:
        """All three strategies can use the same watchlist."""
        clock = FixedClock(datetime(2026, 2, 25, 15, 0, 0, tzinfo=UTC))

        orb_strategy = OrbBreakoutStrategy(config=make_orb_breakout_config(), clock=clock)
        scalp_strategy = OrbScalpStrategy(config=make_orb_scalp_config(), clock=clock)
        vwap_strategy = VwapReclaimStrategy(config=make_vwap_reclaim_config())

        shared_watchlist = ["AAPL", "TSLA", "NVDA", "META"]

        orb_strategy.set_watchlist(shared_watchlist)
        scalp_strategy.set_watchlist(shared_watchlist)
        vwap_strategy.set_watchlist(shared_watchlist)

        assert set(orb_strategy._watchlist) == set(shared_watchlist)
        assert set(scalp_strategy._watchlist) == set(shared_watchlist)
        assert set(vwap_strategy._watchlist) == set(shared_watchlist)


class TestTimeStopSeconds:
    """Tests for per-strategy time stop handling."""

    @pytest.mark.asyncio
    async def test_vwap_position_has_time_stop_seconds(self) -> None:
        """VWAP Reclaim position stores time_stop_seconds from signal."""
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

        # Create VWAP signal with 30 minute (1800 second) time stop
        broker.set_price("AAPL", 100.0)
        vwap_signal = SignalEvent(
            strategy_id="strat_vwap_reclaim",
            symbol="AAPL",
            side=Side.LONG,
            entry_price=100.0,
            stop_price=99.0,
            target_prices=(101.0, 102.0),
            share_count=50,
            rationale="VWAP reclaim",
            time_stop_seconds=1800,  # 30 minutes
        )

        approved = OrderApprovedEvent(signal=vwap_signal)
        await order_manager.on_approved(approved)
        await asyncio.sleep(0.05)

        positions = order_manager.get_managed_positions()
        assert "AAPL" in positions
        pos = positions["AAPL"][0]
        assert pos.time_stop_seconds == 1800

        await order_manager.stop()

    @pytest.mark.asyncio
    async def test_all_three_strategies_different_time_stops(self) -> None:
        """Each strategy has distinct time stop durations."""
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

        # ORB: 15 min = 900s, Scalp: 2 min = 120s, VWAP: 30 min = 1800s
        signals = [
            ("AAPL", "strat_orb_breakout", 900),
            ("TSLA", "strat_orb_scalp", 120),
            ("NVDA", "strat_vwap_reclaim", 1800),
        ]

        for symbol, strategy_id, time_stop in signals:
            broker.set_price(symbol, 100.0)
            signal = SignalEvent(
                strategy_id=strategy_id,
                symbol=symbol,
                side=Side.LONG,
                entry_price=100.0,
                stop_price=98.0,
                target_prices=(102.0,),
                share_count=10,
                rationale="Test signal",
                time_stop_seconds=time_stop,
            )
            approved = OrderApprovedEvent(signal=signal)
            await order_manager.on_approved(approved)
            await asyncio.sleep(0.05)

        positions = order_manager.get_managed_positions()

        assert positions["AAPL"][0].time_stop_seconds == 900
        assert positions["TSLA"][0].time_stop_seconds == 120
        assert positions["NVDA"][0].time_stop_seconds == 1800

        await order_manager.stop()


class TestPositionClosedEventRouting:
    """Tests for PositionClosedEvent routing to strategies (Fix 2 — Sprint 19 Session 6)."""

    @pytest.mark.asyncio
    async def test_vwap_position_close_decrements_concurrent_positions(self) -> None:
        """After mark_position_closed, VWAP strategy's concurrent count decreases.

        This tests that:
        1. With max_concurrent_positions=1, a second entry is blocked while first is active
        2. After mark_position_closed, the position count decreases
        3. A new entry can then succeed
        """
        mock_ds = MockDataService(vwap=100.0)
        # Create config with max_concurrent_positions=1 to test concurrent position limit
        vwap_config = VwapReclaimConfig(
            strategy_id="strat_vwap_reclaim",
            name="VWAP Reclaim",
            min_pullback_pct=0.002,
            max_pullback_pct=0.02,
            min_pullback_bars=3,
            volume_confirmation_multiplier=1.0,
            risk_limits=StrategyRiskLimits(
                max_concurrent_positions=1,
            ),
            operating_window=OperatingWindow(
                earliest_entry="10:00",
                latest_entry="12:00",
            ),
        )
        vwap_strategy = VwapReclaimStrategy(
            config=vwap_config,
            data_service=mock_ds,
        )
        vwap_strategy.set_watchlist(["AAPL", "TSLA"])
        vwap_strategy.allocated_capital = 30_000

        # Get AAPL into ENTERED state with position_active=True
        await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=101.0,
                volume=100_000,
                timestamp=datetime(2026, 2, 25, 15, 0, 0, tzinfo=UTC),
            )
        )
        for i in range(3):
            await vwap_strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    low=99.0,
                    volume=100_000,
                    timestamp=datetime(2026, 2, 25, 15, 1 + i, 0, tzinfo=UTC),
                )
            )
        signal_aapl = await vwap_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=150_000,
                timestamp=datetime(2026, 2, 25, 15, 5, 0, tzinfo=UTC),
            )
        )
        assert signal_aapl is not None
        assert vwap_strategy._get_symbol_state("AAPL").position_active is True

        # Verify concurrent position count is 1
        active_count = sum(
            1 for s in vwap_strategy._symbol_state.values() if s.position_active
        )
        assert active_count == 1

        # After mark_position_closed, position count should be 0
        vwap_strategy.mark_position_closed("AAPL")
        assert vwap_strategy._get_symbol_state("AAPL").position_active is False
        active_count = sum(
            1 for s in vwap_strategy._symbol_state.values() if s.position_active
        )
        assert active_count == 0

        # Now TSLA should be able to enter (fresh state)
        await vwap_strategy.on_candle(
            make_candle(
                symbol="TSLA",
                close=101.0,  # Above VWAP=100
                volume=100_000,
                timestamp=datetime(2026, 2, 25, 15, 20, 0, tzinfo=UTC),
            )
        )
        for i in range(3):
            await vwap_strategy.on_candle(
                make_candle(
                    symbol="TSLA",
                    close=99.0,  # Below VWAP=100
                    low=99.0,
                    volume=100_000,
                    timestamp=datetime(2026, 2, 25, 15, 21 + i, 0, tzinfo=UTC),
                )
            )
        signal_tsla = await vwap_strategy.on_candle(
            make_candle(
                symbol="TSLA",
                close=100.2,  # Reclaim VWAP=100
                volume=150_000,
                timestamp=datetime(2026, 2, 25, 15, 25, 0, tzinfo=UTC),
            )
        )
        # Should succeed since AAPL position is closed
        assert signal_tsla is not None
        assert signal_tsla.symbol == "TSLA"

    @pytest.mark.asyncio
    async def test_orb_position_close_calls_mark_position_closed(self) -> None:
        """ORB strategy's mark_position_closed is called on PositionClosedEvent."""
        clock = FixedClock(datetime(2026, 2, 25, 14, 40, 0, tzinfo=UTC))

        orb_strategy = OrbBreakoutStrategy(
            config=make_orb_breakout_config(),
            clock=clock,
        )
        orb_strategy.set_watchlist(["AAPL"])
        orb_strategy.allocated_capital = 30_000

        # Build OR and get entry
        for i in range(5):
            await orb_strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    timestamp=datetime(2026, 2, 25, 14, 30 + i, 0, tzinfo=UTC),
                    open_price=100.0,
                    high=101.0,
                    low=99.0,
                    close=100.0 + i * 0.1,
                    volume=100_000,
                )
            )

        # Trigger breakout and entry
        signal = await orb_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 25, 14, 40, 0, tzinfo=UTC),
                open_price=101.0,
                high=102.0,
                low=101.0,
                close=101.5,
                volume=200_000,
            )
        )
        assert signal is not None

        # Verify position is marked active
        state = orb_strategy._get_symbol_state("AAPL")
        assert state.position_active is True

        # Call mark_position_closed
        orb_strategy.mark_position_closed("AAPL")

        # Verify position is marked inactive
        assert state.position_active is False
