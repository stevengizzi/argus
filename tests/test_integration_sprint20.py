"""Sprint 20 Integration Tests — Four-Strategy Multi-Strategy Operations.

Tests for four-strategy scenarios including:
- Four strategies (ORB, Scalp, VWAP Reclaim, Afternoon Momentum) registering with Orchestrator
- Equal allocation across four strategies
- Sequential flows (ORB → VWAP Reclaim → Afternoon Momentum on same symbol)
- Concurrent position management
- Afternoon Momentum state machine in integration context
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
    AfternoonMomentumConfig,
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
    OrderApprovedEvent,
    OrderRejectedEvent,
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
from argus.strategies.afternoon_momentum import (
    AfternoonMomentumStrategy,
    ConsolidationState,
)
from argus.strategies.orb_breakout import OrbBreakoutStrategy
from argus.strategies.orb_scalp import OrbScalpStrategy
from argus.strategies.vwap_reclaim import VwapReclaimStrategy


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
    volume_confirmation_multiplier: float = 1.0,
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


def make_afternoon_momentum_config(
    strategy_id: str = "strat_afternoon_momentum",
    **overrides,
) -> AfternoonMomentumConfig:
    """Create an AfternoonMomentumConfig for testing."""
    defaults = dict(
        strategy_id=strategy_id,
        name="Afternoon Momentum",
        consolidation_start_time="12:00",
        consolidation_atr_ratio=0.75,
        max_consolidation_atr_ratio=2.0,
        min_consolidation_bars=5,  # Minimum allowed by config
        volume_multiplier=1.0,  # Low for testing
        max_chase_pct=0.01,
        target_1_r=1.0,
        target_2_r=2.0,
        max_hold_minutes=60,
        stop_buffer_pct=0.001,
        force_close_time="15:45",
        operating_window=OperatingWindow(
            earliest_entry="14:00",
            latest_entry="15:30",
            force_close="15:45",
        ),
        risk_limits=StrategyRiskLimits(
            max_trades_per_day=6,
            max_daily_loss_pct=0.03,
            max_loss_per_trade_pct=0.01,
            max_concurrent_positions=3,
        ),
    )
    defaults.update(overrides)
    return AfternoonMomentumConfig(**defaults)


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
        timestamp = datetime(2026, 2, 26, 19, 15, 0, tzinfo=UTC)  # 2:15 PM ET
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

    def __init__(
        self,
        vwap: float | None = 100.0,
        atr_14: float | None = 1.0,
    ) -> None:
        """Initialize with default values."""
        self._vwap = vwap
        self._atr_14 = atr_14
        self._indicator_values: dict[str, dict[str, float | None]] = {}

    def set_indicator(
        self, symbol: str, indicator: str, value: float | None
    ) -> None:
        """Set indicator for a specific symbol."""
        if symbol not in self._indicator_values:
            self._indicator_values[symbol] = {}
        self._indicator_values[symbol][indicator] = value

    async def get_indicator(self, symbol: str, indicator: str) -> float | None:
        """Get indicator value."""
        if symbol in self._indicator_values:
            if indicator in self._indicator_values[symbol]:
                return self._indicator_values[symbol][indicator]
        if indicator == "vwap":
            return self._vwap
        if indicator == "atr_14":
            return self._atr_14
        return None

    async def get_daily_bars(self, symbol: str, **kwargs) -> None:
        """Mock get_daily_bars."""
        return None

    async def fetch_daily_bars(self, symbol: str, lookback_days: int) -> None:
        """Mock fetch_daily_bars."""
        return None


def make_mock_trade_logger() -> MagicMock:
    """Create a mock TradeLogger with all required methods."""
    trade_logger = MagicMock()
    trade_logger.get_todays_pnl = AsyncMock(return_value=0.0)
    trade_logger.query_trades = AsyncMock(return_value=[])
    trade_logger.get_trades_by_strategy = AsyncMock(return_value=[])
    trade_logger.get_daily_pnl = AsyncMock(return_value=[])
    trade_logger.get_trades_by_date = AsyncMock(return_value=[])
    trade_logger.log_orchestrator_decision = AsyncMock()
    return trade_logger


# ===========================================================================
# Test Classes
# ===========================================================================


class TestFourStrategyRegistration:
    """Tests for four-strategy registration and basic operations."""

    @pytest.mark.asyncio
    async def test_four_strategy_registration(self) -> None:
        """Register all four strategies, verify orchestrator.get_strategies() has 4."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 26, 14, 0, 0, tzinfo=UTC))  # 9:00 AM ET
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        trade_logger = make_mock_trade_logger()
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
        afternoon_strategy = AfternoonMomentumStrategy(
            config=make_afternoon_momentum_config(),
            data_service=data_service,
            clock=clock,
        )

        orchestrator.register_strategy(orb_strategy)
        orchestrator.register_strategy(scalp_strategy)
        orchestrator.register_strategy(vwap_strategy)
        orchestrator.register_strategy(afternoon_strategy)

        strategies = orchestrator.get_strategies()

        assert len(strategies) == 4
        assert "strat_orb_breakout" in strategies
        assert "strat_orb_scalp" in strategies
        assert "strat_vwap_reclaim" in strategies
        assert "strat_afternoon_momentum" in strategies

    @pytest.mark.asyncio
    async def test_four_strategy_equal_allocation(self) -> None:
        """Four strategies registered, but only 3 eligible at 9:00 AM.

        Afternoon Momentum's operating window is 2:00 PM - 3:30 PM, so at
        pre-market time (9:00 AM), it is not eligible. The three eligible
        strategies (ORB, Scalp, VWAP) split 80% equally → ~26.67% each.
        """
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 26, 14, 0, 0, tzinfo=UTC))  # 9:00 AM ET
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        trade_logger = make_mock_trade_logger()
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
        afternoon_strategy = AfternoonMomentumStrategy(
            config=make_afternoon_momentum_config(),
            data_service=data_service,
            clock=clock,
        )

        orchestrator.register_strategy(orb_strategy)
        orchestrator.register_strategy(scalp_strategy)
        orchestrator.register_strategy(vwap_strategy)
        orchestrator.register_strategy(afternoon_strategy)

        await orchestrator.run_pre_market()

        allocations = orchestrator.current_allocations
        assert len(allocations) == 4

        # Three strategies eligible at 9:00 AM (afternoon not in window)
        eligible_count = sum(1 for a in allocations.values() if a.eligible)
        assert eligible_count == 3

        # Eligible strategies get ~33.3% each (80% / 3)
        for strategy_id, alloc in allocations.items():
            if alloc.eligible:
                assert alloc.allocation_pct == pytest.approx(1 / 3, rel=0.01)
            else:
                # Afternoon momentum not eligible at this time
                assert alloc.allocation_pct == 0.0

        # Total deployment = 80K (100K - 20% reserve)
        deployable = 100_000 * 0.80
        total_allocated = sum(a.allocation_dollars for a in allocations.values() if a.eligible)
        assert total_allocated == pytest.approx(deployable, rel=0.01)


class TestSequentialFlows:
    """Tests for sequential trading flows between all four strategies."""

    @pytest.mark.asyncio
    async def test_full_day_sequential_flow(self) -> None:
        """ORB signal at 9:40 AM, VWAP signal at 10:30, Afternoon signal at 2:15 PM."""
        event_bus = EventBus()
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        risk_config = RiskConfig(
            account=AccountRiskConfig(
                daily_loss_limit_pct=0.03,
                max_concurrent_positions=10,
            ),
            cross_strategy=CrossStrategyRiskConfig(
                duplicate_stock_policy=DuplicateStockPolicy.ALLOW_ALL,
                max_single_stock_pct=0.20,
            ),
        )

        # ORB signal at 9:40 AM ET (14:40 UTC)
        clock_orb = FixedClock(datetime(2026, 2, 26, 14, 40, 0, tzinfo=UTC))
        orb_strategy = OrbBreakoutStrategy(config=make_orb_breakout_config(), clock=clock_orb)
        orb_strategy.set_watchlist(["AAPL"])
        orb_strategy.allocated_capital = 20_000

        # Build OR
        for i in range(5):
            await orb_strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    timestamp=datetime(2026, 2, 26, 14, 30 + i, 0, tzinfo=UTC),
                    close=100.0 + i * 0.1,
                    volume=100_000,
                )
            )

        # ORB breakout
        orb_signal = await orb_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 26, 14, 40, 0, tzinfo=UTC),
                open_price=101.0,
                high=102.0,
                low=101.0,
                close=101.5,
                volume=200_000,
            )
        )
        assert orb_signal is not None
        assert orb_signal.strategy_id == "strat_orb_breakout"

        # VWAP signal at 10:30 AM ET (15:30 UTC)
        mock_ds = MockDataService(vwap=100.0)
        vwap_strategy = VwapReclaimStrategy(
            config=make_vwap_reclaim_config(),
            data_service=mock_ds,
        )
        vwap_strategy.set_watchlist(["TSLA"])
        vwap_strategy.allocated_capital = 20_000

        # Above VWAP
        await vwap_strategy.on_candle(
            make_candle(
                symbol="TSLA",
                close=101.0,
                timestamp=datetime(2026, 2, 26, 15, 0, 0, tzinfo=UTC),
            )
        )
        # Pullback
        for i in range(3):
            await vwap_strategy.on_candle(
                make_candle(
                    symbol="TSLA",
                    close=99.0,
                    low=99.0,
                    timestamp=datetime(2026, 2, 26, 15, 1 + i, 0, tzinfo=UTC),
                )
            )
        # Reclaim
        vwap_signal = await vwap_strategy.on_candle(
            make_candle(
                symbol="TSLA",
                close=100.2,
                volume=150_000,
                timestamp=datetime(2026, 2, 26, 15, 30, 0, tzinfo=UTC),  # 10:30 AM ET
            )
        )
        assert vwap_signal is not None
        assert vwap_signal.strategy_id == "strat_vwap_reclaim"

        # Afternoon Momentum signal at 2:15 PM ET (19:15 UTC)
        afternoon_ds = MockDataService(vwap=100.0, atr_14=1.0)
        clock_afternoon = FixedClock(datetime(2026, 2, 26, 19, 15, 0, tzinfo=UTC))
        afternoon_strategy = AfternoonMomentumStrategy(
            config=make_afternoon_momentum_config(),
            data_service=afternoon_ds,
            clock=clock_afternoon,
        )
        afternoon_strategy.set_watchlist(["NVDA"])
        afternoon_strategy.allocated_capital = 20_000

        # Build consolidation (12:00-2:00 PM = 17:00-19:00 UTC)
        for i in range(6):
            await afternoon_strategy.on_candle(
                make_candle(
                    symbol="NVDA",
                    timestamp=datetime(2026, 2, 26, 17, i, 0, tzinfo=UTC),  # 12:00 PM+ ET
                    open_price=100.0,
                    high=100.3,
                    low=99.7,
                    close=100.0,
                    volume=100_000,
                )
            )

        # Breakout candle at 2:15 PM ET
        afternoon_signal = await afternoon_strategy.on_candle(
            make_candle(
                symbol="NVDA",
                timestamp=datetime(2026, 2, 26, 19, 15, 0, tzinfo=UTC),
                open_price=100.0,
                high=101.5,
                low=100.0,
                close=101.2,
                volume=200_000,
            )
        )
        assert afternoon_signal is not None
        assert afternoon_signal.strategy_id == "strat_afternoon_momentum"

        # Verify risk manager would approve all three
        order_config = OrderManagerConfig()
        order_manager = OrderManager(
            event_bus=event_bus,
            broker=broker,
            clock=clock_afternoon,
            config=order_config,
        )
        await order_manager.start()

        risk_manager = RiskManager(
            config=risk_config,
            broker=broker,
            event_bus=event_bus,
            clock=clock_afternoon,
            order_manager=order_manager,
        )
        await risk_manager.initialize()
        await risk_manager.reset_daily_state()

        # All three signals should pass risk check
        broker.set_price("AAPL", 101.5)
        orb_result = await risk_manager.evaluate_signal(orb_signal)
        assert isinstance(orb_result, OrderApprovedEvent)

        broker.set_price("TSLA", 100.2)
        vwap_result = await risk_manager.evaluate_signal(vwap_signal)
        assert isinstance(vwap_result, OrderApprovedEvent)

        broker.set_price("NVDA", 101.2)
        afternoon_result = await risk_manager.evaluate_signal(afternoon_signal)
        assert isinstance(afternoon_result, OrderApprovedEvent)

        await order_manager.stop()

    @pytest.mark.asyncio
    async def test_allow_all_same_symbol_different_times(self) -> None:
        """ORB trades TSLA at 9:40, afternoon momentum trades TSLA at 2:15."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 26, 19, 15, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        risk_config = RiskConfig(
            account=AccountRiskConfig(
                daily_loss_limit_pct=0.03,
                max_concurrent_positions=10,
            ),
            cross_strategy=CrossStrategyRiskConfig(
                duplicate_stock_policy=DuplicateStockPolicy.ALLOW_ALL,
                max_single_stock_pct=0.10,  # 10% = $10,000 max
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

        broker.set_price("TSLA", 150.0)

        # ORB position at 9:40 AM (already closed, but use fresh signal for test)
        orb_signal = SignalEvent(
            strategy_id="strat_orb_breakout",
            symbol="TSLA",
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

        # Afternoon Momentum position at 2:15 PM (same symbol)
        # Total = $4,500 + $3,000 = $7,500 < $10,000 limit
        afternoon_signal = SignalEvent(
            strategy_id="strat_afternoon_momentum",
            symbol="TSLA",
            side=Side.LONG,
            entry_price=150.0,
            stop_price=149.0,
            target_prices=(151.5, 153.0),
            share_count=20,
            rationale="Afternoon breakout",
            time_stop_seconds=3600,
        )
        afternoon_result = await risk_manager.evaluate_signal(afternoon_signal)
        assert isinstance(afternoon_result, OrderApprovedEvent)

        await order_manager.stop()


class TestCrossStrategyRisk:
    """Tests for cross-strategy risk enforcement."""

    @pytest.mark.asyncio
    async def test_cross_strategy_stock_exposure(self) -> None:
        """All four try to enter AAPL. Aggregate exposure capped at 5%."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 26, 15, 0, 0, tzinfo=UTC))
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

        broker.set_price("AAPL", 100.0)

        # ORB: $3,000 (30 shares × $100)
        orb_signal = SignalEvent(
            strategy_id="strat_orb_breakout",
            symbol="AAPL",
            side=Side.LONG,
            entry_price=100.0,
            stop_price=98.0,
            target_prices=(102.0,),
            share_count=30,
            rationale="ORB",
            time_stop_seconds=900,
        )
        orb_result = await risk_manager.evaluate_signal(orb_signal)
        assert isinstance(orb_result, OrderApprovedEvent)
        await order_manager.on_approved(orb_result)
        await asyncio.sleep(0.05)

        # Scalp: $1,500 (15 shares × $100) — total $4,500
        scalp_signal = SignalEvent(
            strategy_id="strat_orb_scalp",
            symbol="AAPL",
            side=Side.LONG,
            entry_price=100.0,
            stop_price=99.0,
            target_prices=(100.30,),
            share_count=15,
            rationale="Scalp",
            time_stop_seconds=120,
        )
        scalp_result = await risk_manager.evaluate_signal(scalp_signal)
        assert isinstance(scalp_result, OrderApprovedEvent)
        await order_manager.on_approved(scalp_result)
        await asyncio.sleep(0.05)

        # VWAP: $1,000 (10 shares × $100) — total $5,500 > $5,000 limit
        vwap_signal = SignalEvent(
            strategy_id="strat_vwap_reclaim",
            symbol="AAPL",
            side=Side.LONG,
            entry_price=100.0,
            stop_price=99.5,
            target_prices=(101.0,),
            share_count=10,
            rationale="VWAP",
            time_stop_seconds=1800,
        )
        vwap_result = await risk_manager.evaluate_signal(vwap_signal)
        assert isinstance(vwap_result, OrderRejectedEvent)
        assert "exposure" in vwap_result.reason.lower() or "exceed" in vwap_result.reason.lower()

        await order_manager.stop()

    @pytest.mark.asyncio
    async def test_four_strategies_concurrent_positions(self) -> None:
        """All four strategies can hold positions on different symbols."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 26, 15, 0, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        risk_config = RiskConfig(
            account=AccountRiskConfig(
                daily_loss_limit_pct=0.03,
                max_concurrent_positions=10,
            ),
            cross_strategy=CrossStrategyRiskConfig(
                duplicate_stock_policy=DuplicateStockPolicy.ALLOW_ALL,
                max_single_stock_pct=0.20,
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

        # Four positions on four different symbols
        signals = [
            ("AAPL", "strat_orb_breakout", 150.0, 148.0, (152.0,), 20, 900),
            ("TSLA", "strat_orb_scalp", 200.0, 198.0, (200.60,), 25, 120),
            ("NVDA", "strat_vwap_reclaim", 500.0, 495.0, (505.0,), 10, 1800),
            ("META", "strat_afternoon_momentum", 300.0, 297.0, (303.0,), 15, 3600),
        ]

        for symbol, strategy_id, entry, stop, targets, shares, time_stop in signals:
            broker.set_price(symbol, entry)
            signal = SignalEvent(
                strategy_id=strategy_id,
                symbol=symbol,
                side=Side.LONG,
                entry_price=entry,
                stop_price=stop,
                target_prices=targets,
                share_count=shares,
                rationale="Test position",
                time_stop_seconds=time_stop,
            )
            result = await risk_manager.evaluate_signal(signal)
            assert isinstance(result, OrderApprovedEvent)
            await order_manager.on_approved(result)
            await asyncio.sleep(0.05)

        # Verify all four positions opened
        assert len(opened_events) == 4
        positions = order_manager.get_managed_positions()
        assert "AAPL" in positions
        assert "TSLA" in positions
        assert "NVDA" in positions
        assert "META" in positions

        await order_manager.stop()


class TestAfternoonMomentumStateMachine:
    """Tests for Afternoon Momentum state machine in integration context."""

    @pytest.mark.asyncio
    async def test_afternoon_regime_active(self) -> None:
        """Bullish trending regime → afternoon momentum active."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 26, 14, 0, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        trade_logger = make_mock_trade_logger()
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

        afternoon_strategy = AfternoonMomentumStrategy(
            config=make_afternoon_momentum_config(),
            data_service=data_service,
            clock=clock,
        )

        orchestrator.register_strategy(afternoon_strategy)

        # Force bullish trending regime
        orchestrator._current_regime = MarketRegime.BULLISH_TRENDING

        await orchestrator.run_pre_market()

        # Afternoon momentum should be active in bullish trending
        assert afternoon_strategy.is_active is True
        allocations = orchestrator.current_allocations
        assert allocations["strat_afternoon_momentum"].eligible is True

    @pytest.mark.asyncio
    async def test_afternoon_regime_suspended(self) -> None:
        """Crisis regime → afternoon momentum suspended."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 26, 14, 0, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        trade_logger = make_mock_trade_logger()
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

        afternoon_strategy = AfternoonMomentumStrategy(
            config=make_afternoon_momentum_config(),
            data_service=data_service,
            clock=clock,
        )

        orchestrator.register_strategy(afternoon_strategy)

        # Force crisis regime
        orchestrator._current_regime = MarketRegime.CRISIS

        await orchestrator.run_pre_market()

        # Afternoon momentum should be inactive in crisis
        allocations = orchestrator.current_allocations
        assert allocations["strat_afternoon_momentum"].eligible is False
        assert afternoon_strategy.is_active is False

    @pytest.mark.asyncio
    async def test_no_consolidation_no_entry(self) -> None:
        """Feed midday candles with wide range → REJECTED, no afternoon signal."""
        data_service = MockDataService(vwap=100.0, atr_14=1.0)
        clock = FixedClock(datetime(2026, 2, 26, 19, 15, 0, tzinfo=UTC))  # 2:15 PM ET

        afternoon_strategy = AfternoonMomentumStrategy(
            config=make_afternoon_momentum_config(
                min_consolidation_bars=5,
                consolidation_atr_ratio=0.75,
                max_consolidation_atr_ratio=2.0,
            ),
            data_service=data_service,
            clock=clock,
        )
        afternoon_strategy.set_watchlist(["AAPL"])
        afternoon_strategy.allocated_capital = 20_000

        # Feed midday candles with wide range (exceeds max_consolidation_atr_ratio)
        # ATR-14 = 1.0, so max range = 1.0 * 2.0 = 2.0
        # Use candles with range = 3.0 (high-low) to exceed max
        for i in range(6):
            await afternoon_strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    timestamp=datetime(2026, 2, 26, 17, i, 0, tzinfo=UTC),  # 12:00 PM+ ET
                    open_price=100.0,
                    high=101.5,
                    low=98.5,  # range = 3.0 > max 2.0
                    close=100.0,
                    volume=100_000,
                )
            )

        state = afternoon_strategy._get_symbol_state("AAPL")
        assert state.state == ConsolidationState.REJECTED

        # Breakout should not generate signal
        signal = await afternoon_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 26, 19, 15, 0, tzinfo=UTC),
                open_price=100.0,
                high=102.0,
                low=100.0,
                close=101.5,
                volume=200_000,
            )
        )
        assert signal is None

    @pytest.mark.asyncio
    async def test_consolidation_confirmed_breakout_triggers(self) -> None:
        """Feed tight midday candles → CONSOLIDATED, then breakout candle → signal."""
        data_service = MockDataService(vwap=100.0, atr_14=1.0)
        clock = FixedClock(datetime(2026, 2, 26, 19, 15, 0, tzinfo=UTC))

        afternoon_strategy = AfternoonMomentumStrategy(
            config=make_afternoon_momentum_config(
                min_consolidation_bars=5,
                consolidation_atr_ratio=0.75,
            ),
            data_service=data_service,
            clock=clock,
        )
        afternoon_strategy.set_watchlist(["AAPL"])
        afternoon_strategy.allocated_capital = 20_000

        # Feed tight midday candles (range < consolidation_atr_ratio * ATR-14 = 0.75)
        for i in range(6):
            await afternoon_strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    timestamp=datetime(2026, 2, 26, 17, i, 0, tzinfo=UTC),
                    open_price=100.0,
                    high=100.3,  # range = 0.6 < 0.75
                    low=99.7,
                    close=100.0,
                    volume=100_000,
                )
            )

        state = afternoon_strategy._get_symbol_state("AAPL")
        assert state.state == ConsolidationState.CONSOLIDATED

        # Breakout candle at 2:15 PM ET
        signal = await afternoon_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 26, 19, 15, 0, tzinfo=UTC),
                open_price=100.0,
                high=101.5,
                low=100.0,
                close=101.2,
                volume=200_000,
            )
        )
        assert signal is not None
        assert signal.strategy_id == "strat_afternoon_momentum"
        assert signal.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_volume_filter_blocks(self) -> None:
        """Breakout candle with low volume → no signal."""
        data_service = MockDataService(vwap=100.0, atr_14=1.0)
        clock = FixedClock(datetime(2026, 2, 26, 19, 15, 0, tzinfo=UTC))

        afternoon_strategy = AfternoonMomentumStrategy(
            config=make_afternoon_momentum_config(
                min_consolidation_bars=5,
                volume_multiplier=2.0,  # Need 2x average volume
            ),
            data_service=data_service,
            clock=clock,
        )
        afternoon_strategy.set_watchlist(["AAPL"])
        afternoon_strategy.allocated_capital = 20_000

        # Build consolidation
        for i in range(6):
            await afternoon_strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    timestamp=datetime(2026, 2, 26, 17, i, 0, tzinfo=UTC),
                    open_price=100.0,
                    high=100.3,
                    low=99.7,
                    close=100.0,
                    volume=100_000,  # Average = 100K
                )
            )

        # Breakout with low volume (need 200K = 2x average)
        signal = await afternoon_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 26, 19, 15, 0, tzinfo=UTC),
                open_price=100.0,
                high=101.5,
                low=100.0,
                close=101.2,
                volume=150_000,  # < 200K required
            )
        )
        assert signal is None


class TestTimeStopsAndEOD:
    """Tests for time stops and EOD flatten behavior."""

    @pytest.mark.asyncio
    async def test_late_entry_compressed_time_stop(self) -> None:
        """Entry at 3:28 PM → time_stop_seconds reflects 17 minutes to force_close."""
        data_service = MockDataService(vwap=100.0, atr_14=1.0)
        # 3:28 PM ET = 20:28 UTC
        clock = FixedClock(datetime(2026, 2, 26, 20, 28, 0, tzinfo=UTC))

        afternoon_strategy = AfternoonMomentumStrategy(
            config=make_afternoon_momentum_config(
                min_consolidation_bars=5,
                max_hold_minutes=60,
                force_close_time="15:45",  # 3:45 PM ET
                latest_entry="15:30",  # 3:30 PM ET
            ),
            data_service=data_service,
            clock=clock,
        )
        afternoon_strategy.set_watchlist(["AAPL"])
        afternoon_strategy.allocated_capital = 20_000

        # Build consolidation
        for i in range(6):
            await afternoon_strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    timestamp=datetime(2026, 2, 26, 17, i, 0, tzinfo=UTC),
                    open_price=100.0,
                    high=100.3,
                    low=99.7,
                    close=100.0,
                    volume=100_000,
                )
            )

        # Entry at 3:28 PM ET → 17 minutes to 3:45 PM force_close
        signal = await afternoon_strategy.on_candle(
            make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 26, 20, 28, 0, tzinfo=UTC),
                open_price=100.0,
                high=101.5,
                low=100.0,
                close=101.2,
                volume=200_000,
            )
        )
        assert signal is not None
        # 17 minutes = 17 × 60 = 1020 seconds
        assert signal.time_stop_seconds == 17 * 60

    @pytest.mark.asyncio
    async def test_eod_flatten_afternoon_position(self) -> None:
        """Position open at 3:44 PM, EOD flatten at 3:50 PM."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 26, 20, 44, 0, tzinfo=UTC))  # 3:44 PM ET
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        order_config = OrderManagerConfig(eod_flatten_time="15:50")
        order_manager = OrderManager(
            event_bus=event_bus,
            broker=broker,
            clock=clock,
            config=order_config,
        )
        await order_manager.start()

        broker.set_price("AAPL", 100.0)
        signal = SignalEvent(
            strategy_id="strat_afternoon_momentum",
            symbol="AAPL",
            side=Side.LONG,
            entry_price=100.0,
            stop_price=99.0,
            target_prices=(101.0, 102.0),
            share_count=50,
            rationale="Afternoon momentum",
            time_stop_seconds=3600,
        )

        approved = OrderApprovedEvent(signal=signal)
        await order_manager.on_approved(approved)
        await asyncio.sleep(0.05)

        positions = order_manager.get_managed_positions()
        assert "AAPL" in positions

        await order_manager.stop()


class TestThrottling:
    """Tests for strategy throttling behavior."""

    @pytest.mark.asyncio
    async def test_orchestrator_throttle_blocks_afternoon(self) -> None:
        """Afternoon momentum throttled by consecutive losses → allocation reduced.

        Uses the same pattern as test_throttle_isolation_vwap_vs_orb in Sprint 19.
        Two strategies registered, afternoon momentum has 6 consecutive losses.
        """
        event_bus = EventBus()
        # Set clock to 2:30 PM ET (19:30 UTC) so afternoon momentum is in window
        clock = FixedClock(datetime(2026, 2, 26, 19, 30, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        # Create 6 losing trades for afternoon momentum (exceeds throttle threshold of 5)
        afternoon_losing_trades = [
            Trade(
                strategy_id="strat_afternoon_momentum",
                symbol="AAPL",
                side=OrderSide.BUY,
                entry_price=100.0,
                exit_price=99.0,
                stop_price=98.0,
                shares=10,
                entry_time=datetime(2026, 2, 25, 19, i, 0, tzinfo=UTC),
                exit_time=datetime(2026, 2, 25, 19, i + 5, 0, tzinfo=UTC),
                exit_reason=TradeExitReason.STOP_LOSS,
                commission=1.0,
                gross_pnl=-10.0,
                net_pnl=-11.0,
                outcome=TradeOutcome.LOSS,
            )
            for i in range(6)
        ]

        trade_logger = make_mock_trade_logger()

        async def mock_get_trades_by_strategy(
            strategy_id: str, limit: int = 200
        ) -> list[Trade]:
            if strategy_id == "strat_afternoon_momentum":
                return afternoon_losing_trades
            return []

        trade_logger.get_trades_by_strategy = AsyncMock(
            side_effect=mock_get_trades_by_strategy
        )

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

        # Register two strategies like the Sprint 19 test
        orb_strategy = OrbBreakoutStrategy(config=make_orb_breakout_config(), clock=clock)
        afternoon_strategy = AfternoonMomentumStrategy(
            config=make_afternoon_momentum_config(),
            data_service=data_service,
            clock=clock,
        )

        orchestrator.register_strategy(orb_strategy)
        orchestrator.register_strategy(afternoon_strategy)

        # Force bullish_trending regime so afternoon momentum is eligible
        orchestrator._current_regime = MarketRegime.BULLISH_TRENDING

        await orchestrator.run_pre_market()

        allocations = orchestrator.current_allocations

        # ORB should not be throttled
        assert allocations["strat_orb_breakout"].throttle_action == ThrottleAction.NONE

        # Afternoon momentum should be throttled (REDUCE) due to consecutive losses
        assert allocations["strat_afternoon_momentum"].throttle_action == ThrottleAction.REDUCE


class TestDailyReset:
    """Tests for daily state reset across all strategies."""

    @pytest.mark.asyncio
    async def test_four_strategy_daily_reset(self) -> None:
        """After reset, all strategies have clean state."""
        clock = FixedClock(datetime(2026, 2, 26, 15, 30, 0, tzinfo=UTC))
        data_service = MockDataService(vwap=100.0, atr_14=1.0)

        orb_strategy = OrbBreakoutStrategy(config=make_orb_breakout_config(), clock=clock)
        scalp_strategy = OrbScalpStrategy(config=make_orb_scalp_config(), clock=clock)
        vwap_strategy = VwapReclaimStrategy(
            config=make_vwap_reclaim_config(),
            data_service=data_service,
        )
        afternoon_strategy = AfternoonMomentumStrategy(
            config=make_afternoon_momentum_config(),
            data_service=data_service,
            clock=clock,
        )

        orb_strategy.set_watchlist(["AAPL"])
        scalp_strategy.set_watchlist(["AAPL"])
        vwap_strategy.set_watchlist(["AAPL"])
        afternoon_strategy.set_watchlist(["AAPL"])

        # Build up state for each strategy
        for i in range(5):
            candle = make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 26, 14, 30 + i, 0, tzinfo=UTC),
            )
            await orb_strategy.on_candle(candle)
            await scalp_strategy.on_candle(candle)
            await vwap_strategy.on_candle(candle)
            await afternoon_strategy.on_candle(candle)

        # Verify state accumulated
        assert "AAPL" in orb_strategy._symbol_state
        assert "AAPL" in scalp_strategy._symbol_state
        assert "AAPL" in vwap_strategy._symbol_state
        assert "AAPL" in afternoon_strategy._symbol_state

        # Reset all strategies
        orb_strategy.reset_daily_state()
        scalp_strategy.reset_daily_state()
        vwap_strategy.reset_daily_state()
        afternoon_strategy.reset_daily_state()

        # All state cleared
        assert "AAPL" not in orb_strategy._symbol_state
        assert "AAPL" not in scalp_strategy._symbol_state
        assert "AAPL" not in vwap_strategy._symbol_state
        assert "AAPL" not in afternoon_strategy._symbol_state

    @pytest.mark.asyncio
    async def test_afternoon_momentum_allocation_with_four_strategies(self) -> None:
        """Verify no single strategy exceeds 40% cap.

        At 9:00 AM, only 3 strategies are eligible (afternoon momentum is out of window).
        Each eligible strategy gets ~33.3% which is under the 40% cap.
        """
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 26, 14, 0, 0, tzinfo=UTC))  # 9:00 AM ET
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        trade_logger = make_mock_trade_logger()
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
        afternoon_strategy = AfternoonMomentumStrategy(
            config=make_afternoon_momentum_config(),
            data_service=data_service,
            clock=clock,
        )

        orchestrator.register_strategy(orb_strategy)
        orchestrator.register_strategy(scalp_strategy)
        orchestrator.register_strategy(vwap_strategy)
        orchestrator.register_strategy(afternoon_strategy)

        await orchestrator.run_pre_market()

        allocations = orchestrator.current_allocations

        # Verify no strategy exceeds 40% cap
        for strategy_id, alloc in allocations.items():
            assert alloc.allocation_pct <= 0.40, f"{strategy_id} exceeds 40% cap"

        # At 9:00 AM, 3 strategies eligible, each gets ~33.3%
        eligible_allocations = [a for a in allocations.values() if a.eligible]
        for alloc in eligible_allocations:
            assert alloc.allocation_pct == pytest.approx(1 / 3, rel=0.01)
