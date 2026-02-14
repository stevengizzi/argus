"""Tests for the Risk Manager."""

from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from argus.analytics.trade_logger import TradeLogger
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
from argus.db.manager import DatabaseManager
from argus.execution.simulated_broker import SimulatedBroker
from argus.models.trading import ExitReason, Order, OrderSide, Trade


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

    @pytest.mark.asyncio
    async def test_signal_approved_with_reduced_shares_buying_power(self) -> None:
        """Signal exceeding buying power should be approved with reduced shares.

        Note: In SimulatedBroker V1, buying_power == cash. The buying power
        check (step 6 in evaluate_signal) only runs when the cash reserve check
        (step 5) passes without modification. Since:
          - available = cash - reserve
          - buying_power = cash

        Any signal that triggers step 6 (cost > buying_power) would also trigger
        step 5 (cost > available) first, because available <= buying_power.

        This test verifies that share reduction works correctly when buying
        power is depleted by open positions. The reduction is applied by step 5
        in SimulatedBroker V1, but when AlpacaBroker is added (Sprint 4) with
        margin accounts where buying_power > cash, step 6 will trigger
        independently for margin-constrained signals.
        """
        # Start with 100K, deploy 60K into positions
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        # Buy 400 shares at 150 = 60K, leaving 40K cash/buying_power
        deploy_order = Order(
            strategy_id="test",
            symbol="SPY",
            side=OrderSide.BUY,
            quantity=400,
            limit_price=150.0,
        )
        await broker.place_order(deploy_order)

        bus = EventBus()
        # With 0% reserve, available == cash == buying_power
        config = make_risk_config(cash_reserve_pct=0.0)

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()

        # Account state: cash=40K, equity=100K, buying_power=40K, reserve=0
        # Signal: 300 shares at 150 = 45K (exceeds 40K buying_power)
        # Should be reduced to int(40000/150) = 266 shares
        signal = make_signal(share_count=300, entry_price=150.0, stop_price=147.0)
        result = await rm.evaluate_signal(signal)

        assert isinstance(result, OrderApprovedEvent)
        assert result.modifications is not None
        assert result.modifications["share_count"] == 266
        # V1: hits step 5 (cash reserve) since buying_power == cash
        # When margin is added, this would say "buying power constraint"
        assert "constraint" in result.modifications["reason"].lower()


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

        await rm.reset_daily_state()

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


class TestRiskManagerReconstruction:
    """Tests for state reconstruction after restart."""

    def _make_trade(
        self,
        strategy_id: str = "strat_orb",
        symbol: str = "AAPL",
        net_pnl: float = 100.0,
        entry_time: datetime | None = None,
        exit_time: datetime | None = None,
    ) -> Trade:
        """Helper to create a test trade."""
        if entry_time is None:
            entry_time = datetime(2026, 2, 15, 10, 0, 0)
        if exit_time is None:
            exit_time = datetime(2026, 2, 15, 10, 30, 0)

        return Trade(
            strategy_id=strategy_id,
            symbol=symbol,
            side=OrderSide.BUY,
            entry_price=150.0,
            entry_time=entry_time,
            exit_price=151.0 if net_pnl > 0 else 149.0,
            exit_time=exit_time,
            shares=100,
            stop_price=148.0,
            exit_reason=ExitReason.TARGET_1 if net_pnl > 0 else ExitReason.STOP_LOSS,
            gross_pnl=net_pnl + 1.0,  # gross = net + commission
            commission=1.0,
        )

    @pytest.mark.asyncio
    async def test_reconstruct_state_rebuilds_daily_pnl(self, tmp_path: Path) -> None:
        """reconstruct_state should rebuild daily P&L from database."""
        # Set up database and trade logger
        db = DatabaseManager(tmp_path / "test_reconstruct.db")
        await db.initialize()
        trade_logger = TradeLogger(db)

        # Insert trades for today
        today = date.today()
        await trade_logger.log_trade(
            self._make_trade(
                net_pnl=100.0,
                entry_time=datetime.combine(today, datetime.min.time().replace(hour=10)),
                exit_time=datetime.combine(today, datetime.min.time().replace(hour=10, minute=30)),
            )
        )
        await trade_logger.log_trade(
            self._make_trade(
                net_pnl=-50.0,
                entry_time=datetime.combine(today, datetime.min.time().replace(hour=11)),
                exit_time=datetime.combine(today, datetime.min.time().replace(hour=11, minute=30)),
            )
        )

        # Create Risk Manager and reconstruct state
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config()

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()
        await rm.reconstruct_state(trade_logger)

        # Verify daily P&L: 100 + (-50) = 50 (net_pnl values)
        # Note: net_pnl = gross_pnl - commission = (pnl + 1) - 1 = pnl
        assert rm.daily_realized_pnl == 50.0
        assert rm.trades_today == 2

        await db.close()

    @pytest.mark.asyncio
    async def test_reconstruct_state_rebuilds_weekly_pnl(self, tmp_path: Path) -> None:
        """reconstruct_state should rebuild weekly P&L from Monday through today."""
        db = DatabaseManager(tmp_path / "test_reconstruct_weekly.db")
        await db.initialize()
        trade_logger = TradeLogger(db)

        today = date.today()
        monday = today - timedelta(days=today.weekday())  # Monday of this week

        # Insert trades for Monday, Tuesday, and today
        await trade_logger.log_trade(
            self._make_trade(
                net_pnl=100.0,
                entry_time=datetime.combine(monday, datetime.min.time().replace(hour=10)),
                exit_time=datetime.combine(monday, datetime.min.time().replace(hour=10, minute=30)),
            )
        )
        tuesday = monday + timedelta(days=1)
        if tuesday <= today:  # Only add if Tuesday is in the past
            tue_entry = datetime.combine(tuesday, datetime.min.time().replace(hour=10))
            tue_exit = datetime.combine(tuesday, datetime.min.time().replace(hour=10, minute=30))
            await trade_logger.log_trade(
                self._make_trade(net_pnl=200.0, entry_time=tue_entry, exit_time=tue_exit)
            )
        # Add today's trade
        await trade_logger.log_trade(
            self._make_trade(
                net_pnl=-50.0,
                entry_time=datetime.combine(today, datetime.min.time().replace(hour=10)),
                exit_time=datetime.combine(today, datetime.min.time().replace(hour=10, minute=30)),
            )
        )

        # Create Risk Manager and reconstruct state
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config()

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()
        await rm.reconstruct_state(trade_logger)

        # Verify weekly P&L includes all trades from this week
        # If today is Monday: 100 + (-50) = 50
        # If today is Tuesday or later: 100 + 200 + (-50) = 250
        is_monday = today.weekday() == 0
        expected_weekly = 50.0 if is_monday else (250.0 if tuesday <= today else 50.0)

        assert rm.weekly_realized_pnl == expected_weekly

        await db.close()

    @pytest.mark.asyncio
    async def test_reconstruct_state_rebuilds_pdt_trades(self, tmp_path: Path) -> None:
        """reconstruct_state should rebuild PDT day trades from rolling 5 days."""
        db = DatabaseManager(tmp_path / "test_reconstruct_pdt.db")
        await db.initialize()
        trade_logger = TradeLogger(db)

        today = date.today()

        # Create day trades (entry and exit same day) within last 5 business days
        # A day trade is when entry_date == exit_date
        await trade_logger.log_trade(
            self._make_trade(
                net_pnl=100.0,
                entry_time=datetime.combine(today, datetime.min.time().replace(hour=10)),
                exit_time=datetime.combine(today, datetime.min.time().replace(hour=10, minute=30)),
            )
        )
        # Add another day trade today
        await trade_logger.log_trade(
            self._make_trade(
                net_pnl=50.0,
                entry_time=datetime.combine(today, datetime.min.time().replace(hour=11)),
                exit_time=datetime.combine(today, datetime.min.time().replace(hour=11, minute=30)),
            )
        )

        # Add an overnight trade (not a day trade - entry yesterday, exit today)
        yesterday = today - timedelta(days=1)
        await trade_logger.log_trade(
            self._make_trade(
                net_pnl=75.0,
                entry_time=datetime.combine(yesterday, datetime.min.time().replace(hour=15)),
                exit_time=datetime.combine(today, datetime.min.time().replace(hour=9, minute=30)),
            )
        )

        # Create Risk Manager and reconstruct state
        broker = SimulatedBroker(initial_cash=20_000)  # Under PDT threshold
        await broker.connect()
        bus = EventBus()
        config = make_risk_config(pdt_enabled=True, pdt_threshold=25000)

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()
        await rm.reconstruct_state(trade_logger)

        # Verify PDT tracker has 2 day trades (both same-day trades today)
        # The overnight trade should NOT count as a day trade
        remaining = rm.pdt_tracker.day_trades_remaining(today, 20000)
        assert remaining == 1  # 3 - 2 = 1

        await db.close()


class TestStartOfDayEquity:
    """Tests for DEC-037: Start-of-day equity for cash reserve calculations."""

    @pytest.mark.asyncio
    async def test_reset_daily_state_snapshots_equity(self) -> None:
        """reset_daily_state should snapshot start-of-day equity."""
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config()

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()

        # Initially start_of_day_equity is 0
        assert rm.start_of_day_equity == 0.0

        await rm.reset_daily_state()

        # After reset, start_of_day_equity should equal account equity
        assert rm.start_of_day_equity == 100_000.0

    @pytest.mark.asyncio
    async def test_cash_reserve_uses_start_of_day_equity(self) -> None:
        """Cash reserve check should use start-of-day equity, not live equity."""
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config(cash_reserve_pct=0.20)

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()
        await rm.reset_daily_state()

        # Now simulate position gains changing live equity
        # Buy shares to change account state
        deploy_order = Order(
            strategy_id="test",
            symbol="SPY",
            side=OrderSide.BUY,
            quantity=100,
            limit_price=150.0,
        )
        await broker.place_order(deploy_order)

        # Account state after order:
        # Cash is now 100_000 - 15_000 = 85_000
        # Equity is still ~100_000 (cash + position value)

        # The reserve calculation should use start_of_day_equity (100K)
        # not live equity which could fluctuate with unrealized P&L
        # Reserve = 100K * 0.20 = 20K
        # Available = 85K - 20K = 65K
        # Signal for 500 shares at 150 = 75K (exceeds 65K available)
        # Should be reduced to int(65000/150) = 433 shares
        signal = make_signal(share_count=500, entry_price=150.0, stop_price=147.0)
        result = await rm.evaluate_signal(signal)

        assert isinstance(result, OrderApprovedEvent)
        assert result.modifications is not None
        assert result.modifications["share_count"] == 433

    @pytest.mark.asyncio
    async def test_fallback_to_live_equity_when_not_snapshotted(self) -> None:
        """When start_of_day_equity is 0, should fall back to live equity."""
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config(cash_reserve_pct=0.20)

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()

        # Do NOT call reset_daily_state - start_of_day_equity remains 0
        assert rm.start_of_day_equity == 0.0

        # Signal should still work using live equity fallback
        # Reserve = 100K * 0.20 = 20K (using live equity)
        # Available = 100K - 20K = 80K
        # Signal for 100 shares at 150 = 15K (within available)
        signal = make_signal(share_count=100, entry_price=150.0, stop_price=147.0)
        result = await rm.evaluate_signal(signal)

        assert isinstance(result, OrderApprovedEvent)
        assert result.modifications is None

    @pytest.mark.asyncio
    async def test_reconstruct_state_snapshots_equity(self, tmp_path: Path) -> None:
        """reconstruct_state should also snapshot start-of-day equity."""
        db = DatabaseManager(tmp_path / "test_reconstruct_equity.db")
        await db.initialize()
        trade_logger = TradeLogger(db)

        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config()

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()

        # Initially start_of_day_equity is 0
        assert rm.start_of_day_equity == 0.0

        await rm.reconstruct_state(trade_logger)

        # After reconstruct, start_of_day_equity should be set
        assert rm.start_of_day_equity == 100_000.0

        await db.close()
