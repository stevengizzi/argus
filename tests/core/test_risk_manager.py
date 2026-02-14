"""Tests for the Risk Manager."""

from datetime import date, datetime, timedelta

import pytest

from argus.core.config import (
    AccountRiskConfig,
    AccountType,
    CrossStrategyRiskConfig,
    PDTConfig,
    RiskConfig,
)
from argus.core.event_bus import EventBus
from argus.core.events import (
    CircuitBreakerEvent,
    OrderApprovedEvent,
    OrderRejectedEvent,
    PositionClosedEvent,
    Side,
    SignalEvent,
)
from argus.core.risk_manager import PDTTracker, RiskManager
from argus.execution.simulated_broker import SimulatedBroker
from argus.models.trading import Order, OrderSide


def make_signal(
    symbol: str = "AAPL",
    side: Side = Side.LONG,
    entry_price: float = 150.0,
    stop_price: float = 147.0,
    share_count: int = 100,
    strategy_id: str = "strat_orb_breakout",
    target_prices: tuple[float, ...] | None = None,
) -> SignalEvent:
    """Create a SignalEvent for testing."""
    return SignalEvent(
        strategy_id=strategy_id,
        symbol=symbol,
        side=side,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=target_prices or (153.0, 156.0),
        share_count=share_count,
        rationale="Test signal",
    )


def make_risk_config(
    daily_loss_limit_pct: float = 0.03,
    weekly_loss_limit_pct: float = 0.05,
    cash_reserve_pct: float = 0.20,
    max_concurrent_positions: int = 10,
    pdt_enabled: bool = True,
    pdt_threshold: float = 25000.0,
) -> RiskConfig:
    """Create a RiskConfig for testing."""
    return RiskConfig(
        account=AccountRiskConfig(
            daily_loss_limit_pct=daily_loss_limit_pct,
            weekly_loss_limit_pct=weekly_loss_limit_pct,
            cash_reserve_pct=cash_reserve_pct,
            max_concurrent_positions=max_concurrent_positions,
        ),
        cross_strategy=CrossStrategyRiskConfig(),
        pdt=PDTConfig(
            enabled=pdt_enabled,
            account_type=AccountType.MARGIN,
            threshold_balance=pdt_threshold,
        ),
    )


class TestPDTTracker:
    """Tests for the PDTTracker."""

    def test_day_trades_remaining_under_threshold(self) -> None:
        """Under threshold, should have 3 day trades available."""
        tracker = PDTTracker(account_type="margin", threshold_balance=25000)
        remaining = tracker.day_trades_remaining(date.today(), 20000)
        assert remaining == 3

    def test_day_trades_remaining_above_threshold(self) -> None:
        """Above threshold, should have unlimited day trades."""
        tracker = PDTTracker(account_type="margin", threshold_balance=25000)
        remaining = tracker.day_trades_remaining(date.today(), 30000)
        assert remaining == 999

    def test_day_trades_remaining_cash_account(self) -> None:
        """Cash account should have unlimited day trades."""
        tracker = PDTTracker(account_type="cash", threshold_balance=25000)
        remaining = tracker.day_trades_remaining(date.today(), 10000)
        assert remaining == 999

    def test_record_day_trade_decrements_remaining(self) -> None:
        """Recording a day trade should decrement remaining."""
        tracker = PDTTracker(account_type="margin", threshold_balance=25000)
        tracker.record_day_trade(date.today())
        remaining = tracker.day_trades_remaining(date.today(), 20000)
        assert remaining == 2

    def test_day_trades_prune_after_5_business_days(self) -> None:
        """Day trades older than 5 business days should be pruned."""
        tracker = PDTTracker(account_type="margin", threshold_balance=25000)

        # Record a trade 7 calendar days ago (at least 5 business days)
        old_date = date.today() - timedelta(days=10)
        tracker.record_day_trade(old_date)

        remaining = tracker.day_trades_remaining(date.today(), 20000)
        assert remaining == 3  # Old trade pruned


class TestRiskManagerApproval:
    """Tests for signal approval scenarios."""

    @pytest.mark.asyncio
    async def test_valid_signal_approved_no_modifications(self) -> None:
        """Valid signal within all limits should be approved without modifications."""
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config()

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()

        signal = make_signal(share_count=100, entry_price=150.0)
        result = await rm.evaluate_signal(signal)

        assert isinstance(result, OrderApprovedEvent)
        assert result.modifications is None

    @pytest.mark.asyncio
    async def test_signal_approved_with_reduced_shares_cash_reserve(self) -> None:
        """Signal exceeding cash reserve should be approved with reduced shares."""
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config(cash_reserve_pct=0.20)

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()

        # Available after reserve: 100K * 0.80 = 80K
        # Signal wants 600 shares at 150 = 90K (exceeds)
        # Reduced: int(80000/150) = 533
        signal = make_signal(share_count=600, entry_price=150.0, stop_price=147.0)
        result = await rm.evaluate_signal(signal)

        assert isinstance(result, OrderApprovedEvent)
        assert result.modifications is not None
        assert result.modifications["share_count"] == 533


class TestRiskManagerRejection:
    """Tests for signal rejection scenarios."""

    @pytest.mark.asyncio
    async def test_signal_rejected_when_circuit_breaker_active(self) -> None:
        """Signal should be rejected when circuit breaker is active."""
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config()

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()
        rm._circuit_breaker_active = True

        result = await rm.evaluate_signal(make_signal())

        assert isinstance(result, OrderRejectedEvent)
        assert "circuit breaker" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_signal_rejected_daily_loss_limit(self) -> None:
        """Signal should be rejected when daily loss limit is reached."""
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config(daily_loss_limit_pct=0.03)

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()
        rm._daily_realized_pnl = -3000.0  # 3% of 100K

        result = await rm.evaluate_signal(make_signal())

        assert isinstance(result, OrderRejectedEvent)
        assert "daily loss limit" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_daily_loss_limit_triggers_circuit_breaker(self) -> None:
        """Hitting daily loss limit should trigger circuit breaker."""
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config(daily_loss_limit_pct=0.03)

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()
        rm._daily_realized_pnl = -3000.0

        # Track circuit breaker events
        breaker_events: list[CircuitBreakerEvent] = []
        bus.subscribe(CircuitBreakerEvent, lambda e: breaker_events.append(e))

        await rm.evaluate_signal(make_signal())
        await bus.drain()

        assert rm.circuit_breaker_active is True
        assert len(breaker_events) == 1
        assert breaker_events[0].level.value == "account"

    @pytest.mark.asyncio
    async def test_signal_rejected_weekly_loss_limit(self) -> None:
        """Signal should be rejected when weekly loss limit is reached."""
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config(weekly_loss_limit_pct=0.05)

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()
        rm._weekly_realized_pnl = -5000.0  # 5% of 100K

        result = await rm.evaluate_signal(make_signal())

        assert isinstance(result, OrderRejectedEvent)
        assert "weekly loss limit" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_signal_rejected_max_concurrent_positions(self) -> None:
        """Signal should be rejected when max positions reached."""
        broker = SimulatedBroker(initial_cash=500_000)
        await broker.connect()

        # Fill broker with 10 positions
        for i in range(10):
            order = Order(
                strategy_id="test",
                symbol=f"SYM{i}",
                side=OrderSide.BUY,
                quantity=10,
                limit_price=100.0,
            )
            await broker.place_order(order)

        bus = EventBus()
        config = make_risk_config(max_concurrent_positions=10)

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()

        result = await rm.evaluate_signal(make_signal(symbol="NEWSTOCK"))

        assert isinstance(result, OrderRejectedEvent)
        assert "concurrent positions" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_signal_rejected_below_025r_floor(self) -> None:
        """Signal should be rejected if reduced below 0.25R floor."""
        # Start with 20K, deploy most of it
        broker = SimulatedBroker(initial_cash=20_000)
        await broker.connect()

        # Deploy most cash: buy 190 shares at 100 = 19000, leaving 1000
        order = Order(
            strategy_id="test",
            symbol="SPY",
            side=OrderSide.BUY,
            quantity=190,
            limit_price=100.0,
        )
        await broker.place_order(order)

        bus = EventBus()
        config = make_risk_config(cash_reserve_pct=0.20)  # Reserve = 4000

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()

        # Available = cash - reserve = 1000 - 4000 = -3000 (negative)
        # Should reject due to cash reserve violation
        signal = make_signal(share_count=100, entry_price=150.0)
        result = await rm.evaluate_signal(signal)

        assert isinstance(result, OrderRejectedEvent)

    @pytest.mark.asyncio
    async def test_signal_rejected_pdt_limit(self) -> None:
        """Signal should be rejected when PDT limit is reached."""
        broker = SimulatedBroker(initial_cash=20_000)  # Under PDT threshold
        await broker.connect()
        bus = EventBus()
        config = make_risk_config(pdt_enabled=True, pdt_threshold=25000)

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()

        # Use up all 3 day trades
        rm._pdt_tracker.record_day_trade(date.today())
        rm._pdt_tracker.record_day_trade(date.today())
        rm._pdt_tracker.record_day_trade(date.today())

        result = await rm.evaluate_signal(make_signal())

        assert isinstance(result, OrderRejectedEvent)
        assert "pdt" in result.reason.lower()


class TestRiskManagerEventHandling:
    """Tests for event-driven P&L tracking."""

    @pytest.mark.asyncio
    async def test_position_closed_updates_daily_pnl(self) -> None:
        """PositionClosedEvent should update daily P&L."""
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config()

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()

        # Publish a position closed event
        event = PositionClosedEvent(
            position_id="test",
            exit_price=155.0,
            realized_pnl=500.0,
        )
        await bus.publish(event)
        await bus.drain()

        assert rm.daily_realized_pnl == 500.0
        assert rm.weekly_realized_pnl == 500.0

    @pytest.mark.asyncio
    async def test_position_closed_same_day_records_day_trade(self) -> None:
        """Same-day round trip should be recorded as day trade."""
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config()

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()

        now = datetime.now()
        event = PositionClosedEvent(
            position_id="test",
            exit_price=155.0,
            realized_pnl=500.0,
            entry_time=now,
            exit_time=now,
        )
        await bus.publish(event)
        await bus.drain()

        # Check PDT tracker recorded the day trade
        remaining = rm.pdt_tracker.day_trades_remaining(date.today(), 20000)
        assert remaining == 2  # 3 - 1 = 2


class TestRiskManagerStateManagement:
    """Tests for state reset and reconstruction."""

    @pytest.mark.asyncio
    async def test_reset_daily_state_clears_counters(self) -> None:
        """Reset should clear daily counters."""
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config()

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()

        rm._daily_realized_pnl = -1000.0
        rm._trades_today = 5
        rm._circuit_breaker_active = True

        rm.reset_daily_state()

        assert rm.daily_realized_pnl == 0.0
        assert rm.trades_today == 0
        assert rm.circuit_breaker_active is False


class TestRiskManagerIntegrityCheck:
    """Tests for daily integrity checks."""

    @pytest.mark.asyncio
    async def test_integrity_check_passes_normal_state(self) -> None:
        """Integrity check should pass with normal account state."""
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config()

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()

        report = await rm.daily_integrity_check()

        assert report.passed is True
        assert len(report.issues) == 0
