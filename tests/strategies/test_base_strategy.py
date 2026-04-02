"""Tests for the BaseStrategy ABC."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from argus.analytics.trade_logger import TradeLogger
from argus.core.clock import Clock, FixedClock
from argus.core.config import StrategyConfig, StrategyRiskLimits
from argus.core.events import CandleEvent, Side, SignalEvent, TickEvent
from argus.db.manager import DatabaseManager
from argus.models.strategy import (
    ExitRules,
    MarketConditionsFilter,
    ProfitTarget,
    ScannerCriteria,
)
from argus.models.trading import ExitReason, OrderSide, Trade
from argus.strategies.base_strategy import BaseStrategy


class ConcreteTestStrategy(BaseStrategy):
    """Minimal concrete implementation of BaseStrategy for testing."""

    def __init__(self, config: StrategyConfig, clock: Clock | None = None) -> None:
        super().__init__(config, clock)
        self._last_signal: SignalEvent | None = None

    async def on_candle(self, event: CandleEvent) -> SignalEvent | None:
        """Return a signal if symbol is in watchlist and price > 100."""
        if event.symbol not in self._watchlist:
            return None
        if event.close > 100:
            return SignalEvent(
                strategy_id=self.strategy_id,
                symbol=event.symbol,
                side=Side.LONG,
                entry_price=event.close,
                stop_price=event.close * 0.98,
                target_prices=(event.close * 1.02, event.close * 1.04),
                share_count=self.calculate_position_size(event.close, event.close * 0.98),
                rationale="Test signal",
            )
        return None

    async def on_tick(self, event: TickEvent) -> None:
        """No-op for test strategy."""
        pass

    def get_scanner_criteria(self) -> ScannerCriteria:
        """Return basic scanner criteria."""
        return ScannerCriteria(
            min_price=10.0,
            max_price=200.0,
            min_volume_avg_daily=1_000_000,
        )

    def calculate_position_size(self, entry_price: float, stop_price: float) -> int:
        """Calculate position size using risk formula."""
        if entry_price <= stop_price:
            return 0  # Invalid for longs
        if self._allocated_capital <= 0:
            return 0

        risk_per_share = entry_price - stop_price
        risk_dollars = self._allocated_capital * self._config.risk_limits.max_loss_per_trade_pct
        shares = int(risk_dollars / risk_per_share)
        return max(0, shares)

    def get_exit_rules(self) -> ExitRules:
        """Return basic exit rules."""
        return ExitRules(
            stop_type="fixed",
            stop_price_func="midpoint",
            targets=[
                ProfitTarget(r_multiple=1.0, position_pct=0.5),
                ProfitTarget(r_multiple=2.0, position_pct=0.5),
            ],
            time_stop_minutes=30,
        )

    def get_market_conditions_filter(self) -> MarketConditionsFilter:
        """Return basic market conditions."""
        return MarketConditionsFilter(
            allowed_regimes=["bullish_trending", "range_bound"],
            max_vix=35.0,
        )


def make_config(
    strategy_id: str = "test_strat",
    name: str = "Test Strategy",
    max_trades_per_day: int = 10,
    max_daily_loss_pct: float = 0.03,
    max_loss_per_trade_pct: float = 0.01,
) -> StrategyConfig:
    """Create a StrategyConfig for testing."""
    return StrategyConfig(
        strategy_id=strategy_id,
        name=name,
        risk_limits=StrategyRiskLimits(
            max_trades_per_day=max_trades_per_day,
            max_daily_loss_pct=max_daily_loss_pct,
            max_loss_per_trade_pct=max_loss_per_trade_pct,
        ),
    )


class TestBaseStrategyInstantiation:
    """Tests for strategy instantiation."""

    def test_concrete_strategy_can_be_instantiated(self) -> None:
        """Concrete strategy implementing all abstract methods can be created."""
        config = make_config()
        strategy = ConcreteTestStrategy(config)
        assert strategy.strategy_id == "test_strat"
        assert strategy.name == "Test Strategy"
        assert strategy.version == "1.0.0"

    def test_config_accessible(self) -> None:
        """Full config is accessible from strategy."""
        config = make_config()
        strategy = ConcreteTestStrategy(config)
        assert strategy.config.risk_limits.max_trades_per_day == 10


class TestBaseStrategyProperties:
    """Tests for strategy properties."""

    def test_allocated_capital_default_zero(self) -> None:
        """Allocated capital defaults to 0."""
        strategy = ConcreteTestStrategy(make_config())
        assert strategy.allocated_capital == 0.0

    def test_allocated_capital_setter(self) -> None:
        """Allocated capital can be set."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.allocated_capital = 50_000.0
        assert strategy.allocated_capital == 50_000.0

    def test_allocated_capital_negative_raises(self) -> None:
        """Negative allocated capital raises ValueError."""
        strategy = ConcreteTestStrategy(make_config())
        with pytest.raises(ValueError, match="negative"):
            strategy.allocated_capital = -1000.0

    def test_is_active_default_false(self) -> None:
        """Strategy is inactive by default."""
        strategy = ConcreteTestStrategy(make_config())
        assert strategy.is_active is False

    def test_is_active_setter(self) -> None:
        """Active status can be set."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.is_active = True
        assert strategy.is_active is True

    def test_daily_pnl_default_zero(self) -> None:
        """Daily P&L defaults to 0."""
        strategy = ConcreteTestStrategy(make_config())
        assert strategy.daily_pnl == 0.0

    def test_trade_count_today_default_zero(self) -> None:
        """Trade count defaults to 0."""
        strategy = ConcreteTestStrategy(make_config())
        assert strategy.trade_count_today == 0

    def test_watchlist_default_empty(self) -> None:
        """Watchlist defaults to empty."""
        strategy = ConcreteTestStrategy(make_config())
        assert strategy.watchlist == []


class TestResetDailyState:
    """Tests for reset_daily_state()."""

    def test_clears_daily_pnl(self) -> None:
        """reset_daily_state clears daily P&L."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.record_trade_result(500.0)
        assert strategy.daily_pnl == 500.0

        strategy.reset_daily_state()
        assert strategy.daily_pnl == 0.0

    def test_clears_trade_count(self) -> None:
        """reset_daily_state clears trade count."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.record_trade_result(100.0)
        strategy.record_trade_result(-50.0)
        assert strategy.trade_count_today == 2

        strategy.reset_daily_state()
        assert strategy.trade_count_today == 0

    def test_clears_watchlist(self) -> None:
        """reset_daily_state clears watchlist."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.set_watchlist(["AAPL", "MSFT"])
        assert len(strategy.watchlist) == 2

        strategy.reset_daily_state()
        assert strategy.watchlist == []

    def test_preserves_allocated_capital(self) -> None:
        """reset_daily_state does NOT clear allocated capital."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.allocated_capital = 50_000.0
        strategy.reset_daily_state()
        assert strategy.allocated_capital == 50_000.0


class TestCheckInternalRiskLimits:
    """Tests for check_internal_risk_limits()."""

    def test_returns_true_within_limits(self) -> None:
        """Returns True when within all limits."""
        strategy = ConcreteTestStrategy(make_config(max_trades_per_day=10))
        strategy.allocated_capital = 100_000.0
        assert strategy.check_internal_risk_limits() is True

    def test_returns_false_max_trades_reached(self) -> None:
        """Returns False when max trades per day is reached."""
        strategy = ConcreteTestStrategy(make_config(max_trades_per_day=3))
        for _ in range(3):
            strategy.record_trade_result(100.0)

        assert strategy.check_internal_risk_limits() is False

    def test_returns_false_max_daily_loss_reached(self) -> None:
        """Returns False when max daily loss percentage is reached."""
        strategy = ConcreteTestStrategy(make_config(max_daily_loss_pct=0.03))
        strategy.allocated_capital = 100_000.0

        # Lose 3% of allocated capital
        strategy.record_trade_result(-3000.0)

        assert strategy.check_internal_risk_limits() is False

    def test_winning_trades_dont_trigger_loss_limit(self) -> None:
        """Winning trades don't affect loss limit check."""
        strategy = ConcreteTestStrategy(make_config(max_daily_loss_pct=0.03))
        strategy.allocated_capital = 100_000.0
        strategy.record_trade_result(5000.0)  # Big win

        assert strategy.check_internal_risk_limits() is True


class TestPositionSizing:
    """Tests for calculate_position_size()."""

    def test_position_size_formula(self) -> None:
        """Position size uses correct formula: risk_dollars / risk_per_share."""
        config = make_config(max_loss_per_trade_pct=0.01)
        strategy = ConcreteTestStrategy(config)
        strategy.allocated_capital = 100_000.0

        # Entry: 150, Stop: 147, Risk per share: 3
        # Risk dollars: 100K * 1% = 1000
        # Shares: 1000 / 3 = 333
        shares = strategy.calculate_position_size(150.0, 147.0)
        assert shares == 333

    def test_position_size_zero_capital(self) -> None:
        """Returns 0 if no capital allocated."""
        strategy = ConcreteTestStrategy(make_config())
        shares = strategy.calculate_position_size(150.0, 147.0)
        assert shares == 0

    def test_position_size_invalid_stop(self) -> None:
        """Returns 0 if stop is above entry (invalid for longs)."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.allocated_capital = 100_000.0
        shares = strategy.calculate_position_size(150.0, 155.0)
        assert shares == 0


class TestWatchlist:
    """Tests for watchlist management."""

    def test_set_watchlist(self) -> None:
        """set_watchlist updates the watchlist."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.set_watchlist(["AAPL", "MSFT", "NVDA"])
        assert set(strategy.watchlist) == {"AAPL", "MSFT", "NVDA"}

    def test_watchlist_is_copy(self) -> None:
        """Watchlist property returns a copy."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.set_watchlist(["AAPL"])
        watchlist = strategy.watchlist
        watchlist.append("MSFT")  # Modify the copy
        assert "MSFT" not in strategy.watchlist  # Original unchanged

    def test_set_watchlist_stores_as_set(self) -> None:
        """set_watchlist stores symbols internally as a set."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.set_watchlist(["A", "B", "C"])
        assert isinstance(strategy._watchlist, set)
        assert strategy._watchlist == {"A", "B", "C"}

    def test_set_watchlist_accepts_list(self) -> None:
        """set_watchlist accepts list input without error."""
        strategy = ConcreteTestStrategy(make_config())
        symbols: list[str] = ["AAPL", "MSFT"]
        strategy.set_watchlist(symbols)
        assert set(strategy.watchlist) == {"AAPL", "MSFT"}

    def test_watchlist_property_returns_list(self) -> None:
        """watchlist property returns list[str], not set."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.set_watchlist(["AAPL", "MSFT"])
        result = strategy.watchlist
        assert isinstance(result, list)
        assert not isinstance(result, set)

    def test_set_watchlist_deduplicates(self) -> None:
        """set_watchlist deduplicates symbols via set conversion."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.set_watchlist(["A", "A", "B"])
        assert len(strategy.watchlist) == 2
        assert set(strategy.watchlist) == {"A", "B"}


class TestWatchlistOnCandle:
    """Tests for watchlist gating in on_candle()."""

    @pytest.mark.asyncio
    async def test_on_candle_passes_watchlisted_symbol(self) -> None:
        """Candle for a watchlisted symbol passes through the gate."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.allocated_capital = 100_000.0
        strategy.set_watchlist(["AAPL"])

        candle = CandleEvent(
            symbol="AAPL",
            timeframe="1m",
            open=105.0,
            high=110.0,
            low=104.0,
            close=108.0,
            volume=1_000_000,
        )
        signal = await strategy.on_candle(candle)
        # Signal returned (not None) means the watchlist gate was passed
        assert signal is not None
        assert signal.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_on_candle_rejects_non_watchlisted_symbol(self) -> None:
        """Candle for a non-watchlisted symbol returns None without processing."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.allocated_capital = 100_000.0
        strategy.set_watchlist(["MSFT"])

        candle = CandleEvent(
            symbol="AAPL",
            timeframe="1m",
            open=105.0,
            high=110.0,
            low=104.0,
            close=108.0,
            volume=1_000_000,
        )
        signal = await strategy.on_candle(candle)
        assert signal is None


class TestResetDailyStateClearsWatchlist:
    """Tests for watchlist clearing on reset."""

    def test_reset_daily_state_clears_watchlist(self) -> None:
        """After set_watchlist(), reset_daily_state() empties the watchlist."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.set_watchlist(["AAPL", "MSFT", "NVDA"])
        assert len(strategy.watchlist) == 3

        strategy.reset_daily_state()
        assert strategy.watchlist == []
        assert isinstance(strategy._watchlist, set)


class TestRecordTradeResult:
    """Tests for record_trade_result()."""

    def test_records_winning_trade(self) -> None:
        """Winning trade is recorded correctly."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.record_trade_result(500.0)
        assert strategy.daily_pnl == 500.0
        assert strategy.trade_count_today == 1

    def test_records_losing_trade(self) -> None:
        """Losing trade is recorded correctly."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.record_trade_result(-200.0)
        assert strategy.daily_pnl == -200.0
        assert strategy.trade_count_today == 1

    def test_accumulates_pnl(self) -> None:
        """Multiple trades accumulate P&L."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.record_trade_result(500.0)
        strategy.record_trade_result(-200.0)
        strategy.record_trade_result(300.0)
        assert strategy.daily_pnl == 600.0
        assert strategy.trade_count_today == 3


class TestOnCandle:
    """Tests for on_candle() implementation."""

    @pytest.mark.asyncio
    async def test_on_candle_returns_signal_when_criteria_met(self) -> None:
        """on_candle returns SignalEvent when criteria are met."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.allocated_capital = 100_000.0
        strategy.set_watchlist(["AAPL"])

        candle = CandleEvent(
            symbol="AAPL",
            timeframe="1m",
            open=105.0,
            high=110.0,
            low=104.0,
            close=108.0,
            volume=1_000_000,
        )
        signal = await strategy.on_candle(candle)

        assert signal is not None
        assert signal.symbol == "AAPL"
        assert signal.entry_price == 108.0
        assert signal.share_count > 0

    @pytest.mark.asyncio
    async def test_on_candle_returns_none_symbol_not_in_watchlist(self) -> None:
        """on_candle returns None if symbol not in watchlist."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.set_watchlist(["MSFT"])  # AAPL not in watchlist

        candle = CandleEvent(
            symbol="AAPL",
            timeframe="1m",
            open=105.0,
            high=110.0,
            low=104.0,
            close=108.0,
            volume=1_000_000,
        )
        signal = await strategy.on_candle(candle)

        assert signal is None

    @pytest.mark.asyncio
    async def test_on_candle_returns_none_criteria_not_met(self) -> None:
        """on_candle returns None if criteria not met."""
        strategy = ConcreteTestStrategy(make_config())
        strategy.set_watchlist(["AAPL"])

        # Price below 100 threshold
        candle = CandleEvent(
            symbol="AAPL",
            timeframe="1m",
            open=95.0,
            high=98.0,
            low=94.0,
            close=96.0,
            volume=1_000_000,
        )
        signal = await strategy.on_candle(candle)

        assert signal is None


class TestReconstructState:
    """Tests for reconstruct_state()."""

    def _make_trade(
        self,
        strategy_id: str,
        net_pnl: float,
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
            symbol="AAPL",
            side=OrderSide.BUY,
            entry_price=150.0,
            entry_time=entry_time,
            exit_price=151.0 if net_pnl > 0 else 149.0,
            exit_time=exit_time,
            shares=100,
            stop_price=148.0,
            exit_reason=ExitReason.TARGET_1 if net_pnl > 0 else ExitReason.STOP_LOSS,
            gross_pnl=net_pnl + 1.0,
            commission=1.0,
        )

    @pytest.mark.asyncio
    async def test_reconstruct_state_from_database(self, tmp_path: Path) -> None:
        """reconstruct_state rebuilds state from database."""
        from datetime import date

        # Use a fixed date to avoid timezone issues
        test_date = date(2026, 2, 16)
        clock = FixedClock(datetime(2026, 2, 16, 15, 0, 0, tzinfo=UTC))

        db = DatabaseManager(tmp_path / "test_reconstruct.db")
        await db.initialize()
        trade_logger = TradeLogger(db)

        # Insert trades for test_date
        await trade_logger.log_trade(
            self._make_trade(
                strategy_id="test_strat",
                net_pnl=100.0,
                entry_time=datetime.combine(test_date, datetime.min.time().replace(hour=10)),
                exit_time=datetime.combine(
                    test_date, datetime.min.time().replace(hour=10, minute=30)
                ),
            )
        )
        await trade_logger.log_trade(
            self._make_trade(
                strategy_id="test_strat",
                net_pnl=-50.0,
                entry_time=datetime.combine(test_date, datetime.min.time().replace(hour=11)),
                exit_time=datetime.combine(
                    test_date, datetime.min.time().replace(hour=11, minute=30)
                ),
            )
        )
        # Trade for different strategy (should be ignored)
        await trade_logger.log_trade(
            self._make_trade(
                strategy_id="other_strat",
                net_pnl=200.0,
                entry_time=datetime.combine(test_date, datetime.min.time().replace(hour=12)),
                exit_time=datetime.combine(
                    test_date, datetime.min.time().replace(hour=12, minute=30)
                ),
            )
        )

        # Create strategy with fixed clock and reconstruct state
        strategy = ConcreteTestStrategy(make_config(strategy_id="test_strat"), clock=clock)
        await strategy.reconstruct_state(trade_logger)

        # Should only count trades for this strategy
        assert strategy.daily_pnl == 50.0  # 100 + (-50)
        assert strategy.trade_count_today == 2

        await db.close()


class TestWatchlistPopulatedFromUniverseManager:
    """Integration test: strategy watchlists populated from Universe Manager routing."""

    def test_watchlist_populated_from_universe_manager(self) -> None:
        """Simulates the main.py startup path: build routing table, then populate watchlists."""
        # Create strategies
        orb = ConcreteTestStrategy(make_config(strategy_id="orb_breakout", name="ORB Breakout"))
        vwap = ConcreteTestStrategy(make_config(strategy_id="vwap_reclaim", name="VWAP Reclaim"))
        strategies = {"orb_breakout": orb, "vwap_reclaim": vwap}

        # Simulate UM routing table: maps strategy_id -> set of symbols
        um_routing: dict[str, set[str]] = {
            "orb_breakout": {"AAPL", "MSFT", "NVDA"},
            "vwap_reclaim": {"TSLA", "AAPL"},
        }

        # Simulate the main.py loop that populates watchlists from UM
        for strategy_id, strategy in strategies.items():
            um_symbols = um_routing.get(strategy_id, set())
            strategy.set_watchlist(list(um_symbols), source="universe_manager")

        # Verify each strategy's watchlist matches UM routing
        assert set(orb.watchlist) == {"AAPL", "MSFT", "NVDA"}
        assert set(vwap.watchlist) == {"TSLA", "AAPL"}
        assert isinstance(orb.watchlist, list)
        assert isinstance(vwap.watchlist, list)


class TestWindowSummary:
    """Tests for _log_window_summary() and related window tracking (Sprint 32.75 S5)."""

    def test_log_window_summary_format(self, caplog) -> None:
        """_log_window_summary logs correct format at INFO level."""
        import logging

        strategy = ConcreteTestStrategy(make_config(name="Test Strategy"))
        strategy._window_symbols_evaluated = 12
        strategy._window_signals_generated = 3
        strategy._window_signals_rejected = 2
        strategy._window_rejection_reasons = {"no_volume": 1, "outside_window": 1}

        with caplog.at_level(logging.INFO):
            strategy._log_window_summary()

        assert len(caplog.records) == 1
        msg = caplog.records[0].message
        assert "Test Strategy" in msg
        assert "12 symbols evaluated" in msg
        assert "3 signals generated" in msg
        assert "2 rejected" in msg
        assert "no_volume=1" in msg
        assert "outside_window=1" in msg

    def test_log_window_summary_no_rejections(self, caplog) -> None:
        """_log_window_summary shows 'none' when no rejections recorded."""
        import logging

        strategy = ConcreteTestStrategy(make_config(name="Test Strategy"))
        strategy._window_symbols_evaluated = 5
        strategy._window_signals_generated = 2
        strategy._window_signals_rejected = 0

        with caplog.at_level(logging.INFO):
            strategy._log_window_summary()

        assert "none" in caplog.records[0].message

    def test_reset_daily_state_clears_window_counters(self) -> None:
        """reset_daily_state resets all window summary counters and the logged flag."""
        strategy = ConcreteTestStrategy(make_config())
        strategy._window_symbols_evaluated = 10
        strategy._window_signals_generated = 3
        strategy._window_signals_rejected = 1
        strategy._window_rejection_reasons = {"foo": 1}
        strategy._window_summary_logged = True

        strategy.reset_daily_state()

        assert strategy._window_symbols_evaluated == 0
        assert strategy._window_signals_generated == 0
        assert strategy._window_signals_rejected == 0
        assert strategy._window_rejection_reasons == {}
        assert strategy._window_summary_logged is False

    def test_maybe_log_window_summary_fires_once_after_latest_entry(self, caplog) -> None:
        """_maybe_log_window_summary fires exactly once when candle_time >= latest_entry."""
        import logging
        from datetime import time

        # Default latest_entry is "11:30" in OperatingWindow
        strategy = ConcreteTestStrategy(make_config())

        with caplog.at_level(logging.INFO):
            # Before window close — should not log
            strategy._maybe_log_window_summary(time(11, 0))
            assert len(caplog.records) == 0

            # At window close — should log once
            strategy._maybe_log_window_summary(time(11, 30))
            assert len(caplog.records) == 1

            # Again — should NOT log a second time
            strategy._maybe_log_window_summary(time(11, 45))
            assert len(caplog.records) == 1

    def test_track_helpers_increment_counters(self) -> None:
        """_track_symbol_evaluated, _track_signal_generated, _track_signal_rejected work."""
        strategy = ConcreteTestStrategy(make_config())

        strategy._track_symbol_evaluated()
        strategy._track_symbol_evaluated()
        strategy._track_signal_generated()
        strategy._track_signal_rejected("no_volume")
        strategy._track_signal_rejected("no_volume")
        strategy._track_signal_rejected("outside_window")

        assert strategy._window_symbols_evaluated == 2
        assert strategy._window_signals_generated == 1
        assert strategy._window_signals_rejected == 3
        assert strategy._window_rejection_reasons == {"no_volume": 2, "outside_window": 1}
