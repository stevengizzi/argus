"""Tests for the ORB Breakout Strategy."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from argus.core.config import OperatingWindow, OrbBreakoutConfig, StrategyRiskLimits
from argus.core.events import CandleEvent, Side, SignalEvent
from argus.strategies.orb_breakout import OrbBreakoutStrategy


def make_orb_config(
    strategy_id: str = "strat_orb_breakout",
    orb_window_minutes: int = 15,
    volume_threshold_rvol: float = 2.0,
    target_1_r: float = 1.0,
    target_2_r: float = 2.0,
    time_stop_minutes: int = 30,
    min_range_atr_ratio: float = 0.5,
    max_range_atr_ratio: float = 2.0,
    chase_protection_pct: float = 0.005,
    breakout_volume_multiplier: float = 1.5,
    max_trades_per_day: int = 6,
    max_daily_loss_pct: float = 0.03,
    max_loss_per_trade_pct: float = 0.01,
    max_concurrent_positions: int = 2,
    latest_entry: str = "11:30",
) -> OrbBreakoutConfig:
    """Create an OrbBreakoutConfig for testing."""
    return OrbBreakoutConfig(
        strategy_id=strategy_id,
        name="ORB Breakout",
        orb_window_minutes=orb_window_minutes,
        volume_threshold_rvol=volume_threshold_rvol,
        target_1_r=target_1_r,
        target_2_r=target_2_r,
        time_stop_minutes=time_stop_minutes,
        min_range_atr_ratio=min_range_atr_ratio,
        max_range_atr_ratio=max_range_atr_ratio,
        chase_protection_pct=chase_protection_pct,
        breakout_volume_multiplier=breakout_volume_multiplier,
        risk_limits=StrategyRiskLimits(
            max_trades_per_day=max_trades_per_day,
            max_daily_loss_pct=max_daily_loss_pct,
            max_loss_per_trade_pct=max_loss_per_trade_pct,
            max_concurrent_positions=max_concurrent_positions,
        ),
        operating_window=OperatingWindow(latest_entry=latest_entry),
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
        timestamp = datetime(2026, 2, 15, 9, 30, 0, tzinfo=UTC)
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


def make_or_candles(
    symbol: str = "AAPL",
    num_candles: int = 15,
    base_time: datetime | None = None,
    or_high: float = 101.0,
    or_low: float = 99.0,
) -> list[CandleEvent]:
    """Generate candles for the opening range window."""
    from datetime import timedelta

    if base_time is None:
        base_time = datetime(2026, 2, 15, 9, 30, 0, tzinfo=UTC)

    candles = []
    for i in range(num_candles):
        timestamp = base_time + timedelta(minutes=i)
        # Vary prices within the OR range
        high = or_high if i == 5 else or_high - 0.5  # One candle hits the high
        low = or_low if i == 10 else or_low + 0.3  # One candle hits the low
        close = (or_high + or_low) / 2 + (i % 3 - 1) * 0.2

        candles.append(
            make_candle(
                symbol=symbol,
                timestamp=timestamp,
                open_price=close - 0.1,
                high=high,
                low=low,
                close=close,
                volume=100_000 + i * 1000,
            )
        )
    return candles


class TestOrbOpeningRangeFormation:
    """Tests for opening range formation."""

    @pytest.mark.asyncio
    async def test_accumulates_candles_during_or_window(self) -> None:
        """Candles during OR window are accumulated."""
        config = make_orb_config(orb_window_minutes=15)
        strategy = OrbBreakoutStrategy(config)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Send 15 candles during OR window (9:30 - 9:44)
        or_candles = make_or_candles("AAPL", num_candles=15)
        for candle in or_candles:
            await strategy.on_candle(candle)

        state = strategy._get_symbol_state("AAPL")
        assert len(state.or_candles) == 15
        assert not state.or_complete

    @pytest.mark.asyncio
    async def test_finalizes_or_after_window(self) -> None:
        """OR is finalized after the first candle past the window."""
        config = make_orb_config(orb_window_minutes=15)
        strategy = OrbBreakoutStrategy(config)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Send OR candles
        or_candles = make_or_candles("AAPL", num_candles=15, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        # Send first candle after OR window (9:45)
        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 9, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        state = strategy._get_symbol_state("AAPL")
        assert state.or_complete
        assert state.or_high == 101.0
        assert state.or_low == 99.0
        assert state.or_midpoint == 100.0

    @pytest.mark.asyncio
    async def test_or_too_tight_rejected(self) -> None:
        """OR with range too tight relative to ATR is rejected."""
        config = make_orb_config(min_range_atr_ratio=0.5)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 5.0  # ATR = 5.0

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # OR range = 0.5 (high=100.5, low=100.0)
        # range/ATR = 0.5/5.0 = 0.1 < min_range_atr_ratio (0.5)
        or_candles = make_or_candles("AAPL", num_candles=15, or_high=100.5, or_low=100.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        # Finalize
        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 9, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        state = strategy._get_symbol_state("AAPL")
        assert state.or_complete
        assert not state.or_valid
        assert "too tight" in state.or_rejection_reason.lower()

    @pytest.mark.asyncio
    async def test_or_too_wide_rejected(self) -> None:
        """OR with range too wide relative to ATR is rejected."""
        config = make_orb_config(max_range_atr_ratio=2.0)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 1.0  # ATR = 1.0

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # OR range = 5.0 (high=105, low=100)
        # range/ATR = 5.0/1.0 = 5.0 > max_range_atr_ratio (2.0)
        or_candles = make_or_candles("AAPL", num_candles=15, or_high=105.0, or_low=100.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        # Finalize
        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 9, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        state = strategy._get_symbol_state("AAPL")
        assert state.or_complete
        assert not state.or_valid
        assert "too wide" in state.or_rejection_reason.lower()


class TestOrbBreakoutDetection:
    """Tests for breakout detection logic."""

    async def _setup_valid_or(
        self,
        strategy: OrbBreakoutStrategy,
        symbol: str = "AAPL",
        or_high: float = 101.0,
        or_low: float = 99.0,
    ) -> None:
        """Helper to set up a valid opening range."""
        strategy.set_watchlist([symbol])

        or_candles = make_or_candles(symbol, num_candles=15, or_high=or_high, or_low=or_low)
        for candle in or_candles:
            await strategy.on_candle(candle)

        # Finalize OR
        post_or = make_candle(
            symbol=symbol,
            timestamp=datetime(2026, 2, 15, 9, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

    @pytest.mark.asyncio
    async def test_breakout_above_or_high_emits_signal(self) -> None:
        """Candle closing above OR high with volume emits signal."""
        config = make_orb_config(breakout_volume_multiplier=1.5, chase_protection_pct=0.02)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,  # Below entry price
        }.get(i)

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        # Breakout candle: close above OR high, high volume
        # Chase limit = 101.0 * 1.02 = 103.02 (with 2% chase protection)
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC),
            open_price=101.0,
            high=102.5,
            low=100.8,
            close=102.0,  # Above OR high (101.0), within chase limit
            volume=200_000,  # 2x avg volume (should exceed 1.5x threshold)
        )
        signal = await strategy.on_candle(breakout)

        assert signal is not None
        assert isinstance(signal, SignalEvent)
        assert signal.symbol == "AAPL"
        assert signal.side == Side.LONG
        assert signal.entry_price == 102.0
        assert signal.stop_price == 100.0  # Midpoint of OR

    @pytest.mark.asyncio
    async def test_wick_above_or_high_no_signal(self) -> None:
        """Candle with wick above OR high but close below does not emit signal."""
        config = make_orb_config()
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 2.0

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        # Wick above OR high but close below
        wick = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC),
            open_price=100.5,
            high=102.0,  # Wicks above OR high
            low=100.3,
            close=100.8,  # Closes below OR high
            volume=200_000,
        )
        signal = await strategy.on_candle(wick)

        assert signal is None

    @pytest.mark.asyncio
    async def test_low_volume_breakout_no_signal(self) -> None:
        """Breakout with insufficient volume does not emit signal."""
        config = make_orb_config(breakout_volume_multiplier=1.5)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 100.0  # VWAP

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        # Breakout but low volume
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC),
            open_price=101.0,
            high=102.5,
            low=100.8,
            close=102.0,  # Above OR high
            volume=50_000,  # Below 1.5x avg volume
        )
        signal = await strategy.on_candle(breakout)

        assert signal is None

    @pytest.mark.asyncio
    async def test_below_vwap_no_signal(self) -> None:
        """Breakout below VWAP does not emit signal."""
        config = make_orb_config()
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 105.0,  # VWAP is above entry price
        }.get(i)

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        # Breakout but below VWAP
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC),
            close=102.0,  # Above OR high but below VWAP (105)
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is None

    @pytest.mark.asyncio
    async def test_chase_protection_no_signal(self) -> None:
        """Breakout past chase protection threshold does not emit signal."""
        config = make_orb_config(chase_protection_pct=0.005)  # 0.5%
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000

        await self._setup_valid_or(strategy, or_high=101.0, or_low=99.0)

        # Chase protection limit = 101.0 * 1.005 = 101.505
        # Close above this triggers chase protection
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC),
            close=102.0,  # Above chase protection limit
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is None


class TestSignalCorrectness:
    """Tests for correct signal values."""

    @pytest.mark.asyncio
    async def test_signal_entry_price_is_candle_close(self) -> None:
        """Signal entry price equals candle close."""
        config = make_orb_config(chase_protection_pct=0.05)  # Looser chase protection
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Set up OR
        or_candles = make_or_candles("AAPL", num_candles=15, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 9, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        # Breakout
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is not None
        assert signal.entry_price == 101.5

    @pytest.mark.asyncio
    async def test_signal_stop_is_or_midpoint(self) -> None:
        """Signal stop price equals OR midpoint."""
        config = make_orb_config(chase_protection_pct=0.05)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # OR: high=102, low=100, midpoint=101
        or_candles = make_or_candles("AAPL", num_candles=15, or_high=102.0, or_low=100.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 9, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC),
            close=102.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is not None
        assert signal.stop_price == 101.0  # Midpoint

    @pytest.mark.asyncio
    async def test_signal_targets_are_correct(self) -> None:
        """Signal targets are calculated correctly from R-multiples."""
        config = make_orb_config(target_1_r=1.0, target_2_r=2.0, chase_protection_pct=0.05)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.side_effect = lambda s, i: {
            "atr_14": 2.0,
            "vwap": 100.0,
        }.get(i)

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # OR: high=101, low=99, midpoint=100
        or_candles = make_or_candles("AAPL", num_candles=15, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 9, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        # Entry = 101.5, Stop = 100, Risk = 1.5
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is not None
        # Target 1 = entry + 1R = 101.5 + 1.5 = 103.0
        # Target 2 = entry + 2R = 101.5 + 3.0 = 104.5
        assert signal.target_prices[0] == pytest.approx(103.0)
        assert signal.target_prices[1] == pytest.approx(104.5)


class TestRiskLimits:
    """Tests for risk limit enforcement."""

    @pytest.mark.asyncio
    async def test_max_trades_reached_no_signal(self) -> None:
        """No signal after max_trades_per_day reached."""
        config = make_orb_config(max_trades_per_day=2, chase_protection_pct=0.05)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 100.0

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Record max trades
        strategy.record_trade_result(100)
        strategy.record_trade_result(100)

        # Set up valid OR
        or_candles = make_or_candles("AAPL", num_candles=15, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 9, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        # Valid breakout should be rejected due to max trades
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is None

    @pytest.mark.asyncio
    async def test_max_daily_loss_reached_no_signal(self) -> None:
        """No signal after max daily loss reached."""
        config = make_orb_config(max_daily_loss_pct=0.03, chase_protection_pct=0.05)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 100.0

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Record 3% loss
        strategy.record_trade_result(-3000)

        # Set up valid OR
        or_candles = make_or_candles("AAPL", num_candles=15, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 9, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is None


class TestTimeWindow:
    """Tests for time window enforcement."""

    @pytest.mark.asyncio
    async def test_after_latest_entry_no_signal(self) -> None:
        """No signal after latest entry time."""
        config = make_orb_config(latest_entry="11:30", chase_protection_pct=0.05)
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 100.0

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Set up valid OR
        or_candles = make_or_candles("AAPL", num_candles=15, or_high=101.0, or_low=99.0)
        for candle in or_candles:
            await strategy.on_candle(candle)

        post_or = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 9, 45, 0, tzinfo=UTC),
        )
        await strategy.on_candle(post_or)

        # Breakout after latest entry (11:31)
        breakout = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 11, 31, 0, tzinfo=UTC),
            close=101.5,
            volume=200_000,
        )
        signal = await strategy.on_candle(breakout)

        assert signal is None

    @pytest.mark.asyncio
    async def test_during_or_formation_no_signal(self) -> None:
        """No signal during OR formation period."""
        config = make_orb_config()
        strategy = OrbBreakoutStrategy(config)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Candle during OR window (9:44) - even if it looks like breakout
        candle = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 9, 44, 0, tzinfo=UTC),
            close=105.0,  # Would be above any OR high
            volume=200_000,
        )
        signal = await strategy.on_candle(candle)

        # Should not emit signal during OR formation
        assert signal is None


class TestStateManagement:
    """Tests for state management."""

    def test_reset_daily_state_clears_symbol_state(self) -> None:
        """reset_daily_state clears all symbol state."""
        config = make_orb_config()
        strategy = OrbBreakoutStrategy(config)

        # Add some state
        state = strategy._get_symbol_state("AAPL")
        state.or_complete = True
        state.or_high = 101.0

        strategy.reset_daily_state()

        # State should be cleared
        assert "AAPL" not in strategy._symbol_state


class TestMultiSymbol:
    """Tests for multi-symbol handling."""

    @pytest.mark.asyncio
    async def test_independent_or_tracking(self) -> None:
        """Each symbol has independent OR tracking."""
        config = make_orb_config()
        mock_data_service = AsyncMock()
        mock_data_service.get_indicator.return_value = 2.0

        strategy = OrbBreakoutStrategy(config, data_service=mock_data_service)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL", "MSFT"])

        # Feed AAPL candles
        aapl_candles = make_or_candles("AAPL", num_candles=15, or_high=150.0, or_low=148.0)
        for candle in aapl_candles:
            await strategy.on_candle(candle)

        # Feed MSFT candles (different OR)
        msft_candles = make_or_candles("MSFT", num_candles=15, or_high=350.0, or_low=345.0)
        for candle in msft_candles:
            await strategy.on_candle(candle)

        # Finalize both
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                timestamp=datetime(2026, 2, 15, 9, 45, 0, tzinfo=UTC),
            )
        )
        await strategy.on_candle(
            make_candle(
                symbol="MSFT",
                timestamp=datetime(2026, 2, 15, 9, 45, 0, tzinfo=UTC),
            )
        )

        aapl_state = strategy._get_symbol_state("AAPL")
        msft_state = strategy._get_symbol_state("MSFT")

        assert aapl_state.or_high == 150.0
        assert msft_state.or_high == 350.0

        # They should be independent
        assert aapl_state.or_low != msft_state.or_low


class TestPositionSizing:
    """Tests for position sizing calculation."""

    def test_position_size_formula(self) -> None:
        """Position size uses correct formula."""
        config = make_orb_config(max_loss_per_trade_pct=0.01)
        strategy = OrbBreakoutStrategy(config)
        strategy.allocated_capital = 100_000

        # Entry: 102, Stop: 100, Risk per share: 2
        # Risk dollars: 100K * 1% = 1000
        # Shares: 1000 / 2 = 500
        shares = strategy.calculate_position_size(102.0, 100.0)
        assert shares == 500

    def test_position_size_zero_capital(self) -> None:
        """Returns 0 if no capital allocated."""
        config = make_orb_config()
        strategy = OrbBreakoutStrategy(config)

        shares = strategy.calculate_position_size(102.0, 100.0)
        assert shares == 0
